# U5 Order Monitoring (SSE) — NFR Design Plan (Part 1: Planning)

**단계**: CONSTRUCTION — Phase 1 · 스트림 D [U5] — NFR Design
**유닛**: U5 Order Monitoring (SSE)
**목적**: NFR 요구사항을 **설계 패턴 + 논리 컴포넌트**로 구체화. (인프라 매핑은 다음 단계 Infrastructure Design.)
**입력**: `u5-monitoring/nfr-requirements/*`, `functional-design/*`, `order_event_broker.py`(동결 계약), `sse-client.ts`(동결 인터페이스).

> **이미 확정(FD/NFR)**: StreamingResponse+asyncio.Queue broker / EventSource+쿼리토큰 / 15s ping / 백오프 재연결 / 스냅샷 replace 멱등 복구 / 큐 maxsize=1000 드롭 / 커밋 후 발행 / Hypothesis PBT / 신규 의존성 0. 아래 질문은 **설계 패턴의 세부**만 다룹니다.

---

## 결정이 필요한 질문 (Questions)

> 각 `[Answer]:` 태그에 답을 채워 주세요. 권장안(A)대로면 `A` 또는 "권장". 전부 권장이면 "전부 권장".

### Q1. 이벤트 발행 트리거 패턴 (Performance / Logical Components)
서비스가 커밋 후 broker.publish를 호출하는 방식은?
- **A (권장)**: **서비스 계층 명시 호출** — `change_status`/`delete_order`(및 U4 `create_order`)가 커밋 성공 직후 `broker.publish(...)`를 직접 호출. 단순·명확, 의존성 0. (ORM 이벤트 훅/아웃박스 패턴 미도입.)
- B: SQLAlchemy `after_commit` 이벤트 훅으로 자동 발행.
- C: 트랜잭셔널 아웃박스 + 폴러(신뢰성↑, MVP엔 과함).

[Answer]: A

### Q2. 구독자 큐 소비/연결 수명 패턴 (Resilience / Logical Components)
async generator가 큐를 소비하는 루프와 취소 처리는?
- **A (권장)**: **`while True: event = await queue.get()` + `finally: unsubscribe()`** 패턴. 클라이언트 연결 종료(`asyncio.CancelledError`)·서버 종료 시 `finally`에서 구독 해제·자원 정리. ping은 `asyncio.wait_for(queue.get(), timeout=15)`의 타임아웃 분기로 전송.
- B: 별도 백그라운드 태스크가 ping을 push하고 소비 루프는 큐만 대기.

[Answer]: A

### Q3. 스냅샷 일관성 패턴 (Reliability)
재연결 스냅샷과 이후 증분 이벤트 사이의 경합(스냅샷 계산 중 새 이벤트 발생)을?
- **A (권장)**: **구독 등록 → 스냅샷 계산 → yield 순서 보장**. 구독을 큐에 먼저 등록한 뒤 스냅샷을 만들면, 스냅샷 이후 이벤트는 큐에 쌓여 순서대로 전달됨. 중복(스냅샷에도 있고 이벤트로도 옴)은 프론트가 `order_id` 기준 upsert(멱등)로 흡수 → 유실 0, 중복 무해.
- B: 스냅샷 계산 동안 발행 잠금(lock) — 단일 프로세스 MVP엔 과함.

[Answer]: A

### Q4. 프론트 리듀서 멱등성 패턴 (Reliability / Performance)
SSE 이벤트 적용 리듀서의 설계 원칙은?
- **A (권장)**: **`order_id` 키 기반 순수 리듀서** — created/updated=upsert, deleted=remove+총액 세팅, snapshot=전체 replace(단, unseen 집합은 교집합 유지). 동일 이벤트 재적용해도 결과 동일(멱등). 총액은 이벤트의 `table_total` 우선, 없으면 로컬 재합산.
- B: 이벤트마다 서버 재조회로 정합(트래픽↑).

[Answer]: A

### Q5. 보안 패턴 — SSE 인증 경계 (Security)
쿼리 토큰 검증을 어디서?
- **A (권장)**: **라우터 진입 시 `AuthDependency` 재사용해 토큰 검증** 후에만 StreamingResponse 시작(401 조기 반환). 스트림 시작 후에는 재검증 없음(연결 수명=토큰 수명 내). 로그는 토큰 마스킹.
- B: 스트림 중 주기적 토큰 재검증.

[Answer]: A

### Q6. 성능 — 스냅샷 조회 최적화 (Performance)
`snapshot`/`GET /api/admin/orders`의 active 세션 주문 조회를?
- **A (권장)**: **OrderRepo 단일 쿼리(조인)로 active 세션 주문+항목 로드** 후 메모리에서 table 그룹핑/총액 집계. 소규모 데이터라 인덱스(session status, table_id)로 충분, 캐시 미도입.
- B: 인메모리 캐시 계층 추가(무효화 복잡, MVP 불필요).

[Answer]: A

---

## 계획 실행 체크리스트 (Part 2 = NFR Design 산출물 생성)

> 위 질문 승인 후 아래 산출물을 생성합니다. (nfr-design.md Step 6)

- [x] `construction/u5-monitoring/nfr-design/nfr-design-patterns.md` — 적용 패턴: Publish-after-commit, In-memory Pub/Sub(fan-out), Snapshot-replace 재동기화(멱등), 지수 백오프 재연결, Keep-alive heartbeat, Bounded queue + drop(백프레셔), 순수 리듀서 멱등성, Auth-at-connect. 각 패턴 → NFR 매핑·트레이드오프.
- [x] `construction/u5-monitoring/nfr-design/logical-components.md` — 논리 컴포넌트: `OrderEventBroker`(subscribers registry·fan-out·snapshot), `SubscriberQueue`(bounded), `SseStreamEndpoint`(generator·ping·auth), `OrderAdminService`(change_status/delete_order·publish), 프론트 `SseClient`·`useOrderStream`·리듀서. 컴포넌트 간 상호작용·시퀀스·경계.

---

## 승인 요청

Q1~Q6에 답변을 채워 주시면 분석 후(모호 시 후속 질문) NFR Design 산출물 2종을 생성합니다. 전부 권장안으로 진행하려면 "전부 권장"이라고 답하셔도 됩니다.
