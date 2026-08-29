"""What `examples/cp-01-counterparty-reference-snapshot` actually serves.

The example reads the store `backends.yaml` names through an environment
variable. Locally that points at the real counterparty estate; here the schema
comes from `tests/examples/fixtures/cp_01_counterparty_schema.sql` and the rows
from `tests/examples/fixtures/cp_01_counterparty_rows.sql`, both applied by the
``seeded`` fixture and by nothing else — `24-CONTEXT.md` `D-25` and `D-27`: *the
fixture is seeded by the test, never committed as a database.*

Marked ``postgres``: every fixture requests the session-scoped ``postgres_dsn``.
Unset ``CCF_TEST_POSTGRES_DSN`` starts a container; ``CCF_REQUIRE_POSTGRES``
turns a skip into a failure.

**WHAT THIS MODULE IS FOR.** Each test below is one of the specification's
product-specific gates (`CP-SPEC-001` §D.7) or one of its §G acceptance
criteria, asserted against a run rather than against a docstring. Two of them
assert a REFUSAL, and one of those — :func:`test_a_no_lei_entity_is_refused_by
_the_ttl_lower_bound` — asserts a failure the specification itself records as a
defect it expects (§F.4 finding 8). **It is written to pass while the defect
stands and to FAIL when it is fixed**, which is what makes it the evidence the
deviation gets taken back with rather than a test that ratifies a bug.
"""

from __future__ import annotations

import importlib
import os
import pathlib
import sys
from decimal import Decimal
from typing import Any

import psycopg
import pytest
import yaml

from ccf.agents.errors import AssemblyRefused
from ccf.contracts.canonical import content_hash

REPO = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO / "examples" / "cp-01-counterparty-reference-snapshot"
FIXTURES = pathlib.Path(__file__).parent / "fixtures"
SCHEMA_SQL = FIXTURES / "cp_01_counterparty_schema.sql"
ROWS_SQL = FIXTURES / "cp_01_counterparty_rows.sql"

pytestmark = pytest.mark.postgres


def _load(name: str) -> Any:
    """Load one of the example's modules under its own bare name.

    The example is a directory of modules rather than a package, and its modules
    import each other by bare name — ``assembler`` does ``import produce``,
    ``run`` does ``import assembler``. Loading them under prefixed names would
    leave a SECOND copy of ``produce`` in ``sys.modules``, and an ``isinstance``
    across the two copies would then be false for reasons that have nothing to
    do with the code under test.
    """
    if str(EXAMPLE) not in sys.path:
        sys.path.insert(0, str(EXAMPLE))
    return importlib.import_module(name)


def _dsn_variable() -> str:
    """The env var `backends.yaml` declares, read through the deployment's keys."""
    deployment = _load("deployment")
    document = yaml.safe_load(deployment.BACKENDS.read_text(encoding="utf-8"))
    source = document[deployment.DECLARATION][deployment.SOURCES]
    binding = source[deployment.SOURCE_BINDING][deployment.SETTINGS]
    return str(binding[deployment.SOURCE_SETTING_DSN][deployment.FROM_ENV])


@pytest.fixture(scope="module")
def seeded(postgres_dsn: str) -> Any:
    """A seeded container, with the DSN exported where `backends.yaml` reads it."""
    with psycopg.connect(postgres_dsn, autocommit=True) as db, db.cursor() as cursor:
        cursor.execute(SCHEMA_SQL.read_text(encoding="utf-8"))
        cursor.execute(ROWS_SQL.read_text(encoding="utf-8"))

    variable = _dsn_variable()
    previous = os.environ.get(variable)
    os.environ[variable] = postgres_dsn
    yield postgres_dsn
    if previous is None:
        os.environ.pop(variable, None)
    else:
        os.environ[variable] = previous


def _serve(seeded: str, **kwargs: Any) -> Any:
    """Run one assembly through the assembler seam, as `run.py` does.

    Returns the SPINE's value, captured through the observer, because the
    Protocol's return type carries the assembly's governance and not the served
    vessel — see `assembler.py`'s note on why that is a seam property rather
    than an omission.
    """
    import tempfile

    deployment = _load("deployment")
    assembler = _load("assembler")

    anchor = kwargs.pop("anchor", None)
    principal = kwargs.pop("principal", None)
    parameters: dict[str, object] = {
        deployment.PARAM_DEBT_TOLERANCE: Decimal(
            str(deployment.demonstration_debt_tolerance())
        ),
        deployment.PARAM_INCLUDE_LAPSED: kwargs.pop("include_lapsed", False),
    }
    parameters.update(kwargs)

    asked = deployment.request(parameters=parameters)
    if anchor is not None:
        asked = asked.model_copy(update={"subject": anchor})

    with tempfile.TemporaryDirectory(prefix="cp01-test-") as tmp:
        root = pathlib.Path(tmp)
        captured: list[object] = []
        seam = assembler.CounterpartyAssembler(
            config=deployment.CONFIG,
            root=root,
            connection=deployment.connection(root=root),
            read=(
                deployment.read
                if principal is None
                else (lambda b, q: deployment.read(b, q, principal_id=principal))
            ),
            plan_class=deployment.plan_class(),
            observer=captured.append,
        )
        governed = seam.assemble(
            request=asked,
            perspective=deployment.perspective(),
            tenant_id=deployment.tenant_id(),
        )
        return captured[0] if captured else governed


# --------------------------------------------------------------------------
# The seed is measured before anything is asserted against it.
# --------------------------------------------------------------------------
def test_the_seeder_seeded(seeded: str) -> None:
    """A silent seed would make every assertion below pass against nothing.

    The control returns a DIFFERENT number: the same query with an impossible
    LEI returns 0 while the real predicate returns the fixture's own count. A
    count with no control is not a measurement — this repository has recorded
    that lesson three times.
    """
    deployment = _load("deployment")
    with psycopg.connect(seeded) as db, db.cursor() as cursor:
        cursor.execute(
            f"select count(*) from {deployment.SOURCE_SCHEMA}"  # noqa: S608
            f".{deployment.TABLE_ENTITY} where lei = %s",
            (deployment.demonstration_anchor(),),
        )
        real = int(cursor.fetchone()[0])
        cursor.execute(
            f"select count(*) from {deployment.SOURCE_SCHEMA}"  # noqa: S608
            f".{deployment.TABLE_ENTITY} where lei = %s",
            ("NOT-A-REAL-LEI",),
        )
        control = int(cursor.fetchone()[0])
    assert real == 1, f"the anchor was not seeded (control returned {control})"
    assert control == 0, "the control matched, so the predicate proves nothing"


# --------------------------------------------------------------------------
# §G acceptance criteria and §D.7 product-specific gates.
# --------------------------------------------------------------------------
def test_the_anchor_resolves_through_the_vendor_authority(seeded: str) -> None:
    """§G criterion 4, and `CPR-G07` — every attribute names its authority."""
    produce = _load("produce")
    assembled = _serve(seeded)
    assert isinstance(assembled, produce.Assembled)
    counterparty = assembled.product.payload["counterparty"]
    assert counterparty["identity_authority"] == "lei-reference-data"
    assert counterparty["legal_name"] == "AVIS BUDGET GROUP, INC."


def test_both_addresses_are_present_and_distinguishable(seeded: str) -> None:
    """`CPR-G01` — §C.4 trap 1, the defect that motivated Wave 20.

    Compared CASE- AND WHITESPACE-NORMALISED. A raw comparison reports 69
    differing entities estate-wide where 65 genuinely differ: four carry
    `WILMINGTON` against `Wilmington` and are ONE address typed twice. A gate
    written on raw inequality would score those as two addresses.
    """
    assembled = _serve(seeded)
    counterparty = assembled.product.payload["counterparty"]
    legal = counterparty["legal_address"]
    hq = counterparty["headquarters_address"]
    assert legal["city"] and hq["city"], "an address is missing entirely"

    def norm(value: str) -> str:
        return " ".join(value.split()).casefold()

    assert norm(legal["city"]) != norm(hq["city"]), (
        "the two addresses are the same place, so this anchor cannot"
        " demonstrate the trap it was chosen for"
    )
    assert norm(legal["city"]) == "wilmington"
    assert norm(hq["city"]) == "parsippany"


def test_the_seven_class_type_chain_is_asserted(seeded: str) -> None:
    """`CPR-G06` — §C.3. A partial chain propagates catalog-wide."""
    assembled = _serve(seeded)
    chain = assembled.product.payload["counterparty"]["type_chain"]
    assert len(chain) == 7, f"a partial chain of {len(chain)} propagates"
    assert chain[0] == "cmns-pts:Agent"
    assert chain[-1] == "fibo-be-le-cb:Corporation"
    assert any(iri.startswith("cmns-org:") for iri in chain), (
        "LegalEntity moved to OMG Commons; a chain with no cmns-org: member"
        " is the pre-remediation binding"
    )


def test_entitlement_discriminates_as_sets_with_a_negative_control(
    seeded: str,
) -> None:
    """`CPR-G02` — §D.3. Counts SETS, never sizes.

    The negative control is the half that matters: a principal differenced
    against ITSELF must see the same thing, so a `DISCRIMINATES` verdict is
    known to be capable of reading the other way. A gate that has never been
    observed failing is not evidence.
    """
    produce = _load("produce")
    visible: dict[str, str | None] = {}
    for principal in (
        "PRIN-COV-001",
        "PRIN-RES-002",
        "PRIN-KYC-004",
        "PRIN-TRD-003",
    ):
        assembled = _serve(seeded, principal=principal)
        assert isinstance(assembled, produce.Assembled)
        counterparty = assembled.product.payload["counterparty"]
        visible[principal] = None if counterparty is None else counterparty["lei"]

    assert visible["PRIN-COV-001"] is not None, "the US grant should see a US-DE entity"
    assert visible["PRIN-RES-002"] is not None
    assert visible["PRIN-KYC-004"] is None, "an EU grant must not see a US-DE entity"
    assert visible["PRIN-TRD-003"] is None

    # NEGATIVE CONTROL — the same principal twice must agree. If this fails,
    # the assertions above are measuring run-to-run noise rather than policy.
    again = _serve(seeded, principal="PRIN-COV-001")
    assert again.product.payload["counterparty"]["lei"] == visible["PRIN-COV-001"]


def test_a_suppressed_entity_leaves_no_marker(seeded: str) -> None:
    """`CPR-G04` — §B.2's suppression rule.

    *"The payload must carry no count, marker, or placeholder indicating that
    anything was withheld."* A `"1 entity hidden"` notice IS a disclosure.
    """
    assembled = _serve(seeded, principal="PRIN-KYC-004")
    payload = assembled.product.payload
    assert payload["counterparty"] is None
    flattened = repr(payload).casefold()
    for leak in ("hidden", "withheld", "suppress", "redact", "denied", "filtered"):
        assert leak not in flattened, f"the payload discloses suppression via {leak!r}"
    assert "excluded" not in payload, (
        "an `excluded` block belongs to the caller-requested lapsed exclusion,"
        " not to a policy suppression — carrying it here would tell an"
        " unentitled caller that something exists"
    )


def test_a_lapsed_entity_is_excluded_entirely_by_default(seeded: str) -> None:
    """`CPR-G01`'s second half — §B.4. Excluded, never returned unflagged."""
    assembled = _serve(seeded, anchor="549300TRW1LZMDJZAQ78")
    payload = assembled.product.payload
    assert payload["counterparty"] is None
    assert payload["excluded"]["reason"] == "registration-lapsed"


def test_include_lapsed_returns_it_with_status_first_class(seeded: str) -> None:
    """§B.4 — and the content address must DIFFER from the exclusion's.

    That difference is what proves the parameter changes the PAYLOAD rather
    than the read: every value of it compiles to the same pinned source query.
    """
    excluded = _serve(seeded, anchor="549300TRW1LZMDJZAQ78")
    included = _serve(seeded, anchor="549300TRW1LZMDJZAQ78", include_lapsed=True)
    counterparty = included.product.payload["counterparty"]
    assert counterparty is not None
    assert counterparty["registration_status"] == "LAPSED"
    assert content_hash(included.product) != content_hash(excluded.product), (
        "the two answers share a content address, so the parameter moved"
        " nothing the product is addressed by"
    )


def test_an_unresolvable_anchor_fails_closed(seeded: str) -> None:
    """§D.2 step 1 — 404, *"never an empty payload"*."""
    with pytest.raises(AssemblyRefused, match="resolved to no entity"):
        _serve(seeded, anchor="NOT-A-REAL-ANCHOR")


def test_as_of_is_declared_and_always_refused(seeded: str) -> None:
    """`CPR-G05` — Standard §2.4's declared-but-inert parameter.

    *"A parameter that appears to work and does not will be relied on in a
    dispute."* It must be DISCOVERABLE in the contract and REFUSED at the door,
    and both halves are asserted: the declaration, then the refusal.
    """
    deployment = _load("deployment")
    declared = yaml.safe_load(deployment.CONFIG.read_text(encoding="utf-8"))
    properties = declared["request_contract"]["arguments"]["properties"]
    assert "as_of" in properties, "an undeclared parameter tells a caller nothing"
    assert "as_of" in deployment.unsupported_arguments()

    with pytest.raises(AssemblyRefused, match="not_supported_at_tier"):
        _serve(seeded, as_of="2026-01-01T00:00:00+00:00")


def test_the_product_is_byte_identical_across_identical_requests(
    seeded: str,
) -> None:
    """§G criterion 4 — `payload_hash` is stable across identical requests.

    Assembly Mode 1: no model is in the path, so reproduction is exact rather
    than similar. Two runs, same anchor, same principal, same pinned
    `asked_at` — one address.
    """
    first = _serve(seeded)
    second = _serve(seeded)
    assert content_hash(first.product) == content_hash(second.product)


def test_a_no_lei_entity_reports_the_lower_freshness_ceiling(seeded: str) -> None:
    """§G criterion 3 and `CPR-G03` — the asymmetry is IN THE PAYLOAD.

    *"An entity resolved through rows two or three carries a materially lower
    ceiling on F, and that asymmetry is stated in the payload rather than
    averaged into a single freshness claim."*

    **This asserts the SOURCE READ rather than a served product**, because the
    product for a no-LEI entity does not currently survive the TTL gate — see
    the test below. Splitting the two keeps this criterion measurable while the
    defect stands, instead of leaving §G criterion 3 untested until it is fixed.
    """
    deployment = _load("deployment")
    read = deployment.source_read(
        deployment.tenant_id(),
        at=deployment.request(parameters={}).asked_at,
        subject="CLI-000101",
        principal_id="PRIN-COV-001",
    )
    resolved = read.resolved
    assert resolved is not None
    assert resolved.authority == "internal-client-master"
    assert resolved.signal_class == "internal_kyc"
    assert resolved.freshness_ceiling_days == 270, (
        "a no-LEI entity advertising the 24-hour vendor SLA is the exact error"
        " the per-signal-class rule exists to prevent"
    )
    assert "lei" not in resolved.attributes, (
        "a SYN- placeholder would resolve like a real anchor and defeat the"
        " §D counterfactual these rows exist to demonstrate"
    )


def test_a_no_lei_entity_is_refused_by_the_ttl_lower_bound(seeded: str) -> None:
    """`CPR-G09` — and this test is written to FAIL when the defect is fixed.

    §B.1 element 3 declares a 24-hour TTL anchored `from_entity_freshness`. For
    an entity resolved through the internal client master the anchor is
    `kyc_last_refresh`, which is MONTHS old by design, so `expires_at` lands in
    the past and `src/ccf/products/gates.py::_refuse_ttl` refuses on the first
    call — the whole population §C.4 trap 2 exists to stop being excluded.

    **This is the evidence, not the ratification.** `spec_generation.md` §2:
    *"a Gate-2 value that contradicts an approved Gate-1 decision is a deviation
    — take it back, do not absorb it."* The refusal is asserted here so the
    deviation is carried by a run rather than by an argument, and §F.4 finding 8
    is what it is carried back to. When the TTL declaration is corrected this
    test goes RED, and that redness is the signal to close the finding — not a
    regression to route around.
    """
    with pytest.raises(RuntimeError, match="ttl-bounds"):
        _serve(seeded, anchor="CLI-000101")
