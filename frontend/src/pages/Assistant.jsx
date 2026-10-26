import { useEffect, useRef, useState } from "react";
import { useAuth } from "@clerk/react";
import { MessageSquarePlus, Send, Sparkles, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { API, useApi } from "@/lib/api";
import { Heading } from "@/components/civic/ui";

const STARTERS = ["Which projects are behind plan and why?", "Summarise this week's site reports", "List high-severity open issues with owners", "What should I check on my next site walk?"];

const Md = ({ text }) => text.split(/(\*\*[^*]+\*\*)/g).map((t, i) => t.startsWith("**") && t.endsWith("**") ? <b key={i}>{t.slice(2, -2)}</b> : t);

export default function Assistant() {
  const api = useApi();
  const { getToken } = useAuth();
  const [sessions, setSessions] = useState([]);
  const [sid, setSid] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const end = useRef(null);
  const loadSessions = () => api("get", "/ai/chat/sessions").then(setSessions).catch(() => {});
  useEffect(() => { loadSessions(); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  const open = async id => { if (busy) return; setSid(id); setMessages(await api("get", `/ai/chat/sessions/${id}`)); };
  const remove = async id => {
    if (busy) return;
    try { await api("delete", `/ai/chat/sessions/${id}`); if (id === sid) { setSid(null); setMessages([]); } loadSessions(); }
    catch { toast.error("Could not delete conversation"); }
  };

  const send = async text => {
    const message = (text ?? input).trim();
    if (!message || busy) return;
    setInput("");
    setBusy(true);
    setMessages(m => [...m, { role: "user", content: message }, { role: "assistant", content: "" }]);
    const append = chunk => setMessages(m => { const c = [...m]; c[c.length - 1] = { ...c[c.length - 1], content: c[c.length - 1].content + chunk }; return c; });
    const isNew = !sid;
    let got = false;
    try {
      const res = await fetch(`${API}/ai/chat`, { method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${await getToken()}` }, body: JSON.stringify({ message, session_id: sid }) });
      if (!res.ok) { const d = await res.json().catch(() => ({})); throw new Error(typeof d.detail === "string" ? d.detail : "AI request failed"); }
      const reader = res.body.getReader();
      const dec = new TextDecoder();
      let buf = "";
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        const parts = buf.split("\n\n");
        buf = parts.pop();
        for (const p of parts) {
          if (!p.startsWith("data: ")) continue;
          const ev = JSON.parse(p.slice(6));
          if (ev.type === "session") setSid(ev.session_id);
          if (ev.type === "delta") { got = true; append(ev.content); }
          if (ev.type === "error") { append(ev.message); toast.error(ev.message); }
        }
      }
      if (isNew && !got) setSid(null);
      loadSessions();
    } catch (e) { if (isNew) setSid(null); append(e.message ? e.message : "Sorry, I couldn't reach the AI. Please try again."); toast.error(e.message || "AI request failed"); }
    finally { setBusy(false); }
  };

  return <div className="content">
    <Heading eyebrow="AI ASSISTANT · GPT-6 ASTRA" title="Ask CIVICPRO" copy="Ask anything about your projects, reports, issues and schedule. Answers use your live workspace data." />
    <div className="assistant-layout">
      <aside className="assistant-sessions" data-testid="chat-sessions">
        <button className="ghost-btn" disabled={busy} onClick={() => { setSid(null); setMessages([]); }} data-testid="new-chat-button"><MessageSquarePlus size={15} /> New conversation</button>
        {sessions.map(s => <div key={s.id} className={`session ${s.id === sid ? "active" : ""}`}><button disabled={busy} onClick={() => open(s.id)} data-testid={`chat-session-${s.id}`}>{s.title}</button><button className="icon-btn small" disabled={busy} onClick={() => remove(s.id)} aria-label="Delete conversation" data-testid={`delete-chat-${s.id}`}><Trash2 size={13} /></button></div>)}
      </aside>
      <section className="assistant-main">
        <div className="chat-log" data-testid="chat-log">
          {!messages.length && <div className="chat-empty"><Sparkles size={22} /><p>Try one of these:</p><div className="starters">{STARTERS.map((s, i) => <button key={s} onClick={() => send(s)} data-testid={`starter-${i}`}>{s}</button>)}</div></div>}
          {messages.map((m, i) => <div key={i} className={`msg ${m.role}`} data-testid={`chat-message-${m.role}-${i}`}>{m.content ? <Md text={m.content} /> : <span className="typing">Thinking<i>.</i><i>.</i><i>.</i></span>}</div>)}
          <div ref={end} />
        </div>
        <form className="chat-input" onSubmit={e => { e.preventDefault(); send(); }}>
          <textarea value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }} placeholder="Ask about progress, risks, reports…" data-testid="chat-input" rows={2} />
          <button className="primary-btn" disabled={busy || !input.trim()} data-testid="chat-send-button"><Send size={16} /></button>
        </form>
      </section>
    </div>
  </div>;
}
