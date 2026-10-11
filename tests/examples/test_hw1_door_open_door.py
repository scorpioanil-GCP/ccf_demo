# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""HW-1's MCP door starts and answers through the SDK's standard door, ``open_door``.

CI ruling C2 (a), Dave, 2026-10-08: *"rebuild hw1's MCP door on the SDK's
public ``open_door``"*. Before the rebuild, ``server/compose.py`` was a hand
copy of the SDK's composition, and four deliberate security changes stopped it
one layer at a time: the store's declared write kinds (``D-IMPL-353`` §1.2), the
keys placed under the tenant (``D-IMPL-354``), capability-gated registration
(``D-IMPL-353`` §1.1) and the egress builder's required authorizer. The door
child crashed before it served anything, so every harness leg reaching it saw a
closed connection.

What is asserted
----------------
The door is spawned exactly the way a client spawns it (the interpreter, the
program ``binding.yaml``'s ``server:`` names, the deployment root) in the plain
environment a client gives it. Neither advertised address is set: under ruling
C2-A (b) (``D-IMPL-378``) the SDK's stdio transport supplies its own, so a
client that knows nothing about the door's environment can start it. Then:

1. **it starts, and lists exactly one tool**, the product request tool;
2. **one question, asked through the SDK's own ``mcp+stdio`` client, comes back
   as the governed decision the in-process transport makes** for the same
   question, recorded under this deployment's replay record class. A call the
   door's authorizer denies under its scope mapping reaches a client as a tool
   error, never as an outcome, so this is the check that exercises the scope
   mapping the ``D-IMPL-353`` ledger expects of a migrated door;
3. **the outcome asserts the producer identity ``egress-door.yaml`` declares**
   (``D-IMPL-340`` ruling 2), which the standard door puts on every outcome it
   emits.

Why the decision is compared rather than named
----------------------------------------------
Without ruling C1's declarations this deployment refused every question
``temporal-boundary-undeclared`` over both transports; with the declared
boundary and serve instant (the ``D-IMPL-378`` C3 example set) both transports
serve. This module's subject is the door, so it asks that the door makes the
decision the in-process transport makes (the same kind and reason when refused,
the same content address when served) and holds no opinion on which one that is.

The subject is the unseeded copy :mod:`tests.examples.test_hw1_two_transports`
builds, and the question is the documented command's own, read by
:mod:`tests.examples.test_hw1_empty_fabric_refusal`'s helpers, so this module
asks what the other hw1 modules ask.
"""

from __future__ import annotations

import asyncio
import os
import pathlib
import sys
import tempfile
from typing import TextIO

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from ccf.client.adapters.binding_document import load_binding_document
from ccf.client.adapters.inprocess import InProcessAdapter, reset_boot_cache
from ccf.client.adapters.mcp_stdio import McpStdioAdapter
from ccf.client.codec import DecodedOutcome, decode_outcome
from ccf.client.wire import WireRequest
from ccf.controlplane.artifacts import EGRESS_DOOR, EgressDoorBinding, load_artifact
from ccf.products.door import PRODUCT_REQUEST_TOOL, ProducerAssertion

from tests.examples.test_hw1_empty_fabric_refusal import (
    deployment_document,
    documented_question,
)
from tests.examples.test_hw1_two_transports import (
    example,  # noqa: F401 — the UNSEEDED copy fixture, re-exported for pytest
)

#: The door's two documents, beside its program.
DOOR_DOCUMENT = "egress-door.yaml"

def door_program(root: pathlib.Path) -> pathlib.Path:
    """The program the deployment at ``root`` declares, by its own ``binding.yaml``."""
    program = load_binding_document(root).server
    assert program is not None, f"{root}'s binding.yaml declares no server program"
    return program


async def listed_tools(program: pathlib.Path, root: pathlib.Path, errlog: TextIO) -> list[str]:
    """Spawn the door as a client does, initialize, and return the tools it lists."""
    parameters = StdioServerParameters(
        command=sys.executable,
        args=[str(program), str(root)],
        env=dict(os.environ),
    )
    async with stdio_client(parameters, errlog=errlog) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listed = await session.list_tools()
    return [tool.name for tool in listed.tools]


def stderr_tail(errlog: TextIO, *, lines: int = 12) -> str:
    """The last lines the door child wrote to stderr, for a failure message."""
    errlog.seek(0)
    written = [line for line in errlog.read().splitlines() if line.strip()]
    return "\n".join(written[-lines:])


def the_question(example: pathlib.Path) -> WireRequest:
    """The documented command's question, as a client puts it on the wire."""
    parameters, as_of = documented_question(example)
    product_class = deployment_document(example, "ccf_config.yaml")["product_class"]
    assert isinstance(product_class, dict)
    return WireRequest(
        product_id=str(product_class["schema_name"]),
        parameters=parameters,
        temporal_boundary=as_of,
    )


def ask_in_process(root: pathlib.Path, request: WireRequest) -> DecodedOutcome:
    """The same question in this process, released afterwards.

    Asked after the door children have exited, and released in a ``finally``,
    because a booted graph keeps its single writer until it is closed.
    """
    try:
        return decode_outcome(InProcessAdapter(str(root)).ask(request), sent=request)
    finally:
        reset_boot_cache()


def test_the_door_starts_and_answers_through_the_standard_door(
    example: pathlib.Path,
) -> None:
    """C2 (a) and C2-A (b). Spawned as a client spawns it, the door lists its tool and answers."""
    root = example / "deployment"
    program = door_program(root)

    with tempfile.TemporaryFile(mode="w+") as errlog:
        try:
            tools = asyncio.run(listed_tools(program, root, errlog))
        except Exception as unreachable:
            raise AssertionError(
                f"the door at {program.name} did not start and list its tools:"
                f" {type(unreachable).__name__}: {unreachable}\n"
                f"--- the door's stderr ---\n{stderr_tail(errlog)}"
            ) from unreachable
    assert tools == [PRODUCT_REQUEST_TOOL], (
        f"the door lists {tools}; the standard door over a parameterized class"
        f" exposes exactly `{PRODUCT_REQUEST_TOOL}`"
    )

    request = the_question(example)
    over_the_door = decode_outcome(McpStdioAdapter(str(root)).ask(request), sent=request)

    binding = load_artifact(
        (program.parent / DOOR_DOCUMENT).read_text(encoding="utf-8"), EGRESS_DOOR
    )
    assert isinstance(binding, EgressDoorBinding)
    assert over_the_door.outcome.producer == ProducerAssertion(
        producer_id=binding.producer_id, tenant_id=binding.producer_tenant
    ), (
        "the door's outcome does not assert the identity"
        f" {DOOR_DOCUMENT} declares: {over_the_door.outcome.producer}"
    )
    config = deployment_document(example, "ccf_config.yaml")
    assert binding.producer_tenant == config["tenant_id"], (
        f"{DOOR_DOCUMENT} asserts tenant {binding.producer_tenant!r} for a"
        f" deployment that boots as {config['tenant_id']!r} (D-IMPL-343 R-6)"
    )

    replay_record_class = load_binding_document(root).replay_record_class
    recorded_under = f"ccf-artifact://{binding.producer_tenant}/{replay_record_class}/"
    in_process = ask_in_process(root, request)
    door_refusal = over_the_door.outcome.refusal
    in_process_refusal = in_process.outcome.refusal
    if in_process_refusal is not None:
        assert door_refusal is not None, (
            "the in-process transport refused this question"
            f" ({in_process_refusal.reason}) and the door served it"
        )
        assert (door_refusal.kind, door_refusal.reason) == (
            in_process_refusal.kind,
            in_process_refusal.reason,
        ), (
            f"the door refused {door_refusal.kind}/{door_refusal.reason} where"
            f" the in-process transport refused"
            f" {in_process_refusal.kind}/{in_process_refusal.reason}"
        )
        assert str(door_refusal.replay_reference).startswith(recorded_under), (
            "the door's refusal is not recorded under this deployment's replay"
            f" record class: {door_refusal.replay_reference}"
        )
    else:
        assert door_refusal is None, (
            "the in-process transport served this question and the door refused"
            f" it: {door_refusal}"
        )
        assert over_the_door.outcome.content_address == in_process.outcome.content_address, (
            "the two transports served different products for one question"
        )
        assert str(over_the_door.outcome.replay_ref).startswith(recorded_under), (
            "the door's answer is not recorded under this deployment's replay"
            f" record class: {over_the_door.outcome.replay_ref}"
        )
