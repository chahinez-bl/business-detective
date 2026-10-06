"""Synthetic customer datasets with deliberately DIFFERENT structures, to prove the product is not tied to Nova Market."""
import io
from datetime import date, timedelta

import numpy as np
import pandas as pd

END = date.today() - timedelta(days=2)


def dataset_a(days=90, seed=1) -> pd.DataFrame:
    """Date / Product / Revenue / Quantity. 'Alpha' collapses in the last 21 days; one very bad day."""
    r = np.random.default_rng(seed)
    rows = []
    prices = {"Alpha": 1000, "Beta": 500, "Gamma": 300, "Delta": 800, "Epsilon": 150}
    base = {"Alpha": 12, "Beta": 15, "Gamma": 20, "Delta": 8, "Epsilon": 25}
    for d in range(days):
        day = END - timedelta(days=days - 1 - d)
        for p, pr in prices.items():
            m = 1.3 if day.weekday() >= 4 else 1.0
            if p == "Alpha" and d >= days - 21:
                m *= 0.4
            q = int(r.poisson(base[p] * m))
            if d == days - 10 and p != "Epsilon":
                q = 0
            rows.append({"Date": day.isoformat(), "Product": p, "Revenue": q * pr, "Quantity": q})
    return pd.DataFrame(rows)


def dataset_b(days=90, seed=2) -> pd.DataFrame:
    """TransactionDate (dd/mm/yyyy) / Article / CA / Qty / Stock. 'Café' runs out; French headers; accents."""
    r = np.random.default_rng(seed)
    rows = []
    stock = {"Café": 60, "Thé": 400, "Sucre": 500}
    price = {"Café": 700, "Thé": 250, "Sucre": 120}
    for d in range(days):
        day = END - timedelta(days=days - 1 - d)
        for a in stock:
            demand = int(r.poisson({"Café": 9, "Thé": 14, "Sucre": 20}[a]))
            sold = min(demand, stock[a])
            stock[a] -= sold
            if a != "Café" and stock[a] < 100:
                stock[a] += 400
            rows.append({"TransactionDate": day.strftime("%d/%m/%Y"), "Article": a, "CA": f"{sold * price[a]:,}".replace(",", " "), "Qty": sold, "Stock": stock[a]})
    return pd.DataFrame(rows)


def dataset_c(days=120, seed=3) -> pd.DataFrame:
    """OrderDate / ItemName / SalesAmount / Units / Customer / Category / UnitCost. A handful of customers disappear in the last 30 days."""
    r = np.random.default_rng(seed)
    customers = [f"C{i:02d}" for i in range(1, 31)]
    items = {"Chair": (4000, 2500, "Furniture"), "Desk": (12000, 8000, "Furniture"), "Lamp": (1500, 1600, "Lighting")}   # Lamp sells BELOW cost
    rows, oid = [], 0
    for d in range(days):
        day = END - timedelta(days=days - 1 - d)
        for _ in range(int(r.integers(3, 8))):
            pool = customers[:20] if d >= days - 30 else customers
            c, it = pool[int(r.integers(0, len(pool)))], list(items)[int(r.integers(0, 3))]
            u = int(r.integers(1, 4))
            oid += 1
            rows.append({"OrderDate": day, "OrderNo": oid, "ItemName": it, "SalesAmount": u * items[it][0], "Units": u, "Customer": c, "Category": items[it][2], "UnitCost": items[it][1]})
    return pd.DataFrame(rows)


def to_csv_bytes(df: pd.DataFrame, sep=",", encoding="utf-8") -> bytes:
    return df.to_csv(index=False, sep=sep).encode(encoding)


def to_xlsx_bytes(df: pd.DataFrame) -> bytes:
    b = io.BytesIO()
    df.to_excel(b, index=False, engine="openpyxl")
    return b.getvalue()
