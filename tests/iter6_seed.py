import os, subprocess, sys, requests
API = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
tok = subprocess.run(["python3", "/app/scripts/clerk_test_token.py", "user_3L9leJprjujidpKUxS1z426Gv5L"], capture_output=True, text=True).stdout.strip().splitlines()[-1]
s = requests.Session(); s.headers["Authorization"] = f"Bearer {tok}"
if sys.argv[1] == "create":
    p = [p for p in s.get(f"{API}/projects").json() if p["code"] == "NL-04"][0]
    r = s.post(f"{API}/issues", json={"project_id": p["id"], "title": "TEST_UI6 deep excavation shoring crack", "category": "Risk", "severity": "Low", "description": "Crack in shoring wall at abutment B, 4m deep excavation, workers below"})
    print(r.json()["id"])
else:
    for i in s.get(f"{API}/issues").json():
        if i["title"].startswith("TEST_"):
            print("del issue", i["title"], s.delete(f"{API}/issues/{i['id']}").status_code)
    for r in s.get(f"{API}/reports").json():
        if r["title"].startswith("TEST_"):
            print("del report", r["title"], s.delete(f"{API}/reports/{r['id']}").status_code)
    for c in s.get(f"{API}/ai/chat/sessions").json():
        if c["title"].startswith("TEST_"):
            print("del session", c["title"], s.delete(f"{API}/ai/chat/sessions/{c['id']}").status_code)
        else:
            print("kept session", c["title"])
