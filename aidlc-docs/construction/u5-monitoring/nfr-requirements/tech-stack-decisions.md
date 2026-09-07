# U5 Order Monitoring (SSE) — Tech Stack Decisions

**단계**: CONSTRUCTION — Phase 1 · 스트림 D [U5] — NFR Requirements
**범위**: U5 구현 기술 선택·근거·대안·트레이드오프. 프로젝트 전역 스택(FastAPI + SQLAlchemy + SQLite / Vite + React + TS)을 준수하며 **신규 의존성 추가 없음**을 목표.
**근거**: 승인된 NFR 계획(Q1~Q9 전부 A), `nfr-requirements.md`, `functional-design/*`.

---

## 1. 백엔드 SSE 전송 (Q8)

- **결정**: FastAPI **`StreamingResponse` + async generator**, media type `text/event-stream`. 이벤트 프레임은 `data: <json>\n\n` 수동 포맷. keep-alive는 `: ping\n\n` 코멘트(REL-1).
- **broker**: 표준 라이브러리 **`asyncio.Queue`** 기반 인메모리 pub/sub(`order_event_broker.py` 실구현). 구독자별 큐(maxsize=1000), store별 fan-out.
- **대안**: `sse-starlette`(`EventSourceResponse`) — 편의 있으나 **신규 의존성**. MVP 규모엔 표준 도구로 충분.
- **트레이드오프**: 수동 프레임 포맷팅 코드 소량 발생 vs 의존성 0·완전한 제어(스냅샷 프레임·ping 커스터마이즈). → **의존성 최소화 채택**. `requirements.txt` 변경 없음(PORT-1).

## 2. 프론트 SSE 클라이언트

- **결정**: 브라우저 표준 **`EventSource`** 사용(`shared/api/sse-client.ts` 실구현). URL 쿼리 토큰(`?token=`)으로 인증(SEC-1). `onerror` 시 지수 백오프 재연결(REL-2). `snapshot` 프레임 수신 시 상태 완전 replace(REL-3).
- **대안**: `fetch` + `ReadableStream`으로 헤더 인증 SSE 직접 파싱 — 헤더 토큰 가능하나 재연결 로직 전부 수동 구현 필요. 프로덕션(HTTPS) 전환 시 옵션으로 문서화(SEC-4).
- **트레이드오프**: EventSource는 헤더 불가(쿼리 토큰 필요) vs 자동 재연결·간결. 로컬 MVP에 EventSource 채택.

## 3. 프론트 상태 관리 (Q9)

- **결정**: 컴포넌트 로컬 **`useReducer` + 커스텀 훅 `useOrderStream`**. 상태: `ordersById`(Map), `unseen`(Set), `tableTotals`(Map), `filterTableId`, `selectedOrderId`, `connState`. 인증은 기존 `AuthContext`(U2) 재사용.
- **대안**: Redux/Zustand 등 전역 상태 — U5 상태는 대시보드 화면에 국소적이라 과함.
- **트레이드오프**: 전역 스토어 없이도 리듀서로 이벤트 패치·멱등 replace 관리 충분. 프로젝트 스택 준수(신규 의존성 없음).

## 4. 테스트 스택 (Q7)

- **백엔드 PBT**: **Hypothesis** — 순수 로직 추출(전이 판정 함수, 총액 합산 함수)에 대해 `PBT-U5-STATE`·`PBT-U5-DELETE`. `backend/tests/`(pytest). 이미 `requirements.txt`에 포함(Phase 0).
- **백엔드 예제**: pytest로 라우터/서비스 경로(401/404/409, 커밋 후 발행, snapshot active 필터).
- **프론트**: **vitest** 예제 기반(SSE 리듀서 멱등 replace, 전이 버튼 노출 규칙). fast-check는 U5 프론트 필수 아님(전역 fast-check 대상은 U4 장바구니).

## 5. 보안 구현 노트 (SEC-2/SEC-4)

- 쿼리 토큰: 기존 관리자 JWT(16h) 재사용. 서버 접근 로그에서 `token` 쿼리 파라미터 **마스킹** 또는 미기록.
- **프로덕션 전환 체크리스트**(문서 전용, 지금 구현 안 함): HTTPS 적용 → SSE를 `fetch`+ReadableStream 헤더 인증으로 전환 또는 짧은 수명 stream 전용 토큰 발급 고려.

## 6. 신규 의존성 요약

| 레이어 | 신규 의존성 | 비고 |
|---|---|---|
| 백엔드 | **없음** | StreamingResponse·asyncio 표준. Hypothesis는 기존 포함. |
| 프론트 | **없음** | EventSource·useReducer 표준. vitest 기존 포함. |

→ **PORT-1 충족**: `requirements.txt`·`package.json` 의존성 변경 없이 U5 구현.

## 7. 결정 요약표

| 항목 | 결정 | 대안 | 근거 |
|---|---|---|---|
| SSE 서버 | StreamingResponse + asyncio.Queue | sse-starlette | 의존성 0, 완전 제어 |
| SSE 클라이언트 | EventSource + 쿼리 토큰 | fetch/ReadableStream | 자동 재연결·간결(로컬) |
| 상태 관리 | useReducer + useOrderStream | Redux/Zustand | 국소 상태, 스택 준수 |
| 백엔드 PBT | Hypothesis | — | NFR-6·전역 결정 |
| 프론트 테스트 | vitest 예제 | fast-check PBT | U5 프론트 PBT 비필수 |
