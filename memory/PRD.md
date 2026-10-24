# CIVICPRO — Construction Project Monitoring (PRD)

## Original problem
Civil engineer needs an app to follow up, monitor and report on construction projects: completed activities, progress %, struggles/issues and related info.

## User choices
- Multiple projects, team workspace with Clerk login; roles engineer / supervisor / manager
- Role model: "Everyone equal, managers manage team" — all roles create/edit everything; only managers change roles (Team page)
- Progress: manual summary + activity-based (weighted) progress
- Daily & weekly site reports; issues/risks/struggles with follow-ups
- Photo/document attachments (Emergent Object Storage)
- Live dashboard charts; exports in PDF and Excel
- Owner/manager email: engsammy122@gmail.com (auto-manager, cannot be demoted)

## Architecture
- Backend FastAPI (`server.py`), `clerk_auth.py` (Clerk JWT), `storage.py` (Emergent object storage), `exports.py` (reportlab PDF, openpyxl XLSX); MongoDB collections: users, projects, activities, reports, issues, files (soft delete)
- Frontend React: `App.js` routes; `pages/` Dashboard, Projects, ProjectDetail, RecordsPage (reports/issues), Team; `components/civic/` Shell, ui, forms, Records, Attachments, Charts (recharts), ExportMenu, ProjectRow; `lib/api.js` (useApi, useResource, MeProvider)

## Key endpoints (all /api, Clerk bearer)
me · projects (GET/POST, GET/PATCH/DELETE /{id} with activities/reports/issues/files) · activities CRUD · reports GET/POST/PATCH/DELETE · issues GET/POST/PATCH/DELETE · files POST (multipart) / GET / GET {id}/download / DELETE · dashboard · export?fmt=pdf|xlsx&project_id&days · users GET, PATCH /{user_id} (manager only)

## Implemented
- 2026-06 (earlier): Clerk auth, base dashboard/projects/reports/issues, Swiss-industrial UI
- 2026-06 (this round): shared team workspace, weighted activity progress, project detail with tabs, report/issue/project attachments with image thumbnails, live KPI + 3 charts + activity feed, daily/weekly/full PDF and Excel exports (portfolio & per project), report edit, issue status workflow + overdue badge, filters, Team role management, test accounts. Tested: iterations 3 & 4 — backend 36/36, frontend 100%.
- 2026-06 (round 3): Overdue reminders — issue owner chosen from team (GET /api/team); daily 07:00 UTC platform cron (.emergent/crons.yml → POST /api/cron/overdue-reminders, bearer WEBHOOK_CRON_SECRET, idempotent via cron_runs) emails the assignee + a copy to managers ONCE for open issues due yesterday (7-day catch-up window); reminder_sent_at badge; re-armed when due date/owner changes. Emails via Emergent managed Resend (mailer.py, from_name CIVICPRO). Planned vs Actual — project start/finish dates, standard S-curve (smoothstep) planned %, daily progress_snapshots for actual, /api/projects/{id}/curve, S-curve panel on project detail, variance badges + planned tick on project rows, planned/variance in PDF/XLSX. Tested iteration 5 — backend 49/49, frontend 100%.


## Backlog
- P1: Issue edit form (owner/due/severity) UI; assignment notifications / overdue reminders (email)
- P1: Report filtering by date range; portfolio-level weekly summary email
- P2: Audit trail of status/progress changes; S-curve planned vs actual chart; offline-friendly field mode; project-level team membership
