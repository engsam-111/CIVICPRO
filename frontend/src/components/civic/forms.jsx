import { useRef } from "react";
import { toast } from "sonner";
import { uploadFiles, useApi, useResource } from "@/lib/api";
import { Field, FormModal, Select } from "@/components/civic/ui";

const today = () => new Date().toISOString().slice(0, 10);
const projectOptions = projects => [{ value: "", label: "Choose a project" }, ...projects.map(p => ({ value: p.id, label: `${p.code} · ${p.name}` }))];
const num = v => Number(v || 0);

async function attach(api, picked, target) {
  if (!picked.length) return;
  try { await uploadFiles(api, picked, target); }
  catch { toast.error("Saved, but some attachments failed to upload. Add them again from the record."); }
}

function FilesField({ inputRef }) {
  return <label className="field full"><span>Photos or documents (optional)</span><input ref={inputRef} type="file" multiple accept="image/*,.pdf,.doc,.docx,.xls,.xlsx,.dwg,.csv,.txt" data-testid="form-attachments-input" /></label>;
}

export function ProjectForm({ close, onSaved, project }) {
  const api = useApi();
  const submit = async f => {
    const body = { ...f, progress: num(f.progress) };
    await (project ? api("patch", `/projects/${project.id}`, body) : api("post", "/projects", body));
    toast.success(project ? "Project updated" : "Project added");
    await onSaved();
  };
  const p = project || {};
  return <FormModal title={project ? "Edit project" : "Add project"} close={close} onSubmit={submit} submitLabel="Save project" testid="save-project-button">
    <Field name="name" label="Project name" placeholder="e.g. East Bypass" defaultValue={p.name} />
    <Field name="code" label="Project code" placeholder="EB-03" defaultValue={p.code} />
    <Field name="location" label="Location" placeholder="Site location" required={false} defaultValue={p.location} />
    <Field name="client" label="Client" placeholder="Client / authority" required={false} defaultValue={p.client} />
    <Field name="progress" label={p.progress_mode === "activity" ? "Manual progress % (activities override)" : "Progress %"} type="number" min={0} max={100} placeholder="0" required={false} defaultValue={p.manual_progress ?? p.progress} />
    <Select name="status" label="Status" options={["Active", "At risk", "On hold", "Completed"]} defaultValue={p.status || "Active"} />
    <Field name="start_date" label="Planned start" type="date" required={false} defaultValue={p.start_date} />
    <Field name="end_date" label="Planned finish" type="date" required={false} defaultValue={p.end_date} />
    <Field name="summary" label="Project summary" type="textarea" full required={false} placeholder="Scope, current stage, key notes…" defaultValue={p.summary} />
  </FormModal>;
}

export function ReportForm({ close, onSaved, projects, projectId, report: edit }) {
  const api = useApi();
  const files = useRef(null);
  const r = edit || {};
  const submit = async f => {
    const body = { ...f, workforce: num(f.workforce), progress: num(f.progress) };
    if (edit) { delete body.project_id; await api("patch", `/reports/${edit.id}`, body); toast.success("Report updated"); await onSaved(); return; }
    const report = await api("post", "/reports", body);
    const picked = Array.from(files.current?.files || []);
    await attach(api, picked, { project_id: report.project_id, entity_type: "report", entity_id: report.id });
    toast.success("Site report submitted");
    await onSaved();
  };
  return <FormModal title={edit ? "Edit site report" : "New site report"} close={close} onSubmit={submit} submitLabel={edit ? "Save changes" : "Submit report"} testid="save-report-button">
    {!edit && <Select name="project_id" label="Project" full options={projectOptions(projects)} defaultValue={projectId || ""} testid="report-project-select" />}
    <Select name="report_type" label="Report type" options={["Daily", "Weekly"]} defaultValue={r.report_type} testid="report-type-select" />
    <Field name="report_date" label="Report date" type="date" defaultValue={r.report_date || today()} />
    <Field name="title" label="Report title" placeholder="Morning site walk" full defaultValue={r.title} />
    <Field name="workforce" label="Workforce on site" type="number" min={0} placeholder="24" required={false} defaultValue={r.workforce} />
    <Field name="progress" label="Progress reported %" type="number" min={0} max={100} placeholder="68" required={false} defaultValue={r.progress} />
    <Field name="weather" label="Weather / site conditions" placeholder="Sunny, dry ground" required={false} full defaultValue={r.weather} />
    <Field name="summary" label="Work completed" type="textarea" full placeholder="What was done today? Key quantities, inspections…" defaultValue={r.summary} />
    <Field name="next_steps" label="Planned next / blockers" type="textarea" full required={false} placeholder="What's next, what's blocking…" defaultValue={r.next_steps} />
    {!edit && <FilesField inputRef={files} />}
  </FormModal>;
}

export function IssueForm({ close, onSaved, projects, projectId }) {
  const api = useApi();
  const files = useRef(null);
  const [team] = useResource("/team");
  const submit = async f => {
    const issue = await api("post", "/issues", { ...f, owner: f.owner_id ? undefined : "Unassigned" });
    const picked = Array.from(files.current?.files || []);
    await attach(api, picked, { project_id: issue.project_id, entity_type: "issue", entity_id: issue.id });
    toast.success("Issue logged");
    await onSaved();
  };
  return <FormModal title="Log issue or risk" close={close} onSubmit={submit} submitLabel="Save issue" testid="save-issue-button">
    <Select name="project_id" label="Project" full options={projectOptions(projects)} defaultValue={projectId || ""} testid="issue-project-select" />
    <Field name="title" label="Title" placeholder="Concrete delivery delay" full />
    <Select name="category" label="Type" options={["Issue", "Risk", "Struggle"]} testid="issue-category-select" />
    <Select name="severity" label="Severity" options={["High", "Medium", "Low"]} defaultValue="Medium" testid="issue-severity-select" />
    <Select name="owner_id" label="Action owner (gets overdue reminder)" required={false} options={[{ value: "", label: "Unassigned — managers only" }, ...(team || []).map(u => ({ value: u.user_id, label: `${u.name || u.email} · ${u.role}` }))]} testid="issue-owner-select" />
    <Field name="due_date" label="Follow-up due" type="date" required={false} />
    <Field name="description" label="Details & action required" type="textarea" full required={false} placeholder="What happened, impact, agreed action…" />
    <FilesField inputRef={files} />
  </FormModal>;
}

export function ActivityForm({ close, onSaved, projectId }) {
  const api = useApi();
  const submit = async f => {
    await api("post", "/activities", { ...f, project_id: projectId, weight: Number(f.weight || 1), progress: num(f.progress) });
    toast.success("Activity added");
    await onSaved();
  };
  return <FormModal title="Add activity" close={close} onSubmit={submit} submitLabel="Save activity" testid="save-activity-button">
    <Field name="name" label="Activity" placeholder="Pile caps — Pier 3" full />
    <Field name="owner" label="Owner / crew" placeholder="Site engineer" required={false} />
    <Field name="weight" label="Weight (share of project)" type="number" min={0.1} step={0.1} placeholder="1" required={false} />
    <Field name="progress" label="Progress %" type="number" min={0} max={100} placeholder="0" required={false} />
    <Select name="status" label="Status" options={["Not started", "In progress", "Completed"]} defaultValue="In progress" testid="activity-status-select" />
    <Field name="due_date" label="Due date" type="date" required={false} />
  </FormModal>;
}
