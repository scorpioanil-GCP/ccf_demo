"""Dave's E2 (iii): a refusal recorder that cannot take ``subject_withholding=`` is refused where it is built.

``D-IMPL-378``, Dave, 2026-10-08 12:29 MST, E2 (iii), verbatim: *"Approve the
recorder keyword change. Detect incompatible recorders at construction, rather
than on the first refusal."*

``src/ccf/products/resolver.py::RefusalRecorderProtocol``'s ``record`` takes
``subject_withholding=`` (Dave's Q12), and the governed resolver passes it on
every refusal it records. A deployment's own recorder written to the earlier
signature — every keyword but that one, and no ``**kwargs`` — used to build
cleanly and raise ``TypeError`` at the first refusal: a failure that waited for
a question to be refused. Every path that accepts a refusal recorder now refuses
it while it is being built, by name (``IncompatibleRefusalRecorder``):

* ``GovernedResolver`` (and ``build_governed_resolver``, which builds one);
* the HTTP app (``create_app``), the MCP egress door
  (``build_egress_server``, which ``open_door`` builds), the MCP Experience door
  (``build_experience_server``) — each through
  ``runtime/ccf_runtime/authz/delivery_boundary.py::recorded_boundary``;
* the MCP artifact server (``build_artifact_server``).

The controls: a recorder that names the keyword, and one that takes
``**kwargs``, are accepted. The doors' other arguments are placeholders: the
recorder is the first thing each of them checks, so a refusal by any other
name, or none, is a failure here. Fixture vocabulary only (CINV-01).
"""

from __future__ import annotations

import contextlib
import pathlib
from collections.abc import Callable, Iterator
from datetime import datetime
from typing import Any

import pytest

from ccf.products import resolver as resolver_module
from ccf.products.refusal import RefusalEnvelope
from ccf.products.resolver import NO_REFUSAL_SEAM, GovernedResolver

from tests.products.test_resolver_seam import _arguments, _boot

#: The refusal every path must raise, by name (read off the module, so this
#: module is RED rather than unimportable on a tree that does not have it).
REFUSAL = "IncompatibleRefusalRecorder"


class _WithoutTheKeyword:
    """A deployment's recorder on the signature before Q12: every keyword but ``subject_withholding``.

    Everything else it is asked for — the store, the class, the disclosure
    level — it answers from the SDK's own recorder, so the only thing wrong with
    it is the one keyword.
    """

    def __init__(self, inner: Any) -> None:
        self._inner = inner

    # Stated, not delegated through ``__getattr__``: a runtime-checkable
    # Protocol's ``isinstance`` reads members statically.
    @property
    def replay_record_class(self) -> str:
        return self._inner.replay_record_class  # type: ignore[no-any-return]

    @property
    def artifact_store(self) -> Any:
        return self._inner.artifact_store

    @property
    def tenant_id(self) -> str:
        return self._inner.tenant_id  # type: ignore[no-any-return]

    def disclosure_level_for(self, **keywords: Any) -> Any:
        return self._inner.disclosure_level_for(**keywords)

    def record(
        self,
        envelope: RefusalEnvelope,
        *,
        perspective: Any,
        recorded_at: datetime,
        served_at: datetime | None,
        request: Any = None,
        execution: Any = None,
        policy_bindings: tuple[Any, ...] = (),
        assembler_id: str | None = None,
        assembler_version: str | None = None,
        resolution: Any,
        child_resolutions: tuple[Any, ...] = (),
        refusal_seam: str = NO_REFUSAL_SEAM,
    ) -> RefusalEnvelope:
        return self._inner.record(  # type: ignore[no-any-return]
            envelope, perspective=perspective, recorded_at=recorded_at, served_at=served_at,
            request=request, execution=execution, policy_bindings=policy_bindings,
            assembler_id=assembler_id, assembler_version=assembler_version, resolution=resolution,
            child_resolutions=child_resolutions, refusal_seam=refusal_seam,
        )


class _NamesTheKeyword(_WithoutTheKeyword):
    """The control: the same recorder with the keyword added."""

    def record(self, envelope: RefusalEnvelope, *, subject_withholding: str | None = None,  # type: ignore[override]
               **keywords: Any) -> RefusalEnvelope:
        return self._inner.record(  # type: ignore[no-any-return]
            envelope, subject_withholding=subject_withholding, **keywords
        )


class _TakesAnyKeyword(_WithoutTheKeyword):
    """The control: a recorder that takes ``**kwargs`` can be passed the keyword."""

    def record(self, envelope: RefusalEnvelope, **keywords: Any) -> RefusalEnvelope:  # type: ignore[override]
        return self._inner.record(envelope, **keywords)  # type: ignore[no-any-return]


@contextlib.contextmanager
def _booted(tmp_path: pathlib.Path) -> Iterator[Any]:
    """The resolver seam's fixture deployment, driven directly (its fixture is a generator)."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    generator = _boot(tmp_path)
    booted = next(generator)
    try:
        yield booted
    finally:
        generator.close()


def _refused_by_name(build: Callable[[], object], *, path: str) -> None:
    """``build`` raises, and what it raises is the named refusal — never another error, never nothing."""
    with pytest.raises(Exception) as raised:  # noqa: PT011 — the NAME is asserted below
        build()
    assert type(raised.value).__name__ == REFUSAL, (
        f"[{path}] an incompatible recorder was not refused by {REFUSAL} where it was built:"
        f" {type(raised.value).__name__}: {str(raised.value)[:400]}"
    )
    assert "subject_withholding" in str(raised.value), str(raised.value)


def _resolver_with(tmp_path: pathlib.Path, wrap: Callable[[Any], Any]) -> GovernedResolver:
    with _booted(tmp_path) as booted:
        arguments = _arguments(booted)
        arguments["refusal_recorder"] = wrap(arguments["refusal_recorder"])
        return GovernedResolver(**arguments)


def test_e2iii_the_governed_resolver_refuses_an_incompatible_recorder_where_it_is_built(
    tmp_path: pathlib.Path,
) -> None:
    """The resolver is built and no question is asked: the refusal is construction's, not a refusal's."""
    _refused_by_name(lambda: _resolver_with(tmp_path / "without", _WithoutTheKeyword),
                     path="GovernedResolver")


@pytest.mark.parametrize("compatible", [_NamesTheKeyword, _TakesAnyKeyword])
def test_e2iii_a_compatible_recorder_builds_the_resolver(tmp_path: pathlib.Path, compatible: type) -> None:
    """The controls: naming the keyword, or taking ``**kwargs``, is compatible."""
    assert isinstance(_resolver_with(tmp_path / compatible.__name__, compatible), GovernedResolver)


def test_e2iii_build_governed_resolver_refuses_an_incompatible_recorder(tmp_path: pathlib.Path) -> None:
    """``build_governed_resolver`` hands a supplied recorder to the resolver it builds."""
    from tests.deployment import test_replay_binding as binding  # noqa: PLC0415

    generator = binding._boot(tmp_path, "declared", replay=binding._replay_section())
    booted = next(generator)
    try:
        arguments = binding._resolver_arguments(booted, artifact_store_root=tmp_path / "roots")
        probe = resolver_module.build_governed_resolver(**arguments)
        _refused_by_name(
            lambda: resolver_module.build_governed_resolver(
                **arguments, refusal_recorder=_WithoutTheKeyword(probe.refusal_recorder)
            ),
            path="build_governed_resolver",
        )
    finally:
        generator.close()


def _door_recorder(tmp_path: pathlib.Path) -> Any:
    """An incompatible recorder over the SDK's own, for the doors (whose other arguments are placeholders)."""
    with _booted(tmp_path) as booted:
        return _WithoutTheKeyword(_arguments(booted)["refusal_recorder"])


def test_e2iii_create_app_refuses_an_incompatible_recorder(tmp_path: pathlib.Path) -> None:
    from ccf_runtime.http_api.app import create_app  # noqa: PLC0415

    recorder = _door_recorder(tmp_path)
    _refused_by_name(
        lambda: create_app(
            None,  # type: ignore[arg-type]
            auth=None, authorizer=None, product_entitlement=None,  # type: ignore[arg-type]
            perspective_resolver=None, refusal_recorder=recorder,  # type: ignore[arg-type]
            replay_record_product_class=None,
        ),
        path="create_app",
    )


def test_e2iii_build_egress_server_refuses_an_incompatible_recorder(tmp_path: pathlib.Path) -> None:
    from ccf_runtime.mcp.egress import build_egress_server  # noqa: PLC0415

    recorder = _door_recorder(tmp_path)
    _refused_by_name(
        lambda: build_egress_server(
            server_name="e2iii-egress", resolver=None, token_verifier=None,  # type: ignore[arg-type]
            auth_settings=None, authorizer=None, entitlement_source=None,  # type: ignore[arg-type]
            perspective_resolver=None, refusal_recorder=recorder,  # type: ignore[arg-type]
        ),
        path="build_egress_server",
    )


def test_e2iii_build_experience_server_refuses_an_incompatible_recorder(tmp_path: pathlib.Path) -> None:
    import inspect  # noqa: PLC0415

    from ccf_runtime.mcp.experience import build_experience_server  # noqa: PLC0415

    recorder = _door_recorder(tmp_path)
    placeholders: dict[str, Any] = {
        name: None
        for name, parameter in inspect.signature(build_experience_server).parameters.items()
        if parameter.default is inspect.Parameter.empty
    }
    placeholders["refusal_recorder"] = recorder
    _refused_by_name(lambda: build_experience_server(**placeholders), path="build_experience_server")


def test_e2iii_build_artifact_server_refuses_an_incompatible_recorder(tmp_path: pathlib.Path) -> None:
    from ccf_runtime.mcp.artifact_server import build_artifact_server  # noqa: PLC0415

    recorder = _door_recorder(tmp_path)
    _refused_by_name(
        lambda: build_artifact_server(
            server_name="e2iii-artifacts", store=None, token_verifier=None,  # type: ignore[arg-type]
            auth_settings=None, authorizer=None, entitlement_source=None,  # type: ignore[arg-type]
            refusal_recorder=recorder, audit_log=None, erasure_index=None,  # type: ignore[arg-type]
            control_plane=None, erasure_trust=None,  # type: ignore[arg-type]
        ),
        path="build_artifact_server",
    )
