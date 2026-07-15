# Phase 7 설계: 마무리 (Dummy 데이터, 테스트, 문서/커밋 정리)

관련 계획: [`docs/PLAN.md` § Phase 7](../PLAN.md#phase-7--마무리-dummy-데이터-테스트-문서커밋-정리)

## 목적

Phase 1~6으로 6개 메인 메뉴 기능은 모두 구현이 끝났다. Phase 7은 **새 기능을 추가하지 않고**, 미션
평가 기준(Harness, Test, CleanCode, Commit 이력)을 충족하도록 다음 네 가지를 다듬는다:

1. Dummy 데이터 생성 기능 통합 (`../DummyDataGenerator` 패턴 참고).
2. 지금까지 손으로 확인한 시나리오를 자동화된 테스트로 보강 — 특히 Phase 5에서 "손으로 끝까지 실행"으로만
   확인했던 전체 플로우(`RESERVED → ... → RELEASE`)를 자동화된 통합 테스트로 옮긴다.
3. README/CLAUDE.md/PRD.md와 실제 구현 사이의 불일치 점검.
4. 커밋 이력 점검 (구현 작업이므로 실제 코드 변경 항목은 아니며, 완료 기준에서 다룬다).

## 설계 원칙: `../DummyDataGenerator` 패턴 채택, 단 상태를 직접 조작하지 않는다

`../DummyDataGenerator`는 독립 PoC로, `Order`를 생성할 때 `RESERVED`/`PRODUCING`/`CONFIRMED`/`RELEASE`/
`REJECTED` 중 하나를 **가중치 랜덤으로 직접 대입**한다(`STATUS_WEIGHTS`). 이 프로젝트는 이 방식을
**그대로 채택하지 않는다** — 이유:

- 이 프로젝트에서 `PRODUCING`/`CONFIRMED`/`RELEASE` 상태에 도달하려면 각각 재고 차감(Phase 3),
  생산 큐 등록/생산 완료(Phase 4), 재고 재차감이 없는 출고 확정(Phase 5) 같은 **부수 효과를 동반한
  상태 전이**가 실제로 일어나야 한다. 상태 필드만 직접 써넣으면 예를 들어 `PRODUCING`인데 생산 큐에
  해당 `ProductionJob`이 없거나(그리고 큐는 in-memory라 재시작하면 어차피 비어 있다 —
  `docs/design/phase4.md` "후속 Phase에 넘기는 미결정 사항" 참고), `CONFIRMED`인데 재고가 이미
  차감됐어야 할 시점에 차감되지 않은 채로 남는 등, **데이터와 재고/큐 상태가 서로 어긋나는 오염된
  더미 데이터**가 만들어진다.
- 따라서 이 프로젝트의 더미 데이터 생성기는 **시료 등록 + `RESERVED` 주문 생성까지만** 담당한다. 그 이후
  상태(`CONFIRMED`/`PRODUCING`/`REJECTED`/`RELEASE`)는 반드시 실제 메뉴(주문 승인/거절, 생산 라인,
  출고 처리)를 통해서만 도달하게 한다 — PLAN.md Phase 7의 목표("매번 손으로 시나리오를 만들지 않아도
  대량의 시료/주문 샘플 데이터를 채울 수 있게 한다")도 "대량의 **초기** 데이터"를 채우는 것이지 "완성된
  전체 생명주기 데이터"를 채우는 것이 아니므로 이 범위 축소는 목표와 상충하지 않는다.
- 다만 이 축소로 인해 대량의 `RESERVED` 주문만 생기면 승인 화면에서 한 건씩 처리해야 하는 부담이 남는다.
  이는 의도된 트레이드오프다 — "실제 상태 전이 로직을 거치지 않은 상태값은 만들지 않는다"는 원칙이
  "한 번에 완성된 데이터를 채운다"는 편의보다 우선한다 (Phase 3~5에서 이미 재고/큐 정합성을 핵심
  요구사항으로 여러 차례 강조했으므로 일관된 판단이다).

### 초기 재고(`stock`)는 예외적으로 0이 아닌 값을 허용한다

Phase 1(`docs/design/phase1.md`)에서 확립한 규칙은 "시료 등록(콘솔 메뉴)을 통하면 재고는 항상 0에서
시작한다"였다. 이 규칙은 **콘솔의 "시료 등록" 상호작용 흐름**에 대한 것이지, 저장소 자체의 불변식이
아니다. 더미 데이터 생성기는 콘솔 메뉴가 아니라 **데이터 시딩(seed) 도구**로서 `SampleRepository`를
직접 다루므로, 이 예외를 명시적으로 허용한다: 더미 시료는 `0` 이상의 무작위 초기 재고를 가질 수 있다.

이렇게 하는 이유는 Phase 5 검증 과정에서 실제로 드러난 문제와 연결된다 — 콘솔 조작만으로는 신규 등록
시료의 재고가 항상 0에서 시작하고 생산 완료 시점의 산식이 정확히 그 주문의 필요량만큼만 채우기 때문에,
"재고가 이미 충분해서 승인 즉시 `CONFIRMED`" 분기(Phase 3의 핵심 로직 중 하나)를 콘솔만으로 재현할
방법이 없었다(당시엔 검증자가 JSON 파일을 직접 편집해 우회함). 더미 데이터 생성기가 초기 재고를
합리적인 값으로 시딩해주면, 이 분기를 포함한 다양한 시나리오를 손으로 직접 파일을 건드리지 않고도
자연스럽게 재현할 수 있게 된다 — 이것이 이 도구의 실질적인 존재 이유다.

## 변경 대상 파일

```
SampleOrderSystem/
  generate_dummy_data.py          # 신규: 더미 데이터 생성 CLI 진입점 (main.py와 같은 위치)
  app/
    generator/
      __init__.py
      dummy_data.py                # 신규: 더미 Sample/Order 레코드를 만드는 순수 함수 (부작용 없음)
      dummy_data_service.py        # 신규: 생성된 레코드를 SampleRepository/OrderRepository에 반영
  tests/
    test_dummy_data.py             # 신규: 생성 함수 자체의 단위 테스트
    test_dummy_data_service.py     # 신규: 서비스가 저장소에 올바르게 반영하는지 테스트
    test_end_to_end_flow.py        # 신규: RESERVED→CONFIRMED/PRODUCING→CONFIRMED→RELEASE 통합 테스트
  README.md                        # 신규
  requirements-dev.txt             # 신규 (pytest)
```

기존 `app/model/*`, `app/persistence/*`, `app/controller/*`, `app/view/*`는 이 Phase에서 기능적으로
수정하지 않는다 (버그 수정이 필요하면 verify-tester가 발견한 항목에 한해 예외적으로 처리).

## 더미 데이터 생성기 설계

### `app/generator/dummy_data.py` — 순수 생성 함수

`../DummyDataGenerator/src/generator/dummy_data.py`의 이름 풀(`SAMPLE_NAME_POOL`, `CUSTOMER_POOL`)을
그대로 재사용하되, 이 프로젝트의 모델(`Sample`, `Order`, `OrderStatus`)에 맞게 조정한다:

```python
import random

from app.model.order import Order, OrderStatus
from app.model.sample import Sample

SAMPLE_NAME_POOL = [...]   # DummyDataGenerator와 동일한 풀 재사용
CUSTOMER_POOL = [...]      # 동일


def generate_sample(sample_id: str, index: int) -> Sample:
    base_name = random.choice(SAMPLE_NAME_POOL)
    return Sample(
        sample_id=sample_id,
        name=f"{base_name} #{index:02d}",
        avg_process_time=round(random.uniform(0.2, 1.5), 2),
        yield_rate=round(random.uniform(0.70, 0.99), 2),
        stock=random.randint(0, 500),   # 예외적으로 0이 아닌 초기 재고 허용 (위 절 참고)
    )


def generate_order(order_id: str, sample_id: str) -> Order:
    return Order(
        order_id=order_id,
        sample_id=sample_id,
        customer_name=random.choice(CUSTOMER_POOL),
        quantity=random.randint(1, 300),
        status=OrderStatus.RESERVED,   # 다른 상태는 절대 직접 대입하지 않는다
    )
```

- ID는 `SampleRepository.next_id()`/`OrderRepository.next_id()`(Phase 0에서 이미 구현된 채번 로직)를
  그대로 사용한다 — `../DummyDataGenerator`처럼 `next_numeric_suffix()`를 별도로 재구현하지 않는다
  (이미 이 프로젝트 저장소가 같은 기능을 제공하므로 중복 구현을 피한다).
- 수율은 `01-sample.md`의 제약(0 초과 1 이하)을 만족하도록 `random.uniform(0.70, 0.99)` 범위로 제한한다
  (0에 너무 가까운 값은 `ceil(부족분/수율)`을 비현실적으로 크게 만들 수 있으므로 데모 목적상 배제).

### `app/generator/dummy_data_service.py` — 저장소 반영 서비스

```python
class DummyDataService:
    def __init__(self, sample_repo: SampleRepository, order_repo: OrderRepository) -> None:
        self._sample_repo = sample_repo
        self._order_repo = order_repo

    def create_samples(self, count: int) -> list[Sample]:
        created = []
        for i in range(count):
            sample = generate_sample(self._sample_repo.next_id(), i)
            self._sample_repo.create(sample)
            created.append(sample)
        return created

    def create_orders(self, count: int) -> list[Order]:
        sample_ids = [s.sample_id for s in self._sample_repo.get_all()]
        if not sample_ids:
            raise ValueError("등록된 시료가 없습니다. 먼저 시료 더미 데이터를 생성하세요.")
        created = []
        for _ in range(count):
            order = generate_order(
                self._order_repo.next_id(), random.choice(sample_ids)
            )
            self._order_repo.create(order)
            created.append(order)
        return created

    def summary(self) -> dict:
        return {
            "sample_count": len(self._sample_repo.get_all()),
            "order_count": len(self._order_repo.get_all()),
        }
```

- `create_samples`/`create_orders`는 각각 `SampleRepository`/`OrderRepository`가 이미 보장하는
  영속성(JSON 즉시 저장)을 그대로 사용한다 — 서비스 계층이 파일 I/O를 직접 다루지 않는다.
- 등록된 시료가 없는 상태에서 주문을 생성하려 하면 `ValueError`로 명확히 안내한다
  (`../DummyDataGenerator`와 동일한 방어 로직).

### `generate_dummy_data.py` — CLI 진입점

`../DummyDataGenerator/main.py`의 `argparse` 기반 비대화형 모드를 채택한다(대화형 메뉴 모드는 이
Phase의 확인 포인트가 "커맨드 실행"이라고 명시하므로 굳이 필요하지 않음 — 최소 구현):

```python
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
```

- `SampleRepository()`/`OrderRepository()`를 인자 없이 생성하므로 기본 경로(`data/samples.json`,
  `data/orders.json`)를 그대로 사용한다 — `main.py`가 다루는 데이터와 동일한 파일이므로, 더미 데이터
  생성 후 곧바로 `python main.py`로 확인할 수 있다.
- `main.py`의 UTF-8 강제 재구성(Phase 1에서 추가된 `_force_utf8_io`)과 같은 이유로, 이 스크립트도
  실행 시작 시 `stdout`을 UTF-8로 재구성한다 (한글 시료명/고객명 출력 시 cp949 콘솔에서 깨지는 문제
  재발 방지 — `../DummyDataGenerator/main.py`도 동일한 패턴을 이미 쓰고 있다).

## 자동화 테스트 정리

### 신규: 더미 데이터 생성기 테스트

- `tests/test_dummy_data.py` — `generate_sample`/`generate_order`가 유효한 범위의 값(수율 0 초과 1
  이하, 수량 1 이상)을 생성하는지, `status`가 항상 `OrderStatus.RESERVED`인지 검증.
- `tests/test_dummy_data_service.py` — `create_samples`/`create_orders`가 실제로 저장소에 반영되는지
  (`tmp_path` 기반 임시 저장소 사용, Phase 0~6과 동일한 pytest 패턴), 시료가 없는 상태에서
  `create_orders` 호출 시 `ValueError`가 나는지, 여러 번 호출해도 ID가 충돌하지 않는지(`next_id()`
  재사용 검증).

### 신규: 전체 플로우 통합 테스트 (Phase 5의 수동 확인을 자동화)

`tests/test_end_to_end_flow.py` — Phase 5에서 사람이 손으로 끝까지 실행해 확인했던 시나리오를 자동화된
pytest로 옮긴다. 각 Controller를 실제 Repository(`tmp_path` 기반)와 테스트 더블 View로 조합해, 아래
흐름을 한 테스트 함수 안에서 순서대로 실행하고 각 단계의 상태/재고를 단언한다:

1. `SampleController`로 시료 등록 (재고 0에서 시작).
2. `OrderController`로 주문 두 건 생성 — 하나는 재고가 넉넉해지도록(시료의 재고를 테스트에서 직접
   세팅), 다른 하나는 재고가 부족하도록.
3. `ApprovalController`로 두 건 모두 승인 — 하나는 즉시 `CONFIRMED`, 다른 하나는 `PRODUCING` +
   `ProductionQueue`에 등록됨을 확인.
4. `ProductionController`로 생산 완료 처리 — `PRODUCING` 주문이 `CONFIRMED`로 전환되고 재고가
   반영됨을 확인.
5. `ShipmentController`로 두 건 모두 출고 처리 — 둘 다 `RELEASE`로 전환됨을 확인.

이 테스트는 Phase 3~5에서 이미 각 Controller 단위로 검증된 로직을 다시 세세히 검증하는 것이 목적이
아니라, **Controller 간 배선과 데이터 흐름이 전체적으로 맞물려 동작하는지**(통합 테스트)를 확인하는
것이 목적이다. 개별 분기/계산 로직의 엣지 케이스는 각 Phase의 기존 테스트 파일이 이미 충분히 담당한다.

### 기존 테스트 회귀 확인

Phase 0~6에서 작성된 87개 pytest가 이 Phase의 변경 이후에도 전부 통과해야 한다.

## README.md 신규 작성

저장소에 README.md가 아직 없다 — PLAN.md Phase 7 확인 포인트("처음 보는 사람이 README만 보고 실행할
수 있는지")를 충족하려면 반드시 추가해야 한다. 최소 포함 내용:

- 프로젝트 한 줄 소개(반도체 시료 생산주문관리 콘솔 애플리케이션).
- 실행 방법: `python main.py` (Windows cp949 콘솔에서도 한글이 깨지지 않도록 내부적으로 UTF-8을
  강제한다는 점 — 별도 플래그 불필요, `_force_utf8_io()`가 이미 처리).
- 테스트 실행 방법: `pip install -r requirements-dev.txt` 후 `pytest`.
- 더미 데이터 생성 방법: `python generate_dummy_data.py --samples 20 --orders 50 --seed 42` 예시.
- 디렉터리 구조 한눈에 보기 (`app/model`, `app/persistence`, `app/controller`, `app/view`).
- `docs/` 하위 문서(PRD/PLAN/FEATURES/design) 안내 — CLAUDE.md의 "문서" 절과 중복 서술하지 않고
  가리키기만 한다.

## `requirements-dev.txt` 신규 작성

이 프로젝트의 런타임 코드는 표준 라이브러리만 사용하므로 런타임 의존성 파일은 필요 없다. 다만 테스트
실행에는 `pytest`가 필요한데(Phase 0 검증 시 verify-tester가 매번 별도로 설치해야 했음), 지금까지
이를 명시한 파일이 없었다. 최소한의 개발 의존성 파일 하나만 추가한다:

```
pytest
```

## 문서 정합성 점검 (구현이 아니라 점검 절차)

`doc-consistency-checker` 에이전트로 CLAUDE.md/`docs/PRD.md`/`docs/FEATURES/*`/`docs/design/*`가 최종
구현(Phase 1~6 전체)과 어긋나는 부분이 없는지 재점검한다. 지금까지 Phase마다 이미 이 점검을 거쳤으므로
큰 불일치는 예상되지 않으나, 다음 두 가지는 특히 다시 확인한다:
- CLAUDE.md "프로젝트 현황" 절이 Phase 6까지 구현 완료된 최신 상태를 반영하는지(Phase 0 때 갱신한 이후
  다시 갱신되지 않았다).
- 새로 추가되는 README.md/`generate_dummy_data.py`/`requirements-dev.txt`가 CLAUDE.md의 "문서"
  절이나 아키텍처 가이드와 상충하지 않는지.

## 완료 기준 (`docs/PLAN.md` Phase 7 확인 포인트와 매핑)

| PLAN.md 확인 포인트 | 이 설계에서 보장하는 방법 |
| --- | --- |
| Dummy 데이터 생성 커맨드 실행 후 시료 관리/모니터링 화면에서 대량 데이터가 정상적으로 보임 | `generate_dummy_data.py --samples N --orders M` 실행 후 `python main.py`의 시료 목록(Phase 1)/모니터링(Phase 6) 화면에서 직접 확인 |
| `pytest` 전부 통과 | 신규 테스트(더미 생성기, E2E 통합) + 기존 87개 전체 실행 |
| README만 보고 실행 가능 | README.md 신규 작성, 진입점/테스트/더미 데이터 커맨드 명시 |

## 후속 사항 (이 프로젝트 범위를 벗어나는 것으로 남겨둠)

- 대화형 더미 데이터 메뉴(`../DummyDataGenerator`의 `run_interactive`처럼)는 만들지 않는다 — 비대화형
  커맨드로 확인 포인트를 충분히 만족하며, 과도한 기능 추가를 피한다(YAGNI).
- 커밋 이력 정리는 이미 Phase 0~6이 각각 "설계 문서 커밋 + 구현 커밋" 단위로 나뉘어 있으므로, 이 Phase는
  기존 이력을 재작성(rebase 등)하지 않고 이 Phase 자체의 변경분만 같은 관례로 커밋한다.
