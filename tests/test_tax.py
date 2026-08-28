"""#4 의 AC-1 ~ AC-7 — 원천징수를 떼는 부분."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from divcal import load_payments, monthly_after_tax, monthly_totals, parse_tax_rate
from divcal.cli import main

RATE = Decimal(15)

SCHEDULE = """\
ticker,shares,amount_per_share,pay_date
KO,100,0.485,2026-04-01
SCHD,50,0.2645,2026-03-25
"""

# 같은 달에 48.50 이 두 번. 건별로 떼면 세액이 7.28+7.28=14.56 이지만,
# 월 합계 97.00 에 세율을 곱하면 14.55 다 — AC-3 은 이 한 센트를 가른다.
TWICE = """\
ticker,shares,amount_per_share,pay_date
KO,100,0.485,2026-04-01
KO,100,0.485,2026-04-15
"""


#: `--tax` 없이 `SCHEDULE` 을 돌렸을 때 나와야 하는 것. #1 이 만든 출력 그대로다.
PRETAX = """\
2026 배당 현금흐름 (세전, USD)

   1월   0.00
   2월   0.00
   3월  13.23
   4월  48.50
   5월   0.00
   6월   0.00
   7월   0.00
   8월   0.00
   9월   0.00
  10월   0.00
  11월   0.00
  12월   0.00
  ───────────
  합계  61.73
"""


def _write(tmp_path: Path, text: str = SCHEDULE) -> Path:
    path = tmp_path / "schedule.csv"
    path.write_text(text, encoding="utf-8")
    return path


def test_after_tax_column(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """AC-1 — `--tax 15` 면 세전·세후 두 칼럼이 나오고 머리글이 세율을 밝힌다."""
    assert main([str(_write(tmp_path)), "2026", "--tax", "15"]) == 0

    out = capsys.readouterr().out
    assert "2026 배당 현금흐름 (원천징수 15%, USD)" in out
    assert "세전" in out
    assert "세후" in out
    assert "48.50" in out  # 4월 세전
    assert "41.22" in out  # 4월 세후 — 48.50 - 7.28


def test_no_flag_keeps_pretax_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """AC-2 — `--tax` 가 없으면 #1 의 출력이 한 글자도 안 바뀐다."""
    path = _write(tmp_path)

    assert main([str(path), "2026"]) == 0
    out = capsys.readouterr().out

    assert "세후" not in out
    assert "원천징수" not in out
    # 한 칼럼 표를 통째로 못박는다. `--tax` 없는 경로는 #1 이 고정한 계약이다.
    assert out == PRETAX


def test_tax_withheld_per_payment(tmp_path: Path) -> None:
    """AC-3 — 세금은 **지급 건별로** 뗀다. 월 합계에 세율을 곱한 것과 한 센트 다르다."""
    rows = monthly_after_tax(load_payments(_write(tmp_path, TWICE)), 2026, RATE)
    april = rows[3]

    assert april.gross == Decimal("97.00")
    assert april.tax == Decimal("14.56")  # 7.28 + 7.28 — 건별
    assert april.net == Decimal("82.44")

    # 월 합계에 곱했다면 이 숫자가 나왔을 것이다. 그러면 명세서와 어긋난다.
    assert (april.gross * RATE / 100).quantize(Decimal("0.01")) == Decimal("14.55")


def test_gross_equals_net_plus_tax(tmp_path: Path) -> None:
    """AC-4 — 모든 달에서 `세전 = 세후 + 세액` 이 센트까지 맞는다. 반올림이 새지 않는다."""
    payments = load_payments(_write(tmp_path))

    for rate in (Decimal(0), Decimal(15), Decimal("15.4"), Decimal(33), Decimal(100)):
        rows = monthly_after_tax(payments, 2026, rate)
        for month, row in enumerate(rows, start=1):
            assert row.gross == row.tax + row.net, f"{rate}% {month}월"
        # 연간 합계도 맞고, 세전 축은 #1 의 `monthly_totals` 와 동일하다.
        assert [row.gross for row in rows] == monthly_totals(payments, 2026)
        assert sum((r.gross for r in rows), Decimal("0.00")) == sum(
            (r.tax for r in rows), Decimal("0.00")
        ) + sum((r.net for r in rows), Decimal("0.00"))


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        pytest.param("-5", "음수", id="음수"),
        pytest.param("150", "100% 를 넘는다", id="100초과"),
        pytest.param("십오", "숫자가 아니다", id="숫자아님"),
        pytest.param("NaN", "숫자가 아니다", id="NaN"),
        pytest.param("Infinity", "숫자가 아니다", id="무한대"),
    ],
)
def test_bad_rate_exits_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], raw: str, expected: str
) -> None:
    """AC-5 — 세율이 틀렸으면 무엇이 틀렸는지 말하고 종료코드 2 로 끝난다."""
    assert main([str(_write(tmp_path)), "2026", f"--tax={raw}"]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""  # 표를 반쯤 찍고 죽지 않는다
    assert expected in captured.err
    assert "Traceback" not in captured.err


def test_bad_rate_is_caught_before_reading_the_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC-5 — 파일이 없어도 세율 오류가 먼저다. 플래그가 틀렸으면 읽어볼 것도 없다."""
    assert main([str(tmp_path / "없다.csv"), "2026", "--tax=-1"]) == 2
    assert "음수" in capsys.readouterr().err


@pytest.mark.parametrize("raw", ["0.15", "0.5", "0.99"])
def test_sub_one_percent_rate_is_rejected(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], raw: str
) -> None:
    """AC-6 — `--tax 0.15` 는 거부한다.

    15% 로 착각한 값이 통과하면 세금이 **100배 작게 조용히** 계산된다.
    틀린 숫자를 맞는 것처럼 보여주는 것이 최악이라 여기서 막는다.
    """
    assert main([str(_write(tmp_path)), "2026", f"--tax={raw}"]) == 2

    err = capsys.readouterr().err
    assert "퍼센트 단위" in err
    assert "--tax 15" in err


def test_zero_rate_is_not_absent_flag(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """AC-7 — `--tax 0` 은 유효하다. 0% 는 명시적 선택이고 '플래그 없음' 과 다르다."""
    assert main([str(_write(tmp_path)), "2026", "--tax", "0"]) == 0

    out = capsys.readouterr().out
    assert "원천징수 0%" in out
    assert "세후" in out  # 두 칼럼이 나온다 — 세전만 찍는 것과 구분된다

    rows = monthly_after_tax(load_payments(_write(tmp_path)), 2026, Decimal(0))
    assert all(row.tax == Decimal("0.00") and row.gross == row.net for row in rows)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("15", "15"), ("15.40", "15.4"), ("100", "100"), ("0", "0"), ("15.4", "15.4")],
)
def test_rate_is_shown_as_written(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], raw: str, expected: str
) -> None:
    """AC-1 — 머리글의 세율이 사람이 쓴 대로 나온다. `100` 이 `1` 로 깎이지 않는다."""
    assert main([str(_write(tmp_path)), "2026", f"--tax={raw}"]) == 0
    assert f"원천징수 {expected}%," in capsys.readouterr().out


def test_parse_tax_rate_accepts_the_boundaries() -> None:
    """경계값은 통과한다 — 0 과 100 과 1 은 유효한 세율이다."""
    assert parse_tax_rate("0") == Decimal(0)
    assert parse_tax_rate("1") == Decimal(1)
    assert parse_tax_rate("100") == Decimal(100)
