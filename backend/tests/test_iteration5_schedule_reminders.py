# Iteration 5: Planned vs Actual (S-curve, variance) + Overdue Reminders cron + team owner select + exports
import io
import os
import subprocess
import time
import uuid
from datetime import date, datetime, timedelta, timezone

import openpyxl
import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
MANAGER_ID = "user_3L9leJprjujidpKUxS1z426Gv5L"
ENGINEER_ID = "user_3L9kur0VSQjT1w7CtIMJJu2w45c"
load_dotenv("/app/backend/.env")
CRON_SECRET = os.environ.get("WEBHOOK_CRON_SECRET")
DB = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
TODAY = datetime.now(timezone.utc).date()


def smooth(start, end, day):
    x = min(1, max(0, (day - start).days / (end - start).days))
    return round(100 * (3 * x ** 2 - 2 * x ** 3), 1)


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


START, END = date(2026, 1, 1), date(2027, 1, 1)


@pytest.fixture(scope="module")
def proj(eng):
    r = eng.post(f"{API}/projects", json={"name": "TEST_IT5 Sched", "code": "TIT5-1", "progress": 20, "start_date": START.isoformat(), "end_date": END.isoformat()})
    assert r.status_code == 200, r.text
    p = r.json()
    r2 = eng.post(f"{API}/projects", json={"name": "TEST_IT5 NoDates", "code": "TIT5-2", "progress": 5})
    p2 = r2.json()
    yield p, p2
    eng.delete(f"{API}/projects/{p['id']}")
    eng.delete(f"{API}/projects/{p2['id']}")


# ---------- project date validation ----------
class TestDates:
    def test_finish_before_start_422(self, eng):
        r = eng.post(f"{API}/projects", json={"name": "TEST_bad", "code": "TBAD", "start_date": "2026-05-01", "end_date": "2026-04-01"})
        assert r.status_code == 422 and r.json()["detail"] == "Finish date must be after start date"

    def test_equal_dates_and_bad_format_422(self, eng):
        assert eng.post(f"{API}/projects", json={"name": "TEST_bad", "code": "TBAD", "start_date": "2026-05-01", "end_date": "2026-05-01"}).status_code == 422
        assert eng.post(f"{API}/projects", json={"name": "TEST_bad", "code": "TBAD", "start_date": "garbage"}).status_code == 422
        assert DB.projects.count_documents({"code": "TBAD"}) == 0

    def test_patch_end_before_existing_start_422(self, eng, proj):
        r = eng.patch(f"{API}/projects/{proj[0]['id']}", json={"end_date": "2025-12-01"})
        assert r.status_code == 422 and "after start" in r.json()["detail"]


# ---------- planned vs actual ----------
class TestSchedule:
    def test_projects_list_has_planned_and_variance(self, eng, proj):
        rows = {p["code"]: p for p in eng.get(f"{API}/projects").json()}
        p = rows["TIT5-1"]
        exp = smooth(START, END, TODAY)
        assert p["planned_progress"] == exp
        assert p["schedule_variance"] == round(20 - exp, 1)
        assert rows["TIT5-2"]["planned_progress"] is None and rows["TIT5-2"]["schedule_variance"] is None

    def test_curve_with_dates(self, eng, proj):
        c = eng.get(f"{API}/projects/{proj[0]['id']}/curve").json()
        assert c["planned_today"] == smooth(START, END, TODAY)
        assert c["actual_today"] == 20
        assert c["variance"] == round(20 - c["planned_today"], 1)
        assert c["today"] == TODAY.isoformat()
        dates = [pt["date"] for pt in c["points"]]
        assert dates[0] == START.isoformat() and END.isoformat() in dates and TODAY.isoformat() in dates
        assert dates == sorted(dates)
        planned = [pt["planned"] for pt in c["points"]]
        assert planned[0] == 0 and c["points"][dates.index(END.isoformat())]["planned"] == 100
        assert all(a <= b for a, b in zip(planned, planned[1:]))
        assert all(pt["actual"] is None for pt in c["points"] if pt["date"] > TODAY.isoformat())

    def test_curve_missing_dates(self, eng, proj):
        c = eng.get(f"{API}/projects/{proj[1]['id']}/curve").json()
        assert c == {"points": [], "missing_dates": True}

    def test_curve_404(self, eng):
        assert eng.get(f"{API}/projects/{uuid.uuid4()}/curve").status_code == 404

    def test_activity_progress_updates_actual(self, eng, proj):
        pid = proj[0]["id"]
        a = eng.post(f"{API}/activities", json={"project_id": pid, "name": "TEST act", "progress": 90}).json()
        c = eng.get(f"{API}/projects/{pid}/curve").json()
        assert c["actual_today"] == 90 and c["variance"] == round(90 - c["planned_today"], 1)
        eng.patch(f"{API}/activities/{a['id']}", json={"progress": 30})
        c = eng.get(f"{API}/projects/{pid}/curve").json()
        assert c["actual_today"] == 30
        assert [pt for pt in c["points"] if pt["date"] == TODAY.isoformat()][0]["actual"] == 30
        eng.delete(f"{API}/activities/{a['id']}")

    def test_exports_include_schedule(self, eng, proj):
        r = eng.get(f"{API}/export", params={"fmt": "xlsx", "project_id": proj[0]["id"]})
        assert r.status_code == 200
        ws = openpyxl.load_workbook(io.BytesIO(r.content))["Projects"]
        rows = list(ws.iter_rows(values_only=True))
        hdr = next(r for r in rows if r and "Planned %" in r)
        data = rows[rows.index(hdr) + 1]
        rec = dict(zip(hdr, data))
        assert rec["Start"] == START.isoformat() and rec["Planned %"] == smooth(START, END, TODAY) and rec["Variance %"] is not None
        pdf = eng.get(f"{API}/export", params={"fmt": "pdf", "project_id": proj[0]["id"]})
        assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
        full = eng.get(f"{API}/export", params={"fmt": "pdf"})
        assert full.status_code == 200


# ---------- team + issue owner ----------
class TestOwner:
    def test_team_any_role(self, eng):
        r = eng.get(f"{API}/team")
        assert r.status_code == 200
        ids = {u["user_id"]: u for u in r.json()}
        assert ENGINEER_ID in ids and MANAGER_ID in ids
        assert all("_id" not in u and set(u) <= {"user_id", "name", "email", "role"} for u in r.json())

    def test_team_401(self):
        assert requests.get(f"{API}/team").status_code == 401

    def test_issue_owner_id_and_reminder_reset(self, eng, proj):
        eng_name = DB.users.find_one({"user_id": ENGINEER_ID})
        eng_name = eng_name.get("name") or eng_name.get("email")
        r = eng.post(f"{API}/issues", json={"project_id": proj[0]["id"], "title": "TEST_owner", "owner_id": ENGINEER_ID, "due_date": "2026-01-10"})
        assert r.status_code == 200 and r.json()["owner"] == eng_name
        iid = r.json()["id"]
        assert eng.post(f"{API}/issues", json={"project_id": proj[0]["id"], "title": "TEST_x", "owner_id": "nope"}).status_code == 404
        DB.issues.update_one({"id": iid}, {"$set": {"reminder_sent_at": "2026-01-11T07:00:00+00:00"}})
        # status-only PATCH keeps reminder
        eng.patch(f"{API}/issues/{iid}", json={"status": "In progress"})
        assert "reminder_sent_at" in DB.issues.find_one({"id": iid})
        r = eng.patch(f"{API}/issues/{iid}", json={"due_date": "2026-02-01"})
        assert r.status_code == 200 and "reminder_sent_at" not in r.json()
        assert "reminder_sent_at" not in DB.issues.find_one({"id": iid})
        DB.issues.update_one({"id": iid}, {"$set": {"reminder_sent_at": "x"}})
        r = eng.patch(f"{API}/issues/{iid}", json={"owner_id": MANAGER_ID})
        assert r.status_code == 200 and "reminder_sent_at" not in DB.issues.find_one({"id": iid})
        assert r.json()["owner"] != eng_name
        r = eng.patch(f"{API}/issues/{iid}", json={"owner_id": ""})
        assert r.json()["owner"] == "Unassigned"
        eng.delete(f"{API}/issues/{iid}")


# ---------- cron overdue reminders (2 real runs max) ----------
class TestCron:
    def test_auth(self):
        u = f"{API}/cron/overdue-reminders"
        assert requests.post(u).status_code == 401
        assert requests.post(u, headers={"Authorization": "Bearer wrong"}).status_code == 401
        assert requests.post(u, headers={"Authorization": CRON_SECRET or "x"}).status_code == 401

    def test_run_once_and_no_resend(self, eng, proj):
        assert CRON_SECRET
        pid = proj[0]["id"]
        y = (TODAY - timedelta(days=1)).isoformat()
        mk = lambda t, due, status="Open": eng.post(f"{API}/issues", json={"project_id": pid, "title": t, "owner_id": ENGINEER_ID, "due_date": due, "status": status}).json()["id"]
        a = mk("TEST_due_yesterday", y)
        b = mk("TEST_due_today", TODAY.isoformat())
        c = mk("TEST_resolved_yesterday", y, "Resolved")
        d = mk("TEST_due_8_days_ago", (TODAY - timedelta(days=8)).isoformat())
        e = mk("TEST_due_future", (TODAY + timedelta(days=3)).isoformat())
        f = mk("TEST_no_due", "")
        h = {"Authorization": f"Bearer {CRON_SECRET}", "X-Webhook-Id": f"TEST-{uuid.uuid4()}"}
        r = requests.post(f"{API}/cron/overdue-reminders", headers=h, json={})
        assert r.status_code == 200 and r.json()["status"] == "accepted"
        r2 = requests.post(f"{API}/cron/overdue-reminders", headers=h, json={})
        assert r2.status_code == 200 and r2.json()["status"] == "duplicate"
        for _ in range(30):
            if DB.issues.find_one({"id": a}).get("reminder_sent_at"):
                break
            time.sleep(1)
        first = DB.issues.find_one({"id": a}).get("reminder_sent_at")
        assert first, "reminder_sent_at not set for issue due yesterday"
        for x in (b, c, d, e, f):
            assert "reminder_sent_at" not in DB.issues.find_one({"id": x}), x
        listed = {i["id"]: i for i in eng.get(f"{API}/issues", params={"project_id": pid}).json()}
        assert listed[a]["reminder_sent_at"] == first
        # second real run: must not re-send
        h2 = {"Authorization": f"Bearer {CRON_SECRET}", "X-Webhook-Id": f"TEST-{uuid.uuid4()}"}
        assert requests.post(f"{API}/cron/overdue-reminders", headers=h2).json()["status"] == "accepted"
        time.sleep(6)
        assert DB.issues.find_one({"id": a})["reminder_sent_at"] == first
        for x in (b, c, d, e, f):
            assert "reminder_sent_at" not in DB.issues.find_one({"id": x})
        pytest.reminded_issue = a
