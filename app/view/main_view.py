"""메인 메뉴 View. 입출력만 담당하고 비즈니스 로직은 포함하지 않는다."""


class MainView:
    def show_menu(self, summary: dict) -> None:
        print("=" * 60)
        print(" 반도체 시료 생산주문관리 시스템 (S-Semi)")
        print("=" * 60)
        print(f" 등록 시료 : {summary['sample_count']}종"
              f"   총 재고 : {summary['total_stock']} ea")
        print(f" 전체 주문 : {summary['order_count']}건"
              f"   생산 대기 : {summary['producing_count']}건")
        print("-" * 60)
        print(" [1] 시료 관리      [2] 시료 주문")
        print(" [3] 주문 승인/거절 [4] 모니터링")
        print(" [5] 생산 라인 조회 [6] 출고 처리")
        print(" [0] 종료")
        print("-" * 60)

    def prompt_choice(self) -> str:
        return input("선택 > ").strip()

    def show_message(self, message: str) -> None:
        print(message)

    def show_error(self, message: str) -> None:
        print(f"[오류] {message}")

    def pause(self) -> None:
        input("\n계속하려면 Enter 를 누르세요...")
