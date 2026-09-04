import { useEffect, useState } from "react";
import { api } from "../api/client";
import CameraCapture from "../components/CameraCapture";
import PixelWorld from "../components/PixelWorld";
import { useToast } from "../components/Toast";
import type { ActiveEmployee } from "../types";
import { fmtDate, fmtTime, STAGES, TYPE_LABEL } from "../utils/format";

export default function PunchClockView({ onGoAdmin }: { onGoAdmin: () => void }) {
  const toast = useToast();
  const [now, setNow] = useState(new Date());
  const [pin, setPin] = useState("");
  const [activeEmployee, setActiveEmployee] = useState<ActiveEmployee | null>(null);
  const [todayDone, setTodayDone] = useState<Record<string, string>>({});
  const [pendingType, setPendingType] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const id = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(id);
  }, []);

  async function refreshToday(emp: ActiveEmployee) {
    const r = await api<{ done?: Record<string, string> }>("/api/today?employeeId=" + encodeURIComponent(emp.id));
    setTodayDone(r.done || {});
  }

  function addDigit(d: string) {
    if (pin.length >= 4) return;
    const next = pin + d;
    setPin(next);
    if (next.length === 4) {
      window.setTimeout(async () => {
        const r = await api<{ ok: boolean; employee?: ActiveEmployee }>("/api/verify-pin", {
          method: "POST",
          body: JSON.stringify({ pin: next }),
        });
        setPin("");
        if (r.ok && r.employee) {
          setActiveEmployee(r.employee);
          await refreshToday(r.employee);
        } else {
          toast("PIN no encontrado");
        }
      }, 150);
    }
  }

  function backspace() {
    setPin((p) => p.slice(0, -1));
  }

  function requestPunch(type: string) {
    setPendingType(type);
  }

  async function onPhotoCaptured(file: File) {
    const type = pendingType;
    setPendingType(null);
    const emp = activeEmployee;
    if (!emp || !type) return;

    setSubmitting(true);
    const form = new FormData();
    form.append("employeeId", emp.id);
    form.append("employeeName", emp.name);
    form.append("type", type);
    form.append("photo", file);
    const r = await api<{ ok: boolean; time?: string; error?: string }>("/api/punch", {
      method: "POST",
      body: form,
    });
    setSubmitting(false);
    if (r.ok) {
      toast(TYPE_LABEL[type] + " registrada — " + r.time);
    } else {
      toast(r.error || "No se pudo registrar");
    }
    setActiveEmployee(null);
    setTodayDone({});
  }

  function cancelCapture() {
    setPendingType(null);
  }

  let body;
  if (!activeEmployee) {
    body = (
      <>
        <div className="field-label">Ingresa tu PIN</div>
        <div className="pin-dots">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className={`pin-dot ${i < pin.length ? "filled" : ""}`} />
          ))}
        </div>
        <div className="keypad">
          {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((n) => (
            <button key={n} onClick={() => addDigit(String(n))}>
              {n}
            </button>
          ))}
          <button className="wide" onClick={() => setPin("")}>
            Borrar
          </button>
          <button onClick={() => addDigit("0")}>0</button>
          <button className="wide" onClick={backspace}>
            ←
          </button>
        </div>
      </>
    );
  } else {
    const emp = activeEmployee;
    const nextStage = STAGES.find((s) => !todayDone[s]);
    const doneCount = STAGES.filter((s) => todayDone[s]).length;
    const stageDots = (
      <div className="pin-dots" style={{ marginTop: nextStage ? 6 : 16, marginBottom: nextStage ? 22 : undefined }}>
        {STAGES.map((s) => (
          <div key={s} className={`pin-dot ${todayDone[s] ? "filled" : ""}`} />
        ))}
      </div>
    );

    if (!nextStage) {
      body = (
        <>
          <div className="greet">
            <div className="name">Hola, {emp.name.split(" ")[0]}</div>
            <div className="sub">Ya completaste tu registro de hoy</div>
          </div>
          {stageDots}
          <div className="stub-list">
            {STAGES.map((s) => (
              <div className="stub" key={s}>
                <span>{TYPE_LABEL[s]}</span>
                <span>
                  {new Date(todayDone[s]).toLocaleTimeString("es-MX", { hour: "2-digit", minute: "2-digit" })}
                </span>
              </div>
            ))}
          </div>
          <button className="back-link" onClick={() => { setActiveEmployee(null); setTodayDone({}); }}>
            Cambiar de empleado
          </button>
        </>
      );
    } else {
      body = (
        <>
          <div className="greet">
            <div className="name">Hola, {emp.name.split(" ")[0]}</div>
            <div className="sub">Paso {doneCount + 1} de 4</div>
          </div>
          {stageDots}
          <button className="stage-btn" disabled={submitting} onClick={() => requestPunch(nextStage)}>
            {submitting ? "Enviando…" : `Marcar ${TYPE_LABEL[nextStage]}`}
          </button>
          <button className="back-link" onClick={() => { setActiveEmployee(null); setTodayDone({}); }}>
            Cambiar de empleado
          </button>
        </>
      );
    }
  }

  return (
    <div className="wrap">
      <div className="topbar">
        <div className="brand">
          <img src="/logo-icon.png" alt="ValeExpress" />
          Reloj checador
        </div>
        <button className="admin-link" onClick={onGoAdmin}>
          Admin
        </button>
      </div>
      <div className="card">
        <div className="clockpanel">
          <PixelWorld />
          <div className="date">{fmtDate(now)}</div>
          <div className="time">{fmtTime(now)}</div>
        </div>
        <div className="body-pad">{body}</div>
      </div>
      {pendingType && <CameraCapture onCapture={onPhotoCaptured} onCancel={cancelCapture} />}
    </div>
  );
}
