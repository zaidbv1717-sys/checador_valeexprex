export type Stage = "entrada" | "comida_salida" | "comida_entrada" | "salida";

export interface ActiveEmployee {
  id: string;
  name: string;
}

export interface Employee {
  id: string;
  name: string;
  pin: string;
  sched_in: string;
  sched_out: string;
  category: string;
  lunch_minutes: number | null;
  photoUrl: string | null;
}

export interface Category {
  value: string;
  label: string;
  schedIn: string;
  schedOut: string;
  lunchMinutes: number;
}

export interface ReportRow {
  employeeId: string;
  employeeName: string;
  date: string;
  entrada: string | null;
  comida_salida: string | null;
  comida_entrada: string | null;
  salida: string | null;
  hours: number;
  retardoMin: number;
  lunchLateMin: number;
  missing: boolean;
  note: string;
  entradaPhotoUrl: string | null;
  comidaSalidaPhotoUrl: string | null;
  comidaEntradaPhotoUrl: string | null;
  salidaPhotoUrl: string | null;
}

export interface Absence {
  employeeId: string;
  employeeName: string;
  date: string;
  justified: boolean;
  justificationType: string | null;
}

export interface DeviceAlert {
  id: string;
  ip: string | null;
  emp1_name: string;
  emp1_time: string;
  emp2_name: string;
  emp2_time: string;
  created_at: string;
  resolved: number;
}

export interface Justification {
  id: string;
  employee_id: string;
  employee_name: string;
  date_start: string;
  date_end: string;
  type: string;
  status: string;
  note: string | null;
  created_at: string;
}

export interface CalendarDay {
  day: number;
  date: string;
  weekday: number;
  status: "asistio" | "falta" | "justificado" | "no_laboral";
}

export interface EditTarget {
  employeeId: string;
  employeeName: string;
  dateStr: string;
  dateLabel: string;
  entrada: string | null;
  comida_salida: string | null;
  comida_entrada: string | null;
  salida: string | null;
  note: string;
}

export type AdminTab = "registros" | "empleados" | "permisos" | "calendario" | "qr" | "config";
export type View = "clock" | "admin-login" | "admin-recover" | "admin";
