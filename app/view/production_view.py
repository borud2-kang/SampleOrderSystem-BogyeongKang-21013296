"""생산 라인 View. 메뉴/조회/완료 결과 출력만 담당하고 비즈니스 로직은 포함하지 않는다."""

from typing import List, Optional

from app.model.production_job import ProductionJob


class ProductionView:
    def show_menu(self) -> None:
        print("== 생산 라인 조회 ==")
        print("[1] 생산 현황 확인")
        print("[2] 대기 생산 완료 처리")
        print("[0] 뒤로가기")

    def prompt_choice(self) -> str:
        return input("선택 > ").strip()

    def show_error(self, message: str) -> None:
        print(f"[오류] {message}")

    def show_current(self, job: Optional[ProductionJob]) -> None:
        if job is None:
            print("[알림] 현재 생산 중인 작업이 없습니다.")
            return

        print("== 현재 생산 중 ==")
        print(
            f"주문번호 {job.order_id} / 시료 {job.sample_id} / 부족분 {job.shortage_qty} / "
            f"실생산량 {job.actual_qty} / 총 생산시간 {job.total_time}"
        )

    def show_waiting(self, jobs: List[ProductionJob]) -> None:
        if not jobs:
            print("[알림] 대기 중인 작업이 없습니다.")
            return

        print("== 대기 중인 작업 (FIFO 순서) ==")
        for job in jobs:
            print(
                f"주문번호 {job.order_id} / 시료 {job.sample_id} / 부족분 {job.shortage_qty} / "
                f"실생산량 {job.actual_qty} / 총 생산시간 {job.total_time}"
            )

    def show_completed(self, job: ProductionJob) -> None:
        print(
            f"[완료] 주문번호 {job.order_id} / 시료 {job.sample_id} / "
            f"부족분 {job.shortage_qty} / 실생산량 {job.actual_qty}"
        )
