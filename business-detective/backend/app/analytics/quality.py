"""Data-quality engine: parses customer data defensively, rejects only what is truly unusable, and reports everything."""
import re
from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import pandas as pd

from .capabilities import LABELS, MIN_DAYS, capabilities, history_days
from .mapping import FIELDS, check_mapping

NUMERIC = ["revenue", "quantity", "price", "cost", "stock", "returned"]
TEXT = ["product", "category", "supplier", "customer", "location", "order_id"]
_CUR = re.compile(r"\b(dzd|da|dinars?|eur|usd|gbp|mad|tnd)\b|[$€£]", re.I)


def to_number(v) -> float:
    """Parses '1,234.50', '1.234,50', '1 234,5', '12 000 DA', '(15)', 1500 ... -> float, or NaN when it is not a number."""
    if v is None or isinstance(v, bool):
        return np.nan
    if isinstance(v, (int, float, np.integer, np.floating)):
        f = float(v)
        return f if np.isfinite(f) else np.nan
    s = str(v).replace("\u00a0", " ").replace("\u202f", " ").strip()
    if not s:
        return np.nan
    neg = s.startswith("(") and s.endswith(")")
    s = _CUR.sub("", s)
    s = re.sub(r"[\s']", "", s).strip("()")
    if not s or re.search(r"[^\d,.\-+]", s):
        return np.nan
    if "," in s and "." in s:
        dec = "," if s.rfind(",") > s.rfind(".") else "."
        s = s.replace("." if dec == "," else ",", "").replace(dec, ".")
    elif "," in s:
        s = s.replace(",", "") if re.fullmatch(r"[+-]?\d{1,3}(,\d{3})+", s) else s.replace(",", ".")
    elif "." in s and re.fullmatch(r"[+-]?\d{1,3}(\.\d{3}){2,}", s):
        s = s.replace(".", "")
    try:
        f = float(s)
    except ValueError:
        return np.nan
    f = -abs(f) if neg else f
    return f if np.isfinite(f) else np.nan


def parse_numbers(s: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s):
        return pd.to_numeric(s, errors="coerce").replace([np.inf, -np.inf], np.nan).astype(float)
    uniq = s.dropna().unique()
    return s.map({u: to_number(u) for u in uniq}).astype(float)


def parse_dates(s: pd.Series) -> tuple[pd.Series, str]:
    """Returns (datetime series normalised to the day, note). Chooses day-first vs month-first by what parses best."""
    note = ""
    if pd.api.types.is_datetime64_any_dtype(s):
        out = s
    elif pd.api.types.is_numeric_dtype(s):                      # Excel serial numbers
        n = pd.to_numeric(s, errors="coerce")
        out = pd.to_datetime(n.where((n > 20000) & (n < 80000)), unit="D", origin="1899-12-30", errors="coerce")
    else:
        st = s.astype("string").str.strip()
        out = pd.to_datetime(st, errors="coerce", format="ISO8601")           # unambiguous year-first dates are parsed strictly
        rest = st[out.isna() & st.notna() & (st != "")]
        if len(rest):                                                        # remaining formats: choose day-first vs month-first by what parses best
            a = pd.to_datetime(rest, errors="coerce", dayfirst=False, format="mixed")
            b = pd.to_datetime(rest, errors="coerce", dayfirst=True, format="mixed")
            use_b = b.notna().sum() >= a.notna().sum()
            out = out.copy()
            out.loc[rest.index] = (b if use_b else a)
            if re.match(r"^\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}", rest.iloc[0]):
                note = "Dates written like 05/06/2026 are read as " + ("day/month/year." if use_b else "month/day/year.")
    if getattr(out.dt, "tz", None) is not None:
        out = out.dt.tz_localize(None)
    return out.dt.normalize(), note


@dataclass
class Prepared:
    df: pd.DataFrame | None
    report: dict


def _sample(raw: pd.Series, mask: pd.Series, n: int = 3) -> list[str]:
    return [str(x)[:40] for x in raw[mask].dropna().astype(str).unique()[:n]]


def prepare(raw: pd.DataFrame, mapping: dict) -> Prepared:
    """Cleans `raw` according to `mapping` and builds the full data-quality report. `df` is None when analysis is impossible."""
    cols = [str(c) for c in raw.columns]
    mp = check_mapping(mapping, cols)
    issues, passed = [], []
    received = len(raw)

    def issue(sev, code, msg, cons="", fix=""):
        issues.append(dict(severity=sev, code=code, message=msg, consequence=cons, fix=fix))

    has_amount = "revenue" in mp or ("quantity" in mp and "price" in mp)
    blocking = False
    if "date" not in mp:
        issue("error", "no_date", "We couldn't identify a date column.", "Without dates we cannot study trends, anomalies or forecasts.", "Select the column that contains the sale date.")
        blocking = True
    if not has_amount:
        issue("error", "no_amount", "We couldn't identify a revenue column (or quantity and unit price).",
              "Without an amount of money we cannot measure sales.", "Select the revenue/sales amount column, or map both quantity and unit price.")
        blocking = True
    if blocking:
        return Prepared(None, dict(rows_received=received, rows_accepted=0, rows_rejected=received, duplicates_removed=0, score=0, can_analyze=False,
                                   issues=issues, passed=passed, fields=[], capabilities={}, date_range=None))

    sub = raw[list(mp.values())].copy()
    sub.columns = list(mp.keys())
    sub = sub.dropna(how="all")
    passed.append(f"{received:,} rows detected")

    dup_mask = sub.astype(str).duplicated()
    dups = int(dup_mask.sum())
    sub = sub[~dup_mask].copy()
    raw_cols = sub.copy()

    # --- parse
    d, note = parse_dates(sub["date"])
    date_missing = sub["date"].isna() | (sub["date"].astype(str).str.strip() == "")
    today = pd.Timestamp(date.today())
    impossible = d.notna() & ((d.dt.year < 1990) | (d > today + timedelta(days=366)))
    d = d.where(~impossible)
    date_invalid = d.isna() & ~date_missing
    num = {f: parse_numbers(sub[f]) for f in NUMERIC if f in sub}
    if "revenue" not in num:
        num["revenue"] = pd.Series(np.nan, index=sub.index)
    rev, qty, prc = num["revenue"], num.get("quantity"), num.get("price")
    if qty is not None and prc is not None:                      # fall back to quantity x price when the amount itself is missing
        derived = qty * prc
        filled = rev.isna() & derived.notna()
        rev = rev.where(~filled, derived)
    rev_missing = rev.isna() & (sub["revenue"].isna() if "revenue" in sub else True)
    rev_invalid = rev.isna() & ~rev_missing
    neg = (rev < 0) | ((qty < 0) if qty is not None else False) | ((prc < 0) if prc is not None else False)
    reject = date_missing | date_invalid | rev.isna() | neg
    ok = ~reject

    # --- report counts
    def pct(n): return f"{n / max(received, 1) * 100:.1f}%"
    if int(date_invalid.sum()):
        n = int(date_invalid.sum())
        issue("warning", "invalid_dates", f"{n:,} row(s) have a date we couldn't read (e.g. {', '.join(_sample(raw_cols['date'], date_invalid))}).",
              "These rows were left out of the analysis.", "Use a standard date format such as 2026-03-31 or 31/03/2026.")
    if int(date_missing.sum()):
        n = int(date_missing.sum())
        issue("warning", "missing_dates", f"{n:,} row(s) have no date.", "These rows were left out of the analysis.", "Fill in the date for every sale.")
    n_rev = int((rev_missing | rev_invalid).sum())
    if n_rev:
        src = "revenue" if "revenue" in sub else "quantity/price"
        samples = _sample(raw_cols["revenue"], rev_invalid) if "revenue" in sub else []
        issue("warning", "invalid_revenue", f"{n_rev:,} row(s) have a missing or unreadable {src} value" + (f" (e.g. {', '.join(samples)})." if samples else "."),
              "These rows were left out, so totals may be slightly understated.", "Check the amount column for blanks or text.")
    n_neg = int((neg & ~date_missing & ~date_invalid & ~rev.isna()).sum())
    if n_neg:
        issue("warning", "negative_values", f"{n_neg:,} row(s) have a negative quantity, price or revenue.",
              "These rows were excluded because negative sales distort trends.", "If they are refunds, record them in a 'returned quantity' column instead.")
    if dups:
        issue("warning", "duplicates", f"{dups:,} exact duplicate row(s) were removed.",
              "Counting them would double-count sales.", "If repeated identical lines are genuine, add an order/transaction ID column so each line is unique.")
    if impossible.sum():
        issue("warning", "impossible_dates", f"{int(impossible.sum()):,} row(s) have an impossible date (before 1990 or far in the future).", "They were left out.", "Correct those dates.")
    future = int(((d > today) & ok).sum())
    if future:
        issue("info", "future_dates", f"{future:,} row(s) are dated in the future.", "They were kept; check that the dates are correct.", "")
    if note:
        issue("info", "date_format", note, "", "If this is wrong, convert the dates to YYYY-MM-DD before uploading.")

    clean = pd.DataFrame(index=sub.index)
    clean["date"], clean["revenue"] = d, rev
    for f in TEXT:
        if f in sub:
            s = sub[f].astype("string").str.strip().replace({"": pd.NA})
            clean[f] = s.astype(object).where(s.notna(), np.nan)
    for f in ["quantity", "price", "cost", "stock", "returned"]:
        if f in num:
            clean[f] = num[f]
    if "quantity" in clean:
        clean.loc[clean["quantity"] < 0, "quantity"] = np.nan
    clean = clean[ok].copy()
    fields = []
    for f in mp:
        invalid = missing = 0
        if f in NUMERIC and f != "revenue":
            col = num[f][ok]
            raw_present = sub[f][ok].notna() & (sub[f][ok].astype(str).str.strip() != "")
            invalid, missing = int((col.isna() & raw_present).sum()), int((~raw_present).sum())
            if f in ("stock", "returned", "cost", "price"):
                badneg = int((col < 0).sum())
                if badneg:
                    clean.loc[clean[f] < 0, f] = np.nan
                    issue("warning", "impossible_" + f, f"{badneg:,} row(s) have a negative {LABELS[f]}, which is impossible.", f"Those {LABELS[f]} values were ignored.", f"Correct the {LABELS[f]} values.")
                    invalid += badneg
        elif f in TEXT:
            missing = int(clean[f].isna().sum())
        elif f == "date":
            missing, invalid = int(date_missing.sum()), int(date_invalid.sum())
        elif f == "revenue":
            missing, invalid = int(rev_missing.sum()), int(rev_invalid.sum())
        status = "ok" if (invalid + missing) / max(len(sub), 1) < 0.02 else "warning"
        fields.append(dict(field=f, label=FIELDS[f][0], column=mp[f], missing=missing, invalid=invalid, status=status))
        if f not in ("date", "revenue") and f in clean and (missing + invalid) / max(len(clean), 1) >= 0.02:
            issue("warning", "missing_" + f, f"{missing + invalid:,} row(s) have a missing or unreadable {LABELS.get(f, f)}.",
                  f"Analyses that rely on {LABELS.get(f, f)} use only the rows where it is known.", "")
    if "product" in clean:
        miss = int(clean["product"].isna().sum())
        clean["product"] = clean["product"].fillna("(no product)")
        if miss:
            issue("info", "no_product", f"{miss:,} row(s) have no product name; they are grouped as '(no product)'.", "", "")
    if "returned" in clean and "quantity" in clean:
        over = int((clean["returned"] > clean["quantity"]).sum())
        if over:
            issue("warning", "returns_exceed", f"{over:,} row(s) show more units returned than sold.", "Return rates may be overstated.", "Check the returned quantity column.")

    rejected = received - len(clean) - dups - int(raw.isna().all(axis=1).sum())
    rejected = max(rejected, 0)
    result = dict(rows_received=received, rows_accepted=int(len(clean)), rows_rejected=int(rejected), duplicates_removed=dups)
    if len(clean) and rejected / max(received, 1) > 0.5:
        issue("error", "mostly_rejected", "More than half of your rows couldn't be used.", "The results would not represent your business.", "Check that the mapped columns are the right ones.")
        blocking = True
    if len(clean) < 5 or (len(clean) and clean["date"].nunique() < 2):
        issue("error", "too_few_rows", "There isn't enough usable data: we need at least 5 rows covering 2 different dates.", "Nothing meaningful can be calculated.", "Upload a file with more history.")
        blocking = True

    days = history_days(clean) if len(clean) else 0
    if not blocking and days < MIN_DAYS:
        issue("warning", "short_history", f"Your data covers only {days} day(s).",
              f"Unusual-sales detection, driver analysis and forecasts need at least {MIN_DAYS} days, so they are unavailable.", "Upload a longer period when you can.")

    # --- score
    score = 100.0
    score -= min(50.0, rejected / max(received, 1) * 150)
    score -= min(10.0, dups / max(received, 1) * 50)
    score -= min(15.0, sum(min(5.0, (f["missing"] + f["invalid"]) / max(len(sub), 1) * 20) for f in fields if f["field"] not in ("date", "revenue")))
    if days < 14: score -= 25
    elif days < MIN_DAYS: score -= 15
    if blocking: score = min(score, 40)
    score = int(max(0, round(score)))

    for f in fields:
        if f["status"] == "ok":
            passed.append(f"{f['label']} detected (column “{f['column']}”)")
    if len(clean):
        passed.append(f"{len(clean):,} rows accepted")
    rng = dict(start=str(clean["date"].min().date()), end=str(clean["date"].max().date()), days=days) if len(clean) else None
    caps = capabilities(clean) if len(clean) else {}
    report = dict(**result, score=score, can_analyze=not blocking, issues=issues, passed=passed, fields=fields, capabilities=caps, date_range=rng)
    return Prepared(None if blocking else clean.sort_values("date").reset_index(drop=True), report)
