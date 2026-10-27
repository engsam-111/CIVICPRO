"""Iteration 10: project creation file-flow API checks (create, upload, download, auth protection)."""
import base64
import os
import subprocess
import uuid

import pytest
import requests


BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")
if not BASE_URL:
    try:
        with open("/app/frontend/.env", "r", encoding="utf-8") as env_file:
            for line in env_file:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    BASE_URL = line.split("=", 1)[1].strip()
                    break
    except FileNotFoundError:
        BASE_URL = None
if not BASE_URL:
    pytest.skip("REACT_APP_BACKEND_URL is not set", allow_module_level=True)
BASE_URL = BASE_URL.rstrip("/")
API = f"{BASE_URL}/api"
MANAGER_ID = "user_3L9leJprjujidpKUxS1z426Gv5L"


def _token(uid: str) -> str:
    out = subprocess.run(["python3", "/app/scripts/clerk_test_token.py", uid], capture_output=True, text=True, timeout=60)
    tok = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else ""
    if not tok:
        pytest.skip(f"Could not mint Clerk token: {out.stderr[-300:]}")
    return tok


@pytest.fixture(scope="session")
def manager_session():
    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {_token(MANAGER_ID)}"
    return session


@pytest.fixture
def created_projects(manager_session):
    ids = []
    yield ids
    for pid in ids:
        manager_session.delete(f"{API}/projects/{pid}", timeout=30)


def _create_test_project(session: requests.Session, suffix: str) -> dict:
    payload = {
        "name": f"TEST_ProjectFiles_{suffix}",
        "code": f"TPF-{suffix[:6]}",
        "location": "QA",
        "client": "QA Client",
        "progress": 0,
        "status": "Active",
        "summary": "iteration10 file feature test",
    }
    res = session.post(f"{API}/projects", json=payload, timeout=30)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["name"] == payload["name"]
    assert data["code"] == payload["code"]
    assert isinstance(data["id"], str) and data["id"]
    return data


# Module: create project without files
def test_create_project_without_files_still_works(manager_session, created_projects):
    project = _create_test_project(manager_session, uuid.uuid4().hex[:8])
    created_projects.append(project["id"])

    detail = manager_session.get(f"{API}/projects/{project['id']}", timeout=30)
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["project"]["id"] == project["id"]
    assert body["files"] == []


# Module: file upload + download + metadata
def test_create_then_upload_two_files_and_download(manager_session, created_projects):
    project = _create_test_project(manager_session, uuid.uuid4().hex[:8])
    created_projects.append(project["id"])

    txt_bytes = b"Iteration10 text file content for project attachment."
    png_bytes = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9l9iQAAAAASUVORK5CYII="
    )

    txt_upload = manager_session.post(
        f"{API}/files",
        files={"file": ("site-notes.txt", txt_bytes, "text/plain")},
        data={"project_id": project["id"], "entity_type": "project", "entity_id": project["id"]},
        timeout=60,
    )
    assert txt_upload.status_code == 200, txt_upload.text
    txt_file = txt_upload.json()
    assert txt_file["entity_type"] == "project"
    assert txt_file["entity_id"] == project["id"]
    assert txt_file["original_filename"] == "site-notes.txt"
    assert "storage_path" not in txt_file

    png_upload = manager_session.post(
        f"{API}/files",
        files={"file": ("snapshot.png", png_bytes, "image/png")},
        data={"project_id": project["id"], "entity_type": "project", "entity_id": project["id"]},
        timeout=60,
    )
    assert png_upload.status_code == 200, png_upload.text
    png_file = png_upload.json()
    assert png_file["original_filename"] == "snapshot.png"
    assert "storage_path" not in png_file

    detail = manager_session.get(f"{API}/projects/{project['id']}", timeout=30)
    assert detail.status_code == 200, detail.text
    files = detail.json()["files"]
    names = {f["original_filename"] for f in files}
    assert {"site-notes.txt", "snapshot.png"}.issubset(names)
    assert all("storage_path" not in f for f in files)

    download_txt = manager_session.get(f"{API}/files/{txt_file['id']}/download", timeout=60)
    assert download_txt.status_code == 200
    assert download_txt.content == txt_bytes
    assert "site-notes.txt" in download_txt.headers.get("Content-Disposition", "")

    download_png = manager_session.get(f"{API}/files/{png_file['id']}/download", timeout=60)
    assert download_png.status_code == 200
    assert download_png.content == png_bytes
    assert "snapshot.png" in download_png.headers.get("Content-Disposition", "")


# Module: partial upload failure behavior
def test_partial_failure_invalid_pdf_then_later_success(manager_session, created_projects):
    project = _create_test_project(manager_session, uuid.uuid4().hex[:8])
    created_projects.append(project["id"])

    first_txt = manager_session.post(
        f"{API}/files",
        files={"file": ("first-valid.txt", b"first valid text", "text/plain")},
        data={"project_id": project["id"], "entity_type": "project", "entity_id": project["id"]},
        timeout=60,
    )
    assert first_txt.status_code == 200, first_txt.text

    invalid_pdf = manager_session.post(
        f"{API}/files",
        files={"file": ("invalid-content.pdf", b"this is not real pdf bytes", "application/pdf")},
        data={"project_id": project["id"], "entity_type": "project", "entity_id": project["id"]},
        timeout=60,
    )
    assert invalid_pdf.status_code == 415
    assert "allowed" in invalid_pdf.text.lower() or "only" in invalid_pdf.text.lower()

    second_txt = manager_session.post(
        f"{API}/files",
        files={"file": ("second-valid.txt", b"second valid text", "text/plain")},
        data={"project_id": project["id"], "entity_type": "project", "entity_id": project["id"]},
        timeout=60,
    )
    assert second_txt.status_code == 200, second_txt.text

    detail = manager_session.get(f"{API}/projects/{project['id']}", timeout=30)
    assert detail.status_code == 200
    body = detail.json()
    assert body["project"]["id"] == project["id"]
    names = [f["original_filename"] for f in body["files"]]
    assert "first-valid.txt" in names
    assert "second-valid.txt" in names
    assert "invalid-content.pdf" not in names


# Module: download auth protection
def test_download_requires_auth_token(manager_session, created_projects):
    project = _create_test_project(manager_session, uuid.uuid4().hex[:8])
    created_projects.append(project["id"])
    up = manager_session.post(
        f"{API}/files",
        files={"file": ("auth-check.txt", b"auth protected download", "text/plain")},
        data={"project_id": project["id"], "entity_type": "project", "entity_id": project["id"]},
        timeout=60,
    )
    assert up.status_code == 200, up.text
    fid = up.json()["id"]

    no_auth = requests.get(f"{API}/files/{fid}/download", timeout=20)
    assert no_auth.status_code == 401

    yes_auth = manager_session.get(f"{API}/files/{fid}/download", timeout=60)
    assert yes_auth.status_code == 200
    assert yes_auth.content == b"auth protected download"
