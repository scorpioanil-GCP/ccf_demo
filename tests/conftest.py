"""Shared pytest configuration for the CCF SDK test suite.

The one thing this module exists to guarantee: **tests get a graph handle only
by running the real composition root.** There is no test-only writer, no
in-memory fake store, and no convenience helper that constructs
``ccf.graph._writer`` directly. A test double that could write to L3 would
defeat layer 1 of the D-IMPL-41 stack more thoroughly than any production
mistake, because it would ship as the *example* of how to touch the graph
(04-RESEARCH.md anti-patterns; Pitfall 7).

So :func:`fabric_boot` boots an actual fabric — over a temp SQLite database or
over a throwaway Postgres schema — and everything downstream (the conformance
suite, later operator and projection suites) asks it for a handle.

**Postgres comes from a real server, never a fake** (D-10). In CI the GitHub
Actions service container supplies ``CCF_TEST_POSTGRES_DSN``; locally, if that
variable is unset, :func:`postgres_dsn` starts a ``postgres:16`` container
through testcontainers. Both paths run the identical suite, which is the point
— a mocked Postgres would assert that our idea of Postgres is self-consistent.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from ccf.boot import FabricHandle
    from ccf.skills.callables import CallableRegistry

# Control Plane keys used by the test fabric. They live here, in test code,
# rather than in `/src`: key names are deployment vocabulary, and the SDK
# enumerating them would be exactly the hardcoding CINV-01 forbids.
RESOLUTION_SPEC_KEY = "test/entity-resolution-spec"
POLICY_BUNDLE_KEY = "test/policy-bundle"


def _resolution_spec() -> Any:
    """The fixture ontology mapping: source payload vocabulary -> E and R.

    A deliberately multi-type, banking-shaped spec (D-02's realism bar): two
    entity classes correlated on different native identifiers, plus a typed
    edge between them. Everything here is *values* and therefore lives in test
    fixtures, never in `/src`.
    """
    from ccf.assembly.worker import (
        EntityResolutionRule,
        EntityResolutionSpec,
        RelationshipResolutionRule,
    )

    return EntityResolutionSpec(
        semver="1.0.0",
        entity_rules=(
            EntityResolutionRule(
                match_key="counterparty_lei",
                entity_class="counterparty",
                identity_keys=("counterparty_lei",),
                attribute_keys=("counterparty_name", "jurisdiction"),
            ),
            EntityResolutionRule(
                match_key="facility_id",
                entity_class="facility",
                identity_keys=("facility_id",),
                attribute_keys=("facility_type", "currency"),
            ),
        ),
        relationship_rules=(
            RelationshipResolutionRule(
                relationship_type="obligor_of",
                subject_entity_class="counterparty",
                object_entity_class="facility",
            ),
        ),
    )


def _policy_bundle() -> dict[str, str]:
    """A minimal stand-in policy bundle artifact for the slice.

    Its *content* is irrelevant to this plan — what matters is that a version
    of it is resolved from the Control Plane and stamped onto every claim, so
    the policy-binding stage is exercised rather than stubbed. The real bundle
    schema arrives with the policy subsystem plan.
    """
    return {"regime": "test-fixture"}


@pytest.fixture
def banking_spec() -> Any:
    """The fixture resolution spec, for tests that boot a fabric by hand."""
    return _resolution_spec()


#: Set by the CI job (GitHub Actions Postgres service container). When unset,
#: the local testcontainers path takes over — same DSN shape, same suite.
POSTGRES_DSN_ENV = "CCF_TEST_POSTGRES_DSN"

#: Set in CI. Turns "no Postgres available" from a skip into a failure — a
#: postgres leg that quietly skips is a green build that proved nothing, which
#: is the failure mode a marker-selected job is most exposed to.
POSTGRES_REQUIRED_ENV = "CCF_REQUIRE_POSTGRES"


def _unavailable(reason: str) -> None:
    """Skip, or fail if this environment declared Postgres mandatory."""
    if os.environ.get(POSTGRES_REQUIRED_ENV):
        pytest.fail(f"{POSTGRES_REQUIRED_ENV} is set but Postgres is unusable: {reason}")
    pytest.skip(reason)


#: Set in CI. Turns "this harness SDK is not installed" from a skip into a
#: failure, for exactly the reason ``CCF_REQUIRE_POSTGRES`` exists: a harness
#: leg that quietly skips is a green build that proved nothing, and the harness
#: legs are the *only* evidence for the CLAUDE.md §7.3 portability claim. CI
#: installs `[dev]`, which composes `[harnesses]`, so all three legs run there
#: whether or not anyone remembers to look at `-rs` output.
HARNESS_REQUIRED_ENV = "CCF_REQUIRE_HARNESSES"

#: Which extra installs which harness SDK. The message a contributor without
#: the extra reads has to be an instruction, not a mystery, so the skip names
#: both the missing module and the command that fixes it.
HARNESS_EXTRAS: dict[str, str] = {
    "claude_agent_sdk": "claude-agent",
    "langgraph": "langgraph",
    "google.adk": "adk",
}


def harness_unavailable(module_name: str, leg: str) -> None:
    """Skip this harness leg, or fail if the environment declared it mandatory.

    The harness counterpart of :func:`_unavailable`, deliberately the same
    shape rather than a second skip idiom: two mechanisms for "the environment
    can require what would otherwise silently skip" would drift, and the
    reader would have to learn both.

    Args:
        module_name: The harness SDK's importable top-level module.
        leg: The conformance param this guards, named in the message so
            ``pytest -rs`` says which leg did not run.
    """
    import importlib.util

    if importlib.util.find_spec(module_name.split(".")[0]) is not None:
        return
    extra = HARNESS_EXTRAS.get(module_name, leg)
    reason = (
        f"harness leg {leg!r} needs {module_name!r}; install it with"
        f' `pip install -e ".[{extra}]"` (or `.[harnesses]` for all three)'
    )
    if os.environ.get(HARNESS_REQUIRED_ENV):
        pytest.fail(f"{HARNESS_REQUIRED_ENV} is set but {reason}")
    pytest.skip(reason)


@pytest.fixture(scope="session")
def postgres_dsn() -> Iterator[str]:
    """A DSN for a real Postgres, from CI's service container or testcontainers.

    Session-scoped because container startup is the expensive part; test
    isolation comes from a fresh *schema* per fabric, not a fresh server.

    Skips when neither is available, so a contributor without Docker still gets
    a meaningful run of everything else — unless ``CCF_REQUIRE_POSTGRES`` says
    this environment must have one, in which case it fails. A silently-green
    postgres leg would be worse than a red one.
    """
    dsn = os.environ.get(POSTGRES_DSN_ENV)
    if dsn:
        yield dsn
        return

    try:
        from testcontainers.community.postgres import PostgresContainer
    except ImportError as exc:  # pragma: no cover - depends on the environment
        _unavailable(f"testcontainers unavailable and {POSTGRES_DSN_ENV} unset: {exc}")

    try:
        container = PostgresContainer("postgres:16", driver=None)
        container.start()
    except Exception as exc:  # pragma: no cover - depends on the environment
        _unavailable(
            f"cannot start a Postgres container (Docker unavailable?) and "
            f"{POSTGRES_DSN_ENV} is unset: {exc}"
        )
    try:
        yield str(container.get_connection_url())
    finally:
        container.stop()


@pytest.fixture
def fabric_boot(
    tmp_path: Path, request: pytest.FixtureRequest
) -> Iterator[Callable[..., "FabricHandle"]]:
    """Yield a factory that boots a fresh fabric over its own graph.

    Returns a *factory* rather than a handle so a test can boot twice and
    assert what happens (the single-writer boot check needs exactly that).
    Every handle is closed on teardown.

    ``backend="postgres"`` boots against the session Postgres in a schema
    unique to this boot, which is what makes "a fresh graph per test" true on a
    shared server exactly as a temp file makes it true on SQLite. The Postgres
    DSN is resolved lazily, so the SQLite path never touches Docker.
    """
    from ccf.boot import boot
    from ccf.controlplane.registry import ControlPlaneRegistry

    handles: list[FabricHandle] = []
    counter = {"n": 0}

    def factory(
        *, database_path: Path | None = None, backend: str = "sqlite"
    ) -> "FabricHandle":
        counter["n"] += 1
        registry = ControlPlaneRegistry()
        spec_version = registry.register(RESOLUTION_SPEC_KEY, _resolution_spec())
        policy_version = registry.register(POLICY_BUNDLE_KEY, _policy_bundle())
        location: dict[str, Any]
        if backend == "postgres":
            location = {
                "postgres_dsn": request.getfixturevalue("postgres_dsn"),
                "postgres_schema": f"ccf_test_{uuid.uuid4().hex}",
            }
        elif backend == "sqlite":
            location = {
                "database_path": database_path
                or tmp_path / f"fabric-{counter['n']}.sqlite3"
            }
        elif backend == "memory":
            # Phase 15.2 D-06: the zero-dependency in-memory backend. Every
            # boot is its own graph (per-instance synthetic identity), so
            # isolation needs no temp file and no schema.
            location = {"memory": True}
        else:
            raise NotImplementedError(backend)
        handle = boot(
            registry=registry,
            resolution_spec_key=RESOLUTION_SPEC_KEY,
            resolution_spec_version=spec_version,
            policy_bundle_key=POLICY_BUNDLE_KEY,
            policy_bundle_version=policy_version,
            **location,
        )
        handles.append(handle)
        return handle

    try:
        yield factory
    finally:
        for handle in reversed(handles):
            handle.close()


@pytest.fixture
def fabric(fabric_boot: Callable[..., "FabricHandle"]) -> "FabricHandle":
    """A single booted fabric — the common case."""
    return fabric_boot()


@pytest.fixture
def callable_registry() -> "CallableRegistry":
    """The test deployment's composition root for local callables (D-19).

    One explicit ``register(key, fn)`` call, exactly as a real deployment's
    composition root would make it: no decorator, no entry point, no import
    side effect. The key is a fixture *value* (it lives in the skills YAML
    beside the catalog entry that declares it as ``callable_ref``); the
    function is a fixture callable. This module supplies neither — it only
    performs the binding, which is the mechanism under test.

    A registry constructed per test, never module-level: two tests, like two
    deployments, must not be able to see each other's registrations.
    """
    from ccf.skills.callables import CallableRegistry

    from fixtures.banking.skills.callables import covenant_metrics

    registry = CallableRegistry()
    registry.register(_skills_callable_values()["registered_key"], covenant_metrics)
    return registry


def _skills_callable_values() -> dict[str, Any]:
    """The D-19 drive values, read from the skills fixture that owns them."""
    import yaml

    document: dict[str, Any] = yaml.safe_load(
        (
            Path(__file__).resolve().parent
            / "fixtures"
            / "banking"
            / "skills"
            / "covenant_metrics_tool.yaml"
        ).read_text()
    )
    values: dict[str, Any] = document["callables"]
    return values
