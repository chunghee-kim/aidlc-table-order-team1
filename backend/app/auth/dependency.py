"""AuthDependency (contract frozen in Phase 0; real JWT verification implemented by U2/A).

Consumers: U3/U5/U6 protected endpoints depend on `get_current_admin`.
The AdminContext shape and the `get_current_admin` / `verify_token` names are frozen contract —
do NOT change them without owner+consumer agreement. JWT encode/decode primitives live here so
`app.services.auth_service` can build on them without an import cycle (auth_service -> dependency).
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Header

from app.config import settings
from app.errors import AppError, ErrorCode

_ALGORITHM = "HS256"


@dataclass
class AdminContext:
    admin_id: int
    store_id: int


def encode_admin_token(admin_id: int, store_id: int) -> str:
    """Sign a JWT carrying the admin context, expiring in settings.jwt_expire_hours (default 16h)."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(admin_id),
        "admin_id": admin_id,
        "store_id": store_id,
        "iat": now,
        "exp": now + timedelta(hours=settings.jwt_expire_hours),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM)


def verify_token(token: str) -> AdminContext:
    """Verify a JWT and return the admin context. Raises AppError(UNAUTHORIZED) on failure/expiry."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise AppError(ErrorCode.UNAUTHORIZED, "세션이 만료되었습니다. 다시 로그인해 주세요.") from exc
    except jwt.PyJWTError as exc:
        raise AppError(ErrorCode.UNAUTHORIZED, "유효하지 않은 인증 토큰입니다.") from exc
    try:
        return AdminContext(admin_id=int(payload["admin_id"]), store_id=int(payload["store_id"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise AppError(ErrorCode.UNAUTHORIZED, "유효하지 않은 인증 토큰입니다.") from exc


def get_current_admin(authorization: str | None = Header(default=None)) -> AdminContext:
    """FastAPI dependency: extract Bearer token from Authorization header -> AdminContext.

    Protected routers use `Depends(get_current_admin)`. Missing/malformed header or an invalid
    token raises AppError(UNAUTHORIZED) (401) via the shared ErrorHandler.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AppError(ErrorCode.UNAUTHORIZED, "인증이 필요합니다.")
    token = authorization.split(" ", 1)[1].strip()
    return verify_token(token)
