import { useEffect, useState } from "react";
import { api, downloadCsv } from "../../api/client";
import { useToast } from "../../components/Toast";
import type { Absence, DeviceAlert, EditTarget, Employee, ReportRow } from "../../types";
import { fmtShortDate } from "../../utils/format";

const PERIODS: [string, string][] = [
  ["dia", "Día"],
  ["semana", "Semana"],
  ["mes", "Mes"],
];

export default function RecordsTab() {
  const toast = useToast();
  const [rows, setRows] = useState<ReportRow[]>([]);
  const [deviceAlerts, setDeviceAlerts] = useState<DeviceAlert[]>([]);
  const [absences, setAbsences] = useState<Absence[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [period, setPeriod] = useState("dia");
  const [filterDate, setFilterDate] = useState("");
  const [filterEmp, setFilterEmp] = useState("all");
  const [editTarget, setEditTarget] = useState<EditTarget | null>(null);

  const query = `?period=${period}&date=${filterDate}&emp=${encodeURIComponent(filterEmp)}`;

  async function load() {
    const r = await api<{ rows: ReportRow[] }>("/api/admin/records" + query);
    setRows(r.rows || []);
    const ra = await api<{ alerts: DeviceAlert[] }>("/api/admin/device-alerts");
    setDeviceAlerts(ra.alerts || []);
    const rb = await api<{ absences: Absence[] }>("/api/admin/absences" + query);
    setAbsences(rb.absences || []);
    const r2 = await api<{ employees: Employee[] }>("/api/admin/employees");
    setEmployees(r2.employees || []);
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [period, filterDate, filterEmp]);

  const missing = rows.filter((r) => r.missing).slice(0, 8);
  const unjustified = absences.filter((a) => !a.justified);
  const totalHrs = rows.reduce((s, r) => s + r.hours, 0);
  const totalExtra = rows.reduce((s, r) => s + r.extraHrs, 0);
  const lateCount = rows.filter((r) => r.retardoMin > 0).length;
  const missingCount = rows.filter((r) => r.missing).length;

  async function resolveAlert(id: string) {
    await api("/api/admin/device-alerts/resolve", { method: "POST", body: JSON.stringify({ id }) });
    load();
  }

  function exportCsv() {
    downloadCsv("/api/admin/export.csv" + query, "registros_asistencia.csv");
  }

  function openEdit(r: ReportRow) {
    setEditTarget({
      employeeId: r.employeeId,
      employeeName: r.employeeName,
      dateStr: r.date,
      dateLabel: fmtShortDate(r.date),
      entrada: r.entrada,
      comida_salida: r.comida_salida,
      comida_entrada: r.comida_entrada,
      salida: r.salida,
      note: r.note,
    });
  }

  async function saveEdit(edits: Record<string, string>, note: string) {
    if (!editTarget) return;
    await api("/api/admin/manual-edit", {
      method: "POST",
      body: JSON.stringify({
        employeeId: editTarget.employeeId,
        employeeName: editTarget.employeeName,
        dateStr: editTarget.dateStr,
        edits,
        note,
      }),
    });
    setEditTarget(null);
    toast("Horario actualizado");
    load();
  }

  return (
    <>
      {missing.length > 0 && (
        <div className="alert-banner">
          ⚠ {missing.length} registro(s) con entrada o salida faltante:{" "}
          {missing.map((r) => `${r.employeeName} (${fmtShortDate(r.date)})`).join(", ")}
        </div>
      )}
      {unjustified.length > 0 && (
        <div className="alert-banner" style={{ background: "#FBEAEA", borderColor: "#EFC7C0", color: "#7A2E1E" }}>
          🚫 {unjustified.length} falta(s) sin justificar:{" "}
          {unjustified.map((a) => `${a.employeeName} (${fmtShortDate(a.date)})`).join(", ")}
        </div>
      )}
      {deviceAlerts.length > 0 && (
        <div className="alert-banner" style={{ background: "#FBEAEA", borderColor: "#EFC7C0", color: "#7A2E1E" }}>
          {deviceAlerts.map((a) => (
            <div key={a.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8, padding: "3px 0" }}>
              <span>
                ⚠ Posible dispositivo compartido: <b>{a.emp1_name}</b> y <b>{a.emp2_name}</b> marcaron entrada
                desde el mismo aparato con pocos minutos de diferencia (
                {new Date(a.emp1_time).toLocaleTimeString("es-MX", { hour: "2-digit", minute: "2-digit" })} /{" "}
                {new Date(a.emp2_time).toLocaleTimeString("es-MX", { hour: "2-digit", minute: "2-digit" })}).
              </span>
              <button className="edit-icon" style={{ color: "#7A2E1E", whiteSpace: "nowrap" }} onClick={() => resolveAlert(a.id)}>
                Marcar revisado
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="period-tabs">
        {PERIODS.map(([val, label]) => (
          <button key={val} className={`tab-btn ${period === val ? "active" : ""}`} onClick={() => setPeriod(val)}>
            {label}
          </button>
        ))}
      </div>
      <div className="row">
        <input type="date" value={filterDate} onChange={(e) => setFilterDate(e.target.value)} />
        <select value={filterEmp} onChange={(e) => setFilterEmp(e.target.value)}>
          <option value="all">Todos</option>
          {employees.map((e) => (
            <option key={e.id} value={e.name}>
              {e.name}
            </option>
          ))}
        </select>
      </div>
      <div className="stat-row">
        <div className="stat-box">
          <div className="n">{totalHrs.toFixed(1)}</div>
          <div className="l">Horas</div>
        </div>
        <div className="stat-box ok">
          <div className="n">{totalExtra.toFixed(1)}</div>
          <div className="l">Extra</div>
        </div>
        <div className="stat-box warn">
          <div className="n">{lateCount}</div>
          <div className="l">Retardos</div>
        </div>
        <div className="stat-box bad">
          <div className="n">{missingCount}</div>
          <div className="l">Sin marca</div>
        </div>
      </div>

      {editTarget && <EditPanel target={editTarget} onCancel={() => setEditTarget(null)} onSave={saveEdit} />}

      <div className="row">
        <button className="btn secondary" style={{ flex: 1 }} onClick={exportCsv}>
          Exportar CSV
        </button>
      </div>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Empleado</th>
              <th>Fecha</th>
              <th>Ent.</th>
              <th>S.Comer</th>
              <th>R.Comer</th>
              <th>Sal.</th>
              <th>Hrs</th>
              <th>Estado</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows.length ? (
              rows.map((r, i) => (
                <tr key={i}>
                  <td>{r.employeeName}</td>
                  <td>{fmtShortDate(r.date)}</td>
                  <td>{r.entrada || "—"}</td>
                  <td>{r.comida_salida || "—"}</td>
                  <td>{r.comida_entrada || "—"}</td>
                  <td>{r.salida || "—"}</td>
                  <td>{r.hours.toFixed(2)}</td>
                  <td>
                    {r.missing && <span className="badge-mini bad">Falta</span>}{" "}
                    {r.retardoMin > 0 && <span className="badge-mini warn">+{r.retardoMin}m</span>}{" "}
                    {r.extraHrs > 0 && <span className="badge-mini ok">+{r.extraHrs.toFixed(1)}h</span>}{" "}
                    {r.lunchLateMin > 0 && <span className="badge-mini warn">comida +{r.lunchLateMin}m</span>}
                    {r.note && (
                      <div style={{ fontSize: "10.5px", color: "var(--muted)", marginTop: 2 }}>📝 {r.note}</div>
                    )}
                  </td>
                  <td>
                    <button className="edit-icon" onClick={() => openEdit(r)}>
                      ✎
                    </button>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={9} className="msg-empty">
                  Sin registros en este periodo
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}

function EditPanel({
  target,
  onCancel,
  onSave,
}: {
  target: EditTarget;
  onCancel: () => void;
  onSave: (edits: Record<string, string>, note: string) => void;
}) {
  const [entrada, setEntrada] = useState(target.entrada || "");
  const [comidaSalida, setComidaSalida] = useState(target.comida_salida || "");
  const [comidaEntrada, setComidaEntrada] = useState(target.comida_entrada || "");
  const [salida, setSalida] = useState(target.salida || "");
  const [note, setNote] = useState(target.note || "");

  return (
    <div className="edit-panel">
      <div className="field-label" style={{ textAlign: "left", marginBottom: 8 }}>
        Editar horario · {target.employeeName} — {target.dateLabel}
      </div>
      <div className="row">
        <div style={{ flex: 1 }}>
          <label>Entrada</label>
          <input type="time" value={entrada} onChange={(e) => setEntrada(e.target.value)} />
        </div>
        <div style={{ flex: 1 }}>
          <label>Salida a comer</label>
          <input type="time" value={comidaSalida} onChange={(e) => setComidaSalida(e.target.value)} />
        </div>
      </div>
      <div className="row">
        <div style={{ flex: 1 }}>
          <label>Regreso de comer</label>
          <input type="time" value={comidaEntrada} onChange={(e) => setComidaEntrada(e.target.value)} />
        </div>
        <div style={{ flex: 1 }}>
          <label>Salida</label>
          <input type="time" value={salida} onChange={(e) => setSalida(e.target.value)} />
        </div>
      </div>
      <div className="row">
        <div style={{ flex: 1 }}>
          <label>Nota (opcional)</label>
          <input
            type="text"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Ej. permiso para retirarse temprano"
          />
        </div>
      </div>
      <div className="row">
        <button
          className="btn secondary"
          style={{ flex: 1 }}
          onClick={() =>
            onSave(
              { entrada, comida_salida: comidaSalida, comida_entrada: comidaEntrada, salida },
              note
            )
          }
        >
          Guardar
        </button>
        <button className="btn ghost" style={{ flex: 1 }} onClick={onCancel}>
          Cancelar
        </button>
      </div>
    </div>
  );
}
