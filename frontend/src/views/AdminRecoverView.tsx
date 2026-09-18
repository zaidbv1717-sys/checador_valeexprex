import { useEffect, useState } from "react";
import { api } from "../api/client";
import { useToast } from "../components/Toast";

export default function AdminRecoverView({ onDone, onCancel }: { onDone: () => void; onCancel: () => void }) {
  const toast = useToast();
  const [method, setMethod] = useState<"code" | "questions">("code");

  const [code, setCode] = useState("");
  const [newPass, setNewPass] = useState("");

  const [questions, setQuestions] = useState<string[]>([]);
  const [answers, setAnswers] = useState<string[]>([]);
  const [newPass2, setNewPass2] = useState("");

  useEffect(() => {
    if (method !== "questions" || questions.length) return;
    api<{ questions: string[] }>("/api/admin/security-questions").then((r) => {
      setQuestions(r.questions || []);
      setAnswers((r.questions || []).map(() => ""));
    });
  }, [method]);

  async function resendCode() {
    const r = await api<{ ok: boolean; error?: string }>("/api/admin/recover/resend-code", {
      method: "POST",
    });
    if (r.ok) {
      toast("Código enviado al correo oficial");
    } else {
      toast(r.error || "No se pudo enviar el código");
    }
  }

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

  async function doRecoverSecurity() {
    const r = await api<{ ok: boolean; error?: string }>("/api/admin/recover-security", {
      method: "POST",
      body: JSON.stringify({ answers: answers.map((a) => a.trim()), newPassword: newPass2.trim() }),
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

        <div className="row" style={{ marginBottom: 14 }}>
          <button
            className={method === "code" ? "btn secondary" : "btn ghost"}
            style={{ flex: 1 }}
            onClick={() => setMethod("code")}
          >
            Código
          </button>
          <button
            className={method === "questions" ? "btn secondary" : "btn ghost"}
            style={{ flex: 1 }}
            onClick={() => setMethod("questions")}
          >
            Preguntas de seguridad
          </button>
        </div>

        {method === "code" ? (
          <>
            <div className="note" style={{ marginTop: -8, marginBottom: 14 }}>
              Pide el código de recuperación a quien tenga acceso a la computadora donde corre el
              sistema, revisa el correo oficial (si se configuró uno en Ajustes), o consúltalo en
              Config una vez adentro.
            </div>
            <div className="row" style={{ marginBottom: 14 }}>
              <button className="btn ghost" style={{ flex: 1 }} onClick={resendCode}>
                Enviar código al correo oficial
              </button>
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
          </>
        ) : (
          <>
            {questions.length === 0 ? (
              <div className="note" style={{ marginTop: -8, marginBottom: 14 }}>
                Este sistema no tiene preguntas de seguridad configuradas. Usa el código de
                recuperación en su lugar.
              </div>
            ) : (
              <>
                {questions.map((q, i) => (
                  <div key={i} style={{ marginBottom: 10 }}>
                    <div className="note" style={{ marginTop: 0, marginBottom: 4, textAlign: "left" }}>
                      {q}
                    </div>
                    <input
                      type="text"
                      placeholder="Respuesta"
                      value={answers[i] || ""}
                      onChange={(e) => setAnswers((prev) => prev.map((p, idx) => (idx === i ? e.target.value : p)))}
                    />
                  </div>
                ))}
                <input
                  type="password"
                  placeholder="Nueva contraseña"
                  style={{ marginBottom: 10 }}
                  value={newPass2}
                  onChange={(e) => setNewPass2(e.target.value)}
                />
              </>
            )}
            <div className="row">
              <button
                className="btn secondary"
                style={{ flex: 1 }}
                onClick={doRecoverSecurity}
                disabled={questions.length === 0}
              >
                Restablecer
              </button>
              <button className="btn ghost" style={{ flex: 1 }} onClick={onCancel}>
                Volver
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
