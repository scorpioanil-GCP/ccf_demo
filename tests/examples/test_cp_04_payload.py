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
roles' views and the class that explains the difference).

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

#: The finding type a cycle is reported under, and the one the twenty
#: row-less members are reported under. Read from the shipped modules rather
#: than spelled here, so a product that renamed either is a failure in the
#: gate's subject rather than a silent miss.
#:
#: Resolved lazily in :func:`finding_types` because the example's modules are
#: loaded through :func:`_load`, which is import-order sensitive.
CYCLE_FINDING_ATTR = "FINDING_OWNERSHIP_CYCLE"
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
    """The three finding type tokens, read from the shipped modules."""
    deployment = _load("deployment")
    projection = _load("projection")
    return {
        "cycle": str(getattr(deployment, CYCLE_FINDING_ATTR)),
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
        # The status the shipped verdict carries, read off the shipped type
        # rather than spelled here — a product that moved 400 to 409 should
        # move this gate's subject with it.
        status=int(_load("produce").ParameterNotSupported("x", "y").status),
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
