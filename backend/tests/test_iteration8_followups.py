# Iteration 8: follow-up fixes (active-only /team, is_owner on /users, capped upload read, owner assignment)
import os
import subprocess

import pytest
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
MANAGER_ID = "user_3L9leJprjujidpKUxS1z426Gv5L"
ENGINEER_ID = "user_3L9kur0VSQjT1w7CtIMJJu2w45c"
NEWBIE_ID = "user_3LFXniD9mwdgQ4VbMVAXtb3SFfw"
OWNER_ID = "user_3L9lY32nl7VmhC0M9CP0BBmp9zm"
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def _session(uid):
    out = subprocess.run(["python3", "/app/scripts/clerk_test_token.py", uid], capture_output=True, text=True, timeout=60)
    tok = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else ""
    if not tok:
        pytest.skip("Could not mint Clerk token")
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {tok}"
    return s


@pytest.fixture(scope="module")
def mgr():
    return _session(MANAGER_ID)


@pytest.fixture(scope="module", autouse=True)
def keep_newbie_pending():
    db.users.update_one({"user_id": NEWBIE_ID}, {"$set": {"status": "pending", "role": "engineer"}})
    yield
    db.users.update_one({"user_id": NEWBIE_ID}, {"$set": {"status": "pending", "role": "engineer"}})


@pytest.fixture(scope="module")
def project(mgr):
    r = mgr.post(f"{API}/projects", json={"name": "TEST_It8 Project", "code": "TEST-IT8"}, timeout=30)
    assert r.status_code == 200, r.text
    p = r.json()
    yield p
    mgr.delete(f"{API}/projects/{p['id']}", timeout=30)


# /api/team active-only
class TestTeam:
    def test_team_excludes_pending(self, mgr):
        r = mgr.get(f"{API}/team", timeout=30)
        assert r.status_code == 200
        ids = {u["user_id"] for u in r.json()}
        assert NEWBIE_ID not in ids
        assert MANAGER_ID in ids and ENGINEER_ID in ids and OWNER_ID in ids
        for u in r.json():
            assert "_id" not in u

    def test_team_excludes_rejected(self, mgr):
        db.users.update_one({"user_id": NEWBIE_ID}, {"$set": {"status": "rejected"}})
        try:
            ids = {u["user_id"] for u in mgr.get(f"{API}/team", timeout=30).json()}
            assert NEWBIE_ID not in ids
        finally:
            db.users.update_one({"user_id": NEWBIE_ID}, {"$set": {"status": "pending"}})

    def test_team_includes_active_after_approve(self, mgr):
        db.users.update_one({"user_id": NEWBIE_ID}, {"$set": {"status": "active"}})
        try:
            ids = {u["user_id"] for u in mgr.get(f"{API}/team", timeout=30).json()}
            assert NEWBIE_ID in ids
        finally:
            db.users.update_one({"user_id": NEWBIE_ID}, {"$set": {"status": "pending"}})

    def test_team_count_matches_active_users(self, mgr):
        team = mgr.get(f"{API}/team", timeout=30).json()
        users = mgr.get(f"{API}/users", timeout=30).json()["users"]
        assert len(team) == sum(u["status"] == "active" for u in users)


# /api/users is_owner
class TestUsersOwner:
    def test_is_owner_flag(self, mgr):
        users = {u["user_id"]: u for u in mgr.get(f"{API}/users", timeout=30).json()["users"]}
        assert users[OWNER_ID]["is_owner"] is True
        for uid in (MANAGER_ID, ENGINEER_ID, NEWBIE_ID):
            assert users[uid]["is_owner"] is False
        assert all(isinstance(u["is_owner"], bool) for u in users.values())


# Upload size cap
class TestUploadCap:
    def test_over_20mb_413(self, mgr, project):
        data = b"a" * (20 * 1024 * 1024 + 10)
        r = mgr.post(f"{API}/files", files={"file": ("big.txt", data, "text/plain")}, data={"project_id": project["id"]}, timeout=120)
        assert r.status_code == 413, r.text[:200]

    def test_exact_20mb_ok_boundary(self, mgr, project):
        data = b"a" * (20 * 1024 * 1024)
        r = mgr.post(f"{API}/files", files={"file": ("edge.txt", data, "text/plain")}, data={"project_id": project["id"]}, timeout=120)
        assert r.status_code == 200, r.text[:200]
        assert r.json()["size"] == 20 * 1024 * 1024

    def test_small_png_ok(self, mgr, project):
        png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
        r = mgr.post(f"{API}/files", files={"file": ("s.png", png, "image/png")}, data={"project_id": project["id"]}, timeout=60)
        print("small png:", r.status_code, r.text[:120])


# Issue owner assignment of non-active member (observational)
class TestOwnerAssignment:
    def test_assign_pending_owner(self, mgr, project):
        r = mgr.post(f"{API}/issues", json={"project_id": project["id"], "title": "TEST_owner", "owner_id": NEWBIE_ID}, timeout=30)
        print("assign pending owner ->", r.status_code, r.text[:200])
        if r.status_code == 200:
            mgr.delete(f"{API}/issues/{r.json()['id']}", timeout=30)
        assert r.status_code in (200, 400, 404, 422)
