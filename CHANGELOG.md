# 변경 이력

형식은 [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/) 를 따르고,
버전은 [유의적 버전](https://semver.org/lang/ko/) 을 따른다.

> ℹ️ **이 파일은 릴리스를 하는 프로젝트를 위한 것이다.**
> *Keep a Changelog* 는 **릴리스 단위로 항목을 쌓는 형식**이라, 태그·릴리스를 만들지 않을 프로젝트에서는
> 채울 단위가 없다 — 그런 경우 **이 파일을 지워라.** 빈 채로 두면 있는 것처럼 보이지만 아무 정보도 없다
> (야생 실측: CONTRIBUTING 이 present 62% 인데 adequate 는 41% — **있는 것 중 1/3 이 스텁**이다).
>
> 릴리스를 시작하면 아래에 버전 절을 쌓고, 각 버전에 비교 링크를 단다:
> `[1.0.0]: https://github.com/<owner>/<repo>/compare/v0.9.0...v1.0.0`

## [Unreleased]

### Added
- 지급 예정 CSV 를 읽어 **월별 세전 배당 현금흐름 표**를 터미널에 찍는 `divcal` 명령 ([#1](https://github.com/coolbress/divcal/issues/1))
- 예제 예정표 [`examples/schedule.csv`](examples/schedule.csv)
- `--tax <퍼센트>` — **원천징수를 떼고 세전·세후 두 칼럼**으로 찍는다. 세금은 지급 건별로 떼어 `세전 = 세후 + 세액` 이 센트까지 맞는다 ([#4](https://github.com/coolbress/divcal/issues/4))

### Removed
- 템플릿 자리표시자 `greet()` — 실물이 들어와 자리를 비켜줬다
