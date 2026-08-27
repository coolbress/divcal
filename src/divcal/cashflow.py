"""배당 지급 예정표를 읽어 **월 축으로 접는다.**

도구가 전부 종목 축이라 *"다음 달에 얼마 들어오나"* 가 안 보인다는 것이 문제였다(#1).
그래서 이 모듈은 세 가지만 한다 — 읽고(`load_payments`), 접고(`monthly_totals`),
찍는다(`format_year`). 네트워크도 세금도 환율도 여기 없다.
"""

from __future__ import annotations

import csv
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import Final

#: 지급 예정표가 반드시 가져야 할 칼럼. 순서는 상관없고 이름만 본다.
COLUMNS: Final = ("ticker", "shares", "amount_per_share", "pay_date")

MONTHS: Final = 12
CENT: Final = Decimal("0.01")
ZERO: Final = Decimal("0.00")

# `date.fromisoformat` 은 3.11 부터 `20260401` 같은 축약형도 받는다.
# 예정표는 사람이 손으로 적는 파일이라 형식을 하나로 못박는 편이 오해가 적다.
_ISO_DATE: Final = re.compile(r"\d{4}-\d{2}-\d{2}")


class ScheduleError(ValueError):
    """예정표를 읽을 수 없다.

    메시지는 **사람이 파일을 고칠 수 있을 만큼** 구체적이어야 한다 —
    몇 번째 줄의 어느 칸이 왜 틀렸는지. `divcal: ...` 한 줄로 그대로 출력된다.
    """


@dataclass(frozen=True, slots=True)
class Payment:
    """한 번의 지급. **한 행이 한 번의 지급**이고 그 시점 보유수량이 그 행에 있다(#1 가정 3)."""

    ticker: str
    shares: Decimal
    amount_per_share: Decimal
    pay_date: date

    @property
    def total(self) -> Decimal:
        """세전 지급액.

        **반올림은 여기서 한 번만 한다.** 실제로 계좌에 꽂히는 것은 지급 건별 센트 단위이므로,
        건별로 반올림한 뒤 더하는 것이 합계를 반올림하는 것보다 명세서에 가깝다.
        """
        return (self.shares * self.amount_per_share).quantize(CENT, rounding=ROUND_HALF_UP)


def _cell(row: dict[str, str | None], column: str, line: int) -> str:
    raw = (row.get(column) or "").strip()
    if not raw:
        raise ScheduleError(f"{line}번째 줄: {column} 이(가) 비었다")
    return raw


def _amount(raw: str, column: str, line: int) -> Decimal:
    try:
        value = Decimal(raw)
    except InvalidOperation:
        raise ScheduleError(f"{line}번째 줄: {column} 이(가) 숫자가 아니다 — {raw!r}") from None
    # NaN·Infinity 는 `Decimal()` 을 통과하고 비교 연산에서 터진다. 여기서 잡는다.
    if not value.is_finite():
        raise ScheduleError(f"{line}번째 줄: {column} 이(가) 숫자가 아니다 — {raw!r}")
    if value < 0:
        raise ScheduleError(f"{line}번째 줄: {column} 이(가) 음수다 — {raw!r}")
    return value


def _pay_date(raw: str, line: int) -> date:
    if not _ISO_DATE.fullmatch(raw):
        raise ScheduleError(f"{line}번째 줄: pay_date 는 YYYY-MM-DD 여야 한다 — {raw!r}")
    try:
        return date.fromisoformat(raw)
    except ValueError:
        raise ScheduleError(f"{line}번째 줄: 없는 날짜다 — {raw!r}") from None


def load_payments(path: Path) -> list[Payment]:
    """예정표 CSV 를 읽는다. 한 칸이라도 틀리면 `ScheduleError` 로 멈춘다."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise ScheduleError(f"파일이 없다: {path}") from None
    except UnicodeDecodeError:
        raise ScheduleError(f"UTF-8 로 읽을 수 없다: {path}") from None

    reader = csv.DictReader(text.splitlines())
    missing = [c for c in COLUMNS if c not in (reader.fieldnames or ())]
    if missing:
        raise ScheduleError(
            f"머리글에 칼럼이 없다: {', '.join(missing)} (필요: {', '.join(COLUMNS)})"
        )

    payments: list[Payment] = []
    for line, row in enumerate(reader, start=2):  # 1번 줄은 머리글이다
        payments.append(
            Payment(
                ticker=_cell(row, "ticker", line),
                shares=_amount(_cell(row, "shares", line), "shares", line),
                amount_per_share=_amount(
                    _cell(row, "amount_per_share", line), "amount_per_share", line
                ),
                pay_date=_pay_date(_cell(row, "pay_date", line), line),
            )
        )
    return payments


def monthly_totals(payments: Iterable[Payment], year: int) -> list[Decimal]:
    """그 해의 월별 세전 합계 **12개**. 지급이 없는 달도 자리를 비우지 않는다."""
    totals = [ZERO] * MONTHS
    for payment in payments:
        if payment.pay_date.year == year:
            totals[payment.pay_date.month - 1] += payment.total
    return totals


def format_year(totals: Sequence[Decimal], year: int) -> str:
    """월별 합계를 터미널 표 한 장으로 만든다. 금액은 오른쪽 정렬한다."""
    if len(totals) != MONTHS:
        raise ValueError(f"월별 합계는 {MONTHS}개여야 한다 — {len(totals)}개를 받았다")

    year_total = sum(totals, ZERO)
    cells = [f"{amount:,.2f}" for amount in totals]
    width = max(len(cell) for cell in (*cells, f"{year_total:,.2f}"))

    lines = [f"{year} 배당 현금흐름 (세전, USD)", ""]
    lines += [
        f"  {month:>2}월  {cell:>{width}}"
        for month, cell in zip(range(1, MONTHS + 1), cells, strict=True)
    ]
    # 라벨 칸은 4열이다 — "  1월" 도 "합계" 도 화면에서 4열을 쓴다.
    lines.append(f"  {'─' * (width + 6)}")
    lines.append(f"  합계  {year_total:>{width},.2f}")
    return "\n".join(lines)
