# 애플리케이션 설계 (Application Design) — 통합본

**프로젝트**: 테이블오더 서비스 (Table Order Service)
**단계**: INCEPTION — Application Design
**설계 depth**: Standard (유닛별 API 계약 + 데이터 모델 + 핵심 컴포넌트)
**입력**: `requirements.md`, `stories.md`(32), `workflow.md`(U1~U6), `personas.md`
**본 문서**: 개별 설계 문서(components / component-methods / services / component-dependency)를 통합하고, **데이터 모델 상세**와 **API 계약**을 추가로 확정합니다.

## 확정된 아키텍처 결정 (Application Design Plan Q1~Q7)
| # | 결정 | 선택 |
|---|---|---|
| Q1 | 백엔드 계층 구조 | **3계층** (Router → Service → Repository) |
| Q2 | 데이터 접근 | **SQLAlchemy ORM** |
| Q3 | 프론트엔드 조직 | **기능(feature) 기반** |
| Q4 | 클라이언트 상태 | **React Context + hooks** + localStorage |
| Q5 | SSE 전파 | **인메모리 pub/sub 브로커** |
| Q6 | 관리자 JWT 저장 | **localStorage** |
| Q7 | API 규약 | **구조화 에러 바디** + HTTP 상태코드 |

---

## 1. 아키텍처 개요 (Architecture Overview)

```
┌──────────────── FRONTEND (Vite + React) ────────────────┐
│  /customer (고객)              /admin (관리자)            │
│  feature: menu·cart·orders     feature: auth·table·       │
│                                monitoring·menu·history    │
│  State: AuthContext · TableSessionContext · CartContext   │
│  Infra: ApiClient(REST) · SseClient(SSE, reconnect)       │
└───────────────────────┬───────────────────────────────────┘
                        │  HTTP REST + SSE (JSON, 구조화 에러)
┌───────────────────────▼───────────────────────────────────┐
│                  BACKEND (FastAPI, 3계층)                  │
│  Router → Service → Repository                             │
│  Cross-cutting: DbSession · AuthDependency(JWT) ·          │
│                 ErrorHandler · SeedScript · EventBroker    │
└───────────────────────┬───────────────────────────────────┘
                        │  SQLAlchemy ORM
                   ┌─────▼─────┐
                   │  SQLite    │
                   └───────────┘
```

상세 컴포넌트/메서드/서비스/의존성은 동일 폴더의 4개 문서를 참조:
- `components.md` — 컴포넌트 정의·책임
- `component-methods.md` — 메서드 시그니처
- `services.md` — 서비스 오케스트레이션
- `component-dependency.md` — 의존성·통신·데이터 흐름

---

## 2. 데이터 모델 상세 (Data Model — Standard Depth)

> 최종 컬럼 타입·인덱스·제약은 Functional Design(U1)에서 확정. 아래는 설계 수준 스키마.

### 2.1 엔티티 관계 (ERD)
```
Store 1──N AdminUser
Store 1──N Table 1──N TableSession 1──N Order 1──N OrderItem
Store 1──N Category 1──N Menu
Order (완료 시) ──▶ OrderHistory (스냅샷 이관)
OrderItem.menu_id ──▶ Menu (참조, 단 menu_name/unit_price는 스냅샷 보관)
```

### 2.2 테이블 정의
| 엔티티 | 필드(초안) | 비고 |
|---|---|---|
| **Store** | id(PK), store_code(uniq), name, created_at | 시드 1개 |
| **AdminUser** | id(PK), store_id(FK), username, password_hash(bcrypt), created_at | (store_id, username) uniq |
| **Table** | id(PK), store_id(FK), table_number, table_password_hash, is_active, created_at | (store_id, table_number) uniq, 10~20개 시드 |
| **TableSession** | id(PK), table_id(FK), status(active/closed), started_at, closed_at(nullable) | 테이블당 active 최대 1 🔬 |
| **Category** | id(PK), store_id(FK), name, display_order | |
| **Menu** | id(PK), store_id(FK), category_id(FK), name, price(>0), description, image_url, display_order, is_available, created_at, updated_at | 외부 이미지 URL |
| **Order** | id(PK), session_id(FK), table_id(FK), order_number(uniq), status(대기중/준비중/완료), total_amount, created_at | |
| **OrderItem** | id(PK), order_id(FK), menu_id(FK), menu_name(스냅샷), unit_price(스냅샷), quantity(≥1) | |
| **OrderHistory** | id(PK), table_id, session_id, order_number, items_snapshot(JSON), total_amount, ordered_at, closed_at | 이용 완료 이관 |

### 2.3 상태·불변식 (🔬 PBT 대상)
- **주문 상태**: `대기중 → 준비중 → 완료` (허용 전이만, US-A-09).
- **주문 총액**: `total_amount = Σ(unit_price × quantity)` (US-C-08/12).
- **테이블 총액**: 삭제 후 `= 남은 주문 합` (US-A-10).
- **세션**: 테이블당 active 최대 1개(US-A-11), 완료 시 무손실 이관(US-A-12).
- **장바구니 라운드트립**: localStorage 저장→복원 = 원본(US-C-11).
- **메뉴 검증**: `price > 0`, 필수 필드(name/price/category)(US-A-16).

---

## 3. API 계약 (API Contracts — Standard Depth)

**공통 규약**
- Base: `/api`. 인증: `Authorization: Bearer <JWT>`(관리자 보호). 컨텐츠: `application/json`(SSE 제외).
- **성공**: 적절한 2xx + 리소스 바디. **에러**: 구조화 바디 + HTTP 상태코드.
```json
{ "error": { "code": "VALIDATION_ERROR", "message": "사람이 읽는 메시지", "details": { "field": "price" } } }
```
- 대표 코드: 400 BAD_REQUEST, 401 UNAUTHORIZED, 403 FORBIDDEN, 404 NOT_FOUND, 409 CONFLICT, 422 VALIDATION_ERROR, 429 TOO_MANY_ATTEMPTS.

### 3.1 인증·테이블 (U2)
| 메서드·경로 | 요청(주요) | 응답(주요) | 인증 |
|---|---|---|---|
| `POST /api/admin/login` | `{store_code, username, password}` | `{token, admin:{id,username,store_id}}` | 공개 |
| `POST /api/admin/tables/{id}/setup` | `{table_number, table_password}` | `{table_id, table_number, auto_login_enabled}` | 관리자 |
| `POST /api/customer/table-login` | `{store_code, table_number, table_password}` | `{store_id, table_id}` | 공개 |

### 3.2 메뉴 (U3)
| 메서드·경로 | 요청 | 응답 | 인증 |
|---|---|---|---|
| `GET /api/categories` | — | `[{id,name,display_order}]` | 공개 |
| `GET /api/menus` | `?category=` | `[{id,name,price,description,image_url,category_id,display_order,is_available}]` | 공개 |
| `POST /api/admin/menus` | `{name,price,description,category_id,image_url}` | 생성된 메뉴 | 관리자 |
| `PUT /api/admin/menus/{id}` | 동일 | 갱신된 메뉴 | 관리자 |
| `DELETE /api/admin/menus/{id}` | — | 204 | 관리자 |
| `PATCH /api/admin/categories/{id}/menu-order` | `{ordered_menu_ids:[...]}` | 204 | 관리자 |

### 3.3 주문 — 고객 (U4)
| 메서드·경로 | 요청 | 응답 | 인증 |
|---|---|---|---|
| `POST /api/orders` | `{store_id, table_id, items:[{menu_id,quantity}]}` | `201 {order_number, session_id, items, total_amount, status, created_at}` | 테이블 세션 |
| `GET /api/orders?session=current` | `?cursor=&limit=` | `{items:[OrderView], next_cursor}` | 테이블 세션 |

### 3.4 주문 모니터링 — 관리자 (U5)
| 메서드·경로 | 요청 | 응답 | 인증 |
|---|---|---|---|
| `GET /api/admin/orders/stream` | (SSE) | `event: order_created|order_updated|order_deleted\ndata: {...}` | 관리자 |
| `GET /api/admin/orders` | `?table=` | `[OrderView]`(초기 스냅샷) | 관리자 |
| `PATCH /api/admin/orders/{id}/status` | `{status:"준비중"}` | 갱신된 OrderView | 관리자 |
| `DELETE /api/admin/orders/{id}` | — | `{table_id, total_amount}` | 관리자 |

### 3.5 세션·이력 (U6)
| 메서드·경로 | 요청 | 응답 | 인증 |
|---|---|---|---|
| `POST /api/admin/tables/{id}/close` | — | `{moved_order_count, closed_at}` | 관리자 |
| `GET /api/admin/history` | `?table=&date_from=&date_to=` | `[{order_number,items,total_amount,ordered_at,closed_at}]` | 관리자 |

### 3.6 헬스 (U1)
| 메서드·경로 | 응답 |
|---|---|
| `GET /api/health` | `{status:"ok", db:"ok"}` |

**공통 타입 `OrderView`**: `{order_number, table_id, session_id, items:[{menu_name, unit_price, quantity}], total_amount, status, created_at}`

---

## 4. 프론트엔드 구조 (Feature-Based)

```
src/
  app/            # 라우팅(/customer, /admin), 앱 셸
  shared/
    api/          # ApiClient, SseClient
    ui/           # 공용 컴포넌트(버튼 44×44px, 카드 등)
  features/
    auth/         # AuthContext, AdminLoginView
    table-session/# TableSessionContext, AutoLoginBootstrap, TableSetupView
    menu/         # MenuBrowseView, MenuManageView
    cart/         # CartContext, CartView (localStorage)
    orders/       # OrderConfirmView, OrderSuccessView, CurrentOrdersView
    monitoring/   # MonitoringDashboardView, OrderDetailModal (SSE)
    history/      # OrderHistoryView
```
- 상태: AuthContext(JWT/localStorage), TableSessionContext(설정/localStorage), CartContext(장바구니/localStorage).
- 터치 UI: 최소 44×44px, 카드 레이아웃(NFR-4).

---

## 5. 유닛 매핑 & 빌드 순서

| 유닛 | 백엔드 | 프론트 | PBT |
|---|---|---|---|
| U1 | 모델·시드·인프라·Health | — | — |
| U2 | AuthService, TableSessionService(설정/식별), AuthDependency | auth, table-session | — |
| U3 | MenuService | menu | 🔬 가격/필수 |
| U4 | OrderService(생성/조회) | cart, orders | 🔬 총액·라운드트립 |
| U5 | OrderService(상태/삭제), EventBroker | monitoring | 🔬 전이·삭제 |
| U6 | TableSessionService(완료), HistoryService | history | 🔬 세션 |

**논리 의존 순서**: U1 → U2 → U3 → U4 → U5 → U6 (Foundation-First, workflow.md 준수)
**실행 모델**: 5인 병렬 · 2-Phase — Phase 0(U1 + 계약 동결, 1인 선행) → Phase 1(U2~U6 5스트림 병렬). 상세: `parallel-execution.md`, `unit-of-work.md §5`.

---

## 6. 횡단 관심사 (Cross-Cutting)
| 관심사 | 처리 | 위치 |
|---|---|---|
| 인증 | JWT(16h) 발급/검증, localStorage 저장 | AuthService, AuthDependency, AuthContext |
| 에러 | 구조화 에러 바디 단일 규약 | ErrorHandler ↔ ApiClient |
| 실시간 | 인메모리 pub/sub, 커밋 후 발행, 재연결 스냅샷 | OrderEventBroker, SseClient |
| 세션 식별/지속 | store/table/session 컨텍스트, 새로고침 유지 | TableSessionService/Context |
| 로컬 지속 | 장바구니·설정·JWT | localStorage(CartContext 등) |
| 시드 | 매장/관리자/메뉴/테이블 | SeedScript(U1) |
| PBT | 6개 규칙 → Functional Design PBT-01 상세화 | U3~U6 서비스 |

---

## 7. 범위 밖(Out of Scope) 재확인
결제/PG, OAuth/2FA, 이미지 업로드/리사이징, 알림(푸시/SMS/이메일/소리), 재고/주방 전달, 분석/리포트, 다국어, 배달/POS 연동 등은 설계에 포함하지 않음(requirements.md §6).

---

## 8. 다음 단계 (Next)
- **Units Generation** — 위 설계를 기반으로 U1~U6 유닛별 작업 명세 생성.
- **CONSTRUCTION (5인 병렬 · 2-Phase)** — Phase 0(U1 + 계약 동결) → Phase 1(U2~U6 5스트림 병렬)로 Functional Design(PBT-01 포함) → NFR → Infrastructure → Code Generation. 상세: `parallel-execution.md`.
