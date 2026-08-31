"""`Dockerfile` 이 **실제로 쓸 만한지** 검사한다.

**`presence ≠ adequacy`** — 파일이 있다는 것과 쓸 만하다는 것은 다르다.
`.env.example` 을 `test_env_example.py` 가 지키는 것과 같은 자리다:
그 시험은 *"코드가 읽는 환경 변수가 전부 문서화됐나"* 를 보고,
이 시험은 *"이 이미지가 실제로 이 패키지를 돌릴 수 있나"* 를 본다.

🔴 왜 필요했나 (2026-08-30 · `standards` R5-41 ⓐ): 바닥이 서비스 아키타입에 `Dockerfile` 을
요구하는데 템플릿이 안 냈다. 그냥 파일을 내면 **스텁**이 되고, 스텁은 이 저장소가 가장 싫어하는
것이다(야생 실측: CONTRIBUTING present 62% vs adequate 41%). 그래서 **파일과 함께 이 시험이 선다.**
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCKERFILE = ROOT / "Dockerfile"


def _text() -> str:
    return DOCKERFILE.read_text(encoding="utf-8")


def _package_name() -> str:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    name: str = data["project"]["name"]
    return name.replace("-", "_")


def test_every_base_image_is_pinned_by_digest() -> None:
    """🔴 태그는 가변이라 공급망 벡터다 — Actions 를 SHA 로 핀하는 것과 같은 이유다."""
    bases = re.findall(r"^FROM\s+(\S+)", _text(), re.M)
    assert bases, "FROM 이 하나도 없다"
    unpinned = [b for b in bases if "@sha256:" not in b]
    assert not unpinned, (
        f"다이제스트로 안 박힌 베이스: {unpinned}\n"
        "태그는 같은 이름이 다른 내용을 가리킬 수 있다. `이미지:태그@sha256:…` 로 박아라."
    )


def test_the_image_does_not_run_as_root() -> None:
    """탈출이 일어났을 때 피해 범위가 달라진다."""
    users = re.findall(r"^USER\s+(\S+)", _text(), re.M)
    assert users, "USER 가 없다 — 기본은 root 다"
    assert users[-1] != "root", f"마지막 USER 가 root 다: {users}"


def test_dependencies_come_from_the_lockfile() -> None:
    """락파일을 무시하면 **이미지가 저장소와 다른 것을 담는다.** 조용히 갈린다."""
    assert "uv sync --locked" in _text(), (
        "`uv sync --locked` 가 없다. --locked 없이는 락파일과 어긋나도 그냥 진행한다."
    )


def test_the_entrypoint_actually_exists_in_this_package() -> None:
    """🔴 **이 시험이 스텁을 막는 핵심이다.**

    `CMD ["python", "-m", "<패키지>"]` 가 **실제로 있는 모듈**을 가리켜야 한다.
    이름만 맞고 `__main__.py` 가 없으면 이미지는 빌드되고 **실행할 때 죽는다** —
    빌드만 보는 검사로는 안 잡힌다.
    """
    pkg = _package_name()
    cmd = re.search(r"^CMD\s+\[(.+)\]", _text(), re.M)
    assert cmd, "CMD 가 없다 — 이 이미지는 무엇을 돌리는지 말하지 않는다"
    parts = [p.strip().strip('"') for p in cmd.group(1).split(",")]
    assert parts[:2] == ["python", "-m"], f"진입점 형태가 다르다: {parts}"
    assert parts[2] == pkg, f"CMD 가 {parts[2]!r} 를 부르는데 패키지는 {pkg!r} 다"
    assert (ROOT / "src" / pkg / "__main__.py").is_file(), (
        f"src/{pkg}/__main__.py 가 없다. CMD 가 부르는데 모듈이 없으면 "
        "이미지는 빌드되고 실행할 때 죽는다."
    )


def test_the_build_context_excludes_what_must_not_ship() -> None:
    """`.dockerignore` 는 `.gitignore` 와 **목적이 다르다** — 저기는 커밋, 여기는 이미지다."""
    ignored = (ROOT / ".dockerignore").read_text(encoding="utf-8")
    for must in (".git", ".env", ".venv"):
        assert must in ignored, f".dockerignore 에 {must} 가 없다 — 이미지에 딸려 들어간다"
