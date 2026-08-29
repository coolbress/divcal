#!/usr/bin/env bash
# 세션이 열릴 때 **이 저장소가 지금 어디까지 왔는지**를 컨텍스트에 밀어 넣는다.
#
# 🔴 왜 파일이 아니라 훅인가 — **파일은 무시할 수 있다.**
#   실측(`coolbress/standards` divcal 완주 회고): 차가운 세션이 `AGENTS.md` 가 **명시한**
#   저장소를 하나도 열지 않았고, `CONTRIBUTING.md` 를 **두 번 가리켰는데 두 번 다 안 읽었다.**
#   회고가 원인을 *"훅 없음 · 링크 없음"* 으로 지목했다.
#   훅의 stdout 은 **추론이 시작되기 전에** 컨텍스트로 들어간다.
#
# 🔴 **fail-open 이다.** 무엇이 실패해도 세션은 그대로 진행된다 —
#   보여주는 훅이 일을 막으면 그건 벽 흉내이고, **벽은 GitHub 에 있다.**
# 🔴 **상태를 소유하지 않는다.** 열린 이슈의 정본은 `gh issue list` 이고 여기서는 읽기만 한다.
# 🔴 **짧게 유지한다.** 비관련 내용은 선택적 무시가 아니라 **지시 전체의 무시**를 부른다
#   (ETH Zurich · 138 repos · 5,694 PR).
set -u

echo "## 이 저장소의 현재 상태 (SessionStart)"
echo
echo "검사는 이 넷이다 — 로컬에서 먼저 통과시킨다:"
echo '  uv run ruff check . && uv run ruff format --check .'
echo '  uv run mypy .'
echo '  uv run pytest'
echo '  uv build'
echo
echo "\`main\` 은 보호돼 있다. **브랜치 → PR → CI 초록 → 머지**로만 들어간다."
echo "규약은 \`CONTRIBUTING.md\` 에 있다 — 특히 **PR 크기 상한**과 **테스트 정책**."

# 열린 이슈 — 있으면 보여주고, 없거나 못 읽으면 조용히 넘어간다.
if command -v gh >/dev/null 2>&1; then
  issues=$(gh issue list --limit 5 --state open \
             --json number,title --template \
             '{{range .}}  #{{.number}} {{.title}}{{"\n"}}{{end}}' 2>/dev/null) || issues=""
  if [ -n "$issues" ]; then
    echo
    echo "열린 이슈 (최대 5건 · 정본은 \`gh issue list\`):"
    printf '%s' "$issues"
  fi
fi

exit 0
