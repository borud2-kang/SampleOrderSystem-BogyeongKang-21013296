"""DummyDataService 단위 테스트. `tmp_path` 기반 임시 SampleRepository/OrderRepository를 사용해
create_samples/create_orders가 실제로 저장소에 반영되는지, 시료가 없는 상태에서 주문 생성을
시도하면 ValueError가 나는지, 여러 번 나눠 호출해도 ID가 충돌하지 않는지 검증한다."""

import pytest

from app.generator.dummy_data_service import DummyDataService
from app.model.order import OrderStatus
from app.persistence.order_repository import OrderRepository
from app.persistence.sample_repository import SampleRepository


@pytest.fixture
def sample_repo(tmp_path):
    return SampleRepository(str(tmp_path / "samples.json"))


@pytest.fixture
def order_repo(tmp_path):
    return OrderRepository(str(tmp_path / "orders.json"))


@pytest.fixture
def service(sample_repo, order_repo):
    return DummyDataService(sample_repo, order_repo)


def test_create_samples_persists_to_repository(service, sample_repo):
    created = service.create_samples(5)

    assert len(created) == 5
    saved = sample_repo.get_all()
    assert len(saved) == 5
    ids = {s.sample_id for s in saved}
    assert ids == {s.sample_id for s in created}


def test_create_orders_persists_to_repository(service, sample_repo, order_repo):
    service.create_samples(3)
    created = service.create_orders(10)

    assert len(created) == 10
    saved = order_repo.get_all()
    assert len(saved) == 10
    assert all(o.status == OrderStatus.RESERVED for o in saved)

    valid_sample_ids = {s.sample_id for s in sample_repo.get_all()}
    assert all(o.sample_id in valid_sample_ids for o in saved)


def test_create_orders_without_samples_raises_value_error(service):
    with pytest.raises(ValueError):
        service.create_orders(1)


def test_create_orders_without_samples_does_not_persist_partial_data(service, order_repo):
    with pytest.raises(ValueError):
        service.create_orders(5)

    assert order_repo.get_all() == []


def test_create_samples_called_multiple_times_does_not_collide_ids(service, sample_repo):
    first_batch = service.create_samples(3)
    second_batch = service.create_samples(3)

    all_ids = [s.sample_id for s in first_batch + second_batch]
    assert len(all_ids) == len(set(all_ids))
    assert len(sample_repo.get_all()) == 6


def test_create_orders_called_multiple_times_does_not_collide_ids(service, order_repo):
    service.create_samples(2)
    first_batch = service.create_orders(4)
    second_batch = service.create_orders(4)

    all_ids = [o.order_id for o in first_batch + second_batch]
    assert len(all_ids) == len(set(all_ids))
    assert len(order_repo.get_all()) == 8


def test_summary_reports_counts(service):
    service.create_samples(4)
    service.create_orders(6)

    summary = service.summary()
    assert summary == {"sample_count": 4, "order_count": 6}


def test_create_samples_zero_count_creates_nothing(service, sample_repo):
    created = service.create_samples(0)
    assert created == []
    assert sample_repo.get_all() == []
