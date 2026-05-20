"use client";

import { useEffect, useState, useRef } from "react";
import { getAIModels, getAISettings, updateAISettings, getAnalysisSources, updateAnalysisSource, getOptimizerLayers, updateOptimizerLayer, getPortfolioSettings, updatePortfolioSettings, getSectorLimits, updateSectorLimits, backfillSectors } from "@/lib/api";
import type { AIModelsConfig, AISettings, AIModelEntry, AnalysisSources, OptimizerLayers, PortfolioSettings, SectorLimits, BackfillSectorsResult } from "@/lib/api";

const PROVIDER_BADGE: Record<string, { label: string; cls: string }> = {
  anthropic: { label: "ANTHROPIC", cls: "bg-orange-100 text-orange-700" },
  openai:    { label: "OPENAI",    cls: "bg-green-100 text-green-700" },
  gemini:    { label: "GEMINI",    cls: "bg-blue-100 text-blue-700" },
  deepseek:  { label: "DEEPSEEK", cls: "bg-purple-100 text-purple-700" },
  zhipu:     { label: "ZHIPU",    cls: "bg-gray-100 text-gray-600" },
  groq:      { label: "GROQ",     cls: "bg-yellow-100 text-yellow-700" },
};

function ProviderBadge({ provider }: { provider: string }) {
  const b = PROVIDER_BADGE[provider] ?? { label: provider.toUpperCase(), cls: "bg-gray-100 text-gray-600" };
  return (
    <span className={`text-xs font-semibold px-2 py-0.5 rounded ${b.cls}`}>{b.label}</span>
  );
}

function CostInfo({ model }: { model: AIModelEntry | undefined }) {
  if (!model?.cost) return null;
  const { input, output } = model.cost.token_1m;
  return (
    <p className="text-xs text-gray-400 mt-1">
      ${input}/${output} per 1M tokens (in/out)
      {model.memo && <span className="ml-2 text-gray-400">· {model.memo}</span>}
    </p>
  );
}

function ModelSelector({
  label, providerKey, modelKey, settings, models, onChange,
}: {
  label: string;
  providerKey: keyof AISettings;
  modelKey: keyof AISettings;
  settings: AISettings;
  models: AIModelEntry[];
  onChange: (key: keyof AISettings, value: string) => void;
}) {
  const providers = [...new Set(models.map((m) => m.provider))];
  const selectedProvider = settings[providerKey];
  const filteredModels = models.filter((m) => m.provider === selectedProvider);
  const selectedModelId = settings[modelKey];
  const selectedModelEntry = models.find((m) => (m.apiModel ?? m.id) === selectedModelId);

  return (
    <div className="bg-white border rounded-xl p-5 shadow-sm space-y-4">
      <h3 className="font-semibold text-gray-800">{label}</h3>

      <div>
        <label className="block text-xs text-gray-500 mb-1">Provider</label>
        <div className="flex flex-wrap gap-2">
          {providers.map((p) => (
            <button
              key={p}
              onClick={() => {
                onChange(providerKey, p);
                const firstModel = models.find((m) => m.provider === p);
                if (firstModel) onChange(modelKey, firstModel.apiModel ?? firstModel.id);
              }}
              className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${
                selectedProvider === p
                  ? "border-blue-400 bg-blue-50 text-blue-700 font-semibold"
                  : "border-gray-200 hover:border-gray-300"
              }`}
            >
              <ProviderBadge provider={p} />
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-xs text-gray-500 mb-1">Model</label>
        <select
          value={selectedModelId}
          onChange={(e) => onChange(modelKey, e.target.value)}
          className="w-full border rounded-lg px-3 py-2 text-sm bg-white"
        >
          {filteredModels.map((m) => (
            <option key={m.id} value={m.apiModel ?? m.id}>
              {m.label}
            </option>
          ))}
        </select>
        <CostInfo model={selectedModelEntry} />
      </div>
    </div>
  );
}

// ─── Analysis Sources Toggle ───────────────────────────────────────────────────

const SOURCE_DEFS = [
  {
    key: "use_ta" as const,
    label: "Technical Analysis",
    desc: "RSI, MACD, Bollinger Bands, EMA trend",
    badge: "TA",
  },
  {
    key: "use_fa" as const,
    label: "Fundamental Analysis",
    desc: "P/E, EPS, Revenue Growth, ROE, Debt/Equity",
    badge: "FA",
  },
  {
    key: "use_news" as const,
    label: "News Sentiment",
    desc: "Recent news headlines and sentiment",
    badge: "News",
  },
];

function Toggle({ checked, onChange, disabled }: { checked: boolean; onChange: () => void; disabled?: boolean }) {
  return (
    <button
      onClick={onChange}
      disabled={disabled}
      className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none ${
        checked ? "bg-blue-500" : "bg-gray-300"
      } ${disabled ? "opacity-40 cursor-not-allowed" : "cursor-pointer"}`}
    >
      <span
        className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow transition-transform ${
          checked ? "translate-x-4" : "translate-x-0.5"
        }`}
      />
    </button>
  );
}

function AnalysisSourcesSection() {
  const [sources, setSources] = useState<AnalysisSources | null>(null);
  const [saving, setSaving] = useState<string | null>(null);
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    getAnalysisSources()
      .then(setSources)
      .catch(() => setLoadError("Failed to load source settings"));
  }, []);

  async function handleToggle(key: keyof AnalysisSources) {
    if (!sources) return;
    const newVal = !sources[key];
    const enabledCount = Object.values({ ...sources, [key]: newVal }).filter(Boolean).length;
    if (enabledCount === 0) return; // block disabling all

    setSaving(key);
    const optimistic = { ...sources, [key]: newVal };
    setSources(optimistic);
    try {
      const updated = await updateAnalysisSource(key, newVal);
      setSources(updated);
    } catch {
      setSources(sources); // revert
    } finally {
      setSaving(null);
    }
  }

  const enabledCount = sources ? Object.values(sources).filter(Boolean).length : 3;
  const allDisabled = enabledCount === 0;

  return (
    <div className="bg-white border rounded-xl p-5 shadow-sm space-y-4">
      <div>
        <h3 className="font-semibold text-gray-800">Analysis Sources</h3>
        <p className="text-xs text-gray-500 mt-0.5">
          Choose which data sources are included when generating AI analysis.
          Disabled sources reduce max confidence and lower API cost.
        </p>
      </div>

      {loadError && <p className="text-sm text-red-500">{loadError}</p>}

      {allDisabled && (
        <p className="text-xs text-amber-600 bg-amber-50 border border-amber-200 px-3 py-2 rounded-lg">
          At least 1 source required — enable at least one.
        </p>
      )}

      <div className="space-y-3">
        {SOURCE_DEFS.map(({ key, label, desc, badge }) => {
          const checked = sources ? sources[key] : true;
          const otherEnabled = sources
            ? Object.entries(sources).filter(([k, v]) => k !== key && v).length
            : 2;
          const wouldDisableAll = checked && otherEnabled === 0;

          return (
            <div key={key} className="flex items-center gap-3">
              <Toggle
                checked={checked}
                onChange={() => handleToggle(key)}
                disabled={saving !== null || wouldDisableAll}
              />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-800">{label}</span>
                  <span className="text-xs px-1.5 py-0.5 bg-gray-100 text-gray-500 rounded">{badge}</span>
                  {saving === key && <span className="text-xs text-gray-400">saving…</span>}
                </div>
                <p className="text-xs text-gray-400">{desc}</p>
              </div>
            </div>
          );
        })}
      </div>

      {sources && enabledCount < 3 && (
        <p className="text-xs text-amber-600">
          {3 - enabledCount} source{3 - enabledCount > 1 ? "s" : ""} disabled — max confidence capped at{" "}
          <strong>{enabledCount === 1 ? "low" : "medium"}</strong>.
        </p>
      )}
    </div>
  );
}

// ─── Sector Limits ────────────────────────────────────────────────────────────

const SECTOR_ORDER = [
  "Technology", "Financial", "Energy", "Healthcare",
  "Consumer", "Industrial", "Real Estate", "Utilities", "default",
];

function SectorLimitsSection() {
  const [limits, setLimits] = useState<SectorLimits | null>(null);
  const [saving, setSaving] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    getSectorLimits().then(setLimits).catch(() => {});
  }, []);

  function handleChange(sector: string, raw: string) {
    const val = Math.max(5, Math.min(100, parseInt(raw) || 5));
    setLimits((prev) => prev ? { ...prev, [sector]: val } : null);
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(async () => {
      if (!limits) return;
      const next = { ...limits, [sector]: val };
      setSaving(sector);
      try { await updateSectorLimits(next); } catch { /* silent */ } finally { setSaving(null); }
    }, 500);
  }

  if (!limits) return null;

  const sectors = [...SECTOR_ORDER.filter((s) => s in limits), ...Object.keys(limits).filter((s) => !SECTOR_ORDER.includes(s))];

  return (
    <div className="bg-white border rounded-xl p-5 shadow-sm space-y-4">
      <div>
        <h3 className="font-semibold text-gray-800">Sector Allocation Limits</h3>
        <p className="text-xs text-gray-500 mt-0.5">Maximum % of portfolio the Optimizer may allocate to each sector. Auto-saved on change.</p>
      </div>
      <div className="space-y-2">
        {sectors.map((sector) => (
          <div key={sector} className="flex items-center gap-3">
            <span className="text-sm text-gray-700 w-28 shrink-0">{sector === "default" ? "Other (default)" : sector}</span>
            <input
              type="number" min={5} max={100} step={5}
              value={limits[sector] ?? 25}
              onChange={(e) => handleChange(sector, e.target.value)}
              className="w-16 border rounded-lg px-2 py-1 text-sm text-center"
            />
            <span className="text-xs text-gray-400">%</span>
            <div className="flex-1 bg-gray-100 rounded-full h-1.5 overflow-hidden">
              <div
                className="h-1.5 rounded-full bg-blue-400 transition-all"
                style={{ width: `${Math.min(100, limits[sector] ?? 25)}%` }}
              />
            </div>
            {saving === sector && <span className="text-xs text-gray-400 shrink-0">saving…</span>}
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Portfolio Settings ───────────────────────────────────────────────────────

function PortfolioSettingsSection() {
  const [values, setValues] = useState<PortfolioSettings>({ max_stocks: 12, max_sector_pct: 40 });
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getPortfolioSettings().then(setValues).catch(() => {});
  }, []);

  async function handleSave() {
    setSaving(true);
    setSaved(false);
    setError("");
    try {
      const updated = await updatePortfolioSettings(values);
      setValues(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {
      setError("Failed to save");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="bg-white border rounded-xl p-5 shadow-sm space-y-4">
      <div>
        <h3 className="font-semibold text-gray-800">Portfolio Limits</h3>
        <p className="text-xs text-gray-500 mt-0.5">Used by the Optimizer to enforce position and sector constraints.</p>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Max stocks per portfolio</label>
          <div className="flex items-center gap-2">
            <input
              type="number" min={1} max={30} step={1}
              value={values.max_stocks}
              onChange={(e) => setValues((v) => ({ ...v, max_stocks: parseInt(e.target.value) || 12 }))}
              className="w-20 border rounded-lg px-3 py-1.5 text-sm"
            />
            <span className="text-xs text-gray-400">stocks (1–30)</span>
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Max same-sector allocation</label>
          <div className="flex items-center gap-2">
            <input
              type="number" min={10} max={100} step={5}
              value={values.max_sector_pct}
              onChange={(e) => setValues((v) => ({ ...v, max_sector_pct: parseInt(e.target.value) || 40 }))}
              className="w-20 border rounded-lg px-3 py-1.5 text-sm"
            />
            <span className="text-xs text-gray-400">% (10–100)</span>
          </div>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <button
          onClick={handleSave}
          disabled={saving}
          className="bg-blue-600 text-white px-4 py-1.5 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {saving ? "Saving…" : "Save"}
        </button>
        {saved && <span className="text-green-600 text-sm">✓ Saved</span>}
        {error && <span className="text-red-500 text-sm">{error}</span>}
      </div>
    </div>
  );
}

// ─── Data Management ──────────────────────────────────────────────────────────

function DataManagementSection() {
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<BackfillSectorsResult | null>(null);
  const [error, setError] = useState("");

  async function handleBackfill() {
    setRunning(true);
    setError("");
    setResult(null);
    try {
      setResult(await backfillSectors());
    } catch {
      setError("Failed to refresh sectors");
    } finally {
      setRunning(false);
    }
  }

  const total = result ? result.watchlist_updated + result.portfolio_updated : 0;

  return (
    <div className="bg-white border rounded-xl p-5 shadow-sm space-y-4">
      <div>
        <h3 className="font-semibold text-gray-800">Data Management</h3>
        <p className="text-xs text-gray-500 mt-0.5">
          Refresh stored sector labels for all portfolio and watchlist items.
          Use this after adding stocks, or when sectors show as &quot;Other&quot;.
        </p>
      </div>
      <div className="flex items-center gap-4 flex-wrap">
        <button
          onClick={handleBackfill}
          disabled={running}
          className="bg-gray-800 text-white px-4 py-1.5 rounded-lg text-sm font-medium hover:bg-gray-900 disabled:opacity-50"
        >
          {running ? "Running…" : "Refresh All Sectors"}
        </button>
        {result && (
          <span className="text-sm text-green-600">
            ✓ Updated {total} sector{total !== 1 ? "s" : ""}
            {result.failed.length > 0 && (
              <span className="text-amber-600 ml-1">
                ({result.failed.length} failed: {result.failed.join(", ")})
              </span>
            )}
          </span>
        )}
        {error && <span className="text-sm text-red-500">{error}</span>}
      </div>
    </div>
  );
}

// ─── Optimizer Layers ─────────────────────────────────────────────────────────

const LAYER_DEFS: { key: "layer1" | "layer2" | "layer3"; label: string; desc: string }[] = [
  { key: "layer1", label: "Layer 1 — Strategist",   desc: "Aggressive growth with sector diversification" },
  { key: "layer2", label: "Layer 2 — Challenger",   desc: "Independent reviewer seeking alternative allocations" },
  { key: "layer3", label: "Layer 3 — Risk Auditor", desc: "Concentration risk and assumption validator" },
];

function OptimizerLayersSection({ config }: { config: AIModelsConfig }) {
  const [layers, setLayers] = useState<OptimizerLayers | null>(null);
  const [saving, setSaving] = useState<string | null>(null);

  useEffect(() => {
    getOptimizerLayers().then(setLayers).catch(() => {});
  }, []);

  async function handleChange(layer: "layer1" | "layer2" | "layer3", provider: string, model: string) {
    if (!layers) return;
    const optimistic = { ...layers, [layer]: { ...layers[layer], provider, model } };
    setLayers(optimistic);
    setSaving(layer);
    try {
      const updated = await updateOptimizerLayer(layer, provider, model);
      setLayers(updated);
    } catch {
      setLayers(layers);
    } finally {
      setSaving(null);
    }
  }

  if (!layers) return null;

  return (
    <div className="bg-white border rounded-xl p-5 shadow-sm space-y-5">
      <div>
        <h3 className="font-semibold text-gray-800">Optimizer Layers</h3>
        <p className="text-xs text-gray-500 mt-0.5">Each layer uses a different AI model for multi-perspective analysis.</p>
      </div>
      {LAYER_DEFS.map(({ key, label, desc }) => {
        const layer = layers[key];
        const filteredModels = config.models.filter((m) => m.provider === layer.provider);
        const selectedModel = layer.model;
        return (
          <div key={key} className="space-y-2">
            <div>
              <p className="text-sm font-medium text-gray-700">{label}</p>
              <p className="text-xs text-gray-400">{desc}</p>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {[...new Set(config.models.map((m) => m.provider))].map((p) => {
                const b = PROVIDER_BADGE[p] ?? { label: p.toUpperCase(), cls: "bg-gray-100 text-gray-600" };
                return (
                  <button
                    key={p}
                    disabled={saving === key}
                    onClick={() => {
                      const first = config.models.find((m) => m.provider === p);
                      if (first) handleChange(key, p, first.apiModel ?? first.id);
                    }}
                    className={`text-xs px-2.5 py-1 rounded-lg border transition-colors disabled:opacity-50 ${
                      layer.provider === p
                        ? "border-blue-400 bg-blue-50 text-blue-700 font-semibold"
                        : "border-gray-200 hover:border-gray-300"
                    }`}
                  >
                    <ProviderBadge provider={p} />
                  </button>
                );
              })}
            </div>
            <div className="flex items-center gap-2">
              <select
                value={selectedModel}
                disabled={saving === key}
                onChange={(e) => handleChange(key, layer.provider, e.target.value)}
                className="flex-1 border rounded-lg px-2.5 py-1.5 text-sm bg-white disabled:opacity-50"
              >
                {filteredModels.map((m) => (
                  <option key={m.id} value={m.apiModel ?? m.id}>{m.label}</option>
                ))}
              </select>
              {saving === key && <span className="text-xs text-gray-400">saving…</span>}
            </div>
            <CostInfo model={config.models.find((m) => (m.apiModel ?? m.id) === selectedModel)} />
          </div>
        );
      })}
      <p className="text-xs text-gray-400">Auto-saved on change.</p>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function SettingsPage() {
  const [config, setConfig] = useState<AIModelsConfig | null>(null);
  const [settings, setSettings] = useState<AISettings>({
    analyze_provider: "anthropic",
    analyze_model: "claude-sonnet-4-6",
    optimize_provider: "anthropic",
    optimize_model: "claude-sonnet-4-6",
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([getAIModels(), getAISettings()])
      .then(([cfg, s]) => { setConfig(cfg); setSettings(s); })
      .catch(() => setError("Failed to load settings"))
      .finally(() => setLoading(false));
  }, []);

  function handleChange(key: keyof AISettings, value: string) {
    setSettings((prev) => ({ ...prev, [key]: value }));
    setSaved(false);
  }

  async function handleSave() {
    setSaving(true);
    setError("");
    try {
      const updated = await updateAISettings(settings);
      setSettings(updated);
      setSaved(true);
    } catch {
      setError("Failed to save settings");
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <p className="text-sm text-gray-400">Loading…</p>;

  const models = config?.models ?? [];

  return (
    <div className="space-y-8 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold mb-1">Settings</h1>
        <p className="text-sm text-gray-500">Configure AI models and data sources for analysis.</p>
      </div>

      {/* Analysis Sources — auto-save on toggle */}
      <AnalysisSourcesSection />

      {/* Sector Allocation Limits */}
      <SectorLimitsSection />

      {/* Portfolio Limits */}
      <PortfolioSettingsSection />

      {/* Optimizer Layers — auto-save on change */}
      {config && <OptimizerLayersSection config={config} />}

      {/* Data Management */}
      <DataManagementSection />

      {/* AI Model Settings */}
      <ModelSelector
        label="Analysis Model"
        providerKey="analyze_provider"
        modelKey="analyze_model"
        settings={settings}
        models={models}
        onChange={handleChange}
      />

      <div className="flex items-center gap-4">
        <button
          onClick={handleSave}
          disabled={saving}
          className="bg-blue-600 text-white px-6 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {saving ? "Saving…" : "Save"}
        </button>
        {saved && <span className="text-green-600 text-sm">✓ Saved</span>}
        {error && <span className="text-red-500 text-sm">{error}</span>}
      </div>
    </div>
  );
}
