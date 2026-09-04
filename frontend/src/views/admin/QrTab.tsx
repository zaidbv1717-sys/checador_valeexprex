import { useEffect, useState } from "react";
import { QRCodeSVG } from "qrcode.react";

const STORAGE_KEY = "checador_qr_base_url";

export default function QrTab() {
  const isLocalhost = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
  const [ip, setIp] = useState(() => localStorage.getItem(STORAGE_KEY) || "");

  useEffect(() => {
    if (ip) localStorage.setItem(STORAGE_KEY, ip);
  }, [ip]);

  const origin = isLocalhost ? (ip ? `http://${ip}` : "") : window.location.origin;

  return (
    <>
      {isLocalhost && (
        <div className="alert-banner" style={{ background: "#FBF2E2", borderColor: "#EFDCB0", color: "#7A5A16" }}>
          ⚠ Estás viendo este panel como "localhost", que no funciona desde el celular de un empleado. Escribe abajo
          la dirección de red de esta computadora (ábrela con <code>ipconfig</code> en una ventana de símbolo del
          sistema y busca "Dirección IPv4", algo como 192.168.x.x).
        </div>
      )}
      {isLocalhost && (
        <div className="row" style={{ marginBottom: 10 }}>
          <input
            type="text"
            placeholder="192.168.1.100"
            value={ip}
            onChange={(e) => setIp(e.target.value.trim())}
          />
        </div>
      )}
      <div className="qr-print-area">
        <div className="field-label">Este es el enlace que deben escanear los empleados</div>
        <div className="qr-box">
          {origin ? (
            <>
              <div id="qrcanvas" style={{ display: "flex", justifyContent: "center", margin: "14px auto" }}>
                <QRCodeSVG value={origin} size={190} fgColor="#1F2937" bgColor="#ffffff" />
              </div>
              <div className="note" style={{ textAlign: "center", fontFamily: "var(--mono)" }}>
                {origin}
              </div>
            </>
          ) : (
            <div className="note" style={{ textAlign: "center" }}>
              Escribe la dirección de red arriba para generar el código.
            </div>
          )}
          <div className="note">
            Imprime este código y colócalo donde los empleados puedan escanearlo con su celular al llegar. Deben estar
            conectados a la misma red WiFi que esta computadora.
          </div>
        </div>
      </div>
      <div className="row no-print" style={{ marginTop: 10 }}>
        <button className="btn secondary" style={{ flex: 1 }} onClick={() => window.print()}>
          Imprimir hoja
        </button>
        <button className="btn ghost" style={{ flex: 1 }} onClick={() => window.location.reload()}>
          Refrescar enlace
        </button>
      </div>
    </>
  );
}
