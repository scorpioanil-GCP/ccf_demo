"""The adapter leg of ROADMAP criterion 4: L2 remains the only writer to L3.

CLAUDE.md §7.3 seam 3 ("a harness never acquires a write handle to the graph;
the single-writer invariant holds across the adapter boundary") and §10 ("the
single-writer invariant is architectural, not advisory"). Research's criterion-4
table names three observables for this boundary, and this module is those three
— run for **all three** D-IMPL-24 harnesses, so the claim is not proven for one
adapter and assumed for the other two.

**What these tests enforce, exactly (D-21).** Three things, each narrow:

(a) With a real fabric booted, driving a real effect through each harness's
    effect-capture seam leaves the L3 substrate byte-identical, and the same
    effect's payload changes the substrate once it is handed to ``worker.ingest``
    — where the entities that then appear are the ones L2 resolved under the
    fabric's own resolution spec.
(b) Every module file shipped under ``runtime/ccf_runtime/adapters`` is scanned
    two ways: no *identifier* in its source names a fabric write surface, and no
    constructed adapter holds an attribute, public or private, whose type is
    one.
(c) No adapter's constructor signature accepts a fabric object, and no adapter
    instance exposes one as an attribute. The Protocol already gives every seam
    method its fabric-side input as :class:`~ccf.agents.agent.Agent`; this
    checks that nothing arrived by the other door.

**What they do not enforce.** (b) is an identifier scan over the module files
this repository ships plus an attribute check on three constructed instances. It
says nothing about code reachable transitively, nothing about an adapter a
deployment writes itself, and nothing about attributes obtained dynamically. (a)
is an observation of one effect under one deployment's configuration, not a
statement over all inputs. (c) reads declared signatures and instance state, and
a value smuggled through a mutable default or a late ``setattr`` would be seen by
the attribute half only if it were still attached when the scan ran. These are
the strengths the assertions actually reach; the I.2 retrospective flagged
overclaiming here specifically, and 06-16's gate rows are drafted from these
tests rather than from plan intent.

These tests *add to* ``tests/invariants/test_single_writer_boot.py``, the CINV-02
``cinv02-graph-writer`` lint rule, and the A2A and ArtifactStore legs. None is
replaced, and all must stay green alongside this module — together they are the
three boundaries criterion 4 names.

**D-22 note.** ``ALLOWED_CCF_PREFIXES`` in
``tests/agents/test_consumption_discipline.py`` is deliberately untouched. It is
a direct-import allowlist over ``src/ccf/agents`` and it does not scan
``ccf_runtime.adapters`` at all, which is precisely why the adapters needed no
widening: an adapter is not in the agents package. Research Pitfall 7 is explicit
that a plan reaching for that allowlist has almost certainly put an adapter seam
inside ``/src/ccf/agents`` by mistake. ``WRITE_SURFACE_NAMES`` below is
*imported* from that module rather than re-listed, so the two checks cannot
drift.
"""

from __future__ import annotations

import ast
import inspect
import re
from pathlib import Path
from typing import Any

import pytest
import yaml

from ccf.agents.agent import EmittedEffect
from ccf.signal.envelope import SignalEnvelope, SourceIdentity

from agents.test_consumption_discipline import WRITE_SURFACE_NAMES
from conformance.test_harness_adapter import (  # noqa: F401 — re-registered fixture
    BOUNDARY,
    World,
    harness_leg,
    substrate_digest,
    world,
)
from conformance.test_harness_adapter import HarnessLeg

pytestmark = [pytest.mark.harness]

#: Every adapter module file this repository ships. Scanned as **source**
#: rather than as imported modules on purpose: importing them all would require
#: every harness extra to be installed, so a deployment with one extra would
#: silently scan a subset — and the module that dropped out of the scan is
#: exactly the one that would carry the violation.
ADAPTERS_PACKAGE = Path("runtime/ccf_runtime/adapters")
ADAPTER_SOURCES = sorted(ADAPTERS_PACKAGE.rglob("*.py"))

#: The fabric-side objects no adapter may take or hold. Broader than
#: ``WRITE_SURFACE_NAMES``, which is about *write* surfaces specifically: (c) is
#: the stronger claim that the adapter's fabric-side input is ``Agent`` and
#: nothing else, so a read handle and a Control Plane registry are equally out.
FABRIC_INPUT_NAMES = frozenset(
    {
        "AssemblyWorker",
        "ControlPlaneProtocol",
        "ControlPlaneRegistry",
        "FabricHandle",
        "GraphReader",
        "GraphStore",
        "GraphWriter",
    }
)

#: What no adapter constructor may name. :data:`FABRIC_INPUT_NAMES` plus
#: ``Agent`` itself: the Protocol hands the bound agent to every seam *per
#: call*, so an adapter that also took one at construction would have two
#: answers to "whose skills are these" and a cache that could outlive a
#: revocation (D-23). Only the constructor is held to this — the seam methods
#: take ``Agent`` because that is the contract.
CONSTRUCTOR_DENIED_NAMES = FABRIC_INPUT_NAMES | {"Agent"}

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "banking"


def _effect_payload() -> dict[str, Any]:
    """A source system's own payload vocabulary, from the event fixture.

    Deliberately a fixture value rather than a literal composed here: L2 has to
    actually resolve it for (a) to observe anything, and a payload this module
    authored would be this module agreeing with itself about what the
    deployment's ontology says.
    """
    stream: dict[str, Any] = yaml.safe_load((FIXTURES / "events.yaml").read_text())
    payload: dict[str, Any] = stream["envelopes"][0]["payload"]
    return payload


def _identifiers(source: str) -> set[str]:
    """Every name and attribute identifier appearing in ``source``.

    Identifiers, never source text. A text scan cannot tell a violation from a
    docstring that documents compliance — an adapter stating "this holds no
    graph write handle" would fail a grep for the type's name while being
    exactly correct. String constants are not identifiers, so they are outside
    this set and cannot trip it, and a genuine use of the type *is* an
    identifier and cannot escape it.

    The same rule the A2A leg applies, restated over a file rather than an
    imported module for the reason :data:`ADAPTER_SOURCES` gives.
    """
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.alias):
            names.add(node.asname or node.name.rsplit(".", 1)[-1])
    return names


def _annotation_names(annotation: object) -> set[str]:
    """The bare type names an annotation mentions, as whole tokens.

    Whole tokens rather than substrings: ``"Agent" in "agent_name"`` is false
    but ``"Agent" in "AgentDefinition"`` is true, and a substring test would
    make this assertion depend on how a future type happens to be spelled. The
    annotation may be a string (``from __future__ import annotations`` is in
    force in every adapter), so it is read as text and split on non-identifier
    characters rather than resolved.
    """
    return set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", str(annotation)))


def _held(adapter: object) -> dict[str, Any]:
    """Every value an adapter instance holds, public and private.

    Both, because a source scan of a class body cannot see what a constructor
    assigned, and an object holding a writer under a leading underscore would
    hold one all the same.
    """
    return {
        **vars(adapter),
        **{
            name: getattr(adapter, name, None)
            for name in dir(adapter)
            if not name.startswith("__")
        },
    }


# --- the scan is only worth anything if it scanned something ------------------


def test_the_adapter_sources_were_actually_discovered() -> None:
    """A discovery helper that silently returned nothing is the quietest way an
    invariant test stops being one — every parametrized assertion below would
    become vacuously true while staying green."""
    assert len(ADAPTER_SOURCES) >= 7
    found = {path.parent.name for path in ADAPTER_SOURCES}
    assert {"adk", "claude_agent", "langgraph"} <= found


# --- (b) no adapter module holds or names a write surface ---------------------


@pytest.mark.parametrize(
    "source_path", ADAPTER_SOURCES, ids=lambda p: f"{p.parent.name}/{p.name}"
)
def test_no_adapter_module_names_a_fabric_write_surface(source_path: Path) -> None:
    """The same names ``test_consumption_discipline.py`` holds Agent to.

    What would fail here: an adapter declaring a ``GraphWriter``-typed
    parameter, attribute annotation, or local — a write surface can be named
    without being imported by name, and an import scan alone would miss it.
    """
    named = _identifiers(source_path.read_text()) & WRITE_SURFACE_NAMES
    assert not named, f"{source_path} names {sorted(named)}"


def test_no_constructed_adapter_holds_a_fabric_write_surface(
    harness_leg: HarnessLeg,  # noqa: F811 — the re-registered fixture
) -> None:
    """The runtime counterpart of the source scan, on the object itself.

    What would fail here: an adapter that accepted a writer at construction and
    stashed it — invisible to a scan of the class body, and the form this
    violation would most plausibly take.
    """
    for name, member in _held(harness_leg.adapter("governed")).items():
        assert type(member).__name__ not in WRITE_SURFACE_NAMES, (
            f"{harness_leg.harness_id} adapter holds a fabric write surface"
            f" under {name!r} (CLAUDE.md §10, §7.3 seam 3)"
        )


# --- (c) the adapter's fabric-side input is Agent and nothing else -------------


def test_no_adapter_constructor_accepts_a_fabric_object(
    harness_leg: HarnessLeg,  # noqa: F811 — the re-registered fixture
) -> None:
    """Deployment configuration in, fabric objects never.

    The Protocol hands every seam its fabric-side input as ``Agent``, per call.
    An adapter that also took one at construction would have a second answer to
    "whose agent is this"; an adapter that took a reader or a registry would
    have reached past ``Agent`` entirely. What would fail here: either.
    """
    adapter = harness_leg.adapter("governed")
    signature = inspect.signature(type(adapter).__init__)
    for name, parameter in signature.parameters.items():
        if name == "self":
            continue
        named = _annotation_names(parameter.annotation) & CONSTRUCTOR_DENIED_NAMES
        assert not named, (
            f"{harness_leg.harness_id} adapter's constructor takes {name!r}"
            f" annotated {parameter.annotation!r}, which names {sorted(named)}"
        )


def test_no_adapter_instance_exposes_a_fabric_object(
    harness_leg: HarnessLeg,  # noqa: F811 — the re-registered fixture
) -> None:
    """The stronger form of (b): not merely no *writer*, no fabric object.

    What would fail here: an adapter holding a graph reader or a Control Plane
    registry — neither is a write surface, and both would be a route past the
    consumption boundary ``Agent`` exists to be.
    """
    for name, member in _held(harness_leg.adapter("governed")).items():
        assert type(member).__name__ not in FABRIC_INPUT_NAMES, (
            f"{harness_leg.harness_id} adapter exposes a fabric object under"
            f" {name!r} (CLAUDE.md §7.3)"
        )


# --- (a) effects reach L3 only through emit_effect into L2 --------------------


def test_an_effect_reaches_l3_only_through_emit_effect_into_l2(
    harness_leg: HarnessLeg,  # noqa: F811 — the re-registered fixture
    world: World,  # noqa: F811 — the re-registered fixture
    fabric_boot: Any,
    tmp_path: Path,
) -> None:
    """Criterion 4, the adapter row: the seam yields a value, L2 does the write.

    Two halves, and both are needed. The first is that capturing a real effect
    through the harness seam moves nothing: the substrate is byte-identical
    afterwards, write-ahead log included, so the adapter had no route of its
    own. The second is that the effect's payload *does* change the substrate
    once it is handed to ``worker.ingest`` — because a test that only observed
    "nothing happened" would pass equally well against a fabric that could not
    be written at all, which is a green result that proves nothing.

    What would fail here: an adapter that reached L3 during capture. The
    entities that appear afterwards carry the entity class the fabric's own
    resolution spec declares, so a claim that arrived any other way would not
    look like this.
    """
    database_path = tmp_path / "adapter-single-writer.sqlite3"
    handle = fabric_boot(database_path=database_path)
    before = substrate_digest(database_path)

    payload = _effect_payload()
    effect = harness_leg.adapter("governed").capture_effect(
        agent=world.agent_a, output=payload
    )
    assert isinstance(effect, EmittedEffect)
    assert effect.agent_definition_hash == world.agent_a.identity.definition_hash
    assert substrate_digest(database_path) == before, (
        f"the {harness_leg.harness_id} effect seam changed the L3 substrate;"
        " emission is a returned value and carrying it in is L2's job"
        " (CLAUDE.md §10, §7.3 seam 3)"
    )

    tenant = world.definition_a.tenant
    handle.worker.ingest(
        SignalEnvelope(
            tenant_id=tenant,
            envelope_id=f"{harness_leg.harness_id}/{effect.agent_definition_hash}",
            source=SourceIdentity(system_id=harness_leg.harness_id),
            ingestion_timestamp=BOUNDARY,
            observed_time=BOUNDARY,
            raw_payload=dict(effect.payload),
        )
    )
    after = substrate_digest(database_path)
    assert after != before

    view = handle.reader.as_of(tenant_id=tenant, at=BOUNDARY)
    resolved = {record.claim.entity_class for record in view.entities}
    assert resolved, "L2 resolved nothing, so the mutation above is unattributed"


# --- D-22, asserted rather than promised --------------------------------------


def test_the_consumption_discipline_allowlist_is_untouched() -> None:
    """The allowlist is not widened, and this states why it need not be.

    ``test_consumption_discipline.py`` scans ``src/ccf/agents`` only. Adapters
    live in ``ccf_runtime.adapters``, which that module never reads, so nothing
    this plan added could have required an entry. What would fail here: someone
    placing adapter code inside the agents package and widening the allowlist to
    make it pass — research Pitfall 7's exact scenario.
    """
    from agents import test_consumption_discipline as discipline  # noqa: PLC0415

    assert not any(
        prefix.startswith("ccf_runtime")
        for prefix in discipline.ALLOWED_CCF_PREFIXES
    )
    assert str(discipline.AGENTS_PACKAGE) == "src/ccf/agents"
