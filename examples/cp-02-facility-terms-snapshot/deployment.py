"""What THIS deployment binds — spec CP-SPEC-002, `reference.facility.v1`.

[ADAPT] all of it. [MECHANISM] nothing: every function here is an INTERPRETER
of a document beside it, and the fabric is reached only through its published
surface.

:func:`connection` composes the CCF **graph** backend's settings;
:func:`source_dsn` binds the read-only **system of record**. They read
different blocks of `backends.yaml` and are never both in scope in one
function.

**THE ONE THING WORTH READING BEFORE THE CODE.** This product's expiry is a
function of the FACILITY, never of the request. `expires_at` is the credit
agreement's own `effective_date` plus the declared 90-day window, and
`asked_at` appears nowhere in that computation (:func:`expires_at`). Two calls
for the same facility at two different instants return the same expiry. That is
the primitive this rung teaches, and it is the one thing an implementation can
get wrong while passing every other check in this example.

**THE ANCHOR IS AN INSTRUMENT, NOT AN IDENTITY.** A `facility_id` is internal
and has no external registry behind it (spec §C.3) — there is no GLEIF for
facilities — so an anchor that does not resolve is a `404` and never an empty
payload.

**NOTHING HERE WRITES TO THE STORE IT READS.** The role the DSN reaches needs
`SELECT` and nothing else (spec §F.3, `backends.yaml`).
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
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
EXPECTED = ARTIFACTS / "expected.yaml"
RECIPE = ARTIFACTS / "assembly-recipe.yaml"
SPEC = HERE / "spec" / "CP-SPEC-002_Facility_Terms_Snapshot.md"

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

REPLAY_RECORD_CLASS = "cp-02.replay-record"
QUERY_PIN_CLASS = "cp-02.graph-query"
ARTIFACT_STORE_DIRNAME = "artifacts-store"

#: What a claim carries when the source did not supply it, or when the source
#: supplied something a claim cannot be derived from (§E.2, §C.4 trap 1).
NOT_EVALUABLE = "NOT_EVALUABLE"

#: §B.4 — the caller's parameters.
PARAM_DEBT_TOLERANCE = "debt_tolerance"
PARAM_INCLUDE_PRICING_GRID = "include_pricing_grid"

#: The `sources:` block `backends.yaml` declares for the system of record.
SOURCE_BINDING = "facility_terms"
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
TABLE_FACILITY = "facility"
TABLE_ENTITY = "legal_entity"
TABLE_DEBT_RECONCILIATION = "debt_reconciliation"
TABLE_PRINCIPAL = "principal"
TABLE_PRINCIPAL_JURISDICTION = "principal_jurisdiction"

#: §E.1's four signal classes, spanning three orders of magnitude. The one the
#: TTL and the freshness score are taken against is the STRUCTURAL one: the
#: terms are what this product is about, and scoring freshness against the
#: 1-day balance would report a seven-year-stable object as perpetually stale.
SIGNAL_STRUCTURAL = "structural_terms"
SIGNAL_PRICING = "pricing_grid"
SIGNAL_BALANCE = "loan_balance"
SIGNAL_RATING = "internal_rating"

# --- Attribute names in the L1 payload, and therefore in the graph. ---------
#: The rule's MATCH KEY. `SpecDrivenEntityResolution` selects a resolution rule
#: by the PRESENCE of this key in the envelope payload, so a payload without it
#: produces no entity at all.
ATTR_MATCH_KEY = "facility_ref"
ATTR_FACILITY_ID = "facility_id"
ATTR_BORROWER_LEI = "borrower_lei"
ATTR_BORROWER_JURISDICTION = "borrower_jurisdiction"
ATTR_BORROWER_NAME = "borrower_legal_name"
ATTR_FACILITY_TYPE = "facility_type"
ATTR_COMMITMENT = "commitment_amount"
ATTR_CURRENCY = "currency"
ATTR_EFFECTIVE_DATE = "effective_date"
ATTR_MATURITY_DATE = "maturity_date"
ATTR_ADMIN_AGENT = "administrative_agent"
ATTR_AMENDMENT_COUNT = "amendment_count"
ATTR_AMENDED_RESTATED = "is_amended_restated"
ATTR_SYNDICATED = "syndicated"
ATTR_PRICING_GRID = "pricing_grid"
ATTR_OUTSTANDING = "outstanding_balance"
ATTR_UNDRAWN = "undrawn_availability"
ATTR_BALANCE_AS_OF = "balance_as_of"
ATTR_RATING = "internal_risk_rating"
ATTR_REPORTED_DEBT = "reported_debt"
ATTR_RECON_PLAUSIBLE = "debt_reconciliation_plausible"

ENTITY_CLASS = "facility"

#: The basis the expiry is measured from, spelled as the payload spells it
#: (§D.6 note 1). Named rather than implied so a consumer can check the
#: arithmetic without reading the specification.
TTL_BASIS = "effective_date"


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
    artifact wrote is what an operator reads when the variable is unset — which
    is the only reason `backends.yaml` can hold a variable NAME and nothing
    else.
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
    """The Π role-conditioning this product is served under."""
    declared = _document(CONFIG)[KEY_PERSPECTIVE]
    return Perspective(
        principal_id=str(declared["principal_id"]), role=str(declared["role"])
    )


def request(
    *, parameters: Mapping[str, object], asked_at: datetime | None = None
) -> ProductRequest:
    """Build the typed question from the caller's parameters and this
    deployment's declared vocabulary.

    ``parameters`` is the CALLER's — this function supplies no value for it and
    no default, which is what keeps the contract's requirement real (§B.4).
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
    """The facility the bundled demonstration asks about, from scenario material."""
    return str(_declaration(QUESTION)["subject"])


def demonstration_debt_tolerance() -> str:
    """The caller's debt ceiling for the bundled demonstration (§B.4).

    Returned as TEXT, not a float. The artifact quotes the value so it is
    bit-stable in a content-addressed document, and the caller's boundary is
    where it becomes a `Decimal` — see ``run.py``.
    """
    return str(_declaration(QUESTION)[PARAM_DEBT_TOLERANCE])


def demonstration_include_pricing_grid() -> bool:
    """The bundled demonstration's `include_pricing_grid` (§B.4)."""
    return bool(_declaration(QUESTION)[PARAM_INCLUDE_PRICING_GRID])


def unsupported_arguments() -> Mapping[str, str]:
    """Parameters this tier DECLARES and always REFUSES — §B.4, Standard §2.4.

    Read from `ccf_config.yaml`'s `request_contract:` block, never listed here:
    a parameter this deployment stops supporting, or starts, is a change to that
    document and not to this module.
    """
    declared = _document(CONFIG)[KEY_REQUEST_CONTRACT]
    return cast(Mapping[str, str], declared.get("unsupported_arguments", {}))


def declared_ttl_seconds() -> int:
    """This class's declared TTL, from `artifacts/ttl.yaml` (§B.1 element 3)."""
    return int(_declaration(TTL)["declared_ttl_seconds"])


def max_ttl_seconds() -> int:
    """This class's TTL ceiling, from `artifacts/ttl.yaml`."""
    return int(_declaration(TTL)["max_ttl_seconds"])


# --------------------------------------------------------------------------
# Step 1 of the specification's operator table — `Resolve`.
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class ResolvedFacility:
    """One credit facility, and the date its expiry will be measured from.

    ``effective_on`` is the EX-10 credit agreement's own "dated as of" clause —
    a filed public fact — and it is what ``ttl_anchor: from_entity_freshness``
    anchors on (§B.1 element 3). Not this run's clock, not the request instant,
    and NOT ``retrieved_at``: that column carries one distinct value across all
    60 rows, so anchoring there would give every facility the same expiry and
    retire the primitive this rung exists to teach (§E.5).

    ``tenor_days`` is ``None`` when the source's two dates do not admit one —
    absent, or inverted. §C.4 trap 1: four facilities carry a maturity date 196
    days BEFORE their effective date, all from a single source accession. A
    negative tenor is not a short loan; it is arithmetic reported as a term.
    """

    facility_id: str
    effective_on: date
    tenor_days: int | None
    attributes: Mapping[str, str]


@dataclass(frozen=True)
class SourceRead:
    """What one read of the system of record produced."""

    resolved: ResolvedFacility | None
    envelopes: tuple[SignalEnvelope, ...]
    permitted_jurisdictions: tuple[str, ...]
    sees_need_to_know: bool


def _instant(value: date) -> datetime:
    """A source DATE as a UTC instant at midnight.

    The source records these as dates, not timestamps. Widening one to an
    instant is a lossless statement about when the fact is known to have held
    BY; narrowing the other way would invent a time of day.
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


def _tenor_days(effective: date, maturity: date | None) -> int | None:
    """The facility's tenor, or ``None`` when the dates do not admit one.

    §C.4 trap 1 and gate `FTS-G08`. Two ways this returns ``None`` and they are
    different findings sharing one representation:

    * ``maturity`` is absent — 7 of 60 facilities. A completeness shortfall.
    * ``maturity`` PRECEDES ``effective`` — 4 of 60, all from source accession
      ``0000950142-26-001951``. An extraction defect, not a short loan.

    Both serve. Neither is repaired: repairing the dates would put an invented
    maturity into a payload that claims `public` provenance on that field.
    """
    if maturity is None or maturity < effective:
        return None
    return (maturity - effective).days


def _resolve_facility(cur: Any, anchor: str) -> ResolvedFacility | None:
    """Read one facility and the borrower context its policy step needs.

    ONE query. The borrower join is here rather than in a second read because
    `borrower_jurisdiction` is the attribute `PolicyFilter` filters on (§D.2
    step 2) and a facility that arrived without it would be admitted or refused
    on a missing value rather than on a grant.

    The `debt_reconciliation` join is a LEFT join by design: 8 of the 22
    borrowers have no row, and §E.2 makes that a real `S` shortfall rather than
    a reason to drop the facility.
    """
    cur.execute(
        f"""
        select f.facility_id, f.borrower_lei, f.facility_type,
               f.commitment_amount, f.currency,
               f.effective_date, f.maturity_date, f.administrative_agent,
               f.amendment_count, f.is_amended_restated, f.syndicated,
               f.pricing_grid,
               f.outstanding_balance, f.undrawn_availability, f.balance_as_of,
               f.internal_risk_rating,
               le.legal_jurisdiction, le.legal_name,
               dr.reported_debt, dr.plausible
          from {SOURCE_SCHEMA}.{TABLE_FACILITY} f
          join {SOURCE_SCHEMA}.{TABLE_ENTITY} le
            on le.lei = f.borrower_lei
     left join {SOURCE_SCHEMA}.{TABLE_DEBT_RECONCILIATION} dr
            on dr.lei = f.borrower_lei
         where f.facility_id = %s
        """,
        (anchor,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    (
        facility_id, borrower_lei, facility_type, commitment, currency,
        effective_date, maturity_date, admin_agent,
        amendment_count, amended_restated, syndicated, pricing_grid,
        outstanding, undrawn, balance_as_of, rating,
        borrower_jurisdiction, borrower_name, reported_debt, plausible,
    ) = row

    attributes: dict[str, str] = {
        ATTR_MATCH_KEY: str(facility_id),
        ATTR_FACILITY_ID: str(facility_id),
        ATTR_BORROWER_LEI: str(borrower_lei),
        ATTR_FACILITY_TYPE: str(facility_type),
        ATTR_CURRENCY: str(currency).strip(),
        ATTR_EFFECTIVE_DATE: effective_date.isoformat(),
        ATTR_AMENDMENT_COUNT: str(int(amendment_count)),
        ATTR_AMENDED_RESTATED: str(bool(amended_restated)).lower(),
        ATTR_SYNDICATED: str(bool(syndicated)).lower(),
        # The attribute `PolicyFilter` filters on. Carried onto the facility
        # record from the BORROWER: an instrument has no jurisdiction of its
        # own in this estate, and inheriting it from the entity that borrowed
        # is a decision (§D.3), not a mechanism.
        ATTR_BORROWER_JURISDICTION: str(borrower_jurisdiction),
    }
    for key, value in (
        (ATTR_COMMITMENT, commitment),
        (ATTR_MATURITY_DATE, maturity_date.isoformat() if maturity_date else None),
        (ATTR_ADMIN_AGENT, admin_agent),
        (ATTR_OUTSTANDING, outstanding),
        (ATTR_UNDRAWN, undrawn),
        (ATTR_BALANCE_AS_OF, balance_as_of.isoformat() if balance_as_of else None),
        (ATTR_RATING, rating),
        (ATTR_BORROWER_NAME, borrower_name),
        (ATTR_REPORTED_DEBT, reported_debt),
        (
            ATTR_RECON_PLAUSIBLE,
            None if plausible is None else str(bool(plausible)).lower(),
        ),
    ):
        text = _text(value)
        if text is not None:
            attributes[key] = text

    # §C.4 trap 4 — the grid travels as its JSON text, so the tier STRUCTURE
    # survives into the payload. Flattening it to a headline margin here would
    # pass every completeness check and answer a different question.
    if pricing_grid is not None:
        attributes[ATTR_PRICING_GRID] = _json_text(pricing_grid)

    return ResolvedFacility(
        facility_id=str(facility_id),
        effective_on=effective_date,
        tenor_days=_tenor_days(effective_date, maturity_date),
        attributes=attributes,
    )


def _json_text(value: Any) -> str:
    """One JSON-shaped source value as canonical text.

    Sorted keys and no incidental whitespace, so the same grid produces the
    same bytes on every run and therefore the same content address (§D.4).
    """
    import json

    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _principal_entitlement(
    cur: Any, *, principal_id: str
) -> tuple[tuple[str, ...], bool]:
    """The calling principal's grant set and its need-to-know flag.

    **TWO CONDITIONS, AND THEY ARE DIFFERENT KINDS OF THING** — §B.1 element 4,
    §D.3, gate `FTS-G03`.

    * ``sees_need_to_know`` is a property of the PRINCIPAL. Measured
      2026-08-29, 1 of the 4 principals carries it.
    * the grant set is a property of the BORROWER's jurisdiction, matched by
      PREFIX: ``US`` reaches ``US-DE``, ``US-MD``, ``US-FL``.

    They compose in :func:`read` rather than here: this function reports what
    the estate says, and the caller decides what that means for the allowlist.
    Returning them separately is what lets `FTS-G03` remove one condition and
    observe the served set change.

    The prefix is EXPANDED against the jurisdictions the estate actually holds
    because ``src/ccf/operators/categories.py::PolicyFilter`` tests EXACT
    membership — a prefix handed to it unexpanded matches nothing and empties
    the view. Returning the bare prefix as well as its expansions is
    deliberate: a borrower whose jurisdiction IS the prefix (``US``, ``CA``) is
    granted by the same row.
    """
    cur.execute(
        f"""
        select coalesce(bool_or(p.sees_need_to_know), false)
          from {SOURCE_SCHEMA}.{TABLE_PRINCIPAL} p
         where p.principal_id = %s
        """,
        (principal_id,),
    )
    row = cur.fetchone()
    sees_need_to_know = bool(row[0]) if row is not None else False

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
    granted = tuple(sorted(str(r[0]) for r in cur.fetchall()))
    return granted, sees_need_to_know


def source_read(
    tenant: str,
    *,
    at: datetime,
    subject: str,
    principal_id: str,
) -> SourceRead:
    """Read the system of record once — §D.2 step 1's `Resolve`.

    An anchor matching no facility resolves to nothing, and §D.2 makes that a
    `404` rather than an empty payload. The read is `SELECT`-only.
    """
    with psycopg.connect(source_dsn()) as db:
        with db.cursor() as cur:
            resolved = _resolve_facility(cur, subject)
            granted, sees_need_to_know = _principal_entitlement(
                cur, principal_id=principal_id
            )

    if resolved is None:
        return SourceRead(
            resolved=None,
            envelopes=(),
            permitted_jurisdictions=granted,
            sees_need_to_know=sees_need_to_know,
        )

    envelope = SignalEnvelope(
        tenant_id=tenant,
        envelope_id=f"facility:{resolved.facility_id}",
        source=SourceIdentity(system_id=TABLE_FACILITY),
        # The request instant, so the as-of boundary the caller asked at is at
        # or after the claim's `observed_at`.
        ingestion_timestamp=at,
        # THE AGREEMENT'S OWN DATE. This becomes the claim's `valid_from`,
        # which is what the λ_c curve reads and what
        # `ttl_anchor: from_entity_freshness` anchors `expires_at` on. A column
        # a plain SELECT reads past becomes a measured expiry and a measured
        # D_c.
        observed_time=_instant(resolved.effective_on),
        raw_payload=dict(resolved.attributes),
    )
    return SourceRead(
        resolved=resolved,
        envelopes=(envelope,),
        permitted_jurisdictions=granted,
        sees_need_to_know=sees_need_to_know,
    )


def expires_at(resolved: ResolvedFacility) -> datetime:
    """`expires_at` for one resolved facility — §B.1 element 3.

    **The whole product is this line.** `from_entity_freshness`: the credit
    agreement's own effective date plus the class's declared TTL.

    ``asked_at`` is not a parameter of this function and cannot be. An
    implementation that took one would be `from_decision` wearing a different
    label — the counterfactual §A names — and it would pass every other check
    in this example. Gate `FTS-G01` is what refuses it: the same facility asked
    at two different instants must return the same expiry, to the second.
    """
    return _instant(resolved.effective_on) + timedelta(seconds=declared_ttl_seconds())


# --------------------------------------------------------------------------
# What one run needs — satisfies `produce.Scenario` structurally.
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class FacilityScenario:
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
    resolved: ResolvedFacility
    permitted_jurisdictions: tuple[str, ...]
    sees_need_to_know: bool
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

        **A FUNCTION OF THE FACILITY, NOT OF THE REQUEST.** Neither ``now`` nor
        ``temporal_boundary`` appears in it — see :func:`expires_at`.

        **This is where §F.4 finding 1 bites.** ``effective_date`` spans seven
        years across the estate, so for 50 of the 60 facilities this lands in
        the past and ``src/ccf/products/gates.py::_refuse_ttl`` refuses. That
        refusal is the evidence the finding is taken back with (`FTS-G09`) — it
        is not routed around here, and the declaration is not quietly widened
        to make the numbers look healthy.
        """
        return expires_at(self.resolved)

    @property
    def ttl_basis_value(self) -> str:
        """The date the expiry was measured from, as the payload spells it.

        In the payload because a consumer must be able to check the arithmetic
        without reading the specification (§D.6 note 1), and because without it
        two products anchored on different dates are indistinguishable on the
        wire — which is the substitution §E.5 is about.
        """
        return self.resolved.effective_on.isoformat()

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

        **F is measured against the STRUCTURAL signal class**, whose λ_c is ~540
        days. §E.1 carries four classes spanning three orders of magnitude, and
        which one F is taken against is a decision rather than an average: the
        terms are what this product is FOR, and scoring freshness against the
        1-day `loan_balance` would report a seven-year-stable object as
        perpetually stale. §B.1 element 2 forbids averaging them; this picks the
        one the payload is about and says so.

        **Decay is measured from ``valid_from``, not ``observed_at``.**
        ``observed_at`` is when the *fabric* learned a claim and ``valid_from``
        is when the *source's* fact began to hold — here, the agreement's
        effective date. Scoring the former would measure the age of this run, so
        a 2019 agreement re-read a moment ago would score as perfectly fresh: a
        stale source laundered into a low-debt reading.

        **C is over the resolution spec's declared attributes.** §E.2's table
        names which may be absent: 7 facilities carry no maturity date, 1 no
        commitment, 1 no grid, and 8 of the 22 borrowers have no debt
        reconciliation row. Those absences are real shortfalls rather than
        defects to be filled with a default.

        **S IS COMPUTED HERE AND IT CAN ACTUALLY MOVE, which is what separates
        this product from rung 01.** §E.2 defines S as agreement between the
        facility's committed amount and the borrower's own 10-K reported debt —
        "the earliest warning that a facility has been attached to the wrong
        borrower." `ccf_v2.debt_reconciliation` carries that comparison already
        made, as `plausible`, and measured 2026-08-29 **one of its 14 rows is
        `false`**: LEI 549300KTTIRAOGXCRV69 commits 4,786,505,256 against
        2,944,900,000 of reported debt.

        So S is 1 when the reconciliation says plausible, and reduced when it
        does not or when there is no row to ask. Rung 01 recorded that its S was
        structurally 1 because no entity in that estate could disagree with
        itself — an S of 1 that no data could have moved is not evidence of
        agreement. Here it can move, and a run against the implausible borrower
        shows it moving.
        """
        rows = [
            record
            for record in view.entities
            if record.claim.entity_class == ENTITY_CLASS
        ]
        if not rows:
            # `FreshnessScorer` refuses an empty sequence by design. An empty
            # assembled set is a fail-closed condition (§D.2 step 1 -> 404, or
            # step 2 -> 403), not a debt reading, so this returns the maximum
            # rather than inventing a score for nothing.
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
                observation_type=SIGNAL_STRUCTURAL,
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
                semantic_consistency=self._semantic_consistency(rows),
            ),
            profile=self.debt_profile,
        )

    def _semantic_consistency(self, rows: list[Any]) -> Decimal:
        """`S` — does the borrower's own filed debt corroborate this facility?

        Three states, and the middle one is the finding worth having:

        * the reconciliation says ``plausible`` → **1**
        * the reconciliation says NOT plausible → **0.5**. The facility is still
          served; what is reduced is how much the answer should be leaned on.
          A committed amount 62% above the borrower's reported debt is the
          earliest warning of a wrong attribution, and suppressing the facility
          would hide the warning along with it.
        * there is no reconciliation row at all — 8 of the 22 borrowers → **0.5**
          as well, because `S` is not COMPUTABLE rather than satisfied. §E.2:
          "S cannot be computed and contributes its full weight."

        The two 0.5s are deliberately the same number and deliberately not the
        same reason; the payload distinguishes them and the score does not,
        because `D_c` is one dimension and the notice is where the difference
        belongs.
        """
        for record in rows:
            flag = record.claim.attributes.get(ATTR_RECON_PLAUSIBLE)
            if flag == "true":
                return Decimal(1)
        return Decimal("0.5")


def read(
    booted: BootedFabric,
    asked: ProductRequest,
    *,
    principal_id: str | None = None,
    ignore_need_to_know: bool = False,
) -> FacilityScenario | None:
    """Name this deployment's artifact keys and read this question's values.

    Returns ``None`` when the anchor resolves to nothing — §D.2 step 1's
    fail-closed 404.

    ``ignore_need_to_know`` exists for gate `FTS-G03` and for nothing else. The
    gate has to show that the need-to-know condition DOES WORK, and the only
    way to show that is to remove it and observe the served set change. A
    two-condition policy where one condition is inert passes every
    set-difference check, so the removal has to be reachable — deliberately,
    from a test, through a named argument rather than by editing the artifact.
    """
    artifacts = booted.artifacts
    ttl = _declaration(TTL)
    declared_perspective = cast(PerspectiveArtifact, artifacts[KEY_PERSPECTIVE])
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

    # §D.2 step 2 — THE TWO CONDITIONS COMPOSE HERE, and this is the only place
    # they do. A principal WITHOUT facility-level need-to-know gets an EMPTY
    # allowlist and therefore sees no facility at all; a principal with it gets
    # the jurisdictions its grant expands to. The suppression case is reached
    # THROUGH the operator rather than around it, which is what keeps §B.2's
    # rule structural: there is no withheld set to leak a count from because
    # the permissible set was substituted for the full set upstream.
    permitted = (
        read_source.permitted_jurisdictions
        if (read_source.sees_need_to_know or ignore_need_to_know)
        else ()
    )
    declared_policy = cast(
        OperatorParametersArtifact, artifacts[KEY_POLICY_OPERATOR]
    )
    policy_parameters = declared_policy.model_copy(
        update={"permitted_classifications": tuple(permitted)}
    )

    return FacilityScenario(
        envelopes=read_source.envelopes,
        resolved=read_source.resolved,
        permitted_jurisdictions=read_source.permitted_jurisdictions,
        sees_need_to_know=read_source.sees_need_to_know,
        request=asked,
        request_contract=ProductRequestContract.from_declared(
            cast(Any, artifacts[KEY_REQUEST_CONTRACT])
        ),
        product_class=cast(ProductClassDeclaration, artifacts[KEY_PRODUCT_CLASS]),
        perspective=declared_perspective,
        operator_parameters={KEY_POLICY_OPERATOR: policy_parameters},
        resolution=cast(EntityResolutionSpec, artifacts[KEY_RESOLUTION]),
        half_life_table=cast(HalfLifeTable, artifacts[KEY_HALF_LIFE_TABLE]),
        debt_profile=cast(DebtProfile, artifacts[KEY_DEBT_PROFILE]),
        ttl_seconds=int(ttl["declared_ttl_seconds"]),
        max_ttl_seconds=int(ttl["max_ttl_seconds"]),
        halflife_debt_profile=(
            f"ccf-artifact://{booted.tenant_id}/ccf.debt-profile/"
            f"{KEY_DEBT_PROFILE}@{booted.pins.version_for(KEY_DEBT_PROFILE)}"
        ),
    )


# --------------------------------------------------------------------------
# Π — the projection.
# --------------------------------------------------------------------------
class FacilityTermsProjection:
    """Shape the resolved facility into the §D.6 emitted contract.

    **Π is NOT exercised as role-conditioning at this tier** (§A): the product
    returns the same SHAPE to every authorized caller. What differs per
    principal is which facilities EXIST to be shaped, and that is settled
    upstream by `Policy` (§D.2 step 2) — which is why the suppression rule holds
    structurally rather than by filtering here (§B.2).

    **`include_pricing_grid` is applied HERE**, at Π. It is the one parameter
    that changes the payload's SHAPE (§B.4), so applying it at Π keeps every
    value of it compiling to the same pinned read: what the caller's choice
    changes is the payload and therefore the content address, never what was
    read from the store.

    **NO SOURCE POINTER REACHES THIS PAYLOAD** — §C.4 trap 3, gate `FTS-G06`.
    `ccf_v2.facility` carries `source_accession`, `source_document` and
    `source_offsets` on 60 of 60 rows, so the character offsets into the credit
    agreement are available in the same row as the terms. They are not read into
    the graph and they are not shaped here. A T1 example that reaches into a
    document has silently become a T4 example, and this is the boundary the DATA
    does not enforce.
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

    def _number(self, attributes: Mapping[str, str], key: str) -> str | None:
        """One numeric term as the source carried it, or ``None``.

        Left as TEXT rather than parsed to a float. A commitment amount is a
        decimal quantity and a float is not bit-stable across platforms, which
        would put a per-platform value inside the content address (§D.4).
        """
        return attributes.get(key)

    def _pricing_grid(self, attributes: Mapping[str, str]) -> Any:
        """The tiered grid, as a STRUCTURE — §C.4 trap 4, gate `FTS-G07`.

        `basis` plus a `tiers` list, never a single headline margin. A store
        that could hold only a scalar does not fail loudly: it returns *a*
        margin, and a credit officer reading it during an amendment negotiation
        cannot tell that the leverage tiers it depends on were discarded. So the
        absence of a grid is `NOT_EVALUABLE` and a flattened one is not
        produced at all.
        """
        import json

        raw = attributes.get(ATTR_PRICING_GRID)
        if raw is None:
            return NOT_EVALUABLE
        # `parse_float=Decimal`, AND IT IS A MEASURED CONSTRAINT RATHER THAN A
        # PRECAUTION. The grid's leverage thresholds are `1.0`, `1.5`, `2.0` in
        # the store's JSON, and `json.loads` hands those back as Python floats.
        # `src/ccf/contracts/canonical.py::_normalize` REFUSES a float —
        # *"not bit-stable across platforms"* — so the first run of this example
        # died inside `content_hash` while building the replay record.
        #
        # That is the fabric working. A content-addressed payload cannot carry a
        # value whose bytes depend on the machine that serialized it, and a
        # pricing tier is a decimal quantity that was never a float in the
        # credit agreement either. Rung 01 met the same refusal from the other
        # direction, on a bare `debt_tolerance: 0.25` in a YAML artifact.
        # **Twice now, from two different document formats** — recorded at
        # spec §F.4 finding 9, because an adopter carrying any JSON structure
        # out of a store into a served payload will meet it on their first run.
        grid = json.loads(raw, parse_float=Decimal)
        return {
            "basis": grid.get("basis", NOT_EVALUABLE),
            # THE TIER THRESHOLD IS TEXT, for the same reason `_number` gives
            # for every other decimal quantity in this payload: a leverage
            # threshold is a decimal, a float is not bit-stable, and a `Decimal`
            # survives the content address but not a client's `json.dumps`.
            # Text is the one representation that is stable in the hash AND
            # renderable by a caller, and it keeps one rule for numbers across
            # the whole payload rather than two.
            #
            # `margin_bps` stays an INT because it genuinely is one — basis
            # points are whole numbers, and `int` is canonically encodable.
            "tiers": [
                {
                    "leverage_le": str(tier.get("leverage_le")),
                    "margin_bps": int(tier.get("margin_bps")),
                }
                for tier in grid.get("tiers", [])
            ],
        }

    def invoke(
        self,
        *,
        view: GraphView,
        operator_outputs: Mapping[str, Any],
        perspective: Perspective,
        temporal_boundary: datetime,
    ) -> ProjectionOutput:
        include_grid = bool(
            self._scenario.request.parameters.get(
                PARAM_INCLUDE_PRICING_GRID, True
            )
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
            # this facility — either because its borrower's jurisdiction is
            # outside the grant, or because the principal carries no
            # facility-level need-to-know at all.
            #
            # §B.2's suppression rule: no count, no marker, no placeholder
            # saying anything was withheld, AND NO WAY TO TELL THE TWO REASONS
            # APART. `FTS-G04` asserts that this payload is indistinguishable
            # from the one a principal gets for a facility that does not exist —
            # a `"not entitled"` message and a `404` are different disclosures
            # and only one of them is allowed.
            return ProjectionOutput(
                plan_id=self._plan_id,
                payload={
                    "facility": None,
                    "perspective_role": perspective.role,
                },
            )

        attributes = record.claim.attributes
        resolved = self._scenario.resolved

        facility: dict[str, Any] = {
            # FROM THE RESOLVED ROW, NOT FROM `attributes`. `facility_id` is an
            # IDENTITY KEY in `ccf_config.yaml`'s resolution spec, and an
            # identity key is consumed by the resolver to mint the entity rather
            # than stored back as an attribute — so `attributes.get(...)` returns
            # None and the first run of this example printed
            # `"facility_id": null` beside a fully populated record.
            #
            # Taking it from the resolved row rather than from
            # `request.subject` is deliberate: the request's subject is what the
            # CALLER asked for, and echoing it would render identically whether
            # or not anything resolved. This is the value the store returned.
            ATTR_FACILITY_ID: resolved.facility_id,
            # The canonical URI L2 minted for it — the fabric's own name for
            # this instrument, which exists only because the write path ran.
            "entity_id": record.claim.entity_uri,
            # Not in the request — it exists here only because the step read the
            # row and carried the join through. The assembly recipe's step-1
            # witness is on this key for exactly that reason.
            ATTR_BORROWER_LEI: attributes.get(ATTR_BORROWER_LEI),
            ATTR_BORROWER_NAME: attributes.get(ATTR_BORROWER_NAME, NOT_EVALUABLE),
            # The attribute Policy filtered on, returned as well as filtered on:
            # a product that filters on a field it does not return cannot be
            # audited from its own payload.
            ATTR_BORROWER_JURISDICTION: attributes.get(ATTR_BORROWER_JURISDICTION),
            ATTR_FACILITY_TYPE: attributes.get(ATTR_FACILITY_TYPE),
            ATTR_COMMITMENT: self._number(attributes, ATTR_COMMITMENT),
            ATTR_CURRENCY: attributes.get(ATTR_CURRENCY),
            ATTR_EFFECTIVE_DATE: attributes.get(ATTR_EFFECTIVE_DATE),
            ATTR_MATURITY_DATE: attributes.get(ATTR_MATURITY_DATE),
            # §C.4 trap 1 — NOT_EVALUABLE rather than a negative number when the
            # source's two dates do not admit a tenor. The only derived field in
            # this payload, and the only one that could report arithmetic as a
            # term.
            "tenor_days": (
                resolved.tenor_days
                if resolved.tenor_days is not None
                else NOT_EVALUABLE
            ),
            ATTR_ADMIN_AGENT: attributes.get(ATTR_ADMIN_AGENT),
            # §C.4 trap 2 — A COUNT, AND NO DATE. The estate holds
            # `amendment_count` and no amendment effective date anywhere, so the
            # payload states what can be evidenced and is silent on what cannot.
            # A synthetic date here would look filed.
            ATTR_AMENDMENT_COUNT: int(attributes.get(ATTR_AMENDMENT_COUNT, "0")),
            ATTR_AMENDED_RESTATED: attributes.get(ATTR_AMENDED_RESTATED) == "true",
            ATTR_SYNDICATED: attributes.get(ATTR_SYNDICATED) == "true",
            ATTR_OUTSTANDING: self._number(attributes, ATTR_OUTSTANDING),
            ATTR_UNDRAWN: self._number(attributes, ATTR_UNDRAWN),
            # The 1-day signal's OWN observation date, separate from
            # `contract.assembled_at` and from `ttl_basis_value`. Three dates
            # that mean three different things; collapsing any two is how a
            # 1-day signal starts wearing a 540-day signal's currency (§E.1).
            ATTR_BALANCE_AS_OF: attributes.get(ATTR_BALANCE_AS_OF, NOT_EVALUABLE),
            ATTR_RATING: attributes.get(ATTR_RATING),
        }
        if include_grid:
            facility[ATTR_PRICING_GRID] = self._pricing_grid(attributes)

        payload: dict[str, Any] = {
            "facility": facility,
            "perspective_role": perspective.role,
            # §E.2's `S`, surfaced rather than folded silently into one number.
            # The two ways `S` is reduced are DIFFERENT FINDINGS sharing one
            # score, and this is where they are told apart.
            "corroboration": self._corroboration(attributes),
        }
        return ProjectionOutput(plan_id=self._plan_id, payload=payload)

    def _corroboration(self, attributes: Mapping[str, str]) -> Mapping[str, Any]:
        """Whether the borrower's own filed debt corroborates this facility.

        `S` is one number and these are three states (§E.2). The score cannot
        distinguish "checked and disagreed" from "could not be checked", and a
        reader acting on the product needs to.
        """
        flag = attributes.get(ATTR_RECON_PLAUSIBLE)
        if flag is None:
            return {
                "status": "not-computable",
                "reason": "the borrower has no debt reconciliation row",
                "reported_debt": NOT_EVALUABLE,
            }
        return {
            "status": "plausible" if flag == "true" else "implausible",
            "reason": (
                "committed amounts are consistent with the borrower's reported debt"
                if flag == "true"
                else "committed amounts exceed the borrower's own reported debt"
            ),
            "reported_debt": attributes.get(ATTR_REPORTED_DEBT, NOT_EVALUABLE),
        }


def plan_class() -> type[FacilityTermsProjection]:
    """Π as a class the fabric constructs, never an object it is handed."""
    return FacilityTermsProjection
