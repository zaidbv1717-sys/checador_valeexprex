import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { useAdminSession } from "../../context/AdminSessionContext";
import { useToast } from "../../components/Toast";

const PRESET_QUESTIONS = [
  "¿Cuál es el nombre de tu primera mascota?",
  "¿En qué ciudad naciste?",
  "¿Cuál es el apellido de soltera de tu madre?",
  "¿Cuál fue el nombre de tu primera escuela?",
  "¿Cuál es tu comida favorita?",
  "¿Cuál es el nombre de tu mejor amigo de la infancia?",
];

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
  const [officialEmail, setOfficialEmail] = useState("");
  const [secQuestions, setSecQuestions] = useState([PRESET_QUESTIONS[0], PRESET_QUESTIONS[1], PRESET_QUESTIONS[2]]);
  const [secAnswers, setSecAnswers] = useState(["", "", ""]);
  const [hasSecQuestions, setHasSecQuestions] = useState(false);

  useEffect(() => {
    api<{ lunchMinutes: string; hasRecoveryCode: boolean; officialEmail?: string }>("/api/admin/config").then((r) => {
      setLunchMinutes(r.lunchMinutes || "90");
      setHasRecoveryCode(!!r.hasRecoveryCode);
      setOfficialEmail(r.officialEmail || "");
    });
    api<{ questions: string[] }>("/api/admin/security-questions").then((r) => {
      if (r.questions && r.questions.length === 3) {
        setSecQuestions(r.questions);
        setHasSecQuestions(true);
      }
    });
  }, []);

  async function saveOfficialEmail() {
    await api("/api/admin/config", { method: "POST", body: JSON.stringify({ officialEmail }) });
    toast("Correo oficial guardado");
  }

  async function saveSecurityQuestions() {
    if (new Set(secQuestions).size !== secQuestions.length) {
      toast("Elige 3 preguntas distintas");
      return;
    }
    if (secAnswers.some((a) => !a.trim())) {
      toast("Responde las 3 preguntas");
      return;
    }
    const r = await api<{ ok: boolean; error?: string }>("/api/admin/security-questions", {
      method: "POST",
      body: JSON.stringify({
        questions: secQuestions.map((question, i) => ({ question, answer: secAnswers[i] })),
      }),
    });
    if (r.ok) {
      setHasSecQuestions(true);
      setSecAnswers(["", "", ""]);
      toast("Preguntas de seguridad guardadas");
    } else {
      toast(r.error || "No se pudieron guardar las preguntas");
    }
  }

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
    const r = await api<{ recoveryCode?: string; emailError?: string | null }>("/api/admin/config", {
      method: "POST",
      body: JSON.stringify({ generateRecovery: true }),
    });
    setFreshRecoveryCode(r.recoveryCode || "");
    setHasRecoveryCode(!!r.recoveryCode);
    if (r.emailError) {
      toast(`Código regenerado, pero no se pudo enviar por correo: ${r.emailError}`);
    } else if (officialEmail) {
      toast("Código regenerado y enviado al correo oficial");
    } else {
      toast("Código de recuperación regenerado");
    }
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
        Correo oficial
      </div>
      <div className="row">
        <input
          type="email"
          placeholder="admin@empresa.com"
          value={officialEmail}
          onChange={(e) => setOfficialEmail(e.target.value)}
        />
        <button className="btn secondary" onClick={saveOfficialEmail}>
          Guardar
        </button>
      </div>
      <div className="note">
        Cada vez que generes un código de recuperación nuevo, se enviará automáticamente a este correo.
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

      <div className="field-label" style={{ textAlign: "left", marginTop: 22 }}>
        Preguntas de seguridad (segundo método de recuperación)
      </div>
      {secQuestions.map((q, i) => (
        <div key={i} style={{ marginBottom: 10 }}>
          <select
            value={q}
            onChange={(e) => setSecQuestions((prev) => prev.map((p, idx) => (idx === i ? e.target.value : p)))}
            style={{ marginBottom: 6, width: "100%" }}
          >
            {PRESET_QUESTIONS.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
          <input
            type="text"
            placeholder="Respuesta"
            value={secAnswers[i]}
            onChange={(e) => setSecAnswers((prev) => prev.map((p, idx) => (idx === i ? e.target.value : p)))}
          />
        </div>
      ))}
      <div className="row">
        <button className="btn ghost" style={{ flex: 1 }} onClick={saveSecurityQuestions}>
          {hasSecQuestions ? "Actualizar preguntas y respuestas" : "Configurar preguntas de seguridad"}
        </button>
      </div>
      <div className="note">
        {hasSecQuestions
          ? "Ya están configuradas. Para cambiarlas, vuelve a escribir las 3 respuestas y guarda."
          : "Alternativa al código de recuperación: si olvidas la contraseña, podrás restablecerla respondiendo estas 3 preguntas en vez del código."}
      </div>
    </>
  );
}
