"""The semantic stage — and the fail-loud stand-in that keeps CI honest.

**NAMED `memo_packaging`, NOT `packaging`, and that is not fastidiousness.**
`packaging` is an installed distribution in this very venv, so a module by that
name here is reachable or shadowed depending on `sys.path` order — measured
2026-09-23, when the test suite imported the distribution and failed on
`PackagedSection`. It is the `AIA-F-07` bare-name collision in a new costume:
a tree's module names share one namespace with everything installed beside it.
Recorded as `PKG-F-02`.

`DR-SPEC-002` R4 (Dave, 2026-09-23): *"the stub suffices; a green build never
depends on a model provider."*

**Two callers of one seam.** :class:`PackagingModel` is what the acquisition
seam holds. :class:`DeterministicPackager` is the shipped implementation and it
calls no network at all; :class:`AnthropicPackager` is opt-in, reached only
when the deployment names a real model, and is never required for a green
build.

**Why the stub is not a mock.** It is the `hw1-harness-clients` leg-2
discipline, which this copies rather than imports: a stand-in that **fails
loudly on anything it was not told to answer**. A permissive stub that
returned plausible text for any input would make the smoothing gate pass
against prose nobody wrote, which is the one thing this rung cannot afford.

**The stub is still a renderer, not an oracle.** It reads the figures out of
the product it is handed and writes them into sentences. It cannot invent a
figure — which is what makes the smoothing gate's *sabotage* meaningful: to
redden that gate the test has to make the packager lie on purpose, and a stub
that could lie by accident would have made the gate untestable.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import Any, Protocol

__all__ = [
    "AnthropicPackager",
    "DeterministicPackager",
    "PackagedSection",
    "PackagingModel",
    "PackagingRefused",
]


class PackagingRefused(RuntimeError):
    """The packager could not render what it was asked for, and says so.

    Raised rather than returning empty prose: a section that silently came
    back blank would reach the smoothing gate as "no figures claimed", pass
    it, and serve a memo with a hole in it.
    """


class PackagedSection:
    """One rendered heading, with the figures it actually cited.

    ``figures_cited`` is not decoration. The smoothing gate checks it against
    the substrate, so a packager that renders a figure without declaring it
    here is a packager whose prose the gate cannot verify — and an undeclared
    figure is treated as an unsupported one.
    """

    __slots__ = ("heading", "audience", "prose", "figures_cited")

    def __init__(
        self,
        *,
        heading: str,
        audience: str,
        prose: str,
        figures_cited: Sequence[str],
    ) -> None:
        self.heading = heading
        self.audience = audience
        self.prose = prose
        self.figures_cited = tuple(figures_cited)


class PackagingModel(Protocol):
    """The one seam the acquisition stage holds."""

    @property
    def model_version(self) -> str:
        """The version pinned on dimension 3. Never a display name."""

    @property
    def temperature(self) -> str:
        """As text, so an unreported value is a named absence, not a `0.0`."""

    def package(
        self, *, product: Mapping[str, Any], headings: Sequence[Mapping[str, Any]]
    ) -> tuple[PackagedSection, ...]:
        """Render ``headings`` over ``product``."""


def _figures(product: Mapping[str, Any]) -> dict[str, str]:
    """Every scalar the product carries, flattened to `path -> text`.

    The smoothing gate's universe of supported figures. Flattened rather than
    walked per-heading because the gate's question is *"does the substrate
    carry this number anywhere"* — a figure moved between sections is a
    packaging choice, while a figure present nowhere is the defect.
    """
    found: dict[str, str] = {}

    def walk(node: Any, path: str) -> None:
        if isinstance(node, Mapping):
            for key, value in node.items():
                walk(value, f"{path}.{key}" if path else str(key))
        elif isinstance(node, (list, tuple)):
            for index, value in enumerate(node):
                walk(value, f"{path}[{index}]")
        elif node is not None and not isinstance(node, bool):
            found[path] = str(node)

    walk(product, "")
    return found


class DeterministicPackager:
    """The shipped packager: renders from the product, invents nothing.

    It answers only the headings the prompt artifact declares and raises on
    anything else — the fail-loud half. Its ``model_version`` names itself
    rather than borrowing a provider's, because a record claiming a frontier
    model wrote prose a local function wrote would be the exact repudiation
    failure every sentinel in the replay record exists to close.
    """

    def __init__(self, *, temperature: str = "0.0") -> None:
        self._temperature = temperature

    @property
    def model_version(self) -> str:
        return "dr-02-deterministic-packager/1.0.0"

    @property
    def temperature(self) -> str:
        return self._temperature

    def package(
        self, *, product: Mapping[str, Any], headings: Sequence[Mapping[str, Any]]
    ) -> tuple[PackagedSection, ...]:
        figures = _figures(product)
        rendered: list[PackagedSection] = []
        for heading in headings:
            name = str(heading["id"])
            renderer = getattr(self, f"_render_{name}", None)
            if renderer is None:
                raise PackagingRefused(
                    f"this packager was asked for heading {name!r}, which it was"
                    " never told how to render. A stand-in that answered anyway"
                    " would put prose nobody wrote past the smoothing gate."
                )
            prose, cited = renderer(product, figures)
            rendered.append(
                PackagedSection(
                    heading=name,
                    audience=str(heading["audience"]),
                    prose=prose,
                    figures_cited=cited,
                )
            )
        return tuple(rendered)

    # -- one renderer per declared heading ---------------------------------

    def _render_coverage(
        self, product: Mapping[str, Any], figures: Mapping[str, str]
    ) -> tuple[str, tuple[str, ...]]:
        ratio = _first(figures, "coverage_ratio", "priority_adjusted_coverage_ratio")
        commitment = _first(figures, "commitment", "commitment_amount")
        cited = tuple(value for value in (ratio, commitment) if value is not None)
        if ratio is None:
            return (
                "The product carries no coverage ratio for this facility, so the"
                " position cannot be stated here.",
                cited,
            )
        parts = [f"Priority-adjusted coverage stands at {ratio}."]
        if commitment is not None:
            parts.append(f"The facility's commitment is {commitment}.")
        return (" ".join(parts), cited)

    def _render_collateral(
        self, product: Mapping[str, Any], figures: Mapping[str, str]
    ) -> tuple[str, tuple[str, ...]]:
        assets = _assets(product)
        if not assets:
            return (
                "The product reports no collateral reaching this facility.",
                (),
            )
        cited: list[str] = []
        clauses: list[str] = []
        for asset in assets:
            realizable = asset.get("realizable_value")
            lien = asset.get("lien_position")
            label = asset.get("description") or asset.get("uri") or "an unlabelled asset"
            if realizable is not None:
                cited.append(str(realizable))
            clause = f"{label} contributes {realizable}" if realizable is not None else f"{label} carries no realizable value in this product"
            if lien is not None:
                cited.append(str(lien))
                clause += f" at lien position {lien}"
            clauses.append(clause)
        # NO COUNT. `len(assets)` is a figure this packager would have
        # COMPUTED, and the substrate does not carry it — the smoothing gate
        # refused exactly that on this rung's first honest run, which is the
        # gate doing its job on its own author. The prose states what it was
        # given and nothing it derived.
        return (
            "The following secure this facility: " + "; ".join(clauses) + ".",
            tuple(cited),
        )

    def _render_freshness(
        self, product: Mapping[str, Any], figures: Mapping[str, str]
    ) -> tuple[str, tuple[str, ...]]:
        ages = [
            str(asset["valuation_age_days"])
            for asset in _assets(product)
            if asset.get("valuation_age_days") is not None
        ]
        if not ages:
            return (
                "The product carries no valuation ages, so the currency of the"
                " position cannot be stated here.",
                (),
            )
        oldest = max(ages, key=lambda value: Decimal(value))
        return (
            f"The oldest valuation behind this position is {oldest} days old.",
            (oldest,),
        )


def _assets(product: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    for key in ("assets", "collateral", "pledges"):
        found = product.get(key)
        if isinstance(found, (list, tuple)):
            return tuple(item for item in found if isinstance(item, Mapping))
    return ()


def _first(figures: Mapping[str, str], *suffixes: str) -> str | None:
    for suffix in suffixes:
        for path, value in figures.items():
            if path.split(".")[-1] == suffix:
                return value
    return None


class AnthropicPackager:
    """The opt-in real model. Never reached by a test, never required by CI.

    Constructed only when the deployment names a provider model, which the
    shipped environment document does not. It exists so the seam is honest —
    a Mode 2 demonstration whose only packager is a local function would be
    demonstrating a shape rather than a capability — and its one recorded run
    is evidence in `FINDINGS.md` rather than a gate.
    """

    def __init__(self, *, model: str, temperature: str, instruction: str) -> None:
        self._model = model
        self._temperature = temperature
        self._instruction = instruction

    @property
    def model_version(self) -> str:
        return self._model

    @property
    def temperature(self) -> str:
        return self._temperature

    def package(
        self, *, product: Mapping[str, Any], headings: Sequence[Mapping[str, Any]]
    ) -> tuple[PackagedSection, ...]:
        from anthropic import Anthropic  # noqa: PLC0415 — opt-in dependency

        wanted = ", ".join(str(heading["id"]) for heading in headings)
        message = Anthropic().messages.create(
            model=self._model,
            max_tokens=1024,
            temperature=float(self._temperature),
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"{self._instruction}\n\nHeadings: {wanted}\n\n"
                        f"Product JSON:\n{json.dumps(product, indent=1, default=str)}"
                    ),
                }
            ],
        )
        text = "".join(
            block.text for block in message.content if getattr(block, "type", "") == "text"
        )
        by_heading = {
            line.split(":", 1)[0].strip().lower(): line.split(":", 1)[1].strip()
            for line in text.splitlines()
            if ":" in line
        }
        figures = _figures(product)
        sections: list[PackagedSection] = []
        for heading in headings:
            name = str(heading["id"])
            prose = by_heading.get(name)
            if not prose:
                raise PackagingRefused(
                    f"the model returned no line for heading {name!r}; a missing"
                    " section is a refusal, never an empty paragraph"
                )
            # What a real model CITED is not declarable by the model, so it is
            # derived: every substrate figure whose text appears in the prose.
            # The smoothing gate then checks the complement — any number in the
            # prose that is NOT a substrate figure.
            sections.append(
                PackagedSection(
                    heading=name,
                    audience=str(heading["audience"]),
                    prose=prose,
                    figures_cited=tuple(
                        value for value in figures.values() if value and value in prose
                    ),
                )
            )
        return tuple(sections)
