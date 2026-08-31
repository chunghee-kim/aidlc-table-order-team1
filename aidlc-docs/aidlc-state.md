# AI-DLC State Tracking

## Project Information
- **Project Name**: Table Order Service (테이블오더 서비스)
- **Project Type**: Greenfield
- **Start Date**: 2026-08-31T04:12:23Z
- **Current Stage**: CONSTRUCTION - **Phase 0 (공통 기반, 1인 선행)** [U1 Foundation & Data + 전 교차 계약 동결] - Functional Design Part 1 (Planning) — plan generated, awaiting answers
- **Execution Model**: 5인 병렬 (2-Phase). Phase 0 = U1 + 계약 스텁 동결(1인) → Phase 1 = U2~U6 5개 스트림 병렬. 근거: `inception/application-design/parallel-execution.md`

## Workspace State
- **Existing Code**: No
- **Reverse Engineering Needed**: No
- **Programming Languages**: None yet (to be determined)
- **Build System**: None yet (to be determined)
- **Project Structure**: Empty (Greenfield)
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
- [ ] **Phase 0 — 공통 기반 (1인 선행 · 유일 직렬 구간)**
  - [ ] U1 Foundation & Data + 전 교차 계약 스텁 동결 ← **현재: Functional Design (Planning)**
        (9모델·DB·에러·시드·ApiClient + AuthDependency/TableSessionService/OrderEventBroker/MenuRepo/schemas/프론트 Context·SseClient 인터페이스 동결)
  - Phase 0 DoD 달성·머지 → Phase 1 착수 신호
- [ ] **Phase 1 — 5개 스트림 병렬 (5인 · 계약 스텁 대상)** — 각 스트림: Functional Design / NFR / Infrastructure / Code Generation
  - [ ] A · U2 Auth & Session
  - [ ] B · U3 Menu
  - [ ] C · U4 Cart & Order
  - [ ] D · U5 Order Monitoring (SSE)
  - [ ] E · U6 Session Lifecycle & History
  - 권장 머지 순서: A → B → C → (D, E 병렬) → 파사드/DI 조립 PR
- [ ] Build and Test (종단 통합 검증)

### 🟡 OPERATIONS PHASE
- [ ] Operations (placeholder)
