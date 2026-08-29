import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { useAdminSession } from "../../context/AdminSessionContext";
import { useToast } from "../../components/Toast";

export default function ConfigTab() {
  const toast = useToast();
  const { setPass } = useAdminSession();
  const [lunchMinutes, setLunchMinutes] = useState("90");
  const [recoveryCode, setRecoveryCode] = useState("");
  const [newPass, setNewPass] = useState("");

  useEffect(() => {
    api<{ lunchMinutes: string; recoveryCode: string }>("/api/admin/config").then((r) => {
      setLunchMinutes(r.lunchMinutes || "90");
      setRecoveryCode(r.recoveryCode || "");
    });
  }, []);

  async function saveLunch() {
    await api("/api/admin/config", { method: "POST", body: JSON.stringify({ lunchMinutes }) });
    toast("Guardado");
  }

  async function savePassword() {
    if (newPass.length < 4) {
      toast("Usa al menos 4 caracteres");
      return;
    }
    await api("/api/admin/config", { method: "POST", body: JSON.stringify({ password: newPass }) });
    setPass(newPass);
    toast("Contraseña actualizada");
    setNewPass("");
  }

  async function regenerateRecovery() {
    const r = await api<{ recoveryCode?: string }>("/api/admin/config", {
      method: "POST",
      body: JSON.stringify({ generateRecovery: true }),
    });
    setRecoveryCode(r.recoveryCode || "");
    toast("Código de recuperación regenerado");
  }

  return (
    <>
      <div className="field-label" style={{ textAlign: "left" }}>
        Minutos permitidos para comer
      </div>
      <div className="row">
        <input type="number" min={0} value={lunchMinutes} onChange={(e) => setLunchMinutes(e.target.value)} />
        <button className="btn secondary" onClick={saveLunch}>
          Guardar
        </button>
      </div>
      <div className="note">
        Si alguien tarda más de este tiempo entre "salida a comer" y "regreso de comer", se marcará en el reporte.
      </div>

      <div className="field-label" style={{ textAlign: "left", marginTop: 22 }}>
        Cambiar contraseña de administrador
      </div>
      <div className="row">
        <input type="password" placeholder="Nueva contraseña" value={newPass} onChange={(e) => setNewPass(e.target.value)} />
        <button className="btn" onClick={savePassword}>
          Guardar
        </button>
      </div>

      <div className="field-label" style={{ textAlign: "left", marginTop: 22 }}>
        Código de recuperación
      </div>
      <div className="summary-card" style={{ textAlign: "center" }}>
        <div className="summary-total" style={{ letterSpacing: "0.08em", fontSize: 19 }}>
          {recoveryCode || "—"}
        </div>
      </div>
      <div className="row">
        <button className="btn ghost" style={{ flex: 1 }} onClick={regenerateRecovery}>
          Generar código nuevo
        </button>
      </div>
      <div className="note">
        Guárdalo en un lugar seguro fuera del sistema (una nota, tu teléfono). Si olvidas la contraseña de
        administrador, este código es lo único que permite restablecerla desde la pantalla de acceso.
      </div>
    </>
  );
}
