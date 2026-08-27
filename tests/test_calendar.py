"""#1 의 AC-1 ~ AC-4 — 읽고 접는 부분."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from divcal import format_year, load_payments, monthly_totals

# 3월·4월에 한 번씩. 나머지 열 달은 비어 있다.
SCHEDULE = """\
ticker,shares,amount_per_share,pay_date
KO,100,0.485,2026-04-01
SCHD,50,0.2645,2026-03-25
KO,100,0.485,2025-04-01
"""


def _write(tmp_path: Path, text: str = SCHEDULE) -> Path:
    path = tmp_path / "schedule.csv"
    path.write_text(text, encoding="utf-8")
    return path


def test_monthly_totals(tmp_path: Path) -> None:
    """AC-1 — 12개월 + 연간 합계."""
    totals = monthly_totals(load_payments(_write(tmp_path)), 2026)

    assert len(totals) == 12
    assert totals[2] == Decimal("13.23")  # 3월: 50 * 0.2645 = 13.225 -> 13.23
    assert totals[3] == Decimal("48.50")  # 4월: 100 * 0.485
    assert sum(totals, Decimal("0.00")) == Decimal("61.73")

    rendered = format_year(totals, 2026)
    assert "2026 배당 현금흐름 (세전, USD)" in rendered
    assert rendered.count("월") == 12
    assert "48.50" in rendered
    assert "합계" in rendered
    assert "61.73" in rendered


def test_month_without_payment_is_zero(tmp_path: Path) -> None:
    """AC-2 — 지급이 없는 달도 줄이 빠지지 않는다."""
    totals = monthly_totals(load_payments(_write(tmp_path)), 2026)

    empty = [month for month, amount in enumerate(totals, start=1) if amount == Decimal("0.00")]
    assert empty == [1, 2, 5, 6, 7, 8, 9, 10, 11, 12]

    lines = format_year(totals, 2026).splitlines()
    assert lines[2].endswith("0.00")  # 1월 줄이 실제로 찍힌다
    assert sum(1 for line in lines if "0.00" in line) == 10


def test_other_year_excluded(tmp_path: Path) -> None:
    """AC-3 — 요청한 연도 밖의 지급은 합계에 없다."""
    payments = load_payments(_write(tmp_path))

    assert sum(monthly_totals(payments, 2026), Decimal("0.00")) == Decimal("61.73")
    assert sum(monthly_totals(payments, 2025), Decimal("0.00")) == Decimal("48.50")
    assert sum(monthly_totals(payments, 2024), Decimal("0.00")) == Decimal("0.00")


def test_decimal_rounding(tmp_path: Path) -> None:
    """AC-4 — `Decimal` 로 계산한다. `float` 였으면 아래 두 줄이 다 틀린다."""
    path = _write(
        tmp_path,
        "ticker,shares,amount_per_share,pay_date\n"
        "A,3,0.485,2026-01-15\n"  # 1.455 → 반올림 1.46 (float 는 1.4549999… → 1.45)
        "B,1,0.10,2026-02-10\n"
        "B,1,0.10,2026-02-20\n"
        "B,1,0.10,2026-02-28\n",  # 0.1 세 번 → float 이면 0.30000000000000004
    )
    totals = monthly_totals(load_payments(path), 2026)

    assert totals[0] == Decimal("1.46")
    assert totals[1] == Decimal("0.30")
    assert str(totals[1]) == "0.30"
