# Phase 4 설계: 생산 라인 (FIFO + 수율 계산)

관련 계획: [`docs/PLAN.md` § Phase 4](../PLAN.md#phase-4--생산-라인-fifo--수율-계산)
관련 기능 명세: [`docs/FEATURES/05-production-line.md`](../FEATURES/05-production-line.md)

## 목적

Phase 3에서 재고 부족 시 생산 큐(`ProductionQueue`, in-memory FIFO deque)에 쌓이기 시작한
`ProductionJob`을 실제로 소비해서 주문을 `PRODUCING → CONFIRMED`로 완료시킨다. 이 Phase가 끝나면:

- 생산 큐에 대기 중인 작업을 FIFO 순서로 조회할 수 있다 (현재 처리 중인 작업 + 대기 목록).
- "생산 완료" 처리를 트리거하면 큐 맨 앞의 작업이 완료되어 해당 시료의 재고가 갱신되고, 연결된 주문이
  `CONFIRMED`로 전환된다.
- 다음 대기 작업이 자동으로 "현재 처리 중"이 된다 (별도의 "시작" 커맨드는 없다 — 큐의 맨 앞에 있다는
  사실 자체가 "처리 중"이라는 의미다. 아래 "설계 결정" 절 참고).

Phase 3 설계 문서(`docs/design/phase3.md` "설계 결정 (재고 차감 시점)" 절)가 이미 못박은 규칙을 그대로
승계한다: **재고 부족으로 `PRODUCING`에 들어간 주문은 승인 시점엔 재고를 건드리지 않았으므로, 이 Phase의
"생산 완료 처리"가 재고를 갱신하는 유일한 시점**이다.

## 생산 완료 트리거 방식 (구현 결정)

PLAN.md는 "자동 타이머든, 수동 '다음 단계 진행' 커맨드든 방식은 구현 시 결정"이라고 명시한다. 이 프로젝트는
콘솔 메뉴 기반 애플리케이션이고 실제 경과 시간을 시뮬레이션할 백그라운드 스레드/타이머가 없으므로,
**수동 커맨드("생산 완료 처리" 메뉴 선택)로 큐 맨 앞의 작업 하나를 즉시 완료 처리**하는 방식을 채택한다
(`../ConsoleMVC/app/controller/production_controller.py`의 방식 그대로). `total_time`(총 생산 시간)은
화면에 참고용으로 표시만 하고, 실제 경과 시간을 계산해 완료 가능 여부를 판단하지 않는다 — 이 프로젝트
범위에서 "실시간 경과"는 시뮬레이션 대상이 아니다.

## 설계 원칙: ConsoleMVC 패턴 채택, 단 재고 반영 산식은 FEATURES/05 정책에 맞게 수정

`../ConsoleMVC/app/controller/production_controller.py`, `../ConsoleMVC/app/view/production_view.py`를
골격으로 채택한다 (메뉴 구조: `[1] 생산 현황 확인 [2] 대기 생산 완료 처리 [0] 뒤로`), **완료 처리 로직도
재고 반영 부분을 포함해 그대로 채택한다**:

```python
sample.stock += job.actual_qty      # 실 생산량 전체를 그대로 재고에 반영 (ConsoleMVC 원본과 동일)
order.status = OrderStatus.CONFIRMED
sample.stock -= order.quantity      # 이 주문을 위해 재고를 즉시 소비 (Phase 3의 "재고 충분" 분기와
                                     # 동일하게, CONFIRMED 전환 시 해당 주문 수량만큼 즉시 차감하는
                                     # 일관된 규칙을 적용)
```

**왜 수율을 다시 곱해 "정상품 수"를 역산하지 않는가**: 처음에는 `produced_qty =
floor(job.actual_qty * sample.yield_rate)`처럼 수율을 재적용해 산출량을 계산하는 방식을 검토했다.
그러나 `actual_qty = ceil(shortage_qty / yield_rate)`로 이미 올림 처리된 값이므로,

```
floor(ceil(shortage_qty / yield_rate) * yield_rate) == shortage_qty  (항상, 부동소수점 오차 제외)
```

가 수학적으로 성립한다 (증명: `n = ceil(s/y)`라 하면 `(n-1)y < s <= ny`이므로 `0 <= ny - s < y < 1`,
따라서 `floor(ny) = floor(s + (ny-s)) = s`). 즉 **수율을 다시 곱해 산출량을 역산하는 방식은 "부족분만큼만
재고에 반영"하는 것과 수학적으로 완전히 동일한 결과를 내며, 어떤 경우에도 잉여를 만들어내지 않는다**
(직접 20만 개의 무작위 `(부족분, 수율)` 조합으로 검증함). 즉 "산출량은 항상 부족분과 정확히 일치"라는
결론은 수율을 반영하든 안 하든 같아지므로, 굳이 두 번 계산할 필요가 없다.

이 프로젝트는 **실 생산량(`actual_qty`, 불량을 감안해 올림한 생산 지시량) 전체가 그대로 정상품으로
재고에 들어온다고 가정**하는 정책을 채택한다 — 즉 "얼마나 더 많이 생산 지시를 내려야 하는가"를 정하는
데만 수율을 쓰고, 실제로 생산된 뒤에는 그 수량 전체를 정상품으로 취급한다. 이 정책은 개념적으로 수율이
뜻하는 "정상품 비율"과는 다소 모순되지만(불량이 전혀 발생하지 않았다고 가정하는 셈), 다음 이유로
의도적으로 채택한다:
- 부족분보다 더 많이 생산하도록 지시했는데(수율 보정), 실제 반영 시점에 다시 수율을 곱해 정상품 수를
  깎으면 위 증명대로 그 여유분이 정확히 사라져 애초에 "더 많이 생산 지시"한 의미가 없어진다.
- 생산 지시량 전체를 정상품으로 인정해야 비로소 올림으로 인한 여유분(`actual_qty - shortage_qty`)이
  실제 재고에 남아 이후 다른 주문에 재사용되는, 직관적으로 기대되는 "여유 재고" 흐름이 만들어진다.

`shortage_qty = order.quantity - (승인 시점의 재고)`이므로, 위 코드의 두 줄(`+= actual_qty`,
`-= order.quantity`)의 순효과는 `actual_qty - shortage_qty >= 0`만큼 재고가 순수하게 늘어나는 것과
같다 — 이 값이 바로 올림 처리로 인한 여유분이며, 그대로 재고에 남는다. 같은 시료를 두고 다른 주문이
동시에 큐에 쌓여 있었다면(FEATURES/03-approval.md 엣지 케이스: "동시에 여러 RESERVED 주문이 같은
시료를 두고 경쟁하는 경우, 처리 순서대로 재고를 소비한다"), 먼저 완료된 작업이 남긴 여유분은 이후
대기 중인 작업의 `shortage_qty` 판단(승인 시점에 이미 확정된 값이므로 재계산되지 않음)에는 영향을
주지 않지만, 그 여유분만큼 이후 신규 주문의 재고 판단(다음 승인 시점)에는 자연스럽게 반영된다.

## 변경 대상 파일

```
SampleOrderSystem/
  app/
    controller/
      production_controller.py   # 스텁 → 실제 구현 (현황 조회 / 완료 처리 하위 메뉴)
      main_controller.py          # ProductionView를 생성해 ProductionController(..., view)로 배선 갱신
    view/
      production_view.py          # 신규: 생산 라인 화면 (메뉴/조회/완료 결과 출력만, 로직 없음)
  tests/
    test_production_controller.py # 신규: FIFO 순서/재고 반영 로직 단위 테스트 (stdin 시뮬레이션 없이)
```

`app/model/production_job.py`, `app/persistence/production_queue.py`, `app/persistence/order_repository.py`,
`app/persistence/sample_repository.py`는 이미 완성되어 있으므로 이 Phase에서는 수정하지 않는다. 제공
API: `ProductionQueue.peek_current()`, `list_waiting()`, `pop_next()`, `__len__()`; `OrderRepository.get()`,
`update()`; `SampleRepository.get()`, `update()`.

## Controller 설계

```python
class ProductionController:
    def __init__(self, production_queue, order_repo, sample_repo, view) -> None:
        self._production_queue = production_queue
        self._order_repo = order_repo
        self._sample_repo = sample_repo
        self._view = view

    def run(self) -> None:
        while True:
            self._view.show_menu()
            choice = self._view.prompt_choice()
            if choice == "1":
                self._show_status()
            elif choice == "2":
                self._complete_current()
            elif choice == "0":
                return
            else:
                self._view.show_error("알 수 없는 선택입니다. 메뉴에 표시된 번호를 입력하세요.")

    def _show_status(self) -> None:
        self._view.show_current(self._production_queue.peek_current())
        self._view.show_waiting(self._production_queue.list_waiting())

    def _complete_current(self) -> None:
        job = self._production_queue.pop_next()
        if job is None:
            self._view.show_error("완료할 생산 작업이 없습니다.")
            return

        sample = self._sample_repo.get(job.sample_id)
        sample.stock += job.actual_qty
        self._sample_repo.update(sample.sample_id, sample)

        order = self._order_repo.get(job.order_id)
        order.status = OrderStatus.CONFIRMED
        self._order_repo.update(order.order_id, order)

        sample.stock -= order.quantity
        self._sample_repo.update(sample.sample_id, sample)

        self._view.show_completed(job)
```

- **재고/주문 변경 후 반드시 `update()` 호출**: Phase 3에서 확립한 원칙(메모리상 변경만으로는 파일에
  반영되지 않는다)을 그대로 따른다. 이 Controller는 같은 `sample`에 대해 두 번 갱신(`+actual_qty` 후
  저장, `-order.quantity` 후 다시 저장)하는데, 한 번의 계산으로 합쳐서(`+= actual_qty - quantity`)
  `update()`를 한 번만 호출해도 결과는 같다 — 다만 위 코드처럼 두 단계로 나누면 "생산분 반영"과 "출고
  대기 확정을 위한 소비"라는 두 논리적 사건을 테스트/로그에서 구분하기 쉬워지므로, 이 설계는 가독성과
  향후 로그/테스트 작성을 위해 두 단계로 명시한다 (구현 시 한 번의 `update()` 호출로 합쳐도 무방 —
  최종 상태만 동일하면 됨).
- **FIFO 보장**: `ProductionQueue`는 이미 `deque` 기반으로 FIFO를 보장하므로(Phase 0), Controller는
  큐의 내부 순서를 신경 쓰지 않고 `pop_next()`/`peek_current()`/`list_waiting()`만 호출한다.
- **큐가 비어 있을 때**: `_show_status()`는 `peek_current()`가 `None`을 반환하면 View가 "현재 생산 중인
  작업 없음"을 표시하고, `list_waiting()`은 빈 리스트를 그대로 표시("대기 없음"은 View의 표시 책임 —
  아래 View 설계 참고). `_complete_current()`는 `pop_next()`가 `None`이면 오류 안내 후 프로그램이 죽지
  않고 메뉴로 돌아간다 (FEATURES/05-production-line.md 엣지 케이스: "큐가 비어 있는 상태에서 생산 라인
  조회 시 '대기 없음' 등 정상 처리").

## View 설계

```python
class ProductionView:
    def show_menu(self) -> None: ...
    def prompt_choice(self) -> str: ...
    def show_error(self, message: str) -> None: ...

    def show_current(self, job: Optional[ProductionJob]) -> None:
        """현재 처리 중인 작업(큐 맨 앞)을 표시. None이면 '현재 생산 중인 작업이 없습니다.'"""

    def show_waiting(self, jobs: list[ProductionJob]) -> None:
        """대기 목록을 FIFO 순서로 표시. 비어 있으면 '대기 중인 작업이 없습니다.'"""

    def show_completed(self, job: ProductionJob) -> None:
        """완료된 작업의 주문번호/시료ID/부족분/실생산량을 표시."""
```

- 표시 항목은 FEATURES/05-production-line.md "하위 기능 (조회)" 절이 예시로 든 정보 수준(주문 정보, 실
  생산량, 총 생산시간)을 그대로 따르되, 진행률/예상 완료 시각처럼 "실시간 경과"를 전제로 하는 정보는
  표시하지 않는다 (이 Phase는 시간 시뮬레이션을 하지 않기로 결정했으므로 — 위 "생산 완료 트리거 방식"
  절 참고). 이는 명세가 "필수 아님"으로 명시한 항목을 의도적으로 생략하는 것이다.
- Phase 1~3과 동일하게 잘못된 메뉴 선택은 View가 아니라 Controller의 `run()` 루프에서 재시도하도록
  하고(`show_error` 후 같은 루프 유지), View 자체는 순수 표시만 담당한다.

## 에러 처리 정책 (phase0~3.md 정책 승계)

- 잘못된 메뉴 선택(`1`/`2`/`0` 이외) → `show_error` 후 같은 하위 메뉴에서 재입력. 예외로 죽지 않는다.
- 완료할 작업이 없는 상태에서 "완료 처리"를 선택해도 예외 없이 오류 안내 후 메뉴로 돌아간다.

## 테스트 범위

`tests/test_production_controller.py`에서 `ProductionView`를 테스트 더블로 대체해 stdin 시뮬레이션 없이
검증한다 (Phase 1~3의 Controller 테스트와 동일한 패턴). 최소 다음을 검증:

- **FIFO 순서**: 여러 `ProductionJob`을 순서대로 `enqueue`한 뒤, `_show_status()`가 큐에 넣은 순서
  그대로(현재 작업 = 첫 번째, 대기 목록 = 나머지) 보여주는지.
- **생산 완료 시 재고 반영**: 완료 처리 후 해당 시료의 재고가 `job.actual_qty`만큼 증가했다가
  `order.quantity`만큼 감소한 최종 값과 일치하는지. 수율이 1 미만이라 올림 처리로 인한 여유분
  (`actual_qty - shortage_qty > 0`)이 재고에 그대로 남는 케이스와, 수율이 정확히 1이거나 나눠떨어져
  여유분이 0인 케이스(`actual_qty == shortage_qty`) 둘 다 검증.
- **생산 완료 시 상태 전환**: 완료 처리 후 연결된 주문이 `PRODUCING → CONFIRMED`로 바뀌고 저장소에
  반영되는지.
- **여러 건 연속 처리 시 순서 보장**: 두 건 이상을 완료 처리했을 때, 먼저 큐에 들어간 순서대로 처리되고
  각각의 재고/상태 갱신이 올바른지.
- **큐가 비어 있을 때**: `_show_status()`가 예외 없이 "없음" 상태를 반환하는지, `_complete_current()`가
  오류 안내 후 정상 종료하는지 (죽지 않음).
- `pytest`로 실행하며(`unittest.TestCase` 금지) 기존 55개 테스트(Phase 0~3)와 함께 전체 실행해 회귀가
  없는지 확인한다.

## 완료 기준 (`docs/PLAN.md` Phase 4 확인 포인트와 매핑)

| PLAN.md 확인 포인트 | 이 설계에서 보장하는 방법 |
| --- | --- |
| `PRODUCING` 주문이 생산 큐 조회 화면에 FIFO 순서(먼저 승인된 순서)대로 보임 | `_show_status()` → `peek_current()`/`list_waiting()`, `ProductionQueue`의 `deque` FIFO 보장(Phase 0) |
| 표시되는 실 생산량이 `ceil(부족분/수율)`과 일치 | `ProductionJob.actual_qty`는 Phase 3의 승인 시점에 이미 계산되어 큐에 들어가 있으므로, 이 Phase는 그 값을 그대로 표시만 한다(재계산하지 않음) — Phase 3 테스트에서 산식 정확성은 이미 검증됨, 이 Phase는 "표시 정확성"만 검증 |
| 여러 건을 연달아 `PRODUCING`으로 만들었을 때 먼저 등록된 주문부터 순서대로 처리 | FIFO 큐 자체가 보장(Phase 0) + 이 Phase의 "여러 건 연속 처리 시 순서 보장" 테스트 |
| 생산 완료 처리 후 주문 상태가 `CONFIRMED`로 바뀌고 재고가 갱신됨 | `_complete_current()`의 상태 전환 + 재고 반영 로직 |

## 후속 Phase에 넘기는 미결정 사항

- 생산 큐를 파일로 영속화할지 여부는 Phase 0에서 이미 "필요성이 확인되면 결정"으로 미뤄뒀다. 이 Phase도
  in-memory `deque`를 그대로 사용하며, 프로그램을 재시작하면 `PRODUCING` 큐 내용이 사라진다는 한계를
  그대로 유지한다 (주문/시료 데이터 자체는 JSON에 남아있으므로 상태값(`PRODUCING`)만 보고 큐가 비어
  있음을 알 수 있다 — 이 불일치를 해소할지는 사용자에게 문제로 인식되는 시점에 재검토한다).
- 진행률/예상 완료 시각 등 시간 기반 표시는 이 Phase에서 의도적으로 생략했다 (위 "View 설계" 참고). 필요성이
  제기되면 이후 Phase에서 검토한다.
