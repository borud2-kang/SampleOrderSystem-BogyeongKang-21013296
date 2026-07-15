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

## 문서

프로젝트 배경/요구사항/설계는 `docs/` 아래에 정리되어 있습니다:

- [`docs/PRD.md`](docs/PRD.md) — 배경, 목표, 범위, 도메인 모델, 상태 전이도 등 요약.
- [`docs/PLAN.md`](docs/PLAN.md) — Phase별 개발 계획과 확인 포인트.
- [`docs/FEATURES/`](docs/FEATURES) — 메인 메뉴 6개 기능별 상세 명세.
- [`docs/design/`](docs/design) — 각 Phase의 구현 설계 문서.
- [`CLAUDE.md`](CLAUDE.md) — 아키텍처 가이드 및 서브에이전트 구성.
