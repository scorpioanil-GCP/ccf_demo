# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""Dave's E2 (i): the boundary between the operator's record reads and an agent's, measured.

``D-IMPL-378``, Dave, 2026-10-08 12:29 MST, E2 (i), verbatim: *"yes, narrowly:
trusted operator/auditor handles holding the underlying store may remain
unrestricted. Agent-accessible in-process interfaces must still enforce Q12.
Document this boundary explicitly."*

Lane ``378e-s020`` inventoried every in-process interface through which a
Decision Replay record, its contents or a replay result can be read
(``FINAL-REPORT.md`` §3 in the lane directory). Two classes:

* **Operator/auditor handles** — the caller already holds the deployment's
  ArtifactStore, so the handle reads bytes its caller can read directly:
  ``src/ccf/replay/engine.py::replay``, ``::replay_refusal``,
  ``::resolve_artifact`` and ``::resolve_artifact_at_uri`` (each is handed the
  store), and ``src/ccf/products/product.py::OpenedProduct.record_of`` (an
  opened product carries its store as ``artifact_store``). Unrestricted by the
  ruling, and each one's docstring says so.
* **Agent-accessible reads** — the governed evidence reads every door calls
  (``runtime/ccf_runtime/authz/delivery_boundary.py::govern_dereference``: the
  HTTP replay and artifact routes, the MCP artifact server, the ``ccf`` CLI
  through HTTP) hold Q12's default-deny, and the MCP Experience door's
  ``get_replay_record`` refuses every caller; each is measured in
  ``tests/http_api/test_sec020_q12_owner_read_back.py``. The interfaces an
  agent, a harness adapter or a product client is handed in process —
  ``ProductClient``, its ``Result`` and the in-process adapter — carry a
  record's reference and never the record.

This module holds the two sides of that line on one withheld answer, so the
documented boundary is a measurement: the agent's read is refused by name, the
operator's handles read the record, and the handles' caller reads the same bytes
from the store it holds. Fixture vocabulary only (CINV-01).
"""

from __future__ import annotations

import pathlib
import typing

from ccf.client.adapters.inprocess import InProcessAdapter
from ccf.client.client import ProductClient
from ccf.client.result import Result
from ccf.replay.engine import resolve_artifact
from ccf.replay.record import DecisionReplayRecord
from ccf.replay.serve import ServedProduct
from tests.deployment.test_replay_binding import THRESHOLD_PARAMETER
from tests.http_api.test_sec020_q12_owner_read_back import _internal_error_code, _owner_get
from tests.http_api.test_sec020_withheld_record_dereference import (
    PAVED_WITHHELD,
    _ask,
    _door,
    _reference,
)
from tests.products.test_paved_road import ASKED_AT
from tests.products.test_withheld_is_indistinguishable_from_absent import FROM_DECISION


def test_e2i_the_agent_read_is_refused_and_the_operator_handles_read_the_record(
    tmp_path: pathlib.Path,
) -> None:
    """One withheld answer, its class not listed: both sides of E2 (i)'s line.

    The agent-accessible read — the owner at ``full`` presenting the reference
    its own answer handed it to the governed HTTP reads — is refused by hold 2b,
    ``evidence-class-sealed``, named in the refusal's own record. The operator's
    handles over the same deployment — the replay engine's read and
    ``OpenedProduct.record_of`` — return the record, whose dimension 1 names the
    withheld subject; and the store the handles' caller holds returns the very
    bytes, so restricting the handles would protect nothing.
    """
    from ccf_runtime.http_api.errors import ERROR_EVIDENCE_CLASS_SEALED  # noqa: PLC0415

    with _door(tmp_path, "e2i-boundary", anchor=FROM_DECISION, holds_subject=True) as door:
        reference = _reference(_ask(door, PAVED_WITHHELD))
        store = door.opened.artifact_store
        address = store.resolve_uri(uri=reference)

        for path, params in (
            ("/replay/resolutions", {"uri": reference}),
            (f"/artifact/{address}", {}),
        ):
            read = _owner_get(door, path, **params)
            assert read.status_code != 200, f"{path}: the agent-accessible read served the record"
            shell = read.json()["refusal"]["replay_reference"]
            assert _internal_error_code(store, shell) == ERROR_EVIDENCE_CLASS_SEALED, path

        # The operator's handles: unrestricted by the ruling, and holding the store.
        by_engine = resolve_artifact(store=store, content_address=address, contract=DecisionReplayRecord)
        assert PAVED_WITHHELD in by_engine.context_fabric_snapshot.model_dump_json(), (
            "the replay engine's read did not return the record of the withheld answer"
        )
        assert DecisionReplayRecord.model_validate_json(store.get(content_address=address)) == by_engine

        in_process = door.opened.answer(
            door.opened.question(
                subject=PAVED_WITHHELD, asked_at=ASKED_AT, intent="fixture-intent",
                freshness="fixture-freshness", parameters={THRESHOLD_PARAMETER: 1000},
            )
        )
        record = door.opened.record_of(in_process)
        assert PAVED_WITHHELD in record.context_fabric_snapshot.model_dump_json(), (
            "OpenedProduct.record_of did not return the record of the withheld answer"
        )
        if isinstance(in_process, ServedProduct):
            address_in_process = in_process.replay_ref.content_address
        else:
            address_in_process = store.resolve_uri(uri=in_process.replay_reference)
        assert DecisionReplayRecord.model_validate_json(
            store.get(content_address=address_in_process)
        ) == record


def test_e2i_the_in_process_interfaces_an_agent_is_handed_carry_no_record() -> None:
    """The product client, its result and the in-process adapter return no record and no replay result.

    Read off their public members' declared return types, so a member added
    later that hands an agent a record — an unenforced Q12 read — reddens this.
    The control: the operator handle's declared return type IS a record.
    """
    record_types = {DecisionReplayRecord}
    offending: list[str] = []
    for owner in (ProductClient, Result, InProcessAdapter):
        for name, member in vars(owner).items():
            if name.startswith("_"):
                continue
            function = member.fget if isinstance(member, property) else member
            if not callable(function):
                continue
            returned = typing.get_type_hints(function).get("return")
            named = {returned, *typing.get_args(returned)} if returned is not None else set()
            if named & record_types or "Replay" in repr(returned):
                offending.append(f"{owner.__name__}.{name} -> {returned!r}")
    assert not offending, f"an agent-facing interface returns a record or a replay result: {offending}"

    from ccf.products.product import OpenedProduct  # noqa: PLC0415

    assert typing.get_type_hints(OpenedProduct.record_of)["return"] is DecisionReplayRecord, (
        "control: the operator handle's return type is not read as a record, so this scan reads nothing"
    )
