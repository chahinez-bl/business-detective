import io

import pytest

from . import synthetic as syn
from .conftest import upload_and_analyze


# ---------------------------------------------------------------- authentication
def test_register_login_me_logout(client):
    r = client.post("/api/auth/register", json={"email": "Jane@Example.com", "name": "Jane", "password": "Str0ngPass!"})
    assert r.status_code == 201 and r.json()["user"]["email"] == "jane@example.com" and "password" not in r.text
    assert client.post("/api/auth/register", json={"email": "jane@example.com", "name": "J", "password": "Str0ngPass!"}).status_code == 409
    bad = client.post("/api/auth/login", json={"email": "jane@example.com", "password": "wrong-pass1"})
    assert bad.status_code == 401 and bad.json()["detail"] == "Incorrect email or password."
    tok = client.post("/api/auth/login", json={"email": "jane@example.com", "password": "Str0ngPass!"}).json()["token"]
    h = {"Authorization": f"Bearer {tok}"}
    assert client.get("/api/auth/me", headers=h).json()["user"]["name"] == "Jane"
    assert client.post("/api/auth/logout", headers=h).status_code == 200
    assert client.get("/api/auth/me", headers=h).status_code == 401           # token revoked server-side


def test_password_rules_and_hashing(client):
    for pw in ("short1", "alllettersonly", "12345678901"):
        assert client.post("/api/auth/register", json={"email": f"{pw}@x.com", "name": "x", "password": pw}).status_code == 422
    from app.database import SessionLocal
    from app.models import User
    client.post("/api/auth/register", json={"email": "hash@x.com", "name": "x", "password": "Str0ngPass!"})
    with SessionLocal() as db:
        assert db.query(User).filter_by(email="hash@x.com").one().password_hash.startswith("$2")


def test_protected_routes_reject_anonymous_and_garbage_tokens(client, user, business):
    for method, url in [("get", "/api/auth/me"), ("get", "/api/businesses"), ("get", f"/api/businesses/{business['id']}/workspace"), ("post", f"/api/businesses/{business['id']}/reports")]:
        assert getattr(client, method)(url).status_code == 401
        assert getattr(client, method)(url, headers={"Authorization": "Bearer abc.def.ghi"}).status_code == 401


def test_login_throttle(client, user):
    for _ in range(8):
        assert client.post("/api/auth/login", json={"email": user.email, "password": "nope-nope1"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": user.email, "password": "Passw0rd!x"}).status_code == 429


# ---------------------------------------------------------------- business
def test_business_create_validate_update(user):
    assert user.post("/businesses", json={"name": "", "currency": "DZD"}).status_code == 422
    r = user.post("/businesses", json={"name": "Shop", "currency": "xyz"})
    assert r.status_code == 422 and "Choose one of" in r.json()["detail"]
    b = user.post("/businesses", json={"name": "Shop", "industry": "Retail", "currency": "eur"}).json()
    assert b["currency"] == "EUR" and b["role"] == "owner"
    assert user.patch(f"/businesses/{b['id']}", json={"currency": "USD"}).json()["currency"] == "USD"
    assert [x["id"] for x in user.get("/businesses").json()] == [b["id"]]


# ---------------------------------------------------------------- the full customer journey, three differently-structured files
def _journey(user, business, content, filename, expect_caps):
    up, val, an = upload_and_analyze(user, business["id"], content, filename)
    assert an.status_code == 200, an.text
    assert val["can_analyze"] and 0 < val["score"] <= 100 and val["rows_accepted"] > 0
    w = user.get(f"/businesses/{business['id']}/workspace").json()
    assert w["has_data"] and w["mode"] == "customer"
    for k, v in expect_caps.items():
        assert w["capabilities"][k]["available"] is v, k
    mon = user.get(f"/businesses/{business['id']}/monitoring").json()
    assert mon["status"] in ("Normal", "Attention", "Warning", "Critical") and len(mon["areas"]) == 7
    ins = user.get(f"/businesses/{business['id']}/insights").json()
    recs = user.get(f"/businesses/{business['id']}/recommendations").json()
    dc = user.get(f"/businesses/{business['id']}/decision-center").json()
    assert ins and recs and dc["count"] > 0 and len(recs) == len(ins)
    one = user.get(f"/businesses/{business['id']}/insights/{ins[0]['id']}").json()
    assert all(one[k] for k in ("what", "why", "impact_text", "evidence", "action"))
    return w, ins


def test_journey_csv_dataset_a(user, business):
    w, ins = _journey(user, business, syn.to_csv_bytes(syn.dataset_a()), "sales.csv", dict(sales=True, products=True, inventory=False, profitability=False, customers=False))
    assert w["dataset"]["filename"] == "sales.csv" and w["currency"] == "DZD"


def test_journey_semicolon_cp1252_french_dataset_b(user, business):
    w, _ = _journey(user, business, syn.to_csv_bytes(syn.dataset_b(), sep=";", encoding="cp1252"), "ventes.csv", dict(sales=True, inventory=True, profitability=False))
    assert any(p["product"] == "Café" for p in w["products"])


def test_journey_xlsx_dataset_c_with_currency(user):
    b = user.post("/businesses", json={"name": "Furniture", "currency": "EUR"}).json()
    w, ins = _journey(user, b, syn.to_xlsx_bytes(syn.dataset_c()), "orders.xlsx", dict(customers=True, profitability=True, inventory=False))
    assert w["currency"] == "EUR" and any("EUR" in i["impact_text"] for i in ins if i["impact_amount"])


def test_manual_mapping_override(user, business):
    df = syn.dataset_a().rename(columns={"Date": "Col1", "Product": "Col2", "Revenue": "Col3", "Quantity": "Col4"})
    up = user.post(f"/businesses/{business['id']}/datasets/upload", files={"file": ("weird.csv", syn.to_csv_bytes(df))}).json()
    did = up["dataset"]["id"]
    assert "date" not in up["suggested_mapping"] or up["suggested_mapping"].get("date") == "Col1"     # content-based date detection may find it
    blocked = user.post(f"/businesses/{business['id']}/datasets/{did}/validate", json={"mapping": {"product": "Col2"}}).json()
    assert not blocked["can_analyze"] and any(i["code"] == "no_amount" for i in blocked["issues"])
    mp = {"date": "Col1", "product": "Col2", "revenue": "Col3", "quantity": "Col4"}
    assert user.post(f"/businesses/{business['id']}/datasets/{did}/analyze", json={"mapping": mp}).status_code == 200


def test_invalid_mappings_are_friendly(user, business):
    up = user.post(f"/businesses/{business['id']}/datasets/upload", files={"file": ("a.csv", syn.to_csv_bytes(syn.dataset_a()))}).json()
    did = up["dataset"]["id"]
    for mp, text in [({"date": "Nope"}, "do not exist"), ({"date": "Date", "revenue": "Date"}, "two different fields"), ({"banana": "Date"}, "Unknown field")]:
        r = user.post(f"/businesses/{business['id']}/datasets/{did}/validate", json={"mapping": mp})
        assert r.status_code == 422 and text in r.json()["detail"] and "Traceback" not in r.text


# ---------------------------------------------------------------- malformed / hostile uploads
@pytest.mark.parametrize("name,content,code", [
    ("data.txt", b"hello", 415), ("data.exe", b"MZ", 415), ("empty.csv", b"", 422), ("blank.csv", b"   \n\n", 422),
    ("fake.xlsx", b"this is not excel", 422), ("bin.csv", b"\x00\x01\x02\x03" * 50, 422), ("onecol.csv", b"a\n1\n2\n", 422),
])
def test_bad_uploads_get_friendly_errors(user, business, name, content, code):
    r = user.post(f"/businesses/{business['id']}/datasets/upload", files={"file": (name, content)})
    assert r.status_code == code and isinstance(r.json()["detail"], str) and "Traceback" not in r.text and "Error" not in r.json()["detail"][:12]


def test_corrupted_xlsx_zip(user, business):
    r = user.post(f"/businesses/{business['id']}/datasets/upload", files={"file": ("c.xlsx", b"PK\x03\x04" + b"garbage" * 100)})
    assert r.status_code == 422 and "corrupted" in r.json()["detail"].lower()


def test_file_too_large(user, business, monkeypatch):
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "max_upload_mb", 0)
    r = user.post(f"/businesses/{business['id']}/datasets/upload", files={"file": ("big.csv", b"a,b\n1,2\n" * 10)})
    assert r.status_code == 413 and "too large" in r.json()["detail"]


def test_path_traversal_filename_is_neutralised(user, business):
    r = user.post(f"/businesses/{business['id']}/datasets/upload", files={"file": ("../../etc/passwd.csv", syn.to_csv_bytes(syn.dataset_a()))})
    assert r.status_code == 201 and "/" not in r.json()["dataset"]["filename"] and ".." not in r.json()["dataset"]["filename"]


def test_malformed_data_reports_issues(user, business):
    df = syn.dataset_a().iloc[:120].astype(object).copy()
    df.loc[:5, "Revenue"] = "n/a"; df.loc[6:9, "Date"] = "31/31/2026"
    _, val, an = upload_and_analyze(user, business["id"], syn.to_csv_bytes(df), "dirty.csv")
    codes = {i["code"] for i in val["issues"]}
    assert an.status_code == 200 and {"invalid_revenue", "invalid_dates"} <= codes and val["rows_rejected"] >= 10 and val["score"] < 100


def test_insufficient_data_blocks_analysis_with_explanation(user, business):
    df = syn.dataset_a(days=1).iloc[:3]
    _, val, an = upload_and_analyze(user, business["id"], syn.to_csv_bytes(df), "tiny.csv")
    assert an.status_code == 422 and not val["can_analyze"] and "quality" in an.json() and "enough usable data" in an.json()["detail"]
    assert user.get(f"/businesses/{business['id']}/workspace").json()["has_data"] is False


def test_short_history_is_analysed_but_forecast_unavailable(user, business):
    _, val, an = upload_and_analyze(user, business["id"], syn.to_csv_bytes(syn.dataset_a(days=12)), "short.csv")
    assert an.status_code == 200
    w = user.get(f"/businesses/{business['id']}/workspace").json()
    assert not w["forecast"]["available"] and "28 days" in w["forecast"]["message"] and w["health"]["overall"] is None


def test_datasets_are_kept_not_wiped(user, business):
    upload_and_analyze(user, business["id"], syn.to_csv_bytes(syn.dataset_a()), "one.csv")
    upload_and_analyze(user, business["id"], syn.to_csv_bytes(syn.dataset_b()), "two.csv")
    names = [d["filename"] for d in user.get(f"/businesses/{business['id']}/datasets").json()]
    assert names == ["two.csv", "one.csv"]
    assert user.get(f"/businesses/{business['id']}/workspace").json()["dataset"]["filename"] == "two.csv"     # latest analysis drives the workspace


# ---------------------------------------------------------------- actions
def test_action_lifecycle(user, business):
    bid = business["id"]
    upload_and_analyze(user, bid, syn.to_csv_bytes(syn.dataset_a()), "s.csv")
    ins = user.get(f"/businesses/{bid}/insights").json()[0]
    rec = user.get(f"/businesses/{bid}/recommendations").json()[0]
    a = user.post(f"/businesses/{bid}/actions", json={"title": "Check Alpha stock", "note": "call supplier", "insight_id": ins["id"], "recommendation_id": rec["id"],
                                                     "assignee_id": user.user["id"], "due_date": "2030-01-31"})
    assert a.status_code == 201 and a.json()["status"] == "todo" and a.json()["assignee"] == "Tester" and a.json()["source_title"] == ins["title"]
    aid = a.json()["id"]
    assert user.patch(f"/businesses/{bid}/actions/{aid}", json={"status": "in_progress", "note": "waiting"}).json()["status"] == "in_progress"
    done = user.patch(f"/businesses/{bid}/actions/{aid}", json={"status": "resolved"}).json()
    assert done["status"] == "resolved" and done["resolved_at"]
    assert user.patch(f"/businesses/{bid}/actions/{aid}", json={"status": "bogus"}).status_code == 422
    assert user.patch(f"/businesses/{bid}/actions/{aid}", json={"status": "dismissed", "clear_due_date": True}).json()["due_date"] is None
    assert user.get(f"/businesses/{bid}/actions", params={"status": "dismissed"}).json()[0]["id"] == aid
    w = user.get(f"/businesses/{bid}/workspace").json()          # an in-progress action is reflected in the decision centre
    user.patch(f"/businesses/{bid}/actions/{aid}", json={"status": "todo"})
    top = user.get(f"/businesses/{bid}/insights").json()[0]
    assert top["action_item"]["status"] == "todo"
    assert user.delete(f"/businesses/{bid}/actions/{aid}").status_code == 200


# ---------------------------------------------------------------- reports
def test_report_pdf(user, business):
    bid = business["id"]
    assert user.post(f"/businesses/{bid}/reports").status_code == 404           # nothing analysed yet
    upload_and_analyze(user, bid, syn.to_xlsx_bytes(syn.dataset_c()), "o.xlsx")
    r = user.post(f"/businesses/{bid}/reports")
    assert r.status_code == 201
    d = user.get(f"/businesses/{bid}/reports/{r.json()['id']}/download")
    assert d.status_code == 200 and d.headers["content-type"] == "application/pdf" and d.content.startswith(b"%PDF") and len(d.content) > 3000
    assert len(user.get(f"/businesses/{bid}/reports").json()) == 1


# ---------------------------------------------------------------- assistant + simulator (grounded)
def test_assistant_is_grounded_and_admits_ignorance(user, business):
    bid = business["id"]
    upload_and_analyze(user, bid, syn.to_csv_bytes(syn.dataset_a()), "s.csv")
    a = user.post(f"/businesses/{bid}/ask", json={"question": "Why did my revenue drop?"}).json()
    assert a["grounded"] and "Alpha" in a["answer"] and "not proven causes" in a["answer"]
    n = user.post(f"/businesses/{bid}/ask", json={"question": "What will the weather be?"}).json()
    assert n["answer"].startswith("I don't have enough data to answer that reliably")
    assert user.post(f"/businesses/{bid}/ask", json={"question": "Which products may run out of stock?"}).json()["answer"].startswith("I don't have enough data")   # no stock column


def test_assistant_rejects_invented_numbers_from_external_ai(monkeypatch):
    from app.analytics import assistant
    from app.config import get_settings
    s = get_settings()
    for k, v in dict(ai_provider="openai_compatible", ai_api_url="http://x", ai_api_key="k", ai_model="m").items():
        monkeypatch.setattr(s, k, v)

    class R:
        def __init__(self, t): self.t = t
        def json(self): return {"choices": [{"message": {"content": self.t}}]}
    monkeypatch.setattr(assistant.httpx, "post", lambda *a, **k: R("Sales fell 99% to 12345."))
    assert assistant.external_rephrase("q", "Revenue changed -7.3%.") is None
    monkeypatch.setattr(assistant.httpx, "post", lambda *a, **k: R("Revenue is down 7.3%."))
    assert assistant.external_rephrase("q", "Revenue changed -7.3%.") == "Revenue is down 7.3%."


def test_simulate_endpoint(user, business):
    bid = business["id"]
    upload_and_analyze(user, bid, syn.to_xlsx_bytes(syn.dataset_c()), "o.xlsx")
    r = user.post(f"/businesses/{bid}/simulate", json={"product": "Chair", "price_pct": 5, "cost_pct": 0, "volume_pct": -10})
    assert r.status_code == 200 and "SIMULATION" in r.json()["label"] and any(x["metric"].startswith("Gross profit") for x in r.json()["rows"])
    assert user.post(f"/businesses/{bid}/simulate", json={"product": "Ghost"}).status_code == 422


# ---------------------------------------------------------------- demo is separate from customer data
def test_demo_is_public_labelled_and_never_in_customer_workspace(client, user, business):
    d = client.get("/api/demo/workspace").json()
    assert d["mode"] == "demo" and "demo" in d["business"]["name"].lower() and d["insights"]
    w = user.get(f"/businesses/{business['id']}/workspace").json()
    assert w["has_data"] is False and "insights" not in w                       # a new customer workspace is EMPTY, never pre-filled with Nova Market
    assert client.post("/api/demo/ask", json={"question": "What should I restock first?"}).json()["grounded"]


def test_errors_do_not_leak_internals(client):
    r = client.get("/api/does-not-exist")
    assert r.status_code == 404 and "Traceback" not in r.text
    r = client.post("/api/auth/login", json={"email": "not-an-email", "password": "x"})
    assert r.status_code == 422 and isinstance(r.json()["detail"], str)
