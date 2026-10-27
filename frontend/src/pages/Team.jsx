import { useState } from "react";
import { Navigate } from "react-router-dom";
import { Check, KeyRound, X } from "lucide-react";
import { toast } from "sonner";
import { errorText, useApi, useMe, useResource } from "@/lib/api";
import { Badge, Heading, Loading, Modal } from "@/components/civic/ui";

function ResetPassword({ u, close }) {
  const api = useApi();
  const [pw, setPw] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async e => {
    e.preventDefault(); setBusy(true);
    try { await api("post", `/users/${u.user_id}/password`, { password: pw }); toast.success(`Password reset for ${u.name || u.email}. They've been signed out everywhere.`); close(); }
    catch (err) { toast.error(errorText(err, "Could not reset password")); }
    finally { setBusy(false); }
  };
  return <Modal title={`Reset password · ${u.name || u.email}`} close={close}><form className="form-grid" onSubmit={submit}>
    <label className="field full"><span>New password (min. 8 characters)</span><input type="password" value={pw} onChange={e => setPw(e.target.value)} minLength={8} maxLength={128} required autoComplete="new-password" data-testid="new-password-input" /></label>
    <p className="muted-note full">Share it with them privately. They'll be signed out of all devices and can change it later from their profile menu.</p>
    <button className="primary-btn form-submit" disabled={busy || pw.length < 8} data-testid="save-password-button">{busy ? "Saving…" : "Set new password"}</button>
  </form></Modal>;
}

function Member({ u, roles, me, update }) {
  const [reset, setReset] = useState(false);
  const meOwner = me.is_owner;
  const self = u.user_id === me.user_id;
  const locked = self || u.is_owner;
  return <div className="team-row" data-testid={`team-member-${u.user_id}`}>
    <div className="avatar light">{(u.name || u.email || "?").slice(0, 2).toUpperCase()}</div>
    <div className="record-main"><b>{u.name || "Team member"}{self && " (you)"} {u.status !== "active" && <Badge tone={u.status === "pending" ? "amber" : "red"} testid={`member-status-${u.user_id}`}>{u.status}</Badge>}</b><small>{u.email || "—"} · joined {u.created_at?.slice(0, 10)}</small></div>
    {u.status === "pending" ? <div className="approve-actions">
      <button className="primary-btn small" onClick={() => update(u, { status: "active" }, "approved")} data-testid={`approve-${u.user_id}`}><Check size={14} /> Approve</button>
      <button className="ghost-btn small" onClick={() => update(u, { status: "rejected" }, "declined")} data-testid={`decline-${u.user_id}`}><X size={14} /> Decline</button></div>
      : u.status === "rejected" ? <button className="ghost-btn small" onClick={() => update(u, { status: "active" }, "restored")} data-testid={`restore-${u.user_id}`}>Restore access</button>
      : <div className="approve-actions"><select className="status-select" value={u.role} disabled={locked} onChange={e => update(u, { role: e.target.value }, `now ${e.target.value}`)} data-testid={`role-select-${u.user_id}`}>{roles.map(r => <option key={r} value={r}>{r}</option>)}</select>
        {u.is_owner && <Badge tone="amber" testid={`owner-badge-${u.user_id}`}>owner</Badge>}
        {!self && u.status === "active" && (meOwner || (u.role !== "manager" && !u.is_owner)) && <button className="icon-btn small" title="Reset password" onClick={() => setReset(true)} data-testid={`reset-password-${u.user_id}`}><KeyRound size={14} /></button>}
        {!locked && <button className="icon-btn small" title="Remove access" onClick={() => window.confirm(`Remove ${u.name || u.email}'s access?`) && update(u, { status: "rejected" }, "removed")} data-testid={`remove-${u.user_id}`}><X size={14} /></button>}</div>}
    {reset && <ResetPassword u={u} close={() => setReset(false)} />}
  </div>;
}

function TeamTable() {
  const api = useApi();
  const me = useMe();
  const [data, reload] = useResource("/users");
  if (!data) return <Loading />;
  const update = async (u, body, verb) => {
    try { await api("patch", `/users/${u.user_id}`, body); toast.success(`${u.name || u.email} ${verb}`); reload(); }
    catch (e) { toast.error(errorText(e, "Could not update member")); }
  };
  const pending = data.users.filter(u => u.status === "pending");
  const rest = data.users.filter(u => u.status !== "pending");
  return <>
    {pending.length > 0 && <div className="list-page pending-list" data-testid="pending-members"><div className="list-toolbar"><b data-testid="pending-count">{pending.length} waiting for approval</b><span>They can't see any project data until you approve them.</span></div>
      <div className="record-list">{pending.map(u => <Member key={u.user_id} u={u} roles={data.roles} me={me} update={update} />)}</div></div>}
    <div className="list-page"><div className="list-toolbar"><b data-testid="team-count">{rest.filter(u => u.status === "active").length} active members</b><span>New sign-ups wait for approval and join as engineers. Everyone approved works on all projects; only managers manage the team.</span></div>
      <div className="record-list">{rest.map(u => <Member key={u.user_id} u={u} roles={data.roles} me={me} update={update} />)}</div></div>
  </>;
}

export default function Team() {
  const me = useMe();
  if (me.role !== "manager") return <Navigate to="/" replace />;
  return <div className="content"><Heading eyebrow="ADMINISTRATION" title="Team" copy="Approve new sign-ups and assign engineer, supervisor and manager roles." /><TeamTable /></div>;
}
