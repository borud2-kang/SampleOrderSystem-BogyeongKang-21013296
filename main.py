"""SampleOrderSystem 진입점.

콘솔 메뉴 루프를 시작한다. `Ctrl+C`(KeyboardInterrupt)는 여기서만 최상위로 잡아
스택트레이스 없이 정상 종료 메시지를 출력한다.
"""

from app.controller.main_controller import MainController


def main() -> None:
    try:
        MainController().run()
    except KeyboardInterrupt:
        print("\n시스템을 종료합니다.")


if __name__ == "__main__":
    main()
