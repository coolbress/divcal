"""문서의 상대 링크가 **실제로 있는 파일**을 가리키는지 검사한다.

🔴 왜 이 검사가 생겼나 (2026-08-30 실측): 템플릿이 아키타입에 따라 `.env.example` 을
**안 만드는데** README 의 `## 설정` 절은 그것을 **무조건** 가리키고 있었다.
`cli`·`library` 로 뜬 프로젝트는 **없는 파일을 가리키는 README** 를 받았다.
파일을 빼는 조건은 있었는데 **그 파일을 가리키는 문장**을 빼는 조건이 없었다.

`presence ≠ adequacy` 의 거울상이다 — **absence ≠ silence.**
없앤 것을 아무도 안 가리키는지까지 봐야 없앤 것이 된다.

⚠️ 저장소 밖으로 나가는 경로는 **건너뛴다.** `SECURITY.md` 의
`../../security/advisories/new` 처럼 GitHub 이 해석하는 저장소 상대 URL 이 있다 —
파일이 아니므로 파일로 재면 오탐이 된다.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# [텍스트](대상) — 이미지도 같은 문법이라 같이 걸린다
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
SKIP_SCHEME = ("http://", "https://", "mailto:", "#")


def _markdown_files() -> list[Path]:
    return sorted(p for p in ROOT.rglob("*.md") if ".venv" not in p.parts)


def _broken(doc: Path) -> list[str]:
    out = []
    for target in LINK.findall(doc.read_text(encoding="utf-8")):
        if target.startswith(SKIP_SCHEME):
            continue
        path = (doc.parent / target.split("#", 1)[0]).resolve()
        if ROOT not in path.parents and path != ROOT:
            continue  # 저장소 밖 — GitHub 이 해석하는 URL 이다
        if not path.exists():
            out.append(target)
    return out


def test_every_relative_link_points_at_a_file_that_exists() -> None:
    broken: dict[str, list[str]] = {}
    for doc in _markdown_files():
        if bad := _broken(doc):
            broken[doc.relative_to(ROOT).as_posix()] = bad
    assert not broken, (
        f"없는 파일을 가리키는 링크가 있다: {broken}\n"
        "읽는 사람이 클릭하면 404 다. 링크를 고치거나, 그 문장을 조건부로 만들어라."
    )


def test_the_check_actually_looks_at_something() -> None:
    """🔵 문서를 하나도 못 찾으면 위 시험은 조용히 통과한다 — 검사가 헛도는 형태다."""
    assert _markdown_files(), "마크다운 문서를 하나도 못 찾았다"
