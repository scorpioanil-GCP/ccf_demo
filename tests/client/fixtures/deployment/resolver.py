"""This deployment's own Python — the half `ccf_config.yaml` cannot hold.

Everything here is deployment code, exactly as
``examples/s1-00-companies-over-revenue/deployment.py`` is. It names all of this
deployment's vocabulary and **interprets** it out of ``ccf_config.yaml`` and
``scenario.yaml``; delete those two documents and nothing below has anything
left to work on. That is the No-Hardcoding Rule (CLAUDE.md §6.4) being
structural rather than aspirational, and it applies here because
``tools/lints/__main__.py::RULE_TREE_SCOPE`` scopes ``no-hardcoding`` to
``tests`` alongside ``src``, ``runtime`` and ``examples``.

``binding.yaml`` names the three factories below by ``<module>:<attribute>``
reference (``D-IMPL-141``, PROPOSED). The SDK calls them; it never reads a value
out of this file.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import yaml

from ccf.artifacts.file_store import FileArtifactStore
from ccf.client.adapters.binding_document import ResolverCall
from ccf.controlplane.artifacts import DebtProfile, HalfLifeTable
from ccf.controlplane.registry import ControlPlaneProtocol
from ccf.deployment import BootedFabric
from ccf.graph.protocols import GraphView
from ccf.halflife.assessment import DebtAssessment, DebtFactors
from ccf.halflife.debt import FreshnessScorer, assess_debt
from ccf.halflife.decay import Observation
from ccf.operators.base import OperatorOutput
from ccf.products.request import ProductRequest
from ccf.products.resolver import GovernedResolver, ServedProductResolverProtocol
from ccf.projection.plan import Perspective, ProjectionOutput

HERE = Path(__file__).parent
CONFIG = HERE / "ccf_config.yaml"
SCENARIO = HERE / "scenario.yaml"


def _document(path: Path) -> Mapping[str, Any]:
    """One of this deployment's own YAML documents, parsed."""
    return cast(Mapping[str, Any], yaml.safe_load(path.read_text(encoding="utf-8")))


# ---------------------------------------------------------------------------
# Where the graph lives — composed from this deployment's own document.
# ---------------------------------------------------------------------------
def connection(*, root: Path) -> Mapping[str, object]:
    """Compose the declared backend's settings from a path, never a credential.

    ``scenario.yaml`` states a **filename**, and this function resolves it
    against the deployment root it is handed. No host, no port, no secret and
    no environment read — which is exactly what lets the client conformance
    suite run with every substrate environment variable unset.
    """
    storage = _document(SCENARIO)["storage"]
    return {"database_path": str(root / storage["graph_filename"])}


# ---------------------------------------------------------------------------
# The question the caller asks.
# ---------------------------------------------------------------------------
def build_question(
    *,
    product_id: str,
    parameters: Mapping[str, Any],
    temporal_boundary: datetime | None,
) -> ResolverCall:
    """Turn a client's question into the two things the SDK cannot invent.

    The address tokens and the ``as_of=None`` default come from this
    deployment's ``scenario.yaml``; the perspective comes from
    ``ccf_config.yaml``'s ``default_perspective`` section. ``parameters`` is the
    **caller's** — this function supplies no value for it and no default, which
    is what lets the missing-parameter leg reach a governed refusal rather than
    a silently completed question.
    """
    question = _document(SCENARIO)["question"]
    config = _document(CONFIG)
    declared = config["product_class"]
    perspective = config["default_perspective"]
    return ResolverCall(
        perspective=Perspective(
            principal_id=perspective["principal_id"], role=perspective["role"]
        ),
        request=ProductRequest(
            schema_name=declared["schema_name"],
            schema_version=declared["schema_version"],
            subject=question["subject"],
            intent=question["intent"],
            freshness=question["freshness"],
            asked_at=temporal_boundary
            or datetime.fromisoformat(question["default_asked_at"]),
            parameters=parameters,
        ),
    )


# ---------------------------------------------------------------------------
# Π — the projection.
# ---------------------------------------------------------------------------
class _OverScoreProjection:
    """Keep the entities whose declared score exceeds the caller's number.

    The threshold is applied **here**, at Π, and never in the graph query — so
    every threshold compiles to the same pinned query and what the caller's
    number changes is the payload, and therefore the product's content address,
    rather than what was read.
    """

    def __init__(
        self, *, required: tuple[str, ...], request: ProductRequest
    ) -> None:
        self._required = required
        self._request = request
        self._scenario = _document(SCENARIO)

    @property
    def plan_id(self) -> str:
        return cast(str, _document(CONFIG)["product_class"]["schema_name"])

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
        attributes = self._scenario["attributes"]
        parameter = self._declared_parameter()
        threshold = Decimal(str(self._request.parameters[parameter]))
        surviving = sorted(
            (
                {
                    "name": record.claim.attributes[attributes["name"]],
                    "score": str(record.claim.attributes[attributes["score"]]),
                }
                for record in view.entities
                if Decimal(record.claim.attributes[attributes["score"]]) > threshold
            ),
            key=lambda entry: cast(str, entry["name"]),
        )
        return ProjectionOutput(
            plan_id=self.plan_id,
            payload={
                "role": perspective.role,
                "threshold": str(threshold),
                "assembled": len(list(view.entities)),
                "count": len(surviving),
                "widgets": surviving,
            },
        )

    @staticmethod
    def _declared_parameter() -> str:
        """The one required parameter, read off the declared request surface.

        Named here rather than spelled as a constant so this projection and the
        `request_contract:` section cannot drift: the document declares which
        parameter is required, and this reads that declaration.
        """
        required = _document(CONFIG)["request_contract"]["arguments"]["required"]
        return cast(str, required[0])


def _plan_factory(
    *, required: tuple[str, ...], request: ProductRequest
) -> _OverScoreProjection:
    return _OverScoreProjection(required=required, request=request)


# ---------------------------------------------------------------------------
# D_c — measured over what this question assembled (whitepaper §7.7).
# ---------------------------------------------------------------------------
def _debt_scorer(fabric: BootedFabric) -> Any:
    """Close a scorer over the λ_c table and the bands this deployment declared.

    Freshness is measured over the rows **assembled**, not the rows that
    survived Π: ``FreshnessScorer.score`` refuses an empty sequence by design,
    so scoring the survivors would make a threshold that admits nobody raise
    instead of answering.

    **The instant freshness is measured against is the newest observation in
    the assembly, and that is a fixture decision worth naming.**
    :class:`~ccf.products.resolver.GovernedResolver` takes one ``debt_scorer``
    at construction and calls it with the view alone, so a scorer cannot see
    the question's ``asked_at`` the way ``s1-00``'s per-question scenario
    object can. Scoring against the newest row therefore measures the
    **spread** of staleness across what was assembled rather than its absolute
    age — a real, reproducible number for a fixture whose rows are fixed
    instants, and not a stand-in for what a deployment measuring absolute age
    would write.
    """
    scenario = _document(SCENARIO)
    observation_type = _document(CONFIG)["resolution"]["entity_rules"][0][
        "entity_class"
    ]
    attributes = scenario["attributes"]
    table = cast(HalfLifeTable, fabric.artifacts["half_life"])
    profile = cast(DebtProfile, fabric.artifacts["debt_profile"])

    def score(*, view: GraphView) -> DebtAssessment:
        records = list(view.entities)
        if not records:
            # An assembly with no rows, which a temporal boundary before every
            # observation produces. Both factors are ZERO rather than absent:
            # nothing is known, so D_c = 1 − (0 · 0 · 1) = 1 and the deployment
            # fail-closes. Scoring it any other way would report a confident
            # answer about a graph that said nothing, which is the precise
            # failure the fail-closed posture exists to prevent — and
            # `FreshnessScorer.score` refuses an empty sequence by design, so
            # there is no "just call it anyway" branch to take.
            return assess_debt(
                DebtFactors(
                    freshness=Decimal(0),
                    completeness=Decimal(0),
                    semantic_consistency=Decimal(1),
                ),
                profile=profile,
            )
        observations = tuple(
            Observation(
                observation_type=observation_type,
                observed_at=record.claim.valid_from,
                subject=record.claim.entity_uri,
            )
            for record in records
        )
        expected = (attributes["name"], attributes["score"])
        populated = sum(
            1
            for record in records
            if all(record.claim.attributes.get(key) for key in expected)
        )
        scorer = FreshnessScorer(
            table=table, risk_sensitivity=profile.risk_sensitivity
        )
        return assess_debt(
            DebtFactors(
                freshness=scorer.score(
                    observations, now=max(o.observed_at for o in observations)
                ),
                completeness=Decimal(populated) / Decimal(len(records)),
                semantic_consistency=Decimal(1),
            ),
            profile=profile,
        )

    return score


# ---------------------------------------------------------------------------
# The resolver this deployment plugs into the in-process seam.
# ---------------------------------------------------------------------------
def build_resolver(
    *, fabric: BootedFabric, control_plane: ControlPlaneProtocol
) -> ServedProductResolverProtocol:
    """Wire the SDK's reference composition against this deployment's values.

    Every argument below is this deployment's; none has a default in the SDK.
    The keys are read from ``scenario.yaml`` rather than spelled here, and the
    two TTL figures stay two.
    """
    scenario = _document(SCENARIO)
    keys = scenario["keys"]
    ttl = scenario["ttl"]
    classes = scenario["artifact_classes"]
    return GovernedResolver(
        fabric=fabric,
        control_plane=control_plane,
        product_class_key=keys["product_class"],
        request_contract_key=keys["request_contract"],
        operator_parameter_keys=tuple(keys["operator_parameters"]),
        policy_bundle_key=keys["policy"],
        plan_factory=_plan_factory,
        debt_scorer=_debt_scorer(fabric),
        artifact_store=FileArtifactStore(
            root=HERE / scenario["storage"]["artifact_store_dirname"]
        ),
        replay_record_class=classes["replay_record"],
        query_pin_class=classes["query_pin"],
        max_ttl_seconds=int(ttl["max_seconds"]),
        product_ttl_seconds=int(ttl["product_seconds"]),
    )
