"""세션 시작 훅이 **실제로 붙어 있고, 실패해도 세션을 안 막는가.**

🔴 이 훅이 왜 있나 — `coolbress/standards` divcal 완주 회고의 직접 처방이다.
차가운 세션이 `AGENTS.md` 가 명시한 저장소를 하나도 열지 않았고 `CONTRIBUTING.md` 를
두 번 가리켰는데 두 번 다 안 읽었다. **파일은 무시할 수 있고 훅의 stdout 은 못 무시한다.**

⚠️ 이 시험은 **훅이 붙어 있는지와 안전한지**만 본다. 내용이 좋은지는 사람이 읽는다.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SETTINGS = ROOT / ".claude" / "settings.json"
HOOK = ROOT / ".claude" / "session-start.sh"

#: 출력 상한. 넘으면 "비관련 내용이 지시 전체의 무시를 부른다" 쪽으로 넘어간다
#: (ETH Zurich · 138 repos · 5,694 PR · 150줄 초과에서 효용 체감).
MAX_LINES = 40


def test_settings_declare_a_session_start_hook() -> None:
    assert SETTINGS.is_file(), ".claude/settings.json 이 없다 — 훅이 안 붙는다"
    data = json.loads(SETTINGS.read_text(encoding="utf-8"))
    entries = data.get("hooks", {}).get("SessionStart")
    assert entries, "SessionStart 훅이 선언돼 있지 않다"
    commands = [h.get("command", "") for entry in entries for h in entry.get("hooks", [])]
    assert any("session-start.sh" in c for c in commands), (
        f"선언된 명령이 스크립트를 안 부른다: {commands}"
    )


def test_hook_script_exists_and_is_executable() -> None:
    assert HOOK.is_file(), ".claude/session-start.sh 가 없다"
    assert os.access(HOOK, os.X_OK), "실행 권한이 없다 — 훅이 조용히 실패한다"


def _run(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    # 억제 근거(S603·S607): 인자가 이 파일 안에서 만들어지고 사용자 입력이 없다.
    # 🔴 **줄이 갈린다** — S603 은 호출 줄에, S607 은 경로가 적힌 줄에 보고된다.
    return subprocess.run(  # noqa: S603
        ["bash", str(HOOK)],  # noqa: S607
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
        env=env,
    )


def test_hook_is_fail_open_without_gh() -> None:
    """🔴 **가장 중요한 시험.** 실패하는 훅은 세션을 막는다 — 보여주는 훅은 절대 그러면 안 된다.

    `gh` 가 없는 환경(설치 안 됨 · 로그인 안 됨 · 네트워크 없음)을 `PATH` 를 좁혀 흉내낸다.
    """
    env = {"PATH": "/usr/bin:/bin", "HOME": os.environ.get("HOME", "")}
    done = _run(env)
    assert done.returncode == 0, (
        f"gh 가 없을 때 훅이 실패했다 (종료코드 {done.returncode}) — 세션을 막는다\n{done.stderr}"
    )
    assert done.stdout.strip(), "출력이 비었다 — 훅이 아무것도 안 알려준다"


def test_hook_output_stays_short() -> None:
    """길어지면 값이 아니라 소음이다. 상한을 검사로 둔다."""
    done = _run(dict(os.environ))
    lines = done.stdout.splitlines()
    assert len(lines) <= MAX_LINES, (
        f"세션 시작 출력이 {len(lines)}줄이다 (상한 {MAX_LINES}). "
        "매 세션 지불하는 컨텍스트다 — 늘리려면 근거를 적어라."
    )
