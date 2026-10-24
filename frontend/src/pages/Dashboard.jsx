import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { formatDistanceToNow, format } from "date-fns";
import { BarChart3, CheckCircle2, FileText, Flag, FolderKanban, Plus, ShieldAlert } from "lucide-react";
import { useMe, useResource } from "@/lib/api";
import { Heading, Kpi, Loading, Panel, Empty } from "@/components/civic/ui";
import { ProgressChart, ReportTrendChart, SeverityChart } from "@/components/civic/Charts";
import { ProjectForm, ReportForm } from "@/components/civic/forms";
import ExportMenu from "@/components/civic/ExportMenu";
import ProjectRow from "@/components/civic/ProjectRow";

const FEED = { report: { icon: FileText, color: "blue" }, issue: { icon: ShieldAlert, color: "red" }, activity: { icon: CheckCircle2, color: "green" } };
const greeting = () => { const h = new Date().getHours(); return h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening"; };

export default function Dashboard() {
  const [d, reload] = useResource("/dashboard");
  const me = useMe();
  const navigate = useNavigate();
  const [modal, setModal] = useState("");
  if (!d) return <Loading />;
  const k = d.kpis;
  return <div className="content">
    <Heading eyebrow={format(new Date(), "EEEE · d MMMM yyyy").toUpperCase()} title={`${greeting()}, ${me?.name?.split(" ")[0] || "team"}`} copy="Here's the pulse across your active construction portfolio."
      actions={<><ExportMenu /><button className="primary-btn" data-testid="new-site-report-button" onClick={() => setModal("report")}><Plus size={17} /> New site report</button></>} />
    <section className="kpi-grid">
      <Kpi label="Portfolio progress" value={`${k.avg_progress}%`} delta={`${k.on_track} on track`} note={`${k.at_risk} at risk`} tone="amber" icon={BarChart3} />
      <Kpi label="Active projects" value={k.projects} delta={`${k.at_risk} need attention`} note="across the portfolio" tone="blue" icon={FolderKanban} />
      <Kpi label="Open follow-ups" value={k.open_issues} delta={`${k.high_open} high priority`} note={`${k.overdue} overdue`} tone="red" icon={Flag} />
      <Kpi label="Reports this week" value={k.reports_week} delta={`${k.reports_total} total`} note="daily + weekly" tone="green" icon={FileText} />
    </section>
    <div className="chart-grid">
      <Panel eyebrow="PROGRESS" title="Completion by project" testid="chart-progress-panel"><ProgressChart projects={d.projects} /></Panel>
      <Panel eyebrow="RISK" title="Open issues by severity" testid="chart-severity-panel"><SeverityChart data={d.severity} /></Panel>
      <Panel eyebrow="REPORTING" title="Site reports per week" testid="chart-reports-panel"><ReportTrendChart weeks={d.weeks} /></Panel>
    </div>
    <div className="dashboard-grid">
      <Panel eyebrow="LIVE PORTFOLIO" title="Project health" testid="project-health-panel">
        <div className="project-list">{d.projects.map(p => <ProjectRow key={p.id} project={p} onClick={() => navigate(`/projects/${p.id}`)} />)}</div>
        <button className="add-project" data-testid="add-project-button" onClick={() => setModal("project")}><Plus size={17} /> Add a project</button>
      </Panel>
      <Panel eyebrow="FIELD LOG" title="Latest activity" testid="feed-panel">
        <div className="activity-list">{d.feed.length ? d.feed.map((f, i) => { const { icon: Icon, color } = FEED[f.type]; return <div className="activity" key={i} data-testid={`feed-item-${i}`}><span className={`activity-icon ${color}`}><Icon size={16} /></span><div><b>{f.title}</b><small>{f.project_name} · {f.by || "Team"} · {formatDistanceToNow(new Date(f.created_at), { addSuffix: true })}</small></div></div>; }) : <Empty testid="feed-empty">Nothing logged yet. Submit a report or log an issue.</Empty>}</div>
      </Panel>
    </div>
    <section className="insight-band"><div className="insight-copy"><span className="insight-icon"><ShieldAlert size={19} /></span><div><p className="eyebrow">ATTENTION REQUIRED</p><h3 data-testid="insight-title">{k.open_issues ? `${k.open_issues} open follow-ups · ${k.overdue} overdue` : "Portfolio is clear"}</h3><p>Keep your next site walk focused on risk items and overdue actions.</p></div></div><button className="dark-btn" data-testid="review-issues-button" onClick={() => navigate("/issues")}>Review issues →</button></section>
    {modal === "project" && <ProjectForm close={() => setModal("")} onSaved={reload} />}
    {modal === "report" && <ReportForm close={() => setModal("")} onSaved={reload} projects={d.projects} />}
  </div>;
}
