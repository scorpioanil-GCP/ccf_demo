"""examples/00-quickstart — "Hello, Context Product" (EXAM-01).

The smallest possible fabric, end to end and in one process: load a deployment
manifest, ingest a handful of events through L1, assemble into the graph, run
the four-category operator chain, project, gate, record the decision, and serve
one typed Context Product — keyless and model-free, on SQLite and the
file-backed ArtifactStore (D-12/D-13).

This file is the **call spine** an adopter would actually write, and nothing
else. It asserts nothing and prints nothing: its assertions live in
``tests/examples/test_quickstart_output.py``, where they are run by ``pytest``
and can fail a build (D-09). ``make example-00`` running clean means the spine
executed.

Every domain value — entity classes, source systems, identifiers, thresholds,
policy versions, MAX_TTL, the query, the boundary — is loaded from
``artifacts/*.yaml`` and enumerated by ``artifacts/manifest.yaml``. Deleting
the artifacts leaves this file with nothing meaningful to run (CLAUDE.md §6.4,
the No-Hardcoding Rule).

Run it: ``make example-00`` (or
``PYTHONPATH=src:runtime python examples/00-quickstart/run.py``).
"""

from __future__ import annotations

import sys
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import cast

from ccf.artifacts.file_store import FileArtifactStore
from ccf.contracts.base import CCFContract
from ccf.controlplane.artifacts import (
    DebtProfile,
    DeclaredArtifact,
    HalfLifeTable,
    OperatorParametersArtifact,
    PerspectiveArtifact,
    ProductClassDeclaration,
    ProjectionRequirements,
    SignalBatch,
)
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment import (
    build_operator_registry,
    load_and_boot,
    refuse_operator_set_divergence,
)
from ccf.graph.protocols import GraphView
from ccf.halflife.decay import Observation, freshness
from ccf.operators.base import OperatorOutput
from ccf.products.contract import (
    ContextProductContract,
    MaxTTL,
    ProductLineage,
    register_product_class,
)
from ccf.products.gates import ServableProduct, run_gates
from ccf.projection.plan import Perspective, ProjectionOutput
from ccf.projection.engine import ProjectionEngine
from ccf.replay.record import DecisionReplayRecord, PolicyBinding, build_replay_record
from ccf.replay.serve import ReplayWriter, ServedProduct, serve

MANIFEST = Path(__file__).resolve().parent / "artifacts" / "manifest.yaml"


class QuickstartPlan:
    """The deployment's Π: what the reconciled subgraph means to its reader.

    A projection is deployment code — this is what a user writes, and it is
    never a rewrite target (whitepaper §7.5). It declares which operators its
    interpretation depends on and interprets their output; it does not run them
    and cannot tell the engine what ran, which is what leaves the L6 lineage
    gate something real to check.

    ``required`` is passed in from ``artifacts/projection-requirements.yaml``
    — this projection's OWN authored operator set — and is never read off the
    operator registry, which would make the plan's requirements a restatement
    of whatever happens to be registered.

    The product class's ``required_operator_keys`` is a different statement
    about a different thing: the CLAIM the product carries into
    ``lineage.operators_invoked``. Two documents, one per side, held together
    by the operator-set binder in :mod:`ccf.deployment`, which ``run`` below
    calls between constructing this plan and executing it — so a disagreement
    between the two is a refusal rather than an identity nobody can see
    (design E2, D-IMPL-86).
    """

    def __init__(self, *, plan_id: str, required: tuple[str, ...]) -> None:
        self._plan_id = plan_id
        self._required = required

    @property
    def plan_id(self) -> str:
        return self._plan_id

    def required_operators(self) -> tuple[str, ...]:
        return self._required

    def invoke(
        self,
        *,
        view: GraphView,
        operator_outputs: Mapping[str, OperatorOutput],
        perspective: Perspective,
        temporal_boundary: datetime,
    ) -> ProjectionOutput:
        return ProjectionOutput(
            plan_id=self._plan_id,
            payload={
                "role": perspective.role,
                "entity_count": len(view.entities),
                "entities": [
                    {
                        "entity_uri": record.claim.entity_uri,
                        "entity_class": record.claim.entity_class,
                    }
                    for record in view.entities
                ],
                "relationship_types": sorted(
                    {edge.claim.relationship_type for edge in view.relationships}
                ),
            },
        )


@dataclass(frozen=True)
class QuickstartResult:
    """What one run of the spine produced, for a caller to inspect.

    The example returns its state rather than checking it here, so that
    ``tests/examples/test_quickstart_output.py`` can hold the assertions where
    a test runner will actually run them.
    """

    tenant_id: str
    artifacts: Mapping[str, CCFContract]
    product: ContextProductContract
    operators_invoked: tuple[str, ...]
    record: DecisionReplayRecord
    served: ServedProduct
    store: FileArtifactStore
    retained_freshness: Decimal


def run(*, root: Path) -> QuickstartResult:
    """Run the fabric once against ``root`` as its scratch directory."""
    registry = ControlPlaneRegistry()

    # --8<-- [start:boot]
    # 1. One call replaces the registration prologue and the boot: the manifest
    #    names every artifact in force, `load_and_boot` parses all of them,
    #    registers the `role: register` ones, and boots on the resulting pins.
    booted = load_and_boot(
        MANIFEST,
        registry=registry,
        connection={"database_path": str(root / "quickstart.sqlite3")},
    )
    # --8<-- [end:boot]
    try:
        # Each artifact comes back under its own manifest key, already
        # validated against the class the manifest declared for it — so these
        # casts restate what `load_and_boot` already enforced. A wrong
        # `class_id` in the manifest fails at parse, before this line runs.
        events = cast(SignalBatch, booted.artifacts["events"])
        decision = cast(DeclaredArtifact, booted.artifacts["decision"])
        governance = cast(DeclaredArtifact, booted.artifacts["product-governance"])
        declared = cast(ProductClassDeclaration, booted.artifacts["product-class"])
        # The projection's own operator set, authored separately from the claim
        # `declared` carries. Design E2 keeps these two documents apart on
        # purpose; the binder below is what keeps them in agreement.
        requirements = cast(
            ProjectionRequirements, booted.artifacts["projection-requirements"]
        )
        perspective = cast(PerspectiveArtifact, booted.artifacts["perspective"])

        boundary = datetime.fromisoformat(decision.declaration["temporal_boundary"])
        now = datetime.fromisoformat(decision.declaration["now"])

        # --8<-- [start:ingest]
        # 2. Ingest from the batch the manifest declared `role: load`. It came
        #    back parsed on `booted.artifacts`, so this is one line — no
        #    re-read, no second loader.
        for envelope in events.envelopes:
            booted.handle.worker.ingest(envelope)
        # --8<-- [end:ingest]

        # --8<-- [start:operators]
        # 3. The graph view at the temporal boundary this deployment named.
        #    Which boundary a deployment reads its corpus at is a deployment
        #    decision, so it stays an explicit line here.
        view = booted.handle.reader.as_of(tenant_id=booted.tenant_id, at=boundary)

        # 4. The operator-parameters mapping, assembled by naming this
        #    deployment's OWN manifest keys. Deliberately not an isinstance
        #    filter or a class-id match: those are type introspection, and
        #    copied across nine examples they would be a new duplication class.
        #    These four strings are configuration an adopter reads and edits.
        parameters: Mapping[str, OperatorParametersArtifact] = {
            key: cast(OperatorParametersArtifact, booted.artifacts[key])
            for key in ("traversal", "temporal", "policy", "similarity")
        }

        # 5. The four-category operator chain (L4), from those artifacts.
        operators = build_operator_registry(
            parameters=parameters,
            view=view,
            pins=booted.pins,
            policy_bundle_key="policy-bundle",
            similarity_index_version=governance.declaration[
                "similarity_index_version"
            ],
        )
        # --8<-- [end:operators]

        # --8<-- [start:project]
        # 6. Project (L5). The plan's `required` comes from the projection's own
        #    `projection-requirements.yaml` — never from the operator registry's
        #    keys. The product class's `required_operator_keys` is the separate
        #    document, and the binder call between the two lines below is where a
        #    disagreement between them fails: before anything is assembled, by
        #    refusal rather than repair (design E2, D-IMPL-86).
        #
        #    The plan is a named local rather than an argument expression for
        #    exactly that reason — the binder has to be handed the same object
        #    the engine will run.
        plan = QuickstartPlan(
            plan_id=requirements.plan_id,
            required=requirements.required_operator_keys,
        )
        refuse_operator_set_divergence(declared=declared, plan=plan)
        execution = ProjectionEngine(
            reader=booted.handle.reader, registry=operators
        ).execute(
            plan=plan,
            perspective=perspective,
            tenant_id=booted.tenant_id,
            temporal_boundary=boundary,
        )
        # --8<-- [end:project]

        # --8<-- [start:gate]
        # 7. L6 — and this cluster stays in adopter code deliberately.
        #
        #    Gate 3 compares the class's TTL CEILING against this product's own
        #    `expires_at`. That is only a check while the two are independently
        #    authored. Registering the MaxTTL value here is what MINTS
        #    `max_ttl_version` — the pin is a content hash of what was
        #    registered, which is why the product-class artifact cannot declare
        #    it (the same shape D-IMPL-76 ruled for the policy bundle's
        #    admitted-version set). A helper that minted the pin and stamped the
        #    product would be comparing a value against itself, so the SDK
        #    ships no such helper and these lines survive the ergonomics phase
        #    on purpose. Do not remove them.
        max_ttl_version = registry.register(
            declared.max_ttl_key,
            MaxTTL(seconds=governance.declaration["max_ttl_seconds"]),
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

        # 8. The lineage the product CLAIMS, and the gates.
        #
        #    `operators_invoked` is filled from the product-class DECLARATION —
        #    the Control Plane's statement of what this product was computed by
        #    — and never from `execution`. That is design E2's first element
        #    (D-IMPL-86): a claim copied out of the execution record is not a
        #    claim, it is a transcript.
        #
        #    `engine_resolved` stays the engine's own value, and what Gate 2
        #    then verifies is ASSEMBLY-PATH INTEGRITY: the claim transcribed
        #    into this Contract equals the engine's execution of the plan. Be
        #    precise about what that is and is not. The engine is a faithful
        #    TRANSCRIBER of the plan rather than an independent witness of it —
        #    it builds `operators_invoked` and `steps` in one loop over the same
        #    operator plan, so there is no return path where invoked ≠ planned.
        #    Gate 2 therefore does not catch a producer misdeclaring. Authorable
        #    drift fails upstream instead, at the binder call in step 6.
        policy_version = booted.pins.version_for("policy-bundle")
        candidate = ContextProductContract(
            schema_name=product_class.schema_name,
            schema_version=product_class.schema_version,
            plan_id=execution.plan_id,
            tenant_id=booted.tenant_id,
            temporal_boundary=boundary,
            expires_at=now
            + timedelta(seconds=governance.declaration["product_ttl_seconds"]),
            ttl_anchor=product_class.ttl_anchor,
            lineage=ProductLineage(
                operators_invoked=frozenset(declared.required_operator_keys),
                policy_bundle_versions=frozenset({policy_version}),
                graph_snapshot_at=boundary,
            ),
            payload=execution.projection.payload,
        )
        # A refusal is not a thing to proceed past: `ServableProduct` is not
        # constructible outside `run_gates`, so holding one IS the evidence the
        # gates ran (INV-CH7-52).
        match run_gates(
            candidate,
            engine_resolved=execution.operators_invoked,
            now=now,
            registry=registry,
            product_class=product_class,
        ):
            case ServableProduct() as gated:
                pass
            case refusal:
                raise RuntimeError(
                    f"the three validation gates refused this product: {refusal}"
                )
        # --8<-- [end:gate]

        # --8<-- [start:record]
        # Replay before delivery. `policy_bindings` is built here, from the
        # pins the adopter reads off `BootedFabric.pins`: D-06 keeps the
        # SELECTION of which bindings are in force in adopter hands, because
        # dimension 2 assembled by a rule nobody in the deployment wrote down
        # is not an audit record.
        record = build_replay_record(
            execution=execution,
            product=gated.product,
            perspective=perspective,
            policy_bindings=(
                PolicyBinding(key="policy-bundle", version=policy_version),
            ),
            assembly_mode=declared.assembly_mode,
            recorded_at=now,
        )
        # --8<-- [end:record]

        # --8<-- [start:serve]
        store = FileArtifactStore(root=root / "artifacts")
        served = serve(
            product=gated,
            record=record,
            replay_writer=ReplayWriter(
                store=store,
                artifact_class=governance.declaration["replay_record_class"],
            ),
        )
        # --8<-- [end:serve]

        # λ_c: the retained decision-relevance of a declared observation at the
        # decision instant (whitepaper §7.7).
        table = cast(HalfLifeTable, booted.artifacts["half-life-table"])
        profile = cast(DebtProfile, booted.artifacts["debt-profile"])
        retained = freshness(
            Observation.model_validate(
                decision.declaration["freshness_demonstration"]
            ),
            now=now,
            table=table,
            risk_sensitivity=profile.risk_sensitivity,
        )

        # The ENGINE's transcription of the plan, carried out beside the served
        # product. It is deliberately not the same value as
        # `product.lineage.operators_invoked` any more: that is the product's
        # claim, from the product-class declaration. Returning both is what lets
        # `tests/examples/test_quickstart_output.py` compare two things.
        engine_transcription = execution.operators_invoked

        return QuickstartResult(
            tenant_id=booted.tenant_id,
            artifacts=booted.artifacts,
            product=gated.product,
            operators_invoked=engine_transcription,
            record=record,
            served=served,
            store=store,
            retained_freshness=retained,
        )
    finally:
        booted.handle.close()


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="ccf-quickstart-") as scratch:
        run(root=Path(scratch))
    return 0


if __name__ == "__main__":
    sys.exit(main())
