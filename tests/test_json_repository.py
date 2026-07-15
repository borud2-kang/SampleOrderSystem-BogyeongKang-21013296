import json
from pathlib import Path

import pytest

from app.model.order import Order, OrderStatus
from app.model.sample import Sample
from app.persistence.order_repository import OrderRepository
from app.persistence.sample_repository import SampleRepository


@pytest.fixture
def sample_file_path(tmp_path):
    return str(tmp_path / "samples.json")


@pytest.fixture
def order_file_path(tmp_path):
    return str(tmp_path / "orders.json")


def test_create_and_get(sample_file_path):
    repo = SampleRepository(sample_file_path)
    repo.create(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))

    found = repo.get("S-001")
    assert found is not None
    assert found.name == "실리콘 웨이퍼-8인치"


def test_create_duplicate_raises(sample_file_path):
    repo = SampleRepository(sample_file_path)
    repo.create(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))
    with pytest.raises(ValueError):
        repo.create(Sample("S-001", "중복", 0.1, 0.5, 0))


def test_update(sample_file_path):
    repo = SampleRepository(sample_file_path)
    repo.create(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))
    sample = repo.get("S-001")
    sample.stock = 100
    repo.update("S-001", sample)
    assert repo.get("S-001").stock == 100


def test_update_missing_raises(sample_file_path):
    repo = SampleRepository(sample_file_path)
    with pytest.raises(KeyError):
        repo.update("NOPE", Sample("NOPE", "x", 1, 1, 0))


def test_delete(sample_file_path):
    repo = SampleRepository(sample_file_path)
    repo.create(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))
    repo.delete("S-001")
    assert repo.get("S-001") is None


def test_delete_missing_raises(sample_file_path):
    repo = SampleRepository(sample_file_path)
    with pytest.raises(KeyError):
        repo.delete("NOPE")


def test_search_by_name_via_find(sample_file_path):
    repo = SampleRepository(sample_file_path)
    repo.create(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))
    repo.create(Sample("S-002", "GaN 에피텍셜-4인치", 0.3, 0.78, 220))

    results = repo.find(lambda s: "웨이퍼" in s.name)
    assert len(results) == 1
    assert results[0].sample_id == "S-001"


def test_persistence_across_instances(sample_file_path):
    repo1 = SampleRepository(sample_file_path)
    repo1.create(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))

    # 새 인스턴스를 만들어 "재실행" 상황을 재현한다.
    repo2 = SampleRepository(sample_file_path)
    reloaded = repo2.get("S-001")
    assert reloaded is not None
    assert reloaded.name == "실리콘 웨이퍼-8인치"
    assert reloaded.stock == 480


def test_file_written_as_json(sample_file_path):
    repo = SampleRepository(sample_file_path)
    repo.create(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))
    assert Path(sample_file_path).exists()

    with open(sample_file_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    assert len(raw) == 1
    assert raw[0]["sample_id"] == "S-001"


def test_next_id_no_collision_after_restart_sample(sample_file_path):
    repo1 = SampleRepository(sample_file_path)
    first_id = repo1.next_id()
    repo1.create(Sample(first_id, "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))
    second_id = repo1.next_id()
    repo1.create(Sample(second_id, "GaN 에피텍셜-4인치", 0.3, 0.78, 220))
    assert first_id != second_id

    # 저장소를 새로 열어 "재시작"을 재현한다. 다음 채번은 기존 ID와 겹치지 않아야 한다.
    repo2 = SampleRepository(sample_file_path)
    third_id = repo2.next_id()
    assert third_id not in {first_id, second_id}
    assert third_id not in {s.sample_id for s in repo2.get_all()}

    repo2.create(Sample(third_id, "SiC 잉곳-6인치", 0.4, 0.85, 0))
    assert len(repo2.get_all()) == 3


def test_create_and_status_flow(order_file_path):
    repo = OrderRepository(order_file_path)
    order = Order("ORD-0001", "S-001", "삼성전자 파운드리", 200)
    repo.create(order)

    order.status = OrderStatus.CONFIRMED
    repo.update("ORD-0001", order)

    assert repo.get("ORD-0001").status == OrderStatus.CONFIRMED


def test_find_by_status_via_find(order_file_path):
    repo = OrderRepository(order_file_path)
    repo.create(Order("ORD-0001", "S-001", "고객A", 100, status=OrderStatus.RESERVED))
    repo.create(Order("ORD-0002", "S-002", "고객B", 50, status=OrderStatus.CONFIRMED))

    reserved = repo.find(lambda o: o.status == OrderStatus.RESERVED)
    assert len(reserved) == 1
    assert reserved[0].order_id == "ORD-0001"


def test_create_duplicate_raises_order(order_file_path):
    repo = OrderRepository(order_file_path)
    repo.create(Order("ORD-0001", "S-001", "고객A", 100))
    with pytest.raises(ValueError):
        repo.create(Order("ORD-0001", "S-002", "고객B", 50))


def test_update_missing_raises_order(order_file_path):
    repo = OrderRepository(order_file_path)
    with pytest.raises(KeyError):
        repo.update("NOPE", Order("NOPE", "S-001", "고객A", 100))


def test_delete_missing_raises_order(order_file_path):
    repo = OrderRepository(order_file_path)
    with pytest.raises(KeyError):
        repo.delete("NOPE")


def test_persistence_across_instances_preserves_enum_status(order_file_path):
    repo1 = OrderRepository(order_file_path)
    repo1.create(Order("ORD-0001", "S-001", "고객A", 100, status=OrderStatus.PRODUCING))

    repo2 = OrderRepository(order_file_path)
    reloaded = repo2.get("ORD-0001")
    assert reloaded is not None
    assert reloaded.status == OrderStatus.PRODUCING
    assert isinstance(reloaded.status, OrderStatus)


def test_file_written_as_json_order(order_file_path):
    repo = OrderRepository(order_file_path)
    repo.create(Order("ORD-0001", "S-001", "고객A", 100))
    assert Path(order_file_path).exists()

    with open(order_file_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    assert len(raw) == 1
    assert raw[0]["order_id"] == "ORD-0001"
    assert raw[0]["status"] == "RESERVED"


def test_next_id_no_collision_after_restart_order(order_file_path):
    repo1 = OrderRepository(order_file_path)
    first_id = repo1.next_id()
    repo1.create(Order(first_id, "S-001", "고객A", 100))
    second_id = repo1.next_id()
    repo1.create(Order(second_id, "S-002", "고객B", 50))
    assert first_id != second_id

    repo2 = OrderRepository(order_file_path)
    third_id = repo2.next_id()
    assert third_id not in {first_id, second_id}
    assert third_id not in {o.order_id for o in repo2.get_all()}

    repo2.create(Order(third_id, "S-003", "고객C", 10))
    assert len(repo2.get_all()) == 3
