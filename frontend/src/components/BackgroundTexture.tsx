const SMUDGES = [
  { cx: 60, cy: 620, r: 90, o: 0.22 },
  { cx: 40, cy: 260, r: 60, o: 0.16 },
  { cx: 560, cy: 300, r: 110, o: 0.18 },
  { cx: 480, cy: 700, r: 130, o: 0.2 },
  { cx: 300, cy: 60, r: 70, o: 0.1 },
];

const SCRATCHES = [
  "M 20 120 L 380 40",
  "M 60 480 L 340 560",
  "M 420 200 L 560 480",
  "M 10 700 L 260 620",
];

export default function BackgroundTexture() {
  return (
    <div className="bg-texture" aria-hidden="true">
      <svg viewBox="0 0 600 800" preserveAspectRatio="xMidYMid slice">
        <defs>
          <filter id="grain">
            <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" stitchTiles="stitch" result="noise" />
            <feColorMatrix in="noise" type="saturate" values="0" />
            <feComponentTransfer>
              <feFuncA type="linear" slope="0.35" />
            </feComponentTransfer>
          </filter>
          <radialGradient id="vignette" cx="50%" cy="8%" r="90%">
            <stop offset="0%" stopColor="#f1f2f2" />
            <stop offset="35%" stopColor="#dcdedf" />
            <stop offset="70%" stopColor="#b9bcbe" />
            <stop offset="100%" stopColor="#8f9294" />
          </radialGradient>
        </defs>
        <rect x="0" y="0" width="600" height="800" fill="url(#vignette)" />
        <rect x="0" y="0" width="600" height="800" filter="url(#grain)" style={{ mixBlendMode: "multiply" }} />
        <g fill="#3a3d3e">
          {SMUDGES.map((s, i) => (
            <circle key={i} cx={s.cx} cy={s.cy} r={s.r} opacity={s.o} style={{ filter: "blur(14px)" }} />
          ))}
        </g>
        <g stroke="#ffffff" strokeWidth="1" opacity="0.25" fill="none">
          {SCRATCHES.map((d, i) => (
            <path key={i} d={d} />
          ))}
        </g>
        <g stroke="#4a4d4e" strokeWidth="0.6" opacity="0.18" fill="none">
          {SCRATCHES.map((d, i) => (
            <path key={`d-${i}`} d={d} transform="translate(6,4)" />
          ))}
        </g>
      </svg>
    </div>
  );
}
