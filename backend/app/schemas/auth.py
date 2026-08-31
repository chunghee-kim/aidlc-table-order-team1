"""Auth endpoint schemas (U2/A consumes; frozen in Phase 0)."""
from pydantic import BaseModel


class LoginRequest(BaseModel):
    store_code: str
    username: str
    password: str


class AdminSummary(BaseModel):
    id: int
    username: str
    store_id: int


class LoginResponse(BaseModel):
    token: str
    admin: AdminSummary
