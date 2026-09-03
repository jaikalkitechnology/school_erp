/** Self-contained Code-128 (subset B) barcode renderer as inline SVG.
 * No external dependency — encodes the value, computes the checksum, and
 * draws the bar pattern. Good for library copy barcodes (alphanumeric). */

// Standard Code-128 bar patterns, index = symbol value (0..106).
// Each entry is a run of module widths: bar, space, bar, space, bar, space.
// Index 106 is the stop pattern (7 widths).
const PATTERNS = [
  "212222", "222122", "222221", "121223", "121322", "131222", "122213", "122312",
  "132212", "221213", "221312", "231212", "112232", "122132", "122231", "113222",
  "123122", "123221", "223211", "221132", "221231", "213212", "223112", "312131",
  "311222", "321122", "321221", "312212", "322112", "322211", "212123", "212321",
  "232121", "111323", "131123", "131321", "112313", "132113", "132311", "211313",
  "231113", "231311", "112133", "112331", "132131", "113123", "113321", "133121",
  "313121", "211331", "231131", "213113", "213311", "213131", "311123", "311321",
  "331121", "312113", "312311", "332111", "314111", "221411", "431111", "111224",
  "111422", "121124", "121421", "141122", "141221", "112214", "112412", "122114",
  "122411", "142112", "142211", "241211", "221114", "413111", "241112", "134111",
  "111242", "121142", "121241", "114212", "124112", "124211", "411212", "421112",
  "421211", "212141", "214121", "412121", "111143", "111341", "131141", "114113",
  "114311", "411113", "411311", "113141", "114131", "311141", "411131", "211412",
  "211214", "211232", "2331112",
];

const START_B = 104;
const STOP = 106;

/** Returns the ordered list of symbol values for the given ASCII string. */
function encode(value: string): number[] {
  const codes: number[] = [START_B];
  let sum = START_B;
  let pos = 1;
  for (const ch of value) {
    let v = ch.charCodeAt(0) - 32; // Code B maps ASCII 32..126 → 0..94
    if (v < 0 || v > 94) v = 0; // fall back to space for out-of-range chars
    codes.push(v);
    sum += v * pos;
    pos += 1;
  }
  codes.push(sum % 103); // checksum
  codes.push(STOP);
  return codes;
}

export function Barcode128({
  value,
  height = 44,
  moduleWidth = 1.4,
}: {
  value: string;
  height?: number;
  moduleWidth?: number;
}) {
  const symbols = encode(value);
  const bars: { x: number; w: number }[] = [];
  let x = 0;
  for (const sym of symbols) {
    const pattern = PATTERNS[sym] ?? PATTERNS[0];
    for (let i = 0; i < pattern.length; i++) {
      const w = Number(pattern[i]) * moduleWidth;
      if (i % 2 === 0) bars.push({ x, w }); // even index = bar (black)
      x += w;
    }
  }
  const quiet = 10 * moduleWidth;
  const totalWidth = x + quiet * 2;

  return (
    <svg
      viewBox={`0 0 ${totalWidth} ${height}`}
      width="100%"
      height={height}
      preserveAspectRatio="xMidYMid meet"
      role="img"
      aria-label={`Barcode ${value}`}
    >
      <rect x={0} y={0} width={totalWidth} height={height} fill="#ffffff" />
      {bars.map((b, i) => (
        <rect key={i} x={quiet + b.x} y={0} width={b.w} height={height} fill="#000000" />
      ))}
    </svg>
  );
}
