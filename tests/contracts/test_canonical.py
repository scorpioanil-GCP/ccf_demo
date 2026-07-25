"""Canonical-serializer tests (04-RESEARCH.md Pattern 3 bit-for-bit prerequisite).

`ccf.contracts.canonical` is the ONE canonical form in the SDK: composition
preservation (FABR-02), D-IMPL-26 content addressing, and replay hashes all
compare against it, so order-independence and cross-process stability are
invariants, not conveniences.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import (
    CanonicalizationError,
    canonical_bytes,
    content_hash,
)


class _Doc(CCFContract):
    b: str
    a: str
    tags: frozenset[str]


def test_mapping_key_order_does_not_affect_bytes() -> None:
    left = canonical_bytes({"a": 1, "b": 2, "c": {"y": 1, "x": 2}})
    right = canonical_bytes({"c": {"x": 2, "y": 1}, "b": 2, "a": 1})
    assert left == right


def test_set_element_order_does_not_affect_bytes() -> None:
    left = canonical_bytes({"tags": {"z", "a", "m"}})
    right = canonical_bytes({"tags": {"m", "z", "a"}})
    assert left == right


def test_sequence_order_is_significant() -> None:
    assert canonical_bytes([1, 2]) != canonical_bytes([2, 1])


def test_model_and_equivalent_mapping_agree() -> None:
    doc = _Doc(a="1", b="2", tags=frozenset({"x", "y"}))
    assert canonical_bytes(doc) == canonical_bytes(
        {"a": "1", "b": "2", "tags": {"y", "x"}}
    )


def test_timestamps_serialize_as_fixed_precision_rfc3339_utc() -> None:
    aware_utc = datetime(2026, 7, 25, 12, 0, 0, tzinfo=UTC)
    offset = aware_utc.astimezone(timezone(timedelta(hours=-5)))
    assert canonical_bytes({"t": aware_utc}) == canonical_bytes({"t": offset})
    assert b'"2026-07-25T12:00:00.000000Z"' in canonical_bytes({"t": aware_utc})


def test_naive_datetime_is_rejected() -> None:
    with pytest.raises(CanonicalizationError):
        canonical_bytes({"t": datetime(2026, 7, 25, 12, 0, 0)})


def test_floats_are_rejected() -> None:
    with pytest.raises(CanonicalizationError):
        canonical_bytes({"amount": 1.5})


def test_decimal_is_accepted_and_order_stable() -> None:
    assert canonical_bytes({"amount": Decimal("1.50")}) == b'{"amount":"1.50"}'


def test_unsupported_type_is_rejected() -> None:
    with pytest.raises(CanonicalizationError):
        canonical_bytes({"x": object()})


def test_content_hash_matches_sha256_of_canonical_bytes() -> None:
    payload = {"a": 1, "b": ["x", "y"]}
    assert (
        content_hash(payload)
        == hashlib.sha256(canonical_bytes(payload)).hexdigest()
    )


def test_content_hash_is_64_char_lowercase_hex() -> None:
    digest = content_hash({"a": 1})
    assert len(digest) == 64
    assert digest == digest.lower()
    assert all(c in "0123456789abcdef" for c in digest)


def test_known_input_digest_is_pinned() -> None:
    # Pins the canonical form itself: {"a":1} with compact separators.
    assert canonical_bytes({"a": 1}) == b'{"a":1}'
    assert (
        content_hash({"a": 1})
        == hashlib.sha256(b'{"a":1}').hexdigest()
    )


def test_hash_is_stable_across_processes() -> None:
    program = (
        "from ccf.contracts.canonical import content_hash;"
        "print(content_hash({'b': {'z', 'a'}, 'a': 1}))"
    )
    runs = {
        subprocess.run(
            [sys.executable, "-c", program],
            capture_output=True,
            text=True,
            check=True,
            env={"PYTHONHASHSEED": seed, "PATH": "/usr/bin:/bin"},
        ).stdout.strip()
        for seed in ("0", "1", "12345")
    }
    assert len(runs) == 1
    assert runs.pop() == content_hash({"b": {"z", "a"}, "a": 1})


def test_modules_are_tagged_algorithmic() -> None:
    import ccf.contracts.base as base_mod
    import ccf.contracts.canonical as canonical_mod

    assert base_mod.__ccf_mode__ == "algorithmic"
    assert canonical_mod.__ccf_mode__ == "algorithmic"
