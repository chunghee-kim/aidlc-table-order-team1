"""AppBootstrap (U1) — FastAPI app: create_all -> error handlers -> CORS -> routers.

Phase 1 streams add their routers below the marked section (one line each, no other edits here).
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import create_all
from app.errors import register_error_handlers
from app.routers import health


def create_app() -> FastAPI:
    app = FastAPI(title="Table Order Service", version="0.1.0")

    # Schema creation (create_all strategy, no Alembic).
    create_all()

    register_error_handlers(app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # U1 (Phase 0) router.
    app.include_router(health.router)

    # --- Phase 1 stream routers (each stream appends its own include_router here) ---
    # app.include_router(auth.router)          # U2/A
    # app.include_router(table_setup.router)   # U2/A
    # app.include_router(menu.router)          # U3/B
    # app.include_router(order.router)         # U4/C
    # app.include_router(admin_order.router)   # U5/D
    # app.include_router(table_close.router)   # U6/E
    # app.include_router(history.router)       # U6/E

    return app


app = create_app()
