# U2 Auth & Session — NFR Requirements (정의)

**단계**: CONSTRUCTION — Phase 1 · 스트림 A (U2) — **NFR Requirements (Part 1: 정의)**
**목적**: U2가 책임지는 비기능 요구사항을 **측정 가능한 목표(target)와 수용 기준**으로 확정한다. 설계·구현 방법은 `nfr-design.md`에서 다룬다.
**근거**: `inception/requirements/requirements.md §5`(NFR-1~7), `inception/user-stories/stories.md`(US-A-01~04, US-C-01/02), `construction/u2-auth/functional-design/functional-design.md`.

> 확장 설정(`aidlc-state.md`): Security Baseline = **미적용**(요구사항 명시분만 구현), Resiliency Baseline = **미적용**, PBT = 적용(단, U2는 PBT 미배정 → 예제 기반 테스트로 커버).

---

## 1. U2에 적용되는 NFR (매핑)

| NFR | 범주 | U2 적용 여부 | 스토리 |
|---|---|---|---|
| NFR-2 | 보안 | ✅ **주(主) 책임** — bcrypt, JWT, 로그인 시도 제한 | US-A-01/03, US-C-01/02 |
| NFR-3 | 세션 | ✅ **주 책임(일부)** — 관리자 16h 세션, 테이블 세션 **식별**(라이프사이클은 U6) | US-A-02/04, US-C-02 |
| NFR-7 | 이식성 | ✅ 로컬 실행·간단 셋업(시크릿 `.env`) | — |
| NFR-4 | 사용성 | ◐ 부분 — 로그인/설정 폼 터치 타깃 ≥44×44px | US-A-04 |
| NFR-6 | 테스트 | ◐ 부분 — U2는 PBT 미배정, 예제 기반 테스트로 인증/식별 커버 | — |
| NFR-1 | 성능 | ✖ 해당 없음(SSE는 U5) | — |
| NFR-5 | 데이터 지속성 | ◐ 클라이언트 토큰/테이블 설정 localStorage 지속(주문/이력 저장은 U4/U6) | US-C-02 |

---

## 2. 측정 가능한 요구사항 (Targets & Acceptance)

### NFR-2 보안 (Security)

**SEC-1 — 비밀번호 저장**
- 요구: 관리자·테이블 비밀번호는 **평문 저장 금지**, bcrypt 해시(**cost 12**)로만 저장.
- 수용: DB의 `admin_user.password_hash`·`table.table_password_hash`가 bcrypt(`$2b$12$…`) 형식. 평문/역산 가능 형태 부재.

**SEC-2 — 관리자 인증 토큰**
- 요구: 인증은 **JWT(HS256)**, 클레임 `{admin_id, store_id, exp}`. 서명 시크릿은 환경변수(`JWT_SECRET`).
- 수용: 보호 엔드포인트는 유효한 `Authorization: Bearer <jwt>` 없이는 **401(UNAUTHORIZED)**. 위조/변조 토큰 401.

**SEC-3 — 로그인 시도 제한 (US-A-03)**
- 요구: 동일 `(store_code, username)` 연속 실패 **5회** 초과 시 **5분** 잠금.
- 수용: 5회 실패 후 6번째 시도는 자격 정확 여부와 무관하게 **429(TOO_MANY_ATTEMPTS)**. 성공 시 카운터 리셋. 잠금 창 경과 후 자동 해제.

**SEC-4 — 사용자 열거 방지**
- 요구: 매장/사용자 부재와 비밀번호 불일치를 **동일 메시지·동일 상태(401)**로 응답.
- 수용: "매장 식별자, 사용자명 또는 비밀번호가 올바르지 않습니다." 단일 메시지.

**SEC-5 — 테이블 인증 경계**
- 요구: 테이블 로그인은 **테이블 비밀번호**만으로 store/table **식별 컨텍스트**만 반환. 관리자 권한/JWT를 발급하지 않음.
- 수용: `/api/customer/table-login` 응답에 토큰·관리자 정보 부재. 비밀번호 불일치 401, 매장/테이블 부재 404.

**SEC-6 — 시크릿 비노출**
- 요구: `JWT_SECRET` 등 실 시크릿은 커밋 금지(`.env`만 로컬, `.env.example`만 커밋). 에러 응답에 시크릿/스택 미노출(구조화 에러 바디).

### NFR-3 세션 (Session)

**SES-1 — 관리자 16시간 세션 (US-A-02)**
- 요구: 발급 JWT 만료 = **16시간**(`JWT_EXPIRE_HOURS`, 기본 16). 만료 후 보호 자원 접근 시 자동 로그아웃 유도.
- 수용: 토큰 `exp` = iat+16h(±허용오차). 만료 토큰으로 접근 시 401. 새로고침 시 만료 전이면 재로그인 불필요.

**SES-2 — 테이블 세션 식별 유지 (US-C-01/02)**
- 요구: 태블릿 설정 정보(store_code/table_number/table_password)를 클라이언트에 지속, 앱 재진입·새로고침 시 자동 재식별.
- 수용: 새로고침 후에도 동일 store/table로 `getContext()` 복원. 세션 **시작(session_id 발급)은 U6**에 위임 → U2는 `session_id=None`으로 식별만.

**SES-3 — 세션 경계 준수**
- 요구: U2는 세션 **식별·설정**만. `get_or_start_active_session`·`close_table`은 **U6/E 스텁 유지**(U2가 구현·호출하지 않음).
- 수용: `services/table_session/__init__.py`에서 U2 함수(identify)만 배선, lifecycle은 미배선.

### NFR-4 사용성 (Usability, 부분)
**USA-1** — 로그인·테이블 설정·테이블 로그인 폼의 상호작용 버튼 터치 타깃 **≥ 44×44px**(공유 `Button` 프리미티브 사용). 오류는 `role="alert"`로 노출.

### NFR-6 테스트 (부분)
**TST-1** — U2는 PBT 미배정. **예제 기반 테스트**로 다음을 커버: 로그인 성공/실패/열거방지/잠금(429)/카운터 리셋/토큰 만료, 테이블 설정(생성·덮어쓰기·검증오류·인증요구), 테이블 로그인(404/401/성공).

### NFR-7 이식성 (Portability)
**POR-1** — 추가 인프라 없이 로컬 실행(SQLite 파일, Docker 불필요). 설정은 `.env`(로컬 fallback 기본값 제공). `pip install` + `python -m app.seed` + `uvicorn` + `npm run dev`로 기동.

---

## 3. 비목표 (Out of Scope, U2)
- 리프레시 토큰/토큰 갱신·서버측 세션 무효화(로그아웃 블랙리스트) — MVP 범위 밖.
- 분산·다중 프로세스 환경의 시도 제한 공유(현재 인메모리, 단일 프로세스 전제).
- HTTPS/전송 보안·CORS 강화·레이트리밋(전역) — 로컬 개발 전제(NFR-7). Security Baseline 확장 미적용.
- 테이블 세션 라이프사이클(시작/완료), 실시간 성능(NFR-1) — U6/U5 소유.

---

## 4. 검증 방법 (요약)
- **SEC-1**: 시드/설정 후 DB 컬럼 해시 형식 확인.
- **SEC-2/3/4, SES-1**: `backend/tests/test_auth.py`(로그인/잠금/만료/열거방지) + 토큰 `exp` 검사.
- **SEC-5, SES-2/3**: `backend/tests/test_table_session.py`(식별·인증경계) + 프론트 localStorage 라운드트립.
- **USA-1**: 프론트 `Button`(min 44×44) 사용, `npm run build` 통과.
- **POR-1**: `.env.example` 커밋·`.env` 미커밋, 로컬 기동 스모크.

> Part 2(설계) = `nfr-design.md`: 위 요구사항을 어떤 메커니즘·구성으로 충족하는지.
