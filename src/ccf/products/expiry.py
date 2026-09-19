"""The TTL anchor: when the evidence a product rests on stopped being current.

`D-IMPL-341`. §6.3 of the whitepaper commits TTL as the contract element that
bounds a product's validity in time and forces its re-evaluation once that bound
passes (``docs/CCF_Whitepaper_1-2.md:1455``), and `D-IMPL-31` ruled its
derivation declared per class. A class declares the anchor its window runs from
(:data:`~ccf.products.contract.TTLAnchor`): ``from_decision`` — the instant
the answer was produced (`D-IMPL-308`) — or ``from_entity_freshness`` — the
instant the evidence was current. Until this module existed the second was
declared, recorded on the contract, and computed as the first
(`CP03C-F-01`): *"the product says one thing about its validity and computes
another"* (Dave, 2026-09-15).

**The clock is the one the deployment already declared for decay, read once
more.** Every claim carries two instants — ``observed_at``, when the fabric
learned it, and ``valid_from``, when the source observed it — and each λ_c row
says which one it decays against (`D-IMPL-331`). The anchor resolves over the
SAME observation set the freshness factor is scored over (dimension 1's, as
:meth:`~ccf.products.debt_scorer.AssemblyDebtScorer._observations` builds
it), reduced per series to its leading edge as of the decision instant
(`D-IMPL-333`, :func:`~ccf.halflife.decay.leading_edge`), and **only rows
declaring ``decay_basis: valid-from`` contribute**: an ``observed-at`` row's
instant is when the fabric learned the claim, which is never evidence
currency. The anchor is the freshest of those (R-1). No timestamp is minted
here, no payload field is read, and the freshness calculation is not touched.

**Three failures, kept apart (R-3).** A class declaring the anchor over a λ_c
table with no ``valid-from`` row is refused **at registration**
(:func:`refuse_undeclared_ttl_anchor`, raised as :class:`TTLAnchorUndeclared`
by the config derivation and the resolver builder). A served observation set
that supplies no usable instant is refused **at gate 3 by its own reason**
(:class:`~ccf.products.gates.TTLAnchorRefusal`, ``ttl-anchor-unresolvable``).
An anchor whose window has passed keeps gate 3's existing ``ttl-bounds``.
Nothing here ever falls back to ``observed_at`` or to the decision instant
for an evidence-anchored class: a fallback would reproduce the measured
overstatement under a name that says it did not.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Final

from ccf.contracts.base import CCFContract
from ccf.controlplane.artifacts import HalfLifeTable
from ccf.graph.protocols import GraphView
from ccf.halflife.decay import leading_edge
from ccf.products.contract import TTLAnchor
from ccf.products.debt_scorer import AssemblyDebtScorer
from ccf.products.gates import GATE_TTL_ANCHOR, TTLAnchorRefusal

__ccf_mode__ = "algorithmic"

__all__ = [
    "FROM_DECISION",
    "FROM_ENTITY_FRESHNESS",
    "TTLAnchorResolution",
    "TTLAnchorUndeclared",
    "refuse_undeclared_ttl_anchor",
    "resolve_ttl_anchor",
    "valid_from_rows",
]

#: The two members of :data:`~ccf.products.contract.TTLAnchor`, named once.
FROM_DECISION: Final = "from_decision"
FROM_ENTITY_FRESHNESS: Final = "from_entity_freshness"
_VALID_FROM: Final = "valid-from"


class TTLAnchorResolution(CCFContract):
    """What a class's TTL anchor resolved to for one decision.

    Attributes:
        anchor_at: The instant the window runs from — the decision instant for
            a ``from_decision`` class; the freshest contributing evidence
            instant for a ``from_entity_freshness`` class.
        basis: The class's declared anchor, carried so the two cannot be told
            apart only by narrative.
        contributing_types: The observation types whose leading edge IS the
            anchor (empty for ``from_decision``). Evidence for the record,
            never a second authority: the anchor is the instant, and this
            names where it came from.
    """

    anchor_at: datetime
    basis: TTLAnchor
    contributing_types: tuple[str, ...]


class TTLAnchorUndeclared(ValueError):
    """A class declares ``from_entity_freshness`` over a λ_c table with no ``valid-from`` row.

    Raised at registration — the config derivation and the resolver builder —
    because no data could ever honor the declaration: an anchor that silently
    moved to the decision instant would serve the measured overstatement under
    an evidence-anchored label (`D-IMPL-341` R-3, first row).
    """


def valid_from_rows(entries: Mapping[str, object] | None) -> tuple[str, ...]:
    """The observation types whose λ_c row decays against ``valid_from``.

    Accepts the parsed :class:`~ccf.controlplane.artifacts.HalfLifeEntry`
    values a booted table carries and the raw section bodies a config
    derivation holds before parsing, so registration and serve read one
    predicate. A row that declares no basis decays ``observed-at``
    (`D-IMPL-331`'s hash-transparent default) and does not qualify.
    """
    qualifying: list[str] = []
    for name, entry in (entries or {}).items():
        basis = getattr(entry, "decay_basis", None)
        if basis is None and isinstance(entry, Mapping):
            basis = entry.get("decay_basis", "observed-at")
        if basis == _VALID_FROM:
            qualifying.append(str(name))
    return tuple(sorted(qualifying))


def refuse_undeclared_ttl_anchor(
    *, ttl_anchor: str, entries: Mapping[str, object] | None, product_class: str
) -> None:
    """Refuse, by name, an evidence-anchored class no λ_c row could support.

    Raises:
        TTLAnchorUndeclared: ``ttl_anchor`` is ``from_entity_freshness`` and
            ``entries`` declares no ``decay_basis: valid-from`` row.
    """
    if ttl_anchor != FROM_ENTITY_FRESHNESS:
        return
    if valid_from_rows(entries):
        return
    declared = sorted(str(name) for name in (entries or {}))
    raise TTLAnchorUndeclared(
        f"product class {product_class!r} declares `ttl_anchor:"
        f" from_entity_freshness`, and its λ_c table declares no row with"
        " `decay_basis: valid-from`"
        + (f" (rows: {declared})" if declared else " (no half_life section)")
        + ". An evidence-anchored expiry needs the source's own instant on at"
        " least one observation type; a row decaying `observed-at` measures"
        " when the fabric learned the claim, which is not evidence currency."
        " Declare `decay_basis: valid-from` on the load-bearing row and carry"
        " the source instant as `observed_time`, or declare `ttl_anchor:"
        " from_decision` (D-IMPL-341 R-3; D-IMPL-331)"
    )


def resolve_ttl_anchor(
    *,
    ttl_anchor: TTLAnchor,
    view: GraphView | None,
    table: HalfLifeTable | None,
    decided_at: datetime,
    product_class: str,
) -> TTLAnchorResolution | TTLAnchorRefusal:
    """Resolve the instant a class's TTL window runs from, for one decision.

    ``from_decision`` resolves to ``decided_at`` (`D-IMPL-308`), on every
    class, so every served product states its basis (R-2).

    ``from_entity_freshness`` resolves over the observation set the freshness
    factor scores — one observation per entity record of ``view`` — reduced
    to each series' leading edge as of ``decided_at`` by the row's own clock,
    keeping only observations of ``valid-from`` rows that carry a
    ``valid_from`` at or before ``decided_at``. The anchor is the freshest of
    those (R-1). Returned rather than raised when nothing qualifies:
    :class:`~ccf.products.gates.TTLAnchorRefusal`, gate 3's own reason for
    *no usable instant* — never ``ttl-bounds``, never a fallback (R-3).

    Args:
        ttl_anchor: The class's declared anchor.
        view: The execution's final view — what the projection read.
        table: The deployment's λ_c table, or ``None`` for a resolver wired
            without one (then nothing can qualify, and the refusal says so).
        decided_at: The decision instant.
        product_class: Named in the refusal.
    """
    if ttl_anchor == FROM_DECISION:
        return TTLAnchorResolution(
            anchor_at=decided_at, basis=ttl_anchor, contributing_types=()
        )
    rows = valid_from_rows(table.entries) if table is not None else ()
    # The scorer's own observation set, narrowed to the types the table
    # declares: an entity class with no λ_c row is not scored for `F` and
    # cannot carry an evidence clock either (`MissingHalfLife` is the scorer's
    # answer for it; here it simply cannot contribute).
    observations = tuple(
        observation
        for observation in (
            AssemblyDebtScorer._observations(view, table=table)
            if view is not None and table is not None
            else ()
        )
        if table is not None and observation.observation_type in table.entries
    )
    seen = tuple(sorted({o.observation_type for o in observations}))
    if table is None or not rows:
        return TTLAnchorRefusal(
            gate=GATE_TTL_ANCHOR,
            detail=(
                f"product class {product_class!r} declares `ttl_anchor:"
                " from_entity_freshness` and "
                + (
                    "this resolver reaches no λ_c table"
                    if table is None
                    else "its λ_c table declares no `decay_basis: valid-from` row"
                )
                + "; no observation can supply an evidence instant, and the"
                " decision instant is not substituted (D-IMPL-341 R-3)"
            ),
            ttl_anchor=ttl_anchor,
            now=decided_at,
            valid_from_rows=rows,
            observation_types=seen,
        )
    edges = leading_edge(observations, table=table, now=decided_at)
    instants: dict[str, datetime] = {}
    for observation in edges:
        if observation.observation_type not in rows:
            continue
        instant = observation.valid_from
        if instant is None or instant > decided_at:
            continue
        standing = instants.get(observation.observation_type)
        if standing is None or instant > standing:
            instants[observation.observation_type] = instant
    if not instants:
        return TTLAnchorRefusal(
            gate=GATE_TTL_ANCHOR,
            detail=(
                f"product class {product_class!r} declares `ttl_anchor:"
                " from_entity_freshness`; the served observation set carries"
                f" no `valid_from` instant on a `valid-from` row (rows {list(rows)},"
                f" observation types seen {list(seen)}), so there is no"
                " evidence instant to anchor on and the decision instant is"
                " not substituted (D-IMPL-341 R-3)"
            ),
            ttl_anchor=ttl_anchor,
            now=decided_at,
            valid_from_rows=rows,
            observation_types=seen,
        )
    anchor_at = max(instants.values())
    return TTLAnchorResolution(
        anchor_at=anchor_at,
        basis=ttl_anchor,
        contributing_types=tuple(
            sorted(name for name, instant in instants.items() if instant == anchor_at)
        ),
    )
