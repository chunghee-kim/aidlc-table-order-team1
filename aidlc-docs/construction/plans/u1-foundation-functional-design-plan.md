# U1 Foundation & Data — Functional Design Plan (Part 1: Planning)

**단계**: CONSTRUCTION — **Phase 0 (공통 기반, 1인 선행)** [U1] — Functional Design
**유닛**: U1 Foundation & Data
**책임**: 프로젝트 스캐폴딩, **전체 SQLite 스키마(9개 모델)**, 시드 스크립트, 백엔드 공통 인프라(DbSession, ErrorHandler, AppBootstrap, Health), ApiClient 스켈레톤.
**병렬 실행 추가 책임(Phase 0)**: 5인 병렬 착수를 위해 **전 교차 계약을 스텁으로 동결**한다 — `AuthDependency`, `TableSessionService` 프로토콜, `OrderEventBroker`, 리포 인터페이스(특히 `MenuRepo`), 전 엔드포인트 `schemas/`(Pydantic), 프론트 `AuthContext`·`TableSessionContext`·`CartContext`·`SseClient` 인터페이스. 공유 서비스는 분리 패키지(`services/order/`, `services/table_session/`)의 `__init__.py` 파사드로 동결. 근거: `inception/application-design/parallel-execution.md §3`.
**입력**: `unit-of-work.md`, `unit-of-work-story-map.md`(SD-1~3), `application-design.md §2`(데이터 모델), `component-methods.md`.

> **U1 특성**: 비즈니스 로직이 거의 없는 **기반 유닛**입니다. Functional Design은 주로 **도메인 엔티티 상세(타입·제약·인덱스·관계)**, **시드 데이터 규칙**, **기반 기술 결정**에 집중합니다. UI 화면 없음(앱 셸 라우팅 스켈레톤만) → `frontend-components.md`는 생성하지 않습니다.

---

## 배경: 이미 확정된 사항

- **데이터 모델 9종**: Store, AdminUser, Table, TableSession, Category, Menu, Order, OrderItem, OrderHistory (application-design.md §2.2 초안 스키마).
- **ORM**: SQLAlchemy. **DB**: SQLite 단일 파일.
- **시드**: 매장 1 + 관리자(bcrypt) + 카테고리/메뉴(외부 이미지 URL) + 테이블 10~20개.
- **에러 규약**: 구조화 에러 바디 `{error:{code,message,details}}` + HTTP 상태코드.

---

## 결정이 필요한 질문 (Questions)

> 각 `[Answer]:` 태그에 답을 채워 주세요. **권장안(A)**대로 진행하려면 해당 문자(예: `A`)만, 또는 "권장"이라고 적으셔도 됩니다.

### Q1. 기본 키(PK) 전략 (Domain Model)
전 엔티티의 PK 타입을?
- **A (권장)**: 정수 자동증가(`INTEGER PRIMARY KEY AUTOINCREMENT`) — SQLite 기본, 단순·성능 유리.
- B: UUID(문자열) — 분산 환경 대비(로컬 MVP엔 과함).

[Answer]: A (권장) — 전 엔티티 `INTEGER PRIMARY KEY AUTOINCREMENT`.

### Q2. 타임스탬프 저장 (Data Flow)
`created_at` / `started_at` / `closed_at` 등 시간 컬럼 저장 방식?
- **A (권장)**: **UTC** ISO-8601 저장, 표시(로컬 시간 변환)는 프론트 담당.
- B: 로컬(KST) 저장.

[Answer]: A (권장) — UTC ISO-8601 저장, 표시 변환은 프론트 담당.

### Q3. 주문 번호(`order_number`) 생성 규칙 (Business Rules)
고객·관리자에게 표시되는 주문 번호 형식/범위?
- **A (권장)**: **매장 전역 일별 순번** — `YYYYMMDD-###`(예: `20260831-001`), 자정 리셋. 사람이 읽기 쉬움.
- B: 전역 단순 증가 정수(1,2,3…).
- C: 세션별 순번(세션 내 1부터).

[Answer]: A (권장) — 매장 전역 일별 순번 `YYYYMMDD-###`, 자정 리셋.

### Q4. 삭제/이관 시 참조 무결성 (Business Rules / Data Flow)
이용 완료(세션 close) 시 Order/OrderItem를 OrderHistory로 이관 후 원본 처리, 그리고 메뉴 삭제 시 동작?
- **A (권장)**: 이용 완료 시 원본 Order/OrderItem **물리 삭제**(이력은 OrderHistory 스냅샷에 보존). 메뉴 삭제는 **소프트(is_available=false)가 아닌 물리 삭제 허용**하되 OrderItem은 menu_name/unit_price 스냅샷 보유로 무결. FK는 `ON DELETE` 제약보다 **서비스 계층 트랜잭션**으로 제어.
- B: 원본 소프트 삭제(플래그) 유지.

[Answer]: A (권장) — close 시 원본 물리삭제 + OrderHistory 스냅샷 보존, 메뉴 물리삭제 허용(OrderItem 스냅샷 보유), FK는 서비스 계층 트랜잭션 제어.

### Q5. `OrderHistory.items_snapshot` 형식 (Domain Model)
이관된 주문 항목 스냅샷 저장 형식?
- **A (권장)**: **JSON 컬럼**(`[{menu_name, unit_price, quantity}]`) — 이력 조회 시 단일 레코드로 완결, 메뉴 변경과 디커플.
- B: 별도 OrderHistoryItem 테이블로 정규화.

[Answer]: A (권장) — JSON 컬럼 `[{menu_name, unit_price, quantity}]`.

### Q6. 시드 데이터 규모/값 (Business Scenarios)
데모용 시드 데이터의 구체 값?
- **A (권장)**: 매장 1개(`store_code="STORE01"`, name="데모 카페"), 관리자 1명(`username="admin"`, `password="admin1234"` bcrypt 해시), 카테고리 4개(예: 커피/음료/디저트/식사), 카테고리당 메뉴 4~6개(외부 이미지 URL 플레이스홀더), **테이블 12개**(번호 1~12, 초기 비밀번호 예: `table_number` 문자열). 시드는 **재실행 시 멱등**(기존 있으면 스킵).
- B: 다른 값/규모 지정 (직접 기재).

[Answer]: A (권장) — STORE01/"데모 카페", admin/admin1234(bcrypt), 카테고리 4, 카테고리당 메뉴 4~6, 테이블 12, 멱등 시드.

### Q7. bcrypt 비용(cost factor) & 시크릿 관리 (Business Rules / Integration)
비밀번호 해싱 강도와 JWT 시크릿 관리?
- **A (권장)**: bcrypt cost **12**. JWT 시크릿·DB 경로 등은 `.env`/환경변수(로컬 기본값 fallback 제공, 커밋 금지).
- B: 다른 설정.

[Answer]: A (권장) — bcrypt cost 12, JWT 시크릿·DB 경로는 `.env`/환경변수(로컬 fallback, 커밋 금지).

### Q8. DB 스키마 생성 방식 (Data Flow)
스키마 초기화를?
- **A (권장)**: **SQLAlchemy `create_all()`**(MVP 단순) — 앱 부팅/시드 시 테이블 생성. 마이그레이션 도구(Alembic)는 도입하지 않음.
- B: Alembic 마이그레이션 도입.

[Answer]: A (권장) — SQLAlchemy `create_all()`, Alembic 미도입.

### Q9. 에러 코드 체계 (Error Handling)
구조화 에러 `code` 필드의 표준 집합을 U1에서 확정할까요?
- **A (권장)**: U1에서 **공통 에러 코드 enum** 정의(`VALIDATION_ERROR, UNAUTHORIZED, FORBIDDEN, NOT_FOUND, CONFLICT, TOO_MANY_ATTEMPTS, INTERNAL`)하고 ErrorHandler가 예외→코드 매핑. 각 유닛은 이를 재사용.
- B: 유닛별로 필요 시 추가.

[Answer]: A (권장) — U1에서 공통 에러코드 enum(`VALIDATION_ERROR, UNAUTHORIZED, FORBIDDEN, NOT_FOUND, CONFLICT, TOO_MANY_ATTEMPTS, INTERNAL`) 확정, ErrorHandler가 예외→코드 매핑.

---

## 계획 실행 체크리스트 (Part 2 = Functional Design 산출물 생성)

> 위 질문 승인 후 아래 산출물을 생성합니다. (functional-design.md Step 6)

- [x] `construction/u1-foundation/functional-design/domain-entities.md` — 9개 엔티티 상세(컬럼 타입·nullable·기본값·uniq·인덱스·FK·관계), ERD
- [x] `construction/u1-foundation/functional-design/business-rules.md` — 시드 규칙(멱등), order_number 생성, 타임스탬프(UTC), 에러 코드 체계, 스키마 생성 방식
- [x] `construction/u1-foundation/functional-design/business-logic-model.md` — 부팅 흐름(AppBootstrap→create_all→seed), DbSession 라이프사이클, Health 체크 로직, ErrorHandler 매핑 흐름
- [x] 데이터 모델 불변식(🔬 후속 유닛 PBT 대상) 참조 지점 명시
- [x] (프론트 화면 없음 → frontend-components.md 생략, 앱 셸 라우팅만 business-logic-model.md에 기록)

---

## 승인 요청

Q1~Q9에 답변을 채워 주시면 분석 후(모호 시 후속 질문) Functional Design 산출물을 생성합니다. 전부 권장안으로 진행하려면 "전부 권장"이라고 답하셔도 됩니다.
