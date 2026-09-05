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

And one identity fact: the assembler that carries the corrections is
``1.0.2`` — `D-IMPL-245` am.1 (a PATCH for a corrected implementation) and am.3
(ONE bump per phase, and a PATCH only), moved to its 24.6 value by `D-25`.

SUPERSEDED 2026-09-05 (`24.6-L-01`, `24.6-L-15`): the paragraph above pinned ``1.0.1`` and called that identity TRANSCRIPT evidence, *"never a replay claim"*, because Decision Replay carried no assembler identity.
It carries one now: `produce.py::_record` passes `assembler_id` and
`assembler_version` into `build_replay_record`, so dimension 4 answers *which
build made this decision* for a fulfilled outcome and for a refused one alike.

Every number and every roster below is measured at run time; the module writes
down addresses into the fixture and the SDK's own constants, never figures.
"""

from __future__ import annotations

import json
import pathlib
import tempfile
from typing import Any, Iterator, Mapping

import pytest

from ccf.agents.assembler import AssemblyOutcome
from ccf.graph.backends.fluree import DEFAULT_BRANCH
from ccf.products.request import AnchorAmbiguityRefusal
from ccf.products.refusal import REFUSAL_KINDS

from .cp_04_seed import ledger_for, schema_for, seed
from .test_cp_04_debt import (
    LEI_PREDICATE,
    ROW_LESS_MEMBER,
    _document,
    _fixture_body,
    _perturbed_ledger,
    _set_lei,
)
from .test_cp_04_two_callers import Refused, _load, drive, tool_arguments, tool_call

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
# Criterion 4 — the corrected implementation names itself `1.0.2`, once.
# ---------------------------------------------------------------------------


def test_the_served_outcome_names_the_module_assembler_version(
    baseline: tuple[str, str],
    fluree_url: str,
    postgres_dsn: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The Protocol's return names this module's assembler identity, pinned at `1.0.2`.

    `D-25`: *"cp-04 versions — product lane MINOR -> 1.1.0; assembler PATCH if
    its own interface remains compatible."* It does: every value a `1.0.1`
    caller could receive is still returned and none changed shape; what
    `24.6-L-01`/`L-02` added is three more members, each standing where a raise
    stood. An additive widening is PATCH, and `D-IMPL-245` am.3's ONE bump per
    phase is spent on it.

    The transcript line `assembled by` carries this identity, and since
    `24.6-L-15` so does replay dimension 4 —
    `tests/examples/test_cp_04_seams.py::test_replay_carries_the_assembler_identity_for_fulfilled_and_refused`
    is the check that reads it there.
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
    assert assembler.ASSEMBLER_VERSION == "1.0.2", (
        "the pin is D-25's PATCH identity: a previously refused valid request"
        " now produces a product — MINOR on the PRODUCT lane, which moved to"
        " 1.1.0 — while the assembler's own return set widened ADDITIVELY, so"
        " every value a 1.0.1 caller could receive it can still receive, and"
        " that is PATCH. SUPERSEDED 2026-09-05 (`24.6-L-01`): this pin was 1.0.1 and its message said `am.3 rules never 1.0.2`."
        " `D-IMPL-245` am.3 rules ONE bump per phase and PATCH only; it does"
        " not fix which patch number, and 24.6 is a different phase from the"
        " one that reasoning was written in."
    )


# ---------------------------------------------------------------------------
# Criterion 19 — an ambiguous anchor is refused as typed ambiguity data.
# ---------------------------------------------------------------------------

#: The envelope kind the SDK names for the refusal (`src/ccf/products/refusal.py`
#: `REFUSAL_KINDS`), read off the mapping rather than spelled at the assertion.
AMBIGUITY_KIND = REFUSAL_KINDS[AnchorAmbiguityRefusal]

#: The one door operation this module drives.
AMBIGUOUS_ASK = "mcp-tool(the demonstration anchor on the perturbed ledger)"


def _anchor_lei_and_iri(deployment: Any) -> tuple[str, str]:
    """The demonstration anchor's LEI (the request subject) and its fixture IRI.

    Read FROM the fixture by the LEI the shipped request carries, and refused
    loudly when the fixture holds no such document or more than one: a
    perturbation aimed at an anchor the fixture does not carry would build an
    estate with ONE binding for the LEI, and every assertion below would then
    be true of an unambiguous estate — the shape of a test that cannot fail.
    """
    lei = str(deployment.demonstration_request().subject)
    holders = [
        str(document["@id"])
        for document in _fixture_body()["insert"]
        if any(str(value) == lei for value in (document.get(LEI_PREDICATE) or ()))
    ]
    assert len(holders) == 1, (
        f"the committed fixture holds {len(holders)} document(s) carrying the"
        f" demonstration anchor's LEI {lei!r}: {holders}; this module's"
        " perturbation needs exactly ONE so that the second binding is the one"
        " it plants"
    )
    return lei, holders[0]


@pytest.fixture(scope="module")
def ambiguous_estate(
    fluree_url: str, postgres_dsn: str, baseline: tuple[str, str]
) -> tuple[str, str, str]:
    """A ledger where ONE second node carries the anchor's LEI; the baseline schema.

    The inverse of `test_cp_04_debt.py::resolving_estate`: that estate gives a
    row-less member a NEW LEI, this one gives it the ANCHOR's. Two nodes then
    answer the anchor's SELECT, which is the collision the committed fixture
    does not carry (`test_cp_04_seams.py::lei_identity_violations` refuses one
    there). The Postgres schema is the baseline's: the refusal is pre-assembly,
    so the attribute store is never reached, and an LEI edit in Fluree moves no
    attribute row.

    Returns ``(ledger, schema, anchor_iri)``.
    """
    _, schema = baseline
    deployment = _load("deployment")
    anchor_lei, anchor_iri = _anchor_lei_and_iri(deployment)
    assert anchor_iri != ROW_LESS_MEMBER, (
        "the perturbation target IS the anchor; the collision would be one node"
    )
    # `_document` refuses a miss, so a perturbation applied to nothing fails here.
    _document(_fixture_body(), ROW_LESS_MEMBER)
    ledger = _perturbed_ledger(
        fluree_url, lambda body: _set_lei(body, ROW_LESS_MEMBER, anchor_lei)
    )
    return ledger, schema, anchor_iri


def test_cft_g18_an_ambiguous_anchor_is_refused_as_typed_ambiguity_data(
    ambiguous_estate: tuple[str, str, str],
    fluree_url: str,
    postgres_dsn: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`CFT-G18`: two nodes answer the anchor's LEI → `AnchorAmbiguityRefusal`, as data.

    `D-IMPL-245` (4), Dave: *"AnchorAmbiguityRefusal. Not 404, and definitely
    not 'serve with a finding'."* The seam RETURNS the SDK kind — never raises
    it — carrying the anchor and EXACTLY the two candidate IRIs (a set, never a
    count), and nothing is served: no observed vessel, no payload, no address.
    Sabotage: restore `resolve_anchor`'s first-binding return, so the shared
    LEI serves whichever node the store lists first.
    """
    ledger, schema, anchor_iri = ambiguous_estate
    _point_at(
        monkeypatch, fluree_url=fluree_url, ledger=ledger, dsn=postgres_dsn, schema=schema
    )
    deployment = _load("deployment")
    request = deployment.demonstration_request()
    outcome, seen = _assemble_keeping_the_return(request=request)

    assert isinstance(outcome, AnchorAmbiguityRefusal), (
        "an anchor carried by TWO nodes was not refused as typed ambiguity data;"
        f" the seam returned {type(outcome).__name__}: {outcome!r}"[:900]
    )
    assert outcome.anchor == request.subject
    assert outcome.candidates == frozenset({anchor_iri, ROW_LESS_MEMBER}), (
        "the refusal must name EXACTLY the two colliding nodes:"
        f" got {sorted(outcome.candidates)}"
    )
    assert not any(
        getattr(entry, "served", None) is not None for entry in seen
    ), "a vessel was SERVED beside the ambiguity refusal — ambiguity flowed downstream"
    assert REFUSAL_KINDS[type(outcome)] == AMBIGUITY_KIND
    # The detail names the count and the rule; which candidates THIS principal
    # may see is the audit plane's account and must not appear here.
    assert str(len(outcome.candidates)) in outcome.detail
    for word in ("entitle", "principal", "visible", "grant"):
        assert word not in outcome.detail.casefold(), (
            f"the refusal detail discloses visibility via {word!r}: {outcome.detail}"
        )


def test_cft_g18_b_the_tool_carries_the_ambiguity_as_a_governed_refusal(
    ambiguous_estate: tuple[str, str, str],
    fluree_url: str,
    postgres_dsn: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`CFT-G18` over the MCP door: the envelope's `kind` is the SDK's, the door stays up.

    The SHIPPED door (`server/serve.py::door`) is driven through the SHIPPED
    tool. `AnchorAmbiguityRefusal` is a member of `REFUSAL_KINDS`, so
    `door_refusal` translates the value the assembler returned into the one
    refusal envelope with no edit to `transport.py` or `server/compose.py` —
    which is what this leg measures. The door must not be torn down by the
    refusal (a `Refused` here would be the CR-01 symptom), and the outcome the
    tool returns must carry the kind by name and both colliding IRIs.
    """
    ledger, schema, anchor_iri = ambiguous_estate
    _point_at(
        monkeypatch, fluree_url=fluree_url, ledger=ledger, dsn=postgres_dsn, schema=schema
    )
    deployment = _load("deployment")
    serve = _load("serve")
    tenant = deployment.tenant_id()
    request = deployment.demonstration_request()

    with tempfile.TemporaryDirectory(prefix="cp04-anchor-door-") as scratch:
        with serve.door(root=pathlib.Path(scratch)) as opened:
            results = drive(
                opened,
                {AMBIGUOUS_ASK: tool_call(tool_arguments(tenant=tenant, typed=request))},
            )

    result = results[AMBIGUOUS_ASK]
    assert not isinstance(result, Refused), (
        "the ambiguous anchor took the door DOWN instead of answering with a"
        f" governed refusal: {result.reason[:1000]}"
    )
    is_error, text = result
    outcome = json.loads(text)
    refusal = outcome.get("refusal")
    assert refusal is not None, (
        f"the door SERVED on an ambiguous anchor (isError={is_error}): {text[:1000]}"
    )
    assert refusal["kind"] == AMBIGUITY_KIND, (
        f"the door refused under kind {refusal['kind']!r}, not {AMBIGUITY_KIND!r}"
        f" (isError={is_error}): {text[:1000]}"
    )
    assert outcome.get("product_json") is None, "a vessel rode beside the refusal"
    for iri in (anchor_iri, ROW_LESS_MEMBER):
        assert iri in text, f"the envelope does not name the candidate {iri}: {text[:1000]}"
    # The envelope is a RETURN VALUE, not a raised tool error: measured against
    # `mcp==1.28.1`, the egress door renders a refusal as the outcome the tool
    # returns (`runtime/ccf_runtime/mcp/egress.py`, "A refusal, as the return
    # value rather than a raise"), so `isError` carries no governed meaning here
    # and is recorded, not asserted.
    assert isinstance(is_error, bool)


def test_the_ambiguity_gate_measures_the_perturbation_and_not_the_estate(
    baseline: tuple[str, str],
    fluree_url: str,
    postgres_dsn: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Control: the SAME request on the UNPERTURBED estate is SERVED.

    Without this, a seam that refused every anchor as ambiguous would keep
    the gate above green forever. The committed fixture has no shared LEI, so
    the demonstration request resolves to one node and assembles.
    """
    ledger, schema = baseline
    _point_at(
        monkeypatch, fluree_url=fluree_url, ledger=ledger, dsn=postgres_dsn, schema=schema
    )
    outcome, seen = _assemble_keeping_the_return()
    assert isinstance(outcome, AssemblyOutcome), (
        f"the unperturbed estate was REFUSED: {type(outcome).__name__} {outcome!r}"[:600]
    )
    assert any(getattr(entry, "served", None) is not None for entry in seen)
