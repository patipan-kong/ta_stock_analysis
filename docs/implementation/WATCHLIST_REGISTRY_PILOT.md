# Watchlist Registry Pilot

_M6 Compatibility-Layer Integration, Phase 1 step 2 — the first Registry Adoption milestone: introducing Registry awareness into the Watchlist read path while preserving 100% backwards compatibility. Shipped 2026-07-10._

_Companion documents: [ASSET_REGISTRY.md](../architecture/ASSET_REGISTRY.md) (frozen architecture), [REGISTRY_INTEGRATION_GUIDE.md](../architecture/REGISTRY_INTEGRATION_GUIDE.md) (developer-facing usage guide — see its "Watchlist read path (Phase 1 step 2)" section), [ASSET_REGISTRY_IMPLEMENTATION_PLAN.md](ASSET_REGISTRY_IMPLEMENTATION_PLAN.md) (the M0–M7 epic this pilot is part of), [M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md](M6_REGISTRY_READ_PATH_INTEGRATION_PLAN.md) (the audit that originally scoped this as "Phase 1 step 2," §5)._

Per the pilot brief: this is intentionally a small pilot. Scope was held to `GET /watchlist`, `POST /watchlist`, and their shared helper — Classification Consolidation (M6 §5 Phase 7) and Native Asset Persistence (M5 Track B / M6 Native Integration) were explicitly not started.

---

## 1. Audit — the Watchlist flow before this change

### API entry points

```
GET    /watchlist                    — main.py::list_watchlist
POST   /watchlist                    — main.py::add_watchlist
DELETE /watchlist/{symbol}           — main.py::remove_watchlist
POST   /watchlist/analyze/all        — main.py::analyze_watchlist_60m           (out of scope — analysis pipeline)
POST   /watchlist/analyze/all/stream — main.py::analyze_watchlist_stream        (out of scope — analysis pipeline)
POST   /analyze/watchlist            — main.py::start_watchlist_job             (out of scope — job queue)
```

Only `GET /watchlist` and `POST /watchlist` were in scope; both were audited in full. `DELETE /watchlist/{symbol}` was read but not modified — its response (`{"deleted": symbol}`) has nothing to enrich.

### Service layer

There is no separate Watchlist service module — the CRUD logic lives directly in `main.py`. This is consistent with the rest of the platform's CRUD endpoints (Portfolio holdings follow the same pattern) and is not something this pilot changes.

### Repository layer

`models.database.Watchlist` — `id`, `workspace_id` (FK), `symbol` (String, indexed, not null), `sector` (String, nullable, filled at add-time), `created_at`. Unique constraint on `(workspace_id, symbol)`. No `asset_id` column — this is expected; adding one is M5 Track B / M6 Native Integration territory, explicitly out of this pilot's scope ("do NOT change schema").

### Response model

Both `GET` and `POST` build their response through one shared helper, `main.py::_watchlist_row()`, which assembles a flat dict: `id`, `symbol`, `latest_signal`, `signal_confidence`, `analyzed_at`, `reasoning`, `risks`, `ta_score`, `fa_score`, `target_price`, `upside_pct`, `risk_level`, `sector`, `is_dr`, `parent_symbol`, `upside_reference_price`. `GET /watchlist` returns a `list[dict]`; `POST /watchlist` returns one `dict` of the identical shape. This shared helper is exactly what made a single, consistent change point possible for both endpoints.

### UI consumers

`frontend/lib/api.ts` declares `WatchlistItem` (the TypeScript mirror of `_watchlist_row()`'s shape) and `getWatchlist()` / `addToWatchlist()` / `removeFromWatchlist()`. The sole UI consumer is `frontend/app/watchlist/page.tsx`, which destructures specific known fields (`symbol`, `sector`, `latest_signal`, `analyzed_at`, `ta_score`/`fa_score` via `risk_level`, `upside_pct`, `is_dr`/`parent_symbol`/`upside_reference_price`) for its table, sort, and buy-modal logic. It does not spread or validate the full object shape, so an additive, unread field is inert to it by construction.

### Existing symbol normalization

- `main.py::_resolve_symbol(symbol)` — trim + uppercase, used by `add_watchlist`/`remove_watchlist` to canonicalize the *stored* symbol string. This is Watchlist's own long-standing normalization and was not touched.
- `is_dr_symbol()` / `normalize_dr_symbol()` (`services/data_fetcher.py`) — used inside `list_watchlist` to detect Depository Receipts and look up their parent's price for the upside-percentage calculation. This is a DR-specific classification helper, not an identity-matching shim, and was not touched.

### Duplicated matching logic

**None found.** Unlike the five `.BK`-variant shims Phase 2 (2026-07-09) retired from `basket_simulation.py`, `execution_plan.py`, `position_sizing.py`, `allocation_engine.py`, and `idea_review.py`, the Watchlist read path never hand-rolled a bare/`.BK` symbol-matching heuristic — every lookup (`AnalysisCache`, `AgentCache`) is by exact stored-symbol string, and there is nothing to fuzzy-match against. This is precisely what made Watchlist the intended lowest-stakes pilot consumer named in the original M6 read-path plan (§5, Phase 1, step 2): there was no existing logic to risk breaking, only a place to add new, additive information.

---

## 2. Implementation Summary

### What changed

- `backend/main.py`
  - New helper `_registry_view_dict(result)` — projects a `registry_lookup.AssetView`/`Unresolved` result into the JSON shape `{"resolved": True, "asset_id", "canonical_symbol", "market", "exchange"}` or `{"resolved": False, "reason"}`. Identical shape to `services/registry_recommendation_context.py`'s `_view_to_dict`/`_unresolved_to_dict` (Phase 3 step 7), reused by convention rather than reinvented (ENGINEERING_PRINCIPLES.md "Shared Schemas").
  - `_watchlist_row()` gained an optional `registry_view` parameter and one new output key, `"registry"`, defaulting to `{"resolved": False, "reason": "not evaluated"}` when not supplied.
  - `list_watchlist()` (`GET /watchlist`) calls `registry_lookup.resolve_many(db, symbols)` once for the whole watchlist (batched, cache-backed — no N+1), wrapped in `try/except` with a logged warning on failure.
  - `add_watchlist()` (`POST /watchlist`) calls `registry_lookup.resolve_asset(db, symbol)` once for the single symbol being added, same failure handling, so its response carries the identical `"registry"` shape as `GET /watchlist` (both already share `_watchlist_row()`).
- `frontend/lib/api.ts` — `WatchlistItem` gained an optional `registry?: WatchlistRegistryView` field; new `WatchlistRegistryView` discriminated-union type mirrors the backend shape exactly.
- `backend/tests/test_watchlist_registry.py` — new, 10 tests (detailed in §4).
- Documentation: this file, `docs/architecture/REGISTRY_INTEGRATION_GUIDE.md` (new "Watchlist read path (Phase 1 step 2)" section + status banner), `docs/implementation/ASSET_REGISTRY_IMPLEMENTATION_PLAN.md` (Compatibility-Layer status line + new Changelog entry).

### What did not change

- No schema migration. `Watchlist` gained no columns.
- No existing field in either endpoint's response was renamed, removed, or reinterpreted.
- No Portfolio, Optimizer, Recommendation, Analytics, Execution, Ledger, or Replay code was touched.
- `DELETE /watchlist/{symbol}` was not touched.
- Watchlist's own `_resolve_symbol()` normalization (trim/uppercase for the *stored* symbol) is unchanged — Registry resolution is a read-time annotation layered on top, not a replacement for how symbols are stored or deduplicated in the `Watchlist` table.

---

## 3. Compatibility Notes

- **Additive only.** `"registry"` is a new key on an existing dict; every previously-existing key is present with an unchanged value regardless of Registry outcome (verified by `test_existing_response_fields_unchanged_regardless_of_registry_status`).
- **Never fails the request.** A symbol the Registry cannot resolve returns `{"resolved": False, "reason": "..."}` — the honest, first-class `Unresolved` outcome `resolve_asset()`/`resolve_many()` already return, never an exception. A total Registry failure (e.g. a bug in the resolver, a DB issue scoped to Registry tables) is caught at the call site, logged as a warning, and degrades every entry to `{"resolved": False, "reason": "not evaluated"}` — the request still succeeds (`test_registry_failure_degrades_to_not_evaluated_without_failing_request`, `test_add_watchlist_degrades_gracefully_when_registry_resolution_raises`).
- **Unresolved assets keep working exactly as before.** A watchlist entry with no Registry match still returns every field it always did (signal, score, sector, price data) — the pilot brief's requirement that unresolved entries "continue to work" and "never fail the request because Registry resolution fails" holds by construction, since nothing about the pre-existing computation path (`AnalysisCache`/`AgentCache`/price lookups) depends on Registry resolution succeeding.
- **Frontend is untouched at runtime.** The new `registry` field is optional in the TypeScript type and unread by the current UI — no visual or behavioral change ships with this pilot.

---

## 4. Test Coverage

`backend/tests/test_watchlist_registry.py`, 10 tests, all passing:

| Test | Proves |
|---|---|
| `test_resolved_entry_carries_additive_registry_metadata` | A minted, current asset resolves with full metadata |
| `test_unresolved_entry_falls_back_without_failing_request` | An unregistered symbol degrades cleanly, request still succeeds |
| `test_historical_only_alias_is_honestly_unresolved_not_guessed` | A superseded (historical-only, no current claimant) identifier is reported unresolved, never guessed (ASSET_REGISTRY.md §4) |
| `test_recycled_symbol_resolves_to_current_holder_not_the_original_asset` | A symbol value claimed by two different assets over time ("duplicate aliases" / ticker recycling) resolves to the *current* holder, never the stale original |
| `test_mixed_watchlist_resolves_each_entry_independently` | A single `GET /watchlist` call with resolved + historical-alias + never-seen entries handles each independently, no cross-contamination |
| `test_existing_response_fields_unchanged_regardless_of_registry_status` | Every pre-existing response key is present, unchanged, for both a resolved and an unresolved entry — the API-compatibility regression proof |
| `test_empty_watchlist_returns_empty_list` | Baseline empty-list behavior is unaffected |
| `test_registry_failure_degrades_to_not_evaluated_without_failing_request` | A total `resolve_many()` failure degrades gracefully (`GET`) |
| `test_add_watchlist_returns_registry_metadata_for_new_entry` | `POST /watchlist` carries the identical `"registry"` shape as `GET` |
| `test_add_watchlist_degrades_gracefully_when_registry_resolution_raises` | A total `resolve_asset()` failure degrades gracefully (`POST`) |

Regression: full backend suite run before and after via `git stash` isolation. **Byte-identical 58-failure set in both runs** (all pre-existing, none in watchlist/registry modules); passed count up by exactly the 10 new tests (1063 → 1073); 32 skipped unchanged both times.

---

## 5. Performance Considerations

- `list_watchlist()` resolves the entire watchlist in one `resolve_many()` call rather than one `resolve_asset()` call per row — `resolve_many()` reuses the shared in-process TTL cache (default 300s, 2048 entries, LRU-evicted; see `services/registry_lookup.py`), so a symbol repeated across requests within the TTL window is never re-resolved. This mirrors the existing `AgentCache`/regime-detector caching convention already used elsewhere in this codebase.
- No new database queries were added beyond what `resolve_asset()`/`resolve_many()` already perform internally (a `find_current_identifier`-style lookup per uncached symbol) — no join was added against `Watchlist` itself.
- `add_watchlist()` resolves exactly one symbol, an O(1) addition to an endpoint that already performs a sector lookup (`_fetch_sector`, which can itself hit yfinance) — the Registry lookup is not the dominant cost on that path.
- No caching decisions were introduced by this pilot; it consumes the cache `registry_lookup.py` already ships with, unmodified.

---

## 6. Future Adoption Opportunities

Named here as candidates, not started (per the pilot brief's explicit "stop after the Watchlist pilot" instruction):

- **Frontend display.** `frontend/app/watchlist/page.tsx` could surface `registry.resolved`/`canonical_symbol` (e.g. a small "unresolved" indicator, or a canonical-symbol tooltip) — purely a UI decision, no backend change required, since the data is already there.
- **Classification Consolidation (M6 §5 Phase 7).** Once `THAI_SECTOR_MAP`/`_get_sector` become Registry-classification-backed, `Watchlist.sector` (currently set once at add-time from the static map / yfinance fallback) could be read from `AssetView.classification["SECTOR"]` instead — out of this pilot's scope, named in the parent plan.
- **`DELETE /watchlist/{symbol}`** was not enriched (its response has nothing to enrich today), but if a richer delete-confirmation payload is ever wanted, the same `registry_lookup.resolve_asset()` call used here would apply directly.
- **Native Asset Persistence (M5 Track B / M6 Native Integration).** Once `Watchlist` itself carries a native `asset_id` column, this pilot's read-time `resolve_asset()`/`resolve_many()` calls become redundant and should be retired in favor of a direct column read — tracked at the epic level, not restated here.

---

## 7. Success Criteria (restated against this pilot)

- ✅ Watchlist successfully consumes the Registry (`GET`/`POST` both resolve every symbol).
- ✅ Existing API compatibility is preserved (regression-tested; byte-identical pre-existing failure set across the full suite).
- ✅ Registry metadata is additive only (new `"registry"` key, nothing else changed).
- ✅ Performance remains acceptable (batched `resolve_many()`, existing TTL cache, no new queries).
- ✅ All tests pass (10 new, 0 regressions).

**Stopped here, as instructed.** Classification Consolidation and Native Asset Persistence were not started.
