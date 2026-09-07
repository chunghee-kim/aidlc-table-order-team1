# U5 Order Monitoring (SSE) — NFR Requirements

**단계**: CONSTRUCTION — Phase 1 · 스트림 D [U5] — NFR Requirements
**범위**: U5(실시간 모니터링)의 비기능 요구사항과 수용 기준. 전역 NFR-1~7 + 확장(Security=No, Resiliency=No, PBT=Full)을 U5에 특화.
**근거**: 승인된 `plans/u5-monitoring-nfr-requirements-plan.md`(Q1~Q9 전부 A), `functional-design/*`, `requirements/requirements.md`.

---

## 1. 성능 (Performance) — NFR-1

| ID | 요구사항 | 수용 기준 |
|---|---|---|
| PERF-1 | 실시간 반영 지연 | 주문 **생성 커밋 → 대시보드 카드 반영 P95 ≤ 2초**(로컬 네트워크). 상태변경·삭제 반영도 동일 기준 (Q2). |
| PERF-2 | 인메모리 fan-out 지연 | broker `publish` → 구독자 큐 enqueue **수 ms**(비차단 `put_nowait`). |
| PERF-3 | 초기 스냅샷 응답 | `GET /api/admin/orders` 및 스트림 최초 snapshot 프레임 **P95 ≤ 500ms**(소규모 데이터, active 세션 조회). |

---

## 2. 확장성 (Scalability) — Q1

| ID | 요구사항 | 수용 기준 |
|---|---|---|
| SCAL-1 | 동시 구독자 | **1~5 동시 SSE 연결** 상정(1개 매장 데모/MVP). 단일 프로세스 인메모리 broker로 처리. |
| SCAL-2 | 수평 확장 | **비목표(non-goal)**. 크로스 프로세스 pub/sub(Redis 등) 미도입. 프로덕션 확장 시 broker 인터페이스 뒤 교체 가능하도록 계약 유지(현 `OrderEventBroker` Protocol). |

---

## 3. 신뢰성 (Reliability) — Q3/Q4

| ID | 요구사항 | 수용 기준 |
|---|---|---|
| REL-1 | Keep-alive | 서버가 **15초 간격 `: ping` 코멘트** 전송 → 유휴 연결 유지·죽은 연결 조기 감지 (Q3). |
| REL-2 | 재연결 | 클라이언트 **지수 백오프(1→2→4s, 상한 10s, 지터)**. FD `business-rules §5` 준수. |
| REL-3 | 재연결 복구 | 재연결 시 서버 **snapshot 프레임 1건 → 클라이언트 완전 replace**(멱등·무손실). 누락 이벤트 개별 재생 없음. |
| REL-4 | 슬로우 컨슈머 | 구독자 큐 **maxsize=1000 초과 시 연결 드롭·정리**. 다른 구독자/발행 경로 무영향(비차단 put) (Q4). |
| REL-5 | 발행 원자성 | 이벤트는 **DB 커밋 성공 후에만** 발행. 롤백 시 미발행(FD BR-U5-10). |

---

## 4. 보안 (Security) — NFR-2 / Q5

| ID | 요구사항 | 수용 기준 |
|---|---|---|
| SEC-1 | 인증 | 모든 U5 엔드포인트(REST·SSE) **관리자 JWT** 필요. SSE는 쿼리 토큰(`?token=`), `AuthDependency`와 동일 검증. 무효/만료 → 401. |
| SEC-2 | 쿼리 토큰 완화 | 기존 관리자 JWT(16h) **재사용**(신규 토큰 발급 없음). 서버 로그에 쿼리스트링 토큰 **마스킹/미기록** (Q5). |
| SEC-3 | 권한 | 관리자 외 접근 403. |
| SEC-4 | 프로덕션 전환 주의 | HTTP·쿼리 토큰은 **로컬 MVP 전제**. 프로덕션 시 **HTTPS + 헤더 방식(`fetch` 스트림)** 전환 필요 — 문서화(tech-stack-decisions §5). |
| — | 범위 | Security Baseline 확장 **미적용**(전역 결정). 명시 요구사항만 구현. |

---

## 5. 사용성 (Usability) — NFR-4 / Q7(Q7 FD)

| ID | 요구사항 | 수용 기준 |
|---|---|---|
| USE-1 | 터치 타깃 | 상태변경·삭제 등 액션 버튼 **≥ 44×44px**. |
| USE-2 | 신규 강조 | 신규 주문 **unseen 강조**를 관리자가 **열람할 때까지 유지**(FD Q7-B). |
| USE-3 | 연결 상태 표시 | `reconnecting` 중 사용자에게 인디케이터/배너 표시, 복구 시 자동 해제. |
| USE-4 | 표시 포맷 | 금액 원화, 시간 UTC→KST 변환(프론트). |

---

## 6. 테스트 (Test) — NFR-6 / Q7

| ID | 요구사항 | 수용 기준 |
|---|---|---|
| TEST-1 | PBT(백엔드) | **Hypothesis** — `PBT-U5-STATE`(상태 전이 규칙), `PBT-U5-DELETE`(삭제 후 총액=남은 합). `backend/tests/`. CI 그린 필수. |
| TEST-2 | 예제 기반(백엔드) | change_status/delete_order의 401/404/409 경로, 커밋 후 발행, snapshot active 필터. |
| TEST-3 | 프론트 테스트 | SSE 리듀서(created/updated/deleted/snapshot replace 멱등)·전이 버튼 노출은 **예제 기반(vitest)**. fast-check PBT는 U5 프론트에 **필수 아님**(Q7). |

---

## 7. 유지보수·관측성 (Maintainability) — Q6

| ID | 요구사항 | 수용 기준 |
|---|---|---|
| MNT-1 | 로깅 | **구조화 로깅만** — SSE 연결 open/close, publish 건수, 상태전이·삭제 audit line. 토큰 마스킹(SEC-2). |
| MNT-2 | 관측성 범위 | 별도 메트릭 서버/APM **미도입**(로컬 MVP, Resiliency 확장 미적용). |
| MNT-3 | 코드 소유 | U5 소유 파일만 편집(parallel-execution §4), 동결 계약 불변. |

---

## 8. 이식성 (Portability) — NFR-7

| ID | 요구사항 | 수용 기준 |
|---|---|---|
| PORT-1 | 로컬 실행 | **Docker 불필요**. `uvicorn` + `npm run dev`로 기동. 신규 런타임 의존성 추가 없음(§tech-stack). |

---

## 9. NFR → 스토리/FD 추적

| NFR | 관련 | FD 근거 |
|---|---|---|
| PERF-1/2 | US-A-06 | business-rules §5, business-logic-model §2 |
| REL-1~4 | US-A-06 | business-rules §5, §domain §5 |
| SEC-1/2 | US-A-05~10 | business-rules §6 |
| USE-2 | US-A-06 | frontend-components §4 (Q7-B) |
| TEST-1 | US-A-09/10 | business-logic-model §7 |
