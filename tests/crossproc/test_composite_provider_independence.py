"""`INT-01b` — the atomic provider moves; the composite does not change.

`D-IMPL-336` **Amendment 5 §5**. Dave: *"The demonstration must also show an
independently registered atomic product serving another consumer and the
composite. Change its acquisition binding from in-process to a supported
remote route without changing the composite's requirements or roll-up
logic."*

**The shape of the proof.** One atomic Context Product, produced by
``tests.products.provider_boot`` — the same module both sides use, so the two
answers cannot drift. It is reached two ways:

* **In-process**, by a `local_callable` grant, in
  ``tests/products/test_composite_integration.py``.
* **Over MCP**, from a child process with **its own boot, its own SQLite
  database and its own artifact store**, here.

Between the two runs the composite's `requires` declaration, its four
composition laws and its roll-up are **byte-identical** — only the granted
skill's binding differs. That is the claim *"a complex context product can be
made up of several other context products… it does not have to be responsible
for assembling the atomic context products"* stated as something a test can
fail.

**And a second consumer reads the same resource directly**, knowing nothing
about composition — CLAUDE.md §9's client posture: *"the client knows nothing
about the CCF SDK except for the format of the context product they are
consuming."*
"""

from __future__ import annotations

import pathlib
from collections.abc import Iterator
from typing import Any

import pytest

from ccf.contracts.canonical import content_hash
from ccf.mcp.client import McpResourceClient, SyncMcpBridge
from ccf.products.contract import ContextProductContract
from ccf.products.door import DoorOutcome
from ccf.replay.record import DecisionReplayRecord
from ccf.replay.serve import ServedProduct
from ccf.skills.dispatch import McpSkillRegistry

from tests.crossproc.servers.mcp_atomic_product_child import (
    RESOURCE_URI,
    SERVER_NAME,
)

CHILD = str(
    pathlib.Path(__file__).resolve().parent / "servers" / "mcp_atomic_product_child.py"
)
CALL_TIMEOUT_SECONDS = 30.0
RESOURCE_NAME = "atomic-product"


@pytest.fixture
def bridge() -> Iterator[SyncMcpBridge]:
    """One bounded sync bridge per test, closed on teardown."""
    with SyncMcpBridge(call_timeout_seconds=CALL_TIMEOUT_SECONDS) as bridge:
        yield bridge


@pytest.mark.parametrize("child_server_port", [CHILD], indirect=True)
def test_a_second_consumer_reads_the_SAME_product_knowing_nothing_of_composition(
    loopback_url: str, bridge: SyncMcpBridge
) -> None:
    """The atomic product serves another consumer, on its own terms.

    This consumer holds no composite, declares no `requires`, and knows only
    the wire format. It is the half of Dave's instruction that makes the
    product *independently registered* rather than *a composite's private
    input*.
    """
    client = McpResourceClient(url=loopback_url, bridge=bridge)
    answer = DoorOutcome.model_validate_json(client.read_text(RESOURCE_URI))

    assert answer.product_json is not None, answer.refusal
    product = ContextProductContract.model_validate_json(answer.product_json)
    assert product.schema_name == "fixture.child-product"
    # The producer's own hash of its own bytes — the consumer checks it rather
    # than taking the reported value on faith.
    assert content_hash(product) == answer.content_address


@pytest.mark.parametrize("child_server_port", [CHILD], indirect=True)
def test_int01b_the_composite_is_UNCHANGED_when_the_provider_goes_remote(
    loopback_url: str, bridge: SyncMcpBridge, tmp_path: pathlib.Path
) -> None:
    """The load-bearing test: rebind acquisition, change nothing else.

    The composite's product class, its `requires`, its resolver wiring and its
    roll-up are the integration proof's. The ONLY difference is that the
    granted skill's binding is `mcp` rather than `local_callable`, and the
    product is produced in another process over another database.

    **What is asserted is that the composite could not tell.** The served
    lineage still carries the child's operator, the child's row is still
    written, and the debt roll-up still ran — against a provider whose
    assembler, credentials, store and boot context this process never saw.
    """
    from tests.products.composite_fixture import (
        ask_composite,
        boot_composite,
        build_composite,
    )
    from tests.products.test_resolver_seam import ADMITTED_AT

    # Held open explicitly: `boot_composite` is a generator whose `finally`
    # closes the fabric, and abandoning it after one `next` closes the graph
    # under the test — measured as "Cannot operate on a closed database".
    deployment = boot_composite(tmp_path)
    booted = next(deployment)

    mcp_skills = McpSkillRegistry(
        audit_log=booted.control_plane.audit_log, clock=lambda: ADMITTED_AT
    )
    mcp_skills.register(
        server=SERVER_NAME,
        client=McpResourceClient(url=loopback_url, bridge=bridge),
        resources={RESOURCE_NAME: RESOURCE_URI},
    )

    # The ONE argument that differs from the in-process proof.
    resolver, _children = build_composite(
        booted, binding="mcp", mcp_skills=mcp_skills, resource=RESOURCE_NAME
    )
    outcome = ask_composite(resolver)
    assert isinstance(outcome, ServedProduct), getattr(outcome, "detail", outcome)

    # `R4`: the union still includes the REMOTE child's operator.
    operators = outcome.product.lineage.operators_invoked
    assert "similarity.corpus-select" in operators
    assert "traversal.typed-neighborhood" in operators

    record = DecisionReplayRecord.model_validate_json(
        booted.store.get(
            content_address=booted.store.resolve_uri(uri=outcome.replay_ref.uri)
        )
    )
    rows = record.content_generation_path.child_resolutions
    assert len(rows) == 1
    row = rows[0]
    assert row.outcome_status == "admitted"
    assert row.required_product_class == "fixture.child-product"
    # `D-IMPL-59` and Amendment 5: the provider's OWN controls governed the
    # read. This fabric holds no execution record for a remote child, does not
    # consult its own invalidation register, and SAYS SO rather than leaving a
    # reader to infer a local pass.
    assert row.eligibility_basis == "provider-controls"
    assert row.producing_fabric is None
    # `R5`: the remote child's operators and expiry still reach the record, so
    # the composite stays reconstructible across the boundary.
    assert row.child_operators_invoked == frozenset({"similarity.corpus-select"})
    assert row.child_expires_at is not None
    deployment.close()
