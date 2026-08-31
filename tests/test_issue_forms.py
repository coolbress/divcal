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


def test_every_form_labels_its_issues() -> None:
    """🔴 라벨이 없으면 그 이슈는 **목록에서 안 갈린다.**

    실측(2026-08-30): `task.yml` 만 `labels:` 가 비어 있었다. `bug`·`enhancement` 는
    GitHub **기본 라벨**이라 그냥 되는데 `task` 는 아니라서 그렇게 됐다.
    `/kickoff` 이 만드는 과제가 버그 신고와 안 갈리면 `gh issue list` 로
    *다음 할 일* 을 못 추린다 — **그게 이 저장소의 정본인데도.**

    ⚠️ 라벨 이름이 실제로 저장소에 있어야 한다. `new-project.sh` 가 `task` 를 만든다.
    """
    # ⚠️ `yaml` 은 인스턴스의 의존성이 아니다 — 이 파일이 정규식을 쓰는 이유다.
    missing = [
        f.name
        for f in _form_files()
        if not re.search(r"^labels:\s*\[.+\]", f.read_text(encoding="utf-8"), re.M)
    ]
    assert not missing, f"라벨이 없는 폼: {missing} — 그 이슈는 목록에서 안 갈린다"
