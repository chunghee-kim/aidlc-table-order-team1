# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## AI-DLC Workflow Configuration

This project is configured with **AI-DLC (AWS AI Development Lifecycle) v1.0.1** workflows for enhanced code review and development assistance.

### Rule Details

The `.aidlc-rule-details/` directory contains detailed guidelines and standards for:
- **ascii-diagram-standards.md** — Standards for creating ASCII diagrams in documentation
- **content-validation.md** — Guidelines for validating content quality
- **depth-levels.md** — Standards for API/documentation depth levels
- **error-handling.md** — Best practices for error handling
- **overconfidence-prevention.md** — Techniques to prevent overconfident code assessments

These rules are used during code review and development to ensure consistency with AWS best practices.

### Claude Code Settings

The `.claude/settings.json` file contains the configuration for Claude Code integration, including PR attribution settings for contributions to this project.

## Project Status

CONSTRUCTION **Phase 0 (U1 Foundation & Data)** complete: project scaffolding, full 9-model SQLite schema, idempotent seed, common backend infra, `ApiClient`, and **all cross-cutting contract stubs** are in place. Phase 1 (U2–U6, 5 parallel streams) develops against these frozen contracts. Prereqs: **Python 3.11+** and **Node 18+** (not yet verified at runtime in the authoring environment).

## Build, Run, and Test Commands

### Backend (`backend/` — FastAPI + SQLAlchemy + SQLite)
```bash
cd backend
python -m venv .venv && source .venv/Scripts/activate   # Windows Git Bash; use .venv/bin/activate on Unix
pip install -r requirements.txt
cp .env.example .env                # set JWT_SECRET etc. (do not commit .env)
python -m app.seed                  # idempotent seed (store/admin/menus/12 tables)
uvicorn app.main:app --reload       # http://localhost:8000 ; GET /api/health -> {"status":"ok","db":"ok"}
pytest                              # unit tests + PBT (Hypothesis), added per unit in Phase 1
```

### Frontend (`frontend/` — Vite + React + TypeScript)
```bash
cd frontend
npm install
npm run dev          # http://localhost:5173 ; /customer and /admin reachable (proxies /api -> :8000)
npm run typecheck    # tsc --noEmit (contract-stub type check)
npm run build        # tsc --noEmit && vite build
npm run test         # vitest (fast-check PBT for cart round-trip in U4)
```

## Architecture Overview

Monolith: `backend/` (3-layer Router → Service → Repository) + `frontend/` (feature-based, `/customer` & `/admin`). Auth via admin JWT (16h, localStorage); realtime via in-memory pub/sub broker + SSE. Structured error body `{error:{code,message,details}}` everywhere.

- **Backend**: `app/main.py` (AppBootstrap), `app/db.py` (session/`Base`/`create_all`), `app/errors.py` (`ErrorCode`/`AppError`/handler), `app/models/` (9 models), `app/seed.py`, `app/schemas/` (API contract), `app/auth/dependency.py` (`AuthDependency`), `app/services/{order,table_session}/` (facade packages), `app/services/order_event_broker.py`, `app/repositories/` (Protocol interfaces).
- **Frontend**: `src/main.tsx` (app shell), `src/app/route-registry.ts` (auto-collects `features/*/routes.tsx`), `src/shared/api/{api-client,sse-client}.ts`, `src/context/{auth,table-session,cart}-context.tsx`.

## Development Workflow — Parallel Execution Rules (critical)

This repo builds via **2-Phase 5-person parallel execution** (`aidlc-docs/inception/application-design/parallel-execution.md`). Phase 0 (U1) is done. In **Phase 1**:
- **1 file = 1 stream owner.** Streams edit only their owned files (see `unit-of-work.md §3`, `parallel-execution.md §4`). Shared services are split so owners don't collide: `services/order/{create.py→C, admin.py→D}`, `services/table_session/{identify.py→A, lifecycle.py→E}`, `routers/{table_setup.py→A, table_close.py→E}`.
- **Never edit `main.tsx`** to add routes — add `features/<name>/routes.tsx` (auto-collected).
- **Do not change frozen contracts** (`schemas/`, `AuthDependency`, service facades, `OrderEventBroker`, repo Protocols, frontend contexts, `SseClient`) unilaterally; owner + consumer agree and update the stub first.
- **Recommended merge order**: A (U2) → B (U3) → C (U4) → (D, E parallel) → facade/DI assembly PR.
- **PBT (Hypothesis / fast-check)** is enforced: B=price>0/required, C=total/qty/round-trip, D=transitions/delete-total, E=active-session≤1/lossless-migration.
