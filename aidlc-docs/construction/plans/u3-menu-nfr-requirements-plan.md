# U3 Menu — NFR Requirements Plan (Part 1: Planning)

**단계**: CONSTRUCTION — **Phase 1 (스트림 B)** [U3 Menu] — NFR Requirements
**유닛**: U3 Menu (메뉴 조회·CRUD·노출 순서·검증)
**책임(기능)**: 고객 메뉴 탐색(카테고리 탭·카드·이미지·44×44px), 관리자 메뉴 등록/수정/삭제/순서, 가격·필수 필드 검증.
**입력**: `inception/requirements/requirements.md §5`(NFR-1~7), `inception/application-design/{application-design,component-methods,services}.md`, U3 구현물(`backend/app/{routers/menu.py,services/menu_service.py,repositories/{menu,category}.py}`, `frontend/src/features/{customer/menu,admin/menu-manage,menu}`), `aidlc-state.md`(Extension: Security=No, Resiliency=No, PBT=Full).

> **U3 특성**: 읽기 중심(고객)·CRUD(관리자)의 **상태 없는 데이터 유닛**. 실시간·SSE는 범위 밖(U5). NFR 초점은 **조회 성능·입력 검증(불변식)·보호 엔드포인트 인증·사용성(터치)·PBT**. 기술 스택은 Inception/U1에서 확정되어 U3는 **확정 스택의 재사용 + U3 국소 결정**만 기록.

---

## 배경: 이미 확정된 사항 (변경 대상 아님)

- **글로벌 NFR**(`requirements.md §5`): NFR-1 성능(SSE 2s — U5 소관), NFR-2 보안(bcrypt·JWT·시도제한 — U2 소관, U3는 보호 엔드포인트 소비), NFR-4 사용성(44×44px 터치, 카드), NFR-6 테스트(PBT 전면), NFR-7 이식성(로컬·Docker 불요).
- **확정 스택**: FastAPI + SQLAlchemy + SQLite(백엔드), React + Vite + TypeScript(프론트), Pydantic(계약), Hypothesis/fast-check(PBT), `ApiClient`(REST 래퍼·구조화 에러 파싱).
- **규모**: 매장 1개, 테이블 10~20, 메뉴 ~20건·카테고리 4개(시드). 로컬 단일 프로세스.
- **확장 미적용**: Security Baseline=No, Resiliency Baseline=No(학습/데모 MVP). → 서킷브레이커·레이트리밋·WAF·DR 등 **미도입**(정당화: 로컬 MVP).
- **계약 동결**: `schemas/menu.py`(MenuView/MenuInput/CategoryView/MenuOrderInput), `MenuRepo`/`CategoryRepo` Protocol, `AuthDependency`(`get_current_admin`).

---

## 결정이 필요한 질문 (Questions)

> 프로젝트 관례(전 단계 "전부 권장")와 확정 제약에 따라 각 `[Answer]:`에 **권장안**을 미리 기입했습니다. 변경을 원하면 해당 태그를 수정하세요.

### Q1. 메뉴 조회 성능 목표 (Performance)
고객 메뉴 화면(카테고리+메뉴)의 응답/렌더 목표?
- **A (권장)**: 로컬·메뉴 ~20건 전제 → `GET /api/menus`·`GET /api/categories` **p95 < 300ms(로컬)**, 초기 화면 상호작용 가능 **< 1s**. 데이터가 작아 **페이지네이션 불필요**(전량 반환).
- B: 페이지네이션/무한스크롤 도입.

[Answer]: A (권장) — p95<300ms(로컬)·초기 <1s, 전량 반환(페이지네이션 없음).

### Q2. 메뉴 데이터 신선도/캐싱 (Performance / Consistency)
관리자 변경(US-A-17 "고객 화면에도 적용")이 고객에게 반영되는 방식?
- **A (권장)**: **서버측 캐시 없음**. 고객 클라이언트는 **화면 진입 시 1회 fetch**(카테고리·메뉴 병렬). 관리자 변경은 고객이 **화면 재진입/새로고침 시** 반영. 메뉴는 **실시간 push 대상 아님**(SSE는 U5 주문 전용).
- B: 메뉴 실시간 push(SSE 확장) 도입.

[Answer]: A (권장) — 캐시 없음·진입 시 조회, 재진입/새로고침으로 최신 반영(실시간 push 미도입).

### Q3. 공개 읽기 엔드포인트 인증·노출 (Security)
`GET /api/menus`·`/api/categories`의 접근 통제?
- **A (권장)**: 읽기 2종은 **공개(무인증)** — 태블릿/고객이 로그인 없이 조회. 관리자 CRUD·순서(`/api/admin/menus*`, `menu-order`)는 **`AuthDependency`(JWT) 필수**. 응답은 표시용 필드만 노출(원가·내부 플래그 없음). **레이트리밋 미적용**(로컬 MVP; 로그인 시도 제한은 U2).
- B: 읽기도 세션 토큰 요구.

[Answer]: A (권장) — 읽기 공개·쓰기 JWT 보호, 레이트리밋 미적용.

### Q4. 입력 검증 강도 & PBT 범위 (Reliability / Testability)
메뉴 입력 검증의 권위(authority)와 PBT 대상?
- **A (권장)**: **서버 권위 검증** — Pydantic(형식/타입) + Service 도메인 불변식(`price>0`, `name` 필수·trim·≤100자, `category`는 동일 매장 소속). 프론트는 **UX 보조 검증**(서버가 최종). **PBT(Hypothesis)**: ①price>0 거부, ②필수(공백) name 거부, ③유효 입력 생성 라운드트립. (`US-A-16` 불변식)
- B: 프론트 검증만/서버 최소.

[Answer]: A (권장) — 서버 권위 이중검증 + Hypothesis PBT 3속성.

### Q5. 이미지 URL 처리 (Usability / Security)
메뉴 이미지의 저장·표시·검증?
- **A (권장)**: **외부 URL 참조만**(업로드/리사이징 없음 — 요구사항 제외범위). 프론트는 **누락/로드 실패 시 플레이스홀더**("이미지 없음"). URL은 **선택 필드**(빈값 허용), 형식 검증은 관대. SSRF/콘텐츠 검사 등 **미대응**(표시 전용·MVP).
- B: URL 화이트리스트/프록시 도입.

[Answer]: A (권장) — 외부 URL 참조·플레이스홀더 폴백·관대한 검증(SSRF 미대응).

### Q6. 순서변경/동시편집 일관성 (Reliability)
`reorder_menus`와 동시 편집 처리?
- **A (권장)**: **단일 관리자 가정 → last-write-wins**. `reorder`는 **단일 트랜잭션**으로 카테고리 내 `display_order`를 위치값으로 재기록. 낙관/비관 락·버전 컬럼 **미도입**.
- B: 낙관적 락(version) 도입.

[Answer]: A (권장) — last-write-wins·단일 트랜잭션 reorder, 락 미도입.

### Q7. 유지보수·관측성 (Maintainability / Observability)
U3의 코드 품질·운영 관측 수준?
- **A (권장)**: 3계층(Router→Service→Repo) + 구조화 에러 바디 **재사용**. 전용 메트릭/트레이싱/APM **미도입**(MVP), 기본 로깅만. 테스트는 PBT + 예제(단위·TestClient 통합)로 회귀 방어.
- B: 메트릭/트레이싱 스택 도입.

[Answer]: A (권장) — 3계층·구조화 에러 재사용, 전용 관측 스택 미도입, PBT+예제 테스트.

---

## 계획 실행 체크리스트 (Part 2 = NFR Requirements 산출물 생성)

- [x] `construction/u3-menu/nfr-requirements/nfr-requirements.md` — U3 NFR 항목(성능·확장·가용·보안·신뢰·유지보수·사용성·테스트) ID·목표·측정·수용 기준·추적
- [x] `construction/u3-menu/nfr-requirements/tech-stack-decisions.md` — 확정 스택의 U3 재사용 + U3 국소 결정(캐시/페이지네이션/검증/이미지) 및 근거

---

## 승인 요청

Q1~Q7 권장안으로 산출물을 생성했습니다. 변경을 원하면 해당 `[Answer]:`를 수정 요청해 주세요. 다음 단계는 **NFR Design**입니다.
