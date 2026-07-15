"""ApprovalController 단위 테스트. ApprovalView를 테스트 더블로 대체해 stdin 시뮬레이션 없이
재고 기반 상태 분기(CONFIRMED/PRODUCING) 로직만 검증한다."""

import math

import pytest

from app.controller.approval_controller import ApprovalController
from app.model.order import Order, OrderStatus
from app.model.sample import Sample
from app.persistence.order_repository import OrderRepository
from app.persistence.production_queue import ProductionQueue
from app.persistence.sample_repository import SampleRepository


class FakeApprovalView:
    """ApprovalView 대신 사용하는 테스트 더블.

    order_ids: 순서대로 prompt_order_id()가 반환할 값들의 리스트.
    decisions: 순서대로 prompt_decision()이 반환할 값들의 리스트 ("Y"/"N").
    """

    def __init__(self, order_ids=None, decisions=None):
        self._order_ids = list(order_ids or [])
        self._decisions = list(decisions or [])
        self.shown_lists = []
        self.errors = []
        self.results = []

    def show_reserved_list(self, orders, sample_repo):
        self.shown_lists.append(list(orders))

    def prompt_order_id(self):
        return self._order_ids.pop(0)

    def prompt_decision(self):
        return self._decisions.pop(0)

    def show_error(self, message):
        self.errors.append(message)

    def show_result(self, order, extra=""):
        self.results.append((order.order_id, order.status, extra))


@pytest.fixture
def order_repo(tmp_path):
    return OrderRepository(str(tmp_path / "orders.json"))


@pytest.fixture
def sample_repo(tmp_path):
    return SampleRepository(str(tmp_path / "samples.json"))


@pytest.fixture
def production_queue():
    return ProductionQueue()


def make_sample(sample_repo, *, name="웨이퍼", avg_process_time=1.0, yield_rate=0.9, stock=0):
    sample = Sample(
        sample_id=sample_repo.next_id(),
        name=name,
        avg_process_time=avg_process_time,
        yield_rate=yield_rate,
        stock=stock,
    )
    sample_repo.create(sample)
    return sample


def make_order(order_repo, *, sample_id, customer_name="홍길동", quantity, status=OrderStatus.RESERVED):
    order = Order(
        order_id=order_repo.next_id(),
        sample_id=sample_id,
        customer_name=customer_name,
        quantity=quantity,
        status=status,
    )
    order_repo.create(order)
    return order


def test_sufficient_stock_confirms_immediately_and_deducts_stock(
    order_repo, sample_repo, production_queue
):
    sample = make_sample(sample_repo, stock=50)
    order = make_order(order_repo, sample_id=sample.sample_id, quantity=10)

    view = FakeApprovalView(order_ids=[order.order_id], decisions=["Y"])
    controller = ApprovalController(order_repo, sample_repo, production_queue, view)

    controller.run()

    saved_order = order_repo.get(order.order_id)
    assert saved_order.status == OrderStatus.CONFIRMED

    saved_sample = sample_repo.get(sample.sample_id)
    assert saved_sample.stock == 40  # 50 - 10

    assert len(production_queue) == 0
    assert view.results == [(order.order_id, OrderStatus.CONFIRMED, "재고 충분, 즉시 출고 대기")]


def test_stock_exactly_equal_to_quantity_is_treated_as_sufficient(
    order_repo, sample_repo, production_queue
):
    """경계값: 재고 == 주문 수량 -> CONFIRMED (부족분 0)."""
    sample = make_sample(sample_repo, stock=10)
    order = make_order(order_repo, sample_id=sample.sample_id, quantity=10)

    view = FakeApprovalView(order_ids=[order.order_id], decisions=["Y"])
    controller = ApprovalController(order_repo, sample_repo, production_queue, view)

    controller.run()

    saved_order = order_repo.get(order.order_id)
    assert saved_order.status == OrderStatus.CONFIRMED

    saved_sample = sample_repo.get(sample.sample_id)
    assert saved_sample.stock == 0

    assert len(production_queue) == 0


def test_insufficient_stock_enqueues_production_job_without_touching_stock(
    order_repo, sample_repo, production_queue
):
    sample = make_sample(sample_repo, avg_process_time=2.0, yield_rate=0.92, stock=10)
    order = make_order(order_repo, sample_id=sample.sample_id, quantity=180)
    # 부족분 = 180 - 10 = 170, 실 생산량 = ceil(170 / 0.92) = 185

    view = FakeApprovalView(order_ids=[order.order_id], decisions=["Y"])
    controller = ApprovalController(order_repo, sample_repo, production_queue, view)

    controller.run()

    saved_order = order_repo.get(order.order_id)
    assert saved_order.status == OrderStatus.PRODUCING

    saved_sample = sample_repo.get(sample.sample_id)
    assert saved_sample.stock == 10

    assert len(production_queue) == 1
    job = production_queue.pop_next()
    assert job.order_id == order.order_id
    assert job.sample_id == sample.sample_id
    assert job.shortage_qty == 170
    assert job.actual_qty == 185
    assert job.total_time == pytest.approx(2.0 * 185)


def test_insufficient_stock_zero_stock(order_repo, sample_repo, production_queue):
    sample = make_sample(sample_repo, avg_process_time=1.0, yield_rate=0.9, stock=0)
    order = make_order(order_repo, sample_id=sample.sample_id, quantity=50)

    view = FakeApprovalView(order_ids=[order.order_id], decisions=["Y"])
    controller = ApprovalController(order_repo, sample_repo, production_queue, view)

    controller.run()

    saved_order = order_repo.get(order.order_id)
    assert saved_order.status == OrderStatus.PRODUCING

    saved_sample = sample_repo.get(sample.sample_id)
    assert saved_sample.stock == 0

    job = production_queue.pop_next()
    assert job.shortage_qty == 50
    assert job.actual_qty == math.ceil(50 / 0.9)


def test_yield_rate_exactly_one_actual_qty_equals_shortage(
    order_repo, sample_repo, production_queue
):
    sample = make_sample(sample_repo, avg_process_time=1.5, yield_rate=1.0, stock=5)
    order = make_order(order_repo, sample_id=sample.sample_id, quantity=25)

    view = FakeApprovalView(order_ids=[order.order_id], decisions=["Y"])
    controller = ApprovalController(order_repo, sample_repo, production_queue, view)

    controller.run()

    job = production_queue.pop_next()
    assert job.shortage_qty == 20
    assert job.actual_qty == 20
    assert job.total_time == pytest.approx(1.5 * 20)


def test_shortage_divides_evenly_by_yield_does_not_round_up_due_to_float_error(
    order_repo, sample_repo, production_queue
):
    """180 / 0.9 = 200 정확히 나눠떨어지는 경우, 부동소수점 오차로 201이 되면 안 된다."""
    sample = make_sample(sample_repo, avg_process_time=1.0, yield_rate=0.9, stock=0)
    order = make_order(order_repo, sample_id=sample.sample_id, quantity=180)

    view = FakeApprovalView(order_ids=[order.order_id], decisions=["Y"])
    controller = ApprovalController(order_repo, sample_repo, production_queue, view)

    controller.run()

    job = production_queue.pop_next()
    assert job.shortage_qty == 180
    assert job.actual_qty == 200


def test_reject_transitions_to_rejected_without_touching_stock_or_queue(
    order_repo, sample_repo, production_queue
):
    sample = make_sample(sample_repo, stock=100)
    order = make_order(order_repo, sample_id=sample.sample_id, quantity=10)

    view = FakeApprovalView(order_ids=[order.order_id], decisions=["N"])
    controller = ApprovalController(order_repo, sample_repo, production_queue, view)

    controller.run()

    saved_order = order_repo.get(order.order_id)
    assert saved_order.status == OrderStatus.REJECTED

    saved_sample = sample_repo.get(sample.sample_id)
    assert saved_sample.stock == 100

    assert len(production_queue) == 0
    assert view.results == [(order.order_id, OrderStatus.REJECTED, "")]


@pytest.mark.parametrize(
    "status",
    [
        OrderStatus.CONFIRMED,
        OrderStatus.PRODUCING,
        OrderStatus.REJECTED,
        OrderStatus.RELEASE,
    ],
)
def test_reprocessing_already_processed_order_shows_error_and_continues(
    order_repo, sample_repo, production_queue, status
):
    sample = make_sample(sample_repo, stock=100)
    processed_order = make_order(
        order_repo, sample_id=sample.sample_id, quantity=10, status=status
    )
    # RESERVED 목록이 비면 controller가 프롬프트 없이 즉시 종료되므로, 실제로 프롬프트가
    # 뜨는 상황을 만들기 위해 아직 처리되지 않은 RESERVED 주문을 하나 더 둔다.
    still_reserved = make_order(order_repo, sample_id=sample.sample_id, quantity=5)
    view = FakeApprovalView(order_ids=[processed_order.order_id, "0"])
    controller = ApprovalController(order_repo, sample_repo, production_queue, view)

    controller.run()

    assert len(view.errors) == 1
    assert processed_order.order_id in view.errors[0]

    saved_still_reserved = order_repo.get(still_reserved.order_id)
    assert saved_still_reserved.status == OrderStatus.RESERVED

    saved_order = order_repo.get(processed_order.order_id)
    assert saved_order.status == status
    saved_sample = sample_repo.get(sample.sample_id)
    assert saved_sample.stock == 100
    assert len(production_queue) == 0


def test_nonexistent_order_id_shows_error_and_allows_continuing(
    order_repo, sample_repo, production_queue
):
    sample = make_sample(sample_repo, stock=100)
    real_order = make_order(order_repo, sample_id=sample.sample_id, quantity=10)

    view = FakeApprovalView(
        order_ids=["ORD-9999", real_order.order_id], decisions=["Y"]
    )
    controller = ApprovalController(order_repo, sample_repo, production_queue, view)

    controller.run()

    assert len(view.errors) == 1
    assert "ORD-9999" in view.errors[0]

    saved_order = order_repo.get(real_order.order_id)
    assert saved_order.status == OrderStatus.CONFIRMED


def test_back_to_menu_with_zero_stops_loop_without_processing(
    order_repo, sample_repo, production_queue
):
    sample = make_sample(sample_repo, stock=100)
    order = make_order(order_repo, sample_id=sample.sample_id, quantity=10)

    view = FakeApprovalView(order_ids=["0"])
    controller = ApprovalController(order_repo, sample_repo, production_queue, view)

    controller.run()

    saved_order = order_repo.get(order.order_id)
    assert saved_order.status == OrderStatus.RESERVED
    assert view.results == []


def test_multiple_reserved_orders_competing_for_same_sample_consume_stock_in_processed_order(
    order_repo, sample_repo, production_queue
):
    sample = make_sample(sample_repo, avg_process_time=1.0, yield_rate=0.9, stock=15)
    order_a = make_order(order_repo, sample_id=sample.sample_id, customer_name="A사", quantity=10)
    order_b = make_order(order_repo, sample_id=sample.sample_id, customer_name="B사", quantity=10)

    view = FakeApprovalView(
        order_ids=[order_b.order_id, order_a.order_id], decisions=["Y", "Y"]
    )
    controller = ApprovalController(order_repo, sample_repo, production_queue, view)

    controller.run()

    saved_b = order_repo.get(order_b.order_id)
    assert saved_b.status == OrderStatus.CONFIRMED
    stock_after_b = sample_repo.get(sample.sample_id).stock
    assert stock_after_b == 5

    saved_a = order_repo.get(order_a.order_id)
    assert saved_a.status == OrderStatus.PRODUCING

    assert len(production_queue) == 1
    job = production_queue.pop_next()
    assert job.order_id == order_a.order_id
    assert job.shortage_qty == 5
    assert job.actual_qty == math.ceil(5 / 0.9)

    assert sample_repo.get(sample.sample_id).stock == 5


def test_empty_reserved_list_returns_immediately_without_prompting(
    order_repo, sample_repo, production_queue
):
    view = FakeApprovalView()
    controller = ApprovalController(order_repo, sample_repo, production_queue, view)

    controller.run()

    assert view.shown_lists == [[]]
