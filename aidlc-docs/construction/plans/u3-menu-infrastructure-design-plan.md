# U3 Menu — Infrastructure Design Plan (Part 1: Planning)

**단계**: CONSTRUCTION — **Phase 1 (스트림 B)** [U3 Menu] — Infrastructure Design
**유닛**: U3 Menu
**입력**: `construction/u3-menu/functional-design/*`(코드 구현물), `construction/u3-menu/nfr-design/{nfr-design-patterns,logical-components}.md`, `aidlc-state.md`(Extension·규모 설정)
**목적**: U3 논리 컴포넌트를 **실제 배포 인프라**에 매핑한다.

> **U3 특성 · 전역 제약**: 이 프로젝트는 **로컬 단일 매장 MVP**(1 매장, 10~20 테이블, ~20 메뉴)이며 **Security/Resiliency Baseline = No**, **신규 의존성 0**. 인프라는 **U1(Phase 0)이 소유한 모놀리스**(FastAPI 단일 프로세스 + SQLite 파일 + Vite 빌드 정적 자산)를 그대로 공유한다. U3는 **신규 인프라 컴포넌트를 도입하지 않으며**, 클라우드/컨테이너/오케스트레이션은 **향후 지점**으로만 기록한다.

---

## 결정이 필요한 질문 (Questions)

> 관례("전부 권장")·확정 제약(로컬 MVP·Baseline=No·의존성 0)에 따라 각 `[Answer]:`에 권장안을 미리 기입했습니다.

### Q1. 배포 환경 (Deployment Environment)
- **A (권장)**: **로컬/온프레미스 단일 노드**. 개발자 머신에서 백엔드(uvicorn)+프론트(vite dev/preview) 실행. 클라우드 프로바이더·CDN **미도입**(MVP 범위). 향후 지점: 단일 컨테이너(Docker) → 소형 VM/PaaS.
- B: 클라우드(AWS/Azure/GCP)에 배포.

[Answer]: A (권장)

### Q2. 컴퓨트 인프라 (Compute)
- **A (권장)**: **단일 프로세스**. 백엔드 = uvicorn(단일 워커) FastAPI, 프론트 = 정적 빌드(`vite build`) 또는 dev 서버. 오토스케일·다중 워커 **미도입**(동시 사용자 ≤ 테이블 수 + 관리자 1). 향후 지점: gunicorn/uvicorn 다중 워커.
- B: 다중 워커 + 로드밸런서.

[Answer]: A (권장)

### Q3. 스토리지 인프라 (Storage)
- **A (권장)**: **SQLite 파일 1개**(U1 소유, `create_all`로 스키마 생성, `seed.py` 멱등 시드). 메뉴/카테고리는 이 DB에 영속. 이미지는 **외부 URL 참조**(업로드/오브젝트 스토리지 없음 — D4). 별도 DB 서버·백업 파이프라인 미도입. 향후 지점: PostgreSQL + 오브젝트 스토리지.
- B: 관리형 RDB + 오브젝트 스토리지.

[Answer]: A (권장)

### Q4. 메시징 인프라 (Messaging)
- **A (권장)**: **미도입**. U3는 동기 REST CRUD만 수행. 큐·이벤트버스·비동기 파이프라인 없음. (실시간 pub/sub 브로커+SSE는 **U5 주문 전용**이며 메뉴는 대상 아님 — 패턴 P5.)
- B: 큐/이벤트버스 도입.

[Answer]: A (권장)

### Q5. 네트워킹 인프라 (Networking)
- **A (권장)**: **Vite dev 프록시**(`/api` → `:8000`)로 로컬 통합. API 게이트웨이·로드밸런서·WAF **미도입**. 인증 게이트는 애플리케이션 레벨(`AuthDependency`). 향후 지점: 리버스 프록시(nginx) + TLS 종단.
- B: API 게이트웨이/LB/WAF 도입.

[Answer]: A (권장)

### Q6. 모니터링 인프라 (Monitoring)
- **A (권장)**: **기본 로깅 + 구조화 에러 바디**(`{error:{code,message,details}}`). 전용 메트릭(Prometheus)·트레이싱(OTel)·APM·알림 **미도입**(D6, U3-NFR-M3, Resiliency Baseline=No). `GET /api/health`(U1)로 헬스 확인. 향후 지점: 메트릭/트레이싱 수집기.
- B: 관측성 스택 도입.

[Answer]: A (권장)

### Q7. 공유 인프라 & 격리 (Shared Infrastructure)
- **A (권장)**: U3는 **U1 소유 모놀리스 인프라를 공유**(FastAPI 앱·DbSession·SQLite·ApiClient·라우트 레지스트리). U3는 **신규 공유 인프라를 생성하지 않음**. 멀티테넌시는 애플리케이션 레벨 **매장 스코프 격리**(`actor.store_id`, 패턴 P7)로 처리 — 인프라 레벨 격리 불필요(단일 매장·단일 DB).
- B: 유닛 전용 인프라 분리.

[Answer]: A (권장)

---

## 계획 실행 체크리스트 (Part 2 = Infrastructure Design 산출물 생성)

- [x] `construction/u3-menu/infrastructure-design/infrastructure-design.md` — 논리→물리 컴포넌트 매핑 표 + 인프라 결정(IX) + 미도입 인프라 정당화 + 향후 클라우드 매핑
- [x] `construction/u3-menu/infrastructure-design/deployment-architecture.md` — 배포 토폴로지(ASCII) + 실행/기동 절차 + 포트/경로 + 데이터 수명주기
- [x] 공유 인프라: **신규 없음** → `shared-infrastructure.md` 미생성(U1 모놀리스 인프라 참조로 대체)

---

## 승인 요청

Q1~Q7 권장안으로 Infrastructure Design 산출물을 생성했습니다. 변경을 원하면 `[Answer]:` 수정을 요청해 주세요.
