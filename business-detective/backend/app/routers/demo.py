"""Public demo endpoints. Fictional 'Nova Market' data, computed in memory — never stored in, or mixed with, any customer workspace."""
from fastapi import APIRouter

from ..analytics import assistant
from ..analytics.simulator import SimulationError, simulate
from ..errors import ApiError
from ..schemas import AskIn, SimulateIn
from ..services.workspace import demo_bundle

router = APIRouter(prefix="/demo", tags=["demo"])


@router.get("/workspace")
def workspace():
    return demo_bundle()[0]


@router.post("/ask")
def ask(body: AskIn):
    b, r = demo_bundle()
    return assistant.answer(body.question, r, "DZD")


@router.post("/simulate")
def sim(body: SimulateIn):
    b, _ = demo_bundle()
    try:
        return simulate(b["products"], b["kpis"]["days"], body.product, body.price_pct, body.cost_pct, body.volume_pct, body.elasticity)
    except SimulationError as e:
        raise ApiError(422, str(e))
