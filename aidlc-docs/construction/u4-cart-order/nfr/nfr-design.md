# U4 Cart & Order — NFR Design (비기능 요구사항 설계)

**단계**: CONSTRUCTION — Phase 1 [U4 / 스트림 C] — NFR 설계
**범위**: `nfr-requirements.md`의 U4 NFR를 **구체 설계 결정 + 코드 반영 지점 + 검증 매핑**으로 확정한다.
**소유 파일**: `backend/app/services/order/create.py`, `backend/app/repositories/order.py`, `frontend/src/context/cart-context.tsx`, `frontend/src/features/customer/cart-order/cart-logic.ts`. (동결 계약은 미변경.)

> 표기: 🔬 = PBT 대상 불변식. 파일 경로는 스트림 C 소유 파일만 편집.

---

## 1. 장바구니 지속성 설계 (U4-NFR-5)

**결정(Q1=A)**: `localStorage` 단일 키에 **무기한** 저장. TTL·만료 로직 없음.

- **저장 키**: `CART_STORAGE_KEY = "cart:v1"` — 스키마 변경 대비 버전 접미사(`v1`). 향후 구조 변경 시 새 키로 마이그레이션(현재 불필요).
- **쓰기 시점**: 장바구니 상태 변경마다 `serialize` 후 저장(`cart-context.tsx`의 `useEffect([items])`).
- **읽기 시점**: Provider 초기화 시 `deserialize`로 복원(`readInitial`).
- **삭제 트리거(U4-NFR-5.3)**: `clear()`(비우기 버튼) 또는 주문 성공 화면 진입 시. 그 외 자동 삭제 없음.
- **손상 내성(U4-NFR-5.4)**: `deserialize`는 (a) `null`/파싱 실패 → `[]`, (b) 배열 아님 → `[]`, (c) 필드 타입/`quantity>=1` 미충족 라인 필터링. **절대 throw하지 않음**. → 🔬 U4-NFR-6.5.

**코드 반영**: `cart-logic.ts`(`serialize`/`deserialize`/`CART_STORAGE_KEY`), `cart-context.tsx`(persist effect + `readInitial`). 이 결정은 기존 구현과 일치하여 추가 변경 없음.

## 2. 주문번호 채번 동시성 설계 (U4-NFR-1.4)

**결정(Q2=A)**: **UNIQUE 제약 + 재시도 루프**.

- **정합성 근원**: `Order.order_number`의 DB **UNIQUE** 제약(U1 스키마, 동결)이 최종 방어선. 애플리케이션 로직이 틀려도 중복은 물리적으로 불가.
- **채번 알고리즘**: `next_order_number(prefix, max_today)` — 오늘자(`YYYYMMDD`) 최대 번호 +1, 없으면 `-001`. 🔬 U4-NFR-6.4.
- **재시도 루프**(`create.py::create_order`):
  1. `max_order_number_today(store_id, prefix)` 조회 → 채번 → `INSERT` → `commit`.
  2. `commit`이 `IntegrityError`(UNIQUE 충돌)면 `rollback` 후 **오늘자 최대번호를 다시 읽어 재채번**.
  3. 최대 `MAX_NUMBER_RETRIES = 5`회. 소진 시 `AppError(ErrorCode.CONFLICT)`(HTTP 409).
- **동시성 전제**: MVP는 **단일 프로세스**(NFR-7 이식성) → 실경합은 드묾. 재시도는 극소 경합·재실행에 대한 정합성 보장. 다중 워커/다중 매장 확장 시 재검토(설계 한계로 명시).
- **금액 무관계 보장**: 재시도 시 가격·총액(`priced`/`total`)은 루프 밖에서 1회 계산 → 재시도는 **번호와 INSERT만** 반복(총액 불변).

**코드 반영**: `create.py`(`MAX_NUMBER_RETRIES`, `IntegrityError` 재시도 루프), `repositories/order.py`(`max_order_number_today` 매장·일자 필터 쿼리).

```
채번 루프 (create_order)
 ┌───────────────────────────────────────────────┐
 │ for attempt in 0..N:                           │
 │   n = next(max_order_number_today(store,day))  │
 │   INSERT order(order_number=n) + items         │
 │   try commit ──success──▶ break                │
 │   except IntegrityError ▶ rollback             │
 │     if last attempt ▶ raise CONFLICT(409)      │
 └───────────────────────────────────────────────┘
```

## 3. 장바구니 한도 설계 (U4-NFR-4.2/4.3)

**결정(Q3=A)**: 항목당 수량 **1~99**, 메뉴 종류 수 **무제한**. **양측 강제**(U4-NFR-4.4).

- **상수**: 백엔드 `MAX_QUANTITY = 99`(`create.py`), 프론트 `MAX_QUANTITY = 99`(`cart-logic.ts`) — 동일 값, 각 계층 소유.
- **프론트(클램프, UX)**: `addItem`은 `min(qty+1, 99)`, `setQuantity(qty)`는 `qty<=0`→제거 / 그 외 `min(qty, 99)`. 사용자는 상한 초과를 만들 수 없음.
- **백엔드(검증, 권위)**: `_validate_items`가 `quantity < 1 or quantity > 99`면 `VALIDATION_ERROR`(400) — 프론트를 우회한 요청도 거부. 🔬 U4-NFR-6.2.
- **항목 수 무제한**: 상한 없음. 총액 계산은 O(n) 합산으로 충분(NFR-1 규모 내).

**코드 반영**: `create.py::_validate_items`(범위 검증), `cart-logic.ts::addItem`/`setQuantity`(클램프).

## 4. 검증(PBT) 설계 (U4-NFR-6)

| 불변식 | 위치 | 테스트 |
|---|---|---|
| 🔬 총액 = Σ(unit_price×qty) = 장바구니 총액 | `order_total` / `total` | `test_order_pbt.py::test_order_total_equals_sum_of_lines`, `cart-logic.test.ts::"total = Σ..."` |
| 🔬 수량 1~99 수용, 그 외 거부 | `_validate_items` | `test_in_range_quantity_accepted`, `test_non_positive_quantity_rejected`, `test_over_cap_quantity_rejected` |
| 🔬 프론트 99 클램프 | `addItem`/`setQuantity` | `cart-logic.test.ts::"setQuantity clamps..."`, `"addItem never exceeds..."` |
| 🔬 라운드트립 무손실 | `serialize`/`deserialize` | `cart-logic.test.ts::"deserialize(serialize(items)) === items"` |
| 🔬 손상 내성 | `deserialize` | `cart-logic.test.ts::"tolerates garbage..."` |
| 🔬 채번 단조 증가/001 시작 | `next_order_number` | `test_next_order_number_increments`, `test_next_order_number_starts_at_001` |

## 5. 이식성 설계 (U4-NFR-7)

- U4는 U1이 제공하는 **인메모리 `OrderEventBroker`** 만 사용(외부 브로커·큐 미도입).
- 지속성은 SQLite(주문) + 브라우저 `localStorage`(장바구니) 뿐 — 추가 데몬 없음.
- 결과: `uvicorn` + `vite`만으로 U4 전 기능 동작(Docker 불필요).

---

## 설계 한계 및 후속 (Overconfidence 방지)

- **채번은 단일 프로세스 전제**: 다중 워커/프로세스에서는 재시도만으로 스루풋 저하 가능 → 그 시점에 DB 시퀀스/락 재검토 필요.
- **매장별 채번**: `max_order_number_today`가 `store_id`로 필터링(`YYYYMMDD-###`는 매장 내 UNIQUE로 해석). 전역 UNIQUE 제약과의 관계는 다매장 확장 시 재검토(기 기록: functional-design/business-rules).
- **성능 수치(p95<300ms)** 는 목표치이며 로컬 벤치 미실측 — 부하 측정은 후속.
- 본 문서 결정은 `nfr-requirements.md`와 승인된 `plans/u4-cart-order-nfr-plan.md` Q1~Q3에 근거하며, 코드/테스트 반영을 완료했다.
