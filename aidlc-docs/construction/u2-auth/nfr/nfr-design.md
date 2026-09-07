# U2 Auth & Session — NFR Design (설계)

**단계**: CONSTRUCTION — Phase 1 · 스트림 A (U2) — **NFR Design (Part 2: 설계)**
**목적**: `nfr-requirements.md`의 각 목표(SEC/SES/USA/TST/POR)를 **어떤 메커니즘·구성 요소로 충족**하는지 설계로 확정하고, 구현 위치와 검증 지점을 매핑한다.
**입력**: `nfr-requirements.md`, `functional-design.md`, 구현 파일(§ 매핑).

---

## 1. 보안 설계 (NFR-2)

### 1.1 비밀번호 해싱 (SEC-1)
- **메커니즘**: `app/security.py`의 `hash_password`/`verify_password` — `bcrypt.gensalt(rounds=settings.bcrypt_cost)`(기본 **12**). 관리자·테이블 비밀번호 공통.
- **저장**: `admin_user.password_hash`, `table.table_password_hash` (String(255)). 평문 컬럼 없음.
- **흐름**: 설정 시 `identify.setup_table` → `hash_password(table_password)`. 검증 시 `verify_password`(bcrypt `checkpw`, 예외는 False로 흡수 → 타이밍/포맷 오류 안전).
- **구성**: `BCRYPT_COST` env(테스트는 4로 낮춰 속도 확보).

### 1.2 JWT 발급/검증 (SEC-2, SES-1)
- **단일 출처**: JWT 프리미티브를 `app/auth/dependency.py`에 집약 → `encode_admin_token(admin_id, store_id)`, `verify_token(token) -> AdminContext`. `auth_service`는 이를 재사용(`issue_token`/`verify_token`) → **import 사이클 회피**(auth_service → dependency 단방향).
- **클레임**: `{sub, admin_id, store_id, iat, exp}`, `exp = now + jwt_expire_hours(16h)`, 알고리즘 **HS256**, 시크릿 `settings.jwt_secret`.
- **검증 실패 분기**: `ExpiredSignatureError` → 만료 안내, 기타 `PyJWTError`/클레임 파싱 실패 → 무효 안내. 모두 `AppError(UNAUTHORIZED)`(401)로 통일, 공유 ErrorHandler가 구조화 바디로 변환.
- **의존성 주입**: `get_current_admin(authorization: Header)` — `Bearer ` 접두 검사 후 `verify_token`. 보호 라우터는 `Depends(get_current_admin)`로 소비(U3/U5/U6 동일 계약 사용).

### 1.3 로그인 시도 제한 (SEC-3)
- **자료구조**: `auth_service._attempts: dict[key, (failures, locked_until)]`, `key="{store_code}::{username}"`, `threading.Lock`으로 보호(FastAPI 스레드풀 안전).
- **정책**: `_MAX_FAILURES=5`, `_LOCKOUT=5min`. `register_login_attempt(success)` — 성공 시 pop(리셋), 실패 시 증가 후 5회≥면 `locked_until` 설정. `_is_locked`는 잠금 만료 시 자동 pop(창 리셋).
- **적용점**: `authenticate` 진입 시 `_is_locked` → `TOO_MANY_ATTEMPTS`(429). 자격 실패 시 `register_login_attempt(False)`, 성공 시 `(True)`.
- **한계(비목표)**: 인메모리·단일 프로세스 전제. 재시작 시 카운터 리셋 허용(MVP). 분산 공유는 범위 밖.

### 1.4 사용자 열거 방지 (SEC-4)
- 매장/관리자 부재(`admin is None`)와 비밀번호 불일치를 **동일 분기**로 처리 → 단일 메시지·401. 존재 여부 유출 없음.

### 1.5 테이블 인증 경계 (SEC-5)
- `resolve_session_context`는 store→table 조회 + `verify_password`만 수행하고 **JWT 미발급**. 반환은 `TableSessionContext{store_id, table_id, session_id=None}`. 라우터 응답 `TableLoginResponse{store_id, table_id}`에 토큰 필드 없음.
- 실패 매핑: 매장/테이블 부재 → **404(NOT_FOUND)**, 미활성/비밀번호 불일치 → **401(UNAUTHORIZED)**.

### 1.6 시크릿·에러 위생 (SEC-6)
- `.env`(미커밋) + `.env.example`(커밋). 로컬 fallback은 `config.Settings` 기본값(`dev-insecure-change-me`) — 운영 시 override.
- 에러는 항상 `{error:{code,message,details}}`로만 노출(스택/시크릿 미노출). 미처리 예외는 500(INTERNAL) 일반 메시지.

---

## 2. 세션 설계 (NFR-3)

### 2.1 관리자 16h 세션 (SES-1)
- **서버**: 토큰 `exp`로만 만료 강제(무상태). 서버측 세션 저장 없음 → 확장·이식 단순.
- **프론트**: `auth-context.tsx`가 `token`을 localStorage(`auth_token`)에 저장, `isAuthenticated()`는 payload `exp`를 디코드해 **클라이언트 선(先)만료 검사**(만료 시 보호 화면 진입 차단·재로그인 유도). 새로고침은 초기 state를 localStorage에서 복원 → 세션 유지.

### 2.2 테이블 세션 식별·지속 (SES-2)
- **저장 키**: `table-session-context.tsx`의 `TABLE_CONFIG_KEY="table_config"` = `{storeCode, tableNumber, tablePassword}`. `saveTableConfig`(설정/수동 로그인 시)·`readTableConfig`(bootstrap 시).
- **bootstrap()**: 설정 있으면 `/api/customer/table-login` 호출 → `{store_id, table_id}`를 `infoRef`+state에 반영. 새로고침 시 재-bootstrap로 동일 컨텍스트 복원. 설정 없으면 `AutoLoginBootstrap`가 초기설정 안내.
- **경계**: `session_id`는 여기서 null. 실제 세션은 U4 주문 생성 시 U6 `get_or_start_active_session`이 발급(런타임 계약).

### 2.3 세션 경계 준수 (SES-3)
- `services/table_session/__init__.py`: U2의 `setup_table`·`resolve_session_context`만 `identify`로 **지연 임포트 배선**(패키지 순환 회피). `get_or_start_active_session`·`close_table`은 **NotImplementedError 스텁 유지**(U6/E 소유). → U2 머지가 U6 미구현 상태에서도 임포트 안전.

---

## 3. 사용성·테스트·이식성 설계

### 3.1 사용성 (USA-1 / NFR-4)
- `AdminLoginView`·`TableSetupView`·`TableLoginView`가 공유 `shared/ui/Button`(min 44×44px, NFR-4) 사용. 입력 필드 `minHeight:44`. 오류 메시지 `role="alert"`, 성공 피드백 별도 색상.

### 3.2 테스트 (TST-1 / NFR-6)
- `backend/tests/conftest.py`: 앱 import 전 `DATABASE_URL`을 임시 파일로 지정(모듈 레벨 엔진 격리), 세션 스코프 시드(store/admin/table), 테스트 간 `_attempts.clear()`.
- `test_auth.py`(6): 성공·오답·미지매장(열거방지)·5회 잠금(429)·성공 시 카운터 리셋·만료 토큰 401.
- `test_table_session.py`(7): 인증요구(401)·생성+자동로그인·덮어쓰기·검증오류(422)·매장/테이블 부재(404)·비밀번호 오류(401).
- **결과**: 13 pass. (U2 PBT 미배정 → 예제 기반으로 충분 커버.)

### 3.3 이식성 (POR-1 / NFR-7)
- SQLite 파일 + `create_all()`(마이그레이션 도구 불필요). 설정은 `pydantic-settings`가 `.env`/환경변수에서 로드, 없으면 로컬 fallback. Docker·외부 서비스 의존 없음.

---

## 4. 요구사항 → 구현/검증 매핑

| 요구 | 구현 위치 | 검증 |
|---|---|---|
| SEC-1 | `app/security.py`, `identify.setup_table` | DB 해시 형식 / 설정·로그인 테스트 |
| SEC-2, SES-1 | `auth/dependency.py`(encode/verify/get_current_admin), `config.py` | `test_auth`(토큰 검증·만료), 스모크(보호 401) |
| SEC-3 | `auth_service`(`_attempts`,`_is_locked`,`register_login_attempt`) | `test_auth`(429·리셋) |
| SEC-4 | `auth_service.authenticate` 단일 분기 | `test_auth`(미지매장/오답 동일 401) |
| SEC-5 | `identify.resolve_session_context`, `routers/table_setup` | `test_table_session`(404/401, 토큰 부재) |
| SEC-6 | `.env.example`, `errors.py` | 커밋 목록 / 에러 바디 |
| SES-2 | `table-session-context.tsx` | typecheck/build, localStorage 라운드트립 |
| SES-3 | `services/table_session/__init__.py` | import 안전(스텁 유지) |
| USA-1 | `features/*` + `shared/ui/Button` | `npm run build` |
| POR-1 | `config.py`, `db.py`, `.env.example` | 로컬 기동 스모크 |

---

## 5. 잔여 리스크·후속(Infrastructure 단계 연계)
- **인메모리 시도 제한**: 다중 워커 배포 시 무효 → 배포를 단일 프로세스로 제약(NFR-7 로컬 전제와 정합). 확장 시 공유 저장소 필요(비목표).
- **클라이언트 만료 검사**: 프론트 `isAuthenticated`는 편의성 검사이며, **권위 있는 강제는 서버 401**. 시계 오차는 서버 검증으로 보정.
- **HTTPS 부재**: localStorage 토큰은 로컬 개발 전제에서 허용. 운영 이관 시 전송 보안·저장 위치 재검토(Infrastructure 산출물에서 다룸).
