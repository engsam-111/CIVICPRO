# Iteration 6: AI integration (draft report, issue suggest, chat SSE + sessions privacy)
import json
import os
import subprocess

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
MANAGER_ID = "user_3L9leJprjujidpKUxS1z426Gv5L"
ENGINEER_ID = "user_3L9kur0VSQjT1w7CtIMJJu2w45c"
T = 120


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
def project(mgr):
    ps = mgr.get(f"{API}/projects", timeout=30).json()
    nl = [p for p in ps if p.get("code") == "NL-04"]
    return (nl or ps)[0]


def _sse(sess, body):
    r = sess.post(f"{API}/ai/chat", json=body, stream=True, timeout=T)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("text/event-stream")
    evs = []
    for line in r.iter_lines(decode_unicode=True):
        if line and line.startswith("data: "):
            evs.append(json.loads(line[6:]))
    return evs


# Auth: all AI endpoints require a token
class TestAuth:
    @pytest.mark.parametrize("method,path", [("post", "/ai/draft-report"), ("post", "/ai/issues/x/suggest"), ("post", "/ai/chat"),
                                             ("get", "/ai/chat/sessions"), ("get", "/ai/chat/sessions/x"), ("delete", "/ai/chat/sessions/x")])
    def test_401(self, method, path):
        r = getattr(requests, method)(f"{API}{path}", json={}, timeout=30)
        assert r.status_code == 401, (path, r.status_code)


# Draft report
class TestDraft:
    def test_short_notes_422(self, mgr, project):
        r = mgr.post(f"{API}/ai/draft-report", json={"project_id": project["id"], "notes": "ab"}, timeout=30)
        assert r.status_code == 422

    def test_bad_type_422(self, mgr, project):
        r = mgr.post(f"{API}/ai/draft-report", json={"project_id": project["id"], "notes": "abcdef", "report_type": "Monthly"}, timeout=30)
        assert r.status_code == 422

    def test_bad_project_404(self, mgr):
        r = mgr.post(f"{API}/ai/draft-report", json={"project_id": "nope", "notes": "18 guys poured pier 3"}, timeout=30)
        assert r.status_code == 404

    def test_draft_ok(self, mgr, project):
        notes = "18 guys today, poured pier 3 cap 42m3, pump late 1hr, rain after 3pm, tomorrow rebar pier 4, waiting on RFI 12"
        r = mgr.post(f"{API}/ai/draft-report", json={"project_id": project["id"], "notes": notes, "report_type": "Daily"}, timeout=T)
        assert r.status_code == 200, r.text
        d = r.json()
        print("DRAFT:", d)
        assert set(d) == {"title", "summary", "next_steps", "weather", "workforce", "progress"}
        assert d["title"] and d["summary"] and d["next_steps"]
        assert isinstance(d["workforce"], int) and d["workforce"] == 18
        assert isinstance(d["progress"], int) and 0 <= d["progress"] <= 100
        assert "rain" in d["weather"].lower()


# Issue suggestions
class TestSuggest:
    def test_unknown_404(self, mgr):
        assert mgr.post(f"{API}/ai/issues/nope/suggest", timeout=30).status_code == 404

    def test_suggest_persists(self, mgr, project):
        r = mgr.post(f"{API}/issues", json={"project_id": project["id"], "title": "TEST_AI crane outrigger soft ground", "category": "Risk",
                                             "severity": "Low", "description": "Crane outrigger pad sinking after rain near pier 3"}, timeout=30)
        assert r.status_code in (200, 201), r.text
        iid = r.json()["id"]
        try:
            s = mgr.post(f"{API}/ai/issues/{iid}/suggest", timeout=T)
            assert s.status_code == 200, s.text
            d = s.json()
            print("SUGGEST:", d)
            assert d["severity"] in ("High", "Medium", "Low")
            assert d["rationale"]
            assert 3 <= len(d["actions"]) <= 6
            assert all(a["action"] for a in d["actions"])
            issues = mgr.get(f"{API}/issues", timeout=30).json()
            got = [i for i in issues if i["id"] == iid][0]
            assert got["ai_suggestion"]["rationale"] == d["rationale"]
            assert "_id" not in got
        finally:
            mgr.delete(f"{API}/issues/{iid}", timeout=30)


# Chat SSE + sessions privacy
class TestChat:
    def test_chat_flow(self, mgr, eng):
        evs = _sse(mgr, {"message": "TEST_ What is the actual progress of NL-04? One line."})
        types = [e["type"] for e in evs]
        print("TYPES:", types[:5], len(types))
        assert types[0] == "session" and types[-1] == "done"
        assert "error" not in types
        deltas = [e for e in evs if e["type"] == "delta"]
        assert len(deltas) > 1
        answer = "".join(e["content"] for e in deltas)
        print("ANSWER:", answer)
        assert "NL-04" in answer or "%" in answer
        sid = evs[0]["session_id"]
        try:
            ss = mgr.get(f"{API}/ai/chat/sessions", timeout=30).json()
            assert any(s["id"] == sid for s in ss)
            assert all("_id" not in s for s in ss)
            msgs = mgr.get(f"{API}/ai/chat/sessions/{sid}", timeout=30).json()
            assert [m["role"] for m in msgs] == ["user", "assistant"]
            # follow-up keeps context
            evs2 = _sse(mgr, {"message": "And what is its client? Answer briefly.", "session_id": sid})
            assert evs2[0]["session_id"] == sid
            a2 = "".join(e["content"] for e in evs2 if e["type"] == "delta")
            print("FOLLOWUP:", a2)
            assert a2
            msgs = mgr.get(f"{API}/ai/chat/sessions/{sid}", timeout=30).json()
            assert len(msgs) == 4
            # privacy
            assert eng.get(f"{API}/ai/chat/sessions/{sid}", timeout=30).status_code == 404
            assert eng.delete(f"{API}/ai/chat/sessions/{sid}", timeout=30).status_code == 404
            assert all(s["id"] != sid for s in eng.get(f"{API}/ai/chat/sessions", timeout=30).json())
            r = eng.post(f"{API}/ai/chat", json={"message": "hi", "session_id": sid}, timeout=30)
            assert r.status_code == 404
        finally:
            assert mgr.delete(f"{API}/ai/chat/sessions/{sid}", timeout=30).json() == {"ok": True}
        assert mgr.get(f"{API}/ai/chat/sessions/{sid}", timeout=30).status_code == 404

    def test_empty_message_422(self, mgr):
        assert mgr.post(f"{API}/ai/chat", json={"message": ""}, timeout=30).status_code == 422

    def test_unknown_session_404(self, mgr):
        assert mgr.post(f"{API}/ai/chat", json={"message": "hi", "session_id": "nope"}, timeout=30).status_code == 404
