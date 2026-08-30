"""`Payment` 목록을 RFC 5545 `VCALENDAR` 텍스트로 옮긴다 (#6 AC-1~6).

캘린더 앱이 구독하는 것은 **이 텍스트 한 장**이다. 여기에는 서버도 파일도 없다 —
`serve` 가 요청마다 이 함수를 부른다. 계산은 여전히 `cashflow` 에 있다.
"""

from __future__ import annotations

import hashlib
from collections import Counter
from collections.abc import Iterable
from datetime import UTC, datetime
from decimal import Decimal
from typing import Final

from divcal.cashflow import Payment

#: RFC 5545 §3.1 — 줄 끝은 **CRLF** 다. LF 만 주면 안 읽는 클라이언트가 있다.
CRLF: Final = "\r\n"
PRODID: Final = "-//coolbress//divcal//KO"
#: 구독한 캘린더의 이름. `X-WR-CALNAME` 은 규격 밖이지만 애플·구글이 둘 다 읽는다.
CALNAME: Final = "배당 (divcal)"


def _escape(text: str) -> str:
    r"""RFC 5545 §3.3.11 — TEXT 값의 `\` · `;` · `,` 를 막는다.

    티커는 사람이 손으로 적는 CSV 에서 온다. 쉼표 하나가 그대로 나가면 `SUMMARY` 가
    두 값으로 쪼개져 **일정이 깨진 채로 조용히 구독된다.** 역슬래시를 먼저 바꾼다.
    """
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")


def _uid(key: str) -> str:
    """같은 지급이면 언제나 같은 `UID` (AC-5).

    난수를 쓰면 폰이 동기화할 때마다 **같은 일정이 지워졌다 다시 생긴다** — 알림도 다시 온다.
    """
    return f"{hashlib.sha256(key.encode()).hexdigest()[:32]}@divcal"


def to_ics(payments: Iterable[Payment], rate: Decimal | None = None) -> str:
    """지급 목록을 `VCALENDAR` 한 장으로. `rate` 를 주면 `SUMMARY` 가 **세후**다 (AC-3)."""
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{PRODID}",
        f"X-WR-CALNAME:{CALNAME}",
    ]
    seen: Counter[str] = Counter()
    for payment in payments:
        # 세금은 `Payment` 가 뗀다 — 표와 **같은 건별 반올림**이어야 한다 (AC-4, #4 AC-3).
        amount = payment.total if rate is None else payment.total - payment.withheld(rate)
        # UID 는 **세전** 기준이다. `--tax` 를 켜고 껐다고 같은 지급이 다른 일정이 되면 안 된다.
        key = f"{payment.ticker}|{payment.pay_date.isoformat()}|{payment.total}"
        seen[key] += 1  # 같은 날 같은 종목이 두 번이면 UID 가 겹친다 — 순번으로 가른다
        lines += [
            "BEGIN:VEVENT",
            f"UID:{_uid(key + '|' + str(seen[key]))}",
            f"DTSTAMP:{stamp}",
            # 종일 일정이다. DATE 값에는 **DTEND 를 안 준다** — §3.6.1 이 하루를 준다 (AC-2).
            f"DTSTART;VALUE=DATE:{payment.pay_date:%Y%m%d}",
            # ponytail: 줄 접기(folding)를 안 만든다. 75옥텟을 넘는 줄은
            # `tests/test_ics.py::test_summary_fits_unfolded` 가 잡는다 —
            # 긴 티커가 실제로 나오면 그때 §3.1 접기를 넣는다.
            f"SUMMARY:{_escape(payment.ticker)} 배당 ${amount:,.2f}",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return CRLF.join(lines) + CRLF
