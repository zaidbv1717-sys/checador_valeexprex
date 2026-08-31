import { useEffect, useState } from "react";
import { fetchAuthedBlob } from "../api/client";

export default function EmployeePhoto({ url, alt }: { url: string | null; alt: string }) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!url) {
      setBlobUrl(null);
      return;
    }
    let revoked = "";
    fetchAuthedBlob(url).then((b) => {
      revoked = b;
      setBlobUrl(b);
    });
    return () => {
      if (revoked) URL.revokeObjectURL(revoked);
    };
  }, [url]);

  if (!blobUrl) {
    return <span className="emp-avatar emp-avatar-empty" aria-hidden="true" />;
  }
  return <img className="emp-avatar" src={blobUrl} alt={alt} />;
}
