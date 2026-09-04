import { useState } from "react";
import { api } from "../api/client";
import { useToast } from "../components/Toast";

export default function AdminLoginView({
  onCancel,
  onForgot,
  onLoggedIn,
}: {
  onCancel: () => void;
  onForgot: () => void;
  onLoggedIn: (password: string, usingDefaultPassword: boolean) => void;
}) {
  const toast = useToast();
  const [password, setPassword] = useState("");

  async function login() {
    const r = await api<{ ok: boolean; usingDefaultPassword?: boolean; error?: string }>("/api/admin/login", {
      method: "POST",
      body: JSON.stringify({ password }),
    });
    if (r.ok) {
      onLoggedIn(password, !!r.usingDefaultPassword);
    } else {
      toast(r.error || "Contraseña incorrecta");
    }
  }

  return (
    <div className="wrap">
      <div className="topbar">
        <div className="brand">
          <img src="/logo-icon.png" alt="ValeExpress" />
          Reloj checador
        </div>
      </div>
      <div className="card body-pad">
        <div className="field-label" style={{ textAlign: "left" }}>
          Acceso de administrador
        </div>
        <input
          type="password"
          placeholder="Contraseña"
          style={{ marginBottom: 10 }}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && login()}
        />
        <div className="row">
          <button className="btn" style={{ flex: 1 }} onClick={login}>
            Entrar
          </button>
          <button className="btn ghost" style={{ flex: 1 }} onClick={onCancel}>
            Volver
          </button>
        </div>
        <button className="back-link" onClick={onForgot}>
          ¿Olvidaste tu contraseña?
        </button>
      </div>
    </div>
  );
}
