from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..analytics import assistant
from ..analytics.simulator import SimulationError, simulate
from ..database import get_db
from ..deps import Access, business_access
from ..errors import ApiError
from ..models import Insight
from ..schemas import AskIn, SimulateIn
from ..services.workspace import customer_bundle, latest_analysis

router = APIRouter(prefix="/businesses/{business_id}", tags=["workspace"])


def _bundle(a: Access, db: Session) -> dict:
    return customer_bundle(db, a.business, a.role)


def _need(b: dict) -> dict:
    if not b.get("has_data"):
        raise ApiError(404, "No analysis yet. Upload your data to get started.")
    return b


@router.get("/workspace")
def workspace(a: Access = Depends(business_access), db: Session = Depends(get_db)):
    return _bundle(a, db)


@router.get("/overview")
def overview(a: Access = Depends(business_access), db: Session = Depends(get_db)):
    b = _need(_bundle(a, db))
    return dict(business=b["business"], kpis=b["kpis"], health=b["health"], capabilities=b["capabilities"], **b["overview"])


@router.get("/monitoring")
def monitoring(a: Access = Depends(business_access), db: Session = Depends(get_db)):
    return _need(_bundle(a, db))["monitoring"]


@router.get("/insights")
def insights(area: str | None = None, severity: str | None = None, a: Access = Depends(business_access), db: Session = Depends(get_db)):
    rows = _need(_bundle(a, db))["insights"]
    return [i for i in rows if (not area or i["area"] == area) and (not severity or i["severity"] == severity)]


@router.get("/insights/{insight_id}")
def insight(insight_id: int, a: Access = Depends(business_access), db: Session = Depends(get_db)):
    for i in _need(_bundle(a, db))["insights"]:
        if i["id"] == insight_id:
            return i
    raise ApiError(404, "We couldn't find this insight.")


@router.get("/recommendations")
def recommendations(a: Access = Depends(business_access), db: Session = Depends(get_db)):
    return _need(_bundle(a, db))["recommendations"]


@router.get("/decision-center")
def decision_center(a: Access = Depends(business_access), db: Session = Depends(get_db)):
    return _need(_bundle(a, db))["decision"]


@router.post("/simulate")
def run_simulation(body: SimulateIn, a: Access = Depends(business_access), db: Session = Depends(get_db)):
    b = _need(_bundle(a, db))
    try:
        return simulate(b["products"] or [], b["kpis"]["days"], body.product, body.price_pct, body.cost_pct, body.volume_pct, body.elasticity)
    except SimulationError as e:
        raise ApiError(422, str(e))


@router.post("/ask")
def ask(body: AskIn, a: Access = Depends(business_access), db: Session = Depends(get_db)):
    b = _need(_bundle(a, db))
    b = dict(b, insights=b["insights"])
    return assistant.answer(body.question, b, b["currency"])
