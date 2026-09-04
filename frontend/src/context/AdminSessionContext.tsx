import { createContext, useContext, useState, type ReactNode } from "react";
import { setAdminPass } from "../api/client";

interface AdminSessionValue {
  adminPass: string;
  setPass: (pass: string) => void;
  usingDefaultPassword: boolean;
  setUsingDefaultPassword: (v: boolean) => void;
}

const AdminSessionContext = createContext<AdminSessionValue | null>(null);

export function AdminSessionProvider({ children }: { children: ReactNode }) {
  const [adminPass, setAdminPassState] = useState("");
  const [usingDefaultPassword, setUsingDefaultPassword] = useState(false);

  const setPass = (pass: string) => {
    setAdminPassState(pass);
    setAdminPass(pass);
  };

  return (
    <AdminSessionContext.Provider value={{ adminPass, setPass, usingDefaultPassword, setUsingDefaultPassword }}>
      {children}
    </AdminSessionContext.Provider>
  );
}

export function useAdminSession() {
  const ctx = useContext(AdminSessionContext);
  if (!ctx) throw new Error("useAdminSession must be used within AdminSessionProvider");
  return ctx;
}
