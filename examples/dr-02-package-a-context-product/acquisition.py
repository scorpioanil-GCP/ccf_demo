"""Ask the upstream product, package it with a model, emit claims.

**This module is where Assembly Mode 2 actually happens, and the ORDER is the
architectural claim** (`DR-SPEC-002` §D.3):

    upstream product (algorithmic)  ->  MODEL packages  ->  claim
                                                              |
                          algorithmic projection -> three gates -> serve

Algorithmic, then semantic, then algorithmic. The model never sees raw signal —
it sees a product that is already assembled, governed and content-addressed —
and everything it produced enters the fabric as a claim that the ordinary
projection and the ordinary validation gates then judge. **A model inside the
projection would be a model whose output nothing gates**, which is why the
packaging sits here and not there.

**The substrate is the artifact-of-record** (whitepaper §7.10.4). The upstream
product's content address rides on every section this emits, so any figure in
the prose is checkable against the bytes that produced it. That check is
`packaging.did-not-move-the-conclusion`, and it REFUSES (`DR-SPEC-002` R3).

**An upstream refusal is this product's refusal.** `dr-02` resolves no subject
of its own; if the substrate will not answer, there is nothing here to package
and a memo assembled anyway would be a memo about nothing.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from ccf.contracts.canonical import canonical_bytes
from ccf.mcp.client import McpResourceClient, SyncMcpBridge, bearer_client_factory
from ccf.products.door import PRODUCT_REQUEST_TOOL, DoorOutcome, WireRequest
from ccf.products.refusal import (
    RESOLVED_BY_THE_RESOLVER,
    GovernedRefusalRaised,
    SubjectUnavailableRefusal,
)
from ccf.signal.envelope import SignalEnvelope, SourceIdentity

from memo_packaging import PackagedSection, PackagingModel, PackagingRefused

__all__ = ["UpstreamAnswer", "ask_upstream", "envelopes"]

#: The environment document's name for the upstream door.
SOURCE_UPSTREAM = "upstream_product"

#: How long a door call may take before it is unreachable rather than slow.
CALL_TIMEOUT_SECONDS = 120.0


class UpstreamAnswer:
    """What the substrate served, with the identity the packaging must carry."""

    __slots__ = ("payload", "content_address", "expires_at", "debt", "disposition")

    def __init__(
        self,
        *,
        payload: Mapping[str, Any],
        content_address: str,
        expires_at: str | None,
        debt: str | None,
        disposition: str | None,
    ) -> None:
        self.payload = payload
        self.content_address = content_address
        self.expires_at = expires_at
        self.debt = debt
        self.disposition = disposition


def ask_upstream(
    *,
    settings: Mapping[str, str],
    tenant: str,
    product_class: str,
    version: str,
    subject: str,
    intent: str,
    freshness: str,
    parameters: Mapping[str, Any],
    at: datetime,
) -> UpstreamAnswer:
    """Ask the upstream door one question and hold its answer.

    Raises:
        GovernedRefusalRaised: the upstream refused, or answered with neither a
            product nor a refusal. Both are this product's refusal — the second
            because a door that returns neither has not answered, and inventing
            a memo over silence is the failure this rung is about.
    """
    bridge = SyncMcpBridge(call_timeout_seconds=CALL_TIMEOUT_SECONDS)
    try:
        client = McpResourceClient(
            url=settings["url"],
            bridge=bridge,
            http_client_factory=bearer_client_factory(
                settings["token"], timeout_seconds=CALL_TIMEOUT_SECONDS
            ),
        )
        # The door addresses a product by the same three segments its resource
        # URI carries, and asks whitepaper §6.3's four axes alongside them.
        # All are required, deliberately: a some-but-not-all address would
        # leave the door guessing which question it was asked.
        wire = WireRequest(
            product_id=product_class, parameters=dict(parameters), temporal_boundary=at
        )
        text = client.call_tool_text(
            PRODUCT_REQUEST_TOOL,
            {
                "tenant": tenant,
                "product_class": product_class,
                "version": version,
                "request": canonical_bytes(wire).decode("utf-8"),
                "subject": subject,
                "intent": intent,
                "freshness": freshness,
                "asked_at": at.isoformat(),
                "parameters": dict(parameters),
            },
        )
    finally:
        bridge.close()

    outcome = DoorOutcome.model_validate_json(text)
    if outcome.refusal is not None:
        raise GovernedRefusalRaised(
            SubjectUnavailableRefusal(
                cause="nonexistent",
                detail=(
                    "the upstream product refused, so there is nothing to"
                    f" package: {outcome.refusal.reason}"
                ),
                error_code="upstream-refused",
            ),
            resolution=RESOLVED_BY_THE_RESOLVER,
        )
    if outcome.product_json is None or outcome.content_address is None:
        raise GovernedRefusalRaised(
            SubjectUnavailableRefusal(
                cause="nonexistent",
                detail=(
                    "the upstream door returned neither a product nor a refusal;"
                    " a memo over silence is not a memo"
                ),
                error_code="upstream-silent",
            ),
            resolution=RESOLVED_BY_THE_RESOLVER,
        )

    vessel = json.loads(outcome.product_json)
    payload = vessel.get("payload") if isinstance(vessel, Mapping) else None
    return UpstreamAnswer(
        payload=payload if isinstance(payload, Mapping) else {},
        content_address=outcome.content_address,
        expires_at=_text(vessel.get("expires_at")),
        debt=_text(vessel.get("debt")),
        disposition=_text(vessel.get("obligation_in_force")),
    )


def package(
    *,
    answer: UpstreamAnswer,
    model: PackagingModel,
    headings: Sequence[Mapping[str, Any]],
) -> tuple[PackagedSection, ...]:
    """The semantic stage. One call, over a product that is already finished.

    Raises:
        GovernedRefusalRaised: the packager refused to render. A half-written
            memo is worse than none — the missing section would read as an
            absence of collateral rather than an absence of prose.
    """
    try:
        return model.package(product=answer.payload, headings=headings)
    except PackagingRefused as refused:
        raise GovernedRefusalRaised(
            SubjectUnavailableRefusal(
                cause="nonexistent",
                detail=f"the packaging stage refused: {refused}",
                error_code="packaging-refused",
            ),
            resolution=RESOLVED_BY_THE_RESOLVER,
        ) from refused


def envelopes(
    *,
    answer: UpstreamAnswer,
    sections: Sequence[PackagedSection],
    model: PackagingModel,
    prompt_uri: str,
    prompt_hash: str,
    facility_id: str,
    tenant_id: str,
    at: datetime,
) -> tuple[SignalEnvelope, ...]:
    """The packaged memo and its sections, as dated claims.

    The memo node carries the packaging identity — model, temperature, prompt
    URI and hash — so the four §7.10.4 pins are readable from the fabric as
    well as from dimension 3. The sections carry the audience the Policy
    operator admits on, and the upstream address each derives from.
    """
    memo_ref = f"memo/{facility_id}"

    # ONE CLASS, AND EVERY SECTION IS SELF-DESCRIBING. An earlier shape put the
    # packaging identity on a separate `packaged_memo` node joined by
    # `hasSection` edges, and the memo node never reached the view: the
    # traversal returns the neighbourhood its seeds reach, and a subject that
    # is not itself reached is not in it.
    #
    # Carrying the identity on each section is better anyway rather than merely
    # simpler: a section that travels alone — quoted, pasted, forwarded — still
    # names the model, the temperature, the prompt and the substrate that
    # produced it. That is the property this rung exists to demonstrate, and a
    # separate identity node is exactly the thing that gets left behind.
    return tuple(
        SignalEnvelope(
            tenant_id=tenant_id,
            envelope_id=f"section/{section.heading}",
            source=SourceIdentity(system_id=SOURCE_UPSTREAM),
            ingestion_timestamp=at,
            observed_time=at,
            raw_payload={
                "section_ref": f"{memo_ref}/{section.heading}",
                "entity_ref": f"{memo_ref}/{section.heading}",
                "ref": f"{memo_ref}/{section.heading}",
                "facility_id": facility_id,
                "heading": section.heading,
                "prose": section.prose,
                "audience": section.audience,
                # The figures the packager DECLARES it cited. The smoothing
                # gate checks these against the substrate; a figure in the
                # prose that is not declared here is treated as unsupported,
                # which is the strict reading on purpose.
                "figures_cited": "|".join(section.figures_cited),
                # THE SUBSTRATE — the artifact-of-record this prose renders.
                "derived_from": answer.content_address,
                "upstream_expires_at": answer.expires_at or "",
                "upstream_debt": answer.debt or "",
                "upstream_disposition": answer.disposition or "",
                # §7.10.4's four pinned rendering primitives, on every section.
                "packaging_model": model.model_version,
                "packaging_temperature": model.temperature,
                "packaging_prompt_uri": prompt_uri,
                "packaging_prompt_hash": prompt_hash,
            },
        )
        for section in sections
    )


def _text(value: object) -> str | None:
    return None if value is None else str(value)
