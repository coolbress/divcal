"""구조화 로깅 — 서비스 아키타입의 **트리에 사는** 관측성.

🔴 **세 기둥 중 이것만 저장소에 산다.** 코퍼스 측면 19 의 claim 이 직접 말한다 —
*"instrument services for the three pillars (structured logs, RED/USE metrics, distributed
traces) … and **treat live monitoring/SLO targets as out-of-repo posture**"*.
메트릭·트레이스·SLO·대시보드는 Datadog/Grafana/PagerDuty 에 있지 트리에 없다
(실측: observability-as-code **~17%**). 그것들을 여기 넣으면 **스텁**이 된다.

로그는 다르다. **어떤 모양으로 찍을지는 코드가 정한다.**

🔴 **그리고 그 답은 하나가 아니다** (2026-08-31 정정). 첫 판은 *"사람이 읽는 줄로 찍으면
수집기가 못 파싱한다"* 를 이유로 **JSON 하나만** 냈다. 그런데 **개발 중에는 터미널을 읽는다** —
서비스를 처음 만드는 사람이 맨 먼저 부딪히는 자리다. 형식이 틀렸던 게 아니라
**빠져나갈 문이 없던 것**이 틀렸다.

⚠️ **그렇다고 `isatty()` 단독으로 가르지 않는다.** `docker run -t` 면 **프로덕션에서도 TTY** 이고,
그러면 수집기가 사람용 줄을 받는다 — **환경에 따라 조용히 달라지는 것**이 원래 피하려던 것이다.
**명시가 이긴다**: 인자 → 환경변수 → 그래도 없을 때만 `isatty()`.

⚠️ **의존성을 안 늘린다** — 표준 라이브러리만 쓴다. `structlog`·`loguru` 를 박으면
그걸 안 쓰는 프로젝트에 짐이 된다.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any

#: `LogRecord` 가 원래 갖는 필드. 🔴 **두 포매터가 같은 목록을 봐야 한다** —
#: 갈리면 한쪽에서만 문맥이 사라지고 그게 배포 뒤에 드러난다.
_RESERVED = set(logging.LogRecord("", 0, "", 0, "", None, None).__dict__) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    """한 줄에 하나의 JSON 객체. 컨테이너 표준 출력이 그대로 수집된다."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        # 🔴 `logger.info("...", extra={"order_id": 7})` 로 넘긴 것을 살린다.
        # 이게 없으면 구조화의 값이 절반이다 — 문맥이 message 문자열에 녹아버린다.
        payload.update({k: v for k, v in record.__dict__.items() if k not in _RESERVED})
        return json.dumps(payload, ensure_ascii=False, default=str)


class TextFormatter(logging.Formatter):
    """사람이 읽는 한 줄. 🔴 **`extra=` 문맥을 여기서도 살린다.**

    안 살리면 터미널에서만 문맥이 사라지고, 그건 *개발 중에 안 보이던 것이
    프로덕션에서만 보이는* 형태가 된다 — 디버깅이 가장 어려운 부류다.
    """

    def format(self, record: logging.LogRecord) -> str:
        head = f"{self.formatTime(record, '%H:%M:%S')} {record.levelname:<5} {record.getMessage()}"
        extra = {k: v for k, v in record.__dict__.items() if k not in _RESERVED}
        if extra:
            head += "  " + " ".join(f"{k}={v}" for k, v in sorted(extra.items()))
        if record.exc_info:
            head += "\n" + self.formatException(record.exc_info)
        return head


def _resolve(fmt: str | None) -> str:
    """어느 형식으로 찍을지 정한다. **명시가 이긴다.**

    1. 인자 `fmt`
    2. 환경변수 `LOG_FORMAT`
    3. 둘 다 없으면 — stdout 이 터미널이면 `text`, 아니면 `json`

    ⚠️ 3번만으로 가르지 않는 이유: `docker run -t` 면 **프로덕션에도 TTY 가 붙는다.**
    """
    chosen = fmt or os.environ.get("LOG_FORMAT")
    if chosen in ("json", "text"):
        return chosen
    if chosen:
        raise ValueError(f"LOG_FORMAT 은 json 또는 text 다: {chosen!r}")
    return "text" if sys.stdout.isatty() else "json"


def configure(level: int = logging.INFO, fmt: str | None = None) -> None:
    """루트 로거를 stdout 으로 맞춘다. 여러 번 불러도 핸들러가 안 쌓인다.

    `fmt`: `"json"` · `"text"` · `None`(자동 — 위 `_resolve` 규칙).
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter() if _resolve(fmt) == "json" else TextFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
