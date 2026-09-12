"""This deployment's own values — the other half of ``produce.py``.

[ADAPT] everything here. [MECHANISM] nothing.

``produce.py`` beside this file is CCF's calls and names none of the vocabulary
below. Delete ``ccf_config.yaml`` and nothing here has anything left to
interpret, which is the No-Hardcoding Rule (CLAUDE.md §6.4) being structural
rather than aspirational.

**Its boundaries are ruled** (`D-IMPL-315`): vocabulary, source access,
admission, and the deployment half of ONE declared product gate. No binder, no
universal gates, no replay record, no serve — those are ``GovernedResolver``'s,
and ``produce.py`` hands it the seam.

## The ingestion-order contract

Edge envelopes carry two endpoint references and **no attributes**; node
envelopes carry one node's attributes. **Edges are ingested FIRST and nodes
LAST.** Measured on this SDK at rung 4: a claim carrying fewer attributes at
the same URI *supersedes* the richer one rather than merging into it, so an
edge arriving after a node erases that node's attributes and nothing raises.
:func:`ingest` is the only function here that writes, it emits both kinds
itself, and it asserts the result before returning.

## What is NOT invented here

`deposit_account` and `investment_position` carry **no observation timestamp**
in this estate (`CP09-F-01`). Their envelopes therefore carry
``observed_time=None`` — the field is ``datetime | None`` and ``None`` is the
honest value. Stamping ``asked_at`` onto them would manufacture a freshness
claim out of the act of asking, and the product's whole subject is that the
classes do not share a clock.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

import acquisition
from ccf.controlplane.artifacts import PerspectiveArtifact
from ccf.deployment import BootedFabric
from ccf.products.contract import ContextProductContract
from ccf.products.request import ProductRequest
from ccf.signal.envelope import SignalEnvelope, SourceIdentity

HERE = Path(__file__).parent

#: The request parameters this deployment reads by name. `subject`, `intent`,
#: `freshness` and `asked_at` are NOT here: they are `ProductRequest` FIELDS
#: (`CP-SPEC-009` §B.5), and a second copy in `parameters` would be a value the
#: content address hashes twice and replay could resolve two ways.
CLIENTS = "clients"
CURRENCIES = "currencies"
MAX_STALENESS = "max_staleness"

SYSTEM = "treasury_estate"


def config() -> Mapping[str, Any]:
    """The single deployment document, parsed."""
    document: Mapping[str, Any] = yaml.safe_load(
        (HERE / "ccf_config.yaml").read_text(encoding="utf-8")
    )
    return document


def staleness_profile() -> Mapping[str, Mapping[str, Any]]:
    """The §B.6 refusal rule, keyed by signal class."""
    document = yaml.safe_load(
        (HERE / "artifacts" / "staleness-profile.yaml").read_text(encoding="utf-8")
    )
    return {
        str(entry["signal_class"]): entry
        for entry in document["declaration"]["classes"]
    }


def connection(*, root: Path) -> Mapping[str, str]:
    """Where the FABRIC's own L3 lives for this run. Never a source store."""
    profile = yaml.safe_load(
        (HERE / "backends.yaml").read_text(encoding="utf-8")
    )["declaration"]["profiles"]["sqlite"]["settings"]["database_path"]
    return {"database_path": str(root / f"{profile['prefix']}{profile['suffix']}")}


def request(
    *, anchor_lei: str, asked_at: datetime,
    currencies: Sequence[str] | None = None,
    max_staleness: Mapping[str, str] | None = None,
    intent: str = "reserve-buffer", freshness: str = "intraday",
    debt_tolerance: float | None = None,
) -> ProductRequest:
    """The question asked. An argument, never an artifact.

    **The four §6.3 axes are FIELDS** — `subject`, `intent`, `freshness` and
    `asked_at` — because they establish which question was asked and are what
    the content address and the replay record resolve against. Only the
    class-declared remainder reaches ``parameters`` (`CP-SPEC-009` §B.5,
    `TLP-G19`).

    ``asked_at`` arrives from the CALLER. Nothing here reads a clock: the
    instant a question is asked as-of is the boundary a replay resolves
    against and the SDK must never hold one (`D-IMPL-98`, `C-15`).
    """
    declared = config()["product_class"]
    parameters: dict[str, Any] = {CLIENTS: [anchor_lei]}
    if currencies is not None:
        parameters[CURRENCIES] = list(currencies)
    if max_staleness is not None:
        parameters[MAX_STALENESS] = dict(max_staleness)
    if debt_tolerance is not None:
        parameters["debt_tolerance"] = debt_tolerance
    return ProductRequest(
        schema_name=declared["schema_name"],
        schema_version=declared["schema_version"],
        subject=anchor_lei,
        intent=intent,
        freshness=freshness,
        asked_at=asked_at,
        parameters=parameters,
    )


def perspective() -> PerspectiveArtifact:
    """The Π role-conditioning this product is served under."""
    declared = dict(config()["default_perspective"])
    return PerspectiveArtifact(semver="1.0.0", **declared)


def acquire_for(asked: ProductRequest) -> acquisition.Estate:
    """Read both source legs for the question the SDK resolved."""
    return acquisition.acquire(
        anchor_lei=asked.subject,
        asked_at=asked.asked_at,
        currencies=asked.parameters.get(CURRENCIES),
    )


def _uri(kind: str, key: str) -> str:
    return f"{kind}://{key}"


#: Which resolution rule each node kind is admitted by. Seven classes, because
#: the reference debt scorer types an observation by its ENTITY CLASS and one
#: class over everything would price a rate tick like a filing figure.
MATCH_KEY: Mapping[str, str] = {
    "client": "client_node",
    "deposit": "deposit_node",
    "position": "position_node",
    "counterparty": "counterparty_node",
    "rate": "rate_node",
    "fx": "fx_node",
    "posture": "posture_node",
}


def _node(
    *, tenant_id: str, at: datetime, uri: str, client_id: str, kind: str,
    label: str, lei: str, body: Mapping[str, Any],
    observed_time: datetime | None,
) -> SignalEnvelope:
    """One node's attributes. ATTRIBUTED, therefore ingested LAST."""
    return SignalEnvelope(
        tenant_id=tenant_id,
        envelope_id=f"node/{uri}",
        source=SourceIdentity(system_id=SYSTEM),
        ingestion_timestamp=at,
        # `None` WHERE THE ESTATE RECORDED NONE. Not `at`, which would be this
        # run's clock wearing a source's label.
        observed_time=observed_time,
        raw_payload={
            MATCH_KEY[kind]: uri,
            "entity_uri": uri,
            "client_id": client_id,
            "node_kind": kind,
            "label": label,
            "lei": lei,
            "payload_json": json.dumps(body, sort_keys=True, default=str),
            "observed_at_recorded": str(observed_time is not None).lower(),
        },
    )


#: Which endpoint rule resolves each side of each predicate. The rule's
#: `match_key` must be a KEY PRESENT IN THE PAYLOAD — measured while building:
#: an edge envelope carrying only `subject_ref`/`object_ref` minted 41 entities
#: and ZERO relationships, silently, because no rule's match key was there.
ENDPOINT_RULES: Mapping[str, tuple[str, str]] = {
    "holdsDeposit": ("client_subject", "deposit_object"),
    "holdsPosition": ("client_subject", "position_object"),
    "concentratedIn": ("position_subject", "counterparty_object"),
    "governedBy": ("client_subject", "posture_object"),
    "observesRate": ("client_subject", "rate_object"),
    "observesFx": ("client_subject", "fx_object"),
}


def _edge(
    *, tenant_id: str, at: datetime, ordinal: int, subject: str, obj: str,
    predicate: str,
) -> SignalEnvelope:
    """One typed edge, carrying NO attributes.

    .. warning::

       **Must reach L2 BEFORE either endpoint's node envelope.** It resolves
       both endpoints as entities and has no attributes to give them, so the
       claim it mints is thin — and a thin claim arriving after an attributed
       one supersedes it, silently. Do not reorder :func:`ingest`'s two loops.
    """
    subject_rule, object_rule = ENDPOINT_RULES[predicate]
    return SignalEnvelope(
        tenant_id=tenant_id,
        envelope_id=f"edge/{ordinal}",
        source=SourceIdentity(system_id=SYSTEM),
        ingestion_timestamp=at,
        observed_time=None,
        raw_payload={
            subject_rule: subject, "subject_uri": subject,
            object_rule: obj, "object_uri": obj,
            # SELECTS among the six declared rules. It cannot name a type no
            # rule declares: the comparison is against the rule.
            "predicate": predicate,
        },
    )


def envelopes(
    estate: acquisition.Estate, *, tenant_id: str, at: datetime
) -> tuple[list[SignalEnvelope], list[SignalEnvelope]]:
    """``(edges, nodes)`` for one estate read, in the order they must be written."""
    client = estate.client
    anchor = _uri("client", client.lei)
    edges: list[SignalEnvelope] = []
    nodes: list[SignalEnvelope] = []

    def edge(subject: str, obj: str, predicate: str) -> None:
        edges.append(
            _edge(tenant_id=tenant_id, at=at, ordinal=len(edges),
                  subject=subject, obj=obj, predicate=predicate)
        )

    nodes.append(
        _node(
            tenant_id=tenant_id, at=at, uri=anchor, client_id=client.lei,
            kind="client", label=client.label, lei=client.lei,
            body={
                "mandate_id": client.mandate_id, "intent": client.intent,
                "home_currency": client.home_currency,
                "reported_cash": str(client.reported_cash),
                "cash_fact_asof": client.cash_fact_asof.isoformat(),
                "limits": {l.counterparty_lei: str(l.limit_pct) for l in estate.limits},
                "permitted": {p.instrument_kind: p.max_tenor_days for p in estate.permitted},
            },
            # THE CLIENT ROW ITSELF has no observation time either: the only
            # dated thing on it is a reporting-period end, which is not one.
            observed_time=None,
        )
    )

    for deposit in estate.deposits:
        uri = _uri("deposit", deposit.account_id)
        edge(anchor, uri, "holdsDeposit")
        nodes.append(
            _node(tenant_id=tenant_id, at=at, uri=uri, client_id=client.lei,
                  kind="deposit", label=deposit.account_id, lei="",
                  body={
                      "account_id": deposit.account_id, "currency": deposit.currency,
                      "balance": str(deposit.balance),
                      "jurisdiction": deposit.jurisdiction,
                      "setoff_contractual": deposit.setoff_contractual,
                      "setoff_enforceable": deposit.setoff_enforceable,
                  },
                  observed_time=None)
        )

    seen: set[str] = set()
    for position in estate.positions:
        uri = _uri("position", position.position_id)
        counterparty = _uri("counterparty", position.counterparty_lei)
        edge(anchor, uri, "holdsPosition")
        edge(uri, counterparty, "concentratedIn")
        nodes.append(
            _node(tenant_id=tenant_id, at=at, uri=uri, client_id=client.lei,
                  kind="position", label=position.position_id, lei="",
                  body={
                      "position_id": position.position_id,
                      "counterparty_lei": position.counterparty_lei,
                      "instrument_kind": position.instrument_kind,
                      "currency": position.currency,
                      "notional": str(position.notional),
                      "maturity_date": position.maturity_date.isoformat(),
                  },
                  observed_time=None)
        )
        if counterparty not in seen:
            seen.add(counterparty)
            nodes.append(
                _node(tenant_id=tenant_id, at=at, uri=counterparty,
                      client_id=client.lei, kind="counterparty",
                      label=position.counterparty_label,
                      lei=position.counterparty_lei, body={},
                      observed_time=None)
            )

    for observation in (*estate.rates, *estate.fx):
        is_fx = observation.signal_class == "fx-reference"
        uri = _uri("signal", observation.signal_id)
        edge(anchor, uri, "observesFx" if is_fx else "observesRate")
        body: dict[str, Any] = {
            "signal_id": observation.signal_id,
            "signal_class": observation.signal_class,
            "source": observation.source,
            "label": observation.label,
            "value": str(observation.value),
            "observed_at": observation.observed_at.isoformat(),
        }
        if is_fx:
            body["pair"] = observation.signal_id.split(":", 1)[1]
        nodes.append(
            _node(tenant_id=tenant_id, at=at, uri=uri, client_id=client.lei,
                  kind="fx" if is_fx else "rate", label=observation.label,
                  lei="", body=body,
                  # A REAL OBSERVATION TIME, because this one exists.
                  observed_time=observation.observed_at)
        )

    for posture in estate.postures:
        uri = _uri("posture", posture.version_id)
        edge(anchor, uri, "governedBy")
        nodes.append(
            _node(tenant_id=tenant_id, at=at, uri=uri, client_id=client.lei,
                  kind="posture", label=posture.version_id, lei="",
                  body={
                      "jurisdiction": posture.jurisdiction, "intent": posture.intent,
                      "level": posture.level,
                      "valid_from": posture.valid_from.isoformat(),
                      "version_id": posture.version_id,
                  },
                  # EFFECTIVITY, NOT OBSERVATION. `validFrom` says when the
                  # rule took force, which is not when anyone saw it.
                  observed_time=None)
        )
    return edges, nodes


def ingest(booted: BootedFabric, estate: acquisition.Estate, *, at: datetime) -> None:
    """Write the estate into L3 through the ONE write handle, in order.

    ``booted.handle.worker`` is the only write handle to L3 anywhere in this
    process (single-writer, CLAUDE.md §10). **Edges first, nodes last**, and
    the result is asserted rather than trusted.
    """
    edges, nodes = envelopes(estate, tenant_id=booted.tenant_id, at=at)
    worker = booted.handle.worker
    for envelope in edges:
        worker.ingest(envelope)
    for envelope in nodes:
        worker.ingest(envelope)

    view = booted.handle.reader.as_of(tenant_id=booted.tenant_id, at=at)
    unattributed = [
        record.claim.entity_uri
        for record in view.entities
        if not record.claim.attributes.get("node_kind")
    ]
    if unattributed:
        raise AssertionError(
            f"{len(unattributed)} of {len(view.entities)} admitted nodes carry"
            " no attributes after ingestion. The ingestion-order contract was"
            " violated: an endpoint-only claim arrived after the node's own"
            f" claim and superseded it. First: {sorted(unattributed)[0]!r}"
        )


def _iso_seconds(value: str) -> int:
    """`PT15M` / `PT1H` / `P90D`, as seconds. A duration, never a clock read."""
    text = value.strip().upper()
    if not text.startswith("P"):
        raise ValueError(f"{value!r} is not an ISO-8601 duration")
    days, rest = 0, text[1:]
    if "T" in rest:
        head, _, rest = rest.partition("T")
    else:
        head, rest = rest, ""
    if head.endswith("D"):
        days = int(head[:-1])
    seconds = days * 86400
    number = ""
    for character in rest:
        if character.isdigit():
            number += character
            continue
        unit = {"H": 3600, "M": 60, "S": 1}.get(character)
        if unit is None:
            raise ValueError(f"{value!r} carries an unsupported unit {character!r}")
        seconds += int(number or "0") * unit
        number = ""
    return seconds


def build_staleness_gate(
    *, asked: ProductRequest,
) -> Any:
    """The DEPLOYMENT half of the declared product gate (`TLP-G07`).

    The Control Plane owns the gate's IDENTITY — ``declared_product_gate`` in
    ``ccf_config.yaml`` — and the deployment owns the PREDICATE. The resolver
    stamps ``gate`` and ``gate_version`` from the declaration, so this callable
    cannot claim to be a different gate than the one its class declared
    (`D-IMPL-282` R-11).

    **Per signal class, never one clock** (§B.6). The profile declares a bound
    and a mandatory flag per class; a request's ``max_staleness`` tightens a
    NAMED class and leaves the others alone. A non-mandatory class never
    refuses — it contributes Context Debt, which the SDK's own debt path
    computes.

    Returns a detail string to refuse, ``None`` to pass.
    """
    profile = dict(staleness_profile())
    requested = asked.parameters.get(MAX_STALENESS) or {}
    for signal_class, spelling in requested.items():
        if signal_class not in profile:
            continue
        entry = dict(profile[signal_class])
        entry["bound_seconds"] = min(
            int(entry["bound_seconds"]), _iso_seconds(str(spelling))
        )
        profile[signal_class] = entry

    def gate(
        *, candidate: ContextProductContract, evidence: object = None
    ) -> str | None:
        register = candidate.payload.get("signal_register") or []
        breaches = []
        for row in register:
            entry = profile.get(str(row.get("signal_class")))
            if entry is None or not entry.get("mandatory"):
                continue
            bound = int(entry["bound_seconds"])
            age = int(row.get("age_seconds", 0))
            if age > bound:
                breaches.append((age, row, bound))
        if not breaches:
            return None
        # THE OLDEST PARTICIPATING BREACH IS NAMED, and the message carries the
        # class, the signal, its age and the bound — never a bare "stale".
        age, row, bound = max(breaches, key=lambda item: item[0])
        return (
            f"signal {row.get('signal_id')!r} of class"
            f" {row.get('signal_class')!r} was observed at"
            f" {row.get('observed_at')}, {age}s before the decision instant,"
            f" against a bound of {bound}s. The product fails closed rather"
            " than serving a composition that includes it, and rather than"
            " substituting a last-good value"
        )

    return gate


def measured_completeness(estate: acquisition.Estate) -> Decimal:
    """`C` — resolved / served, measured on THIS estate read.

    **Supplied to the SDK's reference scorer rather than scored here.**
    ``build_governed_resolver`` refuses a resolver with nothing to measure
    `D_c` with, and its own message says why: the reference scorer needs the
    two Control Plane keys *and* "the two factors the SDK has no measurement
    for". This is one of those two — the SDK cannot know that a counterparty
    has no concentration limit on file, because that is a fact about this
    estate's registers rather than about the graph.

    The SDK still does every piece of arithmetic: `F` from the registered λ_c
    table over the observation ages, the multiplicative fold, the band routing
    against the declared debt profile. Nothing here computes `D_c`.

    Two terms, per §E.2: concentration-limit coverage and counterparty identity
    resolution. Measured on the anchor at 2026-06-17, coverage is 4 of 7 and
    identity is 7 of 7 — so the term moves and is not decorative.
    """
    counterparties = {position.counterparty_lei for position in estate.positions}
    if not counterparties:
        return Decimal("1")
    covered = len({limit.counterparty_lei for limit in estate.limits} & counterparties)
    resolved = len(
        {p.counterparty_lei for p in estate.positions if p.counterparty_label}
    )
    total = len(counterparties)
    return (
        (Decimal(covered) / Decimal(total)) * (Decimal(resolved) / Decimal(total))
    ).quantize(Decimal("0.0001"))


def measured_semantic_consistency(estate: acquisition.Estate) -> Decimal:
    """`S` — currency coherence, measured on THIS estate read.

    The second factor the SDK has no measurement for. A balance whose
    conversion to the home currency has no FX observation is a consistency
    failure rather than a silent skip, and this is the proportion of held
    currencies that CAN be expressed in one number.

    A currency the request never scoped in is not a missing rate and does not
    enter this ratio — scope decides participation before freshness decides
    admission (§B.6).
    """
    held = {d.currency for d in estate.deposits} | {
        p.currency for p in estate.positions
    }
    if not held:
        return Decimal("1")
    home = estate.client.home_currency
    available = {observation.signal_id.split(":", 1)[1] for observation in estate.fx}
    coherent = sum(
        1 for currency in held
        if currency == home or f"{currency}/{home}" in available
    )
    return (Decimal(coherent) / Decimal(len(held))).quantize(Decimal("0.0001"))


@dataclass(frozen=True)
class TreasuryScenario:
    """What one run needs — satisfies ``produce.Scenario`` structurally."""

    estate: acquisition.Estate
    asked: ProductRequest

    @property
    def product_class_key(self) -> str:
        return "product_class"

    @property
    def request_contract_key(self) -> str:
        return "request_contract"

    @property
    def policy_bundle_key(self) -> str:
        return "policy"

    @property
    def operator_parameter_keys(self) -> tuple[str, ...]:
        """However many the deployment declared — never a fixed count."""
        return tuple(config()["operators"])

    @property
    def plan_id(self) -> str:
        return f"cp-09.treasury-liquidity/{self.estate.client.lei}"

    @property
    def max_ttl_seconds(self) -> int:
        """The CEILING — 15 minutes, and the spec argues why it is not longer.

        §B.1: *"TTL 15 minutes, `ttl_anchor: from_decision` … ceiling 15
        minutes; a request for a longer window refuses with authority
        `technical`."* The fastest class the product admits sets both, because
        a product whose rate leg is good for fifteen minutes cannot honestly
        offer a longer window over the same answer.

        Read from the λ_c table's fastest row rather than restated here, so one
        number has one authority. The slower classes carry no rate at all now —
        they are `supersede-only` — so there is no "slowest half-life" to read
        and there should not be: a ceiling derived from a class that does not
        decay would be a number with nothing behind it.
        """
        return int(config()["half_life"]["treasury_rate_signal"]["half_life_seconds"])

    @property
    def product_ttl_seconds(self) -> int:
        """15 minutes, from the fastest class — `ttl_anchor: from_decision`."""
        return int(config()["half_life"]["treasury_rate_signal"]["half_life_seconds"])

    @property
    def declared(self) -> Mapping[str, Any]:
        """What Π is told that is not in the graph — the named absences."""
        return {"absent_sources": self.estate.rate_sources_out_of_window}
