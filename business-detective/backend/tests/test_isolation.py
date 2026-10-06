"""User A must never be able to read or modify User B's business data (and vice versa)."""
from . import synthetic as syn
from .conftest import upload_and_analyze


def test_cross_user_isolation(client, make_user):
    a, b = make_user("Alice"), make_user("Bob")
    ba = a.post("/businesses", json={"name": "Alice Store", "currency": "DZD"}).json()
    bb = b.post("/businesses", json={"name": "Bob Store", "currency": "EUR"}).json()
    up_a, _, _ = upload_and_analyze(a, ba["id"], syn.to_csv_bytes(syn.dataset_a()), "alice.csv")
    upload_and_analyze(b, bb["id"], syn.to_xlsx_bytes(syn.dataset_c()), "bob.xlsx")
    did_a = up_a["dataset"]["id"]
    ins_a = a.get(f"/businesses/{ba['id']}/insights").json()[0]["id"]
    act_a = a.post(f"/businesses/{ba['id']}/actions", json={"title": "secret plan", "insight_id": ins_a}).json()["id"]
    rep_a = a.post(f"/businesses/{ba['id']}/reports").json()["id"]

    # Bob cannot touch ANY of Alice's resources through ANY endpoint (404, not 403: ids cannot be probed)
    A = ba["id"]
    probes = [("get", f"/businesses/{A}"), ("get", f"/businesses/{A}/workspace"), ("get", f"/businesses/{A}/overview"), ("get", f"/businesses/{A}/monitoring"),
              ("get", f"/businesses/{A}/insights"), ("get", f"/businesses/{A}/insights/{ins_a}"), ("get", f"/businesses/{A}/recommendations"), ("get", f"/businesses/{A}/decision-center"),
              ("get", f"/businesses/{A}/datasets"), ("get", f"/businesses/{A}/datasets/{did_a}"), ("get", f"/businesses/{A}/actions"), ("get", f"/businesses/{A}/reports"),
              ("get", f"/businesses/{A}/reports/{rep_a}/download"), ("get", f"/businesses/{A}/members"), ("delete", f"/businesses/{A}"), ("delete", f"/businesses/{A}/datasets/{did_a}"),
              ("delete", f"/businesses/{A}/actions/{act_a}")]
    for method, url in probes:
        r = getattr(b, method)(url)
        assert r.status_code == 404, (method, url, r.status_code)
    for url, body in [(f"/businesses/{A}/ask", {"question": "hello there"}), (f"/businesses/{A}/simulate", {}), (f"/businesses/{A}/actions", {"title": "x"}),
                      (f"/businesses/{A}/datasets/{did_a}/analyze", {"mapping": {}}), (f"/businesses/{A}/members", {"email": b.email})]:
        assert b.post(url, json=body).status_code == 404, url
    assert b.patch(f"/businesses/{A}", json={"name": "hacked"}).status_code == 404
    assert b.patch(f"/businesses/{A}/actions/{act_a}", json={"status": "resolved"}).status_code == 404
    assert b.post(f"/businesses/{A}/datasets/upload", files={"file": ("x.csv", b"a,b\n1,2")}).status_code == 404

    # Bob's own data is untouched and contains nothing of Alice's
    mine = b.get(f"/businesses/{bb['id']}/workspace").json()
    assert mine["dataset"]["filename"] == "bob.xlsx" and "Alpha" not in str(mine["products"]) and mine["currency"] == "EUR"
    assert [x["id"] for x in b.get("/businesses").json()] == [bb["id"]]
    assert a.get(f"/businesses/{A}/workspace").json()["dataset"]["filename"] == "alice.csv"

    # Cross-business references inside Bob's own business are rejected too
    r = b.post(f"/businesses/{bb['id']}/actions", json={"title": "sneaky", "insight_id": ins_a})
    assert r.status_code == 422
    assert b.post(f"/businesses/{bb['id']}/datasets/{did_a}/validate", json={"mapping": {}}).status_code == 404


def test_roles_viewer_is_read_only(make_user):
    owner, viewer = make_user("Owner"), make_user("Viewer")
    b = owner.post("/businesses", json={"name": "Team Store"}).json()
    upload_and_analyze(owner, b["id"], syn.to_csv_bytes(syn.dataset_a()), "s.csv")
    assert owner.post(f"/businesses/{b['id']}/members", json={"email": viewer.email, "role": "viewer"}).status_code == 201
    assert viewer.get(f"/businesses/{b['id']}/workspace").json()["has_data"]
    assert viewer.post(f"/businesses/{b['id']}/datasets/upload", files={"file": ("x.csv", syn.to_csv_bytes(syn.dataset_a()))}).status_code == 403
    assert viewer.post(f"/businesses/{b['id']}/actions", json={"title": "x"}).status_code == 403
    assert viewer.post(f"/businesses/{b['id']}/reports").status_code == 403
    assert viewer.patch(f"/businesses/{b['id']}", json={"name": "x"}).status_code == 403
    assert viewer.post(f"/businesses/{b['id']}/members", json={"email": owner.email}).status_code == 403
    assert viewer.delete(f"/businesses/{b['id']}").status_code == 403
    assert owner.post(f"/businesses/{b['id']}/members", json={"email": "ghost@nowhere.com"}).status_code == 404


def test_deleting_business_removes_files(user):
    import os
    from app.services.ingest import business_dir
    b = user.post("/businesses", json={"name": "Temp"}).json()
    upload_and_analyze(user, b["id"], syn.to_csv_bytes(syn.dataset_a()), "s.csv")
    d = business_dir(b["id"])
    assert any(os.scandir(d))
    assert user.delete(f"/businesses/{b['id']}").status_code == 200 and not d.exists()
    assert user.get(f"/businesses/{b['id']}").status_code == 404
