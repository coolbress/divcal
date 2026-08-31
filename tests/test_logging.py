"""로그가 **기계가 읽을 수 있는 모양**으로 나오는가.

`presence ≠ adequacy` — 로깅 설정 파일이 있다는 것과 수집기가 파싱할 수 있다는 것은 다르다.
사람이 읽는 한 줄로 찍으면 **배포한 뒤에야** 안다.

🔴 세 기둥 중 이것만 검사한다. 메트릭·트레이스·SLO 는 **트리에 안 산다** —
코퍼스 측면 19 의 claim 이 *"out-of-repo posture"* 라고 못박는다.
"""

from __future__ import annotations

import json
import logging
import tomllib
from io import StringIO
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _pkg() -> str:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    name: str = data["project"]["name"]
    return name.replace("-", "_")


@pytest.fixture
def emitted() -> list[str]:
    """루트 로거를 잡아 실제로 찍힌 줄을 모은다."""
    mod = __import__(f"{_pkg()}._logging", fromlist=["configure", "JsonFormatter"])
    buf = StringIO()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(mod.JsonFormatter())
    log = logging.getLogger("probe")
    log.handlers.clear()
    log.addHandler(handler)
    log.setLevel(logging.INFO)
    log.propagate = False
    log.info("hello", extra={"order_id": 7})
    try:
        raise ValueError("boom")
    except ValueError:
        log.exception("failed")
    return [ln for ln in buf.getvalue().splitlines() if ln]


def test_every_line_is_one_json_object(emitted: list[str]) -> None:
    for line in emitted:
        json.loads(line)  # 못 파싱하면 여기서 터진다


def test_the_fields_a_collector_needs_are_there(emitted: list[str]) -> None:
    first = json.loads(emitted[0])
    for key in ("time", "level", "logger", "message"):
        assert key in first, f"{key} 가 없다 — 수집기가 이 줄을 분류하지 못한다"
    assert first["message"] == "hello"


def test_extra_context_survives(emitted: list[str]) -> None:
    """🔴 이게 없으면 구조화의 값이 절반이다 — 문맥이 message 문자열에 녹아버린다."""
    assert json.loads(emitted[0]).get("order_id") == 7


def test_exceptions_carry_their_traceback(emitted: list[str]) -> None:
    last = json.loads(emitted[-1])
    assert "exception" in last, "예외가 로그에 안 실린다 — 사후에 원인을 못 찾는다"
    assert "ValueError" in last["exception"]


def test_configure_is_idempotent() -> None:
    """훅·프레임워크가 두 번 부를 수 있다. 핸들러가 쌓이면 줄이 중복된다."""
    mod = __import__(f"{_pkg()}._logging", fromlist=["configure"])
    mod.configure()
    n = len(logging.getLogger().handlers)
    mod.configure()
    assert len(logging.getLogger().handlers) == n


def _mod() -> ModuleType:
    """이 패키지의 `_logging` 을 이름으로 불러온다 (패키지 이름이 렌더 시점에 정해진다).

    ⚠️ 반환 타입을 적는다. 첫 판은 `# noqa: ANN202` 로 넘겼는데 **인스턴스의 ruff 설정엔
    `ANN` 이 없어서** 그 억제가 `RUF100`(쓰이지 않은 noqa)으로 되돌아왔다 —
    그리고 `mypy --strict` 는 **untyped 호출**로 따로 걸었다. **억제가 아니라 타입이 답이다.**
    """
    return __import__(f"{_pkg()}._logging", fromlist=["_resolve", "TextFormatter"])


def test_explicit_argument_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    """🔴 **명시가 이긴다.** 환경도 터미널도 이걸 못 뒤집는다."""
    monkeypatch.setenv("LOG_FORMAT", "json")
    assert _mod()._resolve("text") == "text"


def test_env_beats_the_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    """⚠️ `docker run -t` 면 **프로덕션에도 TTY** 가 붙는다 — 그때 이 줄이 벽이다."""
    monkeypatch.setenv("LOG_FORMAT", "json")
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)
    assert _mod()._resolve(None) == "json"


def test_falls_back_to_the_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LOG_FORMAT", raising=False)
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)
    assert _mod()._resolve(None) == "text"
    monkeypatch.setattr("sys.stdout.isatty", lambda: False)
    assert _mod()._resolve(None) == "json"


def test_a_wrong_value_is_refused_not_guessed(monkeypatch: pytest.MonkeyPatch) -> None:
    """🔴 오타를 조용히 기본값으로 넘기면 **틀린 형식이 프로덕션까지 간다.**"""
    monkeypatch.setenv("LOG_FORMAT", "JSON ")
    # 🔴 `match=` 로 **이유까지** 본다. 종류만 보면 엉뚱한 `ValueError` 도 통과한다.
    with pytest.raises(ValueError, match="json 또는 text"):
        _mod()._resolve(None)


def test_text_keeps_the_extra_context() -> None:
    """🔴 터미널에서만 문맥이 사라지면 **개발 중에 안 보이던 것이 프로덕션에서만 보인다.**"""
    rec = logging.LogRecord("p", logging.INFO, "f", 1, "hello", None, None)
    rec.order_id = 7
    line = _mod().TextFormatter().format(rec)
    assert "hello" in line
    assert "order_id=7" in line
