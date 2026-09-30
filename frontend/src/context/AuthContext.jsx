import { createContext, useContext, useEffect, useState, useCallback } from "react";
import client from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const raw = localStorage.getItem("is_reco_user");
    return raw ? JSON.parse(raw) : null;
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("is_reco_token");
    if (!token) {
      setLoading(false);
      return;
    }
    client
      .get("/api/auth/me")
      .then((res) => {
        setUser(res.data);
        localStorage.setItem("is_reco_user", JSON.stringify(res.data));
      })
      .catch(() => {
        localStorage.removeItem("is_reco_token");
        localStorage.removeItem("is_reco_user");
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email, password) => {
    const res = await client.post("/api/auth/login", { email, password });
    localStorage.setItem("is_reco_token", res.data.access_token);
    localStorage.setItem("is_reco_user", JSON.stringify(res.data.user));
    setUser(res.data.user);
    return res.data.user;
  }, []);

  const register = useCallback(async (payload) => {
    const res = await client.post("/api/auth/register", payload);
    localStorage.setItem("is_reco_token", res.data.access_token);
    localStorage.setItem("is_reco_user", JSON.stringify(res.data.user));
    setUser(res.data.user);
    return res.data.user;
  }, []);

  const logout = useCallback(async () => {
    try {
      await client.post("/api/auth/logout");
    } catch {
      // best-effort — even if the network call fails, clear the local session
    }
    localStorage.removeItem("is_reco_token");
    localStorage.removeItem("is_reco_user");
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
