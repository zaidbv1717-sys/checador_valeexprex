const PATHS = [
  "M -20 60 C 60 20, 90 140, 180 90 S 320 40, 420 130",
  "M -10 220 C 90 170, 140 280, 240 230 S 380 180, 440 260",
  "M -30 420 C 70 380, 120 470, 220 430 S 360 380, 430 450",
  "M -20 640 C 80 600, 130 700, 230 660 S 370 610, 440 690",
  "M 20 -10 C 60 90, -20 160, 60 260 S 40 420, 120 520",
  "M 380 -10 C 340 90, 420 160, 340 260 S 360 420, 300 540",
];

export default function BackgroundVines() {
  return (
    <div className="bg-vines" aria-hidden="true">
      <svg viewBox="0 0 400 800" preserveAspectRatio="xMidYMid slice">
        <defs>
          <filter id="vineGlow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3.2" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          <linearGradient id="vineGradient" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="var(--brand-teal)" />
            <stop offset="100%" stopColor="var(--brand-green)" />
          </linearGradient>
        </defs>
        <g className="bg-vines-group" filter="url(#vineGlow)" fill="none" stroke="url(#vineGradient)" strokeWidth="1.4" strokeLinecap="round">
          {PATHS.map((d, i) => (
            <path key={i} d={d} opacity={0.35 + (i % 3) * 0.1} />
          ))}
        </g>
      </svg>
    </div>
  );
}
