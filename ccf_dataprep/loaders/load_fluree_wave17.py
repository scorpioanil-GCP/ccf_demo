#!/usr/bin/env python3
"""Wave 17 Task 13 -- aml-typology-match: nodes, network, ownership binding
and the typology layer, into Fluree.

Reads four frozen artifacts under `sources/screening/` -- `wave17_parties.json`
(201 rows, Task 6), `wave17_transactions.json` (4,358 rows, Task 8/10/12),
`wave17_cases.json` (24 rows, Task 11) and `wave17_typologies.json` (4 rows,
Task 4) -- plus Task 9's ownership binding (`wave17_ownership.json`, 100
rows). Nothing here generates; it projects what earlier tasks already froze.

## Node identity -- derived from content, never position

`AMLP-0001` (party_id), `TYP-STRUCT` (typology_id) and `PSC-0061`
(beneficial_owner_key) are already the artifacts' own content-derived keys,
so `uri(party_id)` / `uri(typology_id)` / `uri(person_key)` (the same `uri()`
`load_collateral_wave9.py` and every Fluree loader since Wave 9 already use)
mints the same subject on every run. Positional identity is a defect class
recorded five times in this estate; nothing here keys off a row's index.

## `ex:AMLParty` nodes carry identity and nothing else

`ex:lei` (reused, not redeclared -- the estate-wide identity predicate every
entity-bearing loader already uses) holds the party's `syn_lei`.
`rdfs:label` holds only `"AML party {party_id}"` -- an id echo, not the
`legal_name` Postgres owns. §C assigns legal name, jurisdiction and
incorporation date to Postgres; `party_kind` is likewise an `aml_party`
column. None of the four appears here in any form, including folded into a
label string -- a stricter reading than some earlier loaders' labels
(Wave 16's `OpportunitySignal` label embeds `signal_type`), because the
brief for this task names legal name, jurisdiction and incorporation date
explicitly and this loader treats "must not appear here" as covering every
predicate, not just the ones `validators/partition.py`'s generic scan
happens to check by name.

## `ex:transactedWith` -- ALL 4,358 rows, both directions, no dedup of pairs

Task 17's `depth_three_holds()` will build its adjacency from THIS
predicate, not from the JSON artifact (per the controller brief), so the
floor Task 11 established -- CASE-008's `AMLP-0166` absent at depth 2,
present at depth 3, walking an UNDIRECTED graph from `AMLP-0049` -- only
survives if the projection is complete and adds nothing extra. Two things
follow:

  * every one of the 4,358 transaction rows is read, ordinary and injected
    alike -- no filter to "the case rows" or any other subset, because a
    subset changes the adjacency and the floor becomes a different claim;
  * each UNORDERED pair `{from_party, to_party}` is asserted in BOTH
    directions (`a transactedWith b` and `b transactedWith a`), matching
    `comparableTo`'s existing symmetric-edge convention (Wave 16), so any
    consumer walking outward from either endpoint finds the other without
    depending on its own code to symmetrize a directed edge first. Multiple
    transaction rows between the SAME unordered pair collapse to the one
    pair -- "deduplicating parallel edges... is fine; dropping pairs is
    not" -- and RDF set semantics would collapse an accidental duplicate
    triple to one assertion regardless, so the Python-side pair set below
    is a clarity choice, not a correctness requirement.

No self-loop (`from_party == to_party`) and no edge to a node outside the
201-party `ex:AMLParty` population is ever asserted -- both are exactly the
"one edge wide" ways this floor could be silently erased that the brief
names, and both are counted and, if nonzero, treated as a load failure
rather than a warning.

## `ex:Typology` / `ex:TypologyPattern` -- one node, two roles, today

Bound in `docs/ccf_dataprep_v2.md`'s Wave 17 section as two DISTINCT
classes "so the same category can carry more than one structural variant."
`wave17_typologies.json` carries exactly one derived, parameterized
structural definition per typology_id today (Task 4's docstring: "the four
typology structural definitions"), so ONE node per typology_id is typed
with BOTH `rdf:type ex:Typology` (the abstract category) and
`rdf:type ex:TypologyPattern` (the concrete, advisory-derived structural
instance) -- no separate node, and no invented linking predicate between
them, since none is bound and this task does not mint new terms. Rule 7
(no reasoner) is why both types are asserted explicitly rather than one
being left to imply the other. `ex:anchoredToPassage` is a plain string
citing the artifact's own `passage_id` -- the same "cite the MongoDB row's
key on a Fluree literal, never construct one" pattern `ex:documentId` and
`ex:variantId` already use for the same cross-store shape (Mongo remains
the sole holder of the passage text).

## `ex:matchesTypology` -- one edge per case, from the subject party

24 cases (Task 11), 6 per typology, each naming one `subject_party`. Each
becomes exactly one `ex:matchesTypology` edge from that party's `ex:AMLParty`
node to its typology_id's dual-typed node above -- never from an
intermediary named in a case's `pattern.intermediaries` list, which is a
separate, Postgres-side demonstration (Task 12's second alert on the
shell-case intermediary), not a second accusation asserted here.

## The floor-1 test the brief ships is too weak -- strengthened here

`validators/test_aml_typology.py::test_every_matches_typology_edge_cites_an_advisory_passage`
is the brief's own name, but its verbatim body checks two independent
counts (`matches > 0`, `anchored > 0`), which a hundred unanchored
`matchesTypology` edges plus one anchored typology elsewhere would still
pass. The test now also asserts, as a SPARQL set difference that must be
empty, that every OBJECT of `matchesTypology` resolves to a node carrying
`anchoredToPassage` directly -- which this loader satisfies by construction,
since `matchesTypology` only ever targets the dual-typed typology nodes that
already carry the anchor. A second test
(`test_the_anchor_universal_can_actually_fail`) proves the strengthened
check is not vacuous: it inserts a throwaway unanchored edge, confirms the
check flags it, and retracts the scratch triple in a `finally` block.

## Ownership binding -- reuse Wave 13b's PSC nodes, never reconstruct one

Task 9 bound 100 `aml_party` rows to EXISTING `bo_chain` owners
(`sources/screening/wave17_ownership.json`), all `PSC-####` keys
(`ccf.aml.is_psc_key` re-checked here as a second, redundant guard -- CLAUDE.md
rule 2/3 has teeth or it does not). `load_bo_chains_wave13b.py` already
minted a Fluree node at `uri(person_key)` for every such key and typed it
`fibo-be-oac-cown:BeneficialOwner`; this loader queries the ledger for that
type FIRST and only asserts `hasBeneficialOwner` / `isBeneficialOwnerOf`
for a binding whose owner resolves to an EXISTING node -- constructing the
URI without checking is exactly the Wave 5 phantom-borrower defect
(`docs/known-issues.md`), reproduced once already on `pledgedBy` in this
estate and not repeated here.

## Idempotency -- retract-then-assert, scoped by subject IRI (Rule 5)

Three populations, matching `load_fluree_wave16.py`'s pattern:

  AML_SUBJECT_PREDICATES     -- every predicate this loader asserts with an
    `ex:AMLParty` node as SUBJECT (`rdf:type`, `rdfs:label`, `ex:lei`,
    `hasBeneficialOwner`, `ex:transactedWith`, `ex:matchesTypology`). Safe
    to retract by subject alone: `AMLP-*` is a namespace this loader alone
    mints, so no other loader could have asserted any of these predicates
    with one of these subjects before this loader existed.

  TYPOLOGY_SUBJECT_PREDICATES -- the same argument for `TYP-*` subjects
    (`rdf:type`, `rdfs:label`, `ex:anchoredToPassage`, `ex:provenance`).

  CLASS_SUBJECT_PREDICATES   -- the three T-box declarations
    (`ex:AMLParty`, `ex:Typology`, `ex:TypologyPattern` as SUBJECTS).

`isBeneficialOwnerOf` is the one exception and gets its own scoping: its
SUBJECT is the REUSED `PSC-*` node, which Wave 13b's own loader already
uses as a subject of this exact predicate for its original `bo_chain`
entities. Scoping by subject alone would retract those pre-existing edges
too -- the same "blind predicate-wide DELETE" failure the estate already
guards against, one level down (subject-shared rather than predicate-shared).
So `isBeneficialOwnerOf` is retracted scoped by (subject, OBJECT) together,
where the object must be one of THIS loader's own `AMLP-*` nodes.

Reconcile is opt-in (`--reconcile`); a plain re-run against an unchanged
artifact is already idempotent because every subject and literal is
deterministic, and Fluree's own set semantics make re-asserting an
unchanged triple a no-op.

## Task 14 -- FilingPosture / DispositionRule, the policy layer

Reads a fifth frozen artifact, `wave17_policy.json` (Task 14): 2 postures,
16 disposition rules. `ex:FilingPosture` gets one node per `posture_id`
with `ex:postureEffectiveFrom` (plain string, Rule 5 -- never a typed date
literal) and `ex:provenance`. `ex:DispositionRule` gets one node per
`rule_id` with `ex:permitsDisposition` (a plain `"true"`/`"false"` string
literal, matching `ex:isFiboTerm`'s existing convention rather than a
typed boolean) and `ex:provenance`.

Neither `belongsToPosture` nor `forTypology` is a bound term, and this task
does not mint one. Instead `rule_id` is itself derived from content --
`RULE-{posture_id}-{typology_id}-{disposition}` -- so the composite key IS
the link: a consumer who already knows which posture and typology it cares
about (Task 17's `posture_flip_holds()`) can construct the same URI and
query `ex:permitsDisposition` directly, the same way `AMLP-0001` and
`TYP-STRUCT` are already their own keys with no extra predicate needed to
resolve them. `advisory_number` (null for both postures today -- see
`generators/generate_aml_policy.py`'s module docstring for why) stays in
the JSON artifact only; no Fluree predicate is bound for it, so it is not
asserted here.

Both new classes join the existing T-box loop (`CLASS_SUBJECT_PREDICATES`)
and both new subject populations get their own idempotency scope
(`POSTURE_SUBJECT_PREDICATES`, `RULE_SUBJECT_PREDICATES`), following
exactly the same subject-scoped-retraction argument as `AML_SUBJECT_PREDICATES`
and `TYPOLOGY_SUBJECT_PREDICATES`: `POST-*` and `RULE-*` are namespaces
only this loader mints.

    uv run loaders/load_fluree_wave17.py --dry-run
    uv run loaders/load_fluree_wave17.py
    uv run loaders/load_fluree_wave17.py --reconcile --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys

from ccf import fluree
from ccf.aml import is_psc_key
from ccf.config import EX, EX_EXTENSION_SCHEMA_NOTE, FLUREE_LEDGER_V2, REPO_ROOT
from loaders.load_collateral_wave9 import triple, uri

SCREEN = REPO_ROOT / "sources" / "screening"
PARTIES_PATH = SCREEN / "wave17_parties.json"
TRANSACTIONS_PATH = SCREEN / "wave17_transactions.json"
CASES_PATH = SCREEN / "wave17_cases.json"
TYPOLOGIES_PATH = SCREEN / "wave17_typologies.json"
OWNERSHIP_PATH = SCREEN / "wave17_ownership.json"
POLICY_PATH = SCREEN / "wave17_policy.json"

RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
OWL_CLASS = "http://www.w3.org/2002/07/owl#Class"

FIBO = "https://spec.edmcouncil.org/fibo/ontology/"
P_HAS_BENEFICIAL_OWNER = f"{FIBO}BE/OwnershipAndControl/CorporateOwnership/hasBeneficialOwner"
P_IS_BENEFICIAL_OWNER_OF = f"{FIBO}BE/OwnershipAndControl/CorporateOwnership/isBeneficialOwnerOf"
C_BENEFICIAL_OWNER = f"{FIBO}BE/OwnershipAndControl/CorporateOwnership/BeneficialOwner"

# --- T-box: bound in docs/ccf_dataprep_v2.md's Wave 17 section, 0 assertions
#     until this task -------------------------------------------------------
C_AML_PARTY = f"{EX}AMLParty"
C_TYPOLOGY = f"{EX}Typology"
C_TYPOLOGY_PATTERN = f"{EX}TypologyPattern"
C_FILING_POSTURE = f"{EX}FilingPosture"
C_DISPOSITION_RULE = f"{EX}DispositionRule"

# --- reused predicates, NOT redeclared --------------------------------------
P_LEI = f"{EX}lei"
P_PROVENANCE = f"{EX}provenance"

# --- new predicates this loader introduces, bound in the same section ------
P_TRANSACTED_WITH = f"{EX}transactedWith"
P_MATCHES_TYPOLOGY = f"{EX}matchesTypology"
P_ANCHORED_TO_PASSAGE = f"{EX}anchoredToPassage"
P_POSTURE_EFFECTIVE_FROM = f"{EX}postureEffectiveFrom"
P_PERMITS_DISPOSITION = f"{EX}permitsDisposition"

P_IS_FIBO_TERM = f"{EX}isFiboTerm"
P_SCHEMA_NOTE = f"{EX}schemaNote"

BATCH = 400

# --- predicates by subject population (see module docstring) ---------------
AML_SUBJECT_PREDICATES = [
    RDF_TYPE, RDFS_LABEL, P_LEI, P_HAS_BENEFICIAL_OWNER,
    P_TRANSACTED_WITH, P_MATCHES_TYPOLOGY,
]
TYPOLOGY_SUBJECT_PREDICATES = [
    RDF_TYPE, RDFS_LABEL, P_ANCHORED_TO_PASSAGE, P_PROVENANCE,
]
POSTURE_SUBJECT_PREDICATES = [
    RDF_TYPE, RDFS_LABEL, P_POSTURE_EFFECTIVE_FROM, P_PROVENANCE,
]
RULE_SUBJECT_PREDICATES = [
    RDF_TYPE, RDFS_LABEL, P_PERMITS_DISPOSITION, P_PROVENANCE,
]
CLASS_SUBJECT_PREDICATES = [RDF_TYPE, RDFS_LABEL, P_IS_FIBO_TERM, P_SCHEMA_NOTE]


def party_uri(party_id: str) -> str:
    return uri(party_id)


def typology_uri(typology_id: str) -> str:
    return uri(typology_id)


def psc_uri(person_key: str) -> str:
    """The SAME node `load_bo_chains_wave13b.py` already minted -- reused,
    never reconstructed. `uri()` is bare concatenation, so this resolves to
    the identical subject as long as the key string matches exactly."""
    return uri(person_key)


def posture_uri(posture_id: str) -> str:
    return uri(posture_id)


def rule_uri(rule_id: str) -> str:
    return uri(rule_id)


# --- readers -----------------------------------------------------------------

def load_parties() -> list[dict]:
    return json.loads(PARTIES_PATH.read_text())["parties"]


def load_transactions() -> list[dict]:
    return json.loads(TRANSACTIONS_PATH.read_text())["transactions"]


def load_cases() -> list[dict]:
    return json.loads(CASES_PATH.read_text())["cases"]


def load_typologies() -> list[dict]:
    return json.loads(TYPOLOGIES_PATH.read_text())["typologies"]


def load_ownership() -> list[dict]:
    return json.loads(OWNERSHIP_PATH.read_text())["bindings"]


def load_policy() -> tuple[list[dict], list[dict]]:
    doc = json.loads(POLICY_PATH.read_text())
    return doc["postures"], doc["rules"]


def resolve_existing_beneficial_owners() -> set[str]:
    """Every Fluree node ALREADY typed `BeneficialOwner` -- Wave 13b's own
    PSC-anchored `bo_chain` population. A binding whose owner is not in this
    set gets no edge; constructing the URI unconditionally is the phantom-
    borrower defect this estate has already hit once."""
    q = (f"SELECT DISTINCT ?s FROM <{FLUREE_LEDGER_V2}> "
         f"WHERE {{ ?s a <{C_BENEFICIAL_OWNER}> }}")
    return {b["s"]["value"] for b in fluree.query(q)["results"]["bindings"]}


# --- build -------------------------------------------------------------------

def build(parties: list[dict], txns: list[dict], cases: list[dict],
          typologies: list[dict], ownership: list[dict],
          postures: list[dict], rules: list[dict],
          existing_bo_nodes: set[str]) -> tuple[list[str], dict]:
    """Compute every triple this loader will assert, deterministically."""
    triples: list[str] = []
    stats = {
        "amlparty_nodes": 0,
        "beneficial_owner_asserted": 0, "beneficial_owner_dangling": 0,
        "distinct_transacting_pairs": 0, "transactedwith_edges": 0,
        "transaction_self_loops": 0, "transaction_dangling": 0,
        "typology_nodes": 0,
        "matches_typology_asserted": 0, "matches_typology_dangling": 0,
        "posture_nodes": 0, "rule_nodes": 0, "rule_dangling": 0,
    }

    # --- T-box ---------------------------------------------------------
    for cls, label in (
        (C_AML_PARTY, "AMLParty (ex: extension -- synthetic-only party "
                      "type; CLAUDE.md rule 2)"),
        (C_TYPOLOGY, "Typology (ex: extension -- no FIBO class for a named "
                     "laundering pattern category)"),
        (C_TYPOLOGY_PATTERN, "TypologyPattern (ex: extension -- the "
                             "derived, parameterized structural instance "
                             "of a Typology)"),
        (C_FILING_POSTURE, "FilingPosture (ex: extension -- a versioned "
                           "internal filing-disposition policy)"),
        (C_DISPOSITION_RULE, "DispositionRule (ex: extension -- one "
                             "posture's ruling for one typology)"),
    ):
        triples += [
            triple(cls, RDF_TYPE, OWL_CLASS),
            triple(cls, RDFS_LABEL, label, literal=True),
            triple(cls, P_IS_FIBO_TERM, "false", literal=True),
            triple(cls, P_SCHEMA_NOTE, EX_EXTENSION_SCHEMA_NOTE, literal=True),
        ]

    # --- AMLParty nodes: identity only, no Postgres-owned attribute -----
    party_node: dict[str, str] = {}
    for p in sorted(parties, key=lambda r: r["party_id"]):
        node = party_uri(p["party_id"])
        party_node[p["party_id"]] = node
        triples += [
            triple(node, RDF_TYPE, C_AML_PARTY),
            triple(node, RDFS_LABEL, f"AML party {p['party_id']}", literal=True),
            triple(node, P_LEI, p["syn_lei"], literal=True),
        ]
        stats["amlparty_nodes"] += 1

    # --- ownership binding: reuse existing PSC-* BeneficialOwner nodes ---
    for b in sorted(ownership, key=lambda r: r["party_id"]):
        key = b["beneficial_owner_key"]
        if not is_psc_key(key):
            # Redundant guard (Task 9 already enforces this at generation
            # time) -- CLAUDE.md rule 2/3 has teeth or it does not.
            raise SystemExit(
                f"refusing to bind {b['party_id']} to non-PSC owner key "
                f"{key!r} -- Wave 17 may only use PSC-* owners")
        aml_node = party_node.get(b["party_id"])
        owner_node = psc_uri(key)
        if aml_node is None or owner_node not in existing_bo_nodes:
            stats["beneficial_owner_dangling"] += 1
            continue
        triples += [
            triple(aml_node, P_HAS_BENEFICIAL_OWNER, owner_node),
            triple(owner_node, P_IS_BENEFICIAL_OWNER_OF, aml_node),
        ]
        stats["beneficial_owner_asserted"] += 1

    # --- transactedWith: ALL 4,358 rows, both directions, dedup by pair --
    pairs: set[frozenset[str]] = set()
    for t in txns:
        a, b_ = t["from_party"], t["to_party"]
        if a == b_:
            stats["transaction_self_loops"] += 1
            continue
        if a not in party_node or b_ not in party_node:
            stats["transaction_dangling"] += 1
            continue
        pairs.add(frozenset((a, b_)))

    for pair in sorted(pairs, key=lambda fs: tuple(sorted(fs))):
        a, b_ = sorted(pair)
        an, bn = party_node[a], party_node[b_]
        triples += [
            triple(an, P_TRANSACTED_WITH, bn),
            triple(bn, P_TRANSACTED_WITH, an),
        ]
    stats["distinct_transacting_pairs"] = len(pairs)
    stats["transactedwith_edges"] = 2 * len(pairs)

    # --- Typology / TypologyPattern: one dual-typed node per typology_id -
    typology_node: dict[str, str] = {}
    for t in sorted(typologies, key=lambda r: r["typology_id"]):
        node = typology_uri(t["typology_id"])
        typology_node[t["typology_id"]] = node
        triples += [
            triple(node, RDF_TYPE, C_TYPOLOGY),
            triple(node, RDF_TYPE, C_TYPOLOGY_PATTERN),
            triple(node, RDFS_LABEL, f"{t['typology']} ({t['typology_id']})",
                   literal=True),
            triple(node, P_ANCHORED_TO_PASSAGE, t["passage_id"], literal=True),
            triple(node, P_PROVENANCE, t["provenance"], literal=True),
        ]
        stats["typology_nodes"] += 1

    # --- matchesTypology: one edge per case, from the subject party ------
    for c in sorted(cases, key=lambda r: r["case_id"]):
        subj = party_node.get(c["subject_party"])
        obj = typology_node.get(c["typology_id"])
        if subj is None or obj is None:
            stats["matches_typology_dangling"] += 1
            continue
        triples.append(triple(subj, P_MATCHES_TYPOLOGY, obj))
        stats["matches_typology_asserted"] += 1

    # --- FilingPosture: one node per posture_id, effective date as a plain
    #     string (Rule 5 -- never a typed date literal) --------------------
    posture_ids: set[str] = set()
    for p in sorted(postures, key=lambda r: r["posture_id"]):
        node = posture_uri(p["posture_id"])
        posture_ids.add(p["posture_id"])
        triples += [
            triple(node, RDF_TYPE, C_FILING_POSTURE),
            triple(node, RDFS_LABEL,
                   f"Filing posture {p['posture_id']} "
                   f"(effective {p['effective_from']})", literal=True),
            triple(node, P_POSTURE_EFFECTIVE_FROM, p["effective_from"],
                   literal=True),
            triple(node, P_PROVENANCE, p["provenance"], literal=True),
        ]
        stats["posture_nodes"] += 1

    # --- DispositionRule: one node per rule_id. rule_id already encodes
    #     (posture_id, typology_id, disposition) -- see module docstring
    #     for why no belongsToPosture/forTypology predicate is needed ----
    for r in sorted(rules, key=lambda r: r["rule_id"]):
        if r["posture_id"] not in posture_ids or r["typology_id"] not in typology_node:
            # A rule naming a posture or typology this run never saw would
            # silently claim a ruling for something that does not exist --
            # the same "counted but not created" shape the estate guards
            # against elsewhere. Refuse to project it.
            stats["rule_dangling"] += 1
            continue
        node = rule_uri(r["rule_id"])
        permitted_lit = "true" if r["permitted"] else "false"
        triples += [
            triple(node, RDF_TYPE, C_DISPOSITION_RULE),
            triple(node, RDFS_LABEL,
                   f"{r['disposition']} for {r['typology_id']} under "
                   f"{r['posture_id']}: permitted={permitted_lit}",
                   literal=True),
            triple(node, P_PERMITS_DISPOSITION, permitted_lit, literal=True),
            triple(node, P_PROVENANCE, r["provenance"], literal=True),
        ]
        stats["rule_nodes"] += 1

    return triples, stats


# ===========================================================================
# Idempotency -- retract-then-assert, scoped by subject (or subject+object)
# ===========================================================================

def _asserted_triples(predicate: str) -> list[tuple[str, str, bool]]:
    """(subject, object, is_literal) for EVERY currently-asserted triple on
    `predicate`, anywhere in the ledger -- filtered to ours by the caller,
    never trusted as ours just because the predicate matches."""
    q = f"SELECT ?s ?o FROM <{FLUREE_LEDGER_V2}> WHERE {{ ?s <{predicate}> ?o }}"
    out: list[tuple[str, str, bool]] = []
    for b in fluree.query(q).get("results", {}).get("bindings", []):
        out.append((b["s"]["value"], b["o"]["value"],
                    b["o"].get("type") == "literal"))
    return out


def _scoped_by_subject(predicates: list[str],
                       subjects: set[str]) -> list[tuple[str, str, str, bool]]:
    out: list[tuple[str, str, str, bool]] = []
    for pred in predicates:
        for s, o, lit in _asserted_triples(pred):
            if s in subjects:
                out.append((pred, s, o, lit))
    return out


def _scoped_by_object(predicate: str,
                      objects: set[str]) -> list[tuple[str, str, str, bool]]:
    """The `isBeneficialOwnerOf` exception: its SUBJECT is a node Wave 13b
    also uses for its OWN, unrelated assertions of this same predicate, so
    scoping by subject alone would retract those too. Scope by (subject,
    OBJECT) instead -- the object is always one of THIS loader's own
    AMLParty nodes."""
    return [(predicate, s, o, lit) for s, o, lit in _asserted_triples(predicate)
            if o in objects]


def _esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def reconcile(*, dry_run: bool, party_uris: set[str],
             typology_uris: set[str], posture_uris: set[str],
             rule_uris: set[str]) -> int:
    """Retract every triple this loader owns, scoped by subject (or, for
    `isBeneficialOwnerOf`, subject+object) -- never a blind predicate-wide
    delete. See the module docstring for why each population is safe."""
    class_uris = {C_AML_PARTY, C_TYPOLOGY, C_TYPOLOGY_PATTERN,
                  C_FILING_POSTURE, C_DISPOSITION_RULE}
    scoped = (
        _scoped_by_subject(AML_SUBJECT_PREDICATES, party_uris)
        + _scoped_by_subject(TYPOLOGY_SUBJECT_PREDICATES, typology_uris)
        + _scoped_by_subject(POSTURE_SUBJECT_PREDICATES, posture_uris)
        + _scoped_by_subject(RULE_SUBJECT_PREDICATES, rule_uris)
        + _scoped_by_subject(CLASS_SUBJECT_PREDICATES, class_uris)
        + _scoped_by_object(P_IS_BENEFICIAL_OWNER_OF, party_uris)
    )

    total = 0
    statements: list[str] = []
    by_pred: dict[str, int] = {}
    for pred, s, o, lit in scoped:
        by_pred[pred] = by_pred.get(pred, 0) + 1
        obj = f'"{_esc(o)}"' if lit else f"<{o}>"
        statements.append(f"<{s}> <{pred}> {obj} .")
        total += 1

    for pred, n in sorted(by_pred.items()):
        print(f"    {pred.rsplit('/', 1)[-1]:<24} {n:>6} asserted (ours)")

    if not statements:
        print("    nothing asserted -- nothing to retract")
        return 0
    print(f"    {total} triples to retract")
    if dry_run:
        print("    [dry-run] nothing retracted")
        return 0

    for i in range(0, len(statements), BATCH):
        fluree.update("DELETE DATA {\n" + "\n".join(statements[i:i + BATCH]) + "\n}")

    remaining = len(
        _scoped_by_subject(AML_SUBJECT_PREDICATES, party_uris)
        + _scoped_by_subject(TYPOLOGY_SUBJECT_PREDICATES, typology_uris)
        + _scoped_by_subject(POSTURE_SUBJECT_PREDICATES, posture_uris)
        + _scoped_by_subject(RULE_SUBJECT_PREDICATES, rule_uris)
        + _scoped_by_subject(CLASS_SUBJECT_PREDICATES, class_uris)
        + _scoped_by_object(P_IS_BENEFICIAL_OWNER_OF, party_uris)
    )
    print(f"    retracted . triples remaining on our own subjects: {remaining}")
    if remaining:
        print("    WARNING -- retraction incomplete; not proceeding to the rebuild.")
    return remaining


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--reconcile", action="store_true",
                    help="retract this loader's own triples before "
                         "rebuilding. Only needed when an artifact changed "
                         "a literal on an existing subject -- a plain "
                         "re-run against an unchanged artifact is already "
                         "idempotent because every subject and literal is "
                         "deterministic.")
    args = ap.parse_args()

    parties = load_parties()
    txns = load_transactions()
    cases = load_cases()
    typologies = load_typologies()
    ownership = load_ownership()
    postures, rules = load_policy()

    existing_bo = resolve_existing_beneficial_owners()
    print(f"  resolved {len(existing_bo)} existing BeneficialOwner nodes to reuse")
    print(f"  {len(parties)} parties . {len(txns)} transactions . "
          f"{len(cases)} cases . {len(typologies)} typologies . "
          f"{len(ownership)} ownership bindings . {len(postures)} postures . "
          f"{len(rules)} disposition rules")

    triples, stats = build(parties, txns, cases, typologies, ownership,
                           postures, rules, existing_bo)

    party_uris = {party_uri(p["party_id"]) for p in parties}
    typology_uris = {typology_uri(t["typology_id"]) for t in typologies}
    posture_uris = {posture_uri(p["posture_id"]) for p in postures}
    rule_uris = {rule_uri(r["rule_id"]) for r in rules}

    print("\nWave 17 Task 13/14 -- Fluree load\n")
    print(f"  AMLParty nodes                  {stats['amlparty_nodes']:>6}")
    print(f"  hasBeneficialOwner asserted     {stats['beneficial_owner_asserted']:>6}  "
          f"(dangling: {stats['beneficial_owner_dangling']})")
    print(f"  distinct transacting pairs      {stats['distinct_transacting_pairs']:>6}  "
          f"from {len(txns)} transaction rows")
    print(f"  transactedWith edges (2/pair)   {stats['transactedwith_edges']:>6}")
    print(f"  transaction self-loops skipped  {stats['transaction_self_loops']:>6}")
    print(f"  transaction dangling skipped    {stats['transaction_dangling']:>6}")
    print(f"  Typology/TypologyPattern nodes  {stats['typology_nodes']:>6}")
    print(f"  matchesTypology asserted        {stats['matches_typology_asserted']:>6}  "
          f"(dangling: {stats['matches_typology_dangling']})")
    print(f"  FilingPosture nodes             {stats['posture_nodes']:>6}")
    print(f"  DispositionRule nodes           {stats['rule_nodes']:>6}  "
          f"(dangling: {stats['rule_dangling']})")
    print(f"  total triples                   {len(triples):>6}")

    hard_failures = (stats["transaction_self_loops"]
                     or stats["transaction_dangling"]
                     or stats["matches_typology_dangling"]
                     or stats["beneficial_owner_dangling"]
                     or stats["rule_dangling"])
    if hard_failures:
        print("\n  FAIL -- one or more rows could not be projected cleanly; "
              "the floors this loader exists to preserve are not "
              "guaranteed. Refusing to write.")
        return 1

    if args.reconcile:
        print("\n  --reconcile: retracting this loader's own triples "
              "before rebuild")
        if reconcile(dry_run=args.dry_run, party_uris=party_uris,
                    typology_uris=typology_uris, posture_uris=posture_uris,
                    rule_uris=rule_uris):
            return 1

    if args.dry_run:
        print("\n  [dry-run] nothing written to Fluree")
        return 0

    for i in range(0, len(triples), BATCH):
        fluree.update("INSERT DATA {\n" + "\n".join(triples[i:i + BATCH]) + "\n}")
    print(f"\n  ledger now at t={fluree.ledger_t()} . "
          f"{fluree.count_triples():,} triples")
    return 0


if __name__ == "__main__":
    sys.exit(main())
