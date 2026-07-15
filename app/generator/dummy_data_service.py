"""생성된 더미 레코드를 `SampleRepository`/`OrderRepository`에 반영하는 서비스."""

import random
from typing import List

from app.generator.dummy_data import generate_order, generate_sample
from app.model.order import Order
from app.model.sample import Sample
from app.persistence.order_repository import OrderRepository
from app.persistence.sample_repository import SampleRepository


class DummyDataService:
    """더미 데이터 생성 결과를 실제 저장소에 반영한다.

    저장소가 이미 보장하는 영속성(JSON 즉시 저장)을 그대로 사용하므로, 이
    서비스 계층은 파일 I/O를 직접 다루지 않는다.
    """

    def __init__(self, sample_repo: SampleRepository, order_repo: OrderRepository) -> None:
        self._sample_repo = sample_repo
        self._order_repo = order_repo

    def create_samples(self, count: int) -> List[Sample]:
        created: List[Sample] = []
        for i in range(count):
            sample = generate_sample(self._sample_repo.next_id(), i)
            self._sample_repo.create(sample)
            created.append(sample)
        return created

    def create_orders(self, count: int) -> List[Order]:
        sample_ids = [sample.sample_id for sample in self._sample_repo.get_all()]
        if not sample_ids:
            raise ValueError("등록된 시료가 없습니다. 먼저 시료 더미 데이터를 생성하세요.")
        created: List[Order] = []
        for _ in range(count):
            order = generate_order(self._order_repo.next_id(), random.choice(sample_ids))
            self._order_repo.create(order)
            created.append(order)
        return created

    def summary(self) -> dict:
        return {
            "sample_count": len(self._sample_repo.get_all()),
            "order_count": len(self._order_repo.get_all()),
        }
