import { QRCodeSVG } from "qrcode.react";

export default function QrTab() {
  const origin = window.location.origin;
  return (
    <>
      <div className="field-label">Este es el enlace que deben escanear los empleados</div>
      <div className="qr-box">
        <div id="qrcanvas" style={{ display: "flex", justifyContent: "center", margin: "14px auto" }}>
          <QRCodeSVG value={origin} size={190} fgColor="#1F2937" bgColor="#ffffff" />
        </div>
        <div className="note" style={{ textAlign: "center", fontFamily: "var(--mono)" }}>
          {origin}
        </div>
        <div className="note">
          Imprime este código y colócalo donde los empleados puedan escanearlo con su celular al llegar. Deben estar
          conectados a la misma red WiFi que esta computadora.
        </div>
      </div>
    </>
  );
}
