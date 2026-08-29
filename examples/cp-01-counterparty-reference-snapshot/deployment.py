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
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import psycopg
import yaml

from ccf.projection.plan import Perspective
from ccf.products.request import ProductRequest
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
