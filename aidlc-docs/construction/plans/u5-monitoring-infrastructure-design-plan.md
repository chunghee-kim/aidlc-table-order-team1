# U5 Order Monitoring (SSE) — Infrastructure Design Plan (Part 1: Planning)

**단계**: CONSTRUCTION — Phase 1 · 스트림 D [U5] — Infrastructure Design
**유닛**: U5 Order Monitoring (SSE)
**목적**: 논리 컴포넌트(NFR Design)를 **실제 런타임/인프라**에 매핑. 배포 형상·SSE 경로·프로세스 모델·관측 확정.
**입력**: `u5-monitoring/nfr-design/*`, `nfr-requirements/*`, `CLAUDE.md`(로컬 실행), `requirements.md`(NFR-7 Docker 불필요), `frontend/vite.config`(프록시).

> **이미 확정(전역/NFR)**: 로컬 개발 전용·Docker 불필요(NFR-7), 단일 리포 모놀리식(backend uvicorn + frontend Vite dev, `/api`→:8000 프록시), SQLite 파일 DB, 인메모리 broker(단일 프로세스). 클라우드(AWS/Azure/GCP) 미사용. 아래 질문은 U5(SSE) 특유 인프라만 다룹니다.

---

## 결정이 필요한 질문 (Questions)

> 각 `[Answer]:` 태그에 답을 채워 주세요. 권장안(A)대로면 `A` 또는 "권장". 전부 권장이면 "전부 권장".

### Q1. 프로세스/워커 모델 (Compute — 인메모리 broker 정합성)
인메모리 broker는 프로세스 로컬 상태이므로 워커 수가 중요합니다.
- **A (권장)**: **단일 프로세스·단일 워커**(`uvicorn app.main:app --reload`, workers=1). 모든 SSE 구독자·이벤트가 한 프로세스 메모리를 공유 → broker 정합 보장. 멀티 워커/gunicorn 미사용(공유 broker 깨짐 방지).
- B: 멀티 워커 + 외부 pub/sub(Redis 등) — MVP 범위 밖.

[Answer]: A

### Q2. SSE 개발 프록시 설정 (Networking — Vite dev proxy)
Vite dev 서버가 `/api`를 :8000으로 프록시할 때 SSE 스트림 처리?
- **A (권장)**: **Vite 프록시에서 스트림 버퍼링 비활성**(`proxy['/api'] = { target, changeOrigin, ...}`; SSE는 http-proxy가 기본 스트리밍 지원). 백엔드 응답 헤더에 `Cache-Control: no-cache`, `X-Accel-Buffering: no`, `Connection: keep-alive` 명시로 중간 버퍼링 방지. 프록시 타임아웃은 keep-alive ping(15s)으로 회피.
- B: 프론트가 프록시 우회하고 절대 URL(:8000)로 EventSource 직접 연결.

[Answer]: A

### Q3. SSE 응답 헤더/미디어 타입 (Networking)
스트림 엔드포인트 응답 형상은?
- **A (권장)**: `Content-Type: text/event-stream`, `Cache-Control: no-cache`, `Connection: keep-alive`, `X-Accel-Buffering: no`. StreamingResponse가 청크 전송. (표준 SSE 형상.)
- B: 다른 헤더 구성.

[Answer]: A

### Q4. 로깅 대상/형식 (Monitoring — MNT-1)
U5 구조화 로깅의 출력 대상은?
- **A (권장)**: **stdout(콘솔)로 구조화 로그** — uvicorn 로거 활용, 연결 open/close·publish 건수·전이/삭제 audit line. 토큰 마스킹. 파일 회전·외부 수집기(ELK 등) 미도입(로컬 MVP). 별도 메트릭 엔드포인트 없음.
- B: 파일 로깅 + 회전 설정 추가.

[Answer]: A

### Q5. 데이터/메시징 인프라 (Storage / Messaging)
U5의 저장·메시징 인프라는?
- **A (권장)**: **저장=기존 SQLite(U1) 재사용**(U5는 신규 테이블·스토리지 없음, Order status UPDATE·row DELETE만). **메시징=프로세스 인메모리 asyncio.Queue**(외부 브로커·큐 서비스 없음). 신규 인프라 0.
- B: 별도 메시지 브로커/큐 서비스 도입.

[Answer]: A

### Q6. 실행/검증 절차 문서화 (Deployment)
U5 로컬 실행·검증 절차를?
- **A (권장)**: CLAUDE.md의 기존 backend/frontend 기동 절차 재사용 + U5 확인 시나리오(대시보드 진입→고객 주문 생성 시 2초 내 카드 반영→상태변경/삭제 반영→재연결 복구)를 deployment-architecture.md에 기재. 신규 배포 스크립트 없음.
- B: 별도 실행 스크립트/컨테이너 추가.

[Answer]: A

---

## 계획 실행 체크리스트 (Part 2 = Infrastructure Design 산출물 생성)

> 위 질문 승인 후 아래 산출물을 생성합니다. (infrastructure-design.md Step 6)

- [x] `construction/u5-monitoring/infrastructure-design/infrastructure-design.md` — 컴포넌트→런타임 매핑(broker=프로세스 메모리, SSE=uvicorn StreamingResponse, DB=SQLite 재사용), 프로세스/워커 모델(단일), 네트워킹(Vite 프록시·SSE 헤더), 로깅(stdout·마스킹), 신규 인프라 없음 명시, 프로덕션 전환 시 고려(멀티워커+외부 pub/sub·HTTPS).
- [x] `construction/u5-monitoring/infrastructure-design/deployment-architecture.md` — 로컬 배포 토폴로지 다이어그램(Browser↔Vite:5173↔proxy↔uvicorn:8000↔SQLite), SSE 연결 경로, 기동/검증 절차·U5 종단 시나리오, 제약(단일 프로세스 전제).

---

## 승인 요청

Q1~Q6에 답변을 채워 주시면 분석 후(모호 시 후속 질문) Infrastructure Design 산출물 2종을 생성합니다. 전부 권장안으로 진행하려면 "전부 권장"이라고 답하셔도 됩니다.
