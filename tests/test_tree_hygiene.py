"""트리에 **있으면 안 되는 것**이 실제로 없는가.

`.gitignore` 는 **예방**이지 보증이 아니다:

- `git add -f` 가 그것을 넘는다
- 규칙이 생기기 **전에** 추적된 파일은 규칙이 생겨도 **그대로 남는다**

🔬 두 번째가 실제로 났다 — `divcal` 이 CLI 인데 `.env.example` 을 v2.2.0 까지 들고 있었다.
통로는 달랐지만(`copier` 의 `_exclude`) 모양은 같다: **규칙은 맞는데 실물이 안 따라간다.**

바닥(`coolbress/standards` `direction/05`)이 요구하는 둘을 여기서 실물로 본다:

- §VCS 위생 — *"트리에 바이너리 산출물 없음"*
- §설정·시크릿 — *"`.env.example` 커밋 + 실제 `.env` 는 ignore"*

⚠️ **추적되는 파일만** 본다. 로컬에 굴러다니는 `dist/` 나 `.venv/` 는 대상이 아니다 —
그건 개발 중 정상이고, 문제는 **그것이 커밋됐을 때**다.
"""

from __future__ import annotations

import subprocess

import pytest

#: 이 접두사로 시작하는 경로는 빌드 산출물·환경이다.
FORBIDDEN_PREFIX = ("dist/", "build/", ".venv/", "site-packages/")

#: 이 꼬리를 가진 파일은 산출물이다.
FORBIDDEN_SUFFIX = (".pyc", ".pyo", ".pyd", ".so", ".whl", ".tar.gz", ".egg-info")

#: 경로 어디에 있어도 산출물인 것.
FORBIDDEN_PART = ("__pycache__/", ".mypy_cache/", ".pytest_cache/", ".ruff_cache/")


def tracked() -> list[str]:
    """추적되는 파일 목록. 🔴 파일시스템이 아니라 **git** 에게 묻는다."""
    # 억제는 **S607 하나만** 단다. 인자가 전부 리터럴이라 S603 은 애초에 안 걸리고,
    # 안 걸리는 것까지 적으면 `RUF100`(쓰이지 않은 noqa)이 반대로 터진다 — 실측으로 그랬다.
    # S607(부분 경로)의 '고침' 인 절대경로 박기는 더 나쁘다: `git` 은 CI 와 개발 기계에서
    # 자리가 다르다.
    done = subprocess.run(
        ["git", "ls-files"],  # noqa: S607 — 억제는 **경로가 적힌 줄**에 붙는다(호출 줄이 아니다)
        capture_output=True,
        text=True,
        check=False,
    )
    if done.returncode != 0:
        # 🔴 **좁게 건너뛴다.** 템플릿의 생성 시험은 렌더한 임시 디렉터리에서 pytest 를 돌리는데
        # 거기는 git 저장소가 아니다. **그 경우만** 건너뛰고 다른 실패는 터뜨린다 —
        # 아무 때나 조용히 초록이 되는 검사는 없느니만 못하다.
        if "not a git repository" in done.stderr.lower():
            pytest.skip("git 저장소가 아니다 — 추적 정보가 없다(렌더 직후 등)")
        raise AssertionError(f"`git ls-files` 가 실패했다: {done.stderr.strip()}")
    return [line for line in done.stdout.splitlines() if line]


def test_no_real_dotenv_is_tracked() -> None:
    """`.env.example` 은 커밋한다. **실제 값이 든 `.env` 는 절대 아니다.**"""
    leaked = [
        p
        for p in tracked()
        if (name := p.rsplit("/", 1)[-1]) == ".env"
        or (name.startswith(".env.") and name != ".env.example")
    ]
    assert not leaked, (
        f".env 파일이 커밋돼 있다: {leaked}\n"
        ".gitignore 가 막고 있어도 `git add -f` 나 규칙 이전의 커밋은 넘어온다. "
        "값이 들어 있었다면 히스토리에 남았으므로 **키를 새로 발급**해야 한다."
    )


def test_no_build_artifact_is_tracked() -> None:
    """바닥 §VCS 위생 — 트리에 바이너리 산출물이 없어야 한다."""
    junk = [
        p
        for p in tracked()
        if p.startswith(FORBIDDEN_PREFIX)
        or p.endswith(FORBIDDEN_SUFFIX)
        or any(part in p for part in FORBIDDEN_PART)
    ]
    assert not junk, (
        f"빌드 산출물이 커밋돼 있다: {junk}\n"
        "산출물은 빌드가 만든다 — 커밋되면 diff 를 부풀리고 리뷰를 묻는다."
    )
