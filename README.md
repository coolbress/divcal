# app

> 한 줄 설명을 여기에 쓴다.

## 시작하기

```bash
git clone <이 저장소>
cd <저장소>
uv sync            # 1. 의존성
uv run pytest      # 2. 테스트
```

**2명령.** 바닥은 clone→install→test 가 5명령 이내일 것을 요구한다.

## 개발

```bash
uv run ruff check . && uv run ruff format .   # 린트·포맷
uv run mypy .                                  # 타입
uv run pytest                                  # 테스트
uv build                                       # 빌드
```

CI 가 이것들을 **각각 별도 검사**로 돌리고 **시크릿 탐지·CodeQL 도 함께** 돈다.
로컬에서 먼저 통과시킨다. **검사 목록의 정본은 저장소 룰셋이다** — 여기 개수를 적지 않는다.

## 설정

[`.env.example`](.env.example) 을 `.env` 로 복사하고 값을 채운다.
**`.env` 는 커밋되지 않는다.**

## 기여

[`CONTRIBUTING.md`](CONTRIBUTING.md) — 특히 **테스트 정책**.
`main` 은 보호돼 있어 **PR + CI 초록**으로만 들어간다.

## 이 템플릿에 대해

[`coolbress/project-template`](https://github.com/coolbress/project-template) 에서 떴다.
CI 로직은 [`coolbress/workflows`](https://github.com/coolbress/workflows) 에 있다.
