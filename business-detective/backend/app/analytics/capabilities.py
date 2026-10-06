"""Which analyses can honestly be produced from the data at hand. Drives validation, the engine, monitoring and the UI."""
import pandas as pd

MIN_DAYS = 28   # minimum history for anomaly detection, contribution analysis and forecasting
LABELS = {"date": "date", "revenue": "revenue", "product": "product", "quantity": "quantity sold", "cost": "purchase cost", "stock": "stock level",
          "supplier": "supplier", "customer": "customer", "returned": "returned quantity", "category": "category", "price": "unit price"}

# key -> (customer-facing name, required fields, needs history?)
SPEC = {
    "sales": ("Sales trends", ["date", "revenue"], False),
    "anomalies": ("What's unusual", ["date", "revenue"], True),
    "contribution": ("What's driving the change", ["revenue"], True),
    "products": ("Products", ["product"], False),
    "inventory": ("Inventory risk", ["product", "stock", "quantity"], False),
    "suppliers": ("Suppliers", ["supplier"], False),
    "profitability": ("Profitability", ["cost", "quantity"], False),
    "customers": ("Customers", ["customer"], False),
    "returns": ("Returns", ["returned", "quantity"], False),
    "forecast": ("What may happen next", ["date", "revenue"], True),
}


def has(df: pd.DataFrame, field: str, min_share: float = 0.3) -> bool:
    return field in df.columns and len(df) > 0 and df[field].notna().mean() >= min_share


def history_days(df: pd.DataFrame) -> int:
    return int((df["date"].max() - df["date"].min()).days + 1) if len(df) else 0


def capabilities(df: pd.DataFrame) -> dict:
    days = history_days(df)
    out = {}
    for key, (label, needs, hist) in SPEC.items():
        miss = [LABELS.get(n, n) for n in needs if n != "revenue" and not has(df, n)] + (["revenue"] if "revenue" in needs and not has(df, "revenue") else [])
        reason = ""
        if miss:
            reason = "This analysis is unavailable because your dataset does not contain the required information: " + ", ".join(miss) + "."
        elif hist and days < MIN_DAYS:
            reason = f"This analysis needs at least {MIN_DAYS} days of history; your data covers {days} day(s)."
        elif key == "contribution" and not (has(df, "product") or has(df, "category")):
            reason = "This analysis is unavailable because your dataset does not contain the required information: product or category."
        out[key] = dict(label=label, available=not reason, reason=reason)
    return out
