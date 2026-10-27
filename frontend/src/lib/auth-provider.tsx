"use client";

import { createContext, ReactNode, useCallback, useContext, useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "./api";
import { refreshSession } from "./auth-token";
import { User } from "@/types";

type AuthStatus = "loading" | "authenticated" | "unauthenticated";

interface AuthContextValue {
  user: User | null;
  status: AuthStatus;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [user, setUser] = useState<User | null>(null);
  const [status, setStatus] = useState<AuthStatus>("loading");

  // Restore the session from the refresh cookie on first load
  useEffect(() => {
    refreshSession().then((restored) => {
      setUser(restored);
      setStatus(restored ? "authenticated" : "unauthenticated");
    });
  }, []);

  const signedIn = useCallback(
    (signedInUser: User) => {
      queryClient.clear(); // never show a previous user's cached data
      setUser(signedInUser);
      setStatus("authenticated");
    },
    [queryClient]
  );

  const login = useCallback(
    async (email: string, password: string) => signedIn(await api.login(email, password)),
    [signedIn]
  );

  const register = useCallback(
    async (email: string, password: string) => signedIn(await api.register(email, password)),
    [signedIn]
  );

  const logout = useCallback(async () => {
    try {
      await api.logout();
    } finally {
      queryClient.clear();
      setUser(null);
      setStatus("unauthenticated");
    }
  }, [queryClient]);

  return (
    <AuthContext.Provider value={{ user, status, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
