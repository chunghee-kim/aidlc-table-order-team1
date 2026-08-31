# U1 Foundation — Business Logic Model (Functional Design)

**단계**: CONSTRUCTION — Phase 0 (U1 Foundation & Data) — Functional Design
**범위**: 부팅 흐름, DbSession 라이프사이클, Health 체크, ErrorHandler 매핑, 앱 셸 라우팅(라우트 레지스트리), **Phase 0 계약 동결 목록**. (U1은 UI 화면 없음 → `frontend-components.md` 생략)

## 1. 부팅 흐름 (AppBootstrap)
```
uvicorn app.main:app
  → app.main: FastAPI() 생성
  → Base.metadata.create_all(engine)     # 스키마 생성(멱등, create_all)
  → register exception handlers(ErrorHandler)  # AppError·Exception → 구조화 바디
  → add CORS (Vite dev origin)
  → include_router(health)               # /api/health (U1 소유)
  # 스트림 라우터(auth/menu/order/...)는 Phase 1에서 각자 include
```
- 시드는 부팅과 분리된 별도 진입점 `python -m app.seed` 로 실행(멱등). 최초 1회 또는 재실행 안전.

## 2. DbSession 라이프사이클 (DbSessionProvider)
```
get_db() (FastAPI Depends, 요청 스코프)
  db = SessionLocal()
  try: yield db
  finally: db.close()
```
- 트랜잭션 커밋/롤백 경계는 **서비스 메서드**가 소유(`services.md §3`). 리포는 주입받은 세션 사용.

## 3. Health 체크 로직 (HealthRouter)
```
GET /api/health
  → SELECT 1 (DB 핑)
  → 200 { "status": "ok", "db": "ok" }   (DB 오류 시 db:"error" + 503)
```

## 4. ErrorHandler 매핑 흐름
```
서비스/라우터 → raise AppError(code, message, details)
  → exception_handler(AppError) → HTTP(code→status) + {error:{code,message,details}}
미처리 Exception → 500 {error:{code:"INTERNAL", ...}}
RequestValidationError(FastAPI) → 422 {error:{code:"VALIDATION_ERROR", details:{...}}}
```
- code↔HTTP 매핑 표는 `business-rules.md §8`.

## 5. 앱 셸 라우팅 — 라우트 레지스트리 패턴 (프론트)
```
main.tsx
  → BrowserRouter
  → /customer/*  및 /admin/*  최상위 경로
  → features/*/routes.ts 가 export한 라우트를 수집(collectRoutes)
  # main.tsx는 Phase 0 소유. 각 스트림은 자기 features/<name>/routes.ts만 편집
  # → main.tsx 동시 편집 제거(머지 충돌 0)
```
- Phase 0은 `/customer`·`/admin` 진입 가능한 최소 셸 플레이스홀더만 제공(스트림이 실제 뷰를 라우트 레지스트리에 추가).

## 6. Phase 0 계약 동결 목록 (후속 유닛 참조 지점) ★
> `component-methods.md` 시그니처와 정확히 일치하는 스텁으로 동결. 계약 변경은 소유자+소비자 페어 합의 후 스텁 먼저 갱신(`parallel-execution.md §6`).

**Backend**
- `app/schemas/*` — 전 엔드포인트 Pydantic 요청/응답 + 공통 `OrderView`/`ErrorBody` (API 계약, `application-design.md §3`).
- `app/auth/dependency.py` — `AuthDependency`(JWT 검증) + `AdminContext`. 소비: U3/U5/U6 보호 엔드포인트. 실구현: U2/A.
- `app/services/table_session/__init__.py` — 프로토콜: `setup_table`, `resolve_session_context`(U2/A), `get_or_start_active_session`, `close_table`(U6/E).
- `app/services/order/__init__.py` — 파사드: `create_order`, `list_current_session_orders`, `list_admin_orders`(U4/C), `change_status`, `delete_order`(U5/D).
- `app/services/order_event_broker.py` — 프로토콜: `publish`/`subscribe`/`unsubscribe`/`snapshot`. 실구현: U5/D.
- `app/repositories/*` — 리포 인터페이스(특히 `MenuRepo.list_by_store` 단가 확정 계약).

**Frontend**
- `context/auth-context`·`table-session-context`·`cart-context` — Context 인터페이스(`component-methods.md §4.1~4.3`).
- `shared/api/sse-client.ts` — `SseClient`(`connect`/`disconnect`).
- `shared/api/api-client.ts` — `ApiClient`(실구현, U1 소유, 각 유닛이 엔드포인트 추가).

## 7. DoD (Phase 0)
DB 생성·시드 성공, FastAPI/Vite 기동, `/customer`·`/admin` 진입, `/health` 200, **전 계약 스텁 임포트/타입체크 통과**. 달성 시 Phase 1(U2~U6 5스트림) 착수 신호.
