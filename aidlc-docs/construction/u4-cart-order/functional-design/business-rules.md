# U4 Cart & Order — Business Rules (Functional Design)

**단계**: CONSTRUCTION — Phase 1 (U4 Cart & Order, 스트림 C) — Functional Design
**범위**: U4가 강제하는 비즈니스 규칙(장바구니·주문 생성·조회). U1 동결 규칙(`u1-foundation/business-rules.md`)을 승계하며, 그 위에 U4 고유 규칙을 정의.
**근거**: `stories.md US-C-07~14`, `u1-foundation/business-rules.md §1·§2·§8`, `unit-of-work-dependency.md §2.1~2.2`. NFR 결정(사용자 승인): 주문번호=매장별 일자별, 현재주문=무한 스크롤, 세션확보=계약 위임만.

## 1. 장바구니 규칙 (US-C-07~11)
- **추가**(C-07): 없는 메뉴는 수량 1로 추가, 이미 있으면 수량 +1. 총 금액 갱신.
- **수량 조절**(C-08 🔬): 수량 증감. **0 이하 불가** → 0 이하로 내리면 항목 제거. 모든 라인 quantity ≥ 1.
- **삭제**(C-09): 특정 항목 제거 후 총액 재계산.
- **비우기**(C-10): 전체 제거.
- **로컬 지속성**(C-11 🔬): 항목·수량을 `localStorage["cart:v1"]`에 저장, 새로고침 시 복원. **직렬화→복원 == 원본**(라운드트립). 주문 확정 전까지 **서버로 전송하지 않음**.
- **총액**(🔬): `getTotal = Σ(unitPrice × quantity)`. 정수 원 단위.

## 2. 주문 생성 규칙 (US-C-12·13 🔬)
- **빈 장바구니 차단**: items 비어있으면 `VALIDATION_ERROR`(422), 주문 생성 안 함. 프론트도 버튼 비활성.
- **수량 검증**: 각 quantity ≥ 1 아니면 `VALIDATION_ERROR`.
- **단가 스냅샷**: 주문 시점 Menu의 `name`/`price`를 OrderItem에 **복사 저장**(이후 메뉴 변경·삭제와 무관하게 과거 주문 무결). 존재하지 않는 menu_id는 `NOT_FOUND`(404).
- **총액 일치**(🔬): `Order.total_amount = Σ(unit_price × quantity)` = 확정 시점 장바구니 총액.
- **세션 확보(위임)**: session_id 없으면 `TableSessionService.get_or_start_active_session(table_id)` 호출(U6/E 소유, 활성 세션 ≤ 1). **U4는 규칙을 구현하지 않고 계약만 호출**.
- **주문번호 채번**: 형식 `YYYYMMDD-###`(`business-rules.md §2` 동결). 당일 프리픽스 최대 순번 +1, `001`부터 3자리 zero-pad. `order_number` **전역 UNIQUE**. 동시성은 SQLite 단일 프로세스 + UNIQUE + 트랜잭션으로 보장.
  - **NFR 결정 주석**: 사용자 승인 "매장별 일자별". 단일 매장 데모에서는 매장 필터 = 전역과 동일. 채번은 store_id 스코프(Table 조인)로 계산하되 UNIQUE·형식은 동결 규칙 준수. **멀티매장 확장 시 재검토 필요**(형식에 매장 구분자 없음).
- **초기 상태**: 신규 주문 `status='대기중'`. 상태 전이는 U5 소유.
- **이벤트 발행**: 커밋 **이후** `OrderEventBroker.publish('order_created', OrderView)`. **best-effort**(브로커 미구현/오류가 주문 성공을 되돌리지 않음).

## 3. 주문 성공/실패 플로우 (US-C-13)
- **성공**: 서버가 주문번호 반환 → 프론트가 번호 표시, **장바구니 자동 비움**, **5초 후 메뉴 화면 자동 리다이렉트**(즉시 이동 버튼도 제공).
- **실패**: 에러 메시지 표시, **장바구니 내용 유지**(재시도 가능).

## 4. 현재 세션 주문 조회 규칙 (US-C-14)
- **범위**: `session_id`로만 필터 → 현재 세션 주문만. 이전/이용완료(closed) 세션 주문은 **표시 안 됨**(세션 close 시 U6가 이력 이관·원본 삭제하므로 자연 배제).
- **정렬**: 시간순(`created_at`, tie-break `id`).
- **각 주문 표시**: 주문번호·시각·메뉴/수량·금액·상태(대기중/준비중/완료).
- **페이지네이션**(NFR: 무한 스크롤): id 커서(`next_cursor`). 센티넬이 뷰포트 진입 시 다음 페이지 로드. `next_cursor=null`이면 종료.

## 5. 에러 코드 매핑 (U1 §8 승계)
| 상황 | ErrorCode | HTTP |
|---|---|---|
| 빈 장바구니·수량 < 1 | VALIDATION_ERROR | 422 |
| 존재하지 않는 메뉴 | NOT_FOUND | 404 |
| (세션 확보 실패 — U6 계약) | (U6 정의) | — |
| 서버 내부 오류 | INTERNAL | 500 |

- 구조화 바디 `{error:{code,message,details}}` 준수. `AppError(ErrorCode.X, ...)` raise.

## 6. 시간·표시 규약 (U1 §1 승계)
- 서버 저장·응답은 **UTC**(`created_at` 등). 프론트가 KST 등 로컬 표시로 변환.

## 7. PBT 배정 (🔬)
| 규칙 | 테스트 위치 | 프레임워크 |
|---|---|---|
| 총액 = Σ(단가×수량) | `backend/tests/test_order_pbt.py` `order_total` | Hypothesis |
| 수량 ≥ 1 / 빈 장바구니 차단 | `test_order_pbt.py` `_validate_items` | Hypothesis |
| 주문번호 증가·001 시작 | `test_order_pbt.py` `next_order_number` | Hypothesis |
| 총액·수량(장바구니) | `cart-logic.test.ts` `total`/`setQuantity` | fast-check |
| 로컬 라운드트립 | `cart-logic.test.ts` `serialize/deserialize` | fast-check |
| 주문 총액 = 장바구니 총액 | 동일 Σ 공식(양측) + 통합 테스트 `test_order_integration.py` | Hypothesis |
