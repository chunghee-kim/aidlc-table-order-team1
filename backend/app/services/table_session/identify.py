"""TableSessionService — identification part (U2/A).

Owns setup_table (tablet provisioning, US-A-04) and resolve_session_context (tablet auto-login,
US-C-01/02). Session LIFECYCLE (start/close) is U6/E (lifecycle.py) — not here. DB session is
service-managed (frozen facade signatures carry no session param).
"""
from app.db import SessionLocal
from app.errors import AppError, ErrorCode
from app.models import Table
from app.repositories.store import SqlStoreRepo
from app.repositories.table import SqlTableRepo
from app.security import hash_password, verify_password
from app.services.table_session import TableSessionContext, TableSetupResult


def setup_table(store_id: int, table_number: int, table_password: str, actor=None) -> TableSetupResult:
    """Tablet initial setup (US-A-04): upsert table by (store_id, table_number), store bcrypt
    password hash, enable auto-login. Re-setting an existing number overwrites its password.
    """
    if table_number < 1:
        raise AppError(ErrorCode.VALIDATION_ERROR, "테이블 번호는 1 이상이어야 합니다.")
    if not table_password or not table_password.strip():
        raise AppError(ErrorCode.VALIDATION_ERROR, "테이블 비밀번호를 입력해 주세요.")

    db = SessionLocal()
    try:
        repo = SqlTableRepo(db)
        table = repo.find_by_number(store_id, table_number)
        if table is None:
            table = Table(
                store_id=store_id,
                table_number=table_number,
                table_password_hash=hash_password(table_password),
                is_active=True,
            )
        else:
            table.table_password_hash = hash_password(table_password)
            table.is_active = True
        table = repo.upsert(table)
        db.commit()
        return TableSetupResult(
            table_id=table.id,
            table_number=table.table_number,
            auto_login_enabled=True,
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def resolve_session_context(store_code: str, table_number: int, table_password: str) -> TableSessionContext:
    """Tablet auto-login (US-C-01/02): identify store/table from stored tablet config.

    session_id is None here — the active session is started lazily on the first order
    (U4 -> U6 get_or_start_active_session), keeping the U2/U6 boundary intact.
    """
    db = SessionLocal()
    try:
        store = SqlStoreRepo(db).find_by_code(store_code)
        if store is None:
            raise AppError(ErrorCode.NOT_FOUND, "매장을 찾을 수 없습니다.")
        table = SqlTableRepo(db).find_by_number(store.id, table_number)
        if table is None:
            raise AppError(ErrorCode.NOT_FOUND, "테이블을 찾을 수 없습니다.")
        if not table.is_active or not verify_password(table_password, table.table_password_hash):
            raise AppError(ErrorCode.UNAUTHORIZED, "테이블 인증에 실패했습니다.")
        return TableSessionContext(store_id=store.id, table_id=table.id, session_id=None)
    finally:
        db.close()
