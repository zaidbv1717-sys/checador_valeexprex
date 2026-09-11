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
  const [showPassword, setShowPassword] = useState(false);

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
        <div style={{ position: "relative", marginBottom: 10 }}>
          <input
            type={showPassword ? "text" : "password"}
            placeholder="Contraseña"
            style={{ paddingRight: 40 }}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && login()}
          />
          <button
            type="button"
            className="pass-toggle"
            aria-label={showPassword ? "Ocultar contraseña" : "Mostrar contraseña"}
            onClick={() => setShowPassword((v) => !v)}
          >
            {showPassword ? "🙈" : "👁"}
          </button>
        </div>
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
