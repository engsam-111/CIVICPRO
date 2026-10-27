export const registerPwa = () => {
  if (!("serviceWorker" in navigator) || !window.isSecureContext) return;
  const register = () => navigator.serviceWorker.register("/sw.js", { scope: "/", updateViaCache: "none" }).catch(() => {
    // Installation may be unavailable in embedded/private browsers; the online app still works.
  });
  // Start immediately: waiting for analytics or external images delays offline readiness.
  register();
};