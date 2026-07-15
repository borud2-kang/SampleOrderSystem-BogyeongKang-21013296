"""모니터링 Controller. Phase 0에서는 스텁이며, Phase 5부터 실제 기능을 채운다."""


class MonitoringController:
    def __init__(self, order_repo, sample_repo) -> None:
        self._order_repo = order_repo
        self._sample_repo = sample_repo

    def run(self) -> None:
        print("[알림] 모니터링 기능은 아직 준비되지 않은 기능입니다.")
