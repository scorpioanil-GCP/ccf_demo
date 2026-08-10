"""[ADAPT] This file is yours. The fabric does not care what is in it.

[MECHANISM] nothing. Not one line here is a call CCF requires you to make —
those are all in ``spine.py`` beside this file, wrapped in seven named marker
regions, and there are no others. What lives here is the three things a
deployment has to supply and the SDK deliberately declines to own:

1. **The projection Π** (:class:`UltimateBeneficialOwnershipPlan`) — what the
   reconciled subgraph *means* to its reader. A projection is deployment code
   and is never a rewrite target (whitepaper §7.5).
2. **The artifact-key vocabulary** — the short names this deployment registered
   its documents under in ``artifacts/manifest.yaml``. They appear as literals
   in :meth:`KycDeployment.read` because they are this deployment's own words:
   configuration an adopter reads and edits, not type introspection.
3. **Scenario setup** — turning the run's parsed artifacts into the values the
   fabric asks for.

**It still holds no domain values.** Every entity class, every attribute name,
every reference, the ownership threshold and the number of decimal places the
answer is reported to are read from ``artifacts/*.yaml`` (CLAUDE.md §6.4, the
No-Hardcoding Rule). Delete ``artifacts/`` and this file has nothing to compute:
the projection is an interpreter of ``ubo-question.yaml`` and
``policy-bundle.yaml``, and the scenario reader is an interpreter of
``manifest.yaml``.

**It imports nothing from ``spine.py``, and ``spine.py`` imports nothing from
it.** The two are held together structurally — ``spine.Scenario`` and
``spine.DeploymentBinding`` are Protocols, and the classes below satisfy them by
shape (CLAUDE.md §11, *Prefer Protocols over inheritance*). That is the same
posture :class:`ccf.projection.plan.ProjectionPlan` takes toward the class you
are reading.

**It holds no write handle to the graph.** The only one that exists in this
process is ``booted.handle.worker``, and it never leaves ``spine.py``'s
``ingest`` region (single-writer, CLAUDE.md §10, INV-CH7-10).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

from ccf.contracts.base import CCFContract
from ccf.controlplane.artifacts import (
    DeclaredArtifact,
    OperatorParametersArtifact,
    PerspectiveArtifact,
    ProductClassDeclaration,
    ProjectionRequirements,
    SignalBatch,
)
from ccf.deployment import BootedFabric
from ccf.graph.protocols import GraphView
from ccf.operators.base import OperatorOutput
from ccf.projection.plan import Perspective, ProjectionOutput
from ccf.signal.envelope import SignalEnvelope

EXAMPLE_DIR = Path(__file__).resolve().parent
MANIFEST = EXAMPLE_DIR / "artifacts" / "manifest.yaml"

# --- this deployment's artifact-key vocabulary -------------------------------
# Every name below is a `key` in `artifacts/manifest.yaml`. They are literals
# here on purpose: naming them is how a deployment says which of ITS documents
# plays which role, and the alternative — an `isinstance` filter or a class-id
# match — is type introspection dressed up as configuration.

KEY_EVENTS = "events"
KEY_DECISION = "decision"
KEY_EXPECTED = "expected"
KEY_PERSPECTIVE = "perspective"
KEY_PRODUCT_CLASS = "product-class"
KEY_PRODUCT_GOVERNANCE = "product-governance"
KEY_PROJECTION_REQUIREMENTS = "projection-requirements"
KEY_POLICY_BUNDLE = "policy-bundle"
KEY_UBO_QUESTION = "ubo-question"

#: The four operator-parameters documents, one per canonical category. Named
#: rather than discovered, for the reason above.
OPERATOR_KEYS = ("traversal", "temporal", "policy", "similarity")

#: The Control Plane connection argument this deployment supplies at boot. The
#: manifest declares the backend KIND; the value that reaches the substrate is
#: this, and it is deliberately a caller-supplied path under a scratch root so
#: that no location is ever written into a content-hashed artifact
#: (threat T-16-05-01).
CONNECTION_PATH_KEY = "database_path"
DATABASE_FILENAME = "ubo.sqlite3"

# --- the roles the two deployment-authored documents play --------------------
# Declaration keys, not values. Each one names a member of a `declaration:`
# block in `artifacts/`; none of them is a domain value, and every value they
# reach is read from the document.

GOVERNANCE_MAX_TTL_SECONDS = "max_ttl_seconds"
GOVERNANCE_PRODUCT_TTL_SECONDS = "product_ttl_seconds"
GOVERNANCE_SIMILARITY_INDEX_VERSION = "similarity_index_version"
GOVERNANCE_REPLAY_RECORD_CLASS = "replay_record_class"
GOVERNANCE_ARTIFACT_STORE_DIRNAME = "artifact_store_dirname"

DECISION_TEMPORAL_BOUNDARY = "temporal_boundary"
DECISION_NOW = "now"

POLICY_THRESHOLD_PERCENT = "beneficial_ownership_threshold_percent"
POLICY_SCALE_PLACES = "ownership_percent_scale_places"

QUESTION_SUBJECT = "subject_entity_ref"
QUESTION_NATURAL_PERSON_CLASS = "natural_person_class"
QUESTION_STAKE_CLASS = "ownership_stake_class"
QUESTION_STAKE_OWNER_ATTRIBUTE = "stake_owner_attribute"
QUESTION_STAKE_TARGET_ATTRIBUTE = "stake_target_attribute"
QUESTION_STAKE_PERCENT_ATTRIBUTE = "stake_percent_attribute"
QUESTION_PARTY_REF_ATTRIBUTE = "party_ref_attribute"
QUESTION_PARTY_NAME_ATTRIBUTE = "party_name_attribute"

#: Percentages are fractions of a hundred. The one arithmetic constant in this
#: file, and it is arithmetic rather than domain: change it and "percent" stops
#: meaning percent.
HUNDRED = Decimal(100)


@dataclass(frozen=True)
class KycScenario:
    """One run's values, read out of this deployment's own artifacts.

    Satisfies ``spine.Scenario`` structurally. The members past
    ``artifacts`` are this deployment's business and the fabric never asks for
    them — they are what the projection interprets.
    """

    artifacts: Mapping[str, CCFContract]
    envelopes: tuple[SignalEnvelope, ...]
    temporal_boundary: datetime
    now: datetime
    expires_at: datetime
    operator_parameters: Mapping[str, OperatorParametersArtifact]
    policy_bundle_key: str
    similarity_index_version: str
    product_class: ProductClassDeclaration
    plan_id: str
    required_operator_keys: tuple[str, ...]
    perspective: PerspectiveArtifact
    max_ttl_seconds: int
    replay_record_class: str
    artifact_store_dirname: str

    # --- not read by the fabric: the question and how to report its answer ---
    question: Mapping[str, Any]
    threshold_percent: Decimal
    scale_places: int


class UltimateBeneficialOwnershipPlan:
    """The deployment's Π: what the reconciled subgraph means to its reader.

    A projection declares which operators its interpretation depends on and
    interprets their output; it does not run them and cannot tell the engine
    what ran, which is what leaves the L6 lineage gate something real to check.

    ``required`` is passed in from ``artifacts/projection-requirements.yaml`` —
    this projection's OWN authored operator set — and is never read off the
    operator registry, which would make the plan's requirements a restatement of
    whatever happens to be registered.

    The product class's ``required_operator_keys`` is a different statement
    about a different thing: the CLAIM the product carries into
    ``lineage.operators_invoked``. Two documents, one per side, held together by
    the operator-set binder in :mod:`ccf.deployment`, which ``spine.py`` calls
    between constructing this plan and executing it — so a disagreement between
    the two is a refusal rather than an identity nobody can see (design E2,
    D-IMPL-86).

    **What it computes.** Aggregate ultimate beneficial ownership of the subject
    named in ``artifacts/ubo-question.yaml``, over the ownership DAG the
    operators left standing, against the threshold in
    ``artifacts/policy-bundle.yaml``. The answer to *"who ultimately owns this
    company?"* is a sum over paths, and it is stated in no single record of any
    source system — which is the whole of why the graph is the substrate.
    """

    def __init__(
        self,
        *,
        plan_id: str,
        required: tuple[str, ...],
        scenario: KycScenario,
    ) -> None:
        self._plan_id = plan_id
        self._required = required
        self._question = scenario.question
        self._threshold = scenario.threshold_percent
        self._scale = scenario.scale_places

    @property
    def plan_id(self) -> str:
        return self._plan_id

    def required_operators(self) -> tuple[str, ...]:
        return self._required

    def _quantize(self, value: Decimal) -> str:
        """Render a percentage at the scale the policy bundle declared.

        Text, not a float: a float is not bit-stable across platforms, and this
        value goes into a canonically serialized Context Product whose content
        hash is what replay resolves against.
        """
        return str(value.quantize(Decimal(1).scaleb(-self._scale)))

    def _stakes(self, view: GraphView) -> dict[str, tuple[tuple[str, Decimal], ...]]:
        """``owner reference -> ((target reference, percent), ...)``.

        Read off the reified ownership-stake entities the operators left in the
        view. Direction comes from the stake's own attributes rather than from
        edge direction — see ``artifacts/resolution-spec.yaml`` for why a
        qualified relation is reified here.
        """
        stake_class = self._question[QUESTION_STAKE_CLASS]
        owner_key = self._question[QUESTION_STAKE_OWNER_ATTRIBUTE]
        target_key = self._question[QUESTION_STAKE_TARGET_ATTRIBUTE]
        percent_key = self._question[QUESTION_STAKE_PERCENT_ATTRIBUTE]
        by_owner: dict[str, list[tuple[str, Decimal]]] = {}
        for record in view.entities:
            if record.claim.entity_class != stake_class:
                continue
            attributes = record.claim.attributes
            by_owner.setdefault(attributes[owner_key], []).append(
                (attributes[target_key], Decimal(attributes[percent_key]))
            )
        return {owner: tuple(sorted(held)) for owner, held in by_owner.items()}

    def _held(
        self,
        owner: str,
        *,
        subject: str,
        by_owner: Mapping[str, tuple[tuple[str, Decimal], ...]],
        seen: frozenset[str],
    ) -> Decimal:
        """The percentage of ``subject`` that ``owner`` holds, direct plus indirect.

        A direct stake contributes its own percentage; an indirect one
        contributes its fraction of whatever the entity it points at holds. The
        estate's ownership edges form a DAG, so this terminates on the data;
        ``seen`` is carried anyway, because a projection that hung on a cyclic
        holding structure would be a projection that trusted its input.
        """
        total = Decimal(0)
        for target, percent in by_owner.get(owner, ()):
            if target == subject:
                total += percent
            elif target not in seen:
                total += (percent / HUNDRED) * self._held(
                    target, subject=subject, by_owner=by_owner, seen=seen | {target}
                )
        return total

    def invoke(
        self,
        *,
        view: GraphView,
        operator_outputs: Mapping[str, OperatorOutput],
        perspective: Perspective,
        temporal_boundary: datetime,
    ) -> ProjectionOutput:
        subject = self._question[QUESTION_SUBJECT]
        person_class = self._question[QUESTION_NATURAL_PERSON_CLASS]
        ref_key = self._question[QUESTION_PARTY_REF_ATTRIBUTE]
        name_key = self._question[QUESTION_PARTY_NAME_ATTRIBUTE]

        by_owner = self._stakes(view)
        people = sorted(
            (
                (
                    record.claim.attributes[ref_key],
                    record.claim.attributes[name_key],
                )
                for record in view.entities
                if record.claim.entity_class == person_class
            )
        )
        holdings = {
            reference: self._held(
                reference,
                subject=subject,
                by_owner=by_owner,
                seen=frozenset({reference}),
            )
            for reference, _name in people
        }

        return ProjectionOutput(
            plan_id=self._plan_id,
            payload={
                "role": perspective.role,
                "subject_entity_ref": subject,
                "entity_count": len(view.entities),
                "entity_classes": sorted(
                    {record.claim.entity_class for record in view.entities}
                ),
                "entity_count_by_class": {
                    entity_class: sum(
                        1
                        for record in view.entities
                        if record.claim.entity_class == entity_class
                    )
                    for entity_class in sorted(
                        {record.claim.entity_class for record in view.entities}
                    )
                },
                "relationship_types": sorted(
                    {edge.claim.relationship_type for edge in view.relationships}
                ),
                "beneficial_ownership_threshold_percent": self._quantize(
                    self._threshold
                ),
                "ownership_percent_by_party": {
                    reference: self._quantize(percent)
                    for reference, percent in sorted(holdings.items())
                },
                # The answer. A natural person whose aggregate interest reaches
                # the regime's threshold — direct and indirect together.
                "beneficial_owners": [
                    {
                        "party_ref": reference,
                        "party_name": name,
                        "aggregate_ownership_percent": self._quantize(
                            holdings[reference]
                        ),
                    }
                    for reference, name in people
                    if holdings[reference] >= self._threshold
                ],
            },
        )


class KycDeployment:
    """The four things this deployment supplies the fabric.

    Satisfies ``spine.DeploymentBinding`` structurally.
    """

    @property
    def manifest(self) -> Path:
        return MANIFEST

    def connection(self, *, root: Path) -> Mapping[str, str]:
        """Where the graph substrate lives, for this run.

        Supplied by the CALLER and never by the manifest. The manifest declares
        the backend as a KIND (``backend: sqlite``); this is the only place a
        location exists, and it is derived from a scratch root the caller
        chose — so nothing that could identify a machine, a database or a
        credential is ever content-hashed into the audit plane.
        """
        return {CONNECTION_PATH_KEY: str(root / DATABASE_FILENAME)}

    def read(self, booted: BootedFabric) -> KycScenario:
        """Name this deployment's own artifact keys and read the run's values.

        Each artifact comes back under its own manifest key, already validated
        against the class the manifest declared for it — so these casts restate
        what ``load_and_boot`` already enforced. A wrong ``class_id`` in the
        manifest fails at parse, before this method runs.
        """
        events = cast(SignalBatch, booted.artifacts[KEY_EVENTS])
        decision = cast(DeclaredArtifact, booted.artifacts[KEY_DECISION]).declaration
        governance = cast(
            DeclaredArtifact, booted.artifacts[KEY_PRODUCT_GOVERNANCE]
        ).declaration
        policy = cast(
            DeclaredArtifact, booted.artifacts[KEY_POLICY_BUNDLE]
        ).declaration
        question = cast(
            DeclaredArtifact, booted.artifacts[KEY_UBO_QUESTION]
        ).declaration
        # The projection's own operator set, authored separately from the claim
        # the product class carries. Design E2 keeps these two documents apart
        # on purpose; the binder in `spine.py` is what keeps them in agreement.
        requirements = cast(
            ProjectionRequirements, booted.artifacts[KEY_PROJECTION_REQUIREMENTS]
        )

        now = datetime.fromisoformat(decision[DECISION_NOW])
        return KycScenario(
            artifacts=booted.artifacts,
            envelopes=events.envelopes,
            temporal_boundary=datetime.fromisoformat(
                decision[DECISION_TEMPORAL_BOUNDARY]
            ),
            now=now,
            expires_at=now
            + timedelta(seconds=governance[GOVERNANCE_PRODUCT_TTL_SECONDS]),
            operator_parameters={
                key: cast(OperatorParametersArtifact, booted.artifacts[key])
                for key in OPERATOR_KEYS
            },
            policy_bundle_key=KEY_POLICY_BUNDLE,
            similarity_index_version=governance[
                GOVERNANCE_SIMILARITY_INDEX_VERSION
            ],
            product_class=cast(
                ProductClassDeclaration, booted.artifacts[KEY_PRODUCT_CLASS]
            ),
            plan_id=requirements.plan_id,
            required_operator_keys=requirements.required_operator_keys,
            perspective=cast(
                PerspectiveArtifact, booted.artifacts[KEY_PERSPECTIVE]
            ),
            max_ttl_seconds=governance[GOVERNANCE_MAX_TTL_SECONDS],
            replay_record_class=governance[GOVERNANCE_REPLAY_RECORD_CLASS],
            artifact_store_dirname=governance[GOVERNANCE_ARTIFACT_STORE_DIRNAME],
            question=question,
            threshold_percent=Decimal(policy[POLICY_THRESHOLD_PERCENT]),
            scale_places=policy[POLICY_SCALE_PLACES],
        )

    #: Π, as a class rather than as a constructed object. ``spine.py`` builds it
    #: one statement before it binds it, because a plan handed over ready-made
    #: is a plan no binder can be shown to have been given (design E2,
    #: D-IMPL-86 as corrected 2026-08-05).
    plan_class = UltimateBeneficialOwnershipPlan


def expectation(artifacts: Mapping[str, CCFContract]) -> Mapping[str, Any]:
    """This deployment's own declaration of what the product should contain.

    Used by ``tests/examples/test_s1_01_output.py``, never by the pipeline. It
    lives here rather than in the test module so that the test reads the
    deployment's declaration rather than agreeing with itself (CLAUDE.md §6.4).
    """
    return cast(DeclaredArtifact, artifacts[KEY_EXPECTED]).declaration


def envelope_count(envelopes: Sequence[SignalEnvelope]) -> int:
    """How many envelopes one run ingested — for the test module's precondition."""
    return len(envelopes)
