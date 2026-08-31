# U5 Order Monitoring (SSE) — NFR Requirements Plan (Part 1: Planning)

**단계**: CONSTRUCTION — Phase 1 · 스트림 D [U5] — NFR Requirements
**유닛**: U5 Order Monitoring (SSE)
**목적**: U5의 비기능 요구사항(성능·신뢰성·보안·사용성·테스트·유지보수)을 확정하고 기술 스택 선택을 문서화.
**입력**: `u5-monitoring/functional-design/*`, `requirements/requirements.md`(NFR-1~7), `constraints.md`, `aidlc-state.md`(확장 설정).

> **이미 확정된 전역 NFR**(프로젝트 요구사항):
> - **NFR-1(성능)**: 실시간 주문 표시 **2초 이내**(SSE) — U5 핵심 지표.
> - **NFR-2(보안)**: bcrypt·JWT·로그인 시도 제한. Security Baseline **확장 미적용**(명시분만).
> - **NFR-4(사용성)**: 터치 44×44px, 카드 레이아웃.
> - **NFR-6(테스트)**: PBT 전체 적용(Hypothesis/fast-check) + 예제 기반 병행.
> - **NFR-7(이식성)**: 로컬 개발(Docker 불필요).
> - **확장 설정**: Security=No, Resiliency=No, PBT=Yes(Full).

---

## 결정이 필요한 질문 (Questions)

> 각 `[Answer]:` 태그에 답을 채워 주세요. 권장안(A)대로면 `A` 또는 "권장". 전부 권장이면 "전부 권장".

### Q1. 동시 SSE 구독자 규모 (Scalability)
관리자 대시보드 동시 접속(활성 SSE 연결) 상정 규모는?
- **A (권장)**: **소규모(동시 1~5)** — 1개 매장 데모/MVP. 인메모리 단일 프로세스 broker로 충분. 부하 대비 수평 확장 불필요.
- B: 중규모(수십) 상정 — 큐 백프레셔·연결 관리 강화.

[Answer]: A

### Q2. 성능 목표 구체화 (Performance — NFR-1)
"2초 이내" 지표의 측정 기준은?
- **A (권장)**: **주문 생성 커밋 → 대시보드 카드 반영까지 P95 ≤ 2초**(로컬 네트워크 전제). 인메모리 fan-out 지연은 수 ms 목표. 상태변경/삭제 반영도 동일 2초 기준.
- B: 다른 기준/백분위 지정.

[Answer]: A

### Q3. SSE 연결 유지·하트비트 (Reliability)
유휴 연결 끊김/프록시 타임아웃 대응은?
- **A (권장)**: **주기적 keep-alive 코멘트(`: ping`) 15초 간격** 전송으로 연결 유지 + 죽은 연결 조기 감지. 클라이언트 재연결은 지수 백오프(1→2→4s, 상한 10s, 지터) — FD `business-rules §5`와 일치.
- B: 하트비트 없이 EventSource 기본 동작에만 의존.

[Answer]: A

### Q4. 슬로우 컨슈머 / 큐 오버플로 정책 (Reliability)
구독자 큐가 가득 찰 때(느린 클라이언트)?
- **A (권장)**: **구독자 큐 상한(maxsize 예 1000) 초과 시 해당 연결 드롭·정리** → 클라이언트가 재연결 시 스냅샷으로 완전 복구(무손실, 멱등). 다른 구독자·발행 경로는 영향 없음(비차단 put).
- B: 무제한 큐(메모리 압박 위험) / 블로킹 put(발행 경로 지연 위험).

[Answer]: A

### Q5. SSE 토큰 인증의 보안 취급 (Security — Q5 FD 연계)
쿼리스트링 토큰(`?token=`)의 위험 완화는?
- **A (권장)**: 로컬 MVP·HTTP 전제이므로 **쿼리 토큰 허용**하되, (1) 토큰은 기존 관리자 JWT(16h) 재사용, (2) 서버 로그에 쿼리스트링 토큰 **마스킹/미기록**, (3) 프로덕션 전환 시 HTTPS + 헤더 방식(`fetch` 스트림) 전환을 문서에 명시. Security Baseline 확장은 미적용(전역 결정).
- B: 지금부터 헤더 기반(`fetch`+ReadableStream)으로 EventSource 대체.

[Answer]: A

### Q6. 로깅·관측성 (Maintainability / Observability)
U5 운영 가시성 수준은?
- **A (권장)**: **표준 구조화 로깅만**(연결 open/close, publish 건수, 전이/삭제 audit 로그 line). 별도 메트릭 서버/APM 미도입(로컬 MVP, Resiliency 확장 미적용).
- B: 메트릭(구독자 수·이벤트 처리율) 노출 엔드포인트 추가.

[Answer]: A

### Q7. PBT 프레임워크·강도 최종 확정 (Test — NFR-6)
U5 PBT(상태전이·삭제후총액) 구현 스택은?
- **A (권장)**: **Hypothesis(Python)** 로 백엔드 순수 로직(전이 판정·총액 합산) PBT, `backend/tests/`. 프론트 SSE 리듀서는 예제 기반(vitest) 위주. 전역 결정(fast-check)은 U4 장바구니 라운드트립 대상이며 U5 프론트는 fast-check 필수 아님.
- B: 프론트 리듀서(멱등 replace)도 fast-check PBT로 강제.

[Answer]: A

### Q8. 백엔드 SSE 구현 방식 (Tech Stack)
FastAPI에서 SSE를?
- **A (권장)**: **`StreamingResponse` + async generator**(`text/event-stream`), 표준 라이브러리 `asyncio.Queue`로 broker 구현. 외부 SSE 라이브러리(sse-starlette 등) **미도입**(의존성 최소화). `requirements.txt` 추가 없음.
- B: `sse-starlette` 도입(EventSourceResponse 편의).

[Answer]: A

### Q9. 프론트 상태관리 방식 (Tech Stack / Maintainability)
대시보드 실시간 상태(ordersById/unseen/totals)를?
- **A (권장)**: **컴포넌트 로컬 `useReducer` + 커스텀 훅(`useOrderStream`)** 로 관리, 별도 전역 상태 라이브러리(Redux 등) 미도입. 기존 Context(Auth) 재사용. 프로젝트 스택(React/Vite) 준수.
- B: 전역 상태 라이브러리 도입.

[Answer]: A

---

## 계획 실행 체크리스트 (Part 2 = NFR 산출물 생성)

> 위 질문 승인 후 아래 산출물을 생성합니다. (nfr-requirements.md Step 6)

- [x] `construction/u5-monitoring/nfr-requirements/nfr-requirements.md` — 성능(2초 P95·fan-out ms), 확장(동시 구독자·단일 프로세스), 신뢰성(하트비트·재연결·큐 오버플로·멱등 복구), 보안(쿼리 토큰 완화·JWT 재사용), 사용성(44px·연결상태 표시), 테스트(PBT 범위), 유지보수(구조화 로깅), 이식성(로컬). 각 항목에 수용 기준.
- [x] `construction/u5-monitoring/nfr-requirements/tech-stack-decisions.md` — 백엔드 SSE(StreamingResponse+asyncio.Queue, 라이브러리 미추가), 프론트(EventSource/useReducer/useOrderStream), PBT(Hypothesis), 각 선택의 근거·대안·트레이드오프, 신규 의존성 유무(없음 목표).

---

## 승인 요청

Q1~Q9에 답변을 채워 주시면 분석 후(모호 시 후속 질문) NFR 산출물 2종을 생성합니다. 전부 권장안으로 진행하려면 "전부 권장"이라고 답하셔도 됩니다.
