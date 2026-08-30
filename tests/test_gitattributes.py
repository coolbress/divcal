"""`.gitattributes` 가 **실제로 무엇을 하는지** 검사한다.

`presence ≠ adequacy` — 파일이 있다는 것과 락파일이 접힌다는 것은 다르다.
빈 `.gitattributes` 를 모든 프로젝트에 복사하면 그 통계에 기여하는 쪽이 된다.

🔴 왜 이게 들어왔나 (2026-08-30 · `standards` `GAPS` R5-42): 이 항목은 한 번 **기각**됐다.
근거는 *"쓰임은 둘이다 — 개행 정규화와 LFS"* 였는데 **열거가 빠져 있었다.**
git 자신이 정의하는 속성만 열두 개가 넘고, 그중 **GitHub 의 `linguist-generated`** 는
파일을 diff 에서 접는다. 락파일을 커밋하는 프로젝트에는 그게 바로 값을 한다.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ATTRS = ROOT / ".gitattributes"


def _rules() -> list[tuple[str, list[str]]]:
    out = []
    for line in ATTRS.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            pattern, *attrs = line.split()
            out.append((pattern, attrs))
    return out


def test_the_lockfile_is_marked_generated() -> None:
    """접히지 않으면 락파일 수백 줄이 리뷰의 눈을 가린다."""
    marked = [p for p, a in _rules() if p == "uv.lock" and "linguist-generated" in a]
    assert marked, (
        "uv.lock 에 linguist-generated 가 없다. "
        "GitHub 이 diff 에서 접지 않아 리뷰가 기계가 쓴 줄을 읽게 된다."
    )


def test_line_endings_are_normalized() -> None:
    """`.editorconfig` 는 편집기에게 부탁하고, 이 줄은 git 이 집행한다."""
    rules = dict(_rules())
    assert "text=auto" in rules.get("*", []), "개행 정규화가 없다 — 편집기 설정에만 기대게 된다"


def test_every_rule_is_self_contained() -> None:
    """🔴 **저장소가 집행할 수 없는 규칙을 적지 않는다.**

    `diff=<이름>`·`merge=<이름>`·`filter=<이름>` 은 그 드라이버를 **각 사용자의 로컬
    git config 에 정의해야** 돈다(git 1차 문서). 커밋된 파일만으로는 안 돈다 —
    적어두면 *돌고 있다고 착각하게* 만든다. 원칙 01(집행은 에이전트 밖에서)과 같은 형태다.
    """
    needs_local_config = []
    for pattern, attrs in _rules():
        for a in attrs:
            key, _, value = a.partition("=")
            if key in {"diff", "merge", "filter"} and value not in {"", "true", "false"}:
                needs_local_config.append(f"{pattern}: {a}")
    assert not needs_local_config, (
        f"로컬 git config 가 있어야 도는 규칙이다: {needs_local_config}\n"
        "커밋된 파일만으로 도는 것만 적는다."
    )
