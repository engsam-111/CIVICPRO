# CIVICPRO — Construction Project Monitoring (PRD)

## Original problem
Civil engineer needs an app to follow up, monitor and report on construction projects: completed activities, progress %, struggles/issues and related info.

## Latest request
- User: "In the projects section, add the ability to upload and download files when creating a new project."
- Failure handling choice: "Keep project and attach later". New projects can have multiple optional files; failed uploads never undo the saved project, and successful files remain attached.

## Previous mobile request
- User: "recreate all this as APP MOBILE"
- Clarification: "Installable phone app" — implement as a mobile-first Progressive Web App (PWA), preserving the existing online workspace, features, and desktop experience. Not a native store binary.
- Earlier unfinished request: email/password login with manager-only forgotten-password resets, using existing Clerk. This was completed and tested during the mobile work.

## User choices
- Multiple projects, team workspace with Clerk login; roles engineer / supervisor / manager
- Role model: "Everyone equal, managers manage team" — all roles create/edit everything; only managers change roles (Team page)
- Progress: manual summary + activity-based (weighted) progress
- Daily & weekly site reports; issues/risks/struggles with follow-ups
- Photo/document attachments (Emergent Object Storage)
- Live dashboard charts; exports in PDF and Excel
- Owner/manager email: engsammy122@gmail.com (auto-manager, cannot be demoted)
- AI: GPT-6 Astra via Emergent LLM key, report drafts, issue suggestions, project chat with saved sessions.
- Overdue reminders: once the day after due date, to assignee with active managers copied.
- Password reset: managers reset regular members; only owner can reset managers; no public forgot-password reset flow.
- Mobile: installable on home screen, not an app-store listing; internet required for private data and saving.

## Architecture
- Backend FastAPI (`server.py`), `clerk_auth.py` (Clerk JWT), `storage.py` (Emergent object storage), `exports.py` (reportlab PDF, openpyxl XLSX); MongoDB collections: users, projects, activities, reports, issues, files (soft delete)
- Frontend React: `App.js` routes; `pages/` Dashboard, Projects, ProjectDetail, RecordsPage (reports/issues), Team; `components/civic/` Shell, ui, forms, Records, Attachments, Charts (recharts), ExportMenu, ProjectRow; `lib/api.js` (useApi, useResource, MeProvider)
- Mobile frontend: `mobile.css` layers responsive changes onto existing desktop styles; `components/mobile/` PwaProvider, MobileNav, InstallPanel; `/more` route for AI, manager-only Team, account identity and installation.
- PWA: `public/manifest.json`, `public/sw.js`, `public/offline.html`, `public/icons/`; early registration in `lib/registerPwa.js` via `index.js`. Public cache only; no caching of API responses, Clerk auth, app HTML, files, or private records. Navigate fetches bypass HTTP cache and use offline fallback on network loss.
- Shared forms use existing shadcn/Radix dialog for focus trapping and escape/backdrop close; bottom sheets on small phones. Existing FastAPI/MongoDB data model unchanged by mobile conversion.
- New-project file flow: `components/civic/ProjectFiles.jsx` provides optional multi-file selection, local download/remove controls and persistent failed-upload notice. `ProjectForm` saves project first then uploads each file independently via existing `/api/files`. `ProjectDetail` supports `?tab=files`; `Attachments.jsx` provides explicit authenticated downloads. No new storage service or backend data-model changes.

## Key endpoints (all /api, Clerk bearer)
me · projects (GET/POST, GET/PATCH/DELETE /{id} with activities/reports/issues/files) · activities CRUD · reports GET/POST/PATCH/DELETE · issues GET/POST/PATCH/DELETE · files POST (multipart) / GET / GET {id}/download / DELETE · dashboard · export?fmt=pdf|xlsx&project_id&days · users GET, PATCH /{user_id} (manager only)
- POST `/api/users/{user_id}/password`: manager-checked Clerk password update with session sign-out flag and audit log, minimum 8 characters, owner protections.

## Implemented
- 2026-06 (earlier): Clerk auth, base dashboard/projects/reports/issues, Swiss-industrial UI
- 2026-06 (this round): shared team workspace, weighted activity progress, project detail with tabs, report/issue/project attachments with image thumbnails, live KPI + 3 charts + activity feed, daily/weekly/full PDF and Excel exports (portfolio & per project), report edit, issue status workflow + overdue badge, filters, Team role management, test accounts. Tested: iterations 3 & 4 — backend 36/36, frontend 100%.
- 2026-06 (round 3): Overdue reminders — issue owner chosen from team (GET /api/team); daily 07:00 UTC platform cron (.emergent/crons.yml → POST /api/cron/overdue-reminders, bearer WEBHOOK_CRON_SECRET, idempotent via cron_runs) emails the assignee + a copy to managers ONCE for open issues due yesterday (7-day catch-up window); reminder_sent_at badge; re-armed when due date/owner changes. Emails via Emergent managed Resend (mailer.py, from_name CIVICPRO). Planned vs Actual — project start/finish dates, standard S-curve (smoothstep) planned %, daily progress_snapshots for actual, /api/projects/{id}/curve, S-curve panel on project detail, variance badges + planned tick on project rows, planned/variance in PDF/XLSX. Tested iteration 5 — backend 49/49, frontend 100%.


- 2026-06 (security round): upload allowlist + magic-byte check, safe download headers/CSP, manager approval for new sign-ups (pending/active/rejected, Team approve/decline/restore/remove, owner protected), XLSX formula + PDF markup escaping, CORS/security headers, JWT issuer check, per-user rate limits (AI 12/min, export 15/min, upload 40/min). Re-audit: PASS (P3 hardening only). Tested iterations 7-8 — 100%.
- 2026-06 (AI round): GPT-6 Astra via Emergent LLM key — AI report drafting from rough notes, AI issue action suggestions (apply severity / add to details), AI assistant chat over portfolio data with per-user saved conversations (SSE streaming). Tested iteration 6.

- 2026-10-27 (mobile PWA): home-screen manifest, CP icons (192/512/maskable/apple-touch), platform-sensitive install help, browser install prompt and installed-state handling. iPhone safe-area support, fixed 5-tab phone navigation, sticky branded header, responsive charts/records/teams/AI chat, touch-sized controls, non-zooming inputs, bottom-sheet forms, preserved desktop sidebar. Dashboard analytics collapsible on mobile, all charts retained. More page exposes AI and authorized team management.
- 2026-10-27 (auth completion): tested custom Clerk email/password and manager password resets; fixed async finalize error handling, numeric one-time-code input, resend success/error reporting, signed-in auth-route redirect, masked reset-password input. Test engineer password temporarily changed and then restored/reverified. Current values remain in `test_credentials.md`.
- 2026-10-27 (offline follow-up): immediate service-worker registration, v2 public cache, explicit offline detection plus no-store navigations eliminate app-HTML/bundle mismatch. Offline save rejected with persistent inline error while keeping the in-memory form intact. Online event refreshes resources. No offline queue or offline record access implemented/promised.
- 2026-10-27 (new-project files): optional multi-file picker in project creation, append/deduplicate/remove selection and download selected files; save project then upload each file under that project's ID. Mixed upload failures preserve project and successful files, continue the batch, and show a dismissible filename/reason notice in Files. Saves with attachments open the new project's Files tab, retained after reload. Explicit authenticated download buttons added alongside existing file previews; report/issue attachment controls retained. Upload limits/types remain existing backend allowlist and 20 MB/file.

## Verification — new-project files
- `yarn build`: successful after implementation.
- `/app/test_reports/iteration_10.json`: focused backend 4/4 passed; real upload/download byte and filename checks, auth-required download and no storage-path exposure. UI passed selection/dedup/removal/local download/cancel, creation+file persistence, partial 415 rejection with later successes, warning dismissal, attach-later recovery, no-file creation, edit regression, Dashboard reuse, and 320/390 responsive checks.
- Inconclusive automated popup capture was resolved by main-agent browser check: new PNG attachment opened in a new tab with blob URL and rendered original 192×192 dimensions, original Files tab preserved. The first follow-up used an incorrect `blob:*` URL glob; corrected DOM/URL predicate passed without app changes. Temporary project deleted afterward.
- Follow-up evidence: `/root/.emergent/automation_output/20261027_202545_7748a017584d/console_20261027_202545.log`. No mocked API or credential changes. Existing real projects were not edited by the feature tests.

## Verification — mobile conversion
- `yarn build`: production compilation successful, including final follow-up edits.
- `/app/test_reports/iteration_9.json`: backend regression and password-reset tests passed (XML recheck: 13/13; API suite: 20/20; agent also ran backend_test.py). Mobile/desktop checks at 320/390/768/1024/1440, navigation, CRUD/attachments, PDF/XLSX, access rules, pending account gate and AI conversation checks passed.
- Iteration 9 reported inconsistent offline hard navigation. Follow-up hardened SW and self-tested known/unknown/sign-in hard navigations offline, offline refresh, blocked form save retaining inputs, and reconnect retry into authenticated workspace: PASS. Chromium `Page.getInstallabilityErrors`: empty list, no reported blockers. Evidence in `/app/test_reports/mobile_offline_followup.json`.
- Install-prompt lifecycle was EMULATED by testing agent; actual physical iPhone/Android installation has NOT been tested. Browser manifest/SW/installability checks are real. No application API is mocked.
- Browser testing confirms preview only. No claim that the earlier asynchronous deployment contains these changes; production status was not inspected.

## Backlog
- P0: No known blocking defects in tested mobile flows. Await user's acceptance on their phone.
- Next action for latest feature: Projects → New project → Project files; save, then download from Files. No known blocking issues in tested upload/download flows.
- P1 verification: install/open/close/sign-in/logout from real iPhone Safari and Android Chrome home-screen apps; verify device file-picker/camera and export behavior. Physical-device app installation is the next action.
- P1 verification carried forward: deployed reminder cron and real recipient inbox delivery; production storage behavior and earlier deployment completion remain unverified.
- P1 features: issue edit form (owner/due/severity), report date-range filtering, assignment notifications, portfolio-level weekly summary email.
- P2: offline report drafts with explicit device-privacy controls and sync/conflict handling; status/progress audit trail; project-level team membership.
- Already completed (not backlog): planned-vs-actual S-curve and application-side overdue reminder automation.

## Mobile use
- Open app in a normal phone browser tab; use the Install app control (also available before login) or More → installation section.
- iPhone/iPad: Safari → Share → Add to Home Screen; leave Open as Web App enabled where shown.
- Android: supported browser installation prompt/menu → Install app / Add to Home Screen.
- Internet is required for loading/saving project records, file uploads and AI. Offline fallback is a public connectivity page, not cached private data.
- Enhancement suggestion: offline site-report drafts would help teams reporting from low-signal construction sites.
