# U3 Menu — NFR Design Plan (Part 1: Planning)

**단계**: CONSTRUCTION — **Phase 1 (스트림 B)** [U3 Menu] — NFR Design
**유닛**: U3 Menu
**입력**: `construction/u3-menu/nfr-requirements/{nfr-requirements,tech-stack-decisions}.md`, U3 구현물, `application-design.md`(3계층·에러 규약)
**목적**: U3 NFR 요구사항을 **설계 패턴 + 논리 컴포넌트**로 반영한다.

> **U3 특성**: 상태 없는 읽기/CRUD 유닛 → 회복성·확장성 인프라 컴포넌트(큐·캐시·서킷브레이커)는 **부재가 정답**. 설계 초점은 **검증 계층·트랜잭션 경계·쿼리 효율·인증 게이트·프론트 폴백** 패턴.

---

## 결정이 필요한 질문 (Questions)

> 관례("전부 권장")·확정 제약에 따라 각 `[Answer]:`에 권장안을 미리 기입했습니다.

### Q1. 검증 계층 배치 패턴 (Reliability / Validation)
- **A (권장)**: **2계층 검증** — Pydantic(경계·형식) → Service 도메인 검증(불변식·소유권). Repo는 영속만. 오류는 `AppError(VALIDATION_ERROR, details.fields)`로 표준화.
- B: Router에 검증 집중.

[Answer]: A (권장)

### Q2. 트랜잭션 경계 패턴 (Consistency)
- **A (권장)**: **Service-owns-transaction** — Repo는 add/flush만, Service가 `commit`. `reorder`·`create`·`update`·`delete` 각각 단일 트랜잭션.
- B: Repo가 commit.

[Answer]: A (권장)

### Q3. 성능 패턴 (Performance)
- **A (권장)**: **인덱스 활용 + 단일 정렬 쿼리**(store_id·category_id 인덱스, 카테고리 조인해 display_order 정렬) → N+1 없음. 프론트는 **병렬 fetch**(카테고리·메뉴 동시) + `useMemo` 필터.
- B: 카테고리별 개별 조회.

[Answer]: A (권장)

### Q4. 캐싱/무효화 패턴 (Performance / Freshness)
- **A (권장)**: **캐시 없음 / 진입 시 조회**. 관리자 mutation 후 프론트 `load()` 재조회로 최신화. 고객은 재진입/새로고침 시 최신.
- B: 클라이언트 캐시 + TTL.

[Answer]: A (권장)

### Q5. 보안 패턴 (Security)
- **A (권장)**: **엔드포인트 게이트**(공개 읽기 / `AuthDependency` 쓰기) + **매장 스코프 격리**(`actor.store_id`로 카테고리·메뉴 검증) + **최소 노출 응답**(`MenuView`).
- B: 행 수준 보안(RLS)/정책엔진.

[Answer]: A (권장)

### Q6. 논리 컴포넌트 & 인프라 (Logical Components)
- **A (권장)**: 논리 컴포넌트 = MenuRouter·MenuService·SqlMenuRepo·SqlCategoryRepo·(프론트)menu-api·MenuBrowseView·MenuManageView. **인프라 컴포넌트(큐·캐시·서킷브레이커·게이트웨이) 미도입**(로컬 MVP·상태없음).
- B: 캐시/큐 도입.

[Answer]: A (권장)

### Q7. 회복성/오류 패턴 (Resilience) — Baseline=No
- **A (권장)**: **우아한 실패만** — 서버 구조화 에러, 프론트 에러/빈 상태 렌더, 이미지 폴백. 재시도·서킷브레이커·백오프 **미도입**(정당화: 로컬 단일 프로세스, Resiliency Baseline=No).
- B: 재시도/서킷브레이커 도입.

[Answer]: A (권장)

---

## 계획 실행 체크리스트 (Part 2 = NFR Design 산출물 생성)

- [x] `construction/u3-menu/nfr-design/nfr-design-patterns.md` — 카테고리별 적용 패턴 + 코드 매핑 + 미적용 패턴 정당화
- [x] `construction/u3-menu/nfr-design/logical-components.md` — 논리 컴포넌트 목록·책임·상호작용(ASCII) + 미사용 인프라 명시

---

## 승인 요청

Q1~Q7 권장안으로 NFR Design 산출물을 생성했습니다. 변경을 원하면 `[Answer]:` 수정을 요청해 주세요.
