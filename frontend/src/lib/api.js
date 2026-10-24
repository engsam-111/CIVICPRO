import axios from "axios";
import { useAuth } from "@clerk/react";
import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

export const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export function useApi() {
  const { getToken } = useAuth();
  const ref = useRef(getToken);
  ref.current = getToken;
  return useCallback(async (method, url, data, extra = {}) => {
    const token = await ref.current();
    const res = await axios({ method, url: `${API}${url}`, data, headers: { Authorization: `Bearer ${token}` }, ...extra });
    return res.data;
  }, []);
}

export function useResource(url) {
  const api = useApi();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const reload = useCallback(() => api("get", url).then(setData).catch(e => { setError(e); toast.error(errorText(e, "Could not load data")); }), [api, url]);
  useEffect(() => { reload(); }, [reload]);
  return [data, reload, error];
}

export const errorText = (e, fallback) => {
  const d = e?.response?.data?.detail;
  return typeof d === "string" ? d : Array.isArray(d) ? `${d[0]?.loc?.slice(-1)[0] || "Field"}: ${d[0]?.msg}` : fallback;
};

export const saveBlob = (blob, name) => {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 5000);
};

export async function uploadFiles(api, files, { project_id, entity_type, entity_id }) {
  for (const file of files) {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("project_id", project_id);
    fd.append("entity_type", entity_type);
    fd.append("entity_id", entity_id || project_id);
    await api("post", "/files", fd);
  }
}

const MeContext = createContext(null);
export const useMe = () => useContext(MeContext);
export function MeProvider({ children }) {
  const [me] = useResource("/me");
  return <MeContext.Provider value={me}>{children}</MeContext.Provider>;
}
