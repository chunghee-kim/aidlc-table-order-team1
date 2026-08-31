# 워크플로우 계획 (Workflow Plan)

**역할**: Solution Architect
**단계**: INCEPTION — Workflow Planning
**입력**: `requirements.md`, `stories.md` (32 스토리), `personas.md`
**분해 방식**: Capability-Based (기능 역량 기반)
**구축 순서**: Foundation-First
**설계 depth**: Standard (유닛별 API 계약 + 데이터 모델 + 핵심 컴포넌트)
**목적**: 이후 단계(Application Design → Units Generation → Construction Per-Unit Loop)가 참조할 유닛 정의·의존성·구축 순서·완료 기준을 확정합니다.

---

## 1. 유닛 개요 (Unit Overview)

| # | 유닛(Unit) | 페르소나 | 포함 스토리 | 우선순위 요약 | PBT |
|---|---|---|---|---|---|
| U1 | **Foundation & Data** | (기반) | SD-1, SD-2, SD-3 | Must | — |
| U2 | **Auth & Session** | 고객·관리자 | US-A-01, US-A-02, US-A-03, US-A-04, US-C-01, US-C-02 | Must(+Should: A-03) | — |
| U3 | **Menu** | 고객·관리자 | US-C-03, US-C-04, US-C-05, US-C-06, US-A-16, US-A-17, US-A-18 | Must(+Should: C-06, A-18) | 🔬 (A-16 검증) |
| U4 | **Cart & Order** | 고객 | US-C-07, US-C-08, US-C-09, US-C-10, US-C-11, US-C-12, US-C-13, US-C-14 | Must(+Should: C-10) | 🔬 |
| U5 | **Order Monitoring (SSE)** | 관리자 | US-A-05, US-A-06, US-A-07, US-A-08, US-A-09, US-A-10 | Must(+Should: A-08) | 🔬 |
| U6 | **Session Lifecycle & History** | 관리자·시스템 | US-A-11, US-A-12, US-A-13, US-A-14, US-A-15 | Must(+Should: A-14, Could: A-15) | 🔬 |

> 스토리 커버리지: 32/32 (고객 14 + 관리자 18). SD-1~3(시드)은 U1에 귀속.

---

## 2. 유닛 상세 (Unit Details)

### U1 — Foundation & Data (기반·데이터 모델·시드)
- **책임**: 프로젝트 스캐폴딩(Vite+React `/customer`·`/admin` 라우트, FastAPI 앱), SQLite 스키마 및 마이그레이션 기초, 시드 스크립트.
- **데이터 모델(초안)**: `Store`, `AdminUser`, `Table`, `TableSession`, `Menu`, `Category`, `Order`, `OrderItem`, `OrderHistory`.
- **API 경계**: 헬스체크, 공통 에러 응답 규약, DB 세션 의존성.
- **시드**: 매장 1개 + 관리자 계정(bcrypt), 카테고리별 샘플 메뉴 + 외부 이미지 URL, 테이블 10~20개.
- **완료 기준(DoD)**: `python` 실행으로 DB 생성·시드 주입 성공, FastAPI/Vite 동시 기동, `/customer`·`/admin` 라우트 진입 확인.
- **의존성**: 없음 (최우선).

### U2 — Auth & Session (인증·세션)
- **책임**: 관리자 JWT 인증(16h), 로그인 시도 제한, 테이블 태블릿 초기 설정·자동 로그인, 테이블 세션 식별 유지.
- **API 경계**: `POST /api/admin/login`, JWT 검증 의존성, `POST /api/admin/tables/{id}/setup`, 테이블 세션 컨텍스트(store/table/session 식별).
- **핵심 컴포넌트**: 관리자 로그인 화면, 태블릿 초기 설정 화면, 자동 로그인 부트스트랩(로컬 저장 정보 → 세션 연결).
- **완료 기준(DoD)**: 관리자 로그인/16h 만료/새로고침 유지, 태블릿 자동 로그인, 세션 ID가 이후 주문에 전파됨.
- **의존성**: U1.

### U3 — Menu (메뉴 조회·관리)
- **책임**: 메뉴 CRUD(등록/수정/삭제/노출 순서), 카테고리별 조회, 고객 메뉴 탐색 UI.
- **API 경계**: `GET /api/menus`(고객), `POST/PUT/DELETE /api/admin/menus`, 순서 변경 엔드포인트.
- **핵심 컴포넌트**: 고객 메뉴 화면(카테고리 탭, 카드, 이미지 플레이스홀더, 44×44px 터치 타깃), 관리자 메뉴 관리 화면.
- **PBT(🔬)**: 메뉴 가격 검증(>0), 필수 필드 검증 (US-A-16).
- **완료 기준(DoD)**: 관리자 메뉴 변경이 고객 화면에 반영, 검증 오류 처리, 순서 반영.
- **의존성**: U1, U2(관리자 보호 엔드포인트).

### U4 — Cart & Order (장바구니·주문) 🔬
- **책임**: 클라이언트 로컬 장바구니(추가/수량/삭제/비우기/새로고침 지속성), 주문 생성·성공 플로우, 현재 세션 주문 조회.
- **API 경계**: `POST /api/orders`(주문 생성 → 세션 시작 트리거는 U6와 계약), `GET /api/orders?session=현재`.
- **핵심 컴포넌트**: 장바구니 상태(로컬 스토리지), 주문 확인/확정, 성공 화면(주문번호 → 5초 후 리다이렉트), 현재 세션 주문 내역 화면.
- **PBT(🔬)**: 장바구니 총액 = Σ(단가×수량), 수량 ≥ 1 정수 (US-C-08); 로컬 저장 라운드트립(저장→복원=원본) (US-C-11); 주문 총액 = 장바구니 총액 (US-C-12).
- **완료 기준(DoD)**: 빈 장바구니 주문 차단, 성공/실패 플로우, 현재 세션 주문만 표시(이전 세션 제외), PBT 통과.
- **의존성**: U1, U2, U3.

### U5 — Order Monitoring (SSE) (실시간 모니터링) 🔬
- **책임**: SSE 기반 실시간 대시보드, 테이블별 카드 그리드, 주문 상세, 상태 전이, 직권 삭제, 테이블 필터.
- **API 경계**: `GET /api/admin/orders/stream`(SSE), `PATCH /api/admin/orders/{id}/status`, `DELETE /api/admin/orders/{id}`.
- **핵심 컴포넌트**: SSE 클라이언트(재연결 시 누락 반영), 그리드 대시보드, 주문 상세 모달, 상태 변경 컨트롤, 신규 주문 강조.
- **PBT(🔬)**: 상태 전이 규칙(대기중→준비중→완료, 허용 전이만) (US-A-09); 삭제 후 테이블 총액 = 남은 주문 합 (US-A-10).
- **완료 기준(DoD)**: 신규 주문 2초 이내 표시, 재연결 시 누락 복구, 상태 변경이 고객 내역(U4)에 반영, PBT 통과.
- **의존성**: U1, U2, U4(주문 데이터·세션).

### U6 — Session Lifecycle & History (세션 라이프사이클·이력) 🔬
- **책임**: 세션 시작(첫 주문), 이용 완료 처리(주문→이력 이동 + 현재 상태/총액 리셋), 과거 내역 조회·날짜 필터.
- **API 경계**: 세션 시작(주문 생성 계약 U4), `POST /api/admin/tables/{id}/close`(이용 완료), `GET /api/admin/history?table=&date=`.
- **핵심 컴포넌트**: 이용 완료 확인 플로우, 과거 내역 화면(테이블별 역순, 날짜 필터, 닫기).
- **PBT(🔬)**: 한 테이블 동시 활성 세션 최대 1개 (US-A-11); 완료 처리 무손실(세션 주문 → OrderHistory 이동 + 상태 리셋) (US-A-12).
- **완료 기준(DoD)**: 이용 완료 후 현재 총액 0·이력 보존, 새 고객이 이전 주문 없이 시작, 날짜 필터 동작, PBT 통과.
- **의존성**: U1, U2, U4, U5.

---

## 3. 의존성 그래프 & 구축 순서 (Dependencies & Sequencing)

```
                 ┌──────────────────────────┐
                 │   U1  Foundation & Data   │  (최우선, 의존성 없음)
                 └────────────┬─────────────┘
                              │
                 ┌────────────▼─────────────┐
                 │   U2  Auth & Session      │
                 └────────────┬─────────────┘
                              │
                 ┌────────────▼─────────────┐
                 │   U3  Menu                │
                 └────────────┬─────────────┘
                              │
                 ┌────────────▼─────────────┐
                 │   U4  Cart & Order  🔬    │
                 └────────────┬─────────────┘
                              │
                 ┌────────────▼─────────────┐
                 │   U5  Order Monitoring 🔬 │
                 └────────────┬─────────────┘
                              │
                 ┌────────────▼─────────────┐
                 │   U6  Session Lifecycle 🔬│
                 └───────────────────────────┘
```

**논리 의존 순서**: U1 → U2 → U3 → U4 → U5 → U6 (Foundation-First, 선형 의존성)

- **실행 모델(개정): 5인 병렬 · 2-Phase.** 논리 의존은 선형이나, **계약 우선(Contract-First)**으로 실행을 병렬화한다. Phase 0(U1 공통 기반 + 전 교차 계약 스텁 동결, 1인 선행) → Phase 1(U2~U6 5개 스트림 5인 병렬). 상세: `application-design/parallel-execution.md`, `application-design/unit-of-work.md §5`.
- U5·U6는 U4의 주문/세션 데이터 모델에 의존하므로 논리적으로 U4 이후이나, Phase 0 계약 스텁 동결로 스텁 대상 병렬 개발이 가능하다.

---

## 4. 공통 관심사 처리 (Cross-Cutting Concerns)

| 관심사 | 귀속 | 참조 방식 |
|---|---|---|
| 데이터 모델·시드 | U1 | 전 유닛이 공유 스키마 참조 |
| JWT 인증·시도 제한 | U2 | 관리자 보호 엔드포인트(U3/U5/U6)가 인증 의존성 사용 |
| 테이블 세션 식별 | U2(식별) + U6(라이프사이클) | U4 주문 생성 시 세션 컨텍스트 주입 |
| 실시간 SSE | U5 | 주문 생성(U4)이 이벤트 소스 |
| PBT(속성 기반 테스트) | U4·U5·U6에 명시적 산출물 | Functional Design(PBT-01)에서 속성으로 상세화 |

---

## 5. 통합·검증 체크포인트 (Integration & Verification)

- **유닛 단위 검증**: 각 유닛 완료 시 단위 테스트 + (해당 시) 속성 기반 테스트(PBT) 통과를 완료 기준으로 함.
- **전체 통합**: CONSTRUCTION 종료 시 **Build & Test** 단계에서 종단 통합(고객 주문 → 관리자 모니터링 → 세션 완료 → 이력) 일괄 검증.
- **회귀 안전**: U4 이후 유닛은 이전 유닛 API 계약을 변경 시 명시적 계약 갱신 필요.

---

## 6. PBT 대상 규칙 → 유닛 매핑 (PBT Rules Mapping)

| 규칙 | 유형 | 유닛 | 스토리 |
|---|---|---|---|
| 장바구니 총액 = Σ(단가×수량) | Invariant | U4 | US-C-08, US-C-12 |
| 장바구니 로컬 저장 라운드트립 | Round-trip | U4 | US-C-11 |
| 주문 상태 전이(대기중→준비중→완료) | Invariant/Stateful | U5 | US-A-09 |
| 삭제 후 테이블 총액 = 남은 주문 합 | Invariant | U5 | US-A-10 |
| 세션: 활성 최대 1개, 완료 시 무손실 이동 | Stateful | U6 | US-A-11, US-A-12 |
| 메뉴 가격/필수 필드 검증 | Invariant | U3 | US-A-16 |

---

## 7. 다음 단계 (Next Stage)

- **Application Design** — 위 6개 유닛을 Standard depth로 설계(도메인/데이터 모델 상세, API 계약, 핵심 컴포넌트/화면).
- **Units Generation** — 설계 확정 후 유닛별 작업 명세 생성.
- **CONSTRUCTION (5인 병렬 · 2-Phase)** — Phase 0(U1 + 계약 동결, 1인) → Phase 1(U2~U6 5스트림 병렬)로 각 스트림이 Functional Design / NFR / Infrastructure / Code Generation 수행. 상세: `application-design/parallel-execution.md`.
