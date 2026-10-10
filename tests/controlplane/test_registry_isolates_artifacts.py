"""The Control Plane registry holds and serves independent reconstructions — never a registrant's object, never a reader's (``D-IMPL-380``, sixth round).

The defect this pins (the fifth-round delta review, the Fable seat, reproduced
by the coordinator at ``ef84f801``): every registry door shared identity. The
three write doors stored the registrant's own object by reference
(``register`` :551, ``register_typed`` :611, ``register_versioned`` :794 at that
commit), and both read doors returned the stored object by reference
(``peek`` :839, ``resolve`` :861). So a registrant that changed its original
after registering changed the registry's content under an unchanged version,
and a reader that changed what it was handed changed what every later reader
saw. The grant ledger's approval-sink copy was defeated through exactly this:
a content-identical copy *is the live object's registry address*, and ``peek``
handed the live object back.

Dave, 2026-10-10 14:44 MST: *"Copy on the way in at ``registry.py:794``, and on
the way out at ``:839`` and ``:852``. That covers every artifact class, not
only grants."* 15:10: *"Copy in at all three write doors. Copy-out alone does
not cover every class."* 15:50, under Grok's reviewed amendment: *"Use
canonical serialization and reconstruction for both copy-in and copy-out.
Shallow copies are not accepted."*

**What these tests measure.** Values and fingerprints, never only
``served is not original``: after a change to the original or to a returned
object, a later read serves the artifact as built — its fields, its nested
values, its canonical bytes and the content hash that is its version — and two
successive reads cannot reach each other. The cases cover the three write
doors and both read doors, top-level field rebinding (the reproduced attack,
``object.__setattr__`` on a frozen model), nested mutable-value changes, a
supported untyped artifact (a plain mapping) beside typed models, a real
workflow definition whose ``gate_routes`` are mapping proxies, and the
existing identical-content idempotency.

RED FIRST: every isolation test here fails at ``ef84f801`` on the property it
names. The two preservation tests (type, canonical bytes, hash, equality;
idempotency) hold before and after and guard the fix.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from types import MappingProxyType
from typing import Any

from ccf.authz.capability import Authorized, Register
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.artifacts import HALF_LIFE_TABLE, HalfLifeEntry, HalfLifeTable
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.workflow.definitions import WORKFLOW_DEFINITION, WorkflowDefinition
from http_api.composition_authority import register_versioned_at_composition
from tests.controlplane.capabilities import register_capability
from tests.workflow.test_factory import _workflow_definition, _workflow_fixture

DOC_KEY = "acme/document"
TABLE_KEY = "acme/half-life"


class _Document(CCFContract):
    """A typed artifact with one scalar and one nested mutable value."""

    label: str
    attributes: Mapping[str, str] = {}


def _cap(key: str) -> Authorized[Register]:
    return register_capability(key, Register)


def _clock() -> Any:
    start = datetime(2026, 10, 10, 16, 0, 0, tzinfo=UTC)
    ticks = iter(range(10_000))

    def now() -> datetime:
        return start + timedelta(seconds=next(ticks))

    return now


def _registry() -> ControlPlaneRegistry:
    return ControlPlaneRegistry(clock=_clock())


def _entry(seconds: int = 86_400) -> HalfLifeEntry:
    return HalfLifeEntry(
        half_life_seconds=seconds,
        decay_driver="market-movement",
        supersession_event="next-observation",
        decay_basis="valid-from",
    )


def _table() -> HalfLifeTable:
    return HalfLifeTable(semver="1.0.0", entries={"spread": _entry()})


def _served_as_built(
    served: object, *, as_built_bytes: bytes, version: str, what: str
) -> list[str]:
    """The fingerprint half of every assertion: bytes and hash, by value."""
    problems: list[str] = []
    if canonical_bytes(served) != as_built_bytes:
        problems.append(f"{what}: the served canonical bytes are not the artifact as built")
    if content_hash(served) != version:
        problems.append(
            f"{what}: the served artifact hashes to {content_hash(served)}, not its version {version}"
        )
    return problems


# --- the write doors: the registrant's object is not the registry's ----------


def test_register_a_document_rewritten_after_registration_is_served_as_built() -> None:
    registry = _registry()
    document = _Document(label="as-built", attributes={"k": "v"})
    as_built = canonical_bytes(document)
    version = registry.register(_cap(DOC_KEY), document)

    object.__setattr__(document, "label", "rewritten")  # the reproduced attack

    served = registry.resolve(DOC_KEY, version)
    assert isinstance(served, _Document)
    problems = _served_as_built(served, as_built_bytes=as_built, version=version, what="register")
    if served.label != "as-built":
        problems.append(f"register: the served label is {served.label!r}, not 'as-built'")
    assert not problems, "; ".join(problems)


def test_register_a_nested_value_changed_on_the_original_after_registration_is_served_as_built() -> None:
    registry = _registry()
    document = _Document(label="as-built", attributes={"k": "v"})
    as_built = canonical_bytes(document)
    version = registry.register(_cap(DOC_KEY), document)

    document.attributes["k"] = "rewritten"  # type: ignore[index]  # a nested mutable value
    document.attributes["injected"] = "x"  # type: ignore[index]

    served = registry.resolve(DOC_KEY, version)
    assert isinstance(served, _Document)
    problems = _served_as_built(served, as_built_bytes=as_built, version=version, what="register")
    if dict(served.attributes) != {"k": "v"}:
        problems.append(f"register: the served attributes are {dict(served.attributes)!r}, not {{'k': 'v'}}")
    assert not problems, "; ".join(problems)


def test_register_an_untyped_mapping_changed_after_registration_is_served_as_built() -> None:
    registry = _registry()
    document: dict[str, Any] = {"label": "as-built", "tags": ["x"]}
    as_built = canonical_bytes(document)
    version = registry.register(_cap(DOC_KEY), document)

    document["label"] = "rewritten"
    document["tags"].append("y")

    served = registry.resolve(DOC_KEY, version)
    problems = _served_as_built(served, as_built_bytes=as_built, version=version, what="register[dict]")
    if type(served) is not dict:
        problems.append(f"register[dict]: served type is {type(served).__name__}, not dict")
    if served != {"label": "as-built", "tags": ["x"]}:
        problems.append(f"register[dict]: served {served!r} is not the mapping as built")
    assert not problems, "; ".join(problems)


def test_register_typed_a_table_changed_after_registration_is_served_as_built() -> None:
    registry = _registry()
    table = _table()
    as_built = canonical_bytes(table)
    version = registry.register_typed(_cap(TABLE_KEY), table, HALF_LIFE_TABLE)

    object.__setattr__(table, "semver", "9.9.9")  # top-level rebinding
    table.entries["rate"] = _entry(1)  # type: ignore[index]  # a nested mutable value

    served = registry.resolve(TABLE_KEY, version)
    assert isinstance(served, HalfLifeTable)
    problems = _served_as_built(served, as_built_bytes=as_built, version=version, what="register_typed")
    if served.semver != "1.0.0":
        problems.append(f"register_typed: the served semver is {served.semver!r}, not '1.0.0'")
    if set(served.entries) != {"spread"}:
        problems.append(f"register_typed: the served entries are {sorted(served.entries)!r}, not ['spread']")
    assert not problems, "; ".join(problems)


def test_register_versioned_a_workflow_definition_changed_after_registration_is_served_as_built() -> None:
    registry = _registry()
    definition = _workflow_definition()
    key = _workflow_fixture()["keys"]["workflow_definition"]
    as_built = canonical_bytes(definition)
    name_as_built = definition.name
    handler, ref_as_built = next(iter(definition.exception_refs.items()))
    version = register_versioned_at_composition(registry, key, definition, WORKFLOW_DEFINITION)
    assert isinstance(version, str), version

    # Rewrites that still re-validate. A registry that shared the object must
    # SERVE the rewrite for this assertion to catch it; a rewrite the read door
    # could only refuse would fail this test by an exception instead, and a
    # severing that fails by an exception does not count (D-IMPL-380 §5).
    object.__setattr__(definition, "name", "rewritten-name")  # top-level rebinding
    definition.exception_refs[handler] = ref_as_built.replace("@1.0.0", "@2.0.0")  # type: ignore[index]  # nested

    served = registry.resolve(key, version)
    assert isinstance(served, WorkflowDefinition)
    problems = _served_as_built(served, as_built_bytes=as_built, version=version, what="register_versioned")
    if served.name != name_as_built:
        problems.append(f"register_versioned: the served name is {served.name!r}, not {name_as_built!r}")
    if served.exception_refs[handler] != ref_as_built:
        problems.append("register_versioned: the rewritten exception ref reached the registry")
    if not isinstance(served.gate_routes, MappingProxyType):
        problems.append("register_versioned: the served gate_routes lost their mapping-proxy protection")
    assert not problems, "; ".join(problems)


# --- the read doors: the reader's object is not the registry's ---------------


def test_peek_a_nested_change_to_the_returned_artifact_does_not_change_a_later_read() -> None:
    registry = _registry()
    table = _table()
    as_built = canonical_bytes(table)
    version = registry.register_typed(_cap(TABLE_KEY), table, HALF_LIFE_TABLE)

    first = registry.peek(TABLE_KEY, version)
    assert isinstance(first, HalfLifeTable)
    first.entries["rate"] = _entry(1)  # type: ignore[index]  # nested
    object.__setattr__(first, "semver", "9.9.9")  # top-level

    later = registry.resolve(TABLE_KEY, version)
    assert isinstance(later, HalfLifeTable)
    problems = _served_as_built(later, as_built_bytes=as_built, version=version, what="peek")
    if set(later.entries) != {"spread"}:
        problems.append(f"peek: a nested change to the peeked artifact reached a later read ({sorted(later.entries)!r})")
    if later.semver != "1.0.0":
        problems.append(f"peek: a rebinding on the peeked artifact reached a later read ({later.semver!r})")
    assert not problems, "; ".join(problems)


def test_resolve_a_nested_change_to_the_returned_artifact_does_not_change_a_later_read() -> None:
    registry = _registry()
    table = _table()
    as_built = canonical_bytes(table)
    version = registry.register_typed(_cap(TABLE_KEY), table, HALF_LIFE_TABLE)

    first = registry.resolve(TABLE_KEY, version)
    assert isinstance(first, HalfLifeTable)
    first.entries["rate"] = _entry(1)  # type: ignore[index]  # nested
    object.__setattr__(first, "semver", "9.9.9")  # top-level

    later = registry.resolve(TABLE_KEY, version)
    assert isinstance(later, HalfLifeTable)
    problems = _served_as_built(later, as_built_bytes=as_built, version=version, what="resolve")
    if set(later.entries) != {"spread"}:
        problems.append(f"resolve: a nested change to the resolved artifact reached a later read ({sorted(later.entries)!r})")
    if later.semver != "1.0.0":
        problems.append(f"resolve: a rebinding on the resolved artifact reached a later read ({later.semver!r})")
    assert not problems, "; ".join(problems)


def test_two_successive_reads_are_independent_of_each_other() -> None:
    registry = _registry()
    table = _table()
    as_built = canonical_bytes(table)
    version = registry.register_typed(_cap(TABLE_KEY), table, HALF_LIFE_TABLE)

    problems: list[str] = []
    for pair, first, second in (
        ("resolve/resolve", registry.resolve(TABLE_KEY, version), registry.resolve(TABLE_KEY, version)),
        ("peek/resolve", registry.peek(TABLE_KEY, version), registry.resolve(TABLE_KEY, version)),
    ):
        assert isinstance(first, HalfLifeTable) and isinstance(second, HalfLifeTable)
        first.entries["rate"] = _entry(1)  # type: ignore[index]
        object.__setattr__(first, "semver", "9.9.9")
        problems += _served_as_built(second, as_built_bytes=as_built, version=version, what=pair)
        if set(second.entries) != {"spread"} or second.semver != "1.0.0":
            problems.append(f"{pair}: a change through the first read reached the second")
    assert not problems, "; ".join(problems)


# --- what a served artifact preserves (holds before and after; guards the fix) --


def test_a_served_artifact_keeps_its_type_canonical_bytes_hash_and_equality() -> None:
    registry = _registry()
    document = _Document(label="as-built", attributes={"k": "v"})
    table = _table()
    definition = _workflow_definition()
    key = _workflow_fixture()["keys"]["workflow_definition"]
    cases = (
        ("register", DOC_KEY, document, registry.register(_cap(DOC_KEY), document)),
        ("register_typed", TABLE_KEY, table, registry.register_typed(_cap(TABLE_KEY), table, HALF_LIFE_TABLE)),
        ("register_versioned", key, definition,
         register_versioned_at_composition(registry, key, definition, WORKFLOW_DEFINITION)),
    )
    problems: list[str] = []
    for door, k, original, version in cases:
        assert isinstance(version, str), version
        for read, served in (("resolve", registry.resolve(k, version)), ("peek", registry.peek(k, version))):
            what = f"{door}/{read}"
            if type(served) is not type(original):
                problems.append(f"{what}: served type {type(served).__name__} is not {type(original).__name__}")
            problems += _served_as_built(served, as_built_bytes=canonical_bytes(original), version=version, what=what)
            if served != original:
                problems.append(f"{what}: the served artifact is not equal to the artifact as built")
    served_definition = registry.resolve(key, cases[2][3])  # type: ignore[arg-type]
    assert isinstance(served_definition, WorkflowDefinition)
    if not isinstance(served_definition.gate_routes, MappingProxyType) or not all(
        isinstance(routes, MappingProxyType) for routes in served_definition.gate_routes.values()
    ):
        problems.append("register_versioned/resolve: gate_routes are not mapping proxies at both levels")
    assert not problems, "; ".join(problems)


def test_identical_content_is_still_idempotent_and_a_rewritten_original_registers_as_a_new_version() -> None:
    registry = _registry()
    document = _Document(label="as-built")
    first = registry.register(_cap(DOC_KEY), document)
    again = registry.register(_cap(DOC_KEY), document)
    assert again == first and registry.versions(DOC_KEY) == (first,)

    object.__setattr__(document, "label", "rewritten")
    second = registry.register(_cap(DOC_KEY), document)

    problems: list[str] = []
    if second == first:
        problems.append("a rewritten original re-registered as the same version")
    if registry.versions(DOC_KEY) != (first, second):
        problems.append(f"versions are {registry.versions(DOC_KEY)!r}, not (first, second)")
    served_first = registry.resolve(DOC_KEY, first)
    served_second = registry.resolve(DOC_KEY, second)
    assert isinstance(served_first, _Document) and isinstance(served_second, _Document)
    if served_first.label != "as-built":
        problems.append(f"the first version now serves {served_first.label!r}: the rewrite reached it")
    if served_second.label != "rewritten" or content_hash(served_second) != second:
        problems.append("the second version does not serve the rewritten content under its own hash")
    assert not problems, "; ".join(problems)
