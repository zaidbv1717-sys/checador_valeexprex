import { useEffect, useState } from "react";
import { api } from "../../api/client";
import type { CalendarDay, Employee } from "../../types";

const MONTH_NAMES = [
  "enero", "febrero", "marzo", "abril", "mayo", "junio",
  "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
];
const DOW_LABELS = ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"];

export default function CalendarTab() {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [employeeId, setEmployeeId] = useState("");
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [days, setDays] = useState<CalendarDay[]>([]);

  useEffect(() => {
    api<{ employees: Employee[] }>("/api/admin/employees").then((r) => setEmployees(r.employees || []));
  }, []);

  useEffect(() => {
    if (!employeeId) {
      setDays([]);
      return;
    }
    api<{ days: CalendarDay[] }>(`/api/admin/calendar?employeeId=${encodeURIComponent(employeeId)}&year=${year}&month=${month}`).then(
      (r) => setDays(r.days || [])
    );
  }, [employeeId, year, month]);

  function prevMonth() {
    if (month === 1) {
      setMonth(12);
      setYear((y) => y - 1);
    } else {
      setMonth((m) => m - 1);
    }
  }

  function nextMonth() {
    if (month === 12) {
      setMonth(1);
      setYear((y) => y + 1);
    } else {
      setMonth((m) => m + 1);
    }
  }

  let grid;
  if (employeeId && days.length) {
    const firstWeekday = days[0].weekday === 6 ? 0 : days[0].weekday + 1;
    grid = (
      <>
        <div className="cal-header">
          <button className="cal-nav" onClick={prevMonth}>
            ‹
          </button>
          <span className="label">
            {MONTH_NAMES[month - 1]} {year}
          </span>
          <button className="cal-nav" onClick={nextMonth}>
            ›
          </button>
        </div>
        <div className="cal-grid">
          {DOW_LABELS.map((l) => (
            <div className="cal-dow" key={l}>
              {l}
            </div>
          ))}
          {Array.from({ length: firstWeekday }).map((_, i) => (
            <div className="cal-day empty" key={"b" + i} />
          ))}
          {days.map((d) => (
            <div className={`cal-day ${d.status}`} title={d.date} key={d.date}>
              {d.day}
            </div>
          ))}
        </div>
        <div className="cal-legend">
          <div className="cal-legend-item">
            <span className="cal-legend-dot" style={{ background: "var(--accent)" }} />
            Asistió
          </div>
          <div className="cal-legend-item">
            <span className="cal-legend-dot" style={{ background: "var(--danger)" }} />
            Falta
          </div>
          <div className="cal-legend-item">
            <span className="cal-legend-dot" style={{ background: "var(--warn)" }} />
            Permiso justificado
          </div>
          <div className="cal-legend-item">
            <span className="cal-legend-dot" style={{ background: "#E5E7EB" }} />
            No laboral
          </div>
        </div>
      </>
    );
  } else {
    grid = <div className="msg-empty">Elige un empleado para ver su calendario</div>;
  }

  return (
    <>
      <div className="field-label" style={{ textAlign: "left" }}>
        Selecciona un empleado
      </div>
      <div className="row">
        <select value={employeeId} onChange={(e) => setEmployeeId(e.target.value)}>
          <option value="">Elige empleado…</option>
          {employees.map((e) => (
            <option key={e.id} value={e.id}>
              {e.name}
            </option>
          ))}
        </select>
      </div>
      {grid}
    </>
  );
}
