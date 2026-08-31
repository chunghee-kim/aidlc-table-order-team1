# AI-DLC State Tracking

## Project Information
- **Project Name**: Table Order Service (테이블오더 서비스)
- **Project Type**: Greenfield
- **Start Date**: 2026-08-31T04:12:23Z
- **Current Stage**: CONSTRUCTION - **Phase 0 (공통 기반, 1인 선행)** [U1 Foundation & Data + 전 교차 계약 동결] - **완료 + 런타임 검증 통과** (Q1~Q9 전부 권장안 A). Python 3.12.10 + Node 24.19.0 설치, backend venv/pip install, 멱등 시드, `uvicorn`+`/api/health`=200, 전 계약 스텁 임포트, frontend `npm install`/`tsc --noEmit`/`vite build`/preview 200 모두 통과. ✅ **Phase 0 DoD 달성 → Phase 1 (U2~U6 5스트림) 착수 가능.**
- **Execution Model**: 5인 병렬 (2-Phase). Phase 0 = U1 + 계약 스텁 동결(1인) → Phase 1 = U2~U6 5개 스트림 병렬. 근거: `inception/application-design/parallel-execution.md`

## Workspace State
- **Existing Code**: Yes (Phase 0 scaffolding + U1 foundation + 계약 스텁)
- **Reverse Engineering Needed**: No
- **Programming Languages**: Python 3 (FastAPI backend) + TypeScript (React/Vite frontend)
- **Build System**: pip / `requirements.txt` (backend), npm / Vite (frontend)
- **Project Structure**: `backend/` (app: models·db·errors·seed·main·health + schemas·auth·services·repositories 스텁) + `frontend/` (src: main·app·shared·context)
- **Workspace Root**: C:\Users\김충희\aidlc-workshop\table-order

## Code Location Rules
- **Application Code**: Workspace root (NEVER in aidlc-docs/)
- **Documentation**: aidlc-docs/ only
- **Structure patterns**: See code-generation.md Critical Rules

## Extension Configuration
| Extension | Enabled | Decided At |
|---|---|---|
| Security Baseline | No | Requirements Analysis |
| Resiliency Baseline | No | Requirements Analysis |
| Property-Based Testing | Yes (Full enforcement) | Requirements Analysis |

## Technology Decisions (from Requirements Analysis)
- **Frontend**: React (Vite + React), single project with route separation (/customer, /admin)
- **Backend**: Python + FastAPI
- **Database**: SQLite (file-based, local)
- **Deployment**: Local development only, no Docker
- **Store/Admin provisioning**: Seed data (sample store + admin account)
- **Menu data**: Sample seed data + external image URL references (no upload)
- **Scale**: Small — 1 store, 10-20 tables (demo/MVP)
- **PBT Framework**: Hypothesis (Python), fast-check (TypeScript) — to be confirmed in NFR Requirements

## Stage Progress
### 🔵 INCEPTION PHASE
- [x] Workspace Detection
- [ ] Reverse Engineering (N/A — Greenfield)
- [x] Requirements Analysis
- [x] User Stories
- [x] Workflow Planning
- [x] Application Design
- [x] Units Generation

### 🟢 CONSTRUCTION PHASE (5인 병렬 · 2-Phase)
- [x] **Phase 0 — 공통 기반 (1인 선행 · 유일 직렬 구간)** — 코드 완주 + 런타임 DoD 검증 통과 ✅
  - [x] U1 Foundation & Data + 전 교차 계약 스텁 동결
        (9모델·DB·에러·멱등시드·ApiClient + AuthDependency/TableSessionService/OrderEventBroker/리포/schemas/프론트 Context·SseClient 인터페이스 동결, main.tsx 라우트 레지스트리)
        Functional Design 산출물: `construction/u1-foundation/functional-design/{domain-entities,business-rules,business-logic-model}.md`
  - Phase 0 DoD: 정적 완료. 런타임 검증 명령은 `construction/plans/u1-foundation-functional-design-plan.md`·CLAUDE.md 참조 → 통과 시 Phase 1 착수 신호
- [ ] **Phase 1 — 5개 스트림 병렬 (5인 · 계약 스텁 대상)** — 각 스트림: Functional Design / NFR / Infrastructure / Code Generation
  - [x] A · U2 Auth & Session — 브랜치 `feat/u2-auth`. Functional Design + 실구현 완료.
        백엔드: AuthDependency(JWT 실검증)·auth_service(로그인/16h/시도제한5회→429)·routers/{auth,table_setup}·table_session/identify·{store,admin_user,table,session}Repo 구체구현·main.py 라우터 등록. 파사드는 identify만 배선(lifecycle는 U6/E 스텁 유지).
        프론트: AuthContext·TableSessionContext 실구현, features/admin/auth(AdminLogin·TableSetup)·features/customer/auto-login(AutoLoginBootstrap·TableLogin).
        검증: `pytest` 13 pass, `npm run typecheck`/`build` pass, 시드 대상 종단 스모크(login→setup→table-login, 보호엔드포인트 401) pass.
        산출물: Functional Design(`construction/u2-auth/functional-design/functional-design.md`), **NFR 정의**(`construction/u2-auth/nfr/nfr-requirements.md`)·**NFR 설계**(`construction/u2-auth/nfr/nfr-design.md`) — NFR-2(보안: bcrypt12·JWT16h·시도제한5→429·열거방지·테이블경계)·NFR-3(세션)·NFR-4/6/7 커버.
        Infrastructure 단계: 별도 인프라 없음(SQLite 파일·`.env`·로컬 기동) → NFR 설계 §3.3/§5에 흡수. Code Generation 완료.
  - [~] B · U3 Menu — Functional Design ✅ · NFR Requirements ✅ · NFR Design ✅ · Infrastructure Design ✅ (Code Generation: 코드 구현 완료, branch `feature/u3-menu`)
        NFR 산출물: `construction/u3-menu/nfr-requirements/{nfr-requirements,tech-stack-decisions}.md`, `construction/u3-menu/nfr-design/{nfr-design-patterns,logical-components}.md`
        Infra 산출물: `construction/u3-menu/infrastructure-design/{infrastructure-design,deployment-architecture}.md` (신규 공유 인프라 없음 — U1 모놀리스 공유)
  - [ ] C · U4 Cart & Order
  - [ ] D · U5 Order Monitoring (SSE)
  - [ ] E · U6 Session Lifecycle & History
  - 권장 머지 순서: A → B → C → (D, E 병렬) → 파사드/DI 조립 PR
- [ ] Build and Test (종단 통합 검증)

### 🟡 OPERATIONS PHASE
- [ ] Operations (placeholder)
