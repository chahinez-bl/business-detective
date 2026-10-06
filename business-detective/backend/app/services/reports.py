"""Server-side PDF reports (reportlab). Built only from the stored analysis of the requesting business."""
import io
import os
from datetime import datetime, timezone
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import HRFlowable, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

FONT, FONT_B = "Helvetica", "Helvetica-Bold"
for d in ("/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/dejavu", "/usr/share/fonts/TTF", os.getenv("REPORT_FONT_DIR", "")):
    if d and os.path.exists(os.path.join(d, "DejaVuSans.ttf")):
        pdfmetrics.registerFont(TTFont("DejaVu", os.path.join(d, "DejaVuSans.ttf")))
        pdfmetrics.registerFont(TTFont("DejaVu-Bold", os.path.join(d, "DejaVuSans-Bold.ttf")))
        FONT, FONT_B = "DejaVu", "DejaVu-Bold"
        break

SEV_COL = {"Critical": "#b91c1c", "High": "#dc6803", "Medium": "#b7791f", "Low": "#2563a8"}
BRAND = colors.HexColor("#1d4ed8")


def _t(x) -> str:
    s = escape(str(x if x is not None else ""))
    if FONT == "Helvetica":
        s = s.replace("→", "->").replace("≈", "~").replace("–", "-").replace("—", "-").replace("’", "'").replace("“", '"').replace("”", '"')
        s = s.encode("cp1252", "replace").decode("cp1252")
    return s


def _money(x, cur): return "n/a" if x is None else f"{x:,.0f} {cur}"


def build_pdf(bundle: dict, actions: list[dict], business_name: str) -> bytes:
    cur = bundle["currency"]
    st = getSampleStyleSheet()
    H1 = ParagraphStyle("H1", parent=st["Title"], fontName=FONT_B, fontSize=22, textColor=BRAND, alignment=0, spaceAfter=4)
    H2 = ParagraphStyle("H2", parent=st["Heading2"], fontName=FONT_B, fontSize=13, textColor=colors.HexColor("#111827"), spaceBefore=14, spaceAfter=6)
    B = ParagraphStyle("B", parent=st["BodyText"], fontName=FONT, fontSize=9.5, leading=13.5)
    SM = ParagraphStyle("SM", parent=B, fontSize=8.5, textColor=colors.HexColor("#4b5563"))
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm, title=f"Business report - {business_name}", author="Business Detective")

    def footer(c, d):
        c.saveState(); c.setFont(FONT, 8); c.setFillColor(colors.HexColor("#6b7280"))
        c.drawString(18 * mm, 9 * mm, _plain(f"Business Detective · {business_name} · Estimates are based only on the data you uploaded."))
        c.drawRightString(A4[0] - 18 * mm, 9 * mm, f"Page {d.page}"); c.restoreState()

    def _plain(s): return s if FONT != "Helvetica" else s.replace("·", "-").encode("cp1252", "replace").decode("cp1252")

    k, h = bundle["kpis"], bundle["health"]
    S = [Paragraph("Business report", H1), Paragraph(_t(f"{business_name} · data from {k['start']} to {k['end']} · generated {datetime.now(timezone.utc):%Y-%m-%d}"), SM),
         HRFlowable(width="100%", color=BRAND, thickness=1.2, spaceBefore=6, spaceAfter=8)]

    S.append(Paragraph("Executive summary", H2))
    alerts = bundle["monitoring"]["alerts"]
    crit = [a for a in alerts if a["severity"] in ("Critical", "High")]
    lines = []
    if h["overall"] is not None:
        lines.append(f"Business health is <b>{h['overall']}/100</b> across {len(h['categories'])} assessed area(s).")
    else:
        lines.append("Not enough data to calculate a business health score.")
    p = k.get("period")
    if p and p.get("revenue_change_pct") is not None:
        lines.append(f"Revenue over the last {p['days']} days was <b>{_money(p['revenue'], cur)}</b> ({p['revenue_change_pct']:+.1f}% versus the previous {p['days']} days).")
    else:
        lines.append(f"Total revenue in the period was <b>{_money(k['revenue'], cur)}</b>. Period-over-period comparison needs more history.")
    lines.append(f"{len(alerts)} issue(s) need attention, {len(crit)} of them high priority." if alerts else "No issues needing attention were detected.")
    for l in lines:
        S.append(Paragraph(_t(l).replace("&lt;b&gt;", "<b>").replace("&lt;/b&gt;", "</b>"), B)); S.append(Spacer(1, 3))

    S.append(Paragraph("Key figures", H2))
    rows = [["Total revenue", _money(k["revenue"], cur)], ["Average daily revenue", _money(k["avg_daily_revenue"], cur)], ["Period covered", f"{k['start']} to {k['end']} ({k['days']} days)"]]
    if k.get("orders") is not None: rows.append(["Orders", f"{k['orders']:,}"])
    if bundle.get("profitability"):
        pr = bundle["profitability"]; rows += [["Gross profit", _money(pr["profit"], cur)], ["Gross margin", f"{pr['margin_pct']:.1f}%" if pr["margin_pct"] is not None else "n/a"]]
    if p and p.get("profit") is not None: rows.append([f"Profit, last {p['days']} days", _money(p["profit"], cur)])
    S.append(_table(rows, [60 * mm, 110 * mm]))

    if h["categories"]:
        S.append(Paragraph("Business health by area", H2))
        S.append(_table([[a, f"{v['score']}/100", "; ".join(v["factors"])] for a, v in h["categories"].items()], [32 * mm, 22 * mm, 116 * mm]))

    S.append(Paragraph("Important alerts", H2))
    if not alerts:
        S.append(Paragraph("No alerts. Nothing unusual was detected in the available data.", B))
    for a in alerts[:8]:
        S.append(_insight_block(a, B, SM))

    ops = bundle["monitoring"]["opportunities"]
    if ops:
        S.append(Paragraph("Opportunities", H2))
        for a in ops:
            S.append(_insight_block(a, B, SM))

    S.append(Paragraph("Trends", H2))
    mrows = [["Month", "Revenue"] + (["Margin"] if bundle.get("profitability") else [])]
    for m in bundle["monthly"][-12:]:
        mrows.append([m["month"] + (" (partial)" if m["partial"] else ""), _money(m["revenue"], cur)] + ([f"{m['margin_pct']:.1f}%" if m.get("margin_pct") is not None else "n/a"] if bundle.get("profitability") else []))
    S.append(_table(mrows, None, header=True))
    f = bundle["forecast"]
    S.append(Spacer(1, 4))
    S.append(Paragraph(_t(("Forecast (estimate): about " + _money(sum(x["value"] for x in f["forecast"]), cur) + f" over the next {len(f['forecast'])} days. " + (f.get("quality_note") or ""))
                          if f.get("available") else "Forecast unavailable: " + (f.get("message") or "")), B))

    S.append(Paragraph("Recommendations", H2))
    for n, r in enumerate(bundle["recommendations"][:8], 1):
        if r["priority"] == "Low" and n > 5: continue
        S.append(KeepTogether([Paragraph(_t(f"{n}. [{r['priority']}] {r['title']}"), ParagraphStyle("rt", parent=B, fontName=FONT_B)),
                               Paragraph(_t(f"Recommended action: {r['action']}"), B), Paragraph(_t(f"Evidence: {r['evidence']}  ·  Confidence {round(r['confidence'] * 100)}%"), SM), Spacer(1, 5)]))
    if not bundle["recommendations"]:
        S.append(Paragraph("No recommendations: nothing needs action right now.", B))

    S.append(Paragraph("Actions", H2))
    if actions:
        S.append(_table([["Action", "Status", "Due", "Owner"]] + [[a["title"], a["status"].replace("_", " "), a.get("due_date") or "-", a.get("assignee") or "-"] for a in actions[:25]], [80 * mm, 26 * mm, 26 * mm, 38 * mm], header=True))
    else:
        S.append(Paragraph("No actions have been created yet.", B))

    S.append(Paragraph("About these numbers", H2))
    S.append(Paragraph(_t("All figures come from your uploaded data. Impact figures, stock-cover days and forecasts are estimates, not guarantees. “Possible contributing factors” show where a change is concentrated; they do not prove a cause."), SM))
    doc.build(S, onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()


def _table(rows, widths, header=False):
    cells = [[Paragraph(_t(c), ParagraphStyle("c", fontName=FONT_B if (header and r == 0) else FONT, fontSize=8.8, leading=11.5, textColor=colors.white if (header and r == 0) else colors.HexColor("#111827"))) for c in row] for r, row in enumerate(rows)]
    t = Table(cells, colWidths=widths, repeatRows=1 if header else 0)
    style = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("ROWBACKGROUNDS", (0, 1 if header else 0), (-1, -1), [colors.white, colors.HexColor("#f9fafb")])]
    if header: style.append(("BACKGROUND", (0, 0), (-1, 0), BRAND))
    t.setStyle(TableStyle(style))
    return t


def _insight_block(a, B, SM):
    col = SEV_COL.get(a["severity"], "#374151")
    head = ParagraphStyle("ih", parent=B, fontName=FONT_B, textColor=colors.HexColor(col))
    return KeepTogether([Paragraph(_t(f"[{a['severity']}] {a['title']}"), head), Paragraph(_t("What: " + a["what"]), B), Paragraph(_t("Why it matters: " + a["why"]), B),
                         Paragraph(_t("Impact: " + a["impact_text"]), B), Paragraph(_t("Evidence: " + "; ".join(a["evidence"])), SM), Paragraph(_t("What to do: " + a["action"]), B),
                         Paragraph(_t(f"Confidence {round(a['confidence'] * 100)}% · detected {a.get('detected_on') or '-'}"), SM), Spacer(1, 7)])
