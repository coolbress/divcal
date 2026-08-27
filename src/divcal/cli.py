"""`divcal <예정표.csv> <연도>` — 명령줄 표면.

여기서는 **인자를 받고 오류를 사람 말로 옮기는 일만** 한다. 계산은 `cashflow` 에 있다.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from divcal.cashflow import COLUMNS, ScheduleError, format_year, load_payments, monthly_totals

EXIT_BAD_INPUT = 2


def main(argv: Sequence[str] | None = None) -> int:
    """종료코드를 돌려준다. 입력이 틀리면 트레이스백 대신 한 줄과 `2` 다."""
    parser = argparse.ArgumentParser(
        prog="divcal",
        description="배당 지급 예정표를 월별 현금흐름 표로 접는다 (세전 · USD).",
    )
    parser.add_argument("schedule", type=Path, help=f"지급 예정 CSV ({','.join(COLUMNS)})")
    parser.add_argument("year", type=int, help="볼 연도 (예: 2026)")
    args = parser.parse_args(argv)

    try:
        payments = load_payments(args.schedule)
    except ScheduleError as exc:
        print(f"divcal: {exc}", file=sys.stderr)
        return EXIT_BAD_INPUT

    print(format_year(monthly_totals(payments, args.year), args.year))
    return 0
