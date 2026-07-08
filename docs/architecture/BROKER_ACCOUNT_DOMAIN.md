# Broker Account Domain

_The architectural boundary between real-world brokerage accounts and the platform's canonical accounting model: how the places where assets are held connect to the portfolios that give them meaning — without ever becoming those portfolios._

_This is not a database design, not an API specification, and not an implementation guide. It defines the Broker Account as a domain object: what it owns, how it relates to Portfolio, Cash, and the ledger, and how any number of brokers, accounts, and currencies attach to the platform without changing Portfolio semantics. It is the transaction-side sibling of [PROVIDER_INTERFACE.md](PROVIDER_INTERFACE.md): that document governs witnesses of the **world's data** (prices, calendars, corporate actions); this one governs witnesses of the **user's own actions** (trades, flows, fees). The Market Data Platform imports the world; the Broker Account domain imports the user's own history._

_Read together with [PORTFOLIO_DOMAIN_MODEL.md](PORTFOLIO_DOMAIN_MODEL.md) (the accounting boundary this document defends), [ASSET_REGISTRY.md](ASSET_REGISTRY.md) (the identity authority every imported symbol must pass through), [PLATFORM_EVOLUTION.md](PLATFORM_EVOLUTION.md) (§5, the Universal Input Layer this domain feeds), and [../investment/PORTFOLIO_CALCULATION_RULES.md](../investment/PORTFOLIO_CALCULATION_RULES.md) (the frozen semantics that make truthful import classification matter)._

---

## 1. Philosophy

### Strategy and custody are different facts

A **Portfolio** answers *why*: it is an investment strategy, a policy, and an accounting boundary (PORTFOLIO_DOMAIN_MODEL.md §1). It is a fact about the investor's intent.

A **Broker Account** answers *where*: it is the real-world container in which assets and cash physically sit, and the venue through which orders actually execute. It is a fact about the world's custody arrangements — which institution holds what, under which account number, in which currency, with which settlement conventions.

These two facts vary independently, which is the entire argument for keeping them separate objects. One strategy can span custodians: a Global Equity portfolio funded through a home-market broker for local listings and a foreign broker for everything else is *one* strategy — one benchmark, one policy, one performance story — that happens to execute in two places. One custodian can host several strategies: a single brokerage account holding both a retirement position and short-term trading positions contains *two* intents that deserve two boundaries, two benchmarks, two honest performance numbers. Fuse the objects — make the portfolio *be* the account — and both cases break: the spanning strategy shatters into per-broker fragments that are individually meaningless, and the shared account welds unrelated strategies into one unjudgeable blur.

The platform therefore fixes the roles permanently: **the Portfolio is the logical investment boundary; the Broker Account is a transaction source and a custody fact.** Broker accounts feed the ledger and describe where things sit. They never define what a holding means, what success is, or where an accounting boundary lies. A user thinking "my SCB account" is thinking about custody; the platform thinking "the Thai Equity portfolio" is thinking about strategy — and the domain model's job is to let both thoughts be true at once without either corrupting the other.

### Brokers are witnesses of the user's own history

The deeper symmetry with the rest of the architecture: just as a market-data provider is a witness to the world's prices and never an authority over them (PROVIDER_INTERFACE.md §2), a broker is a witness to the user's transactions and never the authority over the user's investment history. A broker statement is *evidence* — usually excellent evidence — of what happened. The authority is the platform's own ledger (ADR-001), owned by the human, assembled from broker evidence through explicit, validated import. The distinction sounds pedantic until a broker's export omits a fee, restates a dividend, or disappears entirely — at which point it is the difference between a platform that owns its truth and one that borrowed it.

---

## 2. Responsibilities

### What a Broker Account owns

- **Account identity** — a permanent internal identifier for the account, following the platform's universal identity discipline: minted once, never reused, surviving renames, reconnections, and the broker's own account-number changes. External account numbers are evidence mapped to it, exactly as external symbols map to an `asset_id`.
- **Broker metadata** — which institution this is, what kind of account (cash, margin, retirement wrapper), the descriptive facts a human needs to recognize it and the import machinery needs to interpret its dialect.
- **Account currency** — the denomination(s) in which the account holds cash. An account may be single-currency or hold multi-currency balances; either way this is a custody fact recorded here, not an accounting rule (§7).
- **Import history** — the full record of every import ever run against this account: when, through which door (§5), covering which span, yielding which claims, with which outcomes — accepted, deduplicated, quarantined, rejected. Import history is what makes imports repeatable and auditable (§6); it is provenance for the ledger, never a second ledger.
- **Connection status** — how the account currently relates to its broker: manually maintained, file-fed, API-linked, disconnected, or historical (the broker relationship ended). Status describes the *pipe*, and gates only what imports may happen next — never the validity of anything already recorded.
- **Settlement rules** — the account's operational conventions: settlement cycles as this broker actually applies them, currency-of-settlement habits, fee and tax presentation quirks. These inform how the import layer *interprets* this account's evidence; the portfolio's own settlement policy (PORTFOLIO_DOMAIN_MODEL.md §5) remains the rulebook for what the strategy tolerates.

### What a Broker Account must never own

- **The ledger.** Transactions belong to exactly one Portfolio (PORTFOLIO_DOMAIN_MODEL.md §2), full stop. The broker account appears on a ledger event as *provenance* — where this event was learned from and where it settled — never as the event's home. There is no "account ledger" beside the portfolio ledger; that would be a second source of truth, and the platform has named rules against those.
- **Performance.** An account has no benchmark, no strategy, no return that means anything. "How did my IBKR account do?" is a custody-grouped *description* the platform can derive; it is never a *judgment*, because judgment requires a strategy and strategies live in portfolios (the same judge/describe line PORTFOLIO_DOMAIN_MODEL.md §10 draws for Wealth).
- **Asset identity.** Broker symbols are among the weakest identity evidence the platform receives (ASSET_REGISTRY.md §3); they resolve through the Registry like every other external name. No import path lets a broker's spelling mint or move an `asset_id`.
- **Holdings truth.** A broker's reported positions are a *claim* the platform can reconcile against replayed truth (§10) — a valuable audit input, never the balance of record. When broker statement and replayed ledger disagree, the disagreement is surfaced and investigated; the broker's number never silently overwrites the ledger's.
- **Strategy and policy.** An account knows nothing of universes, personas, goals, or benchmarks. The moment account objects start carrying investment intent, the portfolio boundary has leaked into custody — the exact fusion §1 forbids.

---

## 3. Relationship to Portfolio

### Both directions, deliberately

**One Portfolio ← many Broker Accounts: supported.** A strategy is defined by intent, not by custodian, and real strategies routinely require more than one custodian — a local broker for the home market, a foreign broker for overseas listings, a fund platform for the wrapper products. All of it is one portfolio: one ledger, one base currency, one benchmark. The accounts differ only in the provenance they stamp on the events they feed in.

**One Broker Account → many Portfolios: supported.** Real accounts accumulate mixed intent — the retirement core and the tactical experiments sitting under one account number. The platform must not force a false boundary ("one account = one portfolio") that the user's actual strategy contradicts, because a false boundary produces false performance for both halves.

The relationship is therefore **many-to-many — mediated entirely by transaction attribution.** The binding object is never account-to-portfolio as a bulk mapping; it is each *transaction* landing in exactly one portfolio's ledger. An account that serves one portfolio attributes trivially (a standing default). An account that serves several attributes each imported event by declared rules where rules suffice — and by the human where they don't, following the platform's universal pattern: resolve silently when decisive, surface when ambiguous, never guess. An attribution, once confirmed, is recorded and durable, so the same question is never asked twice.

### The architectural reasoning

This design falls out of two commitments already made. First, the ledger rule: *a transaction belongs to exactly one portfolio* — which means attribution must be decided per-event at import time anyway, so per-event attribution is not extra machinery; it is the only machinery. Second, the boundary rule: portfolio membership is a *strategy* fact, and only the owner knows the strategy. A broker cannot say which of your intents a trade served; an account mapping can only *default* the answer. Keeping attribution explicit keeps the human owner of the one fact only the human has.

Two degenerate cases confirm the model rather than strain it. A portfolio with **zero** broker accounts is fully valid — the property portfolio, the manually tracked holding, the pre-import history — because the ledger never required a custodian, only events (the manual-entry proof case, again). And an account whose broker relationship has **ended** keeps its identity and its provenance role forever: the events it once fed remain attributed, replayable, and auditable, exactly as recorded (§8).

---

## 4. Cash Ownership

Cash is where custody and accounting are easiest to conflate, so the boundary is drawn in one sentence: **the broker holds the money; the portfolio owns the meaning of the money.**

- **Cash balances.** The portfolio's cash balance is *derived by replay* from its own ledger — deposits in, proceeds in, purchases out, fees out — like every other piece of portfolio state. The broker's reported cash balance is an external observation: reconciliation evidence (§10), never the balance of record. Where custody detail matters (how much of this portfolio's cash sits at which broker), that is a *location view* over ledger provenance — derived, descriptive, and never independently stored.
- **Deposits and withdrawals.** Money crossing the portfolio boundary from outside is exactly the event class the platform spent an era hardening: external flows, truthfully classified, excluded from performance (the cash-flow-adjusted return rules, the imported-position stripping, the non-performance inflow discipline — all recorded in the decision log). The broker account is *where* the deposit landed; the DEPOSIT event and its classification belong to the portfolio ledger.
- **Transfers.** The classification turns on boundaries, not on motion. Cash moving between two accounts that serve the *same* portfolio never touches portfolio accounting — no flow occurred at the boundary; only custody location changed, and inventing a deposit out of a location change is precisely the phantom-flow error the platform has already diagnosed and repaired once. Cash moving between accounts serving *different* portfolios is a genuine boundary crossing: explicit, mirrored withdrawal-and-deposit events on both ledgers — the same discipline PORTFOLIO_DOMAIN_MODEL.md §2 demands for all inter-portfolio movement, regardless of whether one custodian or two were involved.
- **FX balances.** An account holding cash in several currencies holds several custody facts. Each portfolio's ledger records its cash events in their actual currencies; base-currency views are translation at read time using canonical FX observations (§7). A currency *conversion* — real money actually exchanged — is a ledger event; a currency *translation* for reporting never is.
- **Settlement cash.** Unsettled proceeds and pending obligations are timing states of recorded events, not separate money. The account's settlement conventions (§2) tell the import layer *when* cash actually moved; the portfolio's settlement policy tells validation whether unsettled cash may fund the next purchase. Neither invents a transaction.

The through-line: every cash rule above is the portfolio-boundary discipline applied to custody. Cash has one authoritative history (the ledger), one truthful classifier (does this cross a boundary, and as what?), and any number of custody locations — and location is provenance, never meaning.

---

## 5. Transaction Sources

The platform learns about transactions through many doors; it records them in exactly one vocabulary. This is "many doors, one hallway" (PLATFORM_EVOLUTION.md §5) applied to the user's own history.

### The doors — how the platform learns

- **CSV Import** — a broker's exported statement or history file, in whatever dialect that broker writes.
- **Broker API** — a programmatic feed of the same facts, fresher and more structured, but architecturally identical: another door.
- **Manual Entry** — the user states what happened. The zero-broker proof case: a door that requires no institution at all, and the reason the ledger's design never depended on brokers existing.
- **Corporate Action** — an event the platform learns from the data side (a split, a merger) that implies ledger consequences for affected holdings — entering as a *claim for confirmation*, adjudicated with Registry help (ASSET_REGISTRY.md §7), never auto-applied to the ledger.
- **Cash Adjustment** — an explicit, signed, human-authorized correction event: the platform's recorded way of saying "the ledger was missing this" without ever editing what the ledger already says.

### The vocabulary — what the platform records

Whatever the door, what lands in the ledger is drawn from the universal transaction vocabulary (UNIVERSAL_ASSET_ARCHITECTURE.md §9): BUY, SELL, TRANSFER; DIVIDEND, INTEREST; FEE, TAX, FX conversion; deposits and withdrawals as boundary flows. A dividend is a DIVIDEND whether it arrived by CSV, by API, or by typing — **the door is provenance, never semantics.** No event type exists that means "the kind of buy that came from broker X"; the moment the vocabulary forks by source, every consumer of the ledger inherits the fork.

### The hallway — how a claim becomes canon

Every door produces the same thing: a **claim** — "this source says this happened," carrying whatever identifiers, amounts, and dates the source knew. Every claim then walks the same pipeline: **identity resolution** (the claim's symbol becomes an `asset_id` through the Registry, or the claim waits — no ledger event ever records a raw broker symbol); **normalization** (the source's dialect of dates, signs, fees, and currency conventions becomes the platform's one shape — inside the import boundary, exactly as provider adapters normalize inside theirs); **classification** (the claim is truthfully typed — purchase or transfer-in, income or return of capital, boundary flow or internal movement — the step this platform's accounting-correctness era proved is where honesty lives); **validation** (portfolio attribution §3, universe and policy checks, duplicate detection §6); and finally **recording** — one immutable ledger event, stamped with full provenance: source door, broker account, import batch, original claim. Same hallway for every door, which is why adding a door never changes the ledger's meaning.

---

## 6. Import Philosophy

Importing is not appending. Importing is **reconciling a source's account of history with the ledger's** — asking "what does the ledger not yet know?", never "what can I add?" Every rule below is that stance applied to a specific hazard.

- **Repeat imports are safe by design.** The same file imported twice, the same API span fetched twice, overlapping statements from adjacent months — all must converge on the same ledger, with the repeats recognized and set aside. Idempotency is not a courtesy; it is what makes import *usable*, because real users re-download files, re-run syncs, and cannot be expected to remember coverage boundaries. An import machinery that duplicates on repeat teaches users to fear the import button.
- **Duplicate detection happens at the boundary.** Each claim is checked against recorded events by content identity — the platform already runs exactly this concept as transaction fingerprinting in its ledger validation and repair machinery, where duplicate-fingerprint findings are among the few things trusted for auto-repair. The architectural point is placement: detection belongs at import time, *before* recording, because the ledger is immutable and prevention is the only cheap correction. The downstream validator remains as the audit net, not the primary defense.
- **Corrections never edit; they append.** When a broker restates history — a corrected dividend, a reclassified fee — the ledger's existing record is not wrong to have existed: it faithfully recorded what was then known. The correction enters as a new, explicit, provenance-tagged event, in the discipline the platform has already built twice over (signed manual adjustments; the repair-overlay machinery that adjusts *replay* without ever touching recorded rows). History is append-only even when history was mistaken.
- **Historical imports are ordinary imports.** Backfilling years of past statements uses the same pipeline with the same guarantees, resting on the ordering rule the platform already settled (ADR-003): the *transaction date* governs where an event lands in replay; the *recording date* governs when the platform learned it. A backfilled 2022 trade replays in 2022 — and the fact it was imported in 2027 remains honestly visible in provenance.
- **Partial imports fail loudly, never silently.** An import that processed 180 of 200 rows reports exactly that: which claims were accepted, which were duplicates, which are quarantined pending identity resolution or attribution, which were rejected and why. The most dangerous import is the one that *looks* complete — the same reasoning PROVIDER_INTERFACE.md §8 applies to partial data, applied to the door where the user's own money is on the line. Quarantine is a first-class outcome: a claim the platform cannot yet honestly record waits, visibly, rather than being guessed into the ledger or dropped on the floor.

The principle underneath all five: **the import layer's product is not transactions — it is confidence.** A ledger the user trusts absolutely is worth more than any single convenience, and every idempotency rule exists to make "run the import again" a perfectly safe, perfectly boring operation.

---

## 7. Multi Currency

Four currency concepts, four owners, no blending:

- **Broker account currency** — the denomination(s) of the account's cash. A custody fact, owned by the Broker Account object (§2). It constrains what the account can *hold*, and implies nothing about how anything is *reported*.
- **Settlement currency** — the currency a given trade actually settled in, which may differ from both the asset's native currency and the account's main balance (a foreign listing settled from a multi-currency balance). A per-transaction fact, recorded on the ledger event, because replay must reproduce what actually moved.
- **Asset currency** — the instrument's native pricing and settlement currency, owned by the Asset Registry as part of canonical identity (ASSET_REGISTRY.md §8). No import path overrides it; a claim whose currency contradicts the Registry's is a validation finding, not a shrug.
- **Portfolio base currency** — the unit in which this portfolio's NAV, returns, and benchmark comparisons are expressed: exactly one per portfolio, chosen deliberately, changed only as an explicit recorded event (PORTFOLIO_DOMAIN_MODEL.md §3).

**FX conversion ownership** then has one clean split. FX *rates* are canonical observations owned by the Market Data Platform — no broker adapter, import routine, or engine ever invents, caches, or improvises a rate. FX *conversion events* — real money actually exchanged, with the actual rate obtained and actual fees paid — are ledger transactions like any other, recorded at their true executed terms (which will differ from the canonical mid-market observation; that difference is real cost, honestly kept). FX *translation* — expressing multi-currency truth in base currency for reporting — is computed at read time from canonical rates and never stored as if it were a transaction, because a translation is an opinion of the moment and the ledger records only facts.

The test for any future multi-currency question: identify which of the four concepts it touches, and the owner answers it. A question that seems to need two owners at once is two questions.

---

## 8. Portfolio Independence

Custody arrangements change constantly over an investing life. The domain model's guarantee: **no custody event can touch portfolio identity, history, or meaning.**

- **Changing brokers.** A new account object is created; imports begin flowing through it; the old account's connection status ends. The portfolio notices nothing: same `portfolio_id`, same ledger, same benchmark, same performance story — with new provenance on new events.
- **Moving assets.** An in-kind transfer between custodians within one portfolio is recorded as what it economically is: the same holdings, held elsewhere. No sale occurred, no cost basis reset, no performance event, no boundary flow — the mirror of §4's transfer rule for cash. The temptation to model it as sell-and-rebuy is a classification lie with tax-shaped consequences, and truthful classification is the import layer's first duty.
- **Account migration.** A broker renumbers, restructures, or merges accounts on its side: evidence mapped to the platform's permanent account identity is updated; the identity itself — and every ledger event stamped with it — stands. The same move the Asset Registry makes when an exchange renames a ticker, applied to accounts.
- **Broker shutdown.** The terminal proof, exactly parallel to provider retirement (PROVIDER_INTERFACE.md §10): the account becomes historical, imports cease, and *everything already learned through it remains* — attributed, replayable, auditable, forever. A broker's death removes a door; it cannot remove a single fact that walked through the door while it stood.

The reason all four hold is structural, not disciplinary: the portfolio's state is derived by replaying *its own ledger*, and the ledger records economic events with custody as provenance. Since no custody fact participates in replay arithmetic, no custody change can alter replayed truth. Brokers live entirely in the provenance layer — visible, honest, and load-free.

---

## 9. Future Integrations

The roadmap's ambitions span the full range of shapes: international brokerages, home-market banks and securities arms, fund platforms, streaming order feeds, open-banking cash visibility. The architecture absorbs all of them with the move it has now made four times — **adapters at the boundary, capabilities over names, one canonical hallway behind.**

- **One adapter per institution.** Each broker's dialect — its file layouts, its API's shape, its sign conventions, its fee presentation — is absorbed by one adapter whose entire job is producing canonical claims (§5). The dialect dies at the adapter, exactly as vendor dialects die at the Provider Interface. Integrating a new broker *is* writing its adapter; nothing else changes, because nothing else ever knew brokers differ.
- **Capabilities, not broker names.** Adapters declare what their institution can supply — statement files, transaction feeds, position claims, cash balances, streaming updates — and the import machinery routes by declaration, never by `if broker == ...`. A new institution is new rows in a table the consuming machinery already reads (the same argument, verbatim, as PROVIDER_INTERFACE.md §5 — because it is the same problem).
- **The two-doors split holds.** One institution may be *both* a market-data source and a transaction source. These remain two doors into two pipelines — its price observations flow through the Provider Interface into the Market Data Platform; its transaction claims flow through broker import into portfolio ledgers — even when one real-world connection serves both (the split MARKET_DATA_PLATFORM.md §13 already reserved). Fusing the doors because the vendor is one company would couple the platform's two most important boundaries to a vendor's org chart.
- **Streaming changes tempo, not architecture.** A pushed execution report is a claim arriving seconds after the event instead of days — same claim shape, same hallway, same idempotency (a stream replay or reconnect re-delivers events; fingerprint dedup makes that a non-event, §6). Freshness improves; semantics are untouched.
- **Open Banking is the cash-side door.** Bank-account visibility feeds cash claims — balances as reconciliation evidence, flows as candidate boundary events (deposits, withdrawals) for classification. It slots in as one more door with one more dialect, valuable precisely because the cash rules (§4) were written without assuming any particular way of learning about cash.

What never changes, no matter how many integrations arrive: the claim shape, the hallway, the ledger vocabulary, the attribution rules, and the portfolio boundary. Integration effort scales with the number of dialects; the platform's meaning does not scale at all — that is the entire point of the design.

---

## 10. Relationship with Replay Engine

The Replay Engine is the accounting authority: portfolio state is whatever deterministic replay of the canonical ledger says it is. Its relationship to the broker domain is defined by three orderings:

- **Replay consumes canonical transactions only.** Not statements, not claims, not import batches, not broker balances — ledger events, already resolved to `asset_id`s, already classified, already attributed. Everything broker-flavored was consumed and discharged *before* the ledger was written; by the time replay runs, there is nothing broker-shaped left to see.
- **Replay never depends on brokers.** No replay step contacts a broker, parses a dialect, or branches on provenance. A portfolio replays identically whether its events arrived by API, CSV, or hand — and replays identically after every broker involved has ceased to exist, because settled ledger truth (like settled price history — MARKET_DATA_PLATFORM.md §12) is a permanent platform record, not a cached vendor answer. Broker unavailability can delay *learning about new* events; it cannot alter, block, or re-answer anything already recorded.
- **Import completes before accounting begins.** The pipeline order is absolute: claim → resolution → classification → validation → ledger → replay. There is no path by which raw broker data reaches accounting, and no "provisional replay" over unvalidated claims — a quarantined claim (§6) is invisible to replay until it is honestly recordable, because a deterministic engine fed maybes produces authoritative-looking maybes.

One deliberate back-channel exists, and it flows the safe direction: **reconciliation.** A broker's statement of current positions and cash can be compared *against* replayed truth as an audit — the broker as witness, testifying about the ledger's completeness. Agreement builds confidence; disagreement is surfaced as a finding (a missing event? a misclassification? a broker error?) and investigated through the platform's read-only audit discipline. What reconciliation never does is write: the broker's number is never patched into portfolio state, because the moment an external balance can overwrite replayed truth, the ledger has quietly stopped being the source of truth — and everything downstream of ADR-001 stops being trustworthy with it.

---

## 11. Design Principles

1. **Portfolio owns investment history; the broker owns only execution custody.** Strategy, boundary, and meaning live in the portfolio; the account is where things sat and how orders happened.
2. **A Broker Account is a transaction source and a custody fact — never an accounting boundary.** No account ledger, no account performance, no account strategy.
3. **Transactions are canonical.** One vocabulary, whatever the door; the door is provenance, never semantics. No ledger event records a raw broker symbol, dialect, or shape.
4. **Attribution is per-event, and the human owns ambiguity.** Accounts and portfolios relate many-to-many; each transaction lands in exactly one ledger — by durable rule where decisive, by the owner's confirmed word where not.
5. **Cash meaning belongs to the boundary.** Flows are classified by whether they cross a portfolio boundary — never by the motion of money between custody locations. Location changes are provenance; boundary crossings are mirrored ledger events.
6. **Imports are repeatable.** Re-running any import is safe and boring: duplicates recognized at the boundary by content identity, corrections appended never edited, partial results confessed never disguised.
7. **The ledger is authority; the broker is a witness.** Statements reconcile against replayed truth and may accuse the ledger of incompleteness — they never overwrite it.
8. **Brokers are replaceable.** Changing, migrating, or losing a broker is a provenance event: identity, history, and performance are untouched, because no custody fact participates in replay.
9. **Adapters isolate change; capabilities route it.** One adapter per institution's dialect, declarations instead of name-branching, and a hallway that never learns how many doors exist.
10. **Replay is broker-independent, permanently.** Import completes before accounting begins; settled ledger truth outlives every institution that ever contributed to it.

---

## Related Documents

- [PORTFOLIO_DOMAIN_MODEL.md](PORTFOLIO_DOMAIN_MODEL.md) — the accounting boundary broker accounts feed and must never become
- [PROVIDER_INTERFACE.md](PROVIDER_INTERFACE.md) — the data-side sibling boundary: witnesses of the world, as this domain's brokers are witnesses of the user
- [ASSET_REGISTRY.md](ASSET_REGISTRY.md) — the identity authority every imported symbol resolves through before touching a ledger
- [MARKET_DATA_PLATFORM.md](MARKET_DATA_PLATFORM.md) — canonical observations, FX rates, and the two-doors split for institutions that are both broker and data source
- [PLATFORM_EVOLUTION.md](PLATFORM_EVOLUTION.md) — §5's Universal Input Layer, of which broker import is the transaction-side realization
- [../investment/PORTFOLIO_CALCULATION_RULES.md](../investment/PORTFOLIO_CALCULATION_RULES.md) — the frozen accounting semantics that truthful import classification protects
- [../engineering/DECISION_LOG.md](../engineering/DECISION_LOG.md) — the recorded lessons (cash-flow adjustment, imported-position stripping, phantom flows, transaction fingerprinting) this domain generalizes
