"""AuthDependency (contract frozen in Phase 0; real JWT verification implemented by U2/A).

Consumers: U3/U5/U6 protected endpoints depend on `get_current_admin`.
Phase 0 provides a dev pass-through stub so streams can wire protected routes before U2 lands.
Do NOT change the AdminContext shape or dependency name without owner+consumer agreement.
"""
from dataclasses import dataclass

from app.errors import AppError, ErrorCode


@dataclass
class AdminContext:
    admin_id: int
    store_id: int


def get_current_admin() -> AdminContext:
    """FastAPI dependency returning the authenticated admin context.

    Phase 0 STUB: dev pass-through (returns a fixed dev admin). U2/A replaces this with
    real JWT (Bearer) verification -> AdminContext, raising AppError(UNAUTHORIZED) on failure.
    """
    # --- Phase 0 dev pass-through. Replace in U2/A. ---
    return AdminContext(admin_id=1, store_id=1)


def verify_token(token: str) -> AdminContext:  # noqa: ARG001
    """Verify a JWT and return the admin context. Implemented in U2/A."""
    raise AppError(ErrorCode.UNAUTHORIZED, "verify_token not implemented (U2/A owns).")
