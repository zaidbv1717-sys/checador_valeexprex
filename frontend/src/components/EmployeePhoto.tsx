import { useEffect, useState } from "react";
import { fetchAuthedBlob } from "../api/client";

export default function EmployeePhoto({ url, alt, large }: { url: string | null; alt: string; large?: boolean }) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const className = `emp-avatar${large ? " emp-avatar-lg" : ""}`;

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
    return <span className={`${className} emp-avatar-empty`} aria-hidden="true" />;
  }
  return <img className={className} src={blobUrl} alt={alt} />;
}
