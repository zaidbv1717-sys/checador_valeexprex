import { useState } from "react";
import type { AdminTab } from "../../types";
import RecordsTab from "./RecordsTab";
import EmployeesTab from "./EmployeesTab";
import JustificationsTab from "./JustificationsTab";
import CalendarTab from "./CalendarTab";
import QrTab from "./QrTab";
import ConfigTab from "./ConfigTab";

const TABS: AdminTab[] = ["registros", "empleados", "permisos", "calendario", "qr", "config"];
const LABELS: Record<AdminTab, string> = {
  registros: "Registros",
  empleados: "Empleados",
  permisos: "Permisos",
  calendario: "Calendario",
  qr: "Código QR",
  config: "Config",
};

export default function AdminDashboard({ onExit }: { onExit: () => void }) {
  const [tab, setTab] = useState<AdminTab>("registros");

  return (
    <div className="wrap">
      <div className="admin-header">
        <h2>Panel de administración</h2>
        <button className="admin-link" onClick={onExit}>
          Salir
        </button>
      </div>
      <div className="tabs">
        {TABS.map((t) => (
          <button key={t} className={`tab-btn ${tab === t ? "active" : ""}`} onClick={() => setTab(t)}>
            {LABELS[t]}
          </button>
        ))}
      </div>
      <div className="card body-pad">
        {tab === "registros" && <RecordsTab />}
        {tab === "empleados" && <EmployeesTab />}
        {tab === "permisos" && <JustificationsTab />}
        {tab === "calendario" && <CalendarTab />}
        {tab === "qr" && <QrTab />}
        {tab === "config" && <ConfigTab />}
      </div>
    </div>
  );
}
