"""Order 전용 JSON 리포지토리. `data/orders.json`을 기본 저장 경로로 사용한다."""

import re

from app.model.order import Order
from app.persistence.json_repository import JsonRepository

DEFAULT_PATH = "data/orders.json"

_ID_PATTERN = re.compile(r"^ORD-(\d+)$")


class OrderRepository(JsonRepository[Order]):
    def __init__(self, file_path: str = DEFAULT_PATH) -> None:
        super().__init__(
            file_path=file_path,
            to_dict=lambda order: order.to_dict(),
            from_dict=Order.from_dict,
            id_field="order_id",
        )
        # 저장된 데이터 중 최댓값 + 1로 시퀀스를 복원한다 (재시작 후 ID 충돌 방지).
        self._seq = self._max_existing_seq()

    def _max_existing_seq(self) -> int:
        max_seq = 0
        for order in self._data.values():
            match = _ID_PATTERN.match(order.order_id)
            if match:
                max_seq = max(max_seq, int(match.group(1)))
        return max_seq

    def next_id(self) -> str:
        self._seq += 1
        return f"ORD-{self._seq:04d}"
