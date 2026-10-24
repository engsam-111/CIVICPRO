from fastapi import FastAPI, APIRouter, Depends, HTTPException, UploadFile, File, Form, Response, Query, Request, BackgroundTasks
from pymongo.errors import DuplicateKeyError
import hmac
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ReturnDocument, UpdateOne
from pydantic import BaseModel, Field
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional, Literal
from urllib.parse import quote
import os, uuid, logging, requests

load_dotenv(Path(__file__).parent / '.env')
from clerk_auth import clerk_router, require_user  # noqa: E402
from storage import init_storage, put_object, get_object, APP_NAME  # noqa: E402
from exports import build_pdf, build_xlsx  # noqa: E402
from mailer import send_email, overdue_email  # noqa: E402
from schedule import planned_at, build_curve  # noqa: E402

logger = logging.getLogger("civicpro")
client = AsyncIOMotorClient(os.environ['MONGO_URL'])
db = client[os.environ['DB_NAME']]
app = FastAPI(title="CivicPro API")
api = APIRouter(prefix="/api")
ROLES = ["manager", "supervisor", "engineer"]
DEFAULT_ROLE = "engineer"
MAX_FILE = 20 * 1024 * 1024
now = lambda: datetime.now(timezone.utc).isoformat()
ProjectStatus = Literal["Active", "At risk", "On hold", "Completed"]


class ProjectIn(BaseModel):
    name: str = Field(min_length=1)
    code: str = Field(min_length=1)
    location: str = ""
    client: str = ""
    progress: int = Field(ge=0, le=100, default=0)
    status: ProjectStatus = "Active"
    summary: str = ""
    start_date: str = ""
    end_date: str = ""


class ProjectPatch(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    location: Optional[str] = None
    client: Optional[str] = None
    progress: Optional[int] = Field(default=None, ge=0, le=100)
    status: Optional[ProjectStatus] = None
    summary: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class ActivityIn(BaseModel):
    project_id: str
    name: str = Field(min_length=1)
    owner: str = "Unassigned"
    weight: float = Field(gt=0, le=100, default=1)
    progress: int = Field(ge=0, le=100, default=0)
    status: Literal["Not started", "In progress", "Completed"] = "In progress"
    due_date: str = ""


class ActivityPatch(BaseModel):
    name: Optional[str] = None
    owner: Optional[str] = None
    weight: Optional[float] = Field(default=None, gt=0, le=100)
    progress: Optional[int] = Field(default=None, ge=0, le=100)
    status: Optional[Literal["Not started", "In progress", "Completed"]] = None
    due_date: Optional[str] = None


class ReportIn(BaseModel):
    project_id: str
    title: str = Field(min_length=1)
    report_type: Literal["Daily", "Weekly"] = "Daily"
    report_date: str = ""
    summary: str = Field(min_length=1)
    next_steps: str = ""
    weather: str = ""
    workforce: int = Field(ge=0, default=0)
    progress: int = Field(ge=0, le=100, default=0)


class ReportPatch(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1)
    report_type: Optional[Literal["Daily", "Weekly"]] = None
    report_date: Optional[str] = None
    summary: Optional[str] = Field(default=None, min_length=1)
    next_steps: Optional[str] = None
    weather: Optional[str] = None
    workforce: Optional[int] = Field(default=None, ge=0)
    progress: Optional[int] = Field(default=None, ge=0, le=100)


class IssueIn(BaseModel):
    project_id: str
    title: str = Field(min_length=1)
    category: Literal["Issue", "Risk", "Struggle"] = "Issue"
    severity: Literal["High", "Medium", "Low"] = "Medium"
    owner: str = "Unassigned"
    owner_id: str = ""
    due_date: str = ""
    status: Literal["Open", "In progress", "Resolved"] = "Open"
    description: str = ""


class IssuePatch(BaseModel):
    title: Optional[str] = None
    severity: Optional[Literal["High", "Medium", "Low"]] = None
    owner: Optional[str] = None
    owner_id: Optional[str] = None
    due_date: Optional[str] = None
    status: Optional[Literal["Open", "In progress", "Resolved"]] = None
    description: Optional[str] = None


class RolePatch(BaseModel):
    role: Literal["manager", "supervisor", "engineer"]


def _clean(doc):
    doc.pop("_id", None)
    return doc


def _admin_emails():
    return {e.strip().lower() for e in os.environ.get("ADMIN_EMAIL", "").split(",") if e.strip()}


def _clerk_profile(user_id):
    r = requests.get(f"https://api.clerk.com/v1/users/{user_id}", timeout=10, headers={"Authorization": f"Bearer {os.environ['CLERK_SECRET_KEY']}", "User-Agent": "emergent-app"})
    r.raise_for_status()
    u = r.json()
    primary = next((e for e in u["email_addresses"] if e["id"] == u.get("primary_email_address_id")), (u["email_addresses"] or [{}])[0])
    admins = _admin_emails()
    is_admin = any(e["email_address"].lower() in admins and (e.get("verification") or {}).get("status") == "verified" for e in u["email_addresses"])
    name = " ".join(x for x in [u.get("first_name"), u.get("last_name")] if x) or primary.get("email_address", "Team member").split("@")[0]
    return {"email": primary.get("email_address", ""), "name": name, "is_admin": is_admin}


async def current_member(user=Depends(require_user)):
    uid = user["user_id"]
    member = await db.users.find_one({"user_id": uid}, {"_id": 0})
    if not member or not member.get("email"):
        profile = await run_in_threadpool(_clerk_profile, uid)
        update = {"email": profile["email"], "name": profile["name"]}
        if profile["is_admin"]:
            update["role"] = "manager"
        insert = {"user_id": uid, "created_at": now()} | ({} if "role" in update else {"role": DEFAULT_ROLE})
        await db.users.update_one({"user_id": uid}, {"$set": update, "$setOnInsert": insert}, upsert=True)
        member = await db.users.find_one({"user_id": uid}, {"_id": 0})
    if member.get("role") == "admin":
        member["role"] = "manager"
        await db.users.update_one({"user_id": uid}, {"$set": {"role": "manager"}})
    member["role"] = member.get("role") if member.get("role") in ROLES else DEFAULT_ROLE
    return member


async def require_manager(member=Depends(current_member)):
    if member["role"] != "manager":
        raise HTTPException(403, "Only managers can manage the team")
    return member


async def _project(pid):
    p = await db.projects.find_one({"id": pid}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Project not found")
    return p


async def _with_progress(projects):
    acts = await db.activities.find({"project_id": {"$in": [p["id"] for p in projects]}}, {"_id": 0, "project_id": 1, "progress": 1, "weight": 1}).to_list(10000)
    by = {}
    today = datetime.now(timezone.utc).date()
    for a in acts:
        by.setdefault(a["project_id"], []).append(a)
    for p in projects:
        items = by.get(p["id"], [])
        p["manual_progress"] = p.get("progress", 0)
        p["activity_count"] = len(items)
        p["progress_mode"] = "activity" if items else "manual"
        if items:
            total = sum(a.get("weight", 1) for a in items)
            p["progress"] = round(sum(a["progress"] * a.get("weight", 1) for a in items) / total)
        planned = planned_at(p.get("start_date"), p.get("end_date"), today)
        p["planned_progress"] = planned
        p["schedule_variance"] = None if planned is None else round(p["progress"] - planned, 1)
    if projects:
        await db.progress_snapshots.bulk_write([UpdateOne({"project_id": p["id"], "date": today.isoformat()}, {"$set": {"progress": p["progress"], "updated_at": now()}}, upsert=True) for p in projects])
    return projects


async def _enrich(docs, with_files=False):
    names = {p["id"]: p["name"] for p in await db.projects.find({}, {"_id": 0, "id": 1, "name": 1}).to_list(1000)}
    files = {}
    if with_files:
        for f in await db.files.find({"entity_id": {"$in": [d["id"] for d in docs]}, "is_deleted": False}, {"_id": 0, "storage_path": 0}).to_list(5000):
            files.setdefault(f["entity_id"], []).append(f)
    for d in docs:
        d["project_name"] = names.get(d.get("project_id"), "Unknown project")
        if with_files:
            d["files"] = files.get(d["id"], [])
    return docs


async def _list(coll, project_id=None, with_files=False, since=None, since_field="created_at"):
    q = {"project_id": project_id} if project_id else {}
    if since:
        q[since_field] = {"$gte": since}
    docs = await db[coll].find(q, {"_id": 0}).sort("created_at", -1).to_list(5000)
    return await _enrich(docs, with_files)


async def _create(coll, body, member):
    if hasattr(body, "project_id"):
        await _project(body.project_id)
    doc = {**body.model_dump(), "id": str(uuid.uuid4()), "created_by": member["user_id"], "created_by_name": member.get("name", ""), "created_at": now()}
    await db[coll].insert_one({**doc})
    return doc


async def _update(coll, item_id, body):
    data = body.model_dump(exclude_none=True)
    doc = await db[coll].find_one_and_update({"id": item_id}, {"$set": {**data, "updated_at": now()}}, projection={"_id": 0}, return_document=ReturnDocument.AFTER)
    if not doc:
        raise HTTPException(404, "Not found")
    return doc


async def _delete(coll, item_id):
    res = await db[coll].delete_one({"id": item_id})
    if not res.deleted_count:
        raise HTTPException(404, "Not found")
    await db.files.update_many({"entity_id": item_id}, {"$set": {"is_deleted": True}})
    return {"ok": True}


async def _seed():
    if await db.projects.count_documents({}):
        return
    samples = [("Northline Interchange", "NL-04", "Accra North", "Metro Works Authority", 68, "Active"), ("Riverside Drainage", "RD-11", "East Basin", "City Infrastructure", 42, "At risk"), ("Harbor Access Road", "HA-02", "Port District", "Coastal Development", 84, "Active")]
    for name, code, loc, cl, prog, status in samples:
        await db.projects.insert_one({"id": str(uuid.uuid4()), "name": name, "code": code, "location": loc, "client": cl, "progress": prog, "status": status, "summary": "Sample project — edit or delete it.", "sample": True, "created_by_name": "CivicPro", "created_at": now()})


@api.get("/me")
async def me(member=Depends(current_member)):
    return {k: member.get(k) for k in ("user_id", "role", "name", "email")}


@api.get("/projects")
async def projects(member=Depends(current_member)):
    await _seed()
    return await _with_progress(await db.projects.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000))


def _check_dates(start, end):
    for v in (start, end):
        if v:
            try:
                datetime.fromisoformat(v)
            except ValueError:
                raise HTTPException(422, "Dates must be YYYY-MM-DD")
    if start and end and end <= start:
        raise HTTPException(422, "Finish date must be after start date")


@api.post("/projects")
async def create_project(body: ProjectIn, member=Depends(current_member)):
    _check_dates(body.start_date, body.end_date)
    return await _create("projects", body, member)


@api.get("/projects/{pid}")
async def project_detail(pid: str, member=Depends(current_member)):
    project = (await _with_progress([await _project(pid)]))[0]
    files = await db.files.find({"project_id": pid, "is_deleted": False}, {"_id": 0, "storage_path": 0}).sort("created_at", -1).to_list(1000)
    return {"project": project, "activities": await _list("activities", pid), "reports": await _list("reports", pid, True), "issues": await _list("issues", pid, True), "files": files}


@api.get("/projects/{pid}/curve")
async def project_curve(pid: str, member=Depends(current_member)):
    project = (await _with_progress([await _project(pid)]))[0]
    snaps = await db.progress_snapshots.find({"project_id": pid}, {"_id": 0}).to_list(5000)
    return build_curve(project, snaps, datetime.now(timezone.utc).date()) or {"points": [], "missing_dates": True}


@api.patch("/projects/{pid}")
async def update_project(pid: str, body: ProjectPatch, member=Depends(current_member)):
    current = await _project(pid)
    _check_dates(body.start_date if body.start_date is not None else current.get("start_date"), body.end_date if body.end_date is not None else current.get("end_date"))
    return await _update("projects", pid, body)


@api.delete("/projects/{pid}")
async def delete_project(pid: str, member=Depends(current_member)):
    await _delete("projects", pid)
    for coll in ("activities", "reports", "issues"):
        await db[coll].delete_many({"project_id": pid})
    await db.files.update_many({"project_id": pid}, {"$set": {"is_deleted": True}})
    return {"ok": True}


@api.get("/activities")
async def activities(project_id: Optional[str] = None, member=Depends(current_member)):
    return await _list("activities", project_id)


@api.post("/activities")
async def create_activity(body: ActivityIn, member=Depends(current_member)):
    return await _create("activities", body, member)


@api.patch("/activities/{aid}")
async def update_activity(aid: str, body: ActivityPatch, member=Depends(current_member)):
    return await _update("activities", aid, body)


@api.delete("/activities/{aid}")
async def delete_activity(aid: str, member=Depends(current_member)):
    return await _delete("activities", aid)


@api.get("/reports")
async def reports(project_id: Optional[str] = None, member=Depends(current_member)):
    return await _list("reports", project_id, True)


@api.post("/reports")
async def create_report(body: ReportIn, member=Depends(current_member)):
    if not body.report_date:
        body.report_date = datetime.now(timezone.utc).date().isoformat()
    return await _create("reports", body, member)


@api.patch("/reports/{rid}")
async def update_report(rid: str, body: ReportPatch, member=Depends(current_member)):
    return await _update("reports", rid, body)


@api.delete("/reports/{rid}")
async def delete_report(rid: str, member=Depends(current_member)):
    return await _delete("reports", rid)


@api.get("/issues")
async def issues(project_id: Optional[str] = None, member=Depends(current_member)):
    return await _list("issues", project_id, True)


@api.post("/issues")
async def create_issue(body: IssueIn, member=Depends(current_member)):
    if body.owner_id:
        body.owner = await _owner_name(body.owner_id)
    return await _create("issues", body, member)


@api.patch("/issues/{iid}")
async def update_issue(iid: str, body: IssuePatch, member=Depends(current_member)):
    if body.owner_id:
        body.owner = await _owner_name(body.owner_id)
    elif body.owner_id == "":
        body.owner = body.owner or "Unassigned"
    doc = await _update("issues", iid, body)
    if body.due_date is not None or body.owner_id is not None:
        await db.issues.update_one({"id": iid}, {"$unset": {"reminder_sent_at": ""}})
        doc.pop("reminder_sent_at", None)
    return doc


async def _owner_name(user_id):
    u = await db.users.find_one({"user_id": user_id}, {"_id": 0, "name": 1, "email": 1})
    if not u:
        raise HTTPException(404, "Team member not found")
    return u.get("name") or u.get("email") or "Team member"


@api.get("/team")
async def team(member=Depends(current_member)):
    return await db.users.find({}, {"_id": 0, "user_id": 1, "name": 1, "email": 1, "role": 1}).sort("name", 1).to_list(1000)


async def _run_overdue_reminders(app_url):
    yesterday = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
    window = (datetime.now(timezone.utc).date() - timedelta(days=7)).isoformat()
    issues = await db.issues.find({"status": {"$ne": "Resolved"}, "due_date": {"$gte": window, "$lte": yesterday, "$ne": ""}, "reminder_sent_at": {"$exists": False}}, {"_id": 0}).to_list(1000)
    if not issues:
        return 0
    names = {p["id"]: p["name"] for p in await db.projects.find({}, {"_id": 0, "id": 1, "name": 1}).to_list(1000)}
    managers = [m for m in await db.users.find({"role": {"$in": ["manager", "admin"]}}, {"_id": 0}).to_list(100) if m.get("email")]
    sent = 0
    for issue in issues:
        pname = names.get(issue["project_id"], "Unknown project")
        owner = await db.users.find_one({"user_id": issue["owner_id"]}, {"_id": 0}) if issue.get("owner_id") else None
        ok = False
        if owner and owner.get("email"):
            subject, html = overdue_email(issue, pname, owner.get("name") or "there", app_url, for_manager=False)
            ok = bool(await send_email(to=[owner["email"]], subject=subject, html=html))
        cc = [m["email"] for m in managers if not owner or m["email"] != owner.get("email")]
        if cc:
            subject, html = overdue_email(issue, pname, "team", app_url, for_manager=True)
            ok = bool(await send_email(to=cc, subject=subject, html=html)) or ok
        if ok:
            sent += 1
            await db.issues.update_one({"id": issue["id"]}, {"$set": {"reminder_sent_at": now()}})
    logger.info(f"Overdue reminders sent for {sent}/{len(issues)} issues")
    return sent


@api.post("/cron/overdue-reminders")
async def cron_overdue(request: Request, background: BackgroundTasks):
    # Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
    auth = request.headers.get("authorization", "")
    secret = os.environ.get("WEBHOOK_CRON_SECRET", "")
    if not secret or not auth.startswith("Bearer ") or not hmac.compare_digest(auth[7:], secret):
        raise HTTPException(401, "Unauthorized")
    try:
        envelope = await request.json()
    except ValueError:
        envelope = None
    if envelope is not None and not isinstance(envelope, dict):
        raise HTTPException(400, "Invalid body")
    run_id = request.headers.get("x-webhook-id") or (envelope or {}).get("run_id") or str(uuid.uuid4())
    try:
        await db.cron_runs.insert_one({"run_id": run_id, "job": "overdue-reminders", "created_at": now()})
    except DuplicateKeyError:
        return {"status": "duplicate"}
    host = request.headers.get("x-forwarded-host") or request.headers.get("host", "")
    background.add_task(_run_overdue_reminders, f"https://{host.split(',')[0].strip()}" if host else "")
    return {"status": "accepted", "run_id": run_id}


@api.delete("/issues/{iid}")
async def delete_issue(iid: str, member=Depends(current_member)):
    return await _delete("issues", iid)


@api.post("/files")
async def upload_file(file: UploadFile = File(...), project_id: str = Form(...), entity_type: Literal["project", "report", "issue"] = Form("project"), entity_id: str = Form(""), member=Depends(current_member)):
    await _project(project_id)
    entity_id = entity_id or project_id
    if entity_type != "project" and not await db[f"{entity_type}s"].find_one({"id": entity_id, "project_id": project_id}):
        raise HTTPException(404, f"{entity_type.capitalize()} not found")
    data = await file.read()
    if not data or len(data) > MAX_FILE:
        raise HTTPException(413, "Files must be between 1 byte and 20 MB")
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "bin"
    ctype = file.content_type or "application/octet-stream"
    result = await run_in_threadpool(put_object, f"{APP_NAME}/uploads/{project_id}/{uuid.uuid4()}.{ext}", data, ctype)
    doc = {"id": str(uuid.uuid4()), "storage_path": result["path"], "original_filename": file.filename, "content_type": ctype, "size": len(data),
           "project_id": project_id, "entity_type": entity_type, "entity_id": entity_id, "uploaded_by_name": member.get("name", ""), "is_deleted": False, "created_at": now()}
    await db.files.insert_one({**doc})
    return {k: v for k, v in doc.items() if k != "storage_path"}


@api.get("/files")
async def list_files(project_id: Optional[str] = None, entity_id: Optional[str] = None, member=Depends(current_member)):
    q = {"is_deleted": False} | ({"project_id": project_id} if project_id else {}) | ({"entity_id": entity_id} if entity_id else {})
    return await db.files.find(q, {"_id": 0, "storage_path": 0}).sort("created_at", -1).to_list(1000)


@api.get("/files/{fid}/download")
async def download_file(fid: str, member=Depends(current_member)):
    rec = await db.files.find_one({"id": fid, "is_deleted": False}, {"_id": 0})
    if not rec:
        raise HTTPException(404, "File not found")
    data, ctype = await run_in_threadpool(get_object, rec["storage_path"])
    return Response(content=data, media_type=rec.get("content_type") or ctype, headers={"Content-Disposition": f"inline; filename*=UTF-8''{quote(rec['original_filename'])}"})


@api.delete("/files/{fid}")
async def delete_file(fid: str, member=Depends(current_member)):
    res = await db.files.update_one({"id": fid, "is_deleted": False}, {"$set": {"is_deleted": True}})
    if not res.matched_count:
        raise HTTPException(404, "File not found")
    return {"ok": True}


@api.get("/dashboard")
async def dashboard(member=Depends(current_member)):
    await _seed()
    projects = await _with_progress(await db.projects.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000))
    names = {p["id"]: p["name"] for p in projects}
    issues = await db.issues.find({}, {"_id": 0}).to_list(5000)
    reports = await db.reports.find({}, {"_id": 0}).sort("created_at", -1).to_list(5000)
    acts = await db.activities.find({}, {"_id": 0}).sort("created_at", -1).to_list(50)
    today = datetime.now(timezone.utc).date()
    week_start = today - timedelta(days=today.weekday())
    open_issues = [i for i in issues if i.get("status") != "Resolved"]
    weeks = []
    for n in range(7, -1, -1):
        start = week_start - timedelta(weeks=n)
        end = start + timedelta(days=7)
        bucket = [r for r in reports if start.isoformat() <= (r.get("report_date") or r["created_at"][:10]) < end.isoformat()]
        weeks.append({"week": start.strftime("%d %b"), "Daily": sum(r.get("report_type") == "Daily" for r in bucket), "Weekly": sum(r.get("report_type") == "Weekly" for r in bucket)})
    feed = [{"type": "report", "title": f"{r.get('report_type', 'Daily')} report: {r['title']}", "project_id": r["project_id"], "by": r.get("created_by_name", ""), "created_at": r["created_at"]} for r in reports[:8]]
    feed += [{"type": "issue", "title": f"{i.get('category', 'Issue')} flagged: {i['title']}", "project_id": i["project_id"], "by": i.get("created_by_name", ""), "created_at": i["created_at"]} for i in sorted(issues, key=lambda x: x["created_at"], reverse=True)[:8]]
    feed += [{"type": "activity", "title": f"Activity: {a['name']} ({a['progress']}%)", "project_id": a["project_id"], "by": a.get("created_by_name", ""), "created_at": a.get("updated_at") or a["created_at"]} for a in acts[:8]]
    feed = sorted(feed, key=lambda x: x["created_at"], reverse=True)[:8]
    for f in feed:
        f["project_name"] = names.get(f["project_id"], "Unknown project")
    return {
        "projects": projects,
        "kpis": {
            "avg_progress": round(sum(p["progress"] for p in projects) / len(projects)) if projects else 0,
            "projects": sum(p.get("status") in ("Active", "At risk") for p in projects), "at_risk": sum(p.get("status") == "At risk" for p in projects), "on_track": sum(p.get("status") == "Active" for p in projects),
            "open_issues": len(open_issues), "high_open": sum(i.get("severity") == "High" for i in open_issues),
            "overdue": sum(bool(i.get("due_date")) and i["due_date"] < today.isoformat() for i in open_issues),
            "reports_week": sum((r.get("report_date") or r["created_at"][:10]) >= week_start.isoformat() for r in reports), "reports_total": len(reports),
        },
        "severity": [{"name": s, "value": sum(i.get("severity") == s for i in open_issues)} for s in ("High", "Medium", "Low")],
        "weeks": weeks,
        "feed": feed,
    }


@api.get("/export")
async def export(fmt: Literal["pdf", "xlsx"] = "pdf", project_id: Optional[str] = None, days: Optional[int] = Query(default=None, ge=1, le=366), member=Depends(current_member)):
    projs = [await _project(project_id)] if project_id else await db.projects.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    projs = await _with_progress(projs)
    since = (datetime.now(timezone.utc).date() - timedelta(days=days - 1)).isoformat() if days else None
    data = {"projects": projs, "activities": await _list("activities", project_id), "reports": await _list("reports", project_id, since=since, since_field="report_date"), "issues": await _list("issues", project_id, since=since)}
    if days:
        data["issues"] += [i for i in await _list("issues", project_id) if i.get("status") != "Resolved" and i["id"] not in {x["id"] for x in data["issues"]}]
    scope = projs[0]["name"] if project_id else "Portfolio"
    period = {1: "Daily site report", 7: "Weekly site report"}.get(days, "Full project report" if not days else f"Last {days} days")
    data |= {"title": f"{scope} — {period}", "period_label": period, "generated_at": datetime.now(timezone.utc).strftime("%d %b %Y %H:%M UTC")}
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    slug = "".join(c if c.isalnum() else "-" for c in scope.lower()).strip("-")
    if fmt == "pdf":
        body, media = await run_in_threadpool(build_pdf, data), "application/pdf"
    else:
        body, media = await run_in_threadpool(build_xlsx, data), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return Response(content=body, media_type=media, headers={"Content-Disposition": f'attachment; filename="civicpro-{slug}-{stamp}.{fmt}"'})


@api.get("/users")
async def users(member=Depends(require_manager)):
    return {"roles": ROLES, "users": await db.users.find({}, {"_id": 0, "env": 0}).sort("created_at", 1).to_list(1000)}


@api.patch("/users/{user_id}")
async def set_role(user_id: str, body: RolePatch, member=Depends(require_manager)):
    if user_id == member["user_id"] and body.role != "manager":
        raise HTTPException(400, "You cannot remove your own manager role")
    target = await db.users.find_one({"user_id": user_id}, {"_id": 0, "email": 1})
    if target and (target.get("email") or "").lower() in _admin_emails() and body.role != "manager":
        raise HTTPException(400, "The workspace owner must stay a manager")
    doc = await db.users.find_one_and_update({"user_id": user_id}, {"$set": {"role": body.role}}, projection={"_id": 0, "env": 0}, return_document=ReturnDocument.AFTER)
    if not doc:
        raise HTTPException(404, "User not found")
    return doc


app.include_router(api)
app.include_router(clerk_router)
app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","), allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
async def startup():
    await db.cron_runs.create_index("run_id", unique=True)
    await db.progress_snapshots.create_index([("project_id", 1), ("date", 1)], unique=True)
    try:
        await run_in_threadpool(init_storage)
    except Exception as e:
        logger.error(f"Storage init failed: {e}")


@app.on_event("shutdown")
async def shutdown():
    client.close()
