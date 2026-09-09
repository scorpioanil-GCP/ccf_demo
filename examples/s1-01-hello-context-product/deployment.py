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
   in :func:`read` because they are this deployment's own words:
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
it.** The two are held together structurally — ``spine.Scenario`` is a Protocol
and :class:`KycScenario` below satisfies it by shape (CLAUDE.md §11, *Prefer
Protocols over inheritance*). That is the same posture
:class:`ccf.projection.plan.ProjectionPlan` takes toward the class you are
reading. Everything else this file supplies — :data:`MANIFEST`,
:func:`connection`, :func:`read` and the projection class — is handed to
``spine.assemble_and_serve`` as an ordinary argument by ``run.py``.

**It holds no write handle to the graph.** The only one that exists in this
process is ``booted.handle.worker``, and it never leaves ``spine.py``'s
``ingest`` region (single-writer, CLAUDE.md §10, INV-CH7-10).
"""

from __future__ import annotations

import os
import re
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import yaml

from ccf.contracts.base import CCFContract
from ccf.controlplane.artifacts import (
    DeclaredArtifact,
    OperatorParametersArtifact,
    PerspectiveArtifact,
    ProductClassDeclaration,
    ProjectionRequirements,
    SignalBatch,
)
from ccf.controlplane.artifacts import DebtProfile, HalfLifeTable
from ccf.deployment import BootedFabric
from ccf.graph.protocols import GraphView
from ccf.halflife.debt import (
    NO_DEBT_EVIDENCE,
    DebtAssessment,
    DebtEvidence,
    DebtFactors,
    FreshnessScorer,
    ScorerPin,
    SourceRefreshRecency,
    SourceRefreshWindow,
    assess_debt,
)
from ccf.halflife.decay import Observation
from ccf.operators.base import OperatorOutput
from ccf.products.payload import ProductPayloadSchema
from ccf.products.request import ProductRequest, ProductRequestContract
from ccf.projection.plan import Perspective, ProjectionOutput
from ccf.signal.envelope import SignalEnvelope

EXAMPLE_DIR = Path(__file__).resolve().parent
MANIFEST = EXAMPLE_DIR / "artifacts" / "manifest.yaml"

#: The questions the bundled demonstration asks. Deliberately NOT in the
#: manifest: a question is caller input, not Control Plane state, and it has no
#: business in Decision Replay dimension 2. Read directly, on the read-side /
#: write-side split ``source-estate.yaml`` already records (`D-04`).
QUESTIONS = EXAMPLE_DIR / "artifacts" / "questions.yaml"

#: How this deployment's connection settings are composed, per backend kind.
#: Deliberately NOT in the manifest either, and for a second reason beyond
#: `questions.yaml`'s: a connection is deployment ENVIRONMENT, and a
#: content-hashed artifact is forever (threat `T-16-05-01`).
BACKENDS = EXAMPLE_DIR / "artifacts" / "backends.yaml"

# --- this deployment's artifact-key vocabulary -------------------------------
# Every name below is a `key` in `artifacts/manifest.yaml`. They are literals
# here on purpose: naming them is how a deployment says which of ITS documents
# plays which role, and the alternative — an `isinstance` filter or a class-id
# match — is type introspection dressed up as configuration.

KEY_EVENTS = "events"
KEY_REQUEST_CONTRACT = "request-contract"
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

#: `artifacts/backends.yaml`'s own blocks — the connection PROFILE per backend
#: kind. Deliberately not in the manifest, for `questions.yaml`'s reason: a
#: connection is deployment environment, not Control Plane state.
PROFILES = "profiles"
PROFILE_SETTINGS = "settings"

#: The three value sources a setting may name. MECHANISM, not substrate: the
#: only branch in this module is over these three, and none of them knows what
#: a backend kind is.
SOURCE_FROM_ENV = "from_env"
SOURCE_PER_RUN = "per_run"
PER_RUN_IDENTIFIER = "identifier"
PER_RUN_PATH = "path"
SETTING_PREFIX = "prefix"
SETTING_FILENAME = "filename"
SETTING_REMEDY = "remedy"

#: `manifest.yaml`'s one-line declaration of which kind is in force. Read with
#: `yaml.safe_load` exactly as `_questions_document()` reads its own document;
#: `ccf.deployment.__all__` exports no manifest parse function, and reaching
#: past the package for a submodule would break the A-1 import convention.
MANIFEST_BACKEND = "backend"

#: The shape a minted per-run identifier has to have to be a name the graph can
#: be written under. Mechanism: it constrains the identifier this module MINTS,
#: and it names no substrate.
IDENTIFIER_SHAPE = re.compile(r"^[a-z][a-z0-9_]*$")

# --- the roles the two deployment-authored documents play --------------------
# Declaration keys, not values. Each one names a member of a `declaration:`
# block in `artifacts/`; none of them is a domain value, and every value they
# reach is read from the document.

GOVERNANCE_MAX_TTL_SECONDS = "max_ttl_seconds"
GOVERNANCE_PRODUCT_TTL_SECONDS = "product_ttl_seconds"
GOVERNANCE_REPLAY_RECORD_CLASS = "replay_record_class"
GOVERNANCE_QUERY_PIN_CLASS = "query_pin_class"
GOVERNANCE_ARTIFACT_STORE_DIRNAME = "artifact_store_dirname"
GOVERNANCE_REQUEST_CONTRACT_KEY = "request_contract_key"
GOVERNANCE_REQUIRED_ENTITY_CLASSES = "required_entity_classes"
GOVERNANCE_SEMANTIC_CONSISTENCY = "semantic_consistency"
GOVERNANCE_SOURCE_REFRESH_RECENCY = "source_refresh_recency"
GOVERNANCE_SOURCE_REF = "source_ref"
GOVERNANCE_REFRESHED_AT = "refreshed_at"

KEY_HALF_LIFE_TABLE = "half-life-table"
KEY_DEBT_PROFILE = "debt-profile"

#: The `arguments` block of `artifacts/request-contract.yaml`. The Control Plane
#: KEY the contract is registered under is authored in
#: `artifacts/product-governance.yaml` beside the MAX_TTL key, for the same
#: reason: the key is authored, the version pinning it is minted by registering
#: the parsed value (D-IMPL-98, D-IMPL-39).
REQUEST_CONTRACT_SCHEMA_NAME = "schema_name"
REQUEST_CONTRACT_SCHEMA_VERSION = "schema_version"
REQUEST_CONTRACT_ARGUMENTS = "arguments"

#: The class-declared remainder of a question, beyond the four address axes.
#: Declared in `artifacts/request-contract.yaml`; named here because naming it
#: is how this deployment says which of ITS parameters plays which role.
PARAM_DECISION_INSTANT = "decision_instant"

#: `artifacts/questions.yaml`'s own blocks — the address every question is sent
#: to, the defaults an ad-hoc command-line question inherits, and the list.
QUESTIONS_SCHEMA_NAME = "schema_name"
QUESTIONS_SCHEMA_VERSION = "schema_version"
QUESTIONS_DEFAULT_INTENT = "default_intent"
QUESTIONS_DEFAULT_FRESHNESS = "default_freshness"
QUESTIONS_LIST = "questions"
QUESTION_SUBJECT = "subject"
QUESTION_INTENT = "intent"
QUESTION_FRESHNESS = "freshness"
QUESTION_ASKED_AT = "asked_at"
QUESTION_PARAMETERS = "parameters"

POLICY_THRESHOLD_PERCENT = "beneficial_ownership_threshold_percent"
POLICY_SCALE_PLACES = "ownership_percent_scale_places"

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

#: Which of the three D_c factors this deployment's pinned scorer accounts for.
#: SDK vocabulary (`DebtFactorName`), named here because a pin has to say which
#: factor it produced.
FRESHNESS_FACTOR = "freshness"


@dataclass(frozen=True)
class KycScenario:
    """One run's values, read out of this deployment's own artifacts.

    Satisfies ``spine.Scenario`` structurally. The members past
    ``artifacts`` are this deployment's business and the fabric never asks for
    them — they are what the projection interprets.
    """

    artifacts: Mapping[str, CCFContract]
    envelopes: tuple[SignalEnvelope, ...]
    request: ProductRequest
    request_contract: ProductRequestContract
    request_contract_key: str
    temporal_boundary: datetime
    now: datetime
    expires_at: datetime
    operator_parameters: Mapping[str, OperatorParametersArtifact]
    policy_bundle_key: str
    product_class: ProductClassDeclaration
    plan_id: str
    required_operator_keys: tuple[str, ...]
    perspective: PerspectiveArtifact
    max_ttl_seconds: int
    replay_record_class: str
    query_pin_class: str
    artifact_store_dirname: str

    half_life_table: HalfLifeTable
    debt_profile: DebtProfile
    required_entity_classes: tuple[str, ...]
    semantic_consistency: Decimal

    #: When the oldest and the newest of this estate's sources last published,
    #: reduced from ``artifacts/product-governance.yaml`` by
    #: :func:`_declared_refresh_window` (D-IMPL-112 gap 2, D-IMPL-117,
    #: D-IMPL-124).
    #:
    #: A **field and not a method**, unlike ``debt`` and ``debt_evidence``
    #: beside it, and the difference is the point: those two are measured
    #: against the assembled view, and this one is *declared*. A refresh
    #: instant is not a property of what the operators left standing — it is a
    #: fact about the world upstream of the fabric, which the deployment
    #: knows and the fabric cannot observe. Giving it a view parameter it would
    #: not read would suggest otherwise.
    #:
    #: **The per-source references are already gone by the time a value reaches
    #: this field** (D-IMPL-124). The artifact keeps them; this scenario carries
    #: only the window they span, and the window is what the spine puts on the
    #: delivered product.
    source_refresh_recency: SourceRefreshRecency

    # --- not read by the fabric: the question and how to report its answer ---
    question: Mapping[str, Any]
    threshold_percent: Decimal
    scale_places: int

    def debt(self, view: GraphView) -> DebtAssessment:
        """Measure D_c over what this question actually assembled.

        **Measured, not declared** — which is why it takes the assembled view.
        F is the reference decay-ratio scorer run over every entity claim the
        operators left standing, typed by the class the resolution spec
        resolved it to and dated by its own ``observed_at``; C is the fraction
        of this deployment's declared required classes the view actually holds;
        S is a declared figure, because the SDK ships no S producer and
        inventing one here would be worse than saying so (D-IMPL-101's posture
        on salience, applied).

        The instant is ``now`` — the class-declared ``decision_instant`` off
        the request — so the same question asked six weeks later measures more
        decay against the same graph and delivers a larger debt. That is the
        whole point of a figure that is measured rather than constant.

        Only F is pinned. An assessment whose pins somebody dropped and one
        whose factors no declared scorer produced would otherwise be the same
        artifact (D-IMPL-47).
        """
        observations = tuple(
            Observation(
                observation_type=record.claim.entity_class,
                observed_at=record.claim.observed_at,
                # [ADAPT] This deployment identifies an observation by the
                # canonical entity URI, because that is the key its own graph
                # is indexed on — so a debt figure can later be attributed back
                # to the entity whose staleness produced it. The SDK chose
                # nothing here: `subject` is an opaque string and `record.claim`
                # also offers `lineage`, whose `LineageEntry.envelope_id` would
                # identify the *source envelope* instead. Either is a legitimate
                # subject; which one you want depends on whether you attribute
                # decay to entities or to feeds (D-IMPL-117 — the SDK owes the
                # structure and none of the judgement).
                subject=record.claim.entity_uri,
            )
            for record in view.entities
        )
        scorer = FreshnessScorer(
            table=self.half_life_table,
            risk_sensitivity=self.debt_profile.risk_sensitivity,
        )
        assembled = {record.claim.entity_class for record in view.entities}
        held = sum(
            1 for required in self.required_entity_classes if required in assembled
        )
        return assess_debt(
            DebtFactors(
                freshness=scorer.score(observations, now=self.now),
                completeness=(
                    Decimal(held) / Decimal(len(self.required_entity_classes))
                ),
                semantic_consistency=self.semantic_consistency,
            ),
            profile=self.debt_profile,
            scorers=(ScorerPin.of(scorer, factor=FRESHNESS_FACTOR),),
        )

    def debt_evidence(self, view: GraphView) -> DebtEvidence:
        """What the debt points at — and why this deployment points at nothing.

        **D-IMPL-119, limb 3(b) — the omission path, taken explicitly.** The
        ruling gives plan ``15.6-06`` exactly two paths and this deployment
        takes the second, quoted verbatim: *"(b) **omit evidence pointers
        entirely** until a later phase adds principal scoping to the assembly
        path."*

        Why (b) rather than (a). The ruling's limb 1 makes the safety property
        **the SDK's**, not the adopter's — it declined ``qb2-opaque`` precisely
        because that *"moves a real disclosure question onto every adopter, and
        the SDK cannot then say the surface is safe by construction"*. Limb 4
        then refuses a handle that is *merely encoded* rather than genuinely
        non-revealing: *"an obfuscated `entity_uri` is an interpretable pointer
        with an extra step"*. The only inputs in hand at this call site are the
        assembled ``EntityClaim``s, and limb 2 puts principal scoping of the
        assembly path explicitly out of scope for this phase — so every handle
        derivable here is either interpretable (refused by limb 4) or has had
        its referent discarded, which is a pointer that points at nothing
        dressed as one that does. Emitting the named sentinel says the same
        thing without the costume.

        What is NOT being asserted: that scoped derivation is unwanted. The
        ruling forecloses that reading — *"it does not license a later plan
        inferring, from limb 2, that scoped derivation is unwanted; limb 1 says
        the opposite."* The carrier ships (D-IMPL-118) and the replay seam that
        makes it reconstructible ships with it, so the phase that closes the
        scoping gap populates this method and changes no surface.

        ``view`` is taken and unread, deliberately: the signature is the one a
        populating deployment needs, so closing the gap is a body change rather
        than a call-site change.
        """
        del view  # See above: the omission is the ruling's, not the shape's.
        return NO_DEBT_EVIDENCE


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
    **the caller asked about**, over the ownership DAG the operators left
    standing, against the threshold in ``artifacts/policy-bundle.yaml``. The
    answer to *"who ultimately owns this company?"* is a sum over paths, and it
    is stated in no single record of any source system — which is the whole of
    why the graph is the substrate.

    **The subject is read off the request, never off an artifact** (plan
    ``15.5-13``). ``artifacts/ubo-question.yaml`` supplies the vocabulary the
    question is asked in — which class is a natural person, which attribute
    carries a stake's percentage — and that genuinely is governance. Which
    company is being asked about is not, and a projection that read it from a
    document could only ever answer about one company. This one answers about
    whichever company arrived on :attr:`ccf.products.request.ProductRequest
    .subject`, which is the difference between a product that is *configured*
    and a product that is *called*.
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
        self._subject = scenario.request.subject
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
        subject = self._subject
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


def _declared_kind() -> str:
    """The one line in ``artifacts/manifest.yaml`` that names the substrate.

    Raises:
        FileNotFoundError: the manifest is absent. This module is an
            interpreter and has nothing to interpret without it (CLAUDE.md
            §6.4).
    """
    document = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    return cast(str, document[MANIFEST_BACKEND])


def _profile(kind: str) -> Mapping[str, Any]:
    """The connection profile ``artifacts/backends.yaml`` declares for ``kind``.

    Two refusals, each naming its remedy and neither offering a value. Neither
    falls back to anything: the whole point of a declared kind is that a fabric
    never guesses its own substrate, and a guess that succeeded would be a
    development store answering a production question.
    """
    if not BACKENDS.is_file():
        raise FileNotFoundError(
            f"{BACKENDS} is missing. It is where this deployment says how its"
            " connection settings are composed, and there is no default to"
            " fall back to: the code is an interpreter and this document is"
            " what it interprets (CLAUDE.md §6.4, the No-Hardcoding Rule)."
        )
    document = yaml.safe_load(BACKENDS.read_text(encoding="utf-8"))
    declared = cast(
        Mapping[str, Any], document["declaration"][PROFILES]
    )
    if kind not in declared:
        raise KeyError(
            f"artifacts/manifest.yaml declares `{MANIFEST_BACKEND}: {kind}` and"
            f" {BACKENDS.name} declares no profile for it. Profiles it does"
            f" declare: {sorted(declared)}. Add one there, or name one of those"
            " in the manifest."
        )
    return cast(Mapping[str, Any], declared[kind][PROFILE_SETTINGS])


def _from_environment(setting: str, source: Mapping[str, Any]) -> str:
    """One setting's value, read from the environment variable it names.

    The document holds the variable's NAME; the value never enters the tree.
    An unset or empty variable is a REFUSAL and never a default — a fabric
    that silently answered from somewhere other than where its operator
    pointed it is the hazard :mod:`ccf.graph.registry` is written against.
    The remedy is quoted from the document, so this module stays free of the
    vocabulary of any particular substrate.
    """
    variable = source[SOURCE_FROM_ENV]
    value = os.environ.get(variable, "")
    if not value:
        raise RuntimeError(
            f"{variable} is unset; {source[SETTING_REMEDY]}. It supplies"
            f" `{setting}`, which artifacts/backends.yaml declares this"
            " deployment reads from the environment. There is no default and"
            " no fallback to another backend kind."
        )
    return cast(str, value)


def _per_run(setting: str, source: Mapping[str, Any], *, root: Path) -> str:
    """One setting's value, minted fresh for this run.

    Two rules, and the branch below is over THOSE — never over a backend kind.
    An identifier gives each run its own graph inside a shared server; a path
    gives each run its own file under the caller's own scratch root. They are
    the same property expressed against two kinds of substrate, which is why
    both are mechanism.
    """
    rule = source[SOURCE_PER_RUN]
    if rule == PER_RUN_IDENTIFIER:
        minted = f"{source[SETTING_PREFIX]}_{uuid.uuid4().hex}"
        if not IDENTIFIER_SHAPE.fullmatch(minted):
            raise ValueError(
                f"the minted value for `{setting}` is {minted!r}, which is not"
                f" the {IDENTIFIER_SHAPE.pattern} shape a graph name takes;"
                f" the `{SETTING_PREFIX}` in artifacts/backends.yaml is what"
                " decides it."
            )
        return minted
    if rule == PER_RUN_PATH:
        return str(root / source[SETTING_FILENAME])
    raise ValueError(
        f"`{setting}` names the per-run rule {rule!r}, which is not one this"
        f" module interprets. Declared rules: {PER_RUN_IDENTIFIER},"
        f" {PER_RUN_PATH}."
    )


def connection(*, root: Path) -> Mapping[str, str]:
    """Where this run's graph lives — composed, never written down.

    Supplied by the CALLER and never by the manifest. ``manifest.yaml``
    declares the KIND; ``backends.yaml`` declares how that kind's settings are
    composed; and every value below comes from the process environment or from
    the caller's own scratch root. Nothing that could identify a machine, a
    database or a credential is ever content-hashed into the audit plane
    (threat ``T-16-05-01``).

    **No substrate name and no branch keyed on one.** The only branch here is
    over the three value SOURCES, which is what lets plan 16-07 add the
    remaining four profiles to the document and change nothing in this file.

    **A fresh value is minted PER CALL, which is per question.** ``ask_all``
    calls this once per question, so the two isolations are complementary and
    both are needed: the caller's scratch directory isolates the
    **ArtifactStore**, and the per-run identifier isolates the **graph**.
    Together they are what lets two replay records — and the query sequences
    they pin — be compared side by side without either run having observed the
    other. Before the substrate moved off per-question temp files, the scratch
    directory did both jobs; on a shared server it can only do one.

    **Repeated runs accumulate graphs on a shared server.** One CCF-owned
    ledger is ``D-03``'s deliberate trade for a single lane, and a fresh
    identifier per run is what buys isolation inside it. Stated here so an
    operator watching a long-lived container is not surprised; discarding the
    container discards them all.
    """
    return {
        setting: (
            _from_environment(setting, source)
            if SOURCE_FROM_ENV in source
            else _per_run(setting, source, root=root)
        )
        for setting, source in _profile(_declared_kind()).items()
    }


def _questions_document() -> Mapping[str, Any]:
    """The caller's questions, read straight off ``artifacts/questions.yaml``.

    Read directly rather than through the manifest, on the split
    ``source-estate.yaml`` records (`D-04`): a question is caller input, not
    Control Plane state, and registering it would content-hash *what one caller
    asked* into the pin set and therefore into Decision Replay dimension 2 —
    which records what the fabric was PERMITTED to do.

    Raises:
        FileNotFoundError: the artifact is absent. This module is an
            interpreter and has nothing to interpret without it (CLAUDE.md
            §6.4).
    """
    document = yaml.safe_load(QUESTIONS.read_text(encoding="utf-8"))
    return cast(Mapping[str, Any], document["declaration"])


def _request(
    *,
    address: Mapping[str, Any],
    subject: str,
    intent: str,
    freshness: str,
    asked_at: str,
    parameters: Mapping[str, Any],
) -> ProductRequest:
    """Build one typed question at the address the questions document names."""
    return ProductRequest(
        schema_name=address[QUESTIONS_SCHEMA_NAME],
        schema_version=address[QUESTIONS_SCHEMA_VERSION],
        subject=subject,
        intent=intent,
        freshness=freshness,
        asked_at=datetime.fromisoformat(asked_at),
        parameters=dict(parameters),
    )


def declared_questions() -> tuple[ProductRequest, ...]:
    """Every question the bundled demonstration asks, typed.

    Three of them, and they are a controlled experiment rather than a list —
    see the artifact's own header. ``run.py`` asks each in turn against its own
    fabric, so the two replay records can be compared side by side.
    """
    document = _questions_document()
    return tuple(
        _request(
            address=document,
            subject=question[QUESTION_SUBJECT],
            intent=question[QUESTION_INTENT],
            freshness=question[QUESTION_FRESHNESS],
            asked_at=question[QUESTION_ASKED_AT],
            parameters=question[QUESTION_PARAMETERS],
        )
        for question in document[QUESTIONS_LIST]
    )


def ad_hoc_question(
    *, subject: str, asked_at: str, decision_instant: str
) -> ProductRequest:
    """A question that is in no artifact at all.

    This is what makes the product *callable*: a reader asks about a company
    nobody anticipated, at an instant nobody authored, without editing a
    document or a line of code. The intent and freshness a command line does not
    carry are taken from the questions document's declared defaults rather than
    invented here — an exposed door would read both off the caller's own
    request and substitute nothing.
    """
    document = _questions_document()
    return _request(
        address=document,
        subject=subject,
        intent=document[QUESTIONS_DEFAULT_INTENT],
        freshness=document[QUESTIONS_DEFAULT_FRESHNESS],
        asked_at=asked_at,
        parameters={PARAM_DECISION_INSTANT: decision_instant},
    )


def _declared_refresh_window(
    entries: Sequence[Mapping[str, str]],
) -> SourceRefreshWindow:
    """Reduce this estate's declared per-source instants to the window they span.

    **[ADAPT] This function is the D-IMPL-124 boundary, and it lives here
    rather than in the SDK on purpose.** ``product-governance.yaml`` declares
    one entry per upstream source with a human-interpretable reference; those
    references reach this function and go no further. What leaves is a
    :class:`~ccf.halflife.assessment.SourceRefreshWindow` carrying two
    instants, no reference and no count — so a consumer of the delivered
    product learns when the oldest and the newest of this estate's sources
    published, and learns nothing about which systems they are or how many
    there are.

    Why not an SDK helper: a reducer in ``src/`` would take a source-bearing
    input type, putting the shape D-IMPL-124 removed back on the public
    surface, and it would make the SDK the party deciding which of a
    deployment's sources count toward the window. Whether the entries below are
    this estate's *complete* set is a deployment fact the SDK cannot verify,
    which is exactly why the reduction is the deployment's work.

    Every instant is parsed from authored text, never read off a clock, and
    ``min``/``max`` select among facts this deployment already stated rather
    than deriving a new one.

    A duplicate reference is refused here rather than silently collapsed: two
    refresh instants for one source describe two facts claiming to be one, and
    with the per-source map gone from the vessel this deployment is the last
    party in a position to notice.
    """
    references = [entry[GOVERNANCE_SOURCE_REF] for entry in entries]
    if len(set(references)) != len(references):
        raise ValueError(
            "a source reference may carry at most one refresh instant; two "
            "instants for one source describe two facts claiming to be one, "
            "which is an incoherent declaration rather than a stricter one"
        )

    instants = [
        datetime.fromisoformat(entry[GOVERNANCE_REFRESHED_AT]) for entry in entries
    ]
    return SourceRefreshWindow(
        oldest_source_refresh_at=min(instants),
        newest_source_refresh_at=max(instants),
    )


def read(booted: BootedFabric, request: ProductRequest) -> KycScenario:
    """Name this deployment's own artifact keys and read this question's values.

    Each artifact comes back under its own manifest key, already validated
    against the class the manifest declared for it — so these casts restate
    what ``load_and_boot`` already enforced. A wrong ``class_id`` in the
    manifest fails at parse, before this function runs.

    **The two instants come off the request, not off a document.** ``asked_at``
    is the boundary the graph is read as of; ``decision_instant`` is the
    class-declared parameter the TTL runs from, and ``expires_at`` derives from
    it exactly as it derived from the old ``decision.yaml``'s ``now``. Nothing
    here reads a clock: replay feeds the recorded values back through this same
    function and gets the same product.
    """
    events = cast(SignalBatch, booted.artifacts[KEY_EVENTS])
    governance = cast(
        DeclaredArtifact, booted.artifacts[KEY_PRODUCT_GOVERNANCE]
    ).declaration
    policy = cast(DeclaredArtifact, booted.artifacts[KEY_POLICY_BUNDLE]).declaration
    question = cast(DeclaredArtifact, booted.artifacts[KEY_UBO_QUESTION]).declaration
    # The projection's own operator set, authored separately from the claim the
    # product class carries. Design E2 keeps these two documents apart on
    # purpose; the binder in `spine.py` is what keeps them in agreement.
    requirements = cast(
        ProjectionRequirements, booted.artifacts[KEY_PROJECTION_REQUIREMENTS]
    )

    contract_artifact = cast(
        DeclaredArtifact, booted.artifacts[KEY_REQUEST_CONTRACT]
    )
    contract = contract_artifact.declaration
    now = datetime.fromisoformat(request.parameters[PARAM_DECISION_INSTANT])
    return KycScenario(
        artifacts=booted.artifacts,
        envelopes=events.envelopes,
        request=request,
        request_contract=ProductRequestContract(
            # The document's OWN lane — how this declaration evolved — which is
            # not the product class's lane below. Two lanes, two things
            # versioned (D-IMPL-98).
            semver=contract_artifact.semver,
            schema_name=contract[REQUEST_CONTRACT_SCHEMA_NAME],
            schema_version=contract[REQUEST_CONTRACT_SCHEMA_VERSION],
            # `ProductPayloadSchema` IS `SkillArgumentSchema` — the alias
            # `ccf.products.payload` exports, reached through the products
            # package so that a Section 1 example imports no agent surface
            # (D-IMPL-103, D-IMPL-97 ruling 1).
            arguments=ProductPayloadSchema.model_validate(
                contract[REQUEST_CONTRACT_ARGUMENTS]
            ),
        ),
        request_contract_key=governance[GOVERNANCE_REQUEST_CONTRACT_KEY],
        temporal_boundary=request.asked_at,
        now=now,
        expires_at=now + timedelta(seconds=governance[GOVERNANCE_PRODUCT_TTL_SECONDS]),
        operator_parameters={
            key: cast(OperatorParametersArtifact, booted.artifacts[key])
            for key in OPERATOR_KEYS
        },
        policy_bundle_key=KEY_POLICY_BUNDLE,
        product_class=cast(
            ProductClassDeclaration, booted.artifacts[KEY_PRODUCT_CLASS]
        ),
        plan_id=requirements.plan_id,
        required_operator_keys=requirements.required_operator_keys,
        perspective=cast(PerspectiveArtifact, booted.artifacts[KEY_PERSPECTIVE]),
        max_ttl_seconds=governance[GOVERNANCE_MAX_TTL_SECONDS],
        replay_record_class=governance[GOVERNANCE_REPLAY_RECORD_CLASS],
        query_pin_class=governance[GOVERNANCE_QUERY_PIN_CLASS],
        artifact_store_dirname=governance[GOVERNANCE_ARTIFACT_STORE_DIRNAME],
        half_life_table=cast(HalfLifeTable, booted.artifacts[KEY_HALF_LIFE_TABLE]),
        debt_profile=cast(DebtProfile, booted.artifacts[KEY_DEBT_PROFILE]),
        required_entity_classes=tuple(
            governance[GOVERNANCE_REQUIRED_ENTITY_CLASSES]
        ),
        semantic_consistency=Decimal(
            governance[GOVERNANCE_SEMANTIC_CONSISTENCY]
        ),
        # [ADAPT] Read from the document, never from a clock. Each instant is
        # authored text in `product-governance.yaml`, parsed here exactly as
        # `decision_instant` is parsed above and for the same reason: an
        # implicit YAML timestamp conversion is one nobody wrote down. The
        # zone is in the text; `SourceRefreshWindow` refuses the value outright
        # if it is not (D-IMPL-38).
        #
        # [ADAPT] THIS LINE IS WHERE THE SOURCE IDENTITIES STOP (D-IMPL-124).
        #
        # The artifact declares three entries with human-interpretable
        # references; what crosses onto the product is the WINDOW those three
        # instants span, and nothing else. No reference and no count reaches
        # the vessel, because the field's purpose is freshness rather than
        # source enumeration.
        #
        # `min` and `max` over the declared instants SELECT AMONG FACTS THIS
        # DEPLOYMENT ALREADY STATED. They manufacture nothing: no formula is
        # derived, no instant is invented, and no clock is read — which is what
        # keeps this a reduction rather than a silent default (D-IMPL-38).
        #
        # THE SDK SHIPS NO REDUCER FOR THIS, and it is not an omission. A
        # `SourceRefreshWindow.from_sources(...)` helper — or any `src/`
        # function taking per-source instants — would put a source-bearing
        # input type back on the public surface, and would make the SDK the
        # party deciding which of a deployment's sources count toward the
        # window. That the three entries below are this estate's COMPLETE set
        # is a fact only this deployment can vouch for and the SDK cannot
        # verify, so the reduction belongs here.
        source_refresh_recency=_declared_refresh_window(
            governance[GOVERNANCE_SOURCE_REFRESH_RECENCY]
        ),
        question=question,
        threshold_percent=Decimal(policy[POLICY_THRESHOLD_PERCENT]),
        scale_places=policy[POLICY_SCALE_PLACES],
    )


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
