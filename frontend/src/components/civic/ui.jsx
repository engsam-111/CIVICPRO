import { useState } from "react";
import { X } from "lucide-react";
import { toast } from "sonner";
import { errorText } from "@/lib/api";

export function Heading({ title, eyebrow, copy, actions }) {
  return <div className="page-heading"><div><p className="eyebrow">{eyebrow}</p><h1 data-testid="page-title">{title}<span>.</span></h1>{copy && <p className="subheading">{copy}</p>}</div><div className="heading-actions">{actions}</div></div>;
}

export function Field({ name, label, type = "text", placeholder, required = true, defaultValue, full, min, max, step }) {
  return <label className={`field ${full ? "full" : ""}`}><span>{label}</span>
    {type === "textarea"
      ? <textarea name={name} required={required} placeholder={placeholder} defaultValue={defaultValue} data-testid={`${name}-input`} />
      : <input name={name} type={type} required={required} placeholder={placeholder} defaultValue={defaultValue} min={min} max={max} step={step} data-testid={`${name}-input`} />}
  </label>;
}

export function Select({ name, label, options, defaultValue, full, required = true, testid }) {
  return <label className={`field ${full ? "full" : ""}`}><span>{label}</span>
    <select name={name} defaultValue={defaultValue} required={required} data-testid={testid || `${name}-select`}>
      {options.map(o => typeof o === "string" ? <option key={o} value={o}>{o}</option> : <option key={o.value} value={o.value}>{o.label}</option>)}
    </select></label>;
}

export function Modal({ title, close, children }) {
  return <div className="modal-backdrop" onMouseDown={e => e.target === e.currentTarget && close()}><div className="modal" role="dialog" data-testid="form-modal"><div className="modal-header"><h2>{title}</h2><button type="button" className="icon-btn" onClick={close} data-testid="close-modal-button" aria-label="Close"><X size={18} /></button></div>{children}</div></div>;
}

export function FormModal({ title, close, onSubmit, submitLabel, testid, children }) {
  const [busy, setBusy] = useState(false);
  const submit = async e => {
    e.preventDefault();
    setBusy(true);
    try { await onSubmit(Object.fromEntries(new FormData(e.target)), e.target); close(); }
    catch (err) { toast.error(errorText(err, "Could not save")); }
    finally { setBusy(false); }
  };
  return <Modal title={title} close={close}><form onSubmit={submit} className="form-grid">{children}<button className="primary-btn form-submit" disabled={busy} data-testid={testid}>{busy ? "Saving…" : submitLabel}</button></form></Modal>;
}

export function Panel({ eyebrow, title, children, actions, testid }) {
  return <section className="section-panel" data-testid={testid}><div className="panel-header"><div><p className="eyebrow">{eyebrow}</p><h2>{title}</h2></div>{actions}</div>{children}</section>;
}

export const Loading = ({ label = "Loading project intelligence…" }) => <div className="loading-inline" data-testid="page-loading">{label}</div>;
export const Empty = ({ children, testid }) => <div className="empty-state" data-testid={testid}>{children}</div>;
export const Progress = ({ value }) => <div className="progress"><i style={{ width: `${value}%` }} /></div>;
export const Badge = ({ tone = "slate", children, testid }) => <span className={`badge badge-${tone}`} data-testid={testid}>{children}</span>;
export const toneFor = v => ({ High: "red", Medium: "amber", Low: "blue", Open: "red", "In progress": "amber", Resolved: "green", "At risk": "red", Active: "green", Completed: "blue", "On hold": "slate", Daily: "blue", Weekly: "amber", "Not started": "slate" }[v] || "slate");

export function Kpi({ label, value, delta, note, tone, icon: Icon }) {
  return <div className={`kpi kpi-${tone}`} data-testid={`kpi-${label.toLowerCase().replaceAll(" ", "-")}`}><div className="kpi-top"><span>{label}</span><Icon size={18} /></div><strong>{value}</strong><div><b>{delta}</b><small>{note}</small></div></div>;
}
