"""ProductionJob(생산 작업) 엔티티 정의. 생산 라인의 FIFO 큐에 적재되는 단위.

Phase 0에서는 클래스 정의만 두고, 실제 큐 처리 로직은 Phase 4에서 구현한다.
"""

from dataclasses import dataclass


@dataclass
class ProductionJob:
    order_id: str
    sample_id: str
    shortage_qty: int   # 부족분 (주문량 - 재고)
    actual_qty: int      # 실 생산량 = ceil(부족분 / 수율)
    total_time: float    # 총 생산 시간 = 평균 생산시간 * 실 생산량
