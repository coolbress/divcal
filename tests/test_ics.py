"""#6 의 AC-1 ~ AC-6 — 지급 목록이 `VCALENDAR` 텍스트가 되는 부분."""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from pathlib import Path

from divcal.cashflow import Payment, load_payments
from divcal.ics import to_ics

ROOT = Path(__file__).resolve().parent.parent

RATE = Decimal(15)
KO = Payment("KO", Decimal(100), Decimal("0.485"), date(2026, 4, 1))
SCHD = Payment("SCHD", Decimal(50), Decimal("0.2645"), date(2026, 3, 25))

#: `DTSTAMP` 는 생성 시각이라 매번 다르다 — AC-5 는 **그것만 빼고** 같기를 요구한다.
DTSTAMP = re.compile(r"DTSTAMP:[^\r\n]*\r\n")
UID = re.compile(r"UID:([^\r\n]+)")
AMOUNT = re.compile(r"SUMMARY:[^$\r\n]*\$([\d,.]+)")


def test_vcalendar_skeleton() -> None:
    """AC-1 — 규격이 요구하는 뼈대와 **CRLF**, 그리고 지급 건당 `VEVENT` 하나."""
    text = to_ics([KO, SCHD])

    assert text.startswith("BEGIN:VCALENDAR\r\n")
    assert text.endswith("END:VCALENDAR\r\n")
    assert "VERSION:2.0\r\n" in text
    assert "PRODID:-//coolbress//divcal" in text
    assert "X-WR-CALNAME:" in text
    assert text.count("BEGIN:VEVENT") == text.count("END:VEVENT") == 2
    # CRLF 를 걷어내고 남은 LF 가 있으면 §3.1 을 어긴 줄이 있다는 뜻이다.
    assert "\n" not in text.replace("\r\n", "")


def test_all_day_no_dtend() -> None:
    """AC-2 — 종일 일정이다. `DTEND` 를 주면 안 된다 (§3.6.1 이 DATE 값에 하루를 준다)."""
    text = to_ics([KO])

    assert "DTSTART;VALUE=DATE:20260401\r\n" in text
    assert "DTEND" not in text


def test_summary_after_tax() -> None:
    """AC-3 — `--tax` 를 주면 세후, 안 주면 세전이다."""
    assert "SUMMARY:KO 배당 $48.50\r\n" in to_ics([KO])
    assert "SUMMARY:KO 배당 $41.22\r\n" in to_ics([KO], RATE)


def test_net_matches_table() -> None:
    """AC-4 — 표와 **같은 건별 반올림**이다. `세전 = 세후 + 세액` 이 깨지지 않는다.

    세전 `48.50` 에 `0.85` 를 곱해 접으면 `41.23` 이 나오고 그러면 항등식이 깨진다(#4 AC-3).
    ics 가 표와 다른 숫자를 보여주면 폰과 터미널이 서로 다른 말을 하게 된다.
    """
    net = Decimal(AMOUNT.findall(to_ics([KO], RATE))[0])

    assert net == KO.total - KO.withheld(RATE) == Decimal("41.22")
    assert KO.total == net + KO.withheld(RATE)


def test_uid_stable() -> None:
    """AC-5 — 같은 CSV 면 `DTSTAMP` 를 뺀 나머지가 바이트 단위로 같다."""
    first, second = to_ics([KO, SCHD], RATE), to_ics([KO, SCHD], RATE)

    assert DTSTAMP.sub("", first) == DTSTAMP.sub("", second)
    # 같은 날 같은 종목이 두 번 지급돼도 UID 가 겹치면 안 된다 —
    # 겹치면 캘린더가 둘을 한 일정으로 보고 **한 건이 소리 없이 사라진다.**
    assert len(set(UID.findall(to_ics([KO, KO])))) == 2
    # 세율을 켰다 껐다 해도 같은 지급은 같은 일정이다 (지웠다 다시 만들지 않는다).
    assert UID.findall(to_ics([KO])) == UID.findall(to_ics([KO], RATE))


def test_summary_fits_unfolded() -> None:
    """AC-6 — 줄 접기(folding)를 **안 만드는 대신** 두는 가드다.

    §3.1 은 한 줄을 75옥텟으로 제한한다. 넘는 줄이 나오면 여기서 걸리고, 그때
    `ics.py` 의 `ponytail:` 가 가리키는 접기를 넣으면 된다.
    """
    text = to_ics(load_payments(ROOT / "examples" / "schedule.csv"), RATE)

    too_long = [line for line in text.split("\r\n") if len(line.encode()) > 75]

    assert not too_long, f"75옥텟을 넘는 줄이 있다 — 접든가 줄이든가: {too_long}"
