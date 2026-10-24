import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Pencil, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { errorText, useApi, useResource } from "@/lib/api";
import { Badge, Empty, Heading, Loading, Progress, toneFor } from "@/components/civic/ui";
import { ActivityForm, IssueForm, ProjectForm, ReportForm } from "@/components/civic/forms";
import { IssueList, ReportList } from "@/components/civic/Records";
import { AttachmentList, Uploader } from "@/components/civic/Attachments";
import ExportMenu from "@/components/civic/ExportMenu";

function ActivityRow({ a, reload }) {
  const api = useApi();
  const [progress, setProgress] = useState(a.progress);
  useEffect(() => setProgress(a.progress), [a.progress]);
  const save = async patch => {
    try { await api("patch", `/activities/${a.id}`, patch); reload(); }
    catch (e) { toast.error(errorText(e, "Could not update activity")); }
  };
  const commit = () => progress !== a.progress && save({ progress, ...(progress === 100 ? { status: "Completed" } : {}) });
  const remove = async () => {
    if (!window.confirm("Delete this activity?")) return;
    try { await api("delete", `/activities/${a.id}`); toast.success("Activity deleted"); reload(); }
    catch (e) { toast.error(errorText(e, "Could not delete activity")); }
  };
  return <div className="activity-row" data-testid={`activity-${a.id}`}>
    <div className="record-main"><b>{a.name}</b><small>{a.owner || "Unassigned"} · weight {a.weight}{a.due_date ? ` · due ${a.due_date}` : ""}</small></div>
    <div className="activity-progress"><input type="range" min={0} max={100} step={5} value={progress} onChange={e => setProgress(Number(e.target.value))} onMouseUp={commit} onTouchEnd={commit} onKeyUp={commit} data-testid={`activity-progress-${a.id}`} />
      <input type="number" min={0} max={100} value={progress} onChange={e => setProgress(Math.min(100, Math.max(0, Number(e.target.value))))} onBlur={commit} data-testid={`activity-progress-input-${a.id}`} /><span>%</span></div>
    <select className={`status-select tone-${toneFor(a.status)}`} value={a.status} onChange={e => save({ status: e.target.value, ...(e.target.value === "Completed" ? { progress: 100 } : {}) })} data-testid={`activity-status-${a.id}`}>{["Not started", "In progress", "Completed"].map(s => <option key={s}>{s}</option>)}</select>
    <button className="icon-btn small" onClick={remove} aria-label="Delete activity" data-testid={`delete-activity-${a.id}`}><Trash2 size={14} /></button>
  </div>;
}

const TABS = ["activities", "reports", "issues", "files"];

export default function ProjectDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const api = useApi();
  const [d, reload, error] = useResource(`/projects/${id}`);
  const [tab, setTab] = useState("activities");
  const [modal, setModal] = useState("");
  if (error) return <div className="content"><Empty testid="project-not-found">Project not found. <button className="text-btn" onClick={() => navigate("/projects")}>Back to projects</button></Empty></div>;
  if (!d) return <Loading />;
  const p = d.project;
  const counts = { activities: d.activities.length, reports: d.reports.length, issues: d.issues.filter(i => i.status !== "Resolved").length, files: d.files.length };
  const removeProject = async () => {
    if (!window.confirm(`Delete ${p.name} and all its records?`)) return;
    try { await api("delete", `/projects/${p.id}`); toast.success("Project deleted"); navigate("/projects"); }
    catch (e) { toast.error(errorText(e, "Could not delete project")); }
  };
  const add = { activities: "activity", reports: "report", issues: "issue" }[tab];
  return <div className="content">
    <button className="text-btn back" onClick={() => navigate("/projects")} data-testid="back-to-projects"><ArrowLeft size={14} /> All projects</button>
    <Heading eyebrow={`${p.code} · ${p.location || "No location"} · ${p.client || "No client"}`} title={p.name}
      actions={<><ExportMenu projectId={p.id} /><button className="ghost-btn" onClick={() => setModal("edit")} data-testid="edit-project-button"><Pencil size={15} /> Edit</button><button className="ghost-btn danger" onClick={removeProject} data-testid="delete-project-button"><Trash2 size={15} /></button></>} />
    <section className="project-hero" data-testid="project-hero">
      <div className="hero-progress"><strong data-testid="project-progress-value">{p.progress}%</strong><div><Progress value={p.progress} /><small data-testid="project-progress-mode">{p.progress_mode === "activity" ? `Calculated from ${p.activity_count} weighted activities` : "Manual summary — add activities to calculate automatically"}</small></div></div>
      <div className="hero-meta"><Badge tone={toneFor(p.status)} testid="project-status">{p.status}</Badge>{p.progress_mode === "activity" && <span>Manual estimate {p.manual_progress}%</span>}</div>
      {p.summary && <p className="hero-summary" data-testid="project-summary">{p.summary}</p>}
    </section>
    <div className="tabs" role="tablist">{TABS.map(t => <button key={t} role="tab" className={tab === t ? "active" : ""} onClick={() => setTab(t)} data-testid={`tab-${t}`}>{t}<i>{counts[t]}</i></button>)}
      <div className="tab-action">{add ? <button className="primary-btn" onClick={() => setModal(add)} data-testid={`add-${add}-button`}><Plus size={16} /> Add {add}</button> : <Uploader target={{ project_id: p.id, entity_type: "project" }} onDone={reload} testid="project-upload" />}</div></div>
    <div className="list-page">
      {tab === "activities" && (d.activities.length ? <div className="record-list">{d.activities.map(a => <ActivityRow key={a.id} a={a} reload={reload} />)}</div> : <Empty testid="activities-empty">No activities yet. Break the project into weighted activities to calculate progress automatically.</Empty>)}
      {tab === "reports" && <ReportList reports={d.reports} reload={reload} />}
      {tab === "issues" && <IssueList issues={d.issues} reload={reload} />}
      {tab === "files" && <div className="files-pane"><AttachmentList files={d.files} onChange={reload} /></div>}
    </div>
    {modal === "edit" && <ProjectForm project={p} close={() => setModal("")} onSaved={reload} />}
    {modal === "activity" && <ActivityForm projectId={p.id} close={() => setModal("")} onSaved={reload} />}
    {modal === "report" && <ReportForm projects={[p]} projectId={p.id} close={() => setModal("")} onSaved={reload} />}
    {modal === "issue" && <IssueForm projects={[p]} projectId={p.id} close={() => setModal("")} onSaved={reload} />}
  </div>;
}
