import os, subprocess, requests
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
API = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
tok = subprocess.run(["python3", "/app/scripts/clerk_test_token.py", "user_3L9leJprjujidpKUxS1z426Gv5L"], capture_output=True, text=True).stdout.strip().splitlines()[-1]
H = {"Authorization": f"Bearer {tok}"}
E = "user_3L9kur0VSQjT1w7CtIMJJu2w45c"
for pw in ["Ab#4kq9Lm", "Xk#83jdPq2!z", "zqxwvplkmnbg"]:
    r = requests.post(f"{API}/users/{E}/password", json={"password": pw}, headers=H)
    print(len(pw), pw, r.status_code, r.text)
r = requests.post(f"{API}/users/{E}/password", json={"password": "CivicPro#Test2026"}, headers=H)
print("restore", r.status_code, r.text)
