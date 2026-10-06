"""Second browser journey: Excel upload with customers and costs (different structure from the CSV journey)."""
import sys, time
from pathlib import Path
from playwright.sync_api import expect, sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
ROOT = Path(__file__).resolve().parent.parent
errs = []
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1300, "height": 900})
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("response", lambda r: r.status >= 500 and errs.append(f"{r.status} {r.url}"))
    pg.goto(BASE + "/register"); pg.get_by_label("Your name").fill("Omar"); pg.get_by_label("Work email").fill(f"x{int(time.time())}@example.com"); pg.get_by_label("Password").fill("Journey123!")
    pg.get_by_role("button", name="Create account").click(); pg.wait_for_url("**/onboarding")
    pg.get_by_label("Business name").fill("Meubles Oran"); pg.get_by_role("button", name="Create my workspace").click(); pg.wait_for_url("**/app/import")
    pg.locator("input[type=file]").set_input_files(str(ROOT / "data/samples/sample_c_orders.xlsx"))
    pg.get_by_role("button", name="Looks right — continue").click(); pg.get_by_role("button", name="Review and confirm").click()
    for lbl in ["Customer", "Unit purchase cost"]:
        assert pg.get_by_label(lbl, exact=False).first.input_value() != "", lbl
    pg.get_by_role("button", name="Check my data").click(); expect(pg.get_by_text("Checks passed")).to_be_visible(timeout=15000)
    pg.get_by_role("button", name="Analyze my business").click(); pg.wait_for_url("**/app/monitoring", timeout=60000)
    pg.goto(BASE + "/app/customers"); expect(pg.get_by_text("Did not return")).to_be_visible(); expect(pg.locator("th", has_text="Orders")).to_be_visible()
    pg.goto(BASE + "/app/profitability"); expect(pg.get_by_text("Gross margin")).to_be_visible(); expect(pg.get_by_text("Margin by product")).to_be_visible()
    pg.goto(BASE + "/app/inventory"); expect(pg.get_by_text("does not contain the required information")).to_be_visible()
    pg.goto(BASE + "/app/insights"); expect(pg.get_by_text("Selling below cost: Lamp")).to_be_visible()
    pg.screenshot(path="/tmp/bd_shots/10_xlsx_insights.png", full_page=True)
    print("✔ XLSX journey: customers + profitability available, inventory honestly unavailable, below-cost product found")
    b.close()
print("errors:", errs or "none"); sys.exit(1 if errs else 0)
