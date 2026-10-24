"""CivicPro API regression: auth, projects, activities (weighted progress), reports, issues, files, dashboard, export, team roles."""
import io
import os
import subprocess
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
MANAGER_ID = "user_3L9leJprjujidpKUxS1z426Gv5L"
ENGINEER_ID = "user_3L9kur0VSQjT1w7CtIMJJu2w45c"


def _token(uid):
    out = subprocess.run(["python3", "/app/scripts/clerk_test_token.py", uid], capture_output=True, text=True, timeout=60)
    tok = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else ""
    if not tok:
        pytest.skip(f"Could not mint Clerk token: {out.stderr[-300:]}")
    return tok


@pytest.fixture(scope="session")
def mgr():
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {_token(MANAGER_ID)}"
    return s


@pytest.fixture(scope="session")
def eng():
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {_token(ENGINEER_ID)}"
    return s


@pytest.fixture(scope="session")
def project(eng):
    r = eng.post(f"{API}/projects", json={"name": "TEST_API Project", "code": "TAPI-1", "location": "Lab", "progress": 30})
    assert r.status_code == 200, r.text
    p = r.json()
    yield p
    eng.delete(f"{API}/projects/{p['id']}")


# Auth
class TestAuth:
    def test_no_token_401(self):
        for path in ("/me", "/projects", "/dashboard", "/export", "/users", "/files", "/activities"):
            assert requests.get(f"{API}{path}", timeout=15).status_code == 401, path

    def test_bad_token_401(self):
        assert requests.get(f"{API}/me", headers={"Authorization": "Bearer abc.def.ghi"}).status_code == 401

    def test_me_roles(self, mgr, eng):
        m, e = mgr.get(f"{API}/me").json(), eng.get(f"{API}/me").json()
        assert m["role"] == "manager" and m["email"].startswith("qa.manager")
        assert e["role"] == "engineer" and e["email"].startswith("qa.engineer")
        assert "_id" not in m


# Projects + activities weighted progress
class TestProjects:
    def test_list_has_seed(self, eng):
        codes = {p["code"] for p in eng.get(f"{API}/projects").json()}
        assert {"NL-04", "RD-11", "HA-02"} <= codes

    def test_validation(self, eng):
        assert eng.post(f"{API}/projects", json={"name": "x", "code": "y", "progress": 101}).status_code == 422
        assert eng.post(f"{API}/projects", json={"name": "x", "code": "y", "status": "Bogus"}).status_code == 422
        assert eng.post(f"{API}/projects", json={"name": "", "code": "y"}).status_code == 422

    def test_patch_and_get(self, eng, project):
        r = eng.patch(f"{API}/projects/{project['id']}", json={"status": "At risk", "summary": "TEST summary"})
        assert r.status_code == 200
        d = eng.get(f"{API}/projects/{project['id']}").json()
        assert d["project"]["status"] == "At risk" and d["project"]["summary"] == "TEST summary"
        assert d["project"]["progress_mode"] == "manual" and d["project"]["progress"] == 30

    def test_weighted_progress(self, eng, project):
        a1 = eng.post(f"{API}/activities", json={"project_id": project["id"], "name": "TEST A1", "weight": 3, "progress": 100}).json()
        a2 = eng.post(f"{API}/activities", json={"project_id": project["id"], "name": "TEST A2", "weight": 1, "progress": 0}).json()
        p = eng.get(f"{API}/projects/{project['id']}").json()["project"]
        assert p["progress_mode"] == "activity" and p["activity_count"] == 2 and p["progress"] == 75 and p["manual_progress"] == 30
        assert eng.patch(f"{API}/activities/{a2['id']}", json={"progress": 40}).status_code == 200
        assert eng.get(f"{API}/projects/{project['id']}").json()["project"]["progress"] == 85
        assert eng.patch(f"{API}/activities/{a2['id']}", json={"progress": 150}).status_code == 422
        assert eng.post(f"{API}/activities", json={"project_id": project["id"], "name": "bad", "weight": 0}).status_code == 422
        assert eng.post(f"{API}/activities", json={"project_id": "nope", "name": "bad"}).status_code == 404
        assert eng.delete(f"{API}/activities/{a1['id']}").status_code == 200
        assert eng.get(f"{API}/projects/{project['id']}").json()["project"]["progress"] == 40

    def test_404(self, eng):
        assert eng.get(f"{API}/projects/does-not-exist").status_code == 404
        assert eng.patch(f"{API}/projects/does-not-exist", json={"name": "x"}).status_code == 404


# Reports, issues, files
class TestRecords:
    def test_report_daily_weekly(self, eng, project):
        for t in ("Daily", "Weekly"):
            r = eng.post(f"{API}/reports", json={"project_id": project["id"], "title": f"TEST {t}", "report_type": t, "summary": "work"})
            assert r.status_code == 200 and r.json()["report_type"] == t and r.json()["report_date"]
        assert eng.post(f"{API}/reports", json={"project_id": project["id"], "title": "x", "report_type": "Monthly", "summary": "s"}).status_code == 422
        reps = eng.get(f"{API}/reports", params={"project_id": project["id"]}).json()
        assert len(reps) == 2 and all("files" in r and r["project_name"] == "TEST_API Project" for r in reps)

    def test_issue_and_status(self, eng, project):
        r = eng.post(f"{API}/issues", json={"project_id": project["id"], "title": "TEST issue", "severity": "High", "category": "Risk", "due_date": "2020-01-01"})
        assert r.status_code == 200
        iid = r.json()["id"]
        assert eng.post(f"{API}/issues", json={"project_id": project["id"], "title": "x", "severity": "Critical"}).status_code == 422
        assert eng.patch(f"{API}/issues/{iid}", json={"status": "In progress"}).json()["status"] == "In progress"
        assert eng.patch(f"{API}/issues/{iid}", json={"status": "Closed"}).status_code == 422
        k = eng.get(f"{API}/dashboard").json()["kpis"]
        assert k["overdue"] >= 1 and k["high_open"] >= 1

    def test_file_upload_download_delete(self, eng, project):
        content = b"TEST file content civicpro"
        r = eng.post(f"{API}/files", files={"file": ("test_note.txt", io.BytesIO(content), "text/plain")}, data={"project_id": project["id"], "entity_type": "project"})
        assert r.status_code == 200, r.text
        f = r.json()
        assert "storage_path" not in f and f["size"] == len(content)
        d = eng.get(f"{API}/files/{f['id']}/download")
        assert d.status_code == 200 and d.content == content
        assert any(x["id"] == f["id"] for x in eng.get(f"{API}/projects/{project['id']}").json()["files"])
        assert eng.delete(f"{API}/files/{f['id']}").status_code == 200
        assert eng.get(f"{API}/files/{f['id']}/download").status_code == 404

    def test_file_to_report(self, eng, project):
        rep = eng.get(f"{API}/reports", params={"project_id": project["id"]}).json()[0]
        r = eng.post(f"{API}/files", files={"file": ("site.png", io.BytesIO(b"\x89PNG\r\n\x1a\nfake"), "image/png")}, data={"project_id": project["id"], "entity_type": "report", "entity_id": rep["id"]})
        assert r.status_code == 200
        rep2 = [x for x in eng.get(f"{API}/reports", params={"project_id": project["id"]}).json() if x["id"] == rep["id"]][0]
        assert len(rep2["files"]) == 1
        bad = eng.post(f"{API}/files", files={"file": ("a.txt", io.BytesIO(b"x"), "text/plain")}, data={"project_id": project["id"], "entity_type": "report", "entity_id": "nope"})
        assert bad.status_code == 404


# Dashboard + export
class TestDashboardExport:
    def test_dashboard_shape(self, eng):
        d = eng.get(f"{API}/dashboard").json()
        assert set(d) >= {"projects", "kpis", "severity", "weeks", "feed"}
        assert len(d["weeks"]) == 8 and [s["name"] for s in d["severity"]] == ["High", "Medium", "Low"]
        assert len(d["feed"]) <= 8

    @pytest.mark.parametrize("params", [{"fmt": "pdf"}, {"fmt": "pdf", "days": 1}, {"fmt": "pdf", "days": 7}, {"fmt": "xlsx"}])
    def test_export_portfolio(self, eng, params):
        r = eng.get(f"{API}/export", params=params)
        assert r.status_code == 200
        assert r.content[:4] == (b"%PDF" if params["fmt"] == "pdf" else b"PK\x03\x04")

    def test_export_project(self, eng, project):
        for fmt, magic in (("pdf", b"%PDF"), ("xlsx", b"PK\x03\x04")):
            r = eng.get(f"{API}/export", params={"fmt": fmt, "project_id": project["id"]})
            assert r.status_code == 200 and r.content[:4] == magic
        assert eng.get(f"{API}/export", params={"fmt": "docx"}).status_code == 422


# Team roles
class TestTeam:
    def test_engineer_forbidden(self, eng):
        assert eng.get(f"{API}/users").status_code == 403
        assert eng.patch(f"{API}/users/{ENGINEER_ID}", json={"role": "manager"}).status_code == 403

    def test_manager_lists_and_changes_role(self, mgr):
        d = mgr.get(f"{API}/users").json()
        assert d["roles"] == ["manager", "supervisor", "engineer"]
        assert all("_id" not in u for u in d["users"])
        r = mgr.patch(f"{API}/users/{ENGINEER_ID}", json={"role": "supervisor"})
        assert r.status_code == 200 and r.json()["role"] == "supervisor"
        assert mgr.patch(f"{API}/users/{ENGINEER_ID}", json={"role": "engineer"}).json()["role"] == "engineer"
        assert mgr.patch(f"{API}/users/{ENGINEER_ID}", json={"role": "god"}).status_code == 422
        assert mgr.patch(f"{API}/users/{MANAGER_ID}", json={"role": "engineer"}).status_code == 400
        assert mgr.patch(f"{API}/users/nope", json={"role": "engineer"}).status_code == 404
