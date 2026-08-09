"""The typed write seam, pinned: shape, behavior, and confinement (15.2-02).

Phase 15.2 generalized the graph write seam from SQL-text transactions to the
nine typed operations of ``_GraphTxn``, so dict-, Cypher-, and
aggregation-backed transactions can satisfy it without interpreting SQL. Three
things must stay true afterwards, and each gets one test here:

* **Shape** — the seam is exactly nine operations. A backend that silently
  widened the write seam would be growing the write path outside the
  conformance suite's sight.
* **Behavior** — the rowcount-zero re-arrival contract survived the refactor
  byte-for-byte: a re-arrived claim accumulates lineage without minting a
  supersession, exactly as the pre-refactor suite pinned.
* **Confinement** — the generalization created no *unguarded* home for write
  code: every writer and every ``_GraphTxn`` implementation lives in a module
  the CINV-02 ``cinv02-graph-writer`` rule guards. Until Phase 15.4 that was
  one module, ``ccf.graph._writer``; D-01 split the per-backend writers out to
  ``ccf.graph.backends.<name>_write``, and the rule's guarded set became the
  predicate ``tools.lints.harness_imports.is_write_module`` over exactly that
  class of modules. The confinement claim is therefore stated against the
  predicate rather than against a path — a test pinned to one file would have
  gone green-and-vacuous the moment the file split, which is the failure
  D-GATE-15.3 records the project learning three times in one phase.

The behavioral test writes through a booted fabric only — never a directly
constructed writer — per the conformance suite's discipline (D-IMPL-41;
``tests/conformance/test_graphstore.py``).
"""

from __future__ import annotations

import ast
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from ccf.contracts.claims import EntityClaim, LineageEntry
from ccf.graph._writer import _GraphTxn
from ccf.signal.envelope import SourceIdentity

if TYPE_CHECKING:
    from ccf.boot import FabricHandle

TENANT = "tenant-a"
T0 = datetime(2026, 1, 1, tzinfo=UTC)
T1 = datetime(2026, 2, 1, tzinfo=UTC)

#: The write seam, exhaustively. Nine operations mirroring the nine dialect
#: statements one-for-one — four per axis (node upsert, claim append, chain
#: select, supersession update) plus the shared lineage append.
EXPECTED_OPERATIONS = frozenset(
    {
        "upsert_entity_node",
        "insert_entity_claim",
        "select_entity_chain",
        "update_entity_supersession",
        "upsert_relationship_node",
        "insert_relationship_claim",
        "select_relationship_chain",
        "update_relationship_supersession",
        "insert_lineage",
    }
)


def test_graph_txn_declares_exactly_the_nine_operations() -> None:
    """The seam is nine operations — no more, no fewer.

    Equality both ways on purpose: a missing operation means the writer
    algorithm lost a step, and an *extra* one means a backend widened the
    write seam without the conformance suite ever exercising the addition.
    ``__protocol_attrs__`` collects across the MRO, so widening via an
    inherited Protocol is caught the same as widening in the class body.
    """
    members = frozenset(_GraphTxn.__protocol_attrs__)

    assert members == EXPECTED_OPERATIONS, (
        f"_GraphTxn drifted from the nine-operation write seam: "
        f"unexpected={sorted(members - EXPECTED_OPERATIONS)} "
        f"missing={sorted(EXPECTED_OPERATIONS - members)}"
    )


def _lineage(system_id: str, envelope_id: str) -> LineageEntry:
    return LineageEntry(
        source=SourceIdentity(system_id=system_id),
        envelope_id=envelope_id,
        observed_at=T1,
    )


def _claim(*, lineage_entries: tuple[LineageEntry, ...]) -> EntityClaim:
    return EntityClaim(
        tenant_id=TENANT,
        entity_uri="counterparty://acme",
        entity_class="counterparty",
        attributes={"legal_name": "Acme Holdings"},
        observed_at=T1,
        valid_from=T0,
        lineage=frozenset(lineage_entries),
    )


def test_rearrival_through_the_typed_seam_is_idempotent(
    fabric: "FabricHandle",
) -> None:
    """The rowcount-zero re-arrival contract survived the seam refactor.

    Same behavior the pre-refactor suite pins (INV-CH7-17), now proven to
    flow through ``_GraphTxn`` typed operations: an exact re-arrival changes
    nothing, a second source accumulates lineage, and neither mints a
    supersession. Writes go through booted L2 only.
    """
    claim = _claim(lineage_entries=(_lineage("core-banking", "env-1"),))
    first = fabric.worker.admit_entity_claim(tenant_id=TENANT, claim=claim)
    second = fabric.worker.admit_entity_claim(tenant_id=TENANT, claim=claim)

    assert first.claim_created is True
    assert first.lineage_added == 1
    assert second.claim_created is False, "re-arrival must not manufacture history"
    assert second.lineage_added == 0
    assert second.claim_id == first.claim_id
    assert second.superseded_claim_id is None, "a re-arrival never supersedes"

    corroborated = _claim(lineage_entries=(_lineage("kyc-registry", "env-2"),))
    third = fabric.worker.admit_entity_claim(tenant_id=TENANT, claim=corroborated)

    assert third.claim_created is False, "same claim content — no new claim row"
    assert third.lineage_added == 1, "corroboration accumulates, never replaces"
    assert third.superseded_claim_id is None

    history = fabric.reader.entity_history(
        tenant_id=TENANT, entity_uri=claim.entity_uri
    )
    assert len(history) == 1
    assert len(history[0].claim.lineage) == 2
    assert history[0].superseded_by is None


#: The one legitimate write-shaped name outside a guarded write module: the
#: ``GraphWriter`` *Protocol* — layer 1 of the D-IMPL-41 stack (the
#: reader/writer interface split). It is a type declaration with no
#: implementation, predates the typed seam, and is exactly what the CINV-02
#: import restriction protects, not what it confines.
_ALLOWED_ELSEWHERE = frozenset({("ccf/graph/protocols.py", "GraphWriter")})


def _dotted(relative: str) -> str:
    """``ccf/graph/backends/x_write.py`` -> ``ccf.graph.backends.x_write``."""
    return relative[: -len(".py")].replace("/", ".")


def test_write_code_has_no_second_home_outside_a_guarded_write_module() -> None:
    """Every writer and txn class lives in a module ``is_write_module`` guards.

    The CINV-02 lint restricts who may *import* a write module; this test
    guards the other direction — that generalizing the seam did not scatter
    write *implementations* (``*GraphWriter``, ``*GraphTxn``) into modules the
    lint never guards. A backend that shipped its transaction class next to its
    *reader* would re-open exactly the hole D-01 closes.

    The membership test is imported from the checker rather than restated, so
    the two cannot drift: whatever the lint guards is what this test permits,
    and a seventh adapter's write module is admitted here on arrival for the
    same reason it joins the guarded set on arrival.
    """
    from tools.lints.harness_imports import is_write_module

    source_root = Path(__file__).resolve().parents[2] / "src"
    write_shaped = re.compile(r"(GraphWriter|GraphTxn)$")

    offenders: list[str] = []
    for path in sorted(source_root.rglob("*.py")):
        relative = path.relative_to(source_root).as_posix()
        if is_write_module(_dotted(relative)):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            if not write_shaped.search(node.name):
                continue
            if (relative, node.name) in _ALLOWED_ELSEWHERE:
                continue
            offenders.append(f"{relative}:{node.lineno}::{node.name}")

    assert offenders == [], (
        "write code found outside a CINV-02-guarded write module "
        f"(second-home violation): {offenders}"
    )


def test_the_guarded_set_is_not_vacuous() -> None:
    """The test above is only worth anything if something was skipped.

    A predicate that matched nothing would make the scan above pass by
    scanning the whole tree and finding no writer at all — green, and
    guarding nothing. So the modules the predicate admits are counted, and
    the count is asserted against the writers actually on disk.
    """
    from tools.lints.harness_imports import is_write_module

    source_root = Path(__file__).resolve().parents[2] / "src"
    guarded = sorted(
        relative
        for relative in (
            path.relative_to(source_root).as_posix()
            for path in source_root.rglob("*.py")
        )
        if is_write_module(_dotted(relative))
    )

    assert "ccf/graph/_writer.py" in guarded, guarded
    assert len(guarded) >= 2, (
        "no per-backend write module is guarded; the predicate matched only "
        f"the neutral base: {guarded}"
    )
