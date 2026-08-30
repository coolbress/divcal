"""`divcal serve <예정표.csv>` — 폰 캘린더가 구독하는 `.ics` 피드를 낸다 (#6 AC-7~13).

stdlib `http.server` 로만 짓는다 — `dependencies = []` 를 지키기 위해서다.

🔴 **이 서버는 보유내역 전체를 URL 하나로 연다.** 비밀번호가 없고 토큰이 유일한 자물쇠다.
그래서 `#1`·`#4` 가 세운 *"보유내역을 어디에도 안 넘긴다"* 는 근거는 여기서 반쯤 판다 —
아는 채로 고른 것이고, 그 선택은 `#6` 과 `README` 에 적혀 있다.
"""

from __future__ import annotations

import argparse
import secrets
import sys
from collections.abc import Sequence
from decimal import Decimal
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Final

from divcal.cashflow import COLUMNS, DivcalError, load_payments, parse_tax_rate
from divcal.ics import to_ics

#: 루프백에만 묶는다. 밖으로 내는 일은 터널이 한다 — 서버가 직접 0.0.0.0 을 잡지 않는다.
HOST: Final = "127.0.0.1"
PORT: Final = 8765
CONTENT_TYPE: Final = "text/calendar; charset=utf-8"


def make_server(schedule: Path, rate: Decimal | None, port: int = PORT) -> ThreadingHTTPServer:
    """포트에 묶인 서버. **구독 URL 을 stdout 에 한 줄 찍는다** (AC-9) — 그게 산출물이다.

    토큰은 프로세스마다 새로 난다. 샜다고 생각되면 **다시 띄우는 것이 무효화**다.
    """
    feed = f"/{secrets.token_urlsafe(32)}.ics"

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            # 상수시간 비교. 토큰은 비밀이고 비밀은 `==` 로 재지 않는다.
            if not secrets.compare_digest(self.path, feed):
                # 본문에 토큰 이야기를 안 쓴다 — 길이도 형식도 존재 여부도 안 흘린다 (AC-8).
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            try:
                # **요청마다 읽는다.** 예정표를 고치면 재시작 없이 다음 동기화에 반영된다 (AC-10).
                body = to_ics(load_payments(schedule), rate).encode()
            except DivcalError as exc:
                # 한 줄 남기고 **서버는 산다** (AC-11). 다음 요청에 고쳐진 CSV 를 다시 읽는다.
                print(f"divcal: {exc}", file=sys.stderr)
                self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", CONTENT_TYPE)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 — 시그니처가 고정이다
            """접속 로그를 끈다 — 기본 구현은 **토큰이 든 경로를** stderr 로 흘린다."""

    try:
        server = ThreadingHTTPServer((HOST, port), Handler)
    except OSError as exc:
        # 두 번 띄우면 여기로 온다 — 가장 흔한 실수에 트레이스백을 보여주지 않는다.
        raise DivcalError(
            f"{HOST}:{port} 을(를) 못 연다 — {exc.strerror}. `--port` 로 옮겨라"
        ) from None
    # `flush` 를 빼면 파이프로 받을 때 URL 이 버퍼에 갇힌다 — 유일한 산출물이라 즉시 내보낸다.
    print(f"http://{HOST}:{server.server_port}{feed}", flush=True)
    return server


def main(argv: Sequence[str]) -> int:
    """`divcal serve` 의 명령줄 표면. `DivcalError` 는 `cli.main` 이 한 줄로 옮긴다."""
    parser = argparse.ArgumentParser(
        prog="divcal serve",
        description="폰 캘린더가 구독하는 .ics 피드를 낸다. 🔴 URL 하나가 보유내역 전체를 연다.",
    )
    parser.add_argument("schedule", type=Path, help=f"지급 예정 CSV ({','.join(COLUMNS)})")
    parser.add_argument(
        "--tax",
        metavar="퍼센트",
        help="원천징수 세율. 퍼센트 단위다 — 15%% 는 `--tax 15`. 안 주면 세전으로 찍는다.",
    )
    parser.add_argument("--port", type=int, default=PORT, help=f"들을 포트 (기본 {PORT})")
    args = parser.parse_args(argv)

    rate = None if args.tax is None else parse_tax_rate(args.tax)
    # 시작할 때 한 번 읽어본다. 경로를 잘못 적었으면 **여기서** 알려주는 편이 낫다 —
    # 안 그러면 폰이 조용히 500 을 받고 사용자는 캘린더가 안 뜨는 이유를 모른다.
    load_payments(args.schedule)

    with make_server(args.schedule, rate, args.port) as server:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print()  # ^C 가 남긴 반 줄을 닫는다
    return 0
