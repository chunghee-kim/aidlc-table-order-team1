# Unit of Work 계획 (Units Generation — Planning)

**단계**: INCEPTION — Units Generation (Part 1: Planning)
**목적**: 시스템을 개발 가능한 작업 단위(Unit of Work)로 분해하고, 유닛 정의·의존성·스토리 매핑·코드 조직 전략을 확정합니다.
**입력**: `application-design/*` (services, components, dependency, methods), `workflow/workflow.md`, `user-stories/stories.md`
**배포 모델**: 단일 배포 가능 애플리케이션 (모놀리식) — 프론트(Vite+React) + 백엔드(FastAPI) + SQLite, 로컬 개발 전용.

> **용어**: 소규모 MVP·로컬 단일 프로세스이므로 각 유닛은 독립 배포 서비스가 아니라 **모놀리식 내부의 논리적 모듈(Module)**입니다. "Unit of Work"는 개발/빌드 순서를 위한 계획 단위입니다.

---

## 배경: 이미 확정된 사항 (Design 단계 산출물)

Application Design과 Workflow Planning에서 아래가 이미 확정되었습니다. 이 계획은 이를 **유닛 산출물로 형식화**하는 것이 목적이며, 아래 미해결 질문만 결정하면 됩니다.

- **6개 유닛**: U1 Foundation & Data / U2 Auth & Session / U3 Menu / U4 Cart & Order / U5 Order Monitoring(SSE) / U6 Session Lifecycle & History
- **분해 방식**: Capability-Based (기능 역량 기반)
- **구축 순서**: Foundation-First 선형 (U1 → U2 → U3 → U4 → U5 → U6)
- **스토리 커버리지**: 32/32 (고객 14 + 관리자 18) + 시드 태스크(SD-1~3 → U1)
- **의존성 그래프**: 선형 DAG (component-dependency.md §7)

---

## 결정이 필요한 질문 (Questions)

> 아래 각 질문의 `[Answer]:` 태그에 직접 답을 채워 주세요. 각 질문에는 **권장안**을 함께 제시했습니다. 권장안대로 진행하려면 "권장"이라고만 적으셔도 됩니다.

### Q1. 유닛 분해 (Story Grouping) — 6유닛 그대로 채택?
Workflow Planning에서 정한 U1~U6 6개 유닛 분해를 그대로 채택할까요, 아니면 병합/분리가 필요한가요?
- **권장**: 6유닛 그대로 채택 (역량 경계가 명확하고 스토리 32개가 균형 있게 분산됨).
- 대안(a): U5(모니터링)와 U6(세션/이력)를 하나로 병합 (둘 다 관리자 후반 기능).
- 대안(b): U1 Foundation을 별도 유닛이 아닌 U2에 흡수.

[Answer]: 권장

### Q2. 코드 조직 전략 (Greenfield Code Organization) — 디렉터리 구조
모놀리식 단일 리포에서 프론트/백엔드 및 유닛별 코드를 어떻게 배치할까요?
- **권장**: 루트에 `backend/`(FastAPI, 계층별 `routers/ services/ repositories/ models/`)와 `frontend/`(Vite+React, feature 기반 `features/customer/ features/admin/ shared/`) 분리. 유닛은 별도 최상위 폴더가 아니라 계층/기능 폴더 안의 파일 그룹으로 존재(예: U3 → `services/menu_service.py`, `features/*/menu/`).
- 대안(a): 유닛별 최상위 폴더(`u1_foundation/`, `u2_auth/` …) 구조 (수직 슬라이스).
- 대안(b): 프론트/백엔드를 별도 리포지토리로 분리.

[Answer]: 권장

### Q3. 공유 코드 소유권 (Shared / Cross-Cutting)
여러 유닛이 공유하는 자산(데이터 모델 전체, ApiClient, ErrorHandler, DbSession 의존성, 공통 UI)은 어느 유닛이 소유할까요?
- **권장**: U1(Foundation)이 **공유 데이터 모델 전체 + 백엔드 공통 인프라(DbSession, ErrorHandler, AppBootstrap, Seed)**를 소유하고, 프론트 공유 인프라(ApiClient는 전 유닛 공용, SseClient는 U5)는 U1에서 ApiClient 스켈레톤만 두고 각 유닛이 확장. 이후 유닛은 U1의 모델을 참조만 함.
- 대안: 각 유닛이 자기 모델만 정의하고 필요 시 점진적 추가.

[Answer]: 권장

### Q4. 데이터 모델 생성 시점 (Data Model Ownership)
9개 데이터 모델(Store/AdminUser/Table/TableSession/Category/Menu/Order/OrderItem/OrderHistory)을 U1에서 **한 번에 전부** 생성할까요, 아니면 유닛별로 **점진적**으로 추가할까요?
- **권장**: U1에서 **전체 스키마를 한 번에** 정의(SQLite 단일 파일·시드 일관성 확보에 유리, 스냅샷/이력 관계가 초기부터 필요).
- 대안: 유닛별 점진 추가(U2에서 Auth/Table, U3에서 Menu … ) — 마이그레이션 관리 부담 증가.

[Answer]: 권장

### Q5. 스토리↔유닛 매핑 확정 (Story Map)
아래 매핑을 확정합니다. 이견이 있으면 수정 요청해 주세요.
| 유닛 | 스토리 |
|---|---|
| U1 | SD-1~3 (스캐폴딩·스키마·시드) |
| U2 | US-A-01, A-02, A-03, A-04, US-C-01, C-02 |
| U3 | US-C-03, C-04, C-05, C-06, US-A-16, A-17, A-18 |
| U4 | US-C-07~14 |
| U5 | US-A-05, A-06, A-07, A-08, A-09, A-10 |
| U6 | US-A-11, A-12, A-13, A-14, A-15 |
- **권장**: 위 매핑 그대로 확정 (application-design.md §4 및 workflow.md와 일치).

[Answer]: 권장

### Q6. 세션 시작 트리거의 유닛 귀속 (Dependency / Contract)
"세션 시작"은 첫 주문(U4)이 트리거하지만 라이프사이클 규칙은 U6 소유입니다. 이 경계를 어떻게 명시할까요?
- **권장**: **규칙·구현은 U6**(TableSessionService.get_or_start_active_session)이 소유, **호출(트리거)은 U4** OrderService가 위임. `unit-of-work-dependency.md`에 U4→U6 계약 의존으로 명시. (services.md §2.4 계약 노트와 일치)
- 대안: 세션 시작 로직을 U4로 이동.

[Answer]: 권장

### Q7. 팀/개발 흐름 (Team Alignment)
개발 진행은 단일 개발 흐름(순차)인가요, 병렬 개발 가능성이 있나요? (유닛 병렬화 계약 필요 여부 판단용)
- **권장**: 단일 개발 흐름, U1→U6 순차 (소규모 MVP). 병렬화 계약 불필요.

[Answer]: 권장

> ⚠️ **개정(SUPERSEDED)**: 이후 5인 병렬 요구로 이 결정은 대체됨. 실행 모델은 **2-Phase 병렬**(Phase 0 U1+계약 동결 1인 선행 → Phase 1 U2~U6 5스트림 병렬). 논리 의존 DAG(U1→U6)는 불변. 상세: `application-design/parallel-execution.md`, `application-design/unit-of-work.md §5`.

---

## 계획 실행 체크리스트 (Part 2에서 실행)

> 위 질문 승인 후 아래 산출물을 생성합니다.

- [x] `application-design/unit-of-work.md` 생성 — 6개 유닛 정의·책임·경계, 코드 조직 전략(Q2/Q3 반영), 공유 자산 소유권
- [x] `application-design/unit-of-work-dependency.md` 생성 — 유닛 간 의존성 매트릭스 + 빌드 순서 + 계약 의존(U4↔U6 세션)
- [x] `application-design/unit-of-work-story-map.md` 생성 — 32개 스토리 + SD 태스크의 유닛 매핑 및 커버리지 검증
- [x] 코드 조직 전략을 `unit-of-work.md`에 문서화 (Greenfield 필수)
- [x] 유닛 경계·의존성 검증 (순환 없음, 선형 DAG 확인)
- [x] 모든 스토리가 유닛에 배정되었는지 확인 (32/32 + SD)

---

## 승인 요청

위 Q1~Q7에 답변을 채워 주시면, 답변을 분석하고(모호한 부분은 후속 질문) 최종 승인 후 Part 2(Generation)로 진행합니다.
