import { useEffect, useState } from "react";
import { fetchAuthedBlob } from "../api/client";

export default function PhotoModal({ url, onClose }: { url: string; onClose: () => void }) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);

  useEffect(() => {
    let revoked = "";
    fetchAuthedBlob(url).then((b) => {
      revoked = b;
      setBlobUrl(b);
    });
    return () => {
      if (revoked) URL.revokeObjectURL(revoked);
    };
  }, [url]);

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed", inset: 0, background: "rgba(18,59,64,0.75)",
        display: "flex", alignItems: "center", justifyContent: "center",
        zIndex: 100, padding: 20,
      }}
    >
      {blobUrl ? (
        <img
          src={blobUrl}
          alt="Foto de la checada"
          style={{ maxWidth: "100%", maxHeight: "90vh", borderRadius: 12 }}
          onClick={(e) => e.stopPropagation()}
        />
      ) : (
        <div style={{ color: "#fff" }}>Cargando…</div>
      )}
    </div>
  );
}
