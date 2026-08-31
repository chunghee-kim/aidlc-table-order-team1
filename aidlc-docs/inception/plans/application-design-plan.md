# 애플리케이션 설계 계획서 (Application Design Plan)

**역할**: Solution Architect
**단계**: INCEPTION — Application Design (Part 1: Planning)
**입력**: `requirements.md`, `stories.md`(32 스토리), `workflow.md`(6 유닛, U1~U6), `personas.md`
**설계 depth**: **Standard** (워크플로우 계획에서 확정) — 유닛별 API 계약 + 데이터 모델 + 핵심 컴포넌트
**목적**: 6개 유닛(U1~U6)에 걸친 **고수준 컴포넌트 식별 및 서비스 계층 설계**를 확정합니다. 상세 비즈니스 로직은 CONSTRUCTION 단계의 Functional Design(유닛별)에서 다룹니다.

이 계획서는 (1) 방법론 체크리스트, (2) 필수 설계 산출물, (3) 방향 결정을 위한 질문으로 구성됩니다.
아래 **질문 섹션**의 각 `[Answer]:` 태그 뒤에 문자를 채워주세요. 맞는 보기가 없으면 마지막 **Other**를 선택하고 직접 기술해 주세요.
답변 완료 후 `continue` 또는 `done`으로 알려주시면 검토 후 설계 산출물을 생성합니다.

---

## A. 방법론 체크리스트 (실행 단계)

- [x] 요구사항·스토리·워크플로우 유닛 분석 → 주요 기능 컴포넌트 식별
- [x] 컴포넌트 책임·인터페이스 정의 (상세 비즈니스 로직 제외)
- [x] 서비스 계층(오케스트레이션) 설계
- [x] 컴포넌트 간 의존성·통신 패턴 정의
- [x] 질문에 대한 사용자 답변 반영 (Q1~Q7 = A, 전부 권장안 채택)
- [x] 필수 설계 산출물 생성 (아래 B 섹션)
- [x] 설계 완전성·일관성 검증

---

## B. 필수 설계 산출물 (Mandatory Artifacts)

Application Design 승인 후 `aidlc-docs/inception/application-design/`에 다음을 생성합니다.

- [x] `components.md` — 컴포넌트 정의와 고수준 책임
- [x] `component-methods.md` — 메서드 시그니처 (비즈니스 규칙 상세는 Functional Design에서)
- [x] `services.md` — 서비스 정의와 오케스트레이션 패턴
- [x] `component-dependency.md` — 의존성 매트릭스·통신 패턴·데이터 흐름
- [x] `application-design.md` — 위 문서 통합본

---

## C. 예비 컴포넌트 지형도 (Preliminary Component Landscape)

> 아래는 요구사항·유닛 기반 **초안**이며, 질문 답변에 따라 확정됩니다.

### 백엔드 (FastAPI)
| 영역 | 예상 컴포넌트 | 관련 유닛 |
|---|---|---|
| API 라우터 | `AuthRouter`, `MenuRouter`, `OrderRouter`, `AdminOrderRouter`(SSE 포함), `TableRouter`, `HistoryRouter` | U2~U6 |
| 서비스 | `AuthService`, `MenuService`, `OrderService`, `SessionService`, `HistoryService`, `OrderEventBroker`(SSE) | U2~U6 |
| 데이터 접근 | `Store`, `AdminUser`, `Table`, `TableSession`, `Menu`, `Category`, `Order`, `OrderItem`, `OrderHistory` (+ Repository/모델) | U1 |
| 공통 | 인증 의존성(JWT), 에러 응답 규약, DB 세션 의존성, 시드 스크립트 | U1, U2 |

### 프론트엔드 (Vite + React, `/customer` · `/admin`)
| 영역 | 예상 컴포넌트 | 관련 유닛 |
|---|---|---|
| 고객 화면 | 자동 로그인 부트스트랩, 메뉴 화면(카테고리 탭·카드), 장바구니, 주문 확인/성공, 현재 세션 주문 내역 | U2~U4 |
| 관리자 화면 | 로그인, 태블릿 초기 설정, SSE 대시보드(그리드), 주문 상세 모달, 상태 변경, 메뉴 관리, 과거 내역 | U2~U6 |
| 클라이언트 상태 | 인증 토큰/세션, 장바구니(로컬 지속성), SSE 구독 | U2, U4, U5 |
| API 클라이언트 | REST 호출 래퍼, SSE 클라이언트(재연결) | 전 유닛 |

---

## D. 질문 (Questions)

### Question 1 — 백엔드 계층 구조 (Backend Layering)
FastAPI 백엔드의 컴포넌트 조직 패턴은 무엇으로 할까요?

A) **3계층 (Router → Service → Repository)** — 라우터(HTTP)·서비스(오케스트레이션/규칙)·리포지토리(데이터 접근) 분리. 테스트·PBT에 유리 *(권장)*

B) **2계층 (Router → Service)** — 서비스가 ORM 모델을 직접 다룸. 리포지토리 계층 생략, 구조 단순

C) **기능 모듈별 수직 슬라이스** — 유닛(U2~U6)별 디렉터리에 라우터·서비스·모델을 함께 배치

X) Other (please describe after [Answer]: tag below)

[Answer]: A

### Question 2 — 데이터 접근 방식 (Data Access)
SQLite 데이터 접근은 어떻게 구현할까요?

A) **SQLAlchemy ORM** (선언적 모델 + 세션) — 관계·마이그레이션·타입 안전성에 유리 *(권장)*

B) **SQLModel** (SQLAlchemy + Pydantic 통합) — FastAPI와 모델 일원화, 보일러플레이트 감소

C) **원시 SQL / sqlite3** — 의존성 최소, 단 관계·검증 수동 관리

X) Other (please describe after [Answer]: tag below)

[Answer]: A

### Question 3 — 프론트엔드 컴포넌트 조직 (Frontend Organization)
React 컴포넌트 조직 전략은?

A) **기능(feature) 기반** — `features/menu`, `features/cart`, `features/orders`, `features/admin-dashboard` 등 유닛에 대응하는 폴더 구조 *(권장)*

B) **타입(type) 기반** — `pages/`, `components/`, `hooks/`, `services/` 등 기술 종류별 분리

C) **역할(route) 기반 우선** — `customer/`, `admin/` 최상위 분리 후 내부는 자유

X) Other (please describe after [Answer]: tag below)

[Answer]: A

### Question 4 — 프론트엔드 상태 관리 (Client State)
인증 세션·장바구니·SSE 구독 등 클라이언트 상태 관리 방식은?

A) **React Context + hooks** (경량, 무외부 의존성) + 장바구니는 localStorage 동기화 — 소규모 MVP 적합 *(권장)*

B) **Zustand** (경량 전역 스토어) — 보일러플레이트 적고 확장 용이

C) **Redux Toolkit** — 구조적 엄격함, 단 MVP 대비 과중

X) Other (please describe after [Answer]: tag below)

[Answer]: A

### Question 5 — SSE 이벤트 전파 메커니즘 (Real-Time Broadcast)
관리자 실시간 모니터링(U5)의 서버측 이벤트 전파는 어떻게 설계할까요?

A) **인메모리 pub/sub 브로커** — 주문 생성/상태변경/삭제 시 서버 내부 이벤트를 SSE 구독자에게 브로드캐스트 (단일 프로세스·로컬 MVP 적합) *(권장)*

B) **DB 폴링 기반 스트림** — SSE 핸들러가 주기적으로 DB를 조회해 변경분 전송 (구현 단순, 지연·부하 존재)

C) **asyncio 큐 + 재연결 시 스냅샷 재동기화** — A에 더해 재연결 시 현재 상태 전량 재전송으로 누락 복구 명시

X) Other (please describe after [Answer]: tag below)

[Answer]: A

### Question 6 — 관리자 인증 토큰 저장 (Admin Token Storage)
관리자 JWT(16시간)의 클라이언트 저장 위치는?

A) **localStorage** — 새로고침·16시간 유지 단순, 로컬 데모 적합 *(권장)*

B) **sessionStorage** — 탭 종료 시 소멸 (16시간 유지 요구와 상충 가능)

C) **httpOnly 쿠키** — XSS에 안전하나 로컬 MVP엔 설정 과중 (Security 확장 미적용 상태)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

### Question 7 — API 응답·에러 규약 (API Conventions)
REST 응답 및 에러 형식 규약은?

A) **표준 JSON + 구조화 에러 바디** (`{ "error": { "code", "message", "details" } }`) + 적절한 HTTP 상태코드 — 프론트 일관 처리에 유리 *(권장)*

B) **FastAPI 기본 형식** (`{ "detail": ... }`) 그대로 사용 — 최소 설정

X) Other (please describe after [Answer]: tag below)

[Answer]: A

--- 

## E. 답변 후 진행 (Next)

- 위 질문 답변 → 모호한 부분이 있으면 후속 질문을 추가합니다.
- 확정 후 `aidlc-docs/inception/application-design/`에 5개 산출물을 생성하고 승인 게이트를 제시합니다.
- 이후: **Units Generation**(유닛별 작업 명세) → **CONSTRUCTION Per-Unit Loop**(U1→U6).
