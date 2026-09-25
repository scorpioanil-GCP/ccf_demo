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
        return {
            name: _LEGACY_ADDRESS.sub("", str(field.annotation))
            for name, field in sorted(fields.items())
        }
    if kind in ("class", "function"):
        try:
            return _LEGACY_ADDRESS.sub("", str(inspect.signature(obj)))
        except (TypeError, ValueError):
            return type(obj).__name__
    return type(obj).__name__


#: The legacy rendering carried each default's process-local address; it is
#: normalized here with a regex of this module's own — never the generator's —
#: so the comparison below is about shapes and not about addresses, and stays
#: independent of the code under test.
_LEGACY_ADDRESS = re.compile(r" at 0x[0-9a-fA-F]+")


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


def _manifest_shape_of(obj: Any) -> Any:
    """The shape the manifest would record, ``kind`` and all.

    **Every alias assertion routes through this, and none passes a hardcoded
    ``kind``.** They used to call ``_shape_of(alias, "function")`` directly,
    which meant `_kind_of` — the function that actually decides whether the
    alias branch is reached — was never exercised on an alias. That is exactly
    how a PEP-604 union stayed invisible: it is not ``callable``, so `_kind_of`
    calls it a ``constant``, and the alias branch guarded by
    ``kind in ("class", "function")`` never ran. Every assertion below passed
    while the shipped manifest recorded ``"UnionType"``.
    """
    return _shape_of(obj, dump_surface._kind_of(obj))


def test_type_aliases_record_their_type_rather_than_a_call_signature() -> None:
    """An alias is a type, and ``inspect.signature`` on one is meaningless.

    A ``Literal`` alias gaining or losing a member is a real surface change an
    adopter must act on; before the fix every one of them rendered
    ``(*args, **kwargs)`` and no such change produced a diff line.

    The PEP-604 case is the one the tests could not previously see, and it is
    parametrized here beside the callable forms rather than in a case of its
    own: the point is that the *same* function has to answer for both.
    """
    cases = {
        Literal["a", "b"]: "typing.Literal['a', 'b']",
        Union[int, str]: "typing.Union[int, str]",
        Mapping[str, str]: "collections.abc.Mapping[str, str]",
        int | None: "int | None",
        int | str | None: "int | str | None",
    }
    for alias, expected in cases.items():
        assert _manifest_shape_of(alias) == expected, alias

    callable_alias = _manifest_shape_of(Callable[[int], str])
    assert callable_alias == "collections.abc.Callable[[int], str]", callable_alias


def test_a_literal_alias_losing_a_member_moves_its_shape() -> None:
    """The property the alias half of the fix exists for."""
    before = _manifest_shape_of(Literal["a", "b"])
    after = _manifest_shape_of(Literal["a"])
    assert before != after


def test_a_pep604_union_alias_moves_when_it_is_widened() -> None:
    """The same property for the form `_kind_of` calls a ``constant``.

    Reproduced from the single-agent review, on the alias **this phase
    shipped**: `SourceRefreshRecency` recorded
    ``{"kind": "constant", "shape": "UnionType"}`` and widening it produced no
    diff line at all — a manifest blind spot introduced by `15.6-10`'s own fix,
    in a plan whose subject (`D-IMPL-122`/`123`) is manifest fidelity.
    """
    from ccf.halflife.assessment import SourceRefreshRecency, SourceRefreshWindow

    shipped = _manifest_shape_of(SourceRefreshRecency)
    assert shipped != _INFORMATION_FREE
    assert shipped != "UnionType", (
        "the alias branch is unreachable for a PEP-604 union again — the"
        " manifest is recording the type's name instead of the type"
    )
    assert "SourceRefreshWindow" in shipped, shipped

    widened = _manifest_shape_of(SourceRefreshWindow | str | None)
    assert widened != shipped, (
        "widening the union produced no shape movement, so the manifest would"
        " record no diff line for it"
    )


def test_the_shipped_literal_aliases_render_their_members() -> None:
    from ccf.operators.base import OperatorCategory
    from ccf.products.contract import TTLAnchor

    category = _manifest_shape_of(OperatorCategory)
    assert "traversal" in category and "similarity" in category, category
    anchor = _manifest_shape_of(TTLAnchor)
    assert "from_decision" in anchor, anchor


def test_no_shipped_alias_export_records_an_information_free_shape() -> None:
    """The whole-tree form of the claim, so a third alias form cannot hide.

    The two cases above name aliases; this one ranges over **every** export the
    manifest resolves to a type alias and asserts none of them records a bare
    type name (``UnionType``, ``_LiteralGenericAlias``) or the information-free
    signature. A future alias spelling that `_kind_of` classifies in some third
    way fails here rather than being found by a fourth reviewer.
    """
    import importlib

    offenders: list[str] = []
    for module_name, record in build_surface().items():
        module = importlib.import_module(module_name)
        for name, entry in record.get("exports", {}).items():
            obj = dump_surface._resolve_export(module, module_name, name)
            if not dump_surface._is_type_alias(obj):
                continue
            shape = entry["shape"]
            if shape in (_INFORMATION_FREE, type(obj).__name__):
                offenders.append(f"{module_name}.{name} -> {shape}")
    assert not offenders, offenders


def test_an_annotated_alias_renders_without_a_memory_address() -> None:
    """The determinism trap the alias fix walks into if it just calls ``str``.

    ``str(Annotated[X, AfterValidator(f)])`` embeds ``<function f at 0x...>``.
    Committed verbatim that would make the manifest differ between two runs on
    an unchanged tree, which is a worse defect than the blind spot being fixed.
    """
    from ccf.halflife.assessment import DebtEvidence

    shape = _manifest_shape_of(DebtEvidence)
    assert shape != _INFORMATION_FREE
    assert "0x" not in shape, shape
    assert "DebtEvidencePointer" in shape, shape


def test_the_serialized_manifest_carries_no_memory_addresses() -> None:
    """The determinism guard, applied to the whole manifest rather than a case."""
    emitted = serialize(build_surface())
    addresses = sorted(set(re.findall(r"0x[0-9a-fA-F]{6,}", emitted)))
    assert not addresses, addresses


def _clock() -> None:  # a function default: repr ``<function _clock at 0x…>``
    return None


class _Apostrophe:
    """A default whose repr carries an unpaired quote — the round-2 attack."""

    def __repr__(self) -> str:
        return "<Foo's>"


class _QuotedName:
    def __repr__(self) -> str:
        return "<Named name='at 0x7f00dead05' at 0x7f00dead06>"


class _Untokenizable:
    def __repr__(self) -> str:
        return "<Trunc it's at 0x7f00dead07>"


def test_a_function_default_renders_without_its_address() -> None:
    """Positive control for the determinism rendering: the parameter, its
    annotation and the default's name stay; only the address goes."""

    def served(*, clock: Callable[[], None] = _clock, key: Any = lambda v: v) -> None: ...

    shape = dump_surface._call_shape(served)
    assert "clock: 'Callable[[], None]' = <function _clock>" in shape, shape
    assert "<function test_a_function_default_renders_without_its_address.<locals>.<lambda>>" in shape, shape
    assert " at 0x" not in shape, shape


def test_a_literal_default_is_never_rewritten_whatever_its_neighbors_render_as() -> None:
    """The guarantee holds by TYPE, not by parsing: a ``str``/``bytes`` default
    is returned as is, so two neighboring reprs with stray quotes — the
    round-2 refutation of every whole-signature scrub — cannot pair up around
    it. Measured through ``inspect.signature`` on real objects, as the
    generator does."""

    def served(
        a: Any = _Apostrophe(),
        y: str = "seen at 0x7f00dead02",
        z: Any = _Apostrophe(),
        w: str = "<function f at 0x7f00dead03>",
        b: bytes = b"at 0x7f00dead04",
        clock: Callable[[], None] = _clock,
    ) -> None: ...

    shape = dump_surface._call_shape(served)
    assert "y: 'str' = 'seen at 0x7f00dead02'" in shape, shape
    assert "w: 'str' = '<function f at 0x7f00dead03>'" in shape, shape
    assert "b: 'bytes' = b'at 0x7f00dead04'" in shape, shape
    assert "a: 'Any' = <Foo's>, " in shape and "z: 'Any' = <Foo's>, " in shape, shape
    assert shape.endswith("clock: 'Callable[[], None]' = <function _clock>) -> 'None'"), shape


def test_a_default_whose_own_repr_quotes_an_address_keeps_the_quoted_one() -> None:
    """Within one value's repr the tokenizer, not a regex, decides what is
    quoted: the address in the quoted name stays, the repr's own goes."""

    def served(named: Any = _QuotedName()) -> None: ...

    assert "named: 'Any' = <Named name='at 0x7f00dead05'>" in dump_surface._call_shape(served)


def test_an_untokenizable_repr_is_left_alone_and_isolated_from_its_neighbors() -> None:
    """A repr that cannot be tokenized keeps its address (the manifest-wide
    no-address gate is what catches that, loudly) — and because rendering is
    per value, the neighboring function default is still scrubbed and the
    neighboring literal untouched."""

    def served(
        t: Any = _Untokenizable(), y: str = "seen at 0x7f00dead02", clock: Callable[[], None] = _clock
    ) -> None: ...

    shape = dump_surface._call_shape(served)
    assert "t: 'Any' = <Trunc it's at 0x7f00dead07>" in shape, shape
    assert "y: 'str' = 'seen at 0x7f00dead02'" in shape, shape
    assert "clock: 'Callable[[], None]' = <function _clock>" in shape, shape


def test_an_unvalidated_signature_still_renders() -> None:
    """A ``__signature__`` built with ``__validate_parameters__=False`` — a
    non-default parameter after a default — rendered under the previous
    generator; rebuilding it per value must not degrade it to a type name."""
    parameter = inspect.Parameter
    unvalidated = inspect.Signature(
        [parameter("a", parameter.POSITIONAL_OR_KEYWORD, default=1), parameter("b", parameter.POSITIONAL_OR_KEYWORD)],
        __validate_parameters__=False,
    )

    class Odd:
        __signature__ = unvalidated

    assert _shape_of(Odd, "class") == "(a=1, b)"


def test_an_alias_carrying_a_validator_renders_without_its_address() -> None:
    """The alias branch renders one alias alone, so a Pydantic validator's
    function loses its address and keeps its name — the shape the five
    ``Annotated`` aliases in the live manifest actually have."""
    from typing import Annotated

    from pydantic import AfterValidator

    def _check(value: str) -> str:
        return value

    alias = Annotated[str, AfterValidator(_check)]
    rendered = _shape_of(alias, dump_surface._kind_of(alias))
    assert isinstance(rendered, str) and "AfterValidator(func=<function " in rendered, rendered
    assert "._check>" in rendered and " at 0x" not in rendered, rendered


def test_the_manifest_is_byte_stable_across_two_builds() -> None:
    """Determinism, asserted end to end rather than inferred from the guard."""
    assert serialize(build_surface()) == serialize(build_surface())


# --- 4. Narrowness: nothing else moved --------------------------------------


def _is_a_bare_type_name(dotted: str, shape: Any) -> bool:
    """True if `shape` is just the export's own ``type(obj).__name__``.

    The second of the pre-fix tool's two uninformative renderings: a
    non-callable export fell through to its type's name, so a PEP-604 union
    recorded ``"UnionType"`` — a fact about Python, not about the surface.
    """
    import importlib

    module_name, attribute = dotted.rsplit(".", 1)
    obj = dump_surface._resolve_export(
        importlib.import_module(module_name), module_name, attribute
    )
    return shape == type(obj).__name__


def test_no_plain_class_or_function_shape_moved(monkeypatch: Any) -> None:
    """The fix is narrow, proven against the whole tree rather than a sample.

    Every name whose shape differs from the pre-fix rendering must be either a
    Protocol defining ``__call__`` or a type alias. A plain class or function
    moving here would mean the change reached past its scope.

    **Two uninformative renderings, not one.** The pre-fix tool rendered a
    callable it could not read as ``(*args, **kwargs)`` and a *non*-callable as
    its bare type name — ``"UnionType"`` for a PEP-604 union. Both are the
    absence of information about the shape, and the first version of this
    assertion admitted only the first, which is why the three unions the alias
    branch now reaches are named here rather than treated as scope creep. What
    the assertion still forbids is the thing it was written for: a name that
    carried a *real* shape before and carries a different one now.
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
        name
        for name in moved
        if before[name]["shape"] != _INFORMATION_FREE
        and not _is_a_bare_type_name(name, before[name]["shape"])
    ]
    assert not unexpected, (
        "these names moved but carried a real shape before the fix, so"
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


#: ``class``/``function``-kind entries whose shape legitimately moved *after*
#: this module was written, each mapped to the surface-change fragment that
#: records why.
#:
#: This is a **named** allowance, in the spirit of the ``contract``-kind
#: exclusion below rather than a widening of it, and it is not a dumping
#: ground: :func:`test_no_committed_plain_class_or_function_shape_is_disturbed`
#: requires each entry here to be claimed by name in the fragment it cites, so
#: an unexplained shape move still fails. The surface machinery's own gates
#: (``tests/test_surface_completeness.py``) independently require a matching
#: ``reshaped`` entry for the same name.
#:
#: Why it exists at all: this module's audit claim — *the shapes that moved
#: moved because the tool can now see them, not because anything about them
#: changed* — was written inside Phase 15.6, where no plan was permitted to
#: reshape a signature. `D-IMPL-96` (Dave, 2026-08-10) revoked that wording for
#: Phase 16 *"precisely so Phase 16 could repair defects it finds"*, and
#: `D-IMPL-126` item (3) is the first such repair to move a plain class's
#: ``__init__``. The claim is therefore amended in reach rather than withdrawn:
#: every *unlisted* shape must still read identically.
_SHAPE_MOVED_BY_FRAGMENT = {
    # `SEC-004` — governed record classes are not client-writable. Both stores
    # gain a `governed=NOTHING_GOVERNED` constructor keyword and a defaulted,
    # keyword-only `minted` on `put`: additive and behavior-preserving at every
    # existing call site, which is exactly the case this allowance was written
    # for. The fragment names both and says why the refusal is at the store
    # rather than at a door.
    "ccf.artifacts.file_store.FileArtifactStore": (
        "350-04-governed-record-classes-are-not-client-writable.md"
    ),
    "ccf.artifacts.mcp_store.McpArtifactStore": (
        "350-04-governed-record-classes-are-not-client-writable.md"
    ),
    # `PKG-F-08` — §7.10.4's Mode 2 footprint reaching replay dimension 3.
    # Five shapes, one parameter: `packaging_trace`. Additive and keyword-only
    # on all four helpers, so every existing call site reads identically at
    # the signature; REQUIRED on `GovernedResolver` alone, on the
    # `composite_children` precedent, because a default there made "this
    # deployment does no packaging" and "nobody wired the seam" the same
    # construction. The fragment names all five and says why.
    "ccf.products.product.OpenedProduct": (
        "20.4-01-mode-2-packaging-reaches-dimension-3.md"
    ),
    "ccf.products.product.open_product": (
        "20.4-01-mode-2-packaging-reaches-dimension-3.md"
    ),
    "ccf.products.resolver.GovernedResolver": (
        "20.4-01-mode-2-packaging-reaches-dimension-3.md"
    ),
    "ccf.products.resolver.build_governed_resolver": (
        "20.4-01-mode-2-packaging-reaches-dimension-3.md"
    ),
    "ccf.replay.record.build_replay_record": (
        "20.4-01-mode-2-packaging-reaches-dimension-3.md"
    ),
    # Phase 24.1.1 (D-58, D-IMPL-213, D-IMPL-214). Three additive,
    # keyword-only, defaulted widenings across the two Protocol-shaped seams —
    # exactly the case this allowance was written for. Every existing call site
    # reads identically at the signature, and each fragment claims its name as
    # `behavior`. Measured rather than asserted: 40 `build_replay_record` call
    # sites across 30 files and 11 `build_operator_registry` calls in
    # `tests/deployment/test_operator_builder.py` all compile and pass
    # unmodified.
    #
    # D-59 — `deployment_operators: Sequence[Operator] = ()`, so a deployment's
    # own operator reaches the registry the operator plan reads. Both entries
    # are the same function: the module and its package re-export.
    "ccf.deployment.operators.build_operator_registry": (
        "24.1.1-02-the-deployment-operator-reaches-the-plan.md"
    ),
    "ccf.deployment.build_operator_registry": (
        "24.1.1-02-the-deployment-operator-reaches-the-plan.md"
    ),
    # D-60 — the reference assembler gained `request_contract:
    # ProductRequestContract | None = None`, so it can RETURN a governed
    # refusal instead of only raising. With the field absent it is
    # byte-for-byte what it was. Both entries are the same class.
    "ccf.agents.assembler.DeterministicAssembler": (
        "24.1.1-03-a-refusal-returns-as-data.md"
    ),
    "ccf.agents.DeterministicAssembler": (
        "24.1.1-03-a-refusal-returns-as-data.md"
    ),
    # 24.7-04 (`D-IMPL-264` D-10, P-2) — `resolution` is a REQUIRED keyword:
    # `"EffectiveRequest | ResolutionNotApplicable"`, no default, beside the
    # other required inputs. The 24.1.1-04 entry this supersedes claimed an
    # additive widening (`assembly_refusal: str | None = None`, sentinel-
    # threaded, no call site moved); this move is the opposite kind — every
    # caller must now state the resolution that ran or a typed marker saying
    # why none applies, and omission is a `TypeError`. One name maps to one
    # fragment, and the citation is the NEWEST reshaping (the 24.5-13/15
    # precedent's reasoning, inverted: there the later change was the
    # additive one; here it is the breaking one). The 24.1.1-04 fragment
    # stays on disk untouched and still documents its own widening. The 41
    # SDK test sites are re-derived in plans 24.7-04 and 24.7-06; the seven
    # frozen example sites are quarantined evidence under `D-IMPL-263`/
    # `D-IMPL-261`, never migrated.
    "ccf.replay.record.build_replay_record": (
        "24.7-04-the-replay-builder-requires-an-explicit-resolution-state.md"
    ),
    "ccf_runtime.http_api.dependencies.ApiDependencies": (
        "16-22-consumption-papercuts.md"
    ),
    # D-IMPL-126 item (5): the egress builder gained two keyword-only
    # arguments, both defaulting closed, that register an opt-in
    # parameterised Tool beside the unchanged resource. A signature widened
    # by additive, defaulted parameters is exactly the case this allowance
    # was written for — every existing call site reads identically, and the
    # fragment claims the name as `reshaped`.
    "ccf_runtime.mcp.egress.build_egress_server": (
        "16-23-mcp-product-tool.md"
    ),
    # D-IMPL-128 limb 1: the experience builder gained two keyword-only
    # arguments, `entitled_product_class` and `lineage_tenant`, both
    # defaulting to `None` and both required conditionally on exposure. The
    # same additive-and-defaulted case as its egress sibling above — every
    # existing call site reads identically at the signature — with the
    # difference that a deployment exposing either gated consumption tool now
    # has to supply the declared address the entitlement decides against, and
    # the fragment says so under Adopter migration. It claims the name as
    # `reshaped`.
    "ccf_runtime.mcp.experience.build_experience_server": (
        "16-24-experience-door-entitlement.md"
    ),
    # D-IMPL-135: `ProductDiscovery` gained a fourth axis, `audiences`,
    # defaulted and additive. `ProductDiscovery` is itself a `contract`-kind
    # export, so its own shape move is invisible to this check (the loop
    # above skips every entry whose kind is not `class` or `function`) — but
    # `register_product_class`'s keyword-only `discovery` parameter defaults
    # to `NOT_DISCOVERABLE`, and this function's captured shape is
    # `str(inspect.signature(obj))`, which renders a default argument's own
    # `repr()` inline. The axis's move therefore surfaces transitively, here,
    # on the one function whose default carries the sentinel — every
    # existing call site that does not pass `discovery=` still receives the
    # same value, unchanged; only the sentinel's printed representation grew
    # a field. Measured rather than assumed (`D-IMPL-138`(c)): `pytest -k
    # surface` was the arbiter, and it caught the move here, not on
    # `ProductDiscovery`.
    "ccf.products.contract.register_product_class": (
        "16-27-discovery-audiences.md"
    ),
    # `D-IMPL-141` (RESOLVED, Dave, 2026-08-16). `BindingDocument` went from
    # four fields — three of them `<module>:<attribute>` reference strings — to
    # the data the SDK builds a resolver from plus **one** reference, `plan:`.
    # This is not an additive widening like its neighbours above and the entry
    # does not pretend otherwise: fields were removed, and every consumer of
    # `document.resolver` or `document.question` had to change. It is listed
    # here because the shape genuinely moved and the fragment records why, in
    # full, under `reshaped` — the allowance's contract is *claimed by name in
    # the fragment it cites*, not *changed only additively*.
    "ccf.client.adapters.binding_document.BindingDocument": (
        "17-12-binding-document-data-only.md"
    ),
    # `D-IMPL-148` Addendum A (Dave, 2026-08-17): the one canonical-body
    # renderer gained a single keyword-only `replay_ref`, defaulting to `None`,
    # which publishes `REPLAY_REF_HEADER` when supplied and sets no header when
    # not. The additive-and-defaulted case this allowance was written for — all
    # five existing call sites read identically and the response is
    # byte-for-byte unchanged when the argument is omitted — and the fragment
    # claims the name as `reshaped`.
    "ccf_runtime.http_api.routes.canonical_response": (
        "17-10-both-doors-carry-the-replay-reference.md"
    ),
    # `C-05` (Phase 19, plan `19-02`). `decode_outcome`'s return went from
    # `WireOutcome` to the `DecodedOutcome` pair, so a caller reads the outcome
    # off `.outcome` and the vessel off `.vessel`. Not an additive widening —
    # the return type changed and every call site that read a field off it had
    # to move — and the entry does not pretend otherwise. It is listed here
    # because the shape genuinely moved and the fragment records why, in full,
    # under `reshaped`: with `C-05` putting this function on the shipped path,
    # a `ProductClient` that received only the outcome would have to re-parse
    # `product_json` to get the vessel `Result` requires, which is a second
    # contract validation on a second decode path — the defect `D-12` exists to
    # prevent. The allowance's contract is *claimed by name in the fragment it
    # cites*, not *changed only additively*.
    "ccf.client.codec.decode_outcome": (
        "19-02-the-adapter-seam-carries-bytes.md"
    ),
    # Phase 24.5 plan 13 (D-IMPL-237, ledger rows 24.5-L-14 / L-26). Both gate
    # runners gained `product_class: RegisteredProductClass` so the ONE
    # declared-obligations gate can read the class's declared ceiling and
    # lineage obligation. A required positional, not a defaulted widening —
    # the fragment records it under `reshaped` and names every call site the
    # resolver threads it through; the two runners are the same move.
    # Plan 15 (D-IMPL-238 second sentence, ledger row 24.5-L-24) widened the
    # same two runners AGAIN — `empty_results: frozenset[str] | None = None`,
    # a defaulted, keyword-only widening — and its fragment
    # `24.5-15-the-empty-operator-gate-s-two-halves-by-name.md` claims both
    # names as `reshaped` too. One name maps to one fragment here; plan 13's
    # stays as the citation because it records the required positional, and
    # the allowance's contract (the fragment exists and claims the name) holds
    # under either.
    "ccf.products.gates.run_gates": (
        "24.5-13-one-structural-gate-for-declared-obligations.md"
    ),
    "ccf.products.gates.run_federated_gates": (
        "24.5-13-one-structural-gate-for-declared-obligations.md"
    ),
    # Phase 24.5 plan 15 (ledger row 24.5-L-24). `ExecutionResult` gained
    # `empty_results: frozenset[str] = frozenset()` as its last field — the
    # engine's own record of which operators returned an empty set, computed
    # always, so the returned-empty half of the empty-operator gate has an
    # observation to read that is not the payload. A defaulted widening: every
    # hand-built result carries the empty set and reads as it did.
    "ccf.projection.engine.ExecutionResult": (
        "24.5-15-the-empty-operator-gate-s-two-halves-by-name.md"
    ),
    # Phase 24.7 plan 02 (`D-IMPL-264` D-08; criterion 12). The seam's return
    # went from the four-way union `EffectiveRequest | ConstraintRefusal |
    # PolicyResolutionConflict | ProductRequestViolation` to the one
    # `ResolutionOutcome` pair, so a caller reads the refusal off `.refusal`
    # and the evidence off `.evidence` — and a refusal reached halfway through
    # now carries what resolution established before it. Not an additive
    # widening: the return type changed and every call site that branched on
    # the union had to move — the SDK's one, in `GovernedResolver.resolve`,
    # did; cp-04's frozen `assembler.py` `isinstance` over the retired union
    # is accepted evidence under `D-IMPL-264` am.1 (Dave: *"Do not distort
    # the new SDK return type to preserve an old example `isinstance`
    # check"*), never a reason to keep the union. The entry does not pretend
    # otherwise: the fragment claims the name as `reshaped`. The two `resolve`
    # methods moved with it and are invisible here — `PolicyConstraintResolver`
    # is a Protocol and the loop skips it, and `ReferencePolicyConstraintResolver`'s
    # captured shape is its dataclass `__init__`, which did not change.
    "ccf.products.constraints.resolve_effective_request": (
        "24.7-02-resolution-returns-a-paired-outcome.md"
    ),
    # Phase 24.11 row 3 (`24.10-F-08`, obligation limb; `D-IMPL-117`).
    # `GovernedResolver` gained `debt_profile_key: str | None` as its FIFTH
    # manifest key, so the candidate can ask the deployment's own profile what
    # it binds to the state the assessment landed in. A required argument, not
    # a defaulted widening — this class is the defaultless composition and the
    # fragment records it under `reshaped`, naming both construction sites that
    # moved. `build_governed_resolver` is not listed here because its signature
    # did not move: only the mutual-exclusion rule narrowed, which the same
    # fragment claims under `behavior`.
    "ccf.products.resolver.GovernedResolver": (
        "24.11-03-the-resolver-carries-the-declared-obligation.md"
    ),
    # `D-IMPL-353` (the join, 2026-09-24) — the handles and the composition
    # roots take the capability for their own action. Each constructor gains a
    # keyword-only `authorized: Authorized[<Kind>]` (or, for `boot`, the
    # `tenant_ids` the fabric composes for) and the fragment named here claims
    # the name `reshaped` and says what the capability replaces.
    "ccf.boot.boot": (
        "353-07-the-composition-roots-mint-for-their-own-writes.md"
    ),
    "ccf.peering.admission.PeeringAdmissionGate": (
        "353-07-the-composition-roots-mint-for-their-own-writes.md"
    ),
    "ccf.products.child_resolver.QuestionBoundChildResolver": (
        "353-07-the-composition-roots-mint-for-their-own-writes.md"
    ),
    "ccf.products.resolver.ReplayRefusalRecorder": (
        "353-07-the-composition-roots-mint-for-their-own-writes.md"
    ),
    "ccf.replay.serve.ReplayWriter": (
        "353-03-the-handles-require-the-capability-for-their-own-action.md"
    ),
    "ccf.replay.serve.QueryPinWriter": (
        "353-09-the-join.md"
    ),
    # `D-IMPL-353` (the join, after its panel, 2026-09-25) — the register loop
    # takes the composition's tenant explicitly (codex HIGH): `tenant=` is a new
    # required keyword on the function and on its package re-export.
    "ccf.deployment.manifest.register_manifest_entries": (
        "353-09-the-join.md"
    ),
    "ccf.deployment.register_manifest_entries": (
        "353-09-the-join.md"
    ),
}


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

    **Entries in :data:`_SHAPE_MOVED_BY_FRAGMENT` are excluded too**, and each
    must earn it: the fragment it names must exist and must claim the name. See
    that constant for why the original claim needed amending in Phase 16 and
    for what it still asserts about every other entry.
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

    # The named allowance, and the price of being on it: the fragment cited
    # must exist and must claim the name. An entry added here without a
    # fragment fails, which is what keeps this from becoming a mute list.
    fragments = _REPO_ROOT / "docs" / "surface-changes"
    for allowed, fragment in _SHAPE_MOVED_BY_FRAGMENT.items():
        path = fragments / fragment
        assert path.is_file(), path
        assert allowed in path.read_text(encoding="utf-8"), (allowed, fragment)

    assert not [
        name for name in differing if name not in _SHAPE_MOVED_BY_FRAGMENT
    ], differing


# --- 5. An export whose value is None is not a resolution failure ----------


def test_an_export_valued_none_is_distinguishable_from_an_unresolved_one() -> None:
    """The collision this plan's regeneration exposed, closed in both directions.

    ``_resolve_export`` used to return ``None`` for a name it could not resolve,
    which was exact only while no export's *value* was ``None``. Plan `15.6-07`
    ended that: ``NO_SOURCE_REFRESH_RECENCY`` is a legitimate
    ``Final[SourceRefreshWindow | None] = None`` sentinel that resolved
    perfectly well and recorded the same ``"NoneType"`` shape a failure did — so
    ``tests/test_surface_drift.py::test_no_export_resolves_to_nothing`` reported
    a real export as a failure. It now returns its own marker, which ``None``
    can never be mistaken for.
    """
    import ccf.halflife.assessment as assessment

    resolved = dump_surface._resolve_export(
        assessment, "ccf.halflife.assessment", "NO_SOURCE_REFRESH_RECENCY"
    )
    assert resolved is None
    assert resolved is not dump_surface.UNRESOLVED
    assert dump_surface._kind_of(resolved) == "constant"

    missing = dump_surface._resolve_export(
        assessment, "ccf.halflife.assessment", "no_such_name_exists"
    )
    assert missing is dump_surface.UNRESOLVED
    assert dump_surface._kind_of(missing) == "unresolved"
    assert dump_surface._shape_of(missing, "unresolved") == "unresolved"


def test_the_manifest_records_the_none_sentinel_rather_than_a_failure() -> None:
    """Asserted against the real export, not only against the resolver."""
    live = _flat(build_surface())
    entry = live["ccf.halflife.assessment.NO_SOURCE_REFRESH_RECENCY"]
    assert entry["kind"] == "constant", entry
    assert entry["shape"] != "unresolved", entry

    unresolved = sorted(
        name
        for name, record in live.items()
        if record["kind"] == "unresolved" or record["shape"] == "unresolved"
    )
    assert not unresolved, unresolved


# --- 6. The whole point: the diff can finally see it ------------------------


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
