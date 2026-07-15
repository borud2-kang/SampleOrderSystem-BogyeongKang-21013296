"""출고 처리 View. 목록/프롬프트/결과 출력만 담당하고 비즈니스 로직은 포함하지 않는다."""

from app.model.order import Order
from app.persistence.sample_repository import SampleRepository


class ShipmentView:
    def show_confirmed_list(self, orders: list, sample_repo: SampleRepository) -> None:
        if not orders:
            print("[알림] 출고 가능한 주문이 없습니다.")
            return

        print("== 출고 대기(CONFIRMED) 주문 목록 ==")
        for order in orders:
            sample = sample_repo.get(order.sample_id)
            sample_name = sample.name if sample is not None else order.sample_id
            print(
                f"{order.order_id} / 고객 {order.customer_name} / 시료 {sample_name} / "
                f"수량 {order.quantity} / 상태 {order.status.value}"
            )

    def prompt_order_id(self) -> str:
        return input("출고할 주문번호 (0: 뒤로가기) > ").strip()

    def show_error(self, message: str) -> None:
        print(f"[오류] {message}")

    def show_result(self, order: Order) -> None:
        print(f"[처리 완료] {order.order_id} / 상태 {order.status.value}")
