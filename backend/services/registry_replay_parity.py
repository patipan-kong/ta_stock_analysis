"""Golden Baseline / Replay Parity — Stage 1 of M5 Track B.

Reference: docs/implementation/M5_TRACK_B_NATIVE_INTEGRATION_TDD.md §5.2, §7
Stage 1 ("Golden Baseline Capture"). ADR-005's own "Consequences" section:
"replay parity is measured against correct accounting, not against today's
bugs" — this module is what makes that measurable. It exists to prove, before
any asset_id migration begins, that today's post-Stage-0 replay is
deterministic and to freeze its output as the fixed reference every later
migration stage (Stage 4's cutover gate, §7 Stage 4) is compared against.

Read-only. Every public function here either performs a dry-run replay
(`rebuild_portfolio(..., dry_run=True)`, which itself never writes) or
operates on already-materialized results in memory. No schema change, no
asset_id, no Registry access, no write-path change — those are Stage 2+.

No new diff algorithm (§6, ADR-004): the MATCH/DIFFERENT/MISSING/EXTRA
vocabulary is portfolio_rebuilder.py's own `ReconciliationStatus`, reused
as-is. `_finding_key()` for validator-finding identity is ledger_validator.py's
own existing helper (already used internally by `compare_ledger_validation`),
reused rather than reimplemented.

Deviations from the TDD's literal §5.2 signatures (both mechanical, not
design choices — see docs/implementation/M5_TRACK_B_NATIVE_INTEGRATION_TDD.md
§5.2 for the original):
  - `capture_golden_baseline` is declared `async def` and takes an explicit
    `workspace_id`, because it must call `rebuild_portfolio()`, which is
    itself `async def` and workspace-scoped like every other multi-tenant
    entry point in this codebase. A sync function cannot await it.
  - `ParityReport` gains one additive field, `validator_diffs`, with a
    default of `()` so the TDD's original 4-field shape still constructs
    positionally. The TDD's own §10.3 testing strategy requires validator-
    output parity ("ledger_validator.py CHECK 2 ... asserting zero
    SYMBOL_ALIAS findings"; "verify_snapshots and validate_ledger ...
    asserting no new findings relative to the Stage 1 baseline run") — that
    requires a place to carry the comparison result.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from services.ledger_validator import LedgerValidationReport, _finding_key
from services.portfolio_rebuilder import (
    ReconciliationRow,
    ReconciliationStatus,
    RebuildResult,
    rebuild_portfolio,
)

_DEFAULT_BASELINE_DIR = "golden_baselines"


# ══════════════════════════════════════════════════════════════════════════════
# Data model
# ══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class HoldingDiff:
    """One field-level difference between a baseline's and a rebuilt run's
    replay-derived holdings truth. `status` never carries MATCH — only rows
    that actually differ are materialized."""
    symbol:         str
    field:          str
    baseline_value: Any
    rebuilt_value:  Any
    status:         ReconciliationStatus   # DIFFERENT | MISSING | EXTRA


@dataclass(frozen=True)
class SnapshotDiff:
    """One field-level difference between a baseline's and a rebuilt run's
    replay-derived snapshot (NAV) truth."""
    date:           str
    field:          str
    baseline_value: Any
    rebuilt_value:  Any
    status:         ReconciliationStatus   # DIFFERENT | MISSING | EXTRA


@dataclass(frozen=True)
class ValidatorDiff:
    """One difference in the set of ledger_validator findings between the
    baseline capture and a later rebuild, keyed by ledger_validator.py's own
    `_finding_key()` (check_id + transaction ids, or check_id + title)."""
    finding_key:       str
    status:            ReconciliationStatus   # MISSING (baseline-only) | EXTRA (rebuilt-only) | DIFFERENT (severity changed)
    baseline_severity: str | None
    rebuilt_severity:  str | None


@dataclass(frozen=True)
class GoldenBaseline:
    """A frozen, hashable, deterministic snapshot of one portfolio's replay
    truth, captured post-Stage-0.

    Per TDD §7 Stage 1: "These baselines are the fixed parity reference for
    the rest of this document. No further exception is granted once
    captured." This dataclass is the storage shape for that reference.
    """
    portfolio_id:                 int
    portfolio_name:               str
    captured_at:                  str             # UTC ISO-8601 — informational only, excluded from content_hash
    success:                      bool
    transactions_replayed:        int
    effective_transaction_count:  int
    excluded_transaction_count:   int
    reconstructed_holdings_count: int
    reconstructed_cash:           float | None
    snapshots_processed:          int
    # (symbol, field, value) triples, sorted — the replay-derived holdings truth
    holdings_truth:                tuple[tuple[str, str, Any], ...]
    # (date, field, value) triples, sorted — the replay-derived snapshot/NAV truth
    snapshot_truth:                tuple[tuple[str, str, Any], ...]
    # (finding_key, severity) pairs, sorted — the validator's findings at capture time
    validator_finding_keys:        tuple[tuple[str, str], ...]
    validator_overall_severity:    str
    content_hash:                  str


@dataclass(frozen=True)
class ParityReport:
    """Result of comparing a GoldenBaseline against a later RebuildResult.

    Matches TDD §5.2's ParityReport shape (portfolio_id, is_bit_identical,
    snapshot_diffs, holding_diffs) plus the additive `validator_diffs` field
    (see module docstring)."""
    portfolio_id:      int
    is_bit_identical:  bool
    snapshot_diffs:    tuple[SnapshotDiff, ...]
    holding_diffs:     tuple[HoldingDiff, ...]
    validator_diffs:   tuple[ValidatorDiff, ...] = ()


@dataclass(frozen=True)
class RegressionReportEntry:
    portfolio_id:          int
    portfolio_name:        str
    baseline_hash:         str
    is_bit_identical:      bool
    holding_diff_count:    int
    snapshot_diff_count:   int
    validator_diff_count:  int


@dataclass(frozen=True)
class RegressionReport:
    """Summary of a determinism check run across one or more portfolios.

    Answers exactly the four questions Stage 1 exists to answer: how many
    portfolios were checked, whether their replay is deterministic (replay
    parity), whether their validator output is deterministic (validator
    parity), and what each portfolio's baseline hash is (the artifact every
    later migration stage compares against)."""
    generated_at:               str
    portfolio_count:            int
    portfolios_bit_identical:   int
    portfolios_with_diffs:      int
    entries:                    tuple[RegressionReportEntry, ...]


# ══════════════════════════════════════════════════════════════════════════════
# Truth extraction — reduces a RebuildResult's reconciliation_report (which
# compares live-DB-vs-reconstructed) down to just the reconstructed side,
# i.e. what replay itself produced, independent of whatever happens to be in
# the DB at capture time.
# ══════════════════════════════════════════════════════════════════════════════

def _extract_holdings_truth(rows: list[ReconciliationRow]) -> tuple[tuple[str, str, Any], ...]:
    truth: dict[tuple[str, str], Any] = {}
    for row in rows:
        if row.entity_type != "portfolio_item":
            continue
        if row.status == ReconciliationStatus.EXTRA:
            continue  # DB-only leftover — not something replay produced
        if row.field == "*":
            if row.reconstructed_value is None:
                continue
            for k, v in row.reconstructed_value.items():
                truth[(row.identifier, k)] = v
        else:
            truth[(row.identifier, row.field)] = row.reconstructed_value
    return tuple(sorted((sym, fld, val) for (sym, fld), val in truth.items()))


def _extract_snapshot_truth(rows: list[ReconciliationRow]) -> tuple[tuple[str, str, Any], ...]:
    truth: dict[tuple[str, str], Any] = {}
    for row in rows:
        if row.entity_type != "snapshot":
            continue
        if row.status == ReconciliationStatus.EXTRA:
            continue
        if row.field == "*":
            if row.reconstructed_value is None:
                continue
            for k, v in row.reconstructed_value.items():
                truth[(row.identifier, k)] = v
        else:
            truth[(row.identifier, row.field)] = row.reconstructed_value
    return tuple(sorted((date, fld, val) for (date, fld), val in truth.items()))


def _extract_validator_finding_keys(
    report: LedgerValidationReport | None,
) -> tuple[tuple[str, str], ...]:
    if report is None:
        return ()
    return tuple(sorted((_finding_key(f), f.severity.value) for f in report.findings))


def _compute_content_hash(
    holdings_truth:         tuple[tuple[str, str, Any], ...],
    snapshot_truth:         tuple[tuple[str, str, Any], ...],
    validator_finding_keys: tuple[tuple[str, str], ...],
    reconstructed_cash:     float | None,
) -> str:
    payload = {
        "holdings_truth":         holdings_truth,
        "snapshot_truth":         snapshot_truth,
        "validator_finding_keys": validator_finding_keys,
        "reconstructed_cash":     reconstructed_cash,
    }
    blob = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


# ══════════════════════════════════════════════════════════════════════════════
# Public API
# ══════════════════════════════════════════════════════════════════════════════

async def capture_golden_baseline(
    db:             Session,
    portfolio_id:   int,
    workspace_id:   int,
    skip_snapshots: bool = False,
) -> GoldenBaseline:
    """Run one dry-run replay and freeze its deterministic output.

    Read-only — delegates entirely to `rebuild_portfolio(..., dry_run=True)`,
    which never writes to the database. `skip_snapshots=True` omits NAV /
    snapshot truth from the baseline (faster, but a strictly weaker
    reference — only use it where snapshot history is not being validated).
    """
    result = await rebuild_portfolio(
        db             = db,
        portfolio_id   = portfolio_id,
        workspace_id   = workspace_id,
        dry_run        = True,
        skip_snapshots = skip_snapshots,
        backup         = False,
    )

    holdings_truth         = _extract_holdings_truth(result.reconciliation_report)
    snapshot_truth          = _extract_snapshot_truth(result.reconciliation_report)
    validator_finding_keys = _extract_validator_finding_keys(result.validator_report)
    content_hash = _compute_content_hash(
        holdings_truth, snapshot_truth, validator_finding_keys, result.reconstructed_cash,
    )

    return GoldenBaseline(
        portfolio_id                 = result.portfolio_id,
        portfolio_name                = result.portfolio_name,
        captured_at                   = datetime.now(timezone.utc).isoformat(),
        success                       = result.success,
        transactions_replayed         = result.transactions_replayed,
        effective_transaction_count   = result.effective_transaction_count,
        excluded_transaction_count    = result.excluded_transaction_count,
        reconstructed_holdings_count  = result.reconstructed_holdings_count,
        reconstructed_cash            = result.reconstructed_cash,
        snapshots_processed           = result.snapshots_processed,
        holdings_truth                = holdings_truth,
        snapshot_truth                = snapshot_truth,
        validator_finding_keys        = validator_finding_keys,
        validator_overall_severity    = (
            result.validator_report.overall_severity if result.validator_report else "PASS"
        ),
        content_hash                  = content_hash,
    )


def compare_against_baseline(baseline: GoldenBaseline, rebuilt: RebuildResult) -> ParityReport:
    """Compare a stored GoldenBaseline against a freshly rebuilt RebuildResult.

    Pure — no DB access, no I/O. `is_bit_identical=True` iff no diff of any
    kind (holdings, snapshots, or validator findings) is found.
    """
    rebuilt_holdings_truth = _extract_holdings_truth(rebuilt.reconciliation_report)
    rebuilt_snapshot_truth = _extract_snapshot_truth(rebuilt.reconciliation_report)
    rebuilt_finding_keys   = _extract_validator_finding_keys(rebuilt.validator_report)

    holding_diffs  = _diff_truth_maps(baseline.holdings_truth, rebuilt_holdings_truth, HoldingDiff, "symbol")
    snapshot_diffs = _diff_truth_maps(baseline.snapshot_truth, rebuilt_snapshot_truth, SnapshotDiff, "date")
    validator_diffs = _diff_validator_findings(baseline.validator_finding_keys, rebuilt_finding_keys)

    return ParityReport(
        portfolio_id      = rebuilt.portfolio_id,
        is_bit_identical  = not (holding_diffs or snapshot_diffs or validator_diffs),
        snapshot_diffs    = snapshot_diffs,
        holding_diffs     = holding_diffs,
        validator_diffs   = validator_diffs,
    )


def _diff_truth_maps(
    baseline_triples: tuple[tuple[str, str, Any], ...],
    rebuilt_triples:  tuple[tuple[str, str, Any], ...],
    diff_cls:         type,
    identifier_field: str,
) -> tuple[Any, ...]:
    baseline_map = {(ident, fld): val for ident, fld, val in baseline_triples}
    rebuilt_map  = {(ident, fld): val for ident, fld, val in rebuilt_triples}

    diffs: list[Any] = []
    for key in sorted(set(baseline_map) | set(rebuilt_map)):
        in_baseline = key in baseline_map
        in_rebuilt  = key in rebuilt_map
        ident, fld  = key

        if in_baseline and not in_rebuilt:
            diffs.append(diff_cls(**{identifier_field: ident}, field=fld,
                                   baseline_value=baseline_map[key], rebuilt_value=None,
                                   status=ReconciliationStatus.MISSING))
        elif in_rebuilt and not in_baseline:
            diffs.append(diff_cls(**{identifier_field: ident}, field=fld,
                                   baseline_value=None, rebuilt_value=rebuilt_map[key],
                                   status=ReconciliationStatus.EXTRA))
        else:
            b_val, r_val = baseline_map[key], rebuilt_map[key]
            if b_val != r_val:
                diffs.append(diff_cls(**{identifier_field: ident}, field=fld,
                                       baseline_value=b_val, rebuilt_value=r_val,
                                       status=ReconciliationStatus.DIFFERENT))
    return tuple(diffs)


def _diff_validator_findings(
    baseline_keys: tuple[tuple[str, str], ...],
    rebuilt_keys:  tuple[tuple[str, str], ...],
) -> tuple[ValidatorDiff, ...]:
    baseline_map = dict(baseline_keys)   # finding_key -> severity
    rebuilt_map  = dict(rebuilt_keys)

    diffs: list[ValidatorDiff] = []
    for key in sorted(set(baseline_map) | set(rebuilt_map)):
        in_baseline = key in baseline_map
        in_rebuilt  = key in rebuilt_map

        if in_baseline and not in_rebuilt:
            diffs.append(ValidatorDiff(key, ReconciliationStatus.MISSING, baseline_map[key], None))
        elif in_rebuilt and not in_baseline:
            diffs.append(ValidatorDiff(key, ReconciliationStatus.EXTRA, None, rebuilt_map[key]))
        elif baseline_map[key] != rebuilt_map[key]:
            diffs.append(ValidatorDiff(key, ReconciliationStatus.DIFFERENT, baseline_map[key], rebuilt_map[key]))
    return tuple(diffs)


async def run_determinism_check(
    db:             Session,
    portfolio_id:   int,
    workspace_id:   int,
    skip_snapshots: bool = False,
) -> tuple[GoldenBaseline, ParityReport]:
    """Replay one portfolio twice and prove the two replays are bit-identical.

    This is Stage 1's own acceptance test, applied at capture time rather
    than waiting for Stage 4: if replay were non-deterministic, a baseline
    captured today would already be worthless as a future reference. Runs
    `capture_golden_baseline()` once, then an independent second dry-run
    replay, and diffs them via `compare_against_baseline()`.
    """
    baseline = await capture_golden_baseline(db, portfolio_id, workspace_id, skip_snapshots=skip_snapshots)
    second_run = await rebuild_portfolio(
        db             = db,
        portfolio_id   = portfolio_id,
        workspace_id   = workspace_id,
        dry_run        = True,
        skip_snapshots = skip_snapshots,
        backup         = False,
    )
    report = compare_against_baseline(baseline, second_run)
    return baseline, report


async def generate_regression_report(
    db:             Session,
    workspace_id:   int,
    portfolio_ids:  list[int],
    skip_snapshots: bool = False,
) -> RegressionReport:
    """Run `run_determinism_check()` across a set of portfolios and summarize.

    Read-only. Produces exactly the four figures Stage 1's Definition of
    Done calls for: portfolio count, replay parity, validator parity, and
    each portfolio's baseline hash.
    """
    entries: list[RegressionReportEntry] = []
    for pid in portfolio_ids:
        baseline, report = await run_determinism_check(
            db, pid, workspace_id, skip_snapshots=skip_snapshots,
        )
        entries.append(RegressionReportEntry(
            portfolio_id         = baseline.portfolio_id,
            portfolio_name        = baseline.portfolio_name,
            baseline_hash          = baseline.content_hash,
            is_bit_identical       = report.is_bit_identical,
            holding_diff_count     = len(report.holding_diffs),
            snapshot_diff_count    = len(report.snapshot_diffs),
            validator_diff_count   = len(report.validator_diffs),
        ))

    bit_identical_count = sum(1 for e in entries if e.is_bit_identical)
    return RegressionReport(
        generated_at              = datetime.now(timezone.utc).isoformat(),
        portfolio_count            = len(entries),
        portfolios_bit_identical   = bit_identical_count,
        portfolios_with_diffs      = len(entries) - bit_identical_count,
        entries                    = tuple(entries),
    )


# ══════════════════════════════════════════════════════════════════════════════
# Durable storage — versioned, outside the operational DB (Migration Principle 7:
# "verification is a deliverable"). Mirrors portfolio_rebuilder.py's own
# `_export_backup()` convention: plain JSON files, not a DB table.
# ══════════════════════════════════════════════════════════════════════════════

def _baseline_path(portfolio_id: int, baseline_dir: str) -> str:
    return os.path.join(baseline_dir, f"portfolio_{portfolio_id}.json")


def save_baseline(baseline: GoldenBaseline, baseline_dir: str = _DEFAULT_BASELINE_DIR) -> str:
    """Write a GoldenBaseline to durable JSON storage. Returns the file path."""
    os.makedirs(baseline_dir, exist_ok=True)
    path = _baseline_path(baseline.portfolio_id, baseline_dir)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(asdict(baseline), fh, indent=2, sort_keys=True, default=str)
    return path


def load_baseline(portfolio_id: int, baseline_dir: str = _DEFAULT_BASELINE_DIR) -> GoldenBaseline | None:
    """Load a previously captured GoldenBaseline. Returns None if none exists."""
    path = _baseline_path(portfolio_id, baseline_dir)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)

    def _triples(v: Any) -> tuple[tuple[str, str, Any], ...]:
        return tuple(tuple(t) for t in v)

    def _pairs(v: Any) -> tuple[tuple[str, str], ...]:
        return tuple(tuple(t) for t in v)

    return GoldenBaseline(
        portfolio_id                  = raw["portfolio_id"],
        portfolio_name                 = raw["portfolio_name"],
        captured_at                    = raw["captured_at"],
        success                        = raw["success"],
        transactions_replayed          = raw["transactions_replayed"],
        effective_transaction_count    = raw["effective_transaction_count"],
        excluded_transaction_count     = raw["excluded_transaction_count"],
        reconstructed_holdings_count   = raw["reconstructed_holdings_count"],
        reconstructed_cash             = raw["reconstructed_cash"],
        snapshots_processed            = raw["snapshots_processed"],
        holdings_truth                 = _triples(raw["holdings_truth"]),
        snapshot_truth                 = _triples(raw["snapshot_truth"]),
        validator_finding_keys         = _pairs(raw["validator_finding_keys"]),
        validator_overall_severity     = raw["validator_overall_severity"],
        content_hash                   = raw["content_hash"],
    )
