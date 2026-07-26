"""The one canonical serialization and content-identity utility of the SDK.

SDK-defined mechanism (CLAUDE.md §11) serving three whitepaper-derived
obligations that all reduce to *byte-level determinism*:

* **Composition preservation** (whitepaper §7.4, ``(A∘B)(G) = A(B(G))``) is
  asserted bit-for-bit, so operator outputs must have exactly one serialized
  form.
* **Decision Replay** (whitepaper §7.10.1) reproduces a prior product exactly;
  "exactly" is only checkable against a canonical form.
* **Artifact addressing** (CLAUDE.md §7.4, D-IMPL-26) is
  ``sha256(canonical_bytes(artifact))``.

Nothing else in the SDK may define its own canonical form. If a subsystem
needs a digest, it hashes these bytes.

Canonical form
--------------
UTF-8 JSON with sorted mapping keys and compact separators (``,`` / ``:``),
plus these normalizations:

============================  ==================================================
Input                         Canonical rendering
============================  ==================================================
mapping                       object with keys sorted by code point; keys must
                              be ``str``
set / frozenset               array sorted by each element's own canonical bytes
list / tuple                  array, order preserved (order is meaningful)
``datetime``                  RFC3339 UTC at fixed microsecond precision,
                              ``YYYY-MM-DDTHH:MM:SS.ffffffZ``; offsets are
                              converted, naive values rejected
``date``                      ``YYYY-MM-DD``
``Decimal``                   string in positional notation (never a JSON
                              number — JSON numbers are not round-trip stable)
``int`` / ``bool`` / ``str``  as-is
``None``                      ``null``
============================  ==================================================

Rejected outright, with :class:`CanonicalizationError`:

* ``float`` — binary floating point is not bit-stable across platforms and
  backends (04-RESEARCH.md anti-pattern). Use ``int`` or ``Decimal``.
* naive ``datetime`` — an implicit timezone is a silent default, and silent
  defaults are prohibited (D-IMPL-38).
* non-``str`` mapping keys, and any type not listed above — an unsupported
  type must fail loudly rather than acquire an accidental encoding.

This module is algorithmic (CINV-03): pure functions over typed inputs, no
I/O, no clock, no LLM dependency ever.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence, Set
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel

__ccf_mode__ = "algorithmic"

__all__ = [
    "CanonicalizationError",
    "canonical_bytes",
    "canonical_timestamp",
    "content_hash",
]

_TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


class CanonicalizationError(TypeError):
    """A value has no canonical rendering and must not be silently encoded."""


def _normalize(value: object) -> Any:
    """Recursively rewrite ``value`` into the JSON-safe canonical shape."""
    if value is None or isinstance(value, (bool, int, str)):
        # Checked before float: bool and int are exact, float never reaches here.
        return value
    if isinstance(value, float):
        raise CanonicalizationError(
            "float is not canonically encodable (not bit-stable across "
            "platforms); use int or decimal.Decimal"
        )
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise CanonicalizationError("non-finite Decimal is not encodable")
        return format(value, "f")
    if isinstance(value, datetime):
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            raise CanonicalizationError(
                "naive datetime is not canonically encodable; attach an "
                "explicit timezone (no implicit UTC — D-IMPL-38)"
            )
        return value.astimezone(UTC).strftime(_TIMESTAMP_FORMAT)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, BaseModel):
        # Field-by-field rather than `model_dump()`: a model dumped to Python
        # rebuilds set-valued fields *as sets of dicts*, which are unhashable,
        # so a contract holding `frozenset[LineageEntry]` — that is, every
        # claim in the fabric — cannot be dumped at all. Walking the fields
        # keeps each nested model a model until this function renders it.
        return {
            name: _normalize(getattr(value, name))
            for name in type(value).model_fields
        }
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise CanonicalizationError(
                    f"mapping keys must be str, got {type(key).__name__}"
                )
            normalized[key] = _normalize(item)
        return normalized
    if isinstance(value, Set):
        # Sets are unordered by definition; a deterministic array requires a
        # total order, and each element's own canonical bytes supply one.
        return [
            element
            for _, element in sorted(
                ((_dumps(_normalize(e)), _normalize(e)) for e in value),
                key=lambda pair: pair[0],
            )
        ]
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [_normalize(element) for element in value]
    raise CanonicalizationError(
        f"{type(value).__name__} has no canonical rendering"
    )


def _dumps(normalized: Any) -> str:
    return json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def canonical_bytes(obj: object) -> bytes:
    """Return the single canonical UTF-8 byte rendering of ``obj``.

    Semantically equal inputs produce identical bytes regardless of mapping
    key insertion order, set iteration order, timezone representation, or
    process hash seed. See the module docstring for the full form.

    Raises:
        CanonicalizationError: the input contains a value with no canonical
            rendering (float, naive datetime, non-``str`` mapping key, or an
            unsupported type).
    """
    return _dumps(_normalize(obj)).encode("utf-8")


def canonical_timestamp(value: datetime) -> str:
    """Return the canonical RFC3339 UTC text rendering of ``value``.

    Exposed because storage backends must write timestamps as text with the
    *same* form the canonical serializer uses. A backend that formatted its own
    would be defining a second canonical form — the one thing this module
    exists to prevent — and would reintroduce exactly the SQLite/Postgres
    precision drift that makes cross-backend comparison flaky
    (04-RESEARCH.md Pitfall 3). The fixed-width rendering also sorts
    lexicographically, so ``ORDER BY`` on the text column is chronological.

    Raises:
        CanonicalizationError: ``value`` is naive (D-IMPL-38).
    """
    rendered = _normalize(value)
    if not isinstance(rendered, str):  # pragma: no cover - unreachable by type
        raise CanonicalizationError("datetime did not render as text")
    return rendered


def content_hash(obj: object) -> str:
    """Return the lowercase sha256 hex digest of ``canonical_bytes(obj)``.

    This is the SDK's content-address primitive (D-IMPL-26) and the identity
    used by replay hashing and composition-preservation comparisons.
    """
    return hashlib.sha256(canonical_bytes(obj)).hexdigest()
