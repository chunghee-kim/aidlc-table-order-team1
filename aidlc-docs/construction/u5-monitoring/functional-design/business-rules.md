# U5 Order Monitoring — Business Rules (Functional Design)

**단계**: CONSTRUCTION — Phase 1 · 스트림 D [U5] — Functional Design
**범위**: 상태 전이, 직권 삭제·총액 재계산, 대시보드 집계 범위, 이벤트 발행, SSE 재연결, 인증·에러 매핑. 🔬 = PBT 대상 불변식.
**근거**: 승인된 `plans/u5-monitoring-functional-design-plan.md`(Q1~Q12), `u1-foundation/functional-design/business-rules.md`(에러코드·타임스탬프).

---

## 1. 상태 전이 규칙 🔬 (US-A-09, Q1-A)

**허용 전이표** (forward-only, 인접만):

| 현재 | 요청 | 결과 |
|---|---|---|
| 대기중 | 준비중 | ✅ 커밋 → `order_updated` 발행 |
| 준비중 | 완료 | ✅ 커밋 → `order_updated` 발행 |
| 대기중 | 완료 | ❌ `CONFLICT`(409) — 건너뛰기 금지 |
| 준비중 | 대기중 | ❌ `CONFLICT`(409) — 역행 금지 |
| 완료 | * | ❌ `CONFLICT`(409) — 종결 상태 |
| X | X(동일) | ❌ `CONFLICT`(409) — 무의미 재설정 |
| * | (미정의 문자열) | ❌ `VALIDATION_ERROR`(422) |

- **정의**: `ALLOWED = { 대기중: {준비중}, 준비중: {완료}, 완료: {} }`. `next_status ∈ ALLOWED[current]` 일 때만 허용.
- **BR-U5-1 (Invariant 🔬)**: 임의의 (현재상태, 요청상태) 쌍에 대해 `change_status`는 위 표와 **정확히 일치**한다. 허용 전이는 상태를 `next_status`로 만들고, 그 외 전이는 상태를 **변경하지 않고** 에러를 던진다.
- **BR-U5-2 (Invariant 🔬)**: 상태 그래프는 비순환·단조. 어떤 전이 시퀀스도 `완료` 이후 다른 상태로 되돌아갈 수 없다(도달 불가).
- **PBT-U5-STATE**: 무작위 현재상태·요청상태·전이 시퀀스를 생성 → (a) 허용 전이만 성공, (b) 성공 후 상태==요청, (c) 실패 시 상태 불변, (d) `완료` 도달 후 추가 전이 전부 실패. `Hypothesis` `st.sampled_from(["대기중","준비중","완료"])` + 시퀀스 전략.

---

## 2. 직권 삭제 & 테이블 총액 재계산 🔬 (US-A-10, Q2-A/Q3-A/Q11-A)

- **BR-U5-3**: 삭제는 **상태 무관**(대기중/준비중/완료 모두 삭제 가능, Q2-A). 대상 없음 → `NOT_FOUND`(404).
- **BR-U5-4**: 삭제는 활성 세션의 Order 행 **물리 삭제**(+연관 OrderItem). 이력 이관 대상이 아님(이관은 세션 close 시 U6). 단일 트랜잭션.
- **BR-U5-5 (Invariant 🔬)**: 삭제 후 반환 `TableTotals.total_amount` = **해당 테이블 활성 세션의 남은(삭제되지 않은) 모든 주문 `total_amount` 합**.
  - 형식: `new_total = Σ{ o.total_amount | o.table_id==T ∧ o.session active ∧ o.id ≠ deleted_id }`.
- **BR-U5-6**: 삭제 커밋 후 `order_deleted` 발행, payload `{order_id, table_id, table_total=new_total}`(Q11-A).
- **PBT-U5-DELETE**: 무작위 (테이블의 주문 total_amount 리스트) 생성 → 임의 1건 삭제 → `new_total == sum(others)` 및 `new_total == old_total - deleted.total_amount` 동시 성립 검증. 0건 남으면 `new_total==0`.

---

## 3. 대시보드 집계 범위 (Q3-A)

- **BR-U5-7**: `snapshot`/`GET /api/admin/orders`는 **활성(active) 세션의 주문만** 포함, 상태 무관(대기중·준비중·완료 전부). 세션 close(U6) 후 그 주문들은 대시보드에서 사라진다(이력 이관·물리 삭제).
- **BR-U5-8**: 테이블 카드 총액 = 그 테이블 활성 세션 주문 `total_amount` 합. "최신 주문 n개 미리보기"의 n=3(Q8-A), `created_at` 내림차순.
- **BR-U5-9**: `table_filter` 지정 시 스냅샷은 해당 테이블 주문만. 단, 실시간 화면 필터는 클라이언트 사이드(Q6-A)이며 stream 구독은 항상 store 전체.

---

## 4. 이벤트 발행 규칙 (Q11/Q12)

- **BR-U5-10**: 모든 이벤트는 **DB 커밋 성공 이후에만** 발행(`order_event_broker.py` 계약). 트랜잭션 롤백 시 미발행.
- **BR-U5-11**: `order_updated` payload = 갱신된 `OrderView` 전체 + `order_id`(Q12-A). 고객측(U4) 소비는 U4 소관(U5는 발행까지 책임).
- **BR-U5-12**: fan-out은 **동일 store의 모든 구독자**에게. 구독자별 큐가 가득 차면(비정상 슬로우 컨슈머) 해당 구독자는 드롭/닫고 재연결 시 스냅샷으로 복구(§5).

---

## 5. SSE 연결·재연결 규칙 (US-A-06, Q4-A/Q5-A)

- **BR-U5-13**: `GET /api/admin/orders/stream?token=<JWT>` 로 구독. 토큰은 `AuthDependency`와 동일 검증(Q5-A). 무효/만료 → `UNAUTHORIZED`(401)로 스트림 거부.
- **BR-U5-14 (재연결 복구)**: 스트림 시작 직후 서버는 **스냅샷 프레임 1건**(전체 활성 주문)을 먼저 전송한다. 클라이언트는 이를 받아 로컬 상태를 **완전 대체(replace)** → 끊긴 동안 누락/변경/삭제가 모두 반영됨(2초 이내 정합, US-A-06). 이후 증분 이벤트 수신.
- **BR-U5-15**: 클라이언트 재연결은 지수 백오프(예 1s→2s→4s, 상한 ~10s). `EventSource` 기본 재연결에 더해 상한/지터 적용.
- **BR-U5-16**: 신규 주문 2초 이내 표시 목표(NFR-1) — 인메모리 fan-out은 즉시성 확보. 지연 원인은 네트워크뿐.

---

## 6. 인증·권한·에러 매핑 (Q5/Q10, U1 에러코드 재사용)

| 상황 | ErrorCode | HTTP |
|---|---|---|
| 스트림/REST 토큰 무효·만료·부재 | UNAUTHORIZED | 401 |
| 관리자 아님(권한 없음) | FORBIDDEN | 403 |
| order_id/table 없음, 이미 삭제/이관됨 | NOT_FOUND | 404 |
| 허용되지 않는 상태 전이 | CONFLICT | 409 |
| 미정의 status 문자열 등 요청 검증 실패 | VALIDATION_ERROR | 422 |
| 서버 내부 오류 | INTERNAL | 500 |

- **BR-U5-17 (낙관적 처리, Q10-A)**: 낙관적 락(버전 필드) 미도입. 경합/부재는 위 404/409로 응답하고, 프론트는 에러 표시 후 스냅샷·이벤트로 자기 상태를 자동 정정. 단일 프로세스 SQLite 트랜잭션이 원자성 보장.
- 모든 에러는 구조화 바디 `{error:{code,message,details}}`로 반환(U1 `ErrorHandler`/`AppError` 재사용).

---

## 7. 규칙 → 스토리/PBT 추적

| 규칙 | 스토리 | PBT |
|---|---|---|
| BR-U5-1,2 상태 전이 | US-A-09 | PBT-U5-STATE 🔬 |
| BR-U5-5 삭제 후 총액 | US-A-10 | PBT-U5-DELETE 🔬 |
| BR-U5-7,8 집계 범위·미리보기 | US-A-05 | — |
| BR-U5-11 이벤트 페이로드 | US-A-06,09 | — |
| BR-U5-14 스냅샷 복구 | US-A-06 | — |
| BR-U5-9 필터 | US-A-08 | — |
