"""#1 의 AC-5 · AC-6 — 입력이 틀렸을 때 무엇을 말하고 어떻게 끝나는가."""

from __future__ import annotations

from pathlib import Path

import pytest

from divcal.cli import main

ROOT = Path(__file__).resolve().parent.parent
GOOD = "ticker,shares,amount_per_share,pay_date\nKO,100,0.485,2026-04-01\n"


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "schedule.csv"
    path.write_text(text, encoding="utf-8")
    return path


def test_prints_table(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([str(_write(tmp_path, GOOD)), "2026"]) == 0

    out = capsys.readouterr().out
    assert "2026 배당 현금흐름" in out
    assert "48.50" in out


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        pytest.param("A,100,0.485,2026/04/01\n", "2번째 줄: pay_date", id="날짜형식"),
        pytest.param("A,100,0.485,2026-02-30\n", "2번째 줄: 없는 날짜", id="없는날짜"),
        pytest.param("A,-100,0.485,2026-04-01\n", "2번째 줄: shares 이(가) 음수", id="음수수량"),
        pytest.param("A,100,없음,2026-04-01\n", "2번째 줄: amount_per_share", id="숫자아님"),
        pytest.param("A,,0.485,2026-04-01\n", "2번째 줄: shares 이(가) 비었다", id="빈칸"),
        pytest.param("A,100,0.485,2026-04-01\nB,1,1,x\n", "3번째 줄", id="줄번호는_행마다"),
    ],
)
def test_bad_row_reports_line_and_exits_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], body: str, expected: str
) -> None:
    """AC-5 — **몇 번째 줄의 무엇이** 틀렸는지 말하고 2 로 끝난다."""
    path = _write(tmp_path, "ticker,shares,amount_per_share,pay_date\n" + body)

    assert main([str(path), "2026"]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""  # 표를 반쯤 찍고 죽지 않는다
    assert expected in captured.err


def test_missing_column_is_reported(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """AC-5 — 머리글이 틀리면 무엇이 없는지 말한다."""
    path = _write(tmp_path, "ticker,shares,pay_date\nKO,100,2026-04-01\n")

    assert main([str(path), "2026"]) == 2
    assert "amount_per_share" in capsys.readouterr().err


def test_missing_file_exits_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """AC-6 — 없는 파일에 트레이스백을 토하지 않는다."""
    missing = tmp_path / "없다.csv"

    assert main([str(missing), "2026"]) == 2

    err = capsys.readouterr().err
    assert str(missing) in err
    assert "Traceback" not in err


def test_example_schedule_is_runnable(capsys: pytest.CaptureFixture[str]) -> None:
    """README 가 가리키는 예제 파일이 실제로 도는지 본다 — `presence ≠ adequacy`."""
    assert main([str(ROOT / "examples" / "schedule.csv"), "2026"]) == 0
    assert "합계" in capsys.readouterr().out
