"""SampleOrderSystem 진입점.

콘솔 메뉴 루프를 시작한다. `Ctrl+C`(KeyboardInterrupt)는 여기서만 최상위로 잡아
스택트레이스 없이 정상 종료 메시지를 출력한다.
"""

import sys

from app.controller.main_controller import MainController


def _force_utf8_io() -> None:
    """표준입출력을 항상 UTF-8로 강제 재구성한다.

    Windows 콘솔(코드페이지 949 등)에서 `-X utf8` 없이 실행하더라도 한글
    입력/출력이 깨지거나 JSON 저장 단계에서 UnicodeEncodeError가 발생하지
    않도록, 어떤 I/O도 하기 전에 가장 먼저 호출되어야 한다.
    """
    for stream_name in ("stdin", "stdout", "stderr"):
        stream = getattr(sys, stream_name)
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def main() -> None:
    _force_utf8_io()
    try:
        MainController().run()
    except KeyboardInterrupt:
        print("\n시스템을 종료합니다.")


if __name__ == "__main__":
    main()
