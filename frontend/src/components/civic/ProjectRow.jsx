import { Badge, Progress, toneFor } from "@/components/civic/ui";

export const Variance = ({ value, testid }) => value == null ? null
  : <Badge tone={value >= 0 ? "green" : value > -10 ? "amber" : "red"} testid={testid}>{value >= 0 ? "+" : ""}{value}% vs plan</Badge>;

export default function ProjectRow({ project: p, onClick }) {
  return <button className="project-row" onClick={onClick} data-testid={`project-row-${p.code}`}>
    <div className="project-code">{p.code}</div>
    <div className="project-info"><b>{p.name}</b><small>{p.location || "—"} · {p.client || "—"}</small></div>
    <div className="progress-wrap"><div className="progress-label"><span>{p.progress}% · {p.progress_mode === "activity" ? `${p.activity_count} activities` : "manual"}</span><span className="badges"><Variance value={p.schedule_variance} testid={`variance-${p.code}`} /><Badge tone={toneFor(p.status)}>{p.status}</Badge></span></div><Progress value={p.progress} planned={p.planned_progress} /></div>
    <span className="row-arrow">→</span>
  </button>;
}
