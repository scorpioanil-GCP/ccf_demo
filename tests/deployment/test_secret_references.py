"""D-08 — a credential travels by reference, and nothing on that path leaks it.

``tests/deployment/test_manifest.py`` asserts what ``load_and_boot`` refuses and
what it pins. This module asserts the one thing that is not a refusal and not a
pin: that **no surface on the credential path can reproduce a credential**, and
that a named reference which does not resolve is refused rather than quietly
treated as no credential at all.

The leak surfaces were measured before this module was written, and each row
dictates one assertion here (15.4-RESEARCH.md §"Secret handling (RQ4, D-08)"):

===============================  =========================================
Surface                          Why it is asserted
===============================  =========================================
``canonical_bytes``              **raises** on ``SecretStr`` — the strongest
                                 guarantee available, so a resolved
                                 credential cannot be content-hashed into an
                                 artifact even by accident (V13a)
Pydantic ``ValidationError``     embeds the supplied value **verbatim**, so a
                                 misspelled connection key puts a live token
                                 in a message that reaches logs (V13b)
``graph_identity``               the string the single-writer check uses, and
                                 the one a store derives from its connection
                                 settings (V13c)
an unresolved reference          WR-02 arriving through a new door: a
                                 mis-set variable connecting anonymously
                                 (V14)
===============================  =========================================

**The empty-string case is the one most likely to be "fixed" later**, and it
must not be. It has its own test with its own docstring saying so.

Where a credential-bearing adapter is needed, this module declares a throwaway
one through a fake entry point — the pattern
``tests/graph/test_backend_registry.py`` sets and
``tests/graph/test_boot_seam.py`` extends. Only one built-in adapter declares a
credential field and booting it needs a reachable server, while the properties
under test here are properties of the *path*, not of any adapter. Stating them
over an adapter written for the test keeps them adapter-agnostic and keeps this
module free of a substrate name it would have to edit later.
"""

from __future__ import annotations

import pathlib
import sys
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import SecretStr

from ccf.contracts.canonical import CanonicalizationError, canonical_bytes
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment import load_and_boot
from ccf.graph.registry import (
    BACKEND_ENTRY_POINT_GROUP,
    InvalidBackendConfig,
    ResolvedSecret,
    declared_names,
    resolve,
)

from tests.deployment.conftest import Deployment, manifest_document

#: A value shaped like a credential and recognisable in any rendering. One
#: constant, because every leak assertion in this module is "this exact string
#: is absent", and two spellings would let one assertion pass on the other's
#: value.
TOKEN = "tok-do-not-log-me-9f3a"

#: The probe's credential field and the reference it is resolved from.
#: Deliberately unalike, so an assertion that accepted either would fail: the
#: fact D-08 makes auditable is *which reference* was in force, and a mapping
#: keyed by field could only ever say that some credential was supplied.
PROBE_FIELD = "api_token"
PROBE_REFERENCE = "CCF_PROBE_TOKEN"

#: A field no adapter declares, used for the undeclared-field refusal. Named
#: for what it is rather than borrowed from a real adapter's vocabulary.
UNDECLARED_FIELD = "not_a_credential_field"

#: An adapter that declares one credential field, records what it was handed,
#: and stores nothing durable. Its store and writer are the SDK's own
#: zero-dependency pair, so the credential really does travel a real
#: construction path rather than into a mock.
_SECRETFUL_PROBE = '''\
"""A throwaway adapter that declares one credential field."""

from typing import Any

from ccf.contracts.base import CCFContract
from ccf.graph.backends.memory import MemoryGraphStore
from ccf.graph.backends.memory_write import MemoryGraphWriter
from ccf.graph.registry import BackendRegistration

#: Credentials this adapter's store constructor actually received, and the
#: identity the store it built reports. Both recorded so the leak assertions
#: have a non-vacuity partner: the value's absence from an identity means
#: something only once the value is known to have arrived.
SEEN: list[str] = []
IDENTITIES: list[str] = []


class ProbeConnection(CCFContract):
    pass


def _open_store(config: Any, secrets: Any) -> Any:
    SEEN.append(secrets["CREDENTIAL_FIELD"].get_secret_value())
    store = MemoryGraphStore()
    IDENTITIES.append(store.graph_identity)
    return store


def _make_writer(store: Any, token: Any) -> Any:
    return MemoryGraphWriter(store=store, token=token)


REGISTRATION = BackendRegistration(
    name="ADAPTER_NAME",
    config_model=ProbeConnection,
    secret_fields=frozenset({"CREDENTIAL_FIELD"}),
    open_store=_open_store,
    make_writer=_make_writer,
)
'''


@pytest.fixture
def secretful_adapter(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> Any:
    """Declare a credential-bearing adapter for the duration of one test."""
    import importlib.metadata as metadata

    from ccf.graph import registry as registry_module

    adapter_name = "probe_secretful"
    module_name = "ccf_probe_secretful_write"
    source = _SECRETFUL_PROBE.replace("ADAPTER_NAME", adapter_name).replace(
        "CREDENTIAL_FIELD", PROBE_FIELD
    )
    (tmp_path / f"{module_name}.py").write_text(source, encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))

    point = metadata.EntryPoint(
        adapter_name, f"{module_name}:REGISTRATION", BACKEND_ENTRY_POINT_GROUP
    )
    point = point._for(SimpleNamespace(name="ccf-probe", version="9.9.9"))
    monkeypatch.setattr(
        registry_module,
        "_declared_entry_points",
        lambda: metadata.EntryPoints((point,)),
    )
    try:
        yield adapter_name
    finally:
        sys.modules.pop(module_name, None)


def _probe_manifest(
    deployment: Deployment,
    adapter: str,
    *,
    field: str = PROBE_FIELD,
    env_var: str = PROBE_REFERENCE,
) -> pathlib.Path:
    """A manifest declaring ``adapter`` and one credential reference."""
    return deployment.variant_manifest(
        f"{adapter}-{field}.yaml",
        manifest_document(
            backend=adapter,
            backend_secrets=[{"field": field, "env_var": env_var}],
        ),
    )


# --- V13a: a credential cannot be content-hashed ------------------------------


def test_canonicalizing_a_resolved_credential_raises(deployment: Deployment) -> None:
    """The no-persistence guarantee is a mechanism, not a discipline (V13a).

    ``canonical_bytes`` refuses ``SecretStr`` outright, so a
    :class:`~ccf.graph.registry.ResolvedSecret` cannot reach a content hash —
    and therefore cannot reach a Control Plane artifact or a replay record —
    even by accident. That is why the resolved value travels in this carrier
    rather than as a bare string.

    Asserted alongside the manifest's own credential *reference*, which
    canonicalizes perfectly well: the asymmetry is the whole design. A name is
    content-hashable and a value is not.
    """
    resolved = ResolvedSecret(
        field=PROBE_FIELD, ref_name=PROBE_REFERENCE, value=SecretStr(TOKEN)
    )
    with pytest.raises(CanonicalizationError):
        canonical_bytes(resolved)

    # And the same value is absent from every ordinary rendering, which is the
    # weaker guarantee the strong one sits on top of.
    for rendering in (repr(resolved), str(resolved), resolved.model_dump_json()):
        assert TOKEN not in rendering


def test_a_manifests_credential_reference_is_content_hashable(
    deployment: Deployment,
) -> None:
    """The reference half of the same asymmetry, asserted rather than assumed.

    A manifest is content-hashed into Decision Replay dimension 2. If a
    ``backend_secrets`` entry could not be canonicalized, the D-08 design would
    not work at all — so the positive case is a test, not a remark.
    """
    from ccf.controlplane.artifacts import DEPLOYMENT_MANIFEST, load_artifact

    path = deployment.variant_manifest(
        "hashable.yaml",
        manifest_document(
            backend_secrets=[{"field": PROBE_FIELD, "env_var": PROBE_REFERENCE}]
        ),
    )
    manifest = load_artifact(path.read_text(encoding="utf-8"), DEPLOYMENT_MANIFEST)
    serialized = canonical_bytes(manifest)
    assert PROBE_REFERENCE.encode() in serialized
    assert TOKEN.encode() not in serialized


# --- V13b: a refusal cannot reproduce what was supplied -----------------------


def test_a_misspelled_connection_key_does_not_echo_its_value(
    deployment: Deployment,
) -> None:
    """T-15.4-05, through the preflight an adopter actually meets (V13b).

    Pydantic reproduces the supplied value verbatim in a validation error, so a
    misspelled connection key is precisely the case where a live credential
    lands under a name nobody declared and travels out in a message. The
    preflight never builds that message: it calls
    :func:`ccf.graph.registry.validate_connection`, the phase's single owner,
    which reads the error's field location and reason and nothing else.

    The whole exception chain is asserted, not just the text. A refusal raised
    with ``from None`` still carries the unsanitized cause on ``__context__``,
    reachable by anything that walks chains explicitly.
    """
    with pytest.raises(InvalidBackendConfig) as raised:
        load_and_boot(
            deployment.manifest_path,
            registry=ControlPlaneRegistry(),
            connection={"databse_path": TOKEN},
        )

    assert TOKEN not in str(raised.value)
    assert TOKEN not in repr(raised.value)
    for linked in (raised.value.__cause__, raised.value.__context__):
        assert TOKEN not in repr(linked)

    # Non-vacuity: the refusal really is about the key that was misspelled.
    assert "databse_path" in str(raised.value)


def test_nothing_is_registered_when_the_connection_is_refused(
    deployment: Deployment,
) -> None:
    """The preflight ordering holds for the connection refusal too.

    A manifest whose connection mapping is wrong parses perfectly well, so a
    check placed beside the ``boot`` call would register every artifact first
    and fail afterwards — Control Plane state from a fabric that never booted.
    Asserted against the audit log as well as the version index, because an
    audited attempt is state too.
    """
    registry = ControlPlaneRegistry()
    with pytest.raises(InvalidBackendConfig):
        load_and_boot(
            deployment.manifest_path,
            registry=registry,
            connection={"databse_path": TOKEN},
        )
    assert registry.audit_events() == ()


# --- V13c: a credential never reaches an identity -----------------------------


def test_a_booted_stores_identity_carries_no_credential(
    deployment: Deployment, secretful_adapter: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """V13c, end to end from the manifest reference to the store.

    The per-adapter identity tests already assert this for the adapters that
    derive an identity from a credentialed URL. What is new on this path is the
    *route*: the value now arrives from an environment variable a versioned
    document named, so the assertion worth making here is that the route
    changed and the property did not.

    Both legs are needed. The credential's absence from the identity means
    nothing unless the credential arrived, so the probe records what its store
    constructor was handed and the test requires it.
    """
    monkeypatch.setenv(PROBE_REFERENCE, TOKEN)
    path = _probe_manifest(deployment, secretful_adapter)

    booted = load_and_boot(path, registry=ControlPlaneRegistry())
    try:
        probe = sys.modules["ccf_probe_secretful_write"]
        # Non-vacuity first: the value reached the store constructor.
        assert probe.SEEN == [TOKEN]
        assert probe.IDENTITIES and TOKEN not in probe.IDENTITIES[0]
        # And the pin names the reference, never the field and never the value.
        assert booted.handle.adapter.secret_refs == (PROBE_REFERENCE,)
        assert PROBE_FIELD not in booted.handle.adapter.secret_refs
        assert TOKEN not in booted.handle.adapter.model_dump_json()
    finally:
        booted.handle.close()


def test_no_adapter_declares_a_credential_as_a_connection_field() -> None:
    """Why no adapter's identity *can* carry a credential, stated once.

    A store derives its identity from its validated connection settings, so the
    structural guarantee behind V13c is that a credential is never one of them:
    ``secret_fields`` and the config model's fields are disjoint for every
    registered adapter. Swept from :func:`ccf.graph.registry.declared_names`
    rather than listed, so a seventh adapter is held to it on arrival.

    This is also the guarantee that keeps the validation error harmless. A
    credential that were a config field would be validated, and a validation
    error reproduces what it was given.
    """
    names = sorted(declared_names())
    assert names, "no adapter is registered — the sweep would be vacuous"
    for name in names:
        registration = resolve(name).registration
        overlap = registration.secret_fields & set(
            registration.config_model.model_fields
        )
        assert not overlap, (
            f"adapter {name!r} declares {sorted(overlap)} as both a credential"
            " field and a connection setting; a credential that is validated"
            " is a credential a validation error can reproduce"
        )


# --- V14: an unresolved reference is a refusal --------------------------------


def test_an_unset_reference_is_refused_naming_the_variable(
    deployment: Deployment, secretful_adapter: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """V14. A manifest that names a reference has asserted a credential.

    The fabric does not fall back to an anonymous connection, and the message
    names the adapter, the field and the variable **name** so an operator can
    fix it — and never a value, because there is none and because naming one
    here would be the disclosure the rest of this module exists to prevent.
    """
    monkeypatch.delenv(PROBE_REFERENCE, raising=False)
    path = _probe_manifest(deployment, secretful_adapter)
    registry = ControlPlaneRegistry()

    with pytest.raises(ValueError) as raised:
        load_and_boot(path, registry=registry)

    message = str(raised.value)
    assert PROBE_REFERENCE in message
    assert PROBE_FIELD in message
    assert secretful_adapter in message
    assert TOKEN not in message
    # Refused in preflight: the Control Plane is exactly as the call found it.
    assert registry.audit_events() == ()


def test_an_empty_reference_is_refused_the_same_way(
    deployment: Deployment, secretful_adapter: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """V14, the case most likely to be "fixed" later. **Do not fix it.**

    An empty environment variable is not "no credential". Treating it as one
    reproduces WR-02 exactly — a deployment that meant to authenticate connects
    anonymously and nothing says so — and it arrives through a new door, which
    is why the refusal is stated over the resolution step rather than left to
    the adapter to notice.

    If a future change makes this test fail, the change is wrong. The empty
    string is a mis-set variable, and a mis-set variable is a deployment error.
    """
    monkeypatch.setenv(PROBE_REFERENCE, "")
    path = _probe_manifest(deployment, secretful_adapter)
    registry = ControlPlaneRegistry()

    with pytest.raises(ValueError) as raised:
        load_and_boot(path, registry=registry)

    message = str(raised.value)
    assert PROBE_REFERENCE in message
    assert PROBE_FIELD in message
    assert TOKEN not in message
    assert registry.audit_events() == ()


def test_a_reference_the_adapter_does_not_declare_is_refused(
    deployment: Deployment, secretful_adapter: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A credential authored against one adapter cannot be handed to another.

    ``secret_fields`` is the whole vocabulary of credentials an adapter accepts,
    so this refusal needs no list here and nothing changes when an adapter is
    added. It fires **before the environment is read**: a reference the adapter
    cannot use is a manifest error, and reading the variable to discover that
    would pull a live credential into the process for nothing — asserted by
    setting the variable and requiring its value absent from the refusal.
    """
    monkeypatch.setenv(PROBE_REFERENCE, TOKEN)
    path = _probe_manifest(deployment, secretful_adapter, field=UNDECLARED_FIELD)
    registry = ControlPlaneRegistry()

    with pytest.raises(ValueError) as raised:
        load_and_boot(path, registry=registry)

    message = str(raised.value)
    assert secretful_adapter in message
    assert UNDECLARED_FIELD in message
    assert PROBE_FIELD in message  # what the adapter does declare
    assert TOKEN not in message
    assert registry.audit_events() == ()
