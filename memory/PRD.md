# CivicPro Product Requirements Document

## Original problem statement
“I am civil engineer and we have projects and need to follow up, monitor and report. Like as what are activities completed? Progress percentage, struggles, others,...etc?”

## Product direction
CivicPro is a multi-project civil engineering command center for engineers, supervisors, managers, and project teams. It brings portfolio health, activity progress, field reporting, issues, risks, and follow-ups into one field-ready workspace.

## Architecture decisions
- React 19 frontend with React Router, Clerk-managed email authentication, Lucide icons, and responsive CSS.
- FastAPI backend with MongoDB via the existing `MONGO_URL` and `DB_NAME` environment variables.
- Clerk owns sign-in and session verification; CivicPro stores application profiles and role data keyed by Clerk user IDs.
- Roles are `admin`, `manager`, `engineer`, and `supervisor`; the first administrator is configured by `ADMIN_EMAIL`.
- Protected API routes use bearer session tokens and return MongoDB-safe documents without `_id`.

## User personas
- Civil engineer: monitors portfolio progress, creates site reports, assigns follow-ups, and exports updates.
- Site supervisor: records field conditions, workforce, completed activities, and blockers.
- Project manager: reviews project health, risks, reports, and team activity across projects.

## Core requirements
- Multiple construction projects with separate project records and portfolio overview.
- Manual project progress percentage and activity/report-driven updates.
- Project health view with status, location, client, progress bars, and attention signals.
- Daily/weekly site report creation with summary, workforce, progress, and attachment filenames.
- Issues and risk records with severity, owner, due date, and status.
- Team role model with protected backend access and first-admin setup.
- Exportable CSV portfolio view.
- Responsive desktop and mobile field-reporting experience.

## Implemented — 2026-10-24
- Provisioned CivicPro Clerk email sign-in and sign-up flows.
- Added FastAPI Clerk verification, runtime config, production relay, role-aware member lookup, and protected routes.
- Added MongoDB-backed projects, reports, activities, issues, and user profile endpoints.
- Added seeded starter portfolio data per signed-in user when their project list is empty.
- Built CivicPro dashboard with KPI tiles, project health, activity log, attention band, export button, and modals.
- Built Projects, Site reports, and Issues & risks routes with working creation forms.
- Added responsive Swiss industrial visual system using amber, slate, white, and status colors.
- Added mobile-safe navigation, Clerk sign-in presentation, test IDs, and file metadata capture for report attachments.
- Verified production build, Clerk config, missing-token protection, signed-out redirects, and 390px mobile overflow behavior.

## Remaining backlog

### P0
- Run authenticated CRUD and role regression with a real Clerk test account.
- Complete persistent activity creation and activity-specific dashboard summaries.

### P1
- Add true file/photo storage and in-report attachment previews.
- Add project detail route with activity timeline, Gantt-style milestones, and project-level charts.
- Add manager Users page for role changes and team membership workflows.
- Add PDF report export alongside current CSV export.

### P2
- Add offline-first field capture and queued sync for poor site connectivity.
- Add scheduled weekly report reminders and overdue follow-up notifications.
- Add richer chart filters by date range, project, discipline, and responsible person.

## Next tasks
1. Add a verified Clerk test account to `memory/test_credentials.md` and run authenticated CRUD regression.
2. Add persistent activity create/edit controls and milestone reporting.
3. Connect managed object storage for actual photo and document uploads.
4. Add project detail and PDF reporting views.