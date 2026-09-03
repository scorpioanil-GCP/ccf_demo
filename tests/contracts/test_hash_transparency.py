"""The hash-transparent mark and the omission rule (``D-IMPL-243``).

Whitepaper §7.10 (a decision reconstructible years later against the exact
identities it was made with); CLAUDE.md §7.4 (replay resolves exact versions,
never "latest"). Phase 24.5's close review (CR-01) measured that every
sentinel-defaulted field the phase added moved the content hash of every model
carrying it — a replay record's per-step ``parameter_hash``, its
``graph_query_sequence`` pins, every Control Plane version — because
``ccf.contracts.canonical::_normalize`` renders every field. ``D-IMPL-243``
rules that such a field is a generation change unless its owner marks it
``ccf_hash_transparent``, meaning its sentinel *is* the old contract; a marked
field is omitted at its sentinel and rendered otherwise. Dave's rule, verbatim:
"silence equals yesterday".

Every model here is a scratch model owned by this module: the rule is about
the canonicalizer, and proving it on a real SDK contract would prove the mark
on that contract rather than the mechanism. The real marks are proven against
the ``13bd250`` tree in ``tests/replay/`` (the golden fixture) and were
measured per model in ``24.5-FIX-01-SUMMARY.md``.
"""

from __future__ import annotations

import pytest
from pydantic import Field

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import (
    HASH_TRANSPARENT_KEY,
    CanonicalizationError,
    canonical_bytes,
    content_hash,
    generation_mismatch,
    hash_transparent_fields,
)
from ccf.graph.protocols import NO_STORE_SNAPSHOT_PIN, StoreSnapshotPin


class _Yesterday(CCFContract):
    """The contract as it was before any field below existed."""

    a: int


class _Today(CCFContract):
    """The same contract after three transparent fields were added.

    One sentinel of each declared form the SDK uses: a plain ``default``, a
    ``default_factory``, and a model-valued default that compares by value.
    """

    a: int
    t: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    f: dict[str, str] = Field(
        default_factory=dict, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    pin: StoreSnapshotPin = Field(
        default=NO_STORE_SNAPSHOT_PIN,
        json_schema_extra={HASH_TRANSPARENT_KEY: True},
    )


class _TodayUnmarked(CCFContract):
    """The same addition WITHOUT the mark — the generation change, as ruled."""

    a: int
    n: int = 0


class _NoSentinel(CCFContract):
    """A mark on a field with no default: nothing to be silent at."""

    a: int
    t: str = Field(json_schema_extra={HASH_TRANSPARENT_KEY: True})


class _Outer(CCFContract):
    inner: _TodayUnmarked
    optional: _TodayUnmarked | None = None
    silent: _Today | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )


# --- the mark ---------------------------------------------------------------


def test_the_mark_is_read_from_the_field_declaration() -> None:
    assert hash_transparent_fields(_Today) == frozenset({"t", "f", "pin"})
    assert hash_transparent_fields(_Yesterday) == frozenset()
    assert hash_transparent_fields(_TodayUnmarked) == frozenset()


def test_only_the_literal_true_is_a_mark() -> None:
    class _Loose(CCFContract):
        a: int
        yes: int = Field(default=0, json_schema_extra={HASH_TRANSPARENT_KEY: 1})
        text: int = Field(
            default=0, json_schema_extra={HASH_TRANSPARENT_KEY: "true"}
        )

    assert hash_transparent_fields(_Loose) == frozenset()
    assert canonical_bytes(_Loose(a=1)) == b'{"a":1,"text":0,"yes":0}'


def test_a_mark_without_a_default_is_refused_not_ignored() -> None:
    with pytest.raises(CanonicalizationError, match="_NoSentinel.t") as refused:
        content_hash(_NoSentinel(a=1, t="q"))
    assert "D-IMPL-243" in str(refused.value)


# --- the omission rule: silence equals yesterday ------------------------------


def test_a_marked_field_at_its_sentinel_is_omitted() -> None:
    assert canonical_bytes(_Today(a=1)) == canonical_bytes(_Yesterday(a=1))
    assert content_hash(_Today(a=1)) == content_hash(_Yesterday(a=1))
    assert canonical_bytes(_Today(a=1)) == b'{"a":1}'


def test_the_sentinel_is_compared_by_value_not_identity() -> None:
    same_pin = StoreSnapshotPin(substrate="none", pin="no-store-snapshot-pin")
    assert same_pin is not NO_STORE_SNAPSHOT_PIN
    assert content_hash(_Today(a=1, pin=same_pin)) == content_hash(
        _Yesterday(a=1)
    )
    assert content_hash(_Today(a=1, f={})) == content_hash(_Yesterday(a=1))


@pytest.mark.parametrize(
    ("field", "value", "rendered"),
    [
        ("t", "x", b'{"a":1,"t":"x"}'),
        ("f", {"k": "v"}, b'{"a":1,"f":{"k":"v"}}'),
        (
            "pin",
            StoreSnapshotPin(substrate="fluree", pin="7"),
            b'{"a":1,"pin":{"pin":"7","substrate":"fluree"}}',
        ),
    ],
)
def test_a_non_sentinel_value_is_rendered_and_moves_the_hash(
    field: str, value: object, rendered: bytes
) -> None:
    today = _Today(a=1, **{field: value})
    assert canonical_bytes(today) == rendered
    assert content_hash(today) != content_hash(_Yesterday(a=1))


def test_an_unmarked_default_still_renders() -> None:
    """The rule is not "defaults never count"."""
    assert canonical_bytes(_TodayUnmarked(a=1)) == b'{"a":1,"n":0}'
    assert content_hash(_TodayUnmarked(a=1)) != content_hash(_Yesterday(a=1))


def test_a_transparent_model_valued_field_is_walked_when_present() -> None:
    outer = _Outer(inner=_TodayUnmarked(a=1), silent=_Today(a=2, t="deep"))
    assert canonical_bytes(outer) == (
        b'{"inner":{"a":1,"n":0},"optional":null,"silent":{"a":2,"t":"deep"}}'
    )


# --- the converse: generation_mismatch ---------------------------------------


def test_a_stored_object_lacking_only_transparent_fields_is_the_same_generation() -> None:
    assert generation_mismatch(_Today, {"a": 1}) == ()


def test_a_stored_object_lacking_a_non_transparent_field_is_named() -> None:
    assert generation_mismatch(_TodayUnmarked, {"a": 1}) == ("n",)


def test_a_stored_object_carrying_every_field_is_the_same_generation() -> None:
    assert generation_mismatch(_TodayUnmarked, {"a": 1, "n": 0}) == ()
    assert generation_mismatch(_Today, {"a": 1, "t": "x"}) == ()


def test_nested_models_are_walked_and_reported_dotted() -> None:
    stored = {"inner": {"a": 1}, "optional": {"a": 2}, "silent": {"a": 3}}
    assert generation_mismatch(_Outer, stored) == ("inner.n", "optional.n")


def test_an_absent_nested_field_is_reported_once_as_the_outer_name() -> None:
    assert generation_mismatch(_Outer, {"inner": {"a": 1, "n": 0}}) == (
        "optional",
    )


def test_a_null_nested_value_is_a_leaf_not_a_walk() -> None:
    stored = {"inner": {"a": 1, "n": 0}, "optional": None}
    assert generation_mismatch(_Outer, stored) == ()
