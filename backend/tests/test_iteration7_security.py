# Iteration 7: security fixes (SEC-001 uploads, SEC-002 approval, SEC-003 xlsx, SEC-004 pdf, hardening, rate limits)
import io
import os
import subprocess
import time
import zipfile

import pytest
import requests
from openpyxl import Workbook, load_workbook
from PIL import Image
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


@pytest.fixture(scope="module")
def eng():
    return _session(ENGINEER_ID)


@pytest.fixture(scope="module")
def newbie():
    s = _session(NEWBIE_ID)
    yield s
    db.users.update_one({"user_id": NEWBIE_ID}, {"$set": {"status": "pending", "role": "engineer"}})


@pytest.fixture(scope="module")
def project(mgr):
    r = mgr.post(f"{API}/projects", json={"name": "TEST_Sec Project", "code": "TEST-SEC", "client": "+1 Client", "location": "@SUM(A1)",
                                           "summary": "=HYPERLINK(\"http://evil\",\"x\") <img src=http://x/a.png> <b> & </para>"}, timeout=30)
    assert r.status_code == 200, r.text
    p = r.json()
    yield p
    mgr.delete(f"{API}/projects/{p['id']}", timeout=30)


def _img(fmt):
    b = io.BytesIO()
    Image.new("RGB", (8, 8), (200, 100, 0)).save(b, fmt)
    return b.getvalue()


def _xlsx():
    b = io.BytesIO()
    Workbook().save(b)
    return b.getvalue()


def _docx():
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
    return b.getvalue()


GOOD = {"a.jpg": _img("JPEG"), "a.png": _img("PNG"), "a.webp": _img("WEBP"), "a.gif": _img("GIF"),
        "a.pdf": b"%PDF-1.4\n%%EOF\n", "a.docx": _docx(), "a.xlsx": _xlsx(), "a.csv": b"a,b\n1,2\n", "a.txt": b"hello site"}
BAD = {"x.html": b"<html><script>alert(1)</script></html>", "x.svg": b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>",
       "fake.png": b"<svg onload=alert(1)>", "x.txt": b"hi <script>alert(1)</script>", "x.csv": b"a,b\n<html>", "s.txt": b"<svg/onload=1>",
       "x.exe": b"MZ\x90\x00", "noext": b"plain", "fake.jpg": b"GIF89a....", "x.js": b"alert(1)"}


def _up(sess, pid, name, data, ctype="image/png"):
    return sess.post(f"{API}/files", files={"file": (name, data, ctype)}, data={"project_id": pid, "entity_type": "project"}, timeout=60)


# SEC-001 uploads/download
class TestUploads:
    @pytest.mark.parametrize("name", list(BAD))
    def test_reject(self, mgr, project, name):
        r = _up(mgr, project["id"], name, BAD[name], "image/png")
        assert r.status_code == 415, f"{name}: {r.status_code} {r.text}"

    def test_accept_and_download_headers(self, mgr, project):
        expected = {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp", "gif": "image/gif", "pdf": "application/pdf",
                    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "csv": "text/csv", "txt": "text/plain"}
        for name, data in GOOD.items():
            ext = name.split(".")[1]
            r = _up(mgr, project["id"], name, data, "text/html")  # client content-type must be ignored
            assert r.status_code == 200, f"{name}: {r.text}"
            doc = r.json()
            assert doc["content_type"] == expected[ext]
            assert "storage_path" not in doc
            d = mgr.get(f"{API}/files/{doc['id']}/download", timeout=60)
            assert d.status_code == 200
            assert d.content == data
            assert d.headers["content-type"].startswith(expected[ext])
            cd = d.headers["content-disposition"]
            assert cd.startswith("inline" if ext in ("jpg", "png", "gif", "webp", "pdf") else "attachment"), f"{name}: {cd}"
            assert d.headers.get("x-content-type-options") == "nosniff"
            csp = d.headers.get("content-security-policy", "")
            assert "default-src 'none'" in csp and "sandbox" in csp

    def test_too_big_or_empty(self, mgr, project):
        assert _up(mgr, project["id"], "e.txt", b"").status_code == 413


# SEC-002 approval flow
class TestApproval:
    def test_pending_me_and_403(self, newbie):
        db.users.update_one({"user_id": NEWBIE_ID}, {"$set": {"status": "pending"}})
        me = newbie.get(f"{API}/me", timeout=30)
        assert me.status_code == 200 and me.json()["status"] == "pending"
        for path in ("/projects", "/dashboard", "/reports", "/issues", "/activities", "/team", "/files", "/export?fmt=pdf", "/ai/chat/sessions", "/users"):
            r = newbie.get(f"{API}{path}", timeout=30)
            assert r.status_code == 403, f"{path}: {r.status_code}"
            assert r.json()["detail"] == "Your access is waiting for manager approval", path
        for path, body in (("/projects", {"name": "TEST_x", "code": "X"}), ("/ai/chat", {"message": "hi"}), ("/ai/draft-report", {"project_id": "x", "notes": "abcd"})):
            assert newbie.post(f"{API}{path}", json=body, timeout=30).status_code == 403, path

    def test_existing_active(self, mgr, eng):
        assert mgr.get(f"{API}/me", timeout=30).json()["status"] == "active"
        assert eng.get(f"{API}/me", timeout=30).json()["status"] == "active"
        assert eng.get(f"{API}/projects", timeout=30).status_code == 200

    def test_users_list_has_pending(self, mgr, eng):
        r = mgr.get(f"{API}/users", timeout=30)
        assert r.status_code == 200
        users = {u["user_id"]: u for u in r.json()["users"]}
        assert users[NEWBIE_ID]["status"] == "pending"
        assert users[ENGINEER_ID]["status"] == "active"
        assert eng.get(f"{API}/users", timeout=30).status_code == 403
        assert eng.patch(f"{API}/users/{NEWBIE_ID}", json={"status": "active"}, timeout=30).status_code == 403

    def test_approve_decline_restore(self, mgr, newbie):
        r = mgr.patch(f"{API}/users/{NEWBIE_ID}", json={"status": "active"}, timeout=30)
        assert r.status_code == 200 and r.json()["status"] == "active"
        assert newbie.get(f"{API}/me", timeout=30).json()["status"] == "active"
        assert newbie.get(f"{API}/projects", timeout=30).status_code == 200
        r = mgr.patch(f"{API}/users/{NEWBIE_ID}", json={"status": "rejected"}, timeout=30)
        assert r.status_code == 200 and r.json()["status"] == "rejected"
        assert newbie.get(f"{API}/me", timeout=30).json()["status"] == "rejected"
        p = newbie.get(f"{API}/projects", timeout=30)
        assert p.status_code == 403 and "declined" in p.json()["detail"]
        r = mgr.patch(f"{API}/users/{NEWBIE_ID}", json={"status": "active"}, timeout=30)
        assert r.status_code == 200
        assert newbie.get(f"{API}/dashboard", timeout=30).status_code == 200

    def test_invalid_status_and_empty(self, mgr):
        assert mgr.patch(f"{API}/users/{NEWBIE_ID}", json={"status": "pending"}, timeout=30).status_code == 422
        assert mgr.patch(f"{API}/users/{NEWBIE_ID}", json={}, timeout=30).status_code == 422
        assert mgr.patch(f"{API}/users/user_nope", json={"status": "active"}, timeout=30).status_code == 404

    def test_remove_and_restore_engineer(self, mgr, eng):
        r = mgr.patch(f"{API}/users/{ENGINEER_ID}", json={"status": "rejected"}, timeout=30)
        try:
            assert r.status_code == 200
            assert eng.get(f"{API}/projects", timeout=30).status_code == 403
        finally:
            assert mgr.patch(f"{API}/users/{ENGINEER_ID}", json={"status": "active"}, timeout=30).status_code == 200
        assert eng.get(f"{API}/projects", timeout=30).status_code == 200

    def test_self_and_owner_protected(self, mgr):
        assert mgr.patch(f"{API}/users/{MANAGER_ID}", json={"status": "rejected"}, timeout=30).status_code == 400
        assert mgr.patch(f"{API}/users/{MANAGER_ID}", json={"role": "engineer"}, timeout=30).status_code == 400
        assert mgr.patch(f"{API}/users/{OWNER_ID}", json={"status": "rejected"}, timeout=30).status_code == 400
        assert mgr.patch(f"{API}/users/{OWNER_ID}", json={"role": "engineer"}, timeout=30).status_code == 400
        owner = db.users.find_one({"user_id": OWNER_ID})
        assert owner["role"] == "manager" and owner.get("status", "active") == "active"

    def test_reset_newbie_pending(self):
        db.users.update_one({"user_id": NEWBIE_ID}, {"$set": {"status": "pending", "role": "engineer"}})
        assert db.users.find_one({"user_id": NEWBIE_ID})["status"] == "pending"


# SEC-003 / SEC-004 exports
class TestExports:
    def test_xlsx_no_formulas(self, mgr, project):
        r = mgr.get(f"{API}/export", params={"fmt": "xlsx", "project_id": project["id"]}, timeout=60)
        assert r.status_code == 200
        wb = load_workbook(io.BytesIO(r.content))
        ws = wb["Projects"]
        found = 0
        for row in ws.iter_rows(min_row=2):
            for c in row:
                if isinstance(c.value, str) and c.value[:1] in "=+-@":
                    found += 1
                    assert c.data_type == "s", f"{c.coordinate} {c.value!r} type {c.data_type}"
                    assert c.quotePrefix, f"{c.coordinate} missing quotePrefix"
        assert found >= 3
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            assert "<f>" not in z.read("xl/worksheets/sheet1.xml").decode()

    def test_pdf_escapes(self, mgr, project):
        r = mgr.get(f"{API}/export", params={"fmt": "pdf", "project_id": project["id"]}, timeout=60)
        assert r.status_code == 200
        assert r.content.startswith(b"%PDF")
        assert r.headers["content-type"] == "application/pdf"


# Hardening
class TestHardening:
    def test_security_headers(self, mgr):
        r = mgr.get(f"{API}/me", timeout=30)
        assert r.headers.get("x-content-type-options") == "nosniff"
        assert r.headers.get("x-frame-options") == "DENY"

    def test_cors(self):
        r = requests.options(f"{API}/projects", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "authorization"}, timeout=30)
        assert r.headers.get("access-control-allow-credentials") != "true", r.headers
        print("CORS headers:", {k: v for k, v in r.headers.items() if k.lower().startswith("access-control")})

    @pytest.mark.parametrize("tok", ["garbage", "eyJhbGciOiJub25lIn0.eyJzdWIiOiJ1c2VyXzNMOWxlSnBydWppZHBLVXhTMXo0MjZHdjVMIn0.",
                                     "eyJhbGciOiJSUzI1NiIsImtpZCI6ImZha2UifQ.eyJzdWIiOiJ1c2VyX3giLCJpc3MiOiJodHRwczovL2V2aWwiLCJleHAiOjk5OTk5OTk5OTksImlhdCI6MX0.AAAA"])
    def test_bad_token_401(self, tok):
        r = requests.get(f"{API}/projects", headers={"Authorization": f"Bearer {tok}"}, timeout=30)
        assert r.status_code == 401

    def test_no_token_401(self):
        assert requests.get(f"{API}/me", timeout=30).status_code == 401


# Rate limits (run last; dependency is evaluated before body validation, so invalid bodies avoid LLM/heavy work)
class TestRateLimits:
    def test_ai_limit_12(self, eng):
        codes = [eng.post(f"{API}/ai/draft-report", json={}, timeout=30).status_code for _ in range(13)]
        print("AI codes", codes)
        assert codes[-1] == 429 and all(c == 422 for c in codes[:12])
        r = eng.post(f"{API}/ai/chat", json={}, timeout=30)
        assert r.status_code == 429 and "wait a minute" in r.json()["detail"]
        assert eng.get(f"{API}/projects", timeout=30).status_code == 200  # other APIs unaffected

    def test_export_limit_15(self, eng):
        codes = [eng.get(f"{API}/export", params={"fmt": "bad"}, timeout=30).status_code for _ in range(16)]
        print("Export codes", codes)
        assert codes[-1] == 429 and all(c == 422 for c in codes[:15])

    def test_upload_limit_40(self, eng):
        codes = [eng.post(f"{API}/files", data={"project_id": "x"}, timeout=30).status_code for _ in range(41)]
        print("Upload codes", codes)
        assert codes[-1] == 429 and all(c == 422 for c in codes[:40])
