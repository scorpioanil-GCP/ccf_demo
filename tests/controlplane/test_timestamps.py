"""Artifact timestamp handling (D-02; D-IMPL-38; CLAUDE.md §6.4).

``2026-08-03T12:00:00Z`` is not an implicit timezone — ``Z`` is the ISO-8601 UTC
designator. PyYAML's timestamp resolver drops it and returns a naive
``datetime``, which the registry then refuses as non-canonicalizable. The
artifact load path suppresses that resolver so the designator survives to the
contract, and refuses a date-time that genuinely names no zone.

These five tests pin that behavior in both directions, including the blast-radius
guarantee: the shared ``yaml.SafeLoader`` is not mutated.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
import yaml

from ccf.contracts.base import CCFContract
from ccf.controlplane.artifacts import (
    ArtifactClass,
    ArtifactLoadError,
    load_artifact,
)

_INSTANT = "2026-08-03T12:00:00Z"
_OFFSET_INSTANT = "2026-08-03T12:00:00+00:00"


class _TextualObservation(CCFContract):
    """A throwaway contract whose timestamp field is annotated ``str``."""

    semver: str
    observed_at: str


class _InstantObservation(CCFContract):
    """A throwaway contract whose timestamp field is annotated ``datetime``."""

    semver: str
    observed_at: datetime


_TEXTUAL = ArtifactClass(class_id="test.textual", contract=_TextualObservation)
_INSTANTIAL = ArtifactClass(class_id="test.instant", contract=_InstantObservation)


def _document(value: str, *, quoted: bool = False) -> str:
    rendered = f'"{value}"' if quoted else value
    return f"semver: 1.0.0\nobserved_at: {rendered}\n"


def test_a_bare_timestamp_scalar_reaches_the_contract_as_text() -> None:
    """The resolver is provably suppressed: a str-annotated field accepts it."""
    loaded = load_artifact(_document(_INSTANT), _TEXTUAL)

    assert isinstance(loaded.observed_at, str)
    assert loaded.observed_at == _INSTANT


def test_a_z_designator_yields_an_aware_utc_instant() -> None:
    """The author said UTC; the contract's annotation is what parses it."""
    loaded = load_artifact(_document(_INSTANT), _INSTANTIAL)

    assert loaded.observed_at.tzinfo is not None
    assert loaded.observed_at.utcoffset() == timedelta(0)


def test_an_explicit_zero_offset_yields_the_same_aware_instant() -> None:
    """The two conventions the example suite mixes converge on one value."""
    designated = load_artifact(_document(_INSTANT), _INSTANTIAL)
    offset = load_artifact(_document(_OFFSET_INSTANT), _INSTANTIAL)

    assert designated.observed_at == offset.observed_at


def test_a_timestamp_naming_no_zone_is_refused_by_the_rule_that_forbids_it() -> None:
    """Refused, never guessed: a zone the SDK picked is a zone nobody stated."""
    with pytest.raises(ArtifactLoadError) as raised:
        load_artifact(_document("2026-08-03T12:00:00", quoted=True), _TEXTUAL)

    assert "D-IMPL-38" in str(raised.value)


def test_the_shared_safe_loader_is_not_mutated() -> None:
    """Blast radius: every other caller in the process parses YAML unchanged."""
    parsed = yaml.safe_load(f"t: {_INSTANT}")

    assert isinstance(parsed["t"], datetime)
