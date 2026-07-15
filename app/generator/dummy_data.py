"""더미 Sample/Order 레코드를 만드는 순수 함수.

부작용이 없으며(저장소에 반영하지 않음), 반환값을 어떻게 사용할지는 호출자
(`DummyDataService`)가 결정한다. ID 채번은 각 Repository의 `next_id()`를
그대로 사용하므로 이 모듈은 ID 생성 로직을 갖지 않는다.
"""

import random

from app.model.order import Order, OrderStatus
from app.model.sample import Sample

# `../DummyDataGenerator/src/generator/dummy_data.py`의 이름 풀을 그대로 재사용한다.
SAMPLE_NAME_POOL = [
    "실리콘 웨이퍼-8인치",
    "실리콘 웨이퍼-12인치",
    "GaN 에피택셜-4인치",
    "SiC 파워기판-6인치",
    "포토레지스트-PR7",
    "산화막 웨이퍼-SiO2",
    "질화막 웨이퍼-Si3N4",
    "게르마늄 기판-4인치",
    "사파이어 기판-6인치",
    "인듐인 웨이퍼-InP",
]

CUSTOMER_POOL = [
    "삼성전자 파운드리",
    "SK하이닉스",
    "LG이노텍",
    "DB하이텍",
    "한국나노기술원",
    "서울대 반도체연구실",
    "카이스트 소재연구실",
    "팹리스코리아",
    "퀀텀세미컨덕터",
    "그린실리콘랩",
]


def generate_sample(sample_id: str, index: int) -> Sample:
    """더미 시료 1건을 생성한다.

    초기 재고(`stock`)는 예외적으로 0이 아닌 무작위 값을 허용한다 — 콘솔의
    "시료 등록" 메뉴는 항상 재고 0에서 시작하지만, 이 함수는 데이터 시딩(seed)
    도구 전용이므로 다양한 재고 시나리오(여유/부족/고갈, 승인 즉시 CONFIRMED
    분기 등)를 재현할 수 있도록 초기 재고를 직접 채운다
    (`docs/design/phase7.md` 참고).
    """
    base_name = random.choice(SAMPLE_NAME_POOL)
    return Sample(
        sample_id=sample_id,
        name=f"{base_name} #{index:02d}",
        avg_process_time=round(random.uniform(0.2, 1.5), 2),
        yield_rate=round(random.uniform(0.70, 0.99), 2),
        stock=random.randint(0, 500),
    )


def generate_order(order_id: str, sample_id: str) -> Order:
    """더미 주문 1건을 생성한다. 상태는 항상 `OrderStatus.RESERVED`다.

    `PRODUCING`/`CONFIRMED`/`RELEASE`/`REJECTED` 등 다른 상태는 재고 차감,
    생산 큐 등록/완료, 출고 확정 같은 실제 부수 효과를 동반한 상태 전이를
    거쳐야만 도달할 수 있다. 이 함수가 상태를 직접 대입해버리면 데이터와
    재고/생산 큐 상태가 어긋나는 오염된 더미 데이터가 만들어지므로, 이후
    상태 전이는 반드시 실제 메뉴(주문 승인/거절, 생산 라인, 출고 처리)를
    통해서만 이루어지게 한다 (`docs/design/phase7.md` 참고).
    """
    return Order(
        order_id=order_id,
        sample_id=sample_id,
        customer_name=random.choice(CUSTOMER_POOL),
        quantity=random.randint(1, 300),
        status=OrderStatus.RESERVED,
    )
