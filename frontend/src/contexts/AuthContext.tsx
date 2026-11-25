import React, { createContext, useContext, useEffect, useState } from "react";
import { api, clearStoredTokens, getStoredToken, setStoredTokens } from "../services/api";
import { User } from "../types";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (identifier: string, password: string) => Promise<User>;
  registerPatient: (payload: Record<string, any>) => Promise<any>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const refreshUser = async () => {
    const token = getStoredToken();
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const me = await api.get<User>("/auth/me");
      setUser(me);
    } catch {
      clearStoredTokens();
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshUser();
  }, []);

  const login = async (identifier: string, password: string) => {
    const res = await api.post<{ access_token: string; refresh_token: string; user: User }>("/auth/login", {
      identifier,
      password,
    });
    setStoredTokens(res.access_token, res.refresh_token);
    setUser(res.user);
    return res.user;
  };

  const registerPatient = async (payload: Record<string, any>) => {
    const res = await api.post<any>("/auth/register", payload);
    setStoredTokens(res.access_token, res.refresh_token);
    setUser(res.user);
    return res;
  };

  const logout = async () => {
    try {
      await api.post("/auth/logout", {});
    } catch {
      // ignore if token already expired
    } finally {
      clearStoredTokens();
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, registerPatient, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
};

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
