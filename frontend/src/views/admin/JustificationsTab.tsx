import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { useToast } from "../../components/Toast";
import type { Employee, Justification } from "../../types";
import { fmtShortDate } from "../../utils/format";

const TYPE_LABELS: Record<string, string> = {
  medica: "Médica / fuerza mayor",
  personal: "Personal",
  permiso_economico: "Permiso económico",
  vacaciones: "Vacaciones",
};
const STATUS_LABELS: Record<string, string> = { pendiente: "Pendiente", aprobada: "Aprobada", rechazada: "Rechazada" };
const STATUS_CLASS: Record<string, string> = { pendiente: "warn", aprobada: "ok", rechazada: "bad" };

export default function JustificationsTab() {
  const toast = useToast();
  const [justifications, setJustifications] = useState<Justification[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [empId, setEmpId] = useState("");
  const [dateStart, setDateStart] = useState("");
  const [dateEnd, setDateEnd] = useState("");
  const [type, setType] = useState("vacaciones");
  const [status, setStatus] = useState("aprobada");
  const [note, setNote] = useState("");

  async function load() {
    const r = await api<{ justifications: Justification[] }>("/api/admin/justifications");
    setJustifications(r.justifications || []);
    const r2 = await api<{ employees: Employee[] }>("/api/admin/employees");
    setEmployees(r2.employees || []);
  }

  useEffect(() => {
    load();
  }, []);

  async function addJustification() {
    if (!empId || !dateStart) {
      toast("Selecciona empleado y fecha de inicio");
      return;
    }
    const empName = employees.find((e) => e.id === empId)?.name || "";
    const r = await api<{ ok: boolean; error?: string }>("/api/admin/justifications", {
      method: "POST",
      body: JSON.stringify({
        employeeId: empId,
        employeeName: empName,
        dateStart,
        dateEnd: dateEnd || dateStart,
        type,
        status,
        note,
      }),
    });
    if (r.ok) {
      toast("Permiso guardado");
      setNote("");
      load();
    } else {
      toast(r.error || "Error");
    }
  }

  async function setJustStatus(id: string, newStatus: string) {
    await api("/api/admin/justifications/status", { method: "POST", body: JSON.stringify({ id, status: newStatus }) });
    load();
  }

  async function deleteJust(id: string) {
    if (!window.confirm("¿Eliminar este permiso? Esta acción no se puede deshacer.")) return;
    await api("/api/admin/justifications/" + id, { method: "DELETE" });
    load();
  }

  return (
    <>
      <div className="field-label" style={{ textAlign: "left" }}>
        Registrar permiso, incapacidad o vacaciones
      </div>
      <div className="row">
        <select value={empId} onChange={(e) => setEmpId(e.target.value)}>
          <option value="">Selecciona empleado…</option>
          {employees.map((e) => (
            <option key={e.id} value={e.id}>
              {e.name}
            </option>
          ))}
        </select>
      </div>
      <div className="row">
        <div style={{ flex: 1 }}>
          <label style={{ fontSize: 11, color: "var(--muted)" }}>Desde</label>
          <input type="date" value={dateStart} onChange={(e) => setDateStart(e.target.value)} />
        </div>
        <div style={{ flex: 1 }}>
          <label style={{ fontSize: 11, color: "var(--muted)" }}>Hasta</label>
          <input type="date" value={dateEnd} onChange={(e) => setDateEnd(e.target.value)} />
        </div>
      </div>
      <div className="row">
        <select value={type} onChange={(e) => setType(e.target.value)}>
          <option value="vacaciones">Vacaciones</option>
          <option value="medica">Médica / fuerza mayor</option>
          <option value="personal">Personal</option>
          <option value="permiso_economico">Permiso económico</option>
        </select>
        <select value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="aprobada">Aprobada</option>
          <option value="pendiente">Pendiente</option>
          <option value="rechazada">Rechazada</option>
        </select>
      </div>
      <div className="row">
        <input type="text" placeholder="Nota (opcional)" value={note} onChange={(e) => setNote(e.target.value)} />
      </div>
      <div className="row">
        <button className="btn" style={{ flex: 1 }} onClick={addJustification}>
          Guardar
        </button>
      </div>
      <div className="note">
        Esto reemplaza la bitácora de WhatsApp: cuando apruebes un permiso aquí, los días dentro del rango dejan de
        contar como falta sin justificar en Registros.
      </div>

      <div style={{ marginTop: 18 }}>
        {justifications.length ? (
          justifications.map((j) => (
            <div className="emp-item" style={{ alignItems: "flex-start" }} key={j.id}>
              <span style={{ flex: 1 }}>
                <b>{j.employee_name}</b>
                <br />
                <span style={{ fontSize: 11, color: "var(--muted)" }}>
                  {fmtShortDate(j.date_start)}
                  {j.date_end !== j.date_start ? " al " + fmtShortDate(j.date_end) : ""} — {TYPE_LABELS[j.type] || j.type}
                  {j.note ? " · " + j.note : ""}
                </span>
              </span>
              <span style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 6 }}>
                <span className={`badge-mini ${STATUS_CLASS[j.status]}`}>{STATUS_LABELS[j.status] || j.status}</span>
                <span style={{ display: "flex", gap: 6 }}>
                  {j.status !== "aprobada" && (
                    <button className="small-btn" style={{ color: "var(--accent)" }} onClick={() => setJustStatus(j.id, "aprobada")}>
                      Aprobar
                    </button>
                  )}
                  {j.status !== "rechazada" && (
                    <button className="small-btn" onClick={() => setJustStatus(j.id, "rechazada")}>
                      Rechazar
                    </button>
                  )}
                  <button className="small-btn" onClick={() => deleteJust(j.id)}>
                    Eliminar
                  </button>
                </span>
              </span>
            </div>
          ))
        ) : (
          <div className="msg-empty">Aún no hay permisos registrados</div>
        )}
      </div>
    </>
  );
}
