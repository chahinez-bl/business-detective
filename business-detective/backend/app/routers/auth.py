from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user, get_claims, purge_revoked
from ..errors import ApiError
from ..models import Business, BusinessMember, RevokedToken, User
from ..schemas import LoginIn, PasswordIn, ProfileIn, RegisterIn, TokenOut, UserOut
from ..security import check_password_rules, create_token, hash_password, throttle_check, throttle_fail, throttle_reset, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])
_DUMMY = hash_password("not-a-real-password")   # constant-time-ish behaviour for unknown emails


@router.post("/register", response_model=TokenOut, status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    email = body.email.lower()
    check_password_rules(body.password)
    if db.scalar(select(User).where(User.email == email)):
        raise ApiError(409, "An account with this email already exists. Try signing in instead.")
    u = User(email=email, name=body.name, password_hash=hash_password(body.password))
    db.add(u)
    db.commit()
    tok, exp = create_token(u.id)
    return TokenOut(token=tok, expires_at=exp, user=UserOut.model_validate(u))


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)):
    email = body.email.lower()
    key = f"{request.client.host if request.client else '?'}|{email}"
    throttle_check(key)
    u = db.scalar(select(User).where(User.email == email))
    ok = verify_password(body.password, u.password_hash if u else _DUMMY) and u is not None and u.is_active
    if not ok:
        throttle_fail(key)
        raise ApiError(401, "Incorrect email or password.")
    throttle_reset(key)
    tok, exp = create_token(u.id)
    return TokenOut(token=tok, expires_at=exp, user=UserOut.model_validate(u))


@router.post("/logout")
def logout(claims: dict = Depends(get_claims), db: Session = Depends(get_db)):
    db.merge(RevokedToken(jti=claims["jti"], expires_at=datetime.fromtimestamp(claims["exp"], timezone.utc)))
    purge_revoked(db)
    db.commit()
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.execute(select(Business, BusinessMember.role).join(BusinessMember, BusinessMember.business_id == Business.id)
                      .where(BusinessMember.user_id == user.id).order_by(Business.id)).all()
    return dict(user=UserOut.model_validate(user), businesses=[dict(id=b.id, name=b.name, industry=b.industry, currency=b.currency, role=r) for b, r in rows])


@router.patch("/me", response_model=UserOut)
def update_me(body: ProfileIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    user.name = body.name.strip()
    db.commit()
    return user


@router.post("/password")
def change_password(body: PasswordIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not verify_password(body.current_password, user.password_hash):
        raise ApiError(400, "Your current password is incorrect.")
    check_password_rules(body.new_password)
    user.password_hash = hash_password(body.new_password)
    db.commit()
    return {"ok": True}
