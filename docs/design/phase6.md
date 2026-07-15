# Phase 6 설계: 모니터링

관련 계획: [`docs/PLAN.md` § Phase 6](../PLAN.md#phase-6--모니터링)
관련 기능 명세: [`docs/FEATURES/04-monitoring.md`](../FEATURES/04-monitoring.md)

## 목적

Phase 1~5에서 쌓인 시료/주문 데이터를 요약해서 보여주는 **조회 전용** 화면 두 개를 완성한다: 상태별 주문
건수(REJECTED 제외), 시료별 재고 현황 + 파생 상태(여유/부족/고갈). 이 Phase는 데이터를 전혀 변경하지
않는다 — FEATURES/04-monitoring.md: "데이터를 변경하지 않는다."

## 설계 원칙: ConsoleMVC 패턴 채택, 재고 회계 모델과 어긋나는 부분만 조정

`../ConsoleMVC/app/controller/monitoring_controller.py`, `../ConsoleMVC/app/view/monitoring_view.py`를
골격으로 채택한다. `../DataMonitor`(sibling PoC, 실시간 자동 갱신·잔여율(%) 바 그래프 포함)도 참고했으나,
이 Phase에서는 **채택하지 않는다** — 이유는 아래 "후속 Phase에 넘기는 미결정 사항" 절 참고.

## 변경 대상 파일

```
SampleOrderSystem/
  app/
    controller/
      monitoring_controller.py   # 스텁 → 실제 구현 (주문량 확인 / 재고량 확인 하위 메뉴)
      main_controller.py          # MonitoringView를 생성해 MonitoringController(..., view)로 배선 갱신
    view/
      monitoring_view.py          # 신규: 모니터링 화면 (조회 결과 출력만, 로직 없음)
  tests/
    test_monitoring_controller.py # 신규: 집계/파생 상태 로직 단위 테스트 (stdin 시뮬레이션 없이)
```

`app/model/order.py`, `app/model/sample.py`, `app/persistence/order_repository.py`,
`app/persistence/sample_repository.py`는 이미 완성되어 있으므로 수정하지 않는다. 제공 API:
`OrderRepository.find(predicate)`, `get_all()`; `SampleRepository.get_all()`.

## Controller 설계

```python
_MONITORED_STATUSES = [
    OrderStatus.RESERVED,
    OrderStatus.PRODUCING,
    OrderStatus.CONFIRMED,
    OrderStatus.RELEASE,
]


class MonitoringController:
    def __init__(self, order_repo, sample_repo, view) -> None:
        self._order_repo = order_repo
        self._sample_repo = sample_repo
        self._view = view

    def run(self) -> None:
        while True:
            self._view.show_menu()
            choice = self._view.prompt_choice()
            if choice == "1":
                self._show_order_counts()
            elif choice == "2":
                self._show_stock_status()
            elif choice == "0":
                return
            else:
                self._view.show_error("알 수 없는 선택입니다. 메뉴에 표시된 번호를 입력하세요.")

    def _show_order_counts(self) -> None:
        counts = {
            status: len(self._order_repo.find(lambda o, s=status: o.status == s))
            for status in _MONITORED_STATUSES
        }
        self._view.show_order_counts(counts)

    def _show_stock_status(self) -> None:
        pending_demand = {}
        for status in (OrderStatus.RESERVED, OrderStatus.PRODUCING):
            for order in self._order_repo.find(lambda o, s=status: o.status == s):
                pending_demand[order.sample_id] = (
                    pending_demand.get(order.sample_id, 0) + order.quantity
                )

        rows = []
        for sample in self._sample_repo.get_all():
            demand = pending_demand.get(sample.sample_id, 0)
            if sample.stock == 0:
                state = "고갈"
            elif sample.stock < demand:
                state = "부족"
            else:
                state = "여유"
            rows.append((sample, demand, state))
        self._view.show_stock_status(rows)
```

- **REJECTED 제외**: `_MONITORED_STATUSES`에 `REJECTED`를 아예 포함하지 않으므로, 상태별 건수·합계
  어디에도 `REJECTED` 주문이 집계되지 않는다(FEATURES/04-monitoring.md: "총 주문 수를 표시할 때도
  REJECTED는 포함하지 않는다"). 합계는 View가 `counts` 딕셔너리 값의 합으로 계산한다(아래 View 설계
  참고) — Controller가 별도 합계 필드를 만들지 않고, `_MONITORED_STATUSES`에 대해서만 집계했다는 사실
  자체가 REJECTED 제외를 보장한다.
- **매 조회 시점에 재계산**: `_show_order_counts()`/`_show_stock_status()` 모두 호출될 때마다
  `order_repo`/`sample_repo`에서 새로 읽어 집계하며, 어떤 값도 캐시하지 않는다 (FEATURES/04-monitoring.md
  엣지 케이스: "캐시된 값 사용 금지").

## 설계 결정: "미결 주문 수요"의 범위 (RESERVED + PRODUCING만, CONFIRMED는 제외)

FEATURES/04-monitoring.md는 "미결(RESERVED/PRODUCING 등 아직 출고되지 않은) 주문 수요"라고 표현해 정확한
상태 집합을 못박지는 않는다. `../DataMonitor` PoC는 `RESERVED`/`PRODUCING`/`CONFIRMED` 세 상태를 모두
"미결 수요"에 포함시키지만, 이 프로젝트는 `../ConsoleMVC`와 동일하게 **`RESERVED`/`PRODUCING`만** 포함하고
`CONFIRMED`는 제외한다. 이유:

- `docs/design/phase3.md`("설계 결정 (재고 차감 시점)")에 따라, 이 프로젝트는 **재고 충분 분기(즉시
  `CONFIRMED`)에서 승인 즉시 재고를 차감**하고, **재고 부족 분기(`PRODUCING`)는 생산 완료 시점(Phase 4)에
  재고를 반영**한다. 즉 어떤 경로로 `CONFIRMED`에 도달했든, `CONFIRMED` 상태가 된 시점엔 **이미 그 주문의
  수요가 현재 재고 값에 반영되어 끝난 상태**다.
- 따라서 `CONFIRMED` 주문의 수량을 "미결 수요"에 다시 더하면, 이미 차감을 마친 수요를 중복으로 재고
  부족 판정에 반영하는 셈이 되어 실제로는 출고만 남은 주문 때문에 "부족"으로 잘못 표시될 수 있다.
  `RESERVED`(아직 승인 여부도 결정되지 않음)와 `PRODUCING`(승인은 됐지만 재고가 아직 반영 안 됨)만이
  "현재 재고 값에 아직 반영되지 않은 진짜 수요"다.
- `../DataMonitor`가 `CONFIRMED`까지 포함한 것은 그 PoC 자체의 회계 모델(승인/생산 완료 시 재고 반영
  시점 정책)이 이 프로젝트와 다를 수 있기 때문으로 추정되며, 이 프로젝트의 Phase 3/4 결정과는 맞지
  않으므로 그대로 가져오지 않는다.

## View 설계

```python
class MonitoringView:
    def show_menu(self) -> None: ...
    def prompt_choice(self) -> str: ...
    def show_error(self, message: str) -> None: ...

    def show_order_counts(self, counts: dict) -> None:
        """상태별 건수 + 합계(REJECTED 제외)를 표시한다. counts가 비어 있을 리는 없다(고정된 4개
        상태 키를 항상 받음) — 다만 값이 전부 0이어도(주문이 하나도 없는 경우) 정상적으로 0건으로
        표시한다."""

    def show_stock_status(self, rows: list) -> None:
        """(sample, demand, state) 튜플 목록을 표 형태로 표시한다 (시료명/재고/미결수요/파생상태).
        rows가 비어 있으면(등록된 시료가 없으면) '등록된 시료가 없습니다.' 안내만 하고 끝낸다."""
```

- Controller에서 계산이 끝난 결과(딕셔너리, 튜플 리스트)만 받아 표 형태로 출력한다 — 재고/수요 계산이나
  상태 판정 로직은 View에 두지 않는다(CLAUDE.md: "화면 코드 안에 재고 계산이나 상태 전환 같은 비즈니스
  로직을 넣지 않는다").
- 주문이 하나도 없는 경우(FEATURES 엣지 케이스)는 `show_order_counts`가 모든 값이 0인 `counts`를
  정상적으로 받아 "0건"으로 표시하는 것으로 자연스럽게 처리된다(별도 분기 불필요).
- 등록된 시료가 없는 경우(FEATURES 엣지 케이스)는 `show_stock_status`가 빈 `rows`를 받아 안내 메시지를
  표시한다.

## 에러 처리 정책 (phase0~5.md 정책 승계)

- 잘못된 메뉴 선택(`1`/`2`/`0` 이외) → `show_error` 후 같은 하위 메뉴에서 재입력. 예외로 죽지 않는다.
- 조회 전용 화면이므로 이 외에 실패할 수 있는 입력 경로가 없다 (주문번호/시료 ID 등 사용자 식별자 입력이
  없음).

## 테스트 범위

`tests/test_monitoring_controller.py`에서 `MonitoringView`를 테스트 더블로 대체해 stdin 시뮬레이션 없이
검증한다 (Phase 1~5의 Controller 테스트와 동일한 패턴). 최소 다음을 검증:

- **상태별 건수 집계**: `RESERVED`/`PRODUCING`/`CONFIRMED`/`RELEASE` 각각의 건수가 정확히 집계되는지.
- **REJECTED 제외**: `REJECTED` 주문이 존재해도 어떤 상태의 건수에도, 합계에도 포함되지 않는지(합계는
  View가 계산하므로, Controller가 넘기는 `counts` 딕셔너리에 애초에 `REJECTED` 키가 없는지 확인).
- **재고 파생 상태 — 고갈**: 재고가 정확히 0인 시료가 "고갈"로 판정되는지(수요가 0이어도 고갈로
  판정됨을 포함 — FEATURES 권장 기본값 그대로).
- **재고 파생 상태 — 부족**: 재고가 0은 아니지만 `RESERVED`+`PRODUCING` 수요 합보다 적은 경우 "부족"으로
  판정되는지.
- **재고 파생 상태 — 여유**: 재고가 수요 이상인 경우(수요가 0인 경우 포함) "여유"로 판정되는지.
- **CONFIRMED 주문은 미결 수요에서 제외**: 같은 시료에 대해 `CONFIRMED` 주문이 있어도 그 수량이 "미결
  수요" 계산에 포함되지 않는지(이 Phase의 핵심 회귀 방지 포인트 — 위 "설계 결정" 절 참고).
- **빈 상태 처리**: 시료가 하나도 없을 때 `show_stock_status`가 빈 목록으로 정상 호출되는지, 주문이
  하나도 없을 때 `show_order_counts`가 모든 상태 0건으로 정상 호출되는지 (예외 없음).
- **매번 재계산**: 같은 `MonitoringController` 인스턴스로 두 번 연속 조회했을 때, 그 사이에 재고/주문
  데이터가 변경되면 두 번째 조회 결과에 반영되는지(캐시되지 않음을 확인).
- 기존 `tests/test_json_repository.py`, `tests/test_sample_*.py`, `tests/test_order_*.py`,
  `tests/test_approval_*.py`, `tests/test_production_controller.py`, `tests/test_shipment_controller.py`
  (Phase 0~5)는 그대로 유지하고 회귀가 없는지 `pytest` 전체 실행으로 확인한다 (`unittest.TestCase` 금지).

## 완료 기준 (`docs/PLAN.md` Phase 6 확인 포인트와 매핑)

| PLAN.md 확인 포인트 | 이 설계에서 보장하는 방법 |
| --- | --- |
| 상태별 건수를 직접 세어보고 화면 숫자와 비교 | `_show_order_counts()`의 `find(status==...)` 집계 |
| `REJECTED` 주문이 어떤 집계에도 포함되지 않음 | `_MONITORED_STATUSES`에 `REJECTED` 자체가 없음 |
| 재고 0인 시료가 "고갈", 넉넉한 시료가 "여유"로 표시 | `_show_stock_status()`의 `stock == 0` / `stock < demand` / else 분기 |

## 후속 Phase에 넘기는 미결정 사항

- `../DataMonitor`가 제공하는 실시간 자동 갱신(주기적 재조회 + 화면 갱신)과 잔여율(%) 바 그래프는 이
  Phase에서 채택하지 않는다. FEATURES/04-monitoring.md가 "잔여율(%) 같은 시각적 요소는 예시일 뿐 필수는
  아니다"라고 명시하고, PLAN.md Phase 6 확인 포인트도 단발성 조회로 충분히 검증 가능하므로 이 Phase의
  범위를 최소로 유지한다(YAGNI). 필요성이 실제로 제기되면(예: Phase 7 더미 데이터로 대량 데이터를 관찰할
  때 정적 조회로는 불편함이 확인되면) 그때 재검토한다.
