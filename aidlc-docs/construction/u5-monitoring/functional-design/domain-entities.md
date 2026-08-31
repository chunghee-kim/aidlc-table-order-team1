# U5 Order Monitoring — Domain Entities (Functional Design)

**단계**: CONSTRUCTION — Phase 1 · 스트림 D [U5] — Functional Design
**범위**: U5가 **참조/투영**하는 엔티티 관점 뷰 + U5가 **소유**하는 런타임 개념(OrderEvent, 인메모리 구독자 레지스트리). 물리 스키마는 U1이 소유하며 여기서 변경하지 않는다.
**근거**: 승인된 `plans/u5-monitoring-functional-design-plan.md`(Q1~Q12), `u1-foundation/functional-design/domain-entities.md`, `schemas/{common,admin_order}.py`.

---

## 1. 참조 엔티티 (U1 소유 · U5는 읽기/상태변경/삭제만)

### 1.1 Order (참조)
| 필드 | 타입 | U5 용도 |
|---|---|---|
| id | int PK | `change_status`/`delete_order` 대상 식별 |
| order_number | str `YYYYMMDD-###` | 카드/상세 표시 |
| table_id | int FK→Table | 그리드 그룹핑 키, 필터 키, `TableTotals` 키 |
| session_id | int FK→TableSession | 활성 세션 판별(대시보드 집계 범위, Q3) |
| status | str `대기중\|준비중\|완료` | 상태 전이 대상(Q1) |
| total_amount | int | 카드/상세/테이블 총액 집계 원천 |
| created_at | datetime(UTC) | 정렬(최신순), "최신 n개" 미리보기(Q8) |

- **불변 컬럼**: U5는 `status`만 UPDATE, 그리고 행 DELETE. `total_amount`·`items`는 생성 시(U4) 확정된 스냅샷으로 취급.

### 1.2 OrderItem (참조)
`{menu_name, unit_price, quantity}` 스냅샷 보유(U1 규칙 §3). U5는 상세 모달(US-A-07)에서 **읽기 전용**으로 표시. 메뉴 원본이 삭제돼도 무결(스냅샷).

### 1.3 TableSession (참조)
`status ∈ {active, closed}`. U5 대시보드 집계는 **active 세션의 주문만** 포함(Q3-A). U6가 close하면 해당 주문은 이력 이관·물리 삭제되어 broker 스냅샷에서 자연 소멸.

### 1.4 Table (참조)
`table_number` 표시, 12개 그리드 카드의 축. U5는 읽기 전용.

---

## 2. 투영(Projection) 규칙 — `OrderView`

동결 스키마(`schemas/common.py`):

```
OrderView {
  order_number: str
  table_id: int
  session_id: int
  items: [ OrderItemView{ menu_name, unit_price, quantity } ]
  total_amount: int
  status: str          # 대기중 | 준비중 | 완료
  created_at: datetime # UTC (프론트가 KST 표시)
}
```

- **`order_id` 부재 주의**: `OrderView`에는 PK가 없다. `change_status`/`delete_order`/`openDetail`는 **`order_id`(경로 파라미터)** 로 대상을 지정한다. 프론트는 클라이언트 상태에서 `order_id ↔ OrderView`를 맵으로 유지한다.
  - **설계 결정**: broker 이벤트/스냅샷에서 프론트가 항목을 식별·갱신·제거하려면 `order_id`가 필요하다. `OrderView` 스키마(동결)는 변경하지 않고, **SSE 이벤트 페이로드 레벨에서 `order_id`를 병기**한다(§4 참조). REST `GET /api/admin/orders`도 동일하게 이벤트 스냅샷 경로를 재사용하므로 프론트는 이벤트/스냅샷 페이로드의 `order_id`에 의존한다.
- `total_amount = Σ(items.unit_price × items.quantity)` (U4 create 시 확정, U5는 재계산하지 않음).

---

## 3. 상태 값 도메인 (Status Enum)

| 상태 | 의미 | 전이 가능(Q1-A, forward-only) |
|---|---|---|
| `대기중` | 접수, 조리 대기 | → `준비중` |
| `준비중` | 조리 중 | → `완료` |
| `완료` | 조리 완료(종결) | (전이 없음) |

- 역행·건너뛰기·동일상태 재설정 = `CONFLICT`(409). 상세 규칙·PBT는 `business-rules.md §1`.
- 구현 표현: 백엔드 상수/리터럴 집합. 별도 Enum 컬럼 마이그레이션 없음(문자열 저장, U1 §7).

---

## 4. OrderEvent (U5 소유 런타임 모델)

`order_event_broker.py` 동결: `OrderEvent = {'type', 'payload'}`, `type ∈ {order_created, order_updated, order_deleted}`.
아래는 **payload 형식 확정**(Q11/Q12 — 스키마 필드 추가가 아니라 이벤트 dict 페이로드 규약):

| type | 발행 시점 | payload | 소비자 처리 |
|---|---|---|---|
| `order_created` | U4 create_order 커밋 후 | `{ order_id, order: OrderView }` | 카드/항목 삽입, unseen 표시(Q7) |
| `order_updated` | U5 change_status 커밋 후 | `{ order_id, order: OrderView }` (Q12-A: 갱신 OrderView 전체) | 해당 항목 교체, 상태 배지 갱신 |
| `order_deleted` | U5 delete_order 커밋 후 | `{ order_id, table_id, table_total }` (Q11-A) | 항목 제거 + 테이블 총액 갱신 |

- **커밋 후 발행 불변식**: 트랜잭션 커밋이 성공한 뒤에만 publish. 실패 시 미발행 → 구독자 상태와 DB 정합.
- `snapshot(store_id, table_filter=None)` 반환은 `list[OrderView]`(동결). 프론트가 `order_id`를 필요로 하므로, 스냅샷 직렬화 시 각 항목에 `order_id`를 병기하는 SSE 프레임 형식은 `business-logic-model.md §6`에서 확정(스냅샷 프레임 = `{type:'snapshot', orders:[{order_id, ...OrderView}]}`).

---

## 5. 인메모리 구독자 레지스트리 (Broker 개념 모델)

`OrderEventBroker` 실구현(U5 소유)이 관리하는 런타임 상태 — DB 아님, 프로세스 메모리:

```
Broker {
  subscribers: Map<subscriber_id: str, Subscriber>
}
Subscriber {
  id: str            # uuid4, unsubscribe 키
  store_id: int      # 라우팅 대상(매장별 브로드캐스트)
  queue: asyncio.Queue[OrderEvent]   # 이벤트 버퍼
}
```

- `subscribe(store_id)`: Subscriber 생성·등록 → 해당 큐를 `AsyncIterator`로 노출. 스트림 시작 시 최초 1회 스냅샷을 큐에 넣는다(Q4-A, 재연결 복구).
- `publish(event)`: `event`의 store 대상 모든 Subscriber 큐에 fan-out(비차단 put).
- `unsubscribe(subscriber_id)`: 레지스트리에서 제거(연결 종료·클라이언트 이탈 시).
- `snapshot(store_id, table_filter)`: OrderRepo로 **active 세션 주문**을 조회해 `list[OrderView]` 구성(Q3-A). 필터는 서버 스냅샷 파라미터로 지원하되, 실시간 구독 필터링은 클라이언트 사이드(Q6-A)라 stream 구독은 항상 store 전체.
- **단일 프로세스 전제**(MVP): 크로스 프로세스 pub/sub(Redis 등) 없음. `application-design.md` 인메모리 broker 결정과 일치.

---

## 6. 관계 요약 (U5 관점)

```
Table 1─* Order *─1 TableSession(active)
                └─* OrderItem (읽기 전용 스냅샷)

OrderRepo ──(조회)──▶ snapshot() ─┐
change_status/delete_order ─(커밋)─┴─▶ publish(OrderEvent) ─▶ Subscriber.queue ─▶ SSE ─▶ MonitoringDashboardView
```

- U5는 어떤 엔티티도 **생성**하지 않는다. Order 행을 **UPDATE(status)** / **DELETE** 하고, 그 사실을 이벤트로 전파한다.
- 테이블 총액은 파생값: `delete_order` 후 `OrderRepo`로 해당 테이블 활성 세션의 남은 주문 `total_amount` 합을 재계산(`business-rules.md §2`).
