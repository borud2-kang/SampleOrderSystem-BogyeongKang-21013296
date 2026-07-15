"""시료 주문(접수) Controller. 주문 생성만 처리한다 (재고 확인/상태 분기는 승인 단계의 책임)."""

from app.model.order import Order, OrderStatus


class OrderController:
    def __init__(self, order_repo, sample_repo, view) -> None:
        self._order_repo = order_repo
        self._sample_repo = sample_repo
        self._view = view

    def run(self) -> None:
        data = self._view.prompt_reservation(self._sample_repo)
        order = Order(
            order_id=self._order_repo.next_id(),
            sample_id=data["sample_id"],
            customer_name=data["customer_name"],
            quantity=data["quantity"],
            status=OrderStatus.RESERVED,
        )
        self._order_repo.create(order)
        self._view.show_reserved(order)
