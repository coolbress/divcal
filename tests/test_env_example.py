"""`.env.example` 이 실제로 쓸모 있는지 검사한다.

**`presence ≠ adequacy`** — 파일이 있다는 것과 쓸 만하다는 것은 다르다.
야생 실측에서 CONTRIBUTING 은 present 61.5% 인데 adequate 는 41.2% 다
(`census-gov-adequacy` · n=2,000 · 내용 파싱). 그 검사는 `test_contributing.py` 가 한다.
템플릿이 빈 파일을 모든 프로젝트에 복사하면 그 통계에 기여하는 쪽이 된다.

그래서 규칙을 문장이 아니라 **검사**로 둔다:
소스가 읽는 환경 변수는 전부 `.env.example` 에 키가 있어야 한다.
지금은 변수가 없어 조용히 통과하고, 첫 변수가 생기는 순간 일하기 시작한다.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# os.environ["X"] · os.environ.get("X") · os.getenv("X")
PATTERN = re.compile(
    r"""os\.(?:environ\s*\[\s*|environ\.get\s*\(\s*|getenv\s*\(\s*)['"]([A-Z_][A-Z0-9_]*)['"]"""
)


def _keys_used() -> set[str]:
    return {
        m
        for f in (ROOT / "src").rglob("*.py")
        for m in PATTERN.findall(f.read_text(encoding="utf-8"))
    }


def _keys_documented() -> set[str]:
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    # 주석 처리된 예시(`# KEY=`)도 문서화로 인정한다 — 값이 아니라 키를 알리는 파일이다.
    return set(re.findall(r"^\s*#?\s*([A-Z_][A-Z0-9_]*)\s*=", text, re.MULTILINE))


def test_env_example_documents_every_variable_the_code_reads() -> None:
    missing = _keys_used() - _keys_documented()
    assert not missing, (
        f".env.example 에 없는 환경 변수를 코드가 읽는다: {sorted(missing)}\n"
        "새로 참여하는 사람이 무엇을 채워야 하는지 알 길이 없다. 키를 추가해라."
    )
