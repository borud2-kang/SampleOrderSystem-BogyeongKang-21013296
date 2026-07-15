"""더미 데이터 생성 순수 함수(`generate_sample`/`generate_order`) 단위 테스트.

이 함수들은 저장소에 반영하지 않는 순수 함수이므로 Repository 없이 직접 호출해 값의
유효 범위(수율 0 초과 1 이하, 평균생산시간 양수, 수량 1 이상)와 상태(`RESERVED` 고정)를
검증한다.
"""

import pytest

from app.generator.dummy_data import generate_order, generate_sample
from app.model.order import OrderStatus


def test_generate_sample_produces_values_within_valid_ranges():
    for i in range(200):
        sample = generate_sample(f"S-{i:03d}", i)

        assert sample.sample_id == f"S-{i:03d}"
        assert sample.name.strip() != ""
        assert sample.avg_process_time > 0
        assert 0 < sample.yield_rate <= 1
        assert sample.stock >= 0


def test_generate_sample_name_includes_index_suffix():
    sample = generate_sample("S-001", 7)
    assert "#07" in sample.name


def test_generate_order_produces_values_within_valid_ranges_and_reserved_status():
    for i in range(200):
        order = generate_order(f"ORD-{i:04d}", "S-001")

        assert order.order_id == f"ORD-{i:04d}"
        assert order.sample_id == "S-001"
        assert order.customer_name.strip() != ""
        assert order.quantity >= 1
        assert order.status == OrderStatus.RESERVED


@pytest.mark.parametrize("_", range(50))
def test_generate_order_status_is_always_reserved(_):
    order = generate_order("ORD-0001", "S-001")
    assert order.status == OrderStatus.RESERVED
