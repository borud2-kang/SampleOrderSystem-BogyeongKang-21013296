"""생산 큐 (FIFO). `../ConsoleMVC`의 `ProductionLineRepository` 패턴을 참고했다.

Phase 0에서는 in-memory `deque` 기반으로만 동작하며, 파일 영속화 여부는 Phase 4에서 결정한다.
"""

from collections import deque
from typing import Deque, List, Optional

from app.model.production_job import ProductionJob


class ProductionQueue:
    """단일 생산 라인의 FIFO 대기열을 보관한다."""

    def __init__(self) -> None:
        self._queue: Deque[ProductionJob] = deque()

    def enqueue(self, job: ProductionJob) -> None:
        self._queue.append(job)

    def pop_next(self) -> Optional[ProductionJob]:
        return self._queue.popleft() if self._queue else None

    def peek_current(self) -> Optional[ProductionJob]:
        return self._queue[0] if self._queue else None

    def list_waiting(self) -> List[ProductionJob]:
        return list(self._queue)[1:]

    def list_all(self) -> List[ProductionJob]:
        return list(self._queue)

    def __len__(self) -> int:
        return len(self._queue)
