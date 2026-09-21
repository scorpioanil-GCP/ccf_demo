"""The HITL half — and it begins where construction ends.

**This module is the one genuinely new coverage shape on the ladder: a
governed Context Product handed to an existing HITL workflow primitive**
(`CP-SPEC-015` §0.2). It uses `ccf.hitl` exactly as shipped and asks the SDK
for nothing new.

THE CONSTRUCTION BOUNDARY IS THE POINT, and it is structural rather than
conventional (`CP-SPEC-015` §F.4.1, ruled 2026-09-21):

    The Context Product must be completely assembled, governed, assessed and
    immutable BEFORE enqueue. The human review workflow consumes its
    references. HITL must not become part of Context Product construction, or
    a way to repair incomplete context manually.

Three things make that true here rather than merely stated. `acquire`,
`assess` and the declared gate — the whole of construction — live in
`deployment.py`, which imports nothing from `ccf.hitl`. This module takes an
already-`ServedProduct` as its argument, so there is no order of operations in
which a referral could precede a serve. And it never returns a product: it
returns the events it enqueued, so nothing it does can reach the payload.
The measurable consequence is `UBO-G20` — assembling with this module never
called produces **byte-identical** output.

THE CONVENTION, as ruled:

- ``workflow_state_ref`` is the originating product's **replay-record**
  reference, because it identifies the exact governed determination that
  caused the review. Not the content address: identical product bytes can
  participate in different governed determinations, so an address alone
  cannot say which one referred the finding.
- ``output_ref`` is the Context Product's **content address**, carried in the
  versioned URI the SDK's contract requires. The URI's version component IS
  the address, so both the ruling and the contract are satisfied without
  changing either.
- ``lineage`` carries one entry per flagged person **where the product has
  that evidence**. References are never manufactured for a finding with none.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ccf.artifacts.protocol import artifact_uri
from ccf.contracts.canonical import content_hash
from ccf.contracts.claims import LineageEntry
from ccf.controlplane.audit import AuditLog
from ccf.hitl.review_queue import PendingHitlEvent, ReviewQueue, ReviewQueueItem
from ccf.hitl.transport import InMemoryHitlTransport
from ccf.replay.serve import ServedProduct
from ccf.signal.envelope import SourceIdentity

#: The artifact class the product's content address is named under. The SDK
#: stores replay records, not products, so the product's URI is this
#: deployment's naming of an address the SDK already computed — no product
#: bytes are filed and no second store appears.
PRODUCT_ARTIFACT_CLASS = "ccf.context-product"
SYSTEM = "cp-15-kyc-beneficial-ownership"

#: Which payload members carry findings a human is asked to look at, and what
#: makes an entry in each one a referral rather than a row.
REFERRABLE: Mapping[str, str] = {
    "sub_threshold_findings": "below-reporting-threshold",
    "resolution_findings": "below-confidence-floor",
    "sanctions_findings": "sanctions-review-band",
}


@dataclass(frozen=True)
class Referral:
    """One finding handed to a human, and what it was referred for."""

    event_key: str
    member: str
    reason: str
    person_key: str
    detail: str
    has_evidence: bool


@dataclass(frozen=True)
class Submitted:
    """What the queue accepted, and what it did not."""

    events: tuple[PendingHitlEvent, ...]
    referrals: tuple[Referral, ...]
    not_referred: tuple[Referral, ...]
    workflow_state_ref: str
    output_ref: str

    @property
    def product_content_address(self) -> str:
        """The address inside `output_ref` — the URI's version component."""
        return self.output_ref.rsplit("@", 1)[-1]


def open_queue(*, clock: Any) -> ReviewQueue:
    """The SDK's review queue over its own shipped transport and audit log.

    Three objects, two of them concrete SDK classes and one a clock. Gate 0
    predicted four injected objects plus a policy artifact; the measured
    figure is three and no artifact, and it is recorded in `FINDINGS.md`.
    """
    return ReviewQueue(transport=InMemoryHitlTransport(), audit=AuditLog(), clock=clock)


def refer_findings(
    *, queue: ReviewQueue, served: ServedProduct, tenant_id: str, at: datetime,
) -> Submitted:
    """Refer every finding in an ALREADY-SERVED product to the review queue.

    Takes a `ServedProduct`, which is the construction boundary expressed as a
    type: there is no way to call this before a complete, governed, assessed
    product exists, and nothing here can change what that product says.
    """
    payload = served.product.payload
    address = content_hash(served.product)
    output_ref = artifact_uri(
        tenant_id=tenant_id, artifact_class=PRODUCT_ARTIFACT_CLASS,
        name=str(served.product.schema_name), artifact_version=address,
    )
    # THE ORIGINATING DETERMINATION, not the product's bytes.
    workflow_state_ref = served.replay_ref.uri or served.replay_ref.content_address

    referrals = _referrals(payload)
    lineage_by_person = _lineage(payload, at=at)

    events: list[PendingHitlEvent] = []
    referred: list[Referral] = []
    withheld: list[Referral] = []
    for referral in referrals:
        entries = lineage_by_person.get(referral.person_key, ())
        if not entries:
            # RULED: do not manufacture references for a finding with no
            # supporting evidence. The finding stays in the product; it is
            # simply not referred, and the product says which.
            withheld.append(referral)
            continue
        events.append(queue.submit_for_review(
            tenant=tenant_id,
            event_key=referral.event_key,
            workflow_state_ref=workflow_state_ref,
            item=ReviewQueueItem(output_ref=output_ref, lineage=tuple(entries)),
        ))
        referred.append(referral)
    return Submitted(
        events=tuple(events), referrals=tuple(referred), not_referred=tuple(withheld),
        workflow_state_ref=workflow_state_ref, output_ref=output_ref,
    )


def _referrals(payload: Mapping[str, Any]) -> tuple[Referral, ...]:
    """Every finding the product carries, as a referral candidate."""
    out: list[Referral] = []
    for member, reason in REFERRABLE.items():
        for item in payload.get(member) or ():
            person_key = str(item.get("person_key", ""))
            if member == "resolution_findings" and item.get("below_floor") != "true":
                continue  # a resolution above the floor is not a finding
            detail = _detail(member, item)
            out.append(Referral(
                event_key=f"{member}/{person_key}/{detail}",
                member=member, reason=reason, person_key=person_key,
                detail=detail, has_evidence=True,
            ))
    return tuple(out)


def _detail(member: str, item: Mapping[str, Any]) -> str:
    if member == "sub_threshold_findings":
        return str(item.get("effective_pct", ""))
    if member == "resolution_findings":
        return f"{item.get('source_system', '')}:{item.get('match_score', '')}"
    return str(item.get("entry_id", ""))


def _lineage(payload: Mapping[str, Any], *, at: datetime) -> Mapping[str, tuple[LineageEntry, ...]]:
    """One lineage entry per person the product actually carries evidence for.

    The entry's `envelope_id` is the person's own claim id in the fabric that
    produced this product, so a reviewer traces the finding to the claim
    rather than to a label.
    """
    source = SourceIdentity(system_id=SYSTEM)
    by_person: dict[str, list[LineageEntry]] = {}
    for person in payload.get("ownership_chain") or ():
        key = str(person.get("person_key", ""))
        if not key:
            continue
        by_person.setdefault(key, []).append(LineageEntry(
            source=source, envelope_id=f"node/urn:ccf:cp15:person:{key}", observed_at=at,
        ))
    return {key: tuple(entries) for key, entries in by_person.items()}


def resolutions(*, queue: ReviewQueue, tenant_id: str) -> tuple[Any, ...]:
    """What is still pending for this tenant, as the SDK reports it."""
    return queue.items(tenant=tenant_id)


def referral_summary(submitted: Submitted) -> Sequence[Mapping[str, str]]:
    """What the product would state about its own referrals, for `run.py`."""
    return [
        {"event_key": r.event_key, "member": r.member, "reason": r.reason,
         "person_key": r.person_key}
        for r in submitted.referrals
    ]
