"""주문 승인/거절 Controller. Phase 0에서는 스텁이며, Phase 3부터 실제 기능을 채운다."""


class ApprovalController:
    def __init__(self, order_repo, sample_repo, production_queue) -> None:
        self._order_repo = order_repo
        self._sample_repo = sample_repo
        self._production_queue = production_queue

    def run(self) -> None:
        print("[알림] 주문 승인/거절 기능은 아직 준비되지 않은 기능입니다.")
