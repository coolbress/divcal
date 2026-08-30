"""`divcal <예정표.csv> <연도>` — 명령줄 표면.

여기서는 **인자를 받고 오류를 사람 말로 옮기는 일만** 한다. 계산은 `cashflow` 에 있다.
`serve` 하위명령은 `divcal.serve` 가 갖는다 — 여기서는 갈래만 탄다.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from divcal.cashflow import (
    COLUMNS,
    DivcalError,
    format_year,
    format_year_after_tax,
    load_payments,
    monthly_after_tax,
    monthly_totals,
    parse_tax_rate,
)
from divcal.serve import main as serve_main

EXIT_BAD_INPUT = 2


def main(argv: Sequence[str] | None = None) -> int:
    """종료코드를 돌려준다. 입력이 틀리면 트레이스백 대신 한 줄과 `2` 다."""
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "serve":
        # 하위명령을 argparse 로 만들지 않는다 — `divcal <csv> <연도>` 가 #1 이 고정한
        # 계약이고, subparsers 를 붙이면 그 자리가 하위명령 이름으로 바뀐다.
        try:
            return serve_main(args[1:])
        except DivcalError as exc:
            print(f"divcal: {exc}", file=sys.stderr)
            return EXIT_BAD_INPUT

    parser = argparse.ArgumentParser(
        prog="divcal",
        description="배당 지급 예정표를 월별 현금흐름 표로 접는다 (세전 · USD).",
        epilog="폰 캘린더용 .ics 피드: divcal serve <예정표.csv> [--tax 15]",
    )
    parser.add_argument("schedule", type=Path, help=f"지급 예정 CSV ({','.join(COLUMNS)})")
    parser.add_argument("year", type=int, help="볼 연도 (예: 2026)")
    parser.add_argument(
        "--tax",
        metavar="퍼센트",
        help="원천징수 세율. 퍼센트 단위다 — 15%% 는 `--tax 15`. 안 주면 세전만 찍는다.",
    )
    parsed = parser.parse_args(args)

    try:
        # 세율을 먼저 본다. 플래그가 틀렸으면 파일을 읽어볼 것도 없다.
        rate = None if parsed.tax is None else parse_tax_rate(parsed.tax)
        payments = load_payments(parsed.schedule)
    except DivcalError as exc:
        print(f"divcal: {exc}", file=sys.stderr)
        return EXIT_BAD_INPUT

    if rate is None:
        # `--tax` 가 없으면 #1 의 출력 그대로다(#4 AC-2).
        print(format_year(monthly_totals(payments, parsed.year), parsed.year))
    else:
        print(
            format_year_after_tax(monthly_after_tax(payments, parsed.year, rate), parsed.year, rate)
        )
    return 0
