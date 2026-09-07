# U6 — Business Rules (Functional Design)

## BR-1. 활성 세션 최대 1개 (US-A-11 🔬)
- `get_or_start_active_session(table_id)`: `find active by (table_id, status='active')` → 있으면 그대로 반환, 없으면 신규 생성(status='active', started_at=utcnow).
- **불변식**: 임의 순서/횟수 호출 후에도 테이블당 active 세션 ≤ 1, close 전까지 동일 세션 id 반환(멱등).
- 동시성: 단일 프로세스 + SQLite(단일 writer) MVP 전제로 조회-후-생성으로 충분(락/부분 유니크 인덱스 미도입).

## BR-2. 이용 완료 = 무손실 이관 + 리셋 (US-A-12 🔬)
- 전제: 테이블에 active 세션 존재. 없으면 `AppError(CONFLICT, "활성 세션이 없습니다")`.
- **단일 트랜잭션 순서**: ① active 세션 확인 → ② 세션 Order.id 목록 캡처 → ③ 각 Order를 OrderHistory 스냅샷으로 insert(ordered_at=created_at, closed_at=공통값) → ④ 원본 Order 물리삭제(OrderItem cascade) → ⑤ session.status='closed', closed_at=공통값 → ⑥ commit.
- **무손실 속성**: `moved_order_count == 원 세션 주문 수`; OrderHistory 건수·items 합계 = 원본. 커밋 후 `sum_total_by_table == 0`, 해당 테이블 active 세션 없음.
- `closed_at`은 트랜잭션 시작 시 `utcnow()` 1회 산출해 OrderHistory·session·CloseResult에 **동일값** 사용.

## BR-3. 대시보드 통지 (Q5=A, 계약 무변경)
- 커밋 성공 **후**, 이관된 각 order_id에 대해 `order_event_broker.broker.publish(OrderEvent(type="order_deleted", payload={"order_id": id}))`.
- broker 미구현(U5/D 미머지) 시 `NotImplementedError`를 **삼켜** close 성공 유지 → U5/D 머지 후 자동 활성.
- 신규 이벤트 타입 추가 없음(broker 계약 동결 준수).

## BR-4. 과거 이력 조회 (US-A-13)
- `list_history(store_id, table_filter, date_range)`: `OrderHistory` ⨝ `Table(id=table_id)` where `store_id` → 시간 역순(`closed_at desc, id desc`) 평면 리스트.
- 매핑: `items_snapshot`(JSON) → `list[OrderItemView]`; order_number/total_amount/ordered_at/closed_at 직결.
- MVP 규모상 페이지네이션 없음(전량).

## BR-5. 날짜 필터 (US-A-14, Q7=A)
- 쿼리 `?table=&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD`(모두 선택).
- 저장은 naive UTC. 필터 기준은 **매장 로컬(KST=UTC+9) 자정 경계**를 서버가 UTC로 환산:
  - `start_utc = date_from 00:00(KST) − 9h`, `end_utc = (date_to + 1일) 00:00(KST) − 9h` (start 포함·end 배타).
  - 한쪽만 주어지면 그쪽 경계만 적용(다른쪽 무한).
- `closed_at` 기준 필터.

## BR-6. 인증·에러 매핑
- 두 라우터 모두 `Depends(get_current_admin)` → `AdminContext{admin_id, store_id}`(Phase 0 stub store_id=1). history는 `store_id`로 스코프.
- 에러: 활성 세션 없음/이미 닫힘 → `CONFLICT(409)`; 잘못된 날짜 형식 → `VALIDATION_ERROR(422)`. 기존 ErrorHandler가 구조화 바디 매핑.

## PBT (Hypothesis) 🔬
- **P1 활성 세션 ≤1·멱등**: 임의 반복 호출 후 active ≤1 & 동일 id.
- **P2 무손실 이관**: 임의 개수(≥0)·구성의 주문 생성 → close → `moved==원수`, 스냅샷 합계=원본, 이후 총액 0 & active 없음.
