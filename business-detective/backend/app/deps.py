from datetime import datetime, timezone

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .errors import ApiError
from .models import Business, BusinessMember, RevokedToken, User
from .security import decode_token

WRITE_ROLES = {"owner", "admin", "member"}
ADMIN_ROLES = {"owner", "admin"}


def get_token(request: Request) -> str:
    h = request.headers.get("authorization", "")
    if not h.lower().startswith("bearer ") or len(h) < 10:
        raise ApiError(401, "Please sign in to continue.")
    return h[7:].strip()


def get_claims(token: str = Depends(get_token), db: Session = Depends(get_db)) -> dict:
    claims = decode_token(token)
    if db.get(RevokedToken, claims.get("jti")):
        raise ApiError(401, "You have been signed out. Please sign in again.")
    return claims


def current_user(claims: dict = Depends(get_claims), db: Session = Depends(get_db)) -> User:
    user = db.get(User, int(claims["sub"]))
    if not user or not user.is_active:
        raise ApiError(401, "Your account is not available. Please sign in again.")
    return user


class Access:
    """Resolved business + the caller's role. Raises 404 (not 403) for non-members so business ids cannot be probed."""

    def __init__(self, business: Business, role: str, user: User):
        self.business, self.role, self.user = business, role, user

    def need_write(self):
        if self.role not in WRITE_ROLES:
            raise ApiError(403, "Your role is read-only in this workspace.")

    def need_admin(self):
        if self.role not in ADMIN_ROLES:
            raise ApiError(403, "Only workspace owners and admins can do this.")


def business_access(business_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)) -> Access:
    m = db.scalar(select(BusinessMember).where(BusinessMember.business_id == business_id, BusinessMember.user_id == user.id))
    b = db.get(Business, business_id) if m else None
    if not b:
        raise ApiError(404, "We couldn't find this business.")
    return Access(b, m.role, user)


def purge_revoked(db: Session) -> None:
    db.query(RevokedToken).filter(RevokedToken.expires_at < datetime.now(timezone.utc)).delete()
