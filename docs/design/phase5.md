# Phase 5 설계: 출고 처리

관련 계획: [`docs/PLAN.md` § Phase 5](../PLAN.md#phase-5--출고-처리)
관련 기능 명세: [`docs/FEATURES/06-shipment.md`](../FEATURES/06-shipment.md)

## 목적

`CONFIRMED` 상태(재고 확보 또는 생산 완료가 끝나 출고 대기 중)인 주문을 선택해 `RELEASE`로 전환한다.
이 기능은 주문 생명주기의 마지막 단계이며, **재고를 다시 조회하거나 차감하지 않는다** —
FEATURES/06-shipment.md: "재고 차감은 주문 승인 또는 생산 완료 시점에 이미 반영되어 있어야 한다."

PLAN.md는 이 Phase를 "하나의 주문이 `RESERVED → (승인) → CONFIRMED/PRODUCING → CONFIRMED → RELEASE`
전체 흐름을 처음부터 끝까지 콘솔에서 수행"할 수 있게 되는 시점으로 명시한다. 즉 이 Phase 자체의 구현
범위는 좁지만(목록 표시 + 상태 전환 하나), **완료 기준은 이 Phase만이 아니라 Phase 1~5 전체 흐름이 손으로
끝까지 재현 가능한지**로 확장된다 (아래 "완료 기준" 절 참고).

## 설계 원칙: ConsoleMVC 패턴 채택 + Phase 3의 반복 루프 구조 재사용

`../ConsoleMVC/app/controller/shipment_controller.py`, `../ConsoleMVC/app/view/shipment_view.py`를
골격으로 채택하되, 두 가지를 이 프로젝트 사정에 맞게 조정한다:

1. **한 번에 여러 건 처리 가능한 루프**로 바꾼다. ConsoleMVC 원본은 `run()`이 한 번 호출될 때 주문 하나만
   처리하고 끝나는 단발성 구조다. 그러나 Phase 3(`ApprovalController`)에서 이미 "목록 표시 → 하나 선택해
   처리 → 갱신된 목록 다시 표시"를 반복하는 루프 구조를 확립했고, 담당자가 한 번에 여러 건의 `CONFIRMED`
   주문을 연달아 출고 처리하는 것이 자연스러운 사용 흐름이므로 같은 구조를 재사용한다.
2. **상태명 오타 수정**: ConsoleMVC 원본은 `order.status = OrderStatus.RELEASED`를 쓰지만, 이 프로젝트의
   `OrderStatus`에는 `RELEASED`가 없다 — `docs/design/phase0.md` "설계 결정" 절에서 이미 `RELEASE`로
   확정했다(`app/model/order.py`도 `RELEASE`). 그대로 옮기면 `AttributeError`가 나므로 `OrderStatus.RELEASE`로
   고쳐서 채택한다.

## 변경 대상 파일

```
SampleOrderSystem/
  app/
    controller/
      shipment_controller.py   # 스텁 → 실제 구현 (CONFIRMED 목록 → 선택 → 출고 처리 루프)
      main_controller.py        # ShipmentView를 생성해 ShipmentController(..., view)로 배선 갱신
    view/
      shipment_view.py          # 신규: 출고 처리 화면 (목록/프롬프트/결과 출력만, 로직 없음)
  tests/
    test_shipment_controller.py # 신규: 출고 분기/거부 로직 단위 테스트 (stdin 시뮬레이션 없이)
```

`app/model/order.py`, `app/persistence/order_repository.py`, `app/persistence/sample_repository.py`는
이미 완성되어 있으므로 수정하지 않는다. 제공 API: `OrderRepository.find(predicate)`, `get(order_id)`,
`update(order_id, order)`; `SampleRepository.get(sample_id)`(시료명 표시용, 아래 참고).

## Controller 설계

```python
class ShipmentController:
    def __init__(self, order_repo, sample_repo, view) -> None:
        self._order_repo = order_repo
        self._sample_repo = sample_repo
        self._view = view

    def run(self) -> None:
        while True:
            confirmed = self._order_repo.find(lambda o: o.status == OrderStatus.CONFIRMED)
            self._view.show_confirmed_list(confirmed, self._sample_repo)
            if not confirmed:
                return

            order_id = self._view.prompt_order_id()
            if order_id == "0":
                return

            order = self._order_repo.get(order_id)
            if order is None or order.status != OrderStatus.CONFIRMED:
                self._view.show_error(f"출고 가능한 주문이 아닙니다: {order_id}")
                continue

            order.status = OrderStatus.RELEASE
            self._order_repo.update(order.order_id, order)
            self._view.show_result(order)
```

- **생성자 시그니처 변경**: Phase 0의 스텁은 `ShipmentController(order_repo, sample_repo)`로 View 없이
  배선됐다. Phase 1~4에서 반복된 패턴과 동일하게 `(order_repo, sample_repo, view)`로 바꾸고
  `MainController.__init__`에서 `ShipmentView()`를 생성해 주입한다.
- **`sample_repo`는 재고 계산이 아니라 목록 표시(시료명 조회)용으로만 사용**한다. FEATURES/06-shipment.md는
  재고를 다시 확인/차감하지 말라고 명시하므로 `Controller`는 `sample_repo.get()`을 오직 View에 전달해
  시료명을 조회하는 용도로만 넘기고, `stock` 필드는 읽지도 쓰지도 않는다.
- **루프 종료 조건**: `CONFIRMED` 목록이 비면(더 출고할 주문이 없으면) 자동으로 메인 메뉴로 돌아가고,
  목록이 남아있어도 사용자가 `0`을 입력하면 뒤로 갈 수 있다 (Phase 3의 `ApprovalController`와 동일한
  규칙).
- **오류 처리 후 루프 유지**: 존재하지 않는 주문번호나 `CONFIRMED`가 아닌 주문번호를 선택해도
  `show_error` 후 최신 목록을 다시 보여주고 계속 진행한다(Phase 3와 동일 원칙 — "잘못된 선택 → 같은
  프롬프트 재입력"이 아니라 "잘못된 선택 → 최신 목록 재조회 후 재선택").
- **재고를 건드리지 않음**: `_order_repo.update()`만 호출하고 `sample_repo.update()`는 호출하지 않는다
  (FEATURES/06 명시 사항 — 재고는 이미 승인/생산완료 시점에 반영 완료).

## View 설계

```python
class ShipmentView:
    def show_confirmed_list(self, orders: list[Order], sample_repo) -> None:
        """CONFIRMED 주문 목록을 표시한다 (주문번호/고객명/시료명/수량/상태). 비어 있으면
        '출고 가능한 주문이 없습니다.' 안내만 하고 끝낸다. 시료명은 `sample_repo.get(order.sample_id)`로
        조회한다 (Phase 3 `ApprovalView.show_reserved_list`와 동일한 패턴)."""

    def prompt_order_id(self) -> str:
        """출고할 주문번호를 입력받는다. `0`이면 뒤로가기. 형식 검증(빈 문자열 등)만 여기서 한다."""

    def show_error(self, message: str) -> None: ...

    def show_result(self, order: Order) -> None:
        """처리 결과(주문번호, 최종 상태)를 표시한다."""
```

- 표시 항목/조회 패턴은 Phase 3의 `ApprovalView.show_reserved_list`와 의도적으로 동일하게 맞춘다 —
  두 화면 모두 "목록에서 하나 골라 상태를 전환"하는 동일한 상호작용 패턴이므로 화면 구성을 통일해
  사용자가 이미 익힌 조작 방식을 그대로 재사용할 수 있게 한다.
- 존재하는 주문인지/`CONFIRMED` 상태인지 검증은 Controller가 담당한다 (Phase 3와 동일한 이유: 목록
  자체가 매 반복마다 바뀌므로 "재입력"이 아니라 "재선택" 흐름이 필요하기 때문).

## 설계 결정

| 항목 | 결정 | 이유 |
| --- | --- | --- |
| 출고 처리 시각 기록 | **이 Phase에서는 구현하지 않는다** | FEATURES/06-shipment.md는 "필수는 아니나 권장"이라고 명시한다. `Order` 모델에 `shipped_at` 같은 필드를 추가하면 Phase 0~4에서 이미 고정된 스키마와 기존 `data/orders.json`(및 관련 테스트 픽스처)에 하위 호환 문제가 생기므로, 필요성이 실제로 제기되는 시점(예: 모니터링/이력 조회 요구가 구체화되는 Phase 6 이후)에 별도로 재검토한다. YAGNI 원칙에 따라 지금은 추가하지 않는다. |
| 재고 갱신 여부 | 하지 않음 | FEATURES/06-shipment.md에 명시적으로 금지("재고를 다시 확인하거나 차감할 필요는 없다"). |
| 상태명 | `OrderStatus.RELEASE` (ConsoleMVC의 `RELEASED`가 아님) | `docs/design/phase0.md`에서 이미 확정, `app/model/order.py`의 실제 Enum 값과 일치시켜야 함(그렇지 않으면 `AttributeError`). |

## 에러 처리 정책 (phase0~4.md 정책 승계)

- 존재하지 않는 주문번호/`CONFIRMED`가 아닌 주문번호 선택 → `show_error` 후 최신 목록으로 재선택, 예외로
  죽지 않는다.
- `CONFIRMED` 목록이 비어 있으면 프롬프트 없이 즉시 메인 메뉴로 돌아간다.

## 테스트 범위

`tests/test_shipment_controller.py`에서 `ShipmentView`를 테스트 더블로 대체해 stdin 시뮬레이션 없이
검증한다 (Phase 1~4의 Controller 테스트와 동일한 패턴). 최소 다음을 검증:

- **정상 출고**: `CONFIRMED` 주문 선택 시 `RELEASE`로 전환되고 저장소에 반영됨.
- **CONFIRMED가 아닌 주문 필터링**: `RESERVED`/`PRODUCING`/`REJECTED`/이미 `RELEASE`된 주문은 목록에
  나타나지 않음.
- **CONFIRMED가 아닌 주문 선택 시도 거부**: 목록에 없는 상태의 주문번호를 직접 선택하면(예: 방어적
  검증이 실제로 동작하는지) 오류 안내 후 상태가 바뀌지 않고 정상 진행됨.
- **존재하지 않는 주문번호**: 오류 안내 후 계속 진행 가능.
- **재고 불변**: 출고 처리 전후로 관련 시료의 `stock` 값이 전혀 변하지 않음 (FEATURES/06 요구사항의 핵심
  회귀 방지 포인트).
- **여러 건 연속 출고**: 두 건 이상의 `CONFIRMED` 주문을 연달아 처리했을 때 모두 정확히 `RELEASE`로
  전환됨.
- 기존 `tests/test_json_repository.py`, `tests/test_sample_*.py`, `tests/test_order_*.py`,
  `tests/test_approval_*.py`, `tests/test_production_controller.py`(Phase 0~4)는 그대로 유지하고
  회귀가 없는지 `pytest` 전체 실행으로 확인한다 (`unittest.TestCase` 금지, pytest 스타일 유지).

## 완료 기준 (`docs/PLAN.md` Phase 5 확인 포인트와 매핑)

| PLAN.md 확인 포인트 | 이 설계에서 보장하는 방법 |
| --- | --- |
| Phase 3/4에서 `CONFIRMED`가 된 주문들이 출고 목록에 모두 나옴 | `run()`의 `order_repo.find(status==CONFIRMED)` |
| 출고 처리 후 해당 주문 상태가 `RELEASE`로 바뀜 | `order.status = OrderStatus.RELEASE` + `order_repo.update()` |
| `CONFIRMED`가 아닌 주문은 출고 목록에 나오지 않음 | `find()`의 상태 필터링 + Controller의 방어적 재검증 |
| **(Phase 5의 최종 확인) 전체 플로우를 한 번 손으로 끝까지 실행** | 시료 등록(Phase 1) → 주문 생성(Phase 2) → 승인(Phase 3, 재고 충분/부족 두 경로 모두) → (재고 부족 경로는) 생산 완료 처리(Phase 4) → 출고(Phase 5)까지 이어지는 시나리오를 이 Phase 구현이 끝난 뒤 verify-tester가 실제 콘솔로 처음부터 끝까지 재현해 확인한다. 이 검증은 코드 변경 사항이 아니라 지금까지 쌓인 모든 Phase의 통합 확인이므로 별도 구현 항목은 없다. |

## 후속 Phase에 넘기는 미결정 사항

- 출고 처리 시각 기록(`shipped_at`) — FEATURES/06가 "권장"으로만 명시했고, 이 시점엔 필요성이 구체화되지
  않았으므로 보류한다. 모니터링(Phase 6)에서 이력 조회 요구가 생기면 그때 `Order` 모델 확장을 재검토한다.
