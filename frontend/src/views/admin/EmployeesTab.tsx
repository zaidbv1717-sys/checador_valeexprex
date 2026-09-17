import { useEffect, useRef, useState } from "react";
import { api } from "../../api/client";
import EmployeePhoto from "../../components/EmployeePhoto";
import PhotoModal from "../../components/PhotoModal";
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
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [photo, setPhoto] = useState<File | null>(null);
  const photoInputRef = useRef<HTMLInputElement>(null);

  const [editing, setEditing] = useState<Employee | null>(null);
  const [editName, setEditName] = useState("");
  const [editPin, setEditPin] = useState("");
  const [editCategory, setEditCategory] = useState("trabajador");
  const [editSchedIn, setEditSchedIn] = useState("");
  const [editSchedOut, setEditSchedOut] = useState("");
  const [editLunchMin, setEditLunchMin] = useState("");
  const [editPhone, setEditPhone] = useState("");
  const [editEmail, setEditEmail] = useState("");
  const [editEmergencyContact, setEditEmergencyContact] = useState("");
  const [editMedicalHistory, setEditMedicalHistory] = useState("");
  const [editPhoto, setEditPhoto] = useState<File | null>(null);
  const [editPhotoPreview, setEditPhotoPreview] = useState<string | null>(null);
  const [editPhotoRemoved, setEditPhotoRemoved] = useState(false);
  const [enlargedPhoto, setEnlargedPhoto] = useState<string | null>(null);
  const editPhotoInputRef = useRef<HTMLInputElement>(null);

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

  useEffect(() => {
    if (!editPhoto) {
      setEditPhotoPreview(null);
      return;
    }
    const url = URL.createObjectURL(editPhoto);
    setEditPhotoPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [editPhoto]);

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
    form.append("phone", phone.trim());
    form.append("email", email.trim());
    form.append("photo", photo);
    const r = await api<{ ok: boolean; error?: string }>("/api/admin/employees", {
      method: "POST",
      body: form,
    });
    if (r.ok) {
      setName("");
      setPin("");
      setPhone("");
      setEmail("");
      setPhoto(null);
      if (photoInputRef.current) photoInputRef.current.value = "";
      load();
    } else {
      toast(r.error || "Error");
    }
  }

  async function deleteEmployee(id: string, name: string) {
    if (!window.confirm(`¿Eliminar a ${name}? Esta acción no se puede deshacer.`)) return;
    const r = await api<{ ok: boolean; error?: string }>("/api/admin/employees/" + id, { method: "DELETE" });
    if (!r.ok) {
      toast(r.error || "No se pudo eliminar");
      return;
    }
    load();
  }

  function openEdit(emp: Employee) {
    setEditing(emp);
    setEditName(emp.name);
    setEditPin(emp.pin);
    setEditCategory(emp.category || "trabajador");
    setEditSchedIn(emp.sched_in);
    setEditSchedOut(emp.sched_out);
    setEditLunchMin(String(emp.lunch_minutes ?? ""));
    setEditPhone(emp.phone || "");
    setEditEmail(emp.email || "");
    setEditEmergencyContact(emp.emergencyContact || "");
    setEditMedicalHistory(emp.medicalHistory || "");
    setEditPhoto(null);
    setEditPhotoRemoved(false);
    if (editPhotoInputRef.current) editPhotoInputRef.current.value = "";
  }

  function closeEdit() {
    setEditing(null);
  }

  function handleEditCategoryChange(value: string) {
    setEditCategory(value);
    const cat = categories.find((c) => c.value === value);
    if (cat) {
      setEditSchedIn(cat.schedIn);
      setEditSchedOut(cat.schedOut);
      setEditLunchMin(String(cat.lunchMinutes));
    }
  }

  function handleRemoveEditPhoto() {
    setEditPhoto(null);
    if (editPhotoInputRef.current) editPhotoInputRef.current.value = "";
    setEditPhotoRemoved(true);
  }

  function openEnlarge() {
    if (editPhotoPreview) {
      setEnlargedPhoto(editPhotoPreview);
    } else if (!editPhotoRemoved && editing?.photoUrl) {
      setEnlargedPhoto(editing.photoUrl);
    }
  }

  async function saveEdit() {
    if (!editing) return;
    if (!editName.trim()) {
      toast("El nombre no puede estar vacío");
      return;
    }
    if (!/^\d{4}$/.test(editPin.trim())) {
      toast("El PIN debe tener 4 dígitos");
      return;
    }
    const form = new FormData();
    form.append("name", editName.trim());
    form.append("pin", editPin.trim());
    form.append("category", editCategory);
    form.append("schedIn", editSchedIn);
    form.append("schedOut", editSchedOut);
    form.append("lunchMinutes", editLunchMin);
    form.append("phone", editPhone.trim());
    form.append("email", editEmail.trim());
    form.append("emergencyContact", editEmergencyContact.trim());
    form.append("medicalHistory", editMedicalHistory.trim());
    if (editPhoto) {
      form.append("photo", editPhoto);
    } else if (editPhotoRemoved) {
      form.append("removePhoto", "true");
    }
    const r = await api<{ ok: boolean; error?: string }>("/api/admin/employees/" + editing.id, {
      method: "PATCH",
      body: form,
    });
    if (r.ok) {
      closeEdit();
      load();
    } else {
      toast(r.error || "Error");
    }
  }

  const canEnlarge = !!editPhotoPreview || (!editPhotoRemoved && !!editing?.photoUrl);
  const canRemovePhoto = !!editPhotoPreview || (!editPhotoRemoved && !!editing?.photoUrl);

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
        <input type="tel" placeholder="Teléfono (opcional)" value={phone} onChange={(e) => setPhone(e.target.value)} />
      </div>
      <div className="row">
        <input type="email" placeholder="Correo electrónico (opcional)" value={email} onChange={(e) => setEmail(e.target.value)} />
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
            capture="user"
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
                    {e.phone ? ` · ${e.phone}` : ""}
                  </span>
                </span>
              </span>
              <span style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <span className="pin">PIN {e.pin}</span>
                <button className="small-btn" style={{ color: "var(--brand-teal-deep)" }} onClick={() => openEdit(e)}>
                  Editar
                </button>
                <button className="small-btn" onClick={() => deleteEmployee(e.id, e.name)}>
                  Eliminar
                </button>
              </span>
            </div>
          ))
        ) : (
          <div className="msg-empty">Aún no hay empleados</div>
        )}
      </div>

      {editing && (
        <div
          onClick={closeEdit}
          style={{
            position: "fixed", inset: 0, background: "rgba(18,59,64,0.55)",
            display: "flex", alignItems: "center", justifyContent: "center",
            zIndex: 100, padding: 20,
          }}
        >
          <div
            className="card"
            onClick={(e) => e.stopPropagation()}
            style={{ width: "min(460px, 92vw)", maxHeight: "88vh", overflowY: "auto", padding: 20, margin: 0 }}
          >
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", marginBottom: 16 }}>
              {editPhotoPreview ? (
                <img className="emp-avatar emp-avatar-lg" src={editPhotoPreview} alt={editName} />
              ) : editPhotoRemoved ? (
                <span className="emp-avatar emp-avatar-lg emp-avatar-empty" aria-hidden="true" />
              ) : (
                <EmployeePhoto url={editing.photoUrl} alt={editing.name} large />
              )}
              <h3 style={{ margin: "10px 0 2px", color: "var(--ink)" }}>{editName || editing.name}</h3>
              <span className={`cat-badge ${editCategory}`}>{CATEGORY_LABEL[editCategory] || "Trabajador"}</span>
              <div className="row" style={{ marginTop: 8 }}>
                <button className="small-btn" style={{ color: "var(--brand-teal-deep)" }} disabled={!canEnlarge} onClick={openEnlarge}>
                  Ver en grande
                </button>
                <button className="small-btn" disabled={!canRemovePhoto} onClick={handleRemoveEditPhoto}>
                  Eliminar foto
                </button>
              </div>
              <div style={{ width: "100%", marginTop: 8 }}>
                <label style={{ fontSize: 11, color: "var(--muted)" }}>Cambiar foto</label>
                <input
                  ref={editPhotoInputRef}
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  onChange={(e) => setEditPhoto(e.target.files?.[0] || null)}
                />
              </div>
            </div>

            <div className="field-label" style={{ textAlign: "left" }}>
              Datos generales
            </div>
            <div className="row">
              <input type="text" placeholder="Nombre del empleado" value={editName} onChange={(e) => setEditName(e.target.value)} />
            </div>
            <div className="row">
              <input
                type="text"
                placeholder="PIN de 4 dígitos"
                maxLength={4}
                value={editPin}
                onChange={(e) => setEditPin(e.target.value)}
              />
            </div>
            <div className="row">
              <select value={editCategory} onChange={(e) => handleEditCategoryChange(e.target.value)}>
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
                <input type="time" value={editSchedIn} onChange={(e) => setEditSchedIn(e.target.value)} />
              </div>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: 11, color: "var(--muted)" }}>Salida esperada</label>
                <input type="time" value={editSchedOut} onChange={(e) => setEditSchedOut(e.target.value)} />
              </div>
            </div>
            <div className="row">
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: 11, color: "var(--muted)" }}>Minutos para comer</label>
                <input type="number" min={0} value={editLunchMin} onChange={(e) => setEditLunchMin(e.target.value)} />
              </div>
            </div>

            <div className="field-label" style={{ textAlign: "left", marginTop: 18 }}>
              Contacto
            </div>
            <div className="row">
              <input type="tel" placeholder="Teléfono" value={editPhone} onChange={(e) => setEditPhone(e.target.value)} />
            </div>
            <div className="row">
              <input type="email" placeholder="Correo electrónico" value={editEmail} onChange={(e) => setEditEmail(e.target.value)} />
            </div>
            <div className="row">
              <input
                type="text"
                placeholder="Contacto de emergencia (nombre y teléfono)"
                value={editEmergencyContact}
                onChange={(e) => setEditEmergencyContact(e.target.value)}
              />
            </div>

            <div className="field-label" style={{ textAlign: "left", marginTop: 18 }}>
              Historial médico
            </div>
            <div className="row">
              <textarea
                placeholder="Alergias, padecimientos, medicamentos, etc. (opcional)"
                rows={3}
                value={editMedicalHistory}
                onChange={(e) => setEditMedicalHistory(e.target.value)}
                style={{ width: "100%", resize: "vertical", fontFamily: "inherit", fontSize: 14, padding: 8 }}
              />
            </div>

            <div className="row" style={{ marginTop: 10 }}>
              <button className="btn ghost" style={{ flex: 1 }} onClick={closeEdit}>
                Cancelar
              </button>
              <button className="btn" style={{ flex: 1 }} onClick={saveEdit}>
                Guardar cambios
              </button>
            </div>
          </div>
        </div>
      )}

      {enlargedPhoto && <PhotoModal url={enlargedPhoto} onClose={() => setEnlargedPhoto(null)} />}
    </>
  );
}
