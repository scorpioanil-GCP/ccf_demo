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
import re
import sys
from decimal import Decimal
from typing import Any

import psycopg
import pytest
import yaml

from ccf.agents.assembler import AssemblyOutcome
from ccf.agents.errors import AssemblyRefused
from ccf.contracts.canonical import content_hash
from ccf.halflife.assessment import DebtSignal

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

    **AND THREE EXAMPLES NOW SHARE THOSE BARE NAMES.** cp-00, cp-01 and cp-02
    each ship a ``deployment``, a ``produce`` and an ``assembler``, while
    ``make leg-postgres`` runs ``pytest tests -m postgres`` as ONE session over
    the whole tree. Whichever module is imported first wins the name, and the
    second module's tests then read the first one's constants —
    ``module 'deployment' has no attribute 'EXPECTED'`` being the polite failure
    and a silently wrong value being the impolite one.

    So the cache is checked against THIS example's directory and evicted when it
    holds somebody else's. Evicting the whole family together rather than one
    name at a time matters: leaving cp-01's ``produce`` behind while reloading
    cp-02's ``assembler`` would rebuild exactly the split-identity problem the
    bare names exist to avoid.
    """
    if sys.path[:1] != [str(EXAMPLE)]:
        while str(EXAMPLE) in sys.path:
            sys.path.remove(str(EXAMPLE))
        sys.path.insert(0, str(EXAMPLE))
    family = ("deployment", "produce", "assembler", "run")
    for cached_name in family:
        cached = sys.modules.get(cached_name)
        if cached is None:
            continue
        origin = str(getattr(cached, "__file__", ""))
        if not origin.startswith(str(EXAMPLE)):
            for sibling in family:
                sys.modules.pop(sibling, None)
            break
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


#: A nonexistent anchor, the control every refusal is compared against. The
#: same string `test_an_unresolvable_anchor_fails_closed` uses.
MISSING_ANCHOR = "NOT-A-REAL-ANCHOR"

#: Words a suppression-silent refusal must not carry (`D-IMPL-245` (4)).
_LEAK_WORDS = re.compile(r"entitle|principal|grant|visible|withheld", re.IGNORECASE)
_SUBJECT_TOKEN = "<subject>"


def _demonstration_subject() -> str:
    """The subject of the request `_serve` builds, read off that request.

    Never a literal: the refusal text carries the subject token, and the
    sameness check has to know which token to normalize away.
    """
    deployment = _load("deployment")
    asked = deployment.request(
        parameters={
            deployment.PARAM_DEBT_TOLERANCE: Decimal(
                str(deployment.demonstration_debt_tolerance())
            ),
            deployment.PARAM_INCLUDE_LAPSED: False,
        }
    )
    return str(asked.subject)


def refusal_sameness_violations(
    excluded: str, missing: str, *, excluded_subject: str, missing_subject: str
) -> list[str]:
    """Every way two refusal texts fail §B.2's indistinguishability, by name.

    (i) with each text's own subject token replaced by ``<subject>``, the two
    must be identical — a difference is something the caller could learn;
    (ii) neither may carry a word from the leak list (``entitle``,
    ``principal``, ``grant``, ``visible``, ``withheld``, case-folded); (iii)
    neither may be empty, because two empty strings are identical for no reason
    at all. Returns an empty list only when all three hold. Three controls
    beside this function watch it refuse.
    """
    violations: list[str] = []
    if not excluded or not missing:
        violations.append(
            f"empty refusal text: excluded={excluded!r} missing={missing!r}"
        )
    normalized_excluded = (
        excluded.replace(excluded_subject, _SUBJECT_TOKEN)
        if excluded_subject
        else excluded
    )
    normalized_missing = (
        missing.replace(missing_subject, _SUBJECT_TOKEN)
        if missing_subject
        else missing
    )
    if normalized_excluded != normalized_missing:
        violations.append(
            "the two refusal texts differ modulo the subject token:"
            f" {normalized_excluded!r} vs {normalized_missing!r}"
        )
    for label, text in (("excluded", excluded), ("missing", missing)):
        for match in _LEAK_WORDS.finditer(text):
            violations.append(
                f"the {label} refusal carries the word {match.group(0)!r}"
            )
    return violations


def test_refusal_sameness_reports_a_one_word_difference() -> None:
    """Control for `refusal_sameness_violations`: one differing word is a violation naming the difference."""
    found = refusal_sameness_violations(
        "subject 'A' is not available",
        "subject 'B' is not there",
        excluded_subject="A",
        missing_subject="B",
    )
    assert any("differ" in v for v in found), found
    # The same pair with the difference removed is clean — the detector reads
    # the words, not the pair.
    assert (
        refusal_sameness_violations(
            "subject 'A' is not available",
            "subject 'B' is not available",
            excluded_subject="A",
            missing_subject="B",
        )
        == []
    )


def test_refusal_sameness_reports_a_leaking_word() -> None:
    """Control for `refusal_sameness_violations`: "not entitled" is a violation naming the word."""
    found = refusal_sameness_violations(
        "subject 'A' is not entitled",
        "subject 'B' is not entitled",
        excluded_subject="A",
        missing_subject="B",
    )
    assert any("entitle" in v for v in found), found


def test_refusal_sameness_reports_empty_texts() -> None:
    """Control for `refusal_sameness_violations`: two empty texts are a violation, not a match."""
    found = refusal_sameness_violations(
        "", "", excluded_subject="A", missing_subject="B"
    )
    assert found and any("empty" in v for v in found), found


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

    An entitled principal is SERVED and its outcome is the set of LEIs it saw;
    an unentitled one is REFUSED and its outcome is the EMPTY set — the refusal
    carrying the one text a nonexistent counterparty receives. The two outcomes
    are compared as sets, never as sizes. History: the unentitled principals
    were previously served `counterparty: None` (the Policy step's removal,
    `D_c 1 / fail_closed`); `D-IMPL-245` (4), 2026-09-03, moved them to the
    refusal — policy exclusion is not Context Debt.

    The negative control is the half that matters: a principal differenced
    against ITSELF must see the same thing, so a `DISCRIMINATES` verdict is
    known to be capable of reading the other way. A gate that has never been
    observed failing is not evidence.
    """
    produce = _load("produce")
    subject = _demonstration_subject()
    with pytest.raises(AssemblyRefused) as missing:
        _serve(seeded, anchor=MISSING_ANCHOR)

    outcome: dict[str, frozenset[str]] = {}
    refusals: dict[str, str] = {}
    for principal in (
        "PRIN-COV-001",
        "PRIN-RES-002",
        "PRIN-KYC-004",
        "PRIN-TRD-003",
    ):
        try:
            assembled = _serve(seeded, principal=principal)
        except AssemblyRefused as refused:
            outcome[principal] = frozenset()
            refusals[principal] = str(refused)
            continue
        assert isinstance(assembled, produce.Assembled)
        counterparty = assembled.product.payload["counterparty"]
        assert counterparty is not None, (
            f"{principal} was served a product with no counterparty — the"
            " Policy-removed serve D-IMPL-245 (4) retired"
        )
        outcome[principal] = frozenset({counterparty["lei"]})

    assert outcome["PRIN-COV-001"], "the US grant should see a US-DE entity"
    assert outcome["PRIN-RES-002"]
    assert "PRIN-KYC-004" in refusals, (
        "an EU grant must not see a US-DE entity — it is REFUSED, not served"
    )
    assert "PRIN-TRD-003" in refusals
    assert outcome["PRIN-KYC-004"] == frozenset()
    assert outcome["PRIN-TRD-003"] == frozenset()
    # SETS, never sizes: the served set of an entitled principal differs from
    # the empty set of an unentitled one.
    assert outcome["PRIN-COV-001"] != outcome["PRIN-KYC-004"]
    assert outcome["PRIN-RES-002"] != outcome["PRIN-TRD-003"]
    for principal, text in refusals.items():
        violations = refusal_sameness_violations(
            text,
            str(missing.value),
            excluded_subject=subject,
            missing_subject=MISSING_ANCHOR,
        )
        assert not violations, f"CPR-G02: {principal}: " + "; ".join(violations)
        assert principal not in text

    # NEGATIVE CONTROL — the same principal twice must agree. If this fails,
    # the assertions above are measuring run-to-run noise rather than policy.
    again = _serve(seeded, principal="PRIN-COV-001")
    assert (
        frozenset({again.product.payload["counterparty"]["lei"]})
        == outcome["PRIN-COV-001"]
    )


def test_a_suppressed_entity_leaves_no_marker(seeded: str) -> None:
    """`CPR-G04` — §B.2's suppression rule, at the whole product boundary.

    *"The payload must carry no count, marker, or placeholder indicating that
    anything was withheld."* A `"1 entity hidden"` notice IS a disclosure.
    Since `D-IMPL-245` (4) (2026-09-03) a Policy-removed entity is not served
    at all — previously it was served `counterparty: None` and this test read
    the payload for a leak. Now the refusal text IS the boundary: it must name
    neither the principal nor the entitlement, and it must be the text a
    nonexistent counterparty receives.
    """
    with pytest.raises(AssemblyRefused) as info:
        _serve(seeded, principal="PRIN-KYC-004")
    text = str(info.value)
    flattened = text.casefold()
    for leak in (
        "hidden",
        "withheld",
        "suppress",
        "redact",
        "denied",
        "filtered",
        "entitle",
        "principal",
        "grant",
        "visible",
    ):
        assert leak not in flattened, (
            f"the refusal discloses suppression via {leak!r}: {text!r}"
        )
    assert "PRIN-KYC-004" not in text, f"the refusal names the principal: {text!r}"
    with pytest.raises(AssemblyRefused) as missing:
        _serve(seeded, anchor=MISSING_ANCHOR)
    violations = refusal_sameness_violations(
        text,
        str(missing.value),
        excluded_subject=_demonstration_subject(),
        missing_subject=MISSING_ANCHOR,
    )
    assert not violations, "CPR-G04: " + "; ".join(violations)


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
    with pytest.raises(AssemblyRefused, match="is not available"):
        _serve(seeded, anchor="NOT-A-REAL-ANCHOR")


def test_as_of_is_declared_and_always_refused(seeded: str) -> None:
    """`CPR-G05` — Standard §2.4's declared-but-inert parameter.

    *"A parameter that appears to work and does not will be relied on in a
    dispute."* It must be DISCOVERABLE in the contract and REFUSED at the door,
    and both halves are asserted: the declaration, then the refusal.

    Rewritten under 24.5-FLIP-ROSTER.md (`24.5-L-12`, `24.5-L-13`): the
    refusal is now the SDK's own verdict, returned as DATA by the tier step of
    `refuse_request` — reason `not-supported-at-tier`, carrying the
    declaration's prose — before the product's own branch could raise.
    """
    deployment = _load("deployment")
    declared = yaml.safe_load(deployment.CONFIG.read_text(encoding="utf-8"))
    properties = declared["request_contract"]["arguments"]["properties"]
    assert "as_of" in properties, "an undeclared parameter tells a caller nothing"
    assert "as_of" in deployment.unsupported_arguments()

    from ccf.products.request import ProductRequestViolation

    served = _serve(seeded, as_of="2026-01-01T00:00:00+00:00")
    assert isinstance(served, ProductRequestViolation), (
        "as_of was not refused by the SDK's tier verdict; the seam handed back"
        f" {type(served).__name__}"
    )
    assert served.reason == "not-supported-at-tier", (
        f"the refusal reads {served.reason!r} rather than not-supported-at-tier"
    )
    assert served.key == "as_of", f"the refusal names {served.key!r}"
    assert "400 not_supported_at_tier" in served.detail, (
        "the refusal's detail does not carry the Standard's status token"
    )
    assert deployment.unsupported_arguments()["as_of"] in served.detail, (
        "the verdict does not carry the declaration's own reason prose"
    )


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


# --------------------------------------------------------------------------
# The ninth gate, backfilled in Phase 24.5 (ledger row 24.5-L-49, ROADMAP
# criterion 13). It occurred ZERO times in this module until then, because the
# specification records (§F.2 row 20) that the estate holds no principal whose
# grant set matches no entity — and a gate with no fixture cannot be watched.
# The principal is constructed HERE, in the test; no fixture row was added.
# --------------------------------------------------------------------------
def test_cpr_g08_a_principal_matching_no_entity_is_refused_and_cannot_be_told_from_a_missing_one(
    seeded: str,
) -> None:
    """`CPR-G08` — a principal whose grant set matches no entity is REFUSED, and the refusal cannot be told from the one a nonexistent counterparty receives.

    THE PRINCIPAL IS CONSTRUCTED HERE. `PRIN-NONE-000` is a name with no
    grant row, asserted against the seeded grant table before it is asked —
    an empty grant set is what a principal nobody granted anything HAS, which
    is exactly the gate's subject, so no fixture row is needed and none was
    added (spec §F.2 row 20 records that the estate holds no such principal).

    `D-IMPL-245` (4), Dave, 2026-09-03: *"refuse. Do not serve 200 + D_c=1 +
    fail_closed. … policy exclusion is not Context Debt"*, and the refusal
    obeys suppression silence — *"make unauthorized/not-visible
    indistinguishable from unavailable at that product boundary."* The
    disjunction the previous shape read ("a fail-closed refusal OR an explicit
    debt contribution") is retired: the served-with-debt limb was the shape the
    ruling rejects, and the early `return` on any refusal was a check that could
    not fail. Now the refusal is asserted BY NAME; its text is compared modulo
    the subject token against the nonexistent-anchor refusal; the word list
    `entitle|principal|grant|visible|withheld` is refused; and the entitled
    principal is the positive control — served, present, `OK` — so the refusal
    is shown to be a difference and not a constant.
    """
    deployment = _load("deployment")
    produce = _load("produce")
    principal = "PRIN-NONE-000"
    with psycopg.connect(seeded) as db, db.cursor() as cursor:
        cursor.execute(
            f"select count(*) from {deployment.SOURCE_SCHEMA}"  # noqa: S608
            f".{deployment.TABLE_PRINCIPAL_JURISDICTION} where principal_id = %s",
            (principal,),
        )
        grants = int(cursor.fetchone()[0])
    assert grants == 0, (
        f"CPR-G08: {principal} holds {grants} grant row(s); the gate's subject"
        " is a principal whose grant set matches NO entity"
    )

    control = _serve(seeded, principal="PRIN-COV-001")
    assert isinstance(control, produce.Assembled)
    assert control.product.payload["counterparty"] is not None
    assert control.product.debt.signal == DebtSignal.OK, (
        "CPR-G08: the entitled control is not served OK, so a fail-closed"
        " reading below would not be a difference"
    )

    with pytest.raises(AssemblyRefused) as excluded:
        _serve(seeded, principal=principal)
    with pytest.raises(AssemblyRefused) as missing:
        _serve(seeded, anchor=MISSING_ANCHOR)
    violations = refusal_sameness_violations(
        str(excluded.value),
        str(missing.value),
        excluded_subject=_demonstration_subject(),
        missing_subject=MISSING_ANCHOR,
    )
    assert not violations, "CPR-G08: " + "; ".join(violations)
    assert principal not in str(excluded.value), (
        f"CPR-G08: the refusal names the principal: {excluded.value!s}"
    )


def test_the_served_outcome_names_the_module_assembler_version(seeded: str) -> None:
    """The Protocol's return names this module's assembler identity, pinned at `1.0.1`.

    `D-IMPL-245` am.1: an assembler materially corrected in 24.5.1 bumps PATCH to
    `1.0.1` — the dead compatibility branch for the inert parameter was deleted from this rung's
    `assembler.py`, so the implementation changed — and am.3: never `1.0.2`.
    `_serve` discards the Protocol's return (`governed`) for the spine's captured
    value, so the seam is constructed here the same way and `governed` is KEPT.
    This is the in-process identity; the transcript line `assembled by` carries it
    as evidence, and Decision Replay carries none of it today (am.1).
    """
    import tempfile

    deployment = _load("deployment")
    assembler = _load("assembler")
    parameters: dict[str, object] = {
        deployment.PARAM_DEBT_TOLERANCE: Decimal(
            str(deployment.demonstration_debt_tolerance())
        ),
        deployment.PARAM_INCLUDE_LAPSED: False,
    }
    asked = deployment.request(parameters=parameters)
    with tempfile.TemporaryDirectory(prefix="cp01-test-") as tmp:
        root = pathlib.Path(tmp)
        captured: list[object] = []
        seam = assembler.CounterpartyAssembler(
            config=deployment.CONFIG,
            root=root,
            connection=deployment.connection(root=root),
            read=deployment.read,
            plan_class=deployment.plan_class(),
            observer=captured.append,
        )
        governed = seam.assemble(
            request=asked,
            perspective=deployment.perspective(),
            tenant_id=deployment.tenant_id(),
        )
    assert captured, "the observer never fired, so nothing was assembled"
    assert isinstance(governed, AssemblyOutcome), type(governed).__name__
    assert governed.assembler_id == assembler.ASSEMBLER_ID
    assert governed.assembler_version == assembler.ASSEMBLER_VERSION
    assert assembler.ASSEMBLER_VERSION == "1.0.1", (
        "the pin is D-IMPL-245 am.1's PATCH identity for the corrected"
        " implementation; 1.0.0 would make two implementations share one name,"
        " and am.3 rules never 1.0.2"
    )
