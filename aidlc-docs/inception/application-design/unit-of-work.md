# Unit of Work — 유닛 정의 및 코드 조직 전략

**단계**: INCEPTION — Units Generation (Part 2: Generation)
**분해 방식**: Capability-Based (기능 역량 기반)
**배포 모델**: 단일 배포 가능 애플리케이션 (모놀리식) — 각 유닛은 독립 서비스가 아닌 **논리적 모듈(Module)**
**구축 순서**: **2-Phase 병렬** — Phase 0(U1 공통 기반 + 계약 동결, 1인 선행) → Phase 1(U2~U6 5개 스트림 5인 병렬). 논리 의존 DAG는 여전히 U1→U2→U3→U4→U5→U6이나, 계약 우선(Contract-First)으로 실행을 병렬화. (§5·`parallel-execution.md` 참조)
**근거 문서**: `workflow/workflow.md`, `application-design/{components,services,component-dependency,component-methods}.md`

> 승인된 계획: `plans/unit-of-work-plan.md` (Q1~Q7 모두 권장안 채택).

---

## 1. 유닛 요약 (Unit of Work Summary)

| # | 유닛 | 역량(Capability) | 스토리 | 우선순위 | PBT | 의존 |
|---|---|---|---|---|:--:|---|
| **U1** | Foundation & Data | 스캐폴딩·데이터 모델·시드·공통 인프라 | SD-1~3 | Must | — | 없음 |
| **U2** | Auth & Session | 관리자 인증·테이블 세션 식별·자동 로그인 | A-01~04, C-01, C-02 | Must | — | U1 |
| **U3** | Menu | 메뉴 조회·CRUD·순서·검증 | C-03~06, A-16~18 | Must | 🔬 | U1, U2 |
| **U4** | Cart & Order | 장바구니·주문 생성·현재 세션 조회 | C-07~14 | Must | 🔬 | U1, U2, U3 |
| **U5** | Order Monitoring (SSE) | 실시간 대시보드·상태 전이·직권 삭제 | A-05~10 | Must | 🔬 | U1, U2, U4 |
| **U6** | Session Lifecycle & History | 세션 시작·이용 완료·과거 이력 | A-11~15 | Must | 🔬 | U1, U2, U4, U5 |

> 커버리지: 32/32 스토리 + SD-1~3 시드 태스크. 🔬 = 속성 기반 테스트(PBT) 대상 규칙 포함.

---

## 2. 유닛 상세 (Unit Definitions & Responsibilities)

### U1 — Foundation & Data
- **책임**: 프로젝트 스캐폴딩(Vite+React `/customer`·`/admin`, FastAPI 앱), **전체 SQLite 스키마(9개 모델) 정의**, 시드 스크립트, 백엔드 공통 인프라.
- **소유 컴포넌트**:
  - 백엔드: `AppBootstrap`, `DbSessionProvider`, `ErrorHandler`, `SeedScript`, `HealthRouter`, **데이터 모델 9종** (Store, AdminUser, Table, TableSession, Category, Menu, Order, OrderItem, OrderHistory)
  - 프론트: 앱 셸 라우팅 스켈레톤, `ApiClient` 스켈레톤(공통 REST 래퍼·구조화 에러 파싱)
- **경계**: 비즈니스 규칙 없음. 다른 모든 유닛이 참조하는 **공유 기반**.
- **DoD**: DB 생성·시드 주입 성공, FastAPI/Vite 동시 기동, `/customer`·`/admin` 진입, `/health` 응답.

### U2 — Auth & Session
- **책임**: 관리자 JWT 인증(16h)·로그인 시도 제한, 테이블 태블릿 초기 설정, 테이블 세션 식별·자동 로그인.
- **소유 컴포넌트**:
  - 백엔드: `AuthService`, `AuthRouter`, `AuthDependency`(JWT 검증 의존성), `TableSessionService`(설정·세션 식별 부분), `TableRouter`(setup), `StoreRepo`, `AdminUserRepo`, `TableRepo`, `SessionRepo`(식별)
  - 프론트: `AdminLoginView`, `TableSetupView`, `AutoLoginBootstrap`, `AuthContext`, `TableSessionContext`
- **경계**: 세션 **라이프사이클(시작/완료)**은 U6 소유. U2는 **식별·설정**만.
- **DoD**: 관리자 로그인/16h 만료/새로고침 유지, 태블릿 자동 로그인, 세션 컨텍스트가 이후 주문에 전파.

### U3 — Menu 🔬
- **책임**: 메뉴 CRUD·카테고리별 조회·노출 순서, 고객 메뉴 탐색 UI, 가격/필수 필드 검증.
- **소유 컴포넌트**:
  - 백엔드: `MenuService`, `MenuRouter`, `MenuRepo`, `CategoryRepo`
  - 프론트: `MenuBrowseView`(카테고리 탭·카드·이미지 플레이스홀더·44×44px), `MenuManageView`
- **PBT(🔬)**: 메뉴 가격 검증(>0), 필수 필드 검증 (US-A-16).
- **DoD**: 관리자 변경이 고객 화면 즉시 반영, 검증 오류 처리, 순서 반영.

### U4 — Cart & Order 🔬
- **책임**: 로컬 장바구니(추가/수량/삭제/비우기/지속성), 주문 생성·성공 플로우, 현재 세션 주문 조회.
- **소유 컴포넌트**:
  - 백엔드: `OrderService`(생성·조회 부분), `OrderRouter`, `OrderRepo`
  - 프론트: `CartContext`, `CartView`, `OrderConfirmView`, `OrderSuccessView`, `CurrentOrdersView`
- **계약 의존**: 주문 생성 시 **세션 확보를 U6 TableSessionService에 위임**(§4 참조).
- **PBT(🔬)**: 장바구니 총액 = Σ(단가×수량)·수량≥1 (US-C-08); 로컬 저장 라운드트립 (US-C-11); 주문 총액 = 장바구니 총액 (US-C-12).
- **DoD**: 빈 장바구니 차단, 성공/실패 플로우, 현재 세션 주문만 표시, PBT 통과.

### U5 — Order Monitoring (SSE) 🔬
- **책임**: SSE 실시간 대시보드, 테이블별 카드 그리드, 주문 상세, 상태 전이, 직권 삭제, 테이블 필터.
- **소유 컴포넌트**:
  - 백엔드: `OrderService`(상태 전이·직권 삭제 부분), `AdminOrderRouter`(SSE), `OrderEventBroker`(인메모리 pub/sub)
  - 프론트: `SseClient`(재연결·스냅샷 복구), `MonitoringDashboardView`, `OrderDetailModal`
- **PBT(🔬)**: 상태 전이 규칙(대기중→준비중→완료) (US-A-09); 삭제 후 테이블 총액 = 남은 주문 합 (US-A-10).
- **DoD**: 신규 주문 2초 이내 표시, 재연결 시 누락 복구, 상태 변경이 고객 내역(U4)에 반영, PBT 통과.

### U6 — Session Lifecycle & History 🔬
- **책임**: 세션 시작(첫 주문 트리거), 이용 완료(주문→이력 이동 + 리셋), 과거 내역 조회·날짜 필터.
- **소유 컴포넌트**:
  - 백엔드: `TableSessionService`(시작·완료 라이프사이클), `HistoryService`, `TableRouter`(close), `HistoryRouter`, `OrderHistoryRepo`
  - 프론트: 이용 완료 확인 플로우, `OrderHistoryView`(역순·날짜 필터·닫기)
- **계약**: `get_or_start_active_session`(U4가 호출), `close_table`(단일 트랜잭션: 이관+삭제+세션 close).
- **PBT(🔬)**: 활성 세션 최대 1개 (US-A-11); 완료 처리 무손실(이관 건수=원 건수) (US-A-12).
- **DoD**: 완료 후 현재 총액 0·이력 보존, 새 고객이 이전 주문 없이 시작, 날짜 필터 동작, PBT 통과.

---

## 3. 코드 조직 전략 (Code Organization — Greenfield)

**결정(Q2 + 병렬 최적화)**: 모놀리식 단일 리포에서 **프론트/백엔드 분리 + 계층/기능 폴더 조직**. 유닛은 별도 최상위 폴더가 아니라 계층·기능 폴더 내부의 **파일 그룹**으로 존재합니다. **병렬 5인 작업을 위해, 다유닛 공유 파일(order_service, table_session_service, table router)은 관심사별로 분리하여 "1파일 = 1스트림 소유"를 달성** → 머지 충돌 핫스팟 제거.

```
table-order/
├── backend/                         # FastAPI (Python)
│   ├── app/
│   │   ├── main.py                  # AppBootstrap (U1/Phase0)
│   │   ├── db.py                    # DbSessionProvider (U1)
│   │   ├── errors.py                # ErrorHandler + 공통 에러코드 enum (U1)
│   │   ├── seed.py                  # SeedScript (U1)
│   │   ├── schemas/                 # 전 엔드포인트 Pydantic 계약 (U1/Phase0 동결)
│   │   ├── auth/                    # AuthDependency 인터페이스(U1 스텁) + JWT 실구현(U2/A)
│   │   ├── models/                  # 데이터 모델 9종 (U1) — 전체 스키마
│   │   ├── routers/                 # health(U1) auth(U2/A)
│   │   │                            #   table_setup(U2/A) table_close(U6/E)   ← TableRouter 분리
│   │   │                            #   menu(U3/B) order(U4/C) admin_order(U5/D) history(U6/E)
│   │   ├── services/
│   │   │   ├── auth_service.py       # (U2/A)
│   │   │   ├── menu_service.py       # (U3/B)
│   │   │   ├── history_service.py    # (U6/E)
│   │   │   ├── order_event_broker.py # 인터페이스(U1 스텁) + 실구현(U5/D)
│   │   │   ├── order/                # ← order_service 분리 패키지
│   │   │   │   ├── __init__.py       #   파사드/조립 (U1 스텁 동결)
│   │   │   │   ├── create.py         #   create_order·list_* (U4/C)
│   │   │   │   └── admin.py          #   change_status·delete_order (U5/D)
│   │   │   └── table_session/        # ← table_session_service 분리 패키지
│   │   │       ├── __init__.py       #   프로토콜/조립 (U1 스텁 동결)
│   │   │       ├── identify.py       #   setup_table·resolve_session_context (U2/A)
│   │   │       └── lifecycle.py      #   get_or_start_active_session·close_table (U6/E)
│   │   └── repositories/            # store,admin_user,table,session(U2/A) menu,category(U3/B)
│   │                                #   order(U4/C) order_history(U6/E)  ← 각 1스트림 소유
│   └── tests/                       # 단위 테스트 + PBT (Hypothesis)
└── frontend/                        # Vite + React (feature 기반)
    └── src/
        ├── shared/                  # ApiClient(U1), SseClient 인터페이스(U1)+구현(U5/D), 공통 UI
        ├── features/
        │   ├── customer/            # auto-login(U2/A) menu(U3/B) cart-order(U4/C)
        │   │   └── */routes.ts      # ← 라우트 레지스트리(main.tsx 편집 없이 등록)
        │   └── admin/               # login/setup(U2/A) monitoring(U5/D) menu-manage(U3/B) history(U6/E)
        ├── context/                 # AuthContext·TableSessionContext(U2/A) CartContext(U4/C)
        └── main.tsx                 # /customer·/admin 라우팅 (U1) — 레지스트리 수집만
```

- **수직 슬라이스 소유(병렬)**: 각 스트림(A~E)이 라우터/서비스/리포/뷰/컨텍스트를 자기 파일에서 소유 → 동시 편집면 제거.
- **공유 파일 분리(핵심)**: `order_service` → `services/order/{create,admin}.py`, `table_session_service` → `services/table_session/{identify,lifecycle}.py`, TableRouter → `routers/{table_setup,table_close}.py`. 파사드(`__init__.py`)는 Phase 0에서 스텁 동결되어 후속 편집 최소(1~2줄).
- **프론트 라우팅 충돌 제거**: `main.tsx`는 Phase 0 소유. 각 스트림은 `features/*/routes.ts`에 라우트를 export하고 `main.tsx`가 수집 → 스트림이 `main.tsx`를 편집하지 않음.
- **PBT 위치**: `backend/tests/` 하위에 규칙별 property 테스트(Hypothesis). 프론트 라운드트립(장바구니)은 `frontend` 테스트(fast-check).
- **PBT 프레임워크**: Hypothesis(Python), fast-check(TypeScript) — NFR Requirements에서 최종 확정.

---

## 4. 공유 자산 소유권 (Shared / Cross-Cutting Ownership)

**결정(Q3, Q4)**: U1이 공유 기반을 소유하고, 이후 유닛은 참조·확장만 합니다.

| 자산 | 소유 유닛 | 확장/참조 |
|---|---|---|
| 데이터 모델 9종 (전체 스키마) | **U1** (한 번에 정의) | 전 유닛이 참조만 |
| DbSessionProvider / ErrorHandler / AppBootstrap / SeedScript | **U1** | 전 유닛 DI 사용 |
| `ApiClient` (REST 래퍼·에러 파싱) | **U1** (스켈레톤) | 각 유닛이 엔드포인트 추가 |
| `AuthDependency` (JWT 검증) | **U2** | U3/U5/U6 보호 엔드포인트가 사용 |
| `AuthContext` / `TableSessionContext` | **U2** | U4가 세션 컨텍스트 주입 |
| `TableSessionService` | **U2**(식별) + **U6**(라이프사이클) | U4가 세션 시작 호출 |
| `SseClient` / `OrderEventBroker` | **U5** | U4 주문 생성이 이벤트 소스 |
| `CartContext` | **U4** | — |

**세션 시작 계약(Q6)**: 규칙·구현은 **U6**(`TableSessionService.get_or_start_active_session`)이 소유하고, **호출(트리거)은 U4** `OrderService.create_order`가 위임합니다. → `unit-of-work-dependency.md`에 U4→U6 계약 의존으로 명시.

---

## 5. 개발 흐름 (Team Alignment) — 5인 병렬

**결정(개정)**: **총 5인 병렬**. 논리 의존 DAG는 U1→U6로 유지하되, **계약 우선(Contract-First)** + **파일 분리(§3)**로 실행을 2-Phase 병렬화.

### 5.1 Phase 0 — 공통 기반 (1인 선행, 유일한 직렬 구간)
담당 1인이 **U1 실구현 + 전 교차 계약 스텁 동결**을 완성·머지한다.
- U1 실체: 스캐폴딩, 9모델, DbSession, ErrorHandler(+에러코드 enum), 멱등 시드, HealthRouter, ApiClient, `main.tsx`(라우트 레지스트리).
- 계약 동결(시그니처만, `NotImplementedError`/mock): `AuthDependency`, `TableSessionService` 프로토콜(`get_or_start_active_session`·`close_table`·`resolve_session_context`·`setup_table`), `OrderEventBroker`(`publish/subscribe/unsubscribe/snapshot`), 리포 인터페이스(특히 `MenuRepo`), 전 엔드포인트 `schemas/`(Pydantic), 프론트 `AuthContext`·`TableSessionContext`·`CartContext`·`SseClient` 인터페이스.
- **Phase 0 DoD**: DB·시드·기동·`/health` + 전 계약 스텁 임포트/타입체크 통과. 머지 후 5인 착수 신호.
- 병행: 나머지 4인은 대기하지 않고 자기 스트림의 Functional Design 답변·PBT 속성 정의·프론트 목업/테스트 스텁 준비.

### 5.2 Phase 1 — 5개 스트림 병렬 (5인, 계약 스텁 대상 개발)
1스트림 = 1인 = 1유닛. 각 스트림은 §3의 소유 파일만 편집.

| 스트림 | 유닛 | 소유 범위(요약) |
|---|---|---|
| **A** | U2 Auth & Table Setup | AuthDependency 실구현, auth_service, routers/{auth,table_setup}, table_session/identify, {store,admin_user,table,session}Repo, AdminLogin·TableSetup·AutoLogin·Auth/TableSessionContext |
| **B** | U3 Menu | menu_service, routers/menu, {menu,category}Repo, MenuBrowse·MenuManage |
| **C** | U4 Cart & Order | order/create, routers/order, orderRepo, CartContext·Cart·OrderConfirm·OrderSuccess·CurrentOrders |
| **D** | U5 Monitoring(SSE) | order/admin, order_event_broker 실구현, routers/admin_order, SseClient·MonitoringDashboard·OrderDetailModal |
| **E** | U6 Session & History | table_session/lifecycle 실구현, history_service, routers/{table_close,history}, orderHistoryRepo, 이용완료 플로우·OrderHistoryView |

- **권장 머지 순서**(계약 안정 기준): A → B → C → (D, E 병렬) → 파사드/DI 조립 PR. D↔E는 서로 다른 파일이라 순서 무관.
- **계약 변경 규칙(회귀 안전)**: Phase 0 동결 계약을 바꾸려면 소유자+소비자 페어가 합의 후 **스텁을 먼저 갱신**한다. 후행 유닛이 선행 API 계약을 변경할 경우 명시적 갱신 필요.
- **PBT 배정**: B=가격>0·필수필드 / C=총액·수량·로컬 라운드트립 / D=상태전이·삭제후 총액 / E=활성세션≤1·무손실 이관.

> 상세 실행·검증 절차는 `parallel-execution.md` 참조.
