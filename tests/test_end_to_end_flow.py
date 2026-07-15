"""전체 플로우 통합 테스트 (Phase 5에서 사람이 손으로 확인했던 시나리오의 자동화 버전).

Controller 간 배선과 데이터 흐름이 전체적으로 맞물려 동작하는지 확인하는 것이 목적이며,
개별 분기/계산 로직의 세세한 엣지 케이스는 각 Phase의 기존 테스트 파일이 담당한다
(`docs/design/phase7.md` "자동화 테스트 정리 > 전체 플로우 통합 테스트" 참고).

흐름: SampleController(등록) -> OrderController(주문 2건) -> ApprovalController(승인,
CONFIRMED/PRODUCING 분기) -> ProductionController(생산 완료) -> ShipmentController(출고).
"""

import pytest

from app.controller.approval_controller import ApprovalController
from app.controller.order_controller import OrderController
from app.controller.production_controller import ProductionController
from app.controller.sample_controller import SampleController
from app.controller.shipment_controller import ShipmentController
from app.model.order import OrderStatus
from app.persistence.order_repository import OrderRepository
from app.persistence.production_queue import ProductionQueue
from app.persistence.sample_repository import SampleRepository


class FakeSampleView:
    def __init__(self, registration=None):
        self._registration = registration
        self.registered = None

    def prompt_registration(self):
        return self._registration

    def show_registered(self, sample):
        self.registered = sample

    def show_duplicate_error(self, sample_id):
        pass

    def show_list(self, samples):
        pass

    def prompt_search_keyword(self):
        return ""

    def show_search_result(self, samples):
        pass

    def show_error(self, message):
        pass


class FakeOrderView:
    def __init__(self, reservation):
        self._reservation = reservation
        self.reserved_order = None
        self.error_message = None

    def prompt_reservation(self, sample_repo):
        return self._reservation

    def show_reserved(self, order):
        self.reserved_order = order

    def show_error(self, message):
        self.error_message = message


class FakeApprovalView:
    def __init__(self, order_ids=None, decisions=None):
        self._order_ids = list(order_ids or [])
        self._decisions = list(decisions or [])
        self.results = []
        self.errors = []

    def show_reserved_list(self, orders, sample_repo):
        pass

    def prompt_order_id(self):
        return self._order_ids.pop(0)

    def prompt_decision(self):
        return self._decisions.pop(0)

    def show_error(self, message):
        self.errors.append(message)

    def show_result(self, order, extra=""):
        self.results.append((order.order_id, order.status, extra))


class FakeProductionView:
    def __init__(self, choices=None):
        self._choices = list(choices or [])
        self.completed = []
        self.errors = []

    def show_menu(self):
        pass

    def prompt_choice(self):
        return self._choices.pop(0)

    def show_error(self, message):
        self.errors.append(message)

    def show_current(self, job):
        pass

    def show_waiting(self, jobs):
        pass

    def show_completed(self, job):
        self.completed.append(job)


class FakeShipmentView:
    def __init__(self, order_ids=None):
        self._order_ids = list(order_ids or [])
        self.results = []
        self.errors = []

    def show_confirmed_list(self, orders, sample_repo):
        pass

    def prompt_order_id(self):
        return self._order_ids.pop(0)

    def show_error(self, message):
        self.errors.append(message)

    def show_result(self, order):
        self.results.append((order.order_id, order.status))


@pytest.fixture
def sample_repo(tmp_path):
    return SampleRepository(str(tmp_path / "samples.json"))


@pytest.fixture
def order_repo(tmp_path):
    return OrderRepository(str(tmp_path / "orders.json"))


@pytest.fixture
def production_queue():
    return ProductionQueue()


def test_full_order_lifecycle_reserved_to_release(sample_repo, order_repo, production_queue):
    # 1. 시료 등록 (재고 0에서 시작).
    sample_view = FakeSampleView(
        registration={"name": "실리콘 웨이퍼-8인치", "avg_process_time": 2.0, "yield_rate": 0.92}
    )
    sample_controller = SampleController(sample_repo, sample_view)
    sample_controller._register()

    sample = sample_view.registered
    assert sample.stock == 0

    # 재고 부족/충분 시나리오를 만들기 위해 등록 직후 재고를 테스트에서 직접 세팅한다
    # (docs/design/phase7.md 시나리오: "하나는 재고를 넉넉하게 세팅해 즉시 CONFIRMED",
    # "하나는 재고 부족으로 PRODUCING").
    sample.stock = 100
    sample_repo.update(sample.sample_id, sample)

    # 2. 주문 두 건 생성.
    order_view_a = FakeOrderView(
        reservation={"sample_id": sample.sample_id, "customer_name": "A사", "quantity": 10}
    )
    OrderController(order_repo, sample_repo, order_view_a).run()
    order_a = order_view_a.reserved_order
    assert order_a.status == OrderStatus.RESERVED

    order_view_b = FakeOrderView(
        reservation={"sample_id": sample.sample_id, "customer_name": "B사", "quantity": 180}
    )
    OrderController(order_repo, sample_repo, order_view_b).run()
    order_b = order_view_b.reserved_order
    assert order_b.status == OrderStatus.RESERVED
    # 부족분 = 180 - (100 - 10 이미 A사 승인 전이므로 아직 100) -> 승인 순서에 따라 달라짐.

    # 3. 두 건 모두 승인 -> A는 재고 충분(100 >= 10)하여 즉시 CONFIRMED,
    #    B는 남은 재고(90) < 180이라 PRODUCING + 생산 큐 등록.
    approval_view = FakeApprovalView(
        order_ids=[order_a.order_id, order_b.order_id], decisions=["Y", "Y"]
    )
    ApprovalController(order_repo, sample_repo, production_queue, approval_view).run()

    saved_a = order_repo.get(order_a.order_id)
    saved_b = order_repo.get(order_b.order_id)
    assert saved_a.status == OrderStatus.CONFIRMED
    assert saved_b.status == OrderStatus.PRODUCING
    assert len(production_queue) == 1

    stock_after_approval = sample_repo.get(sample.sample_id).stock
    assert stock_after_approval == 90  # 100 - 10 (A사분만 차감, B사는 아직 부족분 미반영)

    # 4. 생산 완료 처리 -> PRODUCING 주문이 CONFIRMED로 전환되고 재고 반영.
    production_view = FakeProductionView(choices=["2", "0"])
    ProductionController(production_queue, order_repo, sample_repo, production_view).run()

    saved_b_after_production = order_repo.get(order_b.order_id)
    assert saved_b_after_production.status == OrderStatus.CONFIRMED
    assert len(production_view.completed) == 1
    assert len(production_queue) == 0

    # 부족분 = 180 - 90 = 90, 실 생산량 = ceil(90 / 0.92) = 98
    import math

    expected_actual_qty = math.ceil(round(90 / 0.92, 6))
    expected_stock = 90 + expected_actual_qty - 180
    assert sample_repo.get(sample.sample_id).stock == expected_stock

    # 5. 두 건 모두 출고 처리 -> 둘 다 RELEASE로 전환.
    shipment_view = FakeShipmentView(order_ids=[order_a.order_id, order_b.order_id])
    ShipmentController(order_repo, sample_repo, shipment_view).run()

    assert order_repo.get(order_a.order_id).status == OrderStatus.RELEASE
    assert order_repo.get(order_b.order_id).status == OrderStatus.RELEASE
    assert shipment_view.results == [
        (order_a.order_id, OrderStatus.RELEASE),
        (order_b.order_id, OrderStatus.RELEASE),
    ]
