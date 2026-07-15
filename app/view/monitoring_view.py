"""모니터링 View. 조회 결과 출력만 담당하고 집계/판정 로직은 포함하지 않는다."""


class MonitoringView:
    def show_menu(self) -> None:
        print("== 모니터링 ==")
        print("[1] 주문량 확인")
        print("[2] 재고량 확인")
        print("[0] 뒤로가기")

    def prompt_choice(self) -> str:
        return input("> ").strip()

    def show_error(self, message: str) -> None:
        print(f"[오류] {message}")

    def show_order_counts(self, counts: dict) -> None:
        print("== 상태별 주문 건수 ==")
        for status, count in counts.items():
            print(f"{status.value}: {count}건")
        print(f"합계: {sum(counts.values())}건")

    def show_stock_status(self, rows: list) -> None:
        if not rows:
            print("[알림] 등록된 시료가 없습니다.")
            return

        print("== 시료별 재고 현황 ==")
        for sample, demand, state in rows:
            print(
                f"{sample.sample_id} / {sample.name} / 재고 {sample.stock} / "
                f"미결수요 {demand} / 상태 {state}"
            )
