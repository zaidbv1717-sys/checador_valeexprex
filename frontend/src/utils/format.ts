export function fmtTime(d: Date) {
  return d.toLocaleTimeString("es-MX", { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false });
}

export function fmtDate(d: Date) {
  return d.toLocaleDateString("es-MX", { weekday: "long", day: "numeric", month: "long" });
}

export function fmtHM(iso: string) {
  return new Date(iso).toLocaleTimeString("es-MX", { hour: "2-digit", minute: "2-digit" });
}

export function fmtShortDate(dateStr: string) {
  return new Date(dateStr + "T00:00:00").toLocaleDateString("es-MX", { day: "2-digit", month: "short" });
}

export const TYPE_LABEL: Record<string, string> = {
  entrada: "Entrada",
  comida_salida: "Salida a comer",
  comida_entrada: "Regreso de comer",
  salida: "Salida",
};

export const CATEGORY_LABEL: Record<string, string> = {
  practicante: "Practicante",
  trabajador: "Trabajador",
  administrador: "Administrador",
};

export const STAGES = ["entrada", "comida_salida", "comida_entrada", "salida"] as const;
