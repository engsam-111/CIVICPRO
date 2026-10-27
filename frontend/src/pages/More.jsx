import { Link } from "react-router-dom";
import { ChevronRight, Sparkles, Users, Wifi, WifiOff } from "lucide-react";
import { useMe } from "@/lib/api";
import { Heading } from "@/components/civic/ui";
import { InstallPanel } from "@/components/mobile/InstallPanel";
import { usePwa } from "@/components/mobile/PwaProvider";

export default function More() {
  const me = useMe();
  const { online } = usePwa();
  return <div className="content more-page">
    <Heading eyebrow="YOUR WORKSPACE" title="More" />
    <div className="mobile-account" data-testid="workspace-account"><div className="avatar light">{(me.name || "CP").slice(0, 2).toUpperCase()}</div><div><b>{me.name}</b><p>{me.email}</p><span>{me.role}</span></div></div>
    <section className="more-links" aria-label="Workspace tools">
      <Link to="/assistant" data-testid="more-assistant-link"><Sparkles size={22} /><div><b>AI assistant</b><span>Project insights & conversations</span></div><ChevronRight size={18} /></Link>
      {me.role === "manager" && <Link to="/team" data-testid="more-team-link"><Users size={22} /><div><b>Team management</b><span>Members, approvals & passwords</span></div><ChevronRight size={18} /></Link>}
    </section>
    <InstallPanel />
    <p className={`connection-state ${online ? "online" : "offline"}`} data-testid="connection-status">{online ? <Wifi size={16} /> : <WifiOff size={16} />}{online ? "Connected" : "Offline — reconnect to save updates"}</p>
  </div>;
}