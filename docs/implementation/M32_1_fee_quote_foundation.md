# M32.1 — Versioned FeeQuote Foundation and Ledger Parity

**Date:** 2026-07-14

**Status:** Implemented; transaction posting parity preserved

**Rollout:** Current transaction writes continue through the explicitly named
legacy compatibility selector. The facts-backed quote interface is available
for later planning work but is not connected to an execution plan, optimizer,
evaluation, or frontend path.

## 1. Scope

M32.1 establishes immutable, versioned fee schedules and quotes, separates
schedule selection from arithmetic, and makes current BUY/SELL posting share
the same pure Decimal calculator that future planners can call. It does not
change planning, funding, transaction admission, M31 cutover mode, persistence
schema, or public response shape.

The implementation is split between:

- `backend/services/broker_fees.py`: contracts, schedule registry,
  facts-backed selection, unavailable results, and pure arithmetic;
- `backend/services/broker_fees_compat.py`: the isolated pre-M32 raw-symbol
  selector required for unresolved transaction parity;
- `backend/services/portfolio_transactions.py`: posting-time quote consumption
  for BUY and SELL.

The existing admin recalculation route continues to call `calc_fees()`, whose
implementation now delegates to the same pure component calculator.

## 2. Contracts

### FeeSchedule

`FeeSchedule` is a frozen dataclass containing schedule ID/version, optional
effective date, percentage rules for commission/trading/clearing/VAT, explicit
rounding rules, known currency/applicability metadata, and provenance.

`effective_from` is optional because the legacy module constants do not carry
an authoritative historical effective date. The built-in schedules are
version `1`. `SET_STANDARD` and `DR_STANDARD` are THB schedules with the exact
existing rates. `FREE` remains for explicit simulation/test use and has no
inferred currency.

`FeeProfile` remains a backward-compatible frozen input. It now carries
optional version, effective-date, currency, and provenance metadata without
breaking existing four-rate constructors. A profile is projected to a
`FeeSchedule`; no database schedule or broker-account model was added.

### FeeQuote

`FeeQuote` is a frozen contract with version `1`:

- `QUOTED` contains exact Decimal quantity, unit price, gross, costs, and signed
  net cash effect;
- `UNAVAILABLE` contains `None` for every quantity/price/monetary field and
  schedule identity, never zero or a default SET estimate;
- BUY cash effect is negative and SELL cash effect is positive;
- schedule ID/version, quote/effective times, warnings, and provenance remain
  attached;
- `quote_ref` is deterministic over contract, schedule/version, side,
  normalized quantity/price, currency, and effective time. Observation time is
  deliberately excluded;
- `to_dict()` serializes Decimal values as strings. Current transaction APIs do
  not expose this representation in M32.1.

Typed unavailable reasons are `IDENTITY_UNKNOWN`, `IDENTITY_AMBIGUOUS`,
`NOT_TRADABLE`, `REGISTRY_FAILURE`, `MISSING_FEE_SCHEDULE`, and
`MISSING_ACCOUNT_CONTEXT`.

## 3. Pure formula and rounding

`calculate_fee_components()` is the sole fee-equation implementation:

```text
gross = quantity × unit_price

commission   = round_4(gross × commission_rate)
trading_fee  = round_4(gross × trading_fee_rate)
clearing_fee = round_4(gross × clearing_fee_rate)

pre_vat_cost = commission + trading_fee + clearing_fee
taxes        = round_4(pre_vat_cost × vat_rate)
total_cost   = pre_vat_cost + taxes

BUY  net_cash_effect = -(gross + total_cost)
SELL net_cash_effect =   gross - total_cost
```

Each component uses quantum `0.0001` and `ROUND_HALF_UP`. VAT uses already
rounded components, matching the prior implementation. The quote calculator
receives timestamps from its caller and performs no ORM, database, network,
resolver, environment, or clock access. `calc_fees(gross, profile)` remains as
a thin adapter over the shared calculator.

For gross THB 10,000 under SET/DR version 1:

| Component | Exact Decimal |
|---|---:|
| Commission | 15.0000 |
| Trading fee | 0.6000 |
| Clearing fee | 0.1000 |
| VAT | 1.0990 |
| Total cost | 16.7990 |
| BUY net cash effect | -10016.7990 |
| SELL net cash effect | 9983.2010 |

## 4. Schedule-selection boundary

`select_fee_schedule()` consumes `ExecutionInstrumentFacts`, side, effective
time, and optional explicit schedule/account context. It never inspects the
requested symbol.

- Registry `RESOLVED + TRADABLE`, exchange `SET`, currency `THB`, and form
  `EQUITY`, `ETF`, or `OTHER` selects `SET_STANDARD`.
- Registry `DEPOSITARY_RECEIPT`, exchange `SET`, and currency `THB` selects
  `DR_STANDARD`. DR form can only come from M31's authoritative
  `DEPOSITARY_RECEIPT_OF` relationship adapter.
- An explicit schedule may be used only after facts establish a resolved,
  tradable instrument.
- Unknown, ambiguous, non-tradable/reference, and Registry-failure facts return
  typed unavailable results.
- Resolved venues/currencies with no registered schedule return
  `MISSING_FEE_SCHEDULE`, not SET or zero costs.

No unsupported broker, account, venue, currency, FX, tier, minimum, cap, or
effective-date evidence was invented. `MISSING_ACCOUNT_CONTEXT` is vocabulary
for a future account-dependent schedule; no current schedule requires it.

## 5. Compatibility adapter

`broker_fees_compat.py` contains the one preserved raw-symbol DR regex and the
old fallback-to-SET behavior. It is explicitly non-authoritative and emits a
warning/provenance marker on each non-overridden compatibility quote.

Current BUY/SELL posting calls `quote_transaction_fee_compat()` because M31
Registry coverage remains incomplete. A DR-shaped unresolved symbol still
selects `DR_STANDARD`; every other unresolved/raw symbol still selects
`SET_STANDARD`. This path cannot synthesize M31 facts and is not available
through `quote_fee_for_instrument()`.

The public `resolve_fee_profile(symbol)` name remains as a compatibility shim
for existing callers. New planning work must use the facts-backed selector.

## 6. Profile registry consistency

Previously `register_profile()` updated `_PROFILES`, while automatic resolution
returned module constants and ignored replacements. M32.1 now keeps profile
and schedule registries coherent:

- `register_profile()` replaces the profile and its schedule projection;
- `register_fee_schedule()` replaces the schedule and its profile projection;
- compatibility resolution fetches the selected ID through the registry.

Focused verification replaces registered `SET_STANDARD`, proves automatic
resolution and compatibility quoting observe the new rate/version, and then
restores the built-in profile.

## 7. Transaction and ledger parity

BUY and SELL obtain a posting-time quote before mutation and project it into
the existing `FeeBreakdown`. They preserve:

- `Transaction.fees = commission + trading_fee + clearing_fee`;
- `Transaction.taxes = VAT`;
- BUY `Transaction.total_amount = gross + total_cost`;
- SELL `Transaction.total_amount = gross - total_cost`;
- cash mutation, fee-inclusive BUY cost basis, SELL realized P&L, and existing
  six-decimal Float persistence conversion;
- all existing response fields/types, including `fee_profile` and
  `fee_breakdown`.

No `FeeQuote`, `quote_ref`, or schedule version is persisted or returned.
`portfolio_rebuilder._apply_transaction()` still reads persisted net
`CanonicalTransaction.total_amount` and does not recalculate fees.

## 8. Historical recalculation limitation

`POST /admin/recalculate-cost-basis` was not redesigned or removed. It still
selects the current compatibility profile, but its `calc_fees()` calls now use
the shared pure formula. This adds no rewrite behavior and preserves output.

The endpoint remains an unversioned historical-mutation risk: it can rewrite
historical fee/tax splits, cost basis, realized-P&L notes, and snapshots using
the profile registered at invocation time. M32.1 does not solve immutable
historical fee governance. Before versions diverge, a later decision must
retire, constrain, or make the endpoint select the historical schedule.

## 9. Minimal collection repair

`portfolio_transactions.py` already referenced Stage R1 runtime consultation
types/predicates but omitted their imports. This caused collection to fail at
the `RuntimeConsultationLog` return annotation. M32.1 added only the missing
imports from the existing capability/runtime modules; no branch, predicate,
timing, finding, or consultation behavior changed.

Pre-edit reproduction:

```text
tests/test_fee_accounting.py collection error
NameError: name 'RuntimeConsultationLog' is not defined
portfolio_transactions.py:107
```

## 10. Future M32.2 integration

M32.2 may batch-resolve facts, determine priced/rounded leg inputs, and call
`quote_fee_for_instrument()`. It must treat `UNAVAILABLE` as incomplete
planning evidence, not a free trade. No planner should call
`resolve_fee_profile()` or import `broker_fees_compat.py`.

Remaining foundations include authoritative quantities, lot/fractional rules,
timestamped prices, portfolio/base currency and FX policy, cash-floor policy,
schedule governance/coverage, and a frozen canonical plan projection. M31
remains `LEGACY_FALLBACK`; M32.1 does not enable M31 enforcement or an
execution-plan projection mode.

## 11. Explicit non-goals

- no canonical execution plan or projection-mode activation;
- no optimizer, funding, `execution_plan.py`, evaluation, or frontend change;
- no quantity derivation, lot/fractional rounding, price freshness, FX, or base
  portfolio currency;
- no schema, migration, persisted quote, broker account, or ExecutionIntent;
- no M31 enforcement or compatibility deletion;
- no historical fee-governance redesign;
- no commit or push.

## 12. Verification

Verification completed with these results:

- focused M32.1 plus existing fee/accounting: **58 passed**;
- transaction, canonicalization, write-ID, and replay/rebuilder group excluding
  the separately reported stale capability-shadow case: **198 passed**;
- M31 facts, penalty consumer, eligibility, preparation/remediation, and
  Registry lookup group: **88 passed**;
- optimizer/execution/evaluation group: **91 passed, 4 pre-existing failures**;
- transaction capability-shadow file: **9 passed, 1 pre-existing failure**;
- targeted Python syntax compilation: passed;
- `git diff --check`: passed;
- explicit trailing-whitespace scan of new files: passed.

The four optimizer failures are unchanged stale calls in
`backend/tests/test_optimizer_pipeline.py`:

1. `test_consensus_rebalance_high_confidence`
2. `test_consensus_no_action_low_score`
3. `test_consensus_l1_parse_failure_propagation`
4. `test_consensus_critical_flag_forces_rebalance`

Each calls `_consensus_engine(l2, l3)` after production gained a required
leading argument. No optimizer file changed in M32.1.

The separate capability-shadow failure is
`backend/tests/test_portfolio_transactions_capability_shadow.py::test_execute_buy_unaffected_by_capability_mismatch`.
It expects `execute_buy()` to emit a
`RUNTIME_TRANSACTION_QUANTITY_VALUATION` log, but baseline `HEAD` contains no
BUY call to `_log_runtime_consultation()` (only the DIVIDEND call exists).
Adding that runtime call would be unrelated behavior, so M32.1 leaves it
unchanged. Before the minimal import repair, this file and other transaction
tests could not collect because of the `RuntimeConsultationLog` NameError.

Warnings are pre-existing SQLAlchemy, naive-UTC datetime, pandas, event-loop,
and related test warnings. No new M32.1 test failed.
