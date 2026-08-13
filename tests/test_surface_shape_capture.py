"""`DI-15.5-06` — what the surface manifest can and cannot see about a shape.

`tools/dump_surface.py` resolved every class's shape with `inspect.signature`
on the **class**, which for a ``Protocol`` returns ``__init__`` and therefore
the information-free ``"(*args, **kwargs)"``. `D-IMPL-110` proved the cost by
demonstration: plan `15.5-15` took both resolver seams from three arguments to
five — breaking for every adopter implementing them — and
``docs/surface/v0.2-surface.json`` was **byte-identical across that change**.

This module pins the fix and, just as importantly, **pins what the fix
deliberately does not do**. `D-IMPL-122` scoped it to ``__call__`` capture plus
the information-free type aliases, and descoped multi-method Protocols on a
measured cost. A descope that is not asserted is a descope that quietly becomes
a regression, so the no-``__call__`` behaviour is a test here rather than a
comment there.

Why this module lives in ``tests/`` rather than ``tools/dump_surface_tests/``
-----------------------------------------------------------------------------

The two nearby precedents — ``tools/publish_scan_tests/`` and
``tools/lints/tests/`` — put a tool's tests beside the tool. That is the wrong
home for this one. ``pyproject.toml`` sets ``testpaths = ["tests"]``, so a
module under ``tools/`` runs only in CI's separate step and **not** under
``make ci-core``. ``dump_surface`` is the generator half of the surface record;
a change to what it can see is exactly the class of change that must fail
inside the mid-phase gate, on the commit that causes it, rather than in a
step a worktree may never run.
"""

from __future__ import annotations

import inspect
import json
import pathlib
import re
from collections.abc import Callable, Mapping
from typing import Any, Literal, Protocol, Union

import tools.dump_surface as dump_surface
from tools.dump_surface import _shape_of, build_surface, diff_surfaces, serialize

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
_LIVE_MANIFEST = _REPO_ROOT / "docs" / "surface" / "v0.2-surface.json"

#: The information-free rendering the fix exists to displace.
_INFORMATION_FREE = "(*args, **kwargs)"

#: The two seams `D-IMPL-110` names as the demonstration. Their widening from
#: three arguments to five shipped in `15.5-15` with no manifest diff at all.
_RESOLVER_SEAMS = (
    "ccf_runtime.mcp.egress.ProductResolverProtocol",
    "ccf_runtime.mcp.experience.ExperienceProductResolverProtocol",
)


def _legacy_shape_of(obj: Any, kind: str) -> Any:
    """The pre-fix ``_shape_of``, restated so the fix can be diffed against it.

    Restated rather than imported because the point of the comparison is that
    the old behaviour is *gone*; a version of this helper that delegated to the
    module under test would pass no matter what the fix did.
    """
    if kind == "contract":
        fields = getattr(obj, "model_fields", {})
        return {name: str(field.annotation) for name, field in sorted(fields.items())}
    if kind in ("class", "function"):
        try:
            return str(inspect.signature(obj))
        except (TypeError, ValueError):
            return type(obj).__name__
    return type(obj).__name__


def _flat(document: dict[str, Any]) -> dict[str, Any]:
    return {
        f"{module}.{name}": entry
        for module, record in document.items()
        for name, entry in record.get("exports", {}).items()
    }


def _legacy_surface(monkeypatch: Any) -> dict[str, Any]:
    monkeypatch.setattr(dump_surface, "_shape_of", _legacy_shape_of)
    return build_surface()


# --- Sample fixtures: structural detection, not name matching ---------------


class _CalledProtocol(Protocol):
    """A Protocol with a ``__call__`` and *without* a ``Protocol`` suffix."""

    def __call__(self, *, tenant: str, count: int = 1) -> str: ...


class _MethodsOnlyProtocol(Protocol):
    """A Protocol whose whole contract is a method set — the descoped shape."""

    def read(self, key: str) -> str: ...

    def write(self, key: str, value: str) -> None: ...


class NotAProtocol:
    """A plain class whose *name* would fool a name-based rule."""

    def __init__(self, alpha: int, beta: str = "b") -> None:
        self.alpha = alpha
        self.beta = beta

    def __call__(self, gamma: float) -> float:
        return gamma


# --- 1. `__call__` capture --------------------------------------------------


def test_a_protocol_with_call_records_that_call_with_self_elided() -> None:
    """The defect, inverted into an assertion.

    ``self`` is elided because it is not part of the contract an adopter
    implements against — a caller supplies ``tenant`` and ``count``, never
    ``self``.
    """
    shape = _shape_of(_CalledProtocol, "class")
    assert shape != _INFORMATION_FREE
    # The annotations read back quoted because this module carries
    # ``from __future__ import annotations`` — that is a property of the
    # fixture's defining module, not of the renderer, and the real shipped
    # Protocols below are asserted on substance rather than on this exact form.
    assert shape == "(*, tenant: 'str', count: 'int' = 1) -> 'str'", shape
    assert "self" not in shape


def test_the_shipped_resolver_seams_now_show_their_five_arguments() -> None:
    """`D-IMPL-110`'s demonstration case, asserted against the real objects.

    These are the two Protocols whose three-to-five widening the manifest could
    not see. If this assertion ever reads three arguments again, the audit fix
    has been undone.
    """
    from ccf_runtime.mcp.egress import ProductResolverProtocol
    from ccf_runtime.mcp.experience import ExperienceProductResolverProtocol

    for protocol in (ProductResolverProtocol, ExperienceProductResolverProtocol):
        shape = _shape_of(protocol, "class")
        assert shape != _INFORMATION_FREE, protocol
        for argument in (
            "tenant",
            "product_class",
            "version",
            "perspective",
            "request",
        ):
            assert argument in shape, (protocol, argument, shape)


def test_protocol_detection_is_structural_rather_than_name_based() -> None:
    """A name-based rule would miss ``PeerCardResolver`` and catch this class.

    Two of the twelve capture targets — ``PeerCardResolver`` and
    ``PeerEndpointResolver`` — carry no ``Protocol`` suffix, and a class can be
    named ``...Protocol`` without being one. The rule keys on the runtime
    marker instead.
    """
    assert _shape_of(_CalledProtocol, "class") != _INFORMATION_FREE

    plain = _shape_of(NotAProtocol, "class")
    assert plain == "(alpha: 'int', beta: 'str' = 'b') -> 'None'", plain
    assert "gamma" not in plain, (
        "the plain class's ``__call__`` was captured; the branch is reaching"
        " past Protocols"
    )

    from ccf_runtime.peering.lf_a2a import PeerCardResolver

    assert _shape_of(PeerCardResolver, "class") != _INFORMATION_FREE


# --- 2. The descope, pinned so it cannot silently become a regression -------


def test_a_protocol_with_no_call_keeps_the_information_free_shape() -> None:
    """`D-IMPL-122` limb 2, asserted rather than commented.

    Dave ruled ``__call__``-only capture over full method-set capture on a
    measured cost — 11 new ``reshaped`` diff lines against 65. The consequence
    is that a Protocol whose whole contract is a method set is **still**
    invisible to the manifest, and this assertion is where that stays on the
    record. Changing it is a scope change requiring a ruling, not a repair.
    """
    from ccf.artifacts.protocol import ArtifactStoreProtocol
    from ccf.controlplane.registry import ControlPlaneProtocol
    from ccf.harness import HarnessAdapterProtocol

    assert _shape_of(_MethodsOnlyProtocol, "class") == _INFORMATION_FREE
    for descoped in (
        ArtifactStoreProtocol,
        ControlPlaneProtocol,
        HarnessAdapterProtocol,
    ):
        assert _shape_of(descoped, "class") == _INFORMATION_FREE, descoped


# --- 3. Type aliases (`D-IMPL-122` limb 3) ----------------------------------


def test_type_aliases_record_their_type_rather_than_a_call_signature() -> None:
    """An alias is a type, and ``inspect.signature`` on one is meaningless.

    A ``Literal`` alias gaining or losing a member is a real surface change an
    adopter must act on; before the fix every one of them rendered
    ``(*args, **kwargs)`` and no such change produced a diff line.
    """
    cases = {
        Literal["a", "b"]: "typing.Literal['a', 'b']",
        Union[int, str]: "typing.Union[int, str]",
        Mapping[str, str]: "collections.abc.Mapping[str, str]",
    }
    for alias, expected in cases.items():
        assert _shape_of(alias, "function") == expected, alias

    callable_alias = _shape_of(Callable[[int], str], "function")
    assert callable_alias == "collections.abc.Callable[[int], str]", callable_alias


def test_a_literal_alias_losing_a_member_moves_its_shape() -> None:
    """The property the alias half of the fix exists for."""
    before = _shape_of(Literal["a", "b"], "function")
    after = _shape_of(Literal["a"], "function")
    assert before != after


def test_the_shipped_literal_aliases_render_their_members() -> None:
    from ccf.operators.base import OperatorCategory
    from ccf.products.contract import TTLAnchor

    category = _shape_of(OperatorCategory, "function")
    assert "traversal" in category and "similarity" in category, category
    anchor = _shape_of(TTLAnchor, "function")
    assert "from_decision" in anchor, anchor


def test_an_annotated_alias_renders_without_a_memory_address() -> None:
    """The determinism trap the alias fix walks into if it just calls ``str``.

    ``str(Annotated[X, AfterValidator(f)])`` embeds ``<function f at 0x...>``.
    Committed verbatim that would make the manifest differ between two runs on
    an unchanged tree, which is a worse defect than the blind spot being fixed.
    """
    from ccf.halflife.assessment import DebtEvidence

    shape = _shape_of(DebtEvidence, "function")
    assert shape != _INFORMATION_FREE
    assert "0x" not in shape, shape
    assert "DebtEvidencePointer" in shape, shape


def test_the_serialized_manifest_carries_no_memory_addresses() -> None:
    """The determinism guard, applied to the whole manifest rather than a case."""
    emitted = serialize(build_surface())
    addresses = sorted(set(re.findall(r"0x[0-9a-fA-F]{6,}", emitted)))
    assert not addresses, addresses


def test_the_manifest_is_byte_stable_across_two_builds() -> None:
    """Determinism, asserted end to end rather than inferred from the guard."""
    assert serialize(build_surface()) == serialize(build_surface())


# --- 4. Narrowness: nothing else moved --------------------------------------


def test_no_plain_class_or_function_shape_moved(monkeypatch: Any) -> None:
    """The fix is narrow, proven against the whole tree rather than a sample.

    Every name whose shape differs from the pre-fix rendering must be either a
    Protocol defining ``__call__`` or a type alias. A plain class or function
    moving here would mean the change reached past its scope.
    """
    after = _flat(build_surface())
    before = _flat(_legacy_surface(monkeypatch))

    moved = sorted(
        name
        for name in set(before) & set(after)
        if before[name] != after[name]
    )
    assert moved, "the fix moved nothing — it is not wired into build_surface"

    unexpected = [
        name for name in moved if before[name]["shape"] != _INFORMATION_FREE
    ]
    assert not unexpected, (
        "these names moved but were not information-free before the fix, so"
        f" the change reached past its scope: {unexpected}"
    )


def test_every_moved_name_is_a_call_protocol_or_a_type_alias(
    monkeypatch: Any,
) -> None:
    """The scope of `D-IMPL-122`, asserted against the tree at run time."""
    import importlib
    import typing

    after = _flat(build_surface())
    before = _flat(_legacy_surface(monkeypatch))
    moved = sorted(
        name for name in set(before) & set(after) if before[name] != after[name]
    )

    misfits: list[str] = []
    for name in moved:
        module_name, attribute = name.rsplit(".", 1)
        obj = dump_surface._resolve_export(
            importlib.import_module(module_name), module_name, attribute
        )
        is_call_protocol = inspect.isclass(obj) and getattr(
            obj, "_is_protocol", False
        )
        is_alias = not inspect.isclass(obj) and typing.get_origin(obj) is not None
        if not (is_call_protocol or is_alias):
            misfits.append(name)
    assert not misfits, misfits


def test_no_committed_plain_class_or_function_shape_is_disturbed() -> None:
    """Regression over what is actually committed, not over a fixture.

    Every ``class``- and ``function``-kind entry in the committed manifest that
    is neither a Protocol nor a type alias must read the same after the fix.
    That is the audit claim in executable form: the shapes that moved moved
    because the tool can now see them, not because anything about them changed.

    ``contract``-kind entries are excluded, and the exclusion is narrow and
    named rather than blanket: the committed manifest is deliberately stale
    across plans `15.6-05` through `15.6-13`, which reshaped contract *fields*
    and left the regeneration to this plan. Those are genuine Track B moves
    with their own fragments, so a contract difference here is expected; a
    ``class`` or ``function`` difference would not be.
    """
    import importlib
    import typing

    committed = _flat(json.loads(_LIVE_MANIFEST.read_text(encoding="utf-8")))
    live = _flat(build_surface())

    checked = 0
    differing: list[str] = []
    for name, entry in sorted(committed.items()):
        if name not in live or entry["shape"] == _INFORMATION_FREE:
            continue
        if entry["kind"] not in ("class", "function"):
            continue
        module_name, attribute = name.rsplit(".", 1)
        try:
            obj = dump_surface._resolve_export(
                importlib.import_module(module_name), module_name, attribute
            )
        except ImportError:  # pragma: no cover - defensive
            continue
        if inspect.isclass(obj) and getattr(obj, "_is_protocol", False):
            continue
        if not inspect.isclass(obj) and typing.get_origin(obj) is not None:
            continue
        checked += 1
        if live[name]["shape"] != entry["shape"]:
            differing.append(name)

    assert checked >= 200, checked
    assert not differing, differing


# --- 5. The whole point: the diff can finally see it ------------------------


def test_diff_surfaces_now_reports_the_resolver_seams_as_reshaped(
    monkeypatch: Any,
) -> None:
    """`DI-15.5-06` closed for the twelve, in one assertion.

    Between a manifest built with the pre-fix shape logic and one built with
    the fix, both resolver Protocols appear under ``reshaped``. Before the fix
    this diff was empty for them — which is precisely how a three-to-five
    argument break shipped unrecorded.
    """
    after = build_surface()
    before = _legacy_surface(monkeypatch)
    difference = diff_surfaces(before, after)

    for seam in _RESOLVER_SEAMS:
        assert seam in difference["reshaped"], (seam, difference["reshaped"])
    assert not difference["added"] and not difference["removed"], difference


def test_report_mode_still_writes_nothing_and_exits_zero(
    capsys: Any,
) -> None:
    """``--report`` is what makes the tool safe to run before deciding."""
    digest_before = _LIVE_MANIFEST.read_bytes()
    assert dump_surface.main(["--report"]) == 0
    assert _LIVE_MANIFEST.read_bytes() == digest_before
    captured = capsys.readouterr().out
    for direction in ("added", "removed", "reshaped"):
        assert f"{direction} (" in captured
