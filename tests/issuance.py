# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""Comparing two answers modulo the per-answer issuance — Dave's E1 (a), stated once.

``D-IMPL-378``, Dave's batch ruling of 2026-10-08 12:29 MST, verbatim: *"Approve
random per-answer issuance and the named conformance amendments. Preserve
record content-address integrity. Random references must have indistinguishable
distributions; equality is no longer the criterion."*

Every product answer's Decision Replay record carries a fresh issuance — 256
bits from the operating system's CSPRNG, minted by
``src/ccf/replay/record.py::new_issuance`` into
``src/ccf/replay/record.py::ContentGenerationPath``'s ``issuance`` — and the
record is filed, and its reference named, under its own content address
(``src/ccf/replay/serve.py::ReplayWriter``). So the same question asked twice is
two records and two references. The three rulings that promised one — ``D-IMPL-253``
amendment 3, ``D-IMPL-358`` ruling 1 and ``D-IMPL-148`` Addendum A — are read
**modulo the per-answer issuance**, the restatement E1 (a) approved. A test that
held two answers' references or records EQUAL holds instead, through these
helpers, the three claims that replace that equality, and nothing weaker:

1. **The same question gets different references** — each answer is issued
   apart, so two answers never share a reference.
2. **An equal reference means an identical record** — a reference's name and
   its version are both the content address of the one record it resolves to.
3. **A reference resolves to a record equal modulo the issuance** — every byte
   of the two records but the issuance is held equal, exactly as before.

Everything a test compared besides the reference and the issuance it compares
unchanged. Fixture vocabulary only (CINV-01): no domain value lives here.
"""

from __future__ import annotations

import re
from typing import Final

from ccf.artifacts.protocol import parse_artifact_uri
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.replay.record import NO_ISSUANCE, DecisionReplayRecord

__all__ = [
    "ISSUANCE_PATTERN",
    "assert_issued",
    "assert_named_by_its_own_content",
    "assert_one_determination_issued_twice",
    "differences_modulo_issuance",
    "modulo_issuance",
]

#: What a minted issuance is: 64 lowercase hexadecimal characters, the shape
#: ``new_issuance`` draws (``secrets.token_hex(32)``). The sentinel
#: ``NO_ISSUANCE`` does not match, so a record that was never issued fails here.
ISSUANCE_PATTERN: Final[re.Pattern[str]] = re.compile(r"\A[0-9a-f]{64}\Z")

#: The record's two members that are not dimensions, compared beside them.
_NOT_DIMENSIONS: Final[tuple[str, ...]] = ("tenant_id", "recorded_at")


def modulo_issuance(record: DecisionReplayRecord) -> DecisionReplayRecord:
    """``record`` with its issuance set back to the sentinel, and nothing else touched.

    A model copy: the stored record is not changed. The sentinel is
    hash-transparent, so the result's canonical bytes are the record's bytes as
    they would have been with no issuance at all.
    """
    path = record.content_generation_path.model_copy(update={"issuance": NO_ISSUANCE})
    return record.model_copy(update={"content_generation_path": path})


def differences_modulo_issuance(
    a: DecisionReplayRecord, b: DecisionReplayRecord
) -> list[str]:
    """The members of two records that differ once the issuance is set aside; ``[]`` when none do.

    Every field the record declares is compared — its five dimensions by
    canonical bytes, ``tenant_id`` and ``recorded_at`` beside them — read off
    the model rather than listed, so a member added to the record joins the
    comparison with no edit here.
    """
    left, right = modulo_issuance(a), modulo_issuance(b)
    return [
        name
        for name in DecisionReplayRecord.model_fields
        if canonical_bytes(getattr(left, name)) != canonical_bytes(getattr(right, name))
    ]


def assert_issued(record: DecisionReplayRecord, *, what: str) -> None:
    """``record`` carries a minted issuance: 64 hexadecimal characters, never the sentinel.

    Asserted before any comparison modulo the issuance, because two records
    that both carried the sentinel would compare equal modulo it while proving
    nothing about issuance at all.
    """
    issuance = record.content_generation_path.issuance
    assert issuance != NO_ISSUANCE and ISSUANCE_PATTERN.match(issuance), (
        f"{what}: the record carries issuance {issuance!r}; a product answer's"
        " record is issued per answer with 64 hexadecimal characters"
        " (new_issuance; Dave's Q11 and E1 (a), D-IMPL-378)"
    )


def assert_one_determination_issued_twice(
    a: DecisionReplayRecord, b: DecisionReplayRecord, *, what: str
) -> None:
    """Claims 1 and 3 for two answers to one question: issued apart, one determination.

    Both records are issued, their issuances differ, and every member of the two
    records but the issuance is byte-equal — the dimension-by-dimension equality
    the restated rulings held before the issuance existed, with the issuance
    alone set aside.

    Raises:
        AssertionError: either record is unissued, the two share an issuance,
            or any member but the issuance differs (named in the message).
    """
    assert_issued(a, what=f"{what} (first answer)")
    assert_issued(b, what=f"{what} (second answer)")
    assert a.content_generation_path.issuance != b.content_generation_path.issuance, (
        f"{what}: two answers carry ONE issuance; each answer is issued apart"
        " (Dave's E1 (a), D-IMPL-378)"
    )
    differing = differences_modulo_issuance(a, b)
    assert differing == [], (
        f"{what}: the two answers' records differ beyond their issuance at"
        f" {differing}; one question at one instant is one determination"
        " (D-IMPL-253 amendment 3, read modulo the per-answer issuance)"
    )


def assert_named_by_its_own_content(
    reference: str, record: DecisionReplayRecord, *, what: str
) -> None:
    """Claim 2: ``reference``'s name and version are both the content address of ``record``.

    So a reference names exactly one immutable content, and equal references
    mean identical records. ``record`` must be the record the reference was
    resolved to; this holds it to the address the reference carries.
    """
    parsed = parse_artifact_uri(reference)
    address = content_hash(record)
    assert parsed.name == parsed.artifact_version == address, (
        f"{what}: reference {reference!r} names {parsed.name!r} at version"
        f" {parsed.artifact_version!r}, and the record it resolved to has"
        f" content address {address!r}; a record's name and version are its"
        " own content address (Dave's Q11, D-IMPL-378)"
    )
