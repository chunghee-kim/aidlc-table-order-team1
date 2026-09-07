# U4 Cart & Order — Business Logic Model (Functional Design)

**단계**: CONSTRUCTION — Phase 1 (U4 Cart & Order, 스트림 C) — Functional Design
**범위**: 로컬 장바구니 로직, 주문 생성 흐름(세션 확보 위임·단가 스냅샷·총액·주문번호·이벤트 발행), 현재 세션 주문 조회(무한 스크롤). 소비 계약: `TableSessionService.get_or_start_active_session`(U6/E), Menu 단가(MenuRepo/U3), `OrderEventBroker.publish`(U5/D).
**근거**: `unit-of-work.md §2·§4`, `unit-of-work-dependency.md §2.1~2.2`, `component-methods.md §1.4·§4.3·§5`, `business-rules.md §2`(주문번호), `stories.md US-C-07~14`.

## 1. 주문 생성 흐름 (OrderService.create_order) 🔬
```
POST /api/orders {store_id, table_id, items:[{menu_id, quantity}]}
  → 검증: items 비어있지 않음(빈 장바구니 차단), 각 quantity ≥ 1     # US-C-12
  → 세션 확보(위임): session_ctx.session_id 없으면
        └─ⓒ위임─▶ TableSessionService.get_or_start_active_session(table_id)  # U6/E, 활성 세션 ≤ 1
  → 단가 스냅샷: Menu(store_id, id∈menu_ids) 조회 → 없는 메뉴 있으면 NOT_FOUND
        (단가 원천 = Menu 테이블. 통합 시 MenuRepo.list_by_store로 치환)
  → 총액 = Σ(unit_price × quantity)                                  # 🔬 = 장바구니 총액
  → 주문번호 = YYYYMMDD-###  (당일 최대 순번 +1, 001부터, business-rules §2)
  → Order(status='대기중', total_amount) + OrderItem[](menu_name/unit_price 스냅샷) 저장
  → commit (트랜잭션 경계 = 서비스)
  → (커밋 후) OrderEventBroker.publish('order_created', OrderView)   # U5/D, best-effort
  → 201 OrderView
```
- **트랜잭션**: 서비스가 `SessionLocal()` 열고 commit/rollback 소유(`db.py` 규약). 리포(`SqlOrderRepo`)는 세션 주입.
- **이벤트 발행은 커밋 이후·best-effort**(`unit-of-work-dependency.md §2.2`). 브로커 미구현(U5 이전)/일시 오류가 주문 성공을 되돌리지 않음.
- **에러 플로우**(US-C-13): 실패 시 서버 에러 바디 → 프론트가 메시지 표시하고 **장바구니 유지**.

## 2. 현재 세션 주문 조회 (list_current_session_orders)
```
GET /api/orders?session_id=<id>&cursor=<lastId>&limit=20
  → session_id로만 필터 → 이전/이용완료(closed) 세션 주문 자연 배제  # US-C-14
  → 시간순(created_at, id) 정렬, id 커서 페이지네이션(무한 스크롤)
  → OrderPage{items:[OrderView], next_cursor}
```
- `next_cursor` = 마지막 항목 id(다음 페이지 존재 시), 없으면 `null`. 프론트는 IntersectionObserver 센티넬로 다음 페이지 로드.

## 3. 관리자 스냅샷 (list_admin_orders) — U5/D 소비
```
활성 세션(status='active')에 속한 주문을 store_id로 조회(선택적 table_filter)
  → 시간순 OrderView[] (대시보드 초기 스냅샷, US-A-05/08)
```
- U4가 소유·구현하되 소비자는 U5/D(SSE 대시보드 초기 로드). `services/order/admin.py`(U5)의 상태전이·삭제와는 별개.

## 4. 장바구니 로직 (CartContext, 프론트 로컬) 🔬
```
addItem(menu):      없으면 qty 1, 있으면 qty +1
setQuantity(id,q):  q ≤ 0 이면 항목 제거(0/음수 라인 없음)         # US-C-08
removeItem(id):     해당 항목 제거                                  # US-C-09
clear():            전체 비우기                                     # US-C-10
getTotal():         Σ(unitPrice × quantity)                        # 🔬
지속성:              항목 변경 시 localStorage(cart:v1) 직렬화       # US-C-11
                     초기화 시 복원(save→restore == original), 서버 전송 없음
```
- 순수 로직은 `features/customer/cart-order/cart-logic.ts`로 분리 → React 없이 fast-check PBT 대상.
- 주문 확정 전까지 장바구니는 **클라이언트에만** 존재(서버 미전송, US-C-11).

## 5. 소비 계약 요약 (Integration Contract 준수)
| 계약 | 소유 | U4 소비 방식 | 미구현 시(스텁) 동작 |
|---|---|---|---|
| `get_or_start_active_session(table_id)` | U6/E | session_id 없을 때 호출 | NotImplementedError(계약 위임만 — 답변 채택) |
| Menu 단가(`MenuRepo.list_by_store`) | U3/B | Menu 테이블 직접 조회(통합 시 리포 치환) | Menu 시드 존재 시 동작 |
| `OrderEventBroker.publish` | U5/D | 커밋 후 best-effort 호출 | try/except로 무시(주문 성공 유지) |
| `AuthContext`/`TableSessionContext` | U2/A | 프론트에서 store/table/session 컨텍스트 주입 | null이면 안내 메시지 |

## 6. DoD (U4)
빈 장바구니 차단, 성공/실패 플로우, 현재 세션 주문만 표시, 주문번호 채번, 이벤트 발행(best-effort), **PBT 통과**(백엔드 총액·수량·번호 / 프론트 총액·수량·라운드트립). `pytest`(backend) 13 케이스 + `vitest`(frontend) 7 케이스 그린.
