#!/usr/bin/env python3
"""Wave 17 Task 17 — the seven §F floors for `aml-typology-match`.

## What this is not

This is a **build-time validator, not an operator**. See CLAUDE.md, "What
'operator' means -- and what it does not". An Operator is a runtime SDK
entity: registered, composed into a plan, executed in the Data Plane,
serving a principal at request time. This script registers nothing,
composes into no plan, serves no principal, emits no contract, and writes
nothing to any store. It runs against the loaded estate and asks one
question: does this data support what the spec claims?

The `assemble()` helper below is the one place that could be mistaken for
runtime machinery. It is not a projection engine: it exists so
`sar_confidentiality_holds()` can ask what an unauthorised perspective
would actually SEE, which is the only way to tell "the field is absent"
from "the field is null." It resolves elements from in-memory snapshots
taken once, in `Context`, and it is never invoked by anything but this
file's own floors.

## What it proves, and how

Seven conditions, each recomputed from the stores on every run. Not one of
them reads a stored score, a cached rank, a boolean flag, or a label:

1. TYPOLOGY ANCHORING  -- every `ex:anchoredToPassage` object resolves to a
                          Mongo passage that EXISTS and is non-empty, and
                          no `ex:matchesTypology` target lacks an anchor.
2. DEPTH THREE         -- the Fluree `ex:transactedWith` graph is walked
                          live and pairs at EXACTLY distance 3 are counted.
                          `requires_depth` is a label and is never read.
3. POSTURE FLIP        -- the same disposition for the same typology is
                          evaluated under two `as_of` values that resolve
                          to two different postures, and the answers must
                          DIFFER.
4. SAR CONFIDENTIALITY -- `l1` (never `l2`) assembles its projection plan
                          over every alert, and nothing it yields may
                          reveal that a SAR exists -- by key, by
                          identifier, by a key that appears only on the
                          filed cases, or by any NUMBER that separates the
                          filed cases from the unfiled ones within a
                          typology.
5. OFAC BAND           -- the declared near-match's similarity is
                          recomputed from LIVE Postgres names with
                          `ccf.aml.similarity` (never `quick_ratio`, and
                          never the stored `measured_similarity`).
6. RENDERINGS DIFFER   -- the three perspectives assemble different
                          ELEMENT SETS, and every SAR-bearing element two
                          of them SHARE must render different VALUES for
                          them -- which is what proves `l2`'s exclusion
                          from the confidential SARs is enforced.
7. NO PATH TO REAL     -- CLAUDE.md rule 2's safety property. The AML
                          island must not reach a real legal entity or a
                          real natural person over ANY predicate, walked
                          from both ends.

    uv run validators/aml_typology.py

Exit code is non-zero if any of the seven fails.

## Why the pure helpers are separated out

`build_adjacency`, `walk_for_crossings`, `exact_depth_pairs`,
`resolve_posture`, `parse_rule_id`, `scan_for_sar_leakage`,
`numeric_quantities` and `separating_quantities` take plain Python and
return plain Python. That is not tidiness: it is what lets
`validators/test_aml_typology.py` plant a crossing edge in a THROWAWAY
in-memory adjacency and require the walk to catch it, without writing that
edge to an append-only ledger where it could never be removed. This wave
has already found five tests passing for reasons unrelated to the property
they were named for; a floor that cannot be shown to fail is worse than no
floor.

## Two traps this file is written around

**`?s <p> ?s` does not enforce equality on this Fluree build**
(`docs/known-issues.md` §27) -- it matches every edge. Nothing here relies
on a repeated-variable pattern. `FILTER NOT EXISTS` is unaffected and is
used as a correct anti-join.

**`rdf:type` is excluded from the all-predicate adjacency.** Class
membership is not a path between two entities. Left in, every node in the
ledger would connect to every other through shared class nodes, and floor 7
would fail for a reason that has nothing to do with the data.
"""
from __future__ import annotations

import collections
import datetime
import json
import re
import sqlite3
import sys
from dataclasses import dataclass
from functools import cached_property

from ccf.aml import SAR_REVEALING_ELEMENT_NAMES, similarity
from ccf.config import (
    EX,
    FLUREE_LEDGER_V2 as L,
    MONGO_DB_V2,
    PG_SCHEMA_V2 as S,
    SQLITE_PATH,
    mongo_db,
    pg_connect,
)

RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"

#: The band the one declared OFAC near-match must land in: a genuine match,
#: but not a duplicate. Too low and screening confidence is never exercised;
#: too high and it is effectively the same name. Same band Task 7's own test
#: asserts, restated here because this floor recomputes the figure rather
#: than reading the artifact that test reads.
OFAC_BAND = (0.70, 0.92)

#: The perspective this product's SAR-confidentiality property binds
#: absolutely. **`l1`, never `l2`.** `l1` appears in NO
#: `visible_to_perspectives` set at all; `l2` is excluded from the
#: `confidential` SARs and sees every other one, so a floor built on `l2`
#: would be satisfied on the confidential minority and violated on the rest.
#:
#: Stated as a shape, not as counts. The counts moved once already -- Task
#: 15's fix rounds re-selected the filing half and the SAR population
#: changed with it -- and prose that pins a figure is prose the next data
#: change refutes. The live figures are recomputed from `ctx.sar_rows`
#: (SQLite `sar_classification`, the source) and printed by
#: `sar_confidentiality_holds` on every run.
BLIND_PERSPECTIVE = "l1"


# ===========================================================================
# Pure helpers -- no store access, unit-tested against planted fixtures
# ===========================================================================

def build_adjacency(triples) -> dict[str, set[str]]:
    """UNDIRECTED adjacency from `(subject, predicate, object)` triples,
    with `rdf:type` dropped.

    Both directions are recorded for every edge. A one-directional
    adjacency cannot see an edge whose SUBJECT is the real entity, and that
    is exactly the edge a careless loader writes (`REAL ex:owns AMLP-0003`).
    Reachability between two entities is a symmetric question regardless of
    which way the predicate happens to point.
    """
    adj: dict[str, set[str]] = collections.defaultdict(set)
    for s, p, o in triples:
        if p == RDF_TYPE:
            continue
        adj[s].add(o)
        adj[o].add(s)
    return adj


def reachable(adj, start, depth: int | None = None) -> set[str]:
    """Every node within `depth` hops of `start` (inclusive of `start`).

    `start` may be a single node or an iterable of them, in which case the
    walk is multi-source and the result is the union.

    `depth=None` walks the whole connected component. The frontier only ever
    expands nodes not already seen, so a node found at depth 2 is never
    re-expanded at depth 3 -- which is what makes `exact_depth_pairs` an
    exact-distance measure rather than an at-most measure.
    """
    seen = {start} if isinstance(start, str) else set(start)
    frontier = set(seen)
    steps = 0
    while frontier and (depth is None or steps < depth):
        nxt: set[str] = set()
        for node in frontier:
            nxt |= adj.get(node, set()) - seen
        seen |= nxt
        frontier = nxt
        steps += 1
    return seen


def exact_depth_pairs(adj, nodes, depth: int) -> set[tuple[str, str]]:
    """Ordered `(a, b)` pairs where `b` sits at EXACTLY `depth` hops from
    `a` -- reachable at `depth`, not reachable at `depth - 1`.

    This is the shape of claim `depth_three_holds` needs and no count can
    establish: "invisible at depth 2, visible at depth 3" is a statement
    about a set difference. One extra edge anywhere along the path collapses
    it, so the walk has to be exact rather than approximately right.
    """
    out: set[tuple[str, str]] = set()
    for a in nodes:
        near = reachable(adj, a, depth - 1)
        far = reachable(adj, a, depth)
        for b in far - near:
            out.add((a, b))
    return out


def walk_for_crossings(adj, real, starts) -> tuple[bool, str]:
    """Does any path in `adj` connect `starts` to `real`? Walked from BOTH
    ends.

    Returns `(ok, detail)` -- `ok` is True when the two populations sit in
    disjoint components. `real` and `starts` are compared as sets, so a
    node that is in both is itself a crossing.

    Walking from both ends is not belt-and-braces on a symmetric adjacency;
    it is the property the brief names, and it is what keeps this function
    correct if it is ever handed a DIRECTED adjacency -- which is exactly
    what `validators/test_aml_typology.py` hands it when it plants an edge
    whose subject is the real entity.
    """
    real = set(real)
    starts = set(starts)

    # Two multi-source walks, one per direction. Cheap: two traversals, not
    # one per node. The expensive per-node walk below runs only when
    # something HAS crossed, and only to say which pair did.
    hit_forward = sorted(reachable(adj, starts) & real)
    hit_backward = sorted(reachable(adj, real) & starts)

    if not hit_forward and not hit_backward:
        return True, (f"{len(starts)} start node(s), {len(real)} real "
                      f"node(s), 0 crossings in either direction")

    parts = []
    if hit_forward:
        pairs = [(s, sorted(reachable(adj, s) & real)[:3]) for s in sorted(starts)
                 if reachable(adj, s) & real]
        parts.append("real node(s) reachable FROM the AML island: "
                     + "; ".join(f"{s} -> {t}" for s, t in pairs[:3]))
    if hit_backward:
        pairs = [(r, sorted(reachable(adj, r) & starts)[:3]) for r in sorted(real)
                 if reachable(adj, r) & starts]
        parts.append("AML node(s) reachable FROM the real population: "
                     + "; ".join(f"{r} -> {t}" for r, t in pairs[:3]))
    return False, "; ".join(parts)


def resolve_posture(posture_dates: dict[str, str], as_of: str) -> str | None:
    """The posture in force at `as_of`: the latest `effective_from` that is
    not after `as_of`. Returns None when `as_of` predates every posture.

    Ties are broken by `posture_id` so the answer is deterministic, but two
    postures sharing an effective date could not be told apart by `as_of`
    at all -- `posture_flip_holds` refuses that case explicitly rather than
    letting this function pick one.
    """
    eligible = [(d, p) for p, d in posture_dates.items() if d <= as_of]
    if not eligible:
        return None
    return max(eligible)[1]


def parse_rule_id(rule_id: str, posture_ids, typology_ids
                   ) -> tuple[str, str, str] | None:
    """Split `RULE-<posture>-<typology>-<disposition>` into its three parts.

    `loaders/load_fluree_wave17.py` deliberately asserts no
    `belongsToPosture` / `forTypology` predicate -- the id already encodes
    all three. Splitting on hyphens would be wrong, because every one of the
    three parts contains them (`POST-2025-01`, `TYP-STRUCT`,
    `close-no-action`). So the split is driven by the posture and typology
    id sets read from the SAME ledger, and an id naming something those sets
    do not contain returns None rather than being mis-split into a plausible
    triple.
    """
    if not rule_id.startswith("RULE-"):
        return None
    rest = rule_id[len("RULE-"):]
    for posture in sorted(posture_ids, key=len, reverse=True):
        if not rest.startswith(posture + "-"):
            continue
        tail = rest[len(posture) + 1:]
        for typology in sorted(typology_ids, key=len, reverse=True):
            if tail.startswith(typology + "-"):
                disposition = tail[len(typology) + 1:]
                if disposition:
                    return posture, typology, disposition
    return None


def scan_for_sar_leakage(obj, forbidden_ids) -> list[str]:
    """Every way `obj` betrays that a SAR exists, as a list of findings.

    Three mechanisms, because they fail independently:

    1. **A key** in `ccf.aml.SAR_REVEALING_ELEMENT_NAMES`, at ANY depth. The
       key is the finding -- `"sar_id": None` has still told the reader a
       SAR slot exists for this alert. CLAUDE.md's word for this floor is
       ABSENT, not null.
    2. **A string value** that is one of those same names -- an element name
       carried in a list rather than used as a key.
    3. **A forbidden identifier** appearing anywhere in any string, as a
       substring, so a case id embedded in free-text reasoning is caught as
       readily as one sitting in its own field.

       `forbidden_ids` is supplied by the CALLER and is not a synonym for
       "every case id". Wave 17's engineered cases split into a filed and an
       unfiled half (Task 15, fix rounds 2-3), so "this alert has a
       `case_id`" does NOT imply a SAR exists -- an equivalence that held
       only in the wave's original 1:1 version and that this docstring
       asserted until it was corrected here. `Context.forbidden_ids`
       recomputes the set that does leak by joining SQLite's actual SAR rows
       back to their alerts: the SAR ids, and the case ids of the cases that
       filed. Exposing one of those still leaks by inference; the count is
       whatever the departmental store currently says, and is never written
       down here.
    """
    forbidden_ids = set(forbidden_ids)
    findings: list[str] = []

    def walk(node, path: str) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                here = f"{path}.{k}" if path else str(k)
                if k in SAR_REVEALING_ELEMENT_NAMES:
                    findings.append(f"SAR-revealing key at {here}: {k!r}")
                walk(v, here)
        elif isinstance(node, (list, tuple, set)):
            for i, item in enumerate(node):
                walk(item, f"{path}[{i}]")
        elif isinstance(node, str):
            if node in SAR_REVEALING_ELEMENT_NAMES:
                findings.append(f"SAR-revealing element name as a value at "
                                f"{path}: {node!r}")
            for bad in forbidden_ids:
                if bad and bad in node:
                    findings.append(f"forbidden identifier {bad!r} in the "
                                    f"value at {path}")

    walk(obj, "")
    return findings


def key_paths(obj) -> set[str]:
    """Every dict key path in `obj`, ignoring list indices and values.

    Used to prove no key appears on the SAR-bearing alerts and only on
    those: a field present for 30 alerts and absent for the other 120 is a
    perfect discriminator even when its value never names a case.
    """
    paths: set[str] = set()

    def walk(node, path: str) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                here = f"{path}.{k}" if path else str(k)
                paths.add(here)
                walk(v, here)
        elif isinstance(node, (list, tuple, set)):
            for item in node:
                walk(item, path + "[]")

    walk(obj, "")
    return paths


#: `PREFIX-1234`. Matched, then checked for MEMBERSHIP in the estate's own
#: id sets before being masked -- the pattern alone would also swallow a
#: genuine measurement that happened to be written that way.
_ID_TOKEN_RE = re.compile(r"\b[A-Z]{2,8}-[0-9]+\b")

#: Comma-grouped and decimal numbers: `8,000`, `1,867,013.44`, `87.3`, `6`.
#: A bare `\d+` would read `$8,000` as the two numbers 8 and 000.
_NUMBER_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")

_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def numeric_quantities(obj, identifiers) -> dict[str, float]:
    """Every NUMBER a reader could extract from `obj`, keyed by where it sat.

    A whole ISO date becomes its ordinal, so `raised_at` participates as one
    quantity rather than as the three numbers `2025`, `08`, `12`. Every other
    string yields its numbers in order, keyed `path#i`. Booleans are skipped:
    `True` is a category, not a measurement, and `float(True) == 1.0` would
    silently smuggle it in as one.

    **Entity identifiers are masked out first**, by membership in
    `identifiers` -- the estate's own party, alert, case and SAR id sets --
    never by pattern alone. Membership, not shape, is the rule: `QQ-42` is
    left alone and read as the number 42, because a token that merely LOOKS
    like an id might be a genuine reading written that way.

    `AMLP-0168` is a nominal label that happens to be spelled with digits;
    reading it as the quantity 168 and then asserting something about its
    ORDERING is meaningless. This is a load-bearing decision, so here is the
    whole of it.

    With masking OFF, exactly one quantity in this estate separates filed
    from unfiled: the importer party id inside the trade-based `trigger`,
    read as an integer. The filed cases name `AMLP-0016/0049/0077` and the
    unfiled ones `AMLP-0089/0168/0199` -- perfectly disjoint.

    **There is no process that could link those two things.** Party ids are
    assigned alphabetically by `legal_name`; the TBML importer is drawn by
    `rng.choice`; the filing half is chosen by `sha256(salt:case_id)`.
    Three independent generators with no shared input. The absence of a
    mechanism is the argument -- the arithmetic below only says the
    observation needs no explaining.

    And it does not. For a 3-of-6 split, the probability that the filed
    three are exactly the low three or exactly the high three is
    `2 / C(6,3)` = 10%. Across the four typology groups, the probability of
    at least one such group is `1 - 0.9**4` ~= **34%**. One occurrence is
    the modal outcome, not a surprise.

    Masking is what stops `separating_quantities` from reporting that
    arithmetic accident as a disclosure.
    """
    identifiers = set(identifiers)
    out: dict[str, float] = {}

    def walk(node, path: str) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{path}.{k}" if path else str(k))
        elif isinstance(node, (list, tuple, set)):
            for item in node:
                walk(item, path + "[]")
        elif isinstance(node, bool):
            return
        elif isinstance(node, (int, float)):
            out[path] = float(node)
        elif isinstance(node, str):
            if _ISO_DATE_RE.match(node):
                out[path] = float(datetime.date.fromisoformat(node).toordinal())
                return
            masked = _ID_TOKEN_RE.sub(
                lambda m: "<ID>" if m.group(0) in identifiers else m.group(0),
                node)
            for i, found in enumerate(_NUMBER_RE.findall(masked)):
                out[f"{path}#{i}"] = float(found.replace(",", ""))

    walk(obj, "")
    return out


def separating_quantities(observations) -> tuple[int, list[str]]:
    """Which quantities let a reader tell the FILED cases from the UNFILED
    ones, within a group.

    `observations` is `(group, is_filed, {quantity: value})`. Returns
    `(quantities_compared, findings)`. Three ways a quantity separates, and
    they fail independently:

    * the group holds only filed cases, or only unfiled ones -- then the
      GROUP is itself the rule, and no quantity inside it is needed;
    * the quantity is present on one side of the split and absent on the
      other -- presence discriminates even when the value never does;
    * the two value ranges are disjoint, so some threshold splits them
      cleanly.

    Range overlap is a deliberately weak test and it is the right one here.
    A strong statistical claim over three cases per side would be noise
    dressed as rigour; "no threshold separates them" is a statement the
    sample size can actually support, and it is exactly the rule a reader
    holding only the projected view could apply.
    """
    by_group: dict[str, list[tuple[bool, dict[str, float]]]] = (
        collections.defaultdict(list))
    for group, is_filed, quantities in observations:
        by_group[group].append((is_filed, quantities))

    compared = 0
    findings: list[str] = []
    for group, items in sorted(by_group.items()):
        filed_rows = [q for f, q in items if f]
        unfiled_rows = [q for f, q in items if not f]
        if not filed_rows or not unfiled_rows:
            findings.append(
                f"{group}: every case is "
                f"{'filed' if filed_rows else 'unfiled'} "
                f"({len(filed_rows)} filed / {len(unfiled_rows)} unfiled) -- "
                f"the group is itself the rule")
            continue
        names = sorted(set().union(*(set(q) for q in filed_rows + unfiled_rows)))
        for name in names:
            filed = [q[name] for q in filed_rows if name in q]
            unfiled = [q[name] for q in unfiled_rows if name in q]
            if not filed or not unfiled:
                findings.append(
                    f"{group}/{name}: present on "
                    f"{'filed' if filed else 'unfiled'} cases only "
                    f"({len(filed)} filed / {len(unfiled)} unfiled)")
                continue
            compared += 1
            if max(filed) < min(unfiled) or max(unfiled) < min(filed):
                findings.append(
                    f"{group}/{name}: ranges disjoint -- filed "
                    f"[{min(filed)}, {max(filed)}] vs unfiled "
                    f"[{min(unfiled)}, {max(unfiled)}]")
    return compared, findings


def local(iri: str) -> str:
    """Last path segment of an IRI. Labels only -- never used to compare
    across stores (CLAUDE.md, "Normalize to full IRIs before comparing")."""
    return iri.rsplit("/", 1)[-1]


# ===========================================================================
# Store reads -- one snapshot per run, taken here and nowhere else
# ===========================================================================

def _fluree(query: str):
    from ccf import fluree
    return fluree.query(query)["results"]["bindings"]


@dataclass
class Context:
    """Lazily-loaded snapshots of the five stores.

    Every floor is importable and callable on its own (the tests call them
    with no arguments), so each builds a `Context` if it is not handed one.
    `main()` builds exactly one and passes it to all seven, which is why the
    85,107-triple Fluree read happens once per run rather than seven times.
    """

    as_of: str

    # --- Fluree ---------------------------------------------------------

    @cached_property
    def triples(self) -> list[tuple[str, str, str, bool]]:
        """Every triple in the v2 ledger as `(s, p, o, object_is_iri)`.

        **Guarded against a partial read.** This unbounded scan is where
        floor 7's entire adjacency comes from -- the EDGES it walks, over
        which it proves no path from the AML island to a real entity. Its
        target set, `real_nodes`, carries three independent refusals
        against being empty or partial; this, the side carrying the edges,
        carried none. A read that came back short -- a server-side row cap,
        a truncated page, a partial response -- would DELETE edges, and
        deleting edges makes floor 7 pass. So the row count is checked
        against the ledger's own `COUNT(*)`, which is a second, independent
        query rather than a property of this result. Measured 85,107 rows
        against 85,107 at the time this guard was added, so it is whole
        today; the point is that it can no longer stop being whole in
        silence.
        """
        from ccf import fluree
        # `CheckFailure` lives in validators/conditions.py, this estate's
        # one "the check itself could not run -- render FAIL, never SKIP"
        # signal. Imported lazily: conditions.py imports THIS module (also
        # lazily, inside `_aml_delegate`), and a module-level import here
        # would make the pair circular.
        from validators.conditions import CheckFailure
        rows = _fluree(f"SELECT ?s ?p ?o FROM <{L}> WHERE {{ ?s ?p ?o }}")
        expected = fluree.count_triples(L)
        if len(rows) != expected:
            raise CheckFailure(
                f"refusing to build the graph from a partial read: the "
                f"triple scan returned {len(rows):,} row(s) but the ledger "
                f"counts {expected:,}. Floor 7 walks these rows as its "
                f"edges, and missing edges make it pass.")
        return [(r["s"]["value"], r["p"]["value"], r["o"]["value"],
                 r["o"]["type"] == "uri") for r in rows]

    @cached_property
    def adjacency(self) -> dict[str, set[str]]:
        """All-predicate, IRI-object, undirected, `rdf:type` excluded."""
        return build_adjacency(
            (s, p, o) for s, p, o, is_iri in self.triples if is_iri)

    @cached_property
    def transacted_edges(self) -> list[tuple[str, str]]:
        """Raw DIRECTED `ex:transactedWith` rows, as party-id pairs. Kept
        separate from the adjacency so the directed row count stays
        reportable -- the two figures (7,736 directed rows over 3,868
        unordered pairs) are how a reader tells "the loader asserted both
        directions" from "the graph is twice as dense as it should be"."""
        rows = _fluree(f"SELECT ?s ?o FROM <{L}> WHERE "
                       f"{{ ?s <{EX}transactedWith> ?o }}")
        return [(local(r["s"]["value"]), local(r["o"]["value"])) for r in rows]

    @cached_property
    def transacted(self) -> dict[str, set[str]]:
        """`ex:transactedWith` only, keyed by party id (local name).

        The loader asserts both directions already; building the adjacency
        undirected on top of that is idempotent, not a second edge.
        """
        adj: dict[str, set[str]] = collections.defaultdict(set)
        for a, b in self.transacted_edges:
            adj[a].add(b)
            adj[b].add(a)
        return adj

    @cached_property
    def anchors(self) -> dict[str, str]:
        """Fluree node IRI -> `passage_id` it anchors to."""
        rows = _fluree(f"SELECT ?t ?p FROM <{L}> WHERE "
                       f"{{ ?t <{EX}anchoredToPassage> ?p }}")
        return {r["t"]["value"]: r["p"]["value"] for r in rows}

    @cached_property
    def typology_nodes(self) -> set[str]:
        rows = _fluree(f"SELECT ?t FROM <{L}> WHERE "
                       f"{{ ?t a <{EX}Typology> }}")
        return {r["t"]["value"] for r in rows}

    @cached_property
    def unanchored_match_targets(self) -> list[str]:
        """Every OBJECT of `ex:matchesTypology` carrying no
        `ex:anchoredToPassage`, as a SPARQL anti-join. `FILTER NOT EXISTS`
        is unaffected by the repeated-variable defect in §27."""
        rows = _fluree(
            f"SELECT DISTINCT ?o FROM <{L}> WHERE {{ "
            f"?s <{EX}matchesTypology> ?o . "
            f"FILTER NOT EXISTS {{ ?o <{EX}anchoredToPassage> ?p }} }}")
        return sorted(r["o"]["value"] for r in rows)

    @cached_property
    def party_typology(self) -> dict[str, str]:
        """AML party id -> typology id it matches, from the ledger."""
        rows = _fluree(f"SELECT ?s ?o FROM <{L}> WHERE "
                       f"{{ ?s <{EX}matchesTypology> ?o }}")
        return {local(r["s"]["value"]): local(r["o"]["value"]) for r in rows}

    @cached_property
    def posture_dates(self) -> dict[str, str]:
        rows = _fluree(f"SELECT ?s ?d FROM <{L}> WHERE {{ "
                       f"?s a <{EX}FilingPosture> ; "
                       f"<{EX}postureEffectiveFrom> ?d }}")
        return {local(r["s"]["value"]): r["d"]["value"] for r in rows}

    @cached_property
    def rules(self) -> dict[tuple[str, str, str], bool]:
        """`(posture_id, typology_id, disposition)` -> permitted, parsed out
        of the rule id against the posture and typology id sets this same
        ledger supplies."""
        rows = _fluree(f"SELECT ?s ?p FROM <{L}> WHERE {{ "
                       f"?s a <{EX}DispositionRule> ; "
                       f"<{EX}permitsDisposition> ?p }}")
        typology_ids = {local(t) for t in self.typology_nodes}
        out: dict[tuple[str, str, str], bool] = {}
        unparsed = []
        for r in rows:
            key = parse_rule_id(local(r["s"]["value"]),
                                 set(self.posture_dates), typology_ids)
            if key is None:
                unparsed.append(local(r["s"]["value"]))
                continue
            out[key] = r["p"]["value"] == "true"
        if unparsed:
            raise RuntimeError(
                "refusing to evaluate a posture: rule id(s) could not be "
                f"resolved against the ledger's own posture/typology ids: "
                f"{sorted(unparsed)[:5]}")
        return out

    @cached_property
    def real_nodes(self) -> set[str]:
        """Every Fluree node that IS a real, named entity or person.

        Two populations, resolved independently and both from the estate
        rather than from a pattern this file invents:

        * **Real legal entities** -- subjects of `ex:lei` whose literal
          value appears in Postgres `legal_entity.lei`. AML parties carry
          `ex:lei` too (a `SYN-` identifier), so the Postgres join is what
          separates them, not the shape of the string.
        * **Real natural persons** -- `person-<key>` nodes whose key is a
          NUMERIC `person.person_key`. Numeric keys are officers of real
          companies (817 `person_role` rows); `PSC-####` keys are Wave 13b's
          invented cast and are NOT real.

        The `person-` prefix is a guess about a URI pattern, and a guess
        that silently matched nothing would empty this set and make floor 7
        pass for free -- the "gate blind to its own population" defect. So
        the denominator is counted independently: every `person-` node in
        the ledger must resolve to a `person_key` Postgres knows, and every
        anchor LEI must resolve to a node. Either failing raises.
        """
        by_lei: dict[str, str] = {}
        for r in _fluree(f"SELECT ?s ?l FROM <{L}> WHERE "
                          f"{{ ?s <{EX}lei> ?l }}"):
            by_lei[r["l"]["value"]] = r["s"]["value"]

        entities = {by_lei[lei] for lei in self.real_leis if lei in by_lei}
        missing_anchors = sorted(l for l in self.anchor_leis if l not in by_lei)
        if missing_anchors:
            raise RuntimeError(
                "refusing to check the AML island: "
                f"{len(missing_anchors)} anchor LEI(s) resolve to no Fluree "
                f"node, so they could not be crossed INTO: {missing_anchors[:5]}")

        nodes = set(self.adjacency)
        person_nodes = {n for n in nodes if local(n).startswith("person-")}
        unknown = sorted(n for n in person_nodes
                          if local(n)[len("person-"):] not in self.person_keys)
        if unknown:
            raise RuntimeError(
                "refusing to check the AML island: `person-` node(s) whose "
                f"suffix is not a Postgres person_key: {unknown[:5]} -- the "
                "URI pattern this set is built on has drifted")
        people = {n for n in person_nodes
                   if local(n)[len("person-"):] in self.real_person_keys}
        if not entities or not people:
            raise RuntimeError(
                f"refusing to check the AML island: resolved {len(entities)} "
                f"real entities and {len(people)} real persons -- an empty "
                "population would make this floor pass for free")
        return entities | people

    # --- Postgres --------------------------------------------------------

    @cached_property
    def _pg(self) -> dict:
        with pg_connect() as conn, conn.cursor() as cur:
            cur.execute(f'SELECT party_id, legal_name, beneficial_owner_key, '
                        f'ofac_near_match FROM "{S}".aml_party')
            parties = cur.fetchall()
            cur.execute(f'SELECT alert_id, subject_party, raised_at, case_id, '
                        f'"trigger" FROM "{S}".aml_alert')
            alerts = cur.fetchall()
            cur.execute(f'SELECT alert_id, related_alert_id, relation '
                        f'FROM "{S}".aml_alert_link')
            links = cur.fetchall()
            cur.execute(f'SELECT perspective, elements '
                        f'FROM "{S}".aml_projection_plan')
            plans = cur.fetchall()
            cur.execute(f'SELECT lei, is_anchor FROM "{S}".legal_entity')
            entities = cur.fetchall()
            cur.execute(f'SELECT person_key FROM "{S}".person')
            persons = [r[0] for r in cur.fetchall()]
            cur.execute(f'SELECT entry_id, name FROM "{S}".sanctions_name')
            sanctions = cur.fetchall()
        return {"parties": parties, "alerts": alerts, "links": links,
                "plans": plans, "entities": entities, "persons": persons,
                "sanctions": sanctions}

    @cached_property
    def parties(self) -> dict[str, dict]:
        return {p: {"party_id": p, "legal_name": n,
                    "beneficial_owner_key": b, "ofac_near_match": o}
                for p, n, b, o in self._pg["parties"]}

    @cached_property
    def alerts(self) -> list[dict]:
        """Full alert rows, `case_id` INCLUDED.

        Deliberate. Withholding `case_id` from the assembly would make
        `sar_confidentiality_holds` unable to fail: the resolvers could not
        leak what they were never given, and the floor would be checking
        this file's plumbing rather than the projection plan. The resolvers
        get everything and must be shown not to emit it.
        """
        return [{"alert_id": a, "subject_party": s, "raised_at": r,
                 "case_id": c, "trigger": t}
                for a, s, r, c, t in self._pg["alerts"]]

    @cached_property
    def links_by_alert(self) -> dict[str, list[dict]]:
        out: dict[str, list[dict]] = collections.defaultdict(list)
        for a, rel_a, rel in self._pg["links"]:
            out[a].append({"related_alert_id": rel_a, "relation": rel})
        return out

    @cached_property
    def plans(self) -> dict[str, set[str]]:
        return {p: set(json.loads(e) if isinstance(e, str) else e)
                for p, e in self._pg["plans"]}

    @cached_property
    def real_leis(self) -> set[str]:
        return {lei for lei, _ in self._pg["entities"]}

    @cached_property
    def anchor_leis(self) -> set[str]:
        return {lei for lei, is_anchor in self._pg["entities"] if is_anchor}

    @cached_property
    def person_keys(self) -> set[str]:
        return set(self._pg["persons"])

    @cached_property
    def real_person_keys(self) -> set[str]:
        """Numeric keys only. `PSC-####` is Wave 13b's invented cast."""
        return {k for k in self.person_keys if not k.startswith("PSC-")}

    @cached_property
    def sanctions_names(self) -> dict[str, list[str]]:
        out: dict[str, list[str]] = collections.defaultdict(list)
        for entry_id, name in self._pg["sanctions"]:
            out[entry_id].append(name)
        return out

    # --- SQLite ----------------------------------------------------------

    @cached_property
    def sar_rows(self) -> list[dict]:
        con = sqlite3.connect(SQLITE_PATH)
        try:
            rows = con.execute(
                "SELECT sar_id, alert_id, classification, "
                "visible_to_perspectives FROM sar_classification").fetchall()
        finally:
            con.close()
        return [{"sar_id": s, "alert_id": a, "classification": c,
                 "visible_to_perspectives": set(json.loads(v))}
                for s, a, c, v in rows]

    @cached_property
    def case_by_alert(self) -> dict[str, str]:
        return {a["alert_id"]: a["case_id"] for a in self.alerts
                if a["case_id"]}

    @cached_property
    def all_case_ids(self) -> set[str]:
        return set(self.case_by_alert.values())

    @cached_property
    def filed_cases(self) -> set[str]:
        """The cases a SAR was actually filed on, recomputed by joining
        SQLite `sar_classification` to Postgres `aml_alert`.

        Wave 17's 24 engineered cases split into a filed and an unfiled half
        (Task 15, fix rounds 2-3), so this is a strict subset of
        `all_case_ids` -- it is NOT a synonym for "has a case_id" and nothing
        here may treat it as one. No selection rationale is read; the split
        is observed from the departmental store.
        """
        return {self.case_by_alert[r["alert_id"]] for r in self.sar_rows
                if r["alert_id"] in self.case_by_alert}

    @cached_property
    def forbidden_ids(self) -> set[str]:
        """Every identifier whose appearance would reveal a SAR: the SAR ids
        themselves, and the case ids reachable from the alerts they attach
        to. Recomputed by joining SQLite to Postgres -- never read from a
        list."""
        return {r["sar_id"] for r in self.sar_rows} | self.filed_cases

    @cached_property
    def identifiers(self) -> set[str]:
        """Every nominal identifier in this product, for masking before
        numbers are read out of free text (`numeric_quantities`). Party,
        alert, case and SAR ids -- all recomputed from the stores."""
        return (set(self.parties)
                | {a["alert_id"] for a in self.alerts}
                | self.all_case_ids
                | {r["sar_id"] for r in self.sar_rows})

    # --- MongoDB ---------------------------------------------------------

    @cached_property
    def passages(self) -> dict[str, dict]:
        """The passages the ledger's anchors point at, fetched by `_id`.

        Addressed through `MONGO_DB_V2` directly. db1 is a shared host and
        `ccf.config` deliberately provides no way to enumerate databases.
        """
        wanted = sorted(set(self.anchors.values()))
        db = mongo_db(MONGO_DB_V2, write=False)
        found = db["passage"].find({"_id": {"$in": wanted}})
        return {d["_id"]: d for d in found}


def load_context(as_of: str | None = None) -> Context:
    from generators.generate_aml_transactions import AS_OF_AML
    return Context(as_of=as_of or AS_OF_AML)


# ===========================================================================
# Assembly -- what a perspective actually SEES
# ===========================================================================
#
# Not a projection engine and not an operator (see the module docstring).
# Each resolver reads the in-memory snapshots and returns a plain structure.
# Every resolver returns the SAME SHAPE for every alert -- a field that is
# populated only on the SAR-bearing alerts would discriminate perfectly even
# with its value redacted, which is what `key_paths` above exists to catch.

def _alert_core_facts(alert, ctx, perspective):
    """Deliberately omits `case_id`. That omission is the thing under
    test -- the row handed in carries it."""
    return {"alert_id": alert["alert_id"],
            "subject_party": alert["subject_party"],
            "raised_at": alert["raised_at"],
            "trigger": alert["trigger"]}


def _typology_pattern_summary(alert, ctx, perspective):
    typology = ctx.party_typology.get(alert["subject_party"])
    node = f"{EX}{typology}" if typology else None
    return {"typology_id": typology,
            "anchored_passage_id": ctx.anchors.get(node) if node else None}


def _disposition_candidates(alert, ctx, perspective):
    """Recomputed live: `as_of` resolves a posture, the posture's rules are
    filtered to the subject's typology, and the permitted dispositions fall
    out. No stored candidate list is read."""
    typology = ctx.party_typology.get(alert["subject_party"])
    posture = resolve_posture(ctx.posture_dates, ctx.as_of)
    permitted = sorted(d for (p, t, d), ok in ctx.rules.items()
                        if p == posture and t == typology and ok)
    return {"typology_id": typology, "permitted_dispositions": permitted}


def _sanctions_screening_result(alert, ctx, perspective):
    """The similarity is recomputed from live Postgres names on every call
    -- `measured_similarity` is never read (see `ofac_band_holds`)."""
    party = ctx.parties.get(alert["subject_party"], {})
    declared = party.get("ofac_near_match") or {}
    entry_id = declared.get("sanctions_entry_id")
    names = ctx.sanctions_names.get(entry_id, []) if entry_id else []
    best = max((similarity(party.get("legal_name", ""), n) for n in names),
                default=None)
    return {"sanctions_entry_id": entry_id,
            "recomputed_similarity": best}


def _counterparty_network(alert, ctx, perspective):
    return {"subject_party": alert["subject_party"],
            "direct_counterparties":
                sorted(ctx.transacted.get(alert["subject_party"], set()))}


def _ownership_chain(alert, ctx, perspective):
    party = ctx.parties.get(alert["subject_party"], {})
    return {"subject_party": alert["subject_party"],
            "beneficial_owner_key": party.get("beneficial_owner_key")}


def _prior_alert_lineage(alert, ctx, perspective):
    return {"alert_id": alert["alert_id"],
            "related": ctx.links_by_alert.get(alert["alert_id"], [])}


def _sar_filing_history(alert, ctx, perspective):
    """Filtered by `visible_to_perspectives`, live from SQLite. Never
    resolved for `l1`, whose plan does not name this element -- which is
    the property floor 4 exists to prove."""
    return {"sar_filing_history": [
        {"sar_id": r["sar_id"], "classification": r["classification"]}
        for r in ctx.sar_rows
        if r["alert_id"] == alert["alert_id"]
        and perspective in r["visible_to_perspectives"]]}


def _policy_version_attribution(alert, ctx, perspective):
    posture = resolve_posture(ctx.posture_dates, ctx.as_of)
    return {"posture_id": posture,
            "effective_from": ctx.posture_dates.get(posture),
            "as_of": ctx.as_of}


def _reasoning_trail(alert, ctx, perspective):
    typology = ctx.party_typology.get(alert["subject_party"])
    posture = resolve_posture(ctx.posture_dates, ctx.as_of)
    return {"steps": [
        f"subject {alert['subject_party']} matched typology {typology}",
        f"posture in force at {ctx.as_of} is {posture}",
        f"trigger recorded as {alert['trigger']}"]}


ELEMENT_RESOLVERS = {
    "alert_core_facts": _alert_core_facts,
    "counterparty_network": _counterparty_network,
    "disposition_candidates": _disposition_candidates,
    "ownership_chain": _ownership_chain,
    "policy_version_attribution": _policy_version_attribution,
    "prior_alert_lineage": _prior_alert_lineage,
    "reasoning_trail": _reasoning_trail,
    "sanctions_screening_result": _sanctions_screening_result,
    "sar_filing_history": _sar_filing_history,
    "typology_pattern_summary": _typology_pattern_summary,
}


def assemble(perspective: str, alert: dict, ctx: Context) -> dict:
    """What `perspective` sees for `alert`, per its stored projection plan.

    An element the plan names but no resolver implements raises rather than
    being skipped: a silently-skipped element would shrink the assembled
    output, and `sar_confidentiality_holds` would then be proving absence
    caused by this file rather than by the plan.
    """
    elements = ctx.plans.get(perspective)
    if not elements:
        raise RuntimeError(f"no projection plan rows for {perspective!r}")
    unknown = sorted(elements - set(ELEMENT_RESOLVERS))
    if unknown:
        raise RuntimeError(
            f"projection plan for {perspective!r} names element(s) with no "
            f"resolver: {unknown} -- assembling would silently omit them")
    return {el: ELEMENT_RESOLVERS[el](alert, ctx, perspective)
            for el in sorted(elements)}


# ===========================================================================
# The seven floors
# ===========================================================================

def typology_anchoring(ctx: Context | None = None) -> tuple[bool, str]:
    """FLOOR 1. Every `ex:anchoredToPassage` object resolves to a Mongo
    passage that EXISTS and carries non-empty text, and no
    `ex:matchesTypology` target lacks an anchor.

    What would make this fail: a typology anchored to a `passage_id` Mongo
    does not hold (a renamed document, a passage regenerated under a new
    content hash), a passage whose `text` is empty, a typology node with no
    anchor at all, or one `matchesTypology` edge pointing at an unanchored
    node -- an unsupported accusation about a party. The anti-join is what
    makes the last one visible; a pair of counts (`matches > 0`,
    `anchored > 0`) would pass with a hundred unanchored edges.
    """
    ctx = ctx or load_context()
    anchors = ctx.anchors
    if not anchors:
        return False, "no ex:anchoredToPassage assertions in the ledger"

    passages = ctx.passages
    problems = []
    lengths = []
    for node, passage_id in sorted(anchors.items()):
        doc = passages.get(passage_id)
        if doc is None:
            problems.append(f"{local(node)} -> {passage_id}: no Mongo passage")
            continue
        text = doc.get("text") or ""
        if not text.strip():
            problems.append(f"{local(node)} -> {passage_id}: passage is empty")
            continue
        lengths.append(len(text))

    unanchored_typologies = sorted(
        local(t) for t in ctx.typology_nodes if t not in anchors)
    if unanchored_typologies:
        problems.append(f"typology node(s) with no anchor: "
                        f"{unanchored_typologies}")

    unanchored_targets = ctx.unanchored_match_targets
    if unanchored_targets:
        problems.append(f"{len(unanchored_targets)} matchesTypology target(s) "
                        f"with no anchor: "
                        f"{[local(t) for t in unanchored_targets][:5]}")

    detail = (f"{len(anchors)} anchor(s), {len(ctx.typology_nodes)} typology "
              f"node(s), passage chars "
              f"{min(lengths) if lengths else 0}..{max(lengths) if lengths else 0}, "
              f"0 unanchored matchesTypology targets")
    if problems:
        return False, "; ".join(problems)
    return True, detail


def depth_three_holds(ctx: Context | None = None) -> tuple[bool, str]:
    """FLOOR 2. The `ex:transactedWith` graph, walked LIVE, must contain at
    least one ordered pair at EXACTLY distance 3 -- invisible at depth 2,
    visible at depth 3.

    `requires_depth` is a LABEL sitting in `wave17_cases.json` and is never
    read here. Neither is `depth_three_counterparty` used as an answer: the
    exact-distance-3 set is computed from the ledger over every party, and
    the artifact's named pairs are then checked to be IN it. The gate is
    satisfiable with no artifact at all.

    What would make this fail: any single extra `transactedWith` edge that
    shortens the one path -- 70 of the 20,100 possible party pairs would
    erase the established case -- an off-by-one in the depth counter, or a
    frontier that re-expands nodes it has already seen (which would turn
    "exactly 3" into "at most 3" and never be empty).
    """
    ctx = ctx or load_context()
    adj = ctx.transacted
    parties = sorted(ctx.parties)
    if not adj:
        return False, "no ex:transactedWith edges in the ledger"

    pairs = exact_depth_pairs(adj, parties, 3)
    unordered = {frozenset(p) for p in pairs}
    directed_rows = len(ctx.transacted_edges)
    edges = sum(len(v) for v in adj.values()) // 2

    named = _named_depth_three_pairs()
    missed = [(a, b) for a, b in named if (a, b) not in pairs]

    detail = (f"{directed_rows} directed transactedWith rows over {edges} "
              f"unordered pairs; {len(pairs)} ordered pair(s) at exactly "
              f"depth 3 ({len(unordered)} unordered); "
              f"{len(named)} artifact-named pair(s) all confirmed live")
    if not pairs:
        return False, ("no party pair is reachable at depth 3 and unreachable "
                       "at depth 2 -- the depth-3 claim has collapsed")
    if missed:
        return False, (f"artifact-named depth-3 pair(s) NOT at exact distance "
                       f"3 in the ledger: {missed}")
    return True, detail


def _named_depth_three_pairs() -> list[tuple[str, str]]:
    """`(subject, target)` for every case that names a depth-3 counterparty.

    The artifact is used for POINTERS only -- which pair to spotlight -- and
    never for the answer. `requires_depth` is not read; reachability is
    recomputed from Fluree in `depth_three_holds`.
    """
    from ccf.config import REPO_ROOT
    path = REPO_ROOT / "sources" / "screening" / "wave17_cases.json"
    cases = json.loads(path.read_text())["cases"]
    return [(c["subject_party"], c["depth_three_counterparty"])
            for c in cases if c.get("depth_three_counterparty")]


def posture_flip_holds(ctx: Context | None = None) -> tuple[bool, str]:
    """FLOOR 3. The SAME disposition for the SAME typology, evaluated under
    two `as_of` values that resolve to two DIFFERENT postures, must give
    two different answers.

    Evaluation is live: `as_of` -> posture (`resolve_posture`) -> the rules
    belonging to that posture (`parse_rule_id` against the ledger's own id
    sets) -> permitted. No `flips` flag exists in this estate and none is
    read.

    Three ways this refuses to pass on noise, because three of the four
    typologies are identical across postures by design:

    * the two `as_of` values must resolve to DIFFERENT postures, or the
      comparison is vacuous;
    * both sides of a differing pair must be actual booleans -- a rule
      missing under one posture would "differ" from ABSENCE rather than
      from policy;
    * every differing pair is named in the detail line, so a difference
      arriving from somewhere unexpected is visible rather than absorbed
      into a count.
    """
    ctx = ctx or load_context()
    dates = ctx.posture_dates
    if len(dates) < 2:
        return False, f"fewer than two postures in the ledger: {dates}"
    if len(set(dates.values())) != len(dates):
        return False, ("two postures share an effective date -- they could "
                       f"not be told apart by as_of: {dates}")

    early_as_of = min(dates.values())
    late_as_of = ctx.as_of
    early = resolve_posture(dates, early_as_of)
    late = resolve_posture(dates, late_as_of)
    if early is None or late is None or early == late:
        return False, (f"as_of {early_as_of} and {late_as_of} resolve to "
                       f"{early} and {late} -- not two different postures")

    keys = {(t, d) for (p, t, d) in ctx.rules}
    differing = []
    for typology, disposition in sorted(keys):
        a = ctx.rules.get((early, typology, disposition))
        b = ctx.rules.get((late, typology, disposition))
        if a is None or b is None:
            continue          # differs from absence, not from policy
        if a != b:
            differing.append((typology, disposition, a, b))

    if not differing:
        return False, (f"no disposition is evaluated differently under "
                       f"{early} ({early_as_of}) and {late} ({late_as_of}) "
                       f"-- the Policy Blind counterfactual cannot be shown")
    named = "; ".join(f"{t}/{d}: {early}={a} -> {late}={b}"
                      for t, d, a, b in differing)
    return True, (f"{len(differing)} of {len(keys)} (typology, disposition) "
                  f"pair(s) flip between {early} and {late} -- {named}")


def sar_confidentiality_holds(ctx: Context | None = None) -> tuple[bool, str]:
    """FLOOR 4. Assemble every alert from `l1`'s stored projection plan and
    require that nothing it yields reveals a SAR exists -- absent, not null.

    **`l1`, never `l2`.** `l1` appears in zero of the SAR
    `visible_to_perspectives` sets (recomputed live -- see `ctx.sar_rows`)
    and in no `sar_narrative` document. `l2` is excluded from only the
    `confidential` (TYP-SHELL) SARs and sees the rest, so a floor built on
    `l2` would be satisfied on some records and violated on others.

    Four sub-conditions, each able to fail on its own:

    1. `l1`'s plan names no element in `ccf.aml.SAR_REVEALING_ELEMENT_NAMES`.
    2. No assembled rendering carries a revealing KEY at any depth (a key
       present with a null value is a leak) or a SAR/case identifier as a
       value, including inside free text. **`case_id` no longer implies "a
       SAR was filed"** -- coordinator ruling, fix rounds 2-3: SAR coverage
       is a deliberate PROPER SUBSET of the engineered cases, so every
       case-bearing alert carries a `case_id` while only some of those
       cases filed. `ctx.forbidden_ids` -- recomputed live by joining
       SQLite's actual SAR rows back to their alerts -- only ever contains
       the case_ids that DID file. `case_id` is still checked, because it
       remains an exact inference route for the cases that DO have a SAR;
       it simply no longer covers all of them.

       **The mechanism is a content digest, not a materiality selection.**
       Fix round 2 selected the filing half by aggregate transaction
       exposure, and fix round 3 REMOVED that -- precisely because
       materiality was recoverable from `trigger`, which is the disclosure
       route sub-condition 4 below exists to police. `select_filed_case_ids`
       now sorts each typology's cases by `sha256(salt:case_id)` and keeps
       the first half. Anyone auditing this property must audit against the
       digest; the materiality account is not merely out of date, it
       describes the unsafe design that was rejected. Counts are not
       restated here for the same reason: they moved once already, and the
       live figures come from `ctx.sar_rows` (SQLite `sar_classification`)
       and are printed on every run.
    3. The KEY SHAPE is identical across all alerts. A field present only on
       the case-bearing alerts discriminates perfectly even redacted.
    4. **No `l1`-visible QUANTITY separates the filed cases from the unfiled
       ones, within a typology.** Sub-conditions 1-3 police what the view
       NAMES; this one polices what the view lets a reader DERIVE. Task 15
       re-selected the filing half by a content digest, uncorrelated with
       `l1`-visible signal by construction, and labelled itself honestly as
       engineered for that reason. A rationale is a claim. This recomputes
       the property: every alert is assembled as `l1` sees it, every number
       a reader could extract is pulled out (`numeric_quantities` -- the
       figures inside `trigger`, `raised_at` as an ordinal, and anything
       else numeric the plan yields), the case-bearing alerts are grouped by
       the typology named in their own trigger, and filed and unfiled must
       be inseparable within each group (`separating_quantities`). Task 15's
       selection logic is never imported and its rationale field is never
       read -- the filing split is observed from SQLite, and the quantities
       from the assembled view.

    What would make this fail: adding `case_id` to `_alert_core_facts` as a
    compact-summary convenience; adding `sar_filing_history` to `l1`'s plan;
    a resolver that returns `{}` for noise alerts and a populated dict for
    genuine ones; a resolver emitting ANY number that tracks filing status,
    even under an innocuous key and even with no identifier in it -- the
    first two are planted into `scan_for_sar_leakage` directly by
    `validators/test_aml_typology.py`, the last into
    `separating_quantities`.

    ## What sub-condition 4 does NOT claim

    Stated plainly so nobody overreads the PASS line.

    **It reads NUMBERS only.** `numeric_quantities` extracts numeric
    values; a purely NOMINAL separator is outside its reach -- a country
    code, a channel, a category, a jurisdiction that appears on the filed
    cases and never on the unfiled ones would not be reported here.
    Sub-condition 3 catches such a thing only in the narrow case where it
    changes the KEY SHAPE, which a differing value does not. Extending the
    check to categorical fields (value sets required to intersect, not
    merely value ranges required to overlap) is the obvious next step and
    was deliberately not taken in this round.

    **The test it does apply is range overlap, which is weak on purpose.**
    Three cases per side is what the sample supports; a stronger
    statistical claim over six points would be noise dressed as rigour. So
    the claim is "no threshold separates them" -- which is exactly the rule
    a reader holding only the projected view could act on -- and NOT "no
    correlation exists". A filed group skewing high while still overlapping
    would pass.

    **It reads each alert's own rendering IN ISOLATION.** `l1` receives the
    whole set, so any AGGREGATE over it -- a count, a rank, an ordering, a
    "is this the earliest alert on this subject" derived from
    `subject_party` plus `raised_at` -- is equally `l1`-derivable and is
    never extracted here. The whole-branch review searched this space and
    reported the one candidate it found AGAINST itself as below-chance
    (roughly 40 comparisons at a roughly 10% base rate, about 4 hits
    expected, 1 found: for a trade_based alert, "not the earliest alert on
    its subject" coincided with "a SAR was filed", 3 of 3 both ways). At
    that rate it is a coincidence, not a route -- but the BOUNDARY is real
    and is disclosed here rather than left for the next reader to
    rediscover.

    ## What floor 4 passing does and does not tell you about the data

    Sub-condition 4 recomputes the quantities `l1` can extract. Task 15's
    `FILING_DIGEST_SALT` was itself CHOSEN by trying several literal
    strings and keeping the first with no one-sided split against those
    same quantities (see that constant's own comment, which is careful
    about the distinction and worth reading). The mechanism -- a hash --
    cannot carry a designed relationship to any case attribute whichever
    salt is picked, so this is not fix round 2's mistake repeated. But the
    instrument and the data were, in part, tuned to each other: a reader of
    this PASS line should know the property was partly ARRANGED rather than
    wholly DISCOVERED.

    That does not make floor 4 unable to fail. It fails on planted leaks
    today -- `validators/test_aml_typology.py` feeds `scan_for_sar_leakage`
    and `separating_quantities` known-present inputs and requires a
    different answer from the known-absent ones -- and it would fail on a
    future data change that reintroduced a separator, because it recomputes
    from the stores and never reads Task 15's selection logic or its
    `filing_rationale`.
    """
    ctx = ctx or load_context()
    plan = ctx.plans.get(BLIND_PERSPECTIVE)
    if not plan:
        return False, f"no {BLIND_PERSPECTIVE} projection plan row"

    named_leaks = sorted(plan & SAR_REVEALING_ELEMENT_NAMES)
    if named_leaks:
        return False, (f"{BLIND_PERSPECTIVE}'s plan names SAR-revealing "
                       f"element(s): {named_leaks}")

    forbidden = ctx.forbidden_ids
    if not forbidden:
        return False, ("no SAR or case identifiers were recomputed -- the "
                       "scan would have nothing to look for")

    findings: list[str] = []
    shapes: dict[frozenset, list[str]] = collections.defaultdict(list)
    observations: list[tuple[str, bool, dict[str, float]]] = []
    for alert in ctx.alerts:
        rendered = assemble(BLIND_PERSPECTIVE, alert, ctx)
        for f in scan_for_sar_leakage(rendered, forbidden):
            findings.append(f"{alert['alert_id']}: {f}")
        shapes[frozenset(key_paths(rendered))].append(alert["alert_id"])
        case_id = ctx.case_by_alert.get(alert["alert_id"])
        if case_id:
            # Grouped by the typology named in the alert's OWN trigger --
            # an l1-visible string -- rather than by `matchesTypology`.
            #
            # NOT because l1 cannot see `matchesTypology`: it can. l1's
            # plan names `typology_pattern_summary`, whose resolver is
            # `_typology_pattern_summary` above, and that resolver reads
            # `ctx.party_typology`, which IS the `matchesTypology` edge. A
            # note here once claimed otherwise, and also claimed Task 15
            # fix round 2 had put typology edges on noise-alert subjects;
            # both were false. `e35a883` touched no Fluree loader, and
            # `matchesTypology` is exactly the 24 primary case subjects,
            # set in Task 13 and never changed since.
            #
            # The real reason is coverage in the other direction: the
            # edge does not resolve for every CASE-BEARING alert. 27
            # parties carry one, and 3 of them -- the TYP-SHELL
            # intermediaries carrying the secondary alert -- have no
            # typology edge at all, so grouping by the edge would silently
            # drop them. The trigger prefix is present on every alert by
            # construction. (Note also that 15 of the 24 edge-bearing
            # parties ALSO carry a noise alert, so the edge does not
            # separate genuine from noise either.)
            observations.append((
                alert["trigger"].split(":", 1)[0],
                case_id in ctx.filed_cases,
                numeric_quantities(rendered, ctx.identifiers)))

    if findings:
        return False, f"{len(findings)} leak(s), e.g. {findings[:3]}"
    if len(shapes) != 1:
        sizes = sorted((len(v), sorted(v)[0]) for v in shapes.values())
        return False, (f"{len(shapes)} distinct key shapes across "
                       f"{len(ctx.alerts)} alerts -- presence alone "
                       f"discriminates: {sizes}")

    # Denominator, counted independently of the check. A separability test
    # over an empty split, or one where every case fell on the same side,
    # would report "no quantity separates them" forever -- the estate's
    # "gate blind to its own population" defect.
    unfiled = ctx.all_case_ids - ctx.filed_cases
    if not ctx.filed_cases or not unfiled:
        return False, (f"the filing split is degenerate: "
                       f"{len(ctx.filed_cases)} filed / {len(unfiled)} "
                       f"unfiled of {len(ctx.all_case_ids)} cases -- nothing "
                       f"to be separable")
    compared, separators = separating_quantities(observations)
    if not compared:
        return False, ("no l1-visible quantity could be extracted from any "
                       "assembled view -- the separability check would pass "
                       "vacuously")
    if separators:
        return False, (f"{len(separators)} l1-visible quantity/-ies separate "
                       f"filed from unfiled: {separators[:3]}")

    n_case = sum(1 for a in ctx.alerts if a["case_id"])
    return True, (f"{len(ctx.alerts)} alerts assembled from "
                  f"{BLIND_PERSPECTIVE}'s {len(plan)} element(s); 0 leaks "
                  f"against {len(forbidden)} SAR/case identifier(s); one key "
                  f"shape for all of them ({n_case} carry a case_id, "
                  f"{len(ctx.sar_rows)} SARs exist); {compared} l1-visible "
                  f"quantity/-ies compared across "
                  f"{len({o[0] for o in observations})} typology group(s), "
                  f"none separates {len(ctx.filed_cases)} filed from "
                  f"{len(unfiled)} unfiled")


def ofac_band_holds(ctx: Context | None = None) -> tuple[bool, str]:
    """FLOOR 5. The declared OFAC near-match's similarity, RECOMPUTED from
    live Postgres names, must land in the moderate band.

    `aml_party.ofac_near_match` is read for its POINTERS only -- which
    sanctions entry the party declares. `measured_similarity` is reported
    beside the recomputed figure for drift, and never gated on.

    `ccf.aml.similarity`, never `difflib`'s `quick_ratio()`. `quick_ratio`
    is an upper BOUND on `ratio()`, not a cheaper spelling of it, and the
    only false finding raised against this wave came from that substitution.

    What would make this fail: the party renamed so the names converge (band
    ceiling) or diverge (band floor); the sanctions entry removed from
    `sanctions_name`, leaving nothing to compare against; more than one
    party declaring a near-match, which would make "the" declared match
    ambiguous.
    """
    ctx = ctx or load_context()
    declared = [p for p in ctx.parties.values() if p["ofac_near_match"]]
    if len(declared) != 1:
        return False, (f"expected exactly one party declaring an OFAC "
                       f"near-match, found {len(declared)}")
    party = declared[0]
    entry_id = party["ofac_near_match"]["sanctions_entry_id"]
    names = ctx.sanctions_names.get(entry_id, [])
    if not names:
        return False, (f"{party['party_id']} declares {entry_id}, which has "
                       f"no rows in {S}.sanctions_name")

    scored = sorted(((similarity(party["legal_name"], n), n) for n in names),
                     reverse=True)
    best, best_name = scored[0]
    stored = party["ofac_near_match"].get("measured_similarity")
    lo, hi = OFAC_BAND
    detail = (f"{party['party_id']} {party['legal_name']!r} vs {entry_id} "
              f"{best_name!r} = {best!r} (band {lo}..{hi}; artifact recorded "
              f"{stored!r}, not gated on)")
    if not (lo <= best <= hi):
        return False, "outside the band: " + detail
    return True, detail


def renderings_differ(ctx: Context | None = None) -> tuple[bool, str]:
    """FLOOR 6. The three perspectives must assemble different ELEMENT SETS
    -- and, for the elements they SHARE, different VALUES.

    Two arms, and the second one was rebuilt after review.

    **Arm 1 -- element sets.** Sets, not strings: three plans differing only
    in a display flag would satisfy a "the plans differ" check while
    assembling identical content, which is the Perspective Flat failure this
    product refutes.

    **Arm 2 -- shared elements must be perspective-SENSITIVE.** The arm this
    replaces compared `set(rendered[a])` against `set(rendered[b])`, and
    `assemble()` builds its dict keyed by the plan's own element names, so
    that comparison was the element-set comparison over again wearing a
    different name: it could only fire in a state arm 1 had already
    returned on. That is this estate's own output-that-never-varies defect,
    sitting inside the instrument built to catch it.

    What the dead arm was hiding matters more than the arm. `sar_filing_history`
    is the ONLY element whose resolver reads `perspective` at all, and
    nothing asserted that it filtered: `l2`'s exclusion from the
    `confidential` SARs -- the whole reason this architecture reaches into a
    departmental SQLite store -- was unchecked. So arm 2 now compares
    serialized VALUES, per shared element, across every alert, and requires
    every SAR-bearing shared element to render DIFFERENTLY for at least two
    of the perspectives that name it.

    Which elements those are is derived, not typed in:
    `shared & ccf.aml.SAR_REVEALING_ELEMENT_NAMES`. The set is required to
    be non-empty, because a run where no perspective shared a SAR element
    would satisfy "every SAR element is sensitive" vacuously.

    What would make this fail: any two plans loading identical; `examiner`
    losing an element until it matches `l2`; and -- the one the old arm
    could not see -- `_sar_filing_history` ignoring its `perspective`
    argument, so `l2` and `examiner` receive the same SAR rows and the
    confidential exclusion stops being enforced by anything.

    ## What arm 2 does NOT claim

    It establishes that the resolver filters on SOMETHING
    perspective-dependent. It does not establish that it filters on the
    RIGHT thing. Reproduced rather than assumed: a resolver rewritten to
    return SAR rows only when `perspective == "examiner"` -- so `l2` sees
    no SAR at all, regardless of `visible_to_perspectives` -- still makes
    `l2` and `examiner` differ, and this floor still returns PASS.

    That is strictly better than the arm it replaced, which was blind to
    every version of the fault, and it is what the finding asked for. But
    the property "`l2` sees exactly the SARs whose
    `visible_to_perspectives` names it" is not asserted anywhere. Asserting
    it would mean recomputing the expected row set per (alert, perspective)
    from SQLite and comparing -- a natural next step, and not taken here.
    """
    ctx = ctx or load_context()
    plans = ctx.plans
    if set(plans) != {"l1", "l2", "examiner"}:
        return False, f"projection plans present: {sorted(plans)}"
    empty = sorted(p for p, e in plans.items() if not e)
    if empty:
        return False, f"empty projection plan(s): {empty}"

    names = sorted(plans)
    pairs = [(a, b) for i, a in enumerate(names) for b in names[i + 1:]]
    same_plan = [(a, b) for a, b in pairs if plans[a] == plans[b]]
    if same_plan:
        return False, f"identical element sets: {same_plan}"

    shared = {e for e in set().union(*plans.values())
              if sum(e in plans[p] for p in names) >= 2}
    sar_shared = sorted(shared & SAR_REVEALING_ELEMENT_NAMES)
    if not sar_shared:
        return False, ("no SAR-bearing element is shared by two "
                       "perspectives, so perspective-sensitivity could not "
                       f"be tested at all (shared: {sorted(shared)})")

    renders = {p: [assemble(p, alert, ctx) for alert in ctx.alerts]
               for p in names}

    def serialize(perspective, element, i):
        return json.dumps(renders[perspective][i][element], sort_keys=True,
                           default=str)

    sensitive: dict[str, str] = {}
    for element in sorted(shared):
        holders = [p for p in names if element in plans[p]]
        for a, b in [(x, y) for i, x in enumerate(holders)
                     for y in holders[i + 1:]]:
            for i, alert in enumerate(ctx.alerts):
                if serialize(a, element, i) != serialize(b, element, i):
                    sensitive[element] = (f"{a} != {b} on "
                                          f"{alert['alert_id']}")
                    break
            if element in sensitive:
                break

    flat = [e for e in sar_shared if e not in sensitive]
    if flat:
        return False, (f"SAR-bearing shared element(s) render IDENTICALLY "
                       f"for every perspective that names them, over all "
                       f"{len(ctx.alerts)} alerts: {flat} -- the "
                       f"visible_to_perspectives filter is not being "
                       f"applied by anything")

    sizes = ", ".join(f"{p}={len(plans[p])}" for p in names)
    exclusive = sorted(plans["examiner"] - plans["l1"] - plans["l2"])
    detail_sensitive = "; ".join(f"{e}: {why}"
                                 for e, why in sorted(sensitive.items()))
    return True, (f"element sets {sizes}; examiner-exclusive {exclusive}; "
                  f"{len(shared)} shared element(s), "
                  f"{len(sensitive)} perspective-sensitive "
                  f"({detail_sensitive})")


def no_path_to_real_entity(ctx: Context | None = None) -> tuple[bool, str]:
    """FLOOR 7 / Wave 17 safety property 2. No path of ANY predicate may
    connect an AML party to a real legal entity or a real natural person.

    CLAUDE.md rule 2 is a legal constraint: the entities exhibiting these
    typologies are invented, and a single edge joining them to a named real
    company would make this dataset assert that the company launders money.

    The adjacency spans every predicate in the ledger except `rdf:type`
    (class membership is not a path between entities), is built UNDIRECTED,
    and the walk runs from both ends -- see `walk_for_crossings`. The real
    population is resolved from Postgres, and `Context.real_nodes` refuses
    to hand back an empty or partial set rather than letting this floor pass
    for free.

    What would make this fail: any edge in either direction between the
    islands -- and `validators/test_aml_typology.py` plants exactly that, in
    a throwaway in-memory adjacency, in both directions. Nothing is ever
    written to the ledger, which is append-only and could not take it back.
    """
    ctx = ctx or load_context()
    starts = [f"{EX}{p}" for p in sorted(ctx.parties)]
    absent = [s for s in starts if s not in ctx.adjacency]
    if absent:
        return False, (f"{len(absent)} AML party node(s) have no edges at "
                       f"all, so walking from them proves nothing: "
                       f"{[local(a) for a in absent][:5]}")
    return walk_for_crossings(ctx.adjacency, ctx.real_nodes, starts)


# ===========================================================================
# Rendering (house style, see validators/conditions.py)
# ===========================================================================

FLOORS = [
    ("1. typology anchoring (Fluree -> Mongo passage)", typology_anchoring),
    ("2. depth-3 network (walked live, not labelled)", depth_three_holds),
    ("3. posture flip (same disposition, two as_of)", posture_flip_holds),
    ("4. SAR confidentiality (l1 assembles blind)", sar_confidentiality_holds),
    ("5. OFAC band (similarity recomputed live)", ofac_band_holds),
    ("6. renderings differ (element sets + content)", renderings_differ),
    ("7. no path AML island -> real entity", no_path_to_real_entity),
]


def render(state: str, condition: str, detail: str) -> str:
    return f"  [{state}] {condition:48s} {detail}"


def main() -> int:
    ctx = load_context()
    print("AML-TYPOLOGY-MATCH — §F floors, recomputed from the stores at "
          f"as_of={ctx.as_of}\n")

    failures = 0
    for label, floor in FLOORS:
        ok, detail = floor(ctx)
        if not ok:
            failures += 1
        print(render("PASS" if ok else "FAIL", label, detail))

    print(f"\n  {len(FLOORS) - failures} passed · {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
