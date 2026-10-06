"""Persists analysis results and assembles the read-models (overview, monitoring, decision centre) the UI consumes."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..analytics.engine import AREAS
from ..models import Action, Analysis, Business, Dataset, Insight, Recommendation
from .util import sanitize

AREA_CAP = {"Sales": "sales", "Products": "products", "Inventory": "inventory", "Customers": "customers", "Suppliers": "suppliers", "Profitability": "profitability", "Returns": "returns"}
STATUS = {None: "Normal", "Low": "Attention", "Medium": "Warning", "High": "Critical", "Critical": "Critical"}
SEV_ORDER = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
INSIGHT_FIELDS = ["kind", "area", "category", "severity", "title", "what", "why", "impact_amount", "impact_text", "evidence", "action", "confidence", "priority_score", "detected_on", "details"]


def persist_analysis(db: Session, business: Business, dataset: Dataset, result: dict) -> Analysis:
    result = sanitize(result)
    insights = result.pop("insights")
    a = Analysis(business_id=business.id, dataset_id=dataset.id, currency=business.currency, health_score=result["health"]["overall"],
                 period_start=result["kpis"]["start"], period_end=result["kpis"]["end"], result=result)
    db.add(a)
    db.flush()
    for i in insights:
        d = {k: i.get(k) for k in INSIGHT_FIELDS}
        d["details"] = {**(d["details"] or {}), "impact_basis": i.get("impact_basis"), "impact_ratio": i.get("impact_ratio")}
        row = Insight(analysis_id=a.id, business_id=business.id, **d)
        db.add(row)
        db.flush()
        r = i["recommendation"]
        db.add(Recommendation(analysis_id=a.id, business_id=business.id, insight_id=row.id, problem=r["problem"], evidence=r["evidence"], action=r["action"],
                              objective=r["objective"], priority=r["priority"], confidence=r["confidence"], impact_amount=i.get("impact_amount")))
    db.commit()
    return a


def latest_analysis(db: Session, business_id: int) -> Analysis | None:
    return db.scalar(select(Analysis).where(Analysis.business_id == business_id).order_by(Analysis.id.desc()).limit(1))


def insight_dict(i: Insight, rec_id: int | None = None, action: Action | None = None) -> dict:
    d = {k: getattr(i, k) for k in INSIGHT_FIELDS}
    d.update(id=i.id, recommendation_id=rec_id, action_item=dict(id=action.id, status=action.status) if action else None)
    return d


def rec_dict(r: Recommendation, title: str, area: str, action: Action | None = None) -> dict:
    return dict(id=r.id, insight_id=r.insight_id, title=title, area=area, problem=r.problem, evidence=r.evidence, action=r.action, objective=r.objective,
                priority=r.priority, confidence=r.confidence, impact_amount=r.impact_amount, action_item=dict(id=action.id, status=action.status) if action else None)


def monitoring_view(insights: list[dict], caps: dict, health: dict) -> dict:
    areas = []
    worst = None
    for area in AREAS:
        cap = caps.get(AREA_CAP[area], {})
        if not cap.get("available"):
            areas.append(dict(area=area, monitored=False, status=None, issues=0, message=cap.get("reason", "")))
            continue
        probs = [i for i in insights if i["area"] == area and i["category"] != "Opportunity"]
        top = max((i["severity"] for i in probs), key=lambda s: SEV_ORDER[s], default=None)
        st = STATUS[top]
        areas.append(dict(area=area, monitored=True, status=st, issues=len(probs), message=f"{len(probs)} issue(s) need attention" if probs else "Nothing unusual detected"))
        if top and (worst is None or SEV_ORDER[top] > SEV_ORDER[worst]):
            worst = top
    alerts = [i for i in insights if i["category"] != "Opportunity"]
    return dict(status=STATUS[worst], health=health, areas=areas, alerts=alerts[:8], total_alerts=len(alerts),
                opportunities=[i for i in insights if i["category"] == "Opportunity"][:3],
                recent_events=sorted([i for i in insights if i.get("detected_on")], key=lambda i: i["detected_on"], reverse=True)[:6])


def decision_view(insights: list[dict]) -> dict:
    items = [i for i in insights if i["category"] != "Opportunity" and i["severity"] in ("Critical", "High", "Medium")][:10]
    groups = {s: [x for x in items if x["severity"] == s] for s in ("Critical", "High", "Medium")}
    return dict(groups=groups, count=len(items), opportunities=[i for i in insights if i["category"] == "Opportunity"][:2])


RESULT_KEYS = ["currency", "kpis", "capabilities", "health", "root_cause", "products", "inventory", "suppliers", "supplier_drift", "customers", "returns",
               "profitability", "forecast", "daily", "monthly", "weekday", "leaks"]


def build_bundle(mode: str, business: dict, dataset: dict | None, analysis_meta: dict, result: dict, insights: list[dict], recs: list[dict], quality: dict | None) -> dict:
    out = {k: result.get(k) for k in RESULT_KEYS}
    attention = [i for i in insights if i["category"] != "Opportunity"]
    out.update(has_data=True, mode=mode, business=business, dataset=dataset, analysis=analysis_meta, quality=quality, insights=insights, recommendations=recs,
               overview=dict(attention=attention[:4], opportunities=[i for i in insights if i["category"] == "Opportunity"][:2]),
               monitoring=monitoring_view(insights, result["capabilities"], result["health"]), decision=decision_view(insights))
    return out


def customer_bundle(db: Session, business: Business, role: str) -> dict:
    a = latest_analysis(db, business.id)
    binfo = dict(id=business.id, name=business.name, industry=business.industry, currency=business.currency, role=role)
    if not a:
        return dict(has_data=False, mode="customer", business=binfo)
    ds = db.get(Dataset, a.dataset_id)
    acts = db.scalars(select(Action).where(Action.business_id == business.id, Action.status != "dismissed", Action.insight_id.is_not(None)).order_by(Action.id)).all()
    by_ins = {x.insight_id: x for x in acts}
    ins_rows = db.scalars(select(Insight).where(Insight.analysis_id == a.id).order_by(Insight.priority_score.desc())).all()
    rec_by = {r.insight_id: r for r in db.scalars(select(Recommendation).where(Recommendation.analysis_id == a.id)).all()}
    insights = [insight_dict(i, rec_by[i.id].id if i.id in rec_by else None, by_ins.get(i.id)) for i in ins_rows]
    for n, i in enumerate(insights, 1):
        i["rank"] = n
    recs = [rec_dict(rec_by[i.id], i.title, i.area, by_ins.get(i.id)) for i in ins_rows if i.id in rec_by]
    meta = dict(id=a.id, created_at=a.created_at.isoformat(), period_start=a.period_start, period_end=a.period_end, currency=a.currency,
                stale_currency=a.currency != business.currency)
    dsi = dict(id=ds.id, filename=ds.filename, rows=ds.row_count) if ds else None
    return build_bundle("customer", binfo, dsi, meta, a.result, insights, recs, ds.quality if ds else None)


_demo_cache: dict = {}


def demo_bundle() -> tuple[dict, dict]:
    """Nova Market is fictional demo data. Computed in memory with the same engine; never written to any customer workspace."""
    if not _demo_cache:
        from ..analytics import demo, engine
        from ..analytics.mapping import detect_mapping
        from ..analytics.quality import prepare
        raw = demo.generate()
        p = prepare(raw, detect_mapping(raw))
        r = sanitize(engine.analyze_clean(p.df, "DZD"))
        insights = r.pop("insights")
        recs = []
        for n, i in enumerate(insights, 1):
            i.update(id=n, recommendation_id=n, action_item=None, rank=n)
            rc = i["recommendation"]
            recs.append(dict(id=n, insight_id=n, title=i["title"], area=i["area"], problem=rc["problem"], evidence=rc["evidence"], action=rc["action"], objective=rc["objective"],
                             priority=rc["priority"], confidence=rc["confidence"], impact_amount=i.get("impact_amount"), action_item=None))
        b = build_bundle("demo", dict(id=0, name="Nova Market (demo)", industry="Retail", currency="DZD", role="viewer"), dict(id=0, filename="nova_market.csv", rows=len(raw)),
                         dict(id=0, created_at=None, period_start=r["kpis"]["start"], period_end=r["kpis"]["end"], currency="DZD", stale_currency=False), r, insights, recs, p.report)
        _demo_cache.update(bundle=b, result=dict(r, insights=insights))
    return _demo_cache["bundle"], _demo_cache["result"]
