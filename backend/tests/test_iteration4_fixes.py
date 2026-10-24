# Regression tests for iteration_3 minor fixes: report PATCH, owner demotion guard, export report_date window, dashboard active KPI
import io
import os
import subprocess
from datetime import date, timedelta

import openpyxl
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
MANAGER_ID = "user_3L9leJprjujidpKUxS1z426Gv5L"
ENGINEER_ID = "user_3L9kur0VSQjT1w7CtIMJJu2w45c"
OWNER_ID = "user_3L9lY32nl7VmhC0M9CP0BBmp9zm"


def _token(uid):
    out = subprocess.run(["python3", "/app/scripts/clerk_test_token.py", uid], capture_output=True, text=True, timeout=60)
    tok = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else ""
    if not tok:
        pytest.skip(f"Could not mint Clerk token: {out.stderr[-300:]}")
    return tok


def _session(uid):
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {_token(uid)}"
    return s


@pytest.fixture(scope="module")
def mgr():
    return _session(MANAGER_ID)


@pytest.fixture(scope="module")
def eng():
    return _session(ENGINEER_ID)


@pytest.fixture(scope="module")
def project(eng):
    r = eng.post(f"{API}/projects", json={"name": "TEST_IT4 Project", "code": "TIT4-1", "progress": 10})
    assert r.status_code == 200, r.text
    p = r.json()
    yield p
    eng.delete(f"{API}/projects/{p['id']}")


def _xlsx_text(content):
    wb = openpyxl.load_workbook(io.BytesIO(content))
    return " ".join(str(c.value) for ws in wb.worksheets for row in ws.iter_rows() for c in row if c.value is not None)


# Reports PATCH
class TestReportEdit:
    def test_patch_report_persists(self, eng, project):
        r = eng.post(f"{API}/reports", json={"project_id": project["id"], "title": "TEST_orig", "summary": "s1", "report_type": "Daily", "workforce": 3})
        assert r.status_code == 200
        rid = r.json()["id"]
        u = eng.patch(f"{API}/reports/{rid}", json={"title": "TEST_edited", "report_type": "Weekly", "workforce": 12, "summary": "s2"})
        assert u.status_code == 200, u.text
        assert u.json()["title"] == "TEST_edited" and u.json()["workforce"] == 12
        got = [x for x in eng.get(f"{API}/reports", params={"project_id": project["id"]}).json() if x["id"] == rid][0]
        assert got["title"] == "TEST_edited" and got["report_type"] == "Weekly" and got["summary"] == "s2"
        assert got["project_id"] == project["id"]

    def test_patch_report_404(self, eng):
        assert eng.patch(f"{API}/reports/nope", json={"title": "x"}).status_code == 404

    def test_patch_report_invalid(self, eng, project):
        r = eng.post(f"{API}/reports", json={"project_id": project["id"], "title": "TEST_v", "summary": "s"}).json()
        assert eng.patch(f"{API}/reports/{r['id']}", json={"report_type": "Monthly"}).status_code == 422
        assert eng.patch(f"{API}/reports/{r['id']}", json={"progress": 150}).status_code == 422

    def test_patch_report_empty_title(self, eng, project):
        # Records current behaviour: empty title accepted? (no min_length on ReportPatch)
        r = eng.post(f"{API}/reports", json={"project_id": project["id"], "title": "TEST_e", "summary": "s"}).json()
        resp = eng.patch(f"{API}/reports/{r['id']}", json={"title": ""})
        print("empty title PATCH status:", resp.status_code)
        assert resp.status_code in (200, 422)


# Owner demotion guard
class TestOwnerGuard:
    def test_demote_owner_400(self, mgr):
        users = mgr.get(f"{API}/users").json()["users"]
        owner = [u for u in users if u["user_id"] == OWNER_ID]
        assert owner and owner[0]["role"] == "manager"
        for role in ("engineer", "supervisor"):
            r = mgr.patch(f"{API}/users/{OWNER_ID}", json={"role": role})
            assert r.status_code == 400, r.text
            assert "owner" in r.json()["detail"].lower()
        owner = [u for u in mgr.get(f"{API}/users").json()["users"] if u["user_id"] == OWNER_ID][0]
        assert owner["role"] == "manager"

    def test_owner_set_manager_ok(self, mgr):
        assert mgr.patch(f"{API}/users/{OWNER_ID}", json={"role": "manager"}).status_code == 200

    def test_engineer_cannot(self, eng):
        assert eng.patch(f"{API}/users/{OWNER_ID}", json={"role": "engineer"}).status_code == 403


# Export window by report_date
class TestExportWindow:
    @pytest.mark.parametrize("days", [0, 367, -1])
    def test_days_out_of_range(self, eng, days):
        assert eng.get(f"{API}/export", params={"fmt": "xlsx", "days": days}).status_code == 422

    @pytest.mark.parametrize("days", [1, 366])
    def test_days_bounds_ok(self, eng, days):
        r = eng.get(f"{API}/export", params={"fmt": "pdf", "days": days})
        assert r.status_code == 200 and r.content[:4] == b"%PDF"

    def test_filters_by_report_date(self, eng, project):
        today = date.today().isoformat()
        old = (date.today() - timedelta(days=10)).isoformat()
        eng.post(f"{API}/reports", json={"project_id": project["id"], "title": "TEST_TODAYREP", "summary": "s", "report_date": today})
        eng.post(f"{API}/reports", json={"project_id": project["id"], "title": "TEST_BACKDATED", "summary": "s", "report_date": old})
        d1 = _xlsx_text(eng.get(f"{API}/export", params={"fmt": "xlsx", "days": 1, "project_id": project["id"]}).content)
        assert "TEST_TODAYREP" in d1 and "TEST_BACKDATED" not in d1
        d7 = _xlsx_text(eng.get(f"{API}/export", params={"fmt": "xlsx", "days": 7, "project_id": project["id"]}).content)
        assert "TEST_TODAYREP" in d7 and "TEST_BACKDATED" not in d7
        full = _xlsx_text(eng.get(f"{API}/export", params={"fmt": "xlsx", "project_id": project["id"]}).content)
        assert "TEST_TODAYREP" in full and "TEST_BACKDATED" in full


# Dashboard KPI counts only Active / At risk
class TestDashboardKpi:
    def test_active_projects_count(self, eng, project):
        h = eng.post(f"{API}/projects", json={"name": "TEST_IT4 Hold", "code": "TIT4-H", "status": "On hold"}).json()
        c = eng.post(f"{API}/projects", json={"name": "TEST_IT4 Done", "code": "TIT4-C", "status": "Completed"}).json()
        try:
            d = eng.get(f"{API}/dashboard").json()
            expected = sum(p["status"] in ("Active", "At risk") for p in d["projects"])
            assert d["kpis"]["projects"] == expected
            assert d["kpis"]["projects"] < len(d["projects"])
        finally:
            eng.delete(f"{API}/projects/{h['id']}")
            eng.delete(f"{API}/projects/{c['id']}")
