"""MonitoringController 단위 테스트. MonitoringView를 테스트 더블로 대체해 stdin 시뮬레이션 없이
상태별 건수 집계, 재고 파생 상태(여유/부족/고갈) 판정 로직을 검증한다."""

import pytest

from app.controller.monitoring_controller import MonitoringController
from app.model.order import Order, OrderStatus
from app.model.sample import Sample
from app.persistence.order_repository import OrderRepository
from app.persistence.sample_repository import SampleRepository


class FakeMonitoringView:
    """MonitoringView 대신 사용하는 테스트 더블."""

    def __init__(self, choices=None):
        self._choices = list(choices or [])
        self.order_counts_calls = []
        self.stock_status_calls = []
        self.errors = []

    def show_menu(self):
        pass

    def prompt_choice(self):
        return self._choices.pop(0)

    def show_error(self, message):
        self.errors.append(message)

    def show_order_counts(self, counts):
        self.order_counts_calls.append(dict(counts))

    def show_stock_status(self, rows):
        self.stock_status_calls.append(list(rows))


@pytest.fixture
def order_repo(tmp_path):
    return OrderRepository(str(tmp_path / "orders.json"))


@pytest.fixture
def sample_repo(tmp_path):
    return SampleRepository(str(tmp_path / "samples.json"))


def make_sample(sample_repo, name="wafer", avg_process_time=1.0, yield_rate=0.9, stock=0):
    sample = Sample(
        sample_id=sample_repo.next_id(),
        name=name,
        avg_process_time=avg_process_time,
        yield_rate=yield_rate,
        stock=stock,
    )
    sample_repo.create(sample)
    return sample


def make_order(order_repo, sample_id, customer_name="cust", quantity=1, status=OrderStatus.RESERVED):
    order = Order(
        order_id=order_repo.next_id(),
        sample_id=sample_id,
        customer_name=customer_name,
        quantity=quantity,
        status=status,
    )
    order_repo.create(order)
    return order


def test_order_counts_are_aggregated_correctly(order_repo, sample_repo):
    sample = make_sample(sample_repo, stock=100)
    make_order(order_repo, sample.sample_id, quantity=1, status=OrderStatus.RESERVED)
    make_order(order_repo, sample.sample_id, quantity=1, status=OrderStatus.RESERVED)
    make_order(order_repo, sample.sample_id, quantity=1, status=OrderStatus.PRODUCING)
    make_order(order_repo, sample.sample_id, quantity=1, status=OrderStatus.CONFIRMED)
    make_order(order_repo, sample.sample_id, quantity=1, status=OrderStatus.CONFIRMED)
    make_order(order_repo, sample.sample_id, quantity=1, status=OrderStatus.CONFIRMED)
    make_order(order_repo, sample.sample_id, quantity=1, status=OrderStatus.RELEASE)

    view = FakeMonitoringView(choices=["1", "0"])
    controller = MonitoringController(order_repo, sample_repo, view)
    controller.run()

    assert len(view.order_counts_calls) == 1
    counts = view.order_counts_calls[0]
    assert counts[OrderStatus.RESERVED] == 2
    assert counts[OrderStatus.PRODUCING] == 1
    assert counts[OrderStatus.CONFIRMED] == 3
    assert counts[OrderStatus.RELEASE] == 1
    assert sum(counts.values()) == 7


def test_rejected_orders_excluded_from_counts_and_sum(order_repo, sample_repo):
    sample = make_sample(sample_repo, stock=100)
    make_order(order_repo, sample.sample_id, quantity=1, status=OrderStatus.RESERVED)
    make_order(order_repo, sample.sample_id, quantity=5, status=OrderStatus.REJECTED)
    make_order(order_repo, sample.sample_id, quantity=5, status=OrderStatus.REJECTED)

    view = FakeMonitoringView(choices=["1", "0"])
    controller = MonitoringController(order_repo, sample_repo, view)
    controller.run()

    counts = view.order_counts_calls[0]
    assert OrderStatus.REJECTED not in counts
    assert sum(counts.values()) == 1


def test_stock_status_depleted_when_stock_zero_even_with_no_demand(order_repo, sample_repo):
    sample = make_sample(sample_repo, stock=0)

    view = FakeMonitoringView(choices=["2", "0"])
    controller = MonitoringController(order_repo, sample_repo, view)
    controller.run()

    rows = view.stock_status_calls[0]
    assert len(rows) == 1
    row_sample, demand, state = rows[0]
    assert row_sample.sample_id == sample.sample_id
    assert demand == 0
    assert state == "고갈"


def test_stock_status_shortage_when_stock_below_pending_demand(order_repo, sample_repo):
    sample = make_sample(sample_repo, stock=5)
    make_order(order_repo, sample.sample_id, quantity=3, status=OrderStatus.RESERVED)
    make_order(order_repo, sample.sample_id, quantity=4, status=OrderStatus.PRODUCING)

    view = FakeMonitoringView(choices=["2", "0"])
    controller = MonitoringController(order_repo, sample_repo, view)
    controller.run()

    _, demand, state = view.stock_status_calls[0][0]
    assert demand == 7
    assert state == "부족"


def test_stock_status_sufficient_when_stock_covers_demand(order_repo, sample_repo):
    sample = make_sample(sample_repo, stock=10)
    make_order(order_repo, sample.sample_id, quantity=3, status=OrderStatus.RESERVED)

    view = FakeMonitoringView(choices=["2", "0"])
    controller = MonitoringController(order_repo, sample_repo, view)
    controller.run()

    _, demand, state = view.stock_status_calls[0][0]
    assert demand == 3
    assert state == "여유"


def test_stock_status_sufficient_when_no_demand_and_stock_positive(order_repo, sample_repo):
    sample = make_sample(sample_repo, stock=10)

    view = FakeMonitoringView(choices=["2", "0"])
    controller = MonitoringController(order_repo, sample_repo, view)
    controller.run()

    _, demand, state = view.stock_status_calls[0][0]
    assert demand == 0
    assert state == "여유"


def test_confirmed_orders_excluded_from_pending_demand(order_repo, sample_repo):
    sample = make_sample(sample_repo, stock=5)
    make_order(order_repo, sample.sample_id, quantity=1000, status=OrderStatus.CONFIRMED)

    view = FakeMonitoringView(choices=["2", "0"])
    controller = MonitoringController(order_repo, sample_repo, view)
    controller.run()

    _, demand, state = view.stock_status_calls[0][0]
    assert demand == 0
    assert state == "여유"


def test_empty_state_no_samples_and_no_orders(order_repo, sample_repo):
    view = FakeMonitoringView(choices=["1", "2", "0"])
    controller = MonitoringController(order_repo, sample_repo, view)
    controller.run()

    counts = view.order_counts_calls[0]
    assert sum(counts.values()) == 0
    for status in (OrderStatus.RESERVED, OrderStatus.PRODUCING, OrderStatus.CONFIRMED, OrderStatus.RELEASE):
        assert counts[status] == 0

    assert view.stock_status_calls[0] == []


def test_recomputes_between_two_run_calls_on_same_controller_instance(order_repo, sample_repo):
    sample = make_sample(sample_repo, stock=10)

    view1 = FakeMonitoringView(choices=["2", "0"])
    controller = MonitoringController(order_repo, sample_repo, view1)
    controller.run()

    _, demand1, state1 = view1.stock_status_calls[0][0]
    assert demand1 == 0
    assert state1 == "여유"

    make_order(order_repo, sample.sample_id, quantity=50, status=OrderStatus.RESERVED)

    view2 = FakeMonitoringView(choices=["2", "0"])
    controller._view = view2
    controller.run()

    _, demand2, state2 = view2.stock_status_calls[0][0]
    assert demand2 == 50
    assert state2 == "부족"


def test_invalid_choice_shows_error_and_continues(order_repo, sample_repo):
    view = FakeMonitoringView(choices=["9", "0"])
    controller = MonitoringController(order_repo, sample_repo, view)
    controller.run()

    assert len(view.errors) == 1
