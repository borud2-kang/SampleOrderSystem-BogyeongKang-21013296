# Phase 1 설계: 시료 관리 (등록 / 조회 / 검색)

관련 계획: [`docs/PLAN.md` § Phase 1](../PLAN.md#phase-1--시료-관리)
관련 기능 명세: [`docs/FEATURES/01-sample.md`](../FEATURES/01-sample.md)

## 목적

Phase 0에서 배선만 끝나 있던 `SampleController`/`SampleView` 스텁을 실제 기능으로 채운다. 이 Phase가
끝나면 시료를 등록·조회·검색할 수 있고, 재시작해도 등록한 시료가 그대로 남아있어야 한다 (Phase 0에서 구축한
`SampleRepository` 영속성 위에 얹는 첫 실제 기능).

Phase 1은 시료 도메인에 한정되며, 주문/승인/생산/출고/모니터링은 다음 Phase 이후로 그대로 스텁 상태를
유지한다.

## 설계 원칙: PoC 패턴 재사용

`docs/design/phase0.md`와 동일하게, 새로 발명하기보다 `../ConsoleMVC`에서 이미 검증된 `SampleController`/
`SampleView` 패턴을 채택하고, Phase 0에서 확정한 이 프로젝트의 모델(`Sample`, `sample_id`/`avg_process_time`/
`yield_rate`/`stock` 필드, `SampleRepository.next_id()`)에 맞게 조정한다.

## 변경 대상 파일

```
SampleOrderSystem/
  app/
    controller/
      sample_controller.py   # 스텁 → 실제 구현 (등록/목록/검색 하위 메뉴 루프)
    view/
      sample_view.py          # 신규: 시료 관리 화면 (메뉴/입력/출력)
  tests/
    test_sample_controller.py # 신규: SampleController 단위 테스트 (stdin 시뮬레이션 없이)
```

`app/model/sample.py`, `app/persistence/sample_repository.py`는 Phase 0에서 이미 완성되어 있으므로 이
Phase에서는 수정하지 않는다 (필요한 API: `create`, `get_all`, `find`, `next_id`).

> **사후 기록**: `app/persistence/json_repository.py`는 애초 이 문서가 작성된 시점엔 수정 대상이
> 아니었으나, Phase 1 구현을 검증하는 과정에서 cp949 콘솔 인코딩 문제로 인해 "저장 실패 시 메모리와
> 파일 상태가 어긋나는" 버그가 발견되어 Phase 1 작업 중에 함께 수정했다. 구체적으로 `create`가 중복
> ID일 때 던지는 예외를 일반 `ValueError`에서 전용 타입 `DuplicateIdError(ValueError)`로 좁히고,
> `create`/`update`/`delete` 모두 `_save()` 실패 시 메모리 변경을 롤백하도록 고쳤다. 아래 절의
> `ValueError` 표기는 이 변경 이전 설계 당시 표기이며, 실제 코드는 `DuplicateIdError`를 사용한다
> (`app/controller/sample_controller.py`도 `except DuplicateIdError`로 좁혀 잡는다). 상세는
> [`phase2.md`](phase2.md)에서 정확한 이름으로 다시 인용한다.

## Controller 설계

`ConsoleMVC/app/controller/sample_controller.py`를 그대로 채택하되, 다음을 이 프로젝트 사정에 맞게 조정한다:

```python
class SampleController:
    def __init__(self, sample_repo: SampleRepository, view: SampleView) -> None:
        self._sample_repo = sample_repo
        self._view = view

    def run(self) -> None:
        while True:
            self._view.show_menu()
            choice = self._view.prompt_choice()
            if choice == "1":
                self._register()
            elif choice == "2":
                self._list()
            elif choice == "3":
                self._search()
            elif choice == "0":
                return
            else:
                self._view.show_error("알 수 없는 선택입니다. 메뉴에 표시된 번호를 입력하세요.")
```

- **생성자 시그니처 변경**: Phase 0의 `MainController`는 `SampleController(sample_repo)`로 View 없이
  배선했다 (스텁이라 View가 필요 없었음). Phase 1부터는 `SampleController(sample_repo, view)`로 바꾸고,
  `MainController.__init__`에서 `SampleView()` 인스턴스를 생성해 주입한다. 이는 phase0.md가 "후속 Phase에
  넘기는 미결정 사항"으로 남겨둔 항목을 이 Phase에서 확정하는 것이다.
- **등록(`_register`)**: `SampleView`로부터 검증된 입력(dict)을 받아 `Sample(sample_id=repo.next_id(),
  ...)`을 생성하고 `sample_repo.create(sample)`을 호출한다. 이름 중복은 허용하므로(FEATURES/01-sample.md
  "엣지 케이스" 절) Controller에서 이름에 대한 중복 검사를 하지 않는다. 시료 ID는 `next_id()`로 자동
  채번하므로 사용자가 직접 입력하지 않는다 (ConsoleMVC와 동일한 방식 — 사용자 입력 실수로 인한 ID 형식
  오류/충돌 가능성을 원천 차단).
- **목록(`_list`)**: `sample_repo.get_all()` 결과를 그대로 View에 넘긴다. 정렬 순서는 등록 순(리스트
  삽입 순)으로 두고 별도 정렬 로직을 추가하지 않는다 (명세에 정렬 요구사항 없음).
- **검색(`_search`)**: `sample_repo.find(predicate)`를 사용해 이름에 검색어가 **부분 일치**하는 시료를
  반환한다 (FEATURES/01-sample.md "검색 방식은 구현자 재량" — 부분 일치가 사용성 면에서 더 관대하므로
  채택). 대소문자 구분은 하지 않는다 조건은 없으므로 단순 `in` 연산자로 대소문자 그대로 비교한다(한글
  시료명이 대부분이라 대소문자 이슈가 크지 않음).
- **비즈니스 로직(수율 범위 검증 등)의 위치**: CLAUDE.md의 "View는 얇게 유지, 비즈니스 로직을 넣지
  않는다" 원칙에 따라 **입력값 파싱/재입력 루프는 View**, **도메인 규칙(중복 ID, 수율 범위) 검증은
  Repository/Controller** 경계로 나눈다 — 상세는 아래 "입력 검증 책임 분담" 절 참고.

## View 설계

`ConsoleMVC/app/view/sample_view.py`를 채택하되, FEATURES/01-sample.md의 "엣지 케이스 / 검증 규칙"을
충족하도록 입력 검증 루프를 추가한다 (ConsoleMVC PoC는 검증 없이 `float(input(...))`을 그대로 호출해
잘못된 입력 시 예외로 죽는 구조였으므로 그대로 가져올 수 없음).

```python
class SampleView:
    def show_menu(self) -> None: ...
    def prompt_choice(self) -> str: ...

    def prompt_registration(self) -> dict:
        """이름/평균 생산시간/수율을 입력받는다. 형식이 잘못되면 같은 항목을 재입력받는다."""
        name = self._prompt_nonempty("시료명 > ")
        avg_time = self._prompt_positive_float("평균 생산시간(분/개) > ")
        yield_rate = self._prompt_yield_rate("수율(0 초과 1 이하) > ")
        return {"name": name, "avg_process_time": avg_time, "yield_rate": yield_rate}

    def show_registered(self, sample: Sample) -> None: ...
    def show_duplicate_error(self, sample_id: str) -> None: ...
    def show_list(self, samples: list[Sample]) -> None: ...
    def prompt_search_keyword(self) -> str: ...
    def show_search_result(self, samples: list[Sample]) -> None: ...
    def show_error(self, message: str) -> None: ...

    # 내부 헬퍼: 잘못된 형식이면 오류 출력 후 같은 프롬프트 재입력
    def _prompt_nonempty(self, prompt: str) -> str: ...
    def _prompt_positive_float(self, prompt: str) -> float: ...
    def _prompt_yield_rate(self, prompt: str) -> float: ...
```

- `_prompt_positive_float`/`_prompt_yield_rate`는 `float()` 변환 실패(`ValueError`) 시 "숫자를
  입력하세요" 안내 후 같은 프롬프트를 반복한다. `_prompt_yield_rate`는 추가로 `0 < x <= 1` 범위를
  검증한다 (FEATURES/01-sample.md: "수율은 0을 초과하고 1 이하인 값이어야 한다").
- 시료명은 빈 문자열을 허용하지 않는다 (`_prompt_nonempty`) — 명세에 명시되진 않았으나 "필수값 누락
  처리"(FEATURES/01-sample.md 엣지 케이스)에 해당하는 가장 기본적인 케이스로 간주한다.
- 시료 ID는 `next_id()`로 자동 채번되므로 View에서 입력받지 않는다.
- 목록/검색 결과 출력 시 재고 컬럼을 반드시 포함한다 (FEATURES/01-sample.md: "각 시료의 현재 재고 수량도
  함께 표시").
- 검색 결과가 없으면 "검색 결과가 없습니다." 안내 후 빈 목록을 그대로 찍지 않는다.

## 입력 검증 책임 분담

| 검증 항목 | 위치 | 이유 |
| --- | --- | --- |
| 숫자 형식 오류 (문자열 입력 등) | View (재입력 루프) | 콘솔 입력 파싱은 View의 책임. Controller/Model은 이미 파싱된 값만 받는다. |
| 수율 범위(0 초과 1 이하) | View (재입력 루프) | 콘솔에서 즉시 재입력받는 것이 사용자 경험상 자연스럽고, ConsoleMVC 패턴과 일치. |
| 시료 ID 중복 | Repository (`create`가 `DuplicateIdError` 발생) | `JsonRepository.create`의 책임이며, Controller가 아니라 저장소 계층의 불변식이다. Controller는 이 예외만 좁게 잡아 `view.show_duplicate_error()`로 안내한다 (다른 원인의 예외는 그대로 전파 — 위 "사후 기록" 참고). |
| 이름 중복 허용 여부 | 검증 없음 (허용) | FEATURES/01-sample.md 명시: "이름 중복은 허용하는 쪽을 기본값으로 한다". |

시료 ID는 사용자가 직접 입력하지 않고 `next_id()`로 자동 채번되므로, 실제로 "시료 ID 중복" 경로가
정상 흐름에서 발생할 일은 없다. 그럼에도 `SampleRepository.create`가 이미 이 불변식을 보장하므로
Controller에서 방어적으로 `try/except DuplicateIdError`로 감싸 안내 메시지를 보여주는 정도로만 대응한다
(회귀 방지 및 향후 ID를 사용자 입력으로 바꿀 가능성에 대비).

## 에러 처리 정책 (phase0.md 정책 승계)

- 메뉴에서 정의되지 않은 입력 → `show_error` 후 같은 하위 메뉴에서 재입력. 예외로 죽지 않는다.
- 숫자 입력 파싱 실패 → 해당 항목만 재입력받는다 (전체 등록 과정을 처음부터 다시 하지 않는다).
- `SampleRepository.create` 시 발생하는 `DuplicateIdError`(중복 ID)는 `main.py`까지 전파되지 않고
  `SampleController`에서 잡아 사용자 메시지로 변환한다. 그 외 원인의 예외(예: 저장 중 인코딩 오류)는
  이 처리로 가려지지 않고 그대로 전파된다.

## 테스트 범위

- `tests/test_sample_controller.py` — Controller의 등록/조회/검색 로직을 stdin 시뮬레이션 없이 검증한다.
  `SampleView`를 간단한 테스트 더블(스텁/페이크)로 대체해 `run()`의 분기 대신 `_register`/`_list`/
  `_search`에 해당하는 public 메서드를 직접 호출하는 방식으로 작성한다 (CLAUDE.md: "콘솔 입출력과 분리되어
  stdin 시뮬레이션 없이 단위 테스트가 가능해야 한다"). 최소 다음을 검증:
  - 등록 시 `next_id()`로 채번된 ID로 `Sample`이 생성되고 저장소에 반영되는지.
  - 이름이 중복되어도 등록이 거부되지 않는지 (FEATURES 엣지 케이스).
  - 목록 조회 결과에 재고 필드가 포함되는지.
  - 검색어가 이름에 부분 일치하는 시료만 반환되는지, 일치하는 항목이 없으면 빈 리스트를 반환하는지.
- `SampleView`의 입력 검증(재입력 루프)은 `pytest`에서 `monkeypatch`로 `builtins.input`을 시퀀스로
  대체해 검증한다 (예: 잘못된 문자열 → 올바른 값 순서로 입력을 주고, 최종적으로 올바른 값이 반환되는지
  확인). 이 부분은 pytest 스타일을 유지하되 View 계층이므로 Controller 테스트와 파일을 분리해도 되고
  (`test_sample_view.py`) 한 파일에 묶어도 된다 — 구현 시 판단.
- 기존 `tests/test_json_repository.py`(Phase 0)는 그대로 유지하고 회귀가 없는지 `pytest` 전체 실행으로
  확인한다.

## 완료 기준 (`docs/PLAN.md` Phase 1 확인 포인트와 매핑)

| PLAN.md 확인 포인트 | 이 설계에서 보장하는 방법 |
| --- | --- |
| 시료 2~3개 등록 후 목록 조회에서 모두 보임 | `SampleController._list()` → `sample_repo.get_all()` → `SampleView.show_list()` |
| 등록마다 시료 ID가 자동 채번되고 겹치지 않음 | `next_id()`가 매 등록마다 순차 채번 (`S-001`, `S-002`, ...) — `SampleRepository.create`의 중복 검사가 저장소 계층에서 방어적으로 보장됨(테스트로 확인) |
| 수율에 0, 문자열 등 잘못된 값 입력 시 재입력 요구 | `SampleView._prompt_yield_rate`의 재입력 루프 (`0 < x <= 1` 검증 + `ValueError` 캐치) |
| 이름으로 검색해 원하는 시료만 나옴 | `SampleController._search()` → `sample_repo.find(...)` 부분 일치 |
| 재시작해도 등록한 시료가 남아있음 | Phase 0에서 이미 보장된 `JsonRepository`/`SampleRepository`의 영속성을 그대로 재사용 (변경 없음) |

## 후속 Phase에 넘기는 미결정 사항

- 목록 페이지네이션 — FEATURES/01-sample.md에서 "필수는 아님"으로 명시. 등록 시료가 많아져 화면이 실제로
  불편해지는 시점에 재검토한다.
- 검색 방식 확장(다중 필드 검색, 정규식 등) — 현재는 이름 부분 일치만 지원. 필요성이 확인되면 이후 Phase에서
  검토.
