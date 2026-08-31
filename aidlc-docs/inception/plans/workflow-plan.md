# 워크플로우 계획서 (Workflow Planning Plan)

**역할**: Solution Architect
**목적**: 사용자 스토리(`stories.md`, 32개)를 논리적 **작업 유닛(Units of Work)** 으로 분해하고, 유닛 간 의존성·구축 순서·설계 산출물 범위를 결정하여 이후 단계(Application Design → Units Generation → Construction)의 기반을 마련합니다.

이 계획서는 (1) 워크플로우 계획 방법론 체크리스트, (2) 유닛 분해 접근법 옵션, (3) 방향 결정을 위한 질문으로 구성됩니다.
아래 **질문 섹션**의 각 `[Answer]:` 태그 뒤에 문자를 채워주세요. 맞는 보기가 없으면 마지막 **Other**를 선택하고 직접 기술해 주세요.
답변 완료 후 `continue` 또는 `done`으로 알려주시면 검토 후 확정된 계획을 승인받겠습니다.

---

## A. 워크플로우 계획 방법론 체크리스트 (실행 단계)

- [x] 사용자 스토리를 논리적 작업 유닛(Unit)으로 그룹화
- [x] 각 유닛의 책임 범위(포함 스토리, 데이터, API 경계) 정의
- [x] 유닛 간 의존성 그래프 및 구축 순서(sequencing) 결정
- [x] 공통 관심사(인증, 실시간 SSE, 세션 라이프사이클, 시드 데이터, PBT) 처리 전략 정의
- [x] 각 유닛의 Application Design 산출물 범위(depth) 결정
- [x] MVP 우선순위(Must/Should/Could)와 유닛별 완료 기준(DoD) 정렬
- [x] 유닛 간 통합·검증 체크포인트 정의
- [x] `workflow-plan` 산출물(유닛 목록·의존성·순서) 문서화 → `inception/workflow/workflow.md`

---

## B. 유닛 분해 접근법 (Unit Decomposition Options)

아래는 32개 스토리를 작업 유닛으로 나누는 방식입니다. 트레이드오프를 참고해 Q1에서 선택해 주세요.

- **Capability-Based (기능 역량 기반)**: 시스템 역량(인증, 메뉴, 주문/장바구니, 세션, 실시간 모니터링) 중심으로 유닛 구성 — 응집도 높고 백엔드/프론트 수직 슬라이스에 유리 *(권장)*
- **Persona-Based (페르소나 기반)**: 고객 유닛 / 관리자 유닛 / 공통 유닛으로 분리 — 역할별 완결성에 강점, 단 공유 데이터 모델 중복 위험
- **Layer-Based (계층 기반)**: 프론트엔드 / 백엔드 API / 데이터·시드 유닛 — 기술 계층 명확, 단 기능 단위 종단 검증이 늦어짐
- **Single-Unit (단일 유닛)**: MVP 전체를 하나의 유닛으로 한 번에 구축 — 소규모 데모에 단순, 단 병렬화·점진 검증 이점 없음

### 참고: Capability-Based 유닛 초안 (권장안 채택 시)
| # | 유닛(Unit) | 포함 스토리(예시) | 핵심 책임 |
|---|---|---|---|
| U1 | **Foundation & Data** (기반·데이터 모델·시드) | SD-1~3, 공통 스키마 | SQLite 스키마, 시드 스크립트, 프로젝트 스캐폴딩(Vite/FastAPI) |
| U2 | **Auth & Session** (인증·세션) | US-A-01~03, US-C-01~02, US-A-04 | JWT 관리자 인증(16h), 테이블 태블릿 자동 로그인, 세션 식별 |
| U3 | **Menu** (메뉴 조회·관리) | US-C-03~06, US-A-16~18 | 메뉴 CRUD/노출순서, 고객 메뉴 탐색 |
| U4 | **Cart & Order** (장바구니·주문) 🔬 | US-C-07~14 | 로컬 장바구니, 주문 생성/성공 플로우, 현재 세션 주문 조회 |
| U5 | **Order Monitoring (SSE)** (실시간 모니터링) 🔬 | US-A-05~10 | SSE 대시보드, 주문 상태 전이, 직권 삭제, 필터 |
| U6 | **Session Lifecycle & History** (세션 라이프사이클·이력) 🔬 | US-A-11~15 | 세션 시작/이용 완료, 과거 내역·날짜 필터 |

*(위 표는 예시이며, 답변에 따라 확정됩니다.)*

---

## C. 질문 (Questions)

## Question 1
**유닛 분해 접근법**(위 B 섹션 참고)은 무엇으로 할까요?

A) Capability-Based (기능 역량 기반, 위 초안 6개 유닛) — 권장

B) Persona-Based (고객/관리자/공통)

C) Layer-Based (프론트/백엔드/데이터)

D) Single-Unit (MVP 전체를 하나의 유닛으로)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 2
**유닛 구축 순서(sequencing)** 전략은 무엇을 선호하시나요?

A) Foundation-First (기반 우선): U1(기반·데이터)·U2(인증) 먼저 → 이후 기능 유닛 순차 — 의존성 안전, 권장

B) Vertical-Slice by Priority (우선순위 수직 슬라이스): Must 스토리를 종단으로 먼저 완성 → Should/Could 후속

C) Customer-Journey First (고객 여정 우선): 고객 기능 완성 후 관리자 기능

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 3
**각 유닛의 Application Design 산출물 상세 수준(depth)** 은 어느 정도가 적절할까요?

A) Comprehensive — 유닛별 도메인 모델 + API 계약(엔드포인트·요청/응답) + 데이터 모델 + 주요 컴포넌트/화면 설계

B) Standard — 유닛별 API 계약 + 데이터 모델 + 핵심 컴포넌트 (권장, MVP 적합)

C) Lightweight — 유닛별 책임·인터페이스 요약 수준

X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 4
**공통 관심사(Cross-Cutting Concerns)** — JWT 인증, 실시간 SSE, 세션 라이프사이클, 시드 데이터, PBT — 는 어떻게 다룰까요?

A) 전용 기반 유닛으로 집약 (인증·세션·시드는 U1/U2에 모으고 각 유닛이 참조) — 권장

B) 각 기능 유닛 내부에 분산 배치 (유닛별 독립성 우선)

C) 별도 "공통 관심사" 설계 문서로 분리하여 모든 유닛이 공유 참조

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 5
**유닛 간 통합·검증 체크포인트**를 어떻게 둘까요?

A) 각 유닛 완료 시 유닛 단위 검증(단위/속성 테스트) + 전체 통합은 마지막 Build & Test에서 일괄 — 권장

B) 유닛 2~3개마다 중간 통합 체크포인트 배치

C) 매 유닛 완료 직후 즉시 종단 통합 검증

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 6
**속성 기반 테스트(PBT) 대상 규칙**(장바구니 총액, 상태 전이, 세션 무손실 등 6개)의 워크플로우 반영 방식은?

A) 해당 규칙을 포함한 유닛(U4·U5·U6)에 PBT 작업을 명시적 산출물로 포함, Functional Design(PBT-01)에서 상세화 — 권장

B) PBT를 별도 횡단 유닛으로 분리하여 전체 규칙을 한 번에 처리

X) Other (please describe after [Answer]: tag below)

[Answer]: A
