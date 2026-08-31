# U5 Order Monitoring (SSE) — Functional Design Plan (Part 1: Planning)

**단계**: CONSTRUCTION — **Phase 1 (5스트림 병렬)** · 스트림 **D** [U5] — Functional Design
**유닛**: U5 Order Monitoring (SSE)
**책임**: SSE 실시간 대시보드, 테이블별 카드 그리드, 주문 상세, 상태 전이, 직권 삭제, 테이블 필터.
**커버 스토리**: US-A-05(그리드 대시보드), US-A-06(SSE 실시간 반영·재연결 복구), US-A-07(카드 상세), US-A-08(테이블 필터), US-A-09(상태 전이 🔬), US-A-10(직권 삭제 🔬).
**소유 파일**(parallel-execution.md §4):
- 백엔드: `services/order/admin.py`(`change_status`·`delete_order`), `services/order_event_broker.py`(실구현), `routers/admin_order.py`
- 프론트: `shared/api/sse-client.ts`(실구현), `features/admin/monitoring/*`(`MonitoringDashboardView`·`OrderDetailModal` + `routes.tsx`)
**계약 소비(스텁)**: `OrderRepo`, `AuthDependency`/`AdminContext`, `schemas/{admin_order,common}` (모두 Phase 0 동결).
**PBT(🔬)**: 상태 전이 규칙(대기중→준비중→완료 허용 전이만, US-A-09), 삭제 후 테이블 총액 = 남은 주문 합(US-A-10).

**입력**: `unit-of-work.md §2 U5`, `stories.md US-A-05~10`, `component-methods.md §1.4/1.6/4.5/5`, `application-design.md`, `u1-foundation/functional-design/business-rules.md`(에러코드·타임스탬프).

> **U5 특성**: **읽기 중심 + 실시간 스트리밍 + 소수의 쓰기(상태/삭제)** 유닛. 주문 *생성*·세션 라이프사이클은 소유하지 않음(U4/U6). U5는 **이미 존재하는 주문에 대한 관리자 관찰·상태 조정**과 그 **실시간 전파**에 집중.

---

## 배경: 이미 동결된 계약 (변경하지 않음)

- `OrderEventBroker`(Protocol): `subscribe(store_id)->AsyncIterator[OrderEvent]`, `unsubscribe(subscriber_id)`, `publish(event)`, `snapshot(store_id, table_filter=None)->list[OrderView]`. 이벤트 타입: `order_created|order_updated|order_deleted`.
- 파사드 시그니처: `change_status(order_id, next_status, actor)->OrderView`, `delete_order(order_id, actor)->TableTotals`.
- 라우트: `GET /api/admin/orders/stream`(SSE), `GET /api/admin/orders`, `PATCH /api/admin/orders/{id}/status`, `DELETE /api/admin/orders/{id}` — 모두 관리자 인증.
- 스키마: `ChangeStatusRequest{status}`, `TableTotals{table_id,total_amount}`, `OrderView{order_number,table_id,session_id,items[],total_amount,status,created_at}`.
- 이벤트는 **커밋 이후 발행**(order_event_broker.py 주석). 상태값: `대기중 | 준비중 | 완료`.
- 타임스탬프 UTC 저장(표시는 프론트), 에러 바디 `{error:{code,message,details}}`.

---

## 결정이 필요한 질문 (Questions)

> 각 `[Answer]:` 태그에 답을 채워 주세요. **권장안(A)**대로면 `A` 또는 "권장"만 적으셔도 됩니다. 전부 권장이면 "전부 권장".

### Q1. 상태 전이 규칙 — 방향성 (Business Rules 🔬)
`대기중 → 준비중 → 완료` 전이에서 **역방향/건너뛰기**를 허용할까요? (PBT 불변식의 핵심)
- **A (권장)**: **전진(forward-only) 인접 전이만** 허용 — `대기중→준비중`, `준비중→완료`만 가능. 건너뛰기(`대기중→완료`)·역행(`준비중→대기중`)·동일 상태 재설정은 `CONFLICT`(409) 거부. `완료`는 종결 상태.
- B: 인접 전이 + 역행 허용(실수 정정 목적).
- C: 임의 전이 자유 허용.

[Answer]: A

### Q2. `완료` 주문의 삭제 가능 여부 (Business Rules)
직권 삭제(US-A-10)를 **어떤 상태의 주문**에 허용할까요?
- **A (권장)**: **상태 무관 삭제 허용**(대기중/준비중/완료 모두) — "잘못된 주문 정정" 목적이므로 상태 제약 없음. 삭제 후 테이블 총액 재계산.
- B: `완료` 주문은 삭제 불가(대기중/준비중만).

[Answer]: A

### Q3. 대시보드·총액 계산에 포함되는 주문 범위 (Business Logic / Data Flow)
`GET /api/admin/orders` 스냅샷과 `TableTotals`의 **집계 대상**은?
- **A (권장)**: **현재 활성 세션의 주문 전체**(상태 무관: 대기중·준비중·완료 모두) 포함. 총액 = 활성 세션의 삭제되지 않은 모든 주문 합. 세션 close(U6) 시 해당 주문은 이력으로 이관되어 대시보드에서 사라짐.
- B: `완료` 제외하고 미완료(대기중·준비중)만 대시보드 표시.
- C: 상태별 컬럼(칸반)으로 분리 표시.

[Answer]: A

### Q4. SSE 재연결 시 누락 복구 방식 (Integration / Data Flow — US-A-06)
연결이 끊겼다 복구될 때 누락 주문을 어떻게 반영할까요?
- **A (권장)**: **재연결 시 서버가 최초에 `snapshot`(전체 활성 주문)을 1건 push** → 클라이언트가 현재 상태를 스냅샷으로 **완전 대체(replace)**. 이후 증분 이벤트 수신. (단순·정합성 확실, 소규모 MVP 적합. `Last-Event-ID` 기반 재생은 미도입.)
- B: `Last-Event-ID`로 서버가 놓친 이벤트만 재생(replay).
- C: 재연결 시 클라이언트가 별도 `GET /api/admin/orders`를 호출해 병합.

[Answer]: A

### Q5. SSE 인증 방식 (Integration / Error Handling)
브라우저 `EventSource`는 커스텀 헤더(Authorization)를 못 싣습니다. `/api/admin/orders/stream` 인증을?
- **A (권장)**: **쿼리 파라미터로 토큰 전달**(`/api/admin/orders/stream?token=<JWT>`), 서버가 `AuthDependency`와 동일 검증. (로컬 MVP·HTTPS 아님 전제; 표준 EventSource 사용 가능.)
- B: `fetch` + `ReadableStream`으로 직접 SSE 파싱하여 Authorization 헤더 사용(EventSource 미사용, 재연결 로직 자체 구현).
- C: 쿠키 기반 세션 인증으로 전환.

[Answer]: A

### Q6. 테이블 필터 적용 위치 (Business Logic / Frontend)
US-A-08 테이블 필터를?
- **A (권장)**: **클라이언트 사이드 필터** — SSE는 항상 매장 전체를 구독하고, `applyTableFilter(n)`은 화면 표시만 필터. (재구독 불필요, 즉시 반응. 소규모 데이터 적합.)
- B: 서버 사이드 — 필터 변경 시 stream URL에 `table_filter` 붙여 재구독하고 `snapshot(table_filter)` 재수신.

[Answer]: A

### Q7. 신규 주문 시각 강조 지속 시간 (Frontend — US-A-06)
`order_created` 수신 시 카드 강조(색상/애니메이션)를?
- **A (권장)**: **신규 주문 카드/항목을 약 3초간 하이라이트**(배경 색/펄스) 후 정상 표시로 페이드. 새 이벤트 도착 시 타이머 리셋.
- B: 관리자가 카드를 열람(클릭)할 때까지 하이라이트 유지.
- C: 하이라이트 없이 목록 상단 삽입만.

[Answer]: B

### Q8. 카드 미리보기 "최신 주문 n개" 개수 (Frontend — US-A-05)
테이블 카드에 표시할 최신 주문 미리보기 개수는?
- **A (권장)**: **최신 3개** 주문 미리보기(주문번호·대표 메뉴·상태 요약) + 총액. 전체는 카드 클릭 시 `OrderDetailModal`.
- B: 다른 개수 (직접 기재).

[Answer]: A

### Q9. `OrderDetailModal`이 표시하는 단위 (Frontend — US-A-07)
카드 클릭 상세 모달의 범위는?
- **A (권장)**: **단일 주문 상세** — 클릭한 주문의 전체 메뉴 목록(메뉴명·수량·단가)·총액·상태와 상태 변경/삭제 액션(US-A-09/10)을 제공. (component-methods.md의 `openDetail(orderId)`·`OrderDetailModal.changeStatus/deleteOrder`와 일치.)
- B: 해당 테이블의 모든 주문을 한 모달에 표시.

[Answer]: A

### Q10. 동시 편집/이미 삭제된 주문에 대한 액션 (Error Handling)
두 관리자가 같은 주문을 동시에 다루거나, 이미 삭제/이관된 주문에 상태변경·삭제를 시도하면?
- **A (권장)**: **낙관적 처리** — 대상이 없으면 `NOT_FOUND`(404), 허용되지 않는 전이는 `CONFLICT`(409)를 구조화 에러로 반환. 프론트는 에러 토스트 후 스냅샷/이벤트로 자기 상태를 자동 정정. 별도 낙관적 락 버전 필드는 두지 않음(단일 프로세스 MVP).
- B: 낙관적 락(버전/updated_at 검사) 도입.

[Answer]: A

### Q11. `delete_order`의 응답과 삭제 이벤트 페이로드 (Data Flow / Contract)
삭제 후 반환·전파 내용은? (동결 계약: 반환 `TableTotals`, 이벤트 `order_deleted`)
- **A (권장)**: 반환 = `TableTotals{table_id, total_amount(재계산된 남은 합)}`. `order_deleted` 이벤트 페이로드 = `{order_id, table_id, table_total}` — 구독자가 카드에서 해당 주문 제거 + 테이블 총액 갱신을 한 번에 처리. (broker 주석의 `{order_id}` 최소형에 table 총액 보강 — 계약 주석 범위 내 확정, 스키마 필드 추가 아님.)
- B: `order_deleted` 페이로드는 `{order_id}`만, 프론트가 클라이언트 사이드로 총액 재계산.

[Answer]: A

### Q12. `change_status`의 이벤트 페이로드 (Data Flow / Contract — 고객 반영 연계)
상태 변경 시 `order_updated` 이벤트 페이로드는? (US-A-09: 고객 주문 내역에도 반영)
- **A (권장)**: 페이로드 = **갱신된 `OrderView` 전체**. 관리자 대시보드는 물론, 고객측(U4 CurrentOrders)이 동일 broker/스트림 구독 시 상태 변화를 그대로 반영 가능. (U4는 폴링/자체 조회일 수 있으므로 U5는 이벤트 발행까지만 책임지고, 고객측 소비는 U4 소관으로 명시.)
- B: 페이로드는 `{order_id, status}` 최소형.

[Answer]: A

---

## 계획 실행 체크리스트 (Part 2 = Functional Design 산출물 생성)

> 위 질문 승인 후 아래 산출물을 생성합니다. (functional-design.md Step 6)

- [x] `construction/u5-monitoring/functional-design/domain-entities.md` — U5가 참조하는 엔티티(Order/OrderItem/TableSession) 관점 뷰, `OrderView` 투영 규칙, `OrderEvent` 구조, 상태 enum(대기중/준비중/완료), 인메모리 broker의 구독자 레지스트리 개념 모델.
- [x] `construction/u5-monitoring/functional-design/business-rules.md` — 상태 전이 규칙(허용 전이 표 + 🔬 불변식), 삭제 규칙 및 총액 재계산(🔬 불변식), 대시보드 집계 범위, 이벤트 발행 시점(커밋 후), SSE 재연결/스냅샷 복구 규칙, 인증·에러 매핑(404/409/401).
- [x] `construction/u5-monitoring/functional-design/business-logic-model.md` — 흐름: (1) 대시보드 초기 로드(snapshot) → SSE 구독, (2) 주문 생성 이벤트 수신·강조, (3) 상태 변경 요청→검증→커밋→publish, (4) 삭제→재계산→publish, (5) 재연결 복구, (6) broker publish/subscribe/snapshot 내부 로직(asyncio queue). PBT 속성 명세(상태전이·삭제후총액).
- [x] `construction/u5-monitoring/functional-design/frontend-components.md` — `MonitoringDashboardView`(카드 그리드·필터·강조·구독 라이프사이클), `OrderDetailModal`(상세·상태변경·삭제 확인 팝업), `SseClient`(connect/재연결 백오프/스냅샷 replace), props·state·API 연동 지점, 44×44px 터치 타깃 등 UX 규칙.

---

## 승인 요청

Q1~Q12에 답변을 채워 주시면 분석 후(모호 시 후속 질문) Functional Design 산출물 4종을 생성합니다. 전부 권장안으로 진행하려면 "전부 권장"이라고 답하셔도 됩니다.
