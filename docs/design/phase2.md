# Phase 2 설계: 시료 주문 (예약)

관련 계획: [`docs/PLAN.md` § Phase 2](../PLAN.md#phase-2--시료-주문-예약)
관련 기능 명세: [`docs/FEATURES/02-order.md`](../FEATURES/02-order.md)

## 목적

Phase 0에서 배선만 끝나 있던 `OrderController`/`OrderView` 스텁을 실제 기능으로 채운다. 이 Phase가
끝나면 등록된 시료를 대상으로 주문(예약)을 생성할 수 있고, 생성된 주문은 항상 `RESERVED` 상태로 저장되며
재시작해도 유지되어야 한다.

Phase 2는 주문 "생성"에만 한정된다. 재고 확인/상태 분기(`CONFIRMED`/`PRODUCING`)는 다음 Phase(승인/거절)의
책임이며, 이 Phase에서는 **재고를 전혀 조회하지 않는다** (FEATURES/02-order.md: "이 시점에서는 재고 확인을
하지 않는다"). 주문 목록 조회 화면도 아직 이 Phase의 범위가 아니다 — PLAN.md Phase 2 확인 포인트는 "재시작
후 주문 데이터가 유지되는지"를 **데이터 파일**로 확인하도록 명시하고 있으며, 이는 조회 메뉴가 아직 없어도
됨을 전제한다.

## 설계 원칙: PoC 패턴 재사용, 단 검증 루프는 Phase 1과 동일하게 강화

`../ConsoleMVC/app/controller/order_controller.py`, `../ConsoleMVC/app/view/order_view.py`를 골격으로
채택하되, 그대로 가져오지 않는다. ConsoleMVC의 원본은:

- 존재하지 않는 시료 ID를 입력하면 오류 메시지만 찍고 **주문 생성 자체를 중단**한다 (재입력을 받지 않음).
- 주문 수량을 `int(input(...))`로 바로 변환해, 숫자가 아닌 값을 입력하면 예외로 프로그램이 죽는다.

반면 FEATURES/02-order.md의 "엣지 케이스 / 검증 규칙"은 "거부하고 **재입력을 요구**한다"고 명시하므로,
Phase 1에서 `SampleView`에 적용한 것과 동일한 원칙(잘못된 값은 같은 항목만 재입력, 프로그램이 죽지 않음)을
`OrderView`에도 적용한다. 즉 **View 계층의 검증/재입력 루프 패턴은 Phase 1에서 확립한 방식을 그대로
승계**하고, Controller의 흐름 구조(입력 → 시료 존재 확인 → 채번 → 저장 → 결과 표시)만 ConsoleMVC에서
채택한다.

## 변경 대상 파일

```
SampleOrderSystem/
  app/
    controller/
      order_controller.py   # 스텁 → 실제 구현 (주문 생성 처리)
    view/
      order_view.py          # 신규: 시료 주문 화면 (입력/출력)
  tests/
    test_order_controller.py # 신규: OrderController 단위 테스트 (stdin 시뮬레이션 없이)
```

`app/model/order.py`(`Order`, `OrderStatus`), `app/persistence/order_repository.py`,
`app/persistence/json_repository.py`(Phase 1에서 롤백/`DuplicateIdError` 개선 완료)는 이미 완성되어
있으므로 이 Phase에서는 수정하지 않는다. 제공 API: `OrderRepository.create(order)`(중복 ID면
`DuplicateIdError`), `next_id()`(`ORD-0001` 형식, Phase 0에서 확정 — FEATURES/02-order.md의 예시
`ORD-20260416-0043`은 참고용 표기일 뿐 이 프로젝트의 정본 형식이 아님, `docs/design/phase0.md` "Persistence
설계" 절 참고). `app/persistence/sample_repository.py`의 `get(sample_id)`를 시료 존재 검증에 사용한다.

## Controller 설계

```python
class OrderController:
    def __init__(self, order_repo: OrderRepository, sample_repo: SampleRepository,
                 view: OrderView) -> None:
        self._order_repo = order_repo
        self._sample_repo = sample_repo
        self._view = view

    def run(self) -> None:
        data = self._view.prompt_reservation(self._sample_repo)
        order = Order(
            order_id=self._order_repo.next_id(),
            sample_id=data["sample_id"],
            customer_name=data["customer_name"],
            quantity=data["quantity"],
            status=OrderStatus.RESERVED,
        )
        self._order_repo.create(order)
        self._view.show_reserved(order)
```

- **생성자 시그니처 변경**: Phase 0의 `MainController`는 `OrderController(order_repo, sample_repo)`로
  View 없이 배선했다. Phase 1에서 `SampleController`에 View를 주입한 것과 동일하게, Phase 2부터는
  `OrderController(order_repo, sample_repo, view)`로 바꾸고 `MainController.__init__`에서
  `OrderView()`를 생성해 주입한다.
- **하위 메뉴가 없는 단일 흐름**: Phase 1(`SampleController`)은 등록/목록/검색 3개 하위 기능이 있어 별도
  메뉴 루프가 필요했지만, Phase 2는 "주문 생성" 단일 기능만 있으므로 `run()`이 메뉴 없이 바로 입력 →
  처리 → 결과 표시 흐름을 수행한다 (FEATURES/02-order.md에 "시료 예약(주문 생성)" 하위 기능이 하나뿐).
  이후 Phase(예: 주문 목록 조회가 필요해지는 시점)에서 하위 메뉴가 필요해지면 그때 `SampleController`와
  같은 구조로 확장한다 — Phase 2에서 미리 빈 메뉴를 만들지 않는다(YAGNI).
- **시료 존재 검증은 View의 재입력 루프에서 처리**: "존재하지 않는 시료 ID 입력 시 주문 생성을 거부하고
  재입력을 요구한다"(FEATURES/02-order.md)를 만족시키려면 시료 ID 입력 시점에 반복적으로 검증해야 한다.
  이 검증 자체(등록 여부 조회)는 Model 계층(`sample_repo.get()`) 호출이지만, "재입력을 요구"하는 것은
  콘솔 입출력 흐름이므로 Phase 1과 동일한 경계 원칙에 따라 **View가 `sample_repo`를 전달받아 존재 검증
  루프를 수행**한다 (`prompt_reservation(self._sample_repo)`처럼 Repository를 View에 넘기는 방식은
  Phase 1엔 없었던 패턴이라 아래 "설계 결정" 절에서 별도로 다룬다).
- **주문 수량 검증(1 이상의 정수)도 View에서** 재입력 루프로 처리한다.
- **Repository 계층 예외 처리**: `order_repo.create(order)`가 이론상 `DuplicateIdError`를 던질 수 있으나,
  주문번호는 `next_id()`로만 채번되므로 Phase 1의 시료 등록과 마찬가지로 정상 흐름에서는 발생하지 않는다.
  Phase 1에서 이미 이 불변식을 저장소 계층이 보장하고 있으므로, Controller에서 추가로 방어적
  `try/except`를 걸지 않는다 (Phase 1과 달리 이번엔 새로 예외를 감쌀 필요가 없다 — Phase 1의
  `except DuplicateIdError`는 사용자에게 "중복 ID"라는 의미 있는 안내가 필요했지만, 여기서는 애초에
  일어날 수 없는 상황을 굳이 방어 코드로 감싸는 것은 과도한 방어이므로 생략한다).

## 설계 결정 (Phase 1과 달라지는 부분)

| 항목 | Phase 1(`SampleController`) | Phase 2(`OrderController`) | 이유 |
| --- | --- | --- | --- |
| 하위 메뉴 구조 | 등록/목록/검색 3개, 루프 필요 | 주문 생성 1개, 루프 불필요 | FEATURES 문서상 하위 기능 개수 차이를 그대로 반영 (YAGNI) |
| 대상 존재 검증 위치 | 해당 없음(시료는 신규 생성 대상이라 존재 검증이 없음) | View가 `SampleRepository`를 참조해 입력 시점에 검증 | "재입력을 요구한다"는 요구사항을 만족하려면 검증과 재입력 루프가 같은 자리에 있어야 하며, Controller가 루프를 대신 돌리게 하면 View가 얇아지는 대신 Controller가 콘솔 대화형 로직을 떠안게 되어 CLAUDE.md의 View/Controller 경계 원칙과 반대로 어긋난다. View에 Repository의 조회 전용 메서드(`get`)만 전달하는 것은 "화면 코드 안에 비즈니스 로직(재고 계산, 상태 전환)을 넣지 않는다"는 원칙에 저촉되지 않는다 — 단순 존재 조회는 상태를 변경하지 않는 조회이며 재입력 루프의 일부이기 때문이다. |
| ID 채번 방식 | Repository에서 자동 채번, 사용자 입력 없음 | 동일 | Phase 0/1의 결정을 그대로 승계 |

## View 설계

```python
class OrderView:
    def prompt_reservation(self, sample_repo: SampleRepository) -> dict:
        sample_id = self._prompt_existing_sample_id(sample_repo)
        customer_name = self._prompt_nonempty("고객명 > ")
        quantity = self._prompt_positive_int("주문 수량 > ")
        return {"sample_id": sample_id, "customer_name": customer_name, "quantity": quantity}

    def show_reserved(self, order: Order) -> None: ...
    def show_error(self, message: str) -> None: ...

    # 내부 헬퍼: 잘못된 형식/미등록 ID면 오류 출력 후 같은 프롬프트 재입력
    def _prompt_existing_sample_id(self, sample_repo: SampleRepository) -> str: ...
    def _prompt_nonempty(self, prompt: str) -> str: ...
    def _prompt_positive_int(self, prompt: str) -> int: ...
```

- `_prompt_existing_sample_id`: 입력받은 ID로 `sample_repo.get(sample_id)`를 조회해 `None`이면 "존재하지
  않는 시료 ID 입니다" 안내 후 재입력, 존재하면 해당 ID를 반환한다.
- `_prompt_positive_int`: `int()` 변환 실패(`ValueError`) 시 "숫자를 입력하세요" 안내 후 재입력, 변환은
  됐지만 0 이하면 "1 이상의 수량을 입력하세요" 안내 후 재입력한다 (FEATURES/02-order.md: "수량 0 또는
  음수, 숫자가 아닌 입력에 대한 검증").
- `_prompt_nonempty`는 Phase 1의 `SampleView._prompt_nonempty`와 동일한 규칙(빈 문자열 재입력)을
  고객명에도 적용한다.
- 동일 고객·동일 시료의 중복 주문은 검증하지 않는다 (FEATURES/02-order.md: "별개 주문으로 각각 처리").

## 에러 처리 정책 (phase0.md/phase1.md 정책 승계)

- 잘못된 형식/미등록 시료 ID/잘못된 수량 입력 → 해당 항목만 재입력받는다. 프로그램이 죽지 않는다.
- 이 Phase에는 하위 메뉴가 없으므로 "잘못된 메뉴 선택" 케이스 자체가 없다. `MainController`의 메인 메뉴
  루프(Phase 0에서 이미 구현됨)가 `2`를 선택하면 `OrderController.run()`을 호출하고, 완료되면 자동으로
  메인 메뉴로 돌아간다.

## 테스트 범위

- `tests/test_order_controller.py` — Controller 로직을 stdin 시뮬레이션 없이 검증한다. `OrderView`를
  간단한 테스트 더블로 대체해 `run()`을 직접 호출하는 방식으로 작성한다 (Phase 1의
  `tests/test_sample_controller.py`와 동일한 패턴). 최소 다음을 검증:
  - 정상 입력 시 `next_id()`로 채번된 주문번호로 `Order`가 생성되고 상태가 `RESERVED`인지, 저장소에
    반영되는지.
  - 동일 시료·동일 고객으로 두 번 주문해도 둘 다 별개 주문으로 저장되는지 (중복 제한 없음 확인).
- `OrderView`의 입력 검증(재입력 루프)은 `pytest` + `monkeypatch`로 `builtins.input`을 시퀀스로 대체해
  검증한다 (Phase 1의 `tests/test_sample_view.py`와 동일한 패턴, `unittest.TestCase` 금지). 최소:
  - 미등록 시료 ID → 재입력 → 등록된 시료 ID 순서로 입력했을 때 최종적으로 올바른 ID가 반환되는지.
  - 수량에 문자열/0/음수 → 재입력 → 올바른 양의 정수 순서로 입력했을 때 최종 값이 반환되는지.
- 기존 `tests/test_json_repository.py`, `tests/test_sample_controller.py`, `tests/test_sample_view.py`
  (Phase 0/1)는 그대로 유지하고 회귀가 없는지 `pytest` 전체 실행으로 확인한다.

## 완료 기준 (`docs/PLAN.md` Phase 2 확인 포인트와 매핑)

| PLAN.md 확인 포인트 | 이 설계에서 보장하는 방법 |
| --- | --- |
| Phase 1에서 등록한 시료로 주문 생성 시 주문번호 발급 + `RESERVED` 상태 | `OrderController.run()` → `order_repo.next_id()` 채번 → `Order(..., status=OrderStatus.RESERVED)` 생성 → `show_reserved()`로 주문번호/상태 출력 |
| 등록되지 않은 시료 ID로 주문 시도 시 거부 | `OrderView._prompt_existing_sample_id`가 `sample_repo.get()`으로 존재 검증, 없으면 재입력 요구 |
| 수량에 0, 음수, 문자열 입력 시 재입력 요구 | `OrderView._prompt_positive_int`의 재입력 루프 |
| 재시작 후 주문 데이터가 유지됨 (조회 메뉴 없이 데이터 파일로 확인) | Phase 0에서 이미 보장된 `JsonRepository`/`OrderRepository`의 영속성을 그대로 재사용 (변경 없음), `data/orders.json`을 직접 열어 확인 |

## 후속 Phase에 넘기는 미결정 사항

- 주문 목록 조회 화면 — PLAN.md Phase 2는 조회 메뉴 없이 데이터 파일로만 확인하도록 명시하므로 이
  Phase에서는 만들지 않는다. `RESERVED` 주문 목록 표시는 Phase 3(승인/거절)에서 그 기능의 일부로 처음
  등장한다 (`docs/FEATURES/03-approval.md` 참고).
- 동일 시료에 대한 다건 주문이 쌓였을 때의 정렬/조회 순서 — Phase 3~4(FIFO 큐)에서 실제로 필요해지는
  시점에 결정한다.
