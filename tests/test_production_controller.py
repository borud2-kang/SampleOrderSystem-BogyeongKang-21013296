"""ProductionController 단위 테스트. ProductionView를 테스트 더블로 대체해 stdin 시뮬레이션 없이
FIFO 순서 / 재고 반영(actual_qty 전체 반영, 올림 처리로 인한 여유분 유지) / 상태 전환을 검증한다."""

import pytest

from app.controller.production_controller import ProductionController
from app.model.order import Order, OrderStatus
from app.model.production_job import ProductionJob
from app.model.sample import Sample
from app.persistence.order_repository import OrderRepository
from app.persistence.production_queue import ProductionQueue
from app.persistence.sample_repository import SampleRepository


class FakeProductionView:
    """ProductionView 대신 사용하는 테스트 더블."""

    def __init__(self, choices=None):
        self._choices = list(choices or [])
        self.current_shown = []
        self.waiting_shown = []
        self.errors = []
        self.completed = []

    def show_menu(self):
        pass

    def prompt_choice(self):
        return self._choices.pop(0)

    def show_error(self, message):
        self.errors.append(message)

    def show_current(self, job):
        self.current_shown.append(job)

    def show_waiting(self, jobs):
        self.waiting_shown.append(list(jobs))

    def show_completed(self, job):
        self.completed.append(job)


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


def make_order(order_repo, *, sample_id, customer_name="홍길동", quantity, status=OrderStatus.PRODUCING):
    order = Order(
        order_id=order_repo.next_id(),
        sample_id=sample_id,
        customer_name=customer_name,
        quantity=quantity,
        status=status,
    )
    order_repo.create(order)
    return order


def test_fifo_order_shown_current_and_waiting(order_repo, sample_repo, production_queue):
    sample = make_sample(sample_repo, stock=0)
    order1 = make_order(order_repo, sample_id=sample.sample_id, quantity=10)
    order2 = make_order(order_repo, sample_id=sample.sample_id, quantity=20)
    order3 = make_order(order_repo, sample_id=sample.sample_id, quantity=30)

    job1 = ProductionJob(order1.order_id, sample.sample_id, shortage_qty=10, actual_qty=12, total_time=12.0)
    job2 = ProductionJob(order2.order_id, sample.sample_id, shortage_qty=20, actual_qty=23, total_time=23.0)
    job3 = ProductionJob(order3.order_id, sample.sample_id, shortage_qty=30, actual_qty=34, total_time=34.0)
    production_queue.enqueue(job1)
    production_queue.enqueue(job2)
    production_queue.enqueue(job3)

    view = FakeProductionView(choices=["1", "0"])
    controller = ProductionController(production_queue, order_repo, sample_repo, view)

    controller.run()

    assert view.current_shown == [job1]
    assert view.waiting_shown == [[job2, job3]]


def test_complete_current_credits_full_actual_qty_leaving_surplus(
    order_repo, sample_repo, production_queue
):
    """핵심 검증: actual_qty(올림 처리로 인한 여유분 포함) 전체가 재고에 반영되어야 한다."""
    sample = make_sample(sample_repo, stock=10)
    order = make_order(order_repo, sample_id=sample.sample_id, quantity=180)
    # 부족분 = 170, 실 생산량(ceil(170/0.92)) = 185 (여유분 15)
    job = ProductionJob(order.order_id, sample.sample_id, shortage_qty=170, actual_qty=185, total_time=340.0)
    production_queue.enqueue(job)

    view = FakeProductionView(choices=["2", "0"])
    controller = ProductionController(production_queue, order_repo, sample_repo, view)

    controller.run()

    saved_sample = sample_repo.get(sample.sample_id)
    # 최종 재고 = 기존 재고(10) + actual_qty(185) - order.quantity(180) = 15 (여유분 그대로 남음)
    assert saved_sample.stock == 10 + job.actual_qty - order.quantity
    assert saved_sample.stock == 15

    saved_order = order_repo.get(order.order_id)
    assert saved_order.status == OrderStatus.CONFIRMED


def test_complete_current_no_surplus_when_actual_qty_equals_shortage(
    order_repo, sample_repo, production_queue
):
    """수율이 정확히 1이거나 나눠떨어져 여유분이 0인 경우, 재고 순증감도 0이어야 한다."""
    sample = make_sample(sample_repo, stock=0)
    order = make_order(order_repo, sample_id=sample.sample_id, quantity=10)
    job = ProductionJob(order.order_id, sample.sample_id, shortage_qty=10, actual_qty=10, total_time=10.0)
    production_queue.enqueue(job)

    view = FakeProductionView(choices=["2", "0"])
    controller = ProductionController(production_queue, order_repo, sample_repo, view)

    controller.run()

    assert sample_repo.get(sample.sample_id).stock == 0


def test_complete_current_transitions_producing_to_confirmed_and_persists(
    order_repo, sample_repo, production_queue
):
    sample = make_sample(sample_repo, stock=0)
    order = make_order(order_repo, sample_id=sample.sample_id, quantity=5, status=OrderStatus.PRODUCING)
    job = ProductionJob(order.order_id, sample.sample_id, shortage_qty=5, actual_qty=6, total_time=6.0)
    production_queue.enqueue(job)

    view = FakeProductionView(choices=["2", "0"])
    controller = ProductionController(production_queue, order_repo, sample_repo, view)

    controller.run()

    saved_order = order_repo.get(order.order_id)
    assert saved_order.status == OrderStatus.CONFIRMED
    assert len(view.completed) == 1
    assert view.completed[0].order_id == order.order_id


def test_multiple_complete_calls_processed_in_fifo_order(order_repo, sample_repo, production_queue):
    sample = make_sample(sample_repo, stock=0)
    order1 = make_order(order_repo, sample_id=sample.sample_id, quantity=10)
    order2 = make_order(order_repo, sample_id=sample.sample_id, quantity=20)

    job1 = ProductionJob(order1.order_id, sample.sample_id, shortage_qty=10, actual_qty=10, total_time=10.0)
    job2 = ProductionJob(order2.order_id, sample.sample_id, shortage_qty=20, actual_qty=20, total_time=20.0)
    production_queue.enqueue(job1)
    production_queue.enqueue(job2)

    view = FakeProductionView(choices=["2", "2", "0"])
    controller = ProductionController(production_queue, order_repo, sample_repo, view)

    controller.run()

    assert [job.order_id for job in view.completed] == [order1.order_id, order2.order_id]

    saved_order1 = order_repo.get(order1.order_id)
    saved_order2 = order_repo.get(order2.order_id)
    assert saved_order1.status == OrderStatus.CONFIRMED
    assert saved_order2.status == OrderStatus.CONFIRMED

    # 두 건 순차 처리 후 재고: 0 + 10 - 10 = 0, 그 다음 0 + 20 - 20 = 0
    assert sample_repo.get(sample.sample_id).stock == 0
    assert len(production_queue) == 0


def test_empty_queue_show_status_reports_none_without_error(order_repo, sample_repo, production_queue):
    view = FakeProductionView(choices=["1", "0"])
    controller = ProductionController(production_queue, order_repo, sample_repo, view)

    controller.run()

    assert view.current_shown == [None]
    assert view.waiting_shown == [[]]
    assert view.errors == []


def test_empty_queue_complete_shows_error_and_continues_without_crashing(
    order_repo, sample_repo, production_queue
):
    view = FakeProductionView(choices=["2", "0"])
    controller = ProductionController(production_queue, order_repo, sample_repo, view)

    controller.run()

    assert len(view.errors) == 1
    assert view.completed == []


def test_unknown_choice_shows_error_and_loop_continues(order_repo, sample_repo, production_queue):
    view = FakeProductionView(choices=["9", "0"])
    controller = ProductionController(production_queue, order_repo, sample_repo, view)

    controller.run()

    assert len(view.errors) == 1
