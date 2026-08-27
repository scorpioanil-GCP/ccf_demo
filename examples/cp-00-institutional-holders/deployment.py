"""This deployment's own values — the other half of ``produce.py``.

[ADAPT] Everything here is yours to change. [MECHANISM] nothing.

``produce.py`` beside this file is CCF's calls and names none of the vocabulary
below. This file names all of it and makes no fabric call the spine does not.
**Delete ``ccf_config.yaml`` and ``artifacts/`` and nothing here has anything
left to interpret** — which is the No-Hardcoding Rule (CLAUDE.md §6.4) being
structural rather than aspirational, and it is criterion 7's subject.

**Two substrates, two functions, and they are deliberately not one.**
:func:`connection` composes the CCF **graph** backend's settings;
:func:`source_dsn` binds the read-only **system of record**. Confusing the two
is how a deployment ends up writing its fabric into the estate it reads, so
they are separate functions reading separate blocks of ``backends.yaml`` and
neither can be reached through the other.

**The threshold is applied in Π, and that is worth stating plainly.** The
compiled graph query is therefore the *same* for every threshold: what varies
with the caller's number is the payload, and hence the product's content
address — not the pinned read. The comparison is ``>=`` and not ``>``: the
class declares the parameter as the value *at or above* which a manager
appears, and the smaller example's strict ``>`` is the obvious way to get this
wrong (spec §D.3).

**Two filters on two axes are two filters.** The reported period is pinned by
the specification and applied at the source read; the threshold is chosen by
the caller and applied at Π. A third axis is deliberately **not** filtered:
``issuer_match_band`` travels with the row and is filtered nowhere, because it
is a completeness signal this product declares rather than a defect it removes
in silence (spec §C.4 trap 3). Filtering it would drop real holders and remove
no wrong-security rows.

**Step 1 of the specification's operator table runs in this file, and it is a
real operator.** :class:`DominantSecurityResolution` conforms to
``src/ccf/operators/base.py::Operator`` — key, category, declared parameter
set, and a pure ``apply`` over a view — and it declares the canonical category
``traversal``. It is example-scoped: it is registered into this deployment's
own ``src/ccf/operators/registry.py::OperatorRegistry`` and it adds no name to
the SDK. See :class:`DominantSecurityResolution` for what it ranks, what it
returns, and the one thing about it that is recorded rather than resolved.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import psycopg
import yaml

from ccf.assembly.worker import EntityResolutionSpec
from ccf.contracts.canonical import content_hash
from ccf.contracts.claims import EntityClaim, LineageEntry, RelationshipClaim
from ccf.controlplane.artifacts import (
    DebtProfile,
    HalfLifeTable,
    OperatorParametersArtifact,
    PerspectiveArtifact,
    ProductClassDeclaration,
)
from ccf.deployment import BootedFabric
from ccf.graph.protocols import EntityRecord, GraphView, RelationshipRecord
from ccf.halflife.assessment import DebtAssessment, DebtFactors
from ccf.halflife.debt import FreshnessScorer, assess_debt
from ccf.halflife.decay import Observation
from ccf.operators.base import (
    OperatorOutput,
    OperatorParameters,
    OperatorProvenance,
    mint_provenance,
)
from ccf.operators.registry import OperatorRegistry
from ccf.products.request import ProductRequest, ProductRequestContract
from ccf.projection.plan import Perspective, ProjectionOutput
from ccf.signal.envelope import SignalEnvelope, SourceIdentity

HERE = Path(__file__).parent
ARTIFACTS = HERE / "artifacts"
#: The single authored Control Plane document (`D-IMPL-136`'s AMENDMENT).
CONFIG = HERE / "ccf_config.yaml"
BACKENDS = HERE / "backends.yaml"
QUESTION = ARTIFACTS / "question.yaml"
TTL = ARTIFACTS / "ttl.yaml"
#: The specification this deployment realises. Printed by `run.py`, read from
#: here so the path is written down once.
SPEC = HERE / "spec" / "CP-SPEC-000-institutional-holders.md"

# --- This deployment's Control Plane vocabulary. These are the manifest keys
#     `derive_deployment` derives from `ccf_config.yaml`'s own section names,
#     and this is the only place they are written down.
KEY_PERSPECTIVE = "default_perspective"
KEY_PRODUCT_CLASS = "product_class"
KEY_REQUEST_CONTRACT = "request_contract"
KEY_RESOLUTION = "resolution"
KEY_HALF_LIFE_TABLE = "half_life"
KEY_DEBT_PROFILE = "debt_profile"
KEY_POLICY_BUNDLE = "policy"
#: An `operators:` entry's key is the operator id itself.
KEY_POLICY_OPERATOR = "policy.principal-subgraph"
KEY_TEMPORAL_OPERATOR = "temporal.as-of-boundary"

#: The declared request parameter the caller supplies. Declared REQUIRED in
#: `ccf_config.yaml`'s `request_contract:` section; nothing in this tree
#: defaults it, and the demonstration's fallback lives in
#: `artifacts/question.yaml` rather than here.
THRESHOLD_PARAMETER = "minimum_position_usd"

# --- THIS DEPLOYMENT'S SOURCE VOCABULARY — the system of record it reads. NOT
#     CCF's. These name a schema, two tables and their columns; an adopter
#     replaces them with their own estate's.
SOURCE_SCHEMA = "ccf_v2"
TABLE_HOLDINGS = "institutional_holder"
TABLE_ENTITY = "legal_entity"
COLUMN_ISSUER_LEI = "lei"
COLUMN_MANAGER_CIK = "manager_cik"
COLUMN_MANAGER_NAME = "manager_name"
COLUMN_CUSIP = "cusip"
COLUMN_VALUE = "value_usd"
COLUMN_SHARES = "shares"
COLUMN_PERIOD = "report_period"
COLUMN_MATCH_SCORE = "issuer_match_score"
COLUMN_MATCH_BAND = "issuer_match_band"
COLUMN_PROVENANCE = "provenance"
COLUMN_REGISTERED_NAME = "legal_name"
#: The source spells its reported period this way, so the parse does too. The
#: parse happens in the READ, not in this process: the estate's own date
#: function is the authority on its own text format.
PERIOD_FORMAT = "DD-MON-YYYY"

# --- How a source row's fields are named once they are inside the fabric.
#     Every key below appears in `ccf_config.yaml`'s `resolution:` section; a
#     key that differs here is a silently missing attribute, and a missing
#     attribute moves C_attributes.
ATTR_ISSUER_REF = "issuer_ref"
ATTR_ISSUER_LEI = "issuer_lei"
ATTR_ISSUER_NAME = "issuer_registered_name"
ATTR_MANAGER_REF = "manager_ref"
ATTR_MANAGER_CIK = "manager_cik"
ATTR_MANAGER_NAME = "manager_name"
ATTR_VALUE = "position_value_usd"
ATTR_SHARES = "position_shares"
ATTR_PERIOD = "report_period"
ATTR_CUSIP = "resolved_cusip"
ATTR_MATCH_BAND = "issuer_match_band"
ATTR_MATCH_SCORE = "issuer_match_score"
ATTR_PROVENANCE = "provenance_class"

#: The two entity classes `ccf_config.yaml`'s `resolution:` section declares.
CLASS_ISSUER = "issuer"
CLASS_MANAGER = "institutional_manager"

#: The λ_c entry in `ccf_config.yaml`'s `half_life:` section these rows decay
#: by. One observation type: a filed position.
OBSERVATION_TYPE = "reported_position"

#: The band value C_match counts. The other band is served, not filtered.
BAND_STRONG = "strong"

#: What this product says instead of dropping a non-mandatory field, declared
#: in `artifacts/expected.yaml` as `not_evaluable_marker`.
NOT_EVALUABLE = "NOT_EVALUABLE"

#: The comparison the payload declares, so a consumer never has to infer it.
COMPARISON = ">="

# --- Step 1's operator: its registry identity, the class and edge type its
#     candidate rendering uses, and the basis it ranks on. The basis is
#     DECLARED rather than implied, because "dominant" is ambiguous until
#     something says by what.
OPERATOR_DOMINANT_SECURITY = "traversal.dominant-security"
CLASS_SECURITY = "security"
RELATIONSHIP_REPORTS = "reports_position_in"
RESOLUTION_BASIS = "dominant-by-position-count"
ATTR_SECURITY_CUSIP = "cusip"

# --- Where a run's own state goes, and under which artifact classes.
REPLAY_RECORD_CLASS = "cp-00.replay-record"
QUERY_PIN_CLASS = "cp-00.graph-query"
ARTIFACT_STORE_DIRNAME = "artifacts-store"

# --- `backends.yaml` vocabulary: the value sources, and nothing else.
DECLARATION = "declaration"
PROFILES = "profiles"
SOURCES = "sources"
SETTINGS = "settings"
FROM_ENV = "from_env"
PER_RUN = "per_run"
PREFIX = "prefix"
SUFFIX = "suffix"
REMEDY = "remedy"
SOURCE_BINDING = "institutional_holdings"
SOURCE_SETTING_DSN = "dsn"


def _document(path: Path) -> Mapping[str, Any]:
    """One of this deployment's own YAML documents, parsed."""
    return cast(Mapping[str, Any], yaml.safe_load(path.read_text(encoding="utf-8")))


def _declaration(path: Path) -> Mapping[str, Any]:
    """The `declaration:` body of one declared artifact."""
    return cast(Mapping[str, Any], _document(path)[DECLARATION])


def _from_environment(source: Mapping[str, Any], *, setting: str) -> str:
    """Read one declared environment variable, or raise with its own remedy.

    There is no default and no fallback to another value. A remedy string the
    artifact wrote is what an operator reads when the variable is unset —
    which is the only reason `backends.yaml` can hold a variable NAME and
    nothing else.
    """
    variable = source[FROM_ENV]
    value = os.environ.get(variable, "")
    if not value:
        raise RuntimeError(
            f"{variable} is unset; {source[REMEDY]}. It supplies `{setting}`,"
            " which backends.yaml declares this deployment reads from the"
            " environment. There is no default and no fallback."
        )
    return value


# --------------------------------------------------------------------------
# Where the graph lives — composed, never written down.
# --------------------------------------------------------------------------
def connection(*, root: Path) -> Mapping[str, str]:
    """Compose the declared backend kind's settings.

    The only branch here is over the value SOURCES ``backends.yaml`` declares,
    never over a substrate name: ``ccf_config.yaml`` declares the KIND (its
    top-level ``backend:``) and ``backends.yaml`` says how that kind's settings
    are composed. No host, port, path or credential is read from any document —
    only a variable's name, or a per-run recipe composed under ``root``.

    This function reaches the ``profiles:`` block and nothing else. The system
    of record is :func:`source_dsn`'s business and the two cannot be confused.
    """
    kind = _document(CONFIG)["backend"]
    profiles = _declaration(BACKENDS)[PROFILES]
    settings: Mapping[str, Any] = profiles[kind][SETTINGS]
    composed: dict[str, str] = {}
    for setting, source in settings.items():
        if FROM_ENV in source:
            composed[setting] = _from_environment(source, setting=setting)
        else:
            name = f"{source[PREFIX]}_{uuid.uuid4().hex}{source[SUFFIX]}"
            composed[setting] = str(root / name)
    return composed


def source_dsn() -> str:
    """Bind the read-only system of record, from its declared variable NAME.

    A separate function from :func:`connection`, reading a separate block, so
    that the graph's composition and the source binding are two things a
    reader can tell apart. Nothing this deployment runs writes to the store
    this value reaches (spec §C.3).
    """
    sources = _declaration(BACKENDS)[SOURCES]
    return _from_environment(
        sources[SOURCE_BINDING][SETTINGS][SOURCE_SETTING_DSN],
        setting=SOURCE_SETTING_DSN,
    )


# --------------------------------------------------------------------------
# The question the caller asks.
# --------------------------------------------------------------------------
def tenant_id() -> str:
    """The tenant this deployment runs as, from its own configuration."""
    return str(_document(CONFIG)["tenant_id"])


def perspective() -> Perspective:
    """The Π role-conditioning this product is served under.

    Read from ``ccf_config.yaml``'s ``default_perspective:`` section, which is
    the same document the fabric registers the artifact from. A caller needs
    this *before* the fabric boots — the assembler seam takes it as an
    argument — so it is read here rather than off the booted registry, and the
    assembler cross-checks the two afterwards.
    """
    declared = _document(CONFIG)[KEY_PERSPECTIVE]
    return Perspective(
        principal_id=str(declared["principal_id"]), role=str(declared["role"])
    )


def request(
    *, parameters: Mapping[str, object], asked_at: datetime | None = None
) -> ProductRequest:
    """Build the typed question from the caller's parameters and this
    deployment's declared vocabulary.

    The four address tokens come from ``artifacts/question.yaml`` and the class
    identity from ``ccf_config.yaml``'s ``product_class:`` section.
    ``parameters`` is the CALLER's — this function supplies no value for it and
    no default, which is what keeps the contract's requirement real.
    """
    question = _declaration(QUESTION)
    declared = _document(CONFIG)[KEY_PRODUCT_CLASS]
    return ProductRequest(
        schema_name=declared["schema_name"],
        schema_version=declared["schema_version"],
        subject=question["subject"],
        intent=question["intent"],
        freshness=question["freshness"],
        asked_at=asked_at or datetime.fromisoformat(question["asked_at"]),
        parameters=parameters,
    )


def demonstration_threshold() -> int:
    """The threshold the bundled demonstration asks, from scenario material.

    A CLI convenience, never a contract obligation: the class declares the
    parameter REQUIRED with no default, and a request omitting it is refused as
    data before the graph is touched.
    """
    return int(_declaration(QUESTION)["demonstration"][THRESHOLD_PARAMETER])


def reported_period() -> str:
    """The pinned reported period, spelled as the source spells it."""
    return str(_declaration(QUESTION)[COLUMN_PERIOD])


# --------------------------------------------------------------------------
# Step 1 of the specification's operator table — the dominant security.
# --------------------------------------------------------------------------
class DominantSecurityParameters(OperatorParameters):
    """What :class:`DominantSecurityResolution` was configured with.

    Fields, never defaults, on the base's own discipline: the parameter set's
    ``content_hash`` is what pins this operator's behaviour into the provenance
    chain, so a value the SDK picked would pin a decision nobody made.

    ``resolution_basis`` is declared rather than implied. *Dominant* is
    ambiguous until something says by what, and this product's answer — the
    security carrying the most filed positions for the anchor and period — is
    the value that reaches the payload as ``resolved_security.resolution_basis``.
    """

    security_entity_class: str
    holding_relationship_type: str
    resolution_basis: str


@dataclass(frozen=True)
class DominantSecurityResolution:
    """Rank an issuer's candidate securities and return the winner's subgraph.

    Step 1 of the specification's §D.2 table, and it is **an operator** —
    `24-CONTEXT.md` `D-47` (Dave, 2026-08-26): *"You must specify an operator —
    deterministic, etc. — you cannot not have an operator."* It conforms to
    ``src/ccf/operators/base.py::Operator`` structurally, declares the
    canonical category ``traversal``, and is **example-scoped**: it is
    registered into this deployment's own
    ``src/ccf/operators/registry.py::OperatorRegistry`` and adds no name to the
    SDK. ``src/ccf/operators/base.py::OperatorCategory`` stays the closed four;
    a new operator NAME under an existing category is additive.

    **What it ranks, and why that fits a view-to-view function.** The anchor
    issuer fans out across several candidate securities in one reported period,
    and only one of them is the security the question is about. The ranking is
    a bounded expansion over the holdings edges of the candidate rendering this
    deployment builds at the source boundary, and the ranking is **expressed as
    the subgraph it returns**: the winning security, the edges that reach it,
    and the managers on those edges.

    **Being deterministic is no obstacle to being an operator, and the base
    says so.** ``src/ccf/operators/base.py::Operator`` states that
    *"realization is unconstrained ... the algebra is the determinism
    surface, and conformance to this Protocol is the whole obligation"* — so a
    deterministic computation is exactly what the Protocol is for, and there
    was never a tension to resolve. The one shape the Protocol does fix is the
    RESULT's: ``apply`` returns a view, so an operator cannot emit a SCALAR.
    *Which security is dominant* is a SELECTION rather than a measure, and a
    selection is a view by construction. (The place that shape genuinely bites
    is the Standard's ``Evaluate`` — see
    :class:`HoldersOverThresholdProjection` — and the two are separate facts.)

    **Deterministic, and the tie-break is stated.** Highest number of holdings
    edges wins; equal counts are broken by the security's URI ascending. A rank
    with an unstated tie-break is a rank that can return two answers for one
    input, and this product's payload hash depends on it not doing that.

    **What is recorded and not resolved.** This operator does not appear in the
    served product's ``lineage.operators_invoked``, because it does not run
    inside the projection's operator plan — see :func:`source_read` for the
    measurement behind that sentence. Its runtime witness is the payload's
    ``resolved_security`` block, which is exactly the witness
    ``artifacts/assembly-recipe.yaml`` declares for this step.
    """

    parameters: DominantSecurityParameters

    @property
    def key(self) -> str:
        return OPERATOR_DOMINANT_SECURITY

    @property
    def category(self) -> str:
        """``traversal`` — a bounded expansion over holdings edges."""
        return "traversal"

    def apply(
        self,
        *,
        view: GraphView,
        tenant_id: str,
        temporal_boundary: datetime,
        upstream: tuple[OperatorProvenance, ...],
    ) -> OperatorOutput:
        """Return the winning security's subgraph, with its provenance.

        Pure: no writes, no I/O, no clock read. ``view`` is a frozen value and
        the return is a new one.
        """
        securities = {
            record.claim.entity_uri: record
            for record in view.entities
            if record.claim.entity_class == self.parameters.security_entity_class
        }
        edges = [
            record
            for record in view.relationships
            if record.claim.relationship_type
            == self.parameters.holding_relationship_type
            and record.claim.object_uri in securities
        ]
        if not securities:
            raise ValueError(
                f"{self.key} was applied to a view carrying no"
                f" {self.parameters.security_entity_class!r} entity; an anchor"
                " that resolves to no security is a fail-closed condition, not"
                " an empty answer (spec §D.2 step 1)"
            )
        counted = {uri: 0 for uri in securities}
        for edge in edges:
            counted[edge.claim.object_uri] += 1
        # Highest count wins; equal counts break on the URI ascending, so the
        # answer is a function of the input and not of the iteration order.
        winner = min(counted, key=lambda uri: (-counted[uri], uri))
        kept = [edge for edge in edges if edge.claim.object_uri == winner]
        holders = {edge.claim.subject_uri for edge in kept}
        return OperatorOutput(
            view=GraphView(
                tenant_id=view.tenant_id,
                as_of=view.as_of,
                entities=tuple(
                    record
                    for record in view.entities
                    if record.claim.entity_uri == winner
                    or record.claim.entity_uri in holders
                ),
                relationships=tuple(kept),
            ),
            provenance=mint_provenance(cast(Any, self), upstream=upstream),
        )


@dataclass(frozen=True)
class ResolvedSecurity:
    """Step 1's output, as the payload carries it."""

    cusip: str
    candidates_considered: int
    resolution_basis: str


@dataclass(frozen=True)
class SourceRead:
    """One read of the system of record: what it resolved, and what it emits."""

    resolved_security: ResolvedSecurity
    envelopes: tuple[SignalEnvelope, ...]


# --------------------------------------------------------------------------
# L1 — the signal, read from the source system.
# --------------------------------------------------------------------------
def _rows(dsn: str, *, subject: str, period: str) -> list[tuple[Any, ...]]:
    """Every filed position for the anchor at the pinned period, ordered.

    ONE read, pinned on the two axes the specification fixes and filtered on no
    third: the reported period is pinned because the archive restates
    historical periods and an unpinned read silently mixes a decade of
    positions into one answer, and ``issuer_match_band`` is deliberately NOT
    filtered — it travels with the row (spec §C.4 traps 1 and 3).

    The threshold is not here and never will be. Every threshold compiles to
    this same read, which is what makes "the rows assembled" one well-defined
    set rather than a per-caller one — and it is what the freshness figure in
    :meth:`HoldersScenario.debt` is measured over.

    Ordered by the remainder of the source's primary key, so two runs read the
    same rows in the same order.
    """
    with psycopg.connect(dsn) as db:
        db.read_only = True
        with db.cursor() as cursor:
            cursor.execute(  # noqa: S608 — names come from this module's block
                f"select h.{COLUMN_MANAGER_CIK}, h.{COLUMN_MANAGER_NAME},"
                f" h.{COLUMN_CUSIP}, h.{COLUMN_VALUE}, h.{COLUMN_SHARES},"
                f" h.{COLUMN_PERIOD}, h.{COLUMN_MATCH_SCORE},"
                f" h.{COLUMN_MATCH_BAND}, h.{COLUMN_PROVENANCE},"
                f" e.{COLUMN_REGISTERED_NAME},"
                f" to_date(h.{COLUMN_PERIOD}, '{PERIOD_FORMAT}')"
                f" from {SOURCE_SCHEMA}.{TABLE_HOLDINGS} h"
                f" left join {SOURCE_SCHEMA}.{TABLE_ENTITY} e"
                f" on e.{COLUMN_ISSUER_LEI} = h.{COLUMN_ISSUER_LEI}"
                f" where h.{COLUMN_ISSUER_LEI} = %s"
                f" and h.{COLUMN_PERIOD} = %s"
                f" order by h.{COLUMN_MANAGER_CIK}, h.{COLUMN_CUSIP}",
                (subject, period),
            )
            return cast("list[tuple[Any, ...]]", cursor.fetchall())


def _instant(value: date) -> datetime:
    """The source's own date, as the instant the fabric's T axis reads."""
    return datetime(value.year, value.month, value.day, tzinfo=UTC)


def _candidate_view(
    rows: Sequence[tuple[Any, ...]],
    *,
    tenant: str,
    at: datetime,
    observed: datetime,
    policy_bundle_version: str,
) -> GraphView:
    """Render the read as the candidate graph step 1's operator ranks.

    **This is a source-boundary rendering, not the fabric's state.** Nothing
    here has been through L2 and nothing here reaches L3; it is a value built
    so that step 1 can be an operator — a pure view-to-view function — rather
    than an ad-hoc loop. The fabric's own assembled state is built later, by
    the single writer, from the envelopes this read emits.

    ``policy_bundle_version`` is the deployment's own pinned bundle, passed in
    rather than invented: the P axis on a record is the bundle in force, and
    this rendering runs under the same one the fabric will stamp its claims
    with.
    """
    securities: dict[str, EntityRecord] = {}
    managers: dict[str, EntityRecord] = {}
    edges: list[RelationshipRecord] = []
    for cik, _name, cusip, *_rest in rows:
        security_uri = f"{CLASS_SECURITY}://{content_hash({ATTR_SECURITY_CUSIP: str(cusip)})}"
        manager_uri = f"{CLASS_MANAGER}://{content_hash({ATTR_MANAGER_CIK: str(cik)})}"
        lineage = frozenset(
            {
                LineageEntry(
                    source=SourceIdentity(system_id=TABLE_HOLDINGS),
                    envelope_id=_envelope_id(cik=str(cik), cusip=str(cusip)),
                    observed_at=at,
                )
            }
        )
        if security_uri not in securities:
            claim = EntityClaim(
                tenant_id=tenant,
                observed_at=at,
                valid_from=observed,
                lineage=lineage,
                entity_uri=security_uri,
                entity_class=CLASS_SECURITY,
                attributes={ATTR_SECURITY_CUSIP: str(cusip)},
            )
            securities[security_uri] = EntityRecord(
                claim_id=content_hash(claim),
                claim=claim,
                policy_bundle_version=policy_bundle_version,
            )
        if manager_uri not in managers:
            claim = EntityClaim(
                tenant_id=tenant,
                observed_at=at,
                valid_from=observed,
                lineage=lineage,
                entity_uri=manager_uri,
                entity_class=CLASS_MANAGER,
                attributes={ATTR_MANAGER_CIK: str(cik)},
            )
            managers[manager_uri] = EntityRecord(
                claim_id=content_hash(claim),
                claim=claim,
                policy_bundle_version=policy_bundle_version,
            )
        edge = RelationshipClaim(
            tenant_id=tenant,
            observed_at=at,
            valid_from=observed,
            lineage=lineage,
            relationship_type=RELATIONSHIP_REPORTS,
            subject_uri=manager_uri,
            object_uri=security_uri,
        )
        edges.append(
            RelationshipRecord(
                relationship_key=content_hash(
                    {
                        "type": RELATIONSHIP_REPORTS,
                        "subject": manager_uri,
                        "object": security_uri,
                    }
                ),
                claim_id=content_hash(edge),
                claim=edge,
                policy_bundle_version=policy_bundle_version,
            )
        )
    return GraphView(
        tenant_id=tenant,
        as_of=at,
        entities=tuple(securities.values()) + tuple(managers.values()),
        relationships=tuple(edges),
    )


def _envelope_id(*, cik: str, cusip: str) -> str:
    """One envelope per filed position, addressed by the source's own key."""
    return f"{TABLE_HOLDINGS}/{cik}/{cusip}"


def source_read(
    tenant: str, *, at: datetime, subject: str, policy_bundle_version: str
) -> SourceRead:
    """Read the estate once, resolve the security, and emit L1 envelopes.

    **The order matters and it is step 1 followed by step 2.** The read is
    rendered as a candidate graph, :class:`DominantSecurityResolution` ranks it
    and returns the winner's subgraph, and only the rows on that security
    become envelopes. Canonical entity resolution then happens at L2, one
    envelope at a time, inside the single writer.

    **Registration is real, not decorative.** The operator is registered into
    an ``src/ccf/operators/registry.py::OperatorRegistry`` and resolved back out
    of it before it is applied, so the registry's duplicate-key and
    category checks actually run over it.

    **What this deployment measured and recorded rather than worked around.**
    ``src/ccf/deployment/operators.py::build_operator_registry`` — the builder
    the spine calls — maps a *declared parameter artifact* onto an SDK operator
    class and raises for any artifact type it does not recognise, so there is
    no path by which a deployment's own operator reaches the registry the
    projection plan resolves against. The registry itself is open;
    the composition path in front of it is not. This deployment therefore
    registers its operator into its own registry, at the layer the
    specification places step 1 — the source boundary — and the served
    lineage still names exactly the two operators the product class declares.
    Recorded in this wave's summary as an SDK finding; nothing in ``src/`` was
    changed to accommodate it.
    """
    period = reported_period()
    rows = _rows(source_dsn(), subject=subject, period=period)
    if not rows:
        raise RuntimeError(
            f"the source holds no filed position for {subject!r} at"
            f" {period!r}; an anchor that resolves to nothing is a fail-closed"
            " condition (spec §D.2 step 1), never an empty answer"
        )
    # The parsed period is the LAST column of the select above, and it is
    # the same value on every row: the read is pinned to one period.
    observed = _instant(rows[0][-1])

    registry = OperatorRegistry()
    registry.register(
        cast(
            Any,
            DominantSecurityResolution(
                parameters=DominantSecurityParameters(
                    security_entity_class=CLASS_SECURITY,
                    holding_relationship_type=RELATIONSHIP_REPORTS,
                    resolution_basis=RESOLUTION_BASIS,
                )
            ),
        )
    )
    resolver = cast(Any, registry.resolve(OPERATOR_DOMINANT_SECURITY))
    candidates = _candidate_view(
        rows,
        tenant=tenant,
        at=at,
        observed=observed,
        policy_bundle_version=policy_bundle_version,
    )
    ranked = resolver.apply(
        view=candidates, tenant_id=tenant, temporal_boundary=at, upstream=()
    )
    resolved = ResolvedSecurity(
        cusip=next(
            record.claim.attributes[ATTR_SECURITY_CUSIP]
            for record in ranked.view.entities
            if record.claim.entity_class == CLASS_SECURITY
        ),
        candidates_considered=sum(
            1
            for record in candidates.entities
            if record.claim.entity_class == CLASS_SECURITY
        ),
        resolution_basis=RESOLUTION_BASIS,
    )
    return SourceRead(
        resolved_security=resolved,
        envelopes=_envelopes(
            rows,
            tenant=tenant,
            at=at,
            observed=observed,
            subject=subject,
            resolved=resolved,
        ),
    )


def _envelopes(
    rows: Sequence[tuple[Any, ...]],
    *,
    tenant: str,
    at: datetime,
    observed: datetime,
    subject: str,
    resolved: ResolvedSecurity,
) -> tuple[SignalEnvelope, ...]:
    """One L1 envelope per filed position on the resolved security.

    **``observed_time`` is the reported quarter end, never this run's clock,
    and that single mapping is what the whole freshness story turns on.** It
    becomes the claim's ``valid_from`` — when the *source's* fact began to hold
    — which is what the λ_c curve reads. A column a plain ``SELECT`` ignores
    becomes a measured D_c. The quarter-end coarseness is a property of the
    filing regime, not a data defect: the archive reports per period and this
    product anchors on that period.

    ``ingestion_timestamp`` is the request instant, so the as-of boundary the
    caller asked at is at or after every claim's ``observed_at``. A boundary
    set to the reported quarter end instead — the natural mistake after reading
    the TTL anchor — would empty the view while every shipped gate passed.

    Every ``raw_payload`` value is a string: decimals and dates are stringified
    at this boundary, because canonical bytes refuse a float and the payload is
    the source's vocabulary rather than the fabric's.
    """
    emitted: list[SignalEnvelope] = []
    for cik, name, cusip, value, shares, period, score, band, prov, legal, _d in rows:
        if str(cusip) != resolved.cusip:
            continue
        payload: dict[str, str] = {
            ATTR_ISSUER_REF: subject,
            ATTR_ISSUER_LEI: subject,
            ATTR_MANAGER_REF: str(cik),
            ATTR_MANAGER_CIK: str(cik),
            ATTR_VALUE: str(value),
            ATTR_PERIOD: str(period),
            ATTR_CUSIP: str(cusip),
            ATTR_MATCH_SCORE: str(score),
            ATTR_PROVENANCE: str(prov),
        }
        # A non-mandatory field the source did not carry is ABSENT from the
        # payload rather than blank. `SpecDrivenEntityResolution` copies the
        # keys it finds, so an absent key is a real completeness shortfall
        # C_attributes counts — a blank string would be a value that measured
        # as present.
        for key, source_value in (
            (ATTR_ISSUER_NAME, legal),
            (ATTR_MANAGER_NAME, name),
            (ATTR_SHARES, shares),
            (ATTR_MATCH_BAND, band),
        ):
            if source_value is not None:
                payload[key] = str(source_value)
        emitted.append(
            SignalEnvelope(
                tenant_id=tenant,
                envelope_id=_envelope_id(cik=str(cik), cusip=str(cusip)),
                source=SourceIdentity(system_id=TABLE_HOLDINGS),
                ingestion_timestamp=at,
                observed_time=observed,
                raw_payload=payload,
            )
        )
    return tuple(emitted)


def envelopes(
    tenant: str, *, at: datetime, subject: str, policy_bundle_version: str
) -> tuple[SignalEnvelope, ...]:
    """The L1 signal this run ingests — :func:`source_read`'s envelopes.

    The named entry point the rest of the suite uses. It discards the resolved
    security, so a caller that needs step 1's output calls :func:`source_read`
    once instead of calling this twice.
    """
    return source_read(
        tenant, at=at, subject=subject, policy_bundle_version=policy_bundle_version
    ).envelopes


# --------------------------------------------------------------------------
# What one run needs — satisfies `produce.Scenario` structurally.
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class HoldersScenario:
    """This deployment's answers to what the spine asks for."""

    envelopes: tuple[SignalEnvelope, ...]
    request: ProductRequest
    request_contract: ProductRequestContract
    product_class: ProductClassDeclaration
    perspective: PerspectiveArtifact
    operator_parameters: Mapping[str, OperatorParametersArtifact]
    resolution: EntityResolutionSpec
    half_life_table: HalfLifeTable
    debt_profile: DebtProfile
    resolved_security: ResolvedSecurity
    report_period: str
    ttl_seconds: int
    max_ttl_seconds: int
    halflife_debt_profile: str

    request_contract_key: str = KEY_REQUEST_CONTRACT
    policy_bundle_key: str = KEY_POLICY_BUNDLE
    replay_record_class: str = REPLAY_RECORD_CLASS
    query_pin_class: str = QUERY_PIN_CLASS
    artifact_store_dirname: str = ARTIFACT_STORE_DIRNAME

    @property
    def plan_id(self) -> str:
        return self.product_class.schema_name

    @property
    def temporal_boundary(self) -> datetime:
        """Off the request, never off a clock — so replay feeds it back."""
        return self.request.asked_at

    @property
    def now(self) -> datetime:
        return self.request.asked_at

    @property
    def expires_at(self) -> datetime:
        """The declared TTL applied to the anchor the class names.

        ``ttl_anchor`` is ``from_entity_freshness``, so the anchor is the
        REPORTED QUARTER END and not the request instant: what makes this
        answer wrong is a restatement of that period, which is why the duration
        is the amendment window rather than the filing cycle. Both numbers come
        from ``artifacts/ttl.yaml``; neither is a constant in this module.
        """
        return self._anchor + timedelta(seconds=self.ttl_seconds)

    @property
    def _anchor(self) -> datetime:
        """The reported quarter end, from what the assembled claims carry."""
        return min(envelope.observed_time for envelope in self.envelopes)  # type: ignore[type-var]

    def _declared_attributes(self) -> tuple[str, ...]:
        """What a served row must carry, from the resolution spec itself.

        Read off ``ccf_config.yaml``'s ``resolution:`` section rather than
        listed here, so C_attributes counts the attributes the deployment
        actually declared. The identity keys are excluded: a row missing one
        produced no entity to count, so it is a fail-closed condition rather
        than a completeness shortfall.
        """
        for rule in self.resolution.entity_rules:
            if rule.entity_class == CLASS_MANAGER:
                return tuple(
                    key
                    for key in rule.attribute_keys
                    if key not in set(rule.identity_keys)
                )
        return ()

    def debt(self, view: GraphView) -> DebtAssessment:
        """D_c over what this question assembled (whitepaper §7.7).

        Four decisions, each stated rather than left for a reader to infer.

        **F is measured over the rows ASSEMBLED, not the rows SELECTED by the
        caller's threshold.** ``src/ccf/halflife/debt.py::FreshnessScorer``
        refuses an empty sequence by design, so scoring the survivors would
        make a threshold that admits nobody RAISE instead of answering — and
        the honest answer to an impossibly high number is *"nobody."* Freshness
        describes what the fabric read; completeness describes what survived
        being read. This is only coherent because the read is
        threshold-independent (see :func:`_rows`).

        **Decay is measured from ``valid_from``, not from ``observed_at``.**
        The T axis is bitemporal: ``observed_at`` is when the *fabric* learned
        a claim and ``valid_from`` is when the *source's* fact began to hold.
        Scoring ``observed_at`` would measure the age of this run, so a
        two-year-old filing re-read a moment ago would score as perfectly
        fresh — a source outage laundered into a low-debt reading, which is the
        precise failure the fail-closed posture exists to prevent.

        **C is over the resolution spec's declared attributes**, decomposed
        into two components because this product has two different
        incompletenesses: ``C_attributes`` over the declared attribute keys,
        and ``C_match`` over the rows whose issuer match is ``strong``. The
        weakly matched rows are SERVED, so they are a shortfall this product
        declares rather than a boundary it draws — and multiplying the two into
        one number without saying so would hide both.

        **S is 1, and the reason is stated rather than left as a magic
        constant:** there is exactly one source here, and a single source
        cannot disagree with itself. That is the honest setup for a later
        product where debt only becomes interesting once assembly spans sources
        that do disagree.
        """
        rows = [
            record
            for record in view.entities
            if record.claim.entity_class == CLASS_MANAGER
        ]
        observations = tuple(
            Observation(
                observation_type=OBSERVATION_TYPE,
                observed_at=record.claim.valid_from,
                subject=record.claim.entity_uri,
            )
            for record in rows
        )
        expected = self._declared_attributes()
        complete = sum(
            1
            for record in rows
            if all(record.claim.attributes.get(key) for key in expected)
        )
        matched = sum(
            1
            for record in rows
            if record.claim.attributes.get(ATTR_MATCH_BAND) == BAND_STRONG
        )
        total = Decimal(len(rows))
        scorer = FreshnessScorer(
            table=self.half_life_table,
            risk_sensitivity=self.debt_profile.risk_sensitivity,
        )
        return assess_debt(
            DebtFactors(
                freshness=scorer.score(observations, now=self.now),
                completeness=(Decimal(complete) / total) * (Decimal(matched) / total),
                semantic_consistency=Decimal(1),
            ),
            profile=self.debt_profile,
        )


def read(booted: BootedFabric, asked: ProductRequest) -> HoldersScenario:
    """Name this deployment's artifact keys and read this question's values."""
    artifacts = booted.artifacts
    ttl = _declaration(TTL)
    policy_bundle_version = booted.pins.version_for(KEY_POLICY_BUNDLE)
    read_source = source_read(
        booted.tenant_id,
        at=asked.asked_at,
        subject=asked.subject,
        policy_bundle_version=policy_bundle_version,
    )
    return HoldersScenario(
        envelopes=read_source.envelopes,
        resolved_security=read_source.resolved_security,
        report_period=reported_period(),
        request=asked,
        request_contract=ProductRequestContract.from_declared(
            cast(Any, artifacts[KEY_REQUEST_CONTRACT])
        ),
        product_class=cast(ProductClassDeclaration, artifacts[KEY_PRODUCT_CLASS]),
        perspective=cast(PerspectiveArtifact, artifacts[KEY_PERSPECTIVE]),
        # TWO entries, so two operators. The spine never counts them.
        operator_parameters={
            key: cast(OperatorParametersArtifact, artifacts[key])
            for key in (KEY_POLICY_OPERATOR, KEY_TEMPORAL_OPERATOR)
        },
        resolution=cast(EntityResolutionSpec, artifacts[KEY_RESOLUTION]),
        half_life_table=cast(HalfLifeTable, artifacts[KEY_HALF_LIFE_TABLE]),
        debt_profile=cast(DebtProfile, artifacts[KEY_DEBT_PROFILE]),
        ttl_seconds=int(ttl["declared_ttl_seconds"]),
        max_ttl_seconds=int(ttl["max_ttl_seconds"]),
        # A pinned reference, never the resolved artifact: the profile has its
        # own version lane, and inlining it would give one record two version
        # identities. The pin is a content hash of what was registered.
        halflife_debt_profile=(
            f"ccf-artifact://{booted.tenant_id}/ccf.debt-profile/"
            f"{KEY_DEBT_PROFILE}@{booted.pins.version_for(KEY_DEBT_PROFILE)}"
        ),
    )


# --------------------------------------------------------------------------
# Π — the projection.
# --------------------------------------------------------------------------
class HoldersOverThresholdProjection:
    """Keep the managers whose reported position is at or above the caller's
    number, and rank them.

    **The threshold is applied HERE**, at Π, and never in the graph query. The
    consequence is worth being explicit about: every threshold compiles to the
    same pinned read, so what the caller's number changes is the *payload* —
    and therefore the product's content address — rather than what was read.
    That is also what makes the assembled state identical across callers, which
    is the whole basis of the materialization optimisation the specification
    names.

    **The comparison is ``>=``.** The class declares the parameter as the value
    at or above which a manager appears, so a manager whose position equals the
    caller's number is served. The smaller example's strict ``>`` is not
    inherited.

    **This is also where the Standard's ``Evaluate`` lives**, and the reason is
    a RESULT SHAPE rather than a determinism one.
    ``src/ccf/operators/base.py::Operator.apply`` returns a view plus
    provenance, so an operator cannot emit a SCALAR — and ``Evaluate``'s modes
    (aggregate, score, reconcile, rank into a measure) all produce numbers.
    Computation that produces measures rather than graph state therefore runs
    here. Step 1's operator is not the same case: *which security is dominant*
    is a subgraph selection, which is why it has an operator home and
    ``Evaluate`` does not.

    **One key this payload deliberately does not carry.** The count of rows the
    fabric read is absent: a read count published beside a served count IS the
    below-threshold count by subtraction, and this product is committed to
    being silent about what fell below the caller's line. The assembled count
    is still needed as freshness's denominator — it lives in the governed debt
    block instead.
    """

    def __init__(
        self, *, plan_id: str, required: tuple[str, ...], scenario: Any
    ) -> None:
        self._plan_id = plan_id
        self._required = required
        self._scenario = scenario

    @property
    def plan_id(self) -> str:
        return self._plan_id

    def required_operators(self) -> tuple[str, ...]:
        """From the product class's own document — the one authored set."""
        return self._required

    def invoke(
        self,
        *,
        view: GraphView,
        operator_outputs: Mapping[str, Any],
        perspective: Perspective,
        temporal_boundary: datetime,
    ) -> ProjectionOutput:
        threshold = Decimal(str(self._scenario.request.parameters[THRESHOLD_PARAMETER]))
        holders = sorted(
            (
                {
                    ATTR_MANAGER_CIK: record.claim.attributes[ATTR_MANAGER_CIK],
                    ATTR_MANAGER_NAME: record.claim.attributes.get(
                        ATTR_MANAGER_NAME, NOT_EVALUABLE
                    ),
                    COLUMN_VALUE: record.claim.attributes[ATTR_VALUE],
                    COLUMN_SHARES: record.claim.attributes.get(
                        ATTR_SHARES, NOT_EVALUABLE
                    ),
                    ATTR_MATCH_BAND: record.claim.attributes.get(
                        ATTR_MATCH_BAND, NOT_EVALUABLE
                    ),
                    ATTR_MATCH_SCORE: record.claim.attributes[ATTR_MATCH_SCORE],
                    # `valid_from`, not `observed_at` — the source's instant,
                    # not this run's. The same bitemporal reading `debt()`
                    # uses, and for the same reason.
                    "last_updated": record.claim.valid_from.isoformat(),
                }
                for record in view.entities
                if record.claim.entity_class == CLASS_MANAGER
                and Decimal(record.claim.attributes[ATTR_VALUE]) >= threshold
            ),
            # A TOTAL order, so the bytes are stable and the content address is
            # reproducible: position descending, then the identity authority
            # ascending. A rank with a partial order hashes two ways.
            key=lambda entry: (
                -Decimal(cast(str, entry[COLUMN_VALUE])),
                cast(str, entry[ATTR_MANAGER_CIK]),
            ),
        )
        issuer = next(
            (
                record
                for record in view.entities
                if record.claim.entity_class == CLASS_ISSUER
            ),
            None,
        )
        resolved = self._scenario.resolved_security
        return ProjectionOutput(
            plan_id=self._plan_id,
            payload={
                "count": len(holders),
                "holders": holders,
                "issuer": {
                    "lei": self._scenario.request.subject,
                    "registered_name": (
                        issuer.claim.attributes.get(ATTR_ISSUER_NAME, NOT_EVALUABLE)
                        if issuer is not None
                        else NOT_EVALUABLE
                    ),
                },
                "perspective_role": perspective.role,
                ATTR_PERIOD: self._scenario.report_period,
                "resolved_security": {
                    "candidates_considered": resolved.candidates_considered,
                    ATTR_SECURITY_CUSIP: resolved.cusip,
                    "resolution_basis": resolved.resolution_basis,
                },
                "threshold": {
                    "comparison": COMPARISON,
                    THRESHOLD_PARAMETER: str(threshold),
                },
            },
        )


def plan_class() -> type[HoldersOverThresholdProjection]:
    """Π as a class the fabric constructs, never an object it is handed."""
    return HoldersOverThresholdProjection
