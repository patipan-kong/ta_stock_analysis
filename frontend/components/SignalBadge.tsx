type Signal = "ACCUMULATE" | "BUY" | "WATCH" | "HOLD" | "REDUCE" | "SELL";

const COLOR: Record<Signal, string> = {
  ACCUMULATE: "#0F6E56",
  BUY:        "#27500A",
  WATCH:      "#0C447C",
  HOLD:       "#444441",
  REDUCE:     "#854F0B",
  SELL:       "#791F1F",
};

const VALID = new Set(Object.keys(COLOR));

export default function SignalBadge({ signal }: { signal: Signal | string }) {
  const s = VALID.has(signal) ? (signal as Signal) : "HOLD";
  const color = COLOR[s];
  return (
    <span
      className="inline-block px-2 py-0.5 text-xs font-bold rounded border"
      style={{ color, borderColor: color, backgroundColor: `${color}20` }}
    >
      {s}
    </span>
  );
}
