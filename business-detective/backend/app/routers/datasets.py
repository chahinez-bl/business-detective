import json

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from ..analytics import engine
from ..analytics.mapping import FIELDS, MappingError, check_mapping, detect_mapping
from ..analytics.quality import prepare
from ..database import get_db
from ..deps import Access, business_access
from ..errors import ApiError
from ..models import Action, Analysis, Dataset
from ..schemas import MappingIn
from ..services import ingest
from ..services.util import sanitize
from ..services.workspace import persist_analysis

router = APIRouter(prefix="/businesses/{business_id}/datasets", tags=["datasets"])


def _ds(db: Session, a: Access, dataset_id: int) -> Dataset:
    d = db.get(Dataset, dataset_id)
    if not d or d.business_id != a.business.id:
        raise ApiError(404, "We couldn't find this dataset.")
    return d


def _out(d: Dataset) -> dict:
    return dict(id=d.id, filename=d.filename, file_type=d.file_type, size_bytes=d.size_bytes, status=d.status, row_count=d.row_count, mapping=d.mapping,
                quality_score=(d.quality or {}).get("score"), error=d.error, created_at=d.created_at.isoformat())


def _frame(a: Access, d: Dataset):
    try:
        return ingest.load_frame(ingest.file_path(a.business.id, d.stored_name), d.file_type)
    except FileNotFoundError:
        raise ApiError(410, "The original file is no longer available. Please upload it again.")


def _prepare(a, d, mapping):
    df, meta = _frame(a, d)
    try:
        mp = check_mapping(mapping, [str(c) for c in df.columns])
    except MappingError as e:
        raise ApiError(422, str(e))
    p = prepare(df, mp)
    if meta.get("skipped_lines"):
        p.report["issues"].append(dict(severity="warning", code="bad_lines", message=f"{meta['skipped_lines']:,} line(s) had the wrong number of columns and were skipped.",
                                       consequence="Those lines are not part of the analysis.", fix="Check for stray separators or unquoted commas in text fields."))
    if meta.get("sheet"):
        p.report["passed"].append(f"Read sheet “{meta['sheet']}”")
    return df, mp, p


@router.post("/upload", status_code=201)
def upload(file: UploadFile = File(...), a: Access = Depends(business_access), db: Session = Depends(get_db)):
    a.need_write()
    info = ingest.save_upload(file, a.business.id)
    path = ingest.file_path(a.business.id, info["stored_name"])
    try:
        df, meta = ingest.load_frame(path, info["file_type"])
    except Exception:
        path.unlink(missing_ok=True)
        raise
    mapping = detect_mapping(df)
    d = Dataset(business_id=a.business.id, uploaded_by=a.user.id, columns=[str(c) for c in df.columns], row_count=len(df), mapping=mapping, **info)
    db.add(d)
    db.commit()
    preview = json.loads(df.head(10).to_json(orient="records", date_format="iso", default_handler=str))
    return sanitize(dict(dataset=_out(d), columns=d.columns, preview=preview, total_rows=len(df), suggested_mapping=mapping,
                         fields=[dict(key=k, label=v[0], help=v[1]) for k, v in FIELDS.items()], sheet=meta.get("sheet")))


@router.get("")
def list_datasets(a: Access = Depends(business_access), db: Session = Depends(get_db)):
    rows = db.scalars(select(Dataset).where(Dataset.business_id == a.business.id).order_by(Dataset.id.desc())).all()
    return [_out(d) for d in rows]


@router.get("/{dataset_id}")
def get_dataset(dataset_id: int, a: Access = Depends(business_access), db: Session = Depends(get_db)):
    d = _ds(db, a, dataset_id)
    return dict(**_out(d), columns=d.columns, quality=d.quality)


@router.post("/{dataset_id}/validate")
def validate(dataset_id: int, body: MappingIn, a: Access = Depends(business_access), db: Session = Depends(get_db)):
    a.need_write()
    d = _ds(db, a, dataset_id)
    _, mp, p = _prepare(a, d, body.mapping)
    d.mapping, d.quality, d.status = mp, sanitize(p.report), "validated" if p.report["can_analyze"] else "uploaded"
    db.commit()
    return sanitize(p.report)


@router.post("/{dataset_id}/analyze")
def analyze(dataset_id: int, body: MappingIn, a: Access = Depends(business_access), db: Session = Depends(get_db)):
    a.need_write()
    d = _ds(db, a, dataset_id)
    _, mp, p = _prepare(a, d, body.mapping)
    d.mapping, d.quality = mp, sanitize(p.report)
    if p.df is None:
        d.status, d.error = "failed", "; ".join(i["message"] for i in p.report["issues"] if i["severity"] == "error")
        db.commit()
        raise ApiError(422, "We can't analyze this data yet: " + (d.error or "please check the column mapping."), quality=sanitize(p.report))
    try:
        result = engine.analyze_clean(p.df, a.business.currency)
    except Exception:
        import logging
        logging.getLogger("businessdetective").exception("analysis failed for dataset %s", d.id)   # no data values are logged
        d.status, d.error = "failed", "The analysis could not be completed."
        db.commit()
        raise ApiError(422, "The analysis could not be completed with this data. Try checking the column mapping, or contact support.")
    d.status, d.error = "analyzed", ""
    analysis = persist_analysis(db, a.business, d, result)
    return dict(analysis_id=analysis.id, dataset=_out(d), health=analysis.health_score)


@router.delete("/{dataset_id}")
def delete_dataset(dataset_id: int, a: Access = Depends(business_access), db: Session = Depends(get_db)):
    a.need_admin()
    d = _ds(db, a, dataset_id)
    ids = db.scalars(select(Analysis.id).where(Analysis.dataset_id == d.id)).all()
    if ids:
        db.execute(update(Action).where(Action.business_id == a.business.id).values(insight_id=None, recommendation_id=None))
    ingest.file_path(a.business.id, d.stored_name).unlink(missing_ok=True)
    db.delete(d)
    db.commit()
    return {"deleted": True}
