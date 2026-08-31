# 컴포넌트 정의 (Components)

**단계**: INCEPTION — Application Design
**설계 depth**: Standard
**아키텍처 결정 요약** (application-design-plan.md 답변):
- 백엔드: **3계층** (Router → Service → Repository), **SQLAlchemy ORM**
- 프론트엔드: **기능(feature) 기반** 조직, **React Context + hooks** + localStorage
- 실시간: **인메모리 pub/sub 브로커** 기반 SSE
- 인증: 관리자 **JWT(16h) → localStorage**
- API: **구조화 에러 바디** + HTTP 상태코드

> 본 문서는 **고수준 컴포넌트 식별과 책임**을 다룹니다. 메서드 시그니처는 `component-methods.md`, 오케스트레이션은 `services.md`, 의존성은 `component-dependency.md`를 참조하세요. 상세 비즈니스 규칙은 CONSTRUCTION 단계 Functional Design(유닛별)에서 확정됩니다.

---

## 0. 컴포넌트 지도 (Component Map)

```
┌───────────────────────────────── FRONTEND (Vite + React) ─────────────────────────────────┐
│  /customer                                    /admin                                        │
│  ┌────────────────────────┐                  ┌────────────────────────────────┐            │
│  │ CustomerApp             │                  │ AdminApp                        │            │
│  │  ├ AutoLoginBootstrap   │                  │  ├ AdminLoginView               │            │
│  │  ├ MenuBrowseView       │                  │  ├ TableSetupView               │            │
│  │  ├ CartView             │                  │  ├ MonitoringDashboardView(SSE) │            │
│  │  ├ OrderConfirmView     │                  │  ├ OrderDetailModal             │            │
│  │  ├ OrderSuccessView     │                  │  ├ MenuManageView               │            │
│  │  └ CurrentOrdersView    │                  │  └ OrderHistoryView             │            │
│  └────────────────────────┘                  └────────────────────────────────┘            │
│  [State] AuthContext · TableSessionContext · CartContext(localStorage) · SseClient          │
│  [Infra] ApiClient(REST) · SseClient(reconnect)                                             │
└───────────────────────────────────────────┬────────────────────────────────────────────────┘
                                             │ HTTP REST + SSE (JSON, 구조화 에러 바디)
┌────────────────────────────────────────────▼───────────────────────────────────────────────┐
│                                   BACKEND (FastAPI)                                          │
│  [Router 계층]   AuthRouter · TableRouter · MenuRouter · OrderRouter ·                       │
│                  AdminOrderRouter(SSE) · HistoryRouter · HealthRouter                        │
│  [Service 계층]  AuthService · TableSessionService · MenuService · OrderService ·            │
│                  HistoryService · OrderEventBroker(pub/sub)                                  │
│  [Repository]    StoreRepo · AdminUserRepo · TableRepo · SessionRepo · MenuRepo ·            │
│                  CategoryRepo · OrderRepo · OrderHistoryRepo                                 │
│  [공통 인프라]   DB 세션 의존성 · JWT 인증 의존성 · 에러 핸들러 · 시드 스크립트              │
│  [데이터 모델]   Store · AdminUser · Table · TableSession · Category · Menu ·                │
│                  Order · OrderItem · OrderHistory                                           │
└─────────────────────────────────────────────┬───────────────────────────────────────────────┘
                                              │ SQLAlchemy ORM
                                     ┌─────────▼─────────┐
                                     │  SQLite (파일)     │
                                     └───────────────────┘
```

---

## 1. 백엔드 컴포넌트 (Backend)

### 1.1 Router 계층 (HTTP 경계)
라우터는 **HTTP 요청/응답 변환, 입력 검증(Pydantic 스키마), 인증 의존성 부착**만 담당하고, 비즈니스 로직은 서비스에 위임합니다.

| 컴포넌트 | 목적 | 책임 | 유닛 |
|---|---|---|---|
| **HealthRouter** | 헬스체크 | 앱/DB 가용성 확인 | U1 |
| **AuthRouter** | 관리자 인증 | 로그인 요청 처리 → JWT 발급, 시도 제한 표면화 | U2 |
| **TableRouter** | 테이블/태블릿 설정 | 테이블 초기 설정, 이용 완료(close) 요청 접수 | U2, U6 |
| **MenuRouter** | 메뉴 조회/관리 | 고객 메뉴 조회(공개), 관리자 CRUD·순서변경(보호) | U3 |
| **OrderRouter** | 고객 주문 | 주문 생성, 현재 세션 주문 조회 | U4 |
| **AdminOrderRouter** | 관리자 주문·SSE | 실시간 스트림(SSE), 상태 변경, 직권 삭제, 테이블 필터 | U5 |
| **HistoryRouter** | 과거 이력 | 테이블별·날짜별 과거 주문 이력 조회 | U6 |

**인터페이스 특성**: 모든 라우터는 REST(JSON). `AdminOrderRouter`의 stream 엔드포인트만 `text/event-stream`(SSE). 관리자 보호 엔드포인트는 JWT 인증 의존성 필수.

### 1.2 Service 계층 (오케스트레이션·규칙)
서비스는 **유즈케이스 오케스트레이션, 비즈니스 규칙 적용, 트랜잭션 경계**를 담당하며 리포지토리를 통해 데이터에 접근합니다. (상세 규칙은 services.md 및 Functional Design)

| 컴포넌트 | 목적 | 핵심 책임 | 유닛 |
|---|---|---|---|
| **AuthService** | 관리자 인증 | 자격 검증(bcrypt), JWT 발급/검증, 로그인 시도 제한 | U2 |
| **TableSessionService** | 테이블 세션·라이프사이클 | 태블릿 설정, 세션 시작(첫 주문), 활성 세션 최대 1개 보장, 이용 완료(주문→이력 이동 + 리셋) | U2, U6 |
| **MenuService** | 메뉴 | 카테고리별 조회, CRUD, 노출 순서, 가격/필수필드 검증(🔬) | U3 |
| **OrderService** | 주문 | 주문 생성(세션 컨텍스트 결합), 총액 계산(🔬), 현재 세션 조회, 상태 전이(🔬), 직권 삭제 후 총액 재계산(🔬) | U4, U5 |
| **HistoryService** | 과거 이력 | 이용 완료된 세션의 이력 조회, 날짜/테이블 필터 | U6 |
| **OrderEventBroker** | 실시간 이벤트 | 주문 생성/상태변경/삭제 이벤트를 SSE 구독자에게 인메모리 pub/sub 브로드캐스트 | U5 |

> 🔬 = 속성 기반 테스트(PBT) 대상 규칙 포함. 검증 속성은 Functional Design(PBT-01)에서 상세화.

### 1.3 Repository 계층 (데이터 접근)
리포지토리는 **SQLAlchemy 세션을 통한 CRUD·쿼리만** 담당하고 비즈니스 규칙은 포함하지 않습니다.

| 컴포넌트 | 대상 모델 | 책임 |
|---|---|---|
| **StoreRepo** | Store | 매장 조회 |
| **AdminUserRepo** | AdminUser | 관리자 계정 조회(매장·사용자명 기준) |
| **TableRepo** | Table | 테이블 조회/설정 저장 |
| **SessionRepo** | TableSession | 활성 세션 조회, 세션 생성/종료 상태 갱신 |
| **CategoryRepo** | Category | 카테고리 목록 |
| **MenuRepo** | Menu | 메뉴 CRUD, 카테고리별 조회, 순서 갱신 |
| **OrderRepo** | Order, OrderItem | 주문·항목 CRUD, 세션별 조회, 상태 갱신, 삭제 |
| **OrderHistoryRepo** | OrderHistory | 이력 저장(이관), 테이블·날짜별 조회 |

### 1.4 공통 인프라 컴포넌트 (Cross-Cutting)
| 컴포넌트 | 목적 | 책임 | 유닛 |
|---|---|---|---|
| **DbSessionProvider** | DB 세션 의존성 | 요청 스코프 SQLAlchemy 세션 생성/정리 | U1 |
| **AuthDependency** | JWT 인증 의존성 | Authorization 헤더 검증 → 관리자 컨텍스트 주입, 만료(16h) 처리 | U2 |
| **ErrorHandler** | 에러 규약 | 예외 → 구조화 에러 바디(`{error:{code,message,details}}`) + HTTP 상태코드 매핑 | U1 |
| **SeedScript** | 시드 데이터 | 매장1 + 관리자(bcrypt) + 카테고리/메뉴(외부 이미지 URL) + 테이블 10~20개 주입 | U1 |
| **AppBootstrap** | 앱 구동 | FastAPI 앱·라우터 등록, DB 초기화/스키마 생성 | U1 |

### 1.5 데이터 모델 (Domain Models)
> Standard depth 데이터 모델. 필드 타입·상세 제약은 Functional Design에서 확정. 상세 스키마는 `application-design.md` §데이터 모델 참조.

| 모델 | 목적 | 핵심 필드(초안) | 관계 |
|---|---|---|---|
| **Store** | 매장 | id, store_code(식별자), name | 1—N AdminUser, Table, Menu |
| **AdminUser** | 관리자 계정 | id, store_id, username, password_hash(bcrypt) | N—1 Store |
| **Table** | 테이블/태블릿 | id, store_id, table_number, table_password_hash, is_active | N—1 Store, 1—N TableSession |
| **TableSession** | 테이블 세션 | id, table_id, status(active/closed), started_at, closed_at | N—1 Table, 1—N Order |
| **Category** | 메뉴 카테고리 | id, store_id, name, display_order | 1—N Menu |
| **Menu** | 메뉴 항목 | id, store_id, category_id, name, price, description, image_url, display_order, is_available | N—1 Category |
| **Order** | 주문 | id, session_id, table_id, order_number, status(대기중/준비중/완료), total_amount, created_at | N—1 TableSession, 1—N OrderItem |
| **OrderItem** | 주문 항목 | id, order_id, menu_id, menu_name(스냅샷), unit_price(스냅샷), quantity | N—1 Order |
| **OrderHistory** | 과거 이력 | id, table_id, session_id, order_snapshot(주문/항목 스냅샷), total_amount, closed_at | 이관 대상 |

**설계 노트**:
- `OrderItem`은 메뉴명·단가를 **스냅샷**으로 보관 → 이후 메뉴 변경/삭제와 무관하게 이력 무결성 유지.
- 이용 완료 시 세션의 `Order`(+items)를 `OrderHistory`로 **이관**하고 활성 세션을 `closed`로 전환(무손실, 🔬 US-A-12).
- 한 `Table`에 `status=active` `TableSession`은 최대 1개(🔬 US-A-11).

---

## 2. 프론트엔드 컴포넌트 (Frontend)

기능(feature) 기반 조직. `/customer`와 `/admin` 라우트로 분리, 공용 인프라(ApiClient, SseClient, 공통 UI)는 공유.

### 2.1 고객 (Customer Feature)
| 컴포넌트 | 목적 | 책임 | 유닛 |
|---|---|---|---|
| **CustomerApp** | 고객 앱 셸 | 라우팅, 자동 로그인 게이트, 기본 화면=메뉴 | U2, U3 |
| **AutoLoginBootstrap** | 자동 로그인 | localStorage의 테이블 설정 → 세션 컨텍스트 복원, 미설정 시 안내 | U2 |
| **MenuBrowseView** | 메뉴 탐색 | 카테고리 탭, 메뉴 카드(이름/가격/설명/이미지, 플레이스홀더), 44×44px 터치 타깃 | U3 |
| **CartView** | 장바구니 | 담기/수량±/삭제/비우기, 실시간 총액, localStorage 지속 | U4 |
| **OrderConfirmView** | 주문 확인 | 최종 내역 확인, 빈 장바구니 차단, 확정 전송 | U4 |
| **OrderSuccessView** | 주문 성공 | 주문번호 표시 → 장바구니 비움 → 5초 후 메뉴 리다이렉트, 실패 시 장바구니 유지 | U4 |
| **CurrentOrdersView** | 현재 세션 주문 | 현재 세션 주문만 시간순 표시(상태 포함), 이전 세션 제외, 페이지네이션 | U4 |

### 2.2 관리자 (Admin Feature)
| 컴포넌트 | 목적 | 책임 | 유닛 |
|---|---|---|---|
| **AdminApp** | 관리자 앱 셸 | 라우팅, 인증 가드(JWT), 만료 처리 | U2 |
| **AdminLoginView** | 로그인 | 매장식별자·사용자명·비밀번호 입력, 실패/시도제한 표시 | U2 |
| **TableSetupView** | 태블릿 설정 | 테이블 번호/비밀번호 설정, 중복 안내, 자동 로그인 활성화 | U2 |
| **MonitoringDashboardView** | 실시간 대시보드 | SSE 구독, 테이블별 카드 그리드, 총액·최신주문 미리보기, 신규 강조, 테이블 필터 | U5 |
| **OrderDetailModal** | 주문 상세 | 카드 클릭 → 전체 메뉴 목록·총액, 상태 변경, 직권 삭제(확인) | U5 |
| **MenuManageView** | 메뉴 관리 | 등록/수정/삭제/순서변경, 검증 오류 표시 | U3 |
| **OrderHistoryView** | 과거 내역 | 테이블별 역순 이력, 날짜 필터, 닫기 | U6 |

### 2.3 클라이언트 상태·인프라 (Shared)
| 컴포넌트 | 목적 | 책임 | 유닛 |
|---|---|---|---|
| **AuthContext** | 관리자 인증 상태 | JWT(localStorage) 보관/주입, 로그인/로그아웃, 만료 감지 | U2 |
| **TableSessionContext** | 테이블 세션 상태 | store/table/session 식별 컨텍스트(고객), 새로고침 유지 | U2, U4 |
| **CartContext** | 장바구니 상태 | 항목/수량/총액, localStorage 직렬화 라운드트립(🔬 US-C-11) | U4 |
| **ApiClient** | REST 클라이언트 | fetch 래퍼, 인증 헤더 주입, 구조화 에러 파싱 | 전 유닛 |
| **SseClient** | SSE 클라이언트 | EventSource 구독, 자동 재연결, 재연결 시 스냅샷 반영 | U5 |

---

## 3. 컴포넌트 인터페이스 원칙 (Interface Principles)

- **라우터는 얇게**: HTTP ↔ 서비스 위임만. 비즈니스 규칙 금지.
- **서비스는 규칙의 소유자**: 트랜잭션 경계·불변식(총액·상태전이·세션) 보장. PBT 대상 규칙의 진입점.
- **리포지토리는 순수 데이터 접근**: 규칙/오케스트레이션 없음.
- **프론트 상태는 Context로 캡슐화**: 컴포넌트는 훅을 통해서만 상태 접근.
- **에러 규약 단일화**: 백엔드 구조화 에러 바디 ↔ ApiClient 단일 파싱 지점.
- **실시간 단방향**: 서버→클라이언트 SSE. 상태 변경은 REST(PATCH/DELETE) → 브로커가 이벤트 재전파.

---

## 4. 스토리 → 컴포넌트 커버리지 (요약)

| 유닛 | 스토리 | 주요 백엔드 | 주요 프론트 |
|---|---|---|---|
| U1 | SD-1~3 | AppBootstrap, SeedScript, 데이터 모델, DbSessionProvider, ErrorHandler | — |
| U2 | A-01~04, C-01~02 | AuthService, TableSessionService(설정/식별), AuthDependency | AdminLoginView, TableSetupView, AutoLoginBootstrap, AuthContext, TableSessionContext |
| U3 | C-03~06, A-16~18 | MenuService, MenuRepo | MenuBrowseView, MenuManageView |
| U4 | C-07~14 | OrderService(생성/조회), OrderRepo | CartView, CartContext, OrderConfirmView, OrderSuccessView, CurrentOrdersView |
| U5 | A-05~10 | OrderService(상태/삭제), OrderEventBroker, AdminOrderRouter | MonitoringDashboardView, OrderDetailModal, SseClient |
| U6 | A-11~15 | TableSessionService(시작/완료), HistoryService | OrderHistoryView |

전 스토리 32/32 커버.
