"""The refusals that bind two separately authored documents at wiring time.

SDK-defined mechanism. The ruling of record for
:func:`refuse_operator_set_divergence` is ``docs/DECISIONS.md`` **D-IMPL-86**
(Dave, 2026-08-05), element (3), **as corrected by the appended `D-IMPL-86
(correction, 2026-08-05)` entry**; for
:func:`refuse_unpromisable_freshness_sla` it is **D-IMPL-31** (Dave,
2026-07-25). CLAUDE.md §11 requires an SDK extension to cite this project's own
decision record rather than the whitepaper, and the whitepaper genuinely
under-determines the first question: §7.5 is silent on the *provenance* of a
projection's operator set and affirmatively blesses data-holder plans.

**Two refusals, one posture.** Each compares two separately authored documents
that can disagree, and each refuses rather than repairing, because only the
deployment's author knows which of the two they meant. They are otherwise
independent: the first is about operator sets, the second about freshness
promises, and neither is a generalization of the other.

What this module binds — 1: the operator sets
---------------------------------------------

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

What this module binds — 2: the freshness promises
--------------------------------------------------

A product class assembled from constituent classes declares its own
:class:`~ccf.products.contract.FreshnessSLA` — the currency bound its
constituent signals have to meet before the product may be treated as sound at
the moment a decision is taken (whitepaper §6.3,
``docs/CCF_Whitepaper_1-2.md:1453``). Its constituents declare theirs.
The two are authored independently and can disagree, and when they do the
composite has promised a currency it cannot keep.

**This is the most valuable of criterion 8's three limbs, and the reason is
worth stating rather than leaving to a reader.** It turns freshness from a
runtime surprise into a **structural refusal**. If a class declares a
twenty-four-hour expectation for a signal but a constituent can only offer
thirty days on that same signal, the composite cannot honour its own
declaration — and that is checkable at class registration, **before any product
of that class exists**, rather than discovered by an agent consuming a product
that quietly missed its SLA.

The companion at assembly time is :mod:`ccf.products.composition`: this refusal
holds the *declarations* to each other, and ``compose_expiry`` /
``refuse_mixing`` hold the *instance* to its constituents' actual validity.
Neither subsumes the other — a deployment can honour every floor at assembly
and still have declared a promise no constituent class ever offered.

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
* :func:`refuse_unpromisable_freshness_sla` returns ``None`` on the same terms.
  It does **not** return a reconciled SLA, a weakest-promise envelope, or the
  breaching constituent's offer as a value to adopt. Handing back a computed
  promise would be the SDK authoring one of the two documents it exists to
  compare.
* Nothing here executes a validation gate, constructs a product's lineage
  record, or accepts a projection execution result. Gate execution stays in
  adopter code. This module imports nothing from :mod:`ccf.products.gates`,
  which the no-allowlist ``cinv02-deployment-gates`` rule enforces; the
  freshness comparison reads
  :class:`~ccf.controlplane.artifacts.ProductClassDeclaration` only, which is
  the artifact side of the fabric and not the gate side.

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
  takes no ``plan`` parameter and has no
  :class:`~ccf.projection.plan.ProjectionPlan` in scope at any of its
  preflights. A plan is adopter code constructed *after* that call returns.
  (The correction cites that signature as
  ``src/ccf/deployment/manifest.py:177``, which is where it stood in the tree
  the correction was written against; the definition has moved since. The
  durable reference is the symbol, not the line.)
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

from collections.abc import Sequence

from ccf.controlplane.artifacts import ProductClassDeclaration
from ccf.projection.plan import ProjectionPlan

__ccf_mode__ = "algorithmic"

__all__ = [
    "refuse_operator_set_divergence",
    "refuse_unpromisable_freshness_sla",
]


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


def refuse_unpromisable_freshness_sla(
    *,
    declared: ProductClassDeclaration,
    constituents: Sequence[ProductClassDeclaration],
) -> None:
    """Raise if a class promises a currency its constituents cannot offer.

    D-IMPL-31's discipline applied to the *declarations* rather than to an
    assembled instance: a composite must not be labelled fresher than what it
    is composed from, and the declarations say so long before any product
    exists. Call it at class registration, or wherever the deployment first
    holds the composite's declaration and its constituents' together.

    Comparison, stated exactly. For every signal type the composite declares an
    expectation for, a constituent that declares a **larger** ``max_age`` for
    that same signal is offering a staler signal than the composite promised,
    and the composite therefore cannot honour its own declaration. The
    comparison is per signal type, because
    :class:`~ccf.products.contract.FreshnessSLA` is per signal type by ruling
    (D-IMPL-106) — a scalar comparison would be exactly the asymmetry §6.3 says
    a product must not hide.

    **Silence on a signal is not a weak promise.**
    :data:`~ccf.products.contract.UNMEASURED_FRESHNESS_SLA` is the positive
    assertion *this class's freshness is bounded by its TTL alone and it
    measures no signal separately*, so a constituent that declares nothing for
    a signal is not compared on it. Reading silence as an unbounded offer would
    refuse every class registered before D-IMPL-106 existed, which is a claim
    about their authors' intent that nobody made. The residual is named rather
    than closed: a constituent that measures nothing cannot be *held* to
    anything here either, and only a declaration can fix that.

    One refusal, deterministically chosen: signal types are examined in sorted
    order and constituents in the caller's own order, so the same two documents
    always produce the same message.

    Args:
        declared: The composite class's authored governance. Its
            ``freshness_sla`` is the promise under test.
        constituents: The authored declarations of the classes it is composed
            from, in the deployment's own order.

    Returns:
        ``None``, always — and see the module docstring for why there is no
        variant that returns a reconciled promise instead.

    Raises:
        ValueError: a constituent cannot offer what the composite promised. The
            message names all three facts — the composite's promise, the
            constituent that cannot meet it, and what that constituent offers —
            so the caller re-derives none of them. **Refused, never repaired**,
            on :func:`refuse_operator_set_divergence`'s posture: the binder does
            not choose which of the two authored documents is right, because
            silently preferring one would leave a deployment whose declared
            freshness depends on which document the SDK happened to trust.
    """
    promised = declared.freshness_sla.max_age_seconds_by_signal
    for signal in sorted(promised):
        promise = promised[signal]
        for constituent in constituents:
            offer = constituent.freshness_sla.max_age_seconds_by_signal.get(
                signal
            )
            if offer is None or offer <= promise:
                continue
            raise ValueError(
                f"unpromisable freshness SLA for product class"
                f" {declared.schema_name!r}: it promises signal {signal!r} no"
                f" older than {promise}s, but its constituent class"
                f" {constituent.schema_name!r} offers only {offer}s on that"
                " signal, so the composite cannot honour its own declaration;"
                " one of the two authored documents is wrong and only its"
                " author knows which (D-IMPL-31)"
            )
    return
