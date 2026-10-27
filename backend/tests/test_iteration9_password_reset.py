# Iteration 9: manager password reset (POST /api/users/{id}/password), /me is_owner, Clerk password errors
import os
import subprocess
import time

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
ENGINEER_PW = "CivicPro#Test2026"
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
CLERK_H = {"Authorization": f"Bearer {os.environ['CLERK_SECRET_KEY']}", "Content-Type": "application/json"}


def _verify_pw(uid, pw):
    r = requests.post(f"https://api.clerk.com/v1/users/{uid}/verify_password", headers=CLERK_H, json={"password": pw}, timeout=15)
    return r.status_code == 200 and r.json().get("verified") is True


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


@pytest.fixture(scope="module")
def eng():
    return _session(ENGINEER_ID)


class TestPasswordReset:
    def test_me_requires_token(self):
        assert requests.get(f"{API}/me").status_code == 401

    def test_me_is_owner(self, mgr):
        r = mgr.get(f"{API}/me")
        assert r.status_code == 200
        assert r.json()["is_owner"] is False
        assert r.json()["role"] == "manager"

    def test_no_token_401(self):
        assert requests.post(f"{API}/users/{ENGINEER_ID}/password", json={"password": "abcdefgh12"}).status_code == 401

    def test_engineer_forbidden(self, eng):
        r = eng.post(f"{API}/users/{NEWBIE_ID}/password", json={"password": "Zq9!xLmw#2026pw"})
        assert r.status_code == 403, r.text

    def test_self_400(self, mgr):
        r = mgr.post(f"{API}/users/{MANAGER_ID}/password", json={"password": "Zq9!xLmw#2026pw"})
        assert r.status_code == 400, r.text

    def test_owner_403(self, mgr):
        r = mgr.post(f"{API}/users/{OWNER_ID}/password", json={"password": "Zq9!xLmw#2026pw"})
        assert r.status_code == 403, r.text

    def test_other_manager_403(self, mgr):
        db.users.update_one({"user_id": ENGINEER_ID}, {"$set": {"role": "manager"}})
        try:
            r = mgr.post(f"{API}/users/{ENGINEER_ID}/password", json={"password": "Zq9!xLmw#2026pw"})
            assert r.status_code == 403, r.text
        finally:
            db.users.update_one({"user_id": ENGINEER_ID}, {"$set": {"role": "engineer"}})

    def test_unknown_404(self, mgr):
        r = mgr.post(f"{API}/users/user_doesnotexist123/password", json={"password": "Zq9!xLmw#2026pw"})
        assert r.status_code == 404, r.text

    def test_short_422(self, mgr):
        r = mgr.post(f"{API}/users/{ENGINEER_ID}/password", json={"password": "short"})
        assert r.status_code == 422, r.text

    def test_weak_breached_422_clerk_message(self, mgr):
        r = mgr.post(f"{API}/users/{ENGINEER_ID}/password", json={"password": "password123"})
        print("weak:", r.status_code, r.text)
        assert r.status_code == 422, r.text
        assert isinstance(r.json()["detail"], str) and len(r.json()["detail"]) > 5
        assert _verify_pw(ENGINEER_ID, ENGINEER_PW)

    def test_success_and_audit_then_restore(self, mgr):
        new_pw = "TEST_Reset#9xQw2026"
        before = db.audit_log.count_documents({"action": "password_reset", "target_id": ENGINEER_ID})
        try:
            r = mgr.post(f"{API}/users/{ENGINEER_ID}/password", json={"password": new_pw})
            assert r.status_code == 200, r.text
            assert r.json() == {"ok": True}
            assert _verify_pw(ENGINEER_ID, new_pw)
            assert not _verify_pw(ENGINEER_ID, ENGINEER_PW)
            log = db.audit_log.find_one({"action": "password_reset", "target_id": ENGINEER_ID}, sort=[("created_at", -1)])
            assert db.audit_log.count_documents({"action": "password_reset", "target_id": ENGINEER_ID}) == before + 1
            assert log["actor_id"] == MANAGER_ID
        finally:
            time.sleep(1)
            r2 = mgr.post(f"{API}/users/{ENGINEER_ID}/password", json={"password": ENGINEER_PW})
            assert r2.status_code == 200, r2.text
            assert _verify_pw(ENGINEER_ID, ENGINEER_PW)
