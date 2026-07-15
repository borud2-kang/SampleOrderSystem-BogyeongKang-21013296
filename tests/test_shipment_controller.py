"""ShipmentController 단위 테스트. ShipmentView를 테스트 더블로 대체해 stdin 시뮬레이션 없이
CONFIRMED -> RELEASE 전환 로직만 검증한다."""

import pytest

from app.controller.shipment_controller import ShipmentController
from app.model.order import Order, OrderStatus
from app.model.sample import Sample
from app.persistence.order_repository import OrderRepository
from app.persistence.sample_repository import SampleRepository


class FakeShipmentView:
    """ShipmentView 대신 사용하는 테스트 더블.

    order_ids: 순서대로 prompt_order_id()가 반환할 값들의 리스트.
    """

    def __init__(self, order_ids=None):
        self._order_ids = list(order_ids or [])
        self.shown_lists = []
        self.errors = []
        self.results = []

    def show_confirmed_list(self, orders, sample_repo):
        self.shown_lists.append(list(orders))

    def prompt_order_id(self):
        return self._order_ids.pop(0)

    def show_error(self, message):
        self.errors.append(message)

    def show_result(self, order):
        self.results.append((order.order_id, order.status))


@pytest.fixture
def order_repo(tmp_path):
    return OrderRepository(str(tmp_path / "orders.json"))


@pytest.fixture
def sample_repo(tmp_path):
    return SampleRepository(str(tmp_path / "samples.json"))


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


def make_order(order_repo, *, sample_id, customer_name="홍길동", quantity, status=OrderStatus.CONFIRMED):
    order = Order(
        order_id=order_repo.next_id(),
        sample_id=sample_id,
        customer_name=customer_name,
        quantity=quantity,
        status=status,
    )
    order_repo.create(order)
    return order


def test_confirmed_order_transitions_to_release_and_is_persisted(order_repo, sample_repo):
    sample = make_sample(sample_repo, stock=40)
    order = make_order(order_repo, sample_id=sample.sample_id, quantity=10)

    view = FakeShipmentView(order_ids=[order.order_id])
    controller = ShipmentController(order_repo, sample_repo, view)

    controller.run()

    saved_order = order_repo.get(order.order_id)
    assert saved_order.status == OrderStatus.RELEASE
    assert view.results == [(order.order_id, OrderStatus.RELEASE)]


@pytest.mark.parametrize(
    "status",
    [
        OrderStatus.RESERVED,
        OrderStatus.PRODUCING,
        OrderStatus.REJECTED,
        OrderStatus.RELEASE,
    ],
)
def test_non_confirmed_orders_are_excluded_from_list(order_repo, sample_repo, status):
    sample = make_sample(sample_repo, stock=40)
    other_order = make_order(order_repo, sample_id=sample.sample_id, quantity=10, status=status)

    view = FakeShipmentView()
    controller = ShipmentController(order_repo, sample_repo, view)

    controller.run()

    assert view.shown_lists == [[]]
    saved_order = order_repo.get(other_order.order_id)
    assert saved_order.status == status


@pytest.mark.parametrize(
    "status",
    [
        OrderStatus.RESERVED,
        OrderStatus.PRODUCING,
        OrderStatus.REJECTED,
        OrderStatus.RELEASE,
    ],
)
def test_selecting_non_confirmed_order_directly_shows_error_and_continues(
    order_repo, sample_repo, status
):
    sample = make_sample(sample_repo, stock=40)
    non_confirmed_order = make_order(
        order_repo, sample_id=sample.sample_id, quantity=10, status=status
    )
    # CONFIRMED 목록이 비면 controller가 프롬프트 없이 즉시 종료되므로, 실제로 프롬프트가
    # 뜨는 상황을 만들기 위해 CONFIRMED 주문을 하나 더 둔다.
    still_confirmed = make_order(order_repo, sample_id=sample.sample_id, quantity=5)

    view = FakeShipmentView(order_ids=[non_confirmed_order.order_id, "0"])
    controller = ShipmentController(order_repo, sample_repo, view)

    controller.run()

    assert len(view.errors) == 1
    assert non_confirmed_order.order_id in view.errors[0]

    saved_non_confirmed = order_repo.get(non_confirmed_order.order_id)
    assert saved_non_confirmed.status == status

    saved_still_confirmed = order_repo.get(still_confirmed.order_id)
    assert saved_still_confirmed.status == OrderStatus.CONFIRMED

    assert view.results == []


def test_nonexistent_order_id_shows_error_and_allows_continuing(order_repo, sample_repo):
    sample = make_sample(sample_repo, stock=40)
    real_order = make_order(order_repo, sample_id=sample.sample_id, quantity=10)

    view = FakeShipmentView(order_ids=["ORD-9999", real_order.order_id])
    controller = ShipmentController(order_repo, sample_repo, view)

    controller.run()

    assert len(view.errors) == 1
    assert "ORD-9999" in view.errors[0]

    saved_order = order_repo.get(real_order.order_id)
    assert saved_order.status == OrderStatus.RELEASE


def test_stock_is_never_touched_by_shipment(order_repo, sample_repo):
    sample = make_sample(sample_repo, stock=40)
    order = make_order(order_repo, sample_id=sample.sample_id, quantity=10)

    view = FakeShipmentView(order_ids=[order.order_id])
    controller = ShipmentController(order_repo, sample_repo, view)

    controller.run()

    saved_sample = sample_repo.get(sample.sample_id)
    assert saved_sample.stock == 40  # unchanged


def test_multiple_confirmed_orders_are_all_released_in_sequence(order_repo, sample_repo):
    sample = make_sample(sample_repo, stock=100)
    order_a = make_order(order_repo, sample_id=sample.sample_id, customer_name="A사", quantity=10)
    order_b = make_order(order_repo, sample_id=sample.sample_id, customer_name="B사", quantity=20)
    order_c = make_order(order_repo, sample_id=sample.sample_id, customer_name="C사", quantity=30)

    view = FakeShipmentView(order_ids=[order_a.order_id, order_b.order_id, order_c.order_id])
    controller = ShipmentController(order_repo, sample_repo, view)

    controller.run()

    for order in (order_a, order_b, order_c):
        saved = order_repo.get(order.order_id)
        assert saved.status == OrderStatus.RELEASE

    assert view.results == [
        (order_a.order_id, OrderStatus.RELEASE),
        (order_b.order_id, OrderStatus.RELEASE),
        (order_c.order_id, OrderStatus.RELEASE),
    ]

    saved_sample = sample_repo.get(sample.sample_id)
    assert saved_sample.stock == 100  # unchanged


def test_empty_confirmed_list_returns_immediately_without_prompting(order_repo, sample_repo):
    view = FakeShipmentView()
    controller = ShipmentController(order_repo, sample_repo, view)

    controller.run()

    assert view.shown_lists == [[]]
    assert view.results == []


def test_back_to_menu_with_zero_stops_loop_without_processing(order_repo, sample_repo):
    sample = make_sample(sample_repo, stock=40)
    order = make_order(order_repo, sample_id=sample.sample_id, quantity=10)

    view = FakeShipmentView(order_ids=["0"])
    controller = ShipmentController(order_repo, sample_repo, view)

    controller.run()

    saved_order = order_repo.get(order.order_id)
    assert saved_order.status == OrderStatus.CONFIRMED
    assert view.results == []
