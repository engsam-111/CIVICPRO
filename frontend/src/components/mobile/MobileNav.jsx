import { NavLink } from "react-router-dom";
import { FileText, FolderKanban, House, LayoutGrid, ShieldAlert } from "lucide-react";

const links = [
  { to: "/", label: "Home", icon: House },
  { to: "/projects", label: "Projects", icon: FolderKanban },
  { to: "/reports", label: "Reports", icon: FileText },
  { to: "/issues", label: "Issues", icon: ShieldAlert },
  { to: "/more", label: "More", icon: LayoutGrid },
];
export const MobileNav = ({ pathname }) => <nav className="mobile-nav" aria-label="Mobile workspace navigation" data-testid="mobile-navigation">
  {links.map(({ to, label, icon: Icon }) => <NavLink key={to} to={to} end={to === "/"} data-testid={`mobile-nav-${label.toLowerCase()}`} className={({ isActive }) => isActive || (to === "/more" && ["/team", "/assistant"].includes(pathname)) ? "active" : ""}><Icon size={21} strokeWidth={1.8} /><span>{label}</span></NavLink>)}
</nav>;