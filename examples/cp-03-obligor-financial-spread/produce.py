"""The CCF call spine — **a STUB. Phase 24.3 step 1; nothing here assembles.**

[MECHANISM] the shape. [ADAPT] nothing yet — there is nothing here to adapt.

**WHY A STUB EXISTS AT ALL, RATHER THAN NOTHING.** This repository has no honest
half-built example state, and that is deliberate rather than an oversight. Two
gates meet here: `test_every_covered_artifact_directory_sits_under_an_example_root`
holds that an `artifacts/` directory beside no `run.py` is not an example, and
`is_pre_build` releases a Gate-1 tree from the spine checks only while it carries
`spec/` and **zero** `.py` files at any depth. Write one module and the tree is
back in scope for all seven canonical regions.

So the two states the repository recognises are *authored specification* and
*built example*, and there is no third. The alternative to this file was
loosening `is_pre_build`, which its own docstring forbids in terms: a tree that
lost its spine would then leave the scan silently and the gate would report green
over the defect it exists to catch. Weakening a gate so an increment fits is the
failure; a stub that is honest about being one is not.

**WHAT THIS FILE IS NOT, AND MUST NOT QUIETLY BECOME.** Bounds set by Dave,
2026-08-30. There is no batch-select here, no store is opened, and no assembly
body exists beyond a raise. Every region below is a NAMED PLACE FOR CODE THAT IS
NOT WRITTEN, and each raises if it is ever reached, so a caller that mistakes
this for the product gets an exception naming the step rather than an empty
payload. **An empty payload is the dangerous failure**: it looks like an answer.

The regions are opened in the canonical order — `boot`, `ingest`, `operators`,
`project`, `gate`, `record`, `serve` — because that is the order the fabric is
called in, and a spine that gates before it projects is not a spine a beginner
can read. Step 3 fills them; it does not renumber them.

**This module is SILENT and stays silent.** Presentation belongs to `run.py`. A
printed line inside a published region is snippet surface an adopter would never
write.
"""

from __future__ import annotations

from typing import Any, NoReturn

from ccf.deployment import BootedFabric
from ccf.graph.protocols import GraphView
from ccf.products.gates import ServableProduct


def _unbuilt(step: str) -> NoReturn:
    """Refuse loudly, naming the step, rather than returning something empty."""
    raise NotImplementedError(
        f"cp-03 {step!r} is not built: Phase 24.3 step 1 ships the artifacts and"
        " this spine's shape only. The census harness is step 2 and the assembly"
        " is step 3 — see .planning/ROADMAP.md Phase 24.3."
    )


# --8<-- [start:boot]
def boot(config_path: str) -> BootedFabric:
    """Read the deployment's configuration and stand the fabric up."""
    _unbuilt("boot")
# --8<-- [end:boot]


# --8<-- [start:ingest]
def ingest(fabric: BootedFabric) -> GraphView:
    """L1/L2 — normalize the estate's rows and admit them through the single writer."""
    _unbuilt("ingest")
# --8<-- [end:ingest]


# --8<-- [start:operators]
def operators(view: GraphView) -> Any:
    """L4 — the operator plan. This product declares exactly ONE: the Policy operator.

    Spec §D.2.1: the attribute batch-select is L2 assembly and is deliberately
    NOT an `Enrich` operator, because `Enrich` does not exist in `src/` and
    forcing it into one of the four canonical categories would be a fake mapping.
    """
    _unbuilt("operators")
# --8<-- [end:operators]


# --8<-- [start:project]
def project(view: GraphView) -> Any:
    """L5 — shape the permitted facts into the declared spread lines."""
    _unbuilt("project")
# --8<-- [end:project]


# --8<-- [start:gate]
def gate(candidate: Any) -> ServableProduct:
    """L6 — the validation gates. A refusal is returned AS DATA, never as a 200."""
    _unbuilt("gate")
# --8<-- [end:gate]


# --8<-- [start:record]
def record(product: ServableProduct) -> Any:
    """The replay record — pinned to exact artifact versions, never to 'latest'."""
    _unbuilt("record")
# --8<-- [end:record]


# --8<-- [start:serve]
def serve(product: ServableProduct) -> Any:
    """Hand back the gated product. Nothing reaches here that has not passed a gate."""
    _unbuilt("serve")
# --8<-- [end:serve]
