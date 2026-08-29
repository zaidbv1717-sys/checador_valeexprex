import { useState } from "react";
import { api } from "../api/client";
import { useToast } from "../components/Toast";

export default function AdminRecoverView({ onDone, onCancel }: { onDone: () => void; onCancel: () => void }) {
  const toast = useToast();
  const [code, setCode] = useState("");
  const [newPass, setNewPass] = useState("");

  async function doRecover() {
    const r = await api<{ ok: boolean; error?: string }>("/api/admin/recover", {
      method: "POST",
      body: JSON.stringify({ recoveryCode: code.trim(), newPassword: newPass.trim() }),
    });
    if (r.ok) {
      toast("Contraseña restablecida, ya puedes entrar");
      onDone();
    } else {
      toast(r.error || "No se pudo restablecer");
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
          Recuperar contraseña
        </div>
        <div className="note" style={{ marginTop: -8, marginBottom: 14 }}>
          Pide el código de recuperación a quien tenga acceso a la computadora donde corre el
          sistema (se muestra en la terminal al arrancar, o en Config una vez adentro).
        </div>
        <input
          type="text"
          placeholder="Código de recuperación"
          style={{ marginBottom: 10, textTransform: "uppercase" }}
          value={code}
          onChange={(e) => setCode(e.target.value)}
        />
        <input
          type="password"
          placeholder="Nueva contraseña"
          style={{ marginBottom: 10 }}
          value={newPass}
          onChange={(e) => setNewPass(e.target.value)}
        />
        <div className="row">
          <button className="btn secondary" style={{ flex: 1 }} onClick={doRecover}>
            Restablecer
          </button>
          <button className="btn ghost" style={{ flex: 1 }} onClick={onCancel}>
            Volver
          </button>
        </div>
      </div>
    </div>
  );
}
