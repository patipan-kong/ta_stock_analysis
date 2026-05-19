const PROVIDER_STYLES: Record<string, string> = {
  anthropic: "bg-orange-50 text-orange-700 border-orange-200",
  openai:    "bg-green-50 text-green-700 border-green-200",
  gemini:    "bg-blue-50 text-blue-700 border-blue-200",
  deepseek:  "bg-purple-50 text-purple-700 border-purple-200",
  zhipu:     "bg-gray-100 text-gray-600 border-gray-200",
  groq:      "bg-yellow-50 text-yellow-700 border-yellow-200",
};

export default function AIBadge({
  provider,
  model,
  label = "by",
}: {
  provider?: string | null;
  model?: string | null;
  label?: string;
}) {
  if (!provider || !model) return null;
  const cls = PROVIDER_STYLES[provider] ?? "bg-gray-100 text-gray-500 border-gray-200";
  const shortModel = model.length > 24 ? model.slice(0, 22) + "…" : model;
  return (
    <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full border ${cls}`}>
      <span className="opacity-60">🤖 {label}</span>
      <span className="font-medium">{shortModel}</span>
      <span className="opacity-50 uppercase tracking-wide text-[10px]">{provider}</span>
    </span>
  );
}
