"""Real-browser acceptance test of the full customer journey against a running server (default http://127.0.0.1:8000).
Usage:  pip install playwright && playwright install chromium && python e2e/journey.py [BASE_URL]"""
import re
import sys
import time
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
ROOT = Path(__file__).resolve().parent.parent
SHOTS = Path("/tmp/bd_shots"); SHOTS.mkdir(exist_ok=True)
EMAIL = f"e2e{int(time.time())}@example.com"; PASSWORD = "Journey123!"
errors: list[str] = []


def step(msg): print("✔", msg, flush=True)


with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_context(viewport={"width": 1366, "height": 900}, accept_downloads=True).new_page()
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    page.on("console", lambda m: m.type == "error" and errors.append(f"console: {m.text}"))
    page.on("response", lambda r: r.status >= 500 and errors.append(f"HTTP {r.status} {r.url}"))

    # 1. public website + demo
    page.goto(BASE); expect(page.get_by_role("heading", name="Turn your business data into decisions.", level=1)).to_be_visible()
    for t in ["Product", "Features", "How it works", "Demo", "Pricing", "FAQ", "Contact"]:
        expect(page.get_by_role("navigation", name="Main").get_by_role("link", name=t, exact=True)).to_be_visible()
    page.screenshot(path=SHOTS / "01_home.png"); step("public website renders with required navigation")
    for path in ["/product", "/features", "/how-it-works", "/pricing", "/faq", "/privacy", "/contact", "/login", "/register"]:
        page.goto(BASE + path); expect(page.locator("main")).not_to_be_empty()
    step("all public pages load")
    page.goto(BASE); page.get_by_role("link", name="Explore demo").first.click(); page.wait_for_url("**/demo/overview")
    expect(page.get_by_text("Demo data — fictional").first).to_be_visible(); expect(page.get_by_role("heading", name="Needs attention")).to_be_visible(timeout=15000)
    page.screenshot(path=SHOTS / "02_demo_overview.png")
    for sub in ["monitoring", "decision-center", "insights", "sales", "products", "inventory", "suppliers", "profitability", "forecast", "what-if", "assistant"]:
        page.goto(f"{BASE}/demo/{sub}"); expect(page.locator("main h1").first).to_be_visible(timeout=15000)
    page.goto(f"{BASE}/demo/customers"); expect(page.get_by_text("does not contain the required information")).to_be_visible()
    step("demo mode works (labelled fictional; customers page honestly unavailable)")

    # 2. register -> onboarding -> create business
    page.goto(BASE + "/register"); page.get_by_label("Your name").fill("Jane Owner"); page.get_by_label("Work email").fill(EMAIL); page.get_by_label("Password").fill(PASSWORD)
    page.get_by_role("button", name="Create account").click(); page.wait_for_url("**/app/onboarding")
    page.get_by_label("Business name").fill("Café Alger"); page.get_by_label("Currency").select_option("EUR"); page.get_by_role("button", name="Create my workspace").click()
    page.wait_for_url("**/app/import"); page.screenshot(path=SHOTS / "03_import.png"); step("registered, logged in, business workspace created")

    # 3. a new workspace must be EMPTY (no demo data)
    page.goto(BASE + "/app/overview"); expect(page.get_by_text("Getting started")).to_be_visible()
    body = page.inner_text("body"); assert "Nova" not in body and "Premium Coffee" not in body and "Olive Oil" not in body
    page.goto(BASE + "/app/monitoring"); expect(page.get_by_text("No analysis yet")).to_be_visible(); step("new customer workspace is empty (no demo data leaks in)")

    # 4. import wizard with a French, semicolon-separated, cp1252 CSV
    page.goto(BASE + "/app/import")
    page.locator("input[type=file]").set_input_files(str(ROOT / "data/samples/sample_b_ventes_fr.csv"))
    expect(page.get_by_text("First rows of your file")).to_be_visible(timeout=15000); page.screenshot(path=SHOTS / "04_preview.png")
    page.get_by_role("button", name="Looks right — continue").click()
    expect(page.get_by_text("Here's what we detected")).to_be_visible(); expect(page.get_by_text("TransactionDate")).to_be_visible(); expect(page.get_by_text("Article")).to_be_visible()
    page.get_by_role("button", name="Review and confirm").click()
    page.get_by_role("button", name="Check my data").click()
    expect(page.get_by_text("Checks passed")).to_be_visible(timeout=15000); expect(page.get_by_text("What you'll get")).to_be_visible()
    page.screenshot(path=SHOTS / "05_quality.png"); step("upload → preview → detected columns → confirm → data quality")
    page.get_by_role("button", name="Analyze my business").click(); page.wait_for_url("**/app/monitoring", timeout=60000)
    expect(page.get_by_role("heading", name="Business monitor")).to_be_visible(); step("analysis completed, monitoring dashboard opened")

    # 5. monitoring -> insight -> recommendation -> decision center -> action
    expect(page.get_by_role("heading", name="Active alerts")).to_be_visible(); page.screenshot(path=SHOTS / "06_monitoring.png", full_page=True)
    page.get_by_role("button", name=re.compile("Why it matters")).first.click(); expect(page.get_by_text("What to do").first).to_be_visible(); step("alert opens with what / why / impact / evidence / action")
    page.get_by_role("button", name="Create action").first.click(); page.get_by_label("Note").fill("Called the supplier"); page.get_by_role("button", name="Save action").click()
    expect(page.get_by_text(re.compile("Action: todo"))).to_be_visible(timeout=10000)
    page.goto(BASE + "/app/decision-center"); expect(page.get_by_text("What should I do today?").first).to_be_visible(); page.screenshot(path=SHOTS / "07_decision.png", full_page=True)
    page.goto(BASE + "/app/actions"); expect(page.get_by_text("To do (1)")).to_be_visible(); page.get_by_role("button", name="Start").click()
    expect(page.get_by_text("In progress (1)")).to_be_visible(); page.get_by_role("button", name="Mark resolved").click(); expect(page.get_by_text("Resolved (1)")).to_be_visible()
    step("decision center + action lifecycle (todo → in progress → resolved)")
    page.goto(BASE + "/app/recommendations"); expect(page.get_by_text("Recommended action").first).to_be_visible()
    page.goto(BASE + "/app/inventory"); expect(page.get_by_text("Estimated cover")).to_be_visible(); page.screenshot(path=SHOTS / "08_inventory.png")
    page.goto(BASE + "/app/customers"); expect(page.get_by_text("does not contain the required information")).to_be_visible()
    page.goto(BASE + "/app/profitability"); expect(page.get_by_text("does not contain the required information")).to_be_visible()
    page.goto(BASE + "/app/assistant"); page.get_by_role("button", name="Which products may run out of stock?").click(); expect(page.locator(".chat .m").nth(1)).to_contain_text("Café")
    page.goto(BASE + "/app/what-if"); page.get_by_role("button", name="Run simulation").click(); expect(page.get_by_text("SIMULATION").first).to_be_visible()
    step("capability gating honest; assistant grounded; what-if labelled as simulation")
    page.goto(BASE + "/app/overview")
    expect(page.get_by_text("EUR").first).to_be_visible(); step("business currency (EUR) used instead of hardcoded DA")

    # 6. report
    page.goto(BASE + "/app/reports")
    with page.expect_download(timeout=60000) as dl: page.get_by_role("button", name="Generate PDF report").click()
    path = dl.value.path(); data = Path(path).read_bytes(); assert data.startswith(b"%PDF") and len(data) > 3000; Path(SHOTS / "report.pdf").write_bytes(data); step(f"PDF report generated and downloaded ({len(data)//1024} KB)")

    # 7. logout / protected routes / login again, data persists
    page.goto(BASE + "/app/settings"); page.get_by_role("button", name="Sign out").first.click(); page.wait_for_url(BASE + "/")
    page.goto(BASE + "/app/overview"); page.wait_for_url("**/login"); step("logout works; protected route redirects to login")
    page.get_by_label("Email").fill(EMAIL); page.get_by_label("Password").fill("wrong-password1"); page.get_by_role("button", name="Sign in").click(); expect(page.get_by_text("Incorrect email or password.")).to_be_visible()
    page.get_by_label("Password").fill(PASSWORD); page.get_by_role("button", name="Sign in").click(); page.wait_for_url("**/app**")
    page.goto(BASE + "/app/overview"); expect(page.get_by_role("heading", name="Needs attention")).to_be_visible(timeout=15000); step("returned later: login restores the workspace and its analysis")

    # 8. mobile viewport
    m = b.new_context(viewport={"width": 390, "height": 800}).new_page(); m.goto(BASE); expect(m.get_by_role("heading", name="Turn your business data into decisions.", level=1)).to_be_visible()
    assert m.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), "horizontal overflow on mobile"; m.screenshot(path=SHOTS / "09_mobile.png"); step("mobile layout has no horizontal overflow")
    b.close()

real = [e for e in errors if "favicon" not in e and "401" not in e and "Failed to load resource" not in e]
print("\nBrowser errors:", real or "none")
sys.exit(1 if real else 0)
