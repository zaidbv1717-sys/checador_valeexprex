let adminPass = "";

export function setAdminPass(pass: string) {
  adminPass = pass;
}

export function getAdminPass() {
  return adminPass;
}

export async function api<T = any>(path: string, opts: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(opts.headers as Record<string, string> | undefined),
  };
  if (adminPass) headers["X-Admin-Pass"] = adminPass;
  const res = await fetch(path, { ...opts, headers });
  return res.json();
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
