import { Download, FileText, X } from "lucide-react";
import { ACCEPT } from "./Attachments";
import { saveBlob } from "@/lib/api";

const sizeLabel = size => size >= 1048576 ? `${(size / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.ceil(size / 1024))} KB`;
const fileKey = file => `${file.name}:${file.size}:${file.lastModified}`;

export const ProjectFilePicker = ({ files, onChange, disabled }) => {
  const pick = event => {
    const selected = Array.from(event.target.files || []);
    const combined = [...files];
    selected.forEach(file => { if (!combined.some(existing => fileKey(existing) === fileKey(file))) combined.push(file); });
    onChange(combined);
    event.target.value = "";
  };
  return <section className="project-file-picker full" data-testid="project-file-picker">
    <label className="field"><span>Project files (optional)</span><input type="file" multiple accept={ACCEPT} disabled={disabled} onChange={pick} data-testid="project-files-input" /></label>
    <p className="muted-note" data-testid="project-file-limit">Photos, PDF, Word, Excel, CSV, TXT or DWG · up to 20 MB per file</p>
    {files.length > 0 && <><p className="picked-file-count" data-testid="project-selected-file-count">{files.length} file{files.length === 1 ? "" : "s"} selected</p>
      <div className="picked-file-list">{files.map((file, index) => <div className="picked-file" key={fileKey(file)} data-testid={`project-selected-file-${index}`}>
        <FileText size={20} /><div className="attachment-meta"><b title={file.name}>{file.name}</b><small>{sizeLabel(file.size)}</small></div>
        <button type="button" className="icon-btn small" onClick={() => saveBlob(file, file.name)} aria-label={`Download ${file.name}`} title="Download selected file" data-testid={`download-selected-file-${index}`}><Download size={16} /></button>
        <button type="button" className="icon-btn small" disabled={disabled} onClick={() => onChange(files.filter((_, i) => i !== index))} aria-label={`Remove ${file.name}`} title="Remove selected file" data-testid={`remove-selected-file-${index}`}><X size={16} /></button>
      </div>)}</div></>}
  </section>;
};

export const ProjectUploadNotice = ({ failures, dismiss }) => !failures?.length ? null : <section className="project-upload-notice" role="alert" data-testid="project-upload-warning">
  <div><b>Project saved. {failures.length} file{failures.length === 1 ? " wasn't" : "s weren't"} uploaded.</b><p>Attach these files again when you're ready.</p>
    <ul>{failures.map((file, index) => <li key={index} data-testid={`failed-project-file-${index}`}><strong>{file.name}</strong> — {file.reason}</li>)}</ul></div>
  <button type="button" className="icon-btn small" aria-label="Dismiss upload warning" title="Dismiss" onClick={dismiss} data-testid="dismiss-project-upload-warning"><X size={16} /></button>
</section>;