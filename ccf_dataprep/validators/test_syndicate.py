"""Wave 18 -- syndicate data invariants and the §F floors."""
import hashlib
import json
import re
import pytest

from ccf.config import REPO_ROOT
from ccf.syndicate import LOCAL_COMPOSITE_TTL_SECONDS, MAX_FEDERATION_LATENCY_MS
from generators.resolve_syndicate_institutions import canonical_key

SCREEN = REPO_ROOT / "sources" / "screening"

def test_name_collapsing_merges_true_variants():
    """Different spellings/casings of the SAME institution must land on the
    same canonical_key(), or a real bank would be split into phantom
    duplicate members."""
    assert canonical_key("JPMORGAN CHASE BANK, N.A.") == \
        canonical_key("JPMorgan Chase Bank, N.A.")
    assert canonical_key("Truist") == canonical_key("Truist Bank") == \
        canonical_key("TRUIST BANK")
    assert canonical_key("PNC Bank Canada Branch") == \
        canonical_key("PNC Bank, National Association")
    assert canonical_key("MUFG Bank, Ltd., Canada Branch") == \
        canonical_key("MUFG Bank, Ltd., Chiba Branch")

def test_name_collapsing_does_not_merge_distinct_entities():
    """A resolver that merges too eagerly is worse than one that doesn't
    merge enough -- it silently attaches one bank's commitments to a
    DIFFERENT bank's LEI. These pairs share a brand name or a word or two
    but are legally distinct institutions and must stay distinct."""
    # BMO Bank, N.A. is the US-chartered subsidiary; Bank of Montreal is the
    # Canadian parent. Same brand, different legal entity, different LEI.
    assert canonical_key("BMO Bank N.A.") != canonical_key("Bank of Montreal")
    # TD Bank, N.A. (US subsidiary) vs The Toronto-Dominion Bank (Canadian
    # parent) -- same split as BMO/Bank of Montreal.
    assert canonical_key("TD Bank, N.A.") != \
        canonical_key("The Toronto-Dominion Bank")
    # Citibank, N.A. (the bank) vs Citicorp North America, Inc. (a separate
    # financing subsidiary) -- both appear as distinct lenders in the same
    # schedule (885590 agreement rows).
    assert canonical_key("Citibank, N.A.") != \
        canonical_key("Citicorp North America, Inc.")
    # Goldman Sachs Bank USA (the bank) vs Goldman Sachs Lending Partners
    # (a separate lending subsidiary) -- both appear in the same schedule.
    assert canonical_key("Goldman Sachs Bank USA") != \
        canonical_key("Goldman Sachs Lending Partners")

def _institutions():
    path = SCREEN / "wave18_institutions.json"
    if not path.exists():
        pytest.skip("Task 3 has not run yet")
    return json.loads(path.read_text())

LEI_RE = re.compile(r"^[A-Z0-9]{18}[0-9]{2}$")

#: Legal names of the five real, filed institutions for which an exhaustive
#: GLEIF search (legalName filter, fulltext search, abbreviation
#: expansions, and -- for the three Centerbridge-named vehicles -- a search
#: on the parent Centerbridge fund family) found no real LEI under any
#: spelling. Per Ruling T3-R1 (coordinator, after independently
#: re-verifying the GLEIF searches: 0 records for TCW Rescue Financing
#: Fund, 0 for Asilia Credit Fund, 21 for "Centerbridge Credit" and none of
#: them "Centerbridge Credit CS") these are MEMBERS with lei=None, not a
#: manual_review exemption -- a real institution named in a real filed
#: credit agreement is never dropped and never given a SYN- synthetic
#: identifier (that format is reserved for INVENTED entities). Named
#: individually so a sixth LEI-less member, or a different one, fails this
#: test loudly instead of slipping through as "expected".
NO_LEI_LEGAL_NAMES = {
    "ASILIA CREDIT FUND, LP",
    "CB SA Fund, L.P.",
    "Centerbridge Credit CS, L.P",
    "CB NC Centerbridge Special Credit Partners IV – I Co-Invest, L.P.",
    "TCW RESCUE FINANCING FUND II LP",
}

def test_lei_less_members_are_exactly_the_five_named_funds_and_no_more():
    """A check that selects its population by the property it polices (e.g.
    'for members that HAVE an lei, assert the lei looks real') cannot see
    that property missing -- this project has been bitten by exactly that
    twice already. So this does NOT filter to members with an LEI. It
    asserts the LEI-less set is EXACTLY the five named funds -- by count
    AND by name -- and that every OTHER member's LEI is real GLEIF format.
    A sixth LEI-less member, or a different one, fails this loudly; it does
    not pass as "at most five" or "some subset"."""
    members = _institutions()["members"]
    no_lei = [m for m in members if m["lei"] is None]

    assert len(no_lei) == 5, (
        f"expected exactly 5 LEI-less members, got {len(no_lei)}: "
        f"{[m['legal_name'] for m in no_lei]}")
    got_names = {m["legal_name"] for m in no_lei}
    assert got_names == NO_LEI_LEGAL_NAMES, (
        f"the LEI-less set is not exactly the five named funds -- "
        f"symmetric difference: {sorted(got_names ^ NO_LEI_LEGAL_NAMES)}")

    for m in no_lei:
        assert m.get("no_lei_reason"), f"{m['legal_name']}: missing no_lei_reason"
        assert m["rssd"] is None, (
            f"{m['legal_name']}: has an RSSD despite no LEI -- RSSD must "
            f"never be invented for an entity the resolver couldn't find "
            f"an LEI for either")
        assert m["id_basis"] == "legal_name", (
            f"{m['legal_name']}: id_basis should be 'legal_name' for a "
            f"member with no LEI to derive an id from")

    for m in members:
        if m["legal_name"] in NO_LEI_LEGAL_NAMES:
            continue
        assert LEI_RE.match(m["lei"]), f"{m['legal_name']}: {m['lei']!r}"
        assert not m["lei"].startswith("SYN-"), (
            f"{m['legal_name']} carries a synthetic LEI; §F requires real ones")
        assert m["id_basis"] == "lei", (
            f"{m['legal_name']}: has a real LEI but id_basis is not 'lei'")

#: Members whose LEI is legitimately a BRANCH-category GLEIF record.
#: Empty on purpose -- every member in this artifact must be bound to the
#: entity-level record, not one of its own branches. Bank of America and
#: Citibank were both bound to a Jakarta branch registration until this was
#: caught: headquartersAddress reads correctly on a branch record too
#: (every branch carries its parent's HQ address by definition), so that
#: field cannot tell an entity apart from its own branch -- entity.category
#: can, and this set is the enforced, named place a real exception would
#: have to be declared rather than silently slipping through.
BRANCH_EXEMPT_LEIS: set[str] = set()

def test_no_member_is_bound_to_a_branch_record():
    """A member's LEI must point at the chartered entity, not one of its
    own branch registrations -- a branch carries its parent's data (Call
    Report RSSD, capital) attached to the WRONG legal identity, which is a
    correlation key that looks fine and joins wrong. gleif_category is
    recorded on every member at resolution time specifically so this can
    be checked without a live GLEIF call in the test suite."""
    for m in _institutions()["members"]:
        assert "gleif_category" in m, f"{m['legal_name']}: no gleif_category recorded"
        if m["lei"] in BRANCH_EXEMPT_LEIS:
            continue
        assert m["gleif_category"] != "BRANCH", (
            f"{m['legal_name']} ({m['lei']}) is bound to a BRANCH-category "
            f"GLEIF record, not the entity -- add it to BRANCH_EXEMPT_LEIS "
            f"explicitly if that is ever legitimately correct, don't let "
            f"this pass silently")

def test_member_ids_are_content_keyed_not_positional():
    """Four loaders on main already rewrite other waves' rows when a table
    grows. A positional id would do the same here. member_id is derived
    from the LEI when one exists, or from the normalised legal name when
    it doesn't (Ruling T3-R1's five LEI-less funds) -- id_basis says which,
    and this test derives BOTH forms independently rather than trusting
    the field."""
    for m in _institutions()["members"]:
        if m["lei"] is not None:
            digest = hashlib.sha256(m["lei"].encode()).hexdigest()[:8]
        else:
            key = "name:" + canonical_key(m["legal_name"])
            digest = hashlib.sha256(key.encode()).hexdigest()[:8]
        assert m["member_id"] == f"SYNM-{digest}", (
            f"{m['legal_name']}: id is not derived from its {m['id_basis']}")

def test_member_ids_are_unique():
    ids = [m["member_id"] for m in _institutions()["members"]]
    assert len(ids) == len(set(ids))

def test_at_least_twenty_five_institutions_with_a_real_lei():
    """§F's '~25 syndicate member institutions' is a scale figure. This
    estate's standing rule (Ruling T3-R2) is that a §F scale number
    describes a shape, while a condition-making '>= N' is a floor. The
    condition-making property here is that identities are REAL and
    JOINABLE -- i.e. institutions carrying a real GLEIF LEI -- not raw
    member-row count, which would trivially clear 25 once the 5 LEI-less
    funds count as members too and stop distinguishing anything."""
    with_lei = [m for m in _institutions()["members"] if m["lei"] is not None]
    assert len(with_lei) >= 25

def test_our_bank_and_the_peer_are_both_present():
    """The whole product rests on JPMorgan and Bank of America sitting in
    the same syndicates. If either is missing the demonstration is moot."""
    leis = {m["lei"] for m in _institutions()["members"]}
    assert "7H6GLXDRUGQFU57RNE97" in leis, "JPMorgan Chase Bank NA absent"
    names = " | ".join(m["legal_name"] for m in _institutions()["members"])
    assert "BANK OF AMERICA" in names.upper()

#: 'BarclaysFifth Third Bank PLC, National Association' is genuinely corrupt
#: (two institutions interleaved word-by-word by a filing redline) and must
#: NOT be fuzzy-matched to either bank. Named explicitly per CLAUDE.md's rule
#: against inventing a lender relationship no filing states. Unlike the five
#: no-LEI funds above, this string is NOT a real, resolvable institution --
#: it stays in manual_review rather than becoming a member.
CORRUPT_RAW = "BarclaysFifth Third Bank PLC, National Association"

def test_raw_names_map_back_to_the_schedules():
    """Every lender_raw the parser found must resolve to exactly one
    member, or a commitment edge in Task 8 will have no member to attach
    to -- with ONE named exception: the corrupt string, routed to
    `manual_review` rather than silently dropped or fuzzy-matched. The
    five LEI-less funds (Ruling T3-R1) ARE mapped here -- they are members
    with lei=None, not an exemption from this test.
    """
    schedules = json.loads((SCREEN / "wave18_schedules.json").read_text())
    raw_seen = {r["lender_raw"] for a in schedules["agreements"]
                for r in a["rows"]}

    assert CORRUPT_RAW in raw_seen, "fixture changed — corrupt string not found"
    assert NO_LEI_LEGAL_NAMES <= raw_seen, (
        "fixture changed — a no-LEI fund's filed name not found")

    institutions = _institutions()
    mapped = {n for m in institutions["members"] for n in m["raw_names"]}
    manual_review_names = {r["lender_raw"] for r in institutions.get("manual_review", [])}

    assert CORRUPT_RAW in manual_review_names, (
        "the corrupt lender string must be routed to manual_review, not "
        "silently dropped or fuzzy-matched")
    assert CORRUPT_RAW not in mapped, (
        "the corrupt lender string must never resolve to a member — "
        "picking either bank invents a lender relationship no filing states")
    assert NO_LEI_LEGAL_NAMES <= mapped, (
        "the five LEI-less funds must be mapped to a member (with "
        "lei=None), not left unmapped or parked in manual_review")

    resolvable = raw_seen - {CORRUPT_RAW}
    assert resolvable <= mapped, (
        f"unmapped lender names: {sorted(resolvable - mapped)}")


# --- Task 5: Postgres load -------------------------------------------------

from ccf.config import pg_connect, PG_SCHEMA_V2 as S


def _pg(sql, params=None):
    """`params or ()` used to be passed unconditionally, which made
    psycopg treat every call as parameterized -- even a param-less one --
    and start parsing `%` in the query text as a placeholder lead-in. Fine
    for `%s`; a literal `LIKE '%unattested%'` then raised
    `only '%s', '%b', '%t' are allowed as placeholders, got '%u'`. Passing
    `None` through when there ARE no params keeps psycopg out of
    placeholder-parsing mode entirely, which is what a query with no
    placeholders needs."""
    with pg_connect() as c, c.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def test_syndicate_member_table_is_populated():
    n = _pg(f'SELECT count(*) FROM "{S}".syndicate_member')[0][0]
    assert n >= 25


def test_no_member_carries_a_commitment_amount():
    """§C assigns commitments to FLUREE. A commitment column in Postgres is
    a single-writer violation, and the design records that an earlier draft
    made exactly this mistake."""
    cols = {r[0] for r in _pg(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema=%s AND table_name='syndicate_member'", (S,))}
    forbidden = {c for c in cols
                 if "commitment" in c or "share" in c or "envelope" in c}
    assert not forbidden, f"Fluree-owned attributes in Postgres: {forbidden}"


def test_no_member_was_inserted_into_the_crosswalk():
    """PREFLIGHT RULING P1. An earlier draft of this plan required a
    crosswalk row per member. That would violate
    conditions.py's CROSSWALK_INVARIANTS["crosswalk rows pointing at no
    entity"], which requires every crosswalk row to have a legal_entity
    row by LEI — and these banks are not in legal_entity. Syndicate
    members are counterparty institutions, not clients: they have no
    internal_client_id, and §C names this product's correlation key as
    facility_id plus lender LEI and RSSD. The correct state is ZERO
    crosswalk rows for them, asserted so nobody re-adds them."""
    leaked = _pg(f'SELECT m.lei FROM "{S}".syndicate_member m '
                 f'JOIN "{S}".crosswalk x ON x.lei = m.lei')
    assert not leaked, (
        f"syndicate members inserted into the crosswalk: {leaked} — this "
        f"breaks CROSSWALK_INVARIANTS estate-wide")


def test_the_crosswalk_invariants_still_hold():
    """The check that would actually catch a violation, run directly."""
    from validators.conditions import CROSSWALK_INVARIANTS
    for name, sql in CROSSWALK_INVARIANTS.items():
        assert _pg(sql)[0][0] == 0, f"invariant violated: {name}"


def test_call_reports_reference_a_real_member():
    orphans = _pg(f'SELECT r.rssd FROM "{S}".member_call_report r '
                  f'LEFT JOIN "{S}".syndicate_member m ON m.rssd = r.rssd '
                  f'WHERE m.rssd IS NULL')
    assert not orphans, f"call reports for unknown institutions: {orphans}"


# --- Task 6: our positions, ratings and workout postures -------------------

def test_our_position_exists_on_every_selected_facility():
    """Floor is >= 5, not the brief's original >= 6. Ruling T6-R2 excludes
    FAC-105FC5 (a Wave 4 duplicate of FAC-08F1D1 -- see
    ccf.syndicate.WAVE18_EXCLUDED_FACILITIES) from Wave 18's facility set,
    which drops the true, evidence-backed count of facilities where a
    filed schedule names JPMorgan from 6 to 5. Keeping a row on FAC-105FC5
    to hold the floor at 6 would have meant keeping a position this
    project's own evidence says is a double count, purely to satisfy a
    number -- the "counted but not created" failure CLAUDE.md exists to
    prevent."""
    n = _pg(f'SELECT count(DISTINCT facility_id) FROM "{S}".own_position')[0][0]
    assert n >= 5


def test_our_positions_are_labelled_synthetic_internal():
    bad = _pg(f'SELECT DISTINCT provenance FROM "{S}".own_position '
              f"WHERE provenance <> 'synthetic — internal'")
    assert not bad, f"wrong provenance labels: {bad}"


def test_our_share_never_exceeds_the_facility_commitment():
    over = _pg(f'SELECT p.facility_id, p.share_usd, f.commitment_amount '
               f'FROM "{S}".own_position p '
               f'JOIN "{S}".facility f USING (facility_id) '
               f'WHERE p.share_usd > f.commitment_amount')
    assert not over, f"our share exceeds the whole facility: {over}"


def test_workout_posture_is_from_a_closed_vocabulary():
    allowed = {"performing", "watch", "workout", "restructuring", "exit"}
    got = {r[0] for r in _pg(f'SELECT DISTINCT workout_posture FROM "{S}".own_position')}
    assert got <= allowed, f"unexpected postures: {got - allowed}"


def test_competition_law_rules_exist_and_are_internal():
    rows = _pg(f'SELECT count(*), count(*) FILTER '
               f"(WHERE provenance = 'synthetic — internal') "
               f'FROM "{S}".competition_law_rule')
    total, internal = rows[0]
    assert total >= 3 and total == internal


def test_internal_rating_is_from_the_rating_scale():
    """A rating outside ccf_v2.rating_scale is uninterpretable by anything
    else in the estate -- CLAUDE.md, item 1 under 'Things to get right'."""
    bad = _pg(f'SELECT DISTINCT p.internal_rating FROM "{S}".own_position p '
              f'LEFT JOIN "{S}".rating_scale r ON r.grade = p.internal_rating '
              f'WHERE r.grade IS NULL')
    assert not bad, f"ratings not in rating_scale: {bad}"


def test_share_comparison_null_blind_spot_is_exactly_the_null_commitment_set():
    """p.share_usd > f.commitment_amount is NULL, not TRUE or FALSE, when
    commitment_amount is NULL -- so that row is silently excluded from
    test_our_share_never_exceeds_the_facility_commitment above rather than
    checked and passed. This test names the excluded set explicitly and
    asserts it is exactly the set of Wave 18 facilities with a NULL
    commitment_amount -- today that is Sabre's FAC-3DF1D5, which is not one
    of ours and so is moot, but a future position on a NULL-commitment
    facility must not be able to slip through unexamined."""
    excluded = {r[0] for r in _pg(
        f'SELECT p.facility_id FROM "{S}".own_position p '
        f'JOIN "{S}".facility f USING (facility_id) '
        f'WHERE (p.share_usd > f.commitment_amount) IS NULL')}
    null_commitment = {r[0] for r in _pg(
        f'SELECT p.facility_id FROM "{S}".own_position p '
        f'JOIN "{S}".facility f USING (facility_id) '
        f'WHERE f.commitment_amount IS NULL')}
    assert excluded == null_commitment, (
        f"comparison silently skipped rows outside the NULL-commitment set: "
        f"{excluded - null_commitment}")


def test_excluded_facilities_carry_no_wave18_position_or_edge():
    """Ruling T6-R2: FAC-105FC5 (duplicate of FAC-08F1D1) and FAC-DFCB72
    (no commitment-schedule support at all) are excluded from Wave 18's
    facility set -- see ccf.syndicate.WAVE18_EXCLUDED_FACILITIES for the
    evidence. ccf_v2.facility itself is untouched (other products
    reference those rows), but no Wave 18 artifact or table may carry a
    position, share, or edge for either. Fails loudly if a future task
    re-adds one."""
    from ccf.syndicate import WAVE18_EXCLUDED_FACILITIES
    excluded = list(WAVE18_EXCLUDED_FACILITIES)
    assert excluded, "WAVE18_EXCLUDED_FACILITIES is empty -- fixture drifted"

    leaked = _pg(f'SELECT facility_id FROM "{S}".own_position '
                 f'WHERE facility_id = ANY(%s)', (excluded,))
    assert not leaked, f"own_position carries an excluded facility: {leaked}"

    internal = json.loads((SCREEN / "wave18_internal.json").read_text())
    artifact_ids = {p["facility_id"] for p in internal["own_positions"]}
    leaked_artifact = artifact_ids & set(excluded)
    assert not leaked_artifact, (
        f"wave18_internal.json carries an excluded facility: "
        f"{leaked_artifact}")


def test_three_perspectives_exist():
    got = {r[0] for r in _pg(
        f'SELECT perspective FROM "{S}".syndicate_projection_plan')}
    assert got == {"agent", "participant", "prospective"}


def test_the_three_plans_assemble_different_element_sets():
    """§D: the agent's perspective carries documentation and waterfall
    detail no participant receives; a prospective participant receives
    materially less than an existing one. Three identical plans would make
    the perspective parameter decorative."""
    rows = dict(_pg(f'SELECT perspective, elements FROM '
                    f'"{S}".syndicate_projection_plan'))
    sets = {k: set(v) for k, v in rows.items()}
    assert sets["agent"] != sets["participant"]
    assert sets["participant"] != sets["prospective"]
    assert sets["prospective"] < sets["participant"] < sets["agent"], (
        "the three must nest: prospective ⊂ participant ⊂ agent")


def test_projection_plan_provenance_is_synthetic_internal():
    """Projection plans are bank-internal policy artifacts -- CLAUDE.md's
    three-class rule, applied. Recomputed from the table, not read off a
    label some other test already trusted."""
    bad = _pg(f'SELECT DISTINCT provenance FROM "{S}".syndicate_projection_plan '
              f"WHERE provenance <> 'synthetic — internal'")
    assert not bad, f"wrong provenance labels: {bad}"


# ===========================================================================
# Task 8 -- Fluree: syndicate structure and commitment shares
# ===========================================================================

from ccf import fluree
from ccf.config import FLUREE_LEDGER_V2 as L

DLN = "https://spec.edmcouncil.org/fibo/ontology/SEC/Debt/DistributedLoans/"
EX = "http://example.org/fibo/"


def _n(sparql):
    rows = fluree.query(sparql)["results"]["bindings"]
    return int(rows[0]["n"]["value"]) if rows else 0


def test_syndicated_loan_nodes_exist():
    assert _n(f"SELECT (COUNT(DISTINCT ?s) AS ?n) FROM <{L}> "
              f"WHERE {{ ?s a <{DLN}SyndicatedLoan> }}") >= 6


def test_member_nodes_are_explicitly_typed():
    """No OWL inference here -- a query for FinanceSyndicateMember returns
    only nodes explicitly typed as one."""
    assert _n(f"SELECT (COUNT(DISTINCT ?s) AS ?n) FROM <{L}> "
              f"WHERE {{ ?s a <{DLN}FinanceSyndicateMember> }}") >= 25


def test_member_nodes_carry_no_postgres_owned_attribute():
    """Single-writer discipline: nodes carry lei + label and nothing else."""
    forbidden = ["legalName", "rssd", "tier1Capital", "totalAssets",
                 "internalRating", "workoutPosture"]
    for attr in forbidden:
        n = _n(f"SELECT (COUNT(*) AS ?n) FROM <{L}> WHERE {{ "
               f"?s a <{DLN}FinanceSyndicateMember> ; <{EX}{attr}> ?v }}")
        assert n == 0, f"{attr} is duplicated into Fluree; Postgres owns it"


def test_commitment_shares_live_on_the_edges():
    """§C assigns commitments to Fluree as R. If the share is not here,
    it is nowhere -- the design forbids a Postgres copy."""
    assert _n(f"SELECT (COUNT(*) AS ?n) FROM <{L}> WHERE {{ "
              f"?e <{EX}commitmentUsd> ?v }}") >= 25


def test_every_commitment_edge_cites_a_passage():
    """A public figure with no offset back to the filing is unverifiable."""
    n_edges = _n(f"SELECT (COUNT(*) AS ?n) FROM <{L}> WHERE {{ "
                 f"?e <{EX}commitmentUsd> ?v }}")
    n_cited = _n(f"SELECT (COUNT(*) AS ?n) FROM <{L}> WHERE {{ "
                 f"?e <{EX}commitmentUsd> ?v ; <{EX}sourcePassage> ?p }}")
    assert n_edges == n_cited, f"{n_edges - n_cited} shares cite no passage"


# ===========================================================================
# Fix round 1 -- T8-R1 regression tests (Finding 2)
#
# The five tests above are the brief's generic shape tests; none of them
# exercises the intricate part of Ruling T8-R1 (the agent/member dual-typing
# and the two exceptions to it). Every assertion below is EXACT (a set
# equality or an exact count), not "at least" -- a sixth dual-typed member
# or a second unresolved agent must fail the suite, not pass as expected.
# ===========================================================================

from loaders.load_fluree_wave18 import (
    TCW_AGENT_LABEL,
    TCW_AGENT_LEI,
    TCW_AGENT_LOCAL_ID,
    agent_node_local,
)

#: The three members that are BOTH a filed lender and the administrative
#: agent on at least one Wave 18 facility (Ruling T8-R1). Matched by label
#: (not member_id/LEI) so this test stays independent of identifier
#: plumbing and only asserts what a human reading the graph would see.
DUAL_TYPED_LABELS = {
    "Bank Of America, National Association",
    "JPMorgan Chase Bank, National Association",
    "PNC Bank, National Association",
}


def test_dual_typed_agent_members_are_exactly_bofa_jpmorgan_pnc():
    """Ruling T8-R1: exactly these three members are dual-typed
    (AdministrativeAgent + FinanceSyndicateMember) on their EXISTING member
    node -- not a fourth, not a fifth, and never TCW (which is agent-only,
    see below)."""
    rows = fluree.query(
        f"SELECT ?lab FROM <{L}> WHERE {{ "
        f"?s a <{DLN}AdministrativeAgent> ; a <{DLN}FinanceSyndicateMember> ; "
        f"<http://www.w3.org/2000/01/rdf-schema#label> ?lab }}"
    )["results"]["bindings"]
    got = {r["lab"]["value"] for r in rows}
    assert got == DUAL_TYPED_LABELS, (
        f"dual-typed member set drifted -- symmetric difference: "
        f"{sorted(got ^ DUAL_TYPED_LABELS)}")


def test_tcw_is_agent_only_with_zero_participation_edges():
    """TCW (the four Regis facilities' agent) is not a Wave 18 lender: it
    must carry AdministrativeAgent and NEVER FinanceSyndicateMember, and it
    must have exactly zero SyndicateParticipation edges in either
    direction -- not "no edges we happened to check for", the full set."""
    tcw = agent_node_local(TCW_AGENT_LOCAL_ID)

    is_agent = _n(f"SELECT (COUNT(*) AS ?n) FROM <{L}> WHERE {{ "
                  f"<{tcw}> a <{DLN}AdministrativeAgent> }}")
    assert is_agent == 1, "TCW's agent node is missing its AdministrativeAgent type"

    is_member = _n(f"SELECT (COUNT(*) AS ?n) FROM <{L}> WHERE {{ "
                   f"<{tcw}> a <{DLN}FinanceSyndicateMember> }}")
    assert is_member == 0, "TCW must never be typed FinanceSyndicateMember -- it is not a lender"

    edges_as_subject = _n(f"SELECT (COUNT(*) AS ?n) FROM <{L}> WHERE {{ "
                          f"<{tcw}> <{EX}participationOf> ?o }}")
    edges_as_object = _n(f"SELECT (COUNT(*) AS ?n) FROM <{L}> WHERE {{ "
                         f"?s <{EX}participationOf> <{tcw}> }}")
    assert edges_as_subject == 0 and edges_as_object == 0, (
        f"TCW has {edges_as_subject + edges_as_object} participation "
        f"edge(s); it is a manager acting as agent, never a lender")

    lei = fluree.query(f"SELECT ?l FROM <{L}> WHERE {{ <{tcw}> <{EX}lei> ?l }}"
                       )["results"]["bindings"]
    assert len(lei) == 1 and lei[0]["l"]["value"] == TCW_AGENT_LEI, (
        "TCW's node must carry its real GLEIF LEI, not an empty or "
        "invented value")
    label = fluree.query(
        f"SELECT ?lab FROM <{L}> WHERE {{ "
        f"<{tcw}> <http://www.w3.org/2000/01/rdf-schema#label> ?lab }}"
    )["results"]["bindings"]
    assert len(label) == 1 and label[0]["lab"]["value"] == TCW_AGENT_LABEL


def test_corrupt_lender_raw_resolves_to_no_node():
    """The word-level-redlined "BarclaysFifth Third Bank PLC, National
    Association" string must never appear as any node's label anywhere in
    the ledger -- confirming the loader's manual_review skip actually held,
    not merely that it printed a count of 1."""
    n = _n(f"SELECT (COUNT(*) AS ?n) FROM <{L}> WHERE {{ "
           f"?s <http://www.w3.org/2000/01/rdf-schema#label> \"{CORRUPT_RAW}\" }}")
    assert n == 0, "a node was minted for the corrupt, unresolvable lender string"


def test_lei_less_members_omit_the_property_and_are_exactly_the_five_funds():
    """CLAUDE.md: 'omit the lei property entirely; do not emit an empty
    string.' Checked two ways: (1) no FinanceSyndicateMember carries
    ex:lei = "" anywhere, and (2) the set of members with NO ex:lei triple
    at all is EXACTLY the five named funds (reusing NO_LEI_LEGAL_NAMES,
    the same ground truth the Postgres-side test already uses) -- not a
    sixth, not a different set."""
    empty_string_lei = _n(f"SELECT (COUNT(*) AS ?n) FROM <{L}> WHERE {{ "
                          f"?s a <{DLN}FinanceSyndicateMember> ; "
                          f"<{EX}lei> \"\" }}")
    assert empty_string_lei == 0, "a member carries an empty-string lei"

    rows = fluree.query(
        f"SELECT ?lab FROM <{L}> WHERE {{ "
        f"?s a <{DLN}FinanceSyndicateMember> ; "
        f"<http://www.w3.org/2000/01/rdf-schema#label> ?lab . "
        f"FILTER NOT EXISTS {{ ?s <{EX}lei> ?l }} }}"
    )["results"]["bindings"]
    got = {r["lab"]["value"] for r in rows}
    assert got == NO_LEI_LEGAL_NAMES, (
        f"the Fluree lei-less set does not match the five named funds -- "
        f"symmetric difference: {sorted(got ^ NO_LEI_LEGAL_NAMES)}")


# ===========================================================================
# Task 9 -- Fluree: the live amendment vote
#
# The brief's own Step 1 snippet reads `<{EX}posture>` on the votesOn
# subject. That local name is bound NOWHERE in this estate -- the bound,
# imported constant is `ccf.syndicate.EX_VOTE_POSTURE` ("votePosture"),
# which is what the loader actually writes and what the v2 binding table
# documents for `votesOn`'s companion predicate. Every test below imports
# the real constants rather than retyping the brief's literal, per this
# task's own instruction ("Import every IRI. Never retype one as a
# literal") -- reusing the brief's typo would have meant writing a test
# that could never fail against a correct loader, or a loader that matches
# a term nothing else in the estate recognises.
# ===========================================================================

from ccf.syndicate import (
    EX_AMENDMENT_EVENT,
    EX_AMENDMENT_VOTE,
    EX_AMENDS,
    EX_EFFECTIVE_DATE,
    EX_VOTE_POSTURE,
    EX_VOTE_STATE,
    EX_VOTES_ON,
    WAVE18_EXCLUDED_FACILITIES,
)


def test_one_open_amendment_vote_exists():
    assert _n(f"SELECT (COUNT(DISTINCT ?v) AS ?n) FROM <{L}> WHERE {{ "
              f"?v a <{EX_AMENDMENT_VOTE}> ; <{EX_VOTE_STATE}> 'open' }}"
              ) >= 1


def test_postures_on_the_open_vote_genuinely_diverge():
    """§F: >= 1 live amendment vote WITH DIVERGENT POSTURES. A vote where
    everyone agrees satisfies the count and not the condition. Reads the
    actual `ex:votePosture` values on the actual `ex:votesOn` edges -- no
    `divergent` flag exists anywhere for this to read instead."""
    rows = fluree.query(
        f"SELECT DISTINCT ?posture FROM <{L}> WHERE {{ "
        f"?v a <{EX_AMENDMENT_VOTE}> ; <{EX_VOTE_STATE}> 'open' . "
        f"?e <{EX_VOTES_ON}> ?v ; <{EX_VOTE_POSTURE}> ?posture }}"
    )["results"]["bindings"]
    postures = {r["posture"]["value"] for r in rows}
    assert len(postures) >= 2, f"all members hold the same posture: {postures}"


def test_postures_are_from_the_closed_vocabulary():
    allowed = {"consent", "decline", "abstain", "undecided"}
    rows = fluree.query(
        f"SELECT DISTINCT ?posture FROM <{L}> WHERE {{ "
        f"?e <{EX_VOTES_ON}> ?v ; <{EX_VOTE_POSTURE}> ?posture }}"
    )["results"]["bindings"]
    got = {r["posture"]["value"] for r in rows}
    assert got, "no votePosture values found at all"
    assert got <= allowed, f"posture outside the closed vocabulary: {got - allowed}"


def test_every_voter_on_the_open_vote_is_a_real_lender_on_that_facility():
    """A votesOn edge from an institution that is not a lender on the
    vote's facility is a fabricated relationship. Checked directly against
    the actual SyndicateParticipation nodes Task 8 wrote, not trusted from
    the generator's own artifact."""
    fac_rows = fluree.query(
        f"SELECT ?fac FROM <{L}> WHERE {{ "
        f"?v a <{EX_AMENDMENT_VOTE}> ; <{EX_VOTE_STATE}> 'open' ; "
        f"<{EX_AMENDS}> ?fac }}"
    )["results"]["bindings"]
    assert len(fac_rows) == 1, (
        f"expected exactly one facility on the open vote, got {fac_rows}")
    fac = fac_rows[0]["fac"]["value"]

    fabricated = _n(
        f"SELECT (COUNT(DISTINCT ?e) AS ?n) FROM <{L}> WHERE {{ "
        f"?v a <{EX_AMENDMENT_VOTE}> ; <{EX_VOTE_STATE}> 'open' . "
        f"?e <{EX_VOTES_ON}> ?v . "
        f"FILTER NOT EXISTS {{ "
        f"?p a <{EX}SyndicateParticipation> ; <{EX}participationOf> ?e ; "
        f"<{EX}participationIn> <{fac}> }} }}")
    assert fabricated == 0, (
        f"{fabricated} voter(s) on the open vote hold no participation on "
        f"{fac} -- a fabricated lender relationship")


def test_administrative_agent_posture_on_its_own_vote_is_neutral():
    """The brief's own note: an agent is usually neutral on a vote it
    administers. Checked against the actual administeredBy edge and the
    actual posture, not asserted in prose."""
    rows = fluree.query(
        f"SELECT ?posture FROM <{L}> WHERE {{ "
        f"?v a <{EX_AMENDMENT_VOTE}> ; <{EX_VOTE_STATE}> 'open' ; "
        f"<{EX_AMENDS}> ?fac . "
        f"?fac <{EX}administeredBy> ?agent . "
        f"?agent <{EX_VOTES_ON}> ?v ; <{EX_VOTE_POSTURE}> ?posture }}"
    )["results"]["bindings"]
    assert len(rows) == 1, (
        f"expected the administering agent to vote exactly once on its own "
        f"facility's vote, got {rows}")
    assert rows[0]["posture"]["value"] == "abstain"


def test_amendment_events_carry_effective_dates():
    n_ev = _n(f"SELECT (COUNT(*) AS ?n) FROM <{L}> WHERE {{ "
              f"?a a <{EX_AMENDMENT_EVENT}> }}")
    n_dated = _n(f"SELECT (COUNT(*) AS ?n) FROM <{L}> WHERE {{ "
                 f"?a a <{EX_AMENDMENT_EVENT}> ; <{EX_EFFECTIVE_DATE}> ?d }}")
    assert n_ev >= 1 and n_ev == n_dated


def test_amendment_events_are_public_the_vote_is_synthetic_internal():
    """§C: amendment events/effective dates are public (filed). Vote
    postures are bank-internal. Checked as two separate, opposite-direction
    assertions -- a mislabel in either direction must fail. Existence is
    asserted FIRST -- a FILTER(?p != ...) count is 0 over an empty
    population too, and this test must not pass vacuously against a loader
    that never ran."""
    n_events = _n(f"SELECT (COUNT(*) AS ?n) FROM <{L}> WHERE {{ "
                  f"?a a <{EX_AMENDMENT_EVENT}> }}")
    n_votes = _n(f"SELECT (COUNT(*) AS ?n) FROM <{L}> WHERE {{ "
                 f"?v a <{EX_AMENDMENT_VOTE}> }}")
    assert n_events >= 1, "no AmendmentEvent node exists"
    assert n_votes >= 1, "no AmendmentVote node exists"

    bad_events = _n(f"SELECT (COUNT(*) AS ?n) FROM <{L}> WHERE {{ "
                     f"?a a <{EX_AMENDMENT_EVENT}> ; <{EX}provenance> ?p . "
                     f"FILTER(?p != 'public') }}")
    assert bad_events == 0, "an AmendmentEvent carries a non-public provenance"

    bad_votes = _n(f"SELECT (COUNT(*) AS ?n) FROM <{L}> WHERE {{ "
                    f"?v a <{EX_AMENDMENT_VOTE}> ; <{EX}provenance> ?p . "
                    f"FILTER(?p != 'synthetic — internal') }}")
    assert bad_votes == 0, "an AmendmentVote carries a non-internal provenance"


def test_every_wave18_facility_has_at_least_one_amendment_event():
    """Stronger than the brief's `>= 1`: every one of the 12 Wave 18
    facilities (not the two Ruling T6-R2 excludes) must be reachable from
    some dated AmendmentEvent via ex:amends -- a document with a real
    recital does the whole estate no good if the loader only wires up one
    of its facilities."""
    facs_with_event = {
        r["fac"]["value"] for r in fluree.query(
            f"SELECT DISTINCT ?fac FROM <{L}> WHERE {{ "
            f"?a a <{EX_AMENDMENT_EVENT}> ; <{EX_AMENDS}> ?fac }}"
        )["results"]["bindings"]
    }
    all_facs = {
        r["s"]["value"] for r in fluree.query(
            f"SELECT DISTINCT ?s FROM <{L}> WHERE {{ ?s a <{DLN}SyndicatedLoan> }}"
        )["results"]["bindings"]
    }
    excluded_uris = {f"{EX}syndicate/{fid}" for fid in WAVE18_EXCLUDED_FACILITIES}
    assert not (all_facs & excluded_uris), (
        "an excluded facility carries a SyndicatedLoan node -- Ruling "
        "T6-R2 violated")
    missing = all_facs - facs_with_event
    assert not missing, f"Wave 18 facilities with no amendment event: {missing}"


# ===========================================================================
# Task 10 -- Fluree: the two asymmetric bilateral disclosure envelopes
# ===========================================================================

from ccf.syndicate import (
    EX_COUNTERPARTY,
    EX_DISCLOSE_SCOPE,
    EX_DISCLOSURE_ENVELOPE,
    EX_ENVELOPE_VERSION,
    EX_REQUEST_SCOPE,
    EX_VALID_FROM,
)


def _envelope_scopes():
    rows = fluree.query(
        f"SELECT ?env ?cp ?kind ?elem FROM <{L}> WHERE {{ "
        f"?env a <{EX_DISCLOSURE_ENVELOPE}> ; <{EX_COUNTERPARTY}> ?cp . "
        f"{{ ?env <{EX_REQUEST_SCOPE}> ?elem . BIND('request' AS ?kind) }} "
        f"UNION "
        f"{{ ?env <{EX_DISCLOSE_SCOPE}> ?elem . BIND('disclose' AS ?kind) }} }}"
    )["results"]["bindings"]
    out = {}
    for r in rows:
        env = r["env"]["value"]
        out.setdefault(env, {"request": set(), "disclose": set()})
        out[env][r["kind"]["value"]].add(r["elem"]["value"])
    return out


def test_two_envelopes_exist():
    assert len(_envelope_scopes()) >= 2


def test_at_least_two_envelopes_are_genuinely_asymmetric():
    """§F: >= 2 bilateral envelopes with asymmetric terms.

    Counts ENVELOPES WHOSE TWO SCOPES DIFFER -- not envelopes, and not
    scope rows. Compares the sets; reads no `asymmetric` flag."""
    asymmetric = [env for env, s in _envelope_scopes().items()
                  if s["request"] != s["disclose"]]
    assert len(asymmetric) >= 2, (
        f"{len(asymmetric)} of {len(_envelope_scopes())} envelopes differ")


def test_both_scopes_are_non_empty():
    """An envelope with an empty disclose set is trivially 'asymmetric'
    and proves nothing."""
    for env, s in _envelope_scopes().items():
        assert s["request"], f"{env} requests nothing"
        assert s["disclose"], f"{env} discloses nothing"


def test_the_asymmetry_test_would_fail_on_symmetric_or_empty_input():
    """A regression check on the CHECKER itself, not the data -- "Output
    that never varies" (this estate's own standing lesson) means a check
    must be shown to give a DIFFERENT answer on a known-present and a
    known-absent input, not merely pass once. Constructs a symmetric
    envelope and an empty-disclose envelope in memory and asserts the SAME
    logic `test_at_least_two_envelopes_are_genuinely_asymmetric` and
    `test_both_scopes_are_non_empty` use would reject both."""
    symmetric = {"request": {"syndicate_composition"},
                 "disclose": {"syndicate_composition"}}
    empty_disclose = {"request": {"own_position"}, "disclose": set()}
    genuinely_asymmetric = {"request": {"own_position"},
                             "disclose": {"syndicate_composition"}}

    fixture = {"env-symmetric": symmetric, "env-empty": empty_disclose,
               "env-real": genuinely_asymmetric}
    asymmetric = [env for env, s in fixture.items()
                  if s["request"] != s["disclose"]]
    assert "env-symmetric" not in asymmetric, (
        "the asymmetry check accepted a SYMMETRIC envelope")
    assert "env-empty" in asymmetric, (
        "an empty disclose set trivially differs from a non-empty request "
        "set, so it MUST still be caught by the separate non-empty check")
    assert not fixture["env-empty"]["disclose"], (
        "the non-empty check must fail on this fixture, or it is decoration")
    assert "env-real" in asymmetric


def test_the_two_envelopes_differ_from_each_other():
    """Not just internally asymmetric -- the two counterparties' scopes
    must actually differ from one another, or 'bilaterally negotiated' is
    a fiction and both envelopes are one template stamped twice."""
    scopes = list(_envelope_scopes().values())
    req_sets = {frozenset(s["request"]) for s in scopes}
    dis_sets = {frozenset(s["disclose"]) for s in scopes}
    assert len(req_sets) > 1 or len(dis_sets) > 1, (
        "every envelope requests and discloses the identical scope -- "
        "the two counterparties are indistinguishable")


def test_envelope_scope_elements_are_drawn_from_the_projection_plan_vocabulary():
    """§C catalog reuse discipline: an envelope element with nothing behind
    it (Task 7's own deleted `payment_waterfall`, which appeared only in
    the spec's §D with no §C data row) makes Task 16's assembly silently
    skip it. Every element used here must appear in at least one
    `syndicate_projection_plan` perspective's `elements` array."""
    known = set()
    for row in _pg(f'SELECT elements FROM "{S}".syndicate_projection_plan'):
        known.update(row[0])
    assert known, "no syndicate_projection_plan rows -- Task 7 has not run"

    used = set()
    for s in _envelope_scopes().values():
        used |= s["request"] | s["disclose"]
    unknown = used - known
    assert not unknown, (
        f"envelope scope element(s) not in any projection plan: {unknown}")


def test_envelopes_are_versioned_and_dated():
    """§E gives envelopes a ~365-day λ_c and lists renegotiation as a
    supersession trigger; §C assigns `P` AND `T`. Both `envelopeVersion`
    and the valid-time predicate are part of the element, not decoration."""
    n_env = _n(f"SELECT (COUNT(DISTINCT ?e) AS ?n) FROM <{L}> WHERE {{ "
               f"?e a <{EX_DISCLOSURE_ENVELOPE}> }}")
    n_versioned = _n(f"SELECT (COUNT(DISTINCT ?e) AS ?n) FROM <{L}> WHERE {{ "
                     f"?e a <{EX_DISCLOSURE_ENVELOPE}> ; "
                     f"<{EX_ENVELOPE_VERSION}> ?v }}")
    n_dated = _n(f"SELECT (COUNT(DISTINCT ?e) AS ?n) FROM <{L}> WHERE {{ "
                 f"?e a <{EX_DISCLOSURE_ENVELOPE}> ; <{EX_VALID_FROM}> ?d }}")
    assert n_env >= 2
    assert n_env == n_versioned == n_dated, (
        f"{n_env} envelopes, {n_versioned} versioned, {n_dated} dated -- "
        f"every envelope must carry both")


def test_envelope_counterparties_are_real_existing_members():
    """`ex:counterparty` must point at a real FinanceSyndicateMember node
    already in the graph -- Bank of America and Citibank (design §6) --
    never a fabricated or dangling subject."""
    rows = fluree.query(
        f"SELECT ?cp FROM <{L}> WHERE {{ "
        f"?e a <{EX_DISCLOSURE_ENVELOPE}> ; <{EX_COUNTERPARTY}> ?cp }}"
    )["results"]["bindings"]
    cps = {r["cp"]["value"] for r in rows}
    assert len(cps) == 2, f"expected exactly 2 counterparties, got {cps}"

    dangling = _n(
        f"SELECT (COUNT(?cp) AS ?n) FROM <{L}> WHERE {{ "
        f"?e a <{EX_DISCLOSURE_ENVELOPE}> ; <{EX_COUNTERPARTY}> ?cp . "
        f"FILTER NOT EXISTS {{ ?cp a <{DLN}FinanceSyndicateMember> }} }}")
    assert dangling == 0, f"{dangling} counterparty(ies) resolve to no member node"

    from loaders.load_fluree_wave18 import RDFS_LABEL
    labels = {r["l"]["value"] for r in fluree.query(
        f"SELECT ?l FROM <{L}> WHERE {{ "
        f"?e a <{EX_DISCLOSURE_ENVELOPE}> ; <{EX_COUNTERPARTY}> ?cp . "
        f"?cp <{RDFS_LABEL}> ?l }}"
    )["results"]["bindings"]}
    assert any("BANK OF AMERICA" in l.upper() for l in labels)
    assert any("CITIBANK" in l.upper() for l in labels)


def test_envelopes_carry_provenance_synthetic_internal():
    """Ruling T8-R2: every node this Fluree loader writes carries
    `ex:provenance`. Envelopes are negotiated bilaterally -- CLAUDE.md's
    exact three-class taxonomy makes them `synthetic — internal`, never
    `public`."""
    n_env = _n(f"SELECT (COUNT(DISTINCT ?e) AS ?n) FROM <{L}> WHERE {{ "
               f"?e a <{EX_DISCLOSURE_ENVELOPE}> }}")
    n_bad = _n(f"SELECT (COUNT(DISTINCT ?e) AS ?n) FROM <{L}> WHERE {{ "
               f"?e a <{EX_DISCLOSURE_ENVELOPE}> ; <{EX}provenance> ?p . "
               f"FILTER(?p != 'synthetic — internal') }}")
    n_labelled = _n(f"SELECT (COUNT(DISTINCT ?e) AS ?n) FROM <{L}> WHERE {{ "
                    f"?e a <{EX_DISCLOSURE_ENVELOPE}> ; <{EX}provenance> ?p }}")
    assert n_env >= 2
    assert n_labelled == n_env, "an envelope carries no ex:provenance at all"
    assert n_bad == 0, "an envelope carries a non-internal provenance"


# --- Task 11: MongoDB -- voting thresholds and assignment provisions ------
#
# Deviation from the brief's literal Step 1 snippet: it reads `p["start"]`
# and `p["end"]`. Those are not this estate's field names -- they are the
# exact alias pair `loaders/load_mongo_wave17.py`'s docstring records as
# retired ("doc_id / start / end as duplicate aliases ... two fields holding
# the same value are two things that can drift"). Every one of the 37,377
# pre-existing passages, and this task's own loader, spell them
# `start_offset` / `end_offset`. Testing the brief's literal field names
# would pass only against a loader that reintroduced the retired aliases --
# exactly the failure this file exists to catch, per this task's own "lesson
# this task must not repeat" instruction.

from ccf.config import mongo_db as _mongo_db_wave18


def test_voting_threshold_passages_exist():
    db = _mongo_db_wave18(write=False)
    assert db["passage"].count_documents(
        {"passage_kind": "voting_threshold"}) >= 6


def test_assignment_passages_exist():
    db = _mongo_db_wave18(write=False)
    assert db["passage"].count_documents(
        {"passage_kind": "assignment_provision"}) >= 6


def test_every_wave18_passage_resolves_inside_its_document():
    """A span that does not resolve is a lineage claim nothing supports."""
    db = _mongo_db_wave18(write=False)
    docs = {d["_id"]: d for d in db["document"].find(
        {"doc_type": "credit_agreement_wave18"})}
    assert docs, "no Wave 18 credit-agreement documents loaded"
    for p in db["passage"].find(
            {"passage_kind": {"$in": ["voting_threshold",
                                       "assignment_provision"]}}):
        doc = docs.get(p["document_id"])
        assert doc, f"passage {p['_id']} points at no loaded document"
        text = doc["text"]
        assert 0 <= p["start_offset"] < p["end_offset"] <= len(text)
        assert text[p["start_offset"]:p["end_offset"]] == p["text"], (
            f"passage {p['_id']} span does not match its own text")


def test_mongo_holds_no_typed_edge():
    """P3: MongoDB holds document text and spans, no typed edges."""
    db = _mongo_db_wave18(write=False)
    assert db["passage"].count_documents(
        {"passage_kind": {"$in": ["voting_threshold", "assignment_provision"]},
         "participatesIn": {"$exists": True}}) == 0


def test_wave18_passages_and_documents_are_public():
    """Ruling T11-R1: both §C rows for what this loader builds ("Voting
    thresholds and amendment mechanics ... public"; "Assignment and
    transfer provisions ... public") say `public`, and the separate
    "Passage spans on agreement text ... derived" catalog row describes
    span METADATA as a category, not this passage document -- the text
    genuinely is filed public text with a named source and retrieval date.
    37,295+ of the collection's passages are already `public`; a consumer
    filtering on that value must not silently miss these 12. (An earlier
    cut of this loader set `passage.provenance = "derived"` for these two
    `passage_kind`s -- this test would have passed THAT version too if it
    only checked for `"derived"`; it now asserts the corrected value and
    would fail again if the loader regressed to `derived`.)"""
    db = _mongo_db_wave18(write=False)
    n_pass = db["passage"].count_documents(
        {"passage_kind": {"$in": ["voting_threshold", "assignment_provision"]}})
    n_pass_public = db["passage"].count_documents(
        {"passage_kind": {"$in": ["voting_threshold", "assignment_provision"]},
         "provenance": "public"})
    n_pass_derived = db["passage"].count_documents(
        {"passage_kind": {"$in": ["voting_threshold", "assignment_provision"]},
         "provenance": "derived"})
    assert n_pass >= 12
    assert n_pass == n_pass_public, (
        f"{n_pass - n_pass_public} of {n_pass} Wave 18 passages carry a "
        f"non-public provenance")
    assert n_pass_derived == 0, (
        "a Wave 18 passage still carries provenance=derived -- Ruling "
        "T11-R1 requires public")

    n_doc = db["document"].count_documents({"doc_type": "credit_agreement_wave18"})
    n_doc_public = db["document"].count_documents(
        {"doc_type": "credit_agreement_wave18", "provenance": "public"})
    assert n_doc == n_doc_public
    assert n_doc == 6


def test_exactly_one_passage_per_kind_per_wave18_document():
    """A second row for the same (document, kind) would mean a re-run
    duplicated rather than upserted -- the idempotency contract this
    loader's `_id` scheme exists to hold."""
    db = _mongo_db_wave18(write=False)
    from collections import Counter
    counts = Counter(
        (p["document_id"], p["passage_kind"])
        for p in db["passage"].find(
            {"passage_kind": {"$in": ["voting_threshold", "assignment_provision"]}},
            {"document_id": 1, "passage_kind": 1}))
    dupes = {k: n for k, n in counts.items() if n != 1}
    assert not dupes, f"duplicate (document, kind) rows: {dupes}"


def test_offset_end_span_survives_a_newline_in_the_heading():
    """Regression pin, the Task 1/2 defect class: a heading string that is
    whitespace-NORMALISED (`" ".join(raw.split())`) paired with an `end`
    offset sized to `len(normalised)` breaks the instant the real heading
    text contains a newline TextExtractor preserved -- exactly what "11.01
    Amendments,\\nEtc." and "11.06 Successors\\nand Assigns." look like in
    every one of this task's six real filings. This fixture reproduces that
    shape and requires the real `{start_offset, end_offset}` contract
    (`text[start:end] == stored text`), not an offset paired with a
    normalised string's length.

    Confirmed failing before the fix: a `buggy_extract_one` that computes
    `end = start + len(" ".join(heading_raw.split()))` and stores the
    NORMALISED heading as `text` was run against this exact fixture and
    both kinds failed --
        voting_threshold:      span='Amendments,\\nEtc.'        stored='Amendments, Etc.'
        assignment_provision:  span='Successors\\nand Assigns.' stored='Successors and Assigns.'
    -- before `extract_one` (which stores `text[start:end]` directly, never
    a normalised derivative) was confirmed to pass it."""
    from generators.extract_amendment_assignment_articles import extract_one

    fixture = (
        "ARTICLE XI\n\nMISCELLANEOUS\n\n"
        "11.01       Amendments,\nEtc. Except as provided in Section 2.16, no "
        "amendment or waiver of any provision of this Agreement or any other "
        "Loan Document shall be effective unless in writing signed by the "
        "Required Lenders. " + ("Filler text padding out the passage so a "
        "realistic snap window applies here today. " * 4) + "\n\n"
        "11.06       Successors\nand Assigns.\n\n(a)           Successors\n"
        "and Assigns Generally. The provisions of this Agreement shall be "
        "binding upon and inure to the benefit of the parties hereto and "
        "their respective successors and assigns permitted hereby, and no "
        "Lender may assign or otherwise transfer its rights or obligations "
        "hereunder except in accordance with the terms of this Section. " +
        ("More filler text so this passage clears the minimum span length "
         "too. " * 4) + "\n\n"
    )
    passages, absent = extract_one("FIXTURE.htm", fixture)
    assert not absent
    kinds = {p["passage_kind"] for p in passages}
    assert kinds == {"voting_threshold", "assignment_provision"}
    for p in passages:
        span = fixture[p["start_offset"]:p["end_offset"]]
        assert "\n" in span, (
            f"{p['passage_kind']}: fixture must exercise a newline-crossing "
            f"span, or this test proves nothing")
        assert span == p["text"], (
            f"{p['passage_kind']}: span {span!r} != stored text {p['text']!r}")


# ===========================================================================
# Task 2 -- `extract_commitment_schedules.py`'s caption/cross-reference
# split. A "Schedule N" marker is a true CAPTION only if its table starts
# within `CAPTION_MAX_GAP` characters; otherwise it is an ordinary prose
# cross-reference. This is the load-bearing heuristic the module's own
# docstring says exists to stop the Super Micro / Vertiv class of defect
# (an unrelated table's figures pulled in via a stray cross-reference) --
# and, until now, had no unit test of its own.
# ===========================================================================

def test_caption_max_gap_separates_a_caption_from_a_cross_reference():
    """Same marker, same keyword, only the distance to the next '|'
    changes. A gap of exactly `CAPTION_MAX_GAP` chars must still read as a
    caption (the boundary is inclusive: `> CAPTION_MAX_GAP` is what skips
    it); one char past it must not. A regression that silently widens or
    narrows this gap would re-admit an unrelated table's figures or drop a
    real caption, and neither would be caught by counting rows -- only by
    requiring these two inputs to give different answers."""
    from generators.extract_commitment_schedules import (
        CAPTION_MAX_GAP,
        _schedule_captions,
    )

    def make_text(gap: int) -> str:
        # "SCHEDULE 2.01" (the marker regex match) + a blurb naming
        # "Commitments" (the INCLUDE keyword) padded to exactly `gap`
        # characters before the table's opening "|".
        prefix = "SCHEDULE 2.01"
        blurb = " Commitments" + ("z" * (gap - len(" Commitments")))
        assert len(blurb) == gap
        return f"{prefix}{blurb}|Lender|Amount|\n"

    inside = make_text(CAPTION_MAX_GAP)
    outside = make_text(CAPTION_MAX_GAP + 1)

    captions_inside = _schedule_captions(inside)
    captions_outside = _schedule_captions(outside)

    assert captions_inside and captions_inside[0][1] == "include", (
        f"gap of exactly CAPTION_MAX_GAP ({CAPTION_MAX_GAP}) chars was not "
        f"read as an 'include' caption: {captions_inside}")
    assert captions_outside == [], (
        f"gap of CAPTION_MAX_GAP + 1 ({CAPTION_MAX_GAP + 1}) chars was "
        f"still read as a caption: {captions_outside} -- a prose "
        f"cross-reference this far from any table must not be mistaken "
        f"for one")


# ===========================================================================
# Task 11b -- one inherited minor: Task 11's "record no passage if the
# article is absent" path had no test, because the real corpus happens to
# have zero absent cases. This fixture feeds text with NO matching heading
# for either kind and asserts the absence path -- not the happy path -- is
# what actually runs.
# ===========================================================================

def test_extract_one_records_absence_and_emits_no_passage_when_heading_missing():
    """CLAUDE.md hard rule ('record nothing if the article is absent') is
    IMPLEMENTED in `extract_one` but was never exercised by any fixture or
    real document -- a regression here would be caught by neither the data
    (all twelve real cases are present) nor any existing test. This fixture
    contains ordinary loan-agreement prose with no "Amendments, Etc." /
    "Waivers; Amendments." heading and no "Successors and Assigns." /
    "Assignments and Participations." heading at all -- both kinds must be
    absent, and `passages` must be empty, not a fabricated or approximate
    span for either."""
    from generators.extract_amendment_assignment_articles import extract_one

    fixture = (
        "ARTICLE VII\n\nCOVENANTS\n\n"
        "7.01       Financial Covenants. The Borrower shall maintain a "
        "Total Leverage Ratio not to exceed 4.00 to 1.00, tested quarterly "
        "as of the last day of each fiscal quarter, commencing with the "
        "fiscal quarter ending after the Closing Date. " +
        ("Filler prose about reporting requirements and information "
         "covenants, padding this fixture out to a realistic section "
         "length so nothing here resembles a table-of-contents row. " * 6) +
        "\n\n7.02       Negative Covenants. The Borrower shall not incur "
        "additional Indebtedness except as permitted under Section 6.01. "
    )
    passages, absent = extract_one("FIXTURE-ABSENT.htm", fixture)

    assert passages == [], (
        f"no heading exists in this fixture for either kind -- a fabricated "
        f"or approximate passage was still emitted: {passages}")
    assert set(absent) == {"voting_threshold", "assignment_provision"}, (
        f"expected BOTH kinds recorded absent, got {absent!r}")


# ===========================================================================
# Task 11b -- the R half: `ex:AmendmentThreshold` nodes in Fluree, linked to
# the facilities they govern, citing the filed text they were read from.
# `docs/wave18-design.md` §5/§7; ccf/syndicate.py's own Task 11b section for
# the full node-shape rationale.
# ===========================================================================

def test_generator_produces_the_expected_thresholds_per_document():
    """Regenerated live (not read from a possibly-stale artifact) so a
    regex regression against the real filings fails here, not downstream."""
    from generators.extract_voting_thresholds import (
        EXPECTED_REQUIRED_LENDERS_HITS,
        extract_carveouts,
        extract_required_lenders,
    )
    from ccf.config import REPO_ROOT as _ROOT
    from generators.extract_facilities import TextExtractor as _TE

    EX10_DIR = _ROOT / "sources" / "ex10"
    expected_total_by_doc = {
        "1046102_0001104659-25-031884_tm2511351d1_ex10-1.htm": 2,
        "885590_0001193125-25-149731_d949183dex101.htm": 2,
        "1632970_0001193125-26-145647_ahr-ex10_1.htm": 2,
        "716643_0001193125-24-281618_d761586dex101.htm": 2,
        "723531_0001193125-26-021794_payx-ex10_1.htm": 3,
        "1597033_0001193125-26-340356_d133770dex101.htm": 5,
    }
    assert set(expected_total_by_doc) == set(EXPECTED_REQUIRED_LENDERS_HITS)

    for document, expected_total in expected_total_by_doc.items():
        path = EX10_DIR / document
        parser = _TE()
        parser.feed(path.read_text(errors="ignore"))
        parser.close()
        text = parser.text()

        thresholds = extract_required_lenders(document, text)
        thresholds += extract_carveouts(document, text)
        assert len(thresholds) == expected_total, (
            f"{document}: expected {expected_total} thresholds, got "
            f"{len(thresholds)}")

        # Every offset resolves back into THIS SAME extraction of the real
        # filing text -- not a hand-typed number that happens to be close.
        for t in thresholds:
            off = t["source_passage"].rsplit("=", 1)[1]
            start, end = (int(x) for x in off.split("-"))
            assert 0 <= start < end <= len(text)
            assert text[start:end], f"{document}/{t['bucket']}: empty span"


def test_percent_is_present_only_on_percentage_of_exposure_standards():
    """A veto standard ('each affected Lender', 'all Lenders', 'each Class
    A/B Lender') is never expressed as a percentage in any of the six
    filings -- `consent_percent` must be None for every one of them, not a
    computed placeholder."""
    from generators.extract_voting_thresholds import (
        CARVEOUT_SPECS,
        extract_carveouts,
        REQUIRED_LENDERS_RE,
    )
    from ccf.config import REPO_ROOT as _ROOT
    from generators.extract_facilities import TextExtractor as _TE

    EX10_DIR = _ROOT / "sources" / "ex10"
    for document in CARVEOUT_SPECS:
        path = EX10_DIR / document
        parser = _TE()
        parser.feed(path.read_text(errors="ignore"))
        parser.close()
        text = parser.text()
        for t in extract_carveouts(document, text):
            assert t["consent_percent"] is None, (
                f"{document}/{t['bucket']}: veto standard carries a "
                f"percent -- {t['consent_percent']!r} -- but no filing "
                f"states one for this kind of standard")


def test_required_lenders_regex_would_fail_on_a_document_with_no_definition():
    """Would the extractor actually notice a missing definition, or does it
    silently return zero and let the caller move on? `extract_required_
    lenders` must raise, not return an empty list, when the expected count
    does not match what the text contains -- proven here against a fixture
    with NO 'Required Lenders' definition at all for a document key that
    expects one."""
    from generators.extract_voting_thresholds import extract_required_lenders

    doc = "1046102_0001104659-25-031884_tm2511351d1_ex10-1.htm"  # expects 1
    fixture = "This agreement contains no defined-terms article at all."
    try:
        extract_required_lenders(doc, fixture)
        raise AssertionError(
            "extract_required_lenders did not raise on a document with "
            "zero 'Required Lenders' definitions where one was expected")
    except AssertionError as exc:
        assert "expected 1" in str(exc)


DLN = "https://spec.edmcouncil.org/fibo/ontology/SEC/Debt/DistributedLoans/"
EX = "http://example.org/fibo/"

#: Ground truth, from the live regenerated extraction above: 16 threshold
#: rows total across 6 documents, 7 of which carry a stated percentage
#: (5 flat "Required Lenders" + Sabre's Class A + Class B).
EXPECTED_THRESHOLD_COUNT = 16
EXPECTED_PERCENT_BEARING_COUNT = 7


def _n_thresh(sparql):
    rows = fluree.query(sparql)["results"]["bindings"]
    return int(rows[0]["n"]["value"]) if rows else 0


def test_amendment_threshold_nodes_exist_at_the_measured_count():
    assert _n_thresh(
        f"SELECT (COUNT(DISTINCT ?s) AS ?n) FROM <{L}> "
        f"WHERE {{ ?s a <{EX}AmendmentThreshold> }}"
    ) == EXPECTED_THRESHOLD_COUNT


def test_every_threshold_carries_a_consent_standard_and_provenance():
    n_type = _n_thresh(f"SELECT (COUNT(DISTINCT ?s) AS ?n) FROM <{L}> "
                        f"WHERE {{ ?s a <{EX}AmendmentThreshold> }}")
    n_standard = _n_thresh(f"SELECT (COUNT(DISTINCT ?s) AS ?n) FROM <{L}> "
                            f"WHERE {{ ?s a <{EX}AmendmentThreshold> ; "
                            f"<{EX}consentStandard> ?v }}")
    n_prov = _n_thresh(f"SELECT (COUNT(DISTINCT ?s) AS ?n) FROM <{L}> "
                        f"WHERE {{ ?s a <{EX}AmendmentThreshold> ; "
                        f"<{EX}provenance> \"public\" }}")
    assert n_type == n_standard == n_prov == EXPECTED_THRESHOLD_COUNT


def test_consent_percent_is_present_on_exactly_the_percentage_standards():
    """Not merely 'consistent with the generator's output' -- this is the
    live count in the loaded ledger, which would catch the loader silently
    dropping or fabricating a percent literal independently of whether the
    generator's own artifact is correct."""
    n_pct = _n_thresh(f"SELECT (COUNT(DISTINCT ?s) AS ?n) FROM <{L}> "
                       f"WHERE {{ ?s a <{EX}AmendmentThreshold> ; "
                       f"<{EX}consentPercent> ?v }}")
    assert n_pct == EXPECTED_PERCENT_BEARING_COUNT


def test_veto_standard_nodes_carry_no_percent_literal():
    """The other side of the same claim: a node whose consentStandard is
    NOT one of the three percentage-of-exposure standards must have ZERO
    consentPercent triples -- not a small number, exactly zero."""
    rows = fluree.query(
        f"SELECT ?s ?std FROM <{L}> WHERE {{ "
        f"?s a <{EX}AmendmentThreshold> ; <{EX}consentStandard> ?std . "
        f"FILTER(?std != \"Required Lenders\" && "
        f"?std != \"Required Class A Lenders\" && "
        f"?std != \"Required Class B Lenders\") }}"
    )["results"]["bindings"]
    veto_nodes = {r["s"]["value"] for r in rows}
    assert len(veto_nodes) == EXPECTED_THRESHOLD_COUNT - EXPECTED_PERCENT_BEARING_COUNT
    for node in veto_nodes:
        n = _n_thresh(f"SELECT (COUNT(*) AS ?n) FROM <{L}> WHERE {{ "
                      f"<{node}> <{EX}consentPercent> ?v }}")
        assert n == 0, f"{node}: veto-standard node carries a consentPercent"


def test_every_threshold_governs_at_least_one_real_syndicated_loan_node():
    """A threshold that points at nothing, or at a facility this graph
    never typed as a SyndicatedLoan, is a fabricated relationship -- the
    same standard Task 9/10 hold `votesOn`/`counterparty` edges to."""
    rows = fluree.query(
        f"SELECT ?s (COUNT(?fac) AS ?n) FROM <{L}> WHERE {{ "
        f"?s a <{EX}AmendmentThreshold> . "
        f"OPTIONAL {{ ?s <{EX}thresholdGoverns> ?fac . "
        f"?fac a <{DLN}SyndicatedLoan> }} }} GROUP BY ?s"
    )["results"]["bindings"]
    assert len(rows) == EXPECTED_THRESHOLD_COUNT
    for r in rows:
        n = int(r["n"]["value"])
        assert n >= 1, f"{r['s']['value']}: governs no real SyndicatedLoan node"


def test_fac_a4a5ee_has_at_least_one_threshold_to_evaluate_the_open_vote_against():
    """The condition Task 11b exists to make demonstrable: RB Global's
    FAC-A4A5EE carries the live, open amendment vote (Task 9) -- it must
    also carry at least one AmendmentThreshold, or Task 16 has a vote with
    nothing to check it against."""
    fac = f"{EX}syndicate/FAC-A4A5EE"
    n = _n_thresh(f"SELECT (COUNT(DISTINCT ?s) AS ?n) FROM <{L}> WHERE {{ "
                  f"?s a <{EX}AmendmentThreshold> ; "
                  f"<{EX}thresholdGoverns> <{fac}> }}")
    assert n >= 1, "FAC-A4A5EE has no AmendmentThreshold governing it"


def test_no_threshold_node_stores_a_computed_pass_fail_outcome():
    """CLAUDE.md / this task's dispatch: the estate recomputes from the
    stores at request time. A `passes`, `outcome`, `result` or `tally*`
    predicate anywhere on an AmendmentThreshold node would be exactly the
    'counted but not created' failure this task was told not to commit.

    Whole-branch review fix: against an empty AmendmentThreshold population
    every forbidden-predicate count below is trivially 0 and the test would
    pass having looked at nothing. Assert the population is non-empty
    FIRST, so the negative claim only counts as a pass when there was
    something to check it against."""
    population = _n_thresh(
        f"SELECT (COUNT(DISTINCT ?s) AS ?n) FROM <{L}> "
        f"WHERE {{ ?s a <{EX}AmendmentThreshold> }}")
    assert population > 0, (
        "no AmendmentThreshold nodes exist -- the negative claim below "
        "would pass vacuously, having checked nothing")

    forbidden = ["passes", "outcome", "result", "tallyConsent",
                 "tallyDecline", "voteResult", "clearsThreshold"]
    for attr in forbidden:
        n = _n_thresh(f"SELECT (COUNT(*) AS ?n) FROM <{L}> WHERE {{ "
                      f"?s a <{EX}AmendmentThreshold> ; <{EX}{attr}> ?v }}")
        assert n == 0, f"{attr}: a computed outcome was stored, not just the threshold"


def test_every_threshold_cites_a_document_and_offset_that_resolve_in_the_real_filing():
    """Traceability, checked against the ACTUAL cached filing text -- not
    merely that a `sourcePassage` literal exists, but that it names a real
    document and a span that genuinely contains text in that document."""
    from ccf.config import REPO_ROOT as _ROOT
    from generators.extract_facilities import TextExtractor as _TE

    EX10_DIR = _ROOT / "sources" / "ex10"
    rows = fluree.query(
        f"SELECT ?s ?p FROM <{L}> WHERE {{ "
        f"?s a <{EX}AmendmentThreshold> ; <{EX}sourcePassage> ?p }}"
    )["results"]["bindings"]
    assert len(rows) == EXPECTED_THRESHOLD_COUNT

    cache: dict[str, str] = {}
    for r in rows:
        citation = r["p"]["value"]
        document, off = citation.split("#offset=")
        start, end = (int(x) for x in off.split("-"))
        if document not in cache:
            path = EX10_DIR / document
            assert path.exists(), f"{citation}: document not found on disk"
            parser = _TE()
            parser.feed(path.read_text(errors="ignore"))
            parser.close()
            cache[document] = parser.text()
        text = cache[document]
        assert 0 <= start < end <= len(text), f"{citation}: offset out of range"
        assert text[start:end], f"{citation}: span resolves to empty text"


def test_every_threshold_cites_a_span_that_actually_supports_its_own_standard():
    """Findings round 1, CRITICAL. The test above (`..._resolve_in_the_
    real_filing`) only checks that an offset is in-bounds and non-empty --
    any offset anywhere in a 600K+ character document passes that, which is
    exactly how four wrong citations (Sabre class-A/class-B/all-Lenders,
    Bausch each-affected-Lender) shipped uncaught: each one resolved to
    real, non-empty text, just the WRONG clause -- a defined-terms block, an
    unrelated Financial Reporting covenant, or a Defaulting-Lender
    cross-reference.

    `consent_standard` is a curated, closed, cross-document label
    (`ccf/syndicate.py::EX_CONSENT_STANDARD`), not verbatim filed text --
    most of these six filings never write the literal words "each affected
    Lender" or "all Lenders" at the operative clause (they write "such
    Lender", "each Lender ... affected", or bare "each Lender:"). A literal
    substring check of the full consent_standard string against the cited
    span therefore cannot be the discriminator for those buckets, and
    could not have caught this bug even in principle: the WRONG Sabre "all
    Lenders" citation matches its pattern's own text BYTE-FOR-BYTE
    identically to the right one ("Administrative Agent and each Lender:"
    appears once in a Financial Reporting covenant and once in the real
    amendments article -- the regex cannot tell them apart, only POSITION
    can).

    So this test checks the discriminator that genuinely distinguishes a
    right citation from a wrong one, for every one of the 16 nodes:

    - For the three percentage-of-exposure standards ("Required [Class X]
      Lenders"), the matched span IS the defined-terms sentence itself, so
      it must literally contain both consent_standard and consent_percent.
    - For the elevated per-Lender veto standards, the citation must fall
      INSIDE this document's own located voting/amendment article (its
      heading through the next article's heading) -- not merely resolve
      somewhere in the filing. This is exactly the span
      `generators.extract_voting_thresholds.voting_article_scope()` now
      scopes the search to.

    Reads the GENERATED ARTIFACT directly (not live Fluree) so this can run,
    and be confirmed RED, before any reload."""
    from ccf.config import REPO_ROOT as _ROOT
    from generators.extract_facilities import TextExtractor as _TE
    from generators.extract_amendment_assignment_articles import (
        ASSIGN_PATTERNS,
        VOTING_PATTERNS,
        find_heading,
    )

    EX10_DIR = _ROOT / "sources" / "ex10"
    artifact = json.loads((SCREEN / "wave18_voting_thresholds.json").read_text())

    text_cache: dict[str, str] = {}
    scope_cache: dict[str, tuple[int, int]] = {}
    failures: list[str] = []

    for doc in artifact["documents"]:
        document = doc["document"]
        if document not in text_cache:
            path = EX10_DIR / document
            parser = _TE()
            parser.feed(path.read_text(errors="ignore"))
            parser.close()
            text_cache[document] = parser.text()
            vt_hit = find_heading(text_cache[document], VOTING_PATTERNS)
            assign_hit = find_heading(text_cache[document], ASSIGN_PATTERNS)
            assert vt_hit and assign_hit, f"{document}: article heading not found"
            scope_cache[document] = (vt_hit[0], assign_hit[0])
        text = text_cache[document]
        vt_start, assign_start = scope_cache[document]

        for t in doc["thresholds"]:
            _, off = t["source_passage"].split("#offset=")
            start, end = (int(x) for x in off.split("-"))
            span = text[start:end]
            label = f"{document}/{t['bucket']}"

            if t.get("consent_percent"):
                if t["consent_standard"] not in span:
                    failures.append(
                        f"{label}: span {span!r} does not contain "
                        f"consent_standard {t['consent_standard']!r}")
                if t["consent_percent"] not in span:
                    failures.append(
                        f"{label}: span {span!r} does not contain "
                        f"consent_percent {t['consent_percent']!r}")
            else:
                if not (vt_start <= start < assign_start):
                    failures.append(
                        f"{label}: offset {start}-{end} falls OUTSIDE this "
                        f"document's voting/amendment article span "
                        f"[{vt_start}:{assign_start}) -- span text: "
                        f"{span!r}")

    assert not failures, "\n" + "\n".join(failures)


def test_snc_report_is_loaded_with_its_provenance():
    """Wave 18 Task 12 -- the interagency Shared National Credit annual
    report. Ruling T12-R1 overrides the brief's example test: `source`
    holds the named publisher (matching every other row in this
    collection, e.g. Task 11's "SEC EDGAR EX-10 exhibit"), and the
    retrievable address is asserted on `url` instead."""
    from ccf.config import mongo_db

    db = mongo_db(write=False)
    doc = db["document"].find_one({"doc_type": "snc_annual_report"})
    if doc is None:
        pytest.skip("SNC report not located -- see docs/known-issues.md; "
                    "Task 17 records the §C row as DEFERRED")
    assert doc["provenance"] == "public"
    assert doc["url"].startswith("http"), "no retrievable source URL"
    assert doc["source"], "no publisher recorded"
    assert doc["retrieved_at"], "no retrieval date recorded"
    assert len(doc["text"]) > 5000, "the report body did not extract"


# --- Task 13: SQLite -- the syndicate desk tracker -------------------------
#
# Ruling T13-R1: the brief's own `test_tracker_is_departmental_only` only
# checks that no Postgres table is NAMED like this one -- a check that
# cannot see a duplicate landing under any other table name. Kept below,
# but followed by a content probe: the actual `desk_note` text of the
# engineered row, searched for verbatim in Postgres (the six tables Wave
# 18's own loader writes -- `syndicate_member`, `member_call_report`,
# `own_position`, `competition_law_rule`, `syndicate_projection_plan`, and
# (Task 15) `context_debt`, the one pre-existing table Wave 18 gained a
# WRITE PATH into without owning; NOT `facility`, which Wave 18 never
# writes to, see `loaders/load_sqlite_wave18.py`'s module docstring),
# Fluree (the whole `fibo-v2` ledger -- Fluree has no table boundary to
# scope to), and MongoDB (the `document` and `passage` collections Wave 18
# writes to). This is a deliberately narrow scan, not a full-estate one --
# named here so a reader knows exactly what it covers and what it does
# not. It still does not cover: any OTHER wave's Postgres tables, the
# peer's `colender` schema (that is `test_the_desks_engineered_note_never_
# crossed_to_the_peer_fabric`, below, added the same task the probe gained
# its `context_debt` arm), or SQLite tables other than the tracker itself.

import sqlite3

from ccf.config import SQLITE_PATH


def _sqlite(sql):
    with sqlite3.connect(SQLITE_PATH) as con:
        return con.execute(sql).fetchall()


def test_desk_tracker_exists_and_is_populated():
    assert _sqlite("SELECT count(*) FROM syndicate_desk_tracker")[0][0] >= 6


def test_tracker_rows_reference_real_facilities():
    from ccf.config import pg_connect, PG_SCHEMA_V2 as S
    tracked = {r[0] for r in _sqlite(
        "SELECT DISTINCT facility_id FROM syndicate_desk_tracker")}
    with pg_connect() as c, c.cursor() as cur:
        cur.execute(f'SELECT facility_id FROM "{S}".facility')
        known = {r[0] for r in cur.fetchall()}
    assert tracked <= known, f"tracker names unknown facilities: {tracked - known}"


def test_tracker_is_departmental_only():
    """P4: SQLite holds departmental material. If the desk's note were
    also in Postgres, the departmental-store narrative would be a fiction."""
    from ccf.config import pg_connect, PG_SCHEMA_V2 as S
    with pg_connect() as c, c.cursor() as cur:
        cur.execute("SELECT count(*) FROM information_schema.tables "
                    "WHERE table_schema=%s AND table_name LIKE %s",
                    (S, "%desk_tracker%"))
        assert cur.fetchone()[0] == 0


def _engineered_note() -> str:
    rows = _sqlite(
        "SELECT desk_note FROM syndicate_desk_tracker "
        "WHERE provenance = 'synthetic — engineered'")
    assert len(rows) == 1, (
        f"expected exactly one engineered row, found {len(rows)}")
    return rows[0][0]


def _postgres_wave18_tables_contain(text: str) -> list[str]:
    """Scoped scan (Ruling T13-R1, extended by Task 15): the six tables
    Wave 18 writes to -- see the block comment above. Not `facility`,
    which is a shared table Wave 18 never inserts into. `context_debt` is
    included because Task 15 gave Wave 18 a write path into it (one
    guarded row per unattested peer product declaration) -- it is a
    pre-existing 303-row table another wave owns, not a Wave 18 table, but
    a write path is a write path and the probe has to see it."""
    from ccf.config import pg_connect, PG_SCHEMA_V2 as S
    tables = ["syndicate_member", "member_call_report", "own_position",
              "competition_law_rule", "syndicate_projection_plan",
              "context_debt"]
    hits = []
    with pg_connect() as c, c.cursor() as cur:
        for table in tables:
            cur.execute(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_schema=%s AND table_name=%s "
                "AND data_type IN ('text', 'character varying', "
                "'character', 'jsonb')", (S, table))
            for col, dtype in cur.fetchall():
                cast = f'"{col}"::text' if dtype == "jsonb" else f'"{col}"'
                cur.execute(
                    f'SELECT 1 FROM "{S}"."{table}" '
                    f"WHERE position(%s in coalesce({cast}, '')) > 0 LIMIT 1",
                    (text,))
                if cur.fetchone():
                    hits.append(f"{table}.{col}")
    return hits


def _fluree_contains(text: str) -> bool:
    """Full-ledger scan -- Fluree has no per-wave table boundary to scope
    to, so every literal object in `fibo-v2` is checked."""
    from ccf import fluree
    from ccf.config import FLUREE_LEDGER_V2 as L
    escaped = text.replace('"', '\\"')
    sparql = (
        f'SELECT ?s FROM <{L}> WHERE {{ ?s ?p ?o . '
        f'FILTER(isLiteral(?o) && CONTAINS(STR(?o), "{escaped}")) }} LIMIT 1'
    )
    r = fluree.query(sparql)
    return bool(r["results"]["bindings"])


def _mongo_wave18_collections_contain(text: str) -> list[str]:
    """Scoped scan (Ruling T13-R1): the two collections Wave 18 writes to."""
    from ccf.config import mongo_db
    db = mongo_db(write=False)
    hits = []
    pattern = re.compile(re.escape(text))
    for coll_name, field in (("document", "text"), ("passage", "text")):
        if db[coll_name].find_one({field: pattern}):
            hits.append(f"{coll_name}.{field}")
    return hits


def test_engineered_note_text_is_absent_from_the_other_four_stores():
    """Ruling T13-R1 content probe. Queries for the string; does not
    reason about it. See the block comment above for exactly what is
    scanned in each store."""
    note = _engineered_note()

    pg_hits = _postgres_wave18_tables_contain(note)
    assert not pg_hits, f"engineered note text found in Postgres: {pg_hits}"

    assert not _fluree_contains(note), (
        "engineered note text found in the Fluree ledger")

    mongo_hits = _mongo_wave18_collections_contain(note)
    assert not mongo_hits, f"engineered note text found in MongoDB: {mongo_hits}"


# =========================================================================
# Task 14 -- the peer estate: positions at two disclosure precisions
# =========================================================================
#
# Everything below runs against the CO-LENDER fabric, never ours. It is a
# separate database, on a separate role, on the same host and port -- which
# is exactly why `test_peer_writes_landed_in_the_peer_database` asks the
# server what it is connected to rather than trusting the config that got
# it there.

from ccf.config import (co_lender_configured, co_lender_pg_connect,
                        CO_LENDER_PG_SCHEMA as PS, assert_distinct_fabrics)


def _peer(sql, params=None):
    if not co_lender_configured():
        pytest.skip("peer fabric not configured in this shell")
    with co_lender_pg_connect() as c, c.cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchall()


def test_the_two_fabrics_are_still_distinct():
    assert_distinct_fabrics()


def test_peer_writes_landed_in_the_peer_database():
    db = _peer("SELECT current_database()")[0][0]
    assert db == "bofa_syndicated", f"peer rows went to {db!r}"


def test_two_counterparty_identities_exist():
    got = {r[0] for r in _peer(
        f'SELECT DISTINCT counterparty FROM "{PS}".peer_position')}
    assert len(got) >= 2, f"only {got} on the peer fabric"


def test_one_counterparty_discloses_exactly_and_one_only_a_band():
    rows = _peer(f'SELECT counterparty, share_usd, band_low, band_high '
                 f'FROM "{PS}".peer_position')
    exact = {r[0] for r in rows if r[1] is not None}
    banded = {r[0] for r in rows if r[1] is None
              and r[2] is not None and r[3] is not None}
    assert exact and banded, f"exact={exact} banded={banded}"
    assert not (exact & banded), (
        "a counterparty discloses both ways; the precision is then not a "
        "property of the counterparty and the floor proves nothing")


def test_the_band_peer_has_no_exact_figure_anywhere_on_the_peer_fabric():
    """§F's mixed-precision floor is only real if the band cannot be
    resolved to a number. Checks the DENOMINATOR independently -- every
    row for that counterparty, not just the rows flagged as banded."""
    banded = {r[0] for r in _peer(
        f'SELECT DISTINCT counterparty FROM "{PS}".peer_position '
        f'WHERE share_usd IS NULL')}
    assert banded, "no banded counterparty at all -- nothing to check"
    for cp in banded:
        leaks = _peer(f'SELECT count(*) FROM "{PS}".peer_position '
                      f'WHERE counterparty = %s AND share_usd IS NOT NULL',
                      (cp,))[0][0]
        assert leaks == 0, f"{cp} has {leaks} exact figures despite banding"


def test_the_band_is_not_a_point():
    """A band whose bounds are equal is an exact figure wearing a costume."""
    degenerate = _peer(f'SELECT counterparty, band_low, band_high '
                       f'FROM "{PS}".peer_position '
                       f'WHERE band_low IS NOT NULL AND band_low >= band_high')
    assert not degenerate, f"degenerate bands: {degenerate}"


# --- the true figure, re-derived independently ---------------------------
#
# Every check below needs the figure the band conceals. It is NOT read from
# `wave18_peer.json` (which deliberately does not carry it) and NOT read
# from the peer fabric (where its absence is the property under test). It
# is re-derived here from the filed commitment schedule -- the public
# source -- so these tests would still catch a leak if the generator and
# the loader agreed on a wrong number.

def _filed_shares_by_facility(lei: str) -> dict[str, int]:
    """facility_id -> that counterparty's filed commitment total ON THAT
    FACILITY, from Task 2's schedule artifact plus the institutions
    artifact's own name resolution.

    PER FACILITY, not per LEI. This function used to return one sum across
    every agreement, and every caller below then scanned for that sum --
    which is not the quantity any band conceals. A band is computed by
    `generators/generate_peer_positions.py` from ONE (lei, facility_id)
    pair, so a per-LEI total is a different quantity that happens to be
    equal while the counterparty has exactly one filed row in the whole
    corpus, and stops being equal the moment it has two. The absence scans
    would then hunt a number nobody is concealing and pass forever with the
    real figure in plain sight -- this estate's "count the unit the
    condition names" failure, on the wave's central floor. Demonstrated
    live before the fix (Task 14 report, fix round 1): with a second filed
    row, all THREE needle-based checks went green while $70,000,000 sat in
    two places on the peer fabric.
    """
    from ccf.syndicate import TRANCHE_TO_FACILITIES
    institutions = _institutions()
    raw_names = {n for m in institutions["members"] if m["lei"] == lei
                 for n in m["raw_names"]}
    assert raw_names, f"{lei} resolves to no member in the Task 3 artifact"

    schedules = json.loads((SCREEN / "wave18_schedules.json").read_text())
    totals: dict[str, int] = {}
    # Keyed across ALL agreements, exactly as load_fluree_wave18.py's own
    # `group_position` is -- the reading has to be the loader's, not a
    # near-copy of it.
    seen: dict[tuple, int] = {}
    for agreement in schedules["agreements"]:
        tranche_map = TRANCHE_TO_FACILITIES[agreement["document"]]
        for row in agreement["rows"]:
            if row["lender_raw"] not in raw_names:
                continue
            # The same positional reading loaders/load_fluree_wave18.py
            # uses for AHR's two-column schedule; asserted, not assumed.
            candidates = tranche_map[row["tranche"]]
            key = (row["lender_raw"], row["offset"], row["end"])
            pos = seen.get(key, 0)
            seen[key] = pos + 1
            assert pos < len(candidates), (
                f"{row['lender_raw']} at offset {row['offset']} has more "
                f"occurrences than TRANCHE_TO_FACILITIES has facilities for "
                f"tranche {row['tranche']!r}")
            facility_id = candidates[pos]
            totals[facility_id] = totals.get(facility_id, 0) + row["amount_usd"]
    assert totals, f"{lei} has no filed schedule rows at all"
    return totals


def _filed_share_for(lei: str, facility_id: str) -> int:
    """The one figure a band on `(lei, facility_id)` conceals."""
    totals = _filed_shares_by_facility(lei)
    assert facility_id in totals, (
        f"{lei} holds a peer position on {facility_id} but no filed schedule "
        f"row puts them on it -- there is no concealed figure to scan for, "
        f"and a scan with no needle proves nothing")
    return totals[facility_id]


def _banded_positions() -> list[tuple[str, str]]:
    """Every (counterparty, facility_id) disclosed as a band, from the peer
    fabric itself. One needle per position, never one per counterparty."""
    rows = sorted({(r[0], r[1]) for r in _peer(
        f'SELECT counterparty, facility_id FROM "{PS}".peer_position '
        f'WHERE share_usd IS NULL')})
    assert rows, (
        "no banded position on the peer fabric at all -- §F's "
        "mixed-precision floor has nothing behind it, and every absence "
        "scan below would be looking for nothing")
    return rows


def _concealed_figures() -> dict[tuple[str, str], int]:
    """(counterparty, facility_id) -> the figure its band conceals."""
    return {(cp, fid): _filed_share_for(cp, fid)
            for cp, fid in _banded_positions()}


def test_the_band_brackets_the_filed_figure_without_revealing_it():
    """A band that does not contain the position is a false disclosure; a
    band whose midpoint IS the position is not a disclosure at all. Both
    are checked against a figure re-derived from the filed schedule, not
    against anything either the generator or the loader emitted."""
    rows = _peer(f'SELECT counterparty, facility_id, band_low, band_high '
                 f'FROM "{PS}".peer_position WHERE share_usd IS NULL')
    assert rows, "no banded position to check"
    for cp, facility_id, low, high in rows:
        # The figure THIS band conceals -- the filed total on THIS
        # facility, not the counterparty's total across the corpus.
        true_usd = _filed_share_for(cp, facility_id)
        low, high = int(low), int(high)
        assert low < true_usd < high, (
            f"{cp} on {facility_id}: band [{low}, {high}] does not contain "
            f"the filed figure")
        width = high - low
        estimators = {
            "midpoint": (low + high) / 2,
            "lower quartile": low + 0.25 * width,
            "upper quartile": low + 0.75 * width,
            "lower tercile": low + width / 3,
            "upper tercile": low + 2 * width / 3,
            "geometric mean": (low * high) ** 0.5,
        }
        for name, estimate in estimators.items():
            margin = abs(estimate - true_usd) / true_usd
            assert margin >= 0.10, (
                f"{cp} on {facility_id}: the band's {name} "
                f"({estimate:,.0f}) lands within {margin:.1%} of the true "
                f"figure -- the band leaks it")


def _peer_schema_columns():
    """Every column of every table in the peer's schema.

    Asserts BOTH that the listing is non-empty AND that every table it
    names holds at least one row. The callers below scan for the ABSENCE
    of a string with `SELECT ... LIMIT 1`, and that returns nothing --
    green -- over an empty schema and equally over a table that exists
    with zero rows in it. The first version of this helper guarded only
    the column listing, which is the same defect one level down: the
    scan still looked at nothing, it just had a schema to not look at
    (Ruling T14-R3).

    A table this refuses is not a bug in the table. It is a scan with no
    population, and it must be loud rather than green.
    """
    columns = _peer(
        "SELECT table_name, column_name FROM information_schema.columns "
        "WHERE table_schema = %s ORDER BY 1, 2", (PS,))
    assert columns, (
        f"the peer schema {PS!r} holds no columns at all -- an absence "
        f"scan over nothing proves nothing")

    empty = [table for table in sorted({t for t, _ in columns})
             if _peer(f'SELECT count(*) FROM "{PS}"."{table}"')[0][0] == 0]
    assert not empty, (
        f"tables {empty} in the peer schema hold zero rows -- a "
        f"'SELECT 1 ... LIMIT 1' absence scan over an empty table returns "
        f"nothing and reports green while looking at nothing")
    return columns


def test_the_true_figure_appears_in_no_column_of_the_peer_schema():
    """Wider than `..._has_no_exact_figure_anywhere_on_the_peer_fabric`,
    deliberately: that one checks `share_usd` on that counterparty's rows,
    this one checks EVERY column of EVERY table in the peer's schema,
    including tables later tasks add. Storing the number in a note field,
    a second table, or somebody's `comment` column would defeat the floor
    just as completely as storing it in `share_usd`.

    One needle PER BANDED POSITION, never one per counterparty -- see
    `_filed_shares_by_facility` for what scanning a per-LEI total instead
    costs, and for the live demonstration that it costs it silently."""
    hits = []
    targets = _peer_schema_columns()
    for (cp, facility_id), figure in _concealed_figures().items():
        needle = str(figure)
        for table, column in targets:
            found = _peer(
                f'SELECT 1 FROM "{PS}"."{table}" '
                f'WHERE position(%s in coalesce("{column}"::text, \'\')) > 0 '
                f"LIMIT 1", (needle,))
            if found:
                hits.append(f"{needle} ({cp} on {facility_id}) in "
                            f"{table}.{column}")
    assert not hits, f"concealed figures appear on the peer fabric: {hits}"


def test_the_true_figure_appears_in_no_literal_on_the_peer_ledger():
    """The other half of the same question. A figure kept out of the
    peer's Postgres and put into the peer's graph is still on the peer
    fabric. One needle per banded position, same as the column scan."""
    if not co_lender_configured():
        pytest.skip("peer fabric not configured in this shell")
    from ccf import fluree
    from ccf.config import CO_LENDER_FLUREE_LEDGER as PL
    hits = []
    for (cp, facility_id), figure in _concealed_figures().items():
        needle = str(figure)
        sparql = (f'SELECT ?s ?p ?o FROM <{PL}> WHERE {{ ?s ?p ?o . '
                  f'FILTER(isLiteral(?o) && CONTAINS(STR(?o), "{needle}")) }} '
                  f"LIMIT 5")
        for b in fluree.co_lender_query(sparql)["results"]["bindings"]:
            hits.append(f"{needle} ({cp} on {facility_id}) at "
                        f"{b['s']['value']} {b['p']['value']}")
    assert not hits, f"concealed figures appear on the peer ledger: {hits}"


def test_peer_positions_reference_facilities_that_exist_on_our_side():
    """A peer position on a facility we do not hold cannot be assembled
    across the boundary, and nothing downstream would say so. Resolved
    against OUR Postgres -- the store that owns facilities -- not against
    the artifact the peer rows were built from."""
    from ccf.config import PG_SCHEMA_V2, pg_connect
    peer_facilities = sorted({r[0] for r in _peer(
        f'SELECT DISTINCT facility_id FROM "{PS}".peer_position')})
    assert peer_facilities, "no peer positions at all"
    with pg_connect() as c, c.cursor() as cur:
        cur.execute(f'SELECT facility_id FROM "{PG_SCHEMA_V2}".facility '
                    f"WHERE facility_id = ANY(%s)", (peer_facilities,))
        ours = {r[0] for r in cur.fetchall()}
    assert not set(peer_facilities) - ours, (
        f"peer positions on facilities we do not hold: "
        f"{sorted(set(peer_facilities) - ours)}")


def test_peer_positions_carry_only_the_three_provenance_classes():
    """CLAUDE.md's exact vocabulary, em dash and all -- and the banded
    rows must be `engineered`, not `internal`: they exist to create §F's
    mixed-precision condition, which is the definition of the third
    class."""
    rows = _peer(f'SELECT provenance, share_usd FROM "{PS}".peer_position')
    allowed = {"public", "synthetic — internal", "synthetic — engineered"}
    assert {p for p, _ in rows} <= allowed, (
        f"unknown provenance: {sorted({p for p, _ in rows} - allowed)}")
    banded_provenance = {p for p, share in rows if share is None}
    assert banded_provenance == {"synthetic — engineered"}, (
        f"banded rows carry {banded_provenance}; a row that exists to "
        f"create the mixed-precision condition is engineered")


def test_both_counterparty_identities_are_typed_nodes_on_the_peer_ledger():
    """Fluree runs without OWL inference (CLAUDE.md rule 7), so a node is
    only findable by the types it explicitly carries. Both identities must
    be reachable as FinanceSyndicateMember AND must declare their own
    disclosure precision on the graph, not only in a Postgres column."""
    if not co_lender_configured():
        pytest.skip("peer fabric not configured in this shell")
    from ccf import fluree
    from ccf.config import CO_LENDER_FLUREE_LEDGER as PL, EX
    from ccf.syndicate import (EX_DISCLOSURE_PRECISION,
                               FIBO_FINANCE_SYNDICATE_MEMBER)
    rdf_type = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
    sparql = (
        f"SELECT ?lei ?precision FROM <{PL}> WHERE {{ "
        f"?s <{rdf_type}> <{FIBO_FINANCE_SYNDICATE_MEMBER}> . "
        f"?s <{EX}lei> ?lei . "
        f"?s <{EX_DISCLOSURE_PRECISION}> ?precision }}")
    got = {b["lei"]["value"]: b["precision"]["value"]
           for b in fluree.co_lender_query(sparql)["results"]["bindings"]}
    pg_leis = {r[0] for r in _peer(
        f'SELECT DISTINCT counterparty FROM "{PS}".peer_position')}
    assert set(got) == pg_leis, (
        f"the peer ledger types {sorted(got)} but its Postgres holds "
        f"positions for {sorted(pg_leis)}")
    assert set(got.values()) == {"exact", "band"}, (
        f"precisions on the peer ledger are {sorted(set(got.values()))}")


def test_the_desks_engineered_note_never_crossed_to_the_peer_fabric():
    """Task 13's content probe, extended across the organizational
    boundary. It asserts the desk's engineered note text sits in SQLite
    and nowhere else in our four stores; the co-lender's estate is the one
    place it would be worst to find, and the probe could not see there."""
    note = _engineered_note()
    hits = []
    for table, column in _peer_schema_columns():
        found = _peer(f'SELECT 1 FROM "{PS}"."{table}" '
                      f'WHERE position(%s in coalesce("{column}"::text, \'\')) > 0 '
                      f"LIMIT 1", (note,))
        if found:
            hits.append(f"{table}.{column}")
    assert not hits, f"the desk's engineered note reached the peer: {hits}"


# =========================================================================
# Task 15 -- peer product declarations: timeout, attestation, TTL
#
# These three are the §F conditions that sound like behaviour. They are
# declarations in data -- the SDK reads them and acts, this project never
# does. Everything below runs against `colender.peer_product_declaration`
# on the peer fabric, plus one guarded row on `ccf_v2.context_debt` on ours.
# =========================================================================

# MAX_FEDERATION_LATENCY_MS and LOCAL_COMPOSITE_TTL_SECONDS (both §B) are
# imported from ccf/syndicate.py, not redefined here (whole-branch review
# fix -- consolidates what were four independent copies under two names).


def test_one_declaration_exceeds_the_default_latency_bound():
    """§F: >= 1 federated request that times out, so fail-closed is
    observed. Recomputed: declared latency vs. the declared bound."""
    slow = _peer(f'SELECT counterparty, declared_latency_ms '
                 f'FROM "{PS}".peer_product_declaration '
                 f'WHERE declared_latency_ms > %s',
                 (MAX_FEDERATION_LATENCY_MS,))
    assert slow, "no declaration would breach the 5s default bound"


def test_not_every_declaration_is_slow():
    """A fabric where every peer times out demonstrates nothing about
    fail-closed -- it just looks broken."""
    fast = _peer(f'SELECT count(*) FROM "{PS}".peer_product_declaration '
                 f'WHERE declared_latency_ms <= %s',
                 (MAX_FEDERATION_LATENCY_MS,))[0][0]
    assert fast >= 1


def test_exactly_one_claim_is_unattested():
    """§F: >= 1 unattested remote claim, so Context Debt is exercised.
    Asserts the absence is genuine AND that it is the intended one."""
    rows = _peer(f'SELECT declaration_id, attestation '
                 f'FROM "{PS}".peer_product_declaration')
    unattested = [r[0] for r in rows if r[1] is None]
    assert len(unattested) == 1, (
        f"{len(unattested)} unattested declarations; the floor needs "
        f"exactly one so the case is identifiable")
    assert len(rows) > 1, "everything is unattested; nothing is contrasted"


def test_the_unattested_claim_is_recorded_as_context_debt_on_our_side():
    n = _pg(f'SELECT count(*) FROM "{S}".context_debt '
            f"WHERE reason LIKE '%unattested%'")[0][0]
    assert n >= 1


def test_a_remote_ttl_binds_below_the_local_composite():
    """§F: >= 1 remote product with a shorter TTL than the local composite
    would otherwise carry. §B puts the local TTL at 4 hours."""
    ttls = [r[0] for r in _peer(
        f'SELECT declared_ttl_seconds FROM "{PS}".peer_product_declaration')]
    assert ttls, "no declarations"
    assert min(ttls) < LOCAL_COMPOSITE_TTL_SECONDS, (
        f"shortest remote TTL is {min(ttls)}s; the local composite is "
        f"{LOCAL_COMPOSITE_TTL_SECONDS}s, so the TTL floor never binds")
    assert max(ttls) > LOCAL_COMPOSITE_TTL_SECONDS, (
        "no remote TTL exceeds the local composite -- a TTL merely equal "
        "to it does not show the local composite winning as the shorter "
        "value, so the 'shortest of them' rule is untested")


def test_declarations_reference_counterparties_that_hold_a_peer_position():
    """A declaration describing a product the peer does not actually
    expose would be unassemblable -- the same reasoning
    `test_peer_positions_reference_facilities_that_exist_on_our_side`
    applies to positions, applied here to declarations."""
    held = {r[0] for r in _peer(
        f'SELECT DISTINCT counterparty FROM "{PS}".peer_position')}
    declared = {r[0] for r in _peer(
        f'SELECT DISTINCT counterparty FROM "{PS}".peer_product_declaration')}
    assert declared, "no product declarations at all"
    assert declared <= held, (
        f"declarations name counterparties with no peer position: "
        f"{declared - held}")


def test_declarations_carry_only_the_three_provenance_classes():
    """CLAUDE.md's exact vocabulary, em dash and all -- and a row
    manufactured to CREATE a condition (the slow row, the unattested row)
    must be `engineered`, not `internal`."""
    rows = _peer(f'SELECT declaration_id, provenance, attestation, '
                 f'declared_latency_ms FROM "{PS}".peer_product_declaration')
    allowed = {"public", "synthetic — internal", "synthetic — engineered"}
    assert {p for _, p, _, _ in rows} <= allowed, (
        f"unknown provenance: {sorted({p for _, p, _, _ in rows} - allowed)}")
    for declaration_id, provenance, attestation, latency in rows:
        if attestation is None or latency > MAX_FEDERATION_LATENCY_MS:
            assert provenance == "synthetic — engineered", (
                f"{declaration_id} exists to demonstrate a §F condition but "
                f"carries provenance {provenance!r}")


# =========================================================================
# Task 16 -- tests of the VALIDATOR itself, not of the data
#
# Every one of the six floors is fed a known-present input and a
# known-absent one and REQUIRED to give different answers. This estate has
# twice shipped a check that returned the same answer either way and hid a
# defect for seven waves (MEMORY: "Output that never varies"), so an arm
# that cannot be made to say "no" is treated here as an arm that is not
# looking at anything.
#
# The mutations run against `syndicate.Context`, which is a mutable
# dataclass of SNAPSHOTS (Preflight Ruling P3) -- never a live cursor.
# Nothing below writes to any store, ours or the peer's.
# =========================================================================

import copy

from validators import syndicate

#: One snapshot, deep-copied per test.
#:
#: `syndicate.load_context()` scans all 111 `ccf_v2` tables, 37k ledger
#: literals and six re-extracted filings -- ~25s. Twenty-odd tests each
#: taking their own snapshot is ten minutes, which is ten minutes nobody
#: runs. The copy is a real deep copy, so a test that flattens the vote or
#: re-points a participation cannot leak that mutation into the next test;
#: Python's immutable strings mean the 3.6MB of filing text is shared rather
#: than duplicated.
_BASE_CTX = None


def _ctx():
    global _BASE_CTX
    if not co_lender_configured():
        pytest.skip("peer fabric not configured in this shell")
    if _BASE_CTX is None:
        _BASE_CTX = syndicate.load_context()
    return copy.deepcopy(_BASE_CTX)


def test_the_shared_snapshot_is_not_leaking_mutations_between_tests():
    """The deep copy above is load-bearing: every falsification test below
    mutates its context, and a shared object would make the results depend
    on test ORDER. Mutate one copy, take another, require the second to be
    untouched."""
    first = _ctx()
    first.vote_postures.clear()
    first.peer_positions[0]["share_usd"] = -1
    second = _ctx()
    assert second.vote_postures, "vote_postures leaked between snapshots"
    assert second.peer_positions[0]["share_usd"] != -1, (
        "peer_positions leaked between snapshots")


def test_every_floor_returns_a_two_tuple():
    ctx = _ctx()
    for label, fn in syndicate.FLOORS:
        ok, detail = fn(ctx)
        assert isinstance(ok, bool), f"{label} returned {ok!r}"
        assert isinstance(detail, str) and detail, f"{label} gave no detail"


def test_every_floor_passes_on_the_real_estate():
    """The known-present half for all six at once. Named separately from
    the shape test above so a failure says WHICH floor, with its own
    measured detail line, rather than 'the tuple was fine'."""
    ctx = _ctx()
    failures = [f"{label}: {detail}"
                for label, fn in syndicate.FLOORS
                for ok, detail in [fn(ctx)] if not ok]
    assert not failures, "\n" + "\n".join(failures)


# --- 1. shares_are_sourced ----------------------------------------------

def test_share_sourcing_says_yes_on_the_real_estate():
    ok, detail = syndicate.shares_are_sourced(_ctx())
    assert ok, detail


def test_share_sourcing_says_no_when_a_share_claims_the_wrong_lender():
    """Re-point one participation at a DIFFERENT member. The cited offset
    still resolves to real, non-empty filed text -- it is simply somebody
    else's name, which is exactly the failure Task 11b's fix round proved
    an in-bounds/non-empty check cannot see."""
    ctx = _ctx()
    part = ctx.participations[0]
    other = next(m for m in ctx.members if m != part["member_id"])
    part["member_id"] = other
    ok, detail = syndicate.shares_are_sourced(ctx)
    assert not ok, f"passed with a share attributed to the wrong lender: {detail}"


def test_share_sourcing_says_no_when_the_amount_is_not_at_that_row():
    """The name still resolves; only the figure is invented."""
    ctx = _ctx()
    ctx.participations[0]["commitment_usd"] = 12_345
    ok, detail = syndicate.shares_are_sourced(ctx)
    assert not ok, f"passed with an amount absent from the filed row: {detail}"


def test_share_sourcing_says_no_when_the_offset_points_somewhere_else():
    """An offset moved well clear of its row but STAYING INSIDE the
    document: still in bounds, still non-empty text, no longer the lender
    it claims.

    Ruling T16-R3, fix round 1. The first cut of this test added a flat
    +50,000, which for the participation it happened to pick left the
    document entirely (615,285 into a 566,425-character filing). The floor
    said "no", but it said it from the BOUNDS guard -- the mutation broke
    the input's shape rather than removing the condition, so the
    name-resolution branch this test is named for was never exercised. The
    displacement now wraps inside the document, the in-bounds precondition
    is ASSERTED before the floor is called, and the failure message is
    required to be the name-resolution one.
    """
    ctx = _ctx()
    part = ctx.participations[0]
    text = ctx.documents[part["document"]]
    span_len = part["end"] - part["start"]
    new_start = (part["start"] + 50_000) % (len(text) - span_len)
    part["start"], part["end"] = new_start, new_start + span_len

    assert 0 <= part["start"] < part["end"] <= len(text), (
        "the mutation left the document -- it would be rejected by the "
        "bounds guard and this test would prove nothing about name "
        "resolution")
    assert text[part["start"]:part["end"]].strip(), (
        "the displaced span is blank; the floor would reject it for being "
        "empty rather than for naming the wrong lender")

    ok, detail = syndicate.shares_are_sourced(ctx)
    assert not ok, f"passed on a displaced offset: {detail}"
    assert "does not resolve to" in detail, (
        f"the floor said no, but not from the name-resolution branch this "
        f"test names: {detail}")


# --- 2. envelopes_are_asymmetric ----------------------------------------

def test_asymmetry_checker_says_no_when_scopes_match():
    """Feed it a context where every envelope's two scopes are identical.
    If it still passes, it is not reading the scopes."""
    ctx = _ctx()
    for env in ctx.envelopes.values():
        env["disclose"] = set(env["request"])
    ok, detail = syndicate.envelopes_are_asymmetric(ctx)
    assert not ok, f"passed on symmetric envelopes: {detail}"


def test_asymmetry_checker_says_yes_on_the_real_estate():
    ok, detail = syndicate.envelopes_are_asymmetric(_ctx())
    assert ok, detail


def test_asymmetry_checker_says_no_when_a_scope_is_empty():
    """An empty disclose set differs from a non-empty request set, so a
    bare set-inequality test would count it as asymmetric. It is not a
    negotiated term, it is a missing one."""
    ctx = _ctx()
    for env in ctx.envelopes.values():
        env["disclose"] = set()
    ok, detail = syndicate.envelopes_are_asymmetric(ctx)
    assert not ok, f"passed on an envelope that discloses nothing: {detail}"


# --- 3. precision_is_mixed ----------------------------------------------

def test_precision_checker_says_yes_on_the_real_estate():
    ok, detail = syndicate.precision_is_mixed(_ctx())
    assert ok, detail


def test_precision_checker_says_no_when_the_band_peer_gains_a_figure():
    ctx = _ctx()
    for row in ctx.peer_positions:
        if row["share_usd"] is None:
            row["share_usd"] = 75_000_000
            break
    ok, detail = syndicate.precision_is_mixed(ctx)
    assert not ok, f"passed after the band peer disclosed exactly: {detail}"


def test_precision_checker_says_no_when_every_counterparty_is_exact():
    """The other direction: no band at all. `share_usd IS NULL` is the
    property the floor polices, so a check that SELECTED banded rows first
    could not see the population empty out."""
    ctx = _ctx()
    for row in ctx.peer_positions:
        if row["share_usd"] is None:
            row["share_usd"] = int(row["band_low"]) + 1
    ok, detail = syndicate.precision_is_mixed(ctx)
    assert not ok, f"passed with every peer position exact: {detail}"


# --- 4. vote_postures_diverge -------------------------------------------

def test_posture_checker_says_yes_on_the_real_estate():
    ok, detail = syndicate.vote_postures_diverge(_ctx())
    assert ok, detail


def test_posture_checker_says_no_when_all_postures_agree():
    ctx = _ctx()
    ctx.vote_postures = {k: "consent" for k in ctx.vote_postures}
    ok, detail = syndicate.vote_postures_diverge(ctx)
    assert not ok, f"passed on unanimous postures: {detail}"


# --- 5. federation_bounds_bind ------------------------------------------

def test_federation_checker_says_yes_on_the_real_estate():
    ok, detail = syndicate.federation_bounds_bind(_ctx())
    assert ok, detail


def test_ttl_checker_says_no_when_every_remote_ttl_is_long():
    ctx = _ctx()
    for d in ctx.declarations:
        d["declared_ttl_seconds"] = 86_400
    ok, detail = syndicate.federation_bounds_bind(ctx)
    assert not ok, f"passed when no remote TTL binds: {detail}"


def test_latency_checker_says_no_when_every_declaration_is_fast():
    ctx = _ctx()
    for d in ctx.declarations:
        d["declared_latency_ms"] = 100
    ok, detail = syndicate.federation_bounds_bind(ctx)
    assert not ok, f"passed when nothing would breach the latency bound: {detail}"


def test_attestation_checker_says_no_when_everything_is_attested():
    ctx = _ctx()
    stand_in = next(d["attestation"] for d in ctx.declarations
                    if d["attestation"] is not None)
    for d in ctx.declarations:
        d["attestation"] = stand_in
    ok, detail = syndicate.federation_bounds_bind(ctx)
    assert not ok, f"passed with no unattested claim at all: {detail}"


# --- 6. lineage_is_separable --------------------------------------------

def test_lineage_checker_says_yes_on_the_real_estate():
    ok, detail = syndicate.lineage_is_separable(_ctx())
    assert ok, detail


def test_element_origin_is_derived_from_the_probes_not_stored():
    """`element_origin` is a computed property over `element_probes`, so it
    cannot be set to a convenient value -- which is the whole point. If it
    ever becomes an assignable field, this test fails and the floor stops
    proving anything."""
    ctx = _ctx()
    with pytest.raises(AttributeError):
        ctx.element_origin = {"peer_position": "remote"}


def test_lineage_checker_says_no_when_a_peer_element_also_answers_locally():
    """The failure the floor exists for: a peer claim reachable through a
    path that marks it local. Simulated by making the SAME probe answer on
    both fabrics -- the element is then not distinguishable by origin."""
    ctx = _ctx()
    remote = next(e for e, o in ctx.element_origin.items() if o == "remote")
    ctx.element_probes[remote]["local"] = 7
    assert ctx.element_origin[remote] == "both"
    ok, detail = syndicate.lineage_is_separable(ctx)
    assert not ok, f"passed with {remote} answering on both fabrics: {detail}"


def test_lineage_checker_says_no_when_no_element_is_remote_at_all():
    """A one-sided estate satisfies 'every element is distinguishable'
    vacuously. The floor must refuse it."""
    ctx = _ctx()
    for probe in ctx.element_probes.values():
        probe["peer"] = 0
        probe["local"] = max(probe["local"], 1)
    assert set(ctx.element_origin.values()) == {"local"}
    ok, detail = syndicate.lineage_is_separable(ctx)
    assert not ok, f"passed with nothing remote to separate: {detail}"


def test_lineage_checker_says_no_when_a_peer_identifier_sits_in_a_local_row():
    """The content half. A peer position id planted in a local row that
    does NOT declare the claim remote must be caught. Planted in the
    in-memory snapshot, never written to any store."""
    ctx = _ctx()
    peer_id = sorted(ctx.peer_identifiers)[0]
    ctx.local_identifier_hits.append(
        {"store": "postgres", "location": "ccf_v2.own_position",
         "identifier": peer_id, "declares_remote": False})
    ok, detail = syndicate.lineage_is_separable(ctx)
    assert not ok, f"passed with {peer_id} sitting in a local row: {detail}"


# =========================================================================
# Task 16 fix round 1 -- the pure helpers, and the branches nothing could
# make say "no"
#
# The section comment at validators/syndicate.py's "Pure helpers -- no store
# access, exercised from validators/test_syndicate.py" was not true when it
# shipped: nothing called any of them. It is true below.
# =========================================================================

def test_local_name_takes_the_last_path_segment():
    assert syndicate.local_name(
        "http://example.org/fibo/member/SYNM-1f7eb72c") == "SYNM-1f7eb72c"
    assert syndicate.local_name("SYNM-1f7eb72c") == "SYNM-1f7eb72c"


def test_parse_citation_splits_a_real_citation_and_refuses_a_shapeless_one():
    doc, start, end = syndicate.parse_citation("x.htm#offset=565285-565297")
    assert (doc, start, end) == ("x.htm", 565285, 565297)
    with pytest.raises(ValueError):
        syndicate.parse_citation("x.htm")


def test_scope_sets_compares_terms_not_sizes():
    """`{a, b}` and `{a, c}` are the same SIZE and are not the same terms.
    A size comparison would call that pair symmetric."""
    a, b = syndicate.scope_sets({"request": {"a", "b"}, "disclose": {"a", "c"}})
    assert a != b and len(a) == len(b)


# --- numeric_values: the matcher precision_is_mixed now turns on ---------

@pytest.mark.parametrize("written", [
    "70000000",
    "70000000.00",
    "70,000,000",
    "$70,000,000.00",
    "7.0E7",
    "USD 70,000,000.00 committed",
    "PPOS-70000000AB",
])
def test_numeric_values_finds_every_representation_of_the_concealed_figure(
        written):
    """The bug this replaced: `str(70000000) in value` finds the first two
    and misses the rest, so an absence scan reports green forever with the
    figure in plain sight. Each representation must normalise to the same
    float."""
    assert 70_000_000.0 in syndicate.numeric_values(written), written


@pytest.mark.parametrize("written", [
    "170000000",          # a longer run is a different number
    "700000000",
    "7000000",
    "7,000,000",
    "no figure here",
    "",
])
def test_numeric_values_does_not_invent_the_concealed_figure(written):
    """The other direction. A matcher that said yes to everything would
    make `precision_is_mixed` fail permanently instead of pass
    permanently -- equally useless, and it must be shown not to."""
    assert 70_000_000.0 not in syndicate.numeric_values(written), written


# --- declares_remote: four conditions, each dropped independently --------
#
# This is the file's ONLY stored-marker path and `lineage_is_separable`
# PASSes because it excuses the estate's one local hit. Drop any one of its
# four conditions and the excuse silently widens. Nothing called it before
# fix round 1 -- the leak test hardcoded `declares_remote: False` rather
# than asking the function.

_PEER_IDS = {"PDEC-14A62D69A5", "PPOS-72ADD2D847"}

_GOOD_ROW = {
    "subject_kind": "federation_attestation",
    "subject_key": "PDEC-14A62D69A5",
    "reason": ("peer product declaration PDEC-14A62D69A5 is unattested -- "
               "federation attestation absent on the co-lender fabric"),
}


def test_declares_remote_excuses_the_row_the_estate_actually_has():
    from ccf.config import PG_SCHEMA_V2 as _S
    assert syndicate.declares_remote(
        "postgres", f"{_S}.context_debt", dict(_GOOD_ROW), _PEER_IDS)


@pytest.mark.parametrize("field,value", [
    ("subject_kind", "rating_action"),      # right table, wrong kind
    ("subject_key", "PDEC-NOT-ON-THE-PEER"),  # kind right, id not the peer's
    ("reason", "an unattested claim, source unstated"),  # says nothing remote
])
def test_declares_remote_refuses_when_any_one_condition_is_dropped(field, value):
    from ccf.config import PG_SCHEMA_V2 as _S
    row = dict(_GOOD_ROW)
    row[field] = value
    assert not syndicate.declares_remote(
        "postgres", f"{_S}.context_debt", row, _PEER_IDS), (
        f"the excuse survived dropping {field}")


@pytest.mark.parametrize("store,location", [
    ("postgres", "ccf_v2.own_position"),   # right store, wrong table
    ("fluree", "ccf_v2.context_debt"),     # right table name, wrong store
    ("sqlite", "context_debt"),
])
def test_declares_remote_refuses_outside_context_debt(store, location):
    """A peer identifier in a Fluree literal or a SQLite row has no
    Context Debt row behind it, whatever it is sitting next to."""
    assert not syndicate.declares_remote(
        store, location, dict(_GOOD_ROW), _PEER_IDS)


def test_declares_remote_refuses_a_missing_reason():
    from ccf.config import PG_SCHEMA_V2 as _S
    row = dict(_GOOD_ROW, reason=None)
    assert not syndicate.declares_remote(
        "postgres", f"{_S}.context_debt", row, _PEER_IDS)


# --- precision_is_mixed: the three branches nothing could falsify --------

def test_precision_checker_says_no_when_the_band_is_degenerate():
    """A band whose bounds meet is an exact figure wearing a costume."""
    ctx = _ctx()
    for row in ctx.peer_positions:
        if row["share_usd"] is None:
            row["band_high"] = row["band_low"]
    ok, detail = syndicate.precision_is_mixed(ctx)
    assert not ok, f"passed on a degenerate band: {detail}"
    assert "degenerate" in detail, detail


def test_precision_checker_says_no_when_the_band_misses_the_filed_figure():
    """A band that does not contain the position is a false disclosure,
    not a coarse one."""
    ctx = _ctx()
    for row in ctx.peer_positions:
        if row["share_usd"] is None:
            row["band_low"], row["band_high"] = 1, 2
    ok, detail = syndicate.precision_is_mixed(ctx)
    assert not ok, f"passed on a band that excludes the filed figure: {detail}"
    assert "does not contain the filed figure" in detail, detail


@pytest.mark.parametrize("written", [
    "70000000", "70,000,000", "$70,000,000.00", "7.0E7",
])
def test_precision_checker_says_no_when_the_figure_leaks_in_any_format(written):
    """**The branch that carries the T14-R1 claim, and the one nothing
    could make say "no" before fix round 1.** A cell holding the concealed
    figure is planted into the in-memory snapshot -- never into any store --
    and the floor must find it in every representation a peer column could
    cast it to. Under the old `str(figure) in value` matcher, three of these
    four planted needles were invisible.
    """
    ctx = _ctx()
    ctx.peer_fabric_cells.append(("peer_position.desk_note", written))
    ok, detail = syndicate.precision_is_mixed(ctx)
    assert not ok, f"the planted needle {written!r} was not found: {detail}"
    assert "appears on the peer fabric" in detail, detail


def test_the_planted_needle_never_reached_the_peer_fabric():
    """The estate is confirmed restored by a NAMED VALUE, not by a count.
    The test above plants `$70,000,000.00` into a deep copy; a fresh
    snapshot must still say the figure is absent from all 99 real peer
    cells, and the floor must still pass."""
    ctx = _ctx()
    hits = [where for where, value in ctx.peer_fabric_cells
            if 70_000_000.0 in syndicate.numeric_values(value)]
    assert not hits, f"70,000,000 is on the real peer fabric at {hits}"
    ok, detail = syndicate.precision_is_mixed(ctx)
    assert ok, detail


def test_precision_checker_says_no_when_its_positive_control_goes_blind():
    """The `CONTROL_NEEDLES` discipline, on this arm. Empty the cells the
    scan searches while leaving `peer_scan_shape` claiming 99 of them --
    exactly what a scan pointed at the wrong place looks like from the
    inside. The old code reported a clean absence; it must now fail."""
    ctx = _ctx()
    ctx.peer_fabric_cells = []
    assert ctx.peer_scan_shape["cells"] > 0, (
        "this test must leave the shape claiming cells, or it exercises the "
        "empty-haystack guard instead of the control")
    ok, detail = syndicate.precision_is_mixed(ctx)
    assert not ok, f"passed with the scan looking at nothing: {detail}"
    assert "control value(s)" in detail, detail


# --- federation_bounds_bind: the undebted branch -------------------------

def test_federation_checker_says_no_when_the_unattested_claim_is_undebted():
    """The only sub-condition on this arm that reaches into OUR Postgres,
    and the one with no mutation before fix round 1. An unattested claim
    nobody recorded is a gap, not Context Debt."""
    ctx = _ctx()
    ctx.context_debt_federation_keys = set()
    ok, detail = syndicate.federation_bounds_bind(ctx)
    assert not ok, f"passed with no context_debt row behind it: {detail}"
    assert "context_debt" in detail, detail


# --- lineage_is_separable: the derived population ------------------------

def test_the_element_population_is_derived_from_both_fabrics():
    """Ruling T16-R2. The population must come from the estate, not from a
    list in the module: every base table in either Postgres schema, and
    every subject on either ledger. Checked by counting each side
    independently against the stores."""
    from ccf.config import (pg_connect, PG_SCHEMA_V2 as _S,
                            CO_LENDER_PG_SCHEMA as _PS)
    ctx = _ctx()

    with pg_connect() as c, c.cursor() as cur:
        cur.execute("SELECT table_name FROM information_schema.tables WHERE "
                    "table_schema = %s AND table_type = 'BASE TABLE'", (_S,))
        ours = {r[0] for r in cur.fetchall()}
    theirs = {r[0] for r in _peer(
        "SELECT table_name FROM information_schema.tables WHERE "
        "table_schema = %s AND table_type = 'BASE TABLE'", (_PS,))}
    expected_pg = {f"{syndicate.PG_ELEMENT_PREFIX}{t}" for t in ours | theirs}

    from ccf import fluree as _fluree
    from ccf.config import (FLUREE_LEDGER_V2 as _L,
                            CO_LENDER_FLUREE_LEDGER as _PL)
    subjects = {b["s"]["value"] for b in _fluree.query(
        f"SELECT DISTINCT ?s FROM <{_L}> WHERE {{ ?s ?p ?o }}"
    )["results"]["bindings"]}
    subjects |= {b["s"]["value"] for b in _fluree.co_lender_query(
        f"SELECT DISTINCT ?s FROM <{_PL}> WHERE {{ ?s ?p ?o }}"
    )["results"]["bindings"]}
    expected_graph = {f"{syndicate.GRAPH_ELEMENT_PREFIX}{s}" for s in subjects}

    assert set(ctx.element_probes) == expected_pg | expected_graph, (
        "the probed population is not the derived one -- symmetric "
        f"difference: "
        f"{sorted(set(ctx.element_probes) ^ (expected_pg | expected_graph))[:5]}")
    assert len(expected_pg) > 100 and len(expected_graph) > 1000, (
        f"the derived population collapsed to {len(expected_pg)} table(s) "
        f"and {len(expected_graph)} subject(s) -- a population that small "
        f"would make this floor pass for free")


def test_the_element_population_is_not_a_hand_written_list():
    """A table nobody remembered to add must still be in the population.
    Proved by naming tables from OTHER waves -- nothing about Wave 18 would
    have put them in a hand-written list."""
    ctx = _ctx()
    for table in ("abs_loan_period", "sanctions_name", "fx_intraday_tick",
                  "psc_person"):
        assert f"{syndicate.PG_ELEMENT_PREFIX}{table}" in ctx.element_probes, (
            f"{table} is not in the probed population")


def test_lineage_checker_says_no_when_a_derived_element_answers_on_both():
    """Not the same test as the hand-picked one above it: this plants the
    collision on an element NOBODY listed -- a table from another wave --
    and requires the floor to catch it."""
    ctx = _ctx()
    name = f"{syndicate.PG_ELEMENT_PREFIX}sanctions_name"
    ctx.element_probes[name]["peer"] = 1
    assert ctx.element_origin[name] == "both"
    ok, detail = syndicate.lineage_is_separable(ctx)
    assert not ok, f"passed with {name} answering on both fabrics: {detail}"
    assert "sanctions_name" in detail, detail


# =========================================================================
# Task 16 fix round 2 -- the two shapes of "unresolved" (Ruling T16-R7)
#
# Both still FAIL the floor, deliberately: an element nobody can see is one
# the floor could never fail on. What must differ is the message, because a
# reader told only "unresolved" will hunt a separability defect that is not
# there.
#
# **These two are the whole pin, and that is deliberate (Ruling T16-R8).**
# Fix round 2 also added an estate-wide assertion that no element is
# currently `unresolved`, so the hazard would be caught one test earlier
# than floor 6. It was DROPPED in round 3, and the reason is worth having
# here so nobody adds it back:
#
#   * `unresolved` covers BOTH shapes. That assertion read `element_origin`
#     alone and never consulted `local_container` / `peer_container`, so on
#     the `absent` shape -- a genuine separability defect, the precise thing
#     floor 6 exists to catch -- its message told the reader it was the
#     benign unloaded table and pointed at known-issues §35. A claim
#     outliving the mechanism that would have to support it, in the round
#     that was fixing exactly that.
#   * Narrowing it means implementing floor 6's container split a SECOND
#     time, in a test, where the two copies can drift and the copy has no
#     guard of its own. More mechanism than the problem is worth.
#   * It adds nothing floor 6 does not already say; its only contribution
#     is firing earlier. And it turns the suite red for waves that have
#     done nothing wrong, which trains people to skim past red.
#
# The hazard stays recorded in `docs/known-issues.md` §35 -- a document the
# next wave reads, not a failing test it has to route around. The two tests
# below pin the BEHAVIOUR, each asserting the other's message is absent,
# which is the part that can silently rot.
# =========================================================================

def test_lineage_says_no_and_names_an_unloaded_table_as_such():
    """A base table that EXISTS in a schema and holds no rows. A normal
    estate state -- the next wave that creates a table before loading it
    will meet this -- and it must fail loudly while saying which case it
    is."""
    ctx = _ctx()
    name = f"{syndicate.PG_ELEMENT_PREFIX}sanctions_name"
    ctx.element_probes[name].update(local=0, peer=0,
                                    local_container=1, peer_container=0)
    assert ctx.element_origin[name] == "unresolved"
    ok, detail = syndicate.lineage_is_separable(ctx)
    assert not ok, f"passed with an element no fabric answers for: {detail}"
    assert "EXIST but hold no rows" in detail, detail
    assert "NEITHER fabric" not in detail, (
        f"an unloaded table was reported as absent from both fabrics: {detail}")


def test_lineage_says_no_and_names_a_genuinely_absent_element_as_such():
    """The other shape: no container on either side. Same verdict,
    different message -- and the two must not be confusable, or the
    distinction is decoration."""
    ctx = _ctx()
    name = f"{syndicate.PG_ELEMENT_PREFIX}sanctions_name"
    ctx.element_probes[name].update(local=0, peer=0,
                                    local_container=0, peer_container=0)
    assert ctx.element_origin[name] == "unresolved"
    ok, detail = syndicate.lineage_is_separable(ctx)
    assert not ok, f"passed with an element present on neither fabric: {detail}"
    assert "NEITHER fabric" in detail, detail
    assert "EXIST but hold no rows" not in detail, (
        f"an absent element was reported as an unloaded table: {detail}")


# =========================================================================
# Task 17 — the partition validator's fabric boundary, both directions
#
# `validators/partition.py` gained two checks this task: nothing peer-owned
# in our stores, and nothing of ours in the peer's. The second direction did
# not exist anywhere before, and a one-directional check sits green while the
# boundary leaks outward.
#
# So each arm gets an input that must make it say NO. Two checks in this repo
# hid defects for seven waves each because nothing ever fed them an input they
# should reject; an arm whose only demonstrated behaviour is silence has not
# been shown to distinguish anything.
# =========================================================================

def _wave18_result(name: str):
    from validators import partition

    return {r.check: r for r in partition.check_wave18()}[name]


def test_the_permitted_inward_crossing_is_exactly_one_row():
    """§D step 5 requires an unattested peer claim to be recorded as Context
    Debt, so `context_debt` legitimately NAMES a peer declaration id. That is
    the only inward crossing there is, and the exemption must not stretch.

    Fix round 1, Ruling T17-R1: the exemption is now ROW-scoped. It was
    column-scoped, and `_cell_scan` discards row identity, so a peer
    declaration id in ANY of `context_debt`'s 304 rows' `reason` was
    exempted while three documents described the one-row rule.
    """
    from validators.partition import (
        _debt_location, _is_permitted_debt_reference as ok,
        federation_debt_locations)

    # one federation_attestation row (4047) and one ordinary debt row (99)
    rows = {
        "4047": {"debt_id": 4047, "subject_kind": "federation_attestation",
                 "subject_key": "PDEC-14A62D69A5", "reason": "... co-lender ..."},
        "99": {"debt_id": 99, "subject_kind": "covenant",
               "subject_key": "ACC-1", "reason": "unrelated"},
    }
    permitted = federation_debt_locations(rows)
    declarations = {"PDEC-14A62D69A5", "PDEC-4BEB7CE1F8"}

    # the real crossing, in each of its two columns
    assert ok(f"PDEC-14A62D69A5 in {_debt_location('subject_key', 4047)}",
              permitted, declarations)
    assert ok(f"PDEC-14A62D69A5 in {_debt_location('reason', 4047)}",
              permitted, declarations)

    # THE CASE THE COLUMN-SCOPED VERSION EXEMPTED: same id, same column,
    # a DIFFERENT row -- one that is not a federation_attestation at all.
    assert not ok(f"PDEC-14A62D69A5 in {_debt_location('reason', 99)}",
                  permitted, declarations)
    # and the un-keyed location the old code accepted no longer matches
    assert not ok("PDEC-14A62D69A5 in pg context_debt.reason",
                  permitted, declarations)
    # a third column of the right row is still not exempt
    assert not ok(f"PDEC-14A62D69A5 in {_debt_location('recorded_at', 4047)}",
                  permitted, declarations)
    # the same id in any other table is a copy, not a debt record
    assert not ok("PDEC-14A62D69A5 in pg own_position.provenance",
                  permitted, declarations)
    # a peer POSITION id is never exempt, wherever it sits
    assert not ok(f"PPOS-5AD02CA9FA in {_debt_location('reason', 4047)}",
                  permitted, declarations)
    # a declaration nobody recorded debt against is not covered
    assert not ok(f"PDEC-4BEB7CE1F8 in {_debt_location('reason', 4047)}",
                  permitted, declarations)
    # a malformed hit with no " in " separator must not crash into a True
    assert not ok("PDEC-14A62D69A5", permitted, declarations)


def test_federation_debt_locations_only_covers_federation_rows():
    """The row-scoping is only as good as the map it is built from."""
    from validators.partition import _debt_location, federation_debt_locations

    rows = {
        "1": {"debt_id": 1, "subject_kind": "federation_attestation",
              "subject_key": "PDEC-A"},
        "2": {"debt_id": 2, "subject_kind": "person", "subject_key": "PDEC-B"},
        "3": {"debt_id": 3, "subject_kind": None, "subject_key": None},
    }
    permitted = federation_debt_locations(rows)
    assert set(permitted) == {_debt_location("reason", 1),
                              _debt_location("subject_key", 1)}
    assert permitted[_debt_location("reason", 1)] == "PDEC-A"


def test_the_two_definitions_of_the_crossing_are_intersected_not_unioned():
    """Ruling T17-R2. `validators/syndicate.py::declares_remote` decides the
    same question for floor 6 and disagrees in BOTH directions. The partition
    exemption requires both, so it can only ever be narrower than either.

    This pins the disagreement itself: a row `_is_permitted_debt_reference`
    would exempt and `declares_remote` would not (its reason never names the
    co-lender fabric), and a needle `declares_remote` would excuse and
    `_is_permitted_debt_reference` would not (a peer position id).
    """
    from validators import syndicate
    from validators.partition import (
        PG_SCHEMA_V2, _debt_location, _is_permitted_debt_reference,
        federation_debt_locations)

    location = f"{PG_SCHEMA_V2}.context_debt"
    peer_ids = {"PDEC-A", "PPOS-A"}

    silent = {"debt_id": 1, "subject_kind": "federation_attestation",
              "subject_key": "PDEC-A", "reason": "unattested claim recorded"}
    permitted = federation_debt_locations({"1": silent})
    hit = f"PDEC-A in {_debt_location('reason', 1)}"
    assert _is_permitted_debt_reference(hit, permitted, {"PDEC-A"}), (
        "the partition predicate should exempt this row on its own")
    assert not syndicate.declares_remote("postgres", location, silent,
                                         peer_ids), (
        "declares_remote requires the reason to name the co-lender fabric")

    spoken = dict(silent, subject_key="PPOS-A",
                  reason="read from the co-lender fabric")
    assert syndicate.declares_remote("postgres", location, spoken, peer_ids), (
        "declares_remote admits any peer identifier, position ids included")
    permitted2 = federation_debt_locations({"1": spoken})
    assert not _is_permitted_debt_reference(
        f"PPOS-A in {_debt_location('reason', 1)}", permitted2, {"PDEC-A"}), (
        "the partition predicate admits declarations only")


def test_a_peer_id_planted_in_an_ORDINARY_debt_row_makes_the_arm_go_red():
    """Ruling T17-R1's required proof, against the LIVE estate.

    The column-scoped version exempted this. Plants a real peer declaration
    id into the `reason` of a `context_debt` row that is NOT a
    `federation_attestation`, asserts the arm goes RED and names the row,
    then restores the row and confirms the restoration by reading the named
    original value back -- never by a row count, which cannot see a field
    being reset (this repo has that failure recorded).
    """
    from validators import partition
    from validators.partition import _debt_location
    from ccf.config import PG_SCHEMA_V2, pg_connect

    assert _wave18_result("no peer element in our stores").passed

    peer_ids, _declared = partition._peer_identifiers()
    needle = sorted(i for i in peer_ids if i.startswith("PDEC-"))[0]

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT debt_id, reason FROM "{PG_SCHEMA_V2}".context_debt '
                    f"WHERE subject_kind IS DISTINCT FROM "
                    f"'federation_attestation' AND reason IS NOT NULL "
                    f"ORDER BY debt_id LIMIT 1")
        victim = cur.fetchone()
    assert victim, "no ordinary context_debt row to plant into"
    debt_id, original = victim
    assert needle not in original

    try:
        with pg_connect() as conn, conn.cursor() as cur:
            cur.execute(f'UPDATE "{PG_SCHEMA_V2}".context_debt SET reason = %s '
                        f"WHERE debt_id = %s",
                        (f"{original} [PLANTED {needle}]", debt_id))
            conn.commit()
        result = _wave18_result("no peer element in our stores")
        assert not result.passed, (
            "a peer declaration id in an ORDINARY debt row was exempted: "
            f"{result.detail}")
        assert "LEAK INWARD" in result.detail
        assert _debt_location("reason", debt_id) in result.detail, result.detail
    finally:
        with pg_connect() as conn, conn.cursor() as cur:
            cur.execute(f'UPDATE "{PG_SCHEMA_V2}".context_debt SET reason = %s '
                        f"WHERE debt_id = %s", (original, debt_id))
            conn.commit()

    # restoration confirmed by the NAMED value, not by a count
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT reason FROM "{PG_SCHEMA_V2}".context_debt '
                    f"WHERE debt_id = %s", (debt_id,))
        restored = cur.fetchone()[0]
    assert restored == original, "the estate was not restored"
    assert needle not in restored
    assert _wave18_result("no peer element in our stores").passed, (
        "the arm did not return to green after restoration")


def test_the_inward_arm_says_no_when_a_peer_identifier_is_in_our_cells(
        monkeypatch):
    """ARM 1. Substituting a needle that IS in our Wave 18 cells for the
    peer's real identifiers is the same scan meeting a real leak."""
    from validators import partition

    assert _wave18_result("no peer element in our stores").passed

    monkeypatch.setattr(partition, "_peer_identifiers",
                        lambda: ({"SYNM-93bb6092"}, {}))
    result = _wave18_result("no peer element in our stores")
    assert not result.passed, result.detail
    assert "LEAK INWARD" in result.detail
    assert "SYNM-93bb6092" in result.detail


def test_the_inward_arm_says_no_when_its_positive_control_goes_blind(
        monkeypatch):
    """A green ABSENCE is the one kind of answer that can be permanently
    wrong with nothing looking broken. Hand the scan no cells and it must
    report that its silence proves nothing, rather than reporting clean."""
    from validators import partition

    monkeypatch.setattr(partition, "_our_wave18_cells", list)
    result = _wave18_result("no peer element in our stores")
    assert not result.passed, result.detail
    assert "POSITIVE CONTROL FAILED" in result.detail


def test_the_outward_arm_says_no_when_one_of_ours_is_in_a_peer_cell(
        monkeypatch):
    """ARM 2, the direction nothing checked before this task."""
    from validators import partition

    assert _wave18_result("no element of ours in the peer").passed

    monkeypatch.setattr(partition, "_our_wave18_identifiers",
                        lambda: {"PPOS-5AD02CA9FA"})
    result = _wave18_result("no element of ours in the peer")
    assert not result.passed, result.detail
    assert "LEAK OUTWARD" in result.detail


def test_the_outward_arm_says_no_when_the_peer_holds_a_table_we_did_not_expect(
        monkeypatch):
    """The misdirected-DDL case: the peer's database differs from ours by
    NAME ALONE, on the same host and port, so a loader pointed at the wrong
    one succeeds and looks like a successful load."""
    from validators import partition

    monkeypatch.setattr(partition, "PEER_TABLES", ["peer_position"])
    result = _wave18_result("no element of ours in the peer")
    assert not result.passed, result.detail
    assert "peer_product_declaration" in result.detail


def test_the_outward_arm_says_no_when_its_positive_control_goes_blind(
        monkeypatch):
    """§C declares `facility_id` a correlation key and the peer really does
    hold ours. The scan proving it can SEE that permitted crossing is what
    licenses its silence about the forbidden ones."""
    from validators import partition

    monkeypatch.setattr(partition, "_cell_scan", lambda cells, needles: [])
    result = _wave18_result("no element of ours in the peer")
    assert not result.passed, result.detail
    assert "POSITIVE CONTROL FAILED" in result.detail


def test_the_member_node_allowlist_is_an_allowlist(monkeypatch):
    """W18-3 is deliberately an allowlist, not a denylist: the generic P1
    scan can only see a leak whose name somebody already added to
    POSTGRES_OWNED_ATTRS."""
    from validators import partition

    assert _wave18_result("member node carries identity only").passed

    monkeypatch.setattr(
        partition, "WAVE18_MEMBER_NODE_PREDICATES",
        [p for p in partition.WAVE18_MEMBER_NODE_PREDICATES
         if not p.endswith("lei")])
    result = _wave18_result("member node carries identity only")
    assert not result.passed, result.detail
    assert "ex:lei" in result.detail


def test_the_syndicate_member_column_pin_fails_on_any_new_column(monkeypatch):
    """W18-1 pins the column SET rather than denying names, because the risk
    is a commitment mirrored in under a name no denylist anticipated."""
    from validators import partition

    assert _wave18_result("syndicate_member identity only").passed

    monkeypatch.setattr(
        partition, "WAVE18_SYNDICATE_MEMBER_COLUMNS",
        partition.WAVE18_SYNDICATE_MEMBER_COLUMNS - {"rssd"})
    result = _wave18_result("syndicate_member identity only")
    assert not result.passed, result.detail
    assert "UNPINNED" in result.detail


# -------------------------------------------------------------------------
# Fix round 1, IMPORTANT 5 — the six sub-conditions that were falsified by
# hand at Task 17 close and had no committed test. Every one of them is a
# check whose only demonstrated behaviour would otherwise be silence, which
# is this repo's own recorded defect class; these are the checks the next
# wave inherits and trusts.
# -------------------------------------------------------------------------

def test_w18_2_says_no_when_a_fluree_owned_name_is_a_wave18_column(monkeypatch):
    """W18-2. Declaring `member_id` Fluree-owned stands in for a real mirror
    -- `own_position.vote_posture`, say -- without writing to the store."""
    from validators import partition

    assert _wave18_result("no Fluree-owned syndicate column").passed

    monkeypatch.setattr(partition, "WAVE18_FLUREE_ONLY_COLUMNS",
                        [*partition.WAVE18_FLUREE_ONLY_COLUMNS, "member_id"])
    result = _wave18_result("no Fluree-owned syndicate column")
    assert not result.passed, result.detail
    assert "MIRRORED" in result.detail
    assert "syndicate_member.member_id" in result.detail


def test_w18_4_says_no_when_the_desk_tracker_is_absent(monkeypatch, tmp_path):
    """W18-4, presence half: the departmental element must actually BE in
    the departmental store, not merely be absent from the others."""
    import sqlite3

    from validators import partition

    assert _wave18_result("desk tracker is SQLite's alone").passed

    empty = tmp_path / "empty.sqlite"
    sqlite3.connect(empty).close()
    monkeypatch.setattr(partition, "SQLITE_PATH", empty)
    result = _wave18_result("desk tracker is SQLite's alone")
    assert not result.passed, result.detail
    assert "absent or empty" in result.detail


def test_w18_4_says_no_when_the_tracker_is_duplicated_into_postgres(
        monkeypatch):
    """W18-4, duplication half, and the half Ruling T13-R1 is about: the
    check hunts the tracker's COLUMN names schema-wide, not only its table
    name, because a copy of the desk note under any other table name passes
    a name check silently.

    Falsified by pointing the column list at `member_id`, which Postgres
    really holds on two tables -- the same shape as `desk_note` appearing on
    a table nobody thought to look at."""
    from validators import partition

    assert _wave18_result("desk tracker is SQLite's alone").passed

    monkeypatch.setattr(partition, "WAVE18_TRACKER_COLUMNS", ("member_id",))
    result = _wave18_result("desk tracker is SQLite's alone")
    assert not result.passed, result.detail
    assert "DUPLICATED" in result.detail
    assert "pg column on syndicate_member" in result.detail


def test_w18_4_says_no_when_the_tracker_table_name_appears_in_postgres(
        monkeypatch):
    """W18-4, table-name half. Naming a table Postgres holds as the tracker
    makes the arm report it as an enterprise-store duplicate."""
    from validators import partition

    monkeypatch.setattr(partition, "WAVE18_TRACKER_TABLE", "syndicate_member")
    result = _wave18_result("desk tracker is SQLite's alone")
    assert not result.passed, result.detail
    assert "pg table syndicate_member" in result.detail


def test_arm1_says_no_when_a_peer_table_name_exists_in_our_schema(monkeypatch):
    """ARM 1, peer-table sub-condition."""
    from validators import partition

    monkeypatch.setattr(partition, "PEER_TABLES", ["syndicate_member"])
    result = _wave18_result("no peer element in our stores")
    assert not result.passed, result.detail
    assert "peer table syndicate_member exists in ours" in result.detail


def test_arm1_says_no_when_a_peer_declared_predicate_is_on_our_ledger(
        monkeypatch):
    """ARM 1, peer-only-predicate sub-condition. `ex:commitmentUsd` is ours
    and is on 97 nodes, so declaring it peer-only is a real hit."""
    from validators import partition

    monkeypatch.setattr(partition, "PEER_ONLY_EX_PREDICATES",
                        [f"{partition.EX}commitmentUsd"])
    result = _wave18_result("no peer element in our stores")
    assert not result.passed, result.detail
    assert "ex:commitmentUsd" in result.detail
    assert "on our ledger" in result.detail


def test_arm1_says_no_when_peer_namespace_subjects_are_on_our_ledger(
        monkeypatch):
    """ARM 1, namespace sub-condition. Treating our own `ex:` prefix as the
    peer's makes every subject we hold a violation."""
    from validators import partition

    monkeypatch.setattr(partition, "PEER_URI_PREFIX", partition.EX)
    result = _wave18_result("no peer element in our stores")
    assert not result.passed, result.detail
    assert "peer-namespace subjects on our ledger" in result.detail


def test_arm2_says_no_when_a_subject_outside_the_peer_namespace_is_there(
        monkeypatch):
    """ARM 2, ledger-subject sub-condition -- the arm that would catch a
    node of ours loaded onto the peer's append-only ledger. Narrowing the
    namespace to one existing subject makes its sibling a stray."""
    from validators import partition

    subjects = partition.bindings(partition._peer_sparql(
        f"SELECT DISTINCT ?s FROM <{partition.CO_LENDER_FLUREE_LEDGER}> "
        f"WHERE {{ ?s ?p ?o }}"))
    assert len(subjects) >= 2, "need two peer subjects to narrow between"
    monkeypatch.setattr(partition, "PEER_URI_PREFIX",
                        subjects[0]["s"]["value"])
    result = _wave18_result("no element of ours in the peer")
    assert not result.passed, result.detail
    assert "on the peer ledger" in result.detail


def test_w18_4_says_no_when_the_tracker_name_appears_as_a_mongo_collection(
        monkeypatch):
    """W18-4, MongoDB half. Naming a collection `fibo_v2` really holds makes
    the arm report the departmental element as duplicated into the document
    store."""
    from validators import partition

    monkeypatch.setattr(partition, "WAVE18_TRACKER_TABLE", "document")
    result = _wave18_result("desk tracker is SQLite's alone")
    assert not result.passed, result.detail
    assert "mongo collection document" in result.detail


def test_arm1_says_no_when_a_peer_DECLARED_VALUE_rides_in_with_the_id():
    """ARM 1's compensating assertion — the one that makes the exemption a
    REFERENCE and not a COPY.

    The Context Debt row may NAME the peer's declaration. It may not carry
    what the peer declared. Plants the peer's own `declared_ttl_seconds` into
    that row's reason, asserts the arm goes RED naming the value, restores,
    and confirms the restoration by reading the named original back."""
    from validators import partition
    from ccf.config import PG_SCHEMA_V2, pg_connect

    assert _wave18_result("no peer element in our stores").passed

    _peer_ids, declared = partition._peer_identifiers()

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT debt_id, subject_key, reason '
                    f'FROM "{PG_SCHEMA_V2}".context_debt '
                    f"WHERE subject_kind = 'federation_attestation' "
                    f"ORDER BY debt_id LIMIT 1")
        row = cur.fetchone()
    assert row, "no federation_attestation Context Debt row to exercise"
    debt_id, subject_key, original = row
    values = sorted(v for v in declared.get(subject_key, set()) if v)
    assert values, f"the peer declares no TTL/latency for {subject_key}"
    value = values[0]
    assert value not in original, (
        "the row already carries a declared value — the check should not "
        "have been green")

    try:
        with pg_connect() as conn, conn.cursor() as cur:
            cur.execute(f'UPDATE "{PG_SCHEMA_V2}".context_debt SET reason = %s '
                        f"WHERE debt_id = %s",
                        (f"{original} declared ttl {value}", debt_id))
            conn.commit()
        result = _wave18_result("no peer element in our stores")
        assert not result.passed, (
            f"a declared value rode in with the identifier: {result.detail}")
        assert "the exemption covers the identifier, never the claim" \
            in result.detail, result.detail
        assert value in result.detail
    finally:
        with pg_connect() as conn, conn.cursor() as cur:
            cur.execute(f'UPDATE "{PG_SCHEMA_V2}".context_debt SET reason = %s '
                        f"WHERE debt_id = %s", (original, debt_id))
            conn.commit()

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT reason FROM "{PG_SCHEMA_V2}".context_debt '
                    f"WHERE debt_id = %s", (debt_id,))
        restored = cur.fetchone()[0]
    assert restored == original, "the estate was not restored"
    assert value not in restored
    assert _wave18_result("no peer element in our stores").passed, (
        "the arm did not return to green after restoration")


def test_the_arm_goes_red_if_declares_remote_stops_excusing_the_row(
        monkeypatch):
    """Ruling T17-R2's conjunction, falsified rather than asserted.

    `check_wave18` exempts the one §D step 5 crossing only if BOTH
    `_is_permitted_debt_reference` AND `validators/syndicate.py`'s
    `declares_remote()` say yes. Round 1 pinned the two rules' DISAGREEMENT
    on constructed rows, but nothing in the suite failed if the
    `declares_remote(...)` conjunct were deleted from `_exempt` -- both
    planting tests plant inputs the other predicate rejects too, and the
    intersection test never runs `check_wave18()`. That is verification by
    construction, which is the standard this round's Important 5 refused
    four times.

    `_exempt` resolves `declares_remote` through a function-level import on
    every call, so neutralising it needs no store write: the estate's real
    crossing must stop being exempt and the arm must go RED, naming those
    exact hits -- not red for some other reason.
    """
    from validators import partition, syndicate

    assert _wave18_result("no peer element in our stores").passed

    monkeypatch.setattr(syndicate, "declares_remote",
                        lambda *a, **k: False)
    result = _wave18_result("no peer element in our stores")
    assert not result.passed, (
        "the arm stayed green with declares_remote neutralised — the "
        f"conjunct is not load-bearing: {result.detail}")
    assert "LEAK INWARD" in result.detail, (
        f"red, but not for the reason under test: {result.detail}")

    # and it is the REAL crossing that is now unexcused, not something else
    debt_rows = partition._context_debt_rows()
    federation = [debt_id for debt_id, row in debt_rows.items()
                  if row.get("subject_kind") == "federation_attestation"]
    assert federation, "no federation_attestation row to be unexcused"
    for debt_id in federation:
        assert partition._debt_location("subject_key", debt_id) \
            in result.detail or \
            partition._debt_location("reason", debt_id) in result.detail, (
                f"the red names no hit on row {debt_id}: {result.detail}")


def test_the_arm_goes_red_if_the_partition_predicate_stops_excusing_the_row(
        monkeypatch):
    """The other half of the same conjunction. Neither rule alone carries
    the exemption: neutralise either and the estate's real crossing is
    reported."""
    from validators import partition

    monkeypatch.setattr(partition, "_is_permitted_debt_reference",
                        lambda *a, **k: False)
    result = _wave18_result("no peer element in our stores")
    assert not result.passed, (
        "the arm stayed green with the partition predicate neutralised: "
        f"{result.detail}")
    assert "LEAK INWARD" in result.detail, result.detail
