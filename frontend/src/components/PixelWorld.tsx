const LAND_PIXELS: [number, number][] = [
  [2, 2], [3, 2], [4, 2], [9, 2], [10, 2],
  [1, 3], [2, 3], [3, 3], [4, 3], [5, 3], [8, 3], [9, 3], [10, 3], [11, 3],
  [2, 4], [3, 4], [4, 4], [5, 4], [6, 4], [9, 4], [10, 4], [11, 4],
  [3, 5], [4, 5], [5, 5], [9, 5], [10, 5],
  [4, 6], [5, 6], [8, 6], [9, 6], [10, 6],
  [2, 7], [3, 7], [5, 7], [6, 7], [9, 7], [10, 7], [11, 7],
  [1, 8], [2, 8], [6, 8], [7, 8], [10, 8], [11, 8],
  [0, 9], [1, 9], [7, 9], [11, 9], [12, 9],
  [6, 10], [7, 10], [8, 10], [13, 10],
  [7, 11], [8, 11], [9, 11],
];

export default function PixelWorld() {
  return (
    <div className="pixel-world" aria-hidden="true">
      <span className="pixel-star s1" />
      <span className="pixel-star s2" />
      <span className="pixel-star s3" />
      <svg viewBox="0 0 16 16" width="40" height="40">
        <defs>
          <clipPath id="pixelGlobeClip">
            <circle cx="8" cy="8" r="7.6" />
          </clipPath>
        </defs>
        <g clipPath="url(#pixelGlobeClip)">
          <rect x="0" y="0" width="16" height="16" fill="var(--brand-teal)" />
          <g className="pixel-world-land">
            {LAND_PIXELS.map(([x, y]) => (
              <rect key={`a-${x}-${y}`} x={x} y={y} width="1" height="1" fill="var(--brand-green-deep)" />
            ))}
            {LAND_PIXELS.map(([x, y]) => (
              <rect key={`b-${x}-${y}`} x={x + 16} y={y} width="1" height="1" fill="var(--brand-green-deep)" />
            ))}
          </g>
          <rect x="0" y="0" width="16" height="1.6" fill="#fff" opacity="0.85" />
          <rect x="0" y="14.4" width="16" height="1.6" fill="#fff" opacity="0.85" />
        </g>
        <circle cx="8" cy="8" r="7.6" fill="none" stroke="rgba(18,59,64,0.15)" strokeWidth="0.3" />
      </svg>
    </div>
  );
}
