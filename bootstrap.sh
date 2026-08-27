#!/usr/bin/env bash
# 템플릿 자리표시자를 실제 값으로 바꾼다. 한 번만 돌린다.
#   사용법: ./bootstrap.sh <프로젝트-이름> [SPDX-라이선스]
#   예:     ./bootstrap.sh myapp Apache-2.0        (기본값 MIT)
#
# 왜 템플릿 안에 있나: 파일 배치를 아는 것은 템플릿 자신이다.
# new-project.sh 는 "저장소 생성 + 서버 바닥" 이 책임이라 여기까지 알 필요가 없다.
# (감사 §생성 방식 — "이름 치환과 선택지가 몇 개뿐이면 작은 bootstrap adapter 로 끝낸다")
set -euo pipefail

# --check-name: 이름만 확인하고 끝낸다 (부작용 없음). 시험이 이걸 쓴다.
check_only=0
if [ "${1:-}" = "--check-name" ]; then check_only=1; shift; fi

name="${1:?사용법: ./bootstrap.sh [--check-name] <프로젝트-이름> [SPDX-라이선스]}"
spdx="${2:-MIT}"

# 🔴 저장소 이름과 Python 패키지 이름은 **규칙이 다르다.**
# GitHub 은 `.` 을 허용하고 숫자로 시작해도 되지만 Python 은 아니다.
# 이전 판은 대문자와 `-` 만 바꿨다 — `my.app` 이 `src/my.app` 이 되어
# bootstrap 은 "완료" 라고 말하고 **pytest 가 나중에 실패**했다.
# 조용히 망가지는 것이 가장 나쁘다. 바꿀 수 있으면 바꾸고, 못 바꾸면 **여기서 멈춘다.**
# ⚠️ `tr` 로 하지 않는다 — BSD tr 은 `'.- '` 를 받아주지만 **GNU tr 은 `.`→` ` 범위로 읽어 거부**한다.
# 로컬(macOS)에서는 통과하고 CI(ubuntu)에서만 깨졌다. 규칙과 검사를 **한 곳**에 둔다.
pkg="$(python3 - "$name" <<'DERIVE'
import keyword, re, sys
name = sys.argv[1]
pkg = re.sub(r"[-. ]", "_", name).lower()
if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", pkg) or keyword.iskeyword(pkg):
    why = ("숫자로 시작한다" if pkg[:1].isdigit()
           else "파이썬 예약어다" if keyword.iskeyword(pkg)
           else "식별자에 쓸 수 없는 문자가 있다")
    sys.exit(
        f"🔴 저장소 이름 '{name}' 에서 Python 패키지 이름을 못 만든다: '{pkg}' 는 {why}.\n"
        f"   저장소 이름은 GitHub 규칙을 따르지만 패키지 이름은 Python 식별자여야 한다.\n"
        f"   저장소 이름을 바꾸거나, src/ 와 pyproject.toml 의 name 을 손으로 정한 뒤 다시 돌려라."
    )
print(pkg)
DERIVE
)"

if [ "$check_only" = 1 ]; then echo "$pkg"; exit 0; fi

[ -d src/app ] || { echo "이미 bootstrap 된 것 같다 (src/app 이 없다)" >&2; exit 1; }

git mv src/app "src/$pkg"
git mv tests/test_app.py "tests/test_$pkg.py"
python3 - "$pkg" "$name" "$spdx" <<'PY'
import pathlib, sys
pkg, name, spdx = sys.argv[1], sys.argv[2], sys.argv[3]
# (파일, 찾을 것, 바꿀 것, 몇 번)
edits = (
    ("pyproject.toml", 'name = "app"', f'name = "{pkg}"', 1),
    ("pyproject.toml", 'license = "MIT"', f'license = "{spdx}"', 1),
    # 배포 메타데이터의 URL 두 줄. 이름이 안 바뀌면 남의 저장소를 가리킨다.
    ("pyproject.toml", "coolbress/app", f"coolbress/{name}", 2),
    ("README.md", "# app", f"# {name}", 1),
    (f"tests/test_{pkg}.py", "from app import", f"from {pkg} import", 1),
)
for path, old, new, n in edits:
    p = pathlib.Path(path); t = p.read_text()
    found = t.count(old)
    assert found == n, f"{path}: '{old}' 가 {found}회 (기대 {n})"
    p.write_text(t.replace(old, new))
PY

# 🔴 uv.lock 은 프로젝트 이름을 담고 있다. 다시 잠그지 않으면
# CI 의 `uv sync --locked` 가 **새 저장소의 첫 PR 부터** 실패한다 —
# 벽이 서 있는 저장소라 그대로 잠긴다.
command -v uv >/dev/null || { echo "uv 가 필요하다: https://docs.astral.sh/uv/" >&2; exit 1; }
uv lock --quiet
uv sync --locked --quiet   # 잠금이 실제로 맞는지 여기서 확인한다. CI 에서 처음 알면 늦다.

git add -A

echo "완료 — 패키지 $pkg · 라이선스 $spdx · uv.lock 재생성"
echo "남은 것: pyproject.toml 의 description 이 아직 자리표시자다. 실제 설명으로 바꿔라."
echo "그리고 이 파일(bootstrap.sh)은 한 번만 쓰는 것이니 지워도 된다."
