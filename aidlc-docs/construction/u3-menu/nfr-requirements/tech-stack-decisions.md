# U3 Menu — 기술 스택 결정 (Tech Stack Decisions)

**단계**: CONSTRUCTION — Phase 1 (스트림 B) [U3 Menu] — NFR Requirements
**유닛**: U3 Menu

> 기술 스택은 **Inception(requirements.md §2) / U1(Phase 0)** 에서 전역 확정되었습니다. 본 문서는 U3가 **재사용하는 확정 스택**과 **U3 국소 결정**(캐시·페이지네이션·검증·이미지·라이브러리)을 근거와 함께 기록합니다. U3는 신규 상위 의존성을 추가하지 않습니다.

---

## 1. 확정 스택 재사용 (Inherited — 변경 없음)

| 영역 | 기술 | U3에서의 사용 | 출처 |
|---|---|---|---|
| 백엔드 프레임워크 | **FastAPI** | `routers/menu.py`(엔드포인트·의존성 주입) | requirements §2 |
| ORM | **SQLAlchemy 2.0** | `SqlMenuRepo`/`SqlCategoryRepo` 쿼리 | 앱설계 Q2 |
| DB | **SQLite(파일)** | 메뉴/카테고리 영속 | requirements §2 |
| 계약/검증 | **Pydantic v2** | `MenuInput`/`MenuView`/`CategoryView`/`MenuOrderInput`(동결) | schemas |
| 인증 의존성 | **`AuthDependency`(JWT)** | 관리자 엔드포인트 보호(`get_current_admin`) | U2 소유·U3 소비 |
| 에러 규약 | **구조화 에러 바디 + `AppError`/`ErrorCode`** | 검증·NOT_FOUND 응답 | U1 |
| 프론트 | **React + Vite + TypeScript** | `MenuBrowseView`·`MenuManageView` | requirements §2 |
| REST 클라이언트 | **`ApiClient`(fetch 래퍼)** | `menu-api.ts`(엔드포인트·Bearer·에러 파싱) | U1 |
| 라우팅 | **react-router + 라우트 레지스트리** | `features/*/routes.tsx`(자동 수집) | U1 |
| PBT | **Hypothesis(Py)** / fast-check(TS) | 백엔드 검증 불변식 PBT | requirements §2, NFR-6 |

---

## 2. U3 국소 결정 (New / Scoped)

### D1. 서버측 캐시 — **미도입**
- **결정**: 메뉴/카테고리 조회에 캐시 레이어(메모리/Redis) 없음. 요청 시 DB 조회.
- **근거**: 단일 매장·메뉴 ~20건·로컬 → 캐시 이득 미미, 무효화 복잡도만 증가. (Q2=A)
- **향후 지점**: 다매장/대량 시 읽기 캐시 + mutation 시 무효화.

### D2. 페이지네이션/무한스크롤 — **미도입**
- **결정**: `GET /api/menus`는 매장 전체 메뉴를 **전량 반환**, 프론트가 카테고리로 필터.
- **근거**: 데이터 소량(U3-NFR-P4). `PageParams`(공통 스키마)는 존재하나 U3 미사용.
- **향후 지점**: 메뉴 급증 시 커서 페이지네이션.

### D3. 검증 라이브러리 — **Pydantic + 서비스 도메인 검증**(추가 라이브러리 없음)
- **결정**: 형식·타입은 Pydantic, 도메인 불변식(`price>0`·`name`·`category` 소속)은 `MenuService`. 별도 검증 프레임워크 미도입.
- **근거**: 이중 계층으로 충분(U3-NFR-R1·R2), 의존성 최소화.

### D4. 이미지 — **외부 URL 참조 + 프론트 플레이스홀더**
- **결정**: 업로드/스토리지/리사이징 없음. `image_url`은 선택 필드. 프론트가 누락/실패 시 "이미지 없음" 폴백.
- **근거**: 요구사항 제외범위(업로드/최적화). SSRF 표면 없음(서버 fetch 안 함). (Q5=A)

### D5. 순서 일관성 — **last-write-wins**(락 라이브러리 없음)
- **결정**: `reorder`는 단일 트랜잭션 재기록, 버전/락 컬럼 없음.
- **근거**: 단일 관리자 가정, MVP. (Q6=A)

### D6. 관측성 스택 — **미도입**
- **결정**: 메트릭(Prometheus)·트레이싱(OTel)·APM 없음. 기본 로깅 + 구조화 에러.
- **근거**: 로컬 MVP, Resiliency Baseline=No. (Q7=A)

### D7. 프론트 상태/데이터 패칭 — **로컬 컴포넌트 상태 + `ApiClient`**(추가 라이브러리 없음)
- **결정**: React Query/SWR 등 미도입. `useState`/`useEffect` + `menu-api.ts`, 필터는 `useMemo`. mutation 후 `load()` 재조회.
- **근거**: 화면 2개·소량 데이터, 앱설계 Q4(Context+hooks) 일관. 신규 상태 라이브러리 불필요.

---

## 3. 신규 의존성 요약

| 의존성 | 추가 여부 | 비고 |
|---|:--:|---|
| 백엔드 상위 패키지 | **없음** | 기존 `requirements.txt` 범위 내(fastapi/sqlalchemy/pydantic/hypothesis) |
| 프론트 상위 패키지 | **없음** | 기존 `package.json` 범위 내(react/react-router/fast-check) |

> U3는 **의존성 추가 0**. 확정 스택과 표준 라이브러리만으로 구현.

---

## 4. NFR 정렬 확인

| 결정 | 정렬되는 U3-NFR |
|---|---|
| D1·D2 (캐시/페이지네이션 미도입) | U3-NFR-P1~P4, SC1~SC2 |
| D3 (Pydantic+서비스 검증) | U3-NFR-R1·R2, T1~T3 |
| D4 (외부 URL·폴백) | U3-NFR-U3, S5 |
| D5 (last-write-wins) | U3-NFR-R3 |
| D6 (관측성 미도입) | U3-NFR-M3, NFR-7 |
| D7 (로컬 상태·ApiClient) | U3-NFR-P2, M1 |
