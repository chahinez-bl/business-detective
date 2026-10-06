from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import Access, business_access
from ..errors import ApiError
from ..models import Action, BusinessMember, Insight, Recommendation, User
from ..schemas import ActionIn, ActionPatch

router = APIRouter(prefix="/businesses/{business_id}/actions", tags=["actions"])


def _out(x: Action, names: dict) -> dict:
    return dict(id=x.id, title=x.title, note=x.note, status=x.status, insight_id=x.insight_id, recommendation_id=x.recommendation_id, source_title=x.source_title,
                assignee_id=x.assignee_id, assignee=names.get(x.assignee_id), due_date=x.due_date.isoformat() if x.due_date else None,
                created_at=x.created_at.isoformat(), updated_at=x.updated_at.isoformat(), resolved_at=x.resolved_at.isoformat() if x.resolved_at else None,
                overdue=bool(x.due_date and x.due_date < datetime.now(timezone.utc).date() and x.status in ("todo", "in_progress")))


def names_for(db: Session, bid: int) -> dict:
    return {u.id: u.name for u in db.scalars(select(User).join(BusinessMember, BusinessMember.user_id == User.id).where(BusinessMember.business_id == bid)).all()}


def _check_assignee(db, bid, uid):
    if uid is not None and not db.scalar(select(BusinessMember).where(BusinessMember.business_id == bid, BusinessMember.user_id == uid)):
        raise ApiError(422, "You can only assign actions to members of this workspace.")


def _get(db, a: Access, action_id: int) -> Action:
    x = db.get(Action, action_id)
    if not x or x.business_id != a.business.id:
        raise ApiError(404, "We couldn't find this action.")
    return x


@router.get("")
def list_actions(status: str | None = None, a: Access = Depends(business_access), db: Session = Depends(get_db)):
    q = select(Action).where(Action.business_id == a.business.id).order_by(Action.id.desc())
    if status:
        q = q.where(Action.status == status)
    names = names_for(db, a.business.id)
    return [_out(x, names) for x in db.scalars(q).all()]


@router.post("", status_code=201)
def create_action(body: ActionIn, a: Access = Depends(business_access), db: Session = Depends(get_db)):
    a.need_write()
    src = ""
    if body.insight_id is not None:
        i = db.get(Insight, body.insight_id)
        if not i or i.business_id != a.business.id:
            raise ApiError(422, "That insight doesn't belong to this business.")
        src = i.title
    if body.recommendation_id is not None:
        r = db.get(Recommendation, body.recommendation_id)
        if not r or r.business_id != a.business.id:
            raise ApiError(422, "That recommendation doesn't belong to this business.")
    _check_assignee(db, a.business.id, body.assignee_id)
    x = Action(business_id=a.business.id, title=body.title.strip(), note=body.note, insight_id=body.insight_id, recommendation_id=body.recommendation_id,
               assignee_id=body.assignee_id, due_date=body.due_date, source_title=src, created_by=a.user.id)
    db.add(x)
    db.commit()
    return _out(x, names_for(db, a.business.id))


@router.patch("/{action_id}")
def update_action(action_id: int, body: ActionPatch, a: Access = Depends(business_access), db: Session = Depends(get_db)):
    a.need_write()
    x = _get(db, a, action_id)
    d = body.model_dump(exclude_unset=True)
    if "title" in d and d["title"]: x.title = d["title"].strip()
    if "note" in d and d["note"] is not None: x.note = d["note"]
    if d.get("assignee_id") is not None:
        _check_assignee(db, a.business.id, d["assignee_id"]); x.assignee_id = d["assignee_id"]
    if d.get("clear_assignee"): x.assignee_id = None
    if d.get("due_date") is not None: x.due_date = d["due_date"]
    if d.get("clear_due_date"): x.due_date = None
    if d.get("status"):
        x.status = d["status"]
        x.resolved_at = datetime.now(timezone.utc) if d["status"] == "resolved" else None
    db.commit()
    return _out(x, names_for(db, a.business.id))


@router.delete("/{action_id}")
def delete_action(action_id: int, a: Access = Depends(business_access), db: Session = Depends(get_db)):
    a.need_write()
    db.delete(_get(db, a, action_id))
    db.commit()
    return {"deleted": True}
