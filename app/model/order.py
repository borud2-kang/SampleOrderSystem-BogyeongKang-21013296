"""Order(주문) 엔티티 및 상태 정의."""

from dataclasses import dataclass
from enum import Enum


class OrderStatus(str, Enum):
    RESERVED = "RESERVED"      # 주문 접수, 승인 대기 중
    REJECTED = "REJECTED"      # 주문 거절 (모니터링/통계에서 제외)
    PRODUCING = "PRODUCING"    # 승인 완료, 재고 부족으로 생산 중
    CONFIRMED = "CONFIRMED"    # 승인 완료, 출고 대기 중
    RELEASE = "RELEASE"        # 출고 완료


@dataclass
class Order:
    """반도체 시료 주문 (Order) 도메인 모델."""

    order_id: str
    sample_id: str
    customer_name: str
    quantity: int
    status: OrderStatus = OrderStatus.RESERVED

    def to_dict(self) -> dict:
        return {
            "order_id": self.order_id,
            "sample_id": self.sample_id,
            "customer_name": self.customer_name,
            "quantity": self.quantity,
            "status": self.status.value,
        }

    @staticmethod
    def from_dict(data: dict) -> "Order":
        return Order(
            order_id=data["order_id"],
            sample_id=data["sample_id"],
            customer_name=data["customer_name"],
            quantity=data["quantity"],
            status=OrderStatus(data.get("status", OrderStatus.RESERVED.value)),
        )
