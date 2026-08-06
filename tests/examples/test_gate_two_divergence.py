"""Gate 2 refuses a diverging declared side at example scale — and admits agreement.

Whitepaper §7.6 / INV-CH7-47 (lineage strict equality); design E2, D-IMPL-86.

What Gate 2 establishes, stated exactly
----------------------------------------

Gate 2 verifies **assembly-path integrity**: the claim transcribed into the
Context Product Contract equals the projection engine's execution of the plan.
That is the whole of it, and the precision matters because the imprecise version
is what CR-2 falsified.

It does **not** detect producer misdeclaration. The engine is a *faithful
transcriber of the plan*, not an independent witness of it: it builds
``operators_invoked`` and ``steps`` in one loop over the same operator plan
(``ccf/projection/engine.py``), so no return path exists where invoked ≠
planned. A producer who declares an operator set the deployment never meant is
not caught here, and this module does not claim otherwise. D-IMPL-86 records
that finding as established and undisputed by any reviewer in the round that
produced design E2.

**The check that catches authorable drift is the binder**, upstream of this one:
:func:`ccf.deployment.refuse_operator_set_divergence`, exercised by
``tests/deployment/test_binder.py``. It compares the product class's
``required_operator_keys`` against the projection's own
``required_operator_keys`` — two separately authored Control Plane documents —
and it is a refusal **placed between plan construction and
``ProjectionEngine.execute``** (D-IMPL-86 correction, 2026-08-05, which
withdrew element (3)'s original placement wording as impossible: ``load_and_boot``
takes no plan and has none in scope at any preflight). Editing either document
by one key produces a refusal there, before anything is assembled. That is
where a deployment's authorable drift fails; this module is downstream of it and
narrower.

Do not let this module drift into claiming the stronger property. Blurring the
two descriptions is precisely what produced the comment CR-2 falsified.

What is perturbed, and why that side
-------------------------------------

The **declared** side — the product's ``lineage.operators_invoked`` — because
that is the side design E2 changed and the side an artifact edit moves.
``tests/products/test_gate_independence.py:179`` already perturbs the other one
at unit scale; perturbing ``engine_resolved`` again here would re-prove a
property that module owns and would say nothing about the deployment.

Both halves, and the docstring says why: a gate that always refuses passes the
divergence assertion, a gate that always admits passes the agreement assertion,
and only the pair says the comparison is live.

Why a deliberately divergent construction is writable here
-----------------------------------------------------------

``tests/products/test_gate_two_call_shape.py`` is the standing tripwire against
filling both of Gate 2's arguments from one source, and its ``SCANNED_TREES``
excludes ``tests`` for exactly this reason: a test may legitimately build a
construction the tripwire would refuse in order to prove a gate fires. This
module is one of the places that happens.

Everything the deployment says is read from the deployment
-----------------------------------------------------------

The claim, the engine's resolution, the decision instant, the MAX_TTL ceiling
and the product class are all reached through the example's own returned result
object and its own parsed artifacts — the exposure ERGO-16 relocated the example
assertions onto. The No-Hardcoding Rule reaches ``tests/`` (D-IMPL-78), so the
key that perturbs the claim is **derived from the deployment's own authored
keys** rather than written here: one of its keys plus a marker suffix that is
test vocabulary and could not name an operator any deployment registered.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pytest

from ccf.controlplane.artifacts import DeclaredArtifact, ProductClassDeclaration
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.products.contract import (
    ContextProductContract,
    MaxTTL,
    ProductLineage,
    RegisteredProductClass,
    register_product_class,
)
from ccf.products.gates import LineageMismatchRefusal, ServableProduct, run_gates

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO_ROOT / "examples" / "00-quickstart" / "run.py"

#: Test-side vocabulary, never a deployment value. Appended to one of the
#: deployment's OWN authored operator keys, so the perturbation is derived from
#: the example rather than authored here — D-IMPL-78 put ``tests/`` inside
#: CINV-01's scope, and an operator key invented in this module would be a
#: domain value in a test file whichever way it was spelled.
NEVER_RAN_SUFFIX = "+this-operator-never-ran"

#: Manifest keys, which are the deployment's own vocabulary for its documents.
PRODUCT_CLASS_KEY = "product-class"
GOVERNANCE_KEY = "product-governance"
DECISION_KEY = "decision"


def _load_example() -> Any:
    """Load the example module by file path (the example dir is no package).

    Registered in ``sys.modules`` before execution, for the reason
    ``test_quickstart_output.py`` records: the example uses
    ``from __future__ import annotations``, so ``@dataclass`` resolves its field
    annotations by looking its own module up there. Its own module name, so this
    module's run does not collide with that one's.
    """
    name = "quickstart_under_gate_two_divergence"
    spec = importlib.util.spec_from_file_location(name, EXAMPLE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@dataclass(frozen=True)
class _Deployment:
    """One run of the example, reduced to what Gate 2 takes as input.

    Every field is read off the example's returned result or its parsed
    artifacts. Nothing here is re-derived from a second read of a file, which
    could drift from what the deployment actually ran against.
    """

    product: ContextProductContract
    claimed: frozenset[str]
    resolved: frozenset[str]
    now: datetime
    registry: ControlPlaneRegistry
    product_class: RegisteredProductClass


def _declaration(result: Any, key: str) -> Any:
    artifact = result.artifacts[key]
    assert isinstance(artifact, DeclaredArtifact), key
    return artifact.declaration


@pytest.fixture(scope="module")
def deployment(tmp_path_factory: pytest.TempPathFactory) -> _Deployment:
    """The quickstart, run once, with its product class re-registered here.

    ``run_gates`` needs a :class:`RegisteredProductClass` and the Control Plane
    the MAX_TTL was pinned in (D-IMPL-39), and the example returns neither — it
    returns the *product*. So the registration is repeated here from the
    example's own two documents, exactly as ``run.py`` performs it. That is not
    a second source of truth: both readings are of the same parsed artifacts the
    fabric booted on, handed back on ``BootedFabric.artifacts``.
    """
    root = tmp_path_factory.mktemp("gate-two-divergence")
    result = _load_example().run(root=root)

    declared = result.artifacts[PRODUCT_CLASS_KEY]
    assert isinstance(declared, ProductClassDeclaration)
    governance = _declaration(result, GOVERNANCE_KEY)
    decision = _declaration(result, DECISION_KEY)

    registry = ControlPlaneRegistry()
    max_ttl_version = registry.register(
        declared.max_ttl_key, MaxTTL(seconds=governance["max_ttl_seconds"])
    )
    product_class = register_product_class(
        registry=registry,
        schema_name=declared.schema_name,
        schema_version=declared.schema_version,
        ttl_anchor=declared.ttl_anchor,
        assembly_mode=declared.assembly_mode,
        max_ttl_key=declared.max_ttl_key,
        max_ttl_version=max_ttl_version,
    )
    return _Deployment(
        product=result.product,
        claimed=frozenset(declared.required_operator_keys),
        resolved=frozenset(result.operators_invoked),
        # The deployment's own decision instant, so Gate 3 (TTL bounds) behaves
        # here exactly as it did in the run rather than under a clock this
        # module chose.
        now=datetime.fromisoformat(decision["now"]),
        registry=registry,
        product_class=product_class,
    )


def _undeclared_key(claimed: frozenset[str]) -> str:
    """An operator key the deployment never declared, derived from one it did."""
    key = sorted(claimed)[0] + NEVER_RAN_SUFFIX
    assert key not in claimed, key
    return key


def _candidate(
    product: ContextProductContract, operators: frozenset[str]
) -> ContextProductContract:
    """The served product with one field replaced: what its lineage claims.

    Rebuilt through the contract's own constructor rather than copied around it,
    so the perturbed candidate is validated at the boundary like any other
    (``extra=forbid``, CLAUDE.md §11) instead of being a model the type system
    never saw.
    """
    return ContextProductContract(
        schema_name=product.schema_name,
        schema_version=product.schema_version,
        plan_id=product.plan_id,
        tenant_id=product.tenant_id,
        temporal_boundary=product.temporal_boundary,
        expires_at=product.expires_at,
        ttl_anchor=product.ttl_anchor,
        lineage=ProductLineage(
            operators_invoked=operators,
            policy_bundle_versions=product.lineage.policy_bundle_versions,
            graph_snapshot_at=product.lineage.graph_snapshot_at,
        ),
        payload=product.payload,
    )


def test_a_claim_carrying_an_operator_that_did_not_run_is_refused(
    deployment: _Deployment,
) -> None:
    """The declared side perturbed by one key, at the scale a deployment runs at.

    The refusal is asserted on **both** of its sides separately, so the test
    says which was which: ``declared`` carries the extra key and ``resolved``
    does not. A single assertion on the refusal *type* would pass just as well
    if the two fields had been swapped, and a reader debugging a real refusal
    reads exactly these two fields.
    """
    never_ran = _undeclared_key(deployment.claimed)
    forged = deployment.claimed | {never_ran}

    refusal = run_gates(
        _candidate(deployment.product, forged),
        engine_resolved=deployment.resolved,
        now=deployment.now,
        registry=deployment.registry,
        product_class=deployment.product_class,
    )

    assert isinstance(refusal, LineageMismatchRefusal), refusal
    assert refusal.declared == forged
    assert never_ran in refusal.declared
    assert refusal.resolved == deployment.resolved
    assert never_ran not in refusal.resolved


def test_the_unperturbed_claim_is_admitted(deployment: _Deployment) -> None:
    """The other half. Without it, a gate that refused everything would pass.

    The precondition asserted first is the deployment's own state and is what
    makes this half reachable at all: the product class's claim and the engine's
    resolution agree, because the binder holds the claim and the projection's
    requirements equal and the engine transcribes the plan it was given.
    """
    assert deployment.claimed == deployment.resolved

    admitted = run_gates(
        _candidate(deployment.product, deployment.claimed),
        engine_resolved=deployment.resolved,
        now=deployment.now,
        registry=deployment.registry,
        product_class=deployment.product_class,
    )

    assert isinstance(admitted, ServableProduct), admitted
    assert admitted.product.lineage.operators_invoked == deployment.resolved
