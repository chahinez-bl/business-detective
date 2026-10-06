"""Explainable, capability-driven analytics engine.

Input : a cleaned DataFrame from quality.prepare() (canonical columns: date, revenue, [product, category, quantity, price, cost,
        stock, supplier, customer, returned, order_id, location]).
Output: plain dict (kpis, health, tables, insights...). Every number comes from the data; nothing is hardcoded to a dataset.
Costs are PER UNIT; profit = revenue - quantity x cost, computed only on rows where both are known.
"""
import numpy as np
import pandas as pd
from scipy import stats

from .capabilities import MIN_DAYS, capabilities, has, history_days

SEV = ["Low", "Medium", "High", "Critical"]
NO_IMPACT = "Financial impact cannot be reliably estimated from the available data."
AREAS = ["Sales", "Products", "Inventory", "Customers", "Suppliers", "Profitability", "Returns"]


def _f(x):
    try:
        if x is None or (isinstance(x, float) and np.isnan(x)) or pd.isna(x):
            return None
    except (TypeError, ValueError):
        pass
    return float(x)


def money(x, cur):
    return f"{x:,.0f} {cur}"


class Ctx:
    """Shared, derived views of the data plus helper formatters."""

    def __init__(self, df: pd.DataFrame, cur: str):
        self.df, self.cur = df, cur
        self.start, self.end = df.date.min(), df.date.max()
        self.days = history_days(df)
        self.caps = capabilities(df)
        self.daily = df.groupby("date").revenue.sum().reindex(pd.date_range(self.start, self.end), fill_value=0.0)
        self.total = float(df.revenue.sum())
        self.monthly_rev = self.total / max(self.days, 1) * 30
        self.window = 30 if self.days >= 60 else 14 if self.days >= MIN_DAYS else 0
        self.has_cost = has(df, "cost") and has(df, "quantity")
        if self.has_cost:
            k = df.cost.notna() & df.quantity.notna()
            self.cost_rows = k
            self.df = df.assign(profit=np.where(k, df.revenue - df.quantity * df.cost, np.nan))
        self.months = max(self.days / 30, 1)

    def m(self, x): return money(x, self.cur)

    def split(self, df=None, w=None):
        df = self.df if df is None else df
        w = w or self.window
        if not w or self.days < 2 * w:
            return None, None
        cut = self.end - pd.Timedelta(days=w)
        return df[df.date > cut], df[(df.date <= cut) & (df.date > cut - pd.Timedelta(days=w))]

    def product_available(self): return self.caps["products"]["available"]


def _ins(kind, area, category, title, what, why, evidence, action, *, impact=None, basis="per month", monthly=None, conf=0.7, date=None,
         floor=0, cap=3, urgency=0.0, details=None, objective=""):
    note = NO_IMPACT if impact is None else f"About {{amt}} {basis} (estimate based on your historical sales)."
    return dict(kind=kind, area=area, category=category, title=title, what=what, why=why, evidence=evidence, action=action, impact_amount=_f(impact),
                impact_basis=basis, impact_monthly=_f(monthly if monthly is not None else impact), confidence=float(conf),
                detected_on=date, floor=floor, cap=cap, urgency=urgency, details=details or {}, objective=objective)


# ---------------------------------------------------------------- sales
def sales_insights(c: Ctx):
    out, daily = [], c.daily
    if not c.caps["anomalies"]["available"]:
        return out
    base = daily.groupby(daily.index.dayofweek).transform("median")
    res = daily - base
    mad = np.median(np.abs(res - np.median(res)))
    sigma = 1.4826 * mad if mad > 0 else float(res.std())
    if sigma and not np.isnan(sigma):
        z = res / sigma
        recent = daily.index > c.end - pd.Timedelta(days=60)
        cand = z[(z.abs() > 3.5) & recent]
        prod_piv = None
        if c.product_available():
            top = c.df.groupby("product").revenue.sum().nlargest(200).index
            prod_piv = c.df[c.df["product"].isin(top)].pivot_table(index="date", columns="product", values="revenue", aggfunc="sum").reindex(daily.index, fill_value=0).fillna(0)
        picked = 0
        for d in cand.abs().sort_values(ascending=False).index:
            obs, bs = float(daily[d]), float(base[d])
            if bs <= 0 or abs(obs - bs) / bs < 0.20 or picked >= 3:
                continue
            picked += 1
            dev = (obs - bs) / bs * 100
            up = dev > 0
            factors, ev = [], [f"Revenue on {d.date()}: {c.m(obs)}", f"Typical for a {d.day_name()}: {c.m(bs)} ({dev:+.0f}%)"]
            if prod_piv is not None and len(prod_piv.columns):
                pb = prod_piv.groupby(prod_piv.index.dayofweek).transform("median")
                delta = (prod_piv.loc[d] - pb.loc[d]).sort_values(key=lambda s: -s.abs() if not up else -s)
                if len(delta) and abs(delta.iloc[0]) > 0:
                    p = delta.index[0]
                    factors.append(f"{p} sold {c.m(prod_piv.loc[d, p])} versus a usual {c.m(pb.loc[d, p])} on this weekday.")
            days_ago = (c.end - d).days
            out.append(_ins("anomaly", "Sales", "Opportunity" if up else "Anomaly",
                            f"Unusual sales {'spike' if up else 'drop'} on {d.date()}",
                            f"Revenue on {d.date()} was {abs(dev):.0f}% {'above' if up else 'below'} what is normal for a {d.day_name()}.",
                            "Large one-day swings can point to a stock problem, a promotion, an outage or a data entry error." if not up else "Worth understanding so it can be repeated.",
                            ev + factors, "Check what happened that day (opening hours, stock, promotions, data entry)." if not up else "Find out what drove the spike (promotion, event, large order) and whether it can be repeated.",
                            impact=0 if up else bs - obs, basis="on that day", monthly=0 if up else (bs - obs) / 4.3,
                            conf=min(0.95, 0.6 + abs(float(z[d])) / 30), date=str(d.date()), floor=0, cap=1 if up else 2, urgency=max(0, 1 - days_ago / 60),
                            details=dict(method="Compared with the median for the same weekday; flagged when far outside normal day-to-day variation (robust z-score).",
                                         metric="Daily revenue", observed=obs, baseline=bs, deviation=dev, z=float(z[d]), factors=factors)))
    # sustained last-7-days shift
    last7 = daily.iloc[-7:]
    exp7 = base.iloc[-7:]
    if len(daily) >= 35 and exp7.sum() > 0:
        chg = (last7.sum() - exp7.sum()) / exp7.sum() * 100
        if chg <= -20 or chg >= 30:
            streak = 0
            for o, b in zip(last7.values[::-1], exp7.values[::-1]):
                if o < b: streak += 1
                else: break
            up = chg > 0
            out.append(_ins("recent_shift", "Sales", "Opportunity" if up else "Anomaly", f"Sales over the last 7 days are {abs(chg):.0f}% {'above' if up else 'below'} normal",
                            f"Revenue for the last 7 days was {c.m(last7.sum())}, versus {c.m(exp7.sum())} expected from your usual weekday pattern.",
                            "A sustained gap (not just one odd day) usually has a business cause worth acting on early.",
                            [f"Last 7 days: {c.m(last7.sum())}", f"Expected: {c.m(exp7.sum())} ({chg:+.0f}%)"] + ([f"Revenue has been below its usual level for {streak} day(s) in a row."] if streak >= 3 and not up else []),
                            "Look at product availability, pricing and recent customer activity." if not up else "Make sure stock and staffing can sustain the higher demand.",
                            impact=0 if up else exp7.sum() - last7.sum(), basis="over the last 7 days", monthly=0 if up else (exp7.sum() - last7.sum()) * 30 / 7, conf=0.75, date=str(c.end.date()),
                            floor=1 if not up else 0, cap=1 if up else 3, urgency=1.0,
                            details=dict(method="Last 7 days compared with the median of the same weekdays across the whole history.", metric="7-day revenue",
                                         observed=float(last7.sum()), baseline=float(exp7.sum()), deviation=float(chg))))
    return out


def root_cause(c: Ctx):
    cur, prev = c.split()
    if cur is None or prev.empty or prev.revenue.sum() <= 0:
        return None, []
    ra, rb, w = float(cur.revenue.sum()), float(prev.revenue.sum()), c.window
    chg = (ra - rb) / rb * 100
    dim = "product" if c.product_available() else ("category" if has(c.df, "category") else None)
    contrib = []
    if dim:
        d = cur.groupby(dim).revenue.sum().sub(prev.groupby(dim).revenue.sum(), fill_value=0)
        tot = ra - rb
        for p, v in d.items():
            contrib.append(dict(name=str(p), delta=_f(v), share=_f(v / tot * 100) if abs(tot) > 1e-9 else None))
        contrib = sorted(contrib, key=lambda x: -abs(x["delta"]))[:5]
    rc = dict(window_days=w, revenue_current=ra, revenue_previous=rb, change_pct=chg, dimension=dim, contributors=contrib)
    if abs(chg) < 5:
        return rc, []
    down = chg < 0
    ev = [f"Last {w} days: {c.m(ra)}", f"Previous {w} days: {c.m(rb)} ({chg:+.1f}%)"]
    factors, why = [], "Changes of this size usually come from a few products, customers or availability problems."
    if contrib and contrib[0]["share"] is not None:
        top = contrib[0]
        if abs(top["share"]) > 100:
            why = f"{top['name']} alone changed by {top['delta']:+,.0f} {c.cur}, more than the whole net change; other products partly offset it. This shows where the change is concentrated; it does not prove the cause."
        else:
            why = f"{top['name']} accounts for {abs(top['share']):.0f}% of the change ({top['delta']:+,.0f} {c.cur}). This shows where the change is concentrated; it does not prove the cause."
        ev.append(f"Biggest mover: {top['name']} ({top['delta']:+,.0f} {c.cur})")
        if dim == "product":
            a, b = cur[cur["product"] == top["name"]], prev[prev["product"] == top["name"]]
            if has(c.df, "quantity") and b.quantity.sum() > 0 and a.quantity.sum() >= 0:
                uchg = (a.quantity.sum() - b.quantity.sum()) / b.quantity.sum() * 100
                ev.append(f"{top['name']} units sold: {b.quantity.sum():,.0f} → {a.quantity.sum():,.0f} ({uchg:+.0f}%)")
            if has(c.df, "stock"):
                so = int(a.groupby("date").stock.min().le(0).sum())
                if so and down:
                    factors.append(f"Possible contributing factor: {top['name']} was out of stock on {so} day(s) in this period.")
    out = [_ins("rootcause", "Sales", "Anomaly" if down else "Opportunity", f"Revenue {'fell' if down else 'grew'} {abs(chg):.1f}% over the last {w} days",
                f"Revenue for the last {w} days was {c.m(ra)}, {abs(chg):.1f}% {'lower' if down else 'higher'} than the previous {w} days ({c.m(rb)}).", why, ev + factors,
                ("Start with the biggest contributor and check availability, pricing and recent sales activity." if down else "Check that stock and supply can sustain the growth.") if contrib else "Review sales by period to locate the change.",
                impact=(rb - ra) * 30 / w if down else 0, basis="per month", conf=0.8, date=str(c.end.date()), floor=1 if chg < -10 else 0, cap=3 if down else 1, urgency=0.9,
                details=dict(method=f"Last {w} days vs the {w} days before; contribution = change per {dim or 'n/a'}.", metric=f"{w}-day revenue", observed=ra, baseline=rb,
                             deviation=chg, contributors=contrib, factors=factors))]
    return rc, out


# ---------------------------------------------------------------- products
def weekly_product_revenue(c: Ctx):
    d = c.df[["date", "product", "revenue"]].copy()
    d["wk"] = d.date - pd.to_timedelta(d.date.dt.weekday, unit="D")
    wks = pd.date_range(c.start - pd.Timedelta(days=c.start.weekday()), c.end, freq="7D")
    wks = [w for w in wks if w >= c.start and w + pd.Timedelta(days=6) <= c.end]
    if len(wks) < 6:
        return None
    piv = d.pivot_table(index="wk", columns="product", values="revenue", aggfunc="sum").reindex(wks, fill_value=0).fillna(0)
    return piv


def product_table(c: Ctx):
    g = c.df.groupby("product")
    t = pd.DataFrame({"revenue": g.revenue.sum()})
    t["share_pct"] = t.revenue / c.total * 100
    if has(c.df, "quantity"):
        t["units"] = g.quantity.sum()
        t["avg_price"] = t.revenue / t.units.replace(0, np.nan)
        t["avg_daily_units"] = t.units / c.days
    if c.has_cost:
        k = c.df[c.cost_rows].groupby("product")
        rv, pf = k.revenue.sum(), k.profit.sum()
        t["profit"] = pf
        t["margin_pct"] = pf / rv.replace(0, np.nan) * 100
        t["avg_cost"] = k.cost.mean()
    if "category" in c.df:
        t["category"] = g.category.agg(lambda s: s.dropna().iloc[0] if s.notna().any() else None)
    return t.sort_values("revenue", ascending=False)


def product_level_shifts(c: Ctx, pt: pd.DataFrame, skip: set):
    """Abrupt product changes (not smooth trends): latest window vs the previous one."""
    cur, prev = c.split()
    if cur is None:
        return []
    ra, rb = cur.groupby("product").revenue.sum(), prev.groupby("product").revenue.sum()
    floor_ = 0.03 * c.monthly_rev * c.window / 30
    rows = []
    for p, b in rb.items():
        if p in skip or b < floor_:
            continue
        a = float(ra.get(p, 0.0))
        ch = (a - b) / b
        if ch <= -0.25 or ch >= 0.5:
            rows.append((p, a, float(b), ch))
    downs = sorted([r for r in rows if r[3] < 0], key=lambda r: r[1] - r[2])[:3]
    ups = sorted([r for r in rows if r[3] > 0], key=lambda r: -(r[1] - r[2]))[:1]
    out = []
    for p, a, b, ch in downs + ups:
        up = ch > 0
        w = c.window
        factors = []
        if has(c.df, "stock"):
            x = cur[cur["product"] == p]
            so = int(x.groupby("date").stock.min().le(0).sum())
            if so and not up:
                factors.append(f"Possible contributing factor: {p} was out of stock on {so} day(s) in this period.")
        if has(c.df, "quantity") and not up:
            ua, ub = cur[cur["product"] == p].quantity.sum(), prev[prev["product"] == p].quantity.sum()
            if ub > 0:
                factors.append(f"Units sold: {ub:,.0f} → {ua:,.0f} ({(ua - ub) / ub * 100:+.0f}%).")
        out.append(_ins("trend", "Products", "Opportunity" if up else "Risk", f"{'Rising demand' if up else 'Declining sales'}: {p}",
                        f"Revenue for {p} {'rose' if up else 'fell'} {abs(ch) * 100:.0f}% in the last {w} days compared with the {w} days before.",
                        "A sharp change in one product usually has a specific cause (availability, price, competition, promotion)." if not up else "Strong growth needs enough stock and supply to keep up.",
                        [f"Last {w} days: {c.m(a)}", f"Previous {w} days: {c.m(b)} ({ch * 100:+.0f}%)"] + factors,
                        "Investigate availability, pricing, placement and recent customer activity for this product." if not up else "Check stock cover and reorder size so growth is not lost to stockouts.",
                        impact=0 if up else (b - a) * 30 / w, basis="per month", conf=0.75, date=str(c.end.date()), floor=0, cap=1 if up else 3, urgency=0.7,
                        details=dict(method=f"Product revenue, last {w} days vs the {w} days before.", metric=f"{w}-day revenue", observed=a, baseline=b, deviation=ch * 100, product=p, factors=factors)))
    return out


def product_insights(c: Ctx, pt: pd.DataFrame):
    out = []
    piv = weekly_product_revenue(c)
    if piv is None:
        return product_level_shifts(c, pt, set())
    n = len(piv)
    cand = []
    for p in piv.columns:
        y = piv[p].values
        if y.mean() <= 0 or pt.loc[p, "share_pct"] < 1:
            continue
        lr = stats.linregress(np.arange(n), y)
        rel = lr.slope * (n - 1) / y.mean()
        if lr.pvalue < 0.05 and abs(rel) > 0.25:
            cand.append((p, y, lr, rel))
    downs = sorted([x for x in cand if x[3] < 0], key=lambda x: x[3] * piv[x[0]].mean())[:4]
    ups = sorted([x for x in cand if x[3] > 0], key=lambda x: -x[3] * piv[x[0]].mean())[:2]
    for p, y, lr, rel in downs + ups:
        up = rel > 0
        first, last = y[:3].mean(), y[-3:].mean()
        mon = (last - first) * 4.33
        ev = [f"Weekly revenue: {c.m(first)} (first 3 weeks) → {c.m(last)} (last 3 weeks)", f"Trend measured over {n} full weeks"]
        factors = []
        if has(c.df, "stock"):
            x = c.df[(c.df["product"] == p) & (c.df.date > c.end - pd.Timedelta(days=28))]
            so = int(x.groupby("date").stock.min().le(0).sum())
            if so and not up:
                factors.append(f"Possible contributing factor: {p} was out of stock on {so} of the last 28 days.")
        out.append(_ins("trend", "Products", "Opportunity" if up else "Risk", f"{'Rising demand' if up else 'Declining sales'}: {p}",
                        f"Weekly revenue for {p} moved {rel * 100:+.0f}% over {n} weeks.",
                        "Steady growth needs enough stock and supply to keep up." if up else "A steady decline (not a one-off dip) is worth investigating before it deepens.",
                        ev + factors, "Check stock cover and reorder size so growth is not lost to stockouts." if up else "Investigate availability, pricing, placement and competition for this product.",
                        impact=0 if up else -mon, basis="per month", monthly=0 if up else -mon, conf=float(1 - lr.pvalue), date=str(c.end.date()), floor=0, cap=1 if up else 3,
                        urgency=0.5, details=dict(method="Linear trend on weekly revenue (significance p<0.05, change >25%).", metric="Weekly revenue", observed=float(last), baseline=float(first),
                                                  deviation=float(rel * 100), p_value=float(lr.pvalue), product=p, factors=factors)))
    done = {i["details"]["product"] for i in out}
    return out + product_level_shifts(c, pt, done)


# ---------------------------------------------------------------- inventory
def inventory(c: Ctx, pt: pd.DataFrame):
    rows, ins = [], []
    if not c.caps["inventory"]["available"]:
        return rows, ins, []
    leaks = []
    rec_from = c.end - pd.Timedelta(days=14)
    prev_from = c.end - pd.Timedelta(days=28)
    for p, x in c.df.groupby("product"):
        xs = x.sort_values("date")
        stk = xs.stock.dropna()
        if stk.empty:
            continue
        cur = float(stk.iloc[-1])
        rec = x[x.date > rec_from]
        prev = x[(x.date <= rec_from) & (x.date > prev_from)]
        dem = rec.quantity.sum() / 14
        trend = (dem / (prev.quantity.sum() / 14) - 1) * 100 if prev.quantity.sum() > 0 else None
        hist_dem = float(x.quantity.sum() / max(c.days, 1))
        if cur <= 0:                       # already out of stock: recent sales are zero BECAUSE of it, so fall back to the historical pace
            days, dem = 0.0, (dem if dem > 0 else hist_dem)
        else:
            days = cur / dem if dem > 0 else None
        so_dates = x.groupby("date").stock.min().le(0)
        so = int(so_dates.sum())
        avg_price = _f(pt.loc[p, "avg_price"]) if "avg_price" in pt else None
        drev = float(rec.revenue.sum() / 14) or float(x.revenue.sum() / max(c.days, 1))
        risk = "LOW" if days is None else "HIGH" if days < 7 else "MEDIUM" if days < 14 else "LOW"
        miss = None
        if so:
            ok_days = x[x.stock > 0].groupby("date").revenue.sum()
            miss = float(ok_days.mean() * so) if len(ok_days) else None
        rows.append(dict(product=p, stock=cur, daily_demand=_f(dem), demand_trend_pct=_f(trend), days_left=_f(days),
                         range=(f"{days * .75:.0f}–{days * 1.25:.0f} days" if days is not None else "n/a"), risk=risk, stockout_days=so, missed_revenue=_f(miss)))
        share = float(pt.loc[p, "share_pct"])
        if risk != "LOW":
            at_risk = drev * max(0.0, 14 - days)
            floor = 3 if days < 3 and share >= 5 else 2 if days < 7 else 1
            ins.append(_ins("inventory", "Inventory", "Risk", f"Stockout risk: {p}",
                            (f"{p} is out of stock right now while it is still selling (about {dem:.1f} units/day recently)." if cur <= 0 else f"{p} has about {days:.0f} day(s) of stock left at the current sales pace ({cur:,.0f} units on hand)."),
                            "Running out means lost sales, and customers may switch to a competitor.",
                            [f"Stock on hand: {cur:,.0f} units", f"Recent demand: {dem:.1f} units/day" + (f" ({trend:+.0f}% vs the 2 weeks before)" if trend is not None else ""), ("Estimated cover: none (out of stock)" if cur <= 0 else f"Estimated cover: {days_label(days)} (estimate)")],
                            ("Check whether a delivery is already on the way; if not, reorder now and review safety stock."),
                            impact=at_risk, basis="over the next 14 days if not replenished", monthly=at_risk * 30 / 14, conf=0.75, date=str(c.end.date()), floor=floor, cap=3,
                            urgency=1.0 if days < 7 else 0.6, details=dict(method="Stock on hand divided by average daily sales of the last 14 days.", metric="Days of stock", observed=float(days), product=p)))
        if so >= 3 and miss:
            mon = miss / c.months
            leaks.append(dict(type="Stockouts", item=p, monthly=mon, note=f"{so} stockout day(s) in the data (estimate)"))
            ins.append(_ins("stockout", "Inventory", "Financial", f"Repeated stockouts: {p}",
                            f"{p} was out of stock on {so} day(s) during the period.", "Each stockout day is a day of potentially lost sales.",
                            [f"{so} day(s) with zero stock", f"Estimated missed revenue: {c.m(miss)} (average revenue of in-stock days × stockout days)"],
                            "Raise the reorder point or safety stock for this product.", impact=mon, basis="per month", conf=0.75, date=str(c.end.date()), floor=1, cap=3, urgency=0.4,
                            details=dict(method="Average daily revenue on in-stock days multiplied by stockout days.", metric="Stockout days", observed=float(so), product=p)))
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    rows.sort(key=lambda r: (order[r["risk"]], r["days_left"] if r["days_left"] is not None else 1e9))
    risky = [i for i in ins if i["kind"] == "inventory"]
    keep_ids = {id(i) for i in sorted(risky, key=lambda i: i["details"]["observed"])[:5]}
    ins = [i for i in ins if i["kind"] != "inventory" or id(i) in keep_ids]
    stock_ins = [i for i in ins if i["kind"] == "stockout"]
    ins = [i for i in ins if i["kind"] == "inventory"] + sorted(stock_ins, key=lambda i: -(i["impact_amount"] or 0))[:3]
    return rows, ins, leaks


def days_label(d): return f"about {d * .75:.0f}–{d * 1.25:.0f} days"


# ---------------------------------------------------------------- suppliers
def suppliers(c: Ctx, pt: pd.DataFrame):
    if not c.caps["suppliers"]["available"]:
        return [], [], [], []
    df = c.df[c.df.supplier.notna()]
    rev = df.groupby("supplier").revenue.sum()
    tab, ins, leaks, drift = [], [], [], []
    w = min(56, c.days // 3)
    if has(c.df, "cost") and w >= 14:
        for (s, p), x in df.groupby(["supplier", "product"]) if "product" in df else []:
            rec, old = x[x.date > c.end - pd.Timedelta(days=w)], x[x.date <= c.end - pd.Timedelta(days=w)]
            if rec.cost.notna().sum() < 3 or old.cost.notna().sum() < 3:
                continue
            a, b = rec.cost.mean(), old.cost.mean()
            if b <= 0:
                continue
            ch = (a / b - 1) * 100
            u = rec.quantity.sum() if "quantity" in rec else None
            mon = (a - b) * u / w * 30 if u is not None and ch > 0 else None
            drift.append(dict(supplier=str(s), product=str(p), cost_change_pct=float(ch), avg_cost_recent=float(a), avg_cost_before=float(b), monthly_impact=_f(mon)))
    flagged = sorted([d for d in drift if d["cost_change_pct"] > 5], key=lambda d: -(d["monthly_impact"] or 0))[:4]
    for d in flagged:
        mon = d["monthly_impact"]
        if mon is not None:
            leaks.append(dict(type="Supplier price", item=f"{d['product']} ({d['supplier']})", monthly=mon, note=f"+{d['cost_change_pct']:.1f}% purchase cost"))
        ins.append(_ins("supplier", "Suppliers", "Financial", f"Supplier cost increase: {d['product']} ({d['supplier']})",
                        f"{d['supplier']}'s average purchase cost for {d['product']} rose {d['cost_change_pct']:.1f}% over the last {w} days.",
                        "Higher costs squeeze your margin unless prices follow.",
                        [f"Average unit cost: {c.m(d['avg_cost_before'])} → {c.m(d['avg_cost_recent'])}", f"Compared the last {w} days with everything before"],
                        "Negotiate with the supplier, compare alternatives, or review the selling price.", impact=mon, basis="per month", conf=0.85, date=str(c.end.date()),
                        floor=2 if d["cost_change_pct"] > 15 else 1, cap=3, urgency=0.4, details=dict(method="Average purchase cost, recent window vs earlier.", metric="Avg unit cost", observed=d["avg_cost_recent"], baseline=d["avg_cost_before"], deviation=d["cost_change_pct"])))
    for s, r in rev.sort_values(ascending=False).items():
        sd = [d for d in drift if d["supplier"] == str(s)]
        tab.append(dict(supplier=str(s), revenue=float(r), share_pct=float(r / rev.sum() * 100), products=int(df[df.supplier == s]["product"].nunique()) if "product" in df else None,
                        max_cost_change_pct=_f(max((d["cost_change_pct"] for d in sd), default=None)), status="Attention" if any(d["cost_change_pct"] > 5 for d in sd) else "Normal"))
    if len(rev) > 1:
        top = rev.idxmax()
        sh = rev.max() / rev.sum() * 100
        if sh > 50:
            ins.append(_ins("concentration", "Suppliers", "Risk", f"Supplier concentration: {top}", f"Products supplied by {top} generate {sh:.0f}% of your revenue.",
                            "Depending on one supplier makes the business vulnerable to delays or price rises.", [f"{top}: {sh:.0f}% of revenue"],
                            "Identify a backup supplier for your most important products.", impact=None, conf=0.7, date=str(c.end.date()), floor=0, cap=1, urgency=0.1,
                            details=dict(method="Share of revenue from products linked to this supplier.", metric="Revenue share %", observed=float(sh))))
    return tab, ins, leaks, drift


# ---------------------------------------------------------------- profitability
def profitability(c: Ctx, pt: pd.DataFrame):
    if not c.has_cost:
        return None, [], []
    ok = c.df[c.cost_rows]
    rev_cov = float(ok.revenue.sum() / c.total * 100)
    profit, rv = float(ok.profit.sum()), float(ok.revenue.sum())
    margin = profit / rv * 100 if rv else None
    cur, prev = c.split(ok)
    mchg = None
    if cur is not None and prev.revenue.sum() > 0 and cur.revenue.sum() > 0:
        mchg = float(cur.profit.sum() / cur.revenue.sum() * 100 - prev.profit.sum() / prev.revenue.sum() * 100)
    info = dict(profit=profit, margin_pct=margin, revenue_coverage_pct=rev_cov, margin_change_pts=mchg)
    ins, leaks = [], []
    if margin is None or "margin_pct" not in pt:
        return info, ins, leaks
    cand = pt[pt.margin_pct.notna()]
    for p, r in cand.iterrows():
        mon_rev = float(ok[ok["product"] == p].revenue.sum() / c.months) if "product" in ok else 0
        if r.margin_pct < 0:
            loss = -float(r.profit) / c.months
            leaks.append(dict(type="Sold below cost", item=p, monthly=loss, note=f"Margin {r.margin_pct:.1f}%"))
            ins.append(_ins("margin", "Profitability", "Financial", f"Selling below cost: {p}", f"{p} has a negative margin ({r.margin_pct:.1f}%): each sale loses money on average.",
                            "Every extra unit sold increases the loss.", [f"Margin: {r.margin_pct:.1f}%", f"{r.share_pct:.0f}% of revenue, {c.m(float(r.profit))} total profit"],
                            "Review the selling price or the purchase cost immediately.", impact=loss, basis="per month", conf=0.9, date=str(c.end.date()), floor=2, cap=3, urgency=0.7,
                            details=dict(method="Revenue minus quantity × unit cost, on rows with a known cost.", metric="Margin %", observed=float(r.margin_pct), product=p)))
        elif margin and r.margin_pct < 0.6 * margin and r.share_pct >= 3:
            gap = mon_rev * (margin - r.margin_pct) / 100
            ins.append(_ins("margin", "Profitability", "Financial", f"Low-margin product: {p}",
                            f"{p} earns a {r.margin_pct:.1f}% margin versus {margin:.1f}% for the business overall, yet represents {r.share_pct:.0f}% of revenue.",
                            "High sales with low profit can hide a weak spot.", [f"Margin: {r.margin_pct:.1f}% (business average {margin:.1f}%)", f"{r.share_pct:.0f}% of revenue"],
                            "Review the price or the supplier cost for this product.", impact=gap, basis="per month if it matched your average margin (a gap, not a forecast)", conf=0.85,
                            date=str(c.end.date()), floor=1, cap=2, urgency=0.2, details=dict(method="Product margin vs overall margin.", metric="Margin %", observed=float(r.margin_pct), baseline=float(margin), product=p)))
    ins = sorted(ins, key=lambda i: -(i["impact_amount"] or 0))[:4]
    if mchg is not None and mchg <= -3:
        ins.append(_ins("margin_trend", "Profitability", "Financial", f"Your margin dropped {abs(mchg):.1f} points", f"Gross margin over the last {c.window} days is {abs(mchg):.1f} points lower than in the previous {c.window} days.",
                        "Shrinking margins reduce profit even when sales hold up.", [f"Margin change: {mchg:+.1f} points", f"Overall margin: {margin:.1f}%"],
                        "Check supplier cost increases and recent discounting.", impact=abs(mchg) / 100 * cur.revenue.sum() * 30 / c.window, basis="per month", conf=0.8, date=str(c.end.date()), floor=1, cap=3, urgency=0.6,
                        details=dict(method="Gross margin, recent window vs previous window.", metric="Margin change (pts)", deviation=float(mchg))))
    return info, ins, leaks


# ---------------------------------------------------------------- customers
def customers(c: Ctx):
    if not c.caps["customers"]["available"]:
        return None, []
    df = c.df[c.df.customer.notna()]
    g = df.groupby("customer")
    rev = g.revenue.sum().sort_values(ascending=False)
    orders = g.order_id.nunique() if "order_id" in df else g.size()
    top1 = float(rev.iloc[0] / rev.sum() * 100)
    top5 = float(rev.head(5).sum() / rev.sum() * 100)
    summary = dict(total=int(len(rev)), top1_share_pct=top1, top5_share_pct=top5, avg_orders=float(orders.mean()), repeat_share_pct=float((orders > 1).mean() * 100))
    cur, prev = c.split(df)
    ins = []
    if cur is not None:
        a, b = set(cur.customer), set(prev.customer)
        lost, new = b - a, a - b
        summary.update(active_current=len(a), active_previous=len(b), new=len(new), lost=len(lost), window_days=c.window)
        lost_rev = float(prev[prev.customer.isin(lost)].revenue.sum())
        if b and len(lost) / len(b) >= 0.25 and lost_rev > 0:
            mon = lost_rev * 30 / c.window
            ins.append(_ins("customers_lost", "Customers", "Risk", f"{len(lost)} customers haven't come back", f"{len(lost)} of {len(b)} customers who bought in the previous {c.window} days did not buy in the last {c.window} days.",
                            "Losing regular customers quietly erodes revenue.", [f"Customers active: {len(b)} → {len(a)}", f"Their previous spend: {c.m(lost_rev)}"],
                            "Contact your most valuable lapsed customers (offer, call or message) to find out why.", impact=mon, basis="per month (their previous spending)", conf=0.65, date=str(c.end.date()), floor=1, cap=3, urgency=0.5,
                            details=dict(method="Customers active in the previous window but absent in the latest one.", metric="Active customers", observed=float(len(a)), baseline=float(len(b)))))
        summary["lost_revenue_previous"] = lost_rev
    if len(rev) >= 5 and (top1 > 25 or top5 > 60):
        ins.append(_ins("customers_concentration", "Customers", "Risk", "Revenue depends on a few customers", f"Your top customer represents {top1:.0f}% of revenue and your top 5 represent {top5:.0f}%.",
                        "Losing one of them would hit revenue hard.", [f"Top customer: {top1:.0f}%", f"Top 5 customers: {top5:.0f}%"], "Grow the number of regular customers and protect the relationship with your largest ones.",
                        impact=None, conf=0.75, date=str(c.end.date()), floor=1 if top1 > 40 else 0, cap=2, urgency=0.1, details=dict(method="Revenue share of the largest customers.", metric="Top-5 share %", observed=top5)))
    tops = []
    for name, r in rev.head(20).items():
        last = df[df.customer == name].date.max()
        tops.append(dict(name=str(name), revenue=float(r), share_pct=float(r / rev.sum() * 100), orders=int(orders[name]), last_purchase=str(last.date()), days_since=int((c.end - last).days)))
    summary["top"] = tops
    return summary, ins


# ---------------------------------------------------------------- returns
def returns(c: Ctx, pt):
    if not c.caps["returns"]["available"]:
        return None, [], []
    df = c.df[c.df.returned.notna() & c.df.quantity.notna()]
    rr = float(df.returned.sum() / max(df.quantity.sum(), 1) * 100)
    info, ins, leaks = dict(return_rate_pct=rr), [], []
    if "product" not in df or c.window == 0:
        return info, ins, leaks
    cur, prev = c.split(df)
    if cur is None:
        return info, ins, leaks
    for p, x in cur.groupby("product"):
        y = prev[prev["product"] == p]
        if x.quantity.sum() < 30 or y.quantity.sum() < 30:
            continue
        a, b = x.returned.sum() / x.quantity.sum() * 100, y.returned.sum() / y.quantity.sum() * 100
        if a >= 5 and a >= 1.5 * max(b, 0.5):
            price = float(x.revenue.sum() / x.quantity.sum())
            loss = float(x.returned.sum() * price) * 30 / c.window
            leaks.append(dict(type="Returns", item=p, monthly=loss, note=f"Return rate {b:.1f}% → {a:.1f}%"))
            ins.append(_ins("returns", "Returns", "Anomaly", f"Rising returns: {p}", f"The return rate for {p} rose from {b:.1f}% to {a:.1f}%.", "More returns mean refunds, handling costs and possible quality problems.",
                            [f"Return rate: {b:.1f}% → {a:.1f}% (last {c.window} days vs the {c.window} before)", f"Units returned recently: {x.returned.sum():,.0f}"],
                            "Inspect quality, batches and customer complaints for this product.", impact=loss, basis="per month (value of returned units)", conf=0.75, date=str(c.end.date()), floor=1, cap=3, urgency=0.5,
                            details=dict(method="Return rate (returned ÷ sold), recent window vs previous window.", metric="Return rate %", observed=float(a), baseline=float(b), product=p)))
    return info, sorted(ins, key=lambda i: -(i["impact_amount"] or 0))[:3], leaks


# ---------------------------------------------------------------- forecast
def forecast(c: Ctx, horizon=14):
    if not c.caps["forecast"]["available"]:
        return dict(available=False, message=c.caps["forecast"]["reason"] or "Not enough historical data for a reliable forecast.")
    daily = c.daily

    def fit(h):
        wd = h.groupby(h.index.dayofweek).mean()
        return wd, float((h - wd.reindex(h.index.dayofweek).values).std())

    h = daily[-56:]
    wd, sd = fit(h)
    wape = None
    if len(daily) >= 42:                                         # honest back-test: predict the last 14 known days from the data before them
        train, test = daily[:-14][-56:], daily[-14:]
        w2, _ = fit(train)
        pred = w2.reindex(test.index.dayofweek).values
        if test.sum() > 0:
            wape = float(np.abs(test.values - pred).sum() / test.sum() * 100)
    quality = "limited" if len(daily) < 56 or wape is None else ("low" if wape > 40 else "moderate")
    fut = pd.date_range(c.end + pd.Timedelta(days=1), periods=horizon)
    pts = [dict(date=str(d.date()), value=_f(wd.get(d.dayofweek, 0)), low=_f(max(0, wd.get(d.dayofweek, 0) - 1.96 * sd)), high=_f(wd.get(d.dayofweek, 0) + 1.96 * sd)) for d in fut]
    msg = {"limited": "Limited history: treat this as a rough guide only.", "low": f"Past tests on your own data were off by about {wape:.0f}%, so treat this as a rough guide only." if wape else "",
           "moderate": f"On your last 14 days the same method was off by about {wape:.0f}%." if wape else ""}[quality]
    return dict(available=True, quality=quality, quality_note=msg, backtest_error_pct=wape,
                method="Average revenue for each weekday over the last 8 weeks; the shaded band is a rough 95% range. It is an estimate, not a guarantee.",
                history=[dict(date=str(d.date()), value=_f(v)) for d, v in daily[-60:].items()], forecast=pts)


# ---------------------------------------------------------------- orchestration
def kpis(c: Ctx):
    df = c.df
    k = dict(revenue=c.total, days=c.days, start=str(c.start.date()), end=str(c.end.date()), rows=len(df), avg_daily_revenue=c.total / max(c.days, 1),
             orders=int(df.order_id.nunique()) if "order_id" in df and df.order_id.notna().any() else None, units=_f(df.quantity.sum()) if has(df, "quantity") else None)
    cur, prev = c.split()
    k["period"] = None
    if cur is not None and prev.revenue.sum() > 0:
        def ch(a, b): return float((a - b) / b * 100) if b else None
        p = dict(days=c.window, revenue=float(cur.revenue.sum()), revenue_prev=float(prev.revenue.sum()), revenue_change_pct=ch(cur.revenue.sum(), prev.revenue.sum()))
        if k["orders"] is not None:
            oc, op = cur.order_id.nunique(), prev.order_id.nunique()
            p.update(orders=int(oc), orders_prev=int(op), orders_change_pct=ch(oc, op))
        if c.has_cost:
            a, b = cur[c.cost_rows.reindex(cur.index, fill_value=False)].profit.sum(), prev[c.cost_rows.reindex(prev.index, fill_value=False)].profit.sum()
            p.update(profit=float(a), profit_prev=float(b), profit_change_pct=ch(a, b) if b > 0 else None)
        k["period"] = p
    return k


def health(c: Ctx, rc, inv_rows, sup_drift, prof, cust, rets, ins):
    cats = {}
    if rc:
        cats["Sales"] = dict(score=int(np.clip(70 + rc["change_pct"] * 2, 0, 100)), factors=[f"Revenue change over the last {rc['window_days']} days: {rc['change_pct']:+.1f}%"])
    if prof and prof["margin_pct"] is not None:
        bad = 0.0
        if "product" in c.df:
            pm = c.df[c.cost_rows].groupby("product").agg(r=("revenue", "sum"), p=("profit", "sum"))
            bad = float(pm[pm.p < 0].r.sum() / max(pm.r.sum(), 1))
        s = 90 - 60 * bad - (min(20, 4 * -prof["margin_change_pts"]) if (prof["margin_change_pts"] or 0) < 0 else 0)
        cats["Profitability"] = dict(score=int(np.clip(s, 0, 100)), factors=[f"Gross margin {prof['margin_pct']:.1f}%"] + ([f"Margin change {prof['margin_change_pts']:+.1f} pts"] if prof["margin_change_pts"] is not None else []))
    if inv_rows:
        n = sum(1 for i in inv_rows if i["risk"] != "LOW")
        so = sum(i["stockout_days"] for i in inv_rows)
        cats["Inventory"] = dict(score=int(np.clip(100 - 100 * n / len(inv_rows) - 3 * so / len(inv_rows), 0, 100)), factors=[f"{n} of {len(inv_rows)} products at stockout risk", f"{so} stockout day(s) in total"])
    if c.caps["suppliers"]["available"] and has(c.df, "cost"):
        n = sum(1 for d in sup_drift if d["cost_change_pct"] > 5)
        cats["Suppliers"] = dict(score=int(np.clip(100 - 20 * n, 0, 100)), factors=[f"{n} supplier cost increase(s) above 5%"])
    if cust and cust.get("lost") is not None and cust.get("active_previous"):
        s = 100 - 60 * cust["lost"] / cust["active_previous"] - (10 if cust["top1_share_pct"] > 25 else 0)
        cats["Customers"] = dict(score=int(np.clip(s, 0, 100)), factors=[f"{cust['lost']} of {cust['active_previous']} previous customers did not return"])
    if rets:
        cats["Operations"] = dict(score=int(np.clip(100 - rets["return_rate_pct"] * 6, 0, 100)), factors=[f"Return rate {rets['return_rate_pct']:.1f}%"])
    overall = int(np.mean([v["score"] for v in cats.values()])) if cats else None
    return dict(overall=overall, categories=cats, note="The score averages the areas your data allows us to assess. Areas without data are not scored." if cats else "Not enough data to calculate this metric.")


def finalize(ins: list[dict], c: Ctx):
    for i in ins:
        mon = i.pop("impact_monthly")
        ratio = (mon / c.monthly_rev) if (mon and c.monthly_rev > 0) else 0.0
        r_idx = 3 if ratio >= .10 else 2 if ratio >= .03 else 1 if ratio >= .005 else 0
        idx = min(max(i["floor"], r_idx if i["category"] != "Opportunity" else 0), i["cap"])
        i["severity"] = SEV[idx]
        i["impact_ratio"] = float(ratio)
        i["priority_score"] = float(idx * 100 + min(60, ratio * 300) + i["confidence"] * 10 + i["urgency"] * 10)
        amt = i["impact_amount"]
        if amt is None:
            i["impact_text"] = NO_IMPACT
        elif amt <= 0:
            i["impact_text"] = "No financial loss detected; this is an opportunity rather than a problem." if i["category"] == "Opportunity" else "No negative financial impact detected."
        else:
            i["impact_text"] = f"About {c.m(amt)} {i['impact_basis']}. This is an estimate based on your historical data."
        for k in ("floor", "cap", "urgency"):
            i.pop(k, None)
        i["recommendation"] = dict(problem=i["what"], evidence="; ".join(i["evidence"][:3]), action=i["action"], priority=i["severity"], confidence=i["confidence"],
                                   objective={"Opportunity": "Capture the upside.", "Risk": "Avoid the loss before it happens."}.get(i["category"], "Limit the financial damage."))
    ins.sort(key=lambda i: -i["priority_score"])
    return ins


def analyze_clean(df: pd.DataFrame, currency: str = "DZD") -> dict:
    c = Ctx(df, currency)
    ins, leaks = [], []
    ins += sales_insights(c)
    rc, rins = root_cause(c)
    ins += rins
    pt = product_table(c) if c.product_available() else pd.DataFrame()
    if len(pt):
        ins += product_insights(c, pt)
    inv_rows, iins, ileaks = inventory(c, pt) if len(pt) else ([], [], [])
    ins += iins; leaks += ileaks
    sup_rows, sins, sleaks, drift = suppliers(c, pt) if len(pt) or c.caps["suppliers"]["available"] else ([], [], [], [])
    ins += sins; leaks += sleaks
    prof, pins, pleaks = profitability(c, pt) if len(pt) else (None, [], [])
    ins += pins; leaks += pleaks
    cust, cins = customers(c)
    ins += cins
    rets, rinsr, rleaks = returns(c, pt)
    ins += rinsr; leaks += rleaks
    ins = finalize(ins, c)
    for n, i in enumerate(ins, 1):
        i["rank"] = n
    leaks.sort(key=lambda l: -(l["monthly"] or 0))
    d = c.df
    monthly = d.groupby(d.date.dt.to_period("M")).agg(revenue=("revenue", "sum"), days=("date", "nunique"))
    mrows = []
    for per, r in monthly.iterrows():
        row = dict(month=str(per), revenue=float(r.revenue), days_with_sales=int(r.days), partial=bool((c.start > per.start_time) or (c.end < per.end_time.normalize())))
        if c.has_cost:
            x = d[(d.date.dt.to_period("M") == per) & c.cost_rows]
            row["profit"] = float(x.profit.sum())
            row["margin_pct"] = float(x.profit.sum() / x.revenue.sum() * 100) if x.revenue.sum() else None
        mrows.append(row)
    weekday = [dict(day=n, avg_revenue=float(c.daily[c.daily.index.dayofweek == i].mean())) for i, n in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]) if (c.daily.index.dayofweek == i).any()]
    return dict(currency=currency, kpis=kpis(c), capabilities=c.caps, root_cause=rc, insights=ins, leaks=leaks,
                products=[dict(product=str(p), **{k: _f(v) if k != "category" else (None if v is None or (isinstance(v, float) and np.isnan(v)) else str(v)) for k, v in r.items()}) for p, r in pt.head(200).iterrows()],
                inventory=inv_rows, suppliers=sup_rows, supplier_drift=drift, profitability=prof, customers=cust, returns=rets, forecast=forecast(c),
                health=health(c, rc, inv_rows, drift, prof, cust, rets, ins),
                daily=[dict(date=str(k.date()), revenue=float(v)) for k, v in c.daily.items()], monthly=mrows, weekday=weekday)


def analyze(raw: pd.DataFrame, mapping: dict | None = None, currency: str = "DZD") -> dict:
    """Convenience wrapper: detect mapping if needed, validate/clean, analyse."""
    from .mapping import detect_mapping
    from .quality import prepare
    p = prepare(raw, mapping or detect_mapping(raw))
    if p.df is None:
        raise ValueError("; ".join(i["message"] for i in p.report["issues"] if i["severity"] == "error") or "The data cannot be analysed.")
    out = analyze_clean(p.df, currency)
    out["quality"] = p.report
    return out
