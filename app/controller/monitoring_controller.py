"""모니터링 Controller. 주문량 확인/재고량 확인 하위 메뉴를 담당한다."""

from app.model.order import OrderStatus

_MONITORED_STATUSES = [
    OrderStatus.RESERVED,
    OrderStatus.PRODUCING,
    OrderStatus.CONFIRMED,
    OrderStatus.RELEASE,
]


class MonitoringController:
    def __init__(self, order_repo, sample_repo, view) -> None:
        self._order_repo = order_repo
        self._sample_repo = sample_repo
        self._view = view

    def run(self) -> None:
        while True:
            self._view.show_menu()
            choice = self._view.prompt_choice()
            if choice == "1":
                self._show_order_counts()
            elif choice == "2":
                self._show_stock_status()
            elif choice == "0":
                return
            else:
                self._view.show_error("알 수 없는 선택입니다. 메뉴에 표시된 번호를 입력하세요.")

    def _show_order_counts(self) -> None:
        counts = {
            status: len(self._order_repo.find(lambda o, s=status: o.status == s))
            for status in _MONITORED_STATUSES
        }
        self._view.show_order_counts(counts)

    def _show_stock_status(self) -> None:
        pending_demand = {}
        for status in (OrderStatus.RESERVED, OrderStatus.PRODUCING):
            for order in self._order_repo.find(lambda o, s=status: o.status == s):
                pending_demand[order.sample_id] = (
                    pending_demand.get(order.sample_id, 0) + order.quantity
                )

        rows = []
        for sample in self._sample_repo.get_all():
            demand = pending_demand.get(sample.sample_id, 0)
            if sample.stock == 0:
                state = "고갈"
            elif sample.stock < demand:
                state = "부족"
            else:
                state = "여유"
            rows.append((sample, demand, state))
        self._view.show_stock_status(rows)
