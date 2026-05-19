type Signal = "ACCUMULATE" | "BUY" | "WATCH" | "HOLD" | "REDUCE" | "SELL";

const STYLE: Record<Signal, string> = {
  ACCUMULATE: "bg-teal-100   text-teal-800   border-teal-400",
  BUY:        "bg-green-100  text-green-900  border-green-500",
  WATCH:      "bg-blue-100   text-blue-800   border-blue-400",
  HOLD:       "bg-gray-100   text-gray-700   border-gray-400",
  REDUCE:     "bg-amber-100  text-amber-800  border-amber-400",
  SELL:       "bg-red-100    text-red-800    border-red-500",
};

const VALID = new Set(Object.keys(STYLE));

export default function SignalBadge({ signal }: { signal: Signal | string }) {
  const s = VALID.has(signal) ? (signal as Signal) : "HOLD";
  return (
    <span className={`inline-block px-2 py-0.5 text-xs font-bold rounded border ${STYLE[s]}`}>
      {s}
    </span>
  );
}
