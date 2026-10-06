import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import Access, business_access
from ..errors import ApiError
from ..models import Action, Report
from ..services import ingest
from ..services.reports import build_pdf
from ..services.workspace import customer_bundle, latest_analysis
from .actions import names_for, _out as action_out

router = APIRouter(prefix="/businesses/{business_id}/reports", tags=["reports"])


def _meta(r: Report) -> dict:
    return dict(id=r.id, title=r.title, size_bytes=r.size_bytes, created_at=r.created_at.isoformat(), analysis_id=r.analysis_id)


def _path(bid: int, r: Report):
    return ingest.business_dir(bid) / f"report_{r.stored_name}.pdf"


@router.post("", status_code=201)
def generate(a: Access = Depends(business_access), db: Session = Depends(get_db)):
    a.need_write()
    bundle = customer_bundle(db, a.business, a.role)
    if not bundle.get("has_data"):
        raise ApiError(404, "Upload and analyze your data before creating a report.")
    names = names_for(db, a.business.id)
    acts = [action_out(x, names) for x in db.scalars(select(Action).where(Action.business_id == a.business.id, Action.status != "dismissed").order_by(Action.id.desc())).all()]
    pdf = build_pdf(bundle, acts, a.business.name)
    r = Report(business_id=a.business.id, analysis_id=bundle["analysis"]["id"], title=f"Business report — {bundle['kpis']['end']}", stored_name=uuid.uuid4().hex, size_bytes=len(pdf), created_by=a.user.id)
    _path(a.business.id, r).write_bytes(pdf)
    db.add(r)
    db.commit()
    return _meta(r)


@router.get("")
def list_reports(a: Access = Depends(business_access), db: Session = Depends(get_db)):
    return [_meta(r) for r in db.scalars(select(Report).where(Report.business_id == a.business.id).order_by(Report.id.desc())).all()]


@router.get("/{report_id}/download")
def download(report_id: int, a: Access = Depends(business_access), db: Session = Depends(get_db)):
    r = db.get(Report, report_id)
    if not r or r.business_id != a.business.id:
        raise ApiError(404, "We couldn't find this report.")
    p = _path(a.business.id, r)
    if not p.exists():
        raise ApiError(410, "This report file is no longer available. Please generate a new one.")
    return Response(p.read_bytes(), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="business-report-{r.id}.pdf"', "Cache-Control": "private, no-store"})


@router.delete("/{report_id}")
def delete_report(report_id: int, a: Access = Depends(business_access), db: Session = Depends(get_db)):
    a.need_write()
    r = db.get(Report, report_id)
    if not r or r.business_id != a.business.id:
        raise ApiError(404, "We couldn't find this report.")
    _path(a.business.id, r).unlink(missing_ok=True)
    db.delete(r)
    db.commit()
    return {"deleted": True}
