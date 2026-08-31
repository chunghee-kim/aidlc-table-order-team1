# U3 Menu — 인프라 설계 (Infrastructure Design)

**단계**: CONSTRUCTION — Phase 1 (스트림 B) [U3 Menu] — Infrastructure Design
**유닛**: U3 Menu
**입력**: `nfr-design/{nfr-design-patterns,logical-components}.md`, U3 구현물, `u3-menu-infrastructure-design-plan.md`(Q1~Q7 권장)

> U3 **논리 컴포넌트**를 **실제 배포 인프라**에 매핑합니다. 이 프로젝트는 **로컬 단일 매장 MVP**(Security/Resiliency Baseline=No, 신규 의존성 0)이므로 U3는 **U1 소유 모놀리스 인프라를 공유**하고 **신규 인프라를 도입하지 않습니다**. 미도입 항목은 정당화와 향후 지점을 함께 기록합니다(overconfidence-prevention).

---

## 1. 논리 → 물리 컴포넌트 매핑

| 논리 컴포넌트 (nfr-design) | 물리 배치 | 인프라 유형 | 소유 |
|---|---|---|---|
| MenuRouter / MenuService / SqlMenuRepo / SqlCategoryRepo | **FastAPI 앱**(uvicorn 단일 프로세스) 내 모듈 | 컴퓨트(로컬 프로세스) | U3 코드 · U1 런타임 |
| Menu / Category 데이터 | **SQLite 파일**(`app.db`, `create_all` + `seed.py`) | 스토리지(로컬 파일) | U1 소유 |
| menu-api / MenuBrowseView / MenuManageView | **정적 자산**(`vite build` → dist) 또는 vite dev 서버 | 컴퓨트(브라우저) + 정적 호스팅 | U3 코드 · U1 셸 |
| 관리자 인증 게이트(`get_current_admin`) | FastAPI 의존성(앱 레벨) | 앱 레벨 보안 | U2 소유 · U3 소비 |
| 이미지(`image_url`) | **외부 URL**(제3자 호스팅) | 외부 참조(서버 fetch 없음) | 외부 |
| `/api` 라우팅 | **Vite dev 프록시**(`/api` → `localhost:8000`) | 로컬 네트워킹 | U1 설정 |

> U3가 배치하는 **신규 물리 컴포넌트는 없음**. 코드 모듈이 기존 프로세스/DB/정적 번들 안에 얹힌다.

---

## 2. 인프라 결정 (IX)

### IX1. 배포 환경 — 로컬/온프레미스 단일 노드
- 백엔드 `uvicorn app.main:app`(단일 워커), 프론트 `vite`(dev) 또는 `vite build` 정적 산출. 클라우드/CDN 미도입.
- **근거**: 단일 매장 MVP, 이식성 목표(NFR-7)는 "로컬 실행 + 추가 인프라 없음"으로 충족. (Q1=A)

### IX2. 컴퓨트 — 단일 프로세스
- 동시 사용자 ≤ 테이블 수(10~20) + 관리자 1 → 단일 워커로 충분. 오토스케일·다중 워커 미도입.
- **근거**: U3-NFR-SC1(부하 경계), P1(p95<300ms 로컬). (Q2=A)

### IX3. 스토리지 — SQLite 파일 (U1 소유)
- 메뉴/카테고리는 U1이 생성한 단일 SQLite 파일에 영속. U3는 스키마·시드를 **추가하지 않고** 기존 `Menu`/`Category` 모델을 사용.
- 이미지 바이너리 스토리지 없음 — `image_url` 외부 참조(D4). 백업/복제 파이프라인 미도입(파일 복사로 충분).
- **근거**: 소량 데이터, U3-NFR-P4·R4(삭제 무결성은 앱 레벨). (Q3=A)

### IX4. 메시징 — 미도입
- U3는 동기 REST CRUD. 큐·이벤트버스 없음. (SSE 실시간은 U5 주문 전용.)
- **근거**: 비동기 파이프라인 부재. (Q4=A)

### IX5. 네트워킹 — Vite 프록시 + 앱 레벨 게이트
- 로컬 통합은 vite `/api` 프록시. API 게이트웨이·LB·WAF·TLS 종단 미도입. 인증은 `AuthDependency`(앱 레벨).
- **근거**: Security Baseline=No, 로컬 MVP. (Q5=A)

### IX6. 모니터링 — 기본 로깅 + 헬스체크
- 구조화 에러 바디 + 기본 로깅. `GET /api/health`(U1)로 상태 확인. 전용 메트릭/트레이싱/APM/알림 미도입.
- **근거**: D6, U3-NFR-M3, Resiliency Baseline=No. (Q6=A)

### IX7. 공유 인프라 & 격리 — 앱 레벨 매장 스코프
- U3는 U1 모놀리스 인프라 공유, 신규 공유 인프라 생성 없음. 멀티테넌시는 `actor.store_id` 스코프(패턴 P7)로 앱 레벨 처리 — 인프라 레벨 격리 불필요.
- **근거**: 단일 매장·단일 DB. (Q7=A)

---

## 3. 미도입 인프라 (Explicitly Not Provisioned — 정당화)

| 인프라 | 도입? | 정당화 | 향후 지점 |
|---|:--:|---|---|
| 클라우드 프로바이더(AWS/Azure/GCP) | ❌ | 로컬 MVP, 단일 매장 | 단일 컨테이너 → 소형 VM/PaaS |
| 컨테이너/오케스트레이션(Docker/K8s) | ❌ | 단일 프로세스로 충분 | Dockerfile → Compose → K8s |
| 관리형 DB(RDS/Cloud SQL) | ❌ | SQLite 파일로 충분(소량) | PostgreSQL 이관 |
| 오브젝트 스토리지(S3 등) | ❌ | 이미지 외부 URL 참조(D4) | 업로드 도입 시 S3 + CDN |
| 메시지 큐/이벤트버스 | ❌ | 동기 CRUD | 비동기 도입 시 SQS/Kafka |
| API 게이트웨이 / LB / WAF | ❌ | 단일 앱, Security Baseline=No | nginx 리버스 프록시 → API GW |
| CDN | ❌ | 로컬 정적 자산 | 정적 호스팅 + CDN |
| 관측성 스택(Prometheus/OTel/APM) | ❌ | 기본 로깅으로 대체(D6) | 메트릭/트레이싱 수집기 |
| 시크릿 매니저 | ❌ | 로컬 `.env`(JWT_SECRET, 미커밋) | 클라우드 시크릿 매니저 |

> **원칙**: 인프라 부재는 규모·확장 설정(1 매장, Baseline=No)에 부합하는 **의도된 설계**이며, 각 항목은 성장 시 도입 지점이 명확하다.

---

## 4. 향후 클라우드 매핑 (Reference — 미구현)

| 논리 컴포넌트 | 로컬(현재) | 향후 클라우드 예시(참고) |
|---|---|---|
| FastAPI 앱 | uvicorn 단일 프로세스 | 컨테이너(ECS/Cloud Run) 다중 인스턴스 |
| SQLite 파일 | 로컬 파일 | 관리형 PostgreSQL(RDS/Cloud SQL) |
| 정적 프론트 | vite dev/build | 오브젝트 스토리지 + CDN(S3+CloudFront) |
| `/api` 프록시 | vite proxy | API Gateway / ALB + 리버스 프록시 |
| 이미지 | 외부 URL | 오브젝트 스토리지 + CDN(업로드 도입 시) |
| 로깅/헬스 | 기본 로깅·`/api/health` | 중앙 로그 + 메트릭/알림 |

> 이 표는 **성장 경로 참고용**이며 U3 범위에서 구현하지 않는다.

---

## 5. NFR → 인프라 결정 추적

| U3-NFR | 인프라 결정 |
|---|---|
| P1·P3·P4 (조회 성능·규모) | IX2(단일 프로세스)·IX3(SQLite 소량) |
| SC1·SC2 (부하 경계·확장 지점) | IX2·§3·§4(향후 지점) |
| A1·A2 (우아한 실패·빈 데이터) | 앱 레벨(패턴 P10) — 인프라 무관 |
| S1~S5 (인증·스코프·노출) | IX5(앱 레벨 게이트)·IX7(스코프 격리)·§3(시크릿 로컬 .env) |
| M3 (관측성) | IX6(기본 로깅·헬스체크) |
| NFR-7 (이식성) | IX1(로컬 실행·추가 인프라 없음) |
