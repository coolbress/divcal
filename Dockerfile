# divcal — 서비스 아키타입의 컨테이너 이미지.
#
# 🔴 **베이스는 태그가 아니라 다이제스트로 핀한다.** 태그는 가변이라 공급망 벡터다 —
# Actions 를 커밋 SHA 로 핀하는 것과 **같은 이유**다(바닥 §빌드·의존성).
# Dependabot 의 `docker` 생태계가 이 다이제스트를 갱신한다.

# ── 빌드 단계 ──────────────────────────────────────────────────
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim@sha256:e5b65587bce7de595f299855d7385fe7fca39b8a74baa261ba1b7147afa78e58 AS build

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# 🔴 의존성을 소스보다 **먼저** 넣는다. 소스만 바뀌면 이 층이 캐시에서 나온다.
COPY pyproject.toml uv.lock ./
# --locked: 락파일과 어긋나면 **실패한다**. 컨테이너가 조용히 다른 버전을 담지 않는다.
# --no-dev: 시험·린터는 이미지에 안 들어간다.
RUN uv sync --locked --no-install-project --no-dev

COPY src/ ./src/
COPY README.md ./
RUN uv sync --locked --no-dev

# ── 실행 단계 ──────────────────────────────────────────────────
FROM python:3.14-slim@sha256:cae66f2ef0ec51a9891263eeee7f987dacf0a9879e8aa9353d5606e0530619a5

# 🔴 **root 로 돌지 않는다.** 컨테이너 탈출의 피해 범위가 달라진다.
RUN useradd --create-home --uid 10001 app
WORKDIR /app

COPY --from=build --chown=app:app /app/.venv /app/.venv
COPY --from=build --chown=app:app /app/src /app/src
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1

USER app

# 🔴 **진입점은 이 패키지의 `__main__.py` 다.** 프레임워크를 고르지 않는다 —
# 무엇으로 서비스를 띄울지는 이 프로젝트가 정한다. 여기서 고르면 그게 스텁이 된다.
CMD ["python", "-m", "divcal", "serve"]
