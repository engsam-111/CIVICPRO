from fastapi import FastAPI, APIRouter, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ReturnDocument
from pydantic import BaseModel, Field
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
import os, uuid, requests

load_dotenv(Path(__file__).parent / '.env')
try:
    from backend.clerk_auth import clerk_router, require_user
except ModuleNotFoundError:
    from clerk_auth import clerk_router, require_user

client = AsyncIOMotorClient(os.environ['MONGO_URL'])
db = client[os.environ['DB_NAME']]
app = FastAPI(title="CivicPro API")
api = APIRouter(prefix="/api")
ROLES = ["admin", "manager", "engineer", "supervisor"]
DEFAULT_ROLE = "engineer"
RANK = {role: len(ROLES) - i for i, role in enumerate(ROLES)}
ENV = "live" if os.environ.get("CLERK_PUBLISHABLE_KEY", "").startswith("pk_live_") else "preview"
now = lambda: datetime.now(timezone.utc).isoformat()

class ProjectIn(BaseModel):
    name: str
    code: str
    location: str = ""
    client: str = ""
    progress: int = Field(ge=0, le=100, default=0)
    status: str = "Active"

class ActivityIn(BaseModel):
    project_id: str
    name: str
    owner: str = "Unassigned"
    progress: int = Field(ge=0, le=100, default=0)
    status: str = "In progress"
    due_date: str = ""

class ReportIn(BaseModel):
    project_id: str
    title: str
    report_type: str = "Daily"
    summary: str
    workforce: int = 0
    progress: int = Field(ge=0, le=100, default=0)
    attachments: list[str] = []

class IssueIn(BaseModel):
    project_id: str
    title: str
    severity: str = "Medium"
    owner: str = "Unassigned"
    due_date: str = ""
    status: str = "Open"

def _clean(doc):
    doc.pop("_id", None)
    return doc

def _is_admin_email(user_id):
    admins = {e.strip().lower() for e in os.environ.get("ADMIN_EMAIL", "").split(",") if e.strip()}
    if not admins: return False
    response = requests.get(f"https://api.clerk.com/v1/users/{user_id}", timeout=10, headers={"Authorization": f"Bearer {os.environ['CLERK_SECRET_KEY']}", "User-Agent": "emergent-app"})
    response.raise_for_status()
    return any(e["email_address"].lower() in admins and (e.get("verification") or {}).get("status") == "verified" for e in response.json()["email_addresses"])

async def current_member(user=Depends(require_user)):
    uid = user["user_id"]
    member = await db.users.find_one({"user_id": uid, "env": {"$in": [ENV, None]}}, {"_id": 0})
    if not member:
        role = "admin" if _is_admin_email(uid) else DEFAULT_ROLE
        await db.users.update_one({"user_id": uid}, {"$setOnInsert": {"user_id": uid, "role": role, "env": ENV, "created_at": now()}}, upsert=True)
        member = await db.users.find_one({"user_id": uid}, {"_id": 0})
    if member.get("env") != ENV: await db.users.update_one({"user_id": uid}, {"$set": {"env": ENV}})
    member["role"] = member.get("role") if member.get("role") in ROLES else DEFAULT_ROLE
    return member

def require_role(*roles):
    async def check(member=Depends(current_member)):
        if member["role"] not in roles: raise HTTPException(403, "Not allowed")
        return member
    return check

async def scoped_collection(name, member):
    docs = await db[name].find({"owner_id": member["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return docs

@api.get("/me")
async def me(member=Depends(current_member)): return {"user_id": member["user_id"], "role": member["role"]}

@api.get("/projects")
async def projects(member=Depends(current_member)):
    docs = await scoped_collection("projects", member)
    if not docs:
        samples = [{"name": "Northline Interchange", "code": "NL-04", "location": "Accra North", "client": "Metro Works Authority", "progress": 68, "status": "Active"}, {"name": "Riverside Drainage", "code": "RD-11", "location": "East Basin", "client": "City Infrastructure", "progress": 42, "status": "At risk"}, {"name": "Harbor Access Road", "code": "HA-02", "location": "Port District", "client": "Coastal Development", "progress": 84, "status": "Active"}]
        for sample in samples: await db.projects.insert_one({**sample, "id": str(uuid.uuid4()), "owner_id": member["user_id"], "created_at": now()})
        docs = await scoped_collection("projects", member)
    return docs

@api.post("/projects")
async def create_project(body: ProjectIn, member=Depends(current_member)):
    doc = {**body.model_dump(), "id": str(uuid.uuid4()), "owner_id": member["user_id"], "created_at": now()}
    await db.projects.insert_one(doc); return _clean(doc)

@api.get("/activities")
async def activities(project_id: Optional[str] = None, member=Depends(current_member)):
    query = {"owner_id": member["user_id"]}
    if project_id: query["project_id"] = project_id
    return await db.activities.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)

@api.post("/activities")
async def create_activity(body: ActivityIn, member=Depends(current_member)):
    doc = {**body.model_dump(), "id": str(uuid.uuid4()), "owner_id": member["user_id"], "created_at": now()}; await db.activities.insert_one(doc); return _clean(doc)

@api.get("/reports")
async def reports(project_id: Optional[str] = None, member=Depends(current_member)):
    query = {"owner_id": member["user_id"]}
    if project_id: query["project_id"] = project_id
    return await db.reports.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)

@api.post("/reports")
async def create_report(body: ReportIn, member=Depends(current_member)):
    doc = {**body.model_dump(), "id": str(uuid.uuid4()), "owner_id": member["user_id"], "created_at": now()}; await db.reports.insert_one(doc); return _clean(doc)

@api.get("/issues")
async def issues(project_id: Optional[str] = None, member=Depends(current_member)):
    query = {"owner_id": member["user_id"]}
    if project_id: query["project_id"] = project_id
    return await db.issues.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)

@api.post("/issues")
async def create_issue(body: IssueIn, member=Depends(current_member)):
    doc = {**body.model_dump(), "id": str(uuid.uuid4()), "owner_id": member["user_id"], "created_at": now()}; await db.issues.insert_one(doc); return _clean(doc)

@api.get("/users")
async def users(member=Depends(require_role("admin", "manager"))):
    people = await db.users.find({"env": {"$in": [ENV, None]}}, {"_id": 0}).to_list(1000)
    return {"roles": ROLES, "users": people}

app.include_router(api); app.include_router(clerk_router)
app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","), allow_methods=["*"], allow_headers=["*"])
@app.on_event("shutdown")
async def shutdown(): client.close()