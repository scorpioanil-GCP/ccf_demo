"""The MCP door carries the declared-obligation kind with no runtime edit.

Ledger rows ``24.5-L-26`` and ``24.6-L-04`` (door half), the MCP mirror of the
HTTP door's typed ``409``; CLAUDE.md §7.1 (MCP as egress) and §8.3.

**Re-derived at ``24.6-04``**: the kind under test carried a debt half when
this module was written, and that is the half it exercised. The half is
retired (``D-IMPL-251`` C1=A), so what travels below is the LINEAGE
obligation. Nothing about the door changed, which is the module's own claim
restated — it carries what the vocabulary carries. The HTTP door maps ONE
refusal kind to a status (plan ``24.5-14``, ``routes/product.py``); the MCP
tool has no status to map to and needs none — its refusal channel is the
:class:`~ccf.products.door.DoorOutcome` return value Wave 2 shipped
(``D-IMPL-148`` Addendum A; plans ``24.5-06`` / ``24.5-07``), and every kind
in :data:`~ccf.products.refusal.REFUSAL_KINDS` already travels through it.
So the same refusal that is a ``409`` over HTTP arrives at a real MCP
``ClientSession`` as ``outcome.refusal.kind == "declared-obligation-refusal"``
with ``is_error False``, and the egress module names neither the kind nor the
type: the door carries what the vocabulary carries.

The plumbing — the real egress door over the supplied resolver, the tool
call at a real client, the decode that validates rather than sniffs — is the
sibling module's, imported rather than re-declared so the two modules cannot
come to disagree about what "the MCP door" is. ``tests/mcp`` is not a package
(no ``__init__.py``), so the sibling is reached by its bare module name under
pytest's default import mode, exactly as pytest itself imports it.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
import re
from pathlib import Path
from typing import Any

import pytest

from ccf.products.gates import (
    GATE_DECLARED_OBLIGATIONS,
    DeclaredObligationRefusal,
)
from ccf.products.refusal import REFUSAL_KINDS, RefusalEnvelope, envelope_for
from ccf_runtime.mcp import egress
from crossproc.servers.mcp_egress_child import build_servable_product
from test_egress_refusal_envelope import (
    CALLER_PARAMETERS,
    _answering,
    _ask_mcp_door,
    _decode,
    _identity,
    _minted,
)

#: What the gate said, rendered as it crosses the wire: the obliged payload
#: member and the state the candidate carried it in. Test vocabulary.
DECLARED = "inputs"
OBSERVED = "absent"

#: The kind under test, read from the mapping — one spelling in the tree.
KIND = REFUSAL_KINDS[DeclaredObligationRefusal]

EGRESS_SOURCE = Path(egress.__file__)


@pytest.fixture(scope="module")
def assembled(tmp_path_factory: pytest.TempPathFactory) -> Any:
    """One assembled, gate-admitted product, whose class the door serves."""
    return build_servable_product(
        database_path=tmp_path_factory.mktemp("egress-declared") / "door.sqlite3"
    )


def _refusal() -> DeclaredObligationRefusal:
    """What the declared-obligations gate returns for a dropped lineage member."""
    return DeclaredObligationRefusal(
        gate=GATE_DECLARED_OBLIGATIONS,
        detail=(
            f"product declares a lineage obligation on payload member"
            f" {DECLARED!r}, which is {OBSERVED} — every served line must name"
            " what it was computed from (24.5-L-26)"
        ),
        obligation="lineage-inputs",
        declared=DECLARED,
        observed=OBSERVED,
    )


def _envelope(assembled: Any) -> RefusalEnvelope:
    """The envelope the SDK's reference resolver returns — lineage and all."""
    return envelope_for(
        _refusal(),
        request=_identity(assembled.address),
        pre_assembly_lineage=assembled.servable.product.lineage,
    )


def _assert_declared_obligation_kind(
    is_error: bool, text: str, *, address: Any
) -> RefusalEnvelope:
    """The MCP mirror of the HTTP door's 409 check: the kind, as a field.

    Returns the decoded refusal so each test can go on to read what it
    specifically asserts.
    """
    assert is_error is False, text
    outcome = _decode(text)
    assert outcome.product_json is None
    refusal = outcome.refusal
    assert refusal is not None, "the outcome carried no refusal"
    assert refusal.kind == KIND
    assert refusal.reason == GATE_DECLARED_OBLIGATIONS
    assert refusal.key is None
    assert set(refusal.fields) == {"obligation", "declared", "observed"}
    # Envelope fields arrive in the SDK's one canonical form — a string
    # quoted — so the value is decoded, never compared to a bare literal.
    assert json.loads(refusal.fields["obligation"]) == "lineage-inputs"
    assert json.loads(refusal.fields["declared"]) == DECLARED
    assert json.loads(refusal.fields["observed"]) == OBSERVED
    assert refusal.request == _identity(address)
    assert dict(refusal.request.parameters) == dict(CALLER_PARAMETERS)
    return refusal


def test_a_declared_obligation_refusal_arrives_as_its_typed_kind(
    assembled: Any, tmp_path: Path
) -> None:
    """The envelope the reference resolver returns, at a real client, ``is_error False``.

    What would fail here: a door that raised for this kind (``isError`` with
    a prose prefix, the shape ``D-IMPL-148`` refused), one that flattened
    the gate's ``declared``/``observed`` pair out of ``fields``, or one that
    dropped the pre-assembly lineage a gate refusal genuinely had.
    """
    address = assembled.address
    # Minted at `full` so the lineage the gate refusal genuinely had crosses;
    # the door releases only what the recorder returned (`D-IMPL-260` P-A).
    is_error, text = _ask_mcp_door(
        tmp_path,
        address=address,
        resolver=_answering(
            _minted(tmp_path, address, _envelope(assembled), level="full")
        ),
    )

    refusal = _assert_declared_obligation_kind(is_error, text, address=address)
    assert refusal.pre_assembly_lineage == assembled.servable.product.lineage


def test_a_bare_declared_obligation_refusal_does_not_cross_the_mcp_door(
    assembled: Any, tmp_path: Path
) -> None:
    """``D-IMPL-260`` P-A: what ``run_gates`` gave a resolver is not a governed answer yet.

    Until this ruling the door translated the bare value itself — undisclosed,
    unrecorded — and answered with it. It now refuses the bare value as a
    wiring defect, which this door reports as its opaque runtime failure: no
    kind, no type name, no prose, and never a refusal the fabric made.
    """
    address = assembled.address
    is_error, text = _ask_mcp_door(
        tmp_path, address=address, resolver=_answering(_refusal())
    )

    assert is_error is True, text
    assert re.fullmatch(
        rf"(Error executing tool [^:\s]+: )?{egress.CCF_FAILURE_PREFIX}:[0-9a-f]{{32}}",
        text.strip(),
    ), text
    assert "DeclaredObligationRefusal" not in text
    assert KIND not in text


def test_the_egress_module_names_neither_the_kind_nor_the_type() -> None:
    """No runtime edit: the MCP door carries the kind without knowing it.

    The plan's own assertion (*"the envelope path already carries it"*),
    measured against the shipped module rather than against a git range a
    shallow CI clone cannot see: ``egress.py`` contains neither the token
    nor the type name. The positive control shows the same scan finding the
    shared emission function the door does run through, so an empty scan is
    not a scan of the wrong file.
    """
    source = EGRESS_SOURCE.read_text(encoding="utf-8")

    assert "DeclaredObligationRefusal" not in source
    assert "declared-obligation" not in source
    assert "declared_obligation" not in source
    # Positive control: the scan reads the file the door is built from.
    assert "door_answer(" in source
    assert "def build_egress_server(" in source
