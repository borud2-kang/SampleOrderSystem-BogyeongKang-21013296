"""생산 라인 Controller. 생산 현황 조회와 생산 완료 처리를 담당한다."""

from app.model.order import OrderStatus


class ProductionController:
    def __init__(self, production_queue, order_repo, sample_repo, view) -> None:
        self._production_queue = production_queue
        self._order_repo = order_repo
        self._sample_repo = sample_repo
        self._view = view

    def run(self) -> None:
        while True:
            self._view.show_menu()
            choice = self._view.prompt_choice()

            if choice == "1":
                self._show_status()
            elif choice == "2":
                self._complete_current()
            elif choice == "0":
                return
            else:
                self._view.show_error("알 수 없는 선택입니다. 메뉴에 표시된 번호를 입력하세요.")

    def _show_status(self) -> None:
        self._view.show_current(self._production_queue.peek_current())
        self._view.show_waiting(self._production_queue.list_waiting())

    def _complete_current(self) -> None:
        job = self._production_queue.pop_next()
        if job is None:
            self._view.show_error("완료할 생산 작업이 없습니다.")
            return

        sample = self._sample_repo.get(job.sample_id)
        sample.stock += job.shortage_qty
        self._sample_repo.update(sample.sample_id, sample)

        order = self._order_repo.get(job.order_id)
        order.status = OrderStatus.CONFIRMED
        self._order_repo.update(order.order_id, order)

        sample.stock -= order.quantity
        self._sample_repo.update(sample.sample_id, sample)

        self._view.show_completed(job)
