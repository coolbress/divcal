"""저장소 이름 → Python 패키지 이름 변환을 검사한다.

왜 필요한가: **저장소 이름과 패키지 이름은 규칙이 다르다.**
GitHub 은 `.` 을 허용하고 숫자로 시작해도 되지만 Python 식별자는 아니다.
이전 판은 대문자와 `-` 만 바꿔서 `my.app` → `src/my.app` 을 만들었고,
`bootstrap.sh` 는 **"완료" 라고 말한 뒤 pytest 가 나중에 실패**했다.

**조용히 망가지는 것이 가장 나쁘다.** 못 만들면 그 자리에서 멈춰야 한다.

`bootstrap.sh` 는 한 번 쓰고 지우는 파일이라, **인스턴스에서는 이 시험이 건너뛰어진다.**
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
BOOTSTRAP = ROOT / "bootstrap.sh"

pytestmark = pytest.mark.skipif(
    not BOOTSTRAP.exists(), reason="bootstrap.sh 는 한 번 쓰고 지운다 (인스턴스에는 없다)"
)


def _derive(name: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [str(BOOTSTRAP), "--check-name", name],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )


@pytest.mark.parametrize(
    ("repo_name", "package"),
    [
        ("app", "app"),
        ("my-app", "my_app"),
        ("My.App", "my_app"),  # GitHub 은 `.` 을 허용한다. Python 은 아니다.
        ("Data-Loader", "data_loader"),
    ],
)
def test_valid_names_normalize(repo_name: str, package: str) -> None:
    r = _derive(repo_name)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == package


@pytest.mark.parametrize(
    ("repo_name", "why"),
    [
        ("9lives", "숫자로 시작한다"),
        ("class", "파이썬 예약어다"),
    ],
)
def test_impossible_names_stop_loudly(repo_name: str, why: str) -> None:
    """만들 수 없으면 **그 자리에서 멈춘다.** 나중에 pytest 가 실패하면 늦다."""
    r = _derive(repo_name)
    assert r.returncode != 0
    assert why in r.stderr
