#!/usr/bin/env python3
"""Wave 19 Task 6/7 — `connectedTo` edges from the real GLEIF control graph,
plus Task 7's engineered `economicallyDependentOn` edges.

§C assigns exactly one element to Fluree here: the control-derived edges
that make a "connected group" computable. It assigns nothing else — no
group node, no group id, no membership table. `docs/wave19-design.md` §4
is explicit: *"Fluree holds edges only... Nothing anywhere stores 'these
nine entities are a group.'"* `validators/large_exposure.py` (Task 15) walks
these edges fresh on every run and forms the groups itself. Materialising a
group here would be exactly the failure CLAUDE.md warns about twice over:
a second store owning what Fluree already owns, and a cache that goes stale
the moment an ownership edge changes.

Source: `ccf_v2.corporate_ownership_record`, ACTIVE rows only — 140
`IS_DIRECTLY_CONSOLIDATED_BY` + 140 `IS_ULTIMATELY_CONSOLIDATED_BY` records
over 166 distinct LEIs (verified live 2026-08-27; INACTIVE rows exist in the
same table and are excluded, matching Wave 13b's own load-time filter).

## Two predicates carry each fact, not a reified node

The brief asks for `ex:connectedTo` *and* "the GLEIF relationship type...
onto the edge, so the basis is visible." A plain RDF triple has no slot for
a second value, and 96 of the 184 distinct (child, parent) pairs here carry
BOTH relationship types (a child whose direct parent is also its ultimate
parent) — so a per-edge literal would need either reification (a node per
fact, the shape `load_bo_chains_wave13b.py` uses for a percentage that
genuinely has nowhere else to live) or a node-level literal (the shape
`load_control_edges.py` and `load_fluree_wave3.py` use for their
single-edge-per-subject control/cycle nodes — explicitly the WRONG shape
per `load_bo_chains_wave13b.py`'s own docstring, where the same trick put an
edge's provenance on a Person node that could carry other edges too).

Neither is needed here, because FIBO already has the exact vocabulary:
`fibo-be-le-lei:isDirectlyConsolidatedBy` and
`...isUltimatelyConsolidatedBy` (both `owl:ObjectProperty`, subPropertyOf
`...isConsolidatedBy`, `rdfs:range cmns-org:LegalEntity`) — found by
grepping `sources/fibo/dev.fibo-quickstart.ttl` directly rather than
trusting that Task 3's semantic-binding pass was exhaustive (it searched
`isConnectedWith` / `connectedWith` / `isRelatedTo` for the *group* edge and
never tried the consolidation vocabulary, even though every one of these
three properties' `cmns-av:adaptedFrom` note names GLEIF's RR-CDF format by
name — the exact format `corporate_ownership_record` was built from). Using
the specific predicate as the edge itself makes the relationship type
visible in the predicate name, with no reification and no ambiguous
node-level literal: a child with both relationship types to the same parent
gets two distinct, unambiguous triples. `ex:connectedTo` is asserted
alongside as the generic edge the brief's verification script and Task 15's
validator both walk; it naturally collapses to one triple per (child,
parent) pair regardless of how many relationship types produced it — RDF
triples are a set, and connectivity does not care about multiplicity.

These three FIBO terms are new bindings this loader adds to
`docs/ccf_dataprep_v2.md` (not found by Task 3) — see that file's Wave 19
extension section. Vault mirror needs refreshing for them.

## Provenance is a node property here, not an edge property

Every established Fluree loader in this repo asserts `ex:provenance` on the
ENTITY NODE (`validators/conditions.py` queries it that way throughout),
never on an edge, and that is sufficient here: every one of the 166
entities this loader touches is a real, GLEIF-registered LEI, so its node
carries `ex:provenance "public"` — set on the 37 nodes this loader mints,
left untouched on the 129 that already exist (single-writer discipline: a
node's provenance is not this loader's to overwrite). No boolean or literal
is attached to describe the EDGES' provenance, because there is no
heterogeneity here for a marker to distinguish — this loader draws every
edge from one `WHERE relationship_status = 'ACTIVE'` filter over one public
table, so "provenance public" is a true statement about the entire
population this loader writes, recorded here in prose and enforced by the
loader reading no other source.

## Extend, do not duplicate

166 LEIs appear across the 280 ACTIVE records. Checked live before writing
anything: 129 already have a Fluree node (from Wave 3's original entity
load — `entity_uri_by_lei()`, the resolve-not-construct helper
`load_collateral_wave9.py` established and `load_control_edges.py` already
reuses). The other 37 are `registry_company` GLEIF entities (Wave 13b) that
were never pushed into Fluree by any loader — confirmed by grep, zero
loaders write Fluree triples from `registry_company`. Those 37 are minted
here, once, using the SAME local-name/URI scheme and the SAME
`entity_triples()` shape Wave 3 established (lei + label + the 7-role
corporate type chain + provenance, nothing else) — not a second, competing
node scheme. A constructed `ex:{lei}` URI instead of a resolved one is the
Wave 5 phantom-borrower defect in miniature: a syntactically valid edge that
resolves nowhere.

    uv run loaders/load_group_edges.py --dry-run
    uv run loaders/load_group_edges.py

Idempotent: `INSERT DATA` of stable triples keyed on (subject, predicate,
object). Re-running advances `t` and leaves the triple population unchanged.

## Task 7 — the engineered `economicallyDependentOn` edges

§C calls this "the one relationship the public estate cannot supply" — an
analyst's judgment, not a fetched fact. Reads
`sources/screening/wave19_dependency_edges.json`
(`generators/generate_dependency_edges.py`) and, for each of its 4 edges,
resolves BOTH ends through the same `entity_uri_by_lei()` this loader already
uses for `connectedTo` — no new node scheme, no minting (all 8 LEIs already
resolve, 5 from Wave 3, 3 minted by this same loader's Task 6 run).

**Why the edge carries its own attributes as node-level literals, and why
that is not the Task 6 trap.** Task 6's docstring rejects a node-level
literal for edge provenance specifically because a subject there could carry
TWO relationship types to different objects (96 of 184 pairs did). Here each
subject has been chosen to carry exactly ONE outgoing
`economicallyDependentOn` edge — `build()` in the generator refuses to write
the artifact if that ever stops being true — so `ex:assertedBy`,
`ex:assertedOn` and `ex:dependencyBasis` on the subject node are unambiguous:
there is only one edge they could describe. `ex:dependencyBasis` also embeds
the depended-upon party's name and LEI in its text (the same self-describing
convention `comparabilityBasis` uses in Wave 12, per
`docs/ccf_dataprep_v2.md`), so the string still names its edge even if a
future task adds a second outgoing edge to one of these subjects.

**Provenance goes on `ex:edgeProvenance`, never `ex:provenance`.** All 8
entities touched here are real, GLEIF-registered public companies —
`ex:provenance "public"` is already correct on their nodes and must not be
touched. It is the RELATIONSHIP that is invented, so `synthetic —
engineered` goes on the estate's existing edge-provenance predicate
(`ex:edgeProvenance`, bound Wave 13b, already used for the second BO cycle's
edges) instead of overwriting a true statement about the entity with a false
one about it.

**`economicallyDependentOn` is a direct triple, not reified**, because the
brief's own verification script (and Task 15's validator) queries
`?a <economicallyDependentOn> ?b` directly — a `BeneficialOwnership`-style
reification node would put the traversal one hop away from where every
consumer expects it.

    uv run loaders/load_group_edges.py --dry-run
    uv run loaders/load_group_edges.py
"""

from __future__ import annotations

import argparse
import collections
import json
import sys

from ccf import fluree
from ccf.config import EX, EX_EXTENSION_SCHEMA_NOTE, PG_SCHEMA_V2, REPO_ROOT, pg_connect
from loaders.load_collateral_wave9 import entity_uri_by_lei
from loaders.load_fluree_wave3 import entity_triples, local_name, triple, uri

S = PG_SCHEMA_V2

RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
RDFS_SUBPROP = "http://www.w3.org/2000/01/rdf-schema#subPropertyOf"
OWL_OBJPROP = "http://www.w3.org/2002/07/owl#ObjectProperty"

P_CONNECTED_TO = f"{EX}connectedTo"

#: GLEIF's own RR-CDF vocabulary, already declared in FIBO. See docstring.
LEI_NS = "https://spec.edmcouncil.org/fibo/ontology/BE/LegalEntities/LEIEntities/"
P_IS_CONSOLIDATED_BY = f"{LEI_NS}isConsolidatedBy"
P_IS_DIRECTLY_CONSOLIDATED_BY = f"{LEI_NS}isDirectlyConsolidatedBy"
P_IS_ULTIMATELY_CONSOLIDATED_BY = f"{LEI_NS}isUltimatelyConsolidatedBy"

#: child_lei --predicate--> parent_lei, subject = child per RR-CDF's own
#: StartNode/EndNode convention (`load_gleif_l2_wave13b.py`'s own comment).
RELATIONSHIP_PREDICATE = {
    "IS_DIRECTLY_CONSOLIDATED_BY": P_IS_DIRECTLY_CONSOLIDATED_BY,
    "IS_ULTIMATELY_CONSOLIDATED_BY": P_IS_ULTIMATELY_CONSOLIDATED_BY,
}

#: Task 7 — engineered economic-dependency edges. Bound Task 3
#: (economicallyDependentOn, assertedBy, assertedOn) and this task
#: (dependencyBasis, verified absent from FIBO under every prefix using
#: verify_fibo_wave19.py's own find_any_prefix_subject method before minting).
P_ECONOMICALLY_DEPENDENT_ON = f"{EX}economicallyDependentOn"
P_ASSERTED_BY = f"{EX}assertedBy"
P_ASSERTED_ON = f"{EX}assertedOn"
P_DEPENDENCY_BASIS = f"{EX}dependencyBasis"
#: Bound Wave 13b for exactly this shape: a fact about a RELATIONSHIP, not a
#: node, with no reified node to hang ex:provenance on.
P_EDGE_PROVENANCE = f"{EX}edgeProvenance"

DEPENDENCY_ARTIFACT = REPO_ROOT / "sources" / "screening" / "wave19_dependency_edges.json"


def tbox_triples() -> list[str]:
    """Declare every predicate this loader is first to use in this ledger.

    Live-checked 2026-08-27: none of these four IRIs has any triple in
    `fibo-v2` yet. Undeclared, a consumer sees a bare IRI with no label and
    no way to tell "real FIBO term this project hasn't typed yet" from
    "invented" — the exact gap `ex:isFiboTerm` / `ex:schemaNote` exist to
    close for the one genuine extension (`connectedTo`).
    """
    out = [
        triple(P_IS_CONSOLIDATED_BY, RDF_TYPE, OWL_OBJPROP),
        triple(P_IS_CONSOLIDATED_BY, RDFS_LABEL, "is consolidated by", literal=True),
        triple(P_IS_DIRECTLY_CONSOLIDATED_BY, RDF_TYPE, OWL_OBJPROP),
        triple(P_IS_DIRECTLY_CONSOLIDATED_BY, RDFS_LABEL,
               "is directly consolidated by", literal=True),
        triple(P_IS_DIRECTLY_CONSOLIDATED_BY, RDFS_SUBPROP, P_IS_CONSOLIDATED_BY),
        triple(P_IS_ULTIMATELY_CONSOLIDATED_BY, RDF_TYPE, OWL_OBJPROP),
        triple(P_IS_ULTIMATELY_CONSOLIDATED_BY, RDFS_LABEL,
               "is ultimately consolidated by", literal=True),
        triple(P_IS_ULTIMATELY_CONSOLIDATED_BY, RDFS_SUBPROP, P_IS_CONSOLIDATED_BY),
        triple(P_CONNECTED_TO, RDF_TYPE, OWL_OBJPROP),
        triple(P_CONNECTED_TO, RDFS_LABEL, "connected to", literal=True),
        triple(P_CONNECTED_TO, f"{EX}isFiboTerm", "false", literal=True),
        triple(P_CONNECTED_TO, f"{EX}schemaNote", EX_EXTENSION_SCHEMA_NOTE, literal=True),
        # Task 7. assertedBy/assertedOn/dependencyBasis/edgeProvenance are
        # plain literal attributes and, per this codebase's own convention
        # (grep finds no `ex:provenance`/`ex:validFrom`/`ex:edgeProvenance`
        # tbox declaration anywhere), attribute literals are not given tbox
        # entries here — only the relationship predicate itself is.
        triple(P_ECONOMICALLY_DEPENDENT_ON, RDF_TYPE, OWL_OBJPROP),
        triple(P_ECONOMICALLY_DEPENDENT_ON, RDFS_LABEL,
               "economically dependent on", literal=True),
        triple(P_ECONOMICALLY_DEPENDENT_ON, f"{EX}isFiboTerm", "false", literal=True),
        triple(P_ECONOMICALLY_DEPENDENT_ON, f"{EX}schemaNote",
               EX_EXTENSION_SCHEMA_NOTE, literal=True),
    ]
    return out


def fetch_dependency_doc() -> dict:
    """The engineered edges Task 7 generated. Fails loudly if absent —
    running this loader without generate_dependency_edges.py having run
    first must not silently skip the engineered condition."""
    if not DEPENDENCY_ARTIFACT.exists():
        print(f"FATAL: {DEPENDENCY_ARTIFACT} does not exist. Run "
              "generators/generate_dependency_edges.py first.")
        sys.exit(2)
    return json.loads(DEPENDENCY_ARTIFACT.read_text())


def verify_analyst(analyst_id: str) -> None:
    """The generator reuses an existing `ccf_v2.banker` id rather than
    inventing one. Confirmed live, not assumed from the generator's own
    comment — a typo in the id would otherwise silently point nowhere."""
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(
            f'SELECT full_name, role, desk FROM "{PG_SCHEMA_V2}".banker '
            f'WHERE banker_id = %s',
            (analyst_id,),
        )
        row = cur.fetchone()
    if row is None:
        print(f"FATAL: analyst {analyst_id!r} not found in "
              f'"{PG_SCHEMA_V2}".banker -- dependencyBasis would cite an '
              "identifier that resolves nowhere.")
        sys.exit(2)
    print(f"  analyst {analyst_id} confirmed: {row[0]} ({row[1]}, {row[2]})")


def dependency_triples(doc: dict, entity_uri: dict[str, str]) -> list[str]:
    """Task 7's 4 engineered edges. Each subject carries exactly ONE
    outgoing economicallyDependentOn edge (enforced by the generator), which
    is what makes the node-level literals below unambiguous -- see the
    module docstring's Task 7 section."""
    out: list[str] = []
    seen_subjects: set[str] = set()
    for edge in doc["edges"]:
        dep_lei, held_lei = edge["dependent_lei"], edge["depended_lei"]
        if dep_lei not in entity_uri or held_lei not in entity_uri:
            missing = [l for l in (dep_lei, held_lei) if l not in entity_uri]
            print(f"FATAL: dependency edge references LEI(s) with no Fluree "
                  f"node: {missing}. Task 6 must run first.")
            sys.exit(2)
        subject = entity_uri[dep_lei]
        if subject in seen_subjects:
            # The generator already refuses to write a repeat; this is the
            # loader's own independent check of the same invariant, since a
            # hand-edited artifact could reintroduce it silently.
            print(f"FATAL: {subject} already carries an "
                  "economicallyDependentOn edge -- a second one would make "
                  "the node-level assertedBy/assertedOn/dependencyBasis "
                  "literals ambiguous.")
            sys.exit(2)
        seen_subjects.add(subject)
        target = entity_uri[held_lei]
        out += [
            triple(subject, P_ECONOMICALLY_DEPENDENT_ON, target),
            triple(subject, P_ASSERTED_BY, doc["analyst"], literal=True),
            triple(subject, P_ASSERTED_ON, edge["asserted_on"], literal=True),
            triple(subject, P_DEPENDENCY_BASIS, edge["basis"], literal=True),
            triple(subject, P_EDGE_PROVENANCE, doc["provenance"], literal=True),
        ]
    return out


def fetch_active_records() -> list[tuple[str, str, str]]:
    """(child_lei, parent_lei, relationship_type) for every ACTIVE record."""
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(
            f'SELECT child_lei, parent_lei, relationship_type '
            f'FROM "{S}".corporate_ownership_record '
            f'WHERE relationship_status = %s',
            ("ACTIVE",),
        )
        return [(c.strip(), p.strip(), t) for c, p, t in cur.fetchall()]


def fetch_names(leis: set[str]) -> dict[str, str]:
    """legal_name for LEIs with no Fluree node yet.

    `registry_company` first, `legal_entity` as a fallback — live-checked
    2026-08-27 that every LEI missing a node is in `registry_company`, but
    the fallback costs nothing and protects against that changing silently.
    """
    if not leis:
        return {}
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(
            f'SELECT lei, legal_name FROM "{S}".registry_company WHERE lei = ANY(%s)',
            (list(leis),),
        )
        names = dict(cur.fetchall())
        still_missing = leis - names.keys()
        if still_missing:
            cur.execute(
                f'SELECT lei, legal_name FROM "{S}".legal_entity WHERE lei = ANY(%s)',
                (list(still_missing),),
            )
            names.update(cur.fetchall())
    return names


def components(edges: list[tuple[str, str]]) -> int:
    """Union-find over (a, b) pairs. Identical to the brief's verify script."""
    par: dict[str, str] = {}

    def find(x: str) -> str:
        par.setdefault(x, x)
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x

    for a, b in edges:
        ra, rb = find(a), find(b)
        if ra != rb:
            par[ra] = rb
    return len(collections.Counter(find(x) for x in list(par)))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    records = fetch_active_records()
    by_type = collections.Counter(t for _, _, t in records)
    all_leis = {lei for c, p, _ in records for lei in (c, p)}

    print("Wave 19 Task 6 — connectedTo edges from the real GLEIF control graph\n")
    print(f"  ACTIVE records            {len(records)}   {dict(by_type)}")
    print(f"  distinct entities         {len(all_leis)}")

    existing = entity_uri_by_lei()
    missing_leis = sorted(all_leis - existing.keys())
    names = fetch_names(set(missing_leis))

    used_locals = {u.rsplit("/", 1)[-1] for u in existing.values()}
    mint_triples: list[str] = []
    minted_uri: dict[str, str] = {}
    for lei in missing_leis:
        name = names.get(lei, lei)
        local = local_name(name)
        while local in used_locals:
            local += "2"
        used_locals.add(local)
        minted_uri[lei] = uri(local)
        mint_triples += entity_triples(local, name, lei, "public")

    entity_uri = {**existing, **minted_uri}
    print(f"  nodes already in Fluree   {len(all_leis) - len(missing_leis)}")
    print(f"  nodes minted this run     {len(missing_leis)}")
    if missing_leis:
        sample = missing_leis[0]
        print(f"    e.g. {sample} -> {names.get(sample, sample)!r}")
    unresolved = [lei for lei in all_leis if lei not in entity_uri]
    if unresolved:
        print(f"  UNRESOLVED (no name, no node): {unresolved}")
        return 1

    edge_triples: list[str] = list(tbox_triples()) + mint_triples
    connected_pairs: set[tuple[str, str]] = set()
    for child, parent, rel_type in records:
        c_uri, p_uri = entity_uri[child], entity_uri[parent]
        edge_triples.append(triple(c_uri, RELATIONSHIP_PREDICATE[rel_type], p_uri))
        connected_pairs.add((c_uri, p_uri))
    for c_uri, p_uri in sorted(connected_pairs):
        edge_triples.append(triple(c_uri, P_CONNECTED_TO, p_uri))

    print(f"\n  typed consolidation edges  {len(records)}  (1 per ACTIVE record)")
    print(f"  connectedTo edges          {len(connected_pairs)}  "
          f"(distinct (child, parent) pairs — {len(records) - len(connected_pairs)} "
          "record(s) share a pair with both relationship types)")

    # --- Task 7: engineered economicallyDependentOn edges -------------------
    print("\n  Task 7 — engineered economicallyDependentOn edges")
    dep_doc = fetch_dependency_doc()
    verify_analyst(dep_doc["analyst"])
    # `entity_uri` here is `existing` (ledger-wide, not filtered to all_leis)
    # merged with this run's mints, so it already resolves every LEI the
    # dependency edges name, whether or not that LEI appears in any ACTIVE
    # ownership record -- TransDigm Group Inc, one of Task 7's four subjects,
    # has zero connectedTo edges of any kind and is exactly the case this
    # matters for.
    dep_triples = dependency_triples(dep_doc, entity_uri)
    edge_triples += dep_triples
    print(f"  economicallyDependentOn edges  {len(dep_doc['edges'])}  "
          f"({len(dep_triples)} triples: edge + assertedBy + assertedOn + "
          "dependencyBasis + edgeProvenance per edge)")

    print(f"\n  total triples to write     {len(edge_triples)}")

    if args.dry_run:
        print("\n  [dry-run] nothing written to Fluree")
        return 0

    before = fluree.count_triples()
    fluree.update("INSERT DATA {\n" + "\n".join(edge_triples) + "\n}")
    after = fluree.count_triples()
    print(f"\n  ledger t={fluree.ledger_t()} · triples {before:,} -> {after:,}")

    # --- verify: Task 6's shape, unchanged ----------------------------------
    def live_edges(predicates: list[str]) -> list[tuple[str, str]]:
        out: list[tuple[str, str]] = []
        for p in predicates:
            q = (f"SELECT ?a ?b FROM <{fluree.FLUREE_LEDGER_V2}> WHERE "
                 f"{{ ?a <{p}> ?b }}")
            out += [(r["a"]["value"], r["b"]["value"])
                    for r in fluree.query(q)["results"]["bindings"]]
        return out

    control_edges = live_edges([P_CONNECTED_TO])
    n_control = components(control_edges)
    print(f"  live query: connectedTo edges {len(control_edges)}, "
          f"components {n_control}")
    if n_control != 26:
        print(f"  MISMATCH: expected 26 components, ledger shows {n_control}. "
              "Not adjusting the assertion -- investigate before proceeding.")
        return 1
    print("  OK — 26 components confirmed against the live ledger")

    # --- Task 7's own required check: the merge actually merges -------------
    # Identical union-find to the brief's Step 3 script, run against the
    # live ledger rather than a fixture: a merge that does not merge is the
    # failure this check exists to catch, and a stored flag could not see it.
    both_edges = live_edges([P_CONNECTED_TO, P_ECONOMICALLY_DEPENDENT_ON])
    n_both = components(both_edges)
    print(f"\n  live query: connectedTo + economicallyDependentOn edges "
          f"{len(both_edges)}, components {n_both}")
    if not n_both < n_control:
        print(f"  MISMATCH: both-basis components ({n_both}) is not lower "
              f"than control-basis ({n_control}) -- the dependency edges "
              "merged nothing, connection_basis is not consequential.")
        return 1
    print(f"  OK — both-basis components ({n_both}) < control-basis "
          f"({n_control}); the dependency edges are consequential")
    return 0


if __name__ == "__main__":
    sys.exit(main())
