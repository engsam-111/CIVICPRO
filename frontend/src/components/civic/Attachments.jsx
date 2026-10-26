import { useEffect, useRef, useState } from "react";
import { FileText, Paperclip, Trash2, Upload } from "lucide-react";
import { toast } from "sonner";
import { errorText, saveBlob, uploadFiles, useApi } from "@/lib/api";

const kb = n => n > 1048576 ? `${(n / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1024))} KB`;
const INLINE = { jpg: "image/jpeg", jpeg: "image/jpeg", png: "image/png", gif: "image/gif", webp: "image/webp", pdf: "application/pdf" };
export const ACCEPT = ".jpg,.jpeg,.png,.webp,.gif,.heic,.heif,.pdf,.doc,.docx,.xls,.xlsx,.csv,.txt,.dwg";

function Thumb({ file }) {
  const api = useApi();
  const [src, setSrc] = useState("");
  useEffect(() => {
    let url = "";
    if (INLINE[file.original_filename.split(".").pop().toLowerCase()]?.startsWith("image/")) api("get", `/files/${file.id}/download`, null, { responseType: "blob" }).then(b => { url = URL.createObjectURL(new Blob([b], { type: INLINE[file.original_filename.split(".").pop().toLowerCase()] })); setSrc(url); }).catch(() => {});
    return () => url && URL.revokeObjectURL(url);
  }, [api, file.id, file.original_filename]);
  return src ? <img src={src} alt={file.original_filename} /> : <FileText size={20} />;
}

export function AttachmentList({ files = [], onChange }) {
  const api = useApi();
  const open = async f => {
    const ext = f.original_filename.split(".").pop().toLowerCase();
    const viewable = INLINE[ext];
    const win = viewable ? window.open("", "_blank") : null;
    try {
      const raw = await api("get", `/files/${f.id}/download`, null, { responseType: "blob" });
      const blob = new Blob([raw], { type: viewable || "application/octet-stream" });
      if (win) win.location.href = URL.createObjectURL(blob); else saveBlob(blob, f.original_filename);
    } catch { win?.close(); toast.error("Could not open file"); }
  };
  const remove = async f => {
    try { await api("delete", `/files/${f.id}`); toast.success("Attachment removed"); onChange?.(); }
    catch (e) { toast.error(errorText(e, "Could not remove attachment")); }
  };
  if (!files.length) return <p className="muted-note" data-testid="no-attachments">No photos or documents attached yet.</p>;
  return <div className="attachments" data-testid="attachment-list">{files.map(f => <div className="attachment" key={f.id} data-testid={`attachment-${f.id}`}>
    <button type="button" className="attachment-thumb" onClick={() => open(f)} data-testid={`open-attachment-${f.id}`}><Thumb file={f} /></button>
    <div className="attachment-meta"><b title={f.original_filename}>{f.original_filename}</b><small>{kb(f.size)} · {f.uploaded_by_name || "Team"}</small></div>
    {onChange && <button type="button" className="icon-btn small" onClick={() => remove(f)} aria-label="Remove attachment" data-testid={`delete-attachment-${f.id}`}><Trash2 size={14} /></button>}
  </div>)}</div>;
}

export function Uploader({ target, onDone, testid = "upload" }) {
  const api = useApi();
  const input = useRef(null);
  const [busy, setBusy] = useState(false);
  const pick = async e => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;
    setBusy(true);
    try { await uploadFiles(api, files, target); toast.success(`${files.length} file${files.length > 1 ? "s" : ""} uploaded`); onDone?.(); }
    catch (err) { toast.error(errorText(err, "Upload failed")); }
    finally { setBusy(false); e.target.value = ""; }
  };
  return <><input ref={input} type="file" multiple hidden accept={ACCEPT} onChange={pick} data-testid={`${testid}-input`} />
    <button type="button" className="ghost-btn" disabled={busy} onClick={() => input.current.click()} data-testid={`${testid}-button`}>{busy ? <Upload size={15} /> : <Paperclip size={15} />} {busy ? "Uploading…" : "Attach photos / documents"}</button></>;
}
