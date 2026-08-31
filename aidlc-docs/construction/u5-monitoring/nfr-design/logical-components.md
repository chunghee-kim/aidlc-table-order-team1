# U5 Order Monitoring (SSE) — Logical Components

**단계**: CONSTRUCTION — Phase 1 · 스트림 D [U5] — NFR Design
**범위**: U5의 논리 컴포넌트·책임·상호작용·시퀀스. 동결 계약(`OrderEventBroker` Protocol, `SseClient` 인터페이스, 파사드 시그니처)은 준수하며 세부 구조만 설계.
**근거**: 승인된 NFR Design 계획(Q1~Q6), `nfr-design-patterns.md`, `functional-design/*`.

---

## 1. 컴포넌트 맵

```
[Browser]                                   [FastAPI process]
MonitoringDashboardView                     routers/admin_order.py (SseStreamEndpoint)
  └ useOrderStream ── EventSource ──HTTP──▶  GET /api/admin/orders/stream?token=
       └ orderStreamReducer                    ├─ AuthDependency (Auth-at-connect)
  └ OrderDetailModal ── ApiClient ──HTTP──▶     ├─ StreamingResponse(async gen)
       PATCH/DELETE /api/admin/orders/{id}      │     └ broker.subscribe(store_id) ─┐
                                                ├─ GET /api/admin/orders            │
                                                └─ PATCH/DELETE ─▶ OrderAdminService │
                                                                     ├ OrderRepo     │
                                                                     └ broker.publish┘
                                          services/order_event_broker.py (OrderEventBroker)
                                             ├ subscribers: Map<id, SubscriberQueue>
                                             ├ subscribe / unsubscribe / publish / snapshot
                                             └ SubscriberQueue (asyncio.Queue, maxsize=1000)
```

---

## 2. 백엔드 논리 컴포넌트

### 2.1 OrderEventBroker (`services/order_event_broker.py` — 실구현, U5 소유)
- **책임**: 인메모리 pub/sub. 구독자 레지스트리, store별 fan-out, 스냅샷 생성.
- **상태**: `subscribers: dict[str, Subscriber]` (`Subscriber{id, store_id, queue}`).
- **메서드**(동결 Protocol 준수):
  - `subscribe(store_id) -> AsyncIterator[OrderEvent]`: Subscriber 생성·등록 → **먼저 등록 후** snapshot 프레임 yield → 큐 소비 루프. `finally`에서 `unsubscribe`.
  - `publish(event)`: `event.store_id` 대상 구독자 큐에 `put_nowait`. QueueFull → 해당 구독자 드롭.
  - `unsubscribe(subscriber_id)`: 레지스트리 제거.
  - `snapshot(store_id, table_filter=None) -> list[OrderView]`: OrderRepo로 active 세션 주문 조회 투영.
- **패턴**: In-memory fan-out(§2), Bounded queue+drop(§6), Snapshot-replace(§3).
- **모듈 전역**: `broker` 싱글턴(Phase 0 스텁 → U5가 실구현으로 교체).

### 2.2 SubscriberQueue (논리 — asyncio.Queue 래핑)
- **책임**: 구독자별 이벤트 버퍼. `maxsize=1000`. 비차단 put, 블로킹 get(with 15s timeout for ping).

### 2.3 SseStreamEndpoint (`routers/admin_order.py` — U5 소유)
- **책임**: SSE·관리자 주문 REST 라우팅.
- **엔드포인트**:
  | 메서드 | 경로 | 동작 |
  |---|---|---|
  | GET | `/api/admin/orders/stream?token=` | Auth-at-connect → StreamingResponse(generator) |
  | GET | `/api/admin/orders[?table=]` | `list_admin_orders`(U4/C) 또는 broker.snapshot 재사용 |
  | PATCH | `/api/admin/orders/{id}/status` | `OrderAdminService.change_status` |
  | DELETE | `/api/admin/orders/{id}` | `OrderAdminService.delete_order` |
- **generator 루프**: `try: yield snapshot_frame; while True: e=await wait_for(queue.get(),15); yield frame(e) except Timeout: yield ': ping'; finally: unsubscribe()`.
- **직렬화**: SSE `data: <json>`. 프레임에 `order_id` 병기(스냅샷=`{type:'snapshot',orders:[{order_id,...OrderView}]}`, 증분=`{type,payload}`). `OrderView` 스키마 자체는 불변.
- **패턴**: Auth-at-connect(§9), Keep-alive(§5), Lifecycle finally(§7).

### 2.4 OrderAdminService (`services/order/admin.py` — U5 소유)
- **책임**: `change_status(order_id, next_status, actor)`, `delete_order(order_id, actor)`. 파사드(`services/order/__init__.py`)가 위임.
- **로직**: 조회→검증(전이 규칙/존재)→TX 커밋→`broker.publish`(커밋 후)→반환. 순수 판정 로직(전이·총액 합산)은 **PBT용 순수 함수로 추출**.
- **패턴**: Publish-after-commit(§1).
- **에러**: NOT_FOUND(404)/CONFLICT(409)/VALIDATION(422) via `AppError`(U1).

### 2.5 소비 계약(스텁, 변경 없음)
- `OrderRepo`(U1 Protocol): `get`, `delete`, active 세션 주문 조회, `sum_active_total(table_id, session_id)`. U5는 인터페이스에 대고 개발, 실제 구현/보강은 소유 규칙 따름(조회 계약 필요 시 소유자와 페어 합의).
- `AuthDependency`/`AdminContext`(U2): 토큰 검증 재사용.

---

## 3. 프론트 논리 컴포넌트

### 3.1 SseClient (`shared/api/sse-client.ts` — U5 소유, 인터페이스 동결)
- **책임**: `connect(url, onEvent)` / `disconnect()`. EventSource 생성(쿼리 토큰), JSON 파싱→`onEvent`, `onerror`→백오프 재연결, `disconnect`→close+타이머 취소.
- **패턴**: Backoff reconnect(§4).

### 3.2 useOrderStream (`features/admin/monitoring/useOrderStream.ts` — U5 소유)
- **책임**: SseClient 래핑 훅. mount 시 connect, 이벤트를 `orderStreamReducer`에 dispatch, unmount 시 disconnect. `connState` 노출.

### 3.3 orderStreamReducer (순수 함수)
- **책임**: `(state, event) -> state`. created/updated=upsert, deleted=remove+`table_total`, snapshot=replace(unseen 교집합). 멱등.
- **패턴**: Idempotent pure reducer(§8). vitest 예제 테스트 대상.

### 3.4 View 컴포넌트 (`MonitoringDashboardView`, `TableCard`, `OrderDetailModal`, `TableFilterBar`)
- FD `frontend-components.md` 참조. 상태는 `useReducer` + `useOrderStream`.

---

## 4. 핵심 시퀀스

### 4.1 구독·재동기화 (US-A-06)
```
Dashboard mount → useOrderStream.connect(stream?token)
  → Endpoint: AuthDependency 검증(OK) → broker.subscribe(store)
      → (구독 등록) → snapshot() 계산 → 'snapshot' 프레임 yield
  → 클라이언트 reducer: SNAPSHOT → 전체 replace
  → 이후 order_* 이벤트 → reducer upsert/remove (멱등)
[연결 끊김] → SseClient 백오프 재연결 → 서버 새 snapshot → replace (무손실)
```

### 4.2 상태 변경 (US-A-09)
```
OrderDetailModal.changeStatus(next) → PATCH /status
  → OrderAdminService.change_status: get→transition 검증→TX commit
      → broker.publish(order_updated{order_id, order:OrderView})
  → 모든 구독자 reducer: UPDATE upsert → 배지 갱신
  (실패: 409/404 → 토스트, 상태 이벤트로 자동 정합)
```

### 4.3 삭제 (US-A-10)
```
OrderDetailModal.deleteOrder() → 확인 팝업 → DELETE /{id}
  → OrderAdminService.delete_order: TX(delete+recompute new_total) commit
      → return TableTotals; broker.publish(order_deleted{order_id,table_id,table_total})
  → reducer: DELETE remove + tableTotals[table_id]=table_total
```

---

## 5. 컴포넌트 → NFR/패턴 매핑

| 컴포넌트 | 패턴 | NFR |
|---|---|---|
| OrderEventBroker | fan-out·bounded queue·snapshot | PERF-2, SCAL-1, REL-3/4 |
| SseStreamEndpoint | auth-at-connect·keep-alive·finally | SEC-1, REL-1, MNT |
| OrderAdminService | publish-after-commit | REL-5 |
| SseClient | backoff reconnect | REL-2 |
| orderStreamReducer | idempotent reducer | REL-3, PERF-1 |

---

## 6. 소유·경계 확인

- U5 소유 파일만 편집: `order_event_broker.py`, `services/order/admin.py`, `routers/admin_order.py`, `shared/api/sse-client.ts`, `features/admin/monitoring/*`.
- 동결 계약 불변: `OrderView`/broker Protocol/파사드 시그니처/`SseClient` 인터페이스. `order_id` 병기는 라우터 직렬화 레이어에서 처리(스키마 미변경).
- OrderRepo 조회 계약(active 세션 주문·`sum_active_total`)이 스텁에 없으면 소유자(U1/U4)와 페어 합의 후 스텁 먼저 갱신(parallel-execution §6 규칙).
