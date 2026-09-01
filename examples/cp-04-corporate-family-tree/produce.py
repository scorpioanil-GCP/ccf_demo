"""The CCF call spine — **a STUB. Phase 24.4 wave 3; nothing here assembles.**

[MECHANISM] the shape. [ADAPT] nothing yet — there is nothing here to adapt.

**WHY A STUB EXISTS AT ALL, RATHER THAN NOTHING.** This repository recognises
**two** example states and no third, deliberately. Two gates meet here:

* ``test_every_covered_artifact_directory_sits_under_an_example_root`` holds
  that an ``artifacts/`` directory beside no ``run.py`` is not an example; and
* ``test_spine_separation.py::is_pre_build`` releases a Gate-1 tree from the
  spine checks **only while it carries** ``spec/`` **and ZERO** ``.py`` files at
  any depth. Write one module anywhere and the tree is back in scope for all
  seven canonical regions.

So the two recognised states are *authored specification* and *built example*.
Writing ``artifacts/`` requires a ``run.py`` beside it; writing any ``.py`` puts
the tree back in spine scope. **There is no green half-example**, and the
alternative to this file was loosening ``is_pre_build``, which its own docstring
forbids in terms: a tree that lost its spine would then leave the scan silently
and the gate would report green over the defect it exists to catch.

**Weakening a gate so an increment fits is the failure; a stub that is honest
about being one is not.** Ruled by Dave at rung 03, 2026-08-30, on exactly this
question and in exactly this position — rung 03's wave-1 commit ``4cf3372``
carries the ruling and this file follows it rather than re-deciding it.

**WHAT THIS FILE IS NOT, AND MUST NOT QUIETLY BECOME.** No store is opened, no
walk is taken, no cycle is detected, and no assembly body exists beyond a raise.
Every region below is a NAMED PLACE FOR CODE THAT IS NOT WRITTEN, and each
raises if it is ever reached, so a caller that mistakes this for the product
gets an exception naming the step rather than an empty payload. **An empty
payload is the dangerous failure on this rung in particular**: an empty family
looks like an answer — *this company has no subsidiaries* — which is a claim
about the world rather than about the request.

The regions are opened in the canonical order — ``boot``, ``ingest``,
``operators``, ``project``, ``gate``, ``record``, ``serve`` — because that is
the order the fabric is called in, and a spine that gates before it projects is
not a spine a beginner can read. **Plan ``24.4-07`` fills them; it does not
renumber them, and it replaces this file in full.**

**This module is SILENT and stays silent.** Presentation belongs to ``run.py``.
A printed line inside a published region is snippet surface an adopter would
never write.
"""

from __future__ import annotations

from typing import Any, NoReturn

from ccf.deployment import BootedFabric
from ccf.graph.protocols import GraphView
from ccf.products.gates import ServableProduct


def _unbuilt(step: str) -> NoReturn:
    """Refuse loudly, naming the step, rather than returning something empty."""
    raise NotImplementedError(
        f"cp-04 {step!r} is not built: Phase 24.4 wave 3 ships the Control Plane"
        " documents, the five artifacts and this spine's shape only. The"
        " deployment is plan 24.4-06, the assembly is plan 24.4-07 and the two"
        " callers are plans 24.4-08 and 24.4-09 — see .planning/ROADMAP.md"
        " Phase 24.4."
    )


# --8<-- [start:boot]
def boot(config_path: str) -> BootedFabric:
    """Read the deployment's configuration and stand the fabric up.

    The fabric's own L3 is per-run SQLite. The two SOURCE stores this product
    reads — Fluree for edges and ontology, PostgreSQL for attributes — are
    reached from `backends.yaml`, and neither is opened here.
    """
    _unbuilt("boot")
# --8<-- [end:boot]


# --8<-- [start:ingest]
def ingest(fabric: BootedFabric) -> GraphView:
    """L1/L2 — read the family, normalize it, and admit it through the single writer.

    §D.2 steps 3 and 4. The six declared family predicates are read from the
    graph store and normalized to parent→child edges by the per-predicate
    direction the declaration carries: 1,058 raw triples become 722 distinct
    edges, and the 336-triple collapse is reported rather than hidden.
    """
    _unbuilt("ingest")
# --8<-- [end:ingest]


# --8<-- [start:operators]
def operators(view: GraphView) -> Any:
    """L4 — the operator plan. This product declares TWO, and this is the rung
    where the count moves off one.

    `policy.principal-subgraph` and `traversal.typed-neighborhood`. Six of the
    ten §D steps declare no operator at all, and step 6 declares the Standard's
    `Enrich` against an L2 mechanism — none of the seven enters
    `lineage.operators_invoked`, which is held to strict equality.

    Cycle detection is L2 and declares `operator: null` deliberately
    (§D.2.2, `D-IMPL-223`): registering circuit enumeration under Traversal to
    make a category fit would make the lineage record say something untrue.
    """
    _unbuilt("operators")
# --8<-- [end:operators]


# --8<-- [start:project]
def project(view: GraphView) -> Any:
    """L5 — condition the served shape on FIBO class, not on a role map.

    §D.2.1 role 3. A credit officer's view and a KYC analyst's view of the same
    family differ BY CLASS, which is why the split is a different class
    predicate rather than a different code path.
    """
    _unbuilt("project")
# --8<-- [end:project]


# --8<-- [start:gate]
def gate(candidate: Any) -> ServableProduct:
    """L6 — the validation gates. A refusal is returned AS DATA, never as a 200.

    The SDK's shipped gates run unchanged and no gate is added to the SDK: the
    sixteen `CFT-G` assertions are a DECLARED ARTIFACT plus CI coverage
    (`D-IMPL-224`), with no serve path.
    """
    _unbuilt("gate")
# --8<-- [end:gate]


# --8<-- [start:record]
def record(product: ServableProduct) -> Any:
    """The replay record — pinned to exact artifact versions, never to 'latest'.

    The `ledger_t` the graph leg read at is recorded BESIDE `graph_snapshot_at`
    and never inside it: one is an int and the other a datetime, and they
    describe two different axes (§B.1.1).
    """
    _unbuilt("record")
# --8<-- [end:record]


# --8<-- [start:serve]
def serve(product: ServableProduct) -> Any:
    """Hand back the gated product. Nothing reaches here that has not passed a gate."""
    _unbuilt("serve")
# --8<-- [end:serve]
