# 이 저장소에서 일하는 법

> 🔬 **이 저장소는 하네스 완주 시험용이다. 그리고 그 시험은 끝났다 (2026-08-28).**
> [`coolbress/standards`](https://github.com/coolbress/standards) 의 *"에이전트로 좋은 프로젝트를 만든다"* 를
> `new-project.sh → /kickoff → 이슈 → PR → CI → 머지` 로 end-to-end 확인하려고 만들었다.
>
> 🔴 **백로그([#15](https://github.com/coolbress/divcal/issues/15))는 순서만 잡아뒀고 착수 계획이 없다.**
> 소유자가 이 도구를 쓰지 않는다. **새 기능을 만들기 전에 물어라** — 안 물으면 아무도 안 쓸 제품에
> 시간을 갈아넣게 된다.

`main` 은 보호돼 있다. **브랜치 → PR → CI 초록 → 머지**로만 들어간다.
직접 푸시도 빨간불 머지도 `--admin` 강제도 거부된다 — 소유자도 못 넘는다.

```bash
uv sync --locked          # 락파일과 어긋나면 실패한다
uv run ruff check . && uv run ruff format --check .
uv run mypy .
uv run pytest
```

CI 는 이것들을 **각각 별도 검사**로 돌린다. 로컬에서 통과시키고 PR 을 연다.

## 다음에 뭘 할지

**`gh issue list` 가 정본이다.** 순서와 그 이유는 [#15 백로그 순서 (추적)](https://github.com/coolbress/divcal/issues/15) 에 있다.

백로그 이슈의 **인수기준은 비어 있다.** 착수할 때 `/kickoff` 인터뷰로 채운다 —
미리 박아두면 인터뷰가 할 일이 없어진다.

## 읽고 시작해라

- **설정의 정본은 [`pyproject.toml`](pyproject.toml)** — 줄길이 100 · ruff 규칙 · `mypy --strict` ·
  `filterwarnings = ["error"]`. **안 읽으면 lint 가 깨져서 알게 된다**
- **[`CONTRIBUTING.md`](CONTRIBUTING.md) 를 PR 열기 전에 읽어라** — 57줄이다. 테스트 정책 ·
  PR 크기의 근거 · `AC-n` 규칙이 거기 있다. 🔴 **두 번 가리켰는데 두 번 다 안 읽힌 파일이다**

## 규율

- **인수기준은 이슈에 `AC-n` 으로 산다.** PR 은 어느 AC 를 닫는지 밝힌다
- 증명할 검사를 못 정하겠으면 **`UNVERIFIABLE` 이라고 쓴다.** 조용히 넘기지 않는다
- **동작이나 버그가 바뀌면 그 변화를 잡는 테스트를 같은 PR 에 넣는다. 해당하지 않으면 이유를 적는다**
- **PR diff 는 200줄을 목표로, 400줄이 상한이다** — `ci / diff-size` 가 상한을 막는다
  (문서·락파일은 안 센다). 근거와 그 한정은 `CONTRIBUTING.md` 에 있다
- CI 로직은 여기 없다 — `coolbress/workflows` 에 있고 `ci.yml` 이 SHA 로 핀한다
