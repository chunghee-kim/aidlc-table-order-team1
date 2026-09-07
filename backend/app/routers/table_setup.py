"""TableRouter — setup part (U2/A). Table close is U6/E (routers/table_close.py).

  POST /api/admin/tables/{table_id}/setup   (admin)  -> tablet provisioning (US-A-04)
  POST /api/customer/table-login            (public) -> tablet auto-login identity (US-C-01/02)

Note: the path {table_id} is kept for REST convention, but the frozen setup_table contract keys
the upsert on (store_id, table_number) from the body — the tablet supplies its number/password.
"""
from fastapi import APIRouter, Depends

from app.auth.dependency import AdminContext, get_current_admin
from app.schemas.table import (
    TableLoginRequest,
    TableLoginResponse,
    TableSetupRequest,
    TableSetupResponse,
)
from app.services.table_session import resolve_session_context, setup_table

router = APIRouter(prefix="/api", tags=["table"])


@router.post("/admin/tables/{table_id}/setup", response_model=TableSetupResponse)
def setup(
    table_id: int,  # noqa: ARG001 — REST path id; upsert keyed by (store_id, table_number) per contract
    body: TableSetupRequest,
    admin: AdminContext = Depends(get_current_admin),
) -> TableSetupResponse:
    result = setup_table(admin.store_id, body.table_number, body.table_password, admin)
    return TableSetupResponse(
        table_id=result.table_id,
        table_number=result.table_number,
        auto_login_enabled=result.auto_login_enabled,
    )


@router.post("/customer/table-login", response_model=TableLoginResponse)
def table_login(body: TableLoginRequest) -> TableLoginResponse:
    ctx = resolve_session_context(body.store_code, body.table_number, body.table_password)
    return TableLoginResponse(store_id=ctx.store_id, table_id=ctx.table_id)
