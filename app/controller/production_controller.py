"""생산 라인 Controller. Phase 0에서는 스텁이며, Phase 4부터 실제 기능을 채운다."""


class ProductionController:
    def __init__(self, production_queue, order_repo, sample_repo) -> None:
        self._production_queue = production_queue
        self._order_repo = order_repo
        self._sample_repo = sample_repo

    def run(self) -> None:
        print("[알림] 생산 라인 조회 기능은 아직 준비되지 않은 기능입니다.")
