"""배당 지급 예정표를 읽어 **월 축으로 접는다.**

도구가 전부 종목 축이라 *"다음 달에 얼마 들어오나"* 가 안 보인다는 것이 문제였다(#1).
그래서 이 모듈은 세 가지만 한다 — 읽고(`load_payments`), 접고(`monthly_totals`),
찍는다(`format_year`). 네트워크도 세금도 환율도 여기 없다.
"""

from __future__ import annotations

import csv
import re
import unicodedata
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
HUNDRED: Final = Decimal(100)

#: 세후 표의 칼럼 머리글. 한글은 터미널에서 두 열을 먹는다 — `_pad` 를 거쳐야 자리가 맞는다.
GROSS_HEAD: Final = "세전"
NET_HEAD: Final = "세후"
#: 월 라벨 칸이 쓰는 열 수. `" 1월"` 도 `"합계"` 도 화면에서 4열이다.
LABEL: Final = 4

# `date.fromisoformat` 은 3.11 부터 `20260401` 같은 축약형도 받는다.
# 예정표는 사람이 손으로 적는 파일이라 형식을 하나로 못박는 편이 오해가 적다.
_ISO_DATE: Final = re.compile(r"\d{4}-\d{2}-\d{2}")


class DivcalError(ValueError):
    """사용자가 고칠 수 있는 입력 오류. `divcal: ...` 한 줄로 찍히고 종료코드 2 로 끝난다."""


class ScheduleError(DivcalError):
    """예정표를 읽을 수 없다.

    메시지는 **사람이 파일을 고칠 수 있을 만큼** 구체적이어야 한다 —
    몇 번째 줄의 어느 칸이 왜 틀렸는지. `divcal: ...` 한 줄로 그대로 출력된다.
    """


class TaxRateError(DivcalError):
    """`--tax` 로 받은 세율을 쓸 수 없다(#4 AC-5·AC-6)."""


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

    def withheld(self, rate: Decimal) -> Decimal:
        """이 지급에서 떼이는 원천징수액. `rate` 는 퍼센트 단위다.

        **건별로 뗀다**(#4 AC-3). 월 합계에 세율을 곱하면 명세서와 센트가 어긋난다 —
        `48.50` 은 세액 `7.28` 을 떼어 `41.22` 가 되지만, 세전에 `0.85` 를 곱해 접으면
        `41.23` 이 나오고 그러면 `48.50 != 41.23 + 7.28` 이라 `MonthTotals` 의 항등식이 깨진다.
        """
        return (self.total * rate / HUNDRED).quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True, slots=True)
class MonthTotals:
    """한 달의 세전·세액·세후. 셋은 언제나 `gross == tax + net` 이다(#4 AC-4)."""

    gross: Decimal
    tax: Decimal
    net: Decimal


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


def parse_tax_rate(raw: str) -> Decimal:
    """`--tax` 로 받은 문자열을 **퍼센트 단위** 세율로 옮긴다. `15` 가 15% 다(#4 AC-5·AC-6)."""
    try:
        rate = Decimal(raw)
    except InvalidOperation:
        raise TaxRateError(f"세율이 숫자가 아니다 — {raw!r}") from None
    if not rate.is_finite():
        raise TaxRateError(f"세율이 숫자가 아니다 — {raw!r}")
    if rate < 0:
        raise TaxRateError(f"세율이 음수다 — {raw!r}")
    if rate > HUNDRED:
        raise TaxRateError(f"세율이 100% 를 넘는다 — {raw!r}")
    # `--tax 0.15` 를 15% 로 착각하면 세금이 100배 작게 **조용히** 통과한다.
    # 원천징수에 1% 미만 세율은 없다고 보고 여기서 막는다(#4 AC-6, 가정 3).
    if 0 < rate < 1:
        raise TaxRateError(f"세율은 퍼센트 단위다 — 15% 는 `--tax 15` 라고 쓴다 (받은 값: {raw!r})")
    return rate


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


def monthly_after_tax(payments: Iterable[Payment], year: int, rate: Decimal) -> list[MonthTotals]:
    """그 해의 월별 세전·세액·세후 **12개**. 세금은 지급 건별로 뗀다(#4 AC-3)."""
    gross = [ZERO] * MONTHS
    tax = [ZERO] * MONTHS
    for payment in payments:
        if payment.pay_date.year == year:
            month = payment.pay_date.month - 1
            gross[month] += payment.total
            tax[month] += payment.withheld(rate)
    return [MonthTotals(g, t, g - t) for g, t in zip(gross, tax, strict=True)]


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


def _columns(text: str) -> int:
    """터미널에서 차지하는 **열 수**. `len()` 과 다르다 — `"세전"` 은 두 글자지만 네 열이다."""
    return sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in text)


def _pad(text: str, width: int) -> str:
    """`_columns` 기준 오른쪽 정렬. 한글 머리글과 숫자 칸을 같은 자리에 세운다."""
    return " " * max(0, width - _columns(text)) + text


def _percent(rate: Decimal) -> str:
    """머리글에 쓸 세율 문자열. `15` → `15`, `15.40` → `15.4`, `100` → `100`."""
    text = f"{rate:f}"
    # 소수점이 있을 때만 깎는다 — 그냥 rstrip("0") 하면 `100` 이 `1` 이 된다.
    return text.rstrip("0").rstrip(".") if "." in text else text


def format_year_after_tax(rows: Sequence[MonthTotals], year: int, rate: Decimal) -> str:
    """세전·세후 두 칼럼 표. 적용 세율을 머리글에 밝힌다(#4 AC-1).

    `format_year` 와 합치지 않는다 — 저쪽은 칼럼 머리글이 없는 한 칼럼 표이고,
    그 출력은 #1 이 고정한 계약이다(#4 AC-2).
    """
    if len(rows) != MONTHS:
        raise ValueError(f"월별 합계는 {MONTHS}개여야 한다 — {len(rows)}개를 받았다")

    gross_total = sum((row.gross for row in rows), ZERO)
    net_total = sum((row.net for row in rows), ZERO)
    gross_cells = [f"{row.gross:,.2f}" for row in rows]
    net_cells = [f"{row.net:,.2f}" for row in rows]

    gross_width = max(_columns(c) for c in (*gross_cells, f"{gross_total:,.2f}", GROSS_HEAD))
    net_width = max(_columns(c) for c in (*net_cells, f"{net_total:,.2f}", NET_HEAD))

    lines = [f"{year} 배당 현금흐름 (원천징수 {_percent(rate)}%, USD)", ""]
    lines.append(f"  {' ' * LABEL}  {_pad(GROSS_HEAD, gross_width)}  {_pad(NET_HEAD, net_width)}")
    lines += [
        f"  {month:>2}월  {_pad(gross, gross_width)}  {_pad(net, net_width)}"
        for month, gross, net in zip(range(1, MONTHS + 1), gross_cells, net_cells, strict=True)
    ]
    lines.append(f"  {'─' * (LABEL + gross_width + net_width + 4)}")
    gross_sum = _pad(f"{gross_total:,.2f}", gross_width)
    net_sum = _pad(f"{net_total:,.2f}", net_width)
    lines.append(f"  합계  {gross_sum}  {net_sum}")
    return "\n".join(lines)
