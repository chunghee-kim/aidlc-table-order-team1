# 컴포넌트 메서드 시그니처 (Component Methods)

**단계**: INCEPTION — Application Design (Standard depth)
**범위**: 메서드 **시그니처와 고수준 목적, 입력/출력 타입**. 상세 비즈니스 규칙·엣지 케이스·검증 로직은 CONSTRUCTION 단계 **Functional Design(유닛별)**에서 확정합니다.

> 타입은 개념적 표기(파이썬/타입스크립트 유사)입니다. 최종 스키마(Pydantic/TS 인터페이스)는 Functional Design에서 확정됩니다.
> 🔬 = PBT 대상 규칙을 포함하는 메서드.

---

## 1. 백엔드 — Service 계층

### 1.1 AuthService (U2)
```
authenticate(store_code: str, username: str, password: str) -> AuthResult
    # 자격 검증(bcrypt) + 시도 제한 확인 → JWT(16h) 발급. 목적: 관리자 로그인.
issue_token(admin: AdminUser) -> str
    # 관리자 컨텍스트로 서명된 JWT(16h 만료) 생성.
verify_token(token: str) -> AdminContext
    # JWT 검증·만료 확인 → 관리자 컨텍스트 반환(실패 시 인증 예외).
register_login_attempt(store_code: str, username: str, success: bool) -> None
    # 로그인 시도 기록/제한 카운터 갱신(시도 제한, US-A-03).
```
- 입력/출력: `AuthResult{ token: str, admin: AdminSummary }`, `AdminContext{ admin_id, store_id }`

### 1.2 TableSessionService (U2, U6)
```
setup_table(store_id, table_number: int, table_password: str, actor: AdminContext) -> TableSetupResult
    # 태블릿 초기 설정: 테이블 번호/비밀번호 저장, 중복 안내, 자동 로그인 활성화(US-A-04).
resolve_session_context(store_code, table_number, table_password) -> TableSessionContext
    # 태블릿 자동 로그인: 저장 정보로 store/table 식별 컨텍스트 복원(US-C-01/02).
get_or_start_active_session(table_id) -> TableSession   # 🔬
    # 활성 세션 반환, 없으면 새 세션 시작. 불변식: 테이블당 활성 세션 최대 1개(US-A-11).
close_table(table_id, actor: AdminContext) -> CloseResult   # 🔬
    # 이용 완료: 활성 세션 주문→OrderHistory 무손실 이관 + 현재 상태/총액 리셋(US-A-12).
```
- 출력: `TableSessionContext{ store_id, table_id, session_id }`, `CloseResult{ moved_order_count, closed_at }`

### 1.3 MenuService (U3)
```
list_menus_for_customer(store_id) -> list[MenuView]
    # 고객용: 카테고리별·노출순서 정렬 메뉴 목록(is_available 반영).
list_categories(store_id) -> list[CategoryView]
create_menu(data: MenuInput, actor: AdminContext) -> MenuView   # 🔬
    # 메뉴 등록. 검증: 필수 필드, 가격 > 0(US-A-16).
update_menu(menu_id, data: MenuInput, actor: AdminContext) -> MenuView   # 🔬
delete_menu(menu_id, actor: AdminContext) -> None
reorder_menus(category_id, ordered_menu_ids: list[int], actor: AdminContext) -> None
    # 노출 순서 재배치(US-A-18).
```
- 입력: `MenuInput{ name, price, description, category_id, image_url }`

### 1.4 OrderService (U4, U5)
```
create_order(session_ctx: TableSessionContext, items: list[OrderItemInput]) -> OrderView   # 🔬
    # 주문 생성: 세션 확보(get_or_start_active_session), 총액=Σ(단가×수량) 계산,
    #           주문번호 부여, OrderEventBroker에 'order_created' 발행.
    # 규칙: 빈 항목 차단, 주문 총액 = 클라이언트 장바구니 총액 일치(US-C-08/12).
list_current_session_orders(session_id, page: PageParams) -> Page[OrderView]
    # 현재 세션 주문만 시간순 조회(이전/완료 세션 제외, US-C-14).
list_admin_orders(store_id, table_filter: int | None) -> list[OrderView]
    # 관리자 대시보드 초기 스냅샷(테이블 필터, US-A-05/08).
change_status(order_id, next_status: OrderStatus, actor: AdminContext) -> OrderView   # 🔬
    # 상태 전이(대기중→준비중→완료), 허용 전이만. 'order_updated' 발행(US-A-09).
delete_order(order_id, actor: AdminContext) -> TableTotals   # 🔬
    # 직권 삭제 후 테이블 총액 재계산(=남은 주문 합). 'order_deleted' 발행(US-A-10).
```
- 입력/출력: `OrderItemInput{ menu_id, quantity }`, `OrderView{ order_number, table, session_id, items[], total_amount, status, created_at }`, `TableTotals{ table_id, total_amount }`

### 1.5 HistoryService (U6)
```
list_history(store_id, table_filter: int | None, date_range: DateRange | None) -> list[OrderHistoryView]
    # 이용 완료된 세션 이력: 테이블별 시간 역순, 날짜 필터(US-A-13/14).
```
- 출력: `OrderHistoryView{ order_number, items[], total_amount, ordered_at, closed_at }`

### 1.6 OrderEventBroker (U5)
```
subscribe(store_id) -> AsyncIterator[OrderEvent]
    # SSE 구독자 등록 → asyncio 큐 기반 이벤트 스트림 반환.
unsubscribe(subscriber_id) -> None
publish(event: OrderEvent) -> None
    # order_created/updated/deleted 이벤트를 해당 매장 구독자에게 브로드캐스트.
snapshot(store_id, table_filter=None) -> list[OrderView]
    # 재연결 시 현재 활성 주문 전량 스냅샷(누락 복구, US-A-06).
```
- 타입: `OrderEvent{ type: 'order_created'|'order_updated'|'order_deleted', payload: OrderView | {order_id} }`

---

## 2. 백엔드 — Repository 계층
> 순수 데이터 접근. 모든 메서드는 요청 스코프 DB 세션을 받거나 주입받음. 시그니처는 대표 메서드만 표기.

```
AdminUserRepo.find_by_store_and_username(store_code, username) -> AdminUser | None
StoreRepo.find_by_code(store_code) -> Store | None
TableRepo.find_by_number(store_id, table_number) -> Table | None
TableRepo.upsert(table: Table) -> Table
SessionRepo.find_active_by_table(table_id) -> TableSession | None
SessionRepo.create(table_id) -> TableSession
SessionRepo.close(session_id, closed_at) -> None
CategoryRepo.list_by_store(store_id) -> list[Category]
MenuRepo.list_by_store(store_id) -> list[Menu]
MenuRepo.create/update/delete(...) -> Menu | None
MenuRepo.update_order(category_id, ordered_ids) -> None
OrderRepo.create(order, items) -> Order
OrderRepo.list_by_session(session_id) -> list[Order]
OrderRepo.list_active_by_store(store_id, table_filter=None) -> list[Order]
OrderRepo.update_status(order_id, status) -> Order
OrderRepo.delete(order_id) -> None
OrderRepo.sum_total_by_table(table_id) -> Decimal
OrderHistoryRepo.move_session_orders(session_id) -> int   # 이관 건수
OrderHistoryRepo.list(store_id, table_filter, date_range) -> list[OrderHistory]
```

---

## 3. 백엔드 — Router 계층 (API 엔드포인트)
> 라우터는 요청 검증 → 서비스 호출 → 응답 매핑. 상세 요청/응답 스키마는 `application-design.md` §API 계약 참조.

| 라우터 | 메서드·경로 | 위임 | 인증 |
|---|---|---|---|
| HealthRouter | `GET /api/health` | — | 공개 |
| AuthRouter | `POST /api/admin/login` | AuthService.authenticate | 공개 |
| TableRouter | `POST /api/admin/tables/{id}/setup` | TableSessionService.setup_table | 관리자 |
| TableRouter | `POST /api/customer/table-login` | TableSessionService.resolve_session_context | 공개(테이블 비번) |
| TableRouter | `POST /api/admin/tables/{id}/close` | TableSessionService.close_table | 관리자 |
| MenuRouter | `GET /api/menus` | MenuService.list_menus_for_customer | 공개 |
| MenuRouter | `GET /api/categories` | MenuService.list_categories | 공개 |
| MenuRouter | `POST/PUT/DELETE /api/admin/menus[/{id}]` | MenuService.create/update/delete | 관리자 |
| MenuRouter | `PATCH /api/admin/categories/{id}/menu-order` | MenuService.reorder_menus | 관리자 |
| OrderRouter | `POST /api/orders` | OrderService.create_order | 테이블 세션 |
| OrderRouter | `GET /api/orders?session=current` | OrderService.list_current_session_orders | 테이블 세션 |
| AdminOrderRouter | `GET /api/admin/orders/stream` (SSE) | OrderEventBroker.subscribe + snapshot | 관리자 |
| AdminOrderRouter | `GET /api/admin/orders` | OrderService.list_admin_orders | 관리자 |
| AdminOrderRouter | `PATCH /api/admin/orders/{id}/status` | OrderService.change_status | 관리자 |
| AdminOrderRouter | `DELETE /api/admin/orders/{id}` | OrderService.delete_order | 관리자 |
| HistoryRouter | `GET /api/admin/history?table=&date=` | HistoryService.list_history | 관리자 |

---

## 4. 프론트엔드 — 상태·인프라 메서드

### 4.1 AuthContext (U2)
```
login(storeCode, username, password): Promise<void>   // 토큰 발급 → localStorage 저장
logout(): void                                          // 토큰 제거 → 로그인 화면
getToken(): string | null
isAuthenticated(): boolean                              // 만료(16h) 포함 검사
```

### 4.2 TableSessionContext (U2, U4)
```
bootstrap(): Promise<void>          // localStorage 설정 → resolve_session_context 호출, 새로고침 유지
getContext(): { storeId, tableId, sessionId } | null
isConfigured(): boolean             // 미설정 시 초기 설정 안내
```

### 4.3 CartContext (U4) 🔬
```
addItem(menu): void                 // 없으면 수량1, 있으면 +1
setQuantity(menuId, qty): void      // qty<=0 이면 제거 (수량 ≥ 1 정수)
removeItem(menuId): void
clear(): void
getTotal(): number                  // Σ(단가 × 수량)
getItems(): CartItem[]
// 모든 변경은 localStorage 동기화. 라운드트립: 저장→복원=원본(US-C-11).
```

### 4.4 ApiClient (전 유닛)
```
get(path, opts): Promise<T>
post(path, body, opts): Promise<T>
patch(path, body, opts): Promise<T>
delete(path, opts): Promise<T>
// 인증 헤더 주입, 구조화 에러 바디 파싱 → ApiError{ code, message, details } throw
```

### 4.5 SseClient (U5)
```
connect(url, onEvent): void         // EventSource 구독
disconnect(): void
// 자동 재연결(백오프), 재연결 시 스냅샷 이벤트로 누락 반영(US-A-06)
```

---

## 5. 프론트엔드 — 주요 뷰 컴포넌트 핸들러(대표)
> 뷰는 Context 훅과 ApiClient/SseClient를 통해 동작. 상세 UX·검증은 Functional Design에서.

| 뷰 | 대표 핸들러 |
|---|---|
| MenuBrowseView | `selectCategory(id)`, `addToCart(menu)` |
| CartView | `changeQty(id, delta)`, `removeItem(id)`, `clearCart()`, `goToConfirm()` |
| OrderConfirmView | `confirmOrder()` → `POST /api/orders` (빈 장바구니 차단) |
| OrderSuccessView | `showOrderNumber()`, `autoRedirect(5s)` |
| CurrentOrdersView | `loadPage(cursor)` → `GET /api/orders?session=current` |
| AdminLoginView | `submitLogin()` → AuthContext.login |
| TableSetupView | `saveSetup()` → `POST /api/admin/tables/{id}/setup` |
| MonitoringDashboardView | `subscribeStream()`, `applyTableFilter(n)`, `openDetail(orderId)` |
| OrderDetailModal | `changeStatus(next)`, `deleteOrder()`(확인 팝업) |
| MenuManageView | `save(menu)`, `remove(id)`, `reorder(ids)` |
| OrderHistoryView | `loadHistory(table, dateRange)`, `close()` |

---

## 6. PBT 대상 메서드 매핑 (Functional Design PBT-01 상세화 예정)
| 규칙 | 메서드 | 스토리 |
|---|---|---|
| 총액 = Σ(단가×수량) | OrderService.create_order, CartContext.getTotal | C-08, C-12 |
| 장바구니 로컬 라운드트립 | CartContext(직렬화/복원) | C-11 |
| 상태 전이(허용 전이만) | OrderService.change_status | A-09 |
| 삭제 후 총액=남은 합 | OrderService.delete_order | A-10 |
| 활성 세션 ≤1, 무손실 이관 | TableSessionService.get_or_start_active_session/close_table | A-11, A-12 |
| 가격>0·필수필드 검증 | MenuService.create_menu/update_menu | A-16 |
