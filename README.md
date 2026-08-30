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

## 원천징수 — 실제로 들어오는 돈

세전 표는 계획에 못 쓴다. `--tax` 에 **퍼센트 단위**로 세율을 주면 세후 칼럼이 붙는다.

```console
$ uv run divcal examples/schedule.csv 2026 --tax 15
2026 배당 현금흐름 (원천징수 15%, USD)

          세전    세후
   1월    7.92    6.73
   ...
   4월   48.50   41.22
  ────────────────────
  합계  270.68  230.07
```

**세금은 지급 건별로 뗀다.** 4월이 `41.22` 지 `41.23` 이 아닌 이유다 —
`48.50` 에서 세액 `7.28` 을 떼면 `41.22` 이고, 세전에 `0.85` 를 곱해 반올림하면 `41.23` 이다.
뒤엣것은 `48.50 != 41.23 + 7.28` 이라 **세전 = 세후 + 세액**이 깨진다. 명세서가 건별이니 앞엣것이다.

| | |
|---|---|
| `--tax 15` | 15% 를 뗀다 |
| `--tax 0` | 0% 로 두 칼럼을 찍는다 (플래그를 안 준 것과 다르다) |
| `--tax` 없음 | 세전 한 칼럼 — 위의 기본 출력 그대로다 |
| `--tax 0.15` | **거부한다.** 15% 로 착각한 값이 통과하면 세금이 100배 작게 조용히 계산된다 |

세율은 사용자가 준다 — 조세조약을 조회하지 않는다(네트워크 없음).
종목마다 세율이 다르면(ADR·리츠) 아직 못 쓴다: [#4](https://github.com/coolbress/divcal/issues/4) 의 *안 만들 것*.

## 아직 안 하는 것

API 자동 조회 · 환율/원화 · 종목별 세율 · `.ics`/웹 화면 · 배당 성장률·DRIP ·
증권사 CSV 파싱. [#1](https://github.com/coolbress/divcal/issues/1) 과
[#4](https://github.com/coolbress/divcal/issues/4) 의 *안 만들 것* 에 있다.

## 시작하기

```bash
git clone https://github.com/coolbress/divcal.git
cd divcal
uv sync --locked                          # 1. 의존성 (CI 와 같은 명령)
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

## 기여

[`CONTRIBUTING.md`](CONTRIBUTING.md) — 특히 **테스트 정책**.
`main` 은 보호돼 있어 **PR + CI 초록**으로만 들어간다.

## 이 템플릿에 대해

[`coolbress/project-template`](https://github.com/coolbress/project-template) 에서 떴다.
CI 로직은 [`coolbress/workflows`](https://github.com/coolbress/workflows) 에 있다.
