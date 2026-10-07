"""One argument rule at the fabric seam — ``Agent.invoke_skill`` (TP-04 follow-on).

``D-IMPL-361``. Task 3's review measured that :meth:`ccf.agents.agent.Agent.invoke_skill`
validates nothing against the bound entry's declared ``argument_schema``: an
undeclared key, a missing required argument and a value of the wrong type all
reached :func:`ccf.skills.dispatch.dispatch_skill`, and so the audit record.
The ruling is ONE rule, enforced at the seam every harness leg crosses: the
presented arguments are validated against the declared schema BEFORE any
dispatch, and a violation is refused by name with the public typed
:class:`~ccf.skills.wire_arguments.ArgumentRefused` family.

"Dispatched" here means :func:`ccf.skills.dispatch.dispatch_skill` was called —
the step that resolves the binding, runs a local callable and builds the
audited invocation. Every agent, grant and declared value comes from the
banking fixtures through the Agent Factory (the conformance suite's ``World``);
the undeclared key and the wrong-typed value are test vocabulary.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any

import pytest

from conformance.test_harness_adapter import World, _tool_fixture

#: A key the fixture entry's ``argument_schema`` does not declare.
UNDECLARED = "not_declared_by_this_skill"


@pytest.fixture
def dispatched(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[Mapping[str, Any]]]:
    """Every argument mapping that reached ``dispatch_skill``."""
    import ccf.skills.dispatch as dispatch_module

    reached: list[Mapping[str, Any]] = []
    original = dispatch_module.dispatch_skill

    def recording(entry: Any, *, arguments: Mapping[str, Any], **kwargs: Any) -> Any:
        reached.append(dict(arguments))
        return original(entry, arguments=arguments, **kwargs)

    monkeypatch.setattr(dispatch_module, "dispatch_skill", recording)
    yield reached


def _world() -> World:
    world = World()
    world.bind(world.grant_a, world.definition_a)
    return world


def _declared() -> dict[str, str]:
    return dict(_tool_fixture()["dispatch"]["arguments"])


def _attempt(world: World, arguments: Mapping[str, Any]) -> BaseException | None:
    try:
        world.agent_a.invoke_skill(world.grant_a.skill_name, arguments=arguments)
    except Exception as raised:  # noqa: BLE001 - the type is asserted after the hole
        return raised
    return None


def _assert_refused_by_name(
    raised: BaseException | None, reached: list[Mapping[str, Any]], *, key: str, kind: str
) -> None:
    assert reached == [], (
        f"an argument mapping with a {kind} argument reached dispatch_skill:"
        f" {reached!r} — invoke_skill validated nothing against the declared"
        " argument_schema (TP-04 follow-on, D-IMPL-361)"
    )
    from ccf.skills.wire_arguments import ArgumentRefused

    assert isinstance(raised, ArgumentRefused), f"not the typed refusal: {raised!r}"
    assert key in str(raised), f"the refusal does not name {key!r}: {raised}"


def test_an_undeclared_argument_is_refused_before_dispatch(
    dispatched: list[Mapping[str, Any]],
) -> None:
    """(a) in-process: an undeclared key is refused by name; nothing dispatches."""
    raised = _attempt(_world(), {**_declared(), UNDECLARED: "smuggled"})

    _assert_refused_by_name(raised, dispatched, key=UNDECLARED, kind="undeclared")
    from ccf.skills.wire_arguments import UndeclaredArgumentRefused

    assert isinstance(raised, UndeclaredArgumentRefused)
    assert raised.undeclared == (UNDECLARED,)


def test_a_missing_required_argument_is_refused_before_dispatch(
    dispatched: list[Mapping[str, Any]],
) -> None:
    """In-process: a required argument left out is refused by name."""
    world = _world()
    required = world.agent_a.invoke_skill(world.grant_a.skill_name).argument_schema.required  # type: ignore[union-attr]
    assert required, "the fixture entry must declare a required argument"
    presented = {k: v for k, v in _declared().items() if k != required[0]}

    raised = _attempt(world, presented)

    _assert_refused_by_name(raised, dispatched, key=required[0], kind="missing required")
    from ccf.skills.wire_arguments import MissingArgumentRefused

    assert isinstance(raised, MissingArgumentRefused)


def test_a_wrong_typed_argument_is_refused_before_dispatch(
    dispatched: list[Mapping[str, Any]],
) -> None:
    """In-process: a list where the schema declares ``string`` is refused by name."""
    declared = _declared()
    name, value = next(iter(declared.items()))

    raised = _attempt(_world(), {**declared, name: [value]})

    _assert_refused_by_name(raised, dispatched, key=name, kind="wrong-typed")
    from ccf.skills.wire_arguments import MistypedArgumentRefused

    assert isinstance(raised, MistypedArgumentRefused)


def test_the_echoed_key_names_are_capped(dispatched: list[Mapping[str, Any]]) -> None:
    """The refusal text is bounded: first 8 keys, each at most 64 characters, plus a count.

    The refusal reason is audited, so a caller who presents thousands of long
    keys must not be able to grow the audit record with them.
    """
    smuggled = {f"{index:02d}" + "k" * 200: "v" for index in range(20)}

    raised = _attempt(_world(), {**_declared(), **smuggled})

    assert dispatched == [], "the smuggled keys reached dispatch_skill"
    assert raised is not None, "nothing was refused"
    text = str(raised)
    echoed = [key for key in sorted(smuggled) if key[:64] in text]
    assert len(echoed) == 8, f"echoed {len(echoed)} of 20 keys: {text[:300]}"
    assert "k" * 65 not in text, "a key was echoed past 64 characters"
    assert "20" in text, f"the total count is not stated: {text[:300]}"
    assert len(text) < 1500, f"refusal text is unbounded: {len(text)} characters"


def test_the_control_a_declared_call_dispatches(dispatched: list[Mapping[str, Any]]) -> None:
    """The positive control: exactly the declared arguments dispatch, unchanged."""
    world = _world()

    invocation = world.agent_a.invoke_skill(world.grant_a.skill_name, arguments=_declared())

    assert dispatched == [_declared()]
    assert dict(invocation.arguments) == _declared()  # type: ignore[union-attr]
