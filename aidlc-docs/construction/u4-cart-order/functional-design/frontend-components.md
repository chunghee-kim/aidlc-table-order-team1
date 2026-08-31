# U4 Cart & Order — Frontend Components (Functional Design)

**단계**: CONSTRUCTION — Phase 1 (U4 Cart & Order, 스트림 C) — Functional Design
**범위**: U4 소유 프론트 컴포넌트/컨텍스트·라우트·API 호출. 메뉴 탐색(MenuBrowseView)은 U3/B 소유 → U4는 장바구니·주문·현재내역만.
**근거**: `component-methods.md §4.3·§5`, `stories.md US-C-07~14`, `route-registry.ts`(자동 수집 패턴). NFR: 현재주문=무한 스크롤, 성공 후 5초 리다이렉트.

## 1. 컴포넌트 트리 & 소유 파일
```
context/cart-context.tsx           CartProvider/useCart (실구현, localStorage 백엔드)  [소유]
features/customer/cart-order/
  ├─ cart-logic.ts                 순수 장바구니 연산+직렬화 (🔬 fast-check 대상)      [소유]
  ├─ api.ts                        createOrder / fetchCurrentOrders (ApiClient 사용)   [소유]
  ├─ CartView.tsx                  장바구니 조회·수량·삭제·비우기·주문하기            [소유]
  ├─ OrderConfirmView.tsx          최종 확인 + 확정(POST) / 빈 장바구니 차단           [소유]
  ├─ OrderSuccessView.tsx          주문번호 표시·5초 자동 리다이렉트                   [소유]
  ├─ CurrentOrdersView.tsx         현재 세션 주문 무한 스크롤                          [소유]
  └─ routes.tsx                    라우트 레지스트리 export (main.tsx 미편집)          [소유]
```

## 2. 라우트 (customer scope, 자동 수집)
| path | 컴포넌트 | 스토리 |
|---|---|---|
| `/customer/cart` | CartView | C-07~10 |
| `/customer/order/confirm` | OrderConfirmView | C-12 |
| `/customer/order/success` | OrderSuccessView | C-13 |
| `/customer/orders` | CurrentOrdersView | C-14 |
- `routes.tsx`가 `FeatureRoutes{scope:"customer", routes:[…]}` default export → `collectRoutes()`가 수집. **`main.tsx` 편집 안 함**(병렬 충돌 0).

## 3. 컴포넌트 계약 (메서드/이벤트 → 동작)
| 컴포넌트 | 트리거 | 동작 |
|---|---|---|
| `CartView` | 수량 ±, 삭제, 비우기, 주문하기 | `useCart` 조작; 총액 실시간; 빈 장바구니면 액션 비활성 → `/customer/order/confirm` |
| `OrderConfirmView` | `confirm()` | `useTableSession.getContext()`로 store/table 확보 → `createOrder()` → 성공 시 `clear()`+`/order/success`(state.orderNumber), 실패 시 메시지+장바구니 유지. 빈 장바구니/컨텍스트 없음 방어. |
| `OrderSuccessView` | 마운트 | 주문번호 표시, 5초 카운트다운 후 `/customer` 리다이렉트(즉시 이동 버튼) |
| `CurrentOrdersView` | 마운트/스크롤 | `sessionId`(컨텍스트)로 `fetchCurrentOrders(cursor)` → IntersectionObserver 센티넬로 다음 페이지 로드. sessionId 없으면 빈 상태 안내. |

## 4. 소비 컨텍스트/공유 자산 (동결 계약)
| 자산 | 소유 | U4 사용 |
|---|---|---|
| `CartContext` | **U4(본 유닛)** | 실구현 제공 |
| `TableSessionContext.getContext()` | U2/A | store/table/session 주입(주문 생성·현재내역) |
| `ApiClient`(`apiClient`, `ApiError`) | U1 | `/api/orders` POST/GET, 구조화 에러 파싱 |
| `route-registry`(`FeatureRoutes`) | U1 | 라우트 등록 |

## 5. 상태·지속성
- **장바구니**: `useState<CartItem[]>` + `localStorage["cart:v1"]` 동기화(변경 시 저장, 마운트 시 복원). 서버 미전송(확정 시에만 요청 바디로 전송).
- **주문 성공 이동**: React Router `location.state.orderNumber`로 번호 전달(직접 진입 시 폴백 문구).

## 6. 접근성/UX
- 수량/삭제 버튼 최소 터치 타깃 44×44px(태블릿). 에러는 `role="alert"`. 금액은 `Intl.NumberFormat("ko-KR")`.

## 7. 테스트 (🔬)
- `cart-logic.test.ts`(fast-check): 총액 = Σ, 수량 ≥ 1(0 이하 제거), 라운드트립(serialize→deserialize==원본), 가비지 내성. `vitest run` 7 케이스 그린.
- 타입/빌드: `npm run typecheck`·`npm run build` 통과(라우트 자동 수집 포함).
