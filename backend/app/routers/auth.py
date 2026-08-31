"""AuthRouter (U2/A) — POST /api/admin/login (public)."""
from fastapi import APIRouter

from app.schemas.auth import LoginRequest, LoginResponse
from app.services import auth_service

router = APIRouter(prefix="/api/admin", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest) -> LoginResponse:
    result = auth_service.authenticate(body.store_code, body.username, body.password)
    return LoginResponse(token=result.token, admin=result.admin)
