import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ClerkProvider } from "@clerk/react";
const appearance = { variables: { colorPrimary: "#d97706", colorPrimaryForeground: "#ffffff", colorBackground: "#ffffff", colorForeground: "#0f172a", colorBorder: "#e2e8f0", fontFamily: "Outfit, sans-serif", borderRadius: "4px" } };
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export default function ClerkAuthProvider({ children }) {
  const navigate = useNavigate(); const [config, setConfig] = useState(null); const [unavailable, setUnavailable] = useState(false);
  useEffect(() => { let cancelled = false; const load = async (attempt=0) => { try { const cfg = await (await fetch(`${BACKEND_URL}/api/clerk/config`)).json(); if (cfg.enabled) return cancelled || setConfig(cfg); } catch {} if (cancelled) return; if (attempt >= 20) return setUnavailable(true); setTimeout(() => load(attempt + 1), 1500); }; load(); return () => { cancelled = true; }; }, []);
  if (unavailable) return <p data-testid="auth-unavailable">Sign-in is unavailable right now. Refresh to try again.</p>;
  if (!config) return <div className="auth-loading" data-testid="auth-loading">Preparing secure workspace…</div>;
  return <ClerkProvider publishableKey={config.publishable_key} proxyUrl={config.proxy_url || undefined} appearance={appearance} routerPush={(to) => navigate(to)} routerReplace={(to) => navigate(to, {replace:true})} signInUrl="/sign-in" signUpUrl="/sign-up" signInFallbackRedirectUrl="/" signUpFallbackRedirectUrl="/" afterSignOutUrl="/">{children}</ClerkProvider>;
}