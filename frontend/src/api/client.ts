let adminPass = "";

export function setAdminPass(pass: string) {
  adminPass = pass;
}

export function getAdminPass() {
  return adminPass;
}

/**
 * Llama a la API y devuelve el cuerpo JSON.
 *
 * Nunca lanza: un fallo de red o una respuesta no-JSON se traducen a
 * `{ ok: false, error }`, porque cada vista ya sabe mostrar `error` en un toast.
 * Antes un `fetch` fallido o un 401 (que ahora si devuelve el login) lanzaba una
 * excepcion no capturada y la pantalla se quedaba colgada sin decir nada.
 */
export async function api<T = unknown>(path: string, opts: RequestInit = {}): Promise<T> {
  const isFormData = opts.body instanceof FormData;
  const headers: Record<string, string> = {
    ...(isFormData ? {} : { "Content-Type": "application/json" }),
    ...(opts.headers as Record<string, string> | undefined),
  };
  if (adminPass) headers["X-Admin-Pass"] = adminPass;
  try {
    const res = await fetch(path, { ...opts, headers });
    const body = await res.json().catch(() => null);
    if (body !== null) return body as T;
    return { ok: false, error: `Error del servidor (${res.status})` } as T;
  } catch {
    return { ok: false, error: "No hay conexión con el servidor" } as T;
  }
}

export async function fetchAuthedBlob(url: string): Promise<string> {
  const res = await fetch(url, { headers: adminPass ? { "X-Admin-Pass": adminPass } : {} });
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}

export async function downloadCsv(url: string, filename: string) {
  const res = await fetch(url, { headers: adminPass ? { "X-Admin-Pass": adminPass } : {} });
  const blob = await res.blob();
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
  URL.revokeObjectURL(link.href);
}
