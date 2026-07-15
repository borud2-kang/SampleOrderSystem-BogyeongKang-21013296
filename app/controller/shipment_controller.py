"""출고 처리 Controller. CONFIRMED 주문을 선택해 RELEASE로 전환하는 흐름을 담당한다.

재고(sample.stock)는 여기서 절대 읽거나 쓰지 않는다 — 이미 승인/생산완료 시점에 반영되어 있어야 한다
(docs/FEATURES/06-shipment.md). sample_repo는 오직 View의 시료명 표시 용도로만 전달한다.
"""

from app.model.order import OrderStatus


class ShipmentController:
    def __init__(self, order_repo, sample_repo, view) -> None:
        self._order_repo = order_repo
        self._sample_repo = sample_repo
        self._view = view

    def run(self) -> None:
        while True:
            confirmed = self._order_repo.find(lambda o: o.status == OrderStatus.CONFIRMED)
            self._view.show_confirmed_list(confirmed, self._sample_repo)
            if not confirmed:
                return

            order_id = self._view.prompt_order_id()
            if order_id == "0":
                return

            order = self._order_repo.get(order_id)
            if order is None or order.status != OrderStatus.CONFIRMED:
                self._view.show_error(f"출고 가능한 주문이 아닙니다: {order_id}")
                continue

            order.status = OrderStatus.RELEASE
            self._order_repo.update(order.order_id, order)
            self._view.show_result(order)
