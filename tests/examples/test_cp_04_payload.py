"""Six of cp-04's sixteen gates — the payload set, the findings set and the ontology-serving set.

`CFT-G06`, `CFT-G07`, `CFT-G08`, `CFT-G09`, `CFT-G15` and `CFT-G16`, discharging
locked ROADMAP criteria 30, 31, 32, 33, 39 and 40, plus criterion 10's PRODUCT
half — the duplicate pair is surfaced by the product rather than served as two
distinct subsidiaries. Each gate is written so that the sabotage
`artifacts/gates.yaml` declares against it turns THIS module red, under THAT
gate's own name, which is the whole content of criterion 42.

## What this module refuses to be

**A check that reads a token present in BOTH the compliant and the violating
case measures vocabulary rather than content.** Phase 24.3 shipped that defect
seven times, and plan `24.4-10` measured a fresh instance of it on this very
ladder: `CFT-G05` written as its criterion words it — *"two depths are two
content addresses"* — PASSES its own sabotage, because ``max_depth_applied`` is
echoed into the sealed payload, so the address moves even when the walk has
stopped reading depth at all. **A content-address comparison is not by itself
evidence that the thing you sabotaged is what produced the difference.** Every
gate below therefore asserts CONTENT — a roster, a member set, a served value —
and never an address, a length or a word the product uses about itself.

**AMENDED 2026-09-01 (Dave), FOR ONE LIMB OF ONE GATE.** The sentence above is
preserved because it is the reason the exception is narrow, and it is stricken
only for `CFT-G16`'s pinned-address limb. Dave, at the build evaluation: *"Keep
both addresses and the 22→0 detailed count in the expected block / README so a
later 'role is cosmetic' regression cannot hide behind a still-green tree of
22."* **The reason a content assertion cannot reach this one:** the two declared
roles are served the SAME 22 members by design, so every roster in this module —
`CFT-G09`'s twenty, criterion 10's pair, `CFT-G15`'s chains, and `CFT-G16`'s own
first limb — is UNMOVED when the role stops conditioning anything. The seal and
the detailed count are the only declared figures that move. **What keeps the limb
an assertion about content rather than about an address:** the addresses are
pinned EXACTLY, one per role, in `artifacts/expected.yaml`. A *"the two addresses
differ"* check would be the `CFT-G05` defect again — ``perspective_role`` is
echoed into the sealed payload, so two addresses appear even when the role is
read for its name and never for its meaning.

## Rosters, never counts

`D-13`: a right count with a wrong member audits clean forever. Criterion 23's
control in plan `24.4-05` is the measured demonstration — a substituted detector
returns the RIGHT NUMBER of cycles with a WRONG third member, so
``len(findings) > 0`` passes and so would ``len(findings) == 2``. Nothing in
this module asserts a finding count, and
:func:`test_this_module_asserts_no_finding_count` holds that by scanning this
file's own source.

## Where every expected figure comes from

`artifacts/expected.yaml`, and nowhere else (criterion 45). A number authored
here would be this module agreeing with itself about what the estate holds. The
rosters read are `census.cycle_1` (the ordered members, the closing edge, the
type and the predicate), `census.cycle_2` (asserted ABSENT from a served
payload, with the measured reason), `census.anchor` (the seven-class chain),
`census.anchor_subtree` (the 22 reachable members),
`census.duplicate_entity_pair` (both names and which one carries the LEI),
`unresolved_subtree_members` (the twenty with no PostgreSQL row) and
`perspective_detailed_members` with `perspective_discriminating_class` (the two
roles' views and the class that explains the difference) and
`perspective_content_addresses` (the address each role's whole served vessel
seals to). The declared 22-member family roster is not a key of its own: it is
DERIVED from `unresolved_subtree_members` and
`census.anchor_subtree_store_split.the_two_resolving`, and
:func:`declared_family_roster` asserts that the derivation still totals the
`census.anchor_subtree.reachable_nodes` the same document declares, so a
shrunken declaration is a failure rather than a smaller expectation.

**The one figure NOT read from that document is the refused parameter's name and
its declared reason** — `as_of` and `not_supported_at_tier`. Those are
assertions ABOUT the declaration, exactly as `CFT-G03` and `CFT-G04` are
assertions about the declared depth bounds, so they are read from
`examples/cp-04-corporate-family-tree/ccf_config.yaml` through
``examples/cp-04-corporate-family-tree/deployment.py::unsupported_arguments``.
Reading them from anywhere else would assert a coincidence instead of a
dependency, and no sabotage in this plan touches a declaration.

## What is deliberately NOT here

**`CFT-G17` does not exist and no test below asserts a type-constrained stop.**
Criterion 41 was WITHDRAWN IN PLACE on 2026-08-31 (Dave) together with ontology
role 1, and is discharged by the id's ABSENCE from the roster rather than by a
gate. It is **not** replaced by a positive-property restatement.

**No `as_of` pin and no depth clamp.** `as_of` appears below only as the
parameter `CFT-G06` watches being refused; the clamp appears nowhere at all.

## Isolation

Per-module ledger and schema names from `tests/examples/cp_04_seed.py`, for the
reason that module records: `tests/conftest.py::fluree_url` is session-scoped
and env-driven — one server, no per-module container — and six cp-04 modules
transact this one fixture. A fixed ledger name means whichever module ran second
cannot seed at all (`409 err:db/LedgerExists`), and a shared one means a sibling
module's deliberate sabotage leaks into this module's answers permanently,
because Fluree is append-only. Shared CI fixtures colliding by collection order
have already left `leg-postgres` red on `main` in this repository once.

## Vacuity

A precondition test runs first and asserts the seed carries what these gates
need. Without it a green gate could be a true statement about nothing. Every
gate is expressed as a function returning the ways an observation FAILS, so a
control can hand the **shipped** check a divergent subject and be watched
refusing it — a check that can only ever be handed the passing subject is a
check nobody has watched fail.
"""

from __future__ import annotations

import ast
import importlib
import pathlib
import sys
import tempfile
from dataclasses import dataclass
from typing import Any, Iterator, Mapping, Sequence

import pytest
import yaml

from ccf.agents.errors import AssemblyRefused

from .cp_04_seed import ledger_for, schema_for, seed

REPO = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO / "examples" / "cp-04-corporate-family-tree"
EXPECTED = EXAMPLE / "artifacts" / "expected.yaml"

#: Both stores. `.github/workflows/ci.yml` exports both legs' variables at JOB
#: level and runs `leg-postgres` and `leg-fluree` as two steps of that one job,
#: so a doubly-marked module is selected twice and runs whole both times.
pytestmark = [pytest.mark.fluree, pytest.mark.postgres]

#: The status a declared-but-inert parameter is refused with, from locked
#: ROADMAP criterion 30 and Standard section 9's *"400 not_supported_at_tier"*.
#:
#: **AUTHORED HERE, DELIBERATELY, AND IT IS THE ONE FIGURE THAT IS.** The
#: shipped verdict type carries this number as its own default, and
#: ``examples/cp-04-corporate-family-tree/produce.py`` is the file `CFT-G06`'s
#: sabotage MUTATES — so reading the status from there would put the gate's
#: expectation and the product's behavior in one file, which is the shape that
#: lets a gate pass its own sabotage. Criterion 45 scopes the
#: read-it-from-`expected.yaml` rule to the criteria 3–18 census figures, and a
#: status code is not one of them: it comes from the Standard rather than from
#: the estate. :func:`test_the_seed_carries_what_these_six_gates_need` asserts
#: the shipped type still agrees with it, so a drift is a failure rather than a
#: divergence nobody looks at.
DECLARED_REFUSAL_STATUS = 400

#: The finding type the duplicate pair is reported under, and the one the
#: twenty row-less members are reported under. Read from the shipped modules
#: rather than spelled here, so a product that renamed either is a failure in
#: the gate's subject rather than a silent miss.
#:
#: **The CYCLE type is read from `expected.yaml::census.cycle_1.type` instead**,
#: because ``projection.py`` is the file `CFT-G07`'s and `CFT-G08`'s sabotages
#: mutate. **`FINDING_UNRESOLVED_JURISDICTION` lives in that same file and the
#: overlap is recorded rather than glossed:** what `CFT-G09` compares is the
#: declared ROSTER from `expected.yaml`, and its size limb reads the served
#: member set — neither moves with a renamed constant, and no sabotage in this
#: plan touches the constant. Said out loud because an unstated overlap is how a
#: gate comes to pass its own sabotage.
#:
#: Resolved lazily in :func:`finding_types` because the example's modules are
#: loaded through :func:`_load`, which is import-order sensitive.
DUPLICATE_FINDING_ATTR = "FINDING_DUPLICATE_ENTITY"
UNRESOLVED_FINDING_ATTR = "FINDING_UNRESOLVED_JURISDICTION"


def _load(name: str) -> Any:
    """Load one of the example's modules under its own bare name.

    The example is a directory of modules rather than a package and its modules
    import each other by bare name, while one pytest session runs over a tree
    holding several `deployment`/`produce`/`run` triples. So the cache is
    checked against THIS example's directory and the whole family is evicted
    together when it holds somebody else's — evicting one name at a time would
    rebuild the split-identity problem the eviction prevents. The shape is
    `tests/examples/test_cp_04_traversal.py::_load`.
    """
    if sys.path[:1] != [str(EXAMPLE)]:
        while str(EXAMPLE) in sys.path:
            sys.path.remove(str(EXAMPLE))
        sys.path.insert(0, str(EXAMPLE))
    family = ("deployment", "produce", "projection", "assembler", "transport", "run")
    for cached_name in family:
        cached = sys.modules.get(cached_name)
        if cached is None:
            continue
        if not str(getattr(cached, "__file__", "")).startswith(str(EXAMPLE)):
            for sibling in family:
                sys.modules.pop(sibling, None)
            break
    return importlib.import_module(name)


# ---------------------------------------------------------------------------
# The declared expectations, read from the artifact and never authored here.
# ---------------------------------------------------------------------------


def declared() -> Mapping[str, Any]:
    """`artifacts/expected.yaml`'s declaration block."""
    return dict(yaml.safe_load(EXPECTED.read_text(encoding="utf-8"))["declaration"])


def census(block: str) -> Mapping[str, Any]:
    """One named `census:` block of the declared expectations."""
    return dict(declared()["census"][block])


def local_name(iri: str) -> str:
    """The local name of one IRI — `deployment.py`'s own derivation.

    The payload carries full IRIs and `expected.yaml` carries the census
    vocabulary of LOCAL names, so every roster comparison below folds one side
    through this. :func:`test_the_seed_carries_what_these_six_gates_need`
    asserts the derivation is total over the served set rather than assuming it.
    """
    return str(iri).rsplit("/", 1)[-1]


def finding_types() -> Mapping[str, str]:
    """The three finding type tokens, and the file each is read from.

    ``cycle`` comes from `artifacts/expected.yaml`, which no sabotage in this
    plan touches; ``duplicate`` from
    ``examples/cp-04-corporate-family-tree/deployment.py``, which no sabotage in
    this plan touches either; ``unresolved`` from
    ``examples/cp-04-corporate-family-tree/projection.py``, which two of them
    do — see :data:`UNRESOLVED_FINDING_ATTR` for why that overlap does not let
    `CFT-G09` pass its own sabotage.
    """
    deployment = _load("deployment")
    projection = _load("projection")
    return {
        "cycle": str(census("cycle_1")["type"]),
        "duplicate": str(getattr(deployment, DUPLICATE_FINDING_ATTR)),
        "unresolved": str(getattr(projection, UNRESOLVED_FINDING_ATTR)),
    }


def declared_unresolved_members() -> tuple[str, ...]:
    """The twenty SMCI-subtree members that resolve to no `legal_entity` row.

    Appended to `expected.yaml` by wave 5 precisely so `CFT-G09` has a source
    for its roster OTHER THAN ITSELF. `D-IMPL-229` records why the roster and
    not the count: a check reading the served jurisdiction SET measures
    vocabulary — the set is unchanged at ``{NL, US-DE}`` under the struck
    fill-from-anchor rule — while this roster collapses from twenty to nothing.
    """
    return tuple(str(name) for name in declared()["unresolved_subtree_members"])


def declared_addresses() -> Mapping[str, str]:
    """The content address `artifacts/expected.yaml` pins for each declared role.

    Appended to that document on 2026-09-01 under `D-IMPL-233` precisely so
    `CFT-G16`'s pinned-address limb has a source OTHER THAN THIS FILE. **A hash
    written into a test module can be "corrected" in one edit beside the change
    that moved it** — a regression and its own repair arriving in one commit,
    reviewed as a refreshed transcript. A hash in the reviewed artifact cannot
    be: that document derives nothing from a run and says so in its own header,
    so moving it is an edit to a reviewed expectation.
    """
    return {
        str(role): str(address)
        for role, address in declared()["perspective_content_addresses"].items()
    }


def declared_family_roster() -> tuple[str, ...]:
    """The members this family serves, as a ROSTER, derived from two blocks.

    `D-13`: a right count with a wrong member audits clean forever, so what the
    two views are compared against is NAMES. `expected.yaml` declares the family
    in two halves rather than as one list — the members that resolve to no
    `legal_entity` row, and the ones that do — and the union is taken here
    rather than authored, because a third place for the same names would be a
    third place for them to be wrong.

    The union is checked against `census.anchor_subtree.reachable_nodes` from
    that same document, so a declaration that lost a member fails here rather
    than quietly shrinking what `CFT-G16` compares against.
    """
    roster = set(declared_unresolved_members())
    roster |= {
        str(row["uri"])
        for row in census("anchor_subtree_store_split")["the_two_resolving"]
    }
    reachable = int(census("anchor_subtree")["reachable_nodes"])
    assert len(roster) == reachable, (
        f"expected.yaml's two halves of the served family total {len(roster)}"
        f" distinct members where census.anchor_subtree declares {reachable}"
        " reachable. The roster CFT-G16 compares against is derived from those"
        " halves, so a disagreement would silently shrink the comparison"
    )
    return tuple(sorted(roster))


# ---------------------------------------------------------------------------
# One ask, reduced to what these six gates read.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Asked:
    """What one ask produced: a served product, or a refusal, never both.

    A value rather than a raise, so `CFT-G06` can inspect BOTH limbs of its
    question in one function — *was it refused by name* and *was a product
    served anyway*. A gate that only caught the exception could not tell a
    refusal from a refusal-plus-a-served-tree, and cp-03's own close-panel
    finding was exactly that: a gate checking the captured verdict could pass
    *"while a product could satisfy it and complete the assembly normally"*.
    """

    #: How it was asked, carried into every failure message so a disagreement
    #: names its subject rather than leaving it to be inferred.
    asked_as: str
    #: The served payload, or ``None`` when nothing was served.
    payload: Mapping[str, Any] | None
    #: `sha256` over the vessel's canonical bytes, computed producer-side.
    #: Read by NO gate below as evidence of content — see the module docstring.
    content_address: str | None
    #: The refusal text, or ``None`` when the ask was answered.
    refusal: str | None
    #: The class name of everything the assembly's own observer saw, in order.
    observed: tuple[str, ...]
    #: The class name of every observed value that CARRIED a served vessel. A
    #: roster rather than a flag: `CFT-G06`'s second limb is that the assembly
    #: served nothing, and the names say what it served if it did.
    served_vessels: tuple[str, ...]

    @property
    def nodes(self) -> tuple[Mapping[str, Any], ...]:
        if self.payload is None:
            return ()
        return tuple(dict(node) for node in self.payload["nodes"])

    @property
    def findings(self) -> tuple[Mapping[str, Any], ...]:
        if self.payload is None:
            return ()
        return tuple(dict(finding) for finding in self.payload["findings"])

    @property
    def roster(self) -> tuple[str, ...]:
        """The served member roster by LOCAL name, sorted. Never a count."""
        return tuple(sorted(local_name(node["uri"]) for node in self.nodes))

    def findings_of(self, kind: str) -> tuple[Mapping[str, Any], ...]:
        return tuple(finding for finding in self.findings if finding["type"] == kind)


def ask(
    *,
    asked_as: str,
    max_depth: int | None = None,
    omit_max_depth: bool = False,
    role: str | None = None,
    extra: Mapping[str, Any] | None = None,
    plan_class: Any = None,
) -> Asked:
    """Ask this deployment one question through the shipped in-process caller.

    Not a reimplementation of the product: the same
    ``ProductClient(product_id=…, adapter=…)`` constructor `run.py` builds
    (`D-IMPL-225` amendment 2), over the same
    ``examples/cp-04-corporate-family-tree/transport.py::FamilyTreeInProcessAdapter``,
    carrying the question
    ``examples/cp-04-corporate-family-tree/deployment.py::demonstration_request``
    composes for both callers.

    ``extra`` puts values on the wire the bundled demonstration does not carry,
    which is what `CFT-G06` needs: `as_of` is DECLARED in the request contract —
    so a caller can discover it — and always refused, and the demonstration
    question never names it.

    ``role`` reaches the adapter's constructor and never the wire, because the
    request contract is a closed declared world (`D-IMPL-98`) and ``role`` is
    not one of its arguments. ``plan_class`` substitutes the projection class
    the adapter hands the spine, which is how `CFT-G16`'s mechanism control
    drives ONE mutated class chain through the SHIPPED projection.

    A refusal the assembler RAISES is caught and returned as data —
    ``AssemblyRefused`` is not in ``ccf.products.refusal::REFUSAL_KINDS`` and has
    no envelope, which `transport.py`'s own docstring records as an SDK-surface
    gap rather than papering over. A refusal it RETURNS arrives on the `Result`.
    """
    from ccf.client.client import ProductClient

    deployment = _load("deployment")
    projection = _load("projection")
    transport = _load("transport")

    typed = deployment.demonstration_request(max_depth=max_depth)
    parameters = {
        name: (value if isinstance(value, (str, int, bool)) else format(value, "f"))
        for name, value in typed.parameters.items()
    }
    if omit_max_depth:
        parameters.pop(deployment.PARAM_MAX_DEPTH, None)
    parameters.update(dict(extra or {}))

    patch = pytest.MonkeyPatch()
    if plan_class is not None:
        patch.setattr(projection, "plan_class", lambda: plan_class)
    try:
        with tempfile.TemporaryDirectory(prefix="cp04-payload-") as scratch:
            adapter = transport.FamilyTreeInProcessAdapter(
                root=pathlib.Path(scratch), role=role
            )
            client = ProductClient(
                product_id=transport.declared_product_id(), adapter=adapter
            )
            try:
                result = client.ask(parameters, as_of=typed.asked_at)
            except AssemblyRefused as refused:
                return _asked(
                    asked_as=asked_as,
                    adapter=adapter,
                    payload=None,
                    address=None,
                    refusal=f"{type(refused).__name__}: {refused}",
                )
            if result.refused:
                return _asked(
                    asked_as=asked_as,
                    adapter=adapter,
                    payload=None,
                    address=None,
                    refusal=str(result.refusal),
                )
            return _asked(
                asked_as=asked_as,
                adapter=adapter,
                payload=dict(result.payload),
                address=str(result.content_address),
                refusal=None,
            )
    finally:
        patch.undo()


def _asked(
    *,
    asked_as: str,
    adapter: Any,
    payload: Mapping[str, Any] | None,
    address: str | None,
    refusal: str | None,
) -> Asked:
    """Fold one ask and what the assembly's own observer saw into a value.

    ``adapter.seen`` is the assembly's observer callback, which the spine calls
    with whatever one run produced — a served assembly, or the verdict that
    stopped it. It is read here rather than reconstructed because it is the one
    place a *served vessel* is visible on a path that RAISED, and `CFT-G06`'s
    second limb needs exactly that.
    """
    observed = tuple(type(value).__name__ for value in adapter.seen)
    served = tuple(
        type(value).__name__
        for value in adapter.seen
        if getattr(value, "served", None) is not None
    )
    return Asked(
        asked_as=asked_as,
        payload=payload,
        content_address=address,
        refusal=refusal,
        observed=observed,
        served_vessels=served,
    )


# ---------------------------------------------------------------------------
# The estate, and the environment the deployment reads it through.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def estate(fluree_url: str, postgres_dsn: str) -> Iterator[tuple[str, str]]:
    """The committed fixture pair, under names nobody else holds."""
    ledger = ledger_for(__name__)
    schema = schema_for(__name__)
    seed(fluree_url, ledger, postgres_dsn, schema)

    patch = pytest.MonkeyPatch()
    for variable, value in (
        ("CCF_CP_04_FLUREE_URL", fluree_url.rstrip("/")),
        ("CCF_CP_04_FLUREE_LEDGER", ledger),
        ("CCF_CP_04_POSTGRES_DSN", postgres_dsn),
        ("CCF_CP_04_POSTGRES_SCHEMA", schema),
    ):
        patch.setenv(variable, value)
    try:
        yield ledger, schema
    finally:
        patch.undo()


@pytest.fixture(scope="module")
def served(estate: tuple[str, str]) -> Asked:
    """One ask at the declared default depth, under the declared default role."""
    return ask(asked_as="the declared default depth and role", omit_max_depth=True)


@pytest.fixture(scope="module")
def asked_with_as_of(estate: tuple[str, str]) -> Asked:
    """One ask naming the DECLARED-BUT-INERT parameter — `CFT-G06`'s subject.

    The parameter name is read from
    ``examples/cp-04-corporate-family-tree/deployment.py::unsupported_arguments``
    rather than spelled here, so a deployment that stopped refusing it — or
    started refusing a second one — moves this fixture's subject rather than
    leaving it asking about a parameter nobody declares.
    """
    deployment = _load("deployment")
    names = sorted(deployment.unsupported_arguments())
    return ask(
        asked_as=f"the declared-but-inert parameter {names[0]!r} supplied",
        omit_max_depth=True,
        # A value in the shape the contract declares — `type: string`. What is
        # under test is that the parameter is refused, never that a malformed
        # value is rejected, so the value is well-formed on purpose.
        extra={names[0]: "2026-03-31T00:00:00+00:00"},
    )


# ---------------------------------------------------------------------------
# PRECONDITIONS — what a green gate below is allowed to mean.
# ---------------------------------------------------------------------------


def test_the_seed_carries_what_these_six_gates_need(served: Asked) -> None:
    """Without this, a green gate could be a true statement about nothing.

    Seven things, each one a way a gate below could pass while measuring
    nothing: an empty node set, an empty finding set, a cycle roster shorter
    than a circuit, an unresolved roster that is empty or is the whole served
    set, a declaration that no longer refuses any parameter, a class axis no
    served node carries, and an IRI no local name derives from.
    """
    deployment = _load("deployment")
    kinds = finding_types()

    assert served.payload is not None, (
        f"the ask `{served.asked_as}` was refused — {served.refusal!r}. Every"
        " gate below reads a served payload"
    )
    assert served.nodes, (
        "the ask served no nodes at all, so every per-node gate below would be"
        " a true statement about the empty set"
    )
    assert served.findings, (
        "the ask served no findings at all, so CFT-G07 and CFT-G08 would be"
        " satisfied vacuously by a product that reports nothing"
    )

    cycle_one = census("cycle_1")
    assert len(cycle_one["members"]) >= 3, (
        "expected.yaml declares a cycle-1 roster shorter than a circuit, so the"
        f" ORDER assertion CFT-G07 makes cannot bite: {cycle_one['members']}"
    )
    assert len(cycle_one["closing_edge"]) == 2, (
        "expected.yaml declares a closing edge that is not a pair, so CFT-G07's"
        " fourth field has nothing to be compared against"
    )

    unresolved = declared_unresolved_members()
    assert unresolved, (
        "expected.yaml declares no unresolved subtree members, so CFT-G09 would"
        " assert a roster of nothing and a build that dropped every member"
        " would satisfy it"
    )
    assert set(unresolved) < set(served.roster), (
        "the declared unresolved roster is not a PROPER subset of the served"
        f" roster — declared {sorted(unresolved)}, served {sorted(served.roster)}."
        " If the two coincide, CFT-G09 cannot tell 'no member was dropped' from"
        " 'the roster is everything'"
    )

    inert = deployment.unsupported_arguments()
    assert len(inert) == 1, (
        f"this deployment declares {sorted(inert)} as declared-but-inert. CFT-G06"
        " reads the single declared name; a second one would leave the gate"
        " asserting a refusal for one parameter while another went unwatched"
    )
    shipped_status = int(
        _load("produce").ParameterNotSupported(parameter="x", reason="y").status
    )
    assert shipped_status == DECLARED_REFUSAL_STATUS, (
        f"the shipped verdict refuses with status {shipped_status} where"
        f" criterion 30 and Standard section 9 declare {DECLARED_REFUSAL_STATUS}."
        " The gate asserts the DECLARED number rather than the shipped one, so"
        " a drift is reported here rather than absorbed"
    )

    axis = deployment.class_axis_iri()
    carrying = [
        local_name(node["uri"])
        for node in served.nodes
        if axis in tuple(node["type_chain"])
    ]
    assert carrying, (
        f"no served node carries the declared class axis {axis!r}, so CFT-G16's"
        " conditioning has nothing to condition on and both roles would see the"
        " same view for a reason having nothing to do with the class"
    )

    for node in served.nodes:
        for iri in node["type_chain"]:
            assert local_name(iri), f"no local name derives from {iri!r}"

    assert set(kinds.values()) <= {finding["type"] for finding in served.findings}, (
        "the served findings do not carry all three declared finding types —"
        f" declared {sorted(kinds.values())}, served"
        f" {sorted({finding['type'] for finding in served.findings})}"
    )


def test_this_module_asserts_no_finding_count() -> None:
    """`D-13`, held against this file's own source rather than against a habit.

    A right count with a wrong member audits clean forever. Criterion 23's
    control measured it on this estate: a substituted detector returns TWO
    findings with a wrong third member on cycle 1, so ``len(findings) > 0``
    passes and so does ``len(findings) == 2``. The scan is over the parsed
    source rather than over lines, so a count spelled across two lines is
    caught too.
    """
    source = pathlib.Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    offenders: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not (isinstance(node.func, ast.Name) and node.func.id == "len"):
            continue
        for argument in node.args:
            rendered = ast.unparse(argument)
            if "finding" in rendered.lower():
                offenders.append(f"len({rendered}) at line {node.lineno}")
    assert not offenders, (
        "this module counts findings instead of naming them, which is the"
        f" roster-blind assertion D-13 forbids: {offenders}"
    )


# ---------------------------------------------------------------------------
# CFT-G06 — `as_of` is refused `400 not_supported_at_tier`, and nothing served.
# ---------------------------------------------------------------------------


def inert_parameter_violations(
    asked: Asked, *, parameter: str, reason: str, status: int
) -> list[str]:
    """Every way a declared-but-inert ask fails `CFT-G06`.

    **Three limbs, and the third is the one a reason-string check cannot see.**
    The dangerous outcome is not the refusal; it is ACCEPTING the parameter and
    ignoring it, which answers a question about today while the caller believes
    they asked about a past date. A product could note the parameter, emit the
    declared reason, and serve the tree anyway — cp-03's close panel found
    precisely that shape in its own `OFS-G06`, where the gate inspected the
    captured verdict and *"a product could satisfy it while completing the
    assembly normally"*. So this asserts the status, the declared reason, the
    parameter's name, that NO payload came back, AND that the assembly served
    no vessel at all.
    """
    violations: list[str] = []
    if asked.payload is not None:
        violations.append(
            f"CFT-G06: {parameter!r} was ANSWERED rather than refused — a tree"
            f" came back over {len(asked.nodes)} members. A silently honored"
            f" {parameter} answers a question about today while the caller"
            " believes they asked about a past date, and nothing in the payload"
            " would say so"
        )
    if asked.served_vessels:
        violations.append(
            f"CFT-G06: the assembly SERVED {list(asked.served_vessels)} while"
            f" {parameter!r} was on the wire. A refusal beside a served product"
            " is not a refusal — it is a product with a note attached"
        )
    if asked.payload is not None or asked.served_vessels:
        return violations
    if not asked.refusal:
        violations.append(
            f"CFT-G06: {parameter!r} produced neither a product nor a refusal,"
            " so nothing was observed at all"
        )
        return violations
    if str(status) not in asked.refusal:
        violations.append(
            f"CFT-G06: the refusal does not name the status {status} —"
            f" {asked.refusal!r}. Standard section 9 requires a DISTINCT"
            " condition, and a refusal that does not carry its status cannot be"
            " told from any other 'no'"
        )
    if reason not in asked.refusal:
        violations.append(
            f"CFT-G06: the refusal does not carry the DECLARED reason"
            f" {reason[:60]!r}… — {asked.refusal!r}. The reason is Control Plane"
            " state; a refusal wording its own would leave the declaration"
            " meaning nothing"
        )
    if parameter not in asked.refusal:
        violations.append(
            f"CFT-G06: the refusal does not name {parameter!r} —"
            f" {asked.refusal!r}, so it is not demonstrably about this parameter"
        )
    return violations


def test_cft_g06_as_of_is_refused_not_supported_at_tier(
    asked_with_as_of: Asked,
) -> None:
    """`CFT-G06` (criterion 30). The declared-but-inert parameter is refused.

    Three limbs held together: the refusal happened and it names the status, the
    declared reason and the parameter; no payload came back; and the assembly
    served no vessel. The third is what a check reading only the reason string
    cannot see.

    Sabotaged by silently honoring it.
    """
    deployment = _load("deployment")
    inert = deployment.unsupported_arguments()
    parameter = sorted(inert)[0]
    violations = inert_parameter_violations(
        asked_with_as_of,
        parameter=parameter,
        reason=str(inert[parameter]).strip(),
        status=DECLARED_REFUSAL_STATUS,
    )
    assert not violations, (
        f"CFT-G06 failed against {asked_with_as_of.asked_as}:\n"
        + "\n".join(violations)
    )


def test_the_inert_check_refuses_a_silently_honored_parameter() -> None:
    """**Positive control.** A served tree is the sabotage, not the refusal."""
    honored = Asked(
        asked_as="as_of honored",
        payload={"nodes": [{"uri": "x://a"}], "edges": [], "findings": []},
        content_address="deadbeef",
        refusal=None,
        observed=("Assembled",),
        served_vessels=("Assembled",),
    )
    violations = inert_parameter_violations(
        honored, parameter="as_of", reason="not_supported_at_tier", status=400
    )
    assert violations, "a silently honored parameter was reported as refused"
    assert any("ANSWERED rather than refused" in entry for entry in violations), (
        violations
    )


def test_the_inert_check_refuses_a_refusal_beside_a_served_product() -> None:
    """**Positive control**, and the one a reason-string check cannot make.

    The refusal text is perfect and the assembly served a vessel anyway. cp-03's
    close panel found this shape in its own gate; here it is refused by name.
    """
    both = Asked(
        asked_as="as_of refused and served",
        payload=None,
        content_address=None,
        refusal="AssemblyRefused: 400 not_supported_at_tier: as_of",
        observed=("Assembled",),
        served_vessels=("Assembled",),
    )
    violations = inert_parameter_violations(
        both, parameter="as_of", reason="not_supported_at_tier", status=400
    )
    assert violations, "a refusal beside a served product was accepted"
    assert any("the assembly SERVED" in entry for entry in violations), violations


def test_the_inert_check_refuses_a_refusal_that_names_nothing() -> None:
    """**Positive control.** *It raised* is not *it refused by name*."""
    vague = Asked(
        asked_as="a refusal naming nothing",
        payload=None,
        content_address=None,
        refusal="AssemblyRefused: something went wrong",
        observed=("ParameterNotSupported",),
        served_vessels=(),
    )
    violations = inert_parameter_violations(
        vague, parameter="as_of", reason="not_supported_at_tier", status=400
    )
    assert violations, "a refusal naming neither status nor reason was accepted"
    assert any("does not name the status" in entry for entry in violations), violations


# ---------------------------------------------------------------------------
# CFT-G07 — a cycle carries type, ORDERED members and the closing edge.
# ---------------------------------------------------------------------------


def cycle_violations(
    findings: Sequence[Mapping[str, Any]], declared_cycle: Mapping[str, Any], kind: str
) -> list[str]:
    """Every way the served cycle finding fails `CFT-G07`.

    **All four fields, and the members compared as an ORDERED sequence.** A set
    comparison would pass on a rotation, and a rotation names a DIFFERENT
    closing edge — the same three companies with the wrong arrow between two of
    them. `expected.yaml::census.cycles.roster_order_convention` pins the order
    (rotate to the lexicographically smallest member) precisely so the ordered
    comparison is stable across runs rather than a coincidence of traversal.

    **Never a count.** `D-13`, and criterion 23's control is the measured
    reason: a substituted detector returns the right NUMBER of findings with a
    wrong third member on cycle 1.
    """
    matching = [finding for finding in findings if finding["type"] == kind]
    if not matching:
        return [
            f"CFT-G07: no finding of type {kind!r} reached the consumer. The"
            " headline finding of this product is a cycle, and a family that"
            " contains one and does not say so is the answer this gate exists"
            " to refuse"
        ]
    if len(matching) != 1:
        return [
            f"CFT-G07: {len(matching)} findings of type {kind!r} reached the"
            " consumer where the anchor's subtree reaches exactly one circuit."
            " expected.yaml::census.external_edges_into_any_cycle records that"
            " the anchor's single edge into cycle 1 is the only path from the"
            " LEI-bearing population into either cycle"
        ]

    finding = matching[0]
    violations: list[str] = []
    served_members = tuple(local_name(member) for member in finding["members"])
    want_members = tuple(str(member) for member in declared_cycle["members"])
    if served_members != want_members:
        violations.append(
            f"CFT-G07: the cycle's members reached the consumer as"
            f" {list(served_members)} where expected.yaml declares"
            f" {list(want_members)}. Compared as an ORDERED sequence: the same"
            " set in a different order is a different circuit, naming a"
            " different closing edge"
        )
    closing = finding["closing_edge"]
    if closing is None:
        violations.append(
            "CFT-G07: the cycle reached the consumer with NO closing edge. A"
            " cycle is a set PLUS the edge that closes it, and the closing edge"
            " is precisely what a flattened representation loses — the members"
            " survive, every count stays right, and the arrow that makes it a"
            " circuit is gone"
        )
    else:
        served_closing = tuple(local_name(member) for member in closing)
        want_closing = tuple(str(member) for member in declared_cycle["closing_edge"])
        if served_closing != want_closing:
            violations.append(
                f"CFT-G07: the closing edge reached the consumer as"
                f" {list(served_closing)} where expected.yaml declares"
                f" {list(want_closing)}"
            )
    if finding["predicate"] != declared_cycle["predicate"]:
        violations.append(
            f"CFT-G07: the cycle is attributed to predicate"
            f" {finding['predicate']!r} where expected.yaml declares"
            f" {declared_cycle['predicate']!r}"
        )
    if finding["type"] != declared_cycle["type"]:
        violations.append(
            f"CFT-G07: the cycle carries type {finding['type']!r} where"
            f" expected.yaml declares {declared_cycle['type']!r}"
        )
    return violations


def test_cft_g07_a_cycle_carries_type_ordered_members_and_closing_edge(
    served: Asked,
) -> None:
    """`CFT-G07` (criterion 31). A cycle reaches the consumer whole.

    All four fields, with the members compared as an ORDERED sequence against
    `expected.yaml::census.cycle_1` and the closing edge against the pair
    declared beside them.

    Sabotaged by dropping the closing edge.
    """
    violations = cycle_violations(
        served.findings, census("cycle_1"), finding_types()["cycle"]
    )
    assert not violations, (
        f"CFT-G07 failed against {served.asked_as}:\n" + "\n".join(violations)
    )


def test_the_cycle_check_refuses_a_dropped_closing_edge() -> None:
    """**Positive control.** The closing edge is what a flattening loses."""
    declared_cycle = census("cycle_1")
    flattened = [
        {
            "type": declared_cycle["type"],
            "predicate": declared_cycle["predicate"],
            "members": list(declared_cycle["member_iris"]),
            "closing_edge": None,
        }
    ]
    violations = cycle_violations(
        flattened, declared_cycle, str(declared_cycle["type"])
    )
    assert violations, "a cycle with no closing edge was reported as whole"
    assert any("NO closing edge" in entry for entry in violations), violations


def test_the_cycle_check_refuses_a_rotated_roster() -> None:
    """**Positive control**, and the reason the comparison is ordered.

    The same three companies, entered from a different node. Every member is
    present, the count is right, and the closing edge it implies is an arrow
    that does not exist. A set comparison accepts it.
    """
    declared_cycle = census("cycle_1")
    members = list(declared_cycle["member_iris"])
    rotated = [
        {
            "type": declared_cycle["type"],
            "predicate": declared_cycle["predicate"],
            "members": members[1:] + members[:1],
            "closing_edge": list(declared_cycle["closing_edge"]),
        }
    ]
    violations = cycle_violations(rotated, declared_cycle, str(declared_cycle["type"]))
    assert violations, "a rotated roster was reported as the declared circuit"
    assert any("ORDERED sequence" in entry for entry in violations), violations


def test_the_cycle_check_refuses_a_product_with_no_cycle_at_all() -> None:
    """**Vacuity control.** Silence about a circuit is not orthogonality."""
    violations = cycle_violations([], census("cycle_1"), "ownership_cycle")
    assert violations, "a product reporting no cycle was reported as compliant"
    assert any("no finding of type" in entry for entry in violations), violations


# ---------------------------------------------------------------------------
# CFT-G08 — findings are ORTHOGONAL to the tree.
# ---------------------------------------------------------------------------


def _flatten(node: Mapping[str, Any], prefix: str = "") -> dict[str, str]:
    """One served node block as ``path -> rendered value`` pairs.

    Nested because a marker hidden one level down — inside ``conditioning``, say
    — is still a marker on the node, and a check reading only the top-level keys
    would not see it.
    """
    flat: dict[str, str] = {}
    for key, value in node.items():
        path = f"{prefix}{key}"
        if isinstance(value, Mapping):
            flat.update(_flatten(value, prefix=f"{path}."))
        else:
            flat[path] = repr(value)
    return flat


def orthogonality_violations(
    nodes: Sequence[Mapping[str, Any]],
    findings: Sequence[Mapping[str, Any]],
    *,
    cycle_kind: str,
) -> list[str]:
    """Every way the served tree fails `CFT-G08`.

    **Two limbs, and the first reads CONTENT rather than a word.** A node-level
    cycle marker is any field whose value PARTITIONS the served set into exactly
    the cycle roster — ``in_cycle: true`` on three members and ``false`` on the
    rest, ``cycle_id: 1`` and ``null``, or any renaming of either. A check
    looking for the token "cycle" among the node keys measures vocabulary: it
    passes against a marker called ``flagged``. So this asks whether any field
    of the node block tells the cycle members apart from the rest, whatever it
    is named, and reports the field that does.

    **The second limb is positive**, so the gate cannot be satisfied by a
    product that has no findings at all: the cycle must be present in
    ``findings[]``, carrying its own members. Orthogonality without the finding
    is silence, and silence about a circuit is the worse answer.

    Measured against the shipped product before the sabotage was written: no
    field of a served node partitions the 22 members into the cycle's three.
    ``lei`` and ``attributes`` are null on twenty, ``depth`` takes three
    different values across the three, ``type_chain`` and ``conditioning`` are
    identical across all 22, and ``uri``, ``entity_id`` and ``label`` are
    distinct per member.
    """
    violations: list[str] = []
    cycles = [finding for finding in findings if finding["type"] == cycle_kind]
    if not cycles:
        return [
            f"CFT-G08: no finding of type {cycle_kind!r} is in findings[]."
            " Orthogonality is a claim about WHERE the cycle is reported, and a"
            " product reporting it nowhere satisfies the negative limb while"
            " saying nothing"
        ]

    members = {local_name(member) for finding in cycles for member in finding["members"]}
    if not members:
        return [f"CFT-G08: the {cycle_kind!r} finding names no members at all"]
    if not nodes:
        return ["CFT-G08: no node was served, so orthogonality holds vacuously"]

    served_members = {local_name(node["uri"]) for node in nodes}
    if not members <= served_members:
        return [
            f"CFT-G08: the finding names {sorted(members - served_members)},"
            " which the tree does not carry. A finding about members the"
            " payload does not serve cannot be tested for orthogonality"
        ]
    if members == served_members:
        return [
            "CFT-G08: every served member is a cycle member, so no field could"
            " partition the tree into the cycle and the rest. The gate would be"
            " vacuous"
        ]

    by_path: dict[str, dict[str, set[str]]] = {}
    for node in nodes:
        name = local_name(node["uri"])
        for path, rendered in _flatten(node).items():
            by_path.setdefault(path, {}).setdefault(rendered, set()).add(name)
    for path, groups in sorted(by_path.items()):
        for rendered, holders in sorted(groups.items()):
            if holders == members:
                violations.append(
                    f"CFT-G08: the served node field {path!r} takes the value"
                    f" {rendered} on EXACTLY the cycle members"
                    f" {sorted(members)} and on no other member. That is a"
                    " cycle flag on the tree, whatever it is named — and"
                    " flattening the circuit onto the nodes destroys the"
                    " closing edge while every node count stays right"
                )
    return violations


def test_cft_g08_findings_are_orthogonal_to_the_tree(served: Asked) -> None:
    """`CFT-G08` (criterion 32). Findings are orthogonal to the tree.

    No field of any served node partitions the tree into the cycle's members,
    AND the cycle is present in its own collection. The second limb is what
    stops a product with no findings at all from satisfying the first.

    Sabotaged by flagging cycle membership on the nodes instead.
    """
    violations = orthogonality_violations(
        served.nodes, served.findings, cycle_kind=finding_types()["cycle"]
    )
    assert not violations, (
        f"CFT-G08 failed against {served.asked_as}:\n" + "\n".join(violations)
    )


def test_the_orthogonality_check_refuses_a_flag_named_anything() -> None:
    """**Positive control**, on a marker whose name says nothing about cycles.

    A check reading the node keys for the token "cycle" is green against this.
    """
    nodes = [
        {"uri": "x://a", "flagged": True},
        {"uri": "x://b", "flagged": True},
        {"uri": "x://c", "flagged": False},
    ]
    findings = [{"type": "ownership_cycle", "members": ["x://a", "x://b"]}]
    violations = orthogonality_violations(
        nodes, findings, cycle_kind="ownership_cycle"
    )
    assert violations, "a node-level cycle marker named `flagged` was accepted"
    assert any("cycle flag on the tree" in entry for entry in violations), violations


def test_the_orthogonality_check_refuses_a_nested_flag() -> None:
    """**Positive control.** One level down is still on the node."""
    nodes = [
        {"uri": "x://a", "meta": {"ring": 1}},
        {"uri": "x://b", "meta": {"ring": 1}},
        {"uri": "x://c", "meta": {"ring": None}},
    ]
    findings = [{"type": "ownership_cycle", "members": ["x://a", "x://b"]}]
    violations = orthogonality_violations(
        nodes, findings, cycle_kind="ownership_cycle"
    )
    assert violations, "a nested node-level cycle marker was accepted"
    assert any("'meta.ring'" in entry for entry in violations), violations


def test_the_orthogonality_check_refuses_a_product_with_no_finding() -> None:
    """**Vacuity control.** A tree with no cycle flag and no cycle finding."""
    nodes = [{"uri": "x://a"}, {"uri": "x://b"}, {"uri": "x://c"}]
    violations = orthogonality_violations(nodes, [], cycle_kind="ownership_cycle")
    assert violations, "a product reporting no cycle satisfied orthogonality"
    assert any("is in findings[]" in entry for entry in violations), violations


# ---------------------------------------------------------------------------
# CFT-G09 — a node with no LEI stays in the tree AND in the roster.
# ---------------------------------------------------------------------------


def unresolved_violations(
    asked: Asked,
    *,
    declared_roster: Sequence[str],
    subtree_size: int,
    unresolved_kind: str,
) -> list[str]:
    """Every way a dropped member escapes notice — `CFT-G09`.

    **Two rosters and one size, and the rosters are what discriminate.** The
    sabotage returns a smaller, tidier, WRONG family with no error at all: 20 of
    the 22 SMCI-subtree members resolve to no `ccf_v2.legal_entity` row, so a
    build that served only the two that do looks perfectly well formed. A count
    alone would pass on twenty entirely different nodes — `D-13`, applied to
    this finding by name in `D-IMPL-229`.

    The declared size is asserted TOO, because a roster comparison against a
    subset would not notice a member appearing that nobody declared.
    """
    if asked.payload is None:
        return [f"CFT-G09: the ask was refused — {asked.refusal!r}"]

    violations: list[str] = []
    served = tuple(asked.roster)
    if len(served) != subtree_size:
        violations.append(
            f"CFT-G09: {len(served)} members were served where"
            f" expected.yaml::census.anchor_subtree declares {subtree_size}."
            f" Served {list(served)}"
        )
    missing = sorted(set(declared_roster) - set(served))
    if missing:
        violations.append(
            f"CFT-G09: {missing} resolve to no PostgreSQL row and were DROPPED"
            " from the tree. A failed join is a null resolution or a finding,"
            " never a member that vanished — a corporate family missing twenty"
            " subsidiaries is a concentration denominator wrong in the"
            " safe-looking direction"
        )

    matching = [
        finding for finding in asked.findings if finding["type"] == unresolved_kind
    ]
    if not matching:
        violations.append(
            f"CFT-G09: no finding of type {unresolved_kind!r} reached the"
            " consumer, so the unresolved members are in the tree and in no"
            " roster. A member served with null attributes and nothing said"
            " about it reads as a member whose attributes are genuinely null"
        )
        return violations
    reported = sorted(
        local_name(member) for finding in matching for member in finding["members"]
    )
    if reported != sorted(declared_roster):
        violations.append(
            f"CFT-G09: the unresolved roster reached the consumer as {reported}"
            f" where expected.yaml declares {sorted(declared_roster)}. The"
            " ROSTER and never the count: a right count over twenty different"
            " nodes audits clean forever"
        )
    return violations


def test_cft_g09_a_node_with_no_lei_stays_in_the_tree_and_the_roster(
    served: Asked,
) -> None:
    """`CFT-G09` (criterion 33). A failed join is a null resolution, not a drop.

    Asserted over the SMCI subtree, where 20 of 22 resolve to no PostgreSQL row:
    the served size is the declared 22, every one of the declared twenty is
    still IN the tree, and the twenty are named BY NAME in their own finding.

    Sabotaged by dropping members whose PostgreSQL join fails.
    """
    violations = unresolved_violations(
        served,
        declared_roster=declared_unresolved_members(),
        subtree_size=int(census("anchor_subtree")["reachable_nodes"]),
        unresolved_kind=finding_types()["unresolved"],
    )
    assert not violations, (
        f"CFT-G09 failed against {served.asked_as}:\n" + "\n".join(violations)
    )


def test_the_unresolved_check_refuses_a_tidier_smaller_family() -> None:
    """**Positive control.** The sabotage returns a family with no error at all."""
    declared_roster = declared_unresolved_members()
    subtree_size = int(census("anchor_subtree")["reachable_nodes"])
    resolving = [
        str(row["uri"])
        for row in census("anchor_subtree_store_split")["the_two_resolving"]
    ]
    tidy = Asked(
        asked_as="only the members whose join resolved",
        payload={
            "nodes": [
                {"uri": f"http://example.org/fibo/{name}"} for name in resolving
            ],
            "findings": [
                {"type": "unresolved_jurisdiction", "members": [], "closing_edge": None}
            ],
        },
        content_address="deadbeef",
        refusal=None,
        observed=("Assembled",),
        served_vessels=("Assembled",),
    )
    violations = unresolved_violations(
        tidy,
        declared_roster=declared_roster,
        subtree_size=subtree_size,
        unresolved_kind="unresolved_jurisdiction",
    )
    assert violations, "a family missing twenty members was reported as whole"
    assert any("were DROPPED" in entry for entry in violations), violations


def test_the_unresolved_check_refuses_twenty_different_nodes() -> None:
    """**Positive control**, and the reason the assertion is a roster.

    The right SIZE, the right COUNT of unresolved members, and one of them is a
    node nobody declared. A count-based check reports clean.
    """
    declared_roster = list(declared_unresolved_members())
    substituted = [*declared_roster[:-1], "SomeCompanyNobodyDeclared"]
    swapped = Asked(
        asked_as="the right count over a wrong member",
        payload={
            "nodes": [
                {"uri": f"http://example.org/fibo/{name}"}
                for name in sorted({*declared_roster, "SuperMicroComputerInc",
                                    "SuperMicroComputerBV"})
            ],
            "findings": [
                {
                    "type": "unresolved_jurisdiction",
                    "members": [
                        f"http://example.org/fibo/{name}" for name in substituted
                    ],
                    "closing_edge": None,
                }
            ],
        },
        content_address="deadbeef",
        refusal=None,
        observed=("Assembled",),
        served_vessels=("Assembled",),
    )
    violations = unresolved_violations(
        swapped,
        declared_roster=declared_roster,
        subtree_size=len(declared_roster) + 2,
        unresolved_kind="unresolved_jurisdiction",
    )
    assert violations, "a wrong member inside a right count was accepted"
    assert any("ROSTER and never the count" in entry for entry in violations), violations


def test_the_unresolved_check_refuses_a_silent_null() -> None:
    """**Vacuity control.** Null attributes with no finding is a silent omission."""
    declared_roster = list(declared_unresolved_members())
    silent = Asked(
        asked_as="every member served, nothing said about the twenty",
        payload={
            "nodes": [
                {"uri": f"http://example.org/fibo/{name}"}
                for name in sorted({*declared_roster, "SuperMicroComputerInc",
                                    "SuperMicroComputerBV"})
            ],
            "findings": [],
        },
        content_address="deadbeef",
        refusal=None,
        observed=("Assembled",),
        served_vessels=("Assembled",),
    )
    violations = unresolved_violations(
        silent,
        declared_roster=declared_roster,
        subtree_size=len(declared_roster) + 2,
        unresolved_kind="unresolved_jurisdiction",
    )
    assert violations, "a payload saying nothing about the twenty was accepted"
    assert any("in no" in entry for entry in violations), violations


# ---------------------------------------------------------------------------
# CFT-G15 — each served node carries its FIBO class chain.
# ---------------------------------------------------------------------------


def class_chain_violations(
    asked: Asked,
    *,
    anchor_chain: Sequence[str],
    cycle_member: str,
    cycle_chain_length: int,
) -> list[str]:
    """Every way the served tree fails `CFT-G15`.

    **Four limbs, and the first two are separate because presence is not
    content.** A presence check alone passes against a chain served as an empty
    list — the key is there, the payload validates, and a consuming agent
    learns nothing. So the chain is asserted NON-EMPTY on every served node AND
    asserted by CONTENT on the anchor and on a cycle member, against
    `expected.yaml::census.anchor.type_chain` and
    `census.cycle_member_typing`.

    **AND BY CONTENT ON EVERY OTHER MEMBER — the close panel's finding.** As
    shipped, content was compared for the anchor and for ONE cycle-1 member;
    the other twenty were checked NON-EMPTY only. This estate is
    class-homogeneous, so twenty wrong-but-non-empty chains were invisible: a
    member served `["Corporation"]`, or served another member's five-class
    chain, satisfied every limb. Limb four therefore compares EVERY served
    member's chain against the anchor's DECLARED chain, as a roster of the
    members that diverge.

    **The scope claim needs no new declared figure, and that is deliberate.**
    The VALUES come from `expected.yaml::census.anchor.type_chain`, the one
    place they are declared; the SCOPE — that every subtree member carries the
    identical chain — is asserted as an observation about the run rather than
    read from a document, because `expected.yaml` records the homogeneity in a
    COMMENT (*"All 22 nodes carry the IDENTICAL 7-class chain"*, beside
    `perspective_discriminating_class`) and a comment is not something a check
    can read. Writing the seven names a second time would be the second place
    to change one fact that document refuses by name. If this estate ever stops
    being class-homogeneous this limb goes red, which is the correct outcome:
    the withdrawal of ontology role 1 and of the seventeenth gate both rest on
    that property, and it should not be able to change in silence.

    Ontology role 2 is what makes the product self-describing over MCP: a
    consuming agent knows what an entity IS without a second lookup. A tree
    served without type information is a tree that has stopped saying so.
    """
    if asked.payload is None:
        return [f"CFT-G15: the ask was refused — {asked.refusal!r}"]
    if not asked.nodes:
        return ["CFT-G15: no node was served, so the property holds vacuously"]

    violations: list[str] = []
    untyped = sorted(
        local_name(node["uri"]) for node in asked.nodes if not node["type_chain"]
    )
    if untyped:
        violations.append(
            f"CFT-G15: {untyped} were served with an EMPTY class chain. Section"
            " D.6 makes type_chain non-nullable, and a tree served without type"
            " information stops being self-describing — a consuming agent needs"
            " a second lookup to learn what any member is"
        )

    served_anchor = tuple(
        sorted(local_name(iri) for iri in asked.payload["anchor"]["type_chain"])
    )
    want_anchor = tuple(sorted(str(name) for name in anchor_chain))
    if served_anchor != want_anchor:
        violations.append(
            f"CFT-G15: the anchor's chain reached the consumer as"
            f" {list(served_anchor)} where expected.yaml declares"
            f" {list(want_anchor)}. Content, not presence: an empty list and a"
            " wrong list both satisfy a check that only looks for the key"
        )

    by_name = {local_name(node["uri"]): node for node in asked.nodes}
    member = by_name.get(cycle_member)
    if member is None:
        violations.append(
            f"CFT-G15: the cycle member {cycle_member!r} is not in the served"
            " tree, so its chain cannot be read and this limb asserts nothing"
        )
        return violations
    diverging = sorted(
        local_name(node["uri"])
        for node in asked.nodes
        if node["type_chain"]
        and tuple(sorted(local_name(iri) for iri in node["type_chain"])) != want_anchor
    )
    if diverging:
        violations.append(
            f"CFT-G15: {diverging} carry a class chain that is not the declared"
            f" profile {list(want_anchor)}. expected.yaml records this subtree"
            " as class-homogeneous — all 22 members carry the IDENTICAL chain —"
            " so a member with a different NON-EMPTY chain is either a"
            " mis-served chain or a measurement that has moved. Content was"
            " compared for the anchor and one cycle member only until"
            " 2026-09-01; the other twenty were checked non-empty, which a"
            " wrong-but-non-empty chain satisfies"
        )

    served_member = tuple(sorted(local_name(iri) for iri in member["type_chain"]))
    if len(served_member) != cycle_chain_length:
        violations.append(
            f"CFT-G15: {cycle_member!r} carries {len(served_member)} classes"
            f" where expected.yaml::census.cycle_member_typing declares"
            f" {cycle_chain_length} — {list(served_member)}"
        )
    if served_member != want_anchor:
        violations.append(
            f"CFT-G15: {cycle_member!r} carries {list(served_member)} where the"
            f" declared profile is {list(want_anchor)}. expected.yaml records"
            " this population as class-homogeneous; a member of it carrying a"
            " different chain is either a mis-served chain or a measurement"
            " that has moved"
        )
    return violations


def test_cft_g15_each_served_node_carries_its_fibo_class_chain(served: Asked) -> None:
    """`CFT-G15` (criterion 39). Ontology role 2 — the chain is SERVED.

    Asserted over the WHOLE returned node set for non-emptiness, and by CONTENT
    for the anchor and for a cycle-1 member. A presence check alone would pass
    on a chain served as an empty list.

    Sabotaged by serving the tree without type information.
    """
    cycle_one = census("cycle_1")
    violations = class_chain_violations(
        served,
        anchor_chain=census("anchor")["type_chain"],
        cycle_member=str(cycle_one["members"][0]),
        cycle_chain_length=int(
            census("cycle_member_typing")["cycle_1_type_chain_length"]
        ),
    )
    assert not violations, (
        f"CFT-G15 failed against {served.asked_as}:\n" + "\n".join(violations)
    )


def test_the_chain_check_refuses_a_chain_served_as_an_empty_list() -> None:
    """**Positive control.** The declared sabotage, in the shape it arrives in."""
    anchor_chain = census("anchor")["type_chain"]
    stripped = Asked(
        asked_as="the tree served without type information",
        payload={
            "anchor": {"uri": "x://anchor", "type_chain": []},
            "nodes": [{"uri": "x://a", "type_chain": []}],
            "edges": [],
            "findings": [],
        },
        content_address="deadbeef",
        refusal=None,
        observed=("Assembled",),
        served_vessels=("Assembled",),
    )
    violations = class_chain_violations(
        stripped, anchor_chain=anchor_chain, cycle_member="a", cycle_chain_length=7
    )
    assert violations, "a tree with empty class chains was reported as typed"
    assert any("EMPTY class chain" in entry for entry in violations), violations


def test_the_chain_check_refuses_a_wrong_chain_on_a_member_that_is_not_the_anchor() -> None:
    """**Positive control** for the close panel's finding, in its own shape.

    The anchor is right, the cycle member is right, and a THIRD member carries a
    plausible five-class chain. Every limb the gate shipped with is satisfied by
    this subject — the chain is non-empty, the anchor matches, the cycle member
    matches and is the declared length — so the check that shipped reported it
    clean. The roster limb names the member.
    """
    anchor_chain = census("anchor")["type_chain"]
    full = [f"http://example.org/fibo/{name}" for name in anchor_chain]
    partial = full[:5]
    subject = Asked(
        asked_as="one member carrying a wrong but non-empty chain",
        payload={
            "anchor": {"uri": "x://anchor", "type_chain": full},
            "nodes": [
                {"uri": "x://a", "type_chain": full},
                {"uri": "http://example.org/fibo/SubSupermicroKk", "type_chain": partial},
            ],
            "edges": [],
            "findings": [],
        },
        content_address="deadbeef",
        refusal=None,
        observed=("Assembled",),
        served_vessels=("Assembled",),
    )
    violations = class_chain_violations(
        subject, anchor_chain=anchor_chain, cycle_member="a", cycle_chain_length=7
    )
    assert violations, "a wrong but non-empty chain on a non-anchor member was accepted"
    assert any("SubSupermicroKk" in entry for entry in violations), violations
    assert any("class-homogeneous" in entry for entry in violations), violations
    assert not any("EMPTY class chain" in entry for entry in violations), (
        "the empty-chain limb fired; this subject carries a NON-empty chain and"
        " the point of the control is that only the roster limb can see it"
    )


def test_the_chain_check_refuses_a_wrong_chain_that_is_not_empty() -> None:
    """**Positive control.** Non-emptiness is presence; the roster is content."""
    anchor_chain = census("anchor")["type_chain"]
    wrong = Asked(
        asked_as="a plausible but wrong chain",
        payload={
            "anchor": {
                "uri": "x://anchor",
                "type_chain": ["http://example.invalid/Whatever"],
            },
            "nodes": [
                {"uri": "x://a", "type_chain": ["http://example.invalid/Whatever"]}
            ],
            "edges": [],
            "findings": [],
        },
        content_address="deadbeef",
        refusal=None,
        observed=("Assembled",),
        served_vessels=("Assembled",),
    )
    violations = class_chain_violations(
        wrong, anchor_chain=anchor_chain, cycle_member="a", cycle_chain_length=7
    )
    assert violations, "a non-empty wrong chain was reported as the declared one"
    assert any("where expected.yaml declares" in entry for entry in violations), (
        violations
    )


def test_no_cycle_two_member_reaches_a_served_payload(served: Asked) -> None:
    """Why `CFT-G15` asserts content for ONE cycle and not for two — measured.

    Plan `24.4-11` asks for the chain's content *"for the anchor and one member
    of each cycle"*. **Against this estate the second half is not assertable
    from a served payload, and the reason is already declared rather than
    discovered here:** `expected.yaml::census.cycle_2` records
    ``external_in_edges: 0``, so no walk from any LEI-bearing anchor reaches
    cycle 2, and `census.cycle_member_typing` records that no cycle member
    carries an LEI at all — so cycle 2 cannot be reached as a subtree and cannot
    be asked for as an anchor either.

    Rather than drop the observation, it is asserted in the direction the estate
    can carry: **no cycle-2 member is in the served set.** The 7-versus-5 fact
    itself is asserted at the census, against the store, by
    `tests/examples/test_cp_04_cycles.py::test_the_two_circuits_class_chains_differ_and_no_member_carries_an_lei`.
    """
    cycle_two = census("cycle_2")
    assert int(cycle_two["external_in_edges"]) == 0, (
        "expected.yaml no longer declares cycle 2 unreachable, so a served"
        " payload may now be able to carry one of its members and CFT-G15's"
        " content limb should be extended to it"
    )
    intruders = sorted(set(served.roster) & {str(m) for m in cycle_two["members"]})
    assert not intruders, (
        f"cycle-2 members {intruders} reached a served payload where"
        " expected.yaml declares cycle 2 has zero external in-edges. Either the"
        " estate changed or the walk found a path the measurement did not"
    )
    typing = census("cycle_member_typing")
    assert int(typing["cycle_2_type_chain_length"]) != int(
        typing["cycle_1_type_chain_length"]
    ), (
        "the two circuits' declared chain lengths no longer differ, so the"
        " 7-versus-5 fact this scope note is about has gone"
    )


# ---------------------------------------------------------------------------
# CFT-G16 — the perspective conditions on FIBO CLASS, not on a role map.
# ---------------------------------------------------------------------------


def chain_mutating_plan_class(*, target: str, axis: str) -> Any:
    """The SHIPPED projection, handed one node whose class chain lacks the axis.

    **This is `CFT-G16`'s mechanism control and not its sabotage.** The gate's
    content is that the two views are conditioned on the FIBO class the graph
    carries, and the only way to show conditioning rather than coincidence is to
    move a class and watch both views move with it —
    ``examples/cp-04-corporate-family-tree/projection.py::FamilyTreeProjection._detailed_for``
    says exactly that: *"Strip the axis class from one node's chain and that
    node leaves the credit officer's detailed set and enters the KYC analyst's.
    A role map keyed by entity name would not move at all."*

    Nothing about the projection is reimplemented. The class returned here is a
    SUBCLASS of the shipped plan class, and the only thing it changes is the
    scenario it reads: one member's ``type_chain`` arrives without ``axis``. The
    conditioning, the payload shape and the detailed-member derivation are all
    the shipped ones, so a sabotage that stops reading the chain is invisible to
    the substitution and visible in the answer.

    The mutated scenario is a PROXY rather than a rebuilt value: the spine's own
    scenario is a frozen dataclass carrying two dozen members, and rebuilding it
    would be this control asserting a shape rather than a behavior.
    """
    import dataclasses

    projection = _load("projection")
    base = projection.plan_class()

    class _OneChainStripped:
        """The scenario, with ``target``'s class chain missing ``axis``."""

        def __init__(self, inner: Any) -> None:
            self._inner = inner

        def __getattr__(self, name: str) -> Any:
            return getattr(self._inner, name)

        @property
        def facts(self) -> Mapping[str, Any]:
            facts = dict(self._inner.facts)
            node = facts[target]
            facts[target] = dataclasses.replace(
                node,
                type_chain=tuple(
                    entry for entry in node.type_chain if entry != axis
                ),
            )
            return facts

    class _Mutated(base):  # type: ignore[misc, valid-type]
        def __init__(self, **kwargs: Any) -> None:
            kwargs["scenario"] = _OneChainStripped(kwargs["scenario"])
            super().__init__(**kwargs)

    return _Mutated


def detailed_roster(asked: Asked) -> tuple[str, ...]:
    """The members this role was shown detail for, by LOCAL name. A roster."""
    if asked.payload is None:
        return ()
    return tuple(
        sorted(local_name(uri) for uri in asked.payload["detailed_members"])
    )


def conditioning_violations(
    *,
    views: Mapping[str, Asked],
    declared_detailed: Mapping[str, int],
    axis_class: str,
) -> list[str]:
    """Every way the two views fail to be conditioned on FIBO class — `CFT-G16`.

    **Two limbs here, and the third is a separate control**, because they fail
    for different reasons and a reader is owed the difference.

    Limb one: the two roles see the SAME family and DIFFERENT detail. The
    detailed sets are compared as ROSTERS derived from what each view served —
    the role `expected.yaml` declares detailing every member must detail exactly
    the served roster, and the role it declares detailing none must detail
    nothing. A count comparison would accept a view detailing twenty-two of the
    wrong members.

    Limb two: the class is NAMED, it is the class `expected.yaml` declares, and
    it is what the served chains actually carry. The payload's own
    ``carries_class_axis`` is asserted to AGREE with the chain beside it — a
    product whose conditioning field disagreed with the chain it was derived
    from would be reporting a conditioning it did not perform.
    """
    violations: list[str] = []
    for role, view in sorted(views.items()):
        if view.payload is None:
            return [f"CFT-G16: the ask under role {role!r} was refused — {view.refusal!r}"]

    rosters = {role: view.roster for role, view in views.items()}
    if len(set(rosters.values())) != 1:
        violations.append(
            f"CFT-G16: the two roles were served DIFFERENT member sets"
            f" — { {role: len(r) for role, r in rosters.items()} }. The family"
            " is the family; what differs between roles is what each is shown"
            " ABOUT each member, and a member set that moved means Policy"
            " changed rather than the perspective"
        )
    served = next(iter(rosters.values()))

    for role, view in sorted(views.items()):
        detailed = detailed_roster(view)
        want = int(declared_detailed[role])
        if want == len(served):
            if detailed != tuple(sorted(served)):
                violations.append(
                    f"CFT-G16: role {role!r} detailed {list(detailed)} where"
                    f" expected.yaml declares it details every served member"
                    f" — {list(sorted(served))}"
                )
        elif want == 0:
            if detailed:
                violations.append(
                    f"CFT-G16: role {role!r} detailed {list(detailed)} where"
                    " expected.yaml declares it details none of them"
                )
        else:
            violations.append(
                f"CFT-G16: expected.yaml declares role {role!r} details {want}"
                f" of {len(served)} served members, which is neither all nor"
                " none — this check compares rosters and can no longer derive"
                " one from that number"
            )

    if len({detailed_roster(view) for view in views.values()}) == 1:
        violations.append(
            "CFT-G16: the two declared roles detailed the IDENTICAL member"
            f" roster ({len(detailed_roster(next(iter(views.values()))))} members)."
            " Two perspectives over one family that show the same thing are one"
            " perspective with two names"
        )

    for role, view in sorted(views.items()):
        assert view.payload is not None
        named = str(view.payload["class_axis"])
        if named != axis_class:
            violations.append(
                f"CFT-G16: role {role!r} names class axis {named!r} where"
                f" expected.yaml declares {axis_class!r}"
            )
        for node in view.nodes:
            carried = axis_class in {
                local_name(iri) for iri in node["type_chain"]
            }
            claimed = bool(node["conditioning"]["carries_class_axis"])
            if carried != claimed:
                violations.append(
                    f"CFT-G16: {local_name(node['uri'])!r} was served under"
                    f" {role!r} claiming carries_class_axis={claimed} while its"
                    f" own type_chain says {carried}. The conditioning field"
                    " does not agree with the chain it is derived from"
                )
    return violations


def mutation_violations(
    *,
    baseline: Mapping[str, Asked],
    mutated: Mapping[str, Asked],
    target: str,
    detailing_role: str,
    other_role: str,
) -> list[str]:
    """Every way the conditioning fails to TRACK the class — `CFT-G16` limb 3.

    **This is the limb a hand-written role map cannot survive**, and it is the
    reason the gate is not satisfied by the outcome alone. One class is stripped
    from ONE member's chain and the member must move in BOTH views, in OPPOSITE
    directions: out of the detailing role's set and into the other role's. A map
    from role to entity name does not move at all, and its served outcome is
    otherwise identical — which is exactly the *"token present in both the
    compliant and the violating case"* shape.

    Every other member must stay put, so the limb cannot be satisfied by a
    projection that simply became unstable.
    """
    violations: list[str] = []
    for role, view in sorted(mutated.items()):
        if view.payload is None:
            return [
                f"CFT-G16: the mutated ask under role {role!r} was refused —"
                f" {view.refusal!r}"
            ]
    if target not in baseline[detailing_role].roster:
        return [
            f"CFT-G16: {target!r} is not in the served set, so stripping its"
            " class proves nothing"
        ]
    if target not in detailed_roster(baseline[detailing_role]):
        return [
            f"CFT-G16: {target!r} is not detailed by {detailing_role!r} before"
            " the mutation, so it has nowhere to move FROM"
        ]

    for role, view in sorted(mutated.items()):
        if view.roster != baseline[role].roster:
            violations.append(
                f"CFT-G16: stripping one class from {target!r} moved the served"
                f" MEMBER roster under {role!r}. The class conditions what a"
                " role is shown, never who is in the family"
            )

    want_detailing = tuple(
        name for name in detailed_roster(baseline[detailing_role]) if name != target
    )
    got_detailing = detailed_roster(mutated[detailing_role])
    if got_detailing != want_detailing:
        violations.append(
            f"CFT-G16: with the class axis stripped from {target!r}, role"
            f" {detailing_role!r} detailed {list(got_detailing)} where the class"
            f" chain implies {list(want_detailing)}. The conditioning did not"
            " FOLLOW the chain — which is what a role map keyed by entity name"
            " looks like, and its served outcome is otherwise identical"
        )
    got_other = detailed_roster(mutated[other_role])
    if got_other != (target,):
        violations.append(
            f"CFT-G16: with the class axis stripped from {target!r}, role"
            f" {other_role!r} detailed {list(got_other)} where the class chain"
            f" implies exactly ['{target}']. One class read from opposite sides"
            " moves one node in BOTH views, in opposite directions; a role map"
            " moves it in neither"
        )
    return violations


def pinned_perspective_violations(
    *,
    views: Mapping[str, Asked],
    pinned_addresses: Mapping[str, str],
    declared_detailed: Mapping[str, int],
    declared_roles: Sequence[str],
    declared_roster: Sequence[str],
) -> list[str]:
    """Every way the two roles fail their PINNED figures — `CFT-G16` limb 4.

    **The limb exists because no roster in this suite can see a cosmetic role.**
    Both declared roles are served the SAME family — the product's own claim,
    asserted by limb one — so a projection that stopped conditioning on anything
    leaves `CFT-G09`'s twenty intact, criterion 10's pair intact, every served
    chain intact and the tree at twenty-two. Dave named the consequence at the
    build evaluation: a later *"role is cosmetic"* regression *"cannot hide
    behind a still-green tree of 22"*, so the two things that DO move are pinned
    and read from `artifacts/expected.yaml`.

    **Four limbs, and the first two are about the DECLARATION rather than about
    the product.** A check that reads its expectation from a file is only as
    strong as the file: a pin that named one role, or named both roles with one
    address, would be satisfiable by a product serving a single view under two
    names. So the pinned roster is required to be exactly the roles the
    deployment declares, and the two pinned addresses are required to DIFFER —
    both read from the artifact, neither authored here.

    **Limb three is the seal, pinned EXACTLY and never compared role-to-role.**
    ``perspective_role`` is echoed into the sealed payload, so two roles produce
    two addresses whether or not either address means anything — the same shape
    that let `CFT-G05` pass its own first sabotage on ``max_depth_applied``. An
    exact pin has no such hiding place: a role read for its name and not for its
    meaning moves one of the two values off what the artifact declares.

    **Limb four is the detailed COUNT beside the roster, deliberately.** The
    roster comparison lives in :func:`conditioning_violations`, where the served
    detail is checked member by member; what is added here is the figure Dave
    named — twenty-two and zero — because it is the number a reader of the
    README and the artifact holds, and a count that silently disagreed with the
    document those two are read from would leave three records of one fact with
    no check between them. The count is asserted BESIDE the roster and never
    instead of it (`D-13`).
    """
    violations: list[str] = []

    pinned_roles = set(pinned_addresses)
    want_roles = {str(role) for role in declared_roles}
    if pinned_roles != want_roles:
        violations.append(
            f"CFT-G16: expected.yaml pins addresses for {sorted(pinned_roles)}"
            f" where the deployment declares the roles {sorted(want_roles)}. A"
            " role with no pin is a role this limb cannot fail on, and a pin"
            " for a role nobody declares is an expectation nothing produces"
        )
    if len(set(pinned_addresses.values())) != len(pinned_addresses):
        violations.append(
            f"CFT-G16: expected.yaml pins {sorted(set(pinned_addresses.values()))}"
            f" across {len(pinned_addresses)} declared roles — one address"
            " written more than once. Two roles pinned to one seal are"
            " satisfied by a product serving one view under two names, which is"
            " the regression this limb exists to catch"
        )

    want_roster = tuple(sorted(str(name) for name in declared_roster))
    for role, view in sorted(views.items()):
        if view.payload is None:
            violations.append(
                f"CFT-G16: the ask under role {role!r} was refused —"
                f" {view.refusal!r}, so it has no seal to compare"
            )
            continue

        if view.roster != want_roster:
            violations.append(
                f"CFT-G16: role {role!r} was served"
                f" {sorted(set(view.roster) ^ set(want_roster))} in symmetric"
                " difference with the family expected.yaml declares. The seal"
                " below is pinned against THAT family, so a moved roster would"
                " make a moved address say nothing about the role"
            )

        pinned = pinned_addresses.get(role)
        if pinned is not None and view.content_address != pinned:
            violations.append(
                f"CFT-G16: role {role!r} sealed to {view.content_address!r}"
                f" where expected.yaml pins {pinned!r}. The two roles are served"
                " the same family, so no member roster in this suite moves when"
                " a role stops conditioning anything — this seal and the"
                " detailed count beside it are the only declared figures that"
                " can, which is why they are pinned"
            )

        detailed = detailed_roster(view)
        want_count = int(declared_detailed[role])
        if len(detailed) != want_count:
            violations.append(
                f"CFT-G16: role {role!r} was shown detail for {len(detailed)}"
                f" members where expected.yaml declares {want_count}. The count"
                " is asserted beside the roster and never instead of it, but it"
                " is the figure the README and the artifact both carry"
            )
    return violations


@pytest.fixture(scope="module")
def views(estate: tuple[str, str]) -> Mapping[str, Asked]:
    """One ask per declared role, over the SAME family at the same depth."""
    deployment = _load("deployment")
    return {
        role: ask(
            asked_as=f"the declared default depth under role {role!r}",
            omit_max_depth=True,
            role=role,
        )
        for role in deployment.declared_roles()
    }


@pytest.fixture(scope="module")
def mutated_views(estate: tuple[str, str]) -> tuple[str, Mapping[str, Asked]]:
    """The same two asks, with ONE member's class chain missing the axis."""
    deployment = _load("deployment")
    axis = deployment.class_axis_iri()
    target_iri = str(census("cycle_1")["member_iris"][0])
    plan_class = chain_mutating_plan_class(target=target_iri, axis=axis)
    return local_name(target_iri), {
        role: ask(
            asked_as=(
                f"role {role!r} with the class axis stripped from"
                f" {local_name(target_iri)!r}"
            ),
            omit_max_depth=True,
            role=role,
            plan_class=plan_class,
        )
        for role in deployment.declared_roles()
    }


def test_cft_g16_perspective_conditions_on_fibo_class(
    views: Mapping[str, Asked], mutated_views: tuple[str, Mapping[str, Asked]]
) -> None:
    """`CFT-G16` (criterion 40). The perspective conditions on FIBO class.

    Four limbs. Two declared perspectives over the SAME family serve the same
    members and DIFFERENT detail; the class that explains the difference is
    NAMED and is the one `expected.yaml` declares; stripping that class from ONE
    member's chain moves that member in BOTH views, in opposite directions — the
    limb a role map cannot survive; and each role's whole served vessel seals to
    the address `expected.yaml` PINS for it, with the detailed count beside it.

    Sabotaged two ways. A hand-written role map produces the SAME served outcome
    and fails the third limb. A projection that ignores the requested role
    altogether — the *"role is cosmetic"* regression — leaves the served family
    at twenty-two under both roles and every member roster in this suite green,
    and fails the fourth.
    """
    deployment = _load("deployment")
    declared_detailed = {
        str(role): int(value)
        for role, value in declared()["perspective_detailed_members"].items()
    }
    axis_class = str(declared()["perspective_discriminating_class"])
    violations = conditioning_violations(
        views=views, declared_detailed=declared_detailed, axis_class=axis_class
    )

    sides = deployment.conditioned_roles()
    detailing = next(
        role for role, side in sides.items() if side == deployment.AXIS_CARRIES
    )
    other = next(
        role for role, side in sides.items() if side == deployment.AXIS_LACKS
    )
    target, mutated = mutated_views
    violations += mutation_violations(
        baseline=views,
        mutated=mutated,
        target=target,
        detailing_role=detailing,
        other_role=other,
    )
    violations += pinned_perspective_violations(
        views=views,
        pinned_addresses=declared_addresses(),
        declared_detailed=declared_detailed,
        declared_roles=deployment.declared_roles(),
        declared_roster=declared_family_roster(),
    )
    assert not violations, "CFT-G16 failed:\n" + "\n".join(violations)


def test_the_conditioning_check_refuses_two_identical_views() -> None:
    """**Positive control.** One perspective with two names is not two."""
    payload = {
        "nodes": [
            {
                "uri": "x://a",
                "type_chain": ["http://x/Corporation"],
                "conditioning": {"carries_class_axis": True},
            }
        ],
        "detailed_members": ["x://a"],
        "class_axis": "Corporation",
    }
    same = {
        role: Asked(
            asked_as=role,
            payload=payload,
            content_address="deadbeef",
            refusal=None,
            observed=("Assembled",),
            served_vessels=("Assembled",),
        )
        for role in ("credit-officer", "kyc-analyst")
    }
    violations = conditioning_violations(
        views=same,
        declared_detailed={"credit-officer": 1, "kyc-analyst": 0},
        axis_class="Corporation",
    )
    assert violations, "two identical views were reported as two perspectives"
    assert any("IDENTICAL member roster" in entry for entry in violations), violations


def test_the_conditioning_check_refuses_a_field_that_disagrees_with_the_chain() -> None:
    """**Positive control.** A conditioning field is not a conditioning.

    ``carries_class_axis`` is a property of the NODE and not of the role: both
    views of a member that carries the class must report that it carries it, and
    only ``detailed`` differs between them. The compliant pair below therefore
    reports ``True`` under both roles — a first draft of this control reported
    it per-role, which is a misreading of the field the shipped check caught.
    """
    def view(detailed: list[str], claims: bool) -> Asked:
        return Asked(
            asked_as="a view whose field disagrees with its chain",
            payload={
                "nodes": [
                    {
                        "uri": "x://a",
                        "type_chain": ["http://x/Corporation"],
                        "conditioning": {"carries_class_axis": claims},
                    }
                ],
                "detailed_members": detailed,
                "class_axis": "Corporation",
            },
            content_address="deadbeef",
            refusal=None,
            observed=("Assembled",),
            served_vessels=("Assembled",),
        )

    violations = conditioning_violations(
        views={
            "credit-officer": view(["x://a"], True),
            "kyc-analyst": view([], True),
        },
        declared_detailed={"credit-officer": 1, "kyc-analyst": 0},
        axis_class="Corporation",
    )
    assert not violations, f"the compliant pair was refused: {violations}"

    violations = conditioning_violations(
        views={
            "credit-officer": view(["x://a"], True),
            "kyc-analyst": view([], False),
        },
        declared_detailed={"credit-officer": 1, "kyc-analyst": 0},
        axis_class="Corporation",
    )
    assert violations, "a conditioning field disagreeing with its chain was accepted"
    assert any("does not agree with the chain" in entry for entry in violations), (
        violations
    )


def test_the_mutation_check_refuses_a_conditioning_that_did_not_move() -> None:
    """**Positive control**, and the one that mirrors the declared sabotage.

    A hand-written role map serves the identical outcome and does not move when
    a class does. Feeding the shipped check a mutated pair that never moved is
    that sabotage in miniature.
    """
    def view(detailed: list[str]) -> Asked:
        return Asked(
            asked_as="unmoved",
            payload={
                "nodes": [{"uri": "x://a"}, {"uri": "x://b"}],
                "detailed_members": detailed,
            },
            content_address="deadbeef",
            refusal=None,
            observed=("Assembled",),
            served_vessels=("Assembled",),
        )

    baseline = {"detailing": view(["x://a", "x://b"]), "other": view([])}
    unmoved = {"detailing": view(["x://a", "x://b"]), "other": view([])}
    violations = mutation_violations(
        baseline=baseline,
        mutated=unmoved,
        target="a",
        detailing_role="detailing",
        other_role="other",
    )
    assert violations, "a conditioning that ignored a moved class was accepted"
    assert any("did not FOLLOW the chain" in entry for entry in violations), violations


def test_the_mutation_check_refuses_a_member_that_moved_in_only_one_view() -> None:
    """**Vacuity control.** One class, two sides — a one-sided move is neither."""
    def view(detailed: list[str]) -> Asked:
        return Asked(
            asked_as="half moved",
            payload={
                "nodes": [{"uri": "x://a"}, {"uri": "x://b"}],
                "detailed_members": detailed,
            },
            content_address="deadbeef",
            refusal=None,
            observed=("Assembled",),
            served_vessels=("Assembled",),
        )

    baseline = {"detailing": view(["x://a", "x://b"]), "other": view([])}
    half = {"detailing": view(["x://b"]), "other": view([])}
    violations = mutation_violations(
        baseline=baseline,
        mutated=half,
        target="a",
        detailing_role="detailing",
        other_role="other",
    )
    assert violations, "a member that left one view and entered neither was accepted"
    assert any("in opposite directions" in entry for entry in violations), violations


def _pinned_subject(
    *, roles: Sequence[str], addresses: Mapping[str, str], detailed: Mapping[str, int]
) -> Mapping[str, Asked]:
    """Two views over the declared family, seals and detail supplied by a caller.

    Built from `expected.yaml`'s own roster so a control cannot pass by asking
    about a family the product does not serve. The controls below hand this to
    the SHIPPED :func:`pinned_perspective_violations` and watch it refuse.
    """
    roster = declared_family_roster()
    return {
        str(role): Asked(
            asked_as=str(role),
            payload={
                "nodes": [
                    {"uri": f"http://example.org/fibo/{name}"} for name in roster
                ],
                "detailed_members": [
                    f"http://example.org/fibo/{name}"
                    for name in roster[: int(detailed[str(role)])]
                ],
            },
            content_address=addresses[str(role)],
            refusal=None,
            observed=("Assembled",),
            served_vessels=("Assembled",),
        )
        for role in roles
    }


def test_the_pinned_check_refuses_a_seal_that_moved() -> None:
    """**Positive control.** The regression Dave named, at the seal.

    The family is the declared twenty-two under both roles, every member roster
    is intact, and one role's seal is not the pinned one. Nothing else moved,
    which is the whole reason this limb exists.
    """
    pinned = declared_addresses()
    roles = sorted(pinned)
    detailed = {
        str(role): int(value)
        for role, value in declared()["perspective_detailed_members"].items()
    }
    moved = dict(pinned)
    moved[roles[0]] = "0" * len(pinned[roles[0]])
    violations = pinned_perspective_violations(
        views=_pinned_subject(roles=roles, addresses=moved, detailed=detailed),
        pinned_addresses=pinned,
        declared_detailed=detailed,
        declared_roles=roles,
        declared_roster=declared_family_roster(),
    )
    assert violations, "a seal that moved off its pin was reported as pinned"
    assert any("where expected.yaml pins" in entry for entry in violations), violations
    assert not any("symmetric difference" in entry for entry in violations), (
        "the served family moved too, so this control is not isolating the seal:"
        f" {violations}"
    )


def test_the_pinned_check_refuses_two_roles_pinned_to_one_address() -> None:
    """**Positive control, on the DECLARATION.** One seal written twice.

    A pin is only as strong as the document it is read from. Two roles pinned to
    one address is satisfied by a product serving a single view under two names,
    which is precisely the regression the limb is for — so the collision is
    refused rather than trusted.
    """
    pinned = declared_addresses()
    roles = sorted(pinned)
    detailed = {
        str(role): int(value)
        for role, value in declared()["perspective_detailed_members"].items()
    }
    collided = {role: pinned[roles[0]] for role in roles}
    violations = pinned_perspective_violations(
        views=_pinned_subject(roles=roles, addresses=collided, detailed=detailed),
        pinned_addresses=collided,
        declared_detailed=detailed,
        declared_roles=roles,
        declared_roster=declared_family_roster(),
    )
    assert violations, "one address written twice was accepted as two pins"
    assert any("written more than once" in entry for entry in violations), violations


def test_the_pinned_check_refuses_a_pin_that_misses_a_declared_role() -> None:
    """**Positive control, on the DECLARATION.** A role with no pin cannot fail."""
    pinned = declared_addresses()
    roles = sorted(pinned)
    detailed = {
        str(role): int(value)
        for role, value in declared()["perspective_detailed_members"].items()
    }
    short = {roles[0]: pinned[roles[0]]}
    violations = pinned_perspective_violations(
        views=_pinned_subject(roles=roles, addresses=pinned, detailed=detailed),
        pinned_addresses=short,
        declared_detailed=detailed,
        declared_roles=roles,
        declared_roster=declared_family_roster(),
    )
    assert violations, "a pin covering one of two declared roles was accepted"
    assert any("where the deployment declares" in entry for entry in violations), (
        violations
    )


def test_the_pinned_check_refuses_a_detailed_count_that_left_the_document() -> None:
    """**Positive control.** Both seals pinned, the detailed count moved.

    The count and the seal are separate limbs because they fail separately: a
    product can serve the pinned bytes under one role while the other role's
    detail has drifted off what the README and the artifact both publish.
    """
    pinned = declared_addresses()
    roles = sorted(pinned)
    detailed = {
        str(role): int(value)
        for role, value in declared()["perspective_detailed_members"].items()
    }
    served_detail = dict(detailed)
    detailing = max(detailed, key=lambda role: detailed[role])
    served_detail[detailing] = detailed[detailing] - 1
    violations = pinned_perspective_violations(
        views=_pinned_subject(roles=roles, addresses=pinned, detailed=served_detail),
        pinned_addresses=pinned,
        declared_detailed=detailed,
        declared_roles=roles,
        declared_roster=declared_family_roster(),
    )
    assert violations, "a detailed count that left the document was accepted"
    assert any("was shown detail for" in entry for entry in violations), violations
    assert not any("where expected.yaml pins" in entry for entry in violations), (
        "the seal moved too, so this control is not isolating the count:"
        f" {violations}"
    )


def test_the_pinned_check_refuses_a_family_that_is_not_the_declared_one() -> None:
    """**Positive control.** A moved seal over a moved family says nothing.

    The seal is pinned against the family `expected.yaml` declares. If the served
    roster is not that family, a difference in the address is not evidence about
    the role — so the roster is checked first and named in its own violation.
    """
    pinned = declared_addresses()
    roles = sorted(pinned)
    detailed = {
        str(role): int(value)
        for role, value in declared()["perspective_detailed_members"].items()
    }
    subject = _pinned_subject(roles=roles, addresses=pinned, detailed=detailed)
    thinned = {
        role: Asked(
            asked_as=view.asked_as,
            payload={
                "nodes": list(view.nodes)[:-1],
                "detailed_members": list(view.payload["detailed_members"]),
            },
            content_address=view.content_address,
            refusal=None,
            observed=view.observed,
            served_vessels=view.served_vessels,
        )
        for role, view in subject.items()
        if view.payload is not None
    }
    violations = pinned_perspective_violations(
        views=thinned,
        pinned_addresses=pinned,
        declared_detailed=detailed,
        declared_roles=roles,
        declared_roster=declared_family_roster(),
    )
    assert violations, "a family missing a member was compared as the declared one"
    assert any("symmetric difference" in entry for entry in violations), violations


def test_the_pinned_check_accepts_the_declared_figures() -> None:
    """**Negative control.** The check is not one that refuses everything.

    Handed the declared roles, the declared family, the pinned seals and the
    declared detail, it must find nothing — otherwise the five controls above
    would be watching a check that cannot pass rather than a check that can fail.
    """
    pinned = declared_addresses()
    roles = sorted(pinned)
    detailed = {
        str(role): int(value)
        for role, value in declared()["perspective_detailed_members"].items()
    }
    violations = pinned_perspective_violations(
        views=_pinned_subject(roles=roles, addresses=pinned, detailed=detailed),
        pinned_addresses=pinned,
        declared_detailed=detailed,
        declared_roles=roles,
        declared_roster=declared_family_roster(),
    )
    assert not violations, violations


def test_no_role_to_entity_mapping_exists_anywhere_in_the_example() -> None:
    """`CFT-G16`'s structural limb — the substitution has no home in the tree.

    **A collection literal, never a token.** The word "class" appears in BOTH a
    class-conditioned projection and a role map keyed by class name, so reading
    the source for that token measures vocabulary. What a role map IS,
    structurally, is a Python collection whose keys or elements name a declared
    ROLE or a served ENTITY — and prose may name either freely, which is why the
    scan is over the parsed source and looks only inside ``dict``, ``list``,
    ``tuple`` and ``set`` literals. Docstrings and comments are invisible to it
    by construction.

    The only role-keyed document in this example is
    `artifacts/source-vocabulary.yaml::perspective_conditioning.roles`, which
    maps each role to a SIDE of one declared class axis and names no entity at
    all.
    """
    deployment = _load("deployment")
    forbidden = {str(role) for role in deployment.declared_roles()}
    forbidden |= {str(name) for name in declared_unresolved_members()}
    forbidden |= {str(name) for name in census("cycle_1")["members"]}
    forbidden |= {str(name) for name in census("cycle_2")["members"]}
    forbidden |= {str(census("anchor")["uri"]).rsplit("/", 1)[-1]}
    forbidden |= {
        str(member["uri"]) for member in census("duplicate_entity_pair")["members"]
    }

    sources = sorted(EXAMPLE.rglob("*.py"))
    assert sources, "no Python source was scanned, so this limb asserted nothing"

    offenders: list[str] = []
    for source in sources:
        tree = ast.parse(source.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Dict):
                entries = [key for key in node.keys if key is not None]
            elif isinstance(node, (ast.List, ast.Tuple, ast.Set)):
                entries = list(node.elts)
            else:
                continue
            for entry in entries:
                if not (isinstance(entry, ast.Constant) and isinstance(entry.value, str)):
                    continue
                named = sorted(
                    token for token in forbidden if token in entry.value
                )
                if named:
                    offenders.append(
                        f"{source.relative_to(REPO)} line {entry.lineno}:"
                        f" a collection literal names {named}"
                    )
    assert not offenders, (
        "a role-to-entity mapping exists in this example, which is the"
        " substitution CFT-G16 is sabotaged with:\n" + "\n".join(offenders)
    )


# ---------------------------------------------------------------------------
# Criterion 10, PRODUCT half — the duplicate pair is SURFACED.
# ---------------------------------------------------------------------------


def duplicate_violations(
    asked: Asked, *, declared_pair: Sequence[Mapping[str, Any]], duplicate_kind: str
) -> list[str]:
    """Every way the duplicate pair fails to be surfaced — criterion 10.

    **Three limbs, because there are three wrong answers and they are
    different.** Serving the two as unrelated subsidiaries double-counts a
    subsidiary, and a concentration denominator that double-counts is wrong in
    the safe-looking direction. Merging them loses a member. Reporting the pair
    somewhere the consumer cannot reach reports it to nobody.

    So: both are still SERVED as members; the pair is named in a finding that
    is IN the served payload; and exactly one of the two carries the declared
    LEI while the other carries none — which is the fact that makes the pair
    hard, because an LEI-keyed comparison finds nothing at all.

    Criterion 10's CENSUS half belongs to plan `24.4-04` and is asserted against
    the store by
    `tests/examples/test_cp_04_census.py::test_the_same_company_is_entered_twice_one_hop_from_the_anchor`.
    This is the half that says the PRODUCT surfaces it.
    """
    if asked.payload is None:
        return [f"criterion 10: the ask was refused — {asked.refusal!r}"]

    violations: list[str] = []
    want = {str(member["uri"]): member for member in declared_pair}
    missing = sorted(set(want) - set(asked.roster))
    if missing:
        violations.append(
            f"criterion 10: {missing} are not in the served tree. Neither member"
            " of a duplicate pair is dropped and neither is merged — a family"
            " that silently merges two is a member that vanished"
        )

    matching = [
        finding for finding in asked.findings if finding["type"] == duplicate_kind
    ]
    named = {
        local_name(member) for finding in matching for member in finding["members"]
    }
    if not set(want) <= named:
        violations.append(
            f"criterion 10: the served findings name {sorted(named)}, which does"
            f" not surface the declared pair {sorted(want)}. The product would"
            " be serving the same company twice as two distinct subsidiaries,"
            " and a concentration denominator that double-counts is wrong in"
            " the safe-looking direction"
        )
        return violations

    by_name = {local_name(node["uri"]): node for node in asked.nodes}
    for name, member in sorted(want.items()):
        node = by_name.get(name)
        if node is None:
            continue
        served_lei = node["lei"]
        want_lei = member["lei"]
        if served_lei != want_lei:
            violations.append(
                f"criterion 10: {name!r} was served carrying lei"
                f" {served_lei!r} where expected.yaml declares {want_lei!r}"
            )
        served_label = node["label"]
        if served_label != member["label"]:
            violations.append(
                f"criterion 10: {name!r} was served carrying label"
                f" {served_label!r} where expected.yaml declares"
                f" {member['label']!r}"
            )
    carrying = sorted(
        name
        for name in want
        if by_name.get(name) is not None and by_name[name]["lei"] is not None
    )
    declared_carrying = sorted(
        str(member["uri"]) for member in declared_pair if member["lei"] is not None
    )
    if carrying != declared_carrying:
        violations.append(
            f"criterion 10: {carrying} carry an LEI in the served payload where"
            f" expected.yaml declares {declared_carrying}. Which of the two"
            " carries it is the fact that makes this pair hard: an LEI-keyed"
            " comparison finds nothing, so the product folds the LABEL"
        )
    return violations


def test_the_duplicate_pair_is_surfaced_by_the_product(served: Asked) -> None:
    """Criterion 10, PRODUCT half. The same company entered twice is SURFACED.

    Both members are served, the pair is named in a finding the consumer holds,
    and exactly one of the two carries the declared LEI — the fact that makes an
    LEI-keyed comparison useless and a label fold necessary.
    """
    violations = duplicate_violations(
        served,
        declared_pair=census("duplicate_entity_pair")["members"],
        duplicate_kind=finding_types()["duplicate"],
    )
    assert not violations, (
        f"criterion 10 failed against {served.asked_as}:\n" + "\n".join(violations)
    )


def test_the_duplicate_check_refuses_two_unrelated_subsidiaries() -> None:
    """**Positive control.** Both served, nothing said — the wrong answer."""
    declared_pair = census("duplicate_entity_pair")["members"]
    silent = Asked(
        asked_as="both served, the pair unsurfaced",
        payload={
            "nodes": [
                {
                    "uri": f"http://example.org/fibo/{member['uri']}",
                    "lei": member["lei"],
                    "label": member["label"],
                }
                for member in declared_pair
            ],
            "findings": [],
        },
        content_address="deadbeef",
        refusal=None,
        observed=("Assembled",),
        served_vessels=("Assembled",),
    )
    violations = duplicate_violations(
        silent, declared_pair=declared_pair, duplicate_kind="duplicate_entity_pair"
    )
    assert violations, "two unsurfaced duplicates were reported as surfaced"
    assert any("distinct subsidiaries" in entry for entry in violations), violations


def test_the_duplicate_check_refuses_a_merged_pair() -> None:
    """**Positive control.** A merge is a member that vanished."""
    declared_pair = census("duplicate_entity_pair")["members"]
    merged = Asked(
        asked_as="the two merged into one",
        payload={
            "nodes": [
                {
                    "uri": f"http://example.org/fibo/{declared_pair[0]['uri']}",
                    "lei": declared_pair[0]["lei"],
                    "label": declared_pair[0]["label"],
                }
            ],
            "findings": [
                {
                    "type": "duplicate_entity_pair",
                    "members": [
                        f"http://example.org/fibo/{member['uri']}"
                        for member in declared_pair
                    ],
                    "closing_edge": None,
                }
            ],
        },
        content_address="deadbeef",
        refusal=None,
        observed=("Assembled",),
        served_vessels=("Assembled",),
    )
    violations = duplicate_violations(
        merged, declared_pair=declared_pair, duplicate_kind="duplicate_entity_pair"
    )
    assert violations, "a merged pair was reported as two served members"
    assert any("not in the served tree" in entry for entry in violations), violations


# ---------------------------------------------------------------------------
# The anchor block is held to the SAME admission as the edges beside it.
#
# NOT A GATE, and no id is minted for it. The roster is SIXTEEN,
# `CFT-G01`..`CFT-G16`, and `CFT-G17` is WITHDRAWN. This is the close panel's
# first finding of the 2026-09-01 second bundle, and its home is here because
# the anchor block is payload shape.
# ---------------------------------------------------------------------------


def test_the_served_anchor_is_a_member_of_the_served_tree(served: Asked) -> None:
    """The payload's anchor is in its own `nodes` block, by name.

    ``projection.py::FamilyTreeProjection.invoke`` built the anchor block from
    ``scenario.anchor_uri`` and ``scenario.facts`` — the SOURCE READ — while the
    ``edges`` block two lines below admitted a pair only when both ends were in
    the operator output. So the payload could NAME a company, its LEI, its label
    and its seven-class chain that its own served member set did not contain.
    Asserted here as a property of what reached the consumer, and refused at
    source by ``projection.py::refuse_unadmitted_anchor``.
    """
    assert served.payload is not None, served.refusal
    anchor = str(served.payload["anchor"]["uri"])
    roster = sorted(str(node["uri"]) for node in served.nodes)
    assert anchor in roster, (
        f"the payload names {anchor!r} as its anchor and its own `nodes` block"
        f" carries {len(roster)} member(s) that do not include it. An anchor"
        " outside the served member set is the same leak the `edges` block"
        " refuses by admitting a pair only when both ends are served"
    )


def test_the_anchor_check_refuses_an_anchor_outside_the_admitted_set() -> None:
    """**Positive control.** The SHIPPED refusal, handed a divergent subject."""
    projection = _load("projection")
    with pytest.raises(RuntimeError) as refused:
        projection.refuse_unadmitted_anchor(
            "x://not-admitted", admitted={"x://one", "x://two"}
        )
    assert "is not in the member set the operators admitted" in str(refused.value)


def test_the_anchor_check_refuses_an_empty_admitted_set() -> None:
    """**Vacuity control.** Over no members the test passes by comparing nothing."""
    projection = _load("projection")
    with pytest.raises(RuntimeError) as refused:
        projection.refuse_unadmitted_anchor("x://anchor", admitted=set())
    assert "refusing a check that cannot fail" in str(refused.value)


def test_the_anchor_check_admits_the_compliant_shape() -> None:
    """**Compliance control.** A later limb cannot quietly forbid the real case."""
    projection = _load("projection")
    projection.refuse_unadmitted_anchor("x://anchor", admitted={"x://anchor", "x://b"})
