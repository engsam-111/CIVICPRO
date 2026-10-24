import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Plus } from "lucide-react";
import { useResource } from "@/lib/api";
import { Empty, Heading, Loading } from "@/components/civic/ui";
import { ProjectForm } from "@/components/civic/forms";
import ExportMenu from "@/components/civic/ExportMenu";
import ProjectRow from "@/components/civic/ProjectRow";

export default function Projects() {
  const [projects, reload] = useResource("/projects");
  const [show, setShow] = useState(false);
  const navigate = useNavigate();
  if (!projects) return <Loading />;
  return <div className="content">
    <Heading eyebrow="PROJECT OPERATIONS" title="Projects" copy="Monitor every active job, its progress basis, and current delivery status."
      actions={<><ExportMenu /><button className="primary-btn" data-testid="new-project-button" onClick={() => setShow(true)}><Plus size={17} /> New project</button></>} />
    <div className="list-page"><div className="list-toolbar"><b data-testid="projects-count">{projects.length} projects</b><span>Click a project to manage activities, reports, issues and files</span></div>
      <div className="project-list flush">{projects.length ? projects.map(p => <ProjectRow key={p.id} project={p} onClick={() => navigate(`/projects/${p.id}`)} />) : <Empty testid="projects-empty">No projects yet.</Empty>}</div></div>
    {show && <ProjectForm close={() => setShow(false)} onSaved={reload} />}
  </div>;
}
