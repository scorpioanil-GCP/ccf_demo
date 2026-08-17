"""This deployment's projection — **the one thing it is permitted to write.**

`D-IMPL-141` (RESOLVED, Dave, 2026-08-16) and Amendment A.3 of
``docs/superpowers/specs/2026-08-16-reference-plan-factory-and-debt-scorer.md``.
Everything else this deployment contributes is **data** in ``binding.yaml`` and
``ccf_config.yaml``. This module exists because
:class:`~ccf.projection.plan.ProjectionPlan` is itself a Protocol — code, not
data — and no declarative plan artifact exists in the tree, so mapping a
:class:`~ccf.graph.protocols.GraphView` of entities onto a payload schema's
declared fields would be *invention* if the SDK attempted it.

**This file is the producer's world and it is opaque to the reader.** The
example a reader studies is ``../consume.py``, which is eighty lines and imports
:mod:`ccf.client` and stdlib. A curious reader may open this; nobody has to.
There is no ``resolver.py`` here, and there is not going to be one: ``17-12``
removed that shape and
:data:`~ccf.client.adapters.binding_document.RULED_OUT_KEYS` refuses
``resolver:`` by name.

It names this deployment's vocabulary and **interprets** it out of
``ccf_config.yaml`` and ``scenario.yaml``; delete those two documents and
nothing below has anything left to work on. That is the No-Hardcoding Rule
(CLAUDE.md §6.4) being structural rather than aspirational.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import yaml

from ccf.graph.protocols import GraphView
from ccf.operators.base import OperatorOutput
from ccf.products.request import ProductRequest
from ccf.projection.plan import Perspective, ProjectionOutput

HERE = Path(__file__).parent
CONFIG = HERE / "ccf_config.yaml"
SCENARIO = HERE / "scenario.yaml"


def _document(path: Path) -> Mapping[str, Any]:
    """One of this deployment's own YAML documents, parsed."""
    return cast(Mapping[str, Any], yaml.safe_load(path.read_text(encoding="utf-8")))


class _OverRevenueProjection:
    """Keep the companies whose declared revenue exceeds the caller's number.

    The threshold is applied **here**, at Π, and never in the graph query — so
    every threshold compiles to the same pinned query and what the caller's
    number changes is the payload, and therefore the product's content address,
    rather than what was read.
    """

    def __init__(self, *, required: tuple[str, ...], request: ProductRequest) -> None:
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
                    "revenue": str(record.claim.attributes[attributes["revenue"]]),
                }
                for record in view.entities
                if Decimal(record.claim.attributes[attributes["revenue"]]) > threshold
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
                "companies": surviving,
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


def build_projection(
    *, required: tuple[str, ...], request: ProductRequest
) -> _OverRevenueProjection:
    """The deployment's ``ProjectionPlanFactoryProtocol`` — its whole surface.

    A factory rather than a plan because a plan interpreting a caller's
    parameters has to *see* them, which is the distinction between an assembled
    product and a configured one.
    """
    return _OverRevenueProjection(required=required, request=request)
