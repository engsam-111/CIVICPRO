import { createContext, useContext, useEffect, useState } from "react";
import { WifiOff } from "lucide-react";
import { toast } from "sonner";

const PwaContext = createContext(null);
export const usePwa = () => useContext(PwaContext);
const standalone = () => window.matchMedia("(display-mode: standalone)").matches || window.navigator.standalone === true;

export const PwaProvider = ({ children }) => {
  const [prompt, setPrompt] = useState(null);
  const [installed, setInstalled] = useState(standalone);
  const [online, setOnline] = useState(navigator.onLine);
  const [installing, setInstalling] = useState(false);
  useEffect(() => {
    const media = window.matchMedia("(display-mode: standalone)");
    const ready = event => { event.preventDefault(); setPrompt(event); };
    const complete = () => { setInstalled(true); setPrompt(null); };
    const mode = () => setInstalled(standalone());
    const connection = () => setOnline(navigator.onLine);
    window.addEventListener("beforeinstallprompt", ready);
    window.addEventListener("appinstalled", complete);
    window.addEventListener("online", connection);
    window.addEventListener("offline", connection);
    media.addEventListener("change", mode);
    return () => {
      window.removeEventListener("beforeinstallprompt", ready);
      window.removeEventListener("appinstalled", complete);
      window.removeEventListener("online", connection);
      window.removeEventListener("offline", connection);
      media.removeEventListener("change", mode);
    };
  }, []);
  const install = async () => {
    if (!prompt || installing) return;
    setInstalling(true);
    try { await prompt.prompt(); await prompt.userChoice; }
    catch { toast.error("Open your browser menu to install CIVICPRO."); }
    finally { setPrompt(null); setInstalling(false); }
  };
  return <PwaContext.Provider value={{ installed, canInstall: !!prompt, install, installing, online }}>
    {!online && <div className="connection-banner" role="status" data-testid="offline-banner"><WifiOff size={17} /><span>You're offline. Reconnect to load or save updates.</span></div>}
    {children}
  </PwaContext.Provider>;
};