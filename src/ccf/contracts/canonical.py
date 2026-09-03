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

Hash-transparent fields — "silence equals yesterday"
-----------------------------------------------------
A model renders **every** declared field, defaults included. That is what
makes the form canonical, and it is also why an additive, sentinel-defaulted
field moves the content hash of every instance of the model that carries it —
a replay record's ``parameter_hash`` per step, its ``graph_query_sequence``
pins, and every Control Plane version minted by ``content_hash(artifact)``.
``D-IMPL-243`` rules that a new required-default field in the canonical form
is a **generation change**, not a hash-neutral addition, and names exactly one
exception, in Dave's words:

    "A field is hash-transparent only when its sentinel means the old
    contract: the walk / table / request is observationally the same as a
    record written before the field existed. Mark that at the field
    (``ccf_hash_transparent``). ``_normalize`` omits it when the value is that
    sentinel. Any non-sentinel value is rendered and must move the hash. That
    is not 'defaults never count.' It is 'silence equals yesterday.'"

The mark is the ``json_schema_extra`` key :data:`HASH_TRANSPARENT_KEY`
(``"ccf_hash_transparent"``) set to ``True`` on the field. A marked field is
**omitted** from the rendering when its value ``==`` its declared sentinel —
the field's ``default``, or the result of its ``default_factory`` — and is
rendered exactly as any other field otherwise. So a model whose marked fields
all sit at their sentinels hashes byte-for-byte as the model did before those
fields existed (whitepaper §7.10: a decision reconstructible years later;
CLAUDE.md §7.4: replay resolves exact identities, never "latest"), while any
non-sentinel value is inside the hash. :func:`hash_transparent_fields` reads
the marks; :func:`generation_mismatch` is the converse check the replay engine
runs on a stored record — a field the running class declares, absent from the
stored bytes and **not** marked transparent, is a generation change the record
cannot cross, refused by name (``canonical_generation_mismatch``).

This module is algorithmic (CINV-03): pure functions over typed inputs, no
I/O, no clock, no LLM dependency ever.
"""

from __future__ import annotations

import hashlib
import json
import types
from collections.abc import Mapping, Sequence, Set
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, Final, Union, get_args, get_origin

from pydantic import BaseModel
from pydantic_core import PydanticUndefined

__ccf_mode__ = "algorithmic"

__all__ = [
    "HASH_TRANSPARENT_KEY",
    "CanonicalizationError",
    "canonical_bytes",
    "canonical_timestamp",
    "content_hash",
    "generation_mismatch",
    "hash_transparent_fields",
]

_TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"

#: The ``json_schema_extra`` key that marks a field hash-transparent
#: (``D-IMPL-243``). Declared at the field —
#: ``Field(default=SENTINEL, json_schema_extra={HASH_TRANSPARENT_KEY: True})``
#: — never inferred: a field is transparent because its owner asserted that
#: its sentinel means the contract as it was before the field existed, and
#: for no other reason. Any value other than ``True`` under the key is not a
#: mark. The key surfaces in the exported JSON Schema, so an adopter reading
#: ``docs/schemas/`` can see which fields are silent at their sentinel.
HASH_TRANSPARENT_KEY: Final[str] = "ccf_hash_transparent"

#: Exact scalar types that render as themselves. Membership is tested on the
#: value's own ``__class__``, never with ``isinstance``, so this set decides
#: nothing about subclasses — a ``str`` subclass misses it and falls through to
#: the ``isinstance`` chain below, which renders it exactly as it always did.
#: This is a dispatch shortcut for the overwhelmingly common case, not a second
#: rule about what is canonically encodable.
_EXACT_SCALARS: frozenset[type] = frozenset({str, int, bool, type(None)})

#: Field names per model class, memoized. ``BaseModel.model_fields`` is a
#: class-level property reached through a Pydantic deprecation shim, and a
#: graph view hashes hundreds of thousands of model fields; the names are fixed
#: once a class is built, so resolving them once per class is the same answer
#: for strictly less work. Keyed by class, which outlives any value.
_MODEL_FIELD_NAMES: dict[type, tuple[str, ...]] = {}

#: Per model class, the hash-transparent fields and their sentinels
#: (``D-IMPL-243``), memoized for the same reason and on the same key as
#: :data:`_MODEL_FIELD_NAMES`: the marks and the defaults are fixed once a
#: class is built, and the omission test runs once per field of every model a
#: graph view hashes. An empty mapping is the common case — most models mark
#: nothing — and costs one dictionary lookup per model rendered.
_TRANSPARENT_SENTINELS: dict[type, Mapping[str, object]] = {}


class CanonicalizationError(TypeError):
    """A value has no canonical rendering and must not be silently encoded."""


def _field_names(model_type: type) -> tuple[str, ...]:
    """The declared field names of ``model_type``, in declaration order."""
    names = _MODEL_FIELD_NAMES.get(model_type)
    if names is None:
        names = tuple(model_type.model_fields)  # type: ignore[attr-defined]
        _MODEL_FIELD_NAMES[model_type] = names
    return names


def _is_marked_transparent(field: Any) -> bool:
    """Whether one ``FieldInfo`` carries the ``D-IMPL-243`` mark."""
    extra = field.json_schema_extra
    return isinstance(extra, Mapping) and extra.get(HASH_TRANSPARENT_KEY) is True


def _declared_sentinel(model_type: type, name: str, field: Any) -> object:
    """The value a transparent field is silent at: its default, computed once.

    A field marked transparent without a default has no sentinel to be silent
    at, which makes the mark meaningless; it is refused here rather than
    rendered as if unmarked, because a mark that quietly did nothing is the
    exact defect class the mark exists to make visible.
    """
    if field.default is not PydanticUndefined:
        return field.default
    if field.default_factory is not None:
        return field.default_factory()
    raise CanonicalizationError(
        f"{model_type.__name__}.{name} is marked {HASH_TRANSPARENT_KEY!r} "
        "but declares no default; a hash-transparent field must have a "
        "sentinel to be silent at (D-IMPL-243)"
    )


def _transparent_sentinels(model_type: type) -> Mapping[str, object]:
    """Name → sentinel for every field of ``model_type`` marked transparent."""
    sentinels = _TRANSPARENT_SENTINELS.get(model_type)
    if sentinels is None:
        fields = model_type.model_fields  # type: ignore[attr-defined]
        sentinels = {
            name: _declared_sentinel(model_type, name, field)
            for name, field in fields.items()
            if _is_marked_transparent(field)
        }
        _TRANSPARENT_SENTINELS[model_type] = sentinels
    return sentinels


def hash_transparent_fields(model_cls: type[BaseModel]) -> frozenset[str]:
    """The fields of ``model_cls`` marked hash-transparent (``D-IMPL-243``).

    Read from the field declarations — ``json_schema_extra`` carrying
    :data:`HASH_TRANSPARENT_KEY` ``True`` — never from a table anywhere else,
    so the answer here and the omission :func:`canonical_bytes` performs
    cannot disagree. A model that marks nothing answers the empty set, which
    is the answer for every model in the SDK before Phase 24.5.

    Whitepaper §7.10; CLAUDE.md §7.4.
    """
    return frozenset(_transparent_sentinels(model_cls))


def _nested_model_class(annotation: object) -> type[BaseModel] | None:
    """The single model class an annotation names, or ``None``.

    ``Model`` and ``Model | None`` resolve; anything else — a scalar, a
    collection, a union of two models — does not, and the field is then read
    as a leaf whose presence is the whole question.
    """
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return annotation
    origin = get_origin(annotation)
    if origin is Union or origin is types.UnionType:
        models = [
            arg
            for arg in get_args(annotation)
            if isinstance(arg, type) and issubclass(arg, BaseModel)
        ]
        if len(models) == 1:
            return models[0]
    return None


def generation_mismatch(
    model_cls: type[BaseModel], stored: Mapping[str, object]
) -> tuple[str, ...]:
    """Fields ``model_cls`` renders that ``stored`` lacks and cannot be silent on.

    The converse of the omission rule (``D-IMPL-243``): the running class
    renders every field except a transparent one at its sentinel, so a field
    the class declares that is **absent** from a stored canonical object was
    either omitted as transparent — in which case the stored bytes and the
    running canonicalizer agree, and the record replays — or never existed
    when the bytes were written and is not transparent, in which case the
    stored object belongs to an earlier generation of the canonical form and
    no hash the running code computes can be compared with one it carries.
    The second case is what this function names, so the replay engine can
    refuse it as ``canonical_generation_mismatch`` **by field name, before
    re-execution** — never as a generic step mismatch and never as a silent
    upgrade (Dave's words in ``D-IMPL-243``: "not a quiet address drift and
    not a silent upgrade").

    Nested models are walked: a field whose annotation names one model class
    (``Model`` or ``Model | None``) and whose stored value is a mapping is
    checked against that class, and its findings are reported dotted
    (``"outer.inner"``). A nested field the stored object lacks entirely is
    reported once, as the outer name — nothing below an absent field can be
    inspected. Collections of models are leaves: their elements are not
    individually walked here. The empty tuple means the stored object and the
    running class are the same generation on every non-transparent field.

    Args:
        model_cls: The class the running code would validate ``stored`` as.
        stored: The parsed canonical JSON object as fetched — the bytes, not a
            re-validated model, because validation fills every default and
            would erase the very absence this function measures.

    Whitepaper §7.10; CLAUDE.md §7.4.
    """
    transparent = _transparent_sentinels(model_cls)
    fields = model_cls.model_fields
    missing: list[str] = []
    for name, field in fields.items():
        if name not in stored:
            if name not in transparent:
                missing.append(name)
            continue
        nested = _nested_model_class(field.annotation)
        value = stored[name]
        if nested is not None and isinstance(value, Mapping):
            missing.extend(
                f"{name}.{inner}" for inner in generation_mismatch(nested, value)
            )
    return tuple(missing)


def _normalize(value: object) -> Any:
    """Recursively rewrite ``value`` into the JSON-safe canonical shape."""
    if value.__class__ in _EXACT_SCALARS:
        # The exact-type shortcut for the same three scalars (and ``None``) the
        # isinstance chain below admits — checked first because it is what a
        # graph view is mostly made of. Subclasses miss it deliberately and are
        # decided by the chain.
        return value
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
        #
        # A field marked hash-transparent (D-IMPL-243) is OMITTED when its
        # value is its declared sentinel — "silence equals yesterday": the
        # model then renders exactly as it did before the field existed. Any
        # other value is rendered as every field is. The comparison is `==`,
        # so a sentinel that is itself a model (NO_STORE_SNAPSHOT_PIN,
        # NO_SERVE_OBLIGATIONS) compares by value, never by identity.
        model_type = value.__class__
        transparent = _transparent_sentinels(model_type)
        if not transparent:
            return {
                name: _normalize(getattr(value, name))
                for name in _field_names(model_type)
            }
        rendered: dict[str, Any] = {}
        for name in _field_names(model_type):
            field_value = getattr(value, name)
            if name in transparent and field_value == transparent[name]:
                continue
            rendered[name] = _normalize(field_value)
        return rendered
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
        #
        # Each element is normalized ONCE and the same normalized value is both
        # sorted on and returned. The rendering is unchanged — the sort key is
        # still the element's own canonical bytes — but a `frozenset` field is
        # the shape every claim in the fabric carries its lineage in, so
        # normalizing each element a second time to return it doubled the cost
        # of hashing a graph view.
        #
        # A set of fewer than two elements has exactly one ordering, so the
        # total order is not consulted for it and no sort key is rendered. The
        # array is the same array either way; what is skipped is the work of
        # proving an ordering that has no alternative. This is the common case
        # by a wide margin — a claim observed once carries one lineage entry.
        normalized_elements = [_normalize(element) for element in value]
        if len(normalized_elements) < 2:
            return normalized_elements
        return [
            element
            for _, element in sorted(
                ((_dumps(element), element) for element in normalized_elements),
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
