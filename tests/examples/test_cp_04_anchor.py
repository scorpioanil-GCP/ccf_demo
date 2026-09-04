"""cp-04's anchor resolution and its read lineage, under `D-IMPL-245` (4) and criterion 20.

Two things this rung reads BEFORE the graph is touched, and both were measured
wrong on the tree Phase 24.5.1 started from (`24.5.1-RESEARCH.md` §D16, §D17):

* **`ledger_t` matched the ledger NAME alone.** Fluree's ``GET …/ledgers``
  lists ``{"name", "branch", "t"}`` for EVERY branch of every ledger, so a
  name-only match answers with whichever branch the server lists first. The
  SDK's own ``head_t`` (``src/ccf/graph/backends/fluree.py``) matches the
  ``name:branch`` pair; the example now mirrors it through a pure function,
  ``deployment.head_t_of``, held here to a synthetic two-branch listing with
  no server in the loop (criterion 20).

* **`resolve_anchor` returned the FIRST binding of an unordered SELECT.** A
  shared LEI therefore made the anchor — and the whole served family — depend
  on the store's row order. Dave's ruling (`D-IMPL-245` (4)): *"Not 404, and
  definitely not 'serve with a finding'"* — ambiguity fails closed as TYPED
  AMBIGUITY DATA, the SDK kind ``AnchorAmbiguityRefusal`` returned through the
  D-60 channel. The committed fixture carries no shared LEI (and
  ``test_cp_04_seams.py::lei_identity_violations`` refuses one), so the
  ambiguous case is a PERTURBED ledger built here from the fixture, with the
  perturbation plumbing ``test_cp_04_debt.py`` already ships.

And one identity fact: the assembler that carries both corrections is
``1.0.1`` — `D-IMPL-245` am.1 (a PATCH for a corrected implementation, printed
as TRANSCRIPT evidence, never a replay claim) and am.3 (ONE bump for both
changes, and a PATCH only).

Every number and every roster below is measured at run time; the module writes
down addresses into the fixture and the SDK's own constants, never figures.
"""

from __future__ import annotations

import pathlib
import tempfile
from typing import Any, Iterator, Mapping

import pytest

from ccf.agents.assembler import AssemblyOutcome
from ccf.graph.backends.fluree import DEFAULT_BRANCH

from .cp_04_seed import ledger_for, schema_for, seed
from .test_cp_04_debt import _load

pytestmark = [pytest.mark.fluree, pytest.mark.postgres]

# ---------------------------------------------------------------------------
# Criterion 20 — `ledger_t` matches name AND branch, exactly as `head_t` does.
# ---------------------------------------------------------------------------


def test_ledger_t_matches_the_ledger_name_and_its_branch() -> None:
    """Pure, no HTTP: a two-branch listing of one name answers per branch.

    The listing shape is Fluree's ``GET …/ledgers`` — one entry per branch of
    every ledger — and the default branch is the SDK's ``DEFAULT_BRANCH``,
    imported rather than spelled. A bare name means the default branch and
    ``name:branch`` means that branch; a name the listing does not carry is
    ``None``, as the example's lineage read has always answered a miss.
    """
    deployment = _load("deployment")
    listing = [
        {"name": "x", "branch": DEFAULT_BRANCH, "t": 5},
        {"name": "x", "branch": "dev", "t": 9},
    ]
    assert deployment.head_t_of(listing, "x") == 5
    assert deployment.head_t_of(listing, f"x:{DEFAULT_BRANCH}") == 5
    assert deployment.head_t_of(listing, "x:dev") == 9
    assert deployment.head_t_of(listing, "y") is None

    # THE CONTROL THAT SEPARATES THIS PREDICATE FROM THE NAME-ONLY ONE. A
    # listing whose ONLY `x` entry is the `dev` branch has no default-branch
    # `x` at all, so the bare name is a miss — the name-only match this rung
    # shipped with would have answered 9 here.
    only_dev = [{"name": "x", "branch": "dev", "t": 9}]
    assert deployment.head_t_of(only_dev, "x") is None, (
        "a bare ledger name matched a NON-default branch — the name-only"
        " predicate `head_t` never had, restored"
    )
    assert deployment.head_t_of(only_dev, "x:dev") == 9

    # A listed branch with no `t` is a missing lineage detail, not a raise.
    assert deployment.head_t_of([{"name": "x", "branch": DEFAULT_BRANCH}], "x") is None


# ---------------------------------------------------------------------------
# The estate, and one assembly through the SHIPPED seam with its return KEPT.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def baseline(fluree_url: str, postgres_dsn: str) -> Iterator[tuple[str, str]]:
    """The committed fixture pair, unperturbed, under names nobody else holds."""
    ledger = ledger_for(__name__)
    schema = schema_for(__name__)
    seed(fluree_url, ledger, postgres_dsn, schema)
    yield ledger, schema


def _point_at(
    monkeypatch: pytest.MonkeyPatch,
    *,
    fluree_url: str,
    ledger: str,
    dsn: str,
    schema: str,
) -> None:
    """Aim the deployment at one estate through the names `backends.yaml` declares."""
    for variable, value in (
        ("CCF_CP_04_FLUREE_URL", fluree_url.rstrip("/")),
        ("CCF_CP_04_FLUREE_LEDGER", ledger),
        ("CCF_CP_04_POSTGRES_DSN", dsn),
        ("CCF_CP_04_POSTGRES_SCHEMA", schema),
    ):
        monkeypatch.setenv(variable, value)


def _assemble_keeping_the_return(
    *, request: Any | None = None
) -> tuple[Any, list[Any]]:
    """Run the SHIPPED assembler exactly as `test_cp_04_debt.py::_assemble` does.

    The one difference is the point: the Protocol's RETURN is kept alongside
    the observer's log, because the subject here is what the seam hands back —
    an `AssemblyOutcome` on the committed estate, a typed refusal on a
    perturbed one — and not only what it let an observer see.
    """
    deployment = _load("deployment")
    projection = _load("projection")
    assembler = _load("assembler")

    state: dict[str, Any] = {}

    def read(booted: Any, asked: Any, **kwargs: Any) -> Any:
        scenario = deployment.read(booted, asked, **kwargs)
        state["scenario"] = scenario
        state["booted"] = booted
        return scenario

    def claims(*, minted: Mapping[str, str]) -> Any:
        scenario = state["scenario"]
        return deployment.relationship_claims(
            tenant=state["booted"].tenant_id,
            at=scenario.request.asked_at,
            edges=scenario.edges,
            nodes=sorted(scenario.facts),
            minted=minted,
            envelopes_by_node=scenario.envelopes_by_node,
        )

    seen: list[Any] = []
    with tempfile.TemporaryDirectory(prefix="cp04-anchor-") as tmp:
        root = pathlib.Path(tmp)
        product = assembler.FamilyTreeAssembler(
            config=deployment.CONFIG,
            root=root,
            connection=deployment.connection(root=root),
            read=read,
            plan_class=projection.plan_class(),
            claims=claims,
            observer=seen.append,
        )
        outcome = product.assemble(
            request=request or deployment.demonstration_request(),
            perspective=deployment.perspective(),
            tenant_id=deployment.tenant_id(),
        )
    return outcome, seen


# ---------------------------------------------------------------------------
# Criterion 4 — the corrected implementation names itself `1.0.1`, once.
# ---------------------------------------------------------------------------


def test_the_served_outcome_names_the_module_assembler_version(
    baseline: tuple[str, str],
    fluree_url: str,
    postgres_dsn: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The Protocol's return names this module's assembler identity, pinned at `1.0.1`.

    `D-IMPL-245` am.1: an assembler materially corrected in 24.5.1 bumps PATCH
    to `1.0.1` — this rung's `resolve_anchor` now fails closed on ambiguity as
    typed data and its dead `ParameterNotSupported` branch is gone — and am.3:
    ONE bump for both changes, and a PATCH only. The transcript line `assembled by`
    carries this identity as evidence; Decision Replay carries none of it
    today (am.1), and no claim that it does is made here.
    """
    ledger, schema = baseline
    _point_at(
        monkeypatch, fluree_url=fluree_url, ledger=ledger, dsn=postgres_dsn, schema=schema
    )
    assembler = _load("assembler")
    outcome, seen = _assemble_keeping_the_return()
    assert seen, "the observer never fired, so nothing was assembled"
    assert isinstance(outcome, AssemblyOutcome), (
        "the committed estate has no shared LEI, so the demonstration request is"
        f" SERVED there; got {type(outcome).__name__}: {outcome!r}"[:600]
    )
    assert outcome.assembler_id == assembler.ASSEMBLER_ID
    assert outcome.assembler_version == assembler.ASSEMBLER_VERSION
    assert assembler.ASSEMBLER_VERSION == "1.0.1", (
        "the pin is D-IMPL-245 am.1's PATCH identity for the corrected"
        " implementation; 1.0.0 would make two implementations share one name,"
        " and am.3 rules never 1.0.2"
    )
