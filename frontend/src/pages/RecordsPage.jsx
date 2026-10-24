import { useState } from "react";
import { Plus } from "lucide-react";
import { useResource } from "@/lib/api";
import { Heading, Loading } from "@/components/civic/ui";
import { IssueForm, ReportForm } from "@/components/civic/forms";
import { IssueList, ReportList } from "@/components/civic/Records";
import ExportMenu from "@/components/civic/ExportMenu";

const CONFIG = {
  reports: { title: "Site reports", copy: "A field-ready record of progress, decisions, and site conditions.", label: "report", filterKey: "report_type", filters: ["All", "Daily", "Weekly"], List: ReportList, Form: ReportForm },
  issues: { title: "Issues & risks", copy: "Keep blockers, risks and follow-ups visible, owned, and moving toward resolution.", label: "issue", filterKey: "status", filters: ["All", "Open", "In progress", "Resolved"], List: IssueList, Form: IssueForm },
};

export default function RecordsPage({ type }) {
  const c = CONFIG[type];
  const [items, reload] = useResource(`/${type}`);
  const [projects] = useResource("/projects");
  const [filter, setFilter] = useState("All");
  const [project, setProject] = useState("");
  const [show, setShow] = useState(false);
  if (!items || !projects) return <Loading />;
  const shown = items.filter(x => (filter === "All" || x[c.filterKey] === filter) && (!project || x.project_id === project));
  return <div className="content">
    <Heading eyebrow="PROJECT OPERATIONS" title={c.title} copy={c.copy} actions={<><ExportMenu projectId={project || undefined} /><button className="primary-btn" data-testid={`new-${c.label}-button`} onClick={() => setShow(true)}><Plus size={17} /> New {c.label}</button></>} />
    <div className="list-page">
      <div className="list-toolbar"><b data-testid={`${type}-count`}>{shown.length} records</b>
        <div className="chips">{c.filters.map(f => <button key={f} className={filter === f ? "active" : ""} onClick={() => setFilter(f)} data-testid={`filter-${f.toLowerCase().replace(" ", "-")}`}>{f}</button>)}</div>
        <select className="toolbar-select" value={project} onChange={e => setProject(e.target.value)} data-testid="project-filter-select"><option value="">All projects</option>{projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</select>
      </div>
      <c.List {...{ [type]: shown }} reload={reload} />
    </div>
    {show && <c.Form projects={projects} projectId={project} close={() => setShow(false)} onSaved={reload} />}
  </div>;
}
