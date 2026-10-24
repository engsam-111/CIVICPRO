import { useState } from "react";
import { Download, FileSpreadsheet, FileText } from "lucide-react";
import { toast } from "sonner";
import { saveBlob, useApi } from "@/lib/api";

const OPTIONS = [
  { key: "daily", label: "Daily report", sub: "PDF · last 24h", fmt: "pdf", days: 1, icon: FileText },
  { key: "weekly", label: "Weekly report", sub: "PDF · last 7 days", fmt: "pdf", days: 7, icon: FileText },
  { key: "full-pdf", label: "Full report", sub: "PDF · all records", fmt: "pdf", icon: FileText },
  { key: "excel", label: "Excel workbook", sub: "XLSX · all records", fmt: "xlsx", icon: FileSpreadsheet },
];

export default function ExportMenu({ projectId }) {
  const api = useApi();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState("");
  const run = async o => {
    setBusy(o.key);
    try {
      const q = new URLSearchParams({ fmt: o.fmt, ...(o.days ? { days: o.days } : {}), ...(projectId ? { project_id: projectId } : {}) });
      const blob = await api("get", `/export?${q}`, null, { responseType: "blob" });
      saveBlob(blob, `civicpro-${o.key}-${new Date().toISOString().slice(0, 10)}.${o.fmt}`);
      toast.success(`${o.label} downloaded`);
      setOpen(false);
    } catch { toast.error("Export failed"); }
    finally { setBusy(""); }
  };
  return <div className="export-menu">
    <button className="ghost-btn" onClick={() => setOpen(!open)} data-testid="export-menu-button"><Download size={16} /> Export</button>
    {open && <div className="export-pop" data-testid="export-menu">{OPTIONS.map(o => <button key={o.key} onClick={() => run(o)} disabled={!!busy} data-testid={`export-${o.key}-button`}><o.icon size={16} /><span><b>{busy === o.key ? "Preparing…" : o.label}</b><small>{o.sub}</small></span></button>)}</div>}
  </div>;
}
