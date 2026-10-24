import { useState } from "react";
import { ChevronDown, FileText, Pencil, ShieldAlert, Trash2 } from "lucide-react";
import { ReportForm } from "@/components/civic/forms";
import { AiSuggest } from "@/components/civic/AiTools";
import { toast } from "sonner";
import { errorText, useApi } from "@/lib/api";
import { AttachmentList, Uploader } from "@/components/civic/Attachments";
import { Badge, Empty, toneFor } from "@/components/civic/ui";

function Row({ id, icon, tone, title, meta, right, date, children, testid }) {
  const [open, setOpen] = useState(false);
  return <div className={`record ${open ? "open" : ""}`} data-testid={testid}>
    <div role="button" tabIndex={0} aria-expanded={open} className="record-row" onClick={() => setOpen(!open)} onKeyDown={e => { if ((e.key === "Enter" || e.key === " ") && e.target === e.currentTarget) { e.preventDefault(); setOpen(!open); } }} data-testid={`${testid}-toggle`}>
      <div className={`record-symbol ${tone}`}>{icon}</div>
      <div className="record-main"><b>{title}</b><small>{meta}</small></div>
      <span className="record-status">{right}</span>
      <span className="record-date">{date}<ChevronDown size={14} /></span>
    </div>
    {open && <div className="record-body" data-testid={`${testid}-details`}>{children}</div>}
  </div>;
}

function Remove({ url, label, onDone, testid }) {
  const api = useApi();
  const go = async () => {
    if (!window.confirm(`Delete this ${label}?`)) return;
    try { await api("delete", url); toast.success(`${label} deleted`); onDone(); }
    catch (e) { toast.error(errorText(e, `Could not delete ${label}`)); }
  };
  return <button type="button" className="text-btn danger" onClick={go} data-testid={testid}><Trash2 size={13} /> Delete {label}</button>;
}

function EditReport({ report, reload }) {
  const [show, setShow] = useState(false);
  return <><button type="button" className="text-btn" onClick={() => setShow(true)} data-testid={`edit-report-${report.id}`}><Pencil size={13} /> Edit report</button>
    {show && <ReportForm report={report} close={() => setShow(false)} onSaved={reload} />}</>;
}

export function ReportList({ reports, reload }) {
  if (!reports.length) return <Empty testid="reports-empty">No site reports yet. Submit the first one from the field.</Empty>;
  return <div className="record-list">{reports.map(r => <Row key={r.id} testid={`report-${r.id}`} icon={<FileText size={18} />} tone="blue" title={r.title}
    meta={`${r.project_name} · ${r.workforce} on site · ${r.progress}% · ${r.files?.length || 0} files`} right={<Badge tone={toneFor(r.report_type)}>{r.report_type}</Badge>} date={r.report_date || r.created_at.slice(0, 10)}>
    <div className="detail-grid"><div><span>Work completed</span><p>{r.summary}</p></div>{r.next_steps && <div><span>Planned next / blockers</span><p>{r.next_steps}</p></div>}
      {r.weather && <div><span>Conditions</span><p>{r.weather}</p></div>}<div><span>Submitted by</span><p>{r.created_by_name || "Team member"}</p></div></div>
    <AttachmentList files={r.files} onChange={reload} />
    <div className="record-actions"><Uploader target={{ project_id: r.project_id, entity_type: "report", entity_id: r.id }} onDone={reload} testid={`report-${r.id}-upload`} /><div className="record-actions-right"><EditReport report={r} reload={reload} /><Remove url={`/reports/${r.id}`} label="report" onDone={reload} testid={`delete-report-${r.id}`} /></div></div>
  </Row>)}</div>;
}

function StatusSelect({ issue, reload }) {
  const api = useApi();
  const change = async e => {
    try { await api("patch", `/issues/${issue.id}`, { status: e.target.value }); toast.success(`Marked ${e.target.value}`); reload(); }
    catch (err) { toast.error(errorText(err, "Could not update")); }
  };
  return <select className={`status-select tone-${toneFor(issue.status)}`} value={issue.status} onClick={e => e.stopPropagation()} onChange={change} data-testid={`issue-status-${issue.id}`}>
    {["Open", "In progress", "Resolved"].map(s => <option key={s}>{s}</option>)}</select>;
}

export function IssueList({ issues, reload }) {
  if (!issues.length) return <Empty testid="issues-empty">No issues logged. Blockers will show here.</Empty>;
  const today = new Date().toISOString().slice(0, 10);
  return <div className="record-list">{issues.map(i => {
    const overdue = i.status !== "Resolved" && i.due_date && i.due_date < today;
    return <Row key={i.id} testid={`issue-${i.id}`} icon={<ShieldAlert size={18} />} tone={toneFor(i.severity)} title={i.title}
      meta={<>{i.project_name} · <Badge tone={toneFor(i.severity)}>{i.severity}</Badge> {i.category} · {i.owner || "Unassigned"}{overdue && <Badge tone="red" testid={`overdue-${i.id}`}>Overdue</Badge>}{i.reminder_sent_at && <Badge tone="slate" testid={`reminded-${i.id}`}>Reminder sent {i.reminder_sent_at.slice(0, 10)}</Badge>}</>}
      right={<StatusSelect issue={i} reload={reload} />} date={i.due_date ? `Due ${i.due_date}` : i.created_at.slice(0, 10)}>
      <div className="detail-grid"><div><span>Details & action</span><p>{i.description || "No details added."}</p></div><div><span>Logged by</span><p>{i.created_by_name || "Team member"} · {i.created_at.slice(0, 10)}</p></div></div>
      <AiSuggest issue={i} reload={reload} />
      <AttachmentList files={i.files} onChange={reload} />
      <div className="record-actions"><Uploader target={{ project_id: i.project_id, entity_type: "issue", entity_id: i.id }} onDone={reload} testid={`issue-${i.id}-upload`} /><Remove url={`/issues/${i.id}`} label="issue" onDone={reload} testid={`delete-issue-${i.id}`} /></div>
    </Row>;
  })}</div>;
}
