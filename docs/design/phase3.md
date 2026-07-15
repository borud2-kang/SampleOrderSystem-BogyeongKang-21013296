# Phase 3 설계: 주문 승인/거절 (핵심 분기 로직)

관련 계획: [`docs/PLAN.md` § Phase 3](../PLAN.md#phase-3--주문-승인거절-핵심-분기-로직)
관련 기능 명세: [`docs/FEATURES/03-approval.md`](../FEATURES/03-approval.md),
생산량 계산 산식은 [`docs/FEATURES/05-production-line.md`](../FEATURES/05-production-line.md) "생산량/시간
계산" 절을 그대로 가져온다 (생산 큐 처리/완료 자체는 Phase 4 범위).

## 목적

이 저장소에서 가장 핵심적인 로직 — 승인 시 재고에 따라 `CONFIRMED`/`PRODUCING`으로 자동 분기되는 로직 —
을 구현한다. CLAUDE.md/PRD가 공통으로 강조하듯, 이 분기 로직은 콘솔 입출력과 완전히 분리된 순수 로직으로
작성해 stdin 시뮬레이션 없이 단위 테스트가 가능해야 한다.

PLAN.md는 이 Phase의 범위를 명확히 제한한다: "주문이 `PRODUCING` 큐에 등록되는 것까지만 확인해도 된다 —
실제 생산 진행/완료는 Phase 4." 즉 이 Phase에서 만드는 것은:

- 재고 충분 → 즉시 재고 차감 + `CONFIRMED` 전환 (생산 큐 관여 없음).
- 재고 부족 → 부족분/실 생산량/총 생산시간을 계산해 `ProductionJob`을 생산 큐에 등록 + `PRODUCING` 전환.
  **이 시점엔 재고를 차감하지 않는다** (아래 "설계 결정" 절 참고). 큐에 쌓인 작업을 실제로 처리해서
  `PRODUCING → CONFIRMED`로 완료시키는 것은 Phase 4의 책임이다.
- 거절 → `REJECTED` 전환 (재고/큐 영향 없음).

## 설계 원칙: 이번엔 View가 아니라 Controller가 로직을 갖는다

Phase 1(`SampleController`)과 Phase 2(`OrderController`)에서는 "입력 형식 검증/재입력 루프는 View,
도메인 불변식은 Repository"라는 경계를 세웠다. Phase 3는 이 경계를 유지하되, **핵심 차이가 하나 있다**:
재고 기반 상태 분기, 생산량 계산(`ceil(부족분/수율)`)은 **입력 검증이 아니라 도메인 규칙**이므로 View가
아니라 Controller에 위치해야 한다 (CLAUDE.md 아키텍처 가이드: "승인 분기, 재고 차감, 생산 스케줄링/완료...
상태 머신과 수율/FIFO 계산이 여기에 위치해야 하며, 콘솔 입출력과 분리되어... 단위 테스트가 가능해야
한다"). `../ConsoleMVC/app/controller/approval_controller.py`가 정확히 이 패턴(분기 계산을 Controller가
직접 수행, View는 목록/프롬프트/결과 출력만)을 채택하고 있으므로 그대로 가져온다.

## 변경 대상 파일

```
SampleOrderSystem/
  app/
    controller/
      approval_controller.py   # 스텁 → 실제 구현 (목록 → 선택 → 승인/거절 분기)
      main_controller.py        # ApprovalView를 생성해 ApprovalController(..., view)로 배선 갱신
    view/
      approval_view.py          # 신규: 승인/거절 화면 (목록/프롬프트/결과 출력만, 로직 없음)
  tests/
    test_approval_controller.py # 신규: 분기 로직 단위 테스트 (stdin 시뮬레이션 없이, 이 Phase의 핵심 테스트)
```

Phase 1/2와 동일하게, `ApprovalController`의 생성자가 `(order_repo, sample_repo, production_queue)`
3개 인자에서 `(order_repo, sample_repo, production_queue, view)` 4개 인자로 바뀌므로
`app/controller/main_controller.py`에서 `ApprovalView()`를 생성해 주입하도록 배선을 함께 갱신해야
한다 (`docs/design/phase1.md` "생성자 시그니처 변경", `docs/design/phase2.md` "생성자 시그니처 변경"
절과 동일한 패턴).

`app/model/order.py`, `app/model/sample.py`, `app/model/production_job.py`,
`app/persistence/{json_repository,sample_repository,order_repository,production_queue}.py`는 이미
완성되어 있으므로 이 Phase에서는 수정하지 않는다. 제공 API: `OrderRepository.find(predicate)`,
`get(order_id)`, `update(order_id, order)`; `SampleRepository.get(sample_id)`, `update(sample_id,
sample)`; `ProductionQueue.enqueue(job)`.

## Controller 설계

```python
import math

class ApprovalController:
    def __init__(self, order_repo, sample_repo, production_queue, view) -> None:
        self._order_repo = order_repo
        self._sample_repo = sample_repo
        self._production_queue = production_queue
        self._view = view

    def run(self) -> None:
        while True:
            reserved = self._order_repo.find(lambda o: o.status == OrderStatus.RESERVED)
            self._view.show_reserved_list(reserved, self._sample_repo)
            if not reserved:
                return

            order_id = self._view.prompt_order_id()
            if order_id == "0":
                return

            order = self._order_repo.get(order_id)
            if order is None or order.status != OrderStatus.RESERVED:
                self._view.show_error(f"승인 대기 중인 주문이 아닙니다: {order_id}")
                continue

            decision = self._view.prompt_decision()
            if decision == "N":
                self._reject(order)
            else:
                self._approve(order)

    def _reject(self, order: Order) -> None:
        order.status = OrderStatus.REJECTED
        self._order_repo.update(order.order_id, order)
        self._view.show_result(order)

    def _approve(self, order: Order) -> None:
        sample = self._sample_repo.get(order.sample_id)
        if sample.stock >= order.quantity:
            sample.stock -= order.quantity
            self._sample_repo.update(sample.sample_id, sample)
            order.status = OrderStatus.CONFIRMED
            self._order_repo.update(order.order_id, order)
            self._view.show_result(order, extra="재고 충분, 즉시 출고 대기")
        else:
            shortage = order.quantity - sample.stock
            actual_qty = self._ceil_division(shortage, sample.yield_rate)
            total_time = sample.avg_process_time * actual_qty
            job = ProductionJob(order.order_id, sample.sample_id, shortage, actual_qty, total_time)
            self._production_queue.enqueue(job)
            order.status = OrderStatus.PRODUCING
            self._order_repo.update(order.order_id, order)
            self._view.show_result(
                order, extra=f"재고 부족(부족분 {shortage}), 생산 등록 {actual_qty}ea"
            )

    @staticmethod
    def _ceil_division(shortage: int, yield_rate: float) -> int:
        """`ceil(shortage / yield_rate)`. 부동소수점 오차로 나눠떨어지는 값이 한 단위 더 올림되지
        않도록 소수점을 반올림한 뒤 ceil을 적용한다 (예: 180/0.9는 정확히 200이어야 하며 201이 되면
        안 된다 — FEATURES/05-production-line.md 엣지 케이스)."""
        return math.ceil(round(shortage / yield_rate, 6))
```

- **하위 메뉴 대신 루프**: Phase 2는 하위 기능이 하나뿐이라 메뉴 없이 단일 흐름이었지만, Phase 3는
  "목록 표시 → 하나 선택해 처리 → 다시 목록"을 반복하는 것이 자연스럽다 (FEATURES/03-approval.md 엣지
  케이스: "동시에 여러 RESERVED 주문이... 담당자가 목록에서 선택한 순서대로 재고를 소비한다" — 즉 담당자가
  한 번에 여러 건을 순서대로 처리하는 시나리오를 전제). 그래서 `run()`을 목록이 빌 때까지, 또는 사용자가
  `0`을 입력할 때까지 반복하는 루프로 설계한다. 이는 Phase 1의 `SampleController.run()` 메뉴 루프와
  구조는 다르지만("메뉴 선택"이 아니라 "처리할 주문번호 선택"이 루프의 단위) 같은 원칙(예외 없이 재입력/
  재선택 가능)을 따른다.
- **`sample.stock -= order.quantity`처럼 dataclass를 in-place로 변경한 뒤 `update()`로 명시적으로
  재저장**하는 패턴은 `../ConsoleMVC`의 in-memory 저장소를 그대로 흉내 낸 것이 아니라, 이 프로젝트의
  JSON 파일 기반 저장소(Phase 0)에 맞게 조정한 것이다 — ConsoleMVC는 in-memory dict라 객체를 변경하면
  즉시 반영되지만, 이 프로젝트는 `update()`를 호출해야 `_save()`가 실행되어 파일에 반영된다. 이 부분을
  빠뜨리면 재고/상태 변경이 화면엔 보여도 재시작 후 사라지는, Phase 1에서 겪었던 것과 같은 종류의
  버그가 재발할 수 있으므로 반드시 명시한다.
- **`order_id == "0"`으로 뒤로가기**: 목록이 비어있지 않은데 지금 처리할 주문이 없으면 사용자가 메인
  메뉴로 돌아갈 수 있어야 한다.

## 설계 결정 (재고 차감 시점)

FEATURES/03-approval.md 2-3절은 "재고 전량을 미리 차감할지, 생산 완료 시 차감할지는 구현 선택 사항이지만
이중 차감이 발생하지 않도록 일관된 규칙을 정하고 테스트로 고정해야 한다"고 명시하고, "권장: 생산 완료 후
재고 갱신 및 즉시 소비 처리"라고 권장한다. FEATURES/05-production-line.md의 "생산 완료 처리" 절도 재고
갱신을 생산 완료 시점의 일로 설명한다. 따라서:

| 분기 | 재고 차감 시점 |
| --- | --- |
| 재고 충분 (`CONFIRMED`) | **승인 즉시** 차감 (이 Phase에서 구현) |
| 재고 부족 (`PRODUCING`) | **생산 완료 시점**(Phase 4)에 차감 — 이 Phase에서는 재고를 건드리지 않는다 |

이 규칙에 따라 `_approve()`의 `else` 분기(재고 부족)는 `sample.stock`을 전혀 수정하지 않는다. 이 결정을
Phase 4 설계 시 반드시 승계해야 이중 차감을 피할 수 있다 (Phase 4 설계 문서 작성 시 이 표를 참고할 것).

## View 설계

```python
class ApprovalView:
    def show_reserved_list(self, orders: list[Order], sample_repo) -> None:
        """RESERVED 주문 목록을 표시한다 (주문번호/고객명/시료명/수량/상태). 비어 있으면 안내만
        하고 끝낸다. 시료명은 `sample_repo.get(order.sample_id)`로 조회한다."""

    def prompt_order_id(self) -> str:
        """처리할 주문번호를 입력받는다. `0`이면 뒤로가기."""

    def prompt_decision(self) -> str:
        """[Y] 승인 / [N] 거절. `Y`/`N` 외 입력은 Controller가 아니라 여기서 재입력을 요구한다
        (Phase 1/2와 동일하게 입력 형식 검증은 View의 책임)."""

    def show_error(self, message: str) -> None: ...

    def show_result(self, order: Order, extra: str = "") -> None:
        """처리 결과(주문번호, 최종 상태, 부가 설명)를 표시한다."""
```

- `show_reserved_list`는 FEATURES/03-approval.md가 명시한 표시 항목(주문번호, 고객명, **시료명**, 주문
  수량, 상태)을 그대로 포함한다. 시료명을 보여주려면 View가 `SampleRepository`를 함께 참조해 시료 ID로
  이름을 조회해야 하는데, 이는 Phase 2에서 `OrderView`가 `SampleRepository.get()`으로 존재 검증을 한
  것과 같은 이유로 "표시를 위한 조회"이지 재고 계산·상태 전이 같은 비즈니스 로직이 아니므로 View 계층에서
  허용한다. 따라서 `ApprovalView.show_reserved_list(orders, sample_repo)`처럼 `sample_repo`를 함께
  전달받아 각 주문의 `sample_id`로 이름을 조회해 표시한다.
- `prompt_decision`은 `Y`/`N`(대소문자 무관) 외의 입력이면 재입력을 요구한다 (형식 검증은 View 책임).
- `prompt_order_id`는 형식 검증(빈 문자열 등)만 View에서 하고, "존재하는 주문인지/RESERVED 상태인지"는
  도메인 조회이므로 Controller가 판단한다 (Phase 2에서 시료 ID 존재 검증을 View가 직접 한 것과 다른
  점 — 차이는 아래에서 설명).

### Phase 2와 달라지는 검증 책임 분담

Phase 2의 `OrderView._prompt_existing_sample_id`는 View가 직접 `SampleRepository.get()`으로 존재
검증을 하고 재입력을 받았다. Phase 3는 다르게, **주문번호 존재/상태 검증을 Controller가 담당**하고 실패
시 목록을 다시 보여주며 루프를 이어간다(재입력이 아니라 "다시 선택"으로 처리). 이렇게 나누는 이유:

- Phase 2는 "이 값이 유효할 때까지 같은 프롬프트를 반복"하는 단순 재입력 루프였다.
- Phase 3는 목록 자체가 매 반복마다 바뀔 수 있다(승인/거절 처리 후 `RESERVED` 목록에서 빠짐). 따라서
  "잘못된 주문번호 → 같은 프롬프트 재입력"이 아니라 "잘못된 주문번호 → 최신 목록을 다시 보여주고 재선택"
  구조가 사용자에게 더 유용하다. 이 판단(최신 목록 재조회 필요 여부)은 콘솔 표시 규칙이 아니라 흐름
  제어이므로 Controller의 `run()` 루프에 둔다.

## 테스트 범위 (이 Phase의 핵심 — FEATURES 엣지 케이스를 그대로 테스트 케이스로 옮긴다)

`tests/test_approval_controller.py`에서 `ApprovalView`를 테스트 더블로 대체해 stdin 시뮬레이션 없이
분기 로직만 검증한다 (Phase 1/2의 Controller 테스트와 동일한 패턴). 최소 다음을 검증:

- **재고 충분**(재고 > 주문 수량): 승인 시 즉시 `CONFIRMED`, 재고가 주문 수량만큼 차감되어 저장소에
  반영됨.
- **경계값**(재고 == 주문 수량): "충분"으로 간주해 `CONFIRMED` (부족분 0) — FEATURES 엣지 케이스 명시.
- **재고 부족**(재고 < 주문 수량, 재고 0 포함): 승인 시 `PRODUCING`, `ProductionQueue`에 정확한
  `shortage_qty`/`actual_qty`(`ceil(부족분/수율)`)/`total_time`을 가진 `ProductionJob`이 큐에 들어감,
  **이 시점에 재고는 변경되지 않음**(위 "설계 결정" 표 검증).
  - 수율이 정확히 1인 경우: `actual_qty == shortage_qty`.
  - 부족분/수율이 정수로 나눠떨어지는 경우(`180/0.9=200`)에도 부동소수점 오차로 `201`이 되지 않는지
    (`_ceil_division`의 `round(..., 6)` 보정 검증).
- **거절**: `REJECTED` 전환, 재고/생산 큐 어느 쪽도 변경되지 않음.
- **이미 처리된 주문 재처리 거부**: `CONFIRMED`/`PRODUCING`/`REJECTED`/`RELEASE` 상태의 주문을 다시
  승인/거절하려 하면 오류 안내 후 프로그램이 죽지 않고 목록으로 돌아감 (`order.status != RESERVED`
  검사).
- **존재하지 않는 주문번호**: 오류 안내 후 계속 진행 가능.
- **여러 RESERVED 주문이 같은 시료를 두고 경쟁하는 경우**: 먼저 승인 처리한 주문이 재고를 먼저
  소비하고, 이후 순서로 처리된 주문이 그만큼 줄어든 재고를 기준으로 판단됨 (처리 순서 = 담당자가 선택한
  순서, 별도 우선순위 없음).
- `ApprovalView`의 `Y`/`N` 외 입력 재입력 루프는 `pytest` + `monkeypatch`로 `builtins.input`을 시퀀스로
  대체해 별도로 검증한다 (`tests/test_approval_view.py`, Phase 1/2와 동일한 패턴).
- 기존 `tests/test_json_repository.py`, `tests/test_sample_*.py`, `tests/test_order_*.py`(Phase 0~2)는
  그대로 유지하고 회귀가 없는지 `pytest` 전체 실행으로 확인한다.

## 완료 기준 (`docs/PLAN.md` Phase 3 확인 포인트와 매핑)

| PLAN.md 확인 포인트 | 이 설계에서 보장하는 방법 |
| --- | --- |
| 재고 충분한 시료 주문 → 승인 시 즉시 `CONFIRMED` | `_approve()`의 `if sample.stock >= order.quantity` 분기 |
| 재고 부족한(또는 0인) 시료 주문 → 승인 시 `PRODUCING` | `_approve()`의 `else` 분기, `ProductionQueue.enqueue()` |
| 재고 == 주문 수량 경계값에서 "충분"(`CONFIRMED`) | `>=` 비교(엄격한 `>`가 아님)로 경계값 포함 |
| 거절 시 `REJECTED`, 이미 처리된 주문 재승인/재거절 시 거부 | `_reject()`, `run()`의 `order.status != OrderStatus.RESERVED` 검사 |

## 후속 Phase에 넘기는 미결정 사항

- `ProductionJob`이 큐에 등록된 뒤 실제로 "생산 처리/완료"되어 재고가 갱신되고 `PRODUCING → CONFIRMED`로
  전환되는 로직은 Phase 4 범위. 이 Phase는 큐에 정확한 값으로 등록되는 것까지만 보장한다.
- 생산 라인/대기열 조회 화면(FEATURES/05-production-line.md "하위 기능 (조회)")은 Phase 4에서 만든다.
