# U3 Menu — 배포 아키텍처 (Deployment Architecture)

**단계**: CONSTRUCTION — Phase 1 (스트림 B) [U3 Menu] — Infrastructure Design
**유닛**: U3 Menu
**입력**: `infrastructure-design.md`, U1 부팅/런타임(`app/main.py`·`app/db.py`·`seed.py`), CLAUDE.md 실행 명령

> U3의 **배포 토폴로지·실행 절차·데이터 수명주기**를 기술합니다. U3는 별도 배포 단위가 아니라 **U1 모놀리스 배포에 포함**되어 함께 기동됩니다.

---

## 1. 배포 토폴로지 (로컬 단일 노드)

```
+-----------------------------------------------------------+
|                 개발자 / 매장 로컬 머신 (1 노드)            |
|                                                           |
|  +---------------------+        +---------------------+   |
|  |  브라우저 (고객)     |        |  브라우저 (관리자)   |   |
|  |  /customer/menu     |        |  /admin/menu-manage |   |
|  +----------+----------+        +----------+----------+   |
|             |                              |              |
|             |  HTTP (localhost:5173)       |              |
|             v                              v              |
|  +-----------------------------------------------------+  |
|  |        Frontend : Vite (dev :5173 / build dist)     |  |
|  |  MenuBrowseView · MenuManageView · menu-api         |  |
|  +--------------------------+--------------------------+  |
|                             |                             |
|                 /api  -->  proxy to :8000                 |
|                             v                             |
|  +-----------------------------------------------------+  |
|  |     Backend : uvicorn FastAPI (single, :8000)       |  |
|  |  MenuRouter -> MenuService -> SqlMenuRepo /          |  |
|  |                               SqlCategoryRepo        |  |
|  |  (auth gate: get_current_admin  [U2])               |  |
|  +--------------------------+--------------------------+  |
|                             |                             |
|                             v                             |
|  +-----------------------------------------------------+  |
|  |            Storage : SQLite file (app.db)           |  |
|  |     create_all() schema  +  seed.py (idempotent)    |  |
|  +-----------------------------------------------------+  |
|                                                           |
+-----------------------------------------------------------+
                             |
                             |  image_url (표시 전용, 서버 fetch 안 함)
                             v
                   +-------------------+
                   |  외부 이미지 호스팅 |
                   +-------------------+
```

- 단일 노드, 두 프로세스(vite, uvicorn) + 파일 DB. 외부 연동은 **브라우저가 렌더하는 이미지 URL** 뿐(서버 프록시 없음, SSRF 표면 없음 — U3-NFR-S5).

---

## 2. 실행 / 기동 절차

| 순서 | 구성요소 | 명령 | 확인 |
|---|---|---|---|
| 1 | Backend 의존성 | `pip install -r requirements.txt`(venv) | 설치 완료 |
| 2 | 환경변수 | `cp .env.example .env`(JWT_SECRET 등, `.env` 미커밋) | 값 설정 |
| 3 | 스키마 + 시드 | `python -m app.seed`(멱등) | store/admin/menus/tables |
| 4 | Backend 기동 | `uvicorn app.main:app --reload`(:8000) | `GET /api/health` → `{"status":"ok"}` |
| 5 | Frontend | `npm install` → `npm run dev`(:5173) | `/customer/menu`·`/admin/menu-manage` |
| 6 | (선택) 프로덕션 빌드 | `npm run build` → 정적 `dist` 서빙 | 정적 자산 |

> 3~5는 U1 부팅 절차이며 U3는 별도 기동 단계가 없다(라우터·뷰가 기존 앱에 포함).

---

## 3. 포트 / 경로 매핑

| 항목 | 값 |
|---|---|
| Frontend (dev) | `http://localhost:5173` |
| Backend (uvicorn) | `http://localhost:8000` |
| API 프록시 | `/api` → `:8000` (vite proxy) |
| 공개 엔드포인트 | `GET /api/menus`, `GET /api/categories` |
| 보호 엔드포인트 | `POST/PUT/DELETE /api/admin/menus[/{id}]`, `PATCH /api/admin/categories/{id}/menu-order` |
| 헬스체크 | `GET /api/health` (U1) |
| DB 파일 | 백엔드 작업 디렉터리의 SQLite 파일(U1 설정) |

---

## 4. 데이터 수명주기 (Data Lifecycle)

| 단계 | 동작 | 소유 |
|---|---|---|
| 스키마 생성 | `create_all()`(앱 부팅) | U1 |
| 초기 데이터 | `seed.py` 멱등 시드(카테고리·메뉴 예시) | U1 |
| 생성/수정/삭제 | `MenuService` 트랜잭션(단일 커밋), 물리 삭제 허용 | U3 |
| 순서 변경 | `reorder` 단일 트랜잭션 재기록(last-write-wins) | U3 |
| 삭제 후 무결성 | 과거 주문은 OrderItem **스냅샷**으로 보존(U3는 스냅샷 생성 안 함) | U4/U5 규약 |
| 백업 | 파일 복사(수동) — 자동 백업 파이프라인 미도입 | 운영(향후) |

---

## 5. 배포 특성 요약

| 특성 | 값 | 근거 |
|---|---|---|
| 배포 단위 | U1 모놀리스에 포함(독립 배포 없음) | 단일 앱 |
| 노드 수 | 1 | 로컬 MVP |
| 상태 | SQLite 파일에 집중, 앱 프로세스는 무상태(메뉴 캐시 없음) | 패턴 P5 |
| 확장 | 수직 확장(단일 워커) — 오토스케일 없음 | U3-NFR-SC1 |
| 롤백 | 코드 재배포 + DB 파일 복원(수동) | MVP |
| 무중단 배포 | 미대상(개발/단일 매장) | MVP |

> 컨테이너화·다중 노드·무중단 배포는 `infrastructure-design.md §3~§4`의 향후 지점으로 문서화되어 있으며 U3 범위 밖이다.
