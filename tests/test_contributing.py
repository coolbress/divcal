"""`CONTRIBUTING.md` 가 **쓸모 있는지** 검사한다.

**`presence ≠ adequacy`** — [`test_env_example.py`](test_env_example.py) 와 같은 이유다.
그 파일이 근거로 인용한 통계가 정확히 이 파일에 관한 것인데, 정작 검사는 안 만들어져 있었다.

야생 실측(`census-gov-adequacy` · n=2,000 · 내용 파싱): CONTRIBUTING 은 **present 61.5%** 인데
**adequate 는 41.2%** — **있는 것 중 1/3(67%)이 빌드·테스트 설명 없는 스텁**이다.
`adequate = has_devflow AND has_prflow` 가 그 실측이 쓴 정의고, 여기서도 같은 둘을 본다.

**템플릿이 파일을 넣어주는 것은 presence 만 해결한다.** 스텁을 모든 인스턴스에 복사하면
이 프로젝트가 그 1/3 통계에 기여하는 쪽이 된다. 그래서 문장이 아니라 검사로 둔다.

⚠️ 이 검사는 **표지가 있는지**를 볼 뿐 글이 좋은지는 못 본다. 그건 사람이 읽는다.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTRIBUTING = ROOT / "CONTRIBUTING.md"

#: 빌드·테스트를 **어떻게 돌리는지** 알려주는가. 명령이 있어야 인정한다.
DEVFLOW = re.compile(r"uv run pytest|uv sync|pytest|npm test|make test", re.IGNORECASE)

#: 변경을 **어떻게 넣는지** 알려주는가.
PRFLOW = re.compile(r"pull request|PR 을 연다|브랜치 *→ *PR|fork|머지", re.IGNORECASE)


def _text() -> str:
    assert CONTRIBUTING.is_file(), "CONTRIBUTING.md 가 없다"
    return CONTRIBUTING.read_text(encoding="utf-8")


def test_contributing_explains_how_to_build_and_test() -> None:
    assert DEVFLOW.search(_text()), (
        "CONTRIBUTING.md 에 빌드·테스트를 어떻게 돌리는지가 없다.\n"
        "야생에서 present 한 CONTRIBUTING 의 1/3 이 정확히 이게 빠진 스텁이다 — "
        "파일만 있고 새로 온 사람이 무엇을 실행해야 하는지 모른다."
    )


def test_contributing_explains_how_to_land_a_change() -> None:
    assert PRFLOW.search(_text()), (
        "CONTRIBUTING.md 에 변경을 어떻게 넣는지(PR 흐름)가 없다.\n"
        "`main` 이 보호돼 있어 PR 말고는 경로가 없는데 그걸 안 적으면 막힌다."
    )


def test_contributing_is_not_a_stub() -> None:
    # 링크 한 줄짜리 CONTRIBUTING 이 야생의 흔한 스텁 형태다.
    body = [ln for ln in _text().splitlines() if ln.strip()]
    assert len(body) >= 10, (
        f"CONTRIBUTING.md 가 {len(body)}줄뿐이다 — 스텁으로 보인다. "
        "빌드·테스트 방법과 PR 흐름을 적어라."
    )
