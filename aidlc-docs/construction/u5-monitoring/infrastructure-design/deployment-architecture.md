# U5 Order Monitoring (SSE) — Deployment Architecture

**단계**: CONSTRUCTION — Phase 1 · 스트림 D [U5] — Infrastructure Design
**범위**: 로컬 배포 토폴로지, SSE 연결 경로, 기동/검증 절차, U5 종단 시나리오. 신규 배포 스크립트 없음(Q6).
**근거**: 승인된 계획(Q1~Q6), `infrastructure-design.md`, `CLAUDE.md`.

---

## 1. 로컬 배포 토폴로지

```
+---------------------------+        +------------------------------------------+
|        Browser            |        |         Dev Machine (single host)        |
|  /admin/monitoring        |        |                                          |
|                           |        |  Vite dev server  :5173                  |
|  EventSource ─────────────┼──HTTP──▶  server.proxy['/api'] → :8000            |
|   /api/admin/orders/stream|        |        │ (SSE streaming pass-through)     |
|      ?token=<JWT>         |        |        ▼                                 |
|  ApiClient (REST) ────────┼──HTTP──▶  uvicorn (FastAPI)  :8000  [workers=1]    |
|   PATCH/DELETE /orders/{} |        |    ├ routers/admin_order.py (SSE+REST)   |
|                           |        |    ├ services/order/admin.py             |
|  orderStreamReducer       |◀─events─┤   ├ order_event_broker.py (in-proc)     |
|  (ordersById/unseen)      |        |    │     └ asyncio.Queue per subscriber  |
+---------------------------+        |    └ OrderRepo → SQLite file (app.db)    |
                                     +------------------------------------------+
```

- **단일 호스트·단일 프로세스**: 모든 SSE 구독자·이벤트가 uvicorn 프로세스 메모리(broker) 공유.
- **경로**: 프론트는 항상 `/api`(상대 경로)로 요청 → Vite 프록시가 :8000 전달(CORS 불필요).

## 2. SSE 연결 경로 (상세)

```
1. Dashboard mount → SseClient.connect("/api/admin/orders/stream?token=JWT")
2. Vite proxy → uvicorn: GET stream
3. Endpoint: AuthDependency(token) 검증 → 200 text/event-stream (no-buffering 헤더)
4. broker.subscribe(store) 등록 → 'snapshot' 프레임 즉시 전송
5. 이후 order_created/updated/deleted 청크 push + 15s마다 ': ping'
6. 끊김 → EventSource 재연결(백오프) → 4로 복귀(스냅샷 replace)
```

## 3. 기동 절차 (기존 재사용 — CLAUDE.md)

```bash
# backend
cd backend
source .venv/Scripts/activate       # (Unix: .venv/bin/activate)
uvicorn app.main:app --reload       # :8000, workers=1 (단일 프로세스 필수)

# frontend
cd frontend
npm run dev                         # :5173, /api → :8000 프록시
```
- 신규 스크립트·컨테이너 없음. `--workers >1` 사용 금지(broker 정합 깨짐).

## 4. U5 종단 검증 시나리오 (DoD)

| # | 시나리오 | 기대 |
|---|---|---|
| 1 | 관리자 로그인 → `/admin/monitoring` 진입 | 테이블 카드 그리드 표시(초기 스냅샷) |
| 2 | 고객이 새 주문 생성(U4) | **2초 이내** 카드에 반영 + unseen 강조(US-A-06) |
| 3 | 신규 주문 카드 열람 | 강조 해제(Q7-B) |
| 4 | 카드 클릭 → 상세 모달 | 주문 전체 항목·총액 표시(US-A-07) |
| 5 | 상태 대기중→준비중→완료 | 갱신 반영, 건너뛰기/역행 시 409(US-A-09) |
| 6 | 주문 삭제(확인 팝업) | 즉시 제거 + 테이블 총액 재계산(US-A-10) |
| 7 | 테이블 필터 적용 | 해당 테이블만 표시(클라이언트, US-A-08) |
| 8 | SSE 연결 끊김→복구 | 누락분 스냅샷 replace로 복구(US-A-06) |
| 9 | PBT | 상태전이·삭제후총액 그린 |

## 5. 제약 / 가정

- **단일 프로세스 전제**: 인메모리 broker 정합의 필수 조건. 멀티 워커·다중 호스트 미지원(프로덕션은 외부 pub/sub로 대체 — infrastructure-design §7).
- **로컬 네트워크**: 2초 성능 목표는 로컬 전제(PERF-1).
- **HTTP·쿼리 토큰**: 로컬 MVP 한정. 프로덕션 HTTPS 전환 필요(SEC-4).
- **데이터 휘발**: broker 상태는 프로세스 재시작 시 소멸 → 재연결 스냅샷이 DB 기준으로 복구(무손실).
