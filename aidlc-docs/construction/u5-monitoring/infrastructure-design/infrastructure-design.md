# U5 Order Monitoring (SSE) — Infrastructure Design

**단계**: CONSTRUCTION — Phase 1 · 스트림 D [U5] — Infrastructure Design
**범위**: U5 논리 컴포넌트를 로컬 런타임에 매핑. 클라우드 미사용, Docker 불필요(NFR-7), 신규 인프라 0.
**근거**: 승인된 `plans/u5-monitoring-infrastructure-design-plan.md`(Q1~Q6 전부 A), `nfr-design/*`, `CLAUDE.md`.

---

## 1. 컴포넌트 → 런타임 매핑

| 논리 컴포넌트 | 런타임 매핑 | 비고 |
|---|---|---|
| `OrderEventBroker` | **uvicorn 프로세스 메모리** 내 싱글턴 객체 | 프로세스 로컬 상태(휘발). 재시작 시 재연결 스냅샷으로 복구 |
| `SubscriberQueue` | `asyncio.Queue`(maxsize=1000) 인스턴스 | 이벤트 루프 관리 |
| `SseStreamEndpoint` | FastAPI 라우트 + `StreamingResponse`(async gen) | uvicorn ASGI가 청크 전송 |
| `OrderAdminService` | 동일 프로세스 서비스 호출 | 커밋 후 broker.publish |
| 저장(Order/OrderItem) | **기존 SQLite 파일**(U1) 재사용 | U5는 신규 스토리지 없음 |
| 메시징 | **인메모리 asyncio.Queue** | 외부 브로커/큐 서비스 없음 |
| 프론트(`SseClient` 등) | Vite dev 서버(:5173) 번들 | 브라우저 EventSource |

- **신규 인프라 없음**(Q5): DB=SQLite 재사용, 메시징=프로세스 큐. `requirements.txt`/`package.json` 변경 없음.

## 2. 컴퓨트 / 프로세스 모델 (Q1)

- **단일 프로세스·단일 워커**: `uvicorn app.main:app --reload`(workers=1).
- **근거**: 인메모리 broker는 프로세스 로컬. 멀티 워커/gunicorn 사용 시 워커별 broker가 분리되어 이벤트 fan-out이 깨짐 → **금지**.
- **동시성**: asyncio 이벤트 루프가 다수 SSE 연결(1~5, SCAL-1)을 단일 스레드 협조적 멀티태스킹으로 처리. DB I/O는 SQLite 동기이나 소규모라 수용.

## 3. 네트워킹 (Q2/Q3)

### 3.1 SSE 응답 헤더 (Q3)
```
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no      # 프록시 버퍼링 방지(nginx 계열 대비)
```
- StreamingResponse가 `data: <json>\n\n` / `: ping\n\n` 청크 flush.

### 3.2 Vite dev 프록시 (Q2)
- `frontend/vite.config`의 `server.proxy['/api'] = { target: 'http://localhost:8000', changeOrigin: true }`. http-proxy는 SSE 스트리밍을 기본 지원.
- 스트림은 `/api/admin/orders/stream?token=` 경로로 프록시 통과. 위 no-buffering 헤더 + keep-alive ping(15s)로 유휴 타임아웃/버퍼링 회피.
- **대안(미채택)**: 절대 URL 직접 연결(CORS 필요) — 프록시 경유가 개발 편의·CORS 회피에 유리.

## 4. 모니터링 / 로깅 (Q4)

- **stdout 구조화 로그**(uvicorn 로거): SSE 연결 open/close, publish 건수, 상태전이·삭제 audit line.
- **토큰 마스킹**: 쿼리스트링 `token` 미기록/마스킹(SEC-2).
- 파일 회전·외부 수집기·메트릭 엔드포인트 **미도입**(로컬 MVP, Resiliency 확장 미적용).

## 5. 스토리지 / 메시징 (Q5)

- **스토리지**: 기존 SQLite. U5는 Order `status` UPDATE·row DELETE만. 스키마 변경 없음. 인덱스(session status, table_id)는 U1 스키마 활용(스냅샷 조회 최적화 PERF-3).
- **메시징**: 프로세스 인메모리 `asyncio.Queue`. 영속 큐·재생 없음(재연결 스냅샷이 복구 담당).

## 6. 공유 인프라 / 격리

- 단일 매장·단일 프로세스 → 멀티테넌시/리소스 격리 비해당. broker fan-out은 `store_id` 경계 유지(멀티 매장 확장 대비 코드 수준 격리).
- 다른 스트림(A~E)과 인프라 공유: 동일 uvicorn 프로세스·동일 SQLite. U5는 소유 파일만 추가.

## 7. 프로덕션 전환 시 고려 (문서 전용, 현재 구현 안 함)

| 항목 | 로컬(현재) | 프로덕션 전환 |
|---|---|---|
| 프로세스 | 단일 워커 | 멀티 워커 → **외부 pub/sub(Redis 등)** 로 broker 대체(Protocol 뒤 교체) |
| 전송 보안 | HTTP + 쿼리 토큰 | **HTTPS** + 헤더 토큰(`fetch` 스트림) 또는 단기 stream 토큰 |
| 프록시 | Vite dev | reverse proxy(nginx) — SSE buffering off 설정 필요 |
| 로깅 | stdout | 중앙 수집(파일/수집기) |

---

## 8. 요약

- U5 인프라 = **기존 로컬 스택 재사용**(uvicorn 단일 워커 + SQLite + Vite dev 프록시). 신규 인프라 0.
- SSE는 표준 헤더 + Vite 프록시 스트리밍 + keep-alive로 로컬에서 안정 동작.
- 인메모리 broker 정합의 전제 = **단일 프로세스**. 확장은 Protocol 교체 지점으로 남김.
