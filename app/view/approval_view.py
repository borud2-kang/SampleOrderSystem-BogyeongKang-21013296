"""주문 승인/거절 View. 목록/프롬프트/결과 출력만 담당하고 비즈니스 로직은 포함하지 않는다."""

from app.model.order import Order
from app.persistence.sample_repository import SampleRepository


class ApprovalView:
    def show_reserved_list(self, orders: list, sample_repo: SampleRepository) -> None:
        if not orders:
            print("[알림] 승인 대기 중인 주문이 없습니다.")
            return

        print("== 승인 대기(RESERVED) 주문 목록 ==")
        for order in orders:
            sample = sample_repo.get(order.sample_id)
            sample_name = sample.name if sample is not None else order.sample_id
            print(
                f"{order.order_id} / 고객 {order.customer_name} / 시료 {sample_name} / "
                f"수량 {order.quantity} / 상태 {order.status.value}"
            )

    def prompt_order_id(self) -> str:
        return input("처리할 주문번호 (0: 뒤로가기) > ").strip()

    def prompt_decision(self) -> str:
        while True:
            raw = input("[Y] 승인 / [N] 거절 > ").strip().upper()
            if raw in ("Y", "N"):
                return raw
            print("[오류] Y 또는 N을 입력하세요.")

    def show_error(self, message: str) -> None:
        print(f"[오류] {message}")

    def show_result(self, order: Order, extra: str = "") -> None:
        message = f"[처리 완료] {order.order_id} / 상태 {order.status.value}"
        if extra:
            message += f" / {extra}"
        print(message)
