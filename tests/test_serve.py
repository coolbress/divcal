"""#6 의 AC-7 ~ AC-11 — 요청이 들어오면 `.ics` 가 나가는 부분.

서버를 **진짜로 띄우고 HTTP 로 두드린다.** 핸들러를 직접 부르면 상태코드·헤더가
실제로 나가는지 못 본다 — 그게 이 조각의 전부다.
"""

from __future__ import annotations

import re
import threading
from collections.abc import Iterator
from http import HTTPStatus
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

import pytest

from divcal.cashflow import DivcalError
from divcal.serve import make_server

SCHEDULE = "ticker,shares,amount_per_share,pay_date\nKO,100,0.485,2026-04-01\n"

#: `secrets.token_urlsafe(32)` 는 43글자 URL-safe base64 다.
FEED_URL = re.compile(r"http://127\.0\.0\.1:\d+/[A-Za-z0-9_-]{43}\.ics")


def _get(url: str) -> tuple[int, str, str]:
    """상태 · `Content-Type` · 본문. 404/500 도 예외가 아니라 값으로 받는다."""
    try:
        with urlopen(url) as res:  # noqa: S310 — 이 테스트가 방금 띄운 http:// 서버다
            return res.status, res.headers.get("Content-Type", ""), res.read().decode()
    except HTTPError as exc:
        with exc:
            return exc.code, exc.headers.get("Content-Type", ""), exc.read().decode()


def _write(tmp_path: Path, text: str = SCHEDULE) -> Path:
    path = tmp_path / "schedule.csv"
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture
def feed(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> Iterator[tuple[str, Path]]:
    """서버 하나를 띄우고 **구독 URL 과 CSV 경로**를 준다.

    URL 은 사용자와 똑같이 **stdout 에서 읽는다** — 토큰을 얻는 다른 통로가 없다는 것도
    이 픽스처가 같이 증명한다.
    """
    path = _write(tmp_path)
    server = make_server(path, None, port=0)
    url = capsys.readouterr().out.strip()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield url, path
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_feed_ok(feed: tuple[str, Path]) -> None:
    """AC-7 — 맞는 토큰이면 200 과 `text/calendar` 다."""
    status, content_type, body = _get(feed[0])

    assert status == HTTPStatus.OK
    assert content_type == "text/calendar; charset=utf-8"
    assert body.startswith("BEGIN:VCALENDAR")
    assert "SUMMARY:KO 배당 $48.50" in body


def test_wrong_token_404_leaks_nothing(feed: tuple[str, Path]) -> None:
    """AC-8 — 틀린 토큰은 404 고, 본문이 토큰의 **존재도 길이도** 안 흘린다."""
    url, _ = feed
    base, token = url.rsplit("/", 1)

    for wrong in (f"{base}/nope.ics", f"{base}/", f"{base}/{token[:-5]}.ics"):
        status, _, body = _get(wrong)

        assert status == HTTPStatus.NOT_FOUND
        assert token[:-4] not in body  # 토큰이 안 새고
        assert "nope" not in body  # 받은 경로를 되비추지도 않고
        assert str(len(token)) not in body  # 길이 힌트도 없다


def test_prints_url_once(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """AC-9 — 시작할 때 전체 URL 을 stdout 에 **한 번** 찍는다."""
    server = make_server(_write(tmp_path), None, port=0)
    server.server_close()

    printed = capsys.readouterr().out.splitlines()

    assert len(printed) == 1
    assert FEED_URL.fullmatch(printed[0]), printed[0]


def test_reflects_edited_csv(feed: tuple[str, Path]) -> None:
    """AC-10 — 요청마다 읽는다. CSV 를 고치면 **재시작 없이** 다음 요청에 반영된다."""
    url, path = feed
    assert "$48.50" in _get(url)[2]

    path.write_text(SCHEDULE.replace("0.485", "0.97"), encoding="utf-8")

    assert "$97.00" in _get(url)[2]


def test_broken_csv_500_stays_up(
    feed: tuple[str, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    """AC-11 — 깨진 CSV 는 500 과 stderr 한 줄이다. **서버는 안 죽는다.**"""
    url, path = feed
    path.write_text("ticker,shares\nKO,100\n", encoding="utf-8")

    assert _get(url)[0] == HTTPStatus.INTERNAL_SERVER_ERROR
    assert "divcal: " in capsys.readouterr().err

    path.write_text(SCHEDULE, encoding="utf-8")

    assert _get(url)[0] == HTTPStatus.OK  # 같은 프로세스가 그대로 답한다


def test_busy_port_is_a_message_not_a_traceback(feed: tuple[str, Path]) -> None:
    """기본 포트로 두 번 띄우는 것이 가장 흔한 실수다. `DivcalError` 면 `cli` 가 한 줄로 옮긴다."""
    url, path = feed
    taken = int(url.rsplit(":", 1)[1].split("/")[0])

    with pytest.raises(DivcalError, match="--port"):
        make_server(path, None, port=taken)
