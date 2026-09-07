"""AuthService (U2/A) — admin login, JWT issuance, login-attempt throttling.

Signatures per component-methods.md §1.1. DB session is service-managed (frozen signatures carry
no session param): open a SessionLocal, read, close. JWT primitives come from app.auth.dependency.
"""
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.auth.dependency import AdminContext, encode_admin_token
from app.auth.dependency import verify_token as _verify_token
from app.db import SessionLocal
from app.errors import AppError, ErrorCode
from app.models import AdminUser
from app.repositories.admin_user import SqlAdminUserRepo
from app.schemas.auth import AdminSummary
from app.security import verify_password


@dataclass
class AuthResult:
    token: str
    admin: AdminSummary


# --- Login attempt throttling (US-A-03). In-memory; single-process MVP (resets on restart). ---
_MAX_FAILURES = 5
_LOCKOUT = timedelta(minutes=5)
_attempts: dict[str, tuple[int, datetime | None]] = {}  # key -> (failure_count, locked_until)
_lock = threading.Lock()


def _attempt_key(store_code: str, username: str) -> str:
    return f"{store_code}::{username}"


def _is_locked(store_code: str, username: str) -> bool:
    with _lock:
        key = _attempt_key(store_code, username)
        _, locked_until = _attempts.get(key, (0, None))
        if locked_until is None:
            return False
        if locked_until > datetime.now(timezone.utc):
            return True
        # Lockout window elapsed — clear so counting restarts.
        _attempts.pop(key, None)
        return False


def register_login_attempt(store_code: str, username: str, success: bool) -> None:
    """Record a login attempt: reset on success, else increment and lock after _MAX_FAILURES."""
    with _lock:
        key = _attempt_key(store_code, username)
        if success:
            _attempts.pop(key, None)
            return
        failures, _ = _attempts.get(key, (0, None))
        failures += 1
        locked_until = datetime.now(timezone.utc) + _LOCKOUT if failures >= _MAX_FAILURES else None
        _attempts[key] = (failures, locked_until)


def issue_token(admin: AdminUser) -> str:
    """Sign a 16h JWT for the given admin (component-methods.md §1.1)."""
    return encode_admin_token(admin.id, admin.store_id)


def verify_token(token: str) -> AdminContext:
    """Verify a JWT -> AdminContext (delegates to the shared JWT primitive)."""
    return _verify_token(token)


def authenticate(store_code: str, username: str, password: str) -> AuthResult:
    """Validate credentials (bcrypt) + attempt limit -> issue JWT. US-A-01/03.

    Raises TOO_MANY_ATTEMPTS (429) while locked, UNAUTHORIZED (401) on bad credentials.
    Uses a uniform error for missing store/admin and wrong password (no user enumeration).
    """
    if _is_locked(store_code, username):
        raise AppError(
            ErrorCode.TOO_MANY_ATTEMPTS,
            "로그인 시도가 너무 많습니다. 잠시 후 다시 시도해 주세요.",
        )

    db = SessionLocal()
    try:
        admin = SqlAdminUserRepo(db).find_by_store_and_username(store_code, username)
        if admin is None or not verify_password(password, admin.password_hash):
            register_login_attempt(store_code, username, success=False)
            raise AppError(ErrorCode.UNAUTHORIZED, "매장 식별자, 사용자명 또는 비밀번호가 올바르지 않습니다.")

        register_login_attempt(store_code, username, success=True)
        return AuthResult(
            token=issue_token(admin),
            admin=AdminSummary(id=admin.id, username=admin.username, store_id=admin.store_id),
        )
    finally:
        db.close()
