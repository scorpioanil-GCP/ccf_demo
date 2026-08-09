"""The third-party path, end to end, against a really installed distribution.

Every other test of the registration seam works against fakes, and rightly so:
those tests are about the registry's *decisions*, and a test that needed
``pip install`` to run is a test that does not run. This module is the one that
has to pay that cost, because the claim it holds is not a decision — it is that
the whole path works for code the SDK does not contain.

The subject is ``tests/fixtures/ccf-demo-adapter``, a second installable
distribution declaring an adapter named ``demo`` through the
``ccf.graph_backends`` entry-point group. Adding it changed no line under
``src/ccf``, which is the claim D-11 rests on and the reason it is a separate
distribution rather than a seventh backend inside the SDK.

**Nothing here skips.** If the fixture is not installed, these tests fail. A
skip that replaces a pass is how a proof goes quiet, and the whole point of
this module is a claim that has to be able to fail — so the first test below
reports the missing install directly, rather than leaving it to surface as a
confusing ``UnknownBackend`` four tests later.

``make install`` installs the fixture, and so does CI. That posture is
always-on rather than opt-in, and the ruling with its rejected alternative is
recorded in the fixture's own README.
"""

from __future__ import annotations

import importlib.metadata as metadata
import sys
import tomllib
import uuid
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from ccf.contracts.canonical import canonical_bytes
from ccf.contracts.claims import EntityClaim, LineageEntry
from ccf.graph import registry
from ccf.graph._writer import SingleWriterViolation
from ccf.graph.protocols import GraphQuery, GraphReader
from ccf.graph.registry import ReservedBackendName, declared_names, resolve
from ccf.signal.envelope import SourceIdentity

# The fake-distribution helper, reused rather than reimplemented. Shipping a
# second real distribution whose only purpose is to claim a name it must not
# have would be a liability in the tree for a fact a fixture already proves.
from graph.test_backend_registry import _entry_point, _entry_points

if TYPE_CHECKING:
    from ccf.boot import FabricHandle

#: The distribution under test and the adapter it declares. Read from the
#: installed metadata wherever possible below; these two are the irreducible
#: literals, because a test that derived even the name of its own subject would
#: be asserting nothing.
DISTRIBUTION = "ccf-demo-adapter"
ADAPTER = "demo"

#: The package the distribution installs. Named because the V6 assertion is
#: precisely about whether this appears in ``sys.modules``.
PACKAGE = "ccf_demo_adapter"

_REPO_ROOT = Path(__file__).resolve().parents[2]

TENANT = "tenant-a"
T0 = datetime(2026, 1, 1, tzinfo=UTC)
T1 = datetime(2026, 2, 1, tzinfo=UTC)
T2 = datetime(2026, 3, 1, tzinfo=UTC)

# Control Plane keys for the boots this module makes itself. Deployment
# vocabulary, so they live in test code exactly as the shared fixture's do.
SPEC_KEY = "test/out-of-tree-resolution-spec"
POLICY_KEY = "test/out-of-tree-policy-bundle"


@pytest.fixture
def demo_boot(banking_spec: Any) -> Iterator[Callable[[str], "FabricHandle"]]:
    """Boot the out-of-tree adapter on a graph name the caller chooses.

    The shared ``fabric_boot`` factory gives every boot a fresh unique name,
    which is what makes "a fresh graph per test" true and is exactly wrong for
    the one property that needs two boots to name the *same* graph. Rather than
    widen a fixture the whole suite depends on for a single test's benefit,
    this one takes the name as its argument.

    Handles are closed on teardown, and in reverse, so a graph whose boot was
    refused leaves nothing attached behind it.
    """
    from ccf.boot import boot
    from ccf.controlplane.registry import ControlPlaneRegistry

    handles: list[FabricHandle] = []

    def factory(graph_name: str) -> "FabricHandle":
        control_plane = ControlPlaneRegistry()
        spec_version = control_plane.register(SPEC_KEY, banking_spec)
        policy_version = control_plane.register(
            POLICY_KEY, {"regime": "test-fixture"}
        )
        handle = boot(
            backend=ADAPTER,
            connection={"graph_name": graph_name},
            registry=control_plane,
            resolution_spec_key=SPEC_KEY,
            resolution_spec_version=spec_version,
            policy_bundle_key=POLICY_KEY,
            policy_bundle_version=policy_version,
        )
        handles.append(handle)
        return handle

    try:
        yield factory
    finally:
        for handle in reversed(handles):
            handle.close()


def _entity(*, legal_name: str = "Acme Holdings") -> EntityClaim:
    return EntityClaim(
        tenant_id=TENANT,
        entity_uri="counterparty://acme",
        entity_class="counterparty",
        attributes={"legal_name": legal_name},
        observed_at=T1,
        valid_from=T0,
        lineage=frozenset(
            {
                LineageEntry(
                    source=SourceIdentity(system_id="core-banking"),
                    envelope_id=f"env-{legal_name}",
                    observed_at=T1,
                )
            }
        ),
    )


def test_the_out_of_tree_distribution_is_installed() -> None:
    """The precondition, reported as itself rather than as a later confusion.

    This is the test that makes "fail, never skip" concrete. Everything below
    depends on the fixture being installed, and without this one the absence
    would surface as an ``UnknownBackend`` from a boot — which reads like a
    defect in the registry rather than a missing step in the environment.
    """
    try:
        installed = metadata.distribution(DISTRIBUTION)
    except metadata.PackageNotFoundError:  # pragma: no cover - the failure path
        pytest.fail(
            f"{DISTRIBUTION} is not installed. It is part of the developer"
            " bootstrap: run `make install`, or"
            " `pip install -e ./tests/fixtures/ccf-demo-adapter`. This is"
            " deliberately a failure and not a skip."
        )
    assert installed.version


def test_the_adapter_is_declared_and_carries_its_own_distribution() -> None:
    """D-04: the entry-point source is real, and the pin is derived from it.

    Two facts, and the second is the one that matters for replay. The adapter
    is discoverable because a distribution declared it — not because the SDK
    knows about it — and the version and distribution on the resolved record
    come from that distribution's own installed metadata. A third-party adapter
    therefore gets its replay pin for free and has no way to misstate it, since
    nothing it declares contributes either value.
    """
    assert ADAPTER in declared_names()

    record = resolve(ADAPTER)

    assert record.registration.name == ADAPTER
    assert record.distribution == DISTRIBUTION
    assert record.version == metadata.version(DISTRIBUTION)
    assert record.version != registry.UNKNOWN_VERSION


def test_discovery_does_not_import_the_distribution_but_resolution_does(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """V6 / D-05, asserted against a distribution that actually exists.

    The registry's own suite proves this with a throwaway module it writes
    itself. This is the same property against the case it exists for: a real
    installed third-party package, whose module-level code would really run.

    The package is evicted from ``sys.modules`` first, because an earlier test
    in the session will have imported it and the assertion would otherwise pass
    for the wrong reason. ``monkeypatch`` puts the original modules back, so no
    later test observes the reimported ones.
    """
    for name in [key for key in sys.modules if key.split(".")[0] == PACKAGE]:
        monkeypatch.delitem(sys.modules, name)
    assert not any(key.split(".")[0] == PACKAGE for key in sys.modules)

    names = declared_names()

    assert ADAPTER in names
    assert not any(key.split(".")[0] == PACKAGE for key in sys.modules), (
        "listing installed adapters imported one of them"
    )

    resolve(ADAPTER)

    assert f"{PACKAGE}.demo_write" in sys.modules


def test_a_fabric_boots_on_the_out_of_tree_adapter_and_answers(
    fabric_boot: Callable[..., "FabricHandle"],
) -> None:
    """The whole path: a real composition root, an L2 write, a query answered.

    Nothing in this test is adapter-aware beyond the name it boots. The claim
    is admitted through the booted worker — never a directly constructed writer
    — so the write semantics under test are the fabric's, exercised through an
    adapter the fabric does not contain.

    The idempotent re-arrival is here rather than in a suite of its own because
    it is the one write outcome that a store can get wrong while still looking
    correct: a second identical claim must add no claim and no lineage.
    """
    handle = fabric_boot(backend=ADAPTER)

    assert isinstance(handle.reader, GraphReader)

    result = handle.worker.admit_entity_claim(tenant_id=TENANT, claim=_entity())
    assert result.claim_created is True
    assert result.lineage_added == 1

    view = handle.reader.query(GraphQuery(tenant_id=TENANT, as_of=T2))
    assert [record.claim.entity_uri for record in view.entities] == [
        "counterparty://acme"
    ]
    assert canonical_bytes(view) == canonical_bytes(
        handle.reader.as_of(tenant_id=TENANT, at=T2)
    )

    again = handle.worker.admit_entity_claim(tenant_id=TENANT, claim=_entity())
    assert again.claim_created is False
    assert again.lineage_added == 0


def test_the_handle_pins_the_out_of_tree_adapter_for_replay(
    fabric_boot: Callable[..., "FabricHandle"],
) -> None:
    """Which adapter answered, at which version, and under which references.

    The pin is what makes a decision replayable once the code behind the graph
    seam can be third-party. All three fields are asserted, and the empty
    ``secret_refs`` is asserted rather than assumed: this adapter declares no
    credential, so a reference name appearing here would mean the pin was
    recording something nobody supplied.
    """
    handle = fabric_boot(backend=ADAPTER)

    assert handle.adapter.name == ADAPTER
    assert handle.adapter.version == metadata.version(DISTRIBUTION)
    assert handle.adapter.version != ""
    assert handle.adapter.secret_refs == ()


def test_two_boots_on_one_graph_name_are_refused(
    demo_boot: Callable[[str], "FabricHandle"],
) -> None:
    """V5: single-writer holds across the out-of-tree boundary.

    The refusal is not something this adapter chose to honour. It comes from
    the SDK's boot-token mint, which refuses a second live writer for one graph
    identity whoever asks — so an adapter installed from outside the repository
    is inside the invariant without having to opt in, and could not opt out.

    The graph name is supplied explicitly here rather than taken from the
    fixture's per-boot default, because the property under test is precisely
    that two boots naming *one* graph collide.
    """
    graph_name = f"ccf_test_{uuid.uuid4().hex}"

    demo_boot(graph_name)

    with pytest.raises(SingleWriterViolation):
        demo_boot(graph_name)


def test_two_boots_on_different_graph_names_both_succeed(
    fabric_boot: Callable[..., "FabricHandle"],
) -> None:
    """The other half of V5, without which the refusal proves nothing.

    A store whose identity collided across genuinely different graphs would
    pass the test above and be badly broken: every second boot would be refused
    for no reason. So distinct names must coexist, and their state must not
    cross.
    """
    first = fabric_boot(backend=ADAPTER)
    second = fabric_boot(backend=ADAPTER)

    first.worker.admit_entity_claim(tenant_id=TENANT, claim=_entity())

    assert first.reader.as_of(tenant_id=TENANT, at=T2).entities != ()
    assert second.reader.as_of(tenant_id=TENANT, at=T2).entities == ()


def test_a_distribution_claiming_a_built_in_name_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-16: a third party cannot answer for a name the SDK ships.

    The impostor is a fake entry point rather than a second real distribution,
    which is the right trade: the behaviour under test is the registry's
    refusal, and a genuinely installed package that claims a built-in name is a
    liability to have in the tree for a fact a fake proves just as well.

    Two things make this stronger than the registry suite's version. The
    built-in name is taken from the real built-in set rather than a synthetic
    one, and the real entry points are kept alongside the impostor — so this
    also shows that a legitimately installed third-party adapter does not
    rescue the deployment. Discovery refuses the whole call, and the refusal
    names the offending distribution so an operator can tell a packaging
    conflict from a missing adapter.
    """
    reserved = sorted(registry._builtin_names())[0]
    impostor = "ccf-impostor-adapter"
    real = tuple(registry._declared_entry_points())
    assert any(point.name == ADAPTER for point in real), (
        "the real out-of-tree declaration should be present alongside the fake"
    )

    monkeypatch.setattr(
        registry,
        "_declared_entry_points",
        lambda: _entry_points(
            *real,
            _entry_point(
                name=reserved,
                value="pkg.impostor:REGISTRATION",
                distribution=impostor,
                version="9.9.9",
            ),
        ),
    )

    with pytest.raises(ReservedBackendName) as caught:
        declared_names()

    message = str(caught.value)
    assert reserved in message
    assert impostor in message


def test_the_sdk_distribution_does_not_depend_on_the_fixture() -> None:
    """The boundedness of the always-on install posture, asserted not asserted.

    Every development checkout and every CI runner has this fixture installed,
    so ``ccf backends list`` reports a seventh name. That cost is accepted, and
    what bounds it is this: the fixture is not a dependency of the ``ccf``
    distribution, so ``pip install ccf`` never pulls it. ``make install`` is the
    developer bootstrap, not an adopter's install path.

    Prose in a README saying so is worth less than a check, because the way
    this would break is somebody adding the fixture to an extra to make a
    workflow simpler — which is exactly the change nobody would think to
    reverse.
    """
    manifest = tomllib.loads(
        (_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    project: dict[str, Any] = manifest["project"]

    requirement_lists = [project.get("dependencies", [])]
    requirement_lists.extend(project.get("optional-dependencies", {}).values())

    offenders = [
        requirement
        for requirements in requirement_lists
        for requirement in requirements
        if DISTRIBUTION in requirement or PACKAGE in requirement
    ]

    assert offenders == [], offenders
    # Non-vacuity: the lists really were read, and really are non-empty.
    assert any(requirement_lists)
