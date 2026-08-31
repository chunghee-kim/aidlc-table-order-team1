# U2 Auth & Session — Functional Design

**단계**: CONSTRUCTION — Phase 1 · 스트림 A (U2 Auth & Session)
**책임**: 관리자 JWT 인증(16h)·로그인 시도 제한, 테이블 태블릿 초기 설정, 테이블 세션 **식별**·자동 로그인.
**스토리**: US-A-01(로그인), US-A-02(16h 유지), US-A-03(시도 제한), US-A-04(태블릿 설정), US-C-01(자동 로그인), US-C-02(세션 식별 유지).
**경계**: 세션 **라이프사이클(시작/완료)**은 U6 소유. U2는 **식별·설정**만. `get_or_start_active_session`/`close_table`은 U6/E 스텁 유지.
**소비 계약**: 없음(최상류). **제공 계약**: `AuthDependency.get_current_admin`(U3/U5/U6이 보호 엔드포인트에 사용), `AuthContext`/`TableSessionContext`(U4가 세션 컨텍스트 주입).

---

## 1. 소유 파일 (parallel-execution.md §4, 1파일=1소유)

### 백엔드
- `app/auth/dependency.py` — JWT 인코드/디코드 + `verify_token` + `get_current_admin` (스텁 → 실구현)
- `app/services/auth_service.py` — `authenticate`·`issue_token`·`verify_token`·`register_login_attempt`
- `app/routers/auth.py` — `POST /api/admin/login`
- `app/routers/table_setup.py` — `POST /api/admin/tables/{id}/setup`, `POST /api/customer/table-login`
- `app/services/table_session/identify.py` — `setup_table`·`resolve_session_context`
- `app/services/table_session/__init__.py` — U2 두 함수만 identify로 위임(파사드 배선, 시그니처 불변)
- `app/repositories/{store,admin_user,table,session}.py` — Protocol + 구체 구현(`Sql*Repo`)
- `app/main.py` — Phase 1 마킹 구역에 `auth`·`table_setup` 라우터 include (스트림별 1줄 추가 허용)

### 프론트엔드
- `src/context/auth-context.tsx` — 실구현(로그인/토큰/16h 만료 검사)
- `src/context/table-session-context.tsx` — 실구현(로컬 설정 → table-login → 컨텍스트, 새로고침 유지)
- `src/features/admin/auth/{AdminLoginView,TableSetupView,routes}.tsx`
- `src/features/customer/auto-login/{AutoLoginBootstrap,TableLoginView,routes}.tsx`

### 테스트
- `backend/tests/{conftest,test_auth,test_table_session}.py` — 인증/설정/식별 유닛·통합 테스트.

---

## 2. 결정 사항

### D1. JWT (US-A-01/02)
- HS256, 클레임 `{sub, admin_id, store_id, iat, exp}`, 만료 `settings.jwt_expire_hours`(기본 16h). 시크릿 `settings.jwt_secret`.
- `Authorization: Bearer <token>` 헤더로 전달. 검증 실패/만료 → `AppError(UNAUTHORIZED)` (401). 프론트는 페이로드 `exp`로 만료를 선검사(만료 시 자동 로그아웃).

### D2. 로그인 시도 제한 (US-A-03, Should)
- **인메모리** 카운터(`(store_code, username)` 키). 연속 실패 **5회** → **5분** 잠금 → `TOO_MANY_ATTEMPTS`(429). 성공 시 카운터 리셋, 잠금 만료 시 자동 해제. 단일 프로세스 MVP 전제(재시작 시 리셋 허용).

### D3. 테이블 설정 (US-A-04)
- 프론트 요청: `{table_number, table_password}`(경로 `{id}`는 REST 관례상 유지하되 **upsert 키는 `(store_id, table_number)`** — 동결된 서비스 시그니처 준수).
- 동작: `(store_id, table_number)` 존재 시 비밀번호/활성 갱신(**덮어쓰기**), 없으면 생성. 응답 `{table_id, table_number, auto_login_enabled=true}`. 중복 확인 UX는 프론트(저장 전 확인 팝업).
- 검증: `table_number ≥ 1`, 비밀번호 비어있지 않음 → 위반 시 `VALIDATION_ERROR`(422). 비밀번호는 bcrypt(cost 12) 해시 저장.

### D4. 세션 식별 (US-C-01/02)
- `resolve_session_context(store_code, table_number, table_password)`: store→table 조회, 비밀번호 검증 → `TableSessionContext{store_id, table_id, session_id=None}`.
- **세션 ID는 여기서 발급하지 않음** — 첫 주문 시 U4→U6 `get_or_start_active_session`이 발급(경계 준수). 실패: 매장/테이블 없음 → `NOT_FOUND`(404), 비밀번호 불일치/비활성 → `UNAUTHORIZED`(401).
- 프론트 태블릿 설정 정보(`storeCode/tableNumber/tablePassword`)는 태블릿 localStorage(`table_config`)에 저장 → 앱 진입 시 자동 로그인, 새로고침에도 유지.

### D5. 서비스-세션 관리
- 동결 서비스 시그니처에 DB 세션 파라미터가 없으므로 서비스가 `SessionLocal()`로 요청당 세션을 열고 커밋/클로즈. 리포는 세션을 생성자로 주입받는 구체 클래스(`Sql*Repo(db)`)로 Protocol 구현.

### D6. 파사드 배선 (services/table_session/__init__.py)
- 동결 데이터클래스/시그니처 유지. U2 두 함수 본문만 `identify` 지연 임포트로 위임(순환 임포트 회피). U6 `lifecycle` 미도입 상태에서도 임포트 안전.

---

## 3. 엔드포인트 계약 (schemas/ 동결 준수)

| 메서드·경로 | 인증 | 요청 | 응답 | 실패 |
|---|---|---|---|---|
| `POST /api/admin/login` | 공개 | `LoginRequest` | `LoginResponse{token, admin}` | 401 자격 오류 / 429 잠금 |
| `POST /api/admin/tables/{id}/setup` | 관리자 | `TableSetupRequest` | `TableSetupResponse` | 401 / 422 |
| `POST /api/customer/table-login` | 공개 | `TableLoginRequest` | `TableLoginResponse` | 404 / 401 |

---

## 4. 검증 (DoD)
- 관리자 로그인/16h 만료/새로고침 유지, 태블릿 자동 로그인, 세션 컨텍스트가 이후 주문(U4)에 전파 가능(`getContext()`).
- 오답 5회 → 429. 보호 엔드포인트가 `Depends(get_current_admin)`로 실제 JWT 검증.
- `pytest`(백엔드 인증/설정/식별) 그린, `npm run typecheck`/`build` 통과.
- 스트림 변경 파일 집합이 §1과 일치(교집합≈공백) → 머지 충돌 0.

> U2는 PBT 미배정(parallel-execution.md §4). 인증/식별의 결정적 유닛·통합 테스트로 커버.
