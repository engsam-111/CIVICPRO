import { Badge, Progress, toneFor } from "@/components/civic/ui";

export default function ProjectRow({ project: p, onClick }) {
  return <button className="project-row" onClick={onClick} data-testid={`project-row-${p.code}`}>
    <div className="project-code">{p.code}</div>
    <div className="project-info"><b>{p.name}</b><small>{p.location || "—"} · {p.client || "—"}</small></div>
    <div className="progress-wrap"><div className="progress-label"><span>{p.progress}% · {p.progress_mode === "activity" ? `${p.activity_count} activities` : "manual"}</span><Badge tone={toneFor(p.status)}>{p.status}</Badge></div><Progress value={p.progress} /></div>
    <span className="row-arrow">→</span>
  </button>;
}
