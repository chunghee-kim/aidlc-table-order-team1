# U5 Order Monitoring — Business Logic Model (Functional Design)

**단계**: CONSTRUCTION — Phase 1 · 스트림 D [U5] — Functional Design
**범위**: 대시보드 로드·구독, 상태 변경, 삭제, 재연결 복구의 흐름 + 인메모리 broker 내부 로직 + PBT 속성 명세. 기술 무관(FastAPI/asyncio는 참조로만).
**근거**: 승인된 계획(Q1~Q12), `domain-entities.md`, `business-rules.md`.

---

## 1. 대시보드 초기 로드 → SSE 구독 (US-A-05/06)

```
[MonitoringDashboardView mount]
  1. GET /api/admin/orders            → 초기 스냅샷(list[OrderView+order_id], active 세션)
  2. 카드 그리드 구성: group by table_id, 각 테이블 total = Σ total_amount,
     최신 3개 미리보기(created_at desc)                    (BR-U5-8, Q8)
  3. SseClient.connect("/api/admin/orders/stream?token=JWT", onEvent)
       └ 서버가 최초 'snapshot' 프레임 push → 로컬 상태 replace  (BR-U5-14)
  4. 이후 증분 이벤트(order_created/updated/deleted) 수신 → 로컬 상태 패치
```

> 1번 REST 스냅샷과 3번 스트림 최초 스냅샷은 동일 소스(OrderRepo active 조회). 구현상 스트림만으로도 충분하나, 초기 페인트 지연을 줄이기 위해 REST 1회 + 스트림 replace 병용.

---

## 2. 신규 주문 수신·강조 (US-A-06, Q7-B)

```
onEvent(order_created {order_id, order}):
  - upsert 로컬 맵[order_id] = order
  - 해당 테이블 카드에 항목 추가, 총액 재합산(로컬)
  - unseen 집합에 order_id 추가 → 카드/항목 강조(색상/펄스)
  - 강조는 관리자가 해당 주문을 '열람'할 때까지 유지         (Q7-B)

열람(seen) 처리: openDetail(order_id) 또는 카드 클릭 시
  - unseen 집합에서 order_id 제거 → 강조 해제
```

- **Q7-B 설계 포인트**: 타이머 페이드가 아니라 **주문별 `seen` 상태**를 프론트가 관리. 서버는 seen을 알지 못함(순수 클라이언트 UX 상태). 재연결·스냅샷 replace 시 unseen 집합은 유지하되, 스냅샷에 없어진 주문(삭제/이관)은 unseen에서도 제거.

---

## 3. 상태 변경 흐름 (US-A-09) — `change_status(order_id, next_status, actor)`

```
change_status(order_id, next_status, actor):
  1. actor 관리자 인증 확인(라우터 레벨 AuthDependency)
  2. order = OrderRepo.get(order_id)           ; 없으면 NOT_FOUND(404)
  3. validate next_status ∈ {대기중,준비중,완료} ; 아니면 VALIDATION_ERROR(422)
  4. if next_status ∉ ALLOWED[order.status]:    CONFLICT(409)   (BR-U5-1)
  5. BEGIN TX: order.status = next_status ; COMMIT
  6. view = to_OrderView(order)
  7. broker.publish(order_updated {order_id, order: view})       (BR-U5-10/11)
  8. return view
```

- 실패(2/3/4)는 상태 불변(BR-U5-1). 5 커밋 성공 후에만 7 발행.

---

## 4. 삭제 흐름 (US-A-10) — `delete_order(order_id, actor)`

```
delete_order(order_id, actor):
  1. actor 인증 확인
  2. order = OrderRepo.get(order_id)            ; 없으면 NOT_FOUND(404)
  3. table_id = order.table_id ; session = order.session
  4. BEGIN TX:
       OrderRepo.delete(order_id)  (OrderItem 동반 삭제)
       new_total = OrderRepo.sum_active_total(table_id, session_id)   (BR-U5-5)
     COMMIT
  5. totals = TableTotals{table_id, total_amount=new_total}
  6. broker.publish(order_deleted {order_id, table_id, table_total=new_total})  (Q11)
  7. return totals
```

- 프론트 확인 팝업(US-A-10)은 `OrderDetailModal.deleteOrder()`에서 처리 후 이 API 호출(frontend-components.md §2).

---

## 5. 재연결 복구 (US-A-06, BR-U5-14)

```
[연결 끊김] → SseClient 백오프 재시도(1→2→4…≤10s, 지터)   (BR-U5-15)
[재연결 성공] → 서버가 'snapshot' 프레임 즉시 전송
             → 클라이언트: 로컬 주문 맵/카드 전체 replace
             → 끊긴 동안의 생성/변경/삭제가 결과 상태에 모두 반영
```

- 개별 이벤트 재생(replay) 없음(Q4-A). 스냅샷 replace가 결과 정합을 보장(멱등).

---

## 6. Broker 내부 로직 (인메모리 pub/sub, asyncio)

```
subscribe(store_id) -> AsyncIterator[OrderEvent]:
   sub = Subscriber(id=uuid4, store_id, queue=asyncio.Queue(maxsize=N))
   subscribers[sub.id] = sub
   # 최초 스냅샷 프레임
   yield {type:'snapshot', orders: snapshot(store_id)}   # order_id 병기 직렬화
   try:
     while True:
       event = await sub.queue.get()
       yield event
   finally:
     unsubscribe(sub.id)        # 연결 종료 시 정리

publish(event):
   for sub in subscribers.values() where sub.store_id == event.store_id:
     try: sub.queue.put_nowait(event)
     except QueueFull: drop_and_close(sub)   # 슬로우 컨슈머 → 재연결로 복구 (BR-U5-12)

unsubscribe(subscriber_id):
   subscribers.pop(subscriber_id, None)

snapshot(store_id, table_filter=None) -> list[OrderView]:
   rows = OrderRepo.list_active(store_id, table_filter)   # active 세션만 (BR-U5-7)
   return [ to_OrderView(r) for r in rows ]
```

- `store_id` 라우팅: MVP는 단일 매장이나, 이벤트에 store 대상 개념을 유지해 fan-out을 매장 경계로 제한(멀티 매장 확장 대비, 계약 시그니처와 일치).
- **스냅샷 프레임 직렬화**: SSE `data:` 에 `{type:'snapshot', orders:[{order_id, ...OrderView}]}` JSON. 증분 이벤트도 `order_id` 병기(§domain-entities §4). `OrderView` Pydantic 스키마 자체는 불변(계약 준수) — 라우터 직렬화 레이어에서 `order_id`를 덧붙인다.
- 이벤트 발행 주체: `order_created`는 U4(create), `order_updated`/`order_deleted`는 U5(admin). broker는 U5 소유이나 U4가 `publish`를 호출하는 것은 계약된 소비(§unit-of-work §4).

---

## 7. PBT 속성 명세 🔬 (backend/tests, Hypothesis)

### PBT-U5-STATE — 상태 전이 (BR-U5-1/2)
- 전략: `status = st.sampled_from(["대기중","준비중","완료"])`; 전이 시퀀스 `st.lists(status)`.
- 속성:
  - (a) `next ∈ ALLOWED[cur]` ⇔ `change_status` 성공, 결과 status == next.
  - (b) `next ∉ ALLOWED[cur]` ⇒ CONFLICT/VALIDATION, status 불변.
  - (c) 임의 시퀀스 적용 후 `완료`에 도달하면 그 뒤 모든 전이 실패(단조·비순환).

### PBT-U5-DELETE — 삭제 후 총액 (BR-U5-5)
- 전략: `totals = st.lists(st.integers(min_value=1, max_value=100000), min_size=1)`; 삭제 인덱스 `st.integers(0, len-1)`.
- 속성:
  - `new_total == sum(totals) - totals[i]`
  - `new_total == sum(totals[:i] + totals[i+1:])`
  - 마지막 1건 삭제 시 `new_total == 0`.

> 두 속성은 서비스 순수 로직(전이 판정 함수·총액 합산 함수)을 대상으로 하며 DB 없이도 실행 가능하도록 순수 함수로 추출한다.

---

## 8. 흐름 요약

```
초기: REST 스냅샷 + SSE 스냅샷 replace → 카드 그리드
실시간: order_created(강조/unseen) · order_updated(배지) · order_deleted(제거+총액)
쓰기: change_status(전이검증→커밋→publish) · delete_order(삭제→재계산→publish)
복구: 재연결 → 서버 스냅샷 프레임 → replace(멱등)
```
