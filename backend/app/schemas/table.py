"""Table setup / customer table-login schemas (U2/A, U6/E; frozen in Phase 0)."""
from datetime import datetime

from pydantic import BaseModel


class TableSetupRequest(BaseModel):
    table_number: int
    table_password: str


class TableSetupResponse(BaseModel):
    table_id: int
    table_number: int
    auto_login_enabled: bool


class TableLoginRequest(BaseModel):
    store_code: str
    table_number: int
    table_password: str


class TableLoginResponse(BaseModel):
    store_id: int
    table_id: int


class CloseResponse(BaseModel):
    moved_order_count: int
    closed_at: datetime
