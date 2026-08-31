import { useEffect, useRef, useState } from "react";
import { api } from "../../api/client";
import EmployeePhoto from "../../components/EmployeePhoto";
import { useToast } from "../../components/Toast";
import type { Category, Employee } from "../../types";
import { CATEGORY_LABEL } from "../../utils/format";

export default function EmployeesTab() {
  const toast = useToast();
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [name, setName] = useState("");
  const [pin, setPin] = useState("");
  const [category, setCategory] = useState("trabajador");
  const [schedIn, setSchedIn] = useState("");
  const [schedOut, setSchedOut] = useState("");
  const [lunchMin, setLunchMin] = useState("");
  const [photo, setPhoto] = useState<File | null>(null);
  const photoInputRef = useRef<HTMLInputElement>(null);

  async function load() {
    const r = await api<{ employees: Employee[] }>("/api/admin/employees");
    setEmployees(r.employees || []);
    const rc = await api<{ categories: Category[] }>("/api/admin/employee-categories");
    setCategories(rc.categories || []);
  }

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    const cat = categories.find((c) => c.value === category);
    if (cat) {
      setSchedIn(cat.schedIn);
      setSchedOut(cat.schedOut);
      setLunchMin(String(cat.lunchMinutes));
    }
  }, [category, categories]);

  async function addEmployee() {
    if (!photo) {
      toast("Se requiere una foto del empleado");
      return;
    }
    const form = new FormData();
    form.append("name", name.trim());
    form.append("pin", pin.trim());
    form.append("category", category);
    form.append("schedIn", schedIn);
    form.append("schedOut", schedOut);
    form.append("lunchMinutes", lunchMin);
    form.append("photo", photo);
    const r = await api<{ ok: boolean; error?: string }>("/api/admin/employees", {
      method: "POST",
      body: form,
    });
    if (r.ok) {
      setName("");
      setPin("");
      setPhoto(null);
      if (photoInputRef.current) photoInputRef.current.value = "";
      load();
    } else {
      toast(r.error || "Error");
    }
  }

  async function deleteEmployee(id: string) {
    await api("/api/admin/employees/" + id, { method: "DELETE" });
    load();
  }

  return (
    <>
      <div className="row">
        <input type="text" placeholder="Nombre del empleado" value={name} onChange={(e) => setName(e.target.value)} />
      </div>
      <div className="row">
        <input
          type="text"
          placeholder="PIN de 4 dígitos"
          maxLength={4}
          value={pin}
          onChange={(e) => setPin(e.target.value)}
        />
      </div>
      <div className="row">
        <select value={category} onChange={(e) => setCategory(e.target.value)}>
          {categories.map((c) => (
            <option key={c.value} value={c.value}>
              {c.label}
            </option>
          ))}
        </select>
      </div>
      <div className="row">
        <div style={{ flex: 1 }}>
          <label style={{ fontSize: 11, color: "var(--muted)" }}>Entrada esperada</label>
          <input type="time" value={schedIn} onChange={(e) => setSchedIn(e.target.value)} />
        </div>
        <div style={{ flex: 1 }}>
          <label style={{ fontSize: 11, color: "var(--muted)" }}>Salida esperada</label>
          <input type="time" value={schedOut} onChange={(e) => setSchedOut(e.target.value)} />
        </div>
      </div>
      <div className="row">
        <div style={{ flex: 1 }}>
          <label style={{ fontSize: 11, color: "var(--muted)" }}>Minutos para comer</label>
          <input type="number" min={0} value={lunchMin} onChange={(e) => setLunchMin(e.target.value)} />
        </div>
      </div>
      <div className="row">
        <div style={{ flex: 1 }}>
          <label style={{ fontSize: 11, color: "var(--muted)" }}>Foto del empleado (obligatoria)</label>
          <input
            ref={photoInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={(e) => setPhoto(e.target.files?.[0] || null)}
          />
        </div>
      </div>
      <div className="note" style={{ marginTop: -4 }}>
        Los horarios y minutos de comida se llenan solos según la categoría — puedes ajustarlos si este empleado es
        distinto. La foto se guarda para identificarlo en un futuro checador biométrico.
      </div>
      <div className="row" style={{ marginTop: 10 }}>
        <button className="btn" style={{ flex: 1 }} onClick={addEmployee}>
          Agregar empleado
        </button>
      </div>
      <div style={{ marginTop: 6 }}>
        {employees.length ? (
          employees.map((e) => (
            <div className="emp-item" key={e.id}>
              <span style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <EmployeePhoto url={e.photoUrl} alt={e.name} />
                <span>
                  {e.name}
                  <span className={`cat-badge ${e.category || "trabajador"}`}>
                    {CATEGORY_LABEL[e.category] || "Trabajador"}
                  </span>
                  <br />
                  <span className="pin">
                    {e.sched_in}–{e.sched_out} · comida {e.lunch_minutes || 90} min
                  </span>
                </span>
              </span>
              <span style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <span className="pin">PIN {e.pin}</span>
                <button className="small-btn" onClick={() => deleteEmployee(e.id)}>
                  Eliminar
                </button>
              </span>
            </div>
          ))
        ) : (
          <div className="msg-empty">Aún no hay empleados</div>
        )}
      </div>
    </>
  );
}
