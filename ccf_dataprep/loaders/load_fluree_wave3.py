#!/usr/bin/env python3
"""Wave 3 — load the ontology and ownership graph into Fluree `fibo-v2`.

Fluree owns `R` (relationships) and `T`. Postgres owns entity attributes. So a
Fluree node here carries **`lei` plus a display label and nothing else** — the
first real test of single-writer discipline, and what the partition validator
checks.

Four provenance classes appear in this load and each is labelled on the edge
itself, because the demonstrations depend on the distinction being honest:

    public                GLEIF Level 2 relationships; Exhibit 21 subsidiaries
    synthetic — bridging  stub entities for Exhibit 21 subsidiaries with no LEI
    synthetic — engineered  depth chains and the cross-shareholding cycle
    derived               domestic ultimate parent — computed from public edges
                          by a deterministic rule, but not itself a filed fact

**Why engineering is needed here.** GLEIF Level 2 records direct and ultimate
parent only, and subsidiaries of US public filers rarely register their own
relationships, so the natural graph is ONE hop deep. Exhibit 21 adds breadth
but is a flat list — inferring hierarchy from indentation would produce
guessed edges indistinguishable from filed ones. §F needs >= 2 families at 4+
hops for the `depth` parameter to change any answer, so the depth is built
deliberately and marked as built.

No OWL inference: every entity is typed explicitly for **all seven roles** in the
Commons party chain, because a query for any one of them otherwise returns
nothing. Typing only the three the v1 loader asserted left every entity
unreachable by `FormalOrganization`, `Organization`, and `LegalPerson`.

    uv run loaders/load_fluree_wave3.py --dry-run
    uv run loaders/load_fluree_wave3.py
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys

from ccf import fluree
from ccf.config import EX, FLUREE_LEDGER_V2, REPO_ROOT

SCREEN = REPO_ROOT / "sources" / "screening"

# --- Bindings, from docs/ccf_dataprep_v2.md § Canonical FIBO IRI binding ----
FIBO = "https://spec.edmcouncil.org/fibo/ontology/"
CMNS = "https://www.omg.org/spec/Commons/"

# Wave 8 correction, part 2 -- see docs/known-issues.md §0.2.
#
# FIBO factored its foundational vocabulary out into the OMG Commons Ontology
# Library. `Agent`, `Party`, `Organization`, `FormalOrganization`, `LegalPerson`,
# and `LegalEntity` are NOT FIBO terms; only `Corporation` stays in FIBO, and it
# moved to BE/LegalEntities/CorporateBodies. The previous constants pointed at
# five IRIs that resolve to nothing.
#
# The subclass chain was invented too. v1 asserted a single line,
# Corporation < FormalOrganization < LegalEntity < Party < Agent. The real
# hierarchy is wider and inverts one link:
#
#     Agent
#     └── Party
#         ├── Organization
#         │   └── FormalOrganization
#         │       └── LegalEntity ──┐
#         └── LegalPerson ──────────┴── (LegalEntity has BOTH parents)
#                                        └── Corporation
#
# Under no-inference (rule 7) that matters concretely: typing an entity
# Party + LegalEntity + Corporation leaves it unreachable by a query for
# FormalOrganization, Organization, or LegalPerson -- three roles it genuinely
# holds. Correcting the IRIs alone would keep that gap, which is why this is a
# re-typing rather than a find-and-replace.
C_AGENT = f"{CMNS}PartiesAndSituations/Agent"
C_PARTY = f"{CMNS}PartiesAndSituations/Party"
C_ORGANIZATION = f"{CMNS}Organizations/Organization"
C_FORMAL_ORG = f"{CMNS}Organizations/FormalOrganization"
C_LEGAL_PERSON = f"{CMNS}Organizations/LegalPerson"
C_LEGAL_ENTITY = f"{CMNS}Organizations/LegalEntity"
C_CORPORATION = f"{FIBO}BE/LegalEntities/CorporateBodies/Corporation"

#: Every role a corporate node genuinely holds, in chain order. Asserted in full
#: because Fluree applies no inference.
CORPORATE_ROLES = [
    C_CORPORATION, C_LEGAL_ENTITY, C_LEGAL_PERSON, C_FORMAL_ORG,
    C_ORGANIZATION, C_PARTY, C_AGENT,
]

#: (subclass, superclass) -- the real chain, including LegalEntity's two parents.
CLASS_CHAIN = [
    (C_CORPORATION, C_LEGAL_ENTITY),
    (C_LEGAL_ENTITY, C_FORMAL_ORG),
    (C_LEGAL_ENTITY, C_LEGAL_PERSON),
    (C_FORMAL_ORG, C_ORGANIZATION),
    (C_ORGANIZATION, C_PARTY),
    (C_LEGAL_PERSON, C_PARTY),
    (C_PARTY, C_AGENT),
]
# Wave 8 correction. These previously read
#   BE/OwnershipAndControl/Ownership/hasOwnershipInterestIn
#   BE/OwnershipAndControl/Control/hasControllingInterestIn
# Neither property exists in FIBO, and neither module resolves -- both 404.
# They came from the v1 starter set, which Wave 0 never re-verified. See
# docs/known-issues.md §0.1. Both replacements are confirmed against published
# Production by generators/verify_fibo_wave8_confirm.py.
#
# `controls` is DECLARED in FND/Relations/Relations and only *refined* (domain
# Party) by FND/OwnershipAndControl/Control. Binding it under the Control
# namespace would reproduce exactly the defect this corrects.
P_OWNS = f"{FIBO}FND/OwnershipAndControl/Ownership/owns"
P_CONTROLS = f"{FIBO}FND/Relations/Relations/controls"

# GLEIF's ultimate-parent endpoint returns the ultimate ACCOUNTING CONSOLIDATING
# parent, which is a global concept -- GLEIF has no domestic-ultimate notion.
# These edges were previously loaded as P_CONTROLS, which conflated two
# different things: an ultimate consolidating parent is not "control" in FIBO's
# sense, and FIBO carries the exact property for it.
#
# Consequence worth stating: once these move off P_CONTROLS, the estate holds
# ZERO genuine control edges. Control-without-ownership (golden shares,
# board-appointment rights, shareholder agreements) is precisely what
# corporate-family-tree exists to surface, so that gap is now visible rather
# than masked. Generating those edges is outstanding manufacture work.
P_GLOBAL_ULTIMATE = f"{FIBO}BE/OwnershipAndControl/CorporateControl/hasGlobalUltimateParent"
P_DOMESTIC_ULTIMATE = f"{FIBO}BE/OwnershipAndControl/CorporateControl/hasDomesticUltimateParent"

RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
RDFS_SUBCLASS = "http://www.w3.org/2000/01/rdf-schema#subClassOf"
OWL_CLASS = "http://www.w3.org/2002/07/owl#Class"
OWL_OBJPROP = "http://www.w3.org/2002/07/owl#ObjectProperty"

#: Target graph size. §F asks ~500 entities and ~800 ownership edges; Exhibit
#: 21 alone yields 1,635 subsidiaries, so it is sampled rather than loaded whole.
TARGET_ENTITIES = 500
MAX_SUBS_PER_ANCHOR = 20

BATCH = 400
SEED = 20260816          # fixed so the engineered graph is reproducible

SAFE = re.compile(r"[^A-Za-z0-9]+")


def local_name(name: str, prefix: str = "") -> str:
    cleaned = SAFE.sub("", name.title())[:48] or "Entity"
    return f"{prefix}{cleaned}"


def uri(local: str) -> str:
    return f"{EX}{local}"


def esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def triple(s: str, p: str, o: str, *, literal: bool = False) -> str:
    obj = f'"{esc(o)}"' if literal else f"<{o}>"
    return f"<{s}> <{p}> {obj} ."


def tbox_triples() -> list[str]:
    """Class and property declarations. The ontology IS the schema."""
    out: list[str] = []
    for cls in CORPORATE_ROLES:
        out.append(triple(cls, RDF_TYPE, OWL_CLASS))
        out.append(triple(cls, RDFS_LABEL, cls.rsplit("/", 1)[-1], literal=True))
    for sub, sup in CLASS_CHAIN:
        out.append(triple(sub, RDFS_SUBCLASS, sup))
    for prop in (P_OWNS, P_CONTROLS, P_GLOBAL_ULTIMATE, P_DOMESTIC_ULTIMATE):
        out.append(triple(prop, RDF_TYPE, OWL_OBJPROP))
        out.append(triple(prop, RDFS_LABEL, prop.rsplit("/", 1)[-1], literal=True))
    # No subPropertyOf axiom between them. v1 asserted control ⊑ ownership;
    # that was invented too. In FIBO both `owns` and `controls` are
    # subPropertyOf `playsActiveRoleThatDirectlyAffects` -- siblings, not
    # sub/super. Re-asserting the old axiom would contradict the ontology.
    #
    # Consequence for queries: callers must match BOTH predicates explicitly.
    # That was previously a no-inference workaround; it is now simply correct.
    return out


def entity_triples(local: str, label: str, lei: str | None,
                   provenance: str) -> list[str]:
    """A Fluree node: lei + label + explicit types. No other attributes.

    Typed for every role that will be queried — Fluree runs without reasoning,
    so a Corporation is not returned by a query for Party unless said so.
    """
    s = uri(local)
    out = [triple(s, RDF_TYPE, role) for role in CORPORATE_ROLES]
    out += [
        triple(s, RDFS_LABEL, label, literal=True),
        triple(s, f"{EX}provenance", provenance, literal=True),
    ]
    if lei:
        out.append(triple(s, f"{EX}lei", lei, literal=True))
    return out


#: Predicates whose SUBJECT is the child rather than the parent.
#:
#: FIBO's parent/child object properties do not all run the same way, and the
#: two families read almost identically at a call site:
#:
#:     fibo-fnd-...:owns                         parent -> child
#:     fibo-be-oac-cctl:hasGlobalUltimateParent  child  -> PARENT
#:
#: Every caller here holds the fact as (parent, child) because that is how
#: GLEIF states it, so the orientation belongs in ONE place rather than at
#: each site. It previously lived nowhere: the same `(p, c)` order was emitted
#: for all four predicates, which was right for `owns` and `controls` and
#: backwards for the two ultimate-parent ones. 139 edges asserted that each
#: group head's ultimate parent was its own subsidiary.
#:
#: Verified against FIBO's published instance data rather than the predicate
#: name -- `Business Entity Data (BED) B.V. NL hasGlobalUltimateParent
#: DepositoryTrustAndClearingCorporation`, where the subject is the
#: subsidiary -- and against 140 GLEIF consolidation records, which matched
#: 0 as stored and 103 reversed.
CHILD_SUBJECT_PREDICATES = frozenset({P_GLOBAL_ULTIMATE, P_DOMESTIC_ULTIMATE})


def edge_triples(parent_local: str, child_local: str, *,
                 predicate: str, provenance: str) -> list[str]:
    """One triple for a parent->child fact, oriented per the predicate."""
    if predicate in CHILD_SUBJECT_PREDICATES:
        return [triple(uri(child_local), predicate, uri(parent_local))]
    return [triple(uri(parent_local), predicate, uri(child_local))]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    rng = random.Random(SEED)

    anchors = json.loads((SCREEN / "anchors_final.json").read_text())["anchors"]
    gleif = json.loads((SCREEN / "gleif_relationships.json").read_text())
    ex21 = json.loads((SCREEN / "exhibit21.json").read_text())["filers"]

    triples: list[str] = list(tbox_triples())
    locals_by_lei: dict[str, str] = {}
    entity_count = 0
    edge_count = 0
    counts = {"public": 0, "synthetic — bridging": 0, "synthetic — engineered": 0}
    engineered_notes: list[str] = []

    # --- anchors -----------------------------------------------------------
    for a in anchors:
        local = local_name(a.get("gleif_legal_name") or a["sec_name"])
        # Guard against two anchors normalising to the same local name.
        while local in locals_by_lei.values():
            local += "X"
        locals_by_lei[a["lei"]] = local
        triples += entity_triples(
            local, a.get("gleif_legal_name") or a["sec_name"], a["lei"], "public"
        )
        entity_count += 1

    # --- GLEIF-discovered entities and their real edges --------------------
    for lei, name in gleif["entities"].items():
        if lei in locals_by_lei:
            continue
        local = local_name(name)
        while local in locals_by_lei.values():
            local += "X"
        locals_by_lei[lei] = local
        triples += entity_triples(local, name, lei, "public")
        entity_count += 1

    # Dedup on (parent, child, predicate), not (parent, child). GLEIF returns
    # each pair from three endpoints, but direct-parent and ultimate-parent are
    # genuinely different relationship types where they differ -- collapsing
    # them would discard real structure, not just duplication.
    seen_edges: set[tuple[str, str, str]] = set()
    for e in gleif["edges"]:
        p, c = e["parent_lei"], e["child_lei"]
        if p not in locals_by_lei or c not in locals_by_lei or p == c:
            continue
        # GLEIF's ultimate parent is the ultimate ACCOUNTING CONSOLIDATING
        # parent -- a global concept. It is not "control", which is what this
        # previously asserted.
        predicate = (P_GLOBAL_ULTIMATE if e["edge_type"] == "hasUltimateParent"
                     else P_OWNS)
        key3 = (locals_by_lei[p], locals_by_lei[c], predicate)
        if key3 in seen_edges:
            continue
        seen_edges.add(key3)
        key = (locals_by_lei[p], locals_by_lei[c])
        triples += edge_triples(key[0], key[1], predicate=predicate,
                                provenance="public")
        edge_count += 1
        counts["public"] += 1

    # --- domestic ultimate parent, DERIVED ---------------------------------
    # GLEIF has no domestic-ultimate concept, so this cannot be fetched. It is
    # the highest ancestor sharing the entity's own jurisdiction, walked over
    # public direct-parent edges. Deterministic, but a modelling choice rather
    # than a filed fact -- so it is labelled `derived`, never `public`.
    #
    # This is the property country-of-risk turns on: for a GB subsidiary of a US
    # parent the domestic answer is GB and the global answer is US, and a single
    # collapsed `hasUltimateParent` cannot express the difference.
    juris_by_lei: dict[str, str] = {}
    for e in gleif["edges"]:
        code = (e.get("jurisdiction") or "").strip()
        if not code:
            continue
        # `jurisdiction` describes the entity at the FAR end of the fetch, which
        # is the parent for parent-endpoints and the child for direct-children.
        subject = e["child_lei"] if e["edge_type"] == "hasDirectChild" else e["parent_lei"]
        juris_by_lei.setdefault(subject, code)
    for a in anchors:
        if a.get("legal_jurisdiction"):
            juris_by_lei.setdefault(a["lei"], a["legal_jurisdiction"])

    direct_parent: dict[str, str] = {}
    for e in gleif["edges"]:
        if e["edge_type"] in ("hasDirectParent", "hasDirectChild"):
            direct_parent.setdefault(e["child_lei"], e["parent_lei"])

    def country(lei: str) -> str | None:
        code = juris_by_lei.get(lei)
        return code.split("-")[0] if code else None

    domestic_count = 0
    for child in list(locals_by_lei):
        home = country(child)
        if not home:
            continue
        highest, cursor, guard = None, child, 0
        while guard < 12:
            guard += 1
            parent = direct_parent.get(cursor)
            if not parent or parent == cursor or country(parent) != home:
                break
            highest, cursor = parent, parent
        if not highest or highest not in locals_by_lei:
            continue
        key3 = (locals_by_lei[highest], locals_by_lei[child], P_DOMESTIC_ULTIMATE)
        if key3 in seen_edges:
            continue
        seen_edges.add(key3)
        triples += edge_triples(locals_by_lei[highest], locals_by_lei[child],
                                predicate=P_DOMESTIC_ULTIMATE,
                                provenance="derived")
        edge_count += 1
        domestic_count += 1
        counts["derived"] = counts.get("derived", 0) + 1
    engineered_notes.append(
        f"domestic ultimate parent: {domestic_count} edges DERIVED by walking "
        f"direct-parent within one country (GLEIF supplies global only)"
    )

    # --- Exhibit 21 subsidiaries as bridging stubs -------------------------
    #
    # `taken` is GLOBAL across filers, and that is the whole point.
    #
    # The dedup here used to be `local in locals_by_lei.values() or local in
    # made`, and `made` is rebuilt per filer -- so a local name already
    # created under a DIFFERENT anchor fell through both tests, and the second
    # filer re-asserted the same node with its own label and hung its own
    # `owns` edge on it. Two filers then shared one subsidiary. Three of them
    # did, all Exhibit 21 table headers that a broken regex let through, and
    # the worst read as THE HAIN CELESTIAL GROUP owning Genesis Energy's
    # offshore pipelines three hops down. known-issues §19.6.
    #
    # Two filers listing a genuinely same-named subsidiary is not the same
    # company either, so the collision gets a DISTINCT local rather than being
    # skipped: skipping would drop a real subsidiary with no trace, which is
    # the harder failure to ever notice.
    stub_locals: dict[str, list[str]] = {}
    taken: set[str] = set(locals_by_lei.values())
    collisions = 0
    for filer in ex21:
        subs = filer.get("subsidiaries") or []
        if not subs:
            continue
        parent_local = locals_by_lei.get(filer["lei"])
        if not parent_local:
            continue
        chosen = subs[:MAX_SUBS_PER_ANCHOR]
        made: list[str] = []
        for sub in chosen:
            if entity_count >= TARGET_ENTITIES:
                break
            local = base = local_name(sub["name"], prefix="Sub")
            if local in taken:
                collisions += 1
                seq = 2
                while local in taken:
                    local = f"{base}N{seq}"
                    seq += 1
            taken.add(local)
            triples += entity_triples(
                local, sub["name"], None, "synthetic — bridging"
            )
            entity_count += 1
            triples += edge_triples(parent_local, local, predicate=P_OWNS,
                                    provenance="public")
            edge_count += 1
            counts["synthetic — bridging"] += 1
            made.append(local)
        if made:
            stub_locals[parent_local] = made
    if collisions:
        engineered_notes.append(
            f"{collisions} subsidiary names collided with a local already "
            f"taken and were given a distinct `...N2` local rather than "
            f"merged onto the existing node (§19.6)")

    # --- ENGINEERED: depth chains -----------------------------------------
    # §F needs >= 2 families at 4+ hops. Natural depth is 1. Built, and marked.
    deep_parents = [p for p, kids in stub_locals.items() if len(kids) >= 4][:3]
    for idx, parent_local in enumerate(deep_parents):
        chain = stub_locals[parent_local][:4]
        # Re-parent a flat run into a chain: anchor -> a -> b -> c -> d
        for i in range(len(chain) - 1):
            triples += edge_triples(chain[i], chain[i + 1], predicate=P_OWNS,
                                    provenance="synthetic — engineered")
            triples.append(triple(uri(chain[i + 1]), f"{EX}edgeProvenance",
                                  "synthetic — engineered", literal=True))
            edge_count += 1
            counts["synthetic — engineered"] += 1
        engineered_notes.append(
            f"depth chain under {parent_local}: {' -> '.join(chain)}"
        )

    # --- ENGINEERED: cross-shareholding cycle ------------------------------
    # §1.4 makes cycles a headline capability; GLEIF Level 2 is a clean
    # hierarchy and genuine cycles are effectively absent at this scale.
    cycle_locals = [
        local_name("Meridian Holdings SA", prefix="Cyc"),
        local_name("Calder Industrial NV", prefix="Cyc"),
        local_name("Thornbury Capital Ltd", prefix="Cyc"),
    ]
    for local, label in zip(cycle_locals,
                            ["Meridian Holdings S.A.", "Calder Industrial N.V.",
                             "Thornbury Capital Ltd"]):
        triples += entity_triples(local, label, None, "synthetic — engineered")
        entity_count += 1
    for i in range(3):
        a_local, b_local = cycle_locals[i], cycle_locals[(i + 1) % 3]
        triples += edge_triples(a_local, b_local, predicate=P_OWNS,
                                provenance="synthetic — engineered")
        triples.append(triple(uri(b_local), f"{EX}edgeProvenance",
                              "synthetic — engineered", literal=True))
        edge_count += 1
        counts["synthetic — engineered"] += 1
    # Attach the cycle to a real family so traversal from an anchor reaches it.
    if deep_parents:
        triples += edge_triples(deep_parents[0], cycle_locals[0],
                                predicate=P_OWNS,
                                provenance="synthetic — engineered")
        edge_count += 1
        counts["synthetic — engineered"] += 1
    engineered_notes.append(
        f"cross-shareholding cycle: {' -> '.join(cycle_locals)} -> {cycle_locals[0]}"
    )

    print(f"Wave 3 — Fluree load into {FLUREE_LEDGER_V2}\n")
    print(f"  entities   {entity_count:>6}")
    print(f"  edges      {edge_count:>6}")
    print(f"  triples    {len(triples):>6}")
    print(f"\n  edge provenance:")
    for k, v in counts.items():
        print(f"    {k:24s} {v:>5}")
    print(f"\n  ENGINEERED, labelled as such:")
    for note in engineered_notes:
        print(f"    {note}")

    if args.dry_run:
        print("\n  DRY RUN — nothing written to Fluree.")
        return 0

    print(f"\n  writing in batches of {BATCH}...")
    for i in range(0, len(triples), BATCH):
        chunk = triples[i:i + BATCH]
        body = "INSERT DATA {\n" + "\n".join(chunk) + "\n}"
        fluree.update(body)
        if (i // BATCH) % 5 == 0:
            print(f"    {min(i + BATCH, len(triples)):>6}/{len(triples)}")

    t = fluree.ledger_t()
    total = fluree.count_triples()
    print(f"\n  loaded. ledger t={t}, {total:,} triples in current state")
    return 0


if __name__ == "__main__":
    sys.exit(main())
