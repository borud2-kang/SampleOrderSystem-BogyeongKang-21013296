# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 현황

이 저장소는 아직 구현 이전 단계입니다: 미션 명세 PDF(`pdf/[CRA_AI] Day3_개인과제_반도체시료관리_r1 2.pdf`)와
IDE/프로젝트 스캐폴딩만 존재하며, 애플리케이션 소스 코드·테스트 스위트·빌드 설정은 아직 없습니다.
이 프로젝트는 Python 으로 구현합니다.

이 저장소는 2개 미션 중 "[미션2] 프로젝트 개발"에 해당합니다. 미션1(PoC)은 이미 구현이 끝난 **독립적인
프로젝트/git 저장소**로, 이 저장소(`SampleOrderSystem`)와 같은 상위 디렉터리(`C:\reviewer\Project\`) 아래에
나란히 존재합니다. 이 저장소 자체의 하위 폴더가 아니므로 착각하지 마세요:

| PoC 저장소 | 경로 | 검증 내용 |
| --- | --- | --- |
| ConsoleMVC | `../ConsoleMVC` | Model/Controller/View 패키지 구조와 역할 분리 (데이터는 in-memory) |
| DataPersistence | `../DataPersistence` | JSON 파일 기반 영속성 + CRUD (`data/samples.json`, `data/orders.json`) |
| DataMonitor | `../DataMonitor` | 저장된 데이터 상태를 콘솔에서 실시간 조회하는 관리자 도구 |
| DummyDataGenerator | `../DummyDataGenerator` | 테스트용 Dummy Sample/Order 데이터 생성 도구 |

각 PoC는 별도 git 저장소이므로 이 저장소에서 직접 import하거나 서브모듈로 끌어오지 않습니다. 대신 [미션2]는 이
네 PoC에서 검증된 패턴(MVC 계층 분리, JSON 영속성/CRUD, 모니터링 도구, Dummy 데이터 생성)을 하나의 완성된
`SampleOrderSystem` 애플리케이션으로 통합·재구현하는 작업입니다. 구현 중 설계가 애매하면 해당 PoC의 코드를
먼저 참고하세요 (예: `Sample`/`Order` 모델 필드, JSON repository 인터페이스, 모니터링 화면 구성 등은 이미 PoC에서
한 번 검증된 형태입니다).

명세에 따르면 이번 미션의 평가 주안점은 CLAUDE.md/PRD.md 등 문서 관리, Harness 도입, Test, CleanCode, Commit
이력이므로 이를 "있으면 좋은 것"이 아니라 실제 평가 기준으로 취급해야 합니다.

## 문서

이 저장소의 요구사항은 `docs/` 아래에 정리되어 있으며, 이 CLAUDE.md는 요구사항 자체를 반복하지 않고 그
문서들을 가리킨다. 코드를 작성하기 전에 관련 문서를 먼저 확인하고, 요구사항이 바뀌면 코드뿐 아니라 해당
문서도 함께 갱신한다.

- [`docs/PRD.md`](docs/PRD.md) — 배경, 목표, 범위, 도메인 모델, 상태 전이도, 기능/비기능 요구사항 요약.
- [`docs/PLAN.md`](docs/PLAN.md) — Phase별 개발 계획. 각 Phase가 끝날 때마다 실행 가능한 상태여야 하며,
  Phase별 확인 포인트(사람이 직접 콘솔에서 검증할 시나리오)가 명시되어 있다. 구현 순서를 정할 때 이 문서를
  따른다.
- [`docs/FEATURES/`](docs/FEATURES) — 메인 메뉴 6개 항목과 1:1로 대응하는 기능별 상세 명세(입력값, 처리
  흐름, 엣지 케이스). 아래 도메인 섹션의 각 항목도 이 문서들을 요약한 것이므로, 구현 중 세부 규칙이
  궁금하면 반드시 원본 문서를 먼저 확인한다:
  - [`01-sample.md`](docs/FEATURES/01-sample.md) — 시료 관리
  - [`02-order.md`](docs/FEATURES/02-order.md) — 시료 주문(예약)
  - [`03-approval.md`](docs/FEATURES/03-approval.md) — 주문 승인/거절 (재고 분기 로직 포함, 가장 핵심)
  - [`04-monitoring.md`](docs/FEATURES/04-monitoring.md) — 모니터링(주문량/재고량)
  - [`05-production-line.md`](docs/FEATURES/05-production-line.md) — 생산 라인(수율 계산, FIFO 큐)
  - [`06-shipment.md`](docs/FEATURES/06-shipment.md) — 출고 처리

## Harness (서브에이전트 구성)

`.claude/agents/` 에 이 프로젝트 전용 서브에이전트 3종이 정의되어 있다. 기능 하나를 진행할 때는
"문서 확인 → 구현 → 검증" 순서로 사용한다:

1. **doc-consistency-checker** — 구현 전/후로 CLAUDE.md, `docs/PRD.md`, `docs/FEATURES/*`,
   `docs/PLAN.md`가 서로 어긋나지 않는지, 코드가 있다면 코드와도 어긋나지 않는지 검증한다. 읽기 전용이며
   직접 수정하지 않는다.
2. **action-implementer** — 특정 Phase/기능의 코드 구현을 담당한다. CLAUDE.md의 Model/Controller/View
   분리 원칙을 따르며, 테스트 작성은 하지 않는다.
3. **verify-tester** — 구현이 끝난 뒤 `docs/PLAN.md`의 확인 포인트와 `docs/FEATURES/*`의 엣지 케이스를
   기준으로 테스트를 작성/실행하고 pass/fail을 보고한다. 버그를 직접 고치지 않고 action-implementer에게
   피드백한다.

## 도메인: 반도체 시료 생산주문관리 시스템

콘솔 기반(메뉴 + 표준입력, GUI/웹 아님)으로 동작하며, 가상의 반도체 회사 "S-Semi"의 시료(Sample) 생산 주문을
등록 → 주문 → 승인/거절 → 생산 → 출고까지 관리하는 시스템입니다. 개념적으로는 세 역할(고객, 주문 담당자,
생산 담당자)이 관여하지만, 실제로는 담당자가 콘솔에 명령을 입력해 시스템을 조작하는 구조이므로 멀티유저 인증은
필요하지 않습니다.

### 핵심 엔티티

- **시료(Sample)**: 카탈로그의 기본 단위. 속성은 시료 ID, 이름, 평균 생산시간(개당), 수율(정상품 수 / 총 생산량,
  예: 0.9)입니다. 시스템에 등록된 시료만 주문할 수 있으며, 시료별 현재 재고 수량을 추적합니다.
- **주문(Order)**: 시료 ID, 고객명, 주문 수량으로 생성됩니다. 주문번호와 상태(아래 상태 흐름 참고)를 가집니다.

### 주문 상태 흐름

```
RESERVED --(승인, 재고 충분)--> CONFIRMED --(출고 처리)--> RELEASE
RESERVED --(승인, 재고 부족)--> PRODUCING --(생산라인 완료)--> CONFIRMED --> RELEASE
RESERVED --(거절)--> REJECTED
```

- `RESERVED`: 주문 접수, 승인 대기 중.
- `REJECTED`: 종단 상태이자 정상 흐름 밖의 상태 — **모든 모니터링/통계에서 제외**해야 합니다.
- `PRODUCING`: 승인은 되었으나 재고가 부족하여 생산 라인에서 제작 중.
- `CONFIRMED`: 승인 완료(재고 충분 또는 생산 완료) 및 출고 대기 중.
- `RELEASE`: 고객에게 출고 완료. 종단 상태.

승인 처리는 재고를 확인하는 유일한 시점이며 자동으로 CONFIRMED/PRODUCING으로 분기됩니다 — 이 분기 로직이
"주문 승인" 기능의 핵심이므로 가장 중점적으로 테스트해야 할 경로입니다.

### 생산 라인 규칙

- 하나의 생산 라인은 한 번에 한 시료 종류만 생산합니다(예시 UI 기준 단일 라인. 명세상 여러 라인을 명시적으로
  금지하진 않으므로, 확장이 필요하면 사용자에게 먼저 확인하세요).
- 실제로 부족분이 발생한 주문에 대해서만 생산합니다.
- **부족분** = 주문 수량 − 현재 재고.
- **실 생산량** = `ceil(부족분 / 수율)` — 수율이 100%가 아니므로, 불량을 감안해 부족분보다 더 많은 수량을
  생산해야 합니다.
- **총 생산 시간** = 평균 생산시간 × 실 생산량.
- 대기 중인 주문은 **FIFO 큐(생산 큐)** 에 보관됩니다 — 스케줄링 전략은 엄격한 선입선출이며 우선순위 재정렬은
  없습니다.
- 생산이 완료되면 주문 상태가 자동으로 `PRODUCING → CONFIRMED`로 전환됩니다.

### 모니터링 기능

콘솔에 표시되는 두 가지 화면:
- **상태별 주문 수** (RESERVED/CONFIRMED/PRODUCING/RELEASE), REJECTED는 제외.
- **시료별 재고 현황**, 각 시료에 파생 상태를 표기: 여유/부족/고갈 — 단순 절대 임계값이 아니라 미결 주문 대비
  재고 수량을 기준으로 산출합니다.

### 메뉴 구성 (제안 구조이며, 명세상 UI 레이아웃은 자유)

1. 시료 관리: 등록, 목록 조회(현재 재고 포함), 이름/속성 검색.
2. 시료 주문(접수): 주문 생성(시료 ID, 고객명, 수량) → RESERVED 상태로 시작.
3. 주문 승인/거절: RESERVED 주문 목록 표시, 승인(재고에 따라 CONFIRMED/PRODUCING로 분기) 또는 거절(→ REJECTED).
4. 모니터링: 위에서 설명한 주문 수 화면과 재고 화면.
5. 생산라인 조회: 현재 생산 중인 항목의 정보 및 FIFO 대기열.
6. 출고 처리: CONFIRMED 주문 목록 표시, 선택한 주문을 출고 → RELEASE.

PDF의 예시 화면(11, 13, 15, 17, 19, 21, 23쪽)은 어디까지나 참고용이며, 정확한 필드 구성·레이블·서식은
명세("화면 구성은 자유롭게 결정하여 표기하시기 바랍니다")에 따라 구현자가 자유롭게 결정합니다.

## 아키텍처 가이드

이 프로젝트는 위에서 소개한 4개의 sibling PoC 저장소(`../ConsoleMVC`, `../DataPersistence`,
`../DataMonitor`, `../DummyDataGenerator`)에서 개별 검증된 요소를 통합합니다. Model/Controller/View를
명확히 분리한 구조로 설계합니다:

- **Model**: 시료(Sample)·주문(Order) 엔티티, 생산 큐, 그리고 (PoC에서 정한 방식대로) 파일/JSON/DB 기반
  영속성과 CRUD.
- **Controller**: 주문 생명주기 로직(승인 분기, 재고 차감, 생산 스케줄링/완료, 출고 처리) — 위에서 설명한
  상태 머신과 수율/FIFO 계산이 여기에 위치해야 하며, 콘솔 입출력과 분리되어 stdin 시뮬레이션 없이 단위 테스트가
  가능해야 합니다.
- **View**: 콘솔 메뉴 루프 및 각 화면 렌더링 — 표시 로직은 최대한 얇게 유지하고, 화면 코드 안에 재고 계산이나
  상태 전환 같은 비즈니스 로직을 넣지 않습니다.

승인 분기, 수율 기반 생산량 계산, FIFO 순서의 정확성이 엣지 케이스(소수점 수율, 재고 0, 동시 타임스탬프 등)가
가장 많이 발생할 부분이므로, 이를 콘솔 상호작용 계층과 독립적인 테스트 가능한 순수 함수/서비스로 설계하세요.
