# 컴포넌트 의존성 및 통신 패턴 (Component Dependency)

**단계**: INCEPTION — Application Design (Standard depth)
**범위**: 의존성 매트릭스, 통신 패턴, 데이터 흐름 다이어그램.

---

## 1. 계층 의존 규칙 (Layering Rule)

```
Router  ──▶  Service  ──▶  Repository  ──▶  SQLAlchemy/SQLite
   │            │
   │            └──▶  OrderEventBroker (인프라, 인메모리)
   └── AuthDependency / DbSessionProvider / ErrorHandler (공통 인프라, 횡단)
```

- 의존 방향은 **항상 아래로**(Router→Service→Repository). 역방향·건너뛰기 금지.
- Repository는 다른 Repository/Service에 의존하지 않음(순수 데이터 접근).
- 공통 인프라(Db 세션, 인증, 에러)는 의존성 주입으로 횡단 제공.

---

## 2. 백엔드 서비스 의존성 매트릭스

행(호출자) → 열(피호출). ✔ = 의존.

| 호출자 \ 대상 | AuthSvc | TableSessionSvc | MenuSvc | OrderSvc | HistorySvc | EventBroker |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| **AuthService** | — | | | | | |
| **TableSessionService** | | — | | | | |
| **MenuService** | | | — | | | |
| **OrderService** | | ✔ | ✔(단가) | — | | ✔ |
| **HistoryService** | | | | | — | |
| **OrderEventBroker** | | | | | | — |

> 순환 없음(DAG). OrderService만 다중 의존(세션 확보·단가 확정·이벤트 발행).

### 2.1 서비스 → Repository 매핑
| 서비스 | 사용 Repository |
|---|---|
| AuthService | StoreRepo, AdminUserRepo |
| TableSessionService | TableRepo, SessionRepo, OrderRepo, OrderHistoryRepo |
| MenuService | MenuRepo, CategoryRepo |
| OrderService | OrderRepo, SessionRepo, MenuRepo |
| HistoryService | OrderHistoryRepo |

---

## 3. 라우터 → 서비스 → 인증 매트릭스

| 라우터 | 주 서비스 | 인증 의존성 |
|---|---|---|
| HealthRouter | — | 없음 |
| AuthRouter | AuthService | 없음(로그인) |
| TableRouter | TableSessionService | setup/close=관리자, table-login=테이블 비번 |
| MenuRouter | MenuService | GET=공개, 쓰기=관리자 |
| OrderRouter | OrderService | 테이블 세션 컨텍스트 |
| AdminOrderRouter | OrderService + OrderEventBroker | 관리자(JWT) |
| HistoryRouter | HistoryService | 관리자(JWT) |

---

## 4. 프론트엔드 의존성

```
CustomerApp ──┬── AutoLoginBootstrap ──▶ TableSessionContext ──▶ ApiClient
              ├── MenuBrowseView ───────▶ ApiClient
              ├── CartView / OrderConfirm ─▶ CartContext (localStorage) + ApiClient
              ├── OrderSuccessView ─────▶ CartContext (clear)
              └── CurrentOrdersView ────▶ ApiClient

AdminApp ─────┬── AdminLoginView ───────▶ AuthContext ──▶ ApiClient
              ├── TableSetupView ───────▶ ApiClient (AuthContext 토큰)
              ├── MonitoringDashboardView ─▶ SseClient + ApiClient
              ├── OrderDetailModal ─────▶ ApiClient
              ├── MenuManageView ───────▶ ApiClient
              └── OrderHistoryView ─────▶ ApiClient

[공유 인프라]  ApiClient ──▶ (REST, 구조화 에러 파싱)   SseClient ──▶ (EventSource, 재연결)
[상태]  AuthContext(localStorage JWT) · TableSessionContext(localStorage 설정) · CartContext(localStorage 장바구니)
```

- 모든 뷰는 상태에 **Context 훅**으로만 접근(직접 전역 접근 금지).
- 인증 토큰은 AuthContext가 단일 소유 → ApiClient에 주입.

---

## 5. 통신 패턴 (Communication Patterns)

| 패턴 | 사용처 | 방향 | 비고 |
|---|---|---|---|
| **REST (요청/응답)** | 로그인, 메뉴, 주문 생성/조회, 상태변경, 삭제, 이력 | 클라이언트 ⇄ 서버 | JSON, 구조화 에러 바디 |
| **SSE (서버 푸시)** | 실시간 주문 모니터링 | 서버 → 관리자 | `text/event-stream`, 단방향 |
| **인메모리 pub/sub** | 주문 이벤트 전파 | 서비스 → 브로커 → SSE 구독자 | 커밋 후 발행 |
| **localStorage 지속** | 장바구니, 테이블 설정, JWT | 클라이언트 내부 | 새로고침 유지 |
| **DI (의존성 주입)** | DB 세션, 인증, 에러 | FastAPI Depends | 요청 스코프 |

**실시간 정합성 원칙**: 상태 변경은 REST로 수행 → 서비스가 **커밋 성공 후** 브로커에 발행 → SSE로 구독자 갱신. 클라이언트는 재연결 시 **스냅샷**으로 누락 복구.

---

## 6. 데이터 흐름 다이어그램 (Data Flow)

### 6.1 고객 주문 → 관리자 실시간 반영 (핵심 종단 흐름)
```
 고객 태블릿                     FastAPI                         관리자 대시보드
 ┌─────────┐   POST /api/orders  ┌──────────────┐               ┌──────────────┐
 │CartView │ ──────────────────▶ │ OrderRouter  │               │ Monitoring   │
 │(local)  │                     │  → OrderSvc  │               │ Dashboard    │
 └─────────┘                     │   ├ 세션확보  │               │  (SseClient) │
      ▲                          │   ├ 총액계산  │               └──────▲───────┘
      │  201 order_number        │   ├ OrderRepo│                      │ SSE push
 ┌─────────┐                     │   │  (SQLite)│  publish             │ (≤2초)
 │Success  │ ◀────────────────── │   └ Broker ──┼──────────────────────┘
 │(5s→menu)│                     └──────────────┘  order_created
 └─────────┘
```

### 6.2 이용 완료(세션 마감) 데이터 이관
```
 활성 세션 주문 ──[close_table 단일 트랜잭션]──▶ OrderHistory (스냅샷 이관)
        │                                              │
        ├─ OrderRepo.delete(현재 주문)  ← 현재 목록/총액 0 리셋
        └─ SessionRepo.close(active→closed)
                    │
                    └─▶ Broker.publish(table_reset) ─▶ 대시보드 총액 0
 (무손실: 이관 건수 == 원 주문 건수 · US-A-12 🔬)
```

### 6.3 상태 변경 → 고객/관리자 양쪽 반영
```
관리자 PATCH status ─▶ OrderSvc.change_status(허용 전이만 🔬) ─▶ OrderRepo.update
                                                    └─▶ Broker.publish(order_updated) ─▶ 대시보드
고객 CurrentOrdersView ─ GET /api/orders?session=current ─▶ 갱신된 상태 조회(동일 소스)
```

---

## 7. 유닛 간 의존성 (빌드 순서 근거)

```
U1 Foundation(모델·시드·인프라)
  └─▶ U2 Auth&Session(AuthSvc·TableSessionSvc·AuthDependency)
        └─▶ U3 Menu(MenuSvc)
              └─▶ U4 Cart&Order(OrderSvc 생성/조회, CartContext)
                    └─▶ U5 Monitoring(OrderSvc 상태/삭제, EventBroker, SseClient)
                          └─▶ U6 Session Lifecycle&History(TableSessionSvc.close, HistorySvc)
```
- U2는 전 보호 엔드포인트가 AuthDependency 참조.
- U5·U6는 U4의 Order/Session 모델·데이터에 의존 → 반드시 U4 이후(workflow.md와 일치).

---

## 8. 결합도·응집도 노트
- **낮은 결합**: 라우터↔서비스↔리포지토리 단방향, 서비스 간 DAG. 프론트는 Context로 상태 캡슐화.
- **높은 응집**: 서비스는 유닛(역량) 단위로 응집(Auth/Session/Menu/Order/History).
- **격리된 실시간 관심사**: OrderEventBroker가 SSE 전파를 단일 책임으로 격리 → 도메인 로직과 분리.
- **이력 무결성**: OrderItem·OrderHistory 스냅샷 저장으로 메뉴 변경과 이력 디커플링.
