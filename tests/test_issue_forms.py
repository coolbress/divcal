"""이슈 폼이 **있고, 깨져 있지 않은지** 검사한다.

`presence ≠ adequacy` 계열의 셋째다 ([`test_env_example.py`](test_env_example.py) ·
[`test_contributing.py`](test_contributing.py)).

**왜 이슈 폼인가**: Sülün et al.(ACM TOSEM 2024 · 100 프로젝트 · 템플릿 350 · 이슈 190만+)이
템플릿이 있으면 해결 시간이 **381.02일 → 103.18일** 로 줄고 YAML 폼은 재오픈·논의 길이까지
더 줄인다고 보고한다. **대부분의 바닥 항목은 채택률 근거인데 이건 결과 근거다.**

**왜 `bug` + `feature` 인가**: census 표준이 그 둘이다(top-2000 software). `task` 는
census 표준이 아니라 **`/kickoff` 를 위한 의도적 add-on** 이다 — 셋 다 둔다.

🔴 **YAML alias 함정을 회귀로 박는다.** `description: **강조**` 처럼 값이 `*` 로 시작하면
YAML 이 그것을 **alias 로 읽어** 폼 전체가 깨진다. 실제로 이 파일들을 만들 때 한 번 났다.
GitHub 은 푸시 뒤에야 알려주므로 여기서 잡는다.
"""

from __future__ import annotations

import re
from pathlib import Path

FORMS = Path(__file__).resolve().parent.parent / ".github" / "ISSUE_TEMPLATE"

#: census 표준 둘 + `/kickoff` 용 add-on 하나.
EXPECTED = ("bug.yml", "feature.yml", "task.yml")

#: 값이 `*` 나 `&` 로 시작하면 YAML 은 alias/anchor 로 읽는다. 따옴표가 필요하다.
ALIAS_TRAP = re.compile(r"^\s*[\w-]+:\s+[*&]")


def _form_files() -> list[Path]:
    return sorted(p for p in FORMS.glob("*.yml") if p.name != "config.yml")


def test_census_standard_forms_exist() -> None:
    have = {p.name for p in FORMS.glob("*.yml")}
    missing = [f for f in EXPECTED if f not in have]
    assert not missing, (
        f"이슈 폼이 없다: {missing}. census 표준은 bug + feature 이고 "
        "task 는 /kickoff 용 add-on 이다."
    )


def test_every_form_has_the_required_keys() -> None:
    for path in _form_files():
        text = path.read_text(encoding="utf-8")
        for key in ("name:", "description:", "body:"):
            assert re.search(rf"^{key}", text, re.MULTILINE), f"{path.name} 에 {key} 가 없다"


def test_no_unquoted_yaml_alias_trap() -> None:
    for path in _form_files():
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            assert not ALIAS_TRAP.match(line), (
                f"{path.name}:{lineno} 값이 `*`/`&` 로 시작한다 — YAML 이 alias 로 읽어 "
                f"폼이 통째로 깨진다. 따옴표로 감싸라.\n  {line.strip()}"
            )
