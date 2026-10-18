# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""The action door's receipt reports the request for the pause the verdict names (D-IMPL-391).

Found by the read-only review of ``4be75f02`` (advisory). Since Dave's ruling of
2026-10-17 18:54 MST the transport judges a verdict against the request for the
pause it names, so a verdict naming a pause whose request is not waiting is
recorded ``missing`` and is never authority. The receipt's ``event_pending``
still answered "any request under the key": with only another pause's request
waiting, one 200 receipt said ``event_state_at_submit: missing`` and
``event_pending: true``, telling the approver their request was waiting for an
approval that can never count. ``HitlActionReceipt`` documents the field as
whether "the submission's event" is still pending. Test vocabulary only
(CINV-01).
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import httpx

from tests.http_api.test_approval_gate_limits_door import (
    APPROVER,
    act,
    bound_hash,
    client,
    fabric_at,
    invoke,
    open_door,
)
from tests.workflow import test_engine as eh

ANOTHER_PAUSE = "f" * 64


def test_a_verdict_naming_a_pause_with_no_request_waiting_is_not_told_its_request_waits(
    tmp_path: Path,
) -> None:
    fabric, key, version = fabric_at(tmp_path / "fabric", two_gate=True)
    door = open_door(fabric, key, version, tmp_path / "gate", eh._Bindings())

    async def flow() -> httpx.Response:
        async with client(door) as c:
            body = await invoke(c, door)
            tenant, event_key = body["tenant"], body["event_key"]
            bound = bound_hash(door, tenant, event_key)
            drained = fabric.hitl.dequeue(tenant=tenant)
            assert drained is not None and drained.product_content_hash == bound
            fabric.hitl.enqueue(event=drained.model_copy(update={"product_content_hash": ANOTHER_PAUSE}))
            return await act(c, event_key=event_key, bound=bound, action="approve", headers=APPROVER)

    response = asyncio.run(flow())
    assert response.status_code == 200, response.text
    receipt = response.json()
    assert receipt["submission"]["event_state_at_submit"] == "missing", receipt
    assert receipt["event_pending"] is False, (
        "the receipt told the approver the request was waiting, for a verdict recorded missing"
    )
