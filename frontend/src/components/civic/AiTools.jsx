import { useRef, useState } from "react";
import { Sparkles } from "lucide-react";
import { toast } from "sonner";
import { errorText, useApi } from "@/lib/api";

export function AiDraft() {
  const api = useApi();
  const box = useRef(null);
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const draft = async () => {
    const form = box.current.closest("form");
    const project_id = form.elements.project_id?.value;
    if (!project_id) return toast.error("Choose a project first");
    setBusy(true);
    try {
      const d = await api("post", "/ai/draft-report", { project_id, notes, report_type: form.elements.report_type.value });
      Object.entries(d).forEach(([k, v]) => { if (form.elements[k]) form.elements[k].value = v; });
      toast.success("Draft ready, review and edit before submitting");
    } catch (e) { toast.error(errorText(e, "AI draft failed")); }
    finally { setBusy(false); }
  };
  return <div className="ai-box full" ref={box} data-testid="ai-draft-box">
    <div className="ai-box-head"><Sparkles size={15} /><b>Draft with AI</b><small>Paste rough site notes. AI fills the fields below.</small></div>
    <textarea value={notes} onChange={e => setNotes(e.target.value)} placeholder="e.g. 18 guys today, poured pier 3 cap 42m3, pump late 1hr, rain after 3pm, tomorrow rebar pier 4, waiting on RFI 12…" data-testid="ai-notes-input" />
    <button type="button" className="ai-btn" onClick={draft} disabled={busy || notes.trim().length < 3} data-testid="ai-draft-button"><Sparkles size={14} />{busy ? "Drafting…" : "Draft report"}</button>
  </div>;
}

export function AiSuggest({ issue, reload }) {
  const api = useApi();
  const [busy, setBusy] = useState(false);
  const s = issue.ai_suggestion;
  const run = async () => {
    setBusy(true);
    try { await api("post", `/ai/issues/${issue.id}/suggest`); await reload(); }
    catch (e) { toast.error(errorText(e, "AI suggestion failed")); }
    finally { setBusy(false); }
  };
  const patch = async (body, msg) => {
    try { await api("patch", `/issues/${issue.id}`, body); toast.success(msg); reload(); }
    catch (e) { toast.error(errorText(e, "Could not update issue")); }
  };
  const actionsText = () => s.actions.map(a => `- ${a.action} (${a.owner_role}, ${a.timeframe})`).join("\n");
  return <div className="ai-suggest" data-testid={`ai-suggest-${issue.id}`}>
    <div className="ai-box-head"><Sparkles size={15} /><b>AI suggested actions</b>
      <button type="button" className="ai-btn small" onClick={run} disabled={busy} data-testid={`ai-suggest-button-${issue.id}`}>{busy ? "Thinking…" : s ? "Regenerate" : "Suggest actions"}</button></div>
    {s && <>
      <p className="ai-rationale" data-testid={`ai-rationale-${issue.id}`}><b>Suggested severity: {s.severity}{s.escalate ? " · escalate" : ""}.</b> {s.rationale}</p>
      <ol className="ai-actions">{s.actions.map((a, n) => <li key={n}>{a.action}<small>{a.owner_role} · {a.timeframe}</small></li>)}</ol>
      <div className="ai-apply">
        {s.severity !== issue.severity && <button type="button" className="text-btn" onClick={() => patch({ severity: s.severity }, `Severity set to ${s.severity}`)} data-testid={`ai-apply-severity-${issue.id}`}>Apply severity</button>}
        {!(issue.description || "").includes("Agreed actions:") && <button type="button" className="text-btn" onClick={() => patch({ description: `${issue.description ? issue.description + "\n\n" : ""}Agreed actions:\n${actionsText()}` }, "Actions added to details")} data-testid={`ai-apply-actions-${issue.id}`}>Add actions to details</button>}
      </div></>}
  </div>;
}
