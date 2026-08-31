# 5인 병렬 실행 계획 (Parallel Execution Plan)

**단계**: INCEPTION — Application Design (병렬화 보강)
**범위**: U1~U6 의존성 확정, 병렬 적합성 평가, 공통 기반 1인 선행 + 5인 병렬 스트림, 머지 최적화, 검증.
**근거**: `unit-of-work.md`, `unit-of-work-dependency.md`, `component-dependency.md`, `component-methods.md`, `services.md`.

> 확정 결정: **총 5인**(1인이 공통 기반 먼저), 공유 서비스 **파일 분리 적용**, 공통 단계에서 **계약 동결(Contract-First)**.

---

## 1. 의존성 확정 (U1~U6)

`unit-of-work-dependency.md §1`·`component-dependency.md §7` 기준 실제 의존 DAG:

```
U1 ─┬─▶ U2 ─┬─▶ U3 ──▶ U4 ─┬─▶ U5 ──▶ U6
    │       │              │          ▲
    └───────┴──────────────┴──── (U6은 U4·U5 데이터 의존)
U4 ──ⓒ위임──▶ U6 (get_or_start_active_session, 런타임 계약. 빌드는 단방향 U4→U6)
```

| 유닛 | 하드 의존 | 의존 이유 |
|---|---|---|
| U1 | 없음 | 공유 기반(9모델·DB·에러·시드·ApiClient) |
| U2 | U1 | 모델·DB세션·에러 규약 |
| U3 | U1, U2 | Menu/Category 모델 + AuthDependency(보호 엔드포인트) |
| U4 | U1, U2, U3 | Order 모델·세션 컨텍스트·**MenuRepo 단가 확정** |
| U5 | U1, U2, U4 | 주문 데이터·상태, 주문 생성이 이벤트 소스 |
| U6 | U1, U2, U4, U5 | 세션/주문 데이터, 이용완료가 대시보드(U5) 리셋 유발 |

**소결론**: 크리티컬 체인은 U1→U2→U3→U4→U5→U6로 **완전 선형** → 유닛 단위 그대로는 사실상 순차. 의존을 "빌드 타임 하드 의존"에서 "머지 타임 통합"으로 낮춰야 병렬 이점이 생긴다.

---

## 2. 병렬 적합성 평가 (현 순서 → 최적화)

**현 순서(선형)는 병렬 부적합.** 이유: (1) 스트림 4개 유휴, (2) 공유 파일(§4 핫스팟) 동시 편집 시 머지 충돌.

**최적화 원리 3가지:**
- **계약 우선(Contract-First)**: U1 단계에서 전 교차 인터페이스를 **스텁으로 동결** → 각 스트림은 구현이 아닌 인터페이스에 대고 개발.
- **파일 분리(Merge-Optimized Ownership)**: 공유 서비스를 관심사별 파일로 분리 → **1파일 = 1스트림 소유**.
- **수직 슬라이스 소유**: 각 스트림이 라우터/서비스/리포/뷰/컨텍스트를 자기 폴더에서 소유 → 충돌면 제거.

---

## 3. Phase 0 — 공통 기반 (1인 선행 · 유일 직렬 구간)

담당 1인이 **U1 전체 + 전 교차 계약 동결**을 완성·머지한다. 이것이 유일한 크리티컬 패스.

### 3.1 U1 실체 구현
- 백엔드: `app/main.py`(AppBootstrap), `app/db.py`(DbSessionProvider), `app/errors.py`(ErrorHandler + 공통 에러코드 enum), `app/seed.py`(멱등 시드), `app/models/`(**9모델 전량**), `routers/health.py`
- 프론트: `main.tsx`(/customer·/admin 라우팅 — **라우트 레지스트리 패턴**), `shared/api-client.ts`(ApiClient), 공통 UI 프리미티브

### 3.2 계약 동결 (스텁 — 시그니처만, `NotImplementedError`/mock 반환)
`component-methods.md` 시그니처를 그대로 스텁 커밋:
- `app/auth/dependency.py` — `AuthDependency`(JWT 검증) 인터페이스 + dev 통과 스텁
- `app/services/table_session/__init__.py` — 프로토콜: `get_or_start_active_session(table_id)->TableSession`, `close_table(...)->CloseResult`, `resolve_session_context(...)`, `setup_table(...)`
- `app/services/order/__init__.py` — 파사드: `create_order`, `list_current_session_orders`, `list_admin_orders`, `change_status`, `delete_order`
- `app/services/order_event_broker.py` — 프로토콜: `publish/subscribe/unsubscribe/snapshot`
- `app/repositories/*.py` — 리포 인터페이스 스텁(특히 `MenuRepo.list_by_store` 단가 확정 계약)
- `app/schemas/` — 전 엔드포인트 Pydantic 요청/응답 스키마(API 계약 동결)
- 프론트 `context/` — `AuthContext`·`TableSessionContext`·`CartContext` 인터페이스 + `shared/sse-client.ts` 시그니처

### 3.3 Phase 0 DoD
DB 생성·시드·FastAPI/Vite 기동·`/health` 응답 + 모든 계약 스텁 임포트/타입체크 통과. 머지 후 5인 착수 신호.

> 병행: 나머지 4인은 대기하지 않고 자기 스트림의 Functional Design 답변·PBT 속성 정의·프론트 목업/테스트 스텁 준비.

---

## 4. Phase 1 — 5개 병렬 스트림 (5인 · 계약 스텁 대상 개발)

한 스트림 = 한 사람 = 한 유닛. 각 스트림은 **소유 파일만** 편집(교차 지점은 §5 파일 분리로 제거).

| 스트림 | 유닛 | 소유 백엔드 | 소유 프론트 | 계약 소비(스텁) |
|---|---|---|---|---|
| **A. Auth & Table Setup** | U2 | `auth_service.py`, `auth/dependency.py`(실구현), `routers/auth.py`, `routers/table_setup.py`, `services/table_session/identify.py`, `repositories/{store,admin_user,table,session}.py` | `AdminLoginView`, `TableSetupView`, `AutoLoginBootstrap`, `AuthContext`·`TableSessionContext` 구현 | — (최상류) |
| **B. Menu** | U3 | `menu_service.py`, `routers/menu.py`, `repositories/{menu,category}.py` | `MenuBrowseView`, `MenuManageView` | AuthDependency |
| **C. Cart & Order** | U4 | `services/order/create.py`, `routers/order.py`, `repositories/order.py` | `CartContext` 구현, `CartView`, `OrderConfirmView`, `OrderSuccessView`, `CurrentOrdersView` | MenuRepo(단가)·TableSessionService·EventBroker |
| **D. Monitoring (SSE)** | U5 | `services/order/admin.py`, `order_event_broker.py`(실구현), `routers/admin_order.py` | `SseClient` 구현, `MonitoringDashboardView`, `OrderDetailModal` | OrderRepo·AuthDependency |
| **E. Session Lifecycle & History** | U6 | `services/table_session/lifecycle.py`(실구현), `history_service.py`, `routers/table_close.py`, `routers/history.py`, `repositories/order_history.py` | 이용완료 플로우, `OrderHistoryView` | OrderRepo·EventBroker·AuthDependency |

**PBT 배정**(스트림 내 소유): B=가격>0·필수필드 / C=총액·수량·로컬 라운드트립 / D=상태전이·삭제후 총액 / E=활성세션≤1·무손실 이관.

**착수 팁**: A가 AuthDependency·Context 실구현을 먼저 머지하면 B/D/E가 스텁을 실구현으로 조기 교체. C·E는 §5.2 세션 계약을 초반 페어로 합의.

---

## 5. 머지 최적화 — 공유 파일 분리 (현 설계 이탈, 확정)

`unit-of-work.md §3`의 "1파일 다유닛 소유"를 **1파일 1스트림 소유**로 재편.

### 5.1 `order_service.py` → `services/order/` 패키지
- `create.py` (C/U4): `create_order`, `list_current_session_orders`, `list_admin_orders`
- `admin.py` (D/U5): `change_status`, `delete_order`
- `__init__.py`: 파사드 — Phase 0 스텁 동결, 이후 편집 최소

### 5.2 `table_session_service.py` → `services/table_session/` 패키지
- `identify.py` (A/U2): `setup_table`, `resolve_session_context`
- `lifecycle.py` (E/U6): `get_or_start_active_session`, `close_table`
- `__init__.py`: 프로토콜 + 조립(Phase 0 동결)

### 5.3 TableRouter 분리
`routers/table_setup.py`(A/U2) + `routers/table_close.py`(E/U6) — 경로(`/api/admin/tables/{id}/setup`·`/close`)는 유지.

### 5.4 프론트 라우팅
`main.tsx`는 Phase 0 소유. 각 스트림은 `features/*/routes.ts`에 자기 라우트를 export → `main.tsx`가 수집. 스트림이 `main.tsx`를 편집하지 않음.

### 5.5 Context/Repo
각 Context·Repo는 단일 스트림 소유(§4 표) → 동시 편집 없음.

**결과**: 남는 통합 지점은 (a) `services/order/__init__.py`·`services/table_session/__init__.py` 파사드, (b) `services/__init__.py` DI 조립뿐. 모두 Phase 0 스텁 동결로 후속 편집 1~2줄.

---

## 6. 통합 & 머지 규율

- **브랜치**: `feat/u2-auth` … `feat/u6-session` 스트림별. `main` 대상 소단위 PR.
- **머지 순서**: A → B → C → (D, E 병렬) → 파사드/DI 조립 PR. D↔E는 서로 다른 파일이라 순서 무관.
- **계약 변경 금지 규칙**(`unit-of-work.md §5` 승계): Phase 0 동결 계약 변경 시 소유자+소비자 페어 합의 후 스텁 먼저 갱신.
- **CI**: 스트림별 테스트 + PBT는 각 PR에서 그린. 통합 PR에서 종단 시나리오.

---

## 7. 검증 (Verification)

1. **Phase 0**: `python -m app.seed` 후 `uvicorn app.main:app` + `npm run dev` → `/health` 200, `/customer`·`/admin` 진입, 전 계약 스텁 임포트 통과.
2. **스트림별**: 각 스트림 DoD(`unit-of-work.md §2`) + 담당 PBT 통과(`pytest`/`vitest`). 스텁 대상으로 단독 실행 가능.
3. **머지 충돌 측정**: 각 스트림 PR 변경 파일 집합이 §4 표와 일치(교집합 ≈ 공백)임을 확인 → 충돌 0 목표.
4. **종단 통합**: 고객 주문(C) → SSE 대시보드 반영(D, ≤2초) → 상태 변경 → 이용완료(E) 총액 0·이력 보존 → 세션 재시작(C↔E 계약). `services.md §2.4~2.8` 흐름대로 수동 시나리오 + 통합 테스트.

---

## 8. 요약

- U1~U6 하드 의존은 **완전 선형** → 유닛 단위 병렬 부적합.
- **Phase 0(1인)**: U1 + 전 교차 계약 스텁 동결 (유일 직렬 구간).
- **Phase 1(5인)**: 계약 스텁 대상 5개 수직 스트림(A~E = U2~U6) 병렬.
- **머지 최적화**: `order_service`·`table_session_service`·TableRouter 파일 분리 + 라우트 레지스트리 → 1파일 1소유 → 충돌 핫스팟 제거.
