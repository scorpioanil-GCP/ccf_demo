"""What THIS deployment binds — spec CP-SPEC-001, `reference.counterparty.v1`.

[ADAPT] all of it. [MECHANISM] nothing: every function here is an INTERPRETER
of a document beside it, and the fabric is reached only through its published
surface.

:func:`connection` composes the CCF **graph** backend's settings;
:func:`source_dsn` binds the read-only **system of record**. Confusing the two
is the mistake this file is arranged to make hard — they read different blocks
of `backends.yaml` and they are never both in scope in one function.

**THE ONE THING WORTH READING BEFORE THE CODE.** This product resolves an
anchor that may be an LEI *or* an internal client id, through two different
identity authorities with two different freshness ceilings (spec §C.3). Which
authority answered is not an implementation detail the assembly can keep to
itself — it is emitted as `identity_authority` in the payload, because a
consumer must be able to tell a 24-hour vendor claim from a months-old KYC one
without parsing lineage. Everything asymmetric in this file follows from that.

**NOTHING HERE WRITES TO THE STORE IT READS.** The role the DSN reaches needs
`SELECT` and nothing else (spec §F.3, `backends.yaml`).
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import psycopg
import yaml

from ccf.assembly.worker import EntityResolutionSpec
from ccf.controlplane.artifacts import (
    DebtProfile,
    HalfLifeTable,
    OperatorParametersArtifact,
    PerspectiveArtifact,
    ProductClassDeclaration,
)
from ccf.deployment import BootedFabric
from ccf.graph.protocols import GraphView
from ccf.halflife.assessment import DebtAssessment, DebtFactors
from ccf.halflife.debt import FreshnessScorer, assess_debt
from ccf.halflife.decay import Observation
from ccf.projection.plan import Perspective, ProjectionOutput
from ccf.products.request import ProductRequest, ProductRequestContract
from ccf.signal.envelope import SignalEnvelope, SourceIdentity

HERE = Path(__file__).parent
ARTIFACTS = HERE / "artifacts"

CONFIG = HERE / "ccf_config.yaml"
BACKENDS = HERE / "backends.yaml"
QUESTION = ARTIFACTS / "question.yaml"
TTL = ARTIFACTS / "ttl.yaml"
SPEC = HERE / "spec" / "CP-SPEC-001_Counterparty_Reference_Snapshot.md"

# --- Keys this deployment reads out of its own documents. -------------------
DECLARATION = "declaration"
PROFILES = "profiles"
SOURCES = "sources"
SETTINGS = "settings"
FROM_ENV = "from_env"
REMEDY = "remedy"
PREFIX = "prefix"
SUFFIX = "suffix"

KEY_PERSPECTIVE = "default_perspective"
KEY_PRODUCT_CLASS = "product_class"
KEY_POLICY_OPERATOR = "policy.principal-subgraph"
KEY_REQUEST_CONTRACT = "request_contract"
KEY_RESOLUTION = "resolution"
KEY_HALF_LIFE_TABLE = "half_life"
KEY_DEBT_PROFILE = "debt_profile"
KEY_POLICY_BUNDLE = "policy"

REPLAY_RECORD_CLASS = "cp-01.replay-record"
QUERY_PIN_CLASS = "cp-01.graph-query"
ARTIFACT_STORE_DIRNAME = "artifacts-store"

#: What a claim carries when the source did not supply it (§E.2).
NOT_EVALUABLE = "NOT_EVALUABLE"

#: §C.3's seven-class typing chain, decided here and inherited catalog-wide.
TYPE_CHAIN = (
    "cmns-pts:Agent",
    "cmns-pts:Party",
    "cmns-org:Organization",
    "cmns-org:FormalOrganization",
    "cmns-org:LegalPerson",
    "cmns-org:LegalEntity",
    "fibo-be-le-cb:Corporation",
)

#: §B.4 — a lapsed registration is EXCLUDED unless the caller asks otherwise.
STATUS_LAPSED = "LAPSED"
PARAM_INCLUDE_LAPSED = "include_lapsed"
PARAM_DEBT_TOLERANCE = "debt_tolerance"

#: The `sources:` block `backends.yaml` declares for the system of record.
SOURCE_BINDING = "counterparty_reference"
SOURCE_SETTING_DSN = "dsn"

# --------------------------------------------------------------------------
# THE SOURCE ESTATE — spec §C.1's system-of-record column, and §F.3's estate
# binding. PostgreSQL, schema `ccf_v2`.
#
# The store IS named, here and in the specification, because an implementation
# specification that will not say which of five stores an element lives in
# cannot be built from (Dave, 2026-08-29). What is NOT named anywhere in this
# tree is the DEPLOYMENT — host, port, credential — which reaches this module
# only through `source_dsn()` and only from the environment.
# --------------------------------------------------------------------------
SOURCE_SCHEMA = "ccf_v2"
TABLE_ENTITY = "legal_entity"
TABLE_INTERNAL = "internal_client"
TABLE_CROSSWALK = "crosswalk"
TABLE_PRINCIPAL_JURISDICTION = "principal_jurisdiction"

#: §C.3's two identity authorities, spelled as the payload spells them.
AUTHORITY_VENDOR = "lei-reference-data"
AUTHORITY_INTERNAL = "internal-client-master"

#: §E.1's two signal classes, one per authority. Never averaged (§B.1 el. 2).
SIGNAL_VENDOR = "vendor_identity"
SIGNAL_INTERNAL = "internal_kyc"

# --- Attribute names in the L1 payload, and therefore in the graph. ---------
#: The rule's MATCH KEY. `SpecDrivenEntityResolution` selects a resolution
#: rule by the PRESENCE of this key in the envelope payload, so a payload
#: without it produces no entity at all — an empty view that every shipped gate
#: would pass over in silence.
ATTR_MATCH_KEY = "counterparty_ref"
ATTR_ANCHOR = "anchor"
ATTR_LEI = "lei"
ATTR_LEGAL_NAME = "legal_name"
ATTR_JURISDICTION = "legal_jurisdiction"
ATTR_ENTITY_STATUS = "entity_status"
ATTR_REGISTRATION_STATUS = "registration_status"
ATTR_LEGAL_FORM = "legal_form"
ATTR_LEGAL_COUNTRY = "legal_address_country"
ATTR_LEGAL_CITY = "legal_address_city"
ATTR_LEGAL_REGION = "legal_address_region"
ATTR_HQ_COUNTRY = "hq_address_country"
ATTR_HQ_CITY = "hq_address_city"
ATTR_HQ_REGION = "hq_address_region"
ATTR_AUTHORITY = "identity_authority"
ATTR_INTERNAL_ID = "internal_client_id"
ATTR_PROVENANCE = "provenance_class"

ENTITY_CLASS = "counterparty"


# --------------------------------------------------------------------------
# This deployment's own documents.
# --------------------------------------------------------------------------
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
    never over a substrate name. This function reaches the ``profiles:`` block
    and nothing else; the system of record is :func:`source_dsn`'s business.
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
    the graph's composition and the source binding are two things a reader can
    tell apart. Nothing this deployment runs writes to the store this reaches.
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

    Read from ``ccf_config.yaml``'s ``default_perspective:``. A caller needs
    this *before* the fabric boots — the assembler seam takes it as an
    argument — so it is read here rather than off the booted registry.
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

    The address tokens come from ``artifacts/question.yaml`` and the class
    identity from ``ccf_config.yaml``. ``parameters`` is the CALLER's — this
    function supplies no value for it and no default, which is what keeps the
    contract's requirement real (§B.4).
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


def demonstration_anchor() -> str:
    """The anchor the bundled demonstration asks about, from scenario material."""
    return str(_declaration(QUESTION)["subject"])


def demonstration_debt_tolerance() -> float:
    """The caller's debt ceiling for the bundled demonstration (§B.4)."""
    return float(_declaration(QUESTION)["debt_tolerance"])


def demonstration_include_lapsed() -> bool:
    """The bundled demonstration's `include_lapsed` (§B.4)."""
    return bool(_declaration(QUESTION)["include_lapsed"])


def declared_ttl_seconds() -> int:
    """This class's declared TTL, from `artifacts/ttl.yaml` (§B.1 element 3)."""
    return int(_declaration(TTL)["declared_ttl_seconds"])


def max_ttl_seconds() -> int:
    """This class's TTL ceiling, from `artifacts/ttl.yaml`."""
    return int(_declaration(TTL)["max_ttl_seconds"])


# --------------------------------------------------------------------------
# Step 1 of the specification's operator table — `Resolve`, and it carries TWO
# identity authorities behind one anchor parameter.
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class ResolvedEntity:
    """One counterparty, and which authority resolved it.

    ``observed_on`` is the SOURCE's own last observation of this entity — the
    vendor's `retrieved_at` or the client master's `kyc_last_refresh` — and it
    is what `ttl_anchor: from_entity_freshness` anchors on (§B.1 element 3).
    Not this run's clock, and not the request instant.

    ``freshness_ceiling_days`` is the entity's OWN ceiling and travels with the
    row: 1 for a vendor-resolved entity, 180/270/365 for an internal one. §C.3
    states the asymmetry belongs in the payload rather than averaged into one
    freshness claim, and this field is how it gets there.
    """

    anchor: str
    authority: str
    signal_class: str
    observed_on: date
    freshness_ceiling_days: int
    attributes: Mapping[str, str]


@dataclass(frozen=True)
class SourceRead:
    """What one read of the system of record produced."""

    resolved: ResolvedEntity | None
    envelopes: tuple[SignalEnvelope, ...]
    permitted_jurisdictions: tuple[str, ...]


def _instant(value: date) -> datetime:
    """A source DATE as a UTC instant at midnight.

    The source records these as dates, not timestamps. Widening one to an
    instant is a lossless statement about when the observation is known to have
    held BY; narrowing the other way would invent a time of day.
    """
    return datetime(value.year, value.month, value.day, tzinfo=UTC)


def _text(value: Any) -> str | None:
    """A source value as text, or None when the source did not carry it.

    A non-mandatory field the source did not carry is ABSENT from the payload
    rather than blank — an absent key is a real completeness shortfall that
    `C_attributes` counts, while a blank string measures as present (§E.2).
    """
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _resolve_by_lei(cur: Any, anchor: str) -> ResolvedEntity | None:
    """The LEI-registered path — §C.3 hierarchy row 1, ceiling 24 hours."""
    cur.execute(
        f"""
        select le.lei, le.legal_name, le.legal_jurisdiction, le.entity_status,
               le.registration_status, le.legal_form,
               le.legal_address_country, le.legal_address_city,
               le.legal_address_region,
               le.hq_address_country, le.hq_address_city, le.hq_address_region,
               le.retrieved_at, le.provenance,
               (select x.internal_client_id
                  from {SOURCE_SCHEMA}.{TABLE_CROSSWALK} x
                 where x.lei = le.lei) as internal_client_id
          from {SOURCE_SCHEMA}.{TABLE_ENTITY} le
         where le.lei = %s
        """,
        (anchor,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    (
        lei, legal_name, jurisdiction, entity_status, registration_status,
        legal_form, legal_country, legal_city, legal_region,
        hq_country, hq_city, hq_region, retrieved_at, provenance,
        internal_client_id,
    ) = row
    attributes: dict[str, str] = {
        ATTR_MATCH_KEY: anchor,
        ATTR_ANCHOR: anchor,
        ATTR_LEI: str(lei),
        ATTR_AUTHORITY: AUTHORITY_VENDOR,
        ATTR_PROVENANCE: str(provenance),
    }
    for key, value in (
        (ATTR_LEGAL_NAME, legal_name),
        (ATTR_JURISDICTION, jurisdiction),
        (ATTR_ENTITY_STATUS, entity_status),
        (ATTR_REGISTRATION_STATUS, registration_status),
        (ATTR_LEGAL_FORM, legal_form),
        (ATTR_LEGAL_COUNTRY, legal_country),
        (ATTR_LEGAL_CITY, legal_city),
        (ATTR_LEGAL_REGION, legal_region),
        (ATTR_HQ_COUNTRY, hq_country),
        (ATTR_HQ_CITY, hq_city),
        (ATTR_HQ_REGION, hq_region),
        (ATTR_INTERNAL_ID, internal_client_id),
    ):
        text = _text(value)
        if text is not None:
            attributes[key] = text
    return ResolvedEntity(
        anchor=anchor,
        authority=AUTHORITY_VENDOR,
        signal_class=SIGNAL_VENDOR,
        observed_on=retrieved_at,
        freshness_ceiling_days=1,
        attributes=attributes,
    )


def _resolve_by_internal_id(cur: Any, anchor: str) -> ResolvedEntity | None:
    """The internal-client path — §C.3 hierarchy rows 2 and 3, ceiling MONTHS.

    The entity has NO LEI, and no `SYN-` placeholder stands in for one: a
    placeholder would resolve like a real anchor and defeat the §D
    counterfactual these rows exist to demonstrate (§C.4 trap 2). So `lei` is
    absent from the payload rather than blank.
    """
    cur.execute(
        f"""
        select i.internal_client_id, i.legal_name, i.legal_jurisdiction,
               i.legal_form,
               i.legal_address_country, i.legal_address_city,
               i.legal_address_region,
               i.hq_address_country, i.hq_address_city, i.hq_address_region,
               i.kyc_last_refresh, i.freshness_ceiling_days, i.provenance
          from {SOURCE_SCHEMA}.{TABLE_INTERNAL} i
         where i.internal_client_id = %s
        """,
        (anchor,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    (
        internal_id, legal_name, jurisdiction, legal_form,
        legal_country, legal_city, legal_region,
        hq_country, hq_city, hq_region,
        kyc_last_refresh, ceiling_days, provenance,
    ) = row
    attributes: dict[str, str] = {
        ATTR_MATCH_KEY: anchor,
        ATTR_ANCHOR: anchor,
        ATTR_INTERNAL_ID: str(internal_id),
        ATTR_AUTHORITY: AUTHORITY_INTERNAL,
        ATTR_PROVENANCE: str(provenance),
    }
    for key, value in (
        (ATTR_LEGAL_NAME, legal_name),
        (ATTR_JURISDICTION, jurisdiction),
        (ATTR_LEGAL_FORM, legal_form),
        (ATTR_LEGAL_COUNTRY, legal_country),
        (ATTR_LEGAL_CITY, legal_city),
        (ATTR_LEGAL_REGION, legal_region),
        (ATTR_HQ_COUNTRY, hq_country),
        (ATTR_HQ_CITY, hq_city),
        (ATTR_HQ_REGION, hq_region),
    ):
        text = _text(value)
        if text is not None:
            attributes[key] = text
    return ResolvedEntity(
        anchor=anchor,
        authority=AUTHORITY_INTERNAL,
        signal_class=SIGNAL_INTERNAL,
        observed_on=kyc_last_refresh,
        freshness_ceiling_days=int(ceiling_days),
        attributes=attributes,
    )


def _permitted_jurisdictions(cur: Any, *, principal_id: str) -> tuple[str, ...]:
    """The calling principal's grant set, EXPANDED against the estate.

    §C.1 row 3 grants a principal a jurisdiction PREFIX — `US` reaches
    `US-DE`, `US-MD`, `US-NV`. `src/ccf/operators/categories.py::PolicyFilter`
    tests EXACT membership of `permitted_classifications`, so a prefix handed
    to it unexpanded matches nothing and empties the view.

    The expansion is therefore the deployment's, and it is done against the
    jurisdictions the estate actually holds rather than against an invented
    list — recorded as an SDK-surface finding in spec §F.4. Returning the
    prefix itself as well as its expansions is deliberate: an entity whose
    jurisdiction IS the bare prefix (`GB`, `CH`) is granted by the same row.
    """
    cur.execute(
        f"""
        select distinct le.legal_jurisdiction
          from {SOURCE_SCHEMA}.{TABLE_ENTITY} le
          join {SOURCE_SCHEMA}.{TABLE_PRINCIPAL_JURISDICTION} pj
            on le.legal_jurisdiction = pj.jurisdiction_prefix
            or le.legal_jurisdiction like pj.jurisdiction_prefix || '-%%'
         where pj.principal_id = %s
           and le.legal_jurisdiction is not null
        """,
        (principal_id,),
    )
    return tuple(sorted(str(r[0]) for r in cur.fetchall()))


def source_read(
    tenant: str,
    *,
    at: datetime,
    subject: str,
    principal_id: str,
) -> SourceRead:
    """Read the system of record once — §D.2 step 1's `Resolve`.

    **Two authorities, tried in the order §C.3's hierarchy states them.** The
    LEI path first because it is the authority for the population that has one;
    the internal client master second, for the population that does not. An
    anchor matching neither resolves to nothing, and §D.2 makes that a `404`
    rather than an empty payload — *"an anchor that resolves to nothing is
    never an empty payload."*

    The read is `SELECT`-only. Nothing this function runs writes to the store.
    """
    with psycopg.connect(source_dsn()) as db:
        with db.cursor() as cur:
            resolved = _resolve_by_lei(cur, subject)
            if resolved is None:
                resolved = _resolve_by_internal_id(cur, subject)
            permitted = _permitted_jurisdictions(cur, principal_id=principal_id)

    if resolved is None:
        return SourceRead(
            resolved=None, envelopes=(), permitted_jurisdictions=permitted
        )

    envelope = SignalEnvelope(
        tenant_id=tenant,
        envelope_id=f"counterparty:{resolved.anchor}",
        source=SourceIdentity(
            system_id=(
                TABLE_ENTITY
                if resolved.authority == AUTHORITY_VENDOR
                else TABLE_INTERNAL
            )
        ),
        # The request instant, so the as-of boundary the caller asked at is at
        # or after the claim's `observed_at`.
        ingestion_timestamp=at,
        # THE SOURCE'S OWN LAST OBSERVATION — the vendor's `retrieved_at` or
        # the client master's `kyc_last_refresh`. This becomes the claim's
        # `valid_from`, which is what the λ_c curve reads and what
        # `ttl_anchor: from_entity_freshness` anchors `expires_at` on. A column
        # a plain SELECT ignores becomes a measured D_c.
        observed_time=_instant(resolved.observed_on),
        raw_payload=dict(resolved.attributes),
    )
    return SourceRead(
        resolved=resolved,
        envelopes=(envelope,),
        permitted_jurisdictions=permitted,
    )


def expires_at(resolved: ResolvedEntity) -> datetime:
    """`expires_at` for one resolved entity — §B.1 element 3.

    `from_entity_freshness`: the entity's own last observation plus the class's
    declared TTL. NOT the request instant plus the TTL, which would be
    `from_decision` and a different product (§A's *primitive taught*).
    """
    return _instant(resolved.observed_on) + timedelta(seconds=declared_ttl_seconds())


# --------------------------------------------------------------------------
# What one run needs — satisfies `produce.Scenario` structurally.
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class CounterpartyScenario:
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
    resolved: ResolvedEntity
    permitted_jurisdictions: tuple[str, ...]
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

        ``ttl_anchor`` is ``from_entity_freshness``, so the anchor is THE
        ENTITY'S OWN LAST OBSERVATION and not the request instant. Both the
        duration and the ceiling come from ``artifacts/ttl.yaml``; neither is a
        constant in this module.

        **This is where §F.4 finding 8 bites.** For an entity resolved through
        the internal client master the anchor is `kyc_last_refresh`, months
        old, so `expires_at` lands in the past and
        ``src/ccf/products/gates.py::_refuse_ttl`` refuses. That refusal is the
        evidence the finding is taken back with (`CPR-G09`) — it is not routed
        around here.
        """
        return _instant(self.resolved.observed_on) + timedelta(
            seconds=self.ttl_seconds
        )

    def _declared_attributes(self) -> tuple[str, ...]:
        """What a served row must carry, from the resolution spec itself.

        Read off ``ccf_config.yaml``'s ``resolution:`` section rather than
        listed here, so C_attributes counts the attributes the deployment
        actually declared. Identity keys are excluded: a row missing one
        produced no entity to count, so it is a fail-closed condition rather
        than a completeness shortfall.
        """
        for rule in self.resolution.entity_rules:
            if rule.entity_class == ENTITY_CLASS:
                return tuple(
                    key
                    for key in rule.attribute_keys
                    if key not in set(rule.identity_keys)
                )
        return ()

    def debt(self, view: GraphView) -> DebtAssessment:
        """D_c over what this question assembled (whitepaper §7.7, spec §E.2).

        **F is measured against the signal class the ANSWERING AUTHORITY
        implies**, never one averaged over both. §B.1 element 2 states the rule
        and §C.3 states why: a single "24 hours" over a mixed population is the
        exact error the per-signal-class rule exists to prevent. The observation
        type is therefore `vendor_identity` or `internal_kyc` depending on which
        authority resolved the anchor, and `half_life:` in `ccf_config.yaml`
        declares both.

        **Decay is measured from ``valid_from``, not ``observed_at``.**
        ``observed_at`` is when the *fabric* learned a claim and ``valid_from``
        is when the *source's* fact began to hold. Scoring the former would
        measure the age of this run, so a months-old KYC record re-read a moment
        ago would score as perfectly fresh — a source outage laundered into a
        low-debt reading.

        **C is over the resolution spec's declared attributes.** One entity, so
        it is the fraction of declared attributes the source actually carried.
        §E.2's table names which may be absent: a no-LEI entity carries no
        `entity_status` or `registration_status` because an internal client
        master has no registrar, and those absences are a real shortfall rather
        than a defect to be filled with a default.

        **S is 1, and the reason is a MEASURED PROPERTY OF THIS ESTATE rather
        than a magic constant.** §E.2 defines S as agreement between the vendor's
        legal name and jurisdiction and the internal client master's for the
        same entity — "the earliest warning of a bad crosswalk match."
        `ccf_v2.internal_client` holds ONLY no-LEI entities, and
        `ccf_v2.legal_entity` holds only entities that have one, so **no entity
        in this estate has both records and there is nothing that could
        disagree.** S is therefore structurally 1 here, and the earliest-warning
        signal §E.2 describes CANNOT FIRE. Recorded as a finding rather than
        presented as a clean score: an S of 1 that no data could have moved is
        not evidence of agreement.
        """
        rows = [
            record
            for record in view.entities
            if record.claim.entity_class == ENTITY_CLASS
        ]
        if not rows:
            # `FreshnessScorer` refuses an empty sequence by design. An empty
            # assembled set is a fail-closed condition (§D.2 step 1 -> 404),
            # not a debt reading, so this returns the maximum rather than
            # inventing a score for nothing.
            return assess_debt(
                DebtFactors(
                    freshness=Decimal(0),
                    completeness=Decimal(0),
                    semantic_consistency=Decimal(1),
                ),
                profile=self.debt_profile,
            )
        observations = tuple(
            Observation(
                observation_type=self.resolved.signal_class,
                observed_at=record.claim.valid_from,
                subject=record.claim.entity_uri,
            )
            for record in rows
        )
        expected = self._declared_attributes()
        present = sum(
            1
            for record in rows
            for key in expected
            if record.claim.attributes.get(key)
        )
        total_expected = Decimal(len(rows) * len(expected)) or Decimal(1)
        scorer = FreshnessScorer(
            table=self.half_life_table,
            risk_sensitivity=self.debt_profile.risk_sensitivity,
        )
        return assess_debt(
            DebtFactors(
                freshness=scorer.score(observations, now=self.now),
                completeness=Decimal(present) / total_expected,
                semantic_consistency=Decimal(1),
            ),
            profile=self.debt_profile,
        )


def read(
    booted: BootedFabric,
    asked: ProductRequest,
    *,
    principal_id: str | None = None,
) -> CounterpartyScenario | None:
    """Name this deployment's artifact keys and read this question's values.

    Returns ``None`` when the anchor resolves to nothing — §D.2 step 1's
    fail-closed 404. *"An anchor that resolves to no entity is never an empty
    payload."* The caller renders the refusal; this function does not invent an
    empty scenario to keep a happy path alive.
    """
    artifacts = booted.artifacts
    ttl = _declaration(TTL)
    declared_perspective = cast(PerspectiveArtifact, artifacts[KEY_PERSPECTIVE])
    # §D.3 — the SAME question asked by four principals is two answers and two
    # refusals. The default is the declared perspective; an override is how the
    # demonstration and gate `CPR-G02` ask it as somebody else, and it changes
    # WHICH ENTITIES EXIST rather than how they are shaped.
    if principal_id is not None and principal_id != declared_perspective.principal_id:
        declared_perspective = declared_perspective.model_copy(
            update={"principal_id": principal_id}
        )
    read_source = source_read(
        booted.tenant_id,
        at=asked.asked_at,
        subject=asked.subject,
        principal_id=declared_perspective.principal_id,
    )
    if read_source.resolved is None:
        return None

    # §D.2 step 2 — the policy parameters are built PER REQUEST from the
    # calling principal's grant set, never taken statically from the config.
    # A static allowlist would serve one principal's entities to every
    # principal, which §E.3 names as a correctness defect presenting
    # intermittently. The declared artifact supplies the SHAPE; the estate
    # supplies this principal's values.
    declared_policy = cast(
        OperatorParametersArtifact, artifacts[KEY_POLICY_OPERATOR]
    )
    policy_parameters = declared_policy.model_copy(
        update={
            "permitted_classifications": tuple(read_source.permitted_jurisdictions)
        }
    )

    return CounterpartyScenario(
        envelopes=read_source.envelopes,
        resolved=read_source.resolved,
        permitted_jurisdictions=read_source.permitted_jurisdictions,
        request=asked,
        request_contract=ProductRequestContract.from_declared(
            cast(Any, artifacts[KEY_REQUEST_CONTRACT])
        ),
        product_class=cast(ProductClassDeclaration, artifacts[KEY_PRODUCT_CLASS]),
        perspective=declared_perspective,
        # ONE entry, so one operator. The spine never counts them.
        operator_parameters={KEY_POLICY_OPERATOR: policy_parameters},
        resolution=cast(EntityResolutionSpec, artifacts[KEY_RESOLUTION]),
        half_life_table=cast(HalfLifeTable, artifacts[KEY_HALF_LIFE_TABLE]),
        debt_profile=cast(DebtProfile, artifacts[KEY_DEBT_PROFILE]),
        ttl_seconds=int(ttl["declared_ttl_seconds"]),
        max_ttl_seconds=int(ttl["max_ttl_seconds"]),
        # A pinned reference, never the resolved artifact: the profile has its
        # own version lane, and inlining it would give one record two version
        # identities.
        halflife_debt_profile=(
            f"ccf-artifact://{booted.tenant_id}/ccf.debt-profile/"
            f"{KEY_DEBT_PROFILE}@{booted.pins.version_for(KEY_DEBT_PROFILE)}"
        ),
    )


# --------------------------------------------------------------------------
# Π — the projection.
# --------------------------------------------------------------------------
class CounterpartyReferenceProjection:
    """Shape the resolved counterparty into the §D.6 emitted contract.

    **Π is NOT exercised as role-conditioning at this tier** (§A): the product
    returns the same SHAPE to every authorized caller, and `projection_plan_id`
    is the class name rather than a plan that assembles differently per
    principal. What differs per principal is which entities EXIST to be shaped,
    and that is settled upstream by `Policy` (§D.2 step 2) — which is the whole
    reason the suppression rule holds structurally rather than by filtering
    here (§B.2).

    **`include_lapsed` is applied HERE**, at Π, not in the graph query. A
    lapsed entity is EXCLUDED ENTIRELY rather than returned unflagged, which is
    the whole point of the parameter (§B.4, gate `CPR-G01`) — and applying it at
    Π keeps every value of the parameter compiling to the same pinned read, so
    what the caller's choice changes is the payload and therefore the content
    address, never what was read.
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

    def _address(self, attributes: Mapping[str, str], prefix: str) -> Mapping[str, str]:
        """One labelled address — §C.4 trap 1.

        Two separate typed objects, never one unlabelled triple. A missing part
        is `NOT_EVALUABLE` rather than blank or absent, because a consumer
        joining on headquarters city must be able to tell "not recorded" from
        "recorded as empty".
        """
        return {
            "country": attributes.get(f"{prefix}_country", NOT_EVALUABLE),
            "city": attributes.get(f"{prefix}_city", NOT_EVALUABLE),
            "region": attributes.get(f"{prefix}_region", NOT_EVALUABLE),
        }

    def invoke(
        self,
        *,
        view: GraphView,
        operator_outputs: Mapping[str, Any],
        perspective: Perspective,
        temporal_boundary: datetime,
    ) -> ProjectionOutput:
        include_lapsed = bool(
            self._scenario.request.parameters.get(PARAM_INCLUDE_LAPSED, False)
        )
        record = next(
            (
                entity
                for entity in view.entities
                if entity.claim.entity_class == ENTITY_CLASS
            ),
            None,
        )
        if record is None:
            # The Policy step removed it: this principal is not entitled to see
            # this entity. §B.2's suppression rule — no count, no marker, no
            # placeholder saying anything was withheld. The payload is simply
            # the payload of a product with no counterparty in it.
            return ProjectionOutput(
                plan_id=self._plan_id,
                payload={
                    "counterparty": None,
                    "perspective_role": perspective.role,
                },
            )

        attributes = record.claim.attributes
        lapsed = attributes.get(ATTR_REGISTRATION_STATUS) == STATUS_LAPSED
        if lapsed and not include_lapsed:
            # §B.4 / `CPR-G01`: excluded ENTIRELY rather than returned
            # unflagged. This is a different silence from the one above and the
            # two must not be confused — here the caller ASKED for the
            # exclusion, so the parameter that produced it is echoed back.
            return ProjectionOutput(
                plan_id=self._plan_id,
                payload={
                    "counterparty": None,
                    "perspective_role": perspective.role,
                    "excluded": {"reason": "registration-lapsed",
                                 PARAM_INCLUDE_LAPSED: include_lapsed},
                },
            )

        resolved = self._scenario.resolved
        counterparty: dict[str, Any] = {
            "anchor": self._scenario.request.subject,
            "entity_id": record.claim.entity_uri,
            # WHICH AUTHORITY ANSWERED — a fact about the answer, not about how
            # the assembly ran, so it is in the payload and not the lineage.
            ATTR_AUTHORITY: resolved.authority,
            ATTR_LEGAL_NAME: attributes.get(ATTR_LEGAL_NAME, NOT_EVALUABLE),
            ATTR_JURISDICTION: attributes.get(ATTR_JURISDICTION, NOT_EVALUABLE),
            # Nullable, and ONLY for one authority: GLEIF publishes these and an
            # internal client master has no registrar. A non-null default would
            # manufacture a registration status for an entity that has none —
            # worse than a null, because it looks answered.
            ATTR_ENTITY_STATUS: attributes.get(ATTR_ENTITY_STATUS),
            ATTR_REGISTRATION_STATUS: attributes.get(ATTR_REGISTRATION_STATUS),
            ATTR_LEGAL_FORM: attributes.get(ATTR_LEGAL_FORM),
            "legal_address": self._address(attributes, "legal_address"),
            "headquarters_address": self._address(attributes, "hq_address"),
            "type_chain": list(TYPE_CHAIN),
        }
        # Absent rather than null for a no-LEI entity — there is no LEI and no
        # `SYN-` placeholder stands in for one (§C.4 trap 2).
        if ATTR_LEI in attributes:
            counterparty[ATTR_LEI] = attributes[ATTR_LEI]
        if ATTR_INTERNAL_ID in attributes:
            counterparty[ATTR_INTERNAL_ID] = attributes[ATTR_INTERNAL_ID]

        return ProjectionOutput(
            plan_id=self._plan_id,
            payload={
                "counterparty": counterparty,
                "perspective_role": perspective.role,
                # §C.3's asymmetry, IN THE PAYLOAD rather than averaged into one
                # freshness claim. A consumer must be able to see that this
                # entity's ceiling is months, not 24 hours.
                "freshness_ceiling_days": resolved.freshness_ceiling_days,
                "signal_class": resolved.signal_class,
            },
        )


def plan_class() -> type[CounterpartyReferenceProjection]:
    """Π as a class the fabric constructs, never an object it is handed."""
    return CounterpartyReferenceProjection
