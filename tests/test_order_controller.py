"""OrderController 단위 테스트. OrderView를 테스트 더블로 대체해 stdin 시뮬레이션 없이 검증한다."""

import pytest

from app.controller.order_controller import OrderController
from app.model.order import OrderStatus
from app.persistence.order_repository import OrderRepository
from app.persistence.sample_repository import SampleRepository


class FakeOrderView:
    """OrderView 대신 사용하는 테스트 더블. 미리 지정된 값을 반환하고 호출을 기록한다."""

    def __init__(self, reservation=None):
        self._reservation = reservation
        self.reserved_order = None
        self.error_message = None

    def prompt_reservation(self, sample_repo):
        return self._reservation

    def show_reserved(self, order):
        self.reserved_order = order

    def show_error(self, message):
        self.error_message = message


@pytest.fixture
def order_repo(tmp_path):
    return OrderRepository(str(tmp_path / "orders.json"))


@pytest.fixture
def sample_repo(tmp_path):
    repo = SampleRepository(str(tmp_path / "samples.json"))
    return repo


@pytest.fixture
def registered_sample_id(sample_repo):
    from app.model.sample import Sample

    sample = Sample(
        sample_id=sample_repo.next_id(),
        name="실리콘 웨이퍼-8인치",
        avg_process_time=0.5,
        yield_rate=0.9,
    )
    sample_repo.create(sample)
    return sample.sample_id


def test_run_creates_order_with_next_id_and_reserved_status(
    order_repo, sample_repo, registered_sample_id
):
    view = FakeOrderView(
        reservation={
            "sample_id": registered_sample_id,
            "customer_name": "홍길동",
            "quantity": 10,
        }
    )
    controller = OrderController(order_repo, sample_repo, view)

    controller.run()

    assert view.reserved_order is not None
    assert view.reserved_order.order_id == "ORD-0001"
    assert view.reserved_order.status == OrderStatus.RESERVED

    saved = order_repo.get("ORD-0001")
    assert saved is not None
    assert saved.sample_id == registered_sample_id
    assert saved.customer_name == "홍길동"
    assert saved.quantity == 10
    assert saved.status == OrderStatus.RESERVED


def test_run_twice_same_sample_same_customer_creates_two_separate_orders(
    order_repo, sample_repo, registered_sample_id
):
    view1 = FakeOrderView(
        reservation={
            "sample_id": registered_sample_id,
            "customer_name": "홍길동",
            "quantity": 5,
        }
    )
    controller1 = OrderController(order_repo, sample_repo, view1)
    controller1.run()

    view2 = FakeOrderView(
        reservation={
            "sample_id": registered_sample_id,
            "customer_name": "홍길동",
            "quantity": 5,
        }
    )
    controller2 = OrderController(order_repo, sample_repo, view2)
    controller2.run()

    orders = order_repo.get_all()
    assert len(orders) == 2
    ids = {o.order_id for o in orders}
    assert ids == {"ORD-0001", "ORD-0002"}
    assert all(o.customer_name == "홍길동" for o in orders)
    assert all(o.sample_id == registered_sample_id for o in orders)
    assert all(o.status == OrderStatus.RESERVED for o in orders)
