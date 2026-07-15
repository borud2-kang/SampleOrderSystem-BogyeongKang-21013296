"""Sample(시료) 엔티티 정의."""

from dataclasses import asdict, dataclass


@dataclass
class Sample:
    """반도체 시료 (Sample) 도메인 모델."""

    sample_id: str
    name: str
    avg_process_time: float  # 평균 생산시간 (분/개)
    yield_rate: float        # 수율 (0 초과 1 이하)
    stock: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> "Sample":
        return Sample(
            sample_id=data["sample_id"],
            name=data["name"],
            avg_process_time=data["avg_process_time"],
            yield_rate=data["yield_rate"],
            stock=data.get("stock", 0),
        )
