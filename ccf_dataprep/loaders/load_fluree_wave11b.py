#!/usr/bin/env python3
"""Wave 11b Task 10 — load the early-warning surveillance graph into Fluree.

Per design §4.1: Postgres owns `E` and policy reference for this product
(the seven surveillance tables, Task 9, already loaded). Fluree owns `T` and
`R` — the part of the graph that has to be *walked*, not merely joined:

    - 8-K event assertions, all six item types, with filing date and accession
    - `signalAbout` edges: signal -> obligor / facility
    - `triggeredBy` edges: signal -> source event
    - prior observation ledger points, one per obligor
    - supersession assertions, reusing the existing `ex:supersededBy`

## Two node roles, not one

`triggeredBy` is "signal -> source event". A self-loop is not a real edge, so
the two ends have to be different nodes:

    SignalSource node  — `ex:{EX}8k-{accession}`  the filed 8-K itself: a
                         SEC accession, an item code, a filing date. This is
                         the "8-K event assertion" bullet above.
    WarningSignal node — `ex:{EX}{signal_id}`      the derived judgment that
                         a sweep would act on. `triggeredBy` points from here
                         to the SignalSource; `signalAbout` points from here
                         to whatever the signal concerns.

534 real 8-K events (`wave11b_8k_events.json`) and 534 `signal_type=8k_event`
rows (`wave11b_signals.json`) are, checked live before writing this file, an
exact bijection **on `(accession, item)`** — every event has exactly one signal
and vice versa, same `lei` on both sides. The engineered cascade
(`wave11b_narrative.json`) adds one more pair on the same shape: accession
`0000000000-26-000001`, item `2.04`, provenance `synthetic — engineered` —
never relabelled to `public`, and never merged into the 534.

**CORRECTED 2026-08-21.** This paragraph previously called that bijection one
**"on `accession`"** and concluded: *"So each accession yields exactly one
SignalSource/WarningSignal pair."* That conclusion is false, and it is false in
the data, not merely in the wording. A single 8-K routinely reports more than
one item, and the SignalSource node is keyed by accession alone
(`ex:{EX}8k-{accession}`), so accessions collapse:

    534 real events  ->  408 distinct accessions  ->  409 SignalSource nodes
                                                       (408 real + 1 engineered)

Live counts confirm it: 535 `ex:item` triples over **409** subjects — 287
carrying one item, 118 carrying two, 4 carrying three. WarningSignal nodes are
unaffected: there are 538, one per `(accession, item)` plus the cascade and the
composite three, so the *signal* side of the model is exactly as described.

**The consequence, and it is a real query hazard: two parallel multi-valued
properties with no linkage between them.** A multi-item SignalSource carries one
`rdfs:label` *and* one `ex:item` per reported item, and nothing says which label
goes with which code. A SPARQL pattern that pairs them returns the cross product:

    ?s rdfs:label ?l . ?s ex:item ?i .

on `8k-0001104659-24-126817` returns **four** rows, two of them nonsense —
`"Item 2.03 filing 0001104659-24-126817 (2024-12-09)"` paired with item
`"1.01"`, and its mirror image.

**Not re-modelled, deliberately.** One filing genuinely reporting two items is
correct: `8k-<accession>` *is* the filed document, and the document really does
carry both codes. Re-keying the node to `(accession, item)` would mint 534
SignalSource nodes for 408 real documents and assert that one filing is two
filings — a worse model, bought late in a wave for a query nothing in the estate
runs. The recorded, safe path is the WarningSignal node: it is one per
`(accession, item)`, its `rdfs:label` and its `triggeredBy` edge are
single-valued, and `signal_event.source_ref` in Postgres carries the item code
per signal. See `docs/known-issues.md` §10.10.

## Explicit typing, no inference (§4.3)

Every WarningSignal carries `ex:WarningSignal`. Two item types carry a second,
more specific type as well, per design §4.2's vocabulary table — reusing
already-bound terms, minting nothing new:

    item 2.03 (debt-issuance disclosure) -> also `ex:IssuanceEvent`
        (the exact class Wave 11a bound for the same kind of filing)
    item 2.04 (acceleration / triggering event) -> also
        `fibo-fnd-agr-ctr:BreachOfCovenant` ("where a breach is the signal",
        design §4.2) — a REAL FIBO term, bound at Wave 0

1.01, 5.02 and 4.01 carry no second type; there is no bound class for them
and none is invented. 4.02 has zero in-window instances (design D5) — nothing
to load, not a gap.

**`ex:filedBy` is deliberately NOT reused here**, despite the vocabulary
table listing it alongside `ex:IssuanceEvent`. `load_fluree_wave11a.py`'s
`--reconcile` retracts EVERY `filedBy` edge in the ledger by a blind
predicate scan (`OWNED_PREDICATES`) before rebuilding only from its own
`wave11a_issuance.json`. If this loader also asserted `filedBy` edges, a
future `--reconcile` run of the Wave 11a loader would silently retract them
and never rebuild them — they belong to a different source file. Reusing the
CLASS (`ex:IssuanceEvent`) carries no such risk (`rdf:type` triples are not
in anyone's reconcile scope); reusing the PROPERTY does. `ex:signalAbout`
handles signal -> obligor uniformly across every item type instead, and nothing
downstream needs `filedBy` specifically — Task 12's cascade-completeness check
walks `signalAbout`, not `filedBy`.

## The cascade's `signalAbout` targets are loaded exactly as given

`wave11b_narrative.json["cascade"]["signal_about"]` already lists the 8
targets — 1 facility, 2 `CollateralPledge` rows, 5 `Drawdown` rows — verified
in Postgres to be Avis Budget's own `FAC-044206` and its actual pledges and
drawdowns. This loader does not recompute them; it resolves each
`{target_type, target_id}` pair to `uri(target_id)` (the SAME construction
Wave 9's collateral loader used for `facility_id` and `asset_id` — a facility
node already carries 5 triples in the ledger, e.g. `hasBorrower`, two
`isCollateralizedBy` edges; collateral assets are fully typed nodes from Wave
9) and asserts `signalAbout` to each of the 8, no more, no fewer. Drawdown
nodes have never been created in Fluree before this loader — `signalAbout`
references them by the SAME natural-key URI convention without minting a
type for them, because Postgres's `drawdown` table (Wave 5) is their
attribute home; a dangling-object edge to an id Postgres does not carry
would be the real defect, and none was found (checked before writing).

## Prior observation points (§3.4) — one per anchor, not per obligor-with-events

All 50 `is_anchor` LEIs get a `PriorObservation` node, including the one
anchor with zero 8-K events in the 24-month window (checked: 49 of 50 have
at least one). Skipping that one would break the `= 50` floor design names
explicitly ("§D names delta anchoring explicitly: without a recorded prior,
the next sweep double-reports" — that reasoning applies to EVERY obligor a
sweep will touch, not only the ones with events already on file). Each node's
watermark date is `wave11b_8k_events.json["window"]["start"]`
(2024-08-19) — the moment just before this load's own surveillance window
begins, i.e. "state as of the last sweep before this data existed". Verified
via SPARQL (Task 10 Step 3):

    SELECT (COUNT(DISTINCT ?o) AS ?n)
    WHERE { ?p a ex:PriorObservation ; ex:signalAbout ?o }

must return 50 — one node, one `signalAbout` target, per anchor.

## Supersession (§4.1's fourth bullet) — computed here, not read off an artifact

Unlike Wave 11a's grade chain, none of the four Wave 11b source artifacts
carry a `supersedes` pointer (checked: zero occurrences of the substring
"supersed" in any of the three `sources/screening/wave11b_*.json` files).
Wave 11b's own opening paragraph names *why* this loader has to produce that
structure anyway: "this product is the catalog's dedicated demonstration of
supersession as a cascading policy event ... one event invalidating every
downstream product that touched the affected entity". The prior observation
point is exactly the state that gets invalidated.

The chain built here, per anchor: order that anchor's WarningSignal nodes
(real + engineered, `8k_event`-type only — the only signal type this loader
gives a Fluree identity to) by `observed_at`, then chain
`PriorObservation -> signal[0] -> signal[1] -> ... -> signal[n-1]` with
`ex:supersededBy`, exactly Wave 11a's link shape
(`triple(older, supersededBy, newer)`), just derived from chronology instead
of read from a field. For Avis Budget this is not a special case bolted on —
the engineered cascade (2026-08-12) is chronologically the LATEST of Avis's
24 in-window events (last real one: 2026-07-01, checked before writing), so
it lands as the final link in Avis's chain by the same rule every other
anchor gets, which is exactly the "one event invalidating what came before it"
shape the product exists to demonstrate.

**`ex:supersededBy` is shared with Wave 11a (215 assertions already on it).**
Unlike `signalAbout`/`triggeredBy`, which this loader owns exclusively, a
blind predicate-wide reconcile on `supersededBy` would be unsafe in BOTH
directions — it would delete Wave 11a's chain from here, or Wave 11a's own
`--reconcile` would delete this loader's chain from there. So `reconcile()`
below scopes `supersededBy` retraction to pairs where the SUBJECT is one of
this loader's own node URIs (`prior-obs-*` or a known `signal_id`), never a
blind scan of the whole predicate. `signalAbout` and `triggeredBy` remain
safe to scan blindly — no other loader writes them.

## The composite case (fix round 1) — three signals, no trigger

`wave11b_narrative.json["composite"]["signals"]` carries three
`synthetic — engineered` signals on Bausch Health Companies Inc.
(`B3BS7ACMDUWISF18KY76`), individually subthreshold and only breaching in
combination (design §3.3). Postgres now carries these same three rows in
`signal_event` (Task 9, re-run) under the SAME `signal_id`s
(`sig-composite-<LEI>-<signal_type>`) — this loader reuses those exact ids so
the two stores refer to the same signals, not parallel ones.

Each becomes an `ex:WarningSignal` node with an `ex:signalAbout` edge to
Bausch Health and `ex:provenance = "synthetic — engineered"`. **No
`triggeredBy` edge** — unlike the cascade, there is no single causal 8-K (or
any other) event behind these three; the whole point of the composite case is
that three otherwise-unremarkable signals combine, and asserting a
`triggeredBy` would claim a causal source the data does not have. No
`SignalSource` node is minted for them for the same reason.

**Bausch Health's obligor node was verified present in Fluree before this was
written** (`SELECT ?p ?o FROM <fibo-v2> WHERE { <.../BauschHealthCompaniesInc>
?p ?o }`, live query, not assumed) — it is `hasGlobalUltimateParent`-linked,
`ex:lei`-tagged, and typed `Corporation`/`Guarantor` from an earlier wave's
loader. This loader does not create obligor nodes; if that resolution had come
back empty the correct response was to stop, not mint one, and it did not come
back empty.

## Idempotency

Every node URI is a deterministic function of a committed artifact's own id
(`accession`, `signal_id`, `lei`) — no random ids are minted. Fluree triples
are set-valued, so re-asserting an unchanged triple via `INSERT DATA` is a
no-op, not a duplicate, on an UNCHANGED artifact; the three-run sequence
below is the proof, not an assumption:

    uv run loaders/load_fluree_wave11b.py --dry-run
    uv run loaders/load_fluree_wave11b.py
    uv run loaders/load_fluree_wave11b.py   # must add zero triples

**What `--reconcile` covers, precisely (fix round 2).** A regenerated
artifact that reuses the SAME deterministic URI (same accession / signal_id
/ lei) but changes a LITERAL on it — a corrected filing date, a relabelled
item, a flipped provenance string — is corrected, not duplicated:
`reconcile()` retracts every triple whose SUBJECT is one of this loader's
own node URIs, across every predicate it writes on an instance node —
`rdf:type`, `rdfs:label`, `ex:validFrom`, `ex:sourceAccession`, `ex:item`,
`ex:provenance` (the literals) as well as `signalAbout`, `triggeredBy`,
`supersededBy` (the edges) — then the caller rebuilds from the fresh
artifact. This closes a gap the first version of this loader had: that
version reconciled edges only, so a same-URI literal change would have been
`INSERT DATA`-ed alongside the stale value and Fluree's append-only history
would have kept both. See `my_node_uris()` and `reconcile()` for the exact
scoping argument (subject-membership in an exactly-known, exclusively-ours
URI set — never a blind predicate scan, because `supersededBy` is shared
with Wave 11a's 215 assertions and `rdf:type`/`rdfs:label` are used by every
loader in the estate).

**What it still does NOT cover — matching Wave 10's and Wave 11a's own
acknowledged gap, not solved here either.** If a regenerated artifact drops
an accession/signal_id/lei entirely or mints a NEW one for what is
conceptually the same fact, the OLD node is orphaned (its triples are never
retracted, because nothing in the fresh artifact names its URI) rather than
corrected. `reconcile()` can only retract what the CURRENT run's artifacts
still name; it cannot discover a node that fell out of the artifact
entirely. That is a structural property of "the artifact's own id is the
node identity" and is the same node-lifecycle limitation
`load_fluree_wave11a.py`'s docstring names for its own loader.
"""

from __future__ import annotations

import argparse
import json
import sys

from ccf import fluree
from ccf.config import EX, FLUREE_LEDGER_V2, PG_SCHEMA_V2, REPO_ROOT, pg_connect
from ccf.currency import verify_current
from loaders.load_collateral_wave9 import entity_uri_by_lei, esc, triple, uri

SCREEN = REPO_ROOT / "sources" / "screening"
FIBO = "https://spec.edmcouncil.org/fibo/ontology/"

RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
OWL_CLASS = "http://www.w3.org/2002/07/owl#Class"

# --- Real FIBO binding — verified 2026-08-20, docs/ccf_dataprep_v2.md line 224
C_BREACH_OF_COVENANT = f"{FIBO}FND/Agreements/Contracts/BreachOfCovenant"

# --- ex: extensions — reused, bound in Wave 11a --------------------------
C_ISSUANCE_EVENT = f"{EX}IssuanceEvent"

# --- ex: extensions — minted in Wave 11b Task 1, verified against FIBO
#     Production + OMG Commons; see docs/ccf_dataprep_v2.md "Wave 11b —
#     early-warning surveillance" -----------------------------------------
C_WARNING_SIGNAL = f"{EX}WarningSignal"
C_SIGNAL_SOURCE = f"{EX}SignalSource"
C_PRIOR_OBSERVATION = f"{EX}PriorObservation"
P_SIGNAL_ABOUT = f"{EX}signalAbout"
P_TRIGGERED_BY = f"{EX}triggeredBy"

# --- declared since Wave 5, populated with 215 assertions by Wave 11a ----
P_SUPERSEDED_BY = f"{EX}supersededBy"

#: Second type layered onto a WarningSignal node, keyed by 8-K item code.
#: Absent items (1.01, 5.02, 4.01) get no second type — no bound class
#: applies and none is invented (design §4.2).
ITEM_SECOND_TYPE = {
    "2.03": C_ISSUANCE_EVENT,
    "2.04": C_BREACH_OF_COVENANT,
}

BATCH = 500

#: Every predicate this loader ever asserts on one of ITS OWN instance nodes
#: (event/signal/prior-observation) — types, labels and literals as well as
#: edges. `reconcile()` (fix round 2) scopes retraction by SUBJECT against
#: this list, not by a blind predicate-wide scan, because two of these
#: (`supersededBy`, and in principle `rdf:type`/`rdfs:label` on a node whose
#: URI happened to collide with another loader's) are shared namespaces in
#: the estate — see `reconcile()`'s docstring.
MY_PREDICATES = [
    RDF_TYPE, RDFS_LABEL,
    f"{EX}validFrom", f"{EX}sourceAccession", f"{EX}item", f"{EX}provenance",
    P_SIGNAL_ABOUT, P_TRIGGERED_BY, P_SUPERSEDED_BY,
]


#: Filled by `load()` so `main()` can print the currency verdict for every
#: artifact it read — coverage visible on each run, not inferred.
CURRENCY_NOTES: list[str] = []


def load(name: str) -> dict:
    """Read one artifact, refusing a STALE one (design §5, built 2026-08-21).

    `ccf.currency.verify_current` re-hashes whatever inputs the artifact
    itself recorded under `_inputs` and raises `StaleArtifact` if any has
    changed on disk since — so a `wave11b_gdelt.json` regenerated after
    `generate_signals.py` last ran stops the load instead of feeding it a
    ledger derived from bytes that no longer exist. What it cannot catch is
    an input that is wrong rather than stale; that boundary is stated in
    `ccf/currency.py` rather than left implicit.
    """
    doc, note = verify_current(name)
    CURRENCY_NOTES.append(note)
    return doc


def event_node(accession: str) -> str:
    return uri(f"8k-{accession}")


def signal_node(signal_id: str) -> str:
    return uri(signal_id)


def prior_obs_node(lei: str) -> str:
    return uri(f"prior-obs-{lei}")


def my_node_uris(accessions: set[str], signal_ids: set[str],
                  leis: list[str]) -> set[str]:
    """The full, exact set of node URIs this loader mints — event nodes,
    signal nodes (real + cascade + composite), prior-observation nodes.
    Nothing else in the estate constructs an `8k-*`, `sig-*` or
    `prior-obs-*` local id (checked by grep across every loader and
    generator before relying on this), so subject-membership in this set is
    an exact, safe reconcile scope."""
    uris = {event_node(a) for a in accessions}
    uris |= {signal_node(sid) for sid in signal_ids}
    uris |= {prior_obs_node(lei) for lei in leis}
    return uris


def _asserted_triples(predicate: str) -> list[tuple[str, str, bool]]:
    """(subject, object, is_literal) for every currently-asserted triple on
    `predicate`, anywhere in the ledger — filtered to OUR subjects by the
    caller, never trusted as ours just because the predicate matches."""
    q = f"SELECT ?s ?o FROM <{FLUREE_LEDGER_V2}> WHERE {{ ?s <{predicate}> ?o }}"
    out: list[tuple[str, str, bool]] = []
    for b in fluree.query(q).get("results", {}).get("bindings", []):
        out.append((b["s"]["value"], b["o"]["value"],
                    b["o"].get("type") == "literal"))
    return out


def _my_asserted(node_uris: set[str]) -> list[tuple[str, str, str, bool]]:
    """(predicate, subject, object, is_literal) across every predicate this
    loader writes, filtered to subjects in `node_uris`."""
    out: list[tuple[str, str, str, bool]] = []
    for pred in MY_PREDICATES:
        for s, o, lit in _asserted_triples(pred):
            if s in node_uris:
                out.append((pred, s, o, lit))
    return out


def reconcile(*, dry_run: bool, node_uris: set[str]) -> int:
    """Retract every triple whose SUBJECT is one of this loader's own node
    URIs — EVERY predicate it writes on an instance node: types, labels,
    literals (`ex:validFrom`, `ex:sourceAccession`, `ex:item`,
    `ex:provenance`) and edges (`signalAbout`, `triggeredBy`,
    `supersededBy`) alike — then the caller rebuilds from the freshly
    loaded artifacts.

    **Fix round 2, replacing an edges-only reconcile.** The prior version
    retracted `signalAbout`/`triggeredBy` (blind predicate scan — safe,
    exclusive to this loader) and `supersededBy` (scoped by subject, because
    that predicate is shared with Wave 11a's 215 assertions). It never
    touched literals. So if a regenerated artifact kept the SAME
    deterministic URI (same accession / signal_id / lei) but changed a
    literal value — a corrected filing date, a relabelled item — a re-run,
    EVEN WITH `--reconcile`, would `INSERT DATA` the new literal alongside
    the stale one, and Fluree being append-only would keep both. That gap is
    closed here: retraction is now scoped by SUBJECT across every predicate
    in `MY_PREDICATES` (which includes the literal-bearing ones), not by
    predicate alone.

    Scoping by subject rather than by predicate is what keeps this safe on
    `supersededBy`, and is provably exact rather than merely convenient:
    every URI in `node_uris` (`my_node_uris()`) is built from an `8k-*`,
    `sig-*` or `prior-obs-*` local id, and grepping every loader and
    generator in the estate turns up no other writer of any of those three
    prefixes. A blind predicate-wide scan on `rdf:type` or `rdfs:label`
    would NOT be safe — those predicates are used by every loader in the
    estate — which is exactly why this filters by subject membership first
    and only then looks at which predicates that subject carries.
    """
    total = 0
    statements: list[str] = []
    by_pred: dict[str, int] = {}
    for pred, s, o, lit in _my_asserted(node_uris):
        by_pred[pred] = by_pred.get(pred, 0) + 1
        obj = f'"{esc(o)}"' if lit else f"<{o}>"
        statements.append(f"<{s}> <{pred}> {obj} .")
        total += 1

    for pred, n in sorted(by_pred.items()):
        print(f"    {pred.rsplit('/', 1)[-1]:<16} {n:>5} asserted (ours)")

    if not statements:
        print("    nothing asserted — nothing to retract")
        return 0
    print(f"    {total} triples to retract")
    if dry_run:
        print("    [dry-run] nothing retracted")
        return 0

    for i in range(0, len(statements), BATCH):
        fluree.update("DELETE DATA {\n" + "\n".join(statements[i:i + BATCH]) + "\n}")

    remaining = len(_my_asserted(node_uris))
    print(f"    retracted · triples remaining on our own subjects: {remaining}")
    if remaining:
        print("    WARNING — retraction incomplete; not proceeding to the rebuild.")
    return remaining


def build(entity_uri: dict[str, str], anchor_leis: list[str],
          window_start: str, events: list[dict], signals: list[dict],
          cascade: dict, composite: dict) -> tuple[list[str], dict]:
    """Compute every triple this loader will assert, deterministically."""
    triples: list[str] = []
    stats = {
        "event_dangling": 0, "signal_dangling": 0, "cascade_dangling": 0,
        "prior_obs": 0, "supersessions": 0, "composite_dangling": 0,
        "composite_loaded": 0,
    }

    # --- T-box: the three ex: classes minted in Wave 11b Task 1 -----------
    for cls, note in (
        (C_WARNING_SIGNAL, "WarningSignal (ex: extension — zero signal/"
         "warning-bearing terms in FIBO Production or OMG Commons)"),
        (C_SIGNAL_SOURCE, "SignalSource (ex: extension — FIBO's …Provider "
         "classes type a vendor organisation, not a feed a signal derives "
         "from)"),
        (C_PRIOR_OBSERVATION, "PriorObservation (ex: extension — no "
         "Observation class in FIBO Production or OMG Commons; "
         "ObservedValue is a measured value, not a sweep watermark)"),
    ):
        triples.append(triple(cls, RDF_TYPE, OWL_CLASS))
        triples.append(triple(cls, RDFS_LABEL, note, literal=True))

    # --- signal id -> chronological key, for the supersession chain -------
    signal_history: dict[str, list[tuple[str, str]]] = {lei: [] for lei in anchor_leis}

    # --- 534 real 8-K events + their 1:1 signals ---------------------------
    ev_by_accession = {e["accession"]: e for e in events}
    for s in signals:
        sr = s["source_ref"]
        accession = sr["accession"]
        ev = ev_by_accession[accession]
        item = sr["item"]
        lei = s["lei"]

        ev_node = event_node(accession)
        triples += [
            triple(ev_node, RDF_TYPE, C_SIGNAL_SOURCE),
            triple(ev_node, RDFS_LABEL,
                   f"Item {item} filing {accession} ({ev['filing_date']})",
                   literal=True),
            triple(ev_node, f"{EX}validFrom", ev["filing_date"], literal=True),
            triple(ev_node, f"{EX}sourceAccession", accession, literal=True),
            triple(ev_node, f"{EX}item", item, literal=True),
            triple(ev_node, f"{EX}provenance", ev["provenance"], literal=True),
        ]

        sig_node = signal_node(s["signal_id"])
        triples += [
            triple(sig_node, RDF_TYPE, C_WARNING_SIGNAL),
            triple(sig_node, RDFS_LABEL,
                   f"8-K item {item} signal — {lei} ({s['observed_at']})",
                   literal=True),
            triple(sig_node, P_TRIGGERED_BY, ev_node),
            triple(sig_node, f"{EX}provenance", s["provenance"], literal=True),
        ]
        second_type = ITEM_SECOND_TYPE.get(item)
        if second_type:
            triples.append(triple(sig_node, RDF_TYPE, second_type))

        target = entity_uri.get(lei)
        if target is None:
            stats["signal_dangling"] += 1
        else:
            triples.append(triple(sig_node, P_SIGNAL_ABOUT, target))

        if lei in signal_history:
            signal_history[lei].append((s["observed_at"], sig_node))

    # --- the engineered cascade: one more event/signal pair ----------------
    cs_accession = cascade["source_ref"]["accession"]
    cs_item = cascade["item"]
    cs_lei = cascade["lei"]
    cs_provenance = cascade["provenance"]

    ev_node = event_node(cs_accession)
    triples += [
        triple(ev_node, RDF_TYPE, C_SIGNAL_SOURCE),
        triple(ev_node, RDFS_LABEL,
               f"Item {cs_item} filing {cs_accession} ({cascade['observed_at']}) "
               "— engineered", literal=True),
        triple(ev_node, f"{EX}validFrom", cascade["observed_at"], literal=True),
        triple(ev_node, f"{EX}sourceAccession", cs_accession, literal=True),
        triple(ev_node, f"{EX}item", cs_item, literal=True),
        triple(ev_node, f"{EX}provenance", cs_provenance, literal=True),
    ]

    sig_node = signal_node(cascade["signal_id"])
    triples += [
        triple(sig_node, RDF_TYPE, C_WARNING_SIGNAL),
        triple(sig_node, RDFS_LABEL,
               f"Engineered 8-K item {cs_item} signal — {cascade['legal_name']} "
               f"({cascade['observed_at']}) — design §3.1 scripted cascade",
               literal=True),
        triple(sig_node, P_TRIGGERED_BY, ev_node),
        triple(sig_node, f"{EX}provenance", cs_provenance, literal=True),
    ]
    second_type = ITEM_SECOND_TYPE.get(cs_item)
    if second_type:
        triples.append(triple(sig_node, RDF_TYPE, second_type))

    for t in cascade["signal_about"]:
        target_node = uri(t["target_id"])
        triples.append(triple(sig_node, P_SIGNAL_ABOUT, target_node))
    if not cascade["signal_about"]:
        stats["cascade_dangling"] += 1

    if cs_lei in signal_history:
        signal_history[cs_lei].append((cascade["observed_at"], sig_node))
    else:
        stats["cascade_dangling"] += 1

    # --- the composite case: three signals, no trigger (fix round 1) ------
    # Design §3.3 / coordinator fix round 1: WarningSignal-typed only,
    # signalAbout -> Bausch Health, provenance synthetic — engineered, and
    # deliberately NO triggeredBy — there is no single causal event behind
    # a composite, so asserting one would claim a causal source the data
    # does not support. Ids match Postgres's signal_event exactly
    # (sig-composite-<LEI>-<signal_type>), so both stores name the same
    # signals rather than parallel ones.
    composite_lei = composite["lei"]
    composite_target = entity_uri.get(composite_lei)
    if composite_target is None:
        # Verified live before this loader was written (SPARQL against
        # BauschHealthCompaniesInc); this branch exists so a future run
        # against a changed ledger fails loudly rather than minting a
        # duplicate obligor node — obligor identity belongs to an earlier
        # wave's loader, not this one.
        raise RuntimeError(
            f"composite case: obligor {composite_lei!r} does not resolve "
            "in Fluree. Refusing to mint a duplicate obligor node — stop "
            "and report, per the coordinator's instruction."
        )
    for cs in composite["signals"]:
        node = signal_node(cs["signal_id"])
        triples += [
            triple(node, RDF_TYPE, C_WARNING_SIGNAL),
            triple(node, RDFS_LABEL,
                   f"Composite signal — {cs['signal_type']} — "
                   f"{composite['legal_name']} ({cs['observed_at']}) — "
                   "design §3.3 composite case", literal=True),
            triple(node, f"{EX}provenance", cs["provenance"], literal=True),
            triple(node, P_SIGNAL_ABOUT, composite_target),
        ]
        stats["composite_loaded"] += 1
        if cs["provenance"] != "synthetic — engineered":
            # Never public, per CLAUDE.md rule 1 and the coordinator's
            # explicit instruction — fail loudly rather than load it.
            raise RuntimeError(
                f"composite signal {cs['signal_id']!r} is not labelled "
                f"synthetic — engineered (got {cs['provenance']!r}); "
                "refusing to load a mislabelled AML/composite condition."
            )

    # --- prior observation points: one per anchor, every anchor ------------
    for lei in anchor_leis:
        p_node = prior_obs_node(lei)
        triples += [
            triple(p_node, RDF_TYPE, C_PRIOR_OBSERVATION),
            triple(p_node, RDFS_LABEL,
                   f"Prior observation — {lei} as of {window_start}",
                   literal=True),
            triple(p_node, f"{EX}validFrom", window_start, literal=True),
            triple(p_node, f"{EX}provenance", "synthetic — internal", literal=True),
        ]
        target = entity_uri.get(lei)
        if target is None:
            stats["event_dangling"] += 1
        else:
            triples.append(triple(p_node, P_SIGNAL_ABOUT, target))
        stats["prior_obs"] += 1

        # --- supersession chain: prior_obs -> sig[0] -> sig[1] -> ... -----
        chain_nodes = [n for _, n in sorted(signal_history[lei])]
        chain = [p_node] + chain_nodes
        for a, b in zip(chain, chain[1:]):
            triples.append(triple(a, P_SUPERSEDED_BY, b))
            stats["supersessions"] += 1

    return triples, stats


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--reconcile", action="store_true",
                    help="retract this loader's own edges before rebuilding. "
                         "Required only if the source JSON has been "
                         "regenerated with different content — a re-run "
                         "against UNCHANGED JSON is already idempotent "
                         "because every node URI is deterministic.")
    args = ap.parse_args()

    events_doc = load("wave11b_8k_events.json")
    signals_doc = load("wave11b_signals.json")
    narrative_doc = load("wave11b_narrative.json")

    events = events_doc["events"]
    window_start = events_doc["window"]["start"]
    signals = [s for s in signals_doc["signals"] if s["signal_type"] == "8k_event"]
    cascade = narrative_doc["cascade"]
    composite = narrative_doc["composite"]

    entity_uri = entity_uri_by_lei()
    print(f"  resolved {len(entity_uri)} entity nodes from the ledger")

    S = PG_SCHEMA_V2
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT lei FROM "{S}".legal_entity WHERE is_anchor ORDER BY lei')
        anchor_leis = [r[0] for r in cur.fetchall()]
    print(f"  {len(anchor_leis)} anchors under surveillance (is_anchor)")

    triples, stats = build(entity_uri, anchor_leis, window_start, events, signals,
                            cascade, composite)

    # --- the full, exact set of node URIs this loader mints (fix round 2) --
    # Used to scope --reconcile by SUBJECT across every predicate it writes,
    # literals included — see reconcile()'s docstring.
    accessions = {s["source_ref"]["accession"] for s in signals}
    accessions.add(cascade["source_ref"]["accession"])
    signal_ids = {s["signal_id"] for s in signals}
    signal_ids.add(cascade["signal_id"])
    signal_ids |= {cs["signal_id"] for cs in composite["signals"]}
    node_uris = my_node_uris(accessions, signal_ids, anchor_leis)

    provenance_split = {
        "public": sum(1 for s in signals if s["provenance"] == "public"),
        "engineered": 1,
    }

    print("\nWave 11b Task 10 — Fluree load\n")
    print(f"  8-K events (real)      {len(events):>6}")
    print(f"  8-K signals (real)     {len(signals):>6}  "
          f"(dangling signalAbout: {stats['signal_dangling']})")
    print(f"  cascade event+signal        1  "
          f"(dangling signalAbout: {stats['cascade_dangling']}, "
          f"targets loaded: {len(cascade['signal_about'])})")
    print(f"  prior observation points {stats['prior_obs']:>4}  "
          f"(dangling signalAbout: {stats['event_dangling']})")
    print(f"  supersession assertions {stats['supersessions']:>5}")
    print(f"  composite signals       {stats['composite_loaded']:>6}  "
          f"(dangling signalAbout: {stats['composite_dangling']})")
    print(f"  total triples          {len(triples):>6}")
    print(f"\n  provenance split of 8-K signal+event pairs: "
          f"{provenance_split['public']} public, "
          f"{provenance_split['engineered']} synthetic — engineered")

    if args.reconcile:
        print("\n  --reconcile: retracting this loader's own triples "
              "(types, labels, literals, edges) before rebuild")
        if reconcile(dry_run=args.dry_run, node_uris=node_uris):
            return 1

    if args.dry_run:
        print("\n  [dry-run] nothing written to Fluree")
        return 0

    for i in range(0, len(triples), BATCH):
        fluree.update("INSERT DATA {\n" + "\n".join(triples[i:i + BATCH]) + "\n}")
    print(f"\n  ledger now at t={fluree.ledger_t()} · "
          f"{fluree.count_triples():,} triples")
    return 0


if __name__ == "__main__":
    sys.exit(main())
