import { Navigate } from "react-router-dom";
import { toast } from "sonner";
import { errorText, useApi, useMe, useResource } from "@/lib/api";
import { Heading, Loading } from "@/components/civic/ui";

function TeamTable() {
  const api = useApi();
  const me = useMe();
  const [data, reload] = useResource("/users");
  if (!data) return <Loading />;
  const change = async (u, role) => {
    try { await api("patch", `/users/${u.user_id}`, { role }); toast.success(`${u.name || u.email} is now ${role}`); reload(); }
    catch (e) { toast.error(errorText(e, "Could not change role")); }
  };
  return <div className="list-page"><div className="list-toolbar"><b data-testid="team-count">{data.users.length} members</b><span>New members join as engineers when they first sign in. Everyone can work on all projects; only managers manage the team.</span></div>
    <div className="record-list">{data.users.map(u => <div className="team-row" key={u.user_id} data-testid={`team-member-${u.user_id}`}>
      <div className="avatar light">{(u.name || u.email || "?").slice(0, 2).toUpperCase()}</div>
      <div className="record-main"><b>{u.name || "Team member"}{u.user_id === me.user_id && " (you)"}</b><small>{u.email || "—"} · joined {u.created_at?.slice(0, 10)}</small></div>
      <select className="status-select" value={u.role} disabled={u.user_id === me.user_id} onChange={e => change(u, e.target.value)} data-testid={`role-select-${u.user_id}`}>{data.roles.map(r => <option key={r} value={r}>{r}</option>)}</select>
    </div>)}</div></div>;
}

export default function Team() {
  const me = useMe();
  if (me.role !== "manager") return <Navigate to="/" replace />;
  return <div className="content"><Heading eyebrow="ADMINISTRATION" title="Team" copy="Assign engineer, supervisor and manager roles to your site team." /><TeamTable /></div>;
}
