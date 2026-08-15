"""This deployment's own values — the other half of ``produce.py``.

[ADAPT] Everything here is yours to change. [MECHANISM] nothing.

``produce.py`` beside this file is CCF's calls and names none of the vocabulary
below. This file names all of it and makes no fabric call the spine does not.
Delete ``ccf_config.yaml`` and nothing here has anything left to interpret —
which is the No-Hardcoding Rule (CLAUDE.md §6.4) being structural rather than
aspirational. (Before `16-31`, this deployment authored the same claim across
ten documents under ``artifacts/config/``; `D-IMPL-136`'s AMENDMENT of
2026-08-15 converts HW-1 to the one-file form, and this sentence is still
true of it.)

**The structural difference from ``s1-01``: L1 comes from a database.** ``s1-01``
authors 341 lines of ``events.yaml``; this deployment reads its source table and
emits one envelope per row. An adopter's signal comes from the system they
already run, not from a fixture — and the row's ``last_updated`` becomes the
envelope's ``observed_time``, which is the whole reason a plain SELECT and this
example differ.

**The threshold is applied in Π, and that is worth stating plainly.** The
compiled graph query is therefore the *same* for every threshold: what varies
with the caller's number is the payload, and hence the product's content
address — not the pinned query. ``D-IMPL-126``'s naive-projection finding is why
this is written down rather than left for a reader to discover.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import psycopg
import yaml

from ccf.contracts.base import CCFContract
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
from ccf.operators.base import OperatorOutput
from ccf.products.request import ProductRequest, ProductRequestContract
from ccf.projection.plan import Perspective, ProjectionOutput
from ccf.signal.envelope import SignalEnvelope, SourceIdentity

HERE = Path(__file__).parent
SCENARIO = HERE / "scenario"
#: The single authored Control Plane document (`D-IMPL-136`'s AMENDMENT).
#: Named `MANIFEST` still — not `CCF_CONFIG` — solely so `consume.py`'s
#: `deployment.MANIFEST` reference needs no edit; the value is
#: `ccf_config.yaml`, not a manifest, and every use below reads it as such.
MANIFEST = HERE / "ccf_config.yaml"

# --- This deployment's Control Plane vocabulary. These are the manifest `key:`
#     values `derive_deployment` derives from `ccf_config.yaml`'s own section
#     names, and this is the only place they are written down.
KEY_PERSPECTIVE = "default_perspective"
KEY_PRODUCT_CLASS = "product_class"
KEY_REQUEST_CONTRACT = "request_contract"
KEY_HALF_LIFE_TABLE = "half_life"
KEY_DEBT_PROFILE = "debt_profile"
KEY_POLICY_BUNDLE = "policy"
#: An `operators:` entry's key is the operator id itself (`derive_deployment`
#: derives no shorter alias) — never `"temporal"` alone, which was only ever
#: the multi-file manifest's own `key:` override for the same artifact.
KEY_TEMPORAL = "temporal.as-of-boundary"

#: The declared request parameter the caller supplies. Declared REQUIRED in
#: `ccf_config.yaml`'s `request_contract:` section; nothing in this tree
#: defaults it.
THRESHOLD_PARAMETER = "revenue_threshold"

# --- THIS DEPLOYMENT'S SCENARIO VOCABULARY — the source system it reads. NOT
#     CCF's. These name columns in `scenario/schema.sql`; an adopter replaces
#     them with their own table's.
TABLE = "companies"
COLUMN_ID = "id"
COLUMN_NAME = "name"
COLUMN_REVENUE = "revenue"
COLUMN_UPDATED = "last_updated"

#: How a row's fields are named once they are inside the fabric. These match
#: `attribute_keys` in `ccf_config.yaml`'s `resolution:` section.
ATTR_REF = "company_ref"
ATTR_NAME = "company_name"
ATTR_REVENUE = "company_revenue"

#: The λ_c entry in `ccf_config.yaml`'s `half_life:` section these rows decay
#: by, and the entity class the `resolution:` section resolves them to. One
#: class, one curve — which is why this example's debt story fits on one line.
OBSERVATION_TYPE = "company"

#: How long a served answer stays servable. The class's declared ceiling is a
#: field default on :class:`RevenueScenario`, beside the rest of what one run
#: carries.
TTL_SECONDS = 600

# --- `backends.yaml` vocabulary: the three value sources, and nothing else.
PROFILES = "profiles"
SETTINGS = "settings"
FROM_ENV = "from_env"
PER_RUN = "per_run"
PREFIX = "prefix"
REMEDY = "remedy"
DECLARATION = "declaration"


def _document(path: Path) -> Mapping[str, Any]:
    """One of this deployment's own YAML documents, parsed."""
    return cast(Mapping[str, Any], yaml.safe_load(path.read_text(encoding="utf-8")))


# --------------------------------------------------------------------------
# Where the graph lives — composed, never written down.
# --------------------------------------------------------------------------
def connection(*, root: Path) -> Mapping[str, str]:
    """Compose the declared backend kind's settings (threat ``T-16-25-01``).

    The only branch here is over the two value SOURCES this example uses, never
    over a substrate name: ``ccf_config.yaml`` declares the KIND (its
    top-level ``backend:``) and ``backends.yaml`` says how that kind's
    settings are composed. No host, port, path or credential is read from any
    document — only a variable's NAME.
    """
    kind = _document(MANIFEST)["backend"]
    profiles = _document(HERE / "backends.yaml")[DECLARATION][PROFILES]
    settings: Mapping[str, Any] = profiles[kind][SETTINGS]
    composed: dict[str, str] = {}
    for setting, source in settings.items():
        if FROM_ENV in source:
            variable = source[FROM_ENV]
            value = os.environ.get(variable, "")
            if not value:
                raise RuntimeError(
                    f"{variable} is unset; {source[REMEDY]}. It supplies"
                    f" `{setting}`, which backends.yaml"
                    " declares this deployment reads from the environment."
                    " There is no default and no fallback to another backend."
                )
            composed[setting] = value
        else:
            composed[setting] = f"{source[PREFIX]}_{uuid.uuid4().hex}"
    return composed


# --------------------------------------------------------------------------
# The question the caller asks.
# --------------------------------------------------------------------------
def request(
    *, parameters: Mapping[str, object], asked_at: datetime | None = None
) -> ProductRequest:
    """Build the typed question from the caller's parameters and this
    deployment's declared vocabulary.

    The three address tokens come from ``scenario/question.yaml`` and the class
    identity from ``ccf_config.yaml``'s ``product_class:`` section.
    ``parameters`` is the CALLER's — this function supplies no value for it
    and no default.
    """
    question = _document(SCENARIO / "question.yaml")[DECLARATION]
    declared = _document(MANIFEST)["product_class"]
    return ProductRequest(
        schema_name=declared["schema_name"],
        schema_version=declared["schema_version"],
        subject=question["subject"],
        intent=question["intent"],
        freshness=question["freshness"],
        asked_at=asked_at or datetime.fromisoformat(question.get("asked_at", DEFAULT_ASKED_AT)),
        parameters=parameters,
    )


#: The instant the bundled demonstration asks as of. A caller who wants another
#: passes `--as-of`; the seeded rows are fixed instants so this is reproducible.
DEFAULT_ASKED_AT = "2026-08-01T00:00:00+00:00"


# --------------------------------------------------------------------------
# L1 — the signal, read from the source system.
# --------------------------------------------------------------------------
def envelopes(tenant_id: str, *, at: datetime) -> tuple[SignalEnvelope, ...]:
    """One L1 envelope per source row.

    The row's ``last_updated`` becomes ``observed_time`` — which becomes the
    claim's ``observed_at``, which is what the λ_c curve reads. That single
    mapping is what turns a column a plain SELECT ignores into a measured D_c.
    """
    dsn = connection(root=Path("."))["dsn"]
    with psycopg.connect(dsn) as db, db.cursor() as cursor:
        cursor.execute(  # noqa: S608 — names come from this module's own block
            f"select {COLUMN_ID}, {COLUMN_NAME}, {COLUMN_REVENUE},"
            f" {COLUMN_UPDATED} from {TABLE} order by {COLUMN_ID}"
        )
        rows = cursor.fetchall()
    return tuple(
        SignalEnvelope(
            tenant_id=tenant_id,
            envelope_id=f"{TABLE}/{row[0]}",
            source=SourceIdentity(system_id=TABLE),
            ingestion_timestamp=at,
            observed_time=row[3],
            raw_payload={
                ATTR_REF: str(row[0]),
                ATTR_NAME: row[1],
                ATTR_REVENUE: str(row[2]),
            },
        )
        for row in rows
    )


# --------------------------------------------------------------------------
# What one run needs — satisfies `produce.Scenario` structurally.
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class RevenueScenario:
    """This deployment's answers to what the spine asks for."""

    envelopes: tuple[SignalEnvelope, ...]
    request: ProductRequest
    request_contract: ProductRequestContract
    product_class: ProductClassDeclaration
    perspective: PerspectiveArtifact
    operator_parameters: Mapping[str, OperatorParametersArtifact]
    half_life_table: HalfLifeTable
    debt_profile: DebtProfile

    request_contract_key: str = KEY_REQUEST_CONTRACT
    policy_bundle_key: str = KEY_POLICY_BUNDLE
    replay_record_class: str = "hw1.replay-record"
    query_pin_class: str = "hw1.graph-query"
    artifact_store_dirname: str = "artifacts-store"
    max_ttl_seconds: int = 3600

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
        return self.request.asked_at + timedelta(seconds=TTL_SECONDS)

    def debt(self, view: GraphView) -> DebtAssessment:
        """D_c over what this question assembled (whitepaper §7.7).

        **F is measured over the rows ASSEMBLED, not the rows SELECTED**, and
        that is a deliberate decision rather than an accident of where the call
        sits. ``FreshnessScorer.score`` refuses an empty sequence by design, so
        scoring the survivors would make a threshold that admits nobody raise
        instead of answering. Freshness therefore describes what the fabric
        *read*; completeness describes what survived being read.

        C is the fraction of assembled rows carrying every attribute the
        resolution spec declares. S is 1: there is exactly one source here, and
        a single source cannot disagree with itself — stated rather than left as
        a magic constant, and the honest setup for a later example where debt
        only gets interesting once assembly spans sources that *do* disagree.

        **Decay is measured from ``valid_from``, not from ``observed_at``, and
        the choice is the whole example.** CCF's T axis is bitemporal:
        ``observed_at`` is when the *fabric* learned a claim, ``valid_from`` is
        when the *source's* fact began to hold — and ``SignalEnvelope
        .observed_time`` (this deployment's ``last_updated``) lands in the
        latter. Scoring ``observed_at`` here would measure the age of *this
        run*, so a two-year-old row re-read a moment ago would score as
        perfectly fresh: a source outage laundered into a low-debt reading,
        which is the precise failure the fail-closed posture exists to prevent.
        The SDK owes the structure and none of this judgement (``D-IMPL-117``);
        Dave's instruction — *"use last update as the input for context debt"* —
        is what it is exercised as.
        """
        records = list(view.entities)
        observations = tuple(
            Observation(
                observation_type=OBSERVATION_TYPE,
                observed_at=record.claim.valid_from,
                subject=record.claim.entity_uri,
            )
            for record in records
        )
        # The identity key is not among them: `company_ref` resolves to the
        # entity's URI, so a row missing it produced no entity to count.
        expected = (ATTR_NAME, ATTR_REVENUE)
        populated = sum(
            1
            for record in records
            if all(record.claim.attributes.get(key) for key in expected)
        )
        scorer = FreshnessScorer(
            table=self.half_life_table,
            risk_sensitivity=self.debt_profile.risk_sensitivity,
        )
        return assess_debt(
            DebtFactors(
                freshness=scorer.score(observations, now=self.now),
                completeness=Decimal(populated) / Decimal(len(records)),
                semantic_consistency=Decimal(1),
            ),
            profile=self.debt_profile,
        )


def read(booted: BootedFabric, asked: ProductRequest) -> RevenueScenario:
    """Name this deployment's artifact keys and read this question's values."""
    artifacts = booted.artifacts
    return RevenueScenario(
        envelopes=envelopes(booted.tenant_id, at=asked.asked_at),
        request=asked,
        # The 16-22 papercut repair (D-IMPL-126 item 1). The four fields are NOT
        # hand-transcribed here; that workaround is what this call replaces.
        request_contract=ProductRequestContract.from_declared(
            cast(Any, artifacts[KEY_REQUEST_CONTRACT])
        ),
        product_class=cast(ProductClassDeclaration, artifacts[KEY_PRODUCT_CLASS]),
        perspective=cast(PerspectiveArtifact, artifacts[KEY_PERSPECTIVE]),
        # ONE entry, so ONE operator (D-IMPL-132). The spine never counts them.
        operator_parameters={
            KEY_TEMPORAL: cast(
                OperatorParametersArtifact, artifacts[KEY_TEMPORAL]
            )
        },
        half_life_table=cast(HalfLifeTable, artifacts[KEY_HALF_LIFE_TABLE]),
        debt_profile=cast(DebtProfile, artifacts[KEY_DEBT_PROFILE]),
    )


# --------------------------------------------------------------------------
# Π — the projection.
# --------------------------------------------------------------------------
class OverThresholdProjection:
    """Keep the entities whose declared amount exceeds the caller's number.

    **The threshold is applied HERE**, at Π, and never in the graph query. The
    consequence is worth being explicit about: every threshold compiles to the
    same pinned query, so what the caller's number changes is the *payload* —
    and therefore the product's content address — rather than what was read.
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
        operator_outputs: Mapping[str, OperatorOutput],
        perspective: Perspective,
        temporal_boundary: datetime,
    ) -> ProjectionOutput:
        threshold = Decimal(
            str(self._scenario.request.parameters[THRESHOLD_PARAMETER])
        )
        surviving = sorted(
            (
                {
                    "name": record.claim.attributes[ATTR_NAME],
                    "revenue": str(record.claim.attributes[ATTR_REVENUE]),
                    # `valid_from`, not `observed_at` — the source's instant,
                    # not this run's. Same bitemporal reading `debt()` uses,
                    # and for the same reason.
                    "last_updated": record.claim.valid_from.isoformat(),
                }
                for record in view.entities
                if Decimal(record.claim.attributes[ATTR_REVENUE]) > threshold
            ),
            key=lambda entry: cast(str, entry["name"]),
        )
        return ProjectionOutput(
            plan_id=self._plan_id,
            payload={
                "role": perspective.role,
                "threshold": str(threshold),
                "assembled": len(list(view.entities)),
                "count": len(surviving),
                "companies": surviving,
            },
        )


def plan_class() -> type[OverThresholdProjection]:
    """Π as a class the fabric constructs, never an object it is handed."""
    return OverThresholdProjection
