import { useState } from "react";
import { Check, Download, Share, Smartphone } from "lucide-react";
import { Modal } from "@/components/civic/ui";
import { usePwa } from "./PwaProvider";

export const InstallPanel = () => {
  const { installed, canInstall, install, installing } = usePwa();
  const ios = /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  return <section className="install-panel" data-testid="install-panel">
    <div className="install-identity"><img src="/icons/icon-192.png" alt="CIVICPRO app icon" width="56" height="56" /><div><h2>CIVICPRO</h2><p>Field command. On your home screen.</p></div></div>
    {installed ? <p className="installed-state" data-testid="app-installed-status"><Check size={18} /> App installed</p> : <>
      {canInstall ? <button type="button" className="primary-btn" onClick={install} disabled={installing} data-testid="install-app-button"><Download size={18} />{installing ? "Opening installation…" : "Install CIVICPRO"}</button>
        : <div className="install-steps" data-testid="install-instructions"><h3>{ios ? "Add to your iPhone or iPad" : "Add to your home screen"}</h3>
          <ol>{ios ? <><li>Open CIVICPRO in Safari.</li><li>Tap <Share size={15} /> <b>Share</b>, then <b>Add to Home Screen</b>.</li><li>Keep <b>Open as Web App</b> on, then tap <b>Add</b>.</li></> : <><li>Open CIVICPRO in Chrome or your device's browser.</li><li>Open the browser menu and choose <b>Install app</b> or <b>Add to Home Screen</b>, if available.</li><li>Confirm to add CIVICPRO.</li></>}</ol>
          <p>On iPhone, use Safari → Share → Add to Home Screen. If this page is inside a preview, open it in a browser tab first.</p></div>}
      <p className="install-note" data-testid="install-online-note">An internet connection is required for project data, uploads, and AI. Private records aren't saved for offline use.</p>
    </>}
  </section>;
};

export const InstallControl = ({ testid = "open-install-button", compact = false }) => {
  const [open, setOpen] = useState(false);
  const { installed } = usePwa();
  if (installed) return null;
  return <><button className={compact ? "icon-btn install-control" : "ghost-btn install-control"} type="button" onClick={() => setOpen(true)} aria-label="Install CIVICPRO" title="Install CIVICPRO" data-testid={testid}><Smartphone size={19} />{!compact && "Install app"}</button>
    {open && <Modal title="CIVICPRO on your phone" close={() => setOpen(false)}><InstallPanel /></Modal>}</>;
};