"""Boot cleanup, pinned: neither step may be skipped by the one before it.

Close-review finding F4 (Gemini and Ollama, independently). ``ccf.boot`` retires
the same two resources in the same order in two places — the handler around the
adapter's writer constructor, and ``shutdown`` — and both were written as two
sequential statements::

    release_boot_token(token)   # or writer.close()
    store.close()

Two statements means the second runs only if the first *returns*, and the first
is a call that can raise. Since D-IMPL-93 both first steps are, or run through,
code an installed distribution supplied.

**What makes this worth a test file rather than a two-line patch.** The comment
above the handler shows its author reasoning about ordering explicitly — the
mint is released first *so that* a store whose ``close`` also raises cannot
leave the graph permanently unbootable. That rationale is correct and survives
this change unaltered. What it did not consider is the symmetric case: the
*first* step raising, which skipped the second entirely and leaked the store's
connection — the exact leak the handler exists to prevent, arriving through the
handler itself.

Both tests here fail against the two-statement form and pass against
``try``/``finally``. They assert on the store's own close count rather than on
the shape of the code, because "these two lines are inside a ``finally``" is a
description of the source and "the connection was released" is the property.

The probe adapter is declared through a real
:class:`importlib.metadata.EntryPoint` for the duration of one test, the way
``tests/graph/test_boot_seam.py`` does it: the behaviour under test is the
composition root's, and a test that needed ``pip install`` to run is a test that
does not run.
"""

from __future__ import annotations

import importlib
import importlib.metadata as metadata
import sys
from types import SimpleNamespace
from typing import Any

import pytest

from ccf.graph._writer import _LIVE_WRITERS
from ccf.graph.registry import BACKEND_ENTRY_POINT_GROUP

#: Graph identities this module mints, so teardown can clear whatever a
#: deliberately-broken release left behind. Both tests below sabotage a cleanup
#: path on purpose, and one of them sabotages the mint release itself — so the
#: global live-writer set is exactly the state that cannot be relied on to
#: unwind here. Prefixed rather than enumerated so a third test inherits it.
_IDENTITY_PREFIX = "probe://f4-"

#: A throwaway adapter with a switch on each call the composition root does not
#: own: the writer constructor, and the writer's teardown.
_CLEANUP_PROBE = '''\
"""A throwaway adapter whose two failure points are switchable from the test."""

from typing import Any

from ccf.contracts.base import CCFContract
from ccf.graph.backends.memory import MemoryGraphStore
from ccf.graph.backends.memory_write import MemoryGraphWriter
from ccf.graph.registry import BackendRegistration

#: One-element lists so the test can flip them through the imported module.
EXPLODE_WRITER_CTOR = [False]
EXPLODE_WRITER_CLOSE = [False]

#: Every store this adapter opened, in order. Each counts its own closes, so
#: "was the connection released?" is a fact the test reads rather than infers
#: from the absence of a complaint.
OPENED: list[Any] = []


class ProbeConnection(CCFContract):
    identity: str


class _CountingStore(MemoryGraphStore):
    """The in-memory store with a supplied identity and a close counter."""

    def __init__(self, identity: str) -> None:
        super().__init__()
        self._graph_identity = identity
        self.closes = 0

    def close(self) -> None:
        self.closes += 1
        super().close()


class _FailingCloseWriter(MemoryGraphWriter):
    """A writer whose teardown raises the way a driver's teardown does.

    It raises **before** ``BaseGraphWriter.close`` runs, which is the harsher
    of the two orderings: the mint is still held when the exception leaves, so
    nothing about this failure is tidy. The store's connection is the resource
    under test and it must be released anyway.
    """

    def close(self) -> None:
        if EXPLODE_WRITER_CLOSE[0]:
            raise RuntimeError("third-party writer blew up closing")
        super().close()


def _open_store(config: Any, secrets: Any) -> Any:
    store = _CountingStore(config.identity)
    OPENED.append(store)
    return store


def _make_writer(store: Any, token: Any) -> Any:
    if EXPLODE_WRITER_CTOR[0]:
        raise RuntimeError("third-party adapter blew up building its writer")
    return _FailingCloseWriter(store=store, token=token)


REGISTRATION = BackendRegistration(
    name="ADAPTER_NAME",
    config_model=ProbeConnection,
    secret_fields=frozenset(),
    open_store=_open_store,
    make_writer=_make_writer,
)
'''


@pytest.fixture
def cleanup_adapter(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> Any:
    """Declare the probe adapter, and hand the test its imported module.

    The module is imported here rather than left for ``resolve`` to import,
    because both tests have to set a switch *before* the boot that trips it.
    Nothing in this file asserts the D-05 "discovery imports nothing" property
    — ``tests/graph/test_backend_registry.py`` owns that — so importing early
    costs no claim.
    """
    adapter_name = "probe_cleanup"
    module_name = "ccf_probe_cleanup_write"
    source = _CLEANUP_PROBE.replace("ADAPTER_NAME", adapter_name)
    (tmp_path / f"{module_name}.py").write_text(source, encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))

    from ccf.graph import registry as registry_module

    point = metadata.EntryPoint(
        adapter_name, f"{module_name}:REGISTRATION", BACKEND_ENTRY_POINT_GROUP
    )
    point = point._for(SimpleNamespace(name="ccf-probe-cleanup", version="0.1.0"))
    monkeypatch.setattr(
        registry_module,
        "_declared_entry_points",
        lambda: metadata.EntryPoints((point,)),
    )

    module = importlib.import_module(module_name)
    try:
        yield adapter_name, module
    finally:
        sys.modules.pop(module_name, None)
        for identity in [
            live for live in _LIVE_WRITERS if live.startswith(_IDENTITY_PREFIX)
        ]:
            _LIVE_WRITERS.discard(identity)


def _boot_probe(adapter_name: str, identity: str, spec: Any) -> Any:
    """Boot the probe adapter over one named graph."""
    from ccf.boot import boot
    from ccf.controlplane.registry import ControlPlaneRegistry

    control_plane = ControlPlaneRegistry()
    spec_version = control_plane.register("probe/spec", spec)
    policy_version = control_plane.register("probe/policy", {"regime": "probe"})
    return boot(
        backend=adapter_name,
        connection={"identity": identity},
        registry=control_plane,
        resolution_spec_key="probe/spec",
        resolution_spec_version=spec_version,
        policy_bundle_key="probe/policy",
        policy_bundle_version=policy_version,
    )


def test_a_release_that_raises_still_closes_the_store(
    cleanup_adapter: Any, banking_spec: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F4, first half — the failed-boot handler runs both of its steps.

    The handler releases the mint and then closes the store, in that order and
    for a stated reason. Written as two statements, a ``release_boot_token``
    that raised took the ``store.close()`` with it: the boot failed, the caller
    was handed no object, and the connection the adapter opened had no reachable
    close left in the process. That is the leak the handler was written to
    prevent, reached through the handler.

    ``release_boot_token`` is replaced rather than provoked because there is no
    supported way to make the real one raise — which is the point. It is a small
    function today; the guarantee under test is that the handler does not
    *depend* on that, since the same handler shape is what a future release that
    touches a lock or a file would meet.

    The adapter's own failure must still be readable, so the test also asserts
    it is on the raised exception's chain rather than discarded.
    """
    from ccf import boot as boot_module

    adapter_name, probe = cleanup_adapter
    probe.EXPLODE_WRITER_CTOR[0] = True

    def _exploding_release(token: Any) -> None:
        raise RuntimeError("release blew up retiring the mint")

    monkeypatch.setattr(boot_module, "release_boot_token", _exploding_release)

    with pytest.raises(RuntimeError) as caught:
        _boot_probe(adapter_name, f"{_IDENTITY_PREFIX}release", banking_spec)

    assert "release blew up" in str(caught.value)
    # The adapter's failure is not swallowed by the cleanup failure.
    assert isinstance(caught.value.__context__, RuntimeError)
    assert "building its writer" in str(caught.value.__context__)
    # The property. Fails on the two-statement form.
    assert len(probe.OPENED) == 1
    assert probe.OPENED[0].closes == 1


def test_a_writer_close_that_raises_still_closes_the_store(
    cleanup_adapter: Any, banking_spec: Any
) -> None:
    """F4, second half — ``shutdown`` runs both of its steps too.

    ``shutdown`` is the ordinary path: it is what ``FabricHandle.close`` calls,
    and what every ``with handle:`` block reaches on exit. Since D-IMPL-93 the
    writer it closes first can be a third party's, and a driver that raises
    tearing down a session is not an exotic failure — it is a network partition
    at the wrong moment.

    Written as two statements, that raise skipped ``store.close()`` and left the
    connection open in a process that had just been told to retire the fabric.
    ``FabricHandle.close`` sets ``_closed`` before delegating here, so the caller
    cannot even retry: a second ``close()`` returns immediately. One raise, one
    permanently leaked connection.
    """
    adapter_name, probe = cleanup_adapter
    probe.EXPLODE_WRITER_CLOSE[0] = True

    handle = _boot_probe(adapter_name, f"{_IDENTITY_PREFIX}shutdown", banking_spec)

    with pytest.raises(RuntimeError) as caught:
        handle.close()

    assert "blew up closing" in str(caught.value)
    # The property. Fails on the two-statement form.
    assert len(probe.OPENED) == 1
    assert probe.OPENED[0].closes == 1
