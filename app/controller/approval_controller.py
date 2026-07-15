"""주문 승인/거절 Controller. 재고 기반 상태 분기(CONFIRMED/PRODUCING)를 담당하는 핵심 로직.

이 분기 로직은 콘솔 입출력과 분리된 순수 로직이어야 하므로, 여기서 input()/print()를 직접 호출하지
않고 View를 통해서만 사용자와 상호작용한다.
"""

import math

from app.model.order import Order, OrderStatus
from app.model.production_job import ProductionJob


class ApprovalController:
    def __init__(self, order_repo, sample_repo, production_queue, view) -> None:
        self._order_repo = order_repo
        self._sample_repo = sample_repo
        self._production_queue = production_queue
        self._view = view

    def run(self) -> None:
        while True:
            reserved = self._order_repo.find(lambda o: o.status == OrderStatus.RESERVED)
            self._view.show_reserved_list(reserved, self._sample_repo)
            if not reserved:
                return

            order_id = self._view.prompt_order_id()
            if order_id == "0":
                return

            order = self._order_repo.get(order_id)
            if order is None or order.status != OrderStatus.RESERVED:
                self._view.show_error(f"승인 대기 중인 주문이 아닙니다: {order_id}")
                continue

            decision = self._view.prompt_decision()
            if decision == "N":
                self._reject(order)
            else:
                self._approve(order)

    def _reject(self, order: Order) -> None:
        order.status = OrderStatus.REJECTED
        self._order_repo.update(order.order_id, order)
        self._view.show_result(order)

    def _approve(self, order: Order) -> None:
        sample = self._sample_repo.get(order.sample_id)
        if sample.stock >= order.quantity:
            sample.stock -= order.quantity
            self._sample_repo.update(sample.sample_id, sample)
            order.status = OrderStatus.CONFIRMED
            self._order_repo.update(order.order_id, order)
            self._view.show_result(order, extra="재고 충분, 즉시 출고 대기")
        else:
            shortage = order.quantity - sample.stock
            actual_qty = self._ceil_division(shortage, sample.yield_rate)
            total_time = sample.avg_process_time * actual_qty
            job = ProductionJob(order.order_id, sample.sample_id, shortage, actual_qty, total_time)
            self._production_queue.enqueue(job)
            order.status = OrderStatus.PRODUCING
            self._order_repo.update(order.order_id, order)
            self._view.show_result(
                order, extra=f"재고 부족(부족분 {shortage}), 생산 등록 {actual_qty}ea"
            )

    @staticmethod
    def _ceil_division(shortage: int, yield_rate: float) -> int:
        """`ceil(shortage / yield_rate)`. 부동소수점 오차로 나눠떨어지는 값이 한 단위 더 올림되지
        않도록 소수점을 반올림한 뒤 ceil을 적용한다 (예: 180/0.9는 정확히 200이어야 하며 201이 되면
        안 된다 - FEATURES/05-production-line.md 엣지 케이스)."""
        return math.ceil(round(shortage / yield_rate, 6))
