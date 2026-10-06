import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="bd_tests_")
os.environ.update(APP_ENV="development", DATABASE_URL=f"sqlite:///{_tmp}/test.sqlite", STORAGE_DIR=f"{_tmp}/storage", SECRET_KEY="test-secret-key-for-unit-tests-only-0123456789",
                  FRONTEND_DIST=f"{_tmp}/none", AI_PROVIDER="rules")

import itertools  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.security import throttle_reset  # noqa: E402

_n = itertools.count(1)


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _reset_throttle():
    throttle_reset()


class Session:
    def __init__(self, client, email, token, user):
        self.c, self.email, self.token, self.user = client, email, token, user
        self.h = {"Authorization": f"Bearer {token}"}

    def get(self, url, **k): return self.c.get("/api" + url, headers=self.h, **k)
    def post(self, url, **k): return self.c.post("/api" + url, headers=self.h, **k)
    def patch(self, url, **k): return self.c.patch("/api" + url, headers=self.h, **k)
    def delete(self, url, **k): return self.c.delete("/api" + url, headers=self.h, **k)


@pytest.fixture
def make_user(client):
    def _mk(name="Tester"):
        email = f"user{next(_n)}@example.com"
        r = client.post("/api/auth/register", json={"email": email, "name": name, "password": "Passw0rd!x"})
        assert r.status_code == 201, r.text
        return Session(client, email, r.json()["token"], r.json()["user"])
    return _mk


@pytest.fixture
def user(make_user): return make_user()


@pytest.fixture
def business(user):
    r = user.post("/businesses", json={"name": "Test Store", "industry": "Retail", "currency": "DZD"})
    assert r.status_code == 201
    return r.json()


def upload_and_analyze(s, bid, content, filename, mapping=None):
    up = s.post(f"/businesses/{bid}/datasets/upload", files={"file": (filename, content)})
    assert up.status_code == 201, up.text
    did, mp = up.json()["dataset"]["id"], mapping or up.json()["suggested_mapping"]
    v = s.post(f"/businesses/{bid}/datasets/{did}/validate", json={"mapping": mp})
    assert v.status_code == 200, v.text
    an = s.post(f"/businesses/{bid}/datasets/{did}/analyze", json={"mapping": mp})
    return up.json(), v.json(), an
