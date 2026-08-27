# divcal

> **배당 지급 예정표 한 장을 월별 현금흐름 표로 접는다.** 세전 · USD · 네트워크 없음.

증권사 앱은 화면이 *종목별*이라 *"다음 달에 배당으로 얼마 들어오나"* 가 한눈에 안 보인다.
`divcal` 은 축을 바꾼다 — 종목 축이 아니라 **월 축**이다.

```console
$ uv run divcal examples/schedule.csv 2026
2026 배당 현금흐름 (세전, USD)

   1월    7.92
   2월    7.92
   3월   21.15
   4월   48.50
   5월    0.00
   6월   13.23
   7월   48.50
   8월    0.00
   9월   13.23
  10월   48.50
  11월    0.00
  12월   61.73
  ────────────
  합계  270.68
```

## 예정표 형식

칼럼 넷. **한 행이 한 번의 지급**이고, 그 시점 보유수량이 그 행에 있다.

```csv
ticker,shares,amount_per_share,pay_date
KO,100,0.485,2026-04-01
SCHD,50,0.2645,2026-03-25
```

| 칼럼 | 무엇 |
|---|---|
| `ticker` | 종목 기호 |
| `shares` | 그 지급 시점의 보유 수량 (음수 불가) |
| `amount_per_share` | 주당 배당금 USD (음수 불가) |
| `pay_date` | **지급일** `YYYY-MM-DD` — 배당락일이 아니다 |

금액은 `shares × amount_per_share` 를 **`Decimal`** 로 계산해 지급 건별로 센트 단위 반올림한다.
`float` 로 하면 `0.485 × 3` 이 `1.4549999…` 가 되어 한 센트가 샌다.

🔴 **실제 보유내역을 이 저장소에 커밋하지 마라.** 공개 저장소다 —
`.gitignore` 가 `examples/` 밖의 모든 `*.csv` 를 막는다.

## 아직 안 하는 것

API 자동 조회 · 환율/원화 · 세금(원천징수 15%) · `.ics`/웹 화면 · 배당 성장률·DRIP ·
증권사 CSV 파싱. 전부 [#1](https://github.com/coolbress/divcal/issues/1) 의 *안 만들 것* 에 있다.

## 시작하기

```bash
git clone https://github.com/coolbress/divcal.git
cd divcal
uv sync                                   # 1. 의존성
uv run divcal examples/schedule.csv 2026  # 2. 돌려보기
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
