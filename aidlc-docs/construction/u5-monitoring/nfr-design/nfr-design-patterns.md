# U5 Order Monitoring (SSE) — NFR Design Patterns

**단계**: CONSTRUCTION — Phase 1 · 스트림 D [U5] — NFR Design
**범위**: NFR을 충족하는 설계 패턴과 그 근거·트레이드오프. 인프라 매핑은 다음 단계(Infrastructure Design).
**근거**: 승인된 `plans/u5-monitoring-nfr-design-plan.md`(Q1~Q6 전부 A), `nfr-requirements/*`, `functional-design/*`.

---

## 1. Publish-after-Commit (Q1) — 신뢰성/정합성

- **패턴**: 서비스가 **트랜잭션 커밋 성공 직후** `broker.publish(...)`를 **명시 호출**. ORM 훅·아웃박스 미사용.
- **적용**: `OrderAdminService.change_status`/`delete_order`(U5), `create_order`(U4가 호출).
- **충족 NFR**: REL-5(발행 원자성) — 롤백 시 미발행 → 구독자 상태와 DB 정합.
- **트레이드오프**: 발행 코드가 서비스에 노출(명시적, 추적 쉬움) vs 자동화 부재. 단일 프로세스·소규모라 아웃박스(중복 방지/재시도)는 과설계.

## 2. In-memory Pub/Sub Fan-out — 성능/확장

- **패턴**: 단일 프로세스 broker가 store별 구독자 레지스트리를 두고 `publish` 시 **비차단 fan-out**(`put_nowait`).
- **충족 NFR**: PERF-2(fan-out 수 ms), SCAL-1(1~5 구독자). SCAL-2는 broker Protocol 뒤 교체로 확장 여지.
- **트레이드오프**: 프로세스 재시작 시 이벤트 휘발 → 재연결 스냅샷으로 복구(§3). 크로스 프로세스 미지원(MVP 수용).

## 3. Snapshot-Replace 재동기화 (Q3) — 신뢰성 (US-A-06)

- **패턴**: 스트림 시작 시 **구독 등록 → 스냅샷 계산 → snapshot 프레임 yield** 순서 보장. 이후 증분 이벤트는 큐에 순서대로 축적. 클라이언트는 스냅샷을 받아 **전체 replace**.
- **경합 처리**: 구독을 먼저 등록하므로 스냅샷 이후 발생 이벤트는 유실 없이 큐에 적재. 스냅샷↔이벤트 중복은 프론트 `order_id` upsert로 흡수(멱등) → **유실 0, 중복 무해**.
- **충족 NFR**: REL-3(멱등·무손실 복구), PERF-1(재연결 2초 내 정합).
- **트레이드오프**: 개별 이벤트 재생(replay)보다 단순하고 정합 확실. 스냅샷 페이로드가 큼(소규모라 무시 가능).

## 4. Exponential Backoff Reconnect — 신뢰성

- **패턴**: 클라이언트 재연결 지연 **1→2→4s, 상한 10s + 지터**. EventSource 기본 재연결에 상한/지터 부여.
- **충족 NFR**: REL-2. 서버 폭주 방지(thundering herd 완화).

## 5. Keep-alive Heartbeat (Q2) — 신뢰성

- **패턴**: 소비 루프에서 `asyncio.wait_for(queue.get(), timeout=15)` → **타임아웃 시 `: ping` 코멘트 전송**, 이벤트 시 전달. 별도 타이머 태스크 불필요(단일 루프).
- **충족 NFR**: REL-1(유휴 연결 유지·죽은 연결 감지).
- **트레이드오프**: 소비 루프에 ping이 결합(단순) vs 정확한 주기성 약간 손해(무해).

## 6. Bounded Queue + Drop (백프레셔) — 신뢰성

- **패턴**: 구독자 큐 `maxsize=1000`, `put_nowait` 실패(QueueFull) 시 **해당 연결 드롭·정리**. 클라이언트는 재연결 → 스냅샷 복구.
- **충족 NFR**: REL-4. 슬로우 컨슈머가 발행 경로·타 구독자에 영향 없음.
- **트레이드오프**: 극단적 슬로우 컨슈머는 재연결 반복 가능(수용). 무제한 큐(메모리 위험)·블로킹 put(발행 지연) 회피.

## 7. Connection Lifecycle with `finally` (Q2) — 자원 관리

- **패턴**: `try: while True: yield ... finally: unsubscribe()`. 연결 종료(`CancelledError`)·서버 종료 시 구독 해제·큐 정리.
- **충족 NFR**: MNT(누수 방지), SCAL(구독자 레지스트리 청결).

## 8. Idempotent Pure Reducer (Q4) — 프론트 신뢰성/성능

- **패턴**: `order_id` 키 순수 리듀서 — created/updated=upsert, deleted=remove+`table_total` 세팅, snapshot=replace(unseen 교집합 유지). 재적용 멱등.
- **충족 NFR**: REL-3(멱등 복구), PERF-1(서버 재조회 없이 로컬 패치). 총액은 이벤트 `table_total` 우선.
- **트레이드오프**: 클라이언트 로직 증가 vs 트래픽·지연 최소.

## 9. Auth-at-Connect (Q5) — 보안

- **패턴**: 라우터 진입 시 **`AuthDependency`로 쿼리 토큰 1회 검증**(401 조기 반환) 후 StreamingResponse 시작. 스트림 중 재검증 없음(연결 수명 ≤ 토큰 수명). 로그 토큰 마스킹.
- **충족 NFR**: SEC-1/2/3. Security Baseline 확장 미적용(전역).
- **트레이드오프**: 장수명 연결이 토큰 만료를 초과할 수 있음 → 만료 시 다음 재연결에서 401, 클라이언트가 재로그인 유도(수용). 주기적 재검증(B)은 MVP 과설계.

## 10. Query-Optimized Snapshot (Q6) — 성능

- **패턴**: OrderRepo **단일 조인 쿼리**로 active 세션 주문+항목 로드 → 메모리에서 table 그룹핑/총액 집계. 인덱스(session status, table_id) 의존, 캐시 없음.
- **충족 NFR**: PERF-3(스냅샷 P95 ≤ 500ms).
- **트레이드오프**: 매 스냅샷 DB 조회 vs 캐시 무효화 복잡성 회피. 소규모라 조회 충분.

---

## 11. 패턴 → NFR 매핑 요약

| 패턴 | NFR | 스토리 |
|---|---|---|
| Publish-after-commit | REL-5 | A-06/09/10 |
| In-memory fan-out | PERF-2, SCAL-1 | A-06 |
| Snapshot-replace | REL-3, PERF-1 | A-06 |
| Backoff reconnect | REL-2 | A-06 |
| Keep-alive heartbeat | REL-1 | A-06 |
| Bounded queue+drop | REL-4 | A-06 |
| Lifecycle finally | MNT | — |
| Idempotent reducer | REL-3, PERF-1 | A-06 |
| Auth-at-connect | SEC-1/2/3 | A-05~10 |
| Query-optimized snapshot | PERF-3 | A-05 |
