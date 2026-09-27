"""`D-IMPL-347` A2 — every deployment seam holds a governed refusal as data.

Ruled by Dave, 2026-09-23. `D-IMPL-304` opened this for ``acquisition`` alone,
and the narrow scope was itself the defect: `CLD-F-06` measured the RIGHT
exception raised from the WRONG seam escaping as a traceback, and cp-20 worked
around it by moving an envelope check into ``acquire``.

**The two axes this closes are separate, and only one of them is A2.** A2 is
SCOPE — the same typed handoff, now honored at all four deployment-supplied
seams. It is deliberately NOT type-widening: a domain exception still
propagates, because the SDK cannot know that a deployment's own error means
*refuse* rather than *broken*. Declaring that is B2's map, and it is a governed
value the product class states (Dave: *"Product class first; deployment may
narrow, not widen"*), not something invented here.

**Each seam is wrapped individually and never the whole resolve.** A blanket
``try`` would convert a ``GovernedRefusalRaised`` escaping from deep inside the
SDK into a plausible-looking governed "no" — an SDK defect wearing a refusal's
clothes. The four are exactly the callables the deployment supplies, which is
the whole reason their refusals are data rather than defects.
"""

from __future__ import annotations

import pathlib
import types
from datetime import UTC, datetime
from typing import Any

import pytest

from ccf.products.refusal import (
    RESOLVED_BY_THE_RESOLVER,
    GovernedRefusalRaised,
    RefusalEnvelope,
    SubjectUnavailableRefusal,
)
from ccf.replay.record import NO_REFUSAL_SEAM, REFUSAL_SEAMS
from tests.products.test_paved_road import (  # noqa: F401 — `tree` is a fixture
    _config,
    _open,
    _question,
    _write_tree,
    tree,
)


def _refusal() -> SubjectUnavailableRefusal:
    return SubjectUnavailableRefusal(
        cause="unauthorized", detail="held at a seam", error_code="seam-held"
    )


def _raised() -> GovernedRefusalRaised:
    return GovernedRefusalRaised(_refusal(), resolution=RESOLVED_BY_THE_RESOLVER)


def _seam_of(opened: Any, outcome: RefusalEnvelope) -> str:
    """The seam dimension 5 recorded, read off the record rather than asserted."""
    record = opened.record_of(outcome)
    return str(record.content_generation_path.refusal_seam)


# --------------------------------------------------------------------------
# The vocabulary is closed, and closed deliberately.
# --------------------------------------------------------------------------


def test_the_seam_vocabulary_is_exactly_the_four_deployment_supplied_callables() -> None:
    """A fifth name would mean a fifth seam, which is a design change.

    Pinned as a ROSTER rather than a count, because a right count with a wrong
    member audits clean forever.
    """
    assert REFUSAL_SEAMS == frozenset(
        {"acquisition", "build_children", "plan_factory", "product_gate"}
    )
    assert NO_REFUSAL_SEAM not in REFUSAL_SEAMS


# --------------------------------------------------------------------------
# `plan_factory` — the seam, and its positive control.
# --------------------------------------------------------------------------


def test_a_refusal_raised_by_the_plan_factory_is_data_and_names_its_seam(
    tree: tuple[pathlib.Path, pathlib.Path],
) -> None:
    """Before A2 this was a traceback through ``opened.answer``."""
    root, scratch = tree

    def _refusing_project(**_: Any) -> Any:
        raise _raised()

    with _open(root, scratch, project=_refusing_project) as opened:
        outcome = opened.answer(_question(opened))
        assert isinstance(outcome, RefusalEnvelope), outcome
        assert _seam_of(opened, outcome) == "plan_factory"


def test_a_plan_factory_raising_a_domain_error_still_propagates(
    tree: tuple[pathlib.Path, pathlib.Path],
) -> None:
    """THE POSITIVE CONTROL, and without it the test above proves nothing.

    A wrap that swallowed everything would pass the test above and destroy the
    distinction between a governed "no" and a broken deployment. A2 is scope,
    never type: only ``GovernedRefusalRaised`` converts.
    """
    root, scratch = tree

    def _broken_project(**_: Any) -> Any:
        raise LookupError("a defect, not a determination")

    with _open(root, scratch, project=_broken_project) as opened:
        with pytest.raises(LookupError, match="a defect, not a determination"):
            opened.answer(_question(opened))


# --------------------------------------------------------------------------
# `product_gate` — a gate that RAISES, distinct from one that RETURNS.
# --------------------------------------------------------------------------


def test_a_refusal_raised_by_the_product_gate_is_data_and_names_its_seam(
    tmp_path: pathlib.Path,
) -> None:
    """A gate that RETURNS a violation already refused through its own branch;
    this is the gate that RAISES, which was previously a traceback.

    Its own tree, because a supplied ``gate=`` and a declared
    ``declared_product_gate`` are both-or-neither: the SDK refuses to stamp an
    identity on a refusal produced by a gate the class never declared.
    """
    config = _config()
    config["product_class"]["declared_product_gate"] = {
        "gate_id": "fixture.gate",
        "gate_version": "1.0.0",
    }
    root = _write_tree(tmp_path / "gate", config=config)
    scratch = tmp_path / "gate" / "scratch"

    def _refusing_gate(*, candidate: Any, evidence: Any = None) -> str:
        raise _raised()

    with _open(root, scratch, gate=_refusing_gate) as opened:
        outcome = opened.answer(_question(opened))
        assert isinstance(outcome, RefusalEnvelope), outcome
        assert _seam_of(opened, outcome) == "product_gate"


# --------------------------------------------------------------------------
# The resolver's OWN refusals are not seam-held, and say so positively.
# --------------------------------------------------------------------------


def test_the_acquisition_seam_still_names_itself_after_the_widening(
    tree: tuple[pathlib.Path, pathlib.Path],
) -> None:
    """`D-IMPL-304`'s original seam, unchanged by A2 and now SAYING which it was.

    Before the widening this was the only seam that converted, so nothing had
    to name it. It names itself now, which is what makes the other three
    distinguishable from it in a record.
    """
    root, scratch = tree

    def _raising_acquire(context: Any) -> Any:
        raise _raised()

    with _open(root, scratch, acquire=_raising_acquire) as opened:
        held = opened.answer(_question(opened))
        assert isinstance(held, RefusalEnvelope), held
        assert _seam_of(opened, held) == "acquisition"


# --------------------------------------------------------------------------
# `build_children` — the seam `CLD-F-06` measured, and the ruling that shapes it.
# --------------------------------------------------------------------------


def test_a_refusal_raised_by_the_child_factory_refuses_the_COMPOSITE(
    tmp_path: pathlib.Path,
) -> None:
    """`CLD-F-06`, closed — and closed as a COMPOSITE refusal, by ruling.

    Dave, 2026-09-23: *"build_children= raising GovernedRefusalRaised
    (envelope / policy / 'do not dispatch') is a composite refusal. There is no
    child outcome to attach it to."* A refusal raised IN the factory is not the
    same thing as a child door returning one — that arrives as an outcome row
    where the slot rules decide (`D-IMPL-336` F1) — and conflating them is the
    mix-up cp-20's workaround was avoiding.

    The evidence that the two paths stay distinct: the refusal is recorded
    against the ``build_children`` seam, which is a fact about the COMPOSITE's
    own assembly, and no child resolution row is minted for it.
    """
    config = _config()
    config["product_class"]["requires"] = [
        {"product_class": "fixture.child", "required": True, "compatible_from": "1.0.0"}
    ]
    root = _write_tree(tmp_path / "composite", config=config)
    scratch = tmp_path / "composite" / "scratch"

    # `build_children=` names TWO things and only one of them can hold a
    # per-question refusal. The FACTORY runs once at open and returns a child
    # resolver; raising there is a boot failure, not a determination. The
    # per-question seam is the RESOLVER it returns, which is what the resolver
    # calls with the request in hand — and what cp-20's envelope check needed.
    class _RefusingResolver:
        def __call__(self, **_: Any) -> Any:
            raise _raised()

    def _factory(_context: Any) -> Any:
        return _RefusingResolver()

    with _open(root, scratch, build_children=_factory) as opened:
        outcome = opened.answer(_question(opened))
        assert isinstance(outcome, RefusalEnvelope), outcome
        assert _seam_of(opened, outcome) == "build_children"
        record = opened.record_of(outcome)
        assert record.content_generation_path.child_resolutions == (), (
            "a refusal raised IN the factory produced a child row; it is a"
            " composite refusal and has no child outcome to attach to"
        )


# --------------------------------------------------------------------------
# B2 — the declared map. Product class first; deployment may narrow, not widen.
# --------------------------------------------------------------------------


class _ControlRoomUnreachable(RuntimeError):
    """A deployment's own domain error, standing in for `CP17-F-11`'s."""


def _class_declaring_the_domain_error() -> dict[str, Any]:
    config = _config()
    config["product_class"]["seam_refusals"] = [
        {
            "exception": f"{__name__}._ControlRoomUnreachable",
            "cause": "unauthorized",
            "error_code": "control-room-unreachable",
        }
    ]
    return config


def test_a_declared_domain_exception_becomes_a_governed_refusal(
    tmp_path: pathlib.Path,
) -> None:
    """`CP17-F-11` / `CP13C-F-03` / `CP14-F-21`, closed BY DECLARATION.

    The product says what its own failure means; the SDK mints the refusal it
    was told to and carries the exception's own message as the detail, unedited.
    """
    root = _write_tree(tmp_path / "b2", config=_class_declaring_the_domain_error())
    scratch = tmp_path / "b2" / "scratch"

    def _unreachable(**_: Any) -> Any:
        raise _ControlRoomUnreachable("the control room did not answer")

    with _open(root, scratch, project=_unreachable) as opened:
        outcome = opened.answer(_question(opened))
        assert isinstance(outcome, RefusalEnvelope), outcome
        assert _seam_of(opened, outcome) == "plan_factory"
        # The SERVED shell is the minimal disclosure — the detail is
        # deliberately not disclosed to the caller. The declared code and the
        # exception's own message are in the RECORD, which is where an
        # examiner reads them.
        block = str(opened.record_of(outcome).content_generation_path.assembly_refusal)
        assert "control-room-unreachable" in block, block


def test_an_UNdeclared_domain_exception_still_propagates(
    tmp_path: pathlib.Path,
) -> None:
    """THE CONTROL that keeps B2 from being a blanket catch.

    Same tree, same seam, same shape of failure — a type the class did NOT
    name. It re-raises, which is what keeps a defect a defect.
    """
    root = _write_tree(tmp_path / "b2u", config=_class_declaring_the_domain_error())
    scratch = tmp_path / "b2u" / "scratch"

    def _other(**_: Any) -> Any:
        raise TimeoutError("undeclared, therefore a defect")

    with _open(root, scratch, project=_other) as opened:
        with pytest.raises(TimeoutError, match="undeclared, therefore a defect"):
            opened.answer(_question(opened))


def test_a_subclass_of_a_declared_type_is_NOT_converted(
    tmp_path: pathlib.Path,
) -> None:
    """Exact type, never a subclass walk.

    A subclass is a different failure the product has not spoken about, and
    inheriting a parent's cause is how a narrow declaration silently becomes a
    wide one. The declaration is the whole authority.
    """

    class _Narrower(_ControlRoomUnreachable):
        pass

    root = _write_tree(tmp_path / "b2s", config=_class_declaring_the_domain_error())
    scratch = tmp_path / "b2s" / "scratch"

    def _subclassed(**_: Any) -> Any:
        raise _Narrower("a subclass nobody declared")

    with _open(root, scratch, project=_subclassed) as opened:
        with pytest.raises(_ControlRoomUnreachable, match="a subclass nobody declared"):
            opened.answer(_question(opened))


def test_a_deployment_may_narrow_the_class_map_but_never_widen_it() -> None:
    """Dave: *"Deployment may subset or bind codes already named by the class."*

    Refused by NAME rather than silently intersected: an ignored widening and
    an honored narrowing are the same green build, and the operator who wrote
    the extra name would never learn it did nothing.
    """
    from ccf.controlplane.artifacts import ProductClassDeclaration, SeamRefusalBinding
    from ccf.deployment import SeamRefusalWidening, refuse_seam_refusal_widening

    declared = ProductClassDeclaration.model_construct(
        seam_refusals=(
            SeamRefusalBinding(
                exception="pkg.Known", cause="nonexistent", error_code="known"
            ),
        )
    )
    # narrowing to nothing, and to the declared member, are both accepted
    refuse_seam_refusal_widening(declared=declared, deployment_exceptions=frozenset())
    refuse_seam_refusal_widening(
        declared=declared, deployment_exceptions=frozenset({"pkg.Known"})
    )
    with pytest.raises(SeamRefusalWidening, match="pkg.Invented"):
        refuse_seam_refusal_widening(
            declared=declared,
            deployment_exceptions=frozenset({"pkg.Known", "pkg.Invented"}),
        )


# --------------------------------------------------------------------------
# `D-IMPL-357` B3 — the SDK's OWN seam class converts by mechanism.
#
# B2 above is the deployment half: a domain exception is a governed refusal
# only where the product class declared what it MEANS, because the SDK cannot
# know. That reasoning does not reach the SDK's own exceptions — it knows
# exactly what `IdentityRefused` means, because it raises it — and before this
# amendment nothing declared a binding for it, so the SDK's own refusal escaped
# the paved road as an untyped error with no record.
# --------------------------------------------------------------------------

from ccf.assembly.worker import IdentityRefused


def test_the_sdks_own_identity_refusal_is_a_governed_refusal_without_a_declaration(
    tmp_path: pathlib.Path,
) -> None:
    """D-IMPL-357 B3 — amends D-IMPL-347 B2 for SDK-raised seam classes only:
    the SDK knows what its own IdentityRefused means (a record naming no
    entity), so the paved road converts it under cause `nonexistent` even
    though no product class declares it. Before: an HTTP 500 with no record."""
    root = _write_tree(tmp_path / "b3", config=_config())   # declares NO seam_refusals
    scratch = tmp_path / "b3" / "scratch"

    def _null_identity(**_: Any) -> Any:
        raise IdentityRefused(
            envelope_id="env-null", entity_class="company", key="lei", field="lei", reason="null"
        )

    with _open(root, scratch, project=_null_identity) as opened:
        outcome = opened.answer(_question(opened))
        assert isinstance(outcome, RefusalEnvelope), outcome
        block = str(opened.record_of(outcome).content_generation_path.assembly_refusal)
        assert "identity-refused" in block and "nonexistent" in block


def test_a_deployment_cannot_widen_the_sdk_seam_map_and_its_own_undeclared_types_still_propagate(
    tmp_path: pathlib.Path,
) -> None:
    """The control that keeps the amendment narrow: only the SDK's own class
    converts by mechanism; `test_an_UNdeclared_domain_exception_still_propagates`
    above keeps proving the deployment half."""
    from ccf.products.resolver import SDK_SEAM_REFUSALS

    assert set(SDK_SEAM_REFUSALS) == {"ccf.assembly.worker.IdentityRefused"}


def test_the_sdk_seam_map_refuses_a_TYPED_WRITE_and_claims_nothing_wider() -> None:
    """THE TYPED WRITE, and nothing wider than that.

    What this proves, exactly: ``SDK_SEAM_REFUSALS[...] = ...`` raises and
    ``.clear()`` does not exist, so accidental and typed mutation cannot happen
    and the roster assertion above is a statement about the shipped map rather
    than about whatever the last importer left behind.

    What it does NOT prove — and what an earlier version of this docstring
    wrongly claimed it did — is that a deployment cannot reach in and widen the
    map. It can, two ways: rebinding the module attribute, and writing through
    the dictionary this proxy wraps. No in-process mechanism can stop either,
    because in-process code is already inside the trust boundary and the seam
    callable can obtain the same conversion by importing ``IdentityRefused`` and
    raising it. The constant's own comment says so plainly. This is a hygiene
    control, not a boundary proof.
    """
    from ccf.controlplane.artifacts import SeamRefusalBinding
    from ccf.products.resolver import SDK_SEAM_REFUSALS

    before = dict(SDK_SEAM_REFUSALS)
    with pytest.raises(TypeError):
        SDK_SEAM_REFUSALS["deployment.pkg.ControlRoomUnreachable"] = (  # type: ignore[index]
            SeamRefusalBinding(
                exception="deployment.pkg.ControlRoomUnreachable",
                cause="unauthorized",
                error_code="smuggled-in",
            )
        )
    with pytest.raises((TypeError, AttributeError)):
        SDK_SEAM_REFUSALS.clear()  # type: ignore[attr-defined]
    assert dict(SDK_SEAM_REFUSALS) == before


def test_an_sdk_seam_binding_cannot_be_RETARGETED_IN_PLACE() -> None:
    """The mechanism the map's docstring did not claim, and the one that holds.

    The proxy stops a typed write and nothing stops an in-process referent
    write, so what is left is whether an entry that IS in the map can be
    quietly made to mean something else. It cannot: a
    :class:`~ccf.controlplane.artifacts.SeamRefusalBinding` is a frozen
    ``CCFContract``, so assigning to ``cause`` or ``error_code`` raises. Code
    that reaches the referent has to REPLACE a whole entry rather than retarget
    an existing SDK-owned name, which is a louder edit and a different shape in
    a diff.

    Pinned because an unclaimed real defense is worth more than three claimed
    ones, and because nothing else in this module would redden if the contract
    base were unfrozen.
    """
    from pydantic import ValidationError

    from ccf.products.resolver import SDK_SEAM_REFUSALS

    binding = SDK_SEAM_REFUSALS["ccf.assembly.worker.IdentityRefused"]
    for field, value in (("cause", "unauthorized"), ("error_code", "borrowed")):
        with pytest.raises(ValidationError):
            setattr(binding, field, value)
    assert (binding.cause, binding.error_code) == ("nonexistent", "identity-refused")


def test_rebinding_the_module_attribute_does_NOT_change_dispatch(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The lookup binds the map at DEFINITION time, so a rebind is inert.

    The one widening route a module global has, closed because it was free:
    ``_declared_seam_refusal`` captures the mapping in a private default
    argument instead of reading ``resolver.SDK_SEAM_REFUSALS`` each call.

    The control substitutes a WIDER map — the SDK's entry plus a deployment's
    own exception — and raises that deployment exception at a seam under a class
    that declares no ``seam_refusals``. Before the binding change this converted
    into a governed refusal carrying the smuggled cause; now it propagates as
    the defect it is. The assertion is on DISPATCH, never on the attribute: a
    test that only read the rebound global back would pass under both versions.
    """
    import ccf.products.resolver as resolver_module
    from ccf.controlplane.artifacts import SeamRefusalBinding

    smuggled = f"{__name__}._ControlRoomUnreachable"
    monkeypatch.setattr(
        resolver_module,
        "SDK_SEAM_REFUSALS",
        dict(resolver_module.SDK_SEAM_REFUSALS)
        | {
            smuggled: SeamRefusalBinding(
                exception=smuggled, cause="unauthorized", error_code="smuggled-in"
            )
        },
    )
    assert smuggled in resolver_module.SDK_SEAM_REFUSALS, "the rebind itself must land"

    root = _write_tree(tmp_path / "b3rebind", config=_config())  # declares NO seam_refusals
    scratch = tmp_path / "b3rebind" / "scratch"

    def _unreachable(**_: Any) -> Any:
        raise _ControlRoomUnreachable("a rebind must not buy this a governed 'no'")

    with _open(root, scratch, project=_unreachable) as opened:
        with pytest.raises(_ControlRoomUnreachable, match="must not buy this"):
            opened.answer(_question(opened))


def test_every_sdk_seam_map_entry_names_a_REAL_exception_the_SDK_ITSELF_defines() -> None:
    """What makes the map the SDK's own, checked rather than asserted.

    The SDK matches these types by name and never imports them (`D-IMPL-347`
    B2), so a string here could name anything at all — including a type the SDK
    does not define, which is exactly the widening this amendment must not
    permit. The TEST may import, so the test resolves each key and proves three
    things a name alone cannot: the module is inside the ``ccf`` package, the
    attribute exists, and it is an exception class. Each binding's own
    ``exception`` field must equal the key, because two spellings of one type is
    how a map comes to have an entry nothing can ever match.
    """
    import importlib

    from ccf.products.resolver import SDK_SEAM_REFUSALS

    assert SDK_SEAM_REFUSALS, "an empty mechanism map would pass every other check here"
    for name, binding in SDK_SEAM_REFUSALS.items():
        assert binding.exception == name, (name, binding.exception)
        module_name, _, qualname = name.rpartition(".")
        assert module_name.split(".")[0] == "ccf", name
        resolved = getattr(importlib.import_module(module_name), qualname)
        assert isinstance(resolved, type) and issubclass(resolved, BaseException), name
        assert f"{resolved.__module__}.{resolved.__qualname__}" == name, name


def test_a_class_declaring_an_SDK_OWNED_seam_type_is_REFUSED_at_registration(
    tmp_path: pathlib.Path,
) -> None:
    """A control that can never fire is refused, not ignored.

    This is the same config the SDK-wins control below exercises below the door:
    a class restating ``IdentityRefused`` as ``unauthorized`` /
    ``borrowed-authority``, which would turn "this record names no entity" into
    "you may not see it". The SDK consults its own map first, so the declaration
    could never be minted — and this project's own doctrine, written one
    function away for the deployment-narrowing case, is that *an ignored
    widening and an honored narrowing are the same green build, and the operator
    who wrote the extra name would never learn it did nothing*.

    It matters because the class declaration is **control evidence**: reviewed,
    versioned, content-hashed, shown to an examiner. A deployed behavior that
    disagrees with its own approved control document, with nothing in the record
    admitting it, is worse than a refusal.

    **At registration, never at the seam.** The refusal arrives with no question
    in flight and names both sides; refusing when the exception was actually
    raised would turn a governance mistake into exactly the untyped
    in-front-of-a-caller failure B3 exists to remove. The message names the
    SDK-owned key, the SDK's binding, and the remedy.
    """
    from ccf.products.contract import ProductClassRegistrationError

    config = _config()
    config["product_class"]["seam_refusals"] = [
        {
            "exception": "ccf.assembly.worker.IdentityRefused",
            "cause": "unauthorized",
            "error_code": "borrowed-authority",
        }
    ]
    root = _write_tree(tmp_path / "b3w", config=config)
    scratch = tmp_path / "b3w" / "scratch"

    def _null_identity(**_: Any) -> Any:
        raise IdentityRefused(
            envelope_id="env-null", entity_class="company", key="lei", field="lei", reason="blank"
        )

    # The load-bearing half of "at registration" on the PAVED ROAD, where the
    # answering call is already in flight: the refusal must still precede every
    # deployment-supplied seam, so nothing is half-assembled and no acquisition
    # has read a source. Asserted rather than asserted-in-prose.
    reached: list[str] = []

    def _acquire(context: Any) -> Any:
        reached.append("acquisition")
        return None

    with _open(root, scratch, project=_null_identity, acquire=_acquire) as opened:
        with pytest.raises(ProductClassRegistrationError) as refused:
            opened.answer(_question(opened))
    assert reached == [], (
        "the acquisition seam ran before the registration refusal; the refusal"
        " must precede every deployment-supplied seam"
    )
    message = str(refused.value)
    for named in (
        "ccf.assembly.worker.IdentityRefused",  # the SDK-owned key
        "nonexistent",  # the SDK's binding …
        "identity-refused",  # … both halves of it
        "borrowed-authority",  # what the author wrote, so they can find it
        "Drop it from `seam_refusals`",  # the remedy
    ):
        assert named in message, (named, message)


def test_the_refusal_and_the_dispatch_read_ONE_map_even_after_a_rebind(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Two readers of one map must not be able to disagree.

    Dispatch binds the mapping object at definition time (see
    ``test_rebinding_the_module_attribute_does_NOT_change_dispatch``). While the
    registration refusal still read the module-level NAME, a rebind made the two
    readers disagree: the refusal PERMITTED a class declaring the SDK's own seam
    type, and dispatch then converted it under the SDK's cause anyway — so the
    permitted declaration was silently inert, which is the exact shape that
    refusal exists to prevent. Measured before the fix; this pins its absence.

    Not a security control. Rebinding is in-process and therefore inside the
    trust boundary (the map's own comment says so). This is a COHERENCE control:
    whatever one reader sees, the other sees.
    """
    import ccf.products.resolver as resolver_module
    from ccf.products.contract import ProductClassRegistrationError

    # The rebind that used to split the two readers: an EMPTY map, which a
    # name-reading refusal would find nothing in.
    monkeypatch.setattr(resolver_module, "SDK_SEAM_REFUSALS", {})
    assert resolver_module.SDK_SEAM_REFUSALS == {}, "the rebind itself must land"

    config = _config()
    config["product_class"]["seam_refusals"] = [
        {
            "exception": "ccf.assembly.worker.IdentityRefused",
            "cause": "unauthorized",
            "error_code": "borrowed-authority",
        }
    ]
    root = _write_tree(tmp_path / "b3coh", config=config)
    scratch = tmp_path / "b3coh" / "scratch"

    def _null_identity(**_: Any) -> Any:
        raise IdentityRefused(
            envelope_id="env-coh", entity_class="company", key="lei", field="lei", reason="null"
        )

    with _open(root, scratch, project=_null_identity) as opened:
        with pytest.raises(ProductClassRegistrationError, match="IdentityRefused"):
            opened.answer(_question(opened))


def test_the_sdk_map_wins_over_a_product_class_declaring_the_same_sdk_type() -> None:
    """THE RUNTIME BACKSTOP the registration refusal does not replace.

    Consulted BEFORE the class's map, so the SDK's meaning is the one minted.
    The registration refusal above closes the paved road to this declaration, so
    this control necessarily sits BELOW that door — it drives the lookup
    directly — and it is the reason the consult ORDER still has to hold: a
    resolver reached by some other route, or a declaration that arrives after a
    boot, must not be able to borrow the SDK's authority for a type the SDK owns.

    Asserted on the binding the lookup RETURNS rather than on record text, which
    is strictly more than the paved-road version could see: it pins the SDK's
    cause and code and pins that the class's restatement is not the object
    chosen.
    """
    from ccf.controlplane.artifacts import ProductClassDeclaration, SeamRefusalBinding
    from ccf.products.resolver import SDK_SEAM_REFUSALS, GovernedResolver

    restated = SeamRefusalBinding(
        exception="ccf.assembly.worker.IdentityRefused",
        cause="unauthorized",
        error_code="borrowed-authority",
    )
    declaring = ProductClassDeclaration.model_construct(seam_refusals=(restated,))

    # The SHIPPED method, called on an instance that supplies only what it
    # reads. `GovernedResolver` is a frozen dataclass, so the declaration read is
    # substituted through `object.__setattr__`; nothing else in the method is
    # touched, so this exercises the real lookup rather than a copy of it.
    resolver = object.__new__(GovernedResolver)

    def _declaring() -> ProductClassDeclaration:
        return declaring

    object.__setattr__(resolver, "_declaration", _declaring)

    chosen = GovernedResolver._declared_seam_refusal(
        resolver,
        IdentityRefused(
            envelope_id="env-null",
            entity_class="company",
            key="lei",
            field="lei",
            reason="blank",
        ),
    )
    assert chosen is SDK_SEAM_REFUSALS["ccf.assembly.worker.IdentityRefused"]
    assert (chosen.cause, chosen.error_code) == ("nonexistent", "identity-refused")
    assert chosen is not restated, "the class's restatement was chosen"

    # And the class's OWN types still reach it — the SDK map is a first look,
    # not a short circuit that drops the declared map.
    declared_only = ProductClassDeclaration.model_construct(
        seam_refusals=(
            SeamRefusalBinding(
                exception=f"{__name__}._ControlRoomUnreachable",
                cause="unauthorized",
                error_code="control-room-unreachable",
            ),
        )
    )

    def _declared_only() -> ProductClassDeclaration:
        return declared_only

    object.__setattr__(resolver, "_declaration", _declared_only)
    assert (
        GovernedResolver._declared_seam_refusal(
            resolver, _ControlRoomUnreachable("still declared")
        )
        is declared_only.seam_refusals[0]
    )


def test_a_subclass_of_an_SDK_seam_class_is_NOT_converted_either(
    tmp_path: pathlib.Path,
) -> None:
    """The mechanism map is consulted by EXACT name, as B2's own map is.

    Written because a severing campaign found the hole: replacing the exact
    ``.get`` with a walk over the raised type's ``__mro__`` left every other test
    in this module green. B2's exact-type rule was pinned for the declared map
    (``test_a_subclass_of_a_declared_type_is_NOT_converted``) and the mechanism
    map's docstring claimed the same rule without anything holding it.

    It matters more here than there: a deployment that subclasses an SDK
    exception to carry its own context would have that subclass silently
    converted under the SDK's cause — a widening of the mechanism map achieved
    without touching the mechanism map.
    """

    class _DeploymentsOwnIdentityProblem(IdentityRefused):
        pass

    root = _write_tree(tmp_path / "b3sub", config=_config())
    scratch = tmp_path / "b3sub" / "scratch"

    def _subclassed(**_: Any) -> Any:
        raise _DeploymentsOwnIdentityProblem(
            envelope_id="env-sub",
            entity_class="company",
            key="lei",
            field="lei",
            reason="null",
        )

    with _open(root, scratch, project=_subclassed) as opened:
        with pytest.raises(_DeploymentsOwnIdentityProblem, match="env-sub"):
            opened.answer(_question(opened))


# The DEPLOYMENT's own module, built at import time so the class defined in it
# genuinely reports `acme.identity` as its `__module__` — a class statement reads
# `__name__` out of the namespace it executes in, so this is the real thing
# rather than an attribute set after the fact. It stands for a deployment that
# happens to name its own exception `IdentityRefused`, which is not a contrived
# coincidence: it is the obvious name for the failure.
_DEPLOYMENT_MODULE = types.ModuleType("acme.identity")
exec(  # noqa: S102 — a class STATEMENT is the point; `type()` would set __module__ by hand
    compile(
        "class IdentityRefused(Exception):\n"
        "    '''A deployment's own identity failure, in a deployment's own module.'''\n",
        "<acme.identity>",
        "exec",
    ),
    _DEPLOYMENT_MODULE.__dict__,
)
_ForeignIdentityRefused: type[Exception] = _DEPLOYMENT_MODULE.IdentityRefused


def test_the_match_is_MODULE_QUALIFIED_so_a_look_alike_name_is_not_converted(
    tmp_path: pathlib.Path,
) -> None:
    """A class merely NAMED like the SDK's, in its own module, is not converted.

    The shipped lookup compares the full ``module.QualName``. Nothing held that:
    replacing the exact lookup with a match on the bare type name left every one
    of the tree's tests green, and under that mutant a deployment's own
    ``IdentityRefused`` — a name any deployment might reasonably choose for the
    same failure — would be converted under the SDK's cause and code, carrying
    the SDK's authority for a diagnosis the SDK never made.

    The class is defined inside a synthetic module, so its ``__module__`` is
    ``acme.identity`` rather than this test module's name; if it were defined
    here the mutant and the shipped code would disagree for the wrong reason.
    """
    assert _ForeignIdentityRefused.__module__ == "acme.identity"
    assert _ForeignIdentityRefused.__qualname__ == IdentityRefused.__qualname__
    assert _ForeignIdentityRefused is not IdentityRefused
    assert not issubclass(_ForeignIdentityRefused, IdentityRefused), (
        "this must not be the subclass case; that is pinned separately"
    )

    root = _write_tree(tmp_path / "b3qual", config=_config())  # declares NO seam_refusals
    scratch = tmp_path / "b3qual" / "scratch"

    def _look_alike(**_: Any) -> Any:
        raise _ForeignIdentityRefused("a deployment's own identity failure")

    with _open(root, scratch, project=_look_alike) as opened:
        with pytest.raises(_ForeignIdentityRefused, match="a deployment's own"):
            opened.answer(_question(opened))


def test_a_DIFFERENT_sdk_exception_at_a_seam_is_not_converted(
    tmp_path: pathlib.Path,
) -> None:
    """The map names ONE type, not "anything the SDK raises".

    A mutant converting every exception whose module starts with the package
    prefix survived this module's own suite and was caught only incidentally, by
    six tests elsewhere that happen to raise SDK errors at a seam. Incidental
    coverage is not evidence: nothing here said the scope was one named type.

    ``SeamRefusalWidening`` is deliberately the SDK exception chosen — it is
    about seam refusals, so it is the most plausible thing to be swept in by a
    subject-matter-shaped widening, and it is still a DEFECT rather than a
    determination when it escapes a seam.
    """
    from ccf.deployment import SeamRefusalWidening
    from ccf.products.resolver import SDK_SEAM_REFUSALS

    assert SeamRefusalWidening.__module__.split(".")[0] == "ccf"
    assert f"{SeamRefusalWidening.__module__}.{SeamRefusalWidening.__qualname__}" not in (
        SDK_SEAM_REFUSALS
    )

    root = _write_tree(tmp_path / "b3other", config=_config())
    scratch = tmp_path / "b3other" / "scratch"

    def _other_sdk_error(**_: Any) -> Any:
        raise SeamRefusalWidening("an SDK error the SDK did not bind")

    with _open(root, scratch, project=_other_sdk_error) as opened:
        with pytest.raises(SeamRefusalWidening, match="did not bind"):
            opened.answer(_question(opened))


# --------------------------------------------------------------------------
# The REAL route. Everything above raises `IdentityRefused` synthetically from a
# seam; this drives the actual producer — an acquisition whose source record
# carries an identity value that names no entity — through the real mint site.
# --------------------------------------------------------------------------

#: A fixed instant. NOT a clock read: a test that read the wall clock would make
#: its own evidence unreproducible.
_ACQUIRED_AT = datetime(2026, 2, 1, tzinfo=UTC)


@pytest.mark.parametrize(
    ("value", "reason"),
    [
        (None, "null"),
        ("", "empty"),
        ("   ", "empty"),
        (True, "bool"),
        (1.5, "float"),
    ],
    ids=["null", "empty", "whitespace", "bool", "float"],
)
def test_the_REAL_route_converts_at_the_acquisition_seam_with_the_workers_own_reason(
    tmp_path: pathlib.Path,
    value: object,
    reason: str,
) -> None:
    """An acquisition reading a record whose identity value names no entity.

    The positive tests above raise ``IdentityRefused`` from a seam by hand, which
    proves the CONVERSION and says nothing about whether anything real produces
    the exception there. This drives the producer:
    :class:`~ccf.assembly.worker.SpecDrivenEntityResolution` over an envelope
    whose declared identity field holds each member of B1's inadmissible set, at
    the ``acquisition`` seam a deployment actually supplies. All five convert,
    and the worker's OWN reason — not a reason this test invented — reaches the
    record's refusal detail, because the SDK carries the exception's message
    unedited.

    **The whitespace case's reason is ``empty``, and the null case's is
    ``null``.** Absence and blankness are separate reasons at the mint site (the
    presence check answers ``None`` before the scalar checks are reached), which
    is exactly the distinction the held question for the project owner is about,
    so the parametrization states each one rather than matching loosely.
    """
    from ccf.assembly.worker import (
        EntityResolutionRule,
        EntityResolutionSpec,
        SpecDrivenEntityResolution,
    )
    from ccf.signal.envelope import SignalEnvelope, SourceIdentity

    spec = EntityResolutionSpec(
        semver="1.0.0",
        entity_rules=(
            EntityResolutionRule(
                match_key="counterparty_lei",
                entity_class="company",
                identity_keys=("counterparty_lei",),
            ),
        ),
    )
    root = _write_tree(tmp_path / f"b3real-{reason}", config=_config())
    scratch = tmp_path / f"b3real-{reason}" / "scratch"

    def _acquire_a_bad_record(context: Any) -> Any:
        """Read one source record and resolve it, exactly as a deployment would."""
        return SpecDrivenEntityResolution(spec=spec).resolve(
            envelope=SignalEnvelope(
                tenant_id="tenant-a",
                envelope_id="env-source-1",
                source=SourceIdentity(system_id="core-banking"),
                ingestion_timestamp=_ACQUIRED_AT,
                raw_payload={"counterparty_lei": value},
            )
        )

    with _open(root, scratch, acquire=_acquire_a_bad_record) as opened:
        outcome = opened.answer(_question(opened))
        assert isinstance(outcome, RefusalEnvelope), outcome
        assert _seam_of(opened, outcome) == "acquisition"
        block = str(opened.record_of(outcome).content_generation_path.assembly_refusal)
        assert "identity-refused" in block and "nonexistent" in block, block
        assert f"({reason})" in block, (reason, block)
        # The reason is asserted EXACTLY, not loosely: every other reason the
        # mint site can name must be absent, so a test that merely saw "some
        # refusal happened" cannot pass. That is what keeps `null` distinct from
        # `non-scalar`, which is the distinction the held question turns on.
        for other in ("null", "empty", "bool", "float", "non-scalar", "non-finite"):
            if other != reason:
                assert f"({other})" not in block, (other, block)


@pytest.mark.parametrize(
    "invisible",
    ["\u200b", "\ufeff", "\xa0", "\u2028", "\x00", "\u200b\ufeff\xa0\x00"],
    ids=["zero-width-space", "BOM", "NBSP", "line-separator", "NUL", "mixed"],
)
def test_an_identity_of_only_invisible_characters_refuses_rather_than_minting(
    invisible: str,
) -> None:
    """D-IMPL-357 item 1, Dave: amend B1 for IDENTITY VALUES ONLY.

    `str.strip` removes Python's whitespace set, which does not contain U+200B,
    U+FEFF or NUL. Before this amendment an identity holding only a zero-width
    space passed the blank check and minted a node — reproduced at fabric level
    as three distinct entities collapsing onto shared nodes with two real
    relationships between them, which for a bank is two counterparties merged
    by a character nobody can see in a diff, a log line or a review.

    The reason stays `empty`: the value IS empty once invisibles are discounted,
    and keeping the reason vocabulary fixed is Dave's item-3 ruling.

    Calls :meth:`~ccf.assembly.worker.SpecDrivenEntityResolution._identity_of`
    directly, per the task brief. That name is a class-level alias this repair
    adds onto the module-level :func:`~ccf.assembly.worker._identity_text` —
    the function the brief actually describes editing (its quoted "current"
    branch text matches `_identity_text` verbatim, not any function literally
    named `_identity_of` in the tree at this HEAD) — so the real production
    path (`SpecDrivenEntityResolution.resolve`, which calls `_identity_text`
    directly) is unchanged and this control exercises the same amended logic
    through the class-qualified name the brief calls for.
    """
    from ccf.assembly.worker import SpecDrivenEntityResolution

    resolved, reason = SpecDrivenEntityResolution._identity_of(invisible)
    assert resolved is None
    assert reason == "empty"


def test_the_identity_amendment_does_not_touch_ordinary_attribute_semantics() -> None:
    """Dave: "Do not change ordinary attribute semantics in this repair."

    An identity carrying an invisible character BESIDE a visible one is still a
    real identity, and an attribute holding only invisible characters is still
    stored as text. Both are ledgered residuals (item 3), not things this repair
    closes, and pinning the first here is what stops a later edit from widening
    the amendment into ordinary attribute semantics.
    """
    from ccf.assembly.worker import SpecDrivenEntityResolution

    assert SpecDrivenEntityResolution._identity_of("a\u200bb")[0] == "a\u200bb"
