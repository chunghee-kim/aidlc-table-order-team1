# U3 Menu — 논리 컴포넌트 (Logical Components)

**단계**: CONSTRUCTION — Phase 1 (스트림 B) [U3 Menu] — NFR Design
**유닛**: U3 Menu
**입력**: `nfr-design-patterns.md`, U3 구현물

> U3의 논리 컴포넌트(책임·상호작용)를 정의합니다. U3는 **상태 없는 CRUD 유닛**으로, 큐·캐시·서킷브레이커 등 **인프라 컴포넌트를 두지 않습니다**(§4 정당화).

---

## 1. 컴포넌트 목록

### 백엔드
| 컴포넌트 | 유형 | 책임 | 파일 |
|---|---|---|---|
| **MenuRouter** | Router | 엔드포인트 노출·요청 매핑·인증 게이트·응답 모델 | `backend/app/routers/menu.py` |
| **MenuService** | Service | 도메인 검증(불변식)·매장 스코프·트랜잭션 소유·투영 | `backend/app/services/menu_service.py` |
| **SqlMenuRepo** | Repository | 메뉴 영속(정렬 조회·생성·수정·삭제·순서) — flush-only | `backend/app/repositories/menu.py` |
| **SqlCategoryRepo** | Repository | 카테고리 조회(정렬)·단건 조회 | `backend/app/repositories/category.py` |

### 프론트엔드
| 컴포넌트 | 유형 | 책임 | 파일 |
|---|---|---|---|
| **menu-api** | API 모듈 | 엔드포인트 래핑(공개/보호)·타입·가격 포맷 | `frontend/src/features/menu/menu-api.ts` |
| **MenuBrowseView** | View(고객) | 카테고리 탭·카드·이미지 폴백·품절 표시 | `.../features/customer/menu/MenuBrowseView.tsx` |
| **MenuManageView** | View(관리자) | 등록/수정/삭제·순서(↑↓)·검증 피드백 | `.../features/admin/menu-manage/MenuManageView.tsx` |
| **routes(customer/admin)** | Route | 레지스트리 등록(`/customer/menu`, `/admin/menu-manage`) | `.../menu/routes.tsx`, `.../menu-manage/routes.tsx` |

### 소비(외부 소유) 컴포넌트
| 컴포넌트 | 소유 | U3 사용 |
|---|---|---|
| AuthDependency(`get_current_admin`) | U2 | 관리자 엔드포인트 보호 |
| ApiClient / Button / ErrorHandler / DbSession | U1 | REST·터치 버튼·에러·세션 |
| Menu / Category 모델 | U1 | 영속 대상(참조) |

---

## 2. 상호작용 — 고객 읽기 흐름 (공개)

```
+------------------+     GET /api/menus       +------------------+
|  MenuBrowseView  | -----------------------> |    MenuRouter    |
|   (customer)     |     GET /api/categories  |   (public gate)  |
+------------------+                          +------------------+
         ^                                             |
         |                                             v
         |                                    +------------------+
         |                                    |   MenuService    |
         |                                    | list_menus /     |
         |                                    | list_categories  |
         |                                    +------------------+
         |                                             |
         |                                             v
         |                                    +------------------+
         |                                    | SqlMenuRepo /    |
         |                                    | SqlCategoryRepo  |
         |                                    | (single query)   |
         |                                    +------------------+
         |                                             |
         |         MenuView[] / CategoryView[]         v
         +------------------------------------- (SQLite / SQLAlchemy)
```

- 무인증. 단일 정렬 쿼리(N+1 없음, P3). 프론트 병렬 fetch + useMemo 필터(P4).

---

## 3. 상호작용 — 관리자 쓰기 흐름 (보호)

```
+------------------+  POST/PUT/DELETE menus   +------------------+
|  MenuManageView  | -----------------------> |    MenuRouter    |
|    (admin)       |  PATCH menu-order        | get_current_admin|
+------------------+                          +------------------+
         |                                             |
         | Bearer token (ApiClient)                    | AdminContext
         |                                             v
         |                                    +------------------+
         |                                    |   MenuService    |
         |                                    | validate ->      |
         |                                    | scope-check ->   |
         |                                    | mutate -> commit |
         |                                    +------------------+
         |                                       |           |
         |                                       v           v
         |                              +-----------+  +-----------+
         |                              | SqlMenu   |  | SqlCateg. |
         |                              | Repo(flush)| | Repo(get) |
         |                              +-----------+  +-----------+
         |                                       |
         |   201/200/204 or 422/404 (structured) |
         +---------------------------------------+
                     |
                     v  on success
              load() re-fetch  (P5: no cache, refresh view)
```

- 인증 게이트(P6) + 매장 스코프 격리(P7). 검증 실패 → 422 구조화 오류(P1). 성공 후 재조회로 최신화(P5).

---

## 4. 인프라 컴포넌트 — 미사용 (Justification)

| 인프라 | 사용? | 사유 |
|---|:--:|---|
| 캐시(Redis/메모리) | ❌ | 소량·단일 매장 — 진입 시 조회로 충분(P5) |
| 메시지 큐 | ❌ | 동기 CRUD, 비동기 파이프라인 없음 |
| 서킷 브레이커 | ❌ | 다운스트림 외부 의존 없음 |
| API 게이트웨이 | ❌ | 로컬 단일 앱(FastAPI 라우터로 충분) |
| 로드밸런서/오토스케일 | ❌ | 단일 프로세스·고정 규모 |
| 메트릭/트레이싱 수집기 | ❌ | MVP — 기본 로깅 + 구조화 에러 |

> **원칙**: U3는 상태 없는 CRUD. 인프라 컴포넌트 부재가 규모·확장 설정(Security/Resiliency Baseline=No)에 부합하는 **의도된 설계**이다.

---

## 5. 데이터 계약 (참조 — 동결)

| 계약 | 필드 |
|---|---|
| `MenuView` | id, name, price, description?, image_url?, category_id, display_order, is_available |
| `CategoryView` | id, name, display_order |
| `MenuInput` | name, price, description?, category_id, image_url? |
| `MenuOrderInput` | ordered_menu_ids: int[] |

> 계약은 Phase 0에서 동결(`schemas/menu.py`). U3는 소비만 하며 시그니처를 변경하지 않는다.

---

## 6. NFR → 컴포넌트 매핑

| NFR | 담당 컴포넌트 |
|---|---|
| U3-NFR-P1·P3 (조회 성능·단일 쿼리) | SqlMenuRepo·SqlCategoryRepo |
| U3-NFR-P2·P4 (렌더·병렬) | MenuBrowseView·MenuManageView·menu-api |
| U3-NFR-R1~R3 (검증·트랜잭션) | MenuService |
| U3-NFR-S1~S4 (인증·스코프·노출) | MenuRouter·MenuService |
| U3-NFR-U1~U5 (터치·카드·폴백) | MenuBrowseView·MenuManageView·Button |
| U3-NFR-T1~T5 (PBT·통합) | tests(menu_service·menu_api) |
