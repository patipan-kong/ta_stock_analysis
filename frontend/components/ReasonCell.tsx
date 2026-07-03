"use client";

import { useState } from "react";

// ─── Reason Cell (progressive disclosure) ──────────────────────────────────
// Shared by every Optimizer recommendation table (L1 Strategist swaps, L2
// Challenger / shared allocation table, and future L3 Auditor / AI Evaluation
// / Attribution tables). Collapsed state shows a 1-line headline (the AI's
// existing short `reason` text) plus an optional second line of deterministic
// context (score chips or an action cue) computed by the caller from fields
// already on the row — no new AI calls. Expanded state adds the untruncated
// reason (split into scannable fragments) and a deterministic facts list.
//
// Renders as a single <td> so it's a drop-in replacement across tables with
// different column counts, rather than a full-width sibling row that would
// force every caller to track its own colSpan and expanded-row-id bookkeeping.

export interface ReasonFact {
  label: string;
  value: string;
}

interface ReasonCellProps {
  reason?: string | null;
  context?: string | null;
  facts?: ReasonFact[];
  italic?: boolean;
  // Row's action/type label (e.g. "BUY", "REDUCE", "SWAP"). Used only to strip
  // action-echoing lead-in phrases ("New position", "Reduce", ...) from the
  // headline so line 1 reads as the thesis rather than restating the Action
  // column. Never rendered directly.
  action?: string | null;
}

// Headline now renders up to 2 lines (see line-clamp-2 below), so this only
// needs to catch text that would still overflow that larger budget.
const HEADLINE_OVERFLOW_CHARS = 110;

function splitReasonNotes(text: string): string[] {
  return text
    .split(/;\s*| — | – |\.\s+(?=[A-Z])/)
    .map((p) => p.trim())
    .filter((p) => p.length > 2);
}

// Lead-in phrases the AI commonly uses that just restate the Action badge
// already shown elsewhere in the row — stripped so the headline can surface
// the actual thesis instead of duplicated metadata.
const ACTION_ECHO_WORDS: Record<string, string[]> = {
  BUY: ["new position", "initiate position", "initiate", "buy"],
  ACCUMULATE: ["accumulate", "add to position", "increase position"],
  REDUCE: ["reduce", "trim", "decrease position"],
  SELL: ["exit position", "close position", "exit", "sell"],
  SWAP: ["swap"],
  HOLD: ["hold", "maintain"],
  WATCH: ["watch"],
};

function escapeRegExp(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function stripActionEcho(text: string, action?: string | null): string {
  const words = action ? ACTION_ECHO_WORDS[action.toUpperCase()] : undefined;
  if (!words || words.length === 0) return text;
  const re = new RegExp(`^(?:${words.map(escapeRegExp).join("|")})\\b[\\s,:;\\-–—]*`, "i");
  return text.replace(re, "");
}

function stripMetadataNoise(text: string): string {
  return text
    .replace(/^score\s*[:=]?\s*-?\d+(\.\d+)?\s*[,;:\-–—]?\s*/i, "")
    // Underscore-joined regime codes (STRONG_UPTREND, MOMENTUM_LOSS) — requires
    // an underscore so short indicator abbreviations (RSI, MACD, PE) survive.
    .replace(/^[A-Z]+(?:_[A-Z]+)+(?:\s+regime)?\b\s*[,;:\-–—]?\s*/, "")
    // Single-word regime code only when explicitly labeled ("NEUTRAL regime").
    .replace(/^[A-Z]{3,}\s+regime\b\s*[,;:\-–—]?\s*/i, "");
}

// Derives a scannable "investment thesis" headline from the AI's free-text
// `reason` by peeling off leading action-echo and score/regime metadata —
// deterministic post-processing of an existing field, not a new AI call.
function deriveHeadline(reason: string, action?: string | null): string {
  let t = reason.trim();
  if (!t) return t;
  let prev: string;
  do {
    prev = t;
    t = stripActionEcho(t, action).trim();
    t = stripMetadataNoise(t).trim();
  } while (t !== prev && t.length > 0);
  const result = t || reason.trim();
  return result.charAt(0).toUpperCase() + result.slice(1);
}

export function ReasonCell({ reason, context, facts = [], italic = false, action }: ReasonCellProps) {
  const [expanded, setExpanded] = useState(false);
  const text = (reason || "").trim();
  const headline = text ? deriveHeadline(text, action) : text;
  const notesRaw = text ? splitReasonNotes(text) : [];
  const notes = notesRaw.length > 1 ? notesRaw : [];
  const overflowsHeadline = text.length > HEADLINE_OVERFLOW_CHARS || headline !== text;
  const hasDetail = facts.length > 0 || notes.length > 0 || overflowsHeadline;

  return (
    <td className="py-1.5 align-top max-w-xs lg:max-w-none whitespace-normal">
      <div
        className={`line-clamp-2 text-xs ${italic ? "italic text-amber-600" : "text-gray-700 font-medium"}`}
        title={text || undefined}
      >
        {headline || "—"}
      </div>
      {(context || hasDetail) && (
        <div className="flex items-center justify-between gap-2 mt-0.5">
          {context && <span className="text-[11px] text-gray-400 line-clamp-1 min-w-0">{context}</span>}
          {hasDetail && (
            <button
              type="button"
              onClick={() => setExpanded((v) => !v)}
              className="text-[10px] text-gray-400 hover:text-blue-600 shrink-0 select-none"
            >
              {expanded ? "Less" : "Details"}
            </button>
          )}
        </div>
      )}
      {expanded && hasDetail && (
        <div className="mt-1.5 pt-1.5 border-t border-gray-100 space-y-1.5 max-w-sm">
          {facts.length > 0 && (
            <ul className="space-y-0.5">
              {facts.map((f) => (
                <li key={f.label} className="text-[11px] text-gray-600">
                  <span className="font-medium text-gray-500">{f.label}:</span> {f.value}
                </li>
              ))}
            </ul>
          )}
          {notes.length > 0 ? (
            <ul className="space-y-0.5">
              {notes.map((n, i) => (
                <li key={i} className="text-[11px] text-gray-600 flex items-start gap-1">
                  <span className="mt-0.5 shrink-0 text-gray-300">•</span>
                  <span>{n}</span>
                </li>
              ))}
            </ul>
          ) : overflowsHeadline ? (
            <p className="text-[11px] text-gray-600">{text}</p>
          ) : null}
        </div>
      )}
    </td>
  );
}
