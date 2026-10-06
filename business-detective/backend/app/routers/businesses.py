import shutil

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import Access, business_access, current_user
from ..errors import ApiError
from ..models import Business, BusinessMember, User
from ..schemas import BusinessIn, BusinessOut, BusinessPatch, MemberIn
from ..services.ingest import business_dir

router = APIRouter(prefix="/businesses", tags=["businesses"])


def _out(b: Business, role: str) -> dict:
    return dict(id=b.id, name=b.name, industry=b.industry, currency=b.currency, role=role)


@router.post("", response_model=BusinessOut, status_code=201)
def create(body: BusinessIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    b = Business(name=body.name, industry=body.industry, currency=body.currency, created_by=user.id)
    db.add(b)
    db.flush()
    db.add(BusinessMember(business_id=b.id, user_id=user.id, role="owner"))
    db.commit()
    return _out(b, "owner")


@router.get("", response_model=list[BusinessOut])
def list_mine(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.execute(select(Business, BusinessMember.role).join(BusinessMember, BusinessMember.business_id == Business.id)
                      .where(BusinessMember.user_id == user.id).order_by(Business.id)).all()
    return [_out(b, r) for b, r in rows]


@router.get("/{business_id}", response_model=BusinessOut)
def get_one(a: Access = Depends(business_access)):
    return _out(a.business, a.role)


@router.patch("/{business_id}", response_model=BusinessOut)
def update(body: BusinessPatch, a: Access = Depends(business_access), db: Session = Depends(get_db)):
    a.need_admin()
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(a.business, k, v.strip() if isinstance(v, str) else v)
    db.commit()
    return _out(a.business, a.role)


@router.delete("/{business_id}")
def delete(a: Access = Depends(business_access), db: Session = Depends(get_db)):
    if a.role != "owner":
        raise ApiError(403, "Only the workspace owner can delete it.")
    d = business_dir(a.business.id)
    db.delete(a.business)
    db.commit()
    shutil.rmtree(d, ignore_errors=True)
    return {"deleted": True}


@router.get("/{business_id}/members")
def members(a: Access = Depends(business_access), db: Session = Depends(get_db)):
    rows = db.execute(select(User, BusinessMember.role).join(BusinessMember, BusinessMember.user_id == User.id).where(BusinessMember.business_id == a.business.id)).all()
    return [dict(user_id=u.id, name=u.name, email=u.email, role=r) for u, r in rows]


@router.post("/{business_id}/members", status_code=201)
def add_member(body: MemberIn, a: Access = Depends(business_access), db: Session = Depends(get_db)):
    a.need_admin()
    if body.role == "owner":
        raise ApiError(422, "A workspace has a single owner.")
    u = db.scalar(select(User).where(User.email == body.email.lower()))
    if not u:
        raise ApiError(404, "No account exists with this email yet. Ask them to sign up first.")
    if db.scalar(select(BusinessMember).where(BusinessMember.business_id == a.business.id, BusinessMember.user_id == u.id)):
        raise ApiError(409, "This person is already a member.")
    db.add(BusinessMember(business_id=a.business.id, user_id=u.id, role=body.role))
    db.commit()
    return dict(user_id=u.id, name=u.name, email=u.email, role=body.role)


@router.delete("/{business_id}/members/{user_id}")
def remove_member(user_id: int, a: Access = Depends(business_access), db: Session = Depends(get_db)):
    a.need_admin()
    m = db.scalar(select(BusinessMember).where(BusinessMember.business_id == a.business.id, BusinessMember.user_id == user_id))
    if not m:
        raise ApiError(404, "Member not found.")
    if m.role == "owner":
        raise ApiError(422, "The owner cannot be removed.")
    db.delete(m)
    db.commit()
    return {"removed": True}
