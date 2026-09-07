# bundle-tests-part-2

READ-PROOF bundle-tests-part-2: 726378dc7147ade40bc98aac

The five EXISTING test/fixture modules Phase 24.8 changed, as per-file diffs. `test_traversal_admission.py`
and `test_traversal_direction.py` carry the re-derived oracles (bare `_walk` -> `fallback.answer`);
`query_corpus.py` gains the tenth strategy; `test_composition.py` carries the strengthened subset pin;
`edge_graphs.yaml` carries the curated `unresolved-reference` case.

## 1. The diffstat

```
 tests/conformance/query_corpus.py                  | 263 ++++++
 .../conformance/test_operator_tier_differential.py | 827 +++++++++++++++++
 tests/fixtures/banking/edge_graphs.yaml            |  52 +-
 tests/operators/test_traversal_admission.py        | 142 ++-
 tests/operators/test_traversal_direction.py        | 318 ++++++-
 .../test_traversal_unresolved_reference.py         | 999 +++++++++++++++++++++
 tests/properties/test_composition.py               | 102 ++-
 7 files changed, 2654 insertions(+), 49 deletions(-)
```

## 2. `tests/conformance/query_corpus.py` — DIFF

```diff
diff --git a/tests/conformance/query_corpus.py b/tests/conformance/query_corpus.py
index 77bf610d..359ff9cd 100644
--- a/tests/conformance/query_corpus.py
+++ b/tests/conformance/query_corpus.py
@@ -45,6 +45,16 @@ The deliberately generated shapes, and the defects they exist to catch:
   docs/GRAPH_QUERY_SEMANTICS.md:122; INV-CH7-20) while any constrained
   answer endpoint-closes it away (the DI-15.2-01 closure-scoping fact,
   pinned differentially).
+* **The unresolved reference** (ledger row ``CP04-G-28``, ``D-IMPL-267``) —
+  a claimed node joined to another claimed node THROUGH a URI no entity
+  claim covers, with its cycle and bypass variants. The edge is legal
+  persisted state (`GQ-05` at docs/GRAPH_QUERY_SEMANTICS.md:122;
+  INV-CH7-20) and the endpoint is an unresolved reference rather than a
+  traversal member, so a constrained walk neither starts at it nor crosses
+  it (`GQ-16` at docs/GRAPH_QUERY_SEMANTICS.md:316, `GQ-13` at
+  docs/GRAPH_QUERY_SEMANTICS.md:261). Distinct from the dangling edge
+  above, whose BOTH endpoints are claim-less and which therefore no seed
+  can reach.
 * **Self-loops** — an entity related to itself; the walk must neither loop
   nor drop the edge.
 * **Absent seeds, empty answers, degenerate and single-family questions** —
@@ -392,6 +402,221 @@ def _traverse(
     )
 
 
+#: The unresolved reference: a pool URI that NO entity claim ever covers, used
+#: here as an EDGE ENDPOINT rather than as an absent seed. The
+#: :func:`depth_cases` idiom (``absent_uri = ENTITY_POOL[SEED_CLASS][-1]  # in
+#: the pool, never written``) applied to the other side of the edge — which is
+#: the whole difference between "a seed naming nothing" (`GQ-11` at
+#: docs/GRAPH_QUERY_SEMANTICS.md:221) and "an edge naming something
+#: unresolved" (ledger row ``CP04-G-28``). The pool holds three members per
+#: class, so ``[2]`` is its last, and :func:`unresolved_reference_case` claims
+#: only ``[0]`` and ``[1]`` of that class.
+UNRESOLVED_URI: str = ENTITY_POOL[MID_CLASS][2]
+
+#: The three ruled shapes, by the role the unresolved reference plays in each:
+#: it lies on the only path (``chain``), on a cycle back to the seed
+#: (``cycle``), and on a SHORTER path than the fully-claimed one the walk must
+#: use instead (``bypass``). ``D-IMPL-268`` requires the second and third —
+#: depth and cycle consequences, not only final membership.
+UNRESOLVED_REFERENCE_VARIANTS: tuple[str, ...] = ("chain", "cycle", "bypass")
+
+
+def unresolved_reference_case(variant: str) -> CorpusCase:
+    """One G-28 shape, built deterministically — the claimed - unresolved - claimed graph.
+
+    ``D-IMPL-267``, ledger row ``CP04-G-28``. A plain builder rather than a
+    strategy, so a test that must name one shape (the depth question needs
+    ``bypass``, the anchor question needs ``chain``) gets it without drawing.
+
+    The three variants, with ``X`` the :data:`UNRESOLVED_URI` and ``A`` /
+    ``B`` the claimed seed and target:
+
+    * ``chain`` — ``A -> X`` and ``X -> B``. Two edges; ``B`` is reachable
+      from ``A`` only through an endpoint no entity claim covers.
+    * ``cycle`` — the chain plus ``X -> A``. Three edges; the cycle exists in
+      persisted state and must not exist for traversal.
+    * ``bypass`` — the chain plus ``A -> C``, ``C -> D``, ``D -> B`` over two
+      claimed intermediates. Five edges; ``B`` is two persisted hops from
+      ``A`` through ``X`` and three admitted hops around it, which is what
+      makes a depth-limited answer read the depth assignment.
+
+    **Orientation is load-bearing, not stylistic.** The ``X - B`` edge is
+    stored ``subject=X, object=B``, unlike :func:`chain_claims`, whose second
+    edge points ``target -> mid`` (the corpus's mixed-direction convention).
+    A copy of that orientation with ``X`` substituted for the mid would stop
+    a FORWARD walk from ``A`` at ``X`` under every implementation, and the
+    forward half of the ruling would be invisible in the answers.
+
+    Every claim is observed at ``EARLY`` and carries the permitted
+    classification, so no question here is vacuous under the as-of cut or
+    under the policy family (the :func:`admission_cases` discipline), and
+    every phantom-path question walks at ``depth >= 2`` because at depth 0
+    and 1 no path through ``X`` exists to take or refuse.
+    """
+    seed_uri = ENTITY_POOL[SEED_CLASS][0]
+    target_uri = ENTITY_POOL[TARGET_CLASS][0]
+    entities = [
+        entity_claim(
+            entity_uri=seed_uri,
+            entity_class=SEED_CLASS,
+            classification=PERMITTED_CLASSIFICATION,
+            observed_at=EARLY,
+        ),
+        entity_claim(
+            entity_uri=target_uri,
+            entity_class=TARGET_CLASS,
+            classification=PERMITTED_CLASSIFICATION,
+            observed_at=EARLY,
+        ),
+    ]
+    relationships = [
+        # A -> X: the seed's edge INTO the unresolved reference.
+        relationship_claim(
+            relationship_type=_RULE_A[0],
+            subject_uri=seed_uri,
+            object_uri=UNRESOLVED_URI,
+            observed_at=EARLY,
+        ),
+        # X -> B: the unresolved reference's edge onward, stored subject=X.
+        relationship_claim(
+            relationship_type=_RULE_B[0],
+            subject_uri=UNRESOLVED_URI,
+            object_uri=target_uri,
+            observed_at=EARLY,
+        ),
+    ]
+    if variant == "cycle":
+        relationships.append(
+            relationship_claim(
+                relationship_type=_RULE_A[0],
+                subject_uri=UNRESOLVED_URI,
+                object_uri=seed_uri,
+                observed_at=EARLY,
+            )
+        )
+    elif variant == "bypass":
+        first_uri, second_uri = ENTITY_POOL[MID_CLASS][0], ENTITY_POOL[MID_CLASS][1]
+        entities.extend(
+            entity_claim(
+                entity_uri=uri,
+                entity_class=MID_CLASS,
+                classification=PERMITTED_CLASSIFICATION,
+                observed_at=EARLY,
+            )
+            for uri in (first_uri, second_uri)
+        )
+        relationships.extend(
+            (
+                relationship_claim(
+                    relationship_type=_RULE_A[0],
+                    subject_uri=seed_uri,
+                    object_uri=first_uri,
+                    observed_at=EARLY,
+                ),
+                relationship_claim(
+                    relationship_type=_RULE_B[0],
+                    subject_uri=first_uri,
+                    object_uri=second_uri,
+                    observed_at=EARLY,
+                ),
+                relationship_claim(
+                    relationship_type=_RULE_B[0],
+                    subject_uri=second_uri,
+                    object_uri=target_uri,
+                    observed_at=EARLY,
+                ),
+            )
+        )
+    elif variant != "chain":
+        raise AssertionError(
+            f"unknown unresolved-reference variant {variant!r};"
+            f" the shapes are {UNRESOLVED_REFERENCE_VARIANTS}"
+        )
+    return CorpusCase(
+        name=f"unresolved-reference-{variant}",
+        entities=tuple(entities),
+        relationships=tuple(relationships),
+        query_specs=_unresolved_reference_specs(),
+    )
+
+
+def _unresolved_reference_specs() -> tuple[QuerySpec, ...]:
+    """The questions every G-28 shape is asked, in both walk directions.
+
+    Depth 0 / 1 / 2 / 3 at the ``admitted=None`` sentinel — the rows where
+    the phantom path is takeable if anything takes it, and the only rows the
+    divergence was ever measured on; ``admitted`` sets, where a class map
+    that has no entry for an unresolved URI already refuses the hop; and the
+    two anchor rows, which ask whether the unresolved URI can START a walk:
+    the operator-fair one seeds by CLASS (the unresolved URI's pool class,
+    which on ``chain`` and ``cycle`` no claimed entity carries) and the
+    query-tier one names it explicitly through ``seeds`` (`GQ-11` at
+    docs/GRAPH_QUERY_SEMANTICS.md:221 — a seed naming nothing in scope
+    contributes no start). A ``seeds`` row is a query-tier-only question: an
+    operator's ``read_intent`` cannot carry walk starts beyond the seed
+    classes, so a cross-tier differential drops it from the operator column
+    and the substrate suite keeps it.
+    """
+    directions: tuple[TraversalDirection, ...] = ("undirected", "forward")
+    anchor_classes = frozenset({MID_CLASS})
+    specs: list[QuerySpec] = []
+    for direction in directions:
+        specs.extend(
+            (
+                # Depths 0 and 1: no path through the unresolved reference is
+                # long enough to exist — the controls for the rows below.
+                QuerySpec(
+                    as_of=ON_BOUNDARY, traverse=_traverse(0, direction=direction)
+                ),
+                QuerySpec(
+                    as_of=ON_BOUNDARY, traverse=_traverse(1, direction=direction)
+                ),
+                # Depths 2 and 3 at the all-admitted sentinel: the phantom
+                # path's own questions.
+                QuerySpec(
+                    as_of=ON_BOUNDARY, traverse=_traverse(2, direction=direction)
+                ),
+                QuerySpec(
+                    as_of=ON_BOUNDARY, traverse=_traverse(3, direction=direction)
+                ),
+                # Admission sets: a URI with no entity record has no class, so
+                # these already refuse the hop at every tier.
+                QuerySpec(
+                    as_of=ON_BOUNDARY,
+                    traverse=_traverse(
+                        2,
+                        admitted=frozenset({TARGET_CLASS}),
+                        direction=direction,
+                    ),
+                ),
+                QuerySpec(
+                    as_of=ON_BOUNDARY,
+                    traverse=_traverse(
+                        2,
+                        admitted=frozenset({MID_CLASS, TARGET_CLASS}),
+                        direction=direction,
+                    ),
+                ),
+                # The anchor, by class — the operator-fair form.
+                QuerySpec(
+                    as_of=ON_BOUNDARY,
+                    traverse=_traverse(
+                        2, direction=direction, seed_classes=anchor_classes
+                    ),
+                ),
+                # The anchor, named explicitly — the query-tier form.
+                QuerySpec(
+                    as_of=ON_BOUNDARY,
+                    traverse=_traverse(
+                        2, direction=direction, seed_classes=anchor_classes
+                    ),
+                    seeds=frozenset({UNRESOLVED_URI}),
+                ),
+            )
+        )
+    return tuple(specs)
+
+
 # --- the named strategies ----------------------------------------------------
 
 
@@ -914,6 +1139,43 @@ def offset_authored_validity_cases(draw: st.DrawFn) -> CorpusCase:
     )
 
 
+@st.composite
+def unresolved_reference_cases(draw: st.DrawFn) -> CorpusCase:
+    """The unresolved reference on the walk (ledger row ``CP04-G-28``).
+
+    ``D-IMPL-267``. An edge may name an endpoint that no entity claim
+    covers — that edge is legal persisted state (`GQ-05` at
+    docs/GRAPH_QUERY_SEMANTICS.md:122; INV-CH7-20) and L2 admits it without
+    checking either endpoint. What the edge does NOT do is establish the
+    entity: traversal operates over claimed entities, so a URI reachable
+    only as an edge endpoint is an unresolved reference — never a walk
+    start, never a hop, on no path and in no cycle. A constrained answer
+    endpoint-closes such an edge away before walking (`GQ-16` at
+    docs/GRAPH_QUERY_SEMANTICS.md:316) and the path that ran through it
+    therefore does not exist (`GQ-13` at
+    docs/GRAPH_QUERY_SEMANTICS.md:261).
+
+    Three shapes are drawn, built by :func:`unresolved_reference_case`: the
+    ``chain`` (the reference lies on the only path), the ``cycle`` (it
+    closes a loop back to the seed, which must change no answer the chain
+    gives), and the ``bypass`` (it offers a two-hop route to a target that
+    is three admitted hops away, so a depth-limited answer reads the depth
+    assignment — ``D-IMPL-268``: a phantom endpoint must not consume depth,
+    create a path, or participate in a cycle even where the final entity
+    set would coincidentally match).
+
+    The ``X -> B`` edge is stored subject-first, unlike
+    :func:`chain_claims`' ``seed -> mid <- target``: under the corpus's own
+    orientation a forward walk would stop at the unresolved endpoint under
+    every implementation and the directed half of the question could not
+    discriminate. Every backend is held byte-identical to the fallback on
+    each shape, whether it pushes the walk or declines it (`GQ-32` at
+    docs/GRAPH_QUERY_SEMANTICS.md:583).
+    """
+    variant = draw(st.sampled_from(UNRESOLVED_REFERENCE_VARIANTS))
+    return unresolved_reference_case(variant)
+
+
 def corpus_cases() -> st.SearchStrategy[CorpusCase]:
     """The whole corpus: one drawn case from the named shape families."""
     return st.one_of(
@@ -926,4 +1188,5 @@ def corpus_cases() -> st.SearchStrategy[CorpusCase]:
         allowed_entities_cases(),
         degenerate_and_family_cases(),
         offset_authored_validity_cases(),
+        unresolved_reference_cases(),
     )
```

## 3. `tests/operators/test_traversal_admission.py` — DIFF

```diff
diff --git a/tests/operators/test_traversal_admission.py b/tests/operators/test_traversal_admission.py
index 5badfe10..fd1aea3d 100644
--- a/tests/operators/test_traversal_admission.py
+++ b/tests/operators/test_traversal_admission.py
@@ -12,10 +12,15 @@ and its control are read off the same state:
   path to it ran through the excluded node (`GQ-13`);
 * the all-admitted control on the same view reaches every neighbor, and the
   ``None`` sentinel reaches the same set (additive over breaking, D-10);
-* ``src/ccf/graph/fallback.py::_walk`` — the differential oracle every
-  pushed answer is held byte-identical to — agrees with
+* ``src/ccf/graph/fallback.py::answer`` — the query tier's ruled sequence,
+  closure included — agrees with
   ``src/ccf/operators/categories.py::TraversalNeighborhood.apply`` in every
-  configuration;
+  configuration, BY BYTES, on the fully-claimed view AND on a dangling shape.
+  The oracle used to be the bare ``src/ccf/graph/fallback.py::_walk``, which
+  is only step 5 of that sequence: it skipped the endpoint closure and so
+  agreed with the shipped operator on exactly the shape the two tiers used to
+  disagree on, leaving this check green in both states (`D-GATE-24.5` R1).
+  Superseded in 24.8 (`D-IMPL-267` D-05, mechanism `D-IMPL-268`);
 * a start of an unadmitted class stays in the answer and still expands.
 
 **The sabotage control.** ``src/ccf/operators/categories.py`` is copied to a
@@ -42,8 +47,14 @@ from types import ModuleType
 
 import pytest
 
-from ccf.graph.fallback import _walk
-from ccf.graph.protocols import EntityRecord, GraphView, RelationshipRecord
+from ccf.contracts.canonical import canonical_bytes
+from ccf.graph.fallback import answer
+from ccf.graph.protocols import (
+    EntityRecord,
+    GraphQuery,
+    GraphView,
+    RelationshipRecord,
+)
 from ccf.operators.categories import TraversalNeighborhood
 from ccf.operators.params import TraversalNeighborhoodParameters
 
@@ -77,6 +88,9 @@ S_URI = ENTITY_POOL[SEED_CLASS][0]
 A_URI = ENTITY_POOL[ADMITTED_CLASS][0]
 B_URI = ENTITY_POOL[EXCLUDED_CLASS][0]
 C_URI = ENTITY_POOL[ADMITTED_CLASS][1]
+#: The dangling endpoint of ``dangling_view()`` — drawn from the pool and never
+#: given an ``_entity`` record, so it is named by edges and by nothing else.
+DANGLING_URI = ENTITY_POOL[EXCLUDED_CLASS][2]
 
 EARLY = INSTANTS[0]
 BUNDLE: str = GENERATION["permitted_policy_bundle_version"]
@@ -164,14 +178,77 @@ def reached_by(operator: TraversalNeighborhood, view: GraphView = VIEW) -> set[s
     return {record.claim.entity_uri for record in output.view.entities}
 
 
-def reached_by_fallback(operator: TraversalNeighborhood, view: GraphView = VIEW) -> set[str]:
-    """The oracle's answer to the operator's own mirrored ``TraversalSpec``."""
+def oracle_view(operator: TraversalNeighborhood, view: GraphView = VIEW) -> GraphView:
+    """The reference semantics for the operator's own question, frozen as a view.
+
+    ``src/ccf/graph/fallback.py::answer``, NOT
+    ``src/ccf/graph/fallback.py::_walk``. The bare walk is only step 5 of the
+    ruled sequence; step 4 endpoint-closes the surviving edges against the
+    surviving entity universe first (`GQ-16` at
+    docs/GRAPH_QUERY_SEMANTICS.md:316, `GQ-13` at
+    docs/GRAPH_QUERY_SEMANTICS.md:261), and that closure is part of the
+    reference semantics every tier now shares (`D-IMPL-267` D-05/D-08,
+    mechanism `D-IMPL-268`). An oracle that skipped it agreed with the shipped
+    operator on exactly the dangling shape the two tiers used to disagree on,
+    so it could not discriminate — `D-GATE-24.5` R1, and the reason this
+    function was re-derived in 24.8.
+
+    The freeze reproduces the two sorts
+    ``tests/conformance/test_substrate_differential.py::_frozen_at`` applies,
+    so ordering is the interface's on both sides and the equality below is
+    about semantics, not collection order (`GQ-22` at
+    docs/GRAPH_QUERY_SEMANTICS.md:461).
+    """
     fragment = operator.read_intent()
     assert fragment.traverse is not None
-    entities, _edges = _walk(
-        view.entities, view.relationships, traverse=fragment.traverse, seeds=None
+    entities, relationships = answer(
+        view.entities,
+        view.relationships,
+        query=GraphQuery(
+            tenant_id=TENANT, as_of=view.as_of, traverse=fragment.traverse
+        ),
+    )
+    return GraphView(
+        tenant_id=TENANT,
+        as_of=view.as_of,
+        entities=tuple(sorted(entities, key=lambda record: record.claim.entity_uri)),
+        relationships=tuple(
+            sorted(relationships, key=lambda record: record.relationship_key)
+        ),
+    )
+
+
+def answered_view(
+    operator: TraversalNeighborhood, view: GraphView = VIEW
+) -> GraphView:
+    """What the in-process operator tier answers over ``view``."""
+    output = operator.apply(
+        view=view, tenant_id=TENANT, temporal_boundary=BOUNDARY, upstream=()
     )
-    return {record.claim.entity_uri for record in entities}
+    return output.view
+
+
+def dangling_view() -> GraphView:
+    """S seeds; one edge to a URI carrying NO entity claim, and one on from it.
+
+    The same G-28 shape as
+    ``tests/operators/test_traversal_unresolved_reference.py``, built in this
+    module's own vocabulary so the oracle above is exercised on the state that
+    discriminates. The claim-less URI is drawn from the excluded class's pool
+    and given no ``_entity`` record, so it carries no class either — which is
+    why the admitted-set parametrization agrees under BOTH the old and the new
+    walk (a claim-less node has no class, so admission excluded it already),
+    and only ``admitted=None`` separates them.
+    """
+    entities = (
+        _entity(S_URI, SEED_CLASS),
+        _entity(A_URI, ADMITTED_CLASS),
+    )
+    relationships = (
+        _edge(S_URI, DANGLING_URI),
+        _edge(DANGLING_URI, A_URI),
+    )
+    return _view(entities, relationships)
 
 
 # --- the exclusion and its controls ------------------------------------------
@@ -259,12 +336,53 @@ def test_starts_are_never_filtered_by_admission() -> None:
 def test_the_fallback_walk_agrees_with_the_operator(
     seed_classes: frozenset[str], admitted: frozenset[str] | None
 ) -> None:
-    """The oracle answers the mirrored spec with the operator's own entity set (D-04)."""
+    """The oracle answers the mirrored spec with the operator's own answer, BY BYTES.
+
+    Equality on ``canonical_bytes`` rather than on a URI set, because the
+    ruling is byte-identical canonical results, not "same set" (`D-IMPL-267`
+    D-05/P-2): ordering drift alone poisons replay and content addressing, so
+    a set comparison would let it through.
+    """
     operator = traversal(seed_classes=seed_classes, admitted=admitted)
     fragment = operator.read_intent()
     assert fragment.traverse is not None
     assert fragment.traverse.admitted_entity_classes == admitted
-    assert reached_by_fallback(operator) == reached_by(operator)
+    assert canonical_bytes(answered_view(operator)) == canonical_bytes(
+        oracle_view(operator)
+    )
+
+
+@pytest.mark.parametrize(
+    "admitted",
+    [None, frozenset({ADMITTED_CLASS})],
+    ids=["none-sentinel", "one-class"],
+)
+def test_the_oracle_is_answer_not_walk_on_the_dangling_shape(
+    admitted: frozenset[str] | None,
+) -> None:
+    """The shape that separates ``answer`` from ``_walk`` — and the two walks (D-05).
+
+    On ``dangling_view()`` at ``depth_limit=2`` the ruled answer is the seed
+    alone: the edge S -> (claim-less URI) is persisted state and not a hop, so
+    A is unreachable even though a persisted two-hop route names it
+    (`D-IMPL-267` D-01/D-02/D-07).
+
+    ``[none-sentinel]`` is the discriminating parametrization: against the base
+    ``categories.py`` — the shipped walk before `D-IMPL-268` — the operator
+    answers ``{S, A}`` where the reference answers ``{S}``, and this assertion
+    is RED. ``[one-class]`` passes under BOTH walks and is here as the control:
+    a claim-less node carries no class, so an admitted SET excluded it already,
+    which is precisely why an admission-only instrument never caught G-28.
+    """
+    operator = traversal(admitted=admitted, depth=2)
+    view = dangling_view()
+    assert canonical_bytes(answered_view(operator, view)) == canonical_bytes(
+        oracle_view(operator, view)
+    )
+    reached = {record.claim.entity_uri for record in answered_view(operator, view).entities}
+    assert reached == {S_URI}, (
+        f"the walk crossed the unresolved reference: reached {sorted(reached)}"
+    )
 
 
 def test_read_intent_mirrors_admission_field_for_field() -> None:
```


READ-PROOF bundle-tests-part-2: 726378dc7147ade40bc98aac

## 4. `tests/operators/test_traversal_direction.py` — DIFF

```diff
diff --git a/tests/operators/test_traversal_direction.py b/tests/operators/test_traversal_direction.py
index c9655108..4f9e350a 100644
--- a/tests/operators/test_traversal_direction.py
+++ b/tests/operators/test_traversal_direction.py
@@ -14,7 +14,8 @@ stored INTO the seed is the whole difference:
 
 * the forward walk does not cross that edge and reaches strictly less; the
   neighborhood walk on the same view still reaches it (additive, D-10);
-* ``src/ccf/graph/fallback.py::_walk`` — the differential oracle — agrees
+* ``src/ccf/graph/fallback.py::answer`` — the differential oracle, endpoint
+  closure included (`GQ-16` at docs/GRAPH_QUERY_SEMANTICS.md:316) — agrees
   with BOTH operators at every depth, so the two walks and the oracle are
   three spellings of one `GQ-10`;
 * the direction is fixed by the operator, never by a parameter;
@@ -52,6 +53,7 @@ written in this file (CLAUDE.md §6.4).
 
 from __future__ import annotations
 
+import ast
 import functools
 import importlib.util
 import json
@@ -62,12 +64,13 @@ from types import ModuleType
 
 import pytest
 
+from ccf.contracts.canonical import canonical_bytes
 from ccf.graph.backends.fluree import FlureeGraphReader
 from ccf.graph.backends.mongo import MongoGraphReader
 from ccf.graph.backends.neo4j import Neo4jGraphReader
 from ccf.graph.backends.postgres import PostgresGraphReader
 from ccf.graph.backends.sqlite import SqliteGraphReader
-from ccf.graph.fallback import _walk
+from ccf.graph.fallback import answer
 from ccf.graph.protocols import (
     EntityRecord,
     GraphQuery,
@@ -192,6 +195,36 @@ def _descendants(depth: int) -> TraversalDescendants:
     )
 
 
+def _fallback_view(view: GraphView, traverse: TraversalSpec) -> GraphView:
+    """The query tier's answer to the operator's own intent, frozen as a view.
+
+    ``answer`` is the whole query-tier oracle — the as-of survival predicate,
+    the policy and validity gates, endpoint closure (`GQ-16` at
+    docs/GRAPH_QUERY_SEMANTICS.md:316) and only then the walk — where the
+    private ``_walk`` is the last of those steps alone and relies on its
+    caller to have closed for it. Since semantics version 1.3.0 the closure
+    precedes EVERY walk at every tier, so the tier boundary is the right
+    place to take the oracle. Frozen under the interface's ordering
+    (`GQ-22` at docs/GRAPH_QUERY_SEMANTICS.md:461), which is the ordering
+    ``_view`` already imposes on the operator's input.
+    """
+    entities, relationships = answer(
+        view.entities,
+        view.relationships,
+        query=GraphQuery(
+            tenant_id=TENANT, as_of=view.as_of, traverse=traverse
+        ),
+    )
+    return GraphView(
+        tenant_id=view.tenant_id,
+        as_of=view.as_of,
+        entities=tuple(sorted(entities, key=lambda r: r.claim.entity_uri)),
+        relationships=tuple(
+            sorted(relationships, key=lambda r: r.relationship_key)
+        ),
+    )
+
+
 def _reached(operator: Operator, view: GraphView = VIEW) -> frozenset[str]:
     output = operator.apply(
         view=view, tenant_id=TENANT, temporal_boundary=BOUNDARY, upstream=()
@@ -237,24 +270,27 @@ def test_the_forward_walk_still_follows_a_chain_of_stored_edges() -> None:
 def test_the_fallback_walk_agrees_with_the_operator(
     build: object, depth: int
 ) -> None:
-    """`_walk` under the operator's own `read_intent()` answers what `apply()` does.
-
-    Entities AND edges: `_walk` prunes to edges among reached nodes exactly
-    as `_substitute` does (INV-CH7-40), so the two answers are compared whole.
-    This is the equality the differential suite rests on — a pushed answer is
-    held to `_walk`, and `_walk` is held here to the operator.
+    """`answer` under the operator's own `read_intent()` answers what `apply()` does.
+
+    Entities AND edges, compared as canonical bytes: the query tier prunes to
+    edges among reached nodes exactly as `_substitute` does (INV-CH7-40), so
+    the two answers are compared whole. This is the equality the differential
+    suite rests on — a pushed answer is held to `answer`, endpoint closure
+    included, and `answer` is held here to the operator. ``VIEW`` is fully
+    claimed (every endpoint of every edge is one of its four entities), so
+    the closure is a no-op on it and this equality is the 1.2.0 equality
+    unchanged; the shape that discriminates the tiers is the unresolved
+    reference, and it is proved in
+    ``tests/operators/test_traversal_unresolved_reference.py``.
     """
     operator = build(depth)  # type: ignore[operator]
     fragment = operator.read_intent()
     assert fragment.traverse is not None
-    entities, edges = _walk(
-        VIEW.entities, VIEW.relationships, traverse=fragment.traverse, seeds=None
-    )
+    expected = _fallback_view(VIEW, fragment.traverse)
     output = operator.apply(
         view=VIEW, tenant_id=TENANT, temporal_boundary=BOUNDARY, upstream=()
     )
-    assert entities == output.view.entities
-    assert edges == output.view.relationships
+    assert canonical_bytes(expected) == canonical_bytes(output.view)
 
 
 def test_direction_and_admission_compose_on_the_descendant_walk() -> None:
@@ -271,7 +307,7 @@ def test_direction_and_admission_compose_on_the_descendant_walk() -> None:
       is unreachable — admission prunes the hop, and direction still keeps P out;
     * the two controls that isolate each lever: undirected + parent admitted
       reaches P; forward + no admission reaches A and C.
-    The fallback's ``_walk`` agrees with each, entities and edges.
+    The fallback's ``answer`` agrees with each, entities and edges.
     """
     def descendants(admitted: frozenset[str] | None) -> TraversalDescendants:
         return TraversalDescendants(
@@ -305,14 +341,11 @@ def test_direction_and_admission_compose_on_the_descendant_walk() -> None:
     ):
         fragment = operator.read_intent()
         assert fragment.traverse is not None
-        entities, edges = _walk(
-            VIEW.entities, VIEW.relationships, traverse=fragment.traverse, seeds=None
-        )
+        expected = _fallback_view(VIEW, fragment.traverse)
         output = operator.apply(
             view=VIEW, tenant_id=TENANT, temporal_boundary=BOUNDARY, upstream=()
         )
-        assert entities == output.view.entities
-        assert edges == output.view.relationships
+        assert canonical_bytes(expected) == canonical_bytes(output.view)
 
 
 # --- the direction is the operator's, never a parameter's --------------------
@@ -524,15 +557,156 @@ def test_the_sibling_is_registered_beside_the_neighborhood() -> None:
     )
 
 
-# --- the vocabulary records the direction at 1.2.0 ---------------------------
+# --- one walk, structurally: both operators call it --------------------------
 
+#: The exact call the sabotage below re-points at a private copy. The shared
+#: walk is invoked once per ``apply`` — twice in the whole module — and the
+#: literal is asserted PRESENT at that count in the real source before any
+#: copy is mutated, so the control cannot pass vacuously against a file that
+#: never carried it. Same discipline as ``FORWARD_BRANCH`` above.
+WALK_CALL = "        entities, traversable = _bounded_walk(\n"
 
-def test_the_semantics_document_records_the_direction_at_1_2_0() -> None:
-    """`GQ-10` names both directions and `GQ-35` carries the 1.2.0 entry."""
-    document = (REPO_ROOT / "docs" / "GRAPH_QUERY_SEMANTICS.md").read_text(
+
+def _apply_callees(source: str) -> dict[str, set[str]]:
+    """Per traversal class, the plain-name callees of its ``apply`` body.
+
+    ``ast.Name`` in ``func`` position only: an attribute call on ``self`` or
+    on an imported module is deliberately not collected, because the property
+    under test is that the ONE module-level function is what both bodies
+    reach for.
+    """
+    wanted = {"TraversalNeighborhood", "TraversalDescendants"}
+    callees: dict[str, set[str]] = {}
+    for node in ast.walk(ast.parse(source)):
+        if not isinstance(node, ast.ClassDef) or node.name not in wanted:
+            continue
+        for member in node.body:
+            if not isinstance(member, ast.FunctionDef) or member.name != "apply":
+                continue
+            callees[node.name] = {
+                inner.func.id
+                for inner in ast.walk(member)
+                if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name)
+            }
+    return callees
+
+
+def _bounded_walk_definitions(source: str) -> int:
+    """How many module-level ``def _bounded_walk`` the source declares."""
+    return sum(
+        1
+        for node in ast.parse(source).body
+        if isinstance(node, ast.FunctionDef) and node.name == "_bounded_walk"
+    )
+
+
+def _assert_one_walk_pin(source: str) -> None:
+    """The pin's assertion body, factored so its control can run it on a copy."""
+    assert _bounded_walk_definitions(source) == 1, (
+        "the shared bounded walk is not defined exactly once at module level"
+    )
+    callees = _apply_callees(source)
+    assert set(callees) == {"TraversalNeighborhood", "TraversalDescendants"}
+    for class_name, called in sorted(callees.items()):
+        assert "_bounded_walk" in called, (
+            f"{class_name}.apply does not call the shared _bounded_walk;"
+            f" it calls {sorted(called)} — the two traversal shapes have drifted"
+        )
+
+
+def test_both_traversal_operators_call_the_one_bounded_walk() -> None:
+    """D-08 (a): one walk, defined once, called by both ``apply`` bodies.
+
+    ``src/ccf/operators/categories.py`` says so in prose at its head — the two
+    walks *"differ in exactly that line and nothing else"* — and that sentence
+    is what makes the conforming change of `D-IMPL-268` a single edit rather
+    than two edits that can disagree. Ledger row ``24.5-L-06`` created the
+    sibling; ``24.5-L-06``'s companion pin
+    ``tests/operators/test_traversal_direction.py::test_the_sibling_is_registered_beside_the_neighborhood``
+    pins the roster, and this one pins the shared mechanism underneath it.
+
+    Structural, not textual: the assertion is over the parsed ``apply``
+    bodies, so a reformatting of the call site does not red it and a private
+    copy of the walk does — which is exactly what the control below shows.
+    """
+    real = CATEGORIES_SOURCE.read_text(encoding="utf-8")
+    assert real.count(WALK_CALL) == 2, (
+        "the shared-walk call site moved; re-anchor WALK_CALL against"
+        " src/ccf/operators/categories.py"
+    )
+    _assert_one_walk_pin(real)
+
+
+def test_control_the_one_walk_pin_fails_on_a_copy_with_a_private_walk(
+    tmp_path: pathlib.Path,
+) -> None:
+    """Sabotage in a scratch copy: the descendants walk gets its own private walk.
+
+    The LAST of the two call sites is re-pointed at ``_private_bounded_walk``
+    and an alias for it is appended, so the copy is a module in which the two
+    operators no longer share one walk — and could therefore drift — while
+    still answering exactly what it answered before. The pin above fails on
+    the copy naming ``TraversalDescendants``; the copy still walks. The
+    sabotage removed the pin's premise and nothing else, which is what makes
+    the control discriminating rather than merely red.
+
+    The alias name deliberately ends in ``_bounded_walk(`` at its call site,
+    so this control's own literal is not a second hit for the tree-wide
+    bare-``_walk`` search the phase asserts elsewhere.
+    """
+    real = CATEGORIES_SOURCE.read_text(encoding="utf-8")
+    assert real.count(WALK_CALL) == 2, "the shared-walk call site moved; re-anchor"
+    head, _match, tail = real.rpartition(WALK_CALL)
+    sabotaged = (
+        head
+        + "        entities, traversable = _private_bounded_walk(\n"
+        + tail
+        + "\n_private_bounded_walk = _bounded_walk\n"
+    )
+    assert sabotaged.count(WALK_CALL) == 1
+
+    with pytest.raises(AssertionError, match="TraversalDescendants"):
+        _assert_one_walk_pin(sabotaged)
+
+    module = _import_scratch_copy(sabotaged, "_ccf_categories_private_walk", tmp_path)
+    copy = module.TraversalDescendants(
+        parameters=TraversalDescendantsParameters(
+            seed_entity_classes=frozenset({SEED_CLASS}),
+            relationship_types=frozenset({EDGE_TYPE}),
+            depth_limit=1,
+        )
+    )
+    assert _reached(copy) == _reached(_descendants(1))
+    deeper = module.TraversalDescendants(
+        parameters=TraversalDescendantsParameters(
+            seed_entity_classes=frozenset({SEED_CLASS}),
+            relationship_types=frozenset({EDGE_TYPE}),
+            depth_limit=2,
+        )
+    )
+    assert _reached(deeper) == _reached(_descendants(2))
+
+
+# --- the vocabulary records the direction, and the universe at 1.3.0 ---------
+
+
+def _semantics_document() -> str:
+    return (REPO_ROOT / "docs" / "GRAPH_QUERY_SEMANTICS.md").read_text(
         encoding="utf-8"
     )
-    assert "**Semantics version: 1.2.0**" in document
+
+
+def test_the_semantics_document_records_the_direction_at_1_2_0() -> None:
+    """`GQ-10` names both directions and `GQ-35` still carries the 1.2.0 entry.
+
+    The banner follows the document forward — it reads 1.3.0 since the
+    traversal-universe amendment — but the 1.2.0 ENTRY is untouched: `GQ-35`
+    appends, it never rewrites the clause or the entry it amends out of
+    existence, so the direction's own record is asserted here as it was
+    written.
+    """
+    document = _semantics_document()
+    assert "**Semantics version: 1.3.0**" in document
     clause = document.split("### `GQ-10`")[1].split("### `GQ-11`")[0]
     assert 'direction="undirected"' in clause and 'direction="forward"' in clause
     amendments = document.split("### `GQ-35`")[1]
@@ -541,6 +715,86 @@ def test_the_semantics_document_records_the_direction_at_1_2_0() -> None:
     assert "20 / 21 / 22" in entry and "20 / 22 / 22" in entry
 
 
+def _assert_records_the_traversal_universe_at_1_3_0(document: str) -> None:
+    """The 1.3.0 amendment, asserted against a document STRING.
+
+    Factored so the two controls below can run it over a mutated copy of the
+    real text without touching the file (ledger row `CP04-G-28`,
+    `D-IMPL-267`).
+    """
+    assert "**Semantics version: 1.3.0**" in document
+    banner = "\n".join(document.split("\n")[:10])
+    assert "1.3.0 the traversal universe" in banner
+    clause = document.split("### `GQ-10`")[1].split("### `GQ-11`")[0]
+    assert "unresolved reference" in clause
+    amendments = document.split("### `GQ-35`")[1]
+    assert amendments.index("- **1.3.0**") < amendments.index("- **1.2.0**"), (
+        "the amendment history is newest-first; the 1.3.0 entry must sit"
+        " above the 1.2.0 entry"
+    )
+    entry = amendments.split("- **1.3.0**")[1].split("- **1.2.0**")[0]
+    for token in (
+        "CP04-G-28",
+        "D-IMPL-267",
+        "{A,B}",
+        "{A}",
+        "{A,B,C,D}",
+        "{A,C,D}",
+        "not the same universe",
+        "execution-path invariant",
+        "test_operator_tier_differential",
+    ):
+        assert token in entry, f"the 1.3.0 entry does not carry {token!r}"
+
+
+def test_the_semantics_document_records_the_traversal_universe_at_1_3_0() -> None:
+    """`GQ-10` defines the unresolved reference and `GQ-35` carries 1.3.0."""
+    _assert_records_the_traversal_universe_at_1_3_0(_semantics_document())
+
+
+def _with_the_1_3_0_entry_moved_below_1_2_0(document: str) -> str:
+    """The amendment history re-ordered oldest-first at its top — on a STRING."""
+    head, rest = document.split("- **1.3.0**", 1)
+    newest, rest = rest.split("- **1.2.0**", 1)
+    older, rest = rest.split("- **1.1.0**", 1)
+    return f"{head}- **1.2.0**{older}- **1.3.0**{newest}- **1.1.0**{rest}"
+
+
+def test_control_the_1_3_0_pin_fails_on_a_reverted_banner() -> None:
+    """Two sabotages of the document TEXT; the file itself is never edited.
+
+    (1) the banner reverted to the previous version — the pin must red, or it
+    is not pinning the version; (2) the 1.3.0 entry moved BELOW the 1.2.0
+    entry — the newest-first order is asserted, not assumed. Both run on
+    copies of the real text, in the voice of
+    ``tests/operators/test_traversal_admission.py::test_no_control_edits_the_real_source_tree``:
+    the real document's cleanliness is asserted through ``git`` afterwards.
+    """
+    document = _semantics_document()
+    _assert_records_the_traversal_universe_at_1_3_0(document)
+
+    reverted = document.replace(
+        "**Semantics version: 1.3.0**", "**Semantics version: 1.2.0**", 1
+    )
+    assert reverted != document, "the banner literal moved; re-anchor the control"
+    with pytest.raises(AssertionError):
+        _assert_records_the_traversal_universe_at_1_3_0(reverted)
+
+    reordered = _with_the_1_3_0_entry_moved_below_1_2_0(document)
+    assert reordered != document, "the entry slicing moved; re-anchor the control"
+    with pytest.raises(AssertionError):
+        _assert_records_the_traversal_universe_at_1_3_0(reordered)
+
+    status = subprocess.run(
+        ["git", "status", "--short", "--", "docs/GRAPH_QUERY_SEMANTICS.md"],
+        cwd=REPO_ROOT,
+        capture_output=True,
+        text=True,
+        check=True,
+    ).stdout
+    assert status == "", f"a control edited the real document: {status!r}"
+
+
 # --- the sabotage control: the copy without the forward branch fails ---------
 
 
@@ -755,24 +1009,24 @@ def test_the_depth_2_divergent_node_is_the_cycle_closer_by_id() -> None:
     ids=["typed-neighborhood", "typed-descendants"],
 )
 def test_the_fallback_agrees_on_both_walks(build: object, depth: int) -> None:
-    """`_walk` under each operator's own intent answers the fixture identically.
+    """`answer` under each operator's own intent answers the fixture identically.
 
     The oracle every backend is held to, held here to the operator on the
-    criterion's own graph — entities AND edges — so the 20/21/22 and
-    20/22/22 figures are the fallback's figures too.
+    criterion's own graph — entities AND edges, as canonical bytes — so the
+    20/21/22 and 20/22/22 figures are the fallback's figures too.
+    ``family_view`` asserts every edge endpoint is a member, so the fixture
+    carries no unresolved reference and endpoint closure changes nothing
+    here: this equality held before semantics version 1.3.0 and holds after.
     """
     view = family_view()
     operator = build(depth)  # type: ignore[operator]
     fragment = operator.read_intent()
     assert fragment.traverse is not None
-    entities, edges = _walk(
-        view.entities, view.relationships, traverse=fragment.traverse, seeds=None
-    )
+    expected = _fallback_view(view, fragment.traverse)
     output = operator.apply(
         view=view, tenant_id=TENANT, temporal_boundary=BOUNDARY, upstream=()
     )
-    assert entities == output.view.entities
-    assert edges == output.view.relationships
+    assert canonical_bytes(expected) == canonical_bytes(output.view)
 
 
 def test_control_the_fixture_measurement_fails_on_a_copy_that_ignores_direction(
```

## 5. `tests/properties/test_composition.py` — DIFF

```diff
diff --git a/tests/properties/test_composition.py b/tests/properties/test_composition.py
index ff5460c6..1a7ab001 100644
--- a/tests/properties/test_composition.py
+++ b/tests/properties/test_composition.py
@@ -25,7 +25,13 @@ surfaces here as a byte difference rather than as a silent wrong answer.
 
 **Two classes of input** (D-14): Hypothesis-generated banking-shaped states,
 and the curated edge graphs — empty result, fully policy-filtered, temporal
-boundary — that generation is unlikely to hit reliably.
+boundary, and (since 24.8) an unresolved reference — that generation is
+unlikely to hit reliably.
+
+**One algebraic consequence the pair law cannot see.** The n² law holds under
+both the shipped and the conforming traversal walk on the dangling case, so
+``T(T(G)) = T(G)`` is asserted separately for each traversal shape at the end
+of this module (`D-IMPL-268`, whitepaper §7.4).
 """
 
 from __future__ import annotations
@@ -76,6 +82,17 @@ TRAVERSAL_KEY = "traversal.typed-neighborhood"
 #: on its own.
 OTHER_KEYS: tuple[str, ...] = tuple(k for k in OPERATOR_KEYS if k != TRAVERSAL_KEY)
 
+#: Every shipped key in the TRAVERSAL category — the two shapes today
+#: (ledger row ``24.5-L-06``), derived from the registry's own category
+#: assignment rather than by name, so a third shape joins the idempotence
+#: test below on its own.
+TRAVERSAL_KEYS: tuple[str, ...] = tuple(
+    key
+    for key in OPERATOR_KEYS
+    if REGISTRY.registration(key).category
+    == REGISTRY.registration(TRAVERSAL_KEY).category
+)
+
 
 def admitted_traversal() -> TraversalNeighborhood:
     """The shipped traversal with ``admitted_entity_classes`` set (ledger row ``24.5-L-05``).
@@ -266,6 +283,85 @@ def test_the_policy_filtered_graph_is_actually_emptied_by_policy() -> None:
 
 
 def test_the_curated_set_covers_the_three_named_edge_cases() -> None:
-    """D-14 names them explicitly; a fixture set that dropped one is a defect."""
+    """D-14 names three explicitly; since 24.8 the set is four.
+
+    A fixture set that dropped one is a defect, and the assertion is a subset
+    check so an ADDED case never reds it — which is why the fourth has to be
+    named here rather than left to arrive on its own. ``unresolved-reference``
+    (G-28, `D-IMPL-267`) is the persisted-edge-onto-an-unclaimed-endpoint
+    shape; it is the state the two traversal tiers disagreed on, and the
+    fixture losing it would silently retire the coverage this phase added.
+
+    The node id is deliberately unchanged: the criteria cite it, and a
+    strengthened assertion under the same id is what keeps that citation
+    resolvable. It reads "three named" because D-14 named three; the fourth
+    is 24.8's addition and is asserted below with the rest.
+    """
     names = {case.name for case in CURATED}
-    assert {"empty-result", "policy-filtered", "temporal-boundary"} <= names
+    assert {
+        "empty-result",
+        "policy-filtered",
+        "temporal-boundary",
+        "unresolved-reference",
+    } <= names
+
+
+@pytest.mark.parametrize("key", TRAVERSAL_KEYS, ids=list(TRAVERSAL_KEYS))
+def test_each_traversal_operator_is_idempotent_on_the_unresolved_reference_case(
+    key: str,
+) -> None:
+    """``T(T(G)) = T(G)`` on the dangling case, by bytes — whitepaper §7.4.
+
+    A traversal is a selection: applying it to its own answer must be the
+    answer again, or the operator algebra's fixed point does not exist and a
+    replayed two-segment plan can disagree with the one-segment plan that
+    recorded it. On the shipped in-process walk this FAILS for the undirected
+    neighborhood (RESEARCH F-3): the first application crosses the unclaimed
+    endpoint and returns the entity beyond it, the second application sees a
+    view in which the phantom route is gone and returns strictly less.
+
+    This is coverage with a sharp edge, not the phase's discriminating
+    instrument: the 25-pair composition law itself holds under either walk on
+    this case (24.8-VALIDATION.md, composition row), so the proof of the
+    ruled semantics is the differential and the in-process oracle module.
+    What this test adds is the one algebraic consequence the pair law cannot
+    see. `D-IMPL-268`.
+    """
+    assert len(TRAVERSAL_KEYS) == 2, (
+        "the traversal category's shape roster moved; a third shape joins this"
+        f" test on its own, but the count is pinned so it cannot do so"
+        f" unnoticed: {TRAVERSAL_KEYS}"
+    )
+    case = next(item for item in CURATED if item.name == "unresolved-reference")
+    # The phantom URI is read OFF the case: the edge endpoint that carries no
+    # entity claim. Never a module-level literal — the fixture owns the value.
+    claimed = {record.claim.entity_uri for record in case.view.entities}
+    endpoints = {
+        uri
+        for edge in case.view.relationships
+        for uri in (edge.claim.subject_uri, edge.claim.object_uri)
+    }
+    unresolved = endpoints - claimed
+    assert len(unresolved) == 1, f"the curated case lost its dangling shape: {case.name}"
+    phantom = next(iter(unresolved))
+
+    operator = REGISTRY.resolve(key)
+    once = operator.apply(
+        view=case.view, tenant_id=TENANT, temporal_boundary=BOUNDARY, upstream=()
+    )
+    twice = operator.apply(
+        view=once.view,
+        tenant_id=TENANT,
+        temporal_boundary=BOUNDARY,
+        upstream=(once.provenance,),
+    )
+    assert phantom not in {
+        record.claim.entity_uri for record in once.view.entities
+    }, f"{key} emitted the unresolved endpoint"
+    assert canonical_bytes(twice.view) == canonical_bytes(once.view), (
+        f"{key} is not idempotent on the unresolved-reference case:"
+        " the second application answers"
+        f" {sorted(record.claim.entity_uri for record in twice.view.entities)}"
+        " where the first answered"
+        f" {sorted(record.claim.entity_uri for record in once.view.entities)}"
+    )
```

## 6. `tests/fixtures/banking/edge_graphs.yaml` — DIFF

```diff
diff --git a/tests/fixtures/banking/edge_graphs.yaml b/tests/fixtures/banking/edge_graphs.yaml
index 47bf3111..be1fcc4a 100644
--- a/tests/fixtures/banking/edge_graphs.yaml
+++ b/tests/fixtures/banking/edge_graphs.yaml
@@ -9,8 +9,9 @@
 #
 #   `graphs` — curated graph states holding the edge cases generation is
 #   unlikely to produce reliably: a state every operator empties, a state the
-#   Policy operator removes entirely, and claims sitting exactly on the
-#   temporal boundary in every configuration that matters.
+#   Policy operator removes entirely, claims sitting exactly on the temporal
+#   boundary in every configuration that matters, and — since 24.8 — a
+#   persisted edge onto an endpoint no entity claim covers.
 #
 # The decision boundary these are written against is
 # controlplane.yaml `decision.temporal_boundary` (2026-03-01T10:00:00Z).
@@ -156,3 +157,50 @@ graphs:
         policy_bundle_version: "acme-bank/policy-bundle@2026-03-01"
         observed_at: 2026-03-01T10:00:00Z
         valid_from: 2026-03-01T10:00:00Z
+
+  # 4. A persisted edge whose endpoint carries no entity claim — an UNRESOLVED
+  #    REFERENCE (G-28, `D-IMPL-267`). `acme-bank:facility:unresolved-1` is
+  #    named by two edges and declared under no entity: legal persisted state
+  #    (whitepaper §7.3, INV-CH7-20 — edges are first-class claims, never
+  #    derived joins), and not a traversal member (P-1). This is the shape the
+  #    two tiers disagreed on: the operator tier's in-process walk steps onto
+  #    the claim-less URI, spends a hop of the controlplane's depth-2 budget on
+  #    it, and arrives at the guarantee on the far side; the query tier
+  #    endpoint-closes first and answers the anchor alone.
+  #
+  #    What the case detects here, beyond coverage: `T(T(G)) != T(G)` on the
+  #    shipped neighborhood walk — the second application sees the pruned view,
+  #    in which the phantom route is gone, and answers strictly less. And the
+  #    Traversal∘Policy / Policy∘Traversal orderings both have to close the same
+  #    edge, whichever ran first.
+  - name: unresolved-reference
+    entities:
+      - entity_uri: "acme-bank:counterparty:claimed-anchor-1"
+        entity_class: counterparty
+        classification: internal
+        policy_bundle_version: "acme-bank/policy-bundle@2026-03-01"
+        observed_at: 2026-03-01T08:00:00Z
+        valid_from: 2026-03-01T08:00:00Z
+      - entity_uri: "acme-bank:guarantee:claimed-beyond-1"
+        entity_class: guarantee
+        classification: internal
+        policy_bundle_version: "acme-bank/policy-bundle@2026-03-01"
+        observed_at: 2026-03-01T08:00:00Z
+        valid_from: 2026-03-01T08:00:00Z
+    relationships:
+      # Both edges name the same unresolved facility URI, from the two
+      # ontology-legal directions (obligor_of: counterparty→facility;
+      # guarantees: guarantee→facility), so the fixture stays a legal banking
+      # graph while the endpoint stays unclaimed.
+      - relationship_type: obligor_of
+        subject_uri: "acme-bank:counterparty:claimed-anchor-1"
+        object_uri: "acme-bank:facility:unresolved-1"
+        policy_bundle_version: "acme-bank/policy-bundle@2026-03-01"
+        observed_at: 2026-03-01T08:00:00Z
+        valid_from: 2026-03-01T08:00:00Z
+      - relationship_type: guarantees
+        subject_uri: "acme-bank:guarantee:claimed-beyond-1"
+        object_uri: "acme-bank:facility:unresolved-1"
+        policy_bundle_version: "acme-bank/policy-bundle@2026-03-01"
+        observed_at: 2026-03-01T08:00:00Z
+        valid_from: 2026-03-01T08:00:00Z
```


READ-PROOF bundle-tests-part-2: 726378dc7147ade40bc98aac
