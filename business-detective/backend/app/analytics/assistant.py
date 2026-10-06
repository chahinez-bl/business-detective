"""Grounded business analyst. Answers are assembled ONLY from the stored analytical results (facts); a language model may
rephrase them but is rejected if it introduces any number that is not in the facts."""
import re

import httpx

from ..config import get_settings

NA = "I don't have enough data to answer that reliably."
_num = re.compile(r"\d[\d,\.]*")


def _m(x, cur): return f"{x:,.0f} {cur}"


def facts_for(question: str, a: dict, cur: str) -> str | None:
    q = question.lower()
    ins = a.get("insights", [])
    rc = a.get("root_cause")
    if any(w in q for w in ["stock", "restock", "run out", "inventory"]):
        s = sorted([x for x in a.get("inventory", []) if x["days_left"] is not None], key=lambda x: x["days_left"])[:3]
        return "Restock first: " + "; ".join((f"{x['product']} (out of stock now, risk {x['risk'].title()})" if x["stock"] <= 0 else f"{x['product']} ({x['stock']:.0f} units, {x['range']} left, risk {x['risk'].title()})") for x in s) + ". Estimates assume no delivery is already on the way." if s else None
    if any(w in q for w in ["unusual", "anomal", "strange", "odd"]):
        x = [i for i in ins if i["kind"] in ("anomaly", "recent_shift")]
        return "What's unusual: " + " ".join(f"[{i['severity']}] {i['title']} — {i['what']}" for i in x[:3]) if x else "No unusual sales days were detected in your data."
    if any(w in q for w in ["why", "drop", "decrease", "declin", "fell", "revenue", "sales change", "changed", "change"]) and "stock" not in q and "supplier" not in q:
        if not rc:
            return None
        s = f"Revenue over the last {rc['window_days']} days changed {rc['change_pct']:+.1f}% ({_m(rc['revenue_previous'], cur)} → {_m(rc['revenue_current'], cur)})."
        if rc["contributors"]:
            s += " Biggest movers: " + "; ".join(f"{c['name']} ({c['delta']:+,.0f} {cur})" for c in rc["contributors"][:3]) + ". These show where the change is concentrated; they are possible contributing factors, not proven causes."
        return s
    if any(w in q for w in ["perform", "bad", "worst", "weak", "declining product"]) and not any(w in q for w in ["profit", "stock"]):
        x = [i for i in ins if i["kind"] == "trend" and i["category"] == "Risk"]
        return "Products with declining sales: " + "; ".join(i["title"].split(": ")[1] + f" ({i['details']['deviation']:+.0f}%)" for i in x[:5]) if x else ("No product shows a statistically clear decline." if a.get("products") else None)
    if any(w in q for w in ["profit", "margin", "hurting"]):
        p = [x for x in a.get("products", []) if x.get("margin_pct") is not None]
        if not p:
            return None
        low = sorted(p, key=lambda x: x["margin_pct"])[:3]
        return "Lowest-margin products: " + "; ".join(f"{x['product']} ({x['margin_pct']:.1f}%)" for x in low) + "."
    if "supplier" in q:
        d = sorted(a.get("supplier_drift", []), key=lambda x: -x["cost_change_pct"])[:3]
        return "Largest supplier cost changes: " + "; ".join(f"{x['supplier']} / {x['product']} ({x['cost_change_pct']:+.1f}%)" for x in d) if d else None
    if "customer" in q:
        cu = a.get("customers")
        if not cu: return None
        s = f"You have {cu['total']} customers; the top customer is {cu['top1_share_pct']:.0f}% of revenue."
        if cu.get("lost") is not None: s += f" {cu['lost']} customer(s) from the previous {cu['window_days']} days did not return."
        return s
    if any(w in q for w in ["prior", "first", "today", "should i", "attention", "do next", "investigate"]):
        top = ins[:3]
        return "Top priorities: " + " ".join(f"{n}. [{i['severity']}] {i['title']} — {i['impact_text']}" for n, i in enumerate(top, 1)) if top else "No significant findings right now."
    if any(w in q for w in ["forecast", "next", "expect", "predict"]):
        f = a.get("forecast", {})
        if not f.get("available"): return f.get("message")
        tot = sum(p["value"] for p in f["forecast"])
        return f"Expected revenue for the next {len(f['forecast'])} days: about {_m(tot, cur)}. {f['quality_note']} This is an estimate."
    return None


def _nums(t): return {n.rstrip(".,").replace(",", "") for n in _num.findall(t)}


def external_rephrase(question: str, facts: str) -> str | None:
    s = get_settings()
    if s.ai_provider != "openai_compatible" or not (s.ai_api_url and s.ai_api_key and s.ai_model):
        return None
    try:
        r = httpx.post(s.ai_api_url, timeout=20, headers={"Authorization": f"Bearer {s.ai_api_key}"}, json={"model": s.ai_model, "messages": [
            {"role": "system", "content": "Rephrase the FACTS as a short, clear answer for a business owner. Use only the numbers in FACTS. Never add numbers or claims."},
            {"role": "user", "content": f"QUESTION: {question}\nFACTS: {facts}"}]})
        text = r.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return None
    return text if _nums(text) <= _nums(facts) else None      # reject any invented number


def answer(question: str, a: dict, cur: str) -> dict:
    facts = facts_for(question, a, cur)
    if not facts:
        return dict(answer=NA + " Try asking about revenue changes, what's unusual, profit, suppliers, stock or priorities.", grounded=True, source="none")
    ext = external_rephrase(question, facts)
    return dict(answer=ext or facts, grounded=True, source="external_ai" if ext else "analytics")
