"""The refusal that binds two separately authored operator sets (design E2).

SDK-defined mechanism. The ruling of record is ``docs/DECISIONS.md``
**D-IMPL-86** (Dave, 2026-08-05), element (3), **as corrected by the appended
`D-IMPL-86 (correction, 2026-08-05)` entry**. CLAUDE.md §11 requires an SDK
extension to cite this project's own decision record rather than the whitepaper,
and the whitepaper genuinely under-determines the question: §7.5 is silent on
the *provenance* of a projection's operator set and affirmatively blesses
data-holder plans.

What this module binds
----------------------

Two documents, one comparison:

* :attr:`~ccf.controlplane.artifacts.ProductClassDeclaration.required_operator_keys`
  — the Control Plane **claim**, the value that fills the product's declared
  lineage and never its execution record; and
* :meth:`~ccf.projection.plan.ProjectionPlan.required_operators` — what the
  plan itself requires, which under design E2 comes from the separately
  authored :class:`~ccf.controlplane.artifacts.ProjectionRequirements`
  artifact (``ccf.projection-requirements``).

Why the comparison has to exist
-------------------------------

Without it the two documents are kept in sync by hand with no mechanism binding
them, and that was the standing objection to introducing a second artifact at
all. The refusal is the mechanism, and it is the reason E2 is a design rather
than a filing convention: a one-key edit to *either* document now produces a
failure, so drift is reachable by editing an artifact instead of only by
writing a bug.

What this is **not**: it is not Gate 2
--------------------------------------

Gate 2 is lineage strict equality (whitepaper §7.6, INV-CH7-47). It compares
the claim *after* it has been transcribed into the Context Product Contract
against the operator set the projection engine reports from executing the plan.
The engine is a faithful transcriber of the plan rather than an independent
witness of it — it builds its invoked set and its steps in one loop over the
same operator plan — so what Gate 2 actually verifies is **assembly-path
integrity**: that the product served was assembled by the path the deployment
claimed, not that the claim was right in the first place.

This binder sits **upstream** of that, over two authored documents, and is
where **authorable drift** fails. The two descriptions must not blur; blurring
them is what produced CR-2, the defect this phase exists to close.

What this module deliberately does not offer
--------------------------------------------

Stated in the negative, so the line is legible from the surface rather than
only from the guard — the shape :mod:`ccf.deployment.manifest` already uses:

* :func:`refuse_operator_set_divergence` returns ``None``. It does **not**
  return the declared operator set, and there is no variant of it that does.
  A binder that handed the set back would put the SDK in the position of
  supplying one of Gate 2's two arguments, which is exactly the D-15A line the
  ``cinv02-deployment-gates`` lint rule holds and the collapse this phase
  exists to close. The value a caller wants is already in the caller's hand:
  it authored both documents.
* Nothing here executes a validation gate, constructs a product's lineage
  record, or accepts a projection execution result. Gate execution stays in
  adopter code.

Two residuals, both named rather than softened
----------------------------------------------

**1. The authorship residual**, in D-IMPL-86's own "Consequences accepted"
words: a deployment that reads one artifact into the other still collapses this
check, so dual authorship remains convention-assisted **at the authoring
boundary** even though the check itself is structural. No AST gate can
distinguish an authored literal from a transcribed one — under the rejected
design the compliant state and the violating state are textually identical, so
the shortcut is undetectable in principle rather than merely unhandled.

**2. The placement residual**, named by `D-IMPL-86 (correction, 2026-08-05)` —
cite **that entry**, never element (3) as originally written, which called this
a binder that runs at boot and was withdrawn. Four parts, each stated because a
docstring that named one residual and not the other would be a fresh instance
of the very defect this phase closes:

* **Where the call must sit.** Between plan construction and
  :meth:`~ccf.projection.engine.ProjectionEngine.execute`, in adopter code.
  :func:`~ccf.deployment.manifest.load_and_boot` cannot host it: its signature
  (``src/ccf/deployment/manifest.py:177`` as the correction cites it; the
  signature spans lines 181-188 in the tree as it now stands) takes no ``plan``
  parameter and has no :class:`~ccf.projection.plan.ProjectionPlan` in scope at
  any of its preflights. A plan is adopter code constructed *after* that call
  returns.
* **The function returns ``None``.** There is therefore no return value a
  caller must consume, and nothing observable at runtime — no product field, no
  pin, no audit event — that proves the call was ever made. A deployment that
  omits it produces output identical to one that made it.
* **Nothing outside this project's own ``examples/`` tree holds a deployment to
  calling it at all.** An adopter who omits the call gets no error, no warning,
  and no degraded output.
* **The AST coverage check that enforces the call —
  ``tests/products/test_gate_two_call_shape.py``, added in plan 15.1-08 — is
  scoped to ``examples/`` only.** It is a check on this project's own teaching
  material, not on adopters, and is not claimed as more.

This is a second convention-not-enforcement residual of the same family as the
first. It is **carried to Phase 16** rather than closed here, and it is surfaced
at Phase 15.1's gate for Dave to rule on — open debt, not a closed question.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from ccf.controlplane.artifacts import ProductClassDeclaration
from ccf.projection.plan import ProjectionPlan

__ccf_mode__ = "algorithmic"

__all__ = ["refuse_operator_set_divergence"]


def refuse_operator_set_divergence(
    *, declared: ProductClassDeclaration, plan: ProjectionPlan
) -> None:
    """Raise if the product class's claim and the plan's requirements disagree.

    Design E2's binder (D-IMPL-86, and its correction of 2026-08-05 for where
    the call belongs). Call it **between constructing the plan and calling**
    :meth:`~ccf.projection.engine.ProjectionEngine.execute` — after that, a
    product has already been assembled from a set the deployment's own claim
    contradicts.

    Order is not significant on either side: both are compared as sets, because
    the engine imposes the dependency order (INV-CH7-28) and neither document's
    author chooses it.

    Args:
        declared: The product class's authored governance. Its
            ``required_operator_keys`` is the Control Plane claim.
        plan: The constructed projection plan, whose ``required_operators()``
            under design E2 comes from the ``ccf.projection-requirements``
            artifact.

    Returns:
        ``None``, always — and see the module docstring for why there is no
        variant that returns the set instead.

    Raises:
        ValueError: the two sets differ. **Refused, never repaired**: the binder
            does not choose which document is right, because only the
            deployment's author knows which of the two they meant. Silently
            preferring one would leave a deployment whose declared operator set
            depends on which document the SDK happened to trust — the same
            refuse-to-infer posture :func:`~ccf.deployment.manifest.load_and_boot`
            takes on the tenant and the backend.
    """
    claimed = frozenset(declared.required_operator_keys)
    required = frozenset(plan.required_operators())
    if claimed == required:
        return
    raise ValueError(
        f"operator set divergence for plan {plan.plan_id!r}: the product class"
        f" claims {sorted(claimed)} and the plan requires {sorted(required)},"
        f" differing on {sorted(claimed ^ required)}; one of the two authored"
        " documents is wrong and only its author knows which (D-IMPL-86)"
    )
