"""What-if simulator. Pure arithmetic on figures computed from the customer's own data; results are ESTIMATES, never actuals."""
import math


class SimulationError(ValueError):
    pass


def simulate(products: list[dict], days: int, product: str | None, price_pct: float, cost_pct: float, volume_pct: float, elasticity: float | None) -> dict:
    """30-day baseline = average daily units x 30 at the observed average price/cost.

    volume change = volume_pct (direct scenario) + elasticity x price_pct (only if the user supplies an elasticity assumption).
    """
    for n, v in (("price", price_pct), ("cost", cost_pct), ("volume", volume_pct)):
        if not isinstance(v, (int, float)) or math.isnan(v) or v < -100 or v > 1000:
            raise SimulationError(f"The {n} change must be a number between -100 and 1000 percent.")
    rows = [p for p in products if p.get("units") and p.get("avg_price")]
    if product:
        rows = [p for p in rows if p["product"] == product]
        if not rows:
            raise SimulationError("We don't have enough data about this product to simulate it.")
    if not rows:
        raise SimulationError("Simulations need quantity and revenue data, which this dataset does not contain.")
    vol_pct = volume_pct + (elasticity * price_pct if elasticity is not None else 0.0)
    cost_known = all(p.get("avg_cost") is not None for p in rows) and cost_pct is not None
    base_units = sum(p["units"] / days * 30 for p in rows)
    base_rev = sum(p["units"] / days * 30 * p["avg_price"] for p in rows)
    sim_rev = sum(p["units"] / days * 30 * max(0.0, 1 + vol_pct / 100) * p["avg_price"] * (1 + price_pct / 100) for p in rows)
    out = dict(label="SIMULATION — estimated, not actual results", scope=product or "All products", assumptions=dict(price_pct=price_pct, cost_pct=cost_pct, volume_pct=volume_pct, elasticity=elasticity, effective_volume_pct=vol_pct),
               rows=[dict(metric="Units (30 days)", current=base_units, simulated=base_units * max(0.0, 1 + vol_pct / 100)),
                     dict(metric="Revenue (30 days)", current=base_rev, simulated=sim_rev)])
    if cost_known:
        base_cost = sum(p["units"] / days * 30 * p["avg_cost"] for p in rows)
        sim_cost = sum(p["units"] / days * 30 * max(0.0, 1 + vol_pct / 100) * p["avg_cost"] * (1 + cost_pct / 100) for p in rows)
        out["rows"] += [dict(metric="Cost (30 days)", current=base_cost, simulated=sim_cost), dict(metric="Gross profit (30 days)", current=base_rev - base_cost, simulated=sim_rev - sim_cost)]
        out["margin"] = dict(current=(base_rev - base_cost) / base_rev * 100 if base_rev else None, simulated=(sim_rev - sim_cost) / sim_rev * 100 if sim_rev else None)
    else:
        out["note"] = "Profit is not simulated because purchase cost is not available for every product."
    for r in out["rows"]:
        r["delta"] = r["simulated"] - r["current"]
    return out
