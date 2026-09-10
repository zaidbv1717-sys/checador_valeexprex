import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { useAdminSession } from "../../context/AdminSessionContext";
import { useToast } from "../../components/Toast";

export default function ConfigTab() {
  const toast = useToast();
  const { setPass, setUsingDefaultPassword } = useAdminSession();
  const [lunchMinutes, setLunchMinutes] = useState("90");
  // El servidor ya no devuelve el codigo guardado, solo si existe: revelarlo a
  // quien ya inicio sesion anula su proposito de restablecer la contrasena.
  // Solo se ve una vez, al generarlo.
  const [hasRecoveryCode, setHasRecoveryCode] = useState(false);
  const [freshRecoveryCode, setFreshRecoveryCode] = useState("");
  const [newPass, setNewPass] = useState("");

  useEffect(() => {
    api<{ lunchMinutes: string; hasRecoveryCode: boolean }>("/api/admin/config").then((r) => {
      setLunchMinutes(r.lunchMinutes || "90");
      setHasRecoveryCode(!!r.hasRecoveryCode);
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
    setUsingDefaultPassword(false);
    toast("Contraseña actualizada");
    setNewPass("");
  }

  async function regenerateRecovery() {
    const r = await api<{ recoveryCode?: string }>("/api/admin/config", {
      method: "POST",
      body: JSON.stringify({ generateRecovery: true }),
    });
    setFreshRecoveryCode(r.recoveryCode || "");
    setHasRecoveryCode(!!r.recoveryCode);
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
          {freshRecoveryCode || (hasRecoveryCode ? "••••-••••" : "—")}
        </div>
      </div>
      <div className="row">
        <button className="btn ghost" style={{ flex: 1 }} onClick={regenerateRecovery}>
          Generar código nuevo
        </button>
      </div>
      <div className="note">
        {freshRecoveryCode
          ? "Anótalo AHORA: por seguridad no se vuelve a mostrar. Si lo pierdes, genera uno nuevo."
          : "Por seguridad el código no se muestra después de generarlo. Si olvidas la contraseña de administrador, este código es lo único que permite restablecerla desde la pantalla de acceso. Si no lo tienes anotado, genera uno nuevo y guárdalo fuera del sistema."}
      </div>
    </>
  );
}
