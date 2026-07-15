"""더미 시료/주문 데이터 생성 CLI.

`main.py`와 같은 저장소 루트에 위치하는 비대화형 진입점이다. 등록된 시료가
없는 상태에서 승인/거절, 생산, 모니터링 등 여러 메뉴를 확인하려면 매번 손으로
시료/주문을 등록해야 하는 부담이 있었는데, 이 커맨드로 대량의 초기 데이터를
빠르게 채울 수 있다.

주의: 이 도구가 만드는 주문은 항상 `RESERVED` 상태다. `CONFIRMED`/`PRODUCING`/
`RELEASE`/`REJECTED` 상태는 반드시 `python main.py`의 실제 메뉴(주문 승인/거절,
생산 라인, 출고 처리)를 통해서만 도달해야 한다 (`docs/design/phase7.md` 참고).
"""

import argparse
import random
import sys

from app.generator.dummy_data_service import DummyDataService
from app.persistence.order_repository import OrderRepository
from app.persistence.sample_repository import SampleRepository


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SampleOrderSystem 더미 데이터 생성 도구")
    parser.add_argument("--samples", type=int, default=0, help="생성할 시료 개수")
    parser.add_argument("--orders", type=int, default=0, help="생성할 주문 개수 (RESERVED로 생성)")
    parser.add_argument("--seed", type=int, default=None, help="재현 가능한 결과를 위한 랜덤 시드")
    return parser.parse_args()


def main() -> None:
    # Windows 콘솔(cp949 등)에서도 한글 시료명/고객명이 깨지지 않도록, 어떤
    # 출력도 하기 전에 가장 먼저 UTF-8로 강제 재구성한다 (`main.py`의
    # `_force_utf8_io`와 같은 이유).
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")

    args = parse_args()
    if args.seed is not None:
        random.seed(args.seed)

    service = DummyDataService(SampleRepository(), OrderRepository())
    if args.samples:
        created = service.create_samples(args.samples)
        print(f"시료 더미 데이터 {len(created)}건 생성 완료.")
    if args.orders:
        created = service.create_orders(args.orders)
        print(f"주문 더미 데이터 {len(created)}건 생성 완료(RESERVED).")

    summary = service.summary()
    print(f"현재 데이터 현황 -> 시료 {summary['sample_count']}건, 주문 {summary['order_count']}건")


if __name__ == "__main__":
    main()
