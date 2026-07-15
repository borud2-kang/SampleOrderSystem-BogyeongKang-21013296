# SampleOrderSystem

가상의 반도체 회사 "S-Semi"의 시료(Sample) 생산 주문을 등록 → 주문 → 승인/거절 → 생산 → 출고까지
관리하는 콘솔 기반(메뉴 + 표준입력) 애플리케이션입니다.

## 실행 방법

```
python main.py
```

메인 메뉴가 콘솔에 표시되며, 번호를 입력해 기능을 선택합니다. Windows 콘솔(코드페이지 949 등)에서
실행하더라도 한글 입출력이 깨지지 않도록 시작 시 표준입출력을 UTF-8로 강제 재구성합니다(`main.py`의
`_force_utf8_io()`) — 별도 플래그를 줄 필요는 없습니다.

## 테스트 실행 방법

```
pip install -r requirements-dev.txt
pytest
```

## 더미 데이터 생성

메뉴를 매번 손으로 입력하지 않고 대량의 초기 시료/주문 데이터를 채우려면 다음 커맨드를 사용합니다:

```
python generate_dummy_data.py --samples 20 --orders 50 --seed 42
```

- `--samples`: 생성할 시료 개수
- `--orders`: 생성할 주문 개수 (항상 `RESERVED` 상태로 생성됩니다)
- `--seed`: 재현 가능한 결과를 위한 랜덤 시드 (생략 가능)

생성된 데이터는 `python main.py`가 사용하는 것과 동일한 `data/samples.json`, `data/orders.json`에
저장되므로, 생성 직후 바로 콘솔 메뉴(시료 관리, 모니터링 등)에서 확인할 수 있습니다. 단, 이 도구는
`RESERVED` 주문까지만 생성하며 `CONFIRMED`/`PRODUCING`/`RELEASE`/`REJECTED` 상태는 실제 메뉴(주문
승인/거절, 생산 라인, 출고 처리)를 통해서만 만들어집니다.

## 디렉터리 구조

```
app/
  model/        # Sample/Order 엔티티, 생산 큐 등 도메인 모델
  persistence/  # JSON 파일 기반 영속성 및 CRUD 리포지토리
  controller/    # 주문 생명주기 로직 (승인 분기, 생산 스케줄링, 출고 처리 등)
  view/          # 콘솔 메뉴 루프와 화면 렌더링
  generator/     # 더미 데이터 생성기 (Model에 반영)
main.py                    # 콘솔 애플리케이션 진입점
generate_dummy_data.py     # 더미 데이터 생성 CLI 진입점
data/                       # samples.json, orders.json (실행 시 자동 생성)
tests/                      # pytest 테스트 스위트
```

## 명세(PDF) 대비 구현 일치성 검토

`pdf/[CRA_AI] Day3_개인과제_반도체시료관리_r1 2.pdf` 원본 명세와 현재 구현을 대조 검토한 결과입니다.

**생산 완료 처리 방식(수동 트리거) — 그대로 유지**: 명세는 생산 완료 시 `PRODUCING → CONFIRMED`
전환만 요구할 뿐, 완료를 "언제/어떻게" 트리거할지는 정하지 않았습니다(`docs/PLAN.md` Phase 4도 "자동
타이머든, 수동 '다음 단계 진행' 커맨드든 방식은 구현 시 결정"이라고 명시). 생산라인 화면 예시(PDF
21쪽)에 실시간 진행률(%)·완료 예정 시각이 보이지만, 해당 쪽 각주가 "화면 구성은 자유롭게 결정"이라고
분명히 밝히고 있어 강제 요구사항이 아닙니다. 자동 스케줄러(백그라운드 시간 경과에 따른 자동 완료)
도입을 검토했으나, 명세를 충족하기 위해 반드시 필요한 것은 아니고 이미 구현·테스트된 수동 트리거
방식(생산 라인 조회 화면에서 "완료 처리" 선택)이 명세를 온전히 만족하므로 그대로 유지하기로 했습니다.

**의도적으로 남겨둔 두 가지 차이점**:

1. **시료 등록 시 "시료 ID" 직접 입력** — PDF 12쪽은 시료 등록 입력값에 "시료 ID"를 포함하지만,
   이 프로젝트는 Phase 0/1에서 사용자가 직접 입력할 경우 발생할 수 있는 ID 충돌 문제를 원천 차단하기
   위해 시스템이 자동 채번(`S-001`, `S-002`, ...)하도록 결정했습니다(`docs/design/phase0.md`,
   `docs/design/phase1.md`, `docs/FEATURES/01-sample.md`에 근거 기록).
2. **주문 승인 화면의 확인 순서** — PDF 17쪽 예시는 승인 선택 후 부족분/실생산량/총생산시간을 먼저
   보여준 다음 `[Y]/[N]`을 다시 묻는 2단계 흐름이지만, 이 프로젝트는 `[Y]/[N]`을 먼저 묻고 계산
   결과는 처리 완료 메시지에만 표시합니다. 두 방식 모두 해당 쪽 각주("화면 구성은 자유")상 허용되는
   범위이며, 필요 시 나중에 조정 가능한 UX 선택 사항입니다.

그 외 메뉴 구성, 상태 전이(`RESERVED`/`REJECTED`/`PRODUCING`/`CONFIRMED`/`RELEASE`), 승인 분기 로직,
`ceil(부족분/수율)` 산식, FIFO 생산 큐, 모니터링의 REJECTED 제외·여유/부족/고갈 판정, 출고 처리 흐름은
PDF 명세와 정확히 일치합니다.

## 문서

프로젝트 배경/요구사항/설계는 `docs/` 아래에 정리되어 있습니다:

- [`docs/PRD.md`](docs/PRD.md) — 배경, 목표, 범위, 도메인 모델, 상태 전이도 등 요약.
- [`docs/PLAN.md`](docs/PLAN.md) — Phase별 개발 계획과 확인 포인트.
- [`docs/FEATURES/`](docs/FEATURES) — 메인 메뉴 6개 기능별 상세 명세.
- [`docs/design/`](docs/design) — 각 Phase의 구현 설계 문서.
- [`CLAUDE.md`](CLAUDE.md) — 아키텍처 가이드 및 서브에이전트 구성.
