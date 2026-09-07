# U4 Cart & Order — Domain Entities (Functional Design)

**단계**: CONSTRUCTION — Phase 1 (U4 Cart & Order, 스트림 C) — Functional Design
**범위**: U4가 **참조/사용**하는 엔티티(U1 소유 스키마)와 **소유하는 뷰/DTO·클라이언트 상태**. 신규 테이블 없음 — U4는 U1의 `Order`/`OrderItem`/`TableSession`/`Menu`/`Table`을 참조하고, 전송·표현 계약(schemas)과 로컬 장바구니 상태를 소유한다.
**근거**: `u1-foundation/domain-entities.md §7·§8`, `schemas/order.py`·`schemas/common.py`(Phase 0 동결), `component-methods.md §4.3`.

## 1. 참조 엔티티 (U1 소유, U4 read/write 경계)
| 엔티티 | U4 접근 | 비고 |
|---|---|---|
| `Order` | **생성/조회** | status='대기중' 초기값, total_amount, order_number 채번. 상태전이/삭제는 U5. |
| `OrderItem` | **생성/조회** | `menu_name`/`unit_price` **스냅샷** 저장(메뉴 변경·삭제와 디커플). quantity ≥ 1. |
| `TableSession` | **조회(위임)** | 세션 확보는 U6 `get_or_start_active_session`에 위임. U4는 session_id만 사용. |
| `Menu` | **조회(단가)** | 단가·이름 스냅샷 원천. 통합 시 `MenuRepo.list_by_store` 경유. |
| `Table` | **조인** | store 스코프 필터(관리자 스냅샷·주문번호 채번)·total 합산 시 조인. |

- U4는 **신규 컬럼/테이블을 추가하지 않는다**(U1 스키마 동결 참조만). 불변식은 서비스+PBT로 강제.

## 2. API 계약 스키마 (Phase 0 동결 — U4 소비)
### CreateOrderRequest (`schemas/order.py`)
```
{ store_id: int, table_id: int, items: [ {menu_id: int, quantity: int} ] }
```
### OrderView (`schemas/common.py`, 공통 프로젝션)
```
{ order_number: str, table_id: int, session_id: int,
  items: [ {menu_name: str, unit_price: int, quantity: int} ],
  total_amount: int, status: str, created_at: datetime }
```
### OrderPage (`schemas/order.py`)
```
{ items: [OrderView], next_cursor: int | null }   # id 커서(무한 스크롤)
```
### PageParams (`schemas/common.py`)
```
{ cursor: int | null, limit: int = 20 }
```

## 3. 서비스 내부 표현 (U4 소유, `services/order/create.py`)
| 타입 | 필드 | 용도 |
|---|---|---|
| `PricedItem` | menu_id, menu_name, unit_price, quantity | 단가 확정된 라인. 순수 총액 계산(🔬)·OrderItem 매핑. |

## 4. 클라이언트 상태 (U4 소유, `context/cart-context.tsx`)
| 타입 | 필드 | 지속성 |
|---|---|---|
| `CartMenu` | id, name, price | 입력(메뉴 카드에서 전달) |
| `CartItem` | menuId, name, unitPrice, quantity(≥1) | `localStorage["cart:v1"]`에 직렬화(US-C-11) |
| `CartContextValue` | addItem/setQuantity/removeItem/clear/getTotal/getItems | 세션 무관 로컬 상태(서버 미전송) |

- 순수 변환/직렬화는 `features/customer/cart-order/cart-logic.ts`(React 비의존) — PBT 대상.

## 5. 데이터 흐름 (요약)
```
[CartItem[]] ──확정──▶ CreateOrderRequest ──▶ create_order
   (localStorage)                               ├─ Menu 단가 스냅샷 → OrderItem
                                                └─ Σ → Order.total_amount
list_current_session_orders(session_id) ──▶ OrderPage(OrderView[]) ──▶ CurrentOrdersView
```

## 6. 불변식(🔬 U4 PBT) 참조 지점
| 불변식 | 지원 스키마/타입 | 강제 위치 |
|---|---|---|
| total_amount = Σ(unit_price × quantity) | `Order.total_amount`, `PricedItem` | `create.py order_total` (Hypothesis) |
| quantity ≥ 1 | `OrderItem.quantity`, `CartItem.quantity` | `_validate_items`, `cart-logic.setQuantity` (Hypothesis/fast-check) |
| 장바구니 로컬 라운드트립 | `CartItem`, localStorage | `cart-logic.{serialize,deserialize}` (fast-check) |
| 주문 총액 = 장바구니 총액 | 동일 Σ 공식 | 백엔드 `order_total` == 프론트 `total` |
