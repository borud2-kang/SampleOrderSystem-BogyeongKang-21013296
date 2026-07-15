# Phase 0 설계: 뼈대 (MVC 스켈레톤 + 영속성 + 메인 메뉴)

관련 계획: [`docs/PLAN.md` § Phase 0](../PLAN.md#phase-0--뼈대-mvc-스켈레톤--영속성--메인-메뉴)

## 목적

Phase 0의 목표는 **기능이 거의 없어도 되지만, 이후 모든 Phase가 얹힐 구조와 데이터 파이프라인이 실제로
동작해야 한다**는 것이다. 이 문서는 그 구조를 구체적인 클래스/파일 단위로 설계한다.

## 설계 원칙: 두 PoC의 결합

이 프로젝트는 미션1 PoC 2종에서 이미 검증된 패턴을 그대로 가져와 결합하는 것으로 Phase 0을 구성한다
(`CLAUDE.md`의 "문서" 섹션 참고). 새로 발명하는 부분을 최소화한다.

- **MVC 계층 분리 및 메뉴 루프** → `../ConsoleMVC` 그대로 채택.
- **JSON 파일 기반 영속성 + CRUD** → `../DataPersistence` 그대로 채택.

두 PoC는 서로 독립적으로 만들어졌기 때문에 결합 시 아래 "설계 결정" 절에서 다루는 몇 가지 차이를 조정해야
한다.

## 디렉터리 구조

```
SampleOrderSystem/
  main.py                        # 진입점: MainController().run()
  app/
    model/
      __init__.py
      sample.py                  # Sample dataclass (+ to_dict/from_dict)
      order.py                   # Order dataclass, OrderStatus 상수/Enum
      production_job.py          # ProductionJob dataclass (Phase 4에서 본격 사용, Phase 0엔 정의만)
    persistence/
      __init__.py
      json_repository.py         # 제네릭 JSON CRUD 리포지토리 (DataPersistence 패턴)
      sample_repository.py       # JsonRepository[Sample], data/samples.json
      order_repository.py        # JsonRepository[Order], data/orders.json
      production_queue.py        # 생산 큐 (FIFO deque, 메모리 — 영속성은 Phase 4에서 결정)
    controller/
      __init__.py
      main_controller.py         # 메뉴 루프, 요약 정보 계산, 하위 컨트롤러 위임
      sample_controller.py       # Phase 0엔 스텁("준비 중")
      order_controller.py        # Phase 0엔 스텁
      approval_controller.py     # Phase 0엔 스텁
      monitoring_controller.py   # Phase 0엔 스텁
      production_controller.py   # Phase 0엔 스텁
      shipment_controller.py     # Phase 0엔 스텁
    view/
      __init__.py
      main_view.py                # 메인 메뉴 출력/입력
      (하위 view들은 Phase 1부터 채움)
  data/
    .gitkeep                     # samples.json/orders.json은 실행 시 자동 생성, 커밋하지 않음
  tests/
    __init__.py
    test_json_repository.py      # Phase 0 범위의 유일한 자동 테스트
```

`app/`, `data/`, `tests/`는 이 저장소 루트 기준이며, `../ConsoleMVC/app`, `../DataPersistence/src`처럼
저장소마다 다르게 부르던 최상위 패키지명은 이 프로젝트에서 `app`으로 통일한다 (ConsoleMVC와 동일하게;
DataPersistence의 `src`보다 `app`이 Controller/View까지 포함하는 이 구조의 성격을 더 잘 드러낸다).

## Model 설계

### `Sample`

```python
@dataclass
class Sample:
    sample_id: str
    name: str
    avg_process_time: float   # 평균 생산시간
    yield_rate: float          # 수율 (0 초과 1 이하)
    stock: int = 0

    def to_dict(self) -> dict: ...
    @staticmethod
    def from_dict(data: dict) -> "Sample": ...
```

`DataPersistence/src/models/sample.py`를 그대로 채택 (필드명 동일).

### `Order` / `OrderStatus`

```python
class OrderStatus(str, Enum):
    RESERVED = "RESERVED"
    REJECTED = "REJECTED"
    PRODUCING = "PRODUCING"
    CONFIRMED = "CONFIRMED"
    RELEASE = "RELEASE"

@dataclass
class Order:
    order_id: str
    sample_id: str
    customer_name: str
    quantity: int
    status: OrderStatus = OrderStatus.RESERVED

    def to_dict(self) -> dict: ...   # status는 .value(str)로 직렬화
    @staticmethod
    def from_dict(data: dict) -> "Order": ...  # status는 OrderStatus(data["status"])로 역직렬화
```

`str, Enum`을 상속해 JSON 직렬화 시 `.value`가 곧 일반 문자열이 되고, `==` 비교도 문자열과 자연스럽게
동작한다 (`ConsoleMVC`의 `OrderStatus`와 동일한 방식).

### `ProductionJob`

`ConsoleMVC/app/model/production_job.py`를 그대로 채택. Phase 0에서는 클래스 정의만 두고, 실제로
사용하는 큐 로직은 Phase 4에서 구현한다.

## 설계 결정 (두 PoC를 합치며 조정한 부분)

| 항목 | ConsoleMVC | DataPersistence | 이 프로젝트의 결정 |
| --- | --- | --- | --- |
| 출고 완료 상태명 | `RELEASED` | `RELEASE` | **`RELEASE`를 채택**. PDF 명세(8쪽 상태표, 23쪽 예시 UI)와 `docs/PRD.md`/`docs/FEATURES/06-shipment.md`가 모두 `RELEASE`를 사용하므로 이를 정본으로 따른다. `ConsoleMVC`의 `RELEASED`는 PoC 단계의 표기 차이로 간주하고 이 프로젝트엔 반영하지 않는다. |
| Order 필드명 | `customer_name` | `customer` | **`customer_name`을 채택** (`docs/FEATURES/02-order.md`의 "고객명"과 의미가 더 명확히 대응). |
| status 타입 | `OrderStatus` Enum | 순수 `str` | **Enum(`str, Enum`) 채택** — 상태 오타를 타입 체크로 방지하면서 JSON에는 문자열로 그대로 저장되어 두 방식의 장점을 모두 취한다. |
| 최상위 패키지명 | `app` | `src` | **`app` 채택** (위 디렉터리 구조 절 참고). |
| 저장소(Repository) 구현 | in-memory dict | JSON 파일 (`JsonRepository[T]` 제네릭) | **JSON 파일 방식 채택** — Phase 0의 핵심 요구사항인 "재시작해도 데이터 유지"를 위해 `DataPersistence`의 `JsonRepository`를 그대로 가져온다. |
| 생산 큐 저장 방식 | in-memory `deque` | (해당 PoC 범위 아님) | Phase 0에서는 **in-memory `deque` 유지** (`ConsoleMVC`의 `ProductionLineRepository` 참고). 생산 큐까지 파일 영속화할지는 Phase 4에서 필요성을 보고 결정한다 — Phase 0에서 미리 정하지 않는다. |

## Persistence 설계

`../DataPersistence/src/persistence/json_repository.py`의 `JsonRepository[T]` 제네릭 클래스를 그대로
가져온다 (`create`/`get`/`get_all`/`find`/`update`/`delete`/`exists`, 파일이 없으면 빈 상태로 시작, 매
변경마다 즉시 저장, `.tmp` 파일에 쓴 뒤 `replace`로 원자적 교체).

`SampleRepository`, `OrderRepository`는 각각 `data/samples.json`, `data/orders.json`을 기본 경로로 하는
`JsonRepository` 서브클래스로 만든다 (`DataPersistence`와 동일한 패턴). `Order.status`가 Enum이므로
`to_dict`에서 `status.value`로 변환하고 `from_dict`에서 `OrderStatus(data["status"])`로 복원하는 부분만
`DataPersistence` 원본과 다르게 처리한다.

시료 ID(`S-001` 형식)와 주문번호(`ORD-0001` 형식) 채번은 `ConsoleMVC`의 `next_id()` 방식을 참고하되,
JSON 저장소 재시작 후에도 채번이 겹치지 않도록 **저장된 데이터 중 최댓값 + 1**로 시퀀스를 복원하는 로직을
`SampleRepository`/`OrderRepository`에 추가한다 (`ConsoleMVC`는 in-memory라 이 문제가 없었지만, 파일
기반에서는 재시작 후 시퀀스가 0으로 리셋되면 ID 충돌이 발생하므로 Phase 0에서 반드시 처리해야 한다).

## Controller / View 설계 (Phase 0 범위)

`MainController`는 `ConsoleMVC/app/controller/main_controller.py`를 그대로 채택하되, 저장소를
`JsonRepository` 기반으로 교체한다:

```python
class MainController:
    def __init__(self) -> None:
        self._sample_repo = SampleRepository()   # data/samples.json
        self._order_repo = OrderRepository()      # data/orders.json
        self._production_queue = ProductionQueue()  # in-memory

        self._view = MainView()
        # 하위 컨트롤러는 Phase 0에서는 스텁 구현을 주입
        ...

    def run(self) -> None:
        while True:
            self._view.show_menu(self._summary())
            choice = self._view.prompt_choice()
            # 1~6, 0 분기. 그 외 입력은 show_error 후 재입력.
```

- **요약 정보(`_summary`)**: 등록 시료 수, 총 재고, 전체 주문 수, 생산 대기 건수. Phase 0 시점엔 데이터가
  없을 수 있으므로 0으로 정상 표시되어야 한다.
- **하위 컨트롤러 스텁**: Phase 0에서는 `SampleController`, `OrderController` 등 6개 하위 컨트롤러를
  파일만 만들고, `run()`이 "아직 준비되지 않은 기능입니다" 메시지만 출력하고 메인 메뉴로 돌아가게 한다.
  이렇게 하면 Phase 1부터는 각 컨트롤러의 `run()` 내부만 채우면 되고, `MainController`의 배선(wiring)은
  Phase 0에서 이미 끝나 있다.
- **View**: `MainView`는 `ConsoleMVC/app/view/main_view.py`를 그대로 채택 (`show_menu`,
  `prompt_choice`, `show_message`, `show_error`, `pause`).

## 에러 처리 정책

- 메뉴에서 정의되지 않은 입력(숫자가 아니거나 범위 밖) → `show_error` 후 같은 메뉴에서 재입력. 예외로
  프로그램이 죽어서는 안 된다.
- `Ctrl+C`(`KeyboardInterrupt`) 입력 시 스택트레이스를 그대로 노출하지 않고 정상 종료 메시지를 출력하고
  종료한다 — `main.py`에서 최상위로 한 번만 처리.
- JSON 파일이 손상되었거나 읽을 수 없는 경우의 복구 정책은 Phase 0 범위 밖으로 두고, 발생 시 있는 그대로
  예외를 노출한다 (조용히 데이터를 날리지 않는 것이 우선).

## Phase 0 테스트 범위

- `tests/test_json_repository.py` — `DataPersistence/tests/test_json_repository.py`를 이식하되,
  `Order` 생성자 인자명(`customer_name`)과 `status`가 `OrderStatus` Enum이 되는 부분만 이 프로젝트의
  모델에 맞게 조정한다. 최소한 다음을 검증한다:
  - 생성 후 조회, 중복 ID 생성 시 에러.
  - 수정(update) 후 재조회 시 값이 반영됨.
  - 존재하지 않는 ID 수정/삭제 시 에러.
  - **인스턴스를 새로 만들어(재시작 재현) 데이터가 유지되는지** — Phase 0의 "데이터 영속성" 요구사항을
    검증하는 가장 중요한 테스트.
  - 파일이 실제로 JSON으로 저장되는지.
- 채번(`next_id`) 로직에 대한 테스트를 추가한다: 데이터를 저장한 뒤 저장소를 새로 열었을 때 다음 채번이
  기존 ID와 충돌하지 않는지 확인 (`test_persistence_across_instances`류 테스트에 이어서 검증).
- Controller/View는 아직 스텁이므로 이 Phase에서 자동 테스트 대상이 아니다 — `docs/PLAN.md` Phase 0의
  확인 포인트는 사람이 직접 콘솔로 확인한다.

## 완료 기준 (`docs/PLAN.md` Phase 0 확인 포인트와 매핑)

| PLAN.md 확인 포인트 | 이 설계에서 보장하는 방법 |
| --- | --- |
| 메인 메뉴가 뜬다 | `MainController.run()` 첫 루프에서 `MainView.show_menu()` 호출 |
| 잘못된 번호 입력에도 죽지 않는다 | 분기 `else` 절에서 `show_error` 후 루프 계속 |
| 재실행해도 에러 없이 뜬다 | `JsonRepository._load()`가 파일이 없으면 빈 상태로 시작 |
| `data/` 하위에 저장 파일이 생성/유지된다 | `JsonRepository.__init__`에서 부모 디렉터리 생성, `_save()`가 매 변경마다 파일에 기록 |

## 후속 Phase에 넘기는 미결정 사항

- 생산 큐(`ProductionQueue`)를 파일로 영속화할지 여부 — Phase 4에서 FIFO 큐를 실제로 채우기 시작할 때
  결정한다.
- `ProductionJob`의 필드가 실제로 이 값 그대로 충분한지 — Phase 4 설계 시 재검토.
- 하위 컨트롤러 스텁의 정확한 안내 문구/형태 — Phase 1부터 실제 기능으로 대체되므로 Phase 0에서는
  최소한으로만 정한다.
