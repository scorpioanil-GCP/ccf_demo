# Findings — cp-03-canonical

Findings raised while authoring this successor against the current SDK surface
(`CP14-F-22`, Dave, 2026-09-14). Each is adjudicated under `D-IMPL-315`: a richer
or different canonical path is a finding to adjudicate, never a licence to edit
the example. The question asked of every one is whether the behavior is
**legitimate SDK semantics** or an **actual mismatch**, with the basis stated.
Findings are raised, not resolved: every one below is Dave's to rule on.

---

## `CP03C-F-01` — the governed path records `from_entity_freshness` and computes `from_decision`

**Status: OPEN — SDK. Raised, not repaired. The serving half of the declaration
is held by this product's own declared gate; the expiry half is quarantined as
`OFC-G07` (`xfail(strict=True)`) and turns red the day the SDK honors it.**

### What was measured

`ccf_config.yaml` declares `ttl_anchor: from_entity_freshness`, as the
specimen did. The served contract carries `ttl_anchor="from_entity_freshness"`
and `expires_at = 2026-10-07T12:00:00+00:00` for a question asked at
`2026-09-07T12:00:00+00:00` whose freshest filing is `2026-08-10` — that is
`asked_at + 30 d`, not `2026-08-10T00:00Z + 30 d = 2026-09-09T00:00Z`.

The reason is structural, not a defect of this tree: `GovernedResolver`
computes `expires_at = decided_at + product_ttl_seconds` on every non-composite
branch (`src/ccf/products/resolver.py`, the candidate construction) and passes
`ttl_anchor=registered.ttl_anchor` through as a recorded field. Nothing in
`src/ccf` reads the anchor to compute anything: `grep -rn ttl_anchor src/ccf`
finds the type, the two contract fields, the artifact field and two
pass-throughs. `cp-04-canonical` declares the same anchor and is subject to the
same behavior; its configuration prose describes an entity-freshness expiry the
resolver does not compute.

### Why this matters here more than at rung 4

The filing-anchored window is the specimen's whole argument for the anchor
(`CP-SPEC-003` §E.1.1): rung 2 anchors on a date that never advances and refuses
permanently; rung 3 anchors on a date that moves as filers file, and its
refusals clear. A successor that silently served `asked_at + 30 d` would serve
every obligor in the estate at any instant, and the count `CP14-F-22` said rung
3 was to measure — how few obligors serve at the CP-14 instant — would read
fifty of fifty instead of three.

### What this tree does about it, and what it does not

* The class's declared product gate `cp-03-canonical.spread-freshness-window`
  (`D-IMPL-282` R-11) refuses a spread whose freshest filing plus the declared
  window is not after the asked instant. That is a deployment expressing its
  own invariant through the SDK's sanctioned slot, and it is the reason the
  population at the CP-14 instant reads three of fifty here.
* The contract's `expires_at` is NOT corrected by this tree. A product gate can
  refuse; it cannot re-anchor. The served contract therefore says
  `from_entity_freshness` and carries a decision-anchored expiry — the
  mismatch is visible on the contract, and `OFC-G07` asserts the declaration.
* No SDK code was changed (`CP14-F-22` §1, §9). Whether the resolver should
  compute `from_entity_freshness` from the served view's freshest `valid_from`
  — and over which entities — is a design question with more than one
  reading, and it needs its own decision id.

### Readings for the ruling — none asserted

1. The resolver computes `expires_at` for `from_entity_freshness` classes from
   the maximum `valid_from` over the entities the served product touched, plus
   `product_ttl_seconds`, and refuses at the TTL gate when that is not after
   the decision instant. The product gate here becomes redundant and is
   removed.
2. The anchor declaration is redefined as documentation of the deployment's
   own gate, and `expires_at` stays decision-anchored by rule; the declaration
   is renamed or removed from the contract so it cannot say one thing and do
   another.
3. Something narrower for composites only, since `D-IMPL-336` F14 already
   floors a composite's expiry by its stalest admitted child.

---

## `CP03C-F-02` — one scratch root, one fabric: a door answering several questions served the first obligor's spread for the third question

**Status: FIXED in this tree (2026-09-14). A deployment defect found by the
door probe, not an SDK gap — and recorded because the failure was silent.**

### What was measured

The door hands every question the same assembly root. `deployment.connection`
first composed a FIXED file name under that root, so every question booted the
SAME SQLite fabric, which already held the previous questions' entities. The
third question, for an LEI that resolves to nothing, was SERVED: Π took the
first obligor entity in the view — the first question's — and the product's
gate saw an anchor inside the window. A stale obligor was likewise served with
the fresh one's anchor. Nothing raised; the content addresses differed, the
`D_c` matched the wrong obligor's.

### What was done

* `backends.yaml` already declared `database_path: {per_run: path}`;
  `deployment.connection` now mints a fresh `uuid` path per run, as the
  specimen did — the declaration and the behavior agree.
* Π takes the request's `subject` from the plan factory (the EFFECTIVE request
  the SDK hands it) and serves that obligor's claims and no other's. A view
  holding a second obligor cannot be served as this one's spread, whatever
  else is in it.
* `OFC-G20` holds the cross-deployment shape: a subject that resolves to
  nothing is refused by the child's own gate, never served another's figures.

---

## `CP03C-F-03` — `peer_basis: sic-and-size` was declared by the specimen and never implemented

**Status: NOT-A-GAP — a specimen observation; the successor declares only what
it answers.**

The specimen's contract and README offered `sic | sic-and-size`; its code read
the parameter only to echo it as `cohort_basis`, and selected the cohort by SIC
equality regardless. This tree declares `argument_domains.peer_basis.members:
[sic]`, so `sic-and-size` is refused `not-in-domain` as data (`OFC-G10`) rather
than accepted and ignored. Implementing a size band is a product decision for
whoever needs it, not a repair.

---

## `CP03C-F-04` — the `peer_set` λ_c row is declared and scores nothing

**Status: CARRIED from the specimen, deliberately. For Dave.**

The specimen declared three λ_c rows and built observations of two classes
(`annual_facts`, `quarterly_facts`); nothing was ever typed `peer_set`. This
tree preserves that, because `CP14-F-22` §8 forbids moving the debt reading,
and typing the cohort statistics as `peer_set` observations would move `F`.
The row is therefore configuration nobody reads — the shape `D-IMPL-323`'s
sitting called out at cp-08. Either the cohort statistics become observations
of that class (and the debt method changes, on a ruling), or the row is removed
from the successor's table.

---

## `CP03C-F-05` — a refusing producer reaches the consumer as `ineligible`, with neither its reason nor its record

**Status: OPEN — SDK observation, adjacent to the `D-IMPL-340` residuals.**

When the producer withholds the spread (`tolerance-exceeded`) or refuses on its
own gate, the consumer's `ChildResolution` row reads `outcome_status:
ineligible`, `refusal_ref: ineligible`, with the producer's identity and the
question address held — and without the producer's own refusal reason or the
replay reference its door returned in the `DoorOutcome`. The composite refuses
correctly (`child_admission`); an examiner reading the consumer's record cannot
tell a tolerance refusal from a window refusal from a suppressed obligor
without the producer's record. `D-GATE-340` recorded that a served answer with
`replay_ref=None` skips the replay-reference claim; this is the refused-answer
neighbor of that residual.

---

## `CP03C-F-06` — assembler identity is absent from the governed path's replay record

**Status: OPEN — SDK observation, carried from the specimen's own note.**

`build_replay_record` accepts `assembler_id` / `assembler_version`;
`build_governed_resolver` and `GovernedResolver.__call__` expose neither, so a
deployment on the canonical path cannot name its assembler in replay. The
specimen recorded the same absence on the hand-composed path ("Decision Replay
carries none of it today"). Not fixed here (`CP14-F-22` §1: no unrelated SDK
change).

---

## `CP03C-F-07` — cp-05's door constructs a `ProductRequestViolation` the contract no longer accepts

**Status: OPEN — observation about another tree, not touched.**

Copying `examples/cp-05-credit-exposure-rollup/server/serve.py`'s
`_wrong_address` verbatim produced a pydantic `ValidationError` inside the
door (`parameter=` is no longer a field; `key`, `declared_type`,
`presented_type`, `declared_keys`, `presented_keys` are required), which the
egress door surfaced as an opaque `ccf-runtime-failure`. This tree's door
constructs the current shape and returns `class-mismatch` at
`key=schema_version` as data with a record. cp-05's door has the same latent
mismatch on its wrong-address path and was not edited (`D-IMPL-261`).

---

## `CP03C-F-08` — `observed_at` is when the fabric learned the claim; a column's age is `valid_from`

**Status: NOT-A-GAP — a measurement recorded so the next reader does not
re-derive it.**

The first debt reading off the graph returned `F = 1` for a spread whose
columns are years old: `AssemblyWorker` sets the claim's `observed_at` to the
envelope's `ingestion_timestamp` (the request instant) and the envelope's
`observed_time` becomes `valid_from`. The specimen never met this because it
built its observations by hand from the period's own filing date. The
canonical form of that hand-dating is the declaration `D-IMPL-331` provides:
`decay_basis: valid-from` on the λ_c rows, with the filing carried as the
observation's `valid_from`. `OFC-G05` holds `F < 1`.

---

## Sabotage matrix

Each fix and each proof was made to fail deliberately at least once. The runs
and their verdicts are recorded in the `CP14-F-22` return under this tree's
review; a gate whose sabotage stayed green would have stopped the phase.
