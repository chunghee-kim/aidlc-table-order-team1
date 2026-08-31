# U3 Menu — NFR 설계 패턴 (NFR Design Patterns)

**단계**: CONSTRUCTION — Phase 1 (스트림 B) [U3 Menu] — NFR Design
**유닛**: U3 Menu
**입력**: `construction/u3-menu/nfr-requirements/*`, `construction/plans/u3-menu-nfr-design-plan.md`(Q1~Q7 권장)

> U3 NFR을 **구현 가능한 설계 패턴**으로 매핑합니다. 각 패턴은 적용 코드 위치와 대응 NFR ID를 명시합니다. **미적용 패턴은 정당화**를 함께 기록합니다(overconfidence-prevention).

---

## 1. 검증 패턴 (Reliability / Validation)

### P1. 2계층 검증 (Boundary + Domain)
- **패턴**: 경계 검증(Pydantic: 타입·필수 존재) → 도메인 검증(Service: 불변식·소유권) → 표준 오류.
- **구현**:
  - Pydantic `MenuInput`(name:str, price:int, category_id:int 필수) — 형식 강제.
  - `MenuService._validate_input` — `price>0`, `name` trim·비공백·≤100.
  - `MenuService._require_category` — 카테고리 존재 + `store_id` 일치.
  - `MenuService._require_owned_menu` — 메뉴 존재 + 매장 소속(없으면 `NOT_FOUND`).
- **오류 형상**: `AppError(VALIDATION_ERROR, "...", {"fields": {...}})` → HTTP 422, 구조화 바디.
- **대응**: U3-NFR-R1·R2, U3-NFR-U4.
- **코드**: `backend/app/services/menu_service.py`, `backend/app/schemas/menu.py`.

---

## 2. 일관성 패턴 (Consistency / Transaction)

### P2. Service-owns-transaction
- **패턴**: Repository는 `add`/`flush`만 수행, **Service가 `commit`/트랜잭션 경계 소유**.
- **구현**: `SqlMenuRepo`는 flush-only; `MenuService.{create,update,delete,reorder}_menu`가 `db.commit()` 호출. 생성/수정 후 `db.refresh`로 최신 투영.
- **원자성**: `reorder_menus` → `update_order`(카테고리 내 `display_order` 위치값 재기록)가 **단일 커밋**으로 완결(부분 적용 방지).
- **대응**: U3-NFR-R3.
- **코드**: `menu_service.py`, `repositories/menu.py`.

---

## 3. 성능 패턴 (Performance)

### P3. 인덱스 기반 단일 정렬 쿼리 (No N+1)
- **패턴**: 목록은 **1쿼리**로 조회·정렬. 카테고리 조인 후 `(category.display_order, menu.display_order, menu.id)` 정렬.
- **구현**: `SqlMenuRepo.list_by_store` — `join(Category).filter(store_id).order_by(...)`. 인덱스: `menu.store_id`·`menu.category_id`·`category.store_id`(모델 정의 기존).
- **대응**: U3-NFR-P1·P3·P4.

### P4. 프론트 병렬 로드 + 메모이즈 필터
- **패턴**: 카테고리·메뉴 **`Promise.all` 병렬 fetch**, 카테고리 필터는 `useMemo`로 재계산 최소화.
- **구현**: `MenuBrowseView`(고객), `MenuManageView`(관리자, `grouped` 메모이즈).
- **대응**: U3-NFR-P2.
- **코드**: `frontend/src/features/customer/menu/MenuBrowseView.tsx`, `.../admin/menu-manage/MenuManageView.tsx`.

---

## 4. 신선도/캐싱 패턴 (Freshness)

### P5. No-cache / fetch-on-enter + mutation 후 재조회
- **패턴**: 서버 캐시 없음. 화면 진입 시 조회, 관리자 mutation(생성/수정/삭제/순서) 후 `load()` **재조회**로 즉시 최신화. 고객은 재진입/새로고침 시 반영.
- **정당화**: 소량·단일 매장 → 캐시 무효화 복잡도 회피. 메뉴 실시간 push는 U3 범위 밖(SSE=U5 주문 전용).
- **대응**: U3-NFR-P4, US-A-17.

---

## 5. 보안 패턴 (Security)

### P6. 엔드포인트 게이트 (공개 읽기 / 보호 쓰기)
- **패턴**: 읽기(`GET /api/menus`·`/api/categories`)는 무인증. 쓰기(`/api/admin/menus*`·`menu-order`)는 `Depends(get_current_admin)`로 게이트.
- **대응**: U3-NFR-S1·S2.

### P7. 매장 스코프 격리 (Tenant-scoped authorization)
- **패턴**: 관리자 작업은 `actor.store_id` 기준으로만 카테고리/메뉴를 조회·검증 → 타 매장 리소스 접근 차단(`VALIDATION_ERROR`/`NOT_FOUND`).
- **대응**: U3-NFR-S3.

### P8. 최소 노출 응답
- **패턴**: `MenuView`/`CategoryView`는 표시용 필드만 — 내부 감사 필드·원가 미노출.
- **대응**: U3-NFR-S4·S5.
- **코드**: `routers/menu.py`, `schemas/menu.py`, `menu_service.py`.

---

## 6. 사용성 패턴 (Usability)

### P9. 터치 프라이머리티브 + 폴백
- **패턴**: 모든 상호작용은 공유 `Button`(min 44×44px). 이미지 누락/실패 시 플레이스홀더, 품절 오버레이(`is_available=false`), 가격 `ko-KR` 로캘 표기.
- **대응**: U3-NFR-U1·U2·U3·U5.
- **코드**: `shared/ui/Button.tsx`, `MenuBrowseView.tsx`, `menu-api.ts`(`formatPrice`).

---

## 7. 회복성/오류 패턴 (Resilience) — 제한적

### P10. 우아한 실패 (Graceful degradation)
- **패턴**: 서버는 구조화 에러 반환, 프론트는 로딩/에러/빈 상태를 분기 렌더(크래시 없음). 빈 매장은 `[]` 반환.
- **대응**: U3-NFR-A1·A2, R5.

---

## 8. 미적용 패턴 (Explicitly Not Applied — 정당화)

| 패턴 | 적용? | 정당화 |
|---|:--:|---|
| 캐시(메모리/Redis) | ❌ | 소량·단일 매장, 무효화 복잡도 > 이득 (D1) |
| 페이지네이션/무한스크롤 | ❌ | 메뉴 ~20건, 전량 반환으로 충분 (D2) |
| 재시도/지수 백오프 | ❌ | 로컬 단일 프로세스, Resiliency Baseline=No |
| 서킷 브레이커 | ❌ | 외부 의존(다운스트림) 없음 |
| 메시지 큐 | ❌ | 비동기 파이프라인 없음(동기 CRUD) |
| 레이트리밋/WAF | ❌ | Security Baseline=No, 로컬 MVP |
| 낙관적 락(version) | ❌ | 단일 관리자, last-write-wins 허용 (D5) |
| 실시간 push(SSE) — 메뉴 | ❌ | 메뉴는 실시간 대상 아님(주문만, U5) |
| 메트릭/트레이싱/APM | ❌ | MVP, 기본 로깅 + 구조화 에러로 대체 (D6) |

---

## 9. 패턴 → NFR 추적

| 패턴 | 대응 NFR |
|---|---|
| P1 | R1, R2, U4 |
| P2 | R3 |
| P3 | P1, P3, P4 |
| P4 | P2 |
| P5 | P4, (US-A-17) |
| P6 | S1, S2 |
| P7 | S3 |
| P8 | S4, S5 |
| P9 | U1, U2, U3, U5 |
| P10 | A1, A2, R5 |
