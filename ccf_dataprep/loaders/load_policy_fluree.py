#!/usr/bin/env python3
"""Wave 19 Task 8 — Regulation O insider designation, into Fluree + Postgres.

Created by Task 8; **Task 9 extends this same file** with `ex:LimitEnvelope`
and `ex:RegimeVersion` nodes (pre-flight ruling P1 — 8-before-9 is the right
order because Task 9 depends on Task 4's passage ids and Task 8 does not).

## What this loader writes, and where

    Postgres  ccf_v2.person     1 row   — the invented insider, provenance
                                          `synthetic — engineered`, alongside
                                          the estate's 210 existing PSC-derived
                                          synthetic people (953 rows total,
                                          keyed on `person_key`, never row
                                          position — see the module docstring
                                          of `generators/generate_insider_cases.py`)
    Fluree    R                 1 Person node, 2 structural edges, 1
                                          `ex:InsiderDesignation` node
    Fluree    P, T (Task 9)     3 `ex:RegimeVersion` nodes (`public`,
                                          CRR/PRA/Reg O, each carrying
                                          `>=1 ex:citesProvision`) and 1
                                          `ex:LimitEnvelope` node (the
                                          internal appetite,
                                          `synthetic — internal`)

Nothing is written to the exposure side. `ccf_v2.facility` and
`ccf_v2.legal_entity` are read-only here — see
`generators/generate_insider_cases.py::verify_related_interest`, which
already asserted live that the facility and its borrower are untouched real
data before this loader ever runs.

## One `InsiderDesignation` node, not two

12 CFR 215.4(b)(2) aggregates "that person, AND all related interests of
that person" into ONE $500,000 ceiling. `ex:designatedPerson`'s own binding
(`docs/ccf_dataprep_v2.md`) allows it to point at either a
`fibo-fnd-aap-ppl:Person` or a `cmns-org:LegalEntity` — nothing restricts a
single subject to one object — so this loader asserts ONE
`ex:InsiderDesignation` node with TWO `ex:designatedPerson` triples: one to
the invented Person node, one to Digital Turbine's existing entity node.
That is not a shortcut; it is the more faithful representation of what the
statute actually aggregates, and it also sidesteps inventing a second,
purely bookkeeping node with nothing else to say.

## Why the person-to-entity "control" tie is NOT a raw graph edge

The obvious edge — `person --controls--> relatedInterestNode`, reusing
Wave 3's `fibo-fnd-rel-rel:controls` — is semantically the cleanest choice,
but `validators/partition.py`'s "no client-360 attribute in the graph"
check enumerates every predicate on any node typed
`fibo-fnd-aap-ppl:Person` against a closed allowlist built for Wave 10's six
client-360 edges (`isEmployedBy`, `isOfficerOf`, `isDirectorOf`,
`coversClient`, `participatedIn`, `relatedToDeal`) plus the Wave 13b
identity edges. `controls` is not on that list, and widening a Wave 10-era
allowlist is Task 16's "Registration" job, not this task's. So the control
relationship is carried entirely by the `InsiderDesignation` node's two
`designatedPerson` triples plus its `citesProvision` reference to
12 CFR 215.2(n)(1) ("a company that is controlled by that person") — the
fact is asserted through the reified case record, exactly the way Task 7
carried `economicallyDependentOn`'s basis as a node-level literal rather
than a second graph shape.

`isDirectorOf` and `isOfficerOf` — both already on that allowlist, both
real FIBO terms bound since Wave 8 — ARE asserted directly,
Person -> reporting-bank node, because they cost nothing against the
allowlist and are the literal, structural "linking an invented person to
the reporting bank" the brief's Interfaces line asks for.

## `ex:InsiderDesignation` must be added to `PERMITTED_EX_TYPES`

Task 3 confirmed `InsiderDesignation` absent from FIBO under every prefix —
it is a genuine extension. `validators/partition.py`'s "no ex: type shadows
a FIBO term" check enumerates every `ex:` type actually asserted in the
ledger against a closed allowlist; asserting a brand-new `ex:` class without
adding it there turns that check red. This loader's commit therefore also
edits `validators/partition.py` to add exactly one entry — not a new
validator, not new scope, the minimum edit that keeps the existing
56-check suite honestly green rather than accidentally green.

## The guard

`assert_no_real_person_designated()` below is the brief's guard, corrected
twice against what was verified live 2026-08-27:

1. Both `person` and `psc_person` key on `person_key`, not `person_id`.
2. The Fluree Person node URI is `ex:person-{person_key}` (Wave 10's own
   convention — `loaders/load_fluree_wave10.py`, and independently
   confirmed by `validators/partition.py`'s existing "every Fluree person
   resolves to a row" check, which strips the SAME `person-` prefix). The
   brief's literal `local_name(uri)` — a bare last-path-segment split, as
   `validators/syndicate.py::local_name` defines it — would return
   `person-SYN-INSIDER-JPM-01`, which resolves NOTHING in `person_key`.
   `_designated_person_key()` below strips the prefix, matching
   `partition.py`'s own `.removeprefix("person-")` exactly, so the guard
   actually resolves instead of vacuously finding no offenders for the
   wrong reason.

    uv run loaders/load_policy_fluree.py --dry-run
    uv run loaders/load_policy_fluree.py
"""

from __future__ import annotations

import argparse
import json
import sys

from ccf import fluree
from ccf.config import EX, EX_EXTENSION_SCHEMA_NOTE, PG_SCHEMA_V2, REPO_ROOT, mongo_db, pg_connect
from loaders.load_collateral_wave9 import entity_uri_by_lei
from loaders.load_fluree_wave3 import triple, uri

S = PG_SCHEMA_V2
L = fluree.FLUREE_LEDGER_V2

RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
OWL_CLASS = "http://www.w3.org/2002/07/owl#Class"

FIBO = "https://spec.edmcouncil.org/fibo/ontology/"
C_PERSON = f"{FIBO}FND/AgentsAndPeople/People/Person"
P_IS_OFFICER_OF = f"{FIBO}BE/OwnershipAndControl/Executives/isOfficerOf"
P_IS_DIRECTOR_OF = f"{FIBO}BE/OwnershipAndControl/Executives/isDirectorOf"

#: Bound Task 3, verified absent from FIBO under every prefix.
C_INSIDER_DESIGNATION = f"{EX}InsiderDesignation"
P_DESIGNATED_PERSON = f"{EX}designatedPerson"
P_CITES_PROVISION = f"{EX}citesProvision"
P_ASSERTED_BY = f"{EX}assertedBy"
P_ASSERTED_ON = f"{EX}assertedOn"
P_PROVENANCE = f"{EX}provenance"

#: Task 9 additions -- also bound Task 3, also verified absent from FIBO
#: under every prefix (generators/verify_fibo_wave19.py).
C_REGIME_VERSION = f"{EX}RegimeVersion"
C_LIMIT_ENVELOPE = f"{EX}LimitEnvelope"
P_EFFECTIVE_FROM = f"{EX}effectiveFrom"
P_EFFECTIVE_TO = f"{EX}effectiveTo"
#: Minor 4 fix -- asserted only on the Reg O RegimeVersion node, whose
#: effectiveFrom is the eCFR retrieval date rather than a verified
#: commencement date. See generate_limit_envelope.py's module docstring.
P_EFFECTIVE_FROM_IS_SNAPSHOT = f"{EX}effectiveFromIsSnapshot"
P_LIMIT_PCT_OF_CAPITAL = f"{EX}limitPctOfCapital"
P_LIMIT_ABSOLUTE_USD = f"{EX}limitAbsoluteUsd"
P_GOVERNED_BY_REGIME = f"{EX}governedByRegime"

ARTIFACT = REPO_ROOT / "sources" / "screening" / "wave19_insider_case.json"
#: Task 9's own artifact -- generators/generate_limit_envelope.py.
LIMIT_ARTIFACT = REPO_ROOT / "sources" / "screening" / "wave19_limit_envelope.json"


def fetch_case_doc() -> dict:
    if not ARTIFACT.exists():
        print(f"FATAL: {ARTIFACT} does not exist. Run "
              "generators/generate_insider_cases.py first.")
        sys.exit(2)
    return json.loads(ARTIFACT.read_text())


def fetch_limit_envelope_doc() -> dict:
    """Task 9's own artifact. `generate_limit_envelope.py` already resolved
    every citation live and bounds-checked the internal appetite before
    writing this file -- this loader still re-verifies against the LIVE
    ledger after writing (see `assert_regime_anchoring()`), because a stale
    artifact re-read from disk is exactly the gap a re-run cannot see."""
    if not LIMIT_ARTIFACT.exists():
        print(f"FATAL: {LIMIT_ARTIFACT} does not exist. Run "
              "generators/generate_limit_envelope.py first.")
        sys.exit(2)
    return json.loads(LIMIT_ARTIFACT.read_text())


def tbox_triples() -> list[str]:
    """This loader is the sole author of `ex:InsiderDesignation`,
    `ex:RegimeVersion` and `ex:LimitEnvelope` in this ledger.
    `designatedPerson`/`citesProvision`/`assertedBy`/`assertedOn`/
    `effectiveFrom`/`effectiveTo`/`limitPctOfCapital`/`limitAbsoluteUsd`/
    `governedByRegime` are plain literal-or-object attributes and, per this
    codebase's established convention (`load_group_edges.py`'s own comment:
    "attribute literals are not given tbox entries here"), get no separate
    tbox entry — only the CLASSES do."""
    return [
        triple(C_INSIDER_DESIGNATION, RDF_TYPE, OWL_CLASS),
        triple(C_INSIDER_DESIGNATION, RDFS_LABEL, "insider designation", literal=True),
        triple(C_INSIDER_DESIGNATION, f"{EX}isFiboTerm", "false", literal=True),
        triple(C_INSIDER_DESIGNATION, f"{EX}schemaNote",
               EX_EXTENSION_SCHEMA_NOTE, literal=True),
        triple(C_REGIME_VERSION, RDF_TYPE, OWL_CLASS),
        triple(C_REGIME_VERSION, RDFS_LABEL, "regime version", literal=True),
        triple(C_REGIME_VERSION, f"{EX}isFiboTerm", "false", literal=True),
        triple(C_REGIME_VERSION, f"{EX}schemaNote",
               EX_EXTENSION_SCHEMA_NOTE, literal=True),
        triple(C_LIMIT_ENVELOPE, RDF_TYPE, OWL_CLASS),
        triple(C_LIMIT_ENVELOPE, RDFS_LABEL, "limit envelope", literal=True),
        triple(C_LIMIT_ENVELOPE, f"{EX}isFiboTerm", "false", literal=True),
        triple(C_LIMIT_ENVELOPE, f"{EX}schemaNote",
               EX_EXTENSION_SCHEMA_NOTE, literal=True),
    ]


def upsert_person(person: dict) -> None:
    """Idempotent by `person_key` (the table's PRIMARY KEY) — never by row
    position. `ccf_v2.person` already holds 953 rows from prior waves; this
    is exactly the "positional identity" defect class CLAUDE.md and Wave
    19's own instructions call out, and a PK-keyed UPSERT is what avoids it.
    """
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(
            f'INSERT INTO "{S}".person '
            "(person_key, person_key_source, cik, name_as_filed, "
            " display_name, owner_kind, name_last, name_first, name_middle, "
            " name_suffix, provenance, source, retrieved_at) "
            "VALUES (%(person_key)s, %(person_key_source)s, %(cik)s, "
            " %(name_as_filed)s, %(display_name)s, %(owner_kind)s, "
            " %(name_last)s, %(name_first)s, %(name_middle)s, %(name_suffix)s, "
            " %(provenance)s, %(source)s, now()) "
            "ON CONFLICT (person_key) DO UPDATE SET "
            "person_key_source=EXCLUDED.person_key_source, "
            "cik=EXCLUDED.cik, name_as_filed=EXCLUDED.name_as_filed, "
            "display_name=EXCLUDED.display_name, "
            "owner_kind=EXCLUDED.owner_kind, name_last=EXCLUDED.name_last, "
            "name_first=EXCLUDED.name_first, name_middle=EXCLUDED.name_middle, "
            "name_suffix=EXCLUDED.name_suffix, provenance=EXCLUDED.provenance, "
            "source=EXCLUDED.source, retrieved_at=now()",
            person,
        )
        conn.commit()


def resolve_bank_node() -> tuple[str, str]:
    """The reporting bank's Fluree node -- resolved, never constructed.

    `RSSD-{rssd}` is the URI local name `load_reporting_bank.py` actually
    minted. Two nodes share the bank's LEI in this ledger (the RSSD node
    AND a Wave 18 syndicate-member node), so resolving by LEI alone is
    ambiguous here -- go through `reporting_bank.rssd` instead.
    """
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT rssd, legal_name FROM "{S}".reporting_bank '
                    "WHERE role = 'reporting_bank'")
        row = cur.fetchone()
    if row is None:
        print("FATAL: no reporting_bank row with role='reporting_bank' -- "
              "run loaders/load_reporting_bank.py first.")
        sys.exit(2)
    rssd, legal_name = row
    return uri(f"RSSD-{rssd}"), legal_name


def _designated_person_key(iri: str) -> str:
    """Last path segment, `person-` prefix stripped if present.

    Matches `validators/partition.py`'s existing "every Fluree person
    resolves to a row" check byte-for-byte
    (`.rsplit('/', 1)[-1].removeprefix('person-')`) rather than the brief's
    bare `local_name(iri)`, which would leave the prefix on and resolve
    nothing in `person_key`. A non-person object (Digital Turbine's entity
    node, cleaned-name local) simply passes `removeprefix` unchanged and
    then matches no row in `person`/`psc_person` — harmless, since it is not
    a person at all.
    """
    return iri.rsplit("/", 1)[-1].removeprefix("person-")


def assert_no_real_person_designated() -> None:
    """No insider designation may name a person sourced from a real registry.

    Designations are Fluree nodes (§C assigns them to `R`); person provenance
    lives in Postgres (§C assigns it to `E`). So this reads ids from the graph
    and resolves provenance from the table -- crossing the stores to ask the
    question, rather than duplicating either side to make it local.

    The estate's real-person populations are `psc_person` (pseudonymised UK
    PSC data) and any `ccf_v2.person` row whose provenance is `public`. An
    insider designation touching either is a legal problem, not a style one.
    """
    q = (f"SELECT ?person FROM <{L}> WHERE {{ "
         f"?d a <{C_INSIDER_DESIGNATION}> ; <{P_DESIGNATED_PERSON}> ?person }}")
    keys = [_designated_person_key(r["person"]["value"])
            for r in fluree.query(q)["results"]["bindings"]]
    if not keys:
        raise AssertionError(
            "no insider designations found -- this guard would pass vacuously")

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT person_key FROM "{S}".person '
                    "WHERE person_key = ANY(%s) AND provenance = 'public'",
                    (keys,))
        offenders = [r[0] for r in cur.fetchall()]
        cur.execute(f'SELECT person_key FROM "{S}".psc_person '
                    "WHERE person_key = ANY(%s)", (keys,))
        offenders += [r[0] for r in cur.fetchall()]

    if offenders:
        raise AssertionError(
            f"insider designations name real people: {sorted(set(offenders))}")
    print(f"  guard OK — {len(keys)} designatedPerson target(s), 0 resolve "
          f"to a real-person row: {keys}")


def build_regime_and_limit_triples(doc: dict) -> tuple[list[str], dict[str, str]]:
    """Task 9. `doc` is `sources/screening/wave19_limit_envelope.json`,
    written by `generators/generate_limit_envelope.py`, which already
    resolved every `citesProvision` value against the live Mongo corpus and
    bounds-checked the internal appetite against the live ledger before
    writing it — this function trusts that artifact's *values* but not its
    freshness; `assert_regime_anchoring()` below re-checks the graph after
    the write, not the artifact.

    Returns `(triples, regime_node_by_key)` so the internal appetite's
    `ex:governedByRegime` edge can point at a URI this same run just
    minted, rather than constructing one blind the way the Wave 5
    phantom-borrower defect did.
    """
    triples: list[str] = []
    regime_node_by_key: dict[str, str] = {}

    for rv in doc["regime_versions"]:
        node = uri(f"regime-version-{rv['key']}")
        regime_node_by_key[rv["key"]] = node
        triples += [
            triple(node, RDF_TYPE, C_REGIME_VERSION),
            triple(node, RDFS_LABEL, rv["label"], literal=True),
            triple(node, P_EFFECTIVE_FROM, rv["effective_from"], literal=True),
            triple(node, P_PROVENANCE, rv["provenance"], literal=True),
        ]
        # effectiveTo is asserted ONLY when the regime version actually
        # closed (CRR, repealed 2021-12-31 by SI 2021/1078). PRA and Reg O
        # are still in force and get no triple at all -- see the module
        # docstring of generate_limit_envelope.py for why an absent triple
        # was chosen over a sentinel date.
        if rv.get("effective_to"):
            triples.append(triple(node, P_EFFECTIVE_TO, rv["effective_to"], literal=True))
        # Minor 4: Reg O's effectiveFrom is the eCFR retrieval date, not a
        # verified commencement date (CRR/PRA's are genuine). Marked
        # explicitly rather than left indistinguishable from the other two.
        if rv.get("effective_from_is_retrieval_snapshot"):
            triples.append(triple(node, P_EFFECTIVE_FROM_IS_SNAPSHOT, "true", literal=True))
        if rv.get("limit_pct_of_capital") is not None:
            triples.append(triple(node, P_LIMIT_PCT_OF_CAPITAL,
                                   str(rv["limit_pct_of_capital"]), literal=True))
        if rv.get("limit_absolute_usd") is not None:
            triples.append(triple(node, P_LIMIT_ABSOLUTE_USD,
                                   str(rv["limit_absolute_usd"]), literal=True))
        for c in rv["citations"]:
            triples.append(triple(node, P_CITES_PROVISION, c["passage_id"], literal=True))

    appetite = doc["internal_appetite"]
    envelope_node = uri(f"limit-envelope-{appetite['key']}")
    governed_node = regime_node_by_key.get(appetite.get("governed_by_regime"))
    triples += [
        triple(envelope_node, RDF_TYPE, C_LIMIT_ENVELOPE),
        triple(envelope_node, RDFS_LABEL, appetite["label"], literal=True),
        triple(envelope_node, P_LIMIT_PCT_OF_CAPITAL,
               str(appetite["limit_pct_of_capital"]), literal=True),
        triple(envelope_node, P_EFFECTIVE_FROM, appetite["effective_from"], literal=True),
        triple(envelope_node, P_PROVENANCE, appetite["provenance"], literal=True),
    ]
    if governed_node:
        triples.append(triple(envelope_node, P_GOVERNED_BY_REGIME, governed_node))

    return triples, regime_node_by_key


def existing_triples_for_subject(node: str) -> list[str]:
    """Every triple currently on `node`, rebuilt via `triple()` (so `esc()`
    runs on every literal -- `remediate_person_owner_kind.py`'s own
    `triples_where_subject` was flagged in `docs/known-issues.md` for
    skipping that and risking malformed Turtle on a value containing a
    quote; this reuses the same helper the write side already uses instead
    of re-implementing the escaping).
    """
    q = f"SELECT ?p ?o FROM <{L}> WHERE {{ <{node}> ?p ?o }}"
    out = []
    for b in fluree.query(q)["results"]["bindings"]:
        out.append(triple(node, b["p"]["value"], b["o"]["value"],
                           literal=(b["o"]["type"] == "literal")))
    return out


def retract_stale_regime_triples(nodes: list[str]) -> list[str]:
    """Fluree is append-only: when `generate_limit_envelope.py`'s citation
    set for a node CHANGES between runs (fix round 1 dropped LE 2.3 from
    the PRA version and added CRR Article 395(1)), a plain re-`INSERT DATA`
    adds the new triples beside the old ones rather than replacing them --
    the exact `docs/known-issues.md` #10.5 shape ("a blind predicate-wide
    DELETE is a data-loss hazard"), inverted: here the risk is UNDER-
    deletion, a stale citesProvision value silently surviving a correction.

    So every triple this loader owns on its own RegimeVersion/LimitEnvelope
    nodes is read back live and retracted before the fresh set is
    inserted -- scoped to these specific node URIs only (never a
    predicate-wide or ledger-wide DELETE), since this loader is the sole
    author of these nodes and nothing else in the estate points at them as
    subject.
    """
    stale: list[str] = []
    for node in nodes:
        stale += existing_triples_for_subject(node)
    if stale:
        fluree.update("DELETE DATA {\n" + "\n".join(stale) + "\n}")
    return stale


def assert_regime_anchoring() -> None:
    """§D's validation gates name 'regime anchoring' explicitly — every
    `RegimeVersion` must cite a real provision. Queried live against the
    ledger, never read back from the artifact this same run just wrote:
    that would only prove the write happened, not that the graph actually
    holds it. A `RegimeVersion` with zero `citesProvision` values is the
    brief's own words a load failure, not a warning.

    Fix round 1 (coordinator review): a bare count is not enough — a
    `citesProvision` value that resolves to NOTHING in Mongo (a stale
    passage_id, e.g. after a re-extraction changed a content-derived hash)
    would still pass a pure `COUNT(?c) > 0` check. So every citesProvision
    value is resolved back to a live Mongo passage here, and its provision
    label + first line of text are printed -- the provision-to-claim
    mapping made visible, not merely asserted.
    """
    q = f"SELECT ?rv ?label FROM <{L}> WHERE {{ ?rv a <{C_REGIME_VERSION}> ; <{RDFS_LABEL}> ?label }}"
    versions = {r["rv"]["value"]: r["label"]["value"]
                for r in fluree.query(q)["results"]["bindings"]}
    if not versions:
        raise AssertionError(
            "no RegimeVersion nodes found -- this guard would pass vacuously")

    db = mongo_db(write=False)
    uncited = []
    unresolved = []
    print("\n  regime anchoring — live from the ledger + Mongo, not the artifact:")
    for v, label in versions.items():
        q2 = f"SELECT ?c FROM <{L}> WHERE {{ <{v}> <{P_CITES_PROVISION}> ?c }}"
        passage_ids = [r["c"]["value"] for r in fluree.query(q2)["results"]["bindings"]]
        if not passage_ids:
            uncited.append(v)
            continue
        print(f"    {label}")
        for pid in passage_ids:
            row = db.passage.find_one({"passage_id": pid})
            if row is None:
                unresolved.append(f"{v} -> {pid}")
                continue
            first_line = row["text"].strip().splitlines()[0][:150]
            print(f"      {row['regime']}/{row['provision']} ({pid})")
            print(f"        \"{first_line}\"")

    if uncited:
        raise AssertionError(
            f"RegimeVersion node(s) with no citesProvision: {sorted(uncited)}")
    if unresolved:
        raise AssertionError(
            f"citesProvision value(s) that do not resolve to any Mongo "
            f"passage: {sorted(unresolved)}")
    print(f"\n  guard OK — {len(versions)} RegimeVersion node(s), "
          f"every citesProvision value resolves to a live passage")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    doc = fetch_case_doc()
    person = doc["person"]
    related_interest = doc["related_interest"]

    print("Wave 19 Task 8 — Regulation O insider designation\n")
    print(f"  insider          {person['display_name']} ({person['person_key']})")
    print(f"  related interest {related_interest['legal_name']} "
          f"({related_interest['lei']})")
    print(f"  facility         {related_interest['facility_id']}  "
          f"{related_interest['commitment_amount']:,.0f} "
          f"{related_interest['currency']} — "
          f"{related_interest['multiple_of_reg_o_cap']}x Reg O's $500,000, "
          f"{related_interest['pct_of_tier1_capital']}% of tier 1 capital "
          f"(CRR/PRA limit {related_interest['crr_pra_limit_pct']}%)")

    bank_node, bank_name = resolve_bank_node()
    entity_uri = entity_uri_by_lei()
    related_node = entity_uri.get(related_interest["lei"])
    if related_node is None:
        print(f"FATAL: {related_interest['lei']} has no Fluree node — "
              "Wave 3/6 must load it first.")
        return 2

    person_node = uri(f"person-{person['person_key']}")

    triples: list[str] = list(tbox_triples())
    triples += [
        triple(person_node, RDF_TYPE, C_PERSON),
        triple(person_node, RDFS_LABEL, person["display_name"], literal=True),
        triple(person_node, P_IS_DIRECTOR_OF, bank_node),
        triple(person_node, P_IS_OFFICER_OF, bank_node),
    ]

    designation_node = uri(f"insider-designation-{person['person_key']}")
    label = (f"Regulation O insider designation — {person['display_name']} "
             f"(insider of {bank_name}) and related interest "
             f"{related_interest['legal_name']}")
    triples += [
        triple(designation_node, RDF_TYPE, C_INSIDER_DESIGNATION),
        triple(designation_node, RDFS_LABEL, label, literal=True),
        triple(designation_node, P_DESIGNATED_PERSON, person_node),
        triple(designation_node, P_DESIGNATED_PERSON, related_node),
        triple(designation_node, P_CITES_PROVISION,
               doc["citations"]["insider_definition"], literal=True),
        triple(designation_node, P_CITES_PROVISION,
               doc["citations"]["related_interest_definition"], literal=True),
        triple(designation_node, P_CITES_PROVISION,
               doc["citations"]["absolute_cap"], literal=True),
        triple(designation_node, P_ASSERTED_BY, doc["asserted_by"], literal=True),
        triple(designation_node, P_ASSERTED_ON, doc["asserted_on"], literal=True),
        triple(designation_node, P_PROVENANCE, doc["provenance"], literal=True),
    ]

    print(f"\n  bank node        {bank_node}")
    print(f"  related node     {related_node}")
    print(f"  person node      {person_node}")
    print(f"  designation node {designation_node}")

    limit_doc = fetch_limit_envelope_doc()
    limit_triples, regime_node_by_key = build_regime_and_limit_triples(limit_doc)
    triples += limit_triples

    print("\nWave 19 Task 9 — limit envelope and regime version history")
    for rv in limit_doc["regime_versions"]:
        print(f"  {rv['label']:<38} "
              f"{rv['effective_from']} -> {rv['effective_to'] or '(open)'}  "
              f"node={regime_node_by_key[rv['key']]}")
    appetite = limit_doc["internal_appetite"]
    appetite_node = uri(f"limit-envelope-{appetite['key']}")
    print(f"  {appetite['label']:<38} {appetite['limit_pct_of_capital']}%  "
          f"node={appetite_node}")
    print(f"\n  triples to write {len(triples)}")

    if args.dry_run:
        print("\n  [dry-run] nothing written to Postgres or Fluree")
        return 0

    upsert_person(person)
    print(f"\n  Postgres: person {person['person_key']!r} upserted "
          f"(provenance={person['provenance']!r})")

    stale = retract_stale_regime_triples(
        list(regime_node_by_key.values()) + [appetite_node])
    if stale:
        print(f"  Fluree:   retracted {len(stale)} prior triple(s) on "
              "Task 9's own 4 nodes before reinserting the current "
              "artifact's set (unconditional retract-then-insert -- "
              "correct on a first run, a no-op-by-value re-run, and a run "
              "after the citation set actually changed alike)")

    before = fluree.count_triples()
    fluree.update("INSERT DATA {\n" + "\n".join(triples) + "\n}")
    after = fluree.count_triples()
    print(f"  Fluree:   t={fluree.ledger_t()} · triples {before:,} -> {after:,}")

    # --- verify: live, not the artifact's own numbers -----------------------
    n_designations = fluree.stable_scalar(
        f"SELECT (COUNT(DISTINCT ?d) AS ?n) FROM <{L}> WHERE "
        f"{{ ?d a <{C_INSIDER_DESIGNATION}> }}")
    n_targets = fluree.stable_scalar(
        f"SELECT (COUNT(?p) AS ?n) FROM <{L}> WHERE "
        f"{{ ?d a <{C_INSIDER_DESIGNATION}> ; <{P_DESIGNATED_PERSON}> ?p }}")
    n_regime_versions = fluree.stable_scalar(
        f"SELECT (COUNT(DISTINCT ?rv) AS ?n) FROM <{L}> WHERE "
        f"{{ ?rv a <{C_REGIME_VERSION}> }}")
    n_limit_envelopes = fluree.stable_scalar(
        f"SELECT (COUNT(DISTINCT ?le) AS ?n) FROM <{L}> WHERE "
        f"{{ ?le a <{C_LIMIT_ENVELOPE}> }}")
    print(f"\n  live: {n_designations} InsiderDesignation node(s), "
          f"{n_targets} designatedPerson target(s), "
          f"{n_regime_versions} RegimeVersion node(s), "
          f"{n_limit_envelopes} LimitEnvelope node(s)")

    failures = []
    if n_designations != 1:
        failures.append(f"expected 1 InsiderDesignation node, found {n_designations}")
    if n_targets != 2:
        failures.append(f"expected 2 designatedPerson targets, found {n_targets}")
    if n_regime_versions != len(limit_doc["regime_versions"]):
        failures.append(f"expected {len(limit_doc['regime_versions'])} "
                         f"RegimeVersion nodes, found {n_regime_versions}")
    if n_limit_envelopes != 1:
        failures.append(f"expected 1 LimitEnvelope node, found {n_limit_envelopes}")

    try:
        assert_no_real_person_designated()
    except AssertionError as exc:
        failures.append(str(exc))

    try:
        assert_regime_anchoring()
    except AssertionError as exc:
        failures.append(str(exc))

    if failures:
        for f in failures:
            print(f"  FAIL: {f}")
        return 1
    print("\n  OK — 1 designation, 2 targets, 0 real people named; "
          f"{n_regime_versions} regime versions all anchored, "
          "1 internal appetite envelope")
    return 0


if __name__ == "__main__":
    sys.exit(main())
