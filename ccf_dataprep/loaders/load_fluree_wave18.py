#!/usr/bin/env python3
"""Wave 18 Task 8 -- syndicate structure and commitment shares, into Fluree.
Extended by Task 9 (amendment events/vote), Task 10 (disclosure envelopes)
and Task 11b (`ex:AmendmentThreshold` nodes -- the R half of "Voting
thresholds and amendment mechanics", closing the gap Task 11's MongoDB-only
`L` half left open; see `build_thresholds()` and `ccf/syndicate.py`'s own
Task 11b section for the node-shape rationale).

Reads `sources/screening/wave18_schedules.json` (98 rows, Task 2) and
`sources/screening/wave18_institutions.json` (45 members, Task 3), plus
`ccf_v2.facility.administrative_agent` (read-only; Task 1 wrote it, Postgres
still owns it) to resolve each of the twelve selected facilities' agent.
Nothing here reads or writes Postgres beyond that one lookup.

`load_structure() -> dict` is the entry point Task 9 and 10 extend this
module against (per this task's brief) -- it runs the full load and
returns every count `main()` prints, as a plain dict. `main()` is a thin
wrapper over it for the CLI.

## The share lives on the edge, and nowhere else

§C assigns "syndicate composition -- lender names and commitments" to
Fluree as `R`. `docs/wave18-design.md` §5 is explicit that Postgres
deliberately does NOT hold the per-member commitment share -- an earlier
draft put it there "for convenience" and that is the single-writer
violation CLAUDE.md forbids. A plain triple cannot carry an amount *and* a
filing offset, so Task 4 bound `ex:SyndicateParticipation` as a reified
node (`ccf.syndicate.EX_SYNDICATE_PARTICIPATION`): one node per
(facility, member) pair, carrying `ex:commitmentUsd` and `ex:sourcePassage`,
linked to the member (`ex:participationOf`) and the facility
(`ex:participationIn`).

## `ex:sourcePassage` -- a document+offset citation, not a Mongo key

Wave 18's MongoDB passage extraction (Task 11/12) covers voting thresholds,
amendment mechanics and the assignment/transfer article -- not the
commitment-schedule text itself, and it runs after this task. There is no
Mongo passage row for a schedule figure to cite yet. `ex:sourcePassage`
here is instead a plain string citing the filed document and Task 2's own
character offsets verbatim: `"{document}#offset={offset}-{end}"` -- publicly
verifiable against the cached filing text right now, unlike a forward
reference to a document that does not exist. If Task 11/12 later mints a
real Mongo passage for this exact span, a future task can repoint this
string to that passage_id without changing what predicate it lives on.

## Node identity -- content-keyed, per the brief

    ex:syndicate/<facility_id>                     SyndicatedLoan
    ex:syndicate/agreement/<document>              FinanceSyndicate
    ex:member/<member_id>                          FinanceSyndicateMember
    ex:agent/AGENT-TCW                             AdministrativeAgent only (below)
    ex:participation/<facility_id>-<member_id>-<offset>   SyndicateParticipation

(The participation key is three-part, not two -- see "Idempotency" below for
why `offset` had to join it.)

`uri()` is bare `EX + local` (the same helper every Fluree loader since
Wave 9 uses); passing a `/`-separated local string is how Wave 17's own
`ex:` extension nodes already read as a path without changing the helper.

## Facility set -- 12, not 14 (Ruling T6-R2)

Every agreement's `facility_ids` list is filtered through
`ccf.syndicate.WAVE18_EXCLUDED_FACILITIES` (FAC-105FC5, FAC-DFCB72) before a
`SyndicatedLoan` node is minted for it. `ccf_v2.facility` itself is never
touched -- other products reference those two rows.

## The corrupt lender_raw -- no member, no edge

`"BarclaysFifth Third Bank PLC, National Association"` (one AHR row, Task
2/3) sits in `wave18_institutions.json`'s `manual_review`, not `members` --
two real institutions interleaved at word level by a redline artifact that
cannot be reconstructed. It resolves to no member_id and therefore gets no
participation edge; the loader counts and reports it rather than silently
dropping it.

## Administrative agents (Ruling T8-R1)

Every one of the 12 facilities' `ccf_v2.facility.administrative_agent`
string resolves, via `canonical_key()`, to one of three existing members
(Bank of America, JPMorgan, PNC) -- each of those, being ALSO a filed
lender, gets a SECOND `rdf:type` (`AdministrativeAgent`) on its EXISTING
member node, not a new one; there is no inference, so both types must be
asserted explicitly. The four Regis facilities' agent, `TCW`, is the
manager acting as agent, not a lender there -- the Regis lender list
carries a different entity, `TCW RESCUE FINANCING FUND II LP`
(`SYNM-6a54e6c8`, already a member with no participation edge to any TCW
facility in this wave's schedule data). TCW gets a new node, typed
`AdministrativeAgent` only (never `FinanceSyndicateMember` -- it is not a
lender on any Wave 18 facility) and no participation edge. Its real LEI --
`TCW Asset Management Company LLC`, 549300LFK257DF2RVN05 -- was resolved
against GLEIF's fulltext search and confirmed against the Regis filing's
own recital ("TCW ASSET MANAGEMENT COMPANY LLC, as Collateral Agent and as
Administrative Agent"), retrieved 2026-08-26.

## Provenance (Ruling T8-R2)

Every node this loader writes -- `SyndicatedLoan`, `FinanceSyndicate`,
`FinanceSyndicateMember`, both agent forms, and `SyndicateParticipation` --
carries `ex:provenance`. All of it derives from filed public documents (the
six EX-10 commitment schedules, GLEIF, FDIC BankFind) or from the members'
own filed identity, so every value is `"public"` -- CLAUDE.md's exact
three-class taxonomy, reusing the estate-wide `ex:provenance` predicate
already bound (Wave 11c) and used across every other Fluree loader, not a
new mint.

## Idempotency

Every subject and every literal here is deterministic from the frozen
artifacts (Task 2/3) plus the one Postgres agent-string lookup, which does
not change between runs, so a plain re-run against unchanged inputs would
already be idempotent under Fluree's set semantics alone (an `INSERT DATA`
of an already-asserted triple is a no-op) -- IF the subject scheme itself
never changes. It did, once, mid-development: the first version keyed a
participation node on `<facility_id>-<member_id>` alone, which collided
whenever one member had more than one filed row against the same facility
(RB Global rolls three separately-filed tranches into ONE combined Postgres
row; Sabre's Class B lists one insurer on two separate rows) -- multiple
`commitmentUsd`/`sourcePassage` pairs landed on one node with no way to
tell which amount matched which offset. `offset` joined the key to fix it
(see `participation_node()`), which means the OLD scheme's nodes are
orphaned garbage in the ledger from that first run, not superseded by the
new INSERT. So this loader retracts every triple on a subject under any of
its four own path prefixes (`ex:syndicate/*`, `ex:member/*`, `ex:agent/*`,
`ex:participation/*` -- confirmed, by grep, minted by no other loader in
this estate) before every run, unconditionally, rather than opt-in like
Wave 17's `--reconcile` -- cheap at this volume, and it is the only way a
subject-SCHEME change (not just a literal change) stays safe to re-run.
Verified by Step 5's before/after VALUE comparison, not trusted on the
set-semantics argument alone.

    uv run loaders/load_fluree_wave18.py
"""
from __future__ import annotations

import sys

import json

from ccf import fluree
from ccf.config import EX, FLUREE_LEDGER_V2, PG_SCHEMA_V2, REPO_ROOT, pg_connect
from ccf.syndicate import (
    CMNS_IS_MEMBER_OF,
    EX_ADMINISTERED_BY,
    EX_AMENDMENT_EVENT,
    EX_AMENDMENT_THRESHOLD,
    EX_AMENDMENT_TYPE,
    EX_AMENDMENT_VOTE,
    EX_AMENDS,
    EX_COMMITMENT_USD,
    EX_CONSENT_PERCENT,
    EX_CONSENT_STANDARD,
    EX_COUNTERPARTY,
    EX_DISCLOSE_SCOPE,
    EX_DISCLOSURE_ENVELOPE,
    EX_EFFECTIVE_DATE,
    EX_ENVELOPE_VERSION,
    EX_PARTICIPATION_IN,
    EX_PARTICIPATION_OF,
    EX_REQUEST_SCOPE,
    EX_SOURCE_PASSAGE,
    EX_SYNDICATE_PARTICIPATION,
    EX_THRESHOLD_GOVERNS,
    EX_VALID_FROM,
    EX_VOTE_POSTURE,
    EX_VOTE_STATE,
    EX_VOTES_ON,
    FIBO_ADMINISTRATIVE_AGENT,
    FIBO_FINANCE_SYNDICATE,
    FIBO_FINANCE_SYNDICATE_MEMBER,
    FIBO_SYNDICATED_LOAN,
    TRANCHE_TO_FACILITIES,
    WAVE18_EXCLUDED_FACILITIES,
)
from generators.resolve_syndicate_institutions import canonical_key
from loaders.load_collateral_wave9 import triple, uri

SCREEN = REPO_ROOT / "sources" / "screening"
SCHEDULES_PATH = SCREEN / "wave18_schedules.json"
INSTITUTIONS_PATH = SCREEN / "wave18_institutions.json"
INTERNAL_PATH = SCREEN / "wave18_internal.json"
ENVELOPES_PATH = SCREEN / "wave18_envelopes.json"
THRESHOLDS_PATH = SCREEN / "wave18_voting_thresholds.json"

RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"

#: Estate-wide predicate, bound Wave 11c and already used by every other
#: Fluree loader (e.g. `loaders/load_fluree_wave17.py`'s own P_PROVENANCE) --
#: reused here, not redeclared as a Wave 18 term. CLAUDE.md's three classes;
#: every node this loader writes is filing/registry-derived, so every value
#: here is exactly "public" (Ruling T8-R2).
EX_PROVENANCE = f"{EX}provenance"
PUBLIC = "public"
#: CLAUDE.md's exact three-class taxonomy, spaced em dash. Vote postures
#: and the vote itself are bank-internal, invented (Task 9).
SYNTHETIC_INTERNAL = "synthetic — internal"

BATCH = 400

#: TCW Asset Management Company LLC -- the manager acting as administrative
#: agent on the four Regis facilities, confirmed against GLEIF (fulltext
#: search on "TCW", retrieved 2026-08-26) and against the Regis credit
#: agreement's own recital naming it "Collateral Agent and ... Administrative
#: Agent". Not a Wave 18 lender -- see the module docstring -- so it has no
#: Task 3 member_id; "AGENT-TCW" is minted here, in the `ex:agent/` path
#: rather than `ex:member/`, precisely so it can never be mistaken for one.
TCW_AGENT_LOCAL_ID = "AGENT-TCW"
TCW_AGENT_LEI = "549300LFK257DF2RVN05"
TCW_AGENT_LABEL = "TCW Asset Management Company LLC"


def facility_node(facility_id: str) -> str:
    return uri(f"syndicate/{facility_id}")


def syndicate_node(document: str) -> str:
    return uri(f"syndicate/agreement/{document}")


def member_node(member_id: str) -> str:
    return uri(f"member/{member_id}")


def participation_node(facility_id: str, member_id: str, offset: int) -> str:
    """`<facility_id>-<member_id>` alone collides: RB Global rolls three
    separately-filed tranches (Revolving A/B/C) into the ONE combined
    Postgres facility FAC-A4A5EE, and Sabre's Class B schedule lists
    Massachusetts Mutual Life Insurance Company on two separate rows --
    both real, both distinct commitments from the SAME member to the SAME
    facility. Without a third key component every such pair's participation
    node ends up carrying MULTIPLE `commitmentUsd`/`sourcePassage` values
    with no way to tell which amount pairs with which offset -- exactly the
    ambiguity reification exists to prevent. `offset` is the row's own
    content (Task 2's parse), not a loop index, so this stays content-keyed,
    never positional."""
    return uri(f"participation/{facility_id}-{member_id}-{offset}")


def agent_node_local(local_id: str) -> str:
    return uri(f"agent/{local_id}")


def amendment_event_node(document: str) -> str:
    """Nested under `syndicate/` on purpose -- `OWNED_SUBJECT_PREFIXES`
    already covers `ex:syndicate/*`, so Task 9's new subjects are retracted
    and re-inserted by the SAME idempotency mechanism Task 8 built, with no
    change to that list required."""
    return uri(f"syndicate/amendment/{document}")


def vote_node(facility_id: str) -> str:
    return uri(f"syndicate/vote/{facility_id}")


def envelope_node(counterparty_member_id: str) -> str:
    """Nested under `syndicate/` on purpose, same reason Task 9's amendment
    nodes are (see `amendment_event_node`'s docstring) -- `OWNED_SUBJECT_
    PREFIXES` already covers `ex:syndicate/*`, so this new subject scheme
    is retracted and re-inserted by the same idempotency mechanism with no
    change to that list required."""
    return uri(f"syndicate/envelope/{counterparty_member_id}")


def threshold_node(document: str, bucket: str) -> str:
    """Task 11b. Nested under `syndicate/` for the same reason
    `amendment_event_node`/`vote_node`/`envelope_node` are -- `OWNED_SUBJECT_
    PREFIXES` already covers `ex:syndicate/*`, so this new subject scheme
    needs no change to the reconcile() prefix list. Content-keyed on
    (document, bucket): the document it was extracted from and the
    consent-standard bucket (`generators/extract_voting_thresholds.py`'s
    `bucket`, e.g. "required-lenders", "each-affected-lender") -- both are
    the row's own content, never a loop index, so a document with a fifth
    curated carve-out added later gets a new stable node, not a collision
    with an existing one."""
    return uri(f"syndicate/threshold/{document}/{bucket}")


# --- readers -----------------------------------------------------------------

def load_schedules() -> dict:
    return json.loads(SCHEDULES_PATH.read_text())


def load_institutions() -> dict:
    return json.loads(INSTITUTIONS_PATH.read_text())


def load_internal() -> dict:
    """Task 6/7/9's own bank-internal artifact -- `own_positions`,
    `competition_law_rule`, `syndicate_projection_plan` (Postgres-owned,
    untouched here) plus `amendment_events` and `amendment_vote`
    (Task 9's own, Fluree-owned)."""
    return json.loads(INTERNAL_PATH.read_text())


def load_envelopes() -> dict:
    """Task 10's own artifact -- `sources/screening/wave18_envelopes.json`,
    written by `generators/generate_disclosure_envelopes.py`."""
    return json.loads(ENVELOPES_PATH.read_text())


def load_thresholds() -> dict:
    """Task 11b's own artifact -- `sources/screening/wave18_voting_
    thresholds.json`, written by `generators/extract_voting_thresholds.py`."""
    return json.loads(THRESHOLDS_PATH.read_text())


def wave18_facility_ids(schedules: dict) -> list[str]:
    """Every facility_id across all six agreements, minus Ruling T6-R2's
    two exclusions. Deterministic order (sorted) so the node list is
    reproducible across runs.

    Loud assert on drift (whole-branch review fix): `loaders/
    load_sqlite_wave18.py::selected_facilities` derives this same 12-facility
    population independently, from Postgres `facility WHERE source_document
    = ANY(WAVE18_SOURCE_DOCS)`, and already fails loudly if its derivation
    disagrees with what it was written against. This side derives from
    `wave18_schedules.json`'s own `facility_ids` instead and, until now, had
    no equivalent guard -- a schedule artifact that silently grew or shrank
    a 13th/11th facility would have loaded without complaint."""
    ids: set[str] = set()
    for agreement in schedules["agreements"]:
        for fid in agreement["facility_ids"]:
            if fid not in WAVE18_EXCLUDED_FACILITIES:
                ids.add(fid)
    result = sorted(ids)
    assert len(result) == 12, (
        f"wave18_schedules.json's facility_ids, minus Ruling T6-R2's two "
        f"exclusions, now derive {len(result)} facilities, not the 12 this "
        f"loader (and the SQLite desk tracker) were written against: "
        f"{result}")
    return result


def build_raw_to_member(institutions: dict) -> dict[str, dict]:
    """Every raw lender string Task 3 resolved -> that member's own dict.
    The one corrupt string is deliberately absent (it lives in
    manual_review, never in members' raw_names)."""
    out: dict[str, dict] = {}
    for m in institutions["members"]:
        for raw in m["raw_names"]:
            out[raw] = m
    return out


def resolve_agents(facility_ids: list[str],
                    raw_to_member: dict[str, dict]) -> dict[str, dict]:
    """facility_id -> {"member": <member dict> or None, "is_tcw": bool}.

    Reads `ccf_v2.facility.administrative_agent` (Postgres-owned, read-only
    here) and resolves each string via `canonical_key()` against every
    member's own `legal_name` -- the same normalisation Task 3 already used
    to collapse name variants, reused rather than re-implemented. A string
    that resolves to no member is asserted to be exactly "TCW" (Ruling
    T8-R1); anything else failing to resolve is a loud error, not a silent
    skip -- §C makes administrative agent identity a required public
    element.
    """
    # keyed by canonical_key(legal_name); raw_to_member has one entry per
    # raw NAME (several can point at the same member), so build this from
    # scratch rather than iterating raw_to_member.values() with duplicates
    member_by_key: dict[str, dict] = {}
    for m in raw_to_member.values():
        member_by_key.setdefault(canonical_key(m["legal_name"]), m)

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(
            f'SELECT facility_id, administrative_agent FROM '
            f'"{PG_SCHEMA_V2}".facility WHERE facility_id = ANY(%s)',
            (facility_ids,),
        )
        agent_strings = dict(cur.fetchall())

    out: dict[str, dict] = {}
    for fid in facility_ids:
        raw_agent = agent_strings.get(fid)
        assert raw_agent, (
            f"{fid}: no administrative_agent recorded in ccf_v2.facility -- "
            f"§C requires this element for every Wave 18 facility")
        key = canonical_key(raw_agent)
        member = member_by_key.get(key)
        if member is None:
            assert raw_agent.strip().upper() == "TCW", (
                f"{fid}: administrative_agent {raw_agent!r} resolves to no "
                f"existing member and is not the known TCW exception "
                f"(Ruling T8-R1) -- refusing to invent or silently drop "
                f"this agent")
            out[fid] = {"member": None, "is_tcw": True}
        else:
            out[fid] = {"member": member, "is_tcw": False}
    return out


# --- build ---------------------------------------------------------------

def build(schedules: dict, institutions: dict
          ) -> tuple[list[str], dict, dict[str, set[str]]]:
    triples: list[str] = []
    stats = {
        "syndicated_loan_nodes": 0,
        "syndicate_nodes": 0,
        "member_nodes": 0,
        "agent_only_nodes": 0,
        "dual_typed_members": 0,
        "administered_by_edges": 0,
        "is_member_of_edges": 0,
        "participation_nodes": 0,
        "commitment_edges": 0,
        "rows_total": 0,
        "rows_to_manual_review": 0,
        "rows_resolved": 0,
    }

    facility_ids = wave18_facility_ids(schedules)
    raw_to_member = build_raw_to_member(institutions)
    manual_review_raws = {r["lender_raw"] for r in institutions["manual_review"]}
    agents = resolve_agents(facility_ids, raw_to_member)

    # --- SyndicatedLoan nodes, one per selected facility -----------------
    for fid in facility_ids:
        node = facility_node(fid)
        triples += [
            triple(node, RDF_TYPE, FIBO_SYNDICATED_LOAN),
            triple(node, RDFS_LABEL, f"Syndicated loan {fid}", literal=True),
            triple(node, EX_PROVENANCE, PUBLIC, literal=True),
        ]
        stats["syndicated_loan_nodes"] += 1

    # --- FinanceSyndicate nodes, one per agreement with >=1 selected
    #     facility -----------------------------------------------------
    doc_has_facility: dict[str, bool] = {}
    for agreement in schedules["agreements"]:
        doc = agreement["document"]
        kept = [f for f in agreement["facility_ids"] if f not in
                WAVE18_EXCLUDED_FACILITIES]
        doc_has_facility[doc] = bool(kept)
        if kept:
            node = syndicate_node(doc)
            triples += [
                triple(node, RDF_TYPE, FIBO_FINANCE_SYNDICATE),
                triple(node, RDFS_LABEL, f"Syndicate for {doc}", literal=True),
                triple(node, EX_PROVENANCE, PUBLIC, literal=True),
            ]
            stats["syndicate_nodes"] += 1

    # --- FinanceSyndicateMember nodes, one per Task 3 institution --------
    # lei + label + type + provenance -- nothing else per the node-
    # discipline rule (provenance added by Ruling T8-R2; it is not a
    # Postgres-owned attribute, so it does not violate single-writer).
    member_uri_by_id: dict[str, str] = {}
    for m in institutions["members"]:
        node = member_node(m["member_id"])
        member_uri_by_id[m["member_id"]] = node
        triples.append(triple(node, RDF_TYPE, FIBO_FINANCE_SYNDICATE_MEMBER))
        triples.append(triple(node, RDFS_LABEL, m["legal_name"], literal=True))
        triples.append(triple(node, EX_PROVENANCE, PUBLIC, literal=True))
        if m["lei"]:
            triples.append(triple(node, f"{EX}lei", m["lei"], literal=True))
        stats["member_nodes"] += 1

    # --- Administrative agent edges + dual typing / TCW-only node -------
    # `dual_typed_members` counts UNIQUE members (a member can be the agent
    # on more than one facility -- BofA on all 4 of RB Global + AHR -- and
    # must not be counted once per facility it administers).
    agent_uri_by_fid: dict[str, str] = {}
    dual_typed_member_ids: set[str] = set()
    tcw_node = agent_node_local(TCW_AGENT_LOCAL_ID)
    tcw_emitted = False
    for fid in facility_ids:
        info = agents[fid]
        if info["is_tcw"]:
            agent_uri_by_fid[fid] = tcw_node
            if not tcw_emitted:
                triples += [
                    triple(tcw_node, RDF_TYPE, FIBO_ADMINISTRATIVE_AGENT),
                    triple(tcw_node, RDFS_LABEL, TCW_AGENT_LABEL, literal=True),
                    triple(tcw_node, f"{EX}lei", TCW_AGENT_LEI, literal=True),
                    triple(tcw_node, EX_PROVENANCE, PUBLIC, literal=True),
                ]
                stats["agent_only_nodes"] += 1
                tcw_emitted = True
        else:
            member = info["member"]
            node = member_uri_by_id[member["member_id"]]
            agent_uri_by_fid[fid] = node
            triples.append(triple(node, RDF_TYPE, FIBO_ADMINISTRATIVE_AGENT))
            dual_typed_member_ids.add(member["member_id"])
        triples.append(triple(facility_node(fid), EX_ADMINISTERED_BY,
                               agent_uri_by_fid[fid]))
        stats["administered_by_edges"] += 1
    stats["dual_typed_members"] = len(dual_typed_member_ids)

    # --- Schedule rows -> participation nodes + isMemberOf --------------
    is_member_of_pairs: set[tuple[str, str]] = set()
    group_position: dict[tuple[str, str, int, int], int] = {}
    #: facility_id -> set(member_id) actually holding a participation node
    #: on it -- built from the SAME rows that mint the participation
    #: triples below, so Task 9's voter-eligibility check (build_vote())
    #: can assert against this rather than re-deriving it a second,
    #: possibly-drifting way.
    facility_members: dict[str, set[str]] = {}

    for agreement in schedules["agreements"]:
        doc = agreement["document"]
        if not doc_has_facility[doc]:
            continue
        syn_node = syndicate_node(doc)
        tranche_map = TRANCHE_TO_FACILITIES.get(doc)
        assert tranche_map is not None, (
            f"{doc}: no entry in ccf.syndicate.TRANCHE_TO_FACILITIES -- "
            f"refusing to guess which facility its rows belong to")

        for row in agreement["rows"]:
            stats["rows_total"] += 1
            lender_raw = row["lender_raw"]

            if lender_raw in manual_review_raws:
                stats["rows_to_manual_review"] += 1
                continue

            member = raw_to_member.get(lender_raw)
            assert member is not None, (
                f"{doc}: lender_raw {lender_raw!r} resolves to no member "
                f"and is not in manual_review -- a schedule row must be "
                f"one or the other")

            tranche = row["tranche"]
            candidates = tranche_map.get(tranche)
            assert candidates, (
                f"{doc}: tranche {tranche!r} has no facility mapping in "
                f"TRANCHE_TO_FACILITIES -- a silently unmapped tranche "
                f"attaches this share to nothing")

            key = (lender_raw, row["offset"], row["end"])
            pos = group_position.get(key, 0)
            group_position[key] = pos + 1
            assert pos < len(candidates), (
                f"{doc}: {lender_raw!r} at offset {row['offset']} has more "
                f"occurrences ({pos + 1}) than TRANCHE_TO_FACILITIES has "
                f"facilities for tranche {tranche!r} ({candidates}) -- "
                f"positional split is ambiguous")
            facility_id = candidates[pos]
            if facility_id in WAVE18_EXCLUDED_FACILITIES:
                # Not reachable today (no excluded facility_id appears in
                # any tranche_map value), but a real error if it ever were.
                raise SystemExit(
                    f"{doc}: TRANCHE_TO_FACILITIES routes a row to "
                    f"{facility_id}, excluded by Ruling T6-R2")

            member_node_uri = member_uri_by_id[member["member_id"]]
            fac_node = facility_node(facility_id)
            part_node = participation_node(facility_id, member["member_id"],
                                            row["offset"])
            source_passage = f"{doc}#offset={row['offset']}-{row['end']}"

            triples += [
                triple(part_node, RDF_TYPE, EX_SYNDICATE_PARTICIPATION),
                triple(part_node, EX_PARTICIPATION_OF, member_node_uri),
                triple(part_node, EX_PARTICIPATION_IN, fac_node),
                triple(part_node, EX_COMMITMENT_USD, str(row["amount_usd"]),
                       literal=True),
                triple(part_node, EX_SOURCE_PASSAGE, source_passage,
                       literal=True),
                triple(part_node, EX_PROVENANCE, PUBLIC, literal=True),
            ]
            stats["participation_nodes"] += 1
            stats["commitment_edges"] += 1
            stats["rows_resolved"] += 1

            is_member_of_pairs.add((member["member_id"], doc))
            facility_members.setdefault(facility_id, set()).add(member["member_id"])

    for member_id, doc in sorted(is_member_of_pairs):
        triples.append(triple(member_uri_by_id[member_id],
                               CMNS_IS_MEMBER_OF, syndicate_node(doc)))
        stats["is_member_of_edges"] += 1

    return triples, stats, facility_members


def build_vote(internal: dict, facility_members: dict[str, set[str]],
                member_uri_by_id: dict[str, str]
                ) -> tuple[list[str], dict]:
    """Task 9 -- amendment events (public, dated, read from
    `wave18_internal.json`'s `amendment_events`, which the generator
    itself extracted from each filing's own recital) and the one live,
    open amendment vote (synthetic — internal).

    **Voter eligibility is asserted here too, not only trusted from the
    generator.** `generate_syndicate_internal.py::build_amendment_vote`
    already asserts its `MEMBER_POSTURES` key set matches
    `VOTE_FACILITY_ID`'s real filed lender roster at GENERATION time. This
    function re-checks the SAME claim against `facility_members` --
    `build()`'s own record of who actually got a `SyndicateParticipation`
    node on each facility THIS run -- so a stale `wave18_internal.json`
    (regenerated against a different schedule/institutions snapshot, or
    hand-edited) cannot silently mint a `votesOn` edge from a non-lender.
    Loud `SystemExit`, not a skip: a fabricated lender relationship must
    never load quietly.
    """
    stats = {
        "amendment_event_nodes": 0,
        "amendment_event_facility_edges": 0,
        "amendment_vote_nodes": 0,
        "votes_on_edges": 0,
    }
    triples: list[str] = []

    # --- AmendmentEvent nodes, one per governing document, each amends
    #     every Wave 18 facility that document carries -----------------
    for event in internal["amendment_events"]:
        node = amendment_event_node(event["document"])
        assert event["provenance"] == PUBLIC, (
            f"{event['document']}: amendment event provenance must be "
            f"{PUBLIC!r}, got {event['provenance']!r} -- §C assigns "
            f"amendment events/effective dates to public filings")
        triples += [
            triple(node, RDF_TYPE, EX_AMENDMENT_EVENT),
            triple(node, RDFS_LABEL,
                   f"Amendment event, {event['document']}", literal=True),
            triple(node, EX_EFFECTIVE_DATE, event["effective_date"],
                   literal=True),
            triple(node, EX_SOURCE_PASSAGE, event["source_passage"],
                   literal=True),
            triple(node, EX_PROVENANCE, PUBLIC, literal=True),
        ]
        stats["amendment_event_nodes"] += 1
        for fid in event["facility_ids"]:
            assert fid not in WAVE18_EXCLUDED_FACILITIES, (
                f"{event['document']}: amendment event routes to "
                f"{fid}, excluded by Ruling T6-R2")
            triples.append(triple(node, EX_AMENDS, facility_node(fid)))
            stats["amendment_event_facility_edges"] += 1

    # --- The one live, open vote -----------------------------------------
    vote = internal["amendment_vote"]
    fid = vote["facility_id"]
    assert vote["vote_state"] == "open", (
        f"amendment_vote.vote_state is {vote['vote_state']!r}, not 'open' "
        f"-- §F requires a LIVE vote")
    assert vote["provenance"] == SYNTHETIC_INTERNAL, (
        f"amendment_vote.provenance must be {SYNTHETIC_INTERNAL!r}, got "
        f"{vote['provenance']!r}")

    eligible = facility_members.get(fid, set())
    posted = set(vote["postures"])
    fabricated = posted - eligible
    assert not fabricated, (
        f"{fid}: amendment_vote names {sorted(fabricated)} as voter(s), "
        f"but {sorted(fabricated)} hold no SyndicateParticipation on "
        f"{fid} in the graph this run just built -- refusing to write a "
        f"fabricated votesOn edge")
    unresolved = posted - set(member_uri_by_id)
    assert not unresolved, (
        f"amendment_vote names member_id(s) with no member node at all: "
        f"{sorted(unresolved)}")

    distinct_postures = set(vote["postures"].values())
    allowed_postures = {"consent", "decline", "abstain", "undecided"}
    bad_postures = distinct_postures - allowed_postures
    assert not bad_postures, (
        f"posture(s) outside the closed vocabulary: {bad_postures}")
    assert len(distinct_postures) >= 2, (
        f"§F requires >= 2 distinct postures on the open vote; got "
        f"{distinct_postures} -- a vote where everyone agrees satisfies "
        f"the count and not the condition")

    vnode = vote_node(fid)
    triples += [
        triple(vnode, RDF_TYPE, EX_AMENDMENT_VOTE),
        triple(vnode, RDFS_LABEL, f"Open amendment vote, {fid}", literal=True),
        triple(vnode, EX_VOTE_STATE, "open", literal=True),
        triple(vnode, EX_AMENDS, facility_node(fid)),
        triple(vnode, EX_PROVENANCE, SYNTHETIC_INTERNAL, literal=True),
    ]
    stats["amendment_vote_nodes"] += 1

    for member_id, posture in sorted(vote["postures"].items()):
        member_uri = member_uri_by_id[member_id]
        triples += [
            triple(member_uri, EX_VOTES_ON, vnode),
            triple(member_uri, EX_VOTE_POSTURE, posture, literal=True),
        ]
        stats["votes_on_edges"] += 1

    return triples, stats


def build_envelopes(envelopes: dict, member_uri_by_id: dict[str, str]
                     ) -> tuple[list[str], dict]:
    """Task 10 -- the two bilateral disclosure envelopes, read from
    `wave18_envelopes.json` (Task 10's own generator).

    **Asymmetry is asserted here too, not only trusted from the
    generator.** `generate_disclosure_envelopes.py` already checks its own
    output before writing it (`_assert_known_elements`, the cross-envelope
    identical-scopes check); this function re-derives the SAME two claims
    against the artifact this run actually reads, so a stale or hand-edited
    `wave18_envelopes.json` cannot silently load a symmetric or empty-scope
    envelope. Loud `AssertionError`, not a skip.

    **Counterparty must be an existing member.** `ex:counterparty` points
    at the SAME `ex:member/<member_id>` node `build()` already minted for
    that institution -- resolved from `member_uri_by_id` (built once in
    `load_structure()`, the same dict `build_vote` already reuses), never a
    new node. A `counterparty_member_id` with no member node is a loud
    error: an envelope negotiated with an institution this graph does not
    even carry as a lender is a fabricated relationship, the same standard
    Task 9 holds `votesOn` edges to.
    """
    stats = {"envelope_nodes": 0, "request_scope_edges": 0,
              "disclose_scope_edges": 0}
    triples: list[str] = []

    req_sets: list[frozenset] = []
    dis_sets: list[frozenset] = []

    for env in envelopes["envelopes"]:
        member_id = env["counterparty_member_id"]
        member_uri = member_uri_by_id.get(member_id)
        assert member_uri is not None, (
            f"envelope counterparty {member_id!r} ({env['counterparty_legal_name']}) "
            f"has no FinanceSyndicateMember node in this graph -- a "
            f"fabricated bilateral relationship, refusing to write it")

        request = set(env["request_scope"])
        disclose = set(env["disclose_scope"])
        assert request, f"{member_id}: request_scope is empty (§F)"
        assert disclose, f"{member_id}: disclose_scope is empty (§F)"
        assert request != disclose, (
            f"{member_id}: request_scope == disclose_scope -- this "
            f"envelope is not asymmetric (§F requires >= 2 that are)")
        assert env["provenance"] == SYNTHETIC_INTERNAL, (
            f"{member_id}: envelope provenance must be {SYNTHETIC_INTERNAL!r}, "
            f"got {env['provenance']!r} -- envelopes are negotiated "
            f"bilaterally, never public")
        req_sets.append(frozenset(request))
        dis_sets.append(frozenset(disclose))

        node = envelope_node(member_id)
        triples += [
            triple(node, RDF_TYPE, EX_DISCLOSURE_ENVELOPE),
            triple(node, RDFS_LABEL,
                   f"Disclosure envelope, {env['counterparty_legal_name']}",
                   literal=True),
            triple(node, EX_COUNTERPARTY, member_uri),
            triple(node, EX_ENVELOPE_VERSION, env["envelope_version"],
                   literal=True),
            triple(node, EX_VALID_FROM, env["valid_from"], literal=True),
            triple(node, EX_PROVENANCE, SYNTHETIC_INTERNAL, literal=True),
        ]
        stats["envelope_nodes"] += 1
        for elem in sorted(request):
            triples.append(triple(node, EX_REQUEST_SCOPE, elem, literal=True))
            stats["request_scope_edges"] += 1
        for elem in sorted(disclose):
            triples.append(triple(node, EX_DISCLOSE_SCOPE, elem, literal=True))
            stats["disclose_scope_edges"] += 1

    assert stats["envelope_nodes"] >= 2, (
        f"§F requires >= 2 bilateral envelopes, got {stats['envelope_nodes']}")
    assert len(set(req_sets)) > 1 or len(set(dis_sets)) > 1, (
        "every envelope's request/disclose scopes are identical to every "
        "other envelope's -- the two counterparties are indistinguishable, "
        "not bilaterally negotiated")

    return triples, stats


def build_thresholds(thresholds: dict, valid_facility_ids: set[str]
                      ) -> tuple[list[str], dict]:
    """Task 11b -- one `ex:AmendmentThreshold` node per (document, bucket)
    entry in Task 11b's own artifact (`generators/extract_voting_thresholds
    .py`), linked by `ex:thresholdGoverns` to every Wave 18 facility that
    document maps to (the artifact's own `facility_ids`, already derived
    there from `TRANCHE_TO_FACILITIES`, imported -- never re-derived here).

    **Facility targets are re-checked here, not only trusted from the
    generator.** Every entry's `facility_ids` must be a subset of
    `valid_facility_ids` -- `load_structure()`'s own record of which
    facility_ids actually got a `SyndicatedLoan` node THIS run (via
    `wave18_facility_ids()`, the same set `build()` uses) -- so a stale or
    hand-edited `wave18_voting_thresholds.json` cannot silently mint a
    `thresholdGoverns` edge to a facility this graph does not carry. Loud
    `AssertionError`, not a skip -- the same standard `build_vote()` and
    `build_envelopes()` already hold their own edges to.

    `ex:consentPercent` is written ONLY when `consent_percent` is not
    `None` -- a veto standard ("each affected Lender", "all Lenders", "each
    Class A/B Lender") never gets a percent literal, by construction of the
    artifact (see `ccf.syndicate.EX_CONSENT_PERCENT`'s own docstring for
    why inventing one would be exactly the failure CLAUDE.md forbids)."""
    stats = {"threshold_nodes": 0, "threshold_governs_edges": 0,
             "thresholds_with_percent": 0}
    triples: list[str] = []

    for doc_entry in thresholds["documents"]:
        document = doc_entry["document"]
        facility_ids = doc_entry["facility_ids"]
        unknown = set(facility_ids) - valid_facility_ids
        assert not unknown, (
            f"{document}: threshold artifact names facility_id(s) "
            f"{sorted(unknown)} not present as a SyndicatedLoan node in "
            f"this graph -- refusing to write a fabricated governs edge")

        for t in doc_entry["thresholds"]:
            node = threshold_node(document, t["bucket"])
            triples += [
                triple(node, RDF_TYPE, EX_AMENDMENT_THRESHOLD),
                triple(node, RDFS_LABEL,
                       f"{t['consent_standard']} -- {document}", literal=True),
                triple(node, EX_CONSENT_STANDARD, t["consent_standard"],
                       literal=True),
                triple(node, EX_AMENDMENT_TYPE, t["amendment_type"],
                       literal=True),
                triple(node, EX_SOURCE_PASSAGE, t["source_passage"],
                       literal=True),
                triple(node, EX_PROVENANCE, PUBLIC, literal=True),
            ]
            stats["threshold_nodes"] += 1
            if t["consent_percent"] is not None:
                triples.append(triple(node, EX_CONSENT_PERCENT,
                                       str(t["consent_percent"]), literal=True))
                stats["thresholds_with_percent"] += 1
            for fid in facility_ids:
                triples.append(triple(node, EX_THRESHOLD_GOVERNS,
                                       facility_node(fid)))
                stats["threshold_governs_edges"] += 1

    return triples, stats


#: The four path prefixes this loader, and only this loader, mints (see the
#: module docstring's Idempotency section). Retracting every triple whose
#: subject starts with one of these -- before every run -- is what makes a
#: SCHEME change (not just a literal change) safe to re-run, not merely a
#: content change.
OWNED_SUBJECT_PREFIXES = [
    f"{EX}syndicate/", f"{EX}member/", f"{EX}agent/", f"{EX}participation/",
]


def _esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def reconcile() -> int:
    """Retract every triple currently in the ledger whose SUBJECT falls
    under one of `OWNED_SUBJECT_PREFIXES`. Returns the number retracted."""
    statements: list[str] = []
    for prefix in OWNED_SUBJECT_PREFIXES:
        q = (f'SELECT ?s ?p ?o FROM <{FLUREE_LEDGER_V2}> WHERE {{ '
             f'?s ?p ?o . FILTER(STRSTARTS(STR(?s), "{prefix}")) }}')
        for b in fluree.query(q).get("results", {}).get("bindings", []):
            s, p, o = b["s"]["value"], b["p"]["value"], b["o"]["value"]
            obj = f'"{_esc(o)}"' if b["o"].get("type") == "literal" else f"<{o}>"
            statements.append(f"<{s}> <{p}> {obj} .")

    if not statements:
        return 0
    for i in range(0, len(statements), BATCH):
        fluree.update("DELETE DATA {\n" + "\n".join(statements[i:i + BATCH])
                       + "\n}")
    return len(statements)


def load_structure() -> dict:
    """The interface the brief promised: `load_structure() -> dict`,
    returning counts, for Task 9 and 10 to extend this module against.
    Does the full load -- build, assert, reconcile, insert -- and returns
    every count as a plain dict, the SAME numbers `main()` prints (it calls
    this and formats the result), not a second, independently-computed
    account that could drift from what the CLI output shows."""
    schedules = load_schedules()
    institutions = load_institutions()
    internal = load_internal()
    envelopes = load_envelopes()
    thresholds = load_thresholds()

    triples, stats, facility_members = build(schedules, institutions)

    assert stats["rows_to_manual_review"] == 1, (
        f"expected exactly the one known corrupt row "
        f"(BarclaysFifth Third...) in manual_review, got "
        f"{stats['rows_to_manual_review']}")
    assert stats["rows_resolved"] + stats["rows_to_manual_review"] == \
        stats["rows_total"]

    # Same construction `build()` used internally -- every institutions
    # member gets a node URI; TCW is deliberately absent (agent-only, never
    # a voter -- see the module docstring's Administrative agents section).
    member_uri_by_id = {m["member_id"]: member_node(m["member_id"])
                         for m in institutions["members"]}
    vote_triples, vote_stats = build_vote(internal, facility_members,
                                           member_uri_by_id)
    triples += vote_triples
    stats.update(vote_stats)

    envelope_triples, envelope_stats = build_envelopes(envelopes,
                                                         member_uri_by_id)
    triples += envelope_triples
    stats.update(envelope_stats)

    # Task 11b -- valid_facility_ids is the SAME set wave18_facility_ids()
    # gave build() above (every facility this run actually typed as a
    # SyndicatedLoan), so a threshold node can never govern a facility this
    # graph does not carry.
    threshold_triples, threshold_stats = build_thresholds(
        thresholds, set(wave18_facility_ids(schedules)))
    triples += threshold_triples
    stats.update(threshold_stats)
    assert stats["threshold_nodes"] == 16, (
        f"expected exactly 16 AmendmentThreshold nodes (measured live "
        f"against the six filings, 2026-08-26 -- 5 documents x 2, Paychex "
        f"x 3, Sabre x 5), got {stats['threshold_nodes']} -- the artifact "
        f"has drifted from what was measured, not a number to silently "
        f"accept")
    assert stats["thresholds_with_percent"] == 7, (
        f"expected exactly 7 percentage-bearing thresholds (5 flat "
        f"'Required Lenders' + Sabre's Class A + Class B), got "
        f"{stats['thresholds_with_percent']}")

    retracted = reconcile()

    for i in range(0, len(triples), BATCH):
        fluree.update("INSERT DATA {\n" + "\n".join(triples[i:i + BATCH])
                       + "\n}")

    result = dict(stats)
    result["total_triples_written"] = len(triples)
    result["retracted"] = retracted
    result["ledger_t"] = fluree.ledger_t()
    result["ledger_triple_count"] = fluree.count_triples()
    return result


def main() -> int:
    result = load_structure()

    print("\nWave 18 Task 8/9/10/11b -- Fluree load\n")
    for key in (
        "syndicated_loan_nodes", "syndicate_nodes", "member_nodes",
        "agent_only_nodes", "dual_typed_members",
        "administered_by_edges", "participation_nodes", "commitment_edges",
        "is_member_of_edges", "rows_total", "rows_resolved",
        "rows_to_manual_review",
        "amendment_event_nodes", "amendment_event_facility_edges",
        "amendment_vote_nodes", "votes_on_edges",
        "envelope_nodes", "request_scope_edges", "disclose_scope_edges",
        "threshold_nodes", "threshold_governs_edges",
        "thresholds_with_percent",
    ):
        print(f"  {key:<28} {result[key]:>6}")
    print(f"  total triples                {result['total_triples_written']:>6}")
    print(f"\n  reconcile: retracted {result['retracted']} pre-existing "
          f"triples on our own subjects")
    print(f"\n  ledger now at t={result['ledger_t']} . "
          f"{result['ledger_triple_count']:,} triples")
    return 0


if __name__ == "__main__":
    sys.exit(main())
