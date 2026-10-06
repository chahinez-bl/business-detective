import numpy as np
import pandas as pd
import pytest

from app.analytics import demo, engine
from app.analytics.mapping import detect_mapping
from app.analytics.quality import prepare, to_number
from app.analytics.simulator import SimulationError, simulate
from . import synthetic as syn


@pytest.fixture(scope="module")
def nova(): return engine.analyze(demo.generate())
def kinds(a, k): return " | ".join(i["title"] for i in a["insights"] if i["kind"] == k)


# --- existing prototype behaviours that must still hold
def test_nova_trends(nova): assert "Detergent" in kinds(nova, "trend") and "Energy Drink" in kinds(nova, "trend")
def test_nova_stockout_supplier_returns(nova): assert kinds(nova, "stockout") and "Premium Coffee" in kinds(nova, "supplier") and "Chocolate" in kinds(nova, "returns")
def test_nova_anomaly(nova): assert kinds(nova, "anomaly")
def test_nova_core(nova):
    assert nova["inventory"] and nova["profitability"]["margin_pct"] > 0 and nova["forecast"]["available"] and len(nova["forecast"]["forecast"]) == 14 and 0 <= nova["health"]["overall"] <= 100 and nova["leaks"]
def test_nova_customers_unavailable(nova):
    assert not nova["capabilities"]["customers"]["available"] and nova["customers"] is None
    assert "does not contain the required information" in nova["capabilities"]["customers"]["reason"]


# --- number / date parsing
@pytest.mark.parametrize("raw,exp", [("1,234.50", 1234.5), ("1.234,50", 1234.5), ("1 234,5", 1234.5), ("12 000 DA", 12000), ("(15)", -15), (1500, 1500), ("1,000", 1000), ("€ 12.5", 12.5)])
def test_to_number(raw, exp): assert to_number(raw) == exp
@pytest.mark.parametrize("raw", ["abc", "", None, "12abc34", float("nan")])
def test_to_number_invalid(raw): assert np.isnan(to_number(raw))


# --- mapping across different structures
def test_mapping_datasets():
    assert detect_mapping(syn.dataset_a()) == {"date": "Date", "product": "Product", "revenue": "Revenue", "quantity": "Quantity"}
    assert detect_mapping(syn.dataset_b()) == {"date": "TransactionDate", "product": "Article", "revenue": "CA", "quantity": "Qty", "stock": "Stock"}
    m = detect_mapping(syn.dataset_c())
    assert m["date"] == "OrderDate" and m["product"] == "ItemName" and m["revenue"] == "SalesAmount" and m["quantity"] == "Units" and m["customer"] == "Customer" and m["cost"] == "UnitCost" and m["order_id"] == "OrderNo"
def test_mapping_french():
    m = detect_mapping(pd.DataFrame(columns=["Produit", "Quantité", "Prix de vente", "Coût", "Fournisseur", "Date"]))
    assert m == {"product": "Produit", "quantity": "Quantité", "price": "Prix de vente", "cost": "Coût", "supplier": "Fournisseur", "date": "Date"}


# --- the engine adapts to each dataset (nothing is hardcoded to Nova Market)
def test_dataset_a_sales_only_adapts():
    a = engine.analyze(syn.dataset_a())
    caps = {k: v["available"] for k, v in a["capabilities"].items()}
    assert caps["sales"] and caps["products"] and caps["anomalies"] and caps["forecast"] and not caps["inventory"] and not caps["profitability"] and not caps["customers"] and not caps["suppliers"]
    assert a["inventory"] == [] and a["profitability"] is None and a["customers"] is None
    assert any("Alpha" in i["title"] for i in a["insights"] if i["kind"] == "trend"), "planted Alpha decline should be found"
    assert any(i["kind"] in ("anomaly", "rootcause", "recent_shift") for i in a["insights"])
    assert all(i["impact_amount"] is None or i["impact_amount"] >= 0 for i in a["insights"])
    assert not any(i["kind"] in ("inventory", "margin", "supplier") for i in a["insights"])

def test_dataset_b_inventory_french_format():
    a = engine.analyze(syn.dataset_b())
    assert a["capabilities"]["inventory"]["available"] and not a["capabilities"]["profitability"]["available"]
    cafe = next(r for r in a["inventory"] if r["product"] == "Café")
    assert cafe["risk"] in ("HIGH", "MEDIUM") or cafe["stockout_days"] > 0
    assert a["kpis"]["revenue"] > 0 and a["quality"]["date_range"]["days"] == 90        # dd/mm/yyyy read correctly, spaces in "1 234" amounts parsed

def test_dataset_c_customers_profit_contribution():
    a = engine.analyze(syn.dataset_c(), currency="EUR")
    assert a["capabilities"]["customers"]["available"] and a["capabilities"]["profitability"]["available"]
    assert a["customers"]["lost"] > 0 and any(i["kind"] == "customers_lost" for i in a["insights"])
    lamp = next(p for p in a["products"] if p["product"] == "Lamp")
    assert lamp["margin_pct"] < 0 and any(i["kind"] == "margin" and "Lamp" in i["title"] for i in a["insights"])
    assert all("EUR" in i["impact_text"] for i in a["insights"] if i["impact_amount"])           # currency is configurable, not hardcoded
    assert "DA" not in " ".join(i["impact_text"] for i in a["insights"]).replace("DATA", "")

def test_every_insight_has_what_why_impact_evidence_action():
    for df in (syn.dataset_a(), syn.dataset_b(), syn.dataset_c(), demo.generate()):
        for i in engine.analyze(df)["insights"]:
            assert i["what"] and i["why"] and i["impact_text"] and i["evidence"] and i["action"] and i["severity"] in ("Low", "Medium", "High", "Critical")
            assert i["recommendation"]["action"]

def test_contribution_identifies_the_planted_driver():
    a = engine.analyze(syn.dataset_a())
    rc = a["root_cause"]
    assert rc["change_pct"] < 0 and rc["contributors"][0]["name"] == "Alpha"

def test_insufficient_history_is_explained_not_faked():
    df = syn.dataset_a(days=10)
    a = engine.analyze(df)
    assert not a["forecast"]["available"] and "28 days" in a["forecast"]["message"]
    assert not a["capabilities"]["anomalies"]["available"] and a["root_cause"] is None and a["health"]["overall"] is None
    assert a["health"]["note"] == "Not enough data to calculate this metric."

def test_forecast_is_honest_about_quality():
    f = engine.analyze(syn.dataset_a(days=40))["forecast"]
    assert f["available"] and f["quality"] == "limited" and "rough guide" in f["quality_note"]

def test_no_cost_means_no_profit_invention():
    a = engine.analyze(syn.dataset_a())
    assert a["profitability"] is None and "profit" not in a["kpis"].get("period", {}) and all("margin_pct" not in p for p in a["products"])


# --- data quality
def test_quality_reports_everything_and_never_hides_rows():
    df = syn.dataset_a().iloc[:200].astype(object).copy()
    df.loc[0, "Date"] = "not-a-date"; df.loc[1, "Revenue"] = "abc"; df.loc[2, "Quantity"] = -5
    df = pd.concat([df, df.iloc[[10, 11]]])                       # two exact duplicates
    p = prepare(df, detect_mapping(df))
    r = p.report
    codes = {i["code"] for i in r["issues"]}
    assert {"invalid_dates", "invalid_revenue", "duplicates", "negative_values"} <= codes
    assert r["rows_received"] == 202 and r["duplicates_removed"] == 2 and r["rows_rejected"] == 3 and r["rows_accepted"] == 197
    assert r["score"] < 100 and r["can_analyze"]
    assert all(i["message"] and "Traceback" not in i["message"] for i in r["issues"])

def test_missing_required_columns_blocks_with_friendly_message():
    p = prepare(pd.DataFrame({"Name": ["a", "b"], "Notes": ["x", "y"]}), {"product": "Name"})
    assert p.df is None and not p.report["can_analyze"]
    msgs = " ".join(i["message"] for i in p.report["issues"])
    assert "date column" in msgs and "revenue column" in msgs and "KeyError" not in msgs

def test_revenue_from_quantity_times_price():
    df = syn.dataset_a().rename(columns={"Revenue": "Total"}).assign(Price=lambda d: 100)
    df = df.drop(columns=["Total"])
    p = prepare(df, {"date": "Date", "product": "Product", "quantity": "Quantity", "price": "Price"})
    assert p.df is not None and abs(p.df.revenue.sum() - df.Quantity.sum() * 100) < 1e-6

def test_mostly_garbage_is_rejected():
    df = pd.DataFrame({"d": ["x"] * 20, "amount": ["y"] * 20})
    p = prepare(df, {"date": "d", "revenue": "amount"})
    assert p.df is None and not p.report["can_analyze"]


# --- simulator
def test_simulator_math_and_labels():
    a = engine.analyze(syn.dataset_c())
    r = simulate(a["products"], a["kpis"]["days"], None, 10, 0, 0, None)
    rev = next(x for x in r["rows"] if x["metric"].startswith("Revenue"))
    assert abs(rev["simulated"] / rev["current"] - 1.10) < 1e-9 and "SIMULATION" in r["label"]
    r2 = simulate(a["products"], a["kpis"]["days"], "Chair", 10, 0, 0, -1.0)           # with an explicit elasticity assumption
    assert r2["assumptions"]["effective_volume_pct"] == -10
def test_simulator_rejects_bad_input_and_missing_data():
    a = engine.analyze(syn.dataset_a())
    with pytest.raises(SimulationError): simulate(a["products"], 90, "Nope", 5, 0, 0, None)
    with pytest.raises(SimulationError): simulate(a["products"], 90, None, -500, 0, 0, None)
    r = simulate(a["products"], 90, None, 5, 0, 0, None)
    assert "note" in r and not any("profit" in x["metric"].lower() for x in r["rows"])     # no cost data -> no profit simulated


def test_product_already_out_of_stock_is_flagged_even_without_recent_sales():
    a = engine.analyze(syn.dataset_b())
    cafe = next(r for r in a["inventory"] if r["product"] == "Café")
    assert cafe["stock"] == 0 and cafe["days_left"] == 0 and cafe["risk"] == "HIGH"
    assert any(i["kind"] == "inventory" and "Café" in i["title"] and "out of stock" in i["what"] for i in a["insights"])
