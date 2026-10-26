import { NavLink, Outlet, useLocation } from "react-router-dom";
import { UserButton } from "@clerk/react";
import { FileText, FolderKanban, LayoutDashboard, ShieldAlert, Sparkles, Users } from "lucide-react";
import { useMe } from "@/lib/api";

const NAV = [{ to: "/", label: "Overview", icon: LayoutDashboard }, { to: "/projects", label: "Projects", icon: FolderKanban }, { to: "/reports", label: "Site reports", icon: FileText }, { to: "/issues", label: "Issues & risks", icon: ShieldAlert }, { to: "/assistant", label: "AI assistant", icon: Sparkles }];
const initials = (name = "") => name.split(" ").map(x => x[0]).join("").slice(0, 2).toUpperCase() || "CP";

export default function Shell() {
  const me = useMe();
  const { pathname } = useLocation();
  const active = me?.status === "active";
  const nav = !active ? [] : me.role === "manager" ? [...NAV, { to: "/team", label: "Team", icon: Users }] : NAV;
  const crumb = pathname === "/" ? "OVERVIEW" : pathname.split("/")[1].toUpperCase();
  return <div className="app-shell">
    <aside className="sidebar"><div className="brand"><span className="brand-mark">CP</span><div><strong>CIVICPRO</strong><small>FIELD COMMAND</small></div></div>
      <div className="workspace-label">WORKSPACE</div>
      <div className="project-switch" data-testid="project-switch"><span className="project-dot" /><div><b>Team workspace</b><small>Shared portfolio</small></div></div>
      <nav>{nav.map(({ to, label, icon: Icon }) => <NavLink key={to} to={to} end={to === "/"} data-testid={`nav-${label.toLowerCase().replaceAll(" ", "-").replace("&", "and")}`}><Icon size={18} /><span>{label}</span></NavLink>)}</nav>
      <div className="sidebar-footer"><div className="sync"><span className="online-dot" />Signed in as <b data-testid="current-role">{me?.role || "…"}</b></div>
        <div className="user-mini"><div className="avatar">{initials(me?.name)}</div><div><b data-testid="current-user-name">{me?.name || "Team member"}</b><small>{me?.email}</small></div></div></div>
    </aside>
    <main className="main-area"><header className="topbar"><div className="crumb">PORTFOLIO <span>/</span> <b>{crumb}</b></div><div className="top-actions"><UserButton /></div></header>
      {!me ? <div className="loading-inline" data-testid="page-loading">Preparing workspace…</div>
        : me.status !== "active" ? <div className="content"><section className="insight-band" data-testid="pending-approval"><div className="insight-copy"><div><p className="eyebrow">{me.status === "pending" ? "WAITING FOR APPROVAL" : "ACCESS DECLINED"}</p>
          <h3>{me.status === "pending" ? "A manager needs to approve your access" : "Your access to this workspace was declined"}</h3>
          <p>{me.status === "pending" ? `You're signed in as ${me.email}. Ask your project manager to approve you on the Team page, then refresh.` : "Contact your project manager if you think this is a mistake."}</p></div></div>
          {me.status === "pending" && <button className="dark-btn" onClick={() => window.location.reload()} data-testid="pending-refresh-button">Refresh</button>}</section></div>
        : <Outlet />}</main>
  </div>;
}
