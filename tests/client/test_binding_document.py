"""`D-IMPL-141` (PROPOSED) — the binding document, and the refusals it owes.

The surface under test is **proposed, not ruled**. These tests pin what the
proposal actually does, so the thing Dave rules on is a measured behaviour
rather than a description of one.

**Every refusal here is asserted on its message, not just on its type.** A
binding document is deployment wiring authored by hand, and the failures below
are the ones an adopter will actually hit — a mistyped key, a renamed factory, a
module that does not import. A refusal that says only "BindingError" costs the
reader the diagnosis the loader already performed, so each assertion names the
file and the key it expects to be told about.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from ccf.client.adapters.binding_document import (
    BINDING_DOCUMENT_NAME,
    OPTIONAL_KEYS,
    REQUIRED_KEYS,
    conforming_resolver,
    load_binding_document,
    load_reference,
)
from ccf.client.errors import BindingError, TransportError


def _document(root: Path) -> dict[str, Any]:
    return dict(
        yaml.safe_load((root / BINDING_DOCUMENT_NAME).read_text(encoding="utf-8"))
    )


def _rewrite(root: Path, body: dict[str, Any]) -> None:
    (root / BINDING_DOCUMENT_NAME).write_text(
        yaml.safe_dump(body), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# The committed fixture is a valid document — asserted first, because every
# refusal below is only meaningful against a subject that otherwise loads.
# ---------------------------------------------------------------------------


def test_binding_document_loads_the_committed_fixture(
    deployment_root: Path,
) -> None:
    """The fixture deployment states a document this loader accepts.

    A precondition, not a formality: every refusal test below mutates this
    document, so if the unmutated form did not load, each of them would be
    asserting that a broken document is broken.
    """
    document = load_binding_document(deployment_root)

    assert document.root == deployment_root.resolve()
    assert document.config == (deployment_root / "ccf_config.yaml").resolve()
    assert document.resolver == "resolver.py:build_resolver"
    assert document.question == "resolver.py:build_question"
    assert document.connection == "resolver.py:connection"


def test_binding_document_resolves_a_relative_root_to_an_absolute_one(
    deployment_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``./deployment`` and its absolute spelling parse to one root.

    This is the property the in-process boot cache keys on (``D-30``), asserted
    here at the loader because this is where the resolution happens.
    """
    monkeypatch.chdir(deployment_root.parent)

    relative = load_binding_document("./deployment")
    absolute = load_binding_document(deployment_root)

    assert relative.root == absolute.root == deployment_root.resolve()


# ---------------------------------------------------------------------------
# The refusals — one per way an adopter gets this wrong.
# ---------------------------------------------------------------------------


def test_binding_document_refuses_a_root_with_no_document(tmp_path: Path) -> None:
    """Refusal 1: no ``binding.yaml`` at the root the address named."""
    empty = tmp_path / "not-a-deployment"
    empty.mkdir()

    with pytest.raises(BindingError) as refused:
        load_binding_document(empty)

    message = str(refused.value)
    assert BINDING_DOCUMENT_NAME in message
    assert str(empty) in message
    for key in REQUIRED_KEYS:
        assert key in message, "the refusal names what to state, not just what is absent"


def test_binding_document_refuses_a_root_that_is_not_a_directory(
    tmp_path: Path,
) -> None:
    """An address naming a file, or nothing at all, is not a deployment root."""
    with pytest.raises(BindingError) as refused:
        load_binding_document(tmp_path / "nowhere")

    assert "not a deployment root" in str(refused.value)


@pytest.mark.parametrize("omitted", REQUIRED_KEYS)
def test_binding_document_refuses_a_missing_required_key(
    deployment_root: Path, omitted: str
) -> None:
    """Refusal 2: a required key is absent, and the refusal names *which*.

    Parameterized over :data:`REQUIRED_KEYS` rather than over a copy of it, so
    a fourth required key cannot arrive without a test for its absence.
    """
    body = _document(deployment_root)
    del body[omitted]
    _rewrite(deployment_root, body)

    with pytest.raises(BindingError) as refused:
        load_binding_document(deployment_root)

    message = str(refused.value)
    assert f"`{omitted}`" in message
    assert BINDING_DOCUMENT_NAME in message


def test_binding_document_refuses_an_empty_required_value(
    deployment_root: Path,
) -> None:
    """A key stated with no value is as absent as a key never stated.

    The two are the same defect from the adopter's seat — nothing names the
    resolver — so they get the same refusal rather than one falling through to
    a later, less informative failure.
    """
    body = _document(deployment_root)
    body["resolver"] = "   "
    _rewrite(deployment_root, body)

    with pytest.raises(BindingError) as refused:
        load_binding_document(deployment_root)

    assert "`resolver`" in str(refused.value)


def test_binding_document_refuses_an_unknown_key_by_name(
    deployment_root: Path,
) -> None:
    """An unknown top-level key is refused, and the refusal names it.

    Refused rather than ignored, in the ``DeploymentConfig`` posture: a typo in
    deployment wiring that silently selected a default is a deployment running
    configuration nobody authored, and it would surface as a wrong answer
    rather than as a failed boot.
    """
    body = _document(deployment_root)
    body["resolvers"] = "resolver.py:build_resolver"
    _rewrite(deployment_root, body)

    with pytest.raises(BindingError) as refused:
        load_binding_document(deployment_root)

    message = str(refused.value)
    assert "`resolvers`" in message, "the refusal names the offending key itself"
    for key in (*REQUIRED_KEYS, *OPTIONAL_KEYS):
        assert f"`{key}`" in message, "and enumerates what the keys actually are"


def test_binding_document_refuses_a_document_that_is_not_a_mapping(
    deployment_root: Path,
) -> None:
    """A document that parsed to a scalar or a list has no keys to read."""
    (deployment_root / BINDING_DOCUMENT_NAME).write_text(
        "- config\n- resolver\n", encoding="utf-8"
    )

    with pytest.raises(BindingError) as refused:
        load_binding_document(deployment_root)

    assert "not a mapping" in str(refused.value)


def test_binding_document_refuses_a_config_path_that_does_not_exist(
    deployment_root: Path,
) -> None:
    """``config:`` naming nothing is caught here, not at boot."""
    body = _document(deployment_root)
    body["config"] = "absent.yaml"
    _rewrite(deployment_root, body)

    with pytest.raises(BindingError) as refused:
        load_binding_document(deployment_root)

    message = str(refused.value)
    assert "absent.yaml" in message
    assert "does not exist" in message


@pytest.mark.parametrize(
    "escaping", ["../outside.yaml", "/etc/passwd", "nested/../../outside.yaml"]
)
def test_binding_document_refuses_a_path_leaving_the_deployment(
    deployment_root: Path, escaping: str
) -> None:
    """Containment: a binding document is trusted no further than a manifest.

    ``T-17-19`` accepts that loading a reference runs the deployment's Python —
    the deployment root is its own trust boundary. What is *not* accepted is a
    document reaching outside the deployment it describes, which is the rule
    :class:`~ccf.controlplane.artifacts.ManifestEntry` already holds a manifest
    to.
    """
    body = _document(deployment_root)
    body["config"] = escaping
    _rewrite(deployment_root, body)

    with pytest.raises(BindingError) as refused:
        load_binding_document(deployment_root)

    assert "outside the deployment root" in str(refused.value)


def test_binding_document_refuses_a_symlink_out_of_the_deployment(
    deployment_root: Path, tmp_path: Path
) -> None:
    """The second containment check, which the first cannot cover.

    A plain name with no ``..`` and no leading ``/`` passes the string check and
    still lands outside once resolved. Both checks exist because neither covers
    the other — and this is the one a reader is most likely to think redundant.
    """
    outside = tmp_path / "outside.yaml"
    outside.write_text("semver: '1.0.0'\n", encoding="utf-8")
    (deployment_root / "sneaky.yaml").symlink_to(outside)
    body = _document(deployment_root)
    body["config"] = "sneaky.yaml"
    _rewrite(deployment_root, body)

    with pytest.raises(BindingError) as refused:
        load_binding_document(deployment_root)

    assert "outside the deployment root" in str(refused.value)


# ---------------------------------------------------------------------------
# The reference loader — refusals 3, 4 and 5.
# ---------------------------------------------------------------------------


def test_load_reference_resolves_the_fixture_factories(
    deployment_root: Path,
) -> None:
    """The positive case, so the refusals below are not the only measurement."""
    document = load_binding_document(deployment_root)

    factory = load_reference(document.resolver, root=document.root, key="resolver")
    question = load_reference(document.question, root=document.root, key="question")

    assert callable(factory)
    assert callable(question)


@pytest.mark.parametrize("malformed", ["resolver.py", ":build", "resolver.py:"])
def test_load_reference_refuses_a_reference_with_no_attribute(
    deployment_root: Path, malformed: str
) -> None:
    """A reference is a module path, a colon and an attribute — all three."""
    with pytest.raises(BindingError) as refused:
        load_reference(malformed, root=deployment_root.resolve(), key="resolver")

    assert "`<module-path>:<attribute>`" in str(refused.value)


def test_load_reference_refuses_an_unresolvable_module(
    deployment_root: Path,
) -> None:
    """Refusal 3: the module the reference names is not there."""
    with pytest.raises(BindingError) as refused:
        load_reference(
            "absent.py:build_resolver", root=deployment_root.resolve(), key="resolver"
        )

    message = str(refused.value)
    assert "`resolver: absent.py:build_resolver`" in message
    assert "does not exist" in message


def test_load_reference_refuses_a_module_that_raises_on_import(
    deployment_root: Path,
) -> None:
    """A module that exists but does not import is named, with its own error.

    Distinct from a module that is absent: the adopter's next action differs,
    so the two refusals differ.
    """
    (deployment_root / "broken.py").write_text(
        "raise ValueError('deployment module is broken')\n", encoding="utf-8"
    )

    with pytest.raises(BindingError) as refused:
        load_reference(
            "broken.py:anything", root=deployment_root.resolve(), key="resolver"
        )

    message = str(refused.value)
    assert "raised while importing" in message
    assert "deployment module is broken" in message


def test_load_reference_refuses_a_missing_attribute(deployment_root: Path) -> None:
    """Refusal 4: the module imports, but holds no such attribute."""
    with pytest.raises(BindingError) as refused:
        load_reference(
            "resolver.py:build_nothing", root=deployment_root.resolve(), key="resolver"
        )

    message = str(refused.value)
    assert "`build_nothing`" in message
    assert "does not define" in message


def test_load_reference_loads_two_roots_as_two_modules(
    deployment_root: Path, tmp_path: Path
) -> None:
    """Two deployments carrying a ``resolver.py`` each are two modules.

    A bare module name would be a real collision, not a theoretical one: the
    conformance suite boots more than one deployment in a process and
    ``sys.modules`` is process-wide, so the second root would silently get the
    first root's code.
    """
    import shutil

    second = tmp_path / "second"
    shutil.copytree(deployment_root, second)
    (second / "resolver.py").write_text(
        (second / "resolver.py").read_text(encoding="utf-8")
        + "\n\nMARKER = 'second-deployment'\n",
        encoding="utf-8",
    )

    first_module = load_reference(
        "resolver.py:build_resolver", root=deployment_root.resolve(), key="resolver"
    )
    second_marker = load_reference(
        "resolver.py:MARKER", root=second.resolve(), key="resolver"
    )

    assert second_marker == "second-deployment"
    assert first_module.__module__ != second_marker


def test_conforming_resolver_accepts_the_fixture_resolver(
    deployment_root: Path,
) -> None:
    """The Protocol check passes on a real resolver.

    Asserted before the negative case below, because a check that refused
    everything would pass that case while being useless.
    """
    from ccf.controlplane.registry import ControlPlaneRegistry
    from ccf.deployment.config import load_config_and_boot

    document = load_binding_document(deployment_root)
    registry = ControlPlaneRegistry()
    connect = load_reference(
        document.connection or "", root=document.root, key="connection"
    )
    booted = load_config_and_boot(
        document.config, registry=registry, connection=connect(root=document.root)
    )
    try:
        factory = load_reference(
            document.resolver, root=document.root, key="resolver"
        )
        resolved = conforming_resolver(
            factory(fabric=booted, control_plane=registry),
            reference=document.resolver,
            root=document.root,
        )
        assert callable(resolved)
    finally:
        booted.handle.close()


def test_conforming_resolver_refuses_a_factory_returning_a_non_resolver(
    deployment_root: Path,
) -> None:
    """Refusal 5: the factory returned something that is not a resolver.

    ``ServedProductResolverProtocol`` is ``@runtime_checkable``, which is what
    makes this a real structural check rather than a comment — and is the whole
    reason the Protocol carries the decorator.
    """
    with pytest.raises(BindingError) as refused:
        conforming_resolver(
            object(), reference="resolver.py:build_resolver", root=deployment_root
        )

    message = str(refused.value)
    assert "ServedProductResolverProtocol" in message
    assert "object" in message


def test_every_binding_refusal_is_a_transport_error() -> None:
    """``except TransportError`` stays the one clause for *the wire never spoke*.

    :class:`~ccf.client.errors.BindingError` inherits it, so a caller that
    branched on the transport case does not acquire a second except clause when
    a deployment's wiring is the thing that is wrong.
    """
    assert issubclass(BindingError, TransportError)
