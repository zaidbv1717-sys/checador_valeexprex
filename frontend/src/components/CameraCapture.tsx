import { useEffect, useRef, useState } from "react";

const SUPPORTS_LIVE_CAMERA = !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);

export default function CameraCapture({
  onCapture,
  onCancel,
}: {
  onCapture: (file: File) => void;
  onCancel: () => void;
}) {
  if (!SUPPORTS_LIVE_CAMERA) {
    return <FileFallbackCapture onCapture={onCapture} onCancel={onCancel} />;
  }
  return <LiveCameraCapture onCapture={onCapture} onCancel={onCancel} />;
}

/**
 * getUserMedia solo está disponible en contexto seguro (https:// o localhost). Si la app
 * se abre por la IP de red en LAN (http://192.168.x.x, el caso normal desde un celular),
 * el navegador no expone la cámara en vivo — así que en ese caso caemos a un <input
 * type=file capture> que abre la app de cámara nativa del dispositivo.
 */
function FileFallbackCapture({
  onCapture,
  onCancel,
}: {
  onCapture: (file: File) => void;
  onCancel: () => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const triggered = useRef(false);

  useEffect(() => {
    if (!triggered.current) {
      triggered.current = true;
      inputRef.current?.click();
    }
  }, []);

  return (
    <input
      ref={inputRef}
      type="file"
      accept="image/*"
      capture="user"
      style={{ display: "none" }}
      onChange={(e) => {
        const file = e.target.files?.[0];
        if (file) onCapture(file);
        else onCancel();
      }}
    />
  );
}

function LiveCameraCapture({
  onCapture,
  onCancel,
}: {
  onCapture: (file: File) => void;
  onCancel: () => void;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewBlob, setPreviewBlob] = useState<Blob | null>(null);

  function startStream() {
    navigator.mediaDevices
      .getUserMedia({ video: { facingMode: "user" }, audio: false })
      .then((stream) => {
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.play().catch(() => {});
        }
      })
      .catch(() => setError("No se pudo acceder a la cámara. Revisa los permisos del navegador."));
  }

  useEffect(() => {
    startStream();
    return () => {
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function stopStream() {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
  }

  function takePhoto() {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || !video.videoWidth) return;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob(
      (blob) => {
        if (!blob) return;
        setPreviewBlob(blob);
        setPreviewUrl(URL.createObjectURL(blob));
        stopStream();
      },
      "image/jpeg",
      0.9
    );
  }

  function retake() {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(null);
    setPreviewBlob(null);
    setError(null);
    startStream();
  }

  function confirm() {
    if (!previewBlob) return;
    onCapture(new File([previewBlob], "checada.jpg", { type: "image/jpeg" }));
  }

  function cancel() {
    stopStream();
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    onCancel();
  }

  return (
    <div
      style={{
        position: "fixed", inset: 0, background: "rgba(18,59,64,0.85)",
        display: "flex", alignItems: "center", justifyContent: "center",
        zIndex: 200, padding: 20,
      }}
    >
      <div style={{ background: "#fff", borderRadius: 14, padding: 16, maxWidth: 420, width: "100%", textAlign: "center" }}>
        <div className="field-label" style={{ marginBottom: 12 }}>
          {previewUrl ? "¿Se ve bien la foto?" : "Toma tu foto para marcar"}
        </div>

        {error && <div className="note err" style={{ marginBottom: 12 }}>{error}</div>}

        {!error && !previewUrl && (
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            style={{ width: "100%", borderRadius: 10, background: "#000", transform: "scaleX(-1)" }}
          />
        )}
        {previewUrl && (
          <img src={previewUrl} alt="Vista previa" style={{ width: "100%", borderRadius: 10 }} />
        )}
        <canvas ref={canvasRef} style={{ display: "none" }} />

        <div className="row" style={{ marginTop: 14 }}>
          {!previewUrl ? (
            <>
              <button className="btn" style={{ flex: 1 }} onClick={takePhoto} disabled={!!error}>
                Tomar foto
              </button>
              <button className="btn ghost" style={{ flex: 1 }} onClick={cancel}>
                Cancelar
              </button>
            </>
          ) : (
            <>
              <button className="btn secondary" style={{ flex: 1 }} onClick={confirm}>
                Usar esta foto
              </button>
              <button className="btn ghost" style={{ flex: 1 }} onClick={retake}>
                Repetir
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
