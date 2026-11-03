#!/usr/bin/env python3
"""Wave 18 Task 16 — the six §F floors for `syndicated-lending-co-lender`.

## What this is not

This is a **build-time validator, not an operator**. See CLAUDE.md, "What
'operator' means -- and what it does not". An Operator is a runtime SDK
entity: registered, composed into an Operator Plan DAG, executed in the
Data Plane, serving a principal at request time. This script registers
nothing, composes into no plan, serves no principal, emits no contract,
enforces no TTL, and **writes nothing to any store on either fabric**. It
runs against the loaded estate -- ours and the co-lender's -- and asks one
question: does this data support what the spec claims?

Every read below is a read. The peer fabric is reached only through
`ccf.config.co_lender_pg_connect` / `ccf.fluree.co_lender_query`, which are
the same guarded entry points the loaders use, and never for write.

## What it proves, and how

Six conditions, each recomputed from the stores on every run. Not one of
them reads a stored score, a cached rank, a boolean flag, or a label as its
ANSWER -- `ex:disclosurePrecision`, `provenance`, `subject_kind` and the
peer's `attestation` column all exist, and none of them is consulted to
decide whether a floor holds:

1. SHARES ARE SOURCED   -- every `SyndicateParticipation`'s cited offset is
                           resolved against the RE-EXTRACTED filing text and
                           must land on the lender the node claims, with its
                           amount present at that row. No share was invented.
2. ENVELOPES ASYMMETRIC -- >= 2 `DisclosureEnvelope` nodes whose request-set
                           and disclose-set DIFFER as sets, both non-empty.
3. PRECISION IS MIXED   -- on the PEER fabric: one counterparty exact, one
                           band-only, the band counterparty's every row a
                           band, and no exact figure for it anywhere on that
                           fabric. See Ruling T14-R1 below.
4. POSTURES DIVERGE     -- the one open amendment vote carries >= 2 distinct
                           `ex:votePosture` values, read from the postures.
5. FEDERATION BOUNDS    -- >= 1 declared latency over the declared bound with
                           a contrast under it; >= 1 unattested claim with a
                           contrast and a matching Context Debt row on our
                           side; min remote TTL < local composite < max.
6. LINEAGE IS SEPARABLE -- every element in a DERIVED population (every
                           table in either Postgres schema, every subject on
                           either ledger) resolves on exactly ONE fabric, and
                           no peer identifier sits in a local row that fails
                           to declare the claim remote.

    uv run validators/syndicate.py

Exit code is non-zero if any of the six fails.

## Ruling T16-PRE — why there is no `shares_reconcile` floor

An earlier cut of this plan required every facility's parsed shares to sum
to `ccf_v2.facility.commitment_amount`. **That floor rested on a false
premise and is deleted.** Measured 2026-08-25 across all twelve Wave 18
facilities: *not one reconciles* -- best case 4.0% off (Paychex), worst
3391%. Four causes, all legitimate, none a Wave 18 defect: placeholder
schedule rows the filing declines to attribute to anyone (Bausch's
"Cashless Option Initial Lenders"), amendment exhibits listing only
INCREMENTAL commitments (Regis), unreliable tranche captions spanning two
tranches (AHR), and Wave 4 totals that are themselves wrong (AHR's
`FAC-2A2C38`, known-issues #32). The weaker variant "no single share
exceeds its facility" fails too, on AHR, for the fourth reason.

The full account is in `docs/known-issues.md` §34 and in
`docs/ccf_dataprep_v2.md`. It is written down so nobody re-derives the
deleted floor from first principles and reports the estate broken.

`shares_are_sourced` replaces it and proves the property that actually
matters -- no share was invented -- which, unlike summation, is both true
and checkable. **Nothing in this file may reference
`facility.commitment_amount`, and nothing may sum shares.**

## Ruling T14-R1 — what `precision_is_mixed` may claim

The condition is often stated as "the band peer has no exact figure
derivable anywhere." **"Anywhere" is false on this estate.** Our own Fluree
ledger holds `ex:participationOf <Citibank> -> FAC-405B7A` with
`ex:commitmentUsd 70000000`; the concealed figure is a real filed
commitment-schedule row and it is public. An assembler unioning our
participations with the peer's positions finds the scalar on our own side.

So this floor is about **what the peer discloses**: the peer's fabric
carries no exact figure for the banded counterparty -- every position it
holds for that counterparty is a band. Every scan it performs is scoped to
the peer fabric, and `Context.peer_fabric_cells` is built only from peer
tables and peer-ledger literals. Our ledger is used to LOCATE the needle
and is deliberately never scanned for it.

Because this arm's green answer is an ABSENCE -- the one kind that can be
permanently wrong with nothing looking broken -- the scan carries a POSITIVE
CONTROL (`Context.peer_numeric_controls`) and matches NUMERICALLY
(`numeric_values`), not by substring. Both are corrections from fix round 1;
the previous `str(figure) in value` would have missed `"70,000,000"`,
`"$70,000,000.00"` and `"7.0E7"` and reported a clean absence forever.

## Preflight Ruling P3 — `Context` is snapshots, never live cursors

Same stance as `aml_typology.Context`: every field is a plain Python value
taken once, so `validators/test_syndicate.py` can MUTATE one and require the
floor to give the opposite answer. `element_origin` is the one exception and
it is deliberately not a field -- see its property below.
"""
from __future__ import annotations

import collections
import json
import re
import sqlite3
import sys
from dataclasses import dataclass, field

from ccf import fluree
from ccf.config import (
    CO_LENDER_FLUREE_LEDGER as PEER_LEDGER,
    CO_LENDER_PG_SCHEMA as PEER_SCHEMA,
    EX,
    FLUREE_LEDGER_V2 as L,
    PG_SCHEMA_V2 as S,
    REPO_ROOT,
    SQLITE_PATH,
    assert_distinct_fabrics,
    co_lender_configured,
    co_lender_pg_connect,
    pg_connect,
)
from ccf.syndicate import (
    EX_AMENDMENT_VOTE,
    EX_AMENDS,
    EX_COMMITMENT_USD,
    EX_COUNTERPARTY,
    EX_DISCLOSE_SCOPE,
    EX_DISCLOSURE_ENVELOPE,
    EX_PARTICIPATION_IN,
    EX_PARTICIPATION_OF,
    EX_REQUEST_SCOPE,
    EX_SOURCE_PASSAGE,
    EX_SYNDICATE_PARTICIPATION,
    EX_VOTE_POSTURE,
    EX_VOTE_STATE,
    EX_VOTES_ON,
    LOCAL_COMPOSITE_TTL_SECONDS,
    MAX_FEDERATION_LATENCY_MS,
)

EX10_DIR = REPO_ROOT / "sources" / "ex10"

#: `MAX_FEDERATION_LATENCY_MS` and `LOCAL_COMPOSITE_TTL_SECONDS` (both §B)
#: are IMPORTED from `ccf/syndicate.py`, not redefined here (whole-branch
#: review fix -- this file, the two Task 14-16 write-time guards, and the
#: tests each held an independent copy). The reason they were stated as
#: literals in the first place still holds and is not weakened by the
#: import: these are BOUNDS the data is measured against, not values read
#: from the data -- reading a bound from the same store as the measurement
#: would let one row move both, and the check would stop checking
#: anything. Importing a code constant from a sibling module is not
#: reading the estate; it is the opposite of that failure -- it is what
#: stops a validator's own copy silently agreeing with a wrong loader
#: value.

#: How far past the end of a cited lender-name span the row's own commitment
#: figure may sit before `shares_are_sourced` calls it absent. Measured, not
#: chosen: across all 97 participations the furthest the figure sits from
#: the end of its lender's name is 99 characters, so 150 is slack rather
#: than the thing doing the work. `shares_are_sourced` reports the observed
#: maximum on every run, which is how a drift toward the ceiling becomes
#: visible instead of silently consuming the margin.
AMOUNT_WINDOW_CHARS = 150

#: A needle each store is KNOWN to contain, scanned alongside the peer
#: identifiers in `lineage_is_separable`'s leak scan. Its purpose is not to
#: find anything interesting: it is there so a scan that has silently
#: stopped looking -- a schema renamed, a connection pointed elsewhere, a
#: regex that no longer compiles the way it did -- reports zero for the
#: control and FAILS, rather than reporting zero for the peer identifiers
#: and passing. This estate has shipped two checks that returned the same
#: answer on every input and hid defects for seven waves each.
CONTROL_NEEDLES = {
    "postgres": "SYNM-",      # ccf_v2.syndicate_member.member_id, 45 rows
    "fluree": "#offset=",     # ex:sourcePassage citations, 100+ literals
    "sqlite": "FAC-",         # syndicate_desk_tracker.facility_id, 12 rows
}


# ===========================================================================
# Pure helpers -- no store access, exercised from validators/test_syndicate.py
# ===========================================================================

def local_name(iri: str) -> str:
    """Last path segment of an IRI. Labels and identifier extraction only --
    never used to compare across stores (CLAUDE.md, "Normalize to full IRIs
    before comparing")."""
    return iri.rsplit("/", 1)[-1]


def parse_citation(citation: str) -> tuple[str, int, int]:
    """`document#offset=start-end` -> `(document, start, end)`.

    Raises on anything else rather than returning a default. A citation this
    cannot parse is a lineage claim with no shape, and defaulting it to
    `(doc, 0, 0)` would make `shares_are_sourced` compare an empty span and
    report a failure that looks like bad data rather than a bad citation.
    """
    document, _, offsets = citation.partition("#offset=")
    if not offsets:
        raise ValueError(f"citation carries no #offset= part: {citation!r}")
    start, _, end = offsets.partition("-")
    return document, int(start), int(end)


#: Scientific notation, matched first and blanked out before the grouped
#: pattern runs -- otherwise `7.0E7` would be read as the two numbers 7.0
#: and 7.
_SCIENTIFIC_RE = re.compile(r"\d+(?:\.\d+)?[eE][+-]?\d+")

#: Comma-grouped and/or decimal runs: `70,000,000.00`, `70000000`, `87.3`.
#: A bare `\d+` would read `$70,000,000.00` as the four numbers 70, 000,
#: 000 and 00.
_GROUPED_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")


def numeric_values(text: str) -> set[float]:
    """Every NUMBER a reader could extract from `text`, as floats.

    **This is the matcher `precision_is_mixed`'s absence scan turns on, and
    it exists because the previous one was representation-fragile.** That
    scan asked `str(figure) in value`, which finds `"70000000.00"` and
    misses `"70,000,000"`, `"$70,000,000.00"` (how a `money` column casts)
    and `"7.0E7"`. A green answer that is an ABSENCE is the one kind that
    can be permanently wrong with nothing looking broken, so the comparison
    is now numeric rather than textual: every representation of 70,000,000
    normalises to the same float.

    Whole digit runs only. `170000000` yields 170000000.0 and not
    70000000.0, so a longer number never counts as a match for a shorter
    one. Conversely a figure embedded in an identifier (`PPOS-70000000AB`)
    IS found, because the run is bounded by non-digits -- concealment does
    not improve by hiding the number in a key.

    Space-grouped writing (`70 000 000`) is deliberately NOT parsed: joining
    digit runs across whitespace would merge genuinely adjacent numbers,
    which is worse than missing the format. Nothing on this estate writes
    figures that way today.

    **That gap is UNGUARDED, and nothing will tell you if it opens.** An
    earlier version of this docstring said the positive control in
    `precision_is_mixed` would notice. It cannot. Every control value comes
    from a `numeric` or `integer` column, and neither type's `::text` cast
    emits a separator in any locale -- so space-grouped writing could only
    ever appear in a FREE-TEXT column (`desk_note`, `provenance`, a ledger
    literal), and adding one there removes no control value from the
    haystack. `blind` stays empty, the floor stays green, and the figure
    sits in plain sight. A maintainer weighing whether this gap is safe must
    weigh it knowing no mechanism is watching it.

    What the control DOES establish, which is real and worth stating
    exactly: control values are compared against the text cast of **their
    own** columns, so a TYPED numeric column whose cast this parser cannot
    read would fail the floor. That covers the `money` -> `"$70,000,000.00"`
    case, and every other typed column's rendering. It says nothing at all
    about what a free-text column may contain.
    """
    out: set[float] = set()
    for match in _SCIENTIFIC_RE.finditer(text):
        try:
            out.add(float(match.group(0)))
        except ValueError:                                # pragma: no cover
            pass
    for match in _GROUPED_RE.finditer(_SCIENTIFIC_RE.sub(" ", text)):
        raw = match.group(0).rstrip(",")
        try:
            out.add(float(raw.replace(",", "")))
        except ValueError:                                # pragma: no cover
            pass
    return out


def scope_sets(envelope: dict) -> tuple[frozenset, frozenset]:
    """The two scopes of one envelope, as sets. Compared as sets and never
    as counts: `{a, b}` and `{a, c}` are the same SIZE and are not the same
    terms, and a size comparison would call that pair symmetric."""
    return frozenset(envelope["request"]), frozenset(envelope["disclose"])


def declares_remote(store: str, location: str, row: dict,
                    peer_identifiers) -> bool:
    """Does this local row, holding a peer identifier, itself declare the
    claim REMOTE?

    The default is False and the exception is narrow and named: a
    `ccf_v2.context_debt` row whose `subject_kind` is
    `federation_attestation`, whose `subject_key` is an identifier that
    actually resolves on the PEER fabric (recomputed -- passed in), and
    whose `reason` names the co-lender fabric in its own text. All four, or
    the occurrence counts as a leak.

    This is the one place in the file that consults a stored marker, and the
    direction matters: the marker cannot make a floor PASS that would
    otherwise fail on data -- it can only excuse an occurrence that the
    estate deliberately records, and only when the identifier it names is
    real. A row that merely sets `subject_kind` without naming a peer
    identifier that exists gets no excuse.

    ## Its counterpart, and why the two deliberately differ (Ruling T17-R2)

    `validators/partition.py::_is_permitted_debt_reference` decides the same
    question -- may this peer identifier sit in this local row? -- for a
    different check, and the two rules do NOT agree:

    | | this function | `_is_permitted_debt_reference` |
    |---|---|---|
    | reason must name "co-lender" | **yes** | no |
    | peer `position_id` admissible | **yes** | **no**, declarations only |
    | needle must be THAT row's `subject_key` | no | **yes** |
    | scope | one row, whole-row | one row, two columns |

    That is a real distinction, not an oversight. **This one is about
    LINEAGE MARKING**: floor 6 asks whether a local row that mentions the
    peer has declared the claim remote, so what matters is that the row
    speaks about the co-lender fabric and names something that really
    resolves there -- any peer identifier will do. **That one is about
    PARTITION SCANNING**: it asks whether a peer-owned element has been
    copied into our stores, so the only crossing it can excuse is the
    §D step 5 Context Debt reference, and a peer `position_id` -- an
    identifier for the peer's actual position data -- is never that.

    Neither is refactored into the other: they serve different floors and
    both are validated. Instead `check_wave18` requires a hit to satisfy
    **both** before exempting it, so the partition exemption is the
    INTERSECTION of the two and they can never drift into two different
    holes. This function is unchanged by that ruling -- floor 6 still uses
    it alone.
    """
    if store != "postgres" or location != f"{S}.context_debt":
        return False
    if row.get("subject_kind") != "federation_attestation":
        return False
    if row.get("subject_key") not in set(peer_identifiers):
        return False
    return "co-lender" in (row.get("reason") or "").lower()


# ===========================================================================
# Store reads -- one snapshot per run, taken here and nowhere else
# ===========================================================================

def _q(sparql: str) -> list[dict]:
    return fluree.query(sparql)["results"]["bindings"]


def _pq(sparql: str) -> list[dict]:
    return fluree.co_lender_query(sparql)["results"]["bindings"]


def _count(sparql: str, *, peer: bool = False) -> int:
    rows = _pq(sparql) if peer else _q(sparql)
    return int(rows[0]["n"]["value"]) if rows else 0


#: How `lineage_is_separable` decides an element's origin: by asking BOTH
#: fabrics the same question and recording which one answers. That symmetry
#: is the whole mechanism -- a probe worded differently for the two sides
#: would be measuring its own wording rather than the estate.
#:
#: **RULING T16-R2 — the population is DERIVED, not listed.** An earlier cut
#: of this file probed eight hand-picked elements under a docstring claiming
#: "every element". An element absent from a hand-written list can never
#: fail this floor, which is the one unread denominator in a file whose own
#: participation guard exists because an unread denominator hid 5 of 97 rows
#: on the first run. So the population is now read from the estate:
#:
#: * `pg:<table>` -- every base table name in EITHER Postgres schema, ours
#:   (`ccf_v2`) or the peer's (`colender`). The question is "does this schema
#:   hold at least one row in a table of that name", asked with `EXISTS` of
#:   both. 113 elements today, and a table added by any wave joins the
#:   population without anybody remembering to add it.
#: * `graph:<subject IRI>` -- every distinct SUBJECT asserted on either
#:   ledger. The question is "does this ledger assert anything about this
#:   node". 11,856 elements today.
#:
#: **Why subjects and not predicates.** The two ledgers deliberately SHARE
#: vocabulary: `rdf:type`, `rdfs:label`, `ex:lei` and `ex:provenance` are all
#: asserted on both, because both fabrics describe syndicate members with the
#: same terms. A predicate-level population would report those as "both" and
#: fail the floor for a reason that has nothing to do with separability --
#: sharing a term is not sharing a claim. A NODE, on the other hand, belongs
#: to exactly one fabric or the boundary has been crossed, which is the
#: property §F names.
#:
#: **What the population does not cover, said plainly.** MongoDB and SQLite
#: contribute no elements: the peer fabric provisions neither
#: (`CO_LENDER_MONGO_URI` is unset and there is no peer departmental file),
#: so every element there would be "local" by construction and could never
#: discriminate. That is a property of the estate, not a narrowing of the
#: check, and `lineage_is_separable`'s detail line says so on every run.
PG_ELEMENT_PREFIX = "pg:"
GRAPH_ELEMENT_PREFIX = "graph:"


@dataclass
class Context:
    """Snapshots of both fabrics, taken once (Preflight Ruling P3).

    Mutable on purpose. `validators/test_syndicate.py` re-points a
    participation at the wrong member, flattens the vote, symmetrises the
    envelopes, hands the band peer an exact figure and stretches every
    remote TTL, and requires the floors to give the OPPOSITE answer each
    time. A floor reading a live cursor could not be falsified that way and
    would be a floor nobody has ever seen say "no".

    There is deliberately no `share_totals` field (Ruling T16-R1). Its two
    members, `parsed_sum` and `recorded_total`, are the inputs of
    `shares_reconcile` -- the floor Ruling T16-PRE deleted, measured, across
    all twelve facilities. A populated-but-unread field holding
    `recorded_total` is how a deleted condition survives its deletion; this
    repo has six recorded instances of exactly that.
    """

    as_of: str

    # --- Fluree, ours ----------------------------------------------------

    #: envelope IRI -> {"request": set[str], "disclose": set[str]}
    envelopes: dict[str, dict[str, set[str]]]

    #: voter IRI -> posture string, for the ONE open vote
    vote_postures: dict[str, str]

    #: every `ex:AmendmentVote` whose `ex:voteState` is 'open'. Snapshotted
    #: separately from `vote_postures` so `vote_postures_diverge` can refuse
    #: an estate with two open votes -- "THE open vote" is not a thing then,
    #: and a posture set pooled across two votes would report divergence
    #: that no single vote exhibits.
    open_vote_iris: list[str]

    #: one row per `ex:SyndicateParticipation` node: member_id, the amount
    #: it claims, and the document/offsets it cites.
    participations: list[dict]

    #: (lender LEI, facility_id) -> commitment total on our own ledger. Used
    #: ONLY to locate the figure a peer band conceals; never scanned for,
    #: never summed against a facility total (Ruling T16-PRE).
    our_commitments: dict[tuple[str, str], int]

    # --- Postgres, ours --------------------------------------------------

    #: member_id -> {"legal_name": str, "raw_names": list[str]}
    members: dict[str, dict]

    #: `context_debt.subject_key` for every `federation_attestation` row
    context_debt_federation_keys: set[str]

    # --- The filings themselves ------------------------------------------

    #: filed document filename -> text, RE-EXTRACTED from `sources/ex10/`
    #: on every run. Not a stored copy of the text and not the extraction
    #: any loader kept: if the extractor drifts, every offset in the ledger
    #: stops resolving and this floor says so.
    documents: dict[str, str]

    # --- The peer fabric -------------------------------------------------

    #: rows of `colender.peer_position`, column names as keys
    peer_positions: list[dict]

    #: rows of `colender.peer_product_declaration`, column names as keys
    declarations: list[dict]

    #: ("<table>.<column>" | "<ledger literal>", text) for EVERY cell of
    #: every table in the peer schema and every literal on the peer ledger.
    #: This is the population `precision_is_mixed` scans -- the peer fabric
    #: and nothing else (Ruling T14-R1).
    peer_fabric_cells: list[tuple[str, str]]

    #: how many peer tables and columns went into `peer_fabric_cells`, so
    #: the detail line can state the denominator rather than assert it
    peer_scan_shape: dict[str, int]

    #: numbers the peer's own TYPED columns say it holds -- share_usd, band
    #: bounds, declared TTLs and latencies -- read by their own query rather
    #: than lifted out of `peer_positions` (which the tests mutate) or out of
    #: `peer_fabric_cells` (which would be circular). Every one must be
    #: findable in `peer_fabric_cells` by `numeric_values`, or
    #: `precision_is_mixed`'s absence scan is not seeing what it claims to
    #: have searched. The `CONTROL_NEEDLES` discipline, applied to the arm
    #: that carries the T14-R1 claim.
    peer_numeric_controls: set[float]

    #: every position id and declaration id the peer fabric carries
    peer_identifiers: set[str]

    # --- Derived-by-reading, for lineage_is_separable --------------------

    #: element name -> {"local": 0|1, "peer": 0|1}. Which fabric ANSWERED,
    #: recorded as `EXISTS` PRESENCE and not as a row count -- origin is a
    #: question about who answers at all (see `_probe_elements`). The
    #: population is derived from the estate on every run; there is no list
    #: of probes in this module any more. `element_origin` is computed from
    #: this and is not stored -- see the property below.
    element_probes: dict[str, dict[str, int]]

    #: every place a PEER identifier was found in one of OUR stores, with
    #: `declares_remote` decided by `declares_remote()` above.
    local_identifier_hits: list[dict]

    #: store -> control-needle hit count, proving the leak scan can find
    #: something. Zero for any store is a scan that looked at nothing.
    control_hits: dict[str, int]

    #: store -> how many rows/literals the leak scan actually examined
    leak_scan_shape: dict[str, int] = field(default_factory=dict)

    @property
    def element_origin(self) -> dict[str, str]:
        """element name -> "local" | "remote" | "both" | "unresolved".

        **Derived, never read.** Nothing in either fabric stores an origin;
        this is decided by which fabric ANSWERED the element's probe. A
        stored column, flag or literal saying "remote" would prove nothing
        at all -- a marker somebody wrote down cannot establish that no peer
        claim is reachable through a local path, and reading one is the
        single defect class this project loses most time to.

        Deliberately a read-only property rather than a dataclass field, so
        it cannot be assigned a convenient value; `validators/
        test_syndicate.py` asserts that assigning it raises. Falsify it by
        changing what the probes SAW (`element_probes`), which is what would
        change if a loader really did put a peer claim on our side.

        "both" and "unresolved" exist so ambiguity is visible instead of
        being forced into one of the two answers -- `lineage_is_separable`
        fails on either.

        **What "unresolved" means changed when the population became
        derived (Ruling T16-R7).** Under the eight hand-picked probes it
        could only mean "an element this floor cannot see", which is an
        element it can never fail on. Under a derived population it ALSO
        means "a base table that exists and nobody has loaded yet" -- a
        normal estate state, not a separability defect. The floor still
        fails on it, deliberately and by ruling: an unseen element is
        exactly the silent-green class this task exists to remove, and
        softening it would trade a loud unrelated failure for a quiet
        relevant one. What changed is that the failure MESSAGE now names
        which of the two you are looking at, using the `*_container` keys
        `_probe_elements` records beside the answer. See
        `docs/known-issues.md` §35.
        """
        out: dict[str, str] = {}
        for name, counts in self.element_probes.items():
            here, there = counts["local"] > 0, counts["peer"] > 0
            out[name] = ("both" if here and there
                         else "local" if here
                         else "remote" if there
                         else "unresolved")
        return out


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def _load_envelopes() -> dict[str, dict[str, set[str]]]:
    rows = _q(
        f"SELECT ?env ?kind ?elem FROM <{L}> WHERE {{ "
        f"?env a <{EX_DISCLOSURE_ENVELOPE}> ; <{EX_COUNTERPARTY}> ?cp . "
        f"{{ ?env <{EX_REQUEST_SCOPE}> ?elem . BIND('request' AS ?kind) }} "
        f"UNION "
        f"{{ ?env <{EX_DISCLOSE_SCOPE}> ?elem . BIND('disclose' AS ?kind) }} }}")
    out: dict[str, dict[str, set[str]]] = {}
    for r in rows:
        env = out.setdefault(r["env"]["value"],
                             {"request": set(), "disclose": set()})
        env[r["kind"]["value"]].add(r["elem"]["value"])
    # An envelope carrying ONE scope predicate and not the other would never
    # appear with an empty set otherwise -- the UNION simply would not
    # produce a row for it, and `envelopes_are_asymmetric`'s non-empty guard
    # would have nothing to fail on. Fill both keys from the envelope list.
    for r in _q(f"SELECT ?env FROM <{L}> WHERE "
                f"{{ ?env a <{EX_DISCLOSURE_ENVELOPE}> }}"):
        out.setdefault(r["env"]["value"], {"request": set(), "disclose": set()})
    return out


def _load_vote() -> tuple[list[str], dict[str, str]]:
    open_votes = sorted({r["v"]["value"] for r in _q(
        f"SELECT DISTINCT ?v FROM <{L}> WHERE {{ "
        f"?v a <{EX_AMENDMENT_VOTE}> ; <{EX_VOTE_STATE}> 'open' }}")})
    postures: dict[str, str] = {}
    for r in _q(f"SELECT ?e ?posture FROM <{L}> WHERE {{ "
                f"?v a <{EX_AMENDMENT_VOTE}> ; <{EX_VOTE_STATE}> 'open' . "
                f"?e <{EX_VOTES_ON}> ?v ; <{EX_VOTE_POSTURE}> ?posture }}"):
        postures[r["e"]["value"]] = r["posture"]["value"]
    return open_votes, postures


def _load_participations() -> tuple[list[dict], dict[tuple[str, str], int]]:
    """Two reads, deliberately not one.

    The obvious single query joins `?member ex:lei ?lei` so both results
    fall out together. That join is INNER, and five of this estate's
    syndicate members carry no `ex:lei` at all -- the five named funds,
    which CLAUDE.md requires to omit the property rather than carry an empty
    string. Folding the two questions into one query silently dropped five
    of the 97 participations, and a floor that cannot see a row cannot fail
    on it. Caught by `shares_are_sourced`'s independent `COUNT(*)`
    denominator on the first run of this file, which is the whole reason
    that guard is there.

    So: participations are read with no lei constraint, and the
    lei-keyed commitment index -- needed only to locate what a peer BAND
    conceals, and both peer counterparties have real GLEIF LEIs -- is a
    second, narrower read.
    """
    rows = _q(
        f"SELECT ?part ?member ?fac ?amt ?src FROM <{L}> WHERE {{ "
        f"?part a <{EX_SYNDICATE_PARTICIPATION}> ; "
        f"<{EX_PARTICIPATION_OF}> ?member ; "
        f"<{EX_PARTICIPATION_IN}> ?fac ; "
        f"<{EX_COMMITMENT_USD}> ?amt ; "
        f"<{EX_SOURCE_PASSAGE}> ?src }}")
    participations = []
    for r in rows:
        document, start, end = parse_citation(r["src"]["value"])
        participations.append({
            "participation": r["part"]["value"],
            "member_id": local_name(r["member"]["value"]),
            "facility_id": local_name(r["fac"]["value"]),
            "commitment_usd": int(r["amt"]["value"]),
            "document": document,
            "start": start,
            "end": end,
        })

    commitments: dict[tuple[str, str], int] = collections.defaultdict(int)
    for r in _q(f"SELECT ?lei ?fac ?amt FROM <{L}> WHERE {{ "
                f"?part a <{EX_SYNDICATE_PARTICIPATION}> ; "
                f"<{EX_PARTICIPATION_OF}> ?member ; "
                f"<{EX_PARTICIPATION_IN}> ?fac ; "
                f"<{EX_COMMITMENT_USD}> ?amt . "
                f"?member <{EX}lei> ?lei }}"):
        commitments[(r["lei"]["value"], local_name(r["fac"]["value"]))] += \
            int(r["amt"]["value"])
    return participations, dict(commitments)


def _load_our_postgres() -> tuple[dict[str, dict], set[str]]:
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT member_id, legal_name, raw_names '
                    f'FROM "{S}".syndicate_member')
        members = {
            m: {"legal_name": n,
                "raw_names": list(json.loads(raw) if isinstance(raw, str)
                                  else raw or [])}
            for m, n, raw in cur.fetchall()}
        cur.execute(f'SELECT subject_key FROM "{S}".context_debt '
                    f"WHERE subject_kind = 'federation_attestation'")
        keys = {r[0] for r in cur.fetchall() if r[0]}
    return members, keys


def _load_documents(participations) -> dict[str, str]:
    from generators.extract_facilities import TextExtractor

    out: dict[str, str] = {}
    for name in sorted({p["document"] for p in participations}):
        path = EX10_DIR / name
        if not path.exists():
            out[name] = ""
            continue
        parser = TextExtractor()
        parser.feed(path.read_text(errors="ignore"))
        parser.close()
        out[name] = parser.text()
    return out


def _load_peer() -> dict:
    """Everything read from the co-lender's fabric, in one pass.

    `assert_distinct_fabrics()` runs first. If the peer's Postgres ever
    turned out to BE ours, every floor below would still return numbers and
    three of them would still pass -- which is the shape of failure
    `ccf/config.py`'s guard block exists for.
    """
    assert_distinct_fabrics()
    with co_lender_pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT * FROM "{PEER_SCHEMA}".peer_position')
        cols = [d[0] for d in cur.description]
        positions = [dict(zip(cols, r)) for r in cur.fetchall()]

        cur.execute(f'SELECT * FROM "{PEER_SCHEMA}".peer_product_declaration')
        cols = [d[0] for d in cur.description]
        declarations = [dict(zip(cols, r)) for r in cur.fetchall()]

        cur.execute("SELECT table_name, column_name FROM "
                    "information_schema.columns WHERE table_schema = %s "
                    "ORDER BY 1, 2", (PEER_SCHEMA,))
        columns = cur.fetchall()

        cells: list[tuple[str, str]] = []
        tables = sorted({t for t, _ in columns})
        for table in tables:
            table_cols = [c for t, c in columns if t == table]
            select = ", ".join(f'coalesce("{c}"::text, \'\')' for c in table_cols)
            cur.execute(f'SELECT {select} FROM "{PEER_SCHEMA}"."{table}"')
            for row in cur.fetchall():
                for column, value in zip(table_cols, row):
                    cells.append((f"{table}.{column}", value))

    for b in _pq(f"SELECT ?s ?p ?o FROM <{PEER_LEDGER}> WHERE "
                 f"{{ ?s ?p ?o . FILTER(isLiteral(?o)) }}"):
        cells.append((f"ledger literal {local_name(b['p']['value'])} "
                      f"on {local_name(b['s']['value'])}", b["o"]["value"]))

    # The POSITIVE CONTROL for `precision_is_mixed`'s absence scan, read by
    # its own query from the peer's TYPED numeric columns rather than lifted
    # out of `cells` or out of `positions`. Two independent reads of the same
    # store that the matcher must be able to connect: if `numeric_values`
    # cannot find, in the text cast of the peer's tables, a figure the peer's
    # own numeric columns say is there, the scan is not seeing what it claims
    # to have searched and the floor fails rather than reporting a clean
    # absence. Same discipline as `CONTROL_NEEDLES`, applied to the arm that
    # carries the T14-R1 claim.
    #
    # Taken from a separate query on purpose: `ctx.peer_positions` is a
    # MUTABLE snapshot the falsification tests rewrite, and a control derived
    # from it could be switched off by the very mutation it is meant to
    # survive.
    with co_lender_pg_connect() as conn, conn.cursor() as cur:
        cur.execute(
            f'SELECT share_usd FROM "{PEER_SCHEMA}".peer_position '
            f'WHERE share_usd IS NOT NULL '
            f'UNION SELECT band_low FROM "{PEER_SCHEMA}".peer_position '
            f'WHERE band_low IS NOT NULL '
            f'UNION SELECT band_high FROM "{PEER_SCHEMA}".peer_position '
            f'WHERE band_high IS NOT NULL '
            f'UNION SELECT declared_ttl_seconds '
            f'FROM "{PEER_SCHEMA}".peer_product_declaration '
            f'UNION SELECT declared_latency_ms '
            f'FROM "{PEER_SCHEMA}".peer_product_declaration')
        controls = {float(r[0]) for r in cur.fetchall()}

    identifiers = ({r["position_id"] for r in positions}
                   | {r["declaration_id"] for r in declarations})
    return {
        "positions": positions,
        "declarations": declarations,
        "cells": cells,
        "shape": {"tables": len(tables), "columns": len(columns),
                  "cells": len(cells)},
        "identifiers": identifiers,
        "numeric_controls": controls,
    }


def _probe_elements() -> dict[str, dict[str, int]]:
    """Ask every derived element's ONE question of both fabrics and record
    who answered. This is `element_origin`'s only input.

    The counts recorded are PRESENCE (1 or 0), not cardinality: origin is a
    question about which fabric answers at all, and `SELECT EXISTS(...)`
    stops at the first row rather than seq-scanning a 1.3M-row table 113
    times. The falsification tests set a count directly, which still works
    -- the floor only ever asks `> 0`.

    See `PG_ELEMENT_PREFIX` above for how the population is derived and why
    it is subjects rather than predicates on the ledger side.
    """
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = %s AND table_type = 'BASE TABLE'",
                    (S,))
        our_tables = {r[0] for r in cur.fetchall()}
    with co_lender_pg_connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = %s AND table_type = 'BASE TABLE'",
                    (PEER_SCHEMA,))
        peer_tables = {r[0] for r in cur.fetchall()}

    probes: dict[str, dict[str, int]] = {}
    with pg_connect() as ours, ours.cursor() as our_cur, \
            co_lender_pg_connect() as theirs, theirs.cursor() as peer_cur:
        for table in sorted(our_tables | peer_tables):
            here = there = 0
            if table in our_tables:
                our_cur.execute(f'SELECT EXISTS(SELECT 1 FROM "{S}"."{table}")')
                here = int(our_cur.fetchone()[0])
            if table in peer_tables:
                peer_cur.execute(
                    f'SELECT EXISTS(SELECT 1 FROM "{PEER_SCHEMA}"."{table}")')
                there = int(peer_cur.fetchone()[0])
            # `local`/`peer` record who ANSWERED; `*_container` records
            # whether the table EXISTS in that schema at all. The pair is
            # what lets the failure message tell "present on neither
            # fabric" from "the table is there and nobody has loaded it
            # yet" -- two very different things that both resolve to
            # `unresolved` (Ruling T16-R7).
            probes[f"{PG_ELEMENT_PREFIX}{table}"] = {
                "local": here, "peer": there,
                "local_container": int(table in our_tables),
                "peer_container": int(table in peer_tables)}

    our_subjects = {b["s"]["value"] for b in _q(
        f"SELECT DISTINCT ?s FROM <{L}> WHERE {{ ?s ?p ?o }}")}
    peer_subjects = {b["s"]["value"] for b in _pq(
        f"SELECT DISTINCT ?s FROM <{PEER_LEDGER}> WHERE {{ ?s ?p ?o }}")}
    if not our_subjects or not peer_subjects:
        # Neither read may come back empty. An empty peer set would make
        # every graph element "local" and an empty local set would make them
        # all "remote"; either way the intersection is empty and the floor's
        # "no element answers on both" arm would pass while looking at
        # nothing. The same failure `real_nodes` refuses in aml_typology.py.
        raise RuntimeError(
            f"refusing to derive element origins: our ledger returned "
            f"{len(our_subjects)} subject(s) and the peer's returned "
            f"{len(peer_subjects)} -- an empty side makes the separability "
            f"check pass for free")
    for subject in sorted(our_subjects | peer_subjects):
        # A subject with no triples does not exist as a subject, so for
        # graph elements the container and the answer are the same thing.
        probes[f"{GRAPH_ELEMENT_PREFIX}{subject}"] = {
            "local": int(subject in our_subjects),
            "peer": int(subject in peer_subjects),
            "local_container": int(subject in our_subjects),
            "peer_container": int(subject in peer_subjects),
        }
    return probes


def _scan_for_peer_identifiers(peer_identifiers: set[str]
                                ) -> tuple[list[dict], dict[str, int],
                                           dict[str, int]]:
    """Every occurrence of a PEER identifier in THREE of our four stores.

    The denominator is counted independently within each store it does
    cover: every base table in `ccf_v2` (not a hand-picked "Wave 18"
    subset), every literal on our ledger, every table in the departmental
    SQLite file. A scan that selects the tables it thinks might be affected
    cannot see the one it did not think of.

    **MongoDB is NOT scanned** (Ruling T16-R5). Saying "four stores" was a
    coverage claim this function never met. Wave 18 writes passage text and
    document rows there and no peer identifier, but that is a statement
    about the loaders rather than a measurement, and this function does not
    make it. Whether a Mongo arm is needed is a behaviour question for
    whoever owns that decision; it is deliberately not answered here.

    Each store is scanned for a CONTROL needle in the same pass -- see
    `CONTROL_NEEDLES`. A store returning zero for its control has stopped
    looking, and `lineage_is_separable` fails rather than reporting a clean
    absence it did not establish.
    """
    hits: list[dict] = []
    control = dict.fromkeys(CONTROL_NEEDLES, 0)
    shape = {"postgres_tables": 0, "fluree_literals": 0, "sqlite_tables": 0}
    needle_re = "(" + "|".join(re.escape(i) for i in sorted(peer_identifiers)) + ")"

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = %s AND table_type = 'BASE TABLE' "
                    "ORDER BY 1", (S,))
        tables = [r[0] for r in cur.fetchall()]
        shape["postgres_tables"] = len(tables)
        for table in tables:
            cur.execute(
                f'SELECT count(*) FILTER (WHERE t ~ %s), '
                f'count(*) FILTER (WHERE position(%s in t) > 0) '
                f'FROM (SELECT to_jsonb(x)::text AS t '
                f'      FROM "{S}"."{table}" x) q',
                (needle_re, CONTROL_NEEDLES["postgres"]))
            n_hit, n_control = cur.fetchone()
            control["postgres"] += n_control
            if not n_hit:
                continue
            cur.execute(f'SELECT to_jsonb(x)::text FROM "{S}"."{table}" x '
                        f'WHERE to_jsonb(x)::text ~ %s', (needle_re,))
            for (payload,) in cur.fetchall():
                row = json.loads(payload)
                location = f"{S}.{table}"
                for identifier in sorted(peer_identifiers):
                    if identifier in payload:
                        hits.append({
                            "store": "postgres",
                            "location": location,
                            "identifier": identifier,
                            "declares_remote": declares_remote(
                                "postgres", location, row, peer_identifiers),
                        })

    literals = _q(f"SELECT ?s ?p ?o FROM <{L}> WHERE "
                  f"{{ ?s ?p ?o . FILTER(isLiteral(?o)) }}")
    shape["fluree_literals"] = len(literals)
    for b in literals:
        value = b["o"]["value"]
        if CONTROL_NEEDLES["fluree"] in value:
            control["fluree"] += 1
        for identifier in sorted(peer_identifiers):
            if identifier in value:
                hits.append({
                    "store": "fluree",
                    "location": f"{local_name(b['p']['value'])} on "
                                f"{local_name(b['s']['value'])}",
                    "identifier": identifier,
                    "declares_remote": False,
                })

    con = sqlite3.connect(SQLITE_PATH)
    try:
        tables = [r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'")]
        shape["sqlite_tables"] = len(tables)
        for table in tables:
            cols = [r[1] for r in con.execute(f'PRAGMA table_info("{table}")')]
            if not cols:
                continue
            blob = " || ".join(f'coalesce(cast("{c}" as text), \'\')'
                               for c in cols)
            control["sqlite"] += con.execute(
                f'SELECT count(*) FROM "{table}" WHERE instr({blob}, ?) > 0',
                (CONTROL_NEEDLES["sqlite"],)).fetchone()[0]
            for identifier in sorted(peer_identifiers):
                n = con.execute(
                    f'SELECT count(*) FROM "{table}" WHERE instr({blob}, ?) > 0',
                    (identifier,)).fetchone()[0]
                for _ in range(n):
                    hits.append({
                        "store": "sqlite",
                        "location": table,
                        "identifier": identifier,
                        "declares_remote": False,
                    })
    finally:
        con.close()

    return hits, control, shape


def load_context(as_of: str | None = None) -> Context:
    """One snapshot of both fabrics. Read-only, start to finish."""
    if not co_lender_configured():
        raise RuntimeError(
            "the co-lender fabric is not configured, so five of the six "
            "floors have nothing to check. Refusing to run rather than "
            "reporting the local half green -- set CO_LENDER_FLUREE_URL, "
            "CO_LENDER_PGHOST and CO_LENDER_PGUSER (see .env.example).")

    from generators.generate_peer_positions import AS_OF

    participations, our_commitments = _load_participations()
    members, debt_keys = _load_our_postgres()
    peer = _load_peer()
    open_votes, postures = _load_vote()
    hits, control, leak_shape = _scan_for_peer_identifiers(peer["identifiers"])

    return Context(
        as_of=as_of or AS_OF.isoformat(),
        envelopes=_load_envelopes(),
        vote_postures=postures,
        open_vote_iris=open_votes,
        participations=participations,
        our_commitments=our_commitments,
        members=members,
        context_debt_federation_keys=debt_keys,
        documents=_load_documents(participations),
        peer_positions=peer["positions"],
        declarations=peer["declarations"],
        peer_fabric_cells=peer["cells"],
        peer_scan_shape=peer["shape"],
        peer_numeric_controls=peer["numeric_controls"],
        peer_identifiers=peer["identifiers"],
        element_probes=_probe_elements(),
        local_identifier_hits=hits,
        control_hits=control,
        leak_scan_shape=leak_shape,
    )


# ===========================================================================
# The six floors
# ===========================================================================

def shares_are_sourced(ctx: Context | None = None) -> tuple[bool, str]:
    """FLOOR 1. Every share's cited offset resolves, in the RE-EXTRACTED
    source filing, to the lender name it claims, with its amount present at
    that row. **No share was invented.**

    Replaces the deleted `shares_reconcile` (Ruling T16-PRE, in the module
    docstring). Nothing here reads `facility.commitment_amount` and nothing
    sums shares against a facility total.

    Three sub-conditions, each able to fail on its own:

    1. The span is in bounds in the filing text as re-extracted TODAY. A
       drifted extractor moves every offset and this is where that shows.
    2. The span resolves to the lender the node claims -- by canonical name
       equality against the member's Postgres `legal_name`, or by the
       member's own declared filed-name variants for the cases where the
       GLEIF legal name and the filed string are genuinely different
       institutions' worth of different ("M&T BANK, N.A." vs
       "Manufacturers and Traders Trust Company"). Which route resolved each
       share is counted and reported.
    3. The amount the node claims is present in the filing within
       `AMOUNT_WINDOW_CHARS` of the end of that name -- at that ROW.

    Task 11b's fix round proved "the offset resolves to non-empty text" is
    NOT the same claim as "the offset resolves to the right text": four
    citations shipped resolving to real, non-empty, entirely unrelated
    clauses. Sub-condition 2 is that lesson applied to shares.

    **RULING T16-R4 -- the scope of sub-condition 2, stated honestly.** For
    the shares resolved by canonical name equality, the check is independent
    of the producer: the GLEIF legal name and the filed span are compared
    through a normalisation that knows nothing about which member the loader
    picked. For the shares resolved by the VARIANT route, it is not:
    `raw_names` is `resolve_syndicate_institutions`'s own grouping output and
    `canonical_key` is imported from that same generator, so what is
    established for those is offset integrity, amount-at-row, and *"this span
    is a name the resolver assigned to this member"* -- not *"this span names
    this institution"*. Misattribution BETWEEN EXISTING MEMBERS is still
    caught either way, which is the failure that actually threatens the
    estate and which falsification row 1 demonstrates. The per-route counts
    are printed on every run so the variant route quietly widening is visible
    rather than absorbed.

    What would make this fail: a participation re-pointed at a different
    member, an offset displaced anywhere else in the document, an amount
    that is not the one the filed row carries, a filing missing from
    `sources/ex10/`, or a lei-less member's participations silently dropping
    out of the read (checked against an independent count below).
    """
    ctx = ctx or load_context()
    from generators.resolve_syndicate_institutions import canonical_key

    total_nodes = _count(f"SELECT (COUNT(DISTINCT ?p) AS ?n) FROM <{L}> "
                         f"WHERE {{ ?p a <{EX_SYNDICATE_PARTICIPATION}> }}")
    if not ctx.participations:
        return False, "no SyndicateParticipation nodes read at all"
    if len(ctx.participations) != total_nodes:
        return False, (
            f"read {len(ctx.participations)} participation row(s) but the "
            f"ledger holds {total_nodes} SyndicateParticipation node(s) -- "
            f"the shares this floor cannot see are the ones it cannot fail "
            f"on")

    problems: list[str] = []
    by_route = collections.Counter()
    max_amount_distance = -1

    for part in ctx.participations:
        label = f"{part['facility_id']}/{part['member_id']}"
        text = ctx.documents.get(part["document"])
        if not text:
            problems.append(f"{label}: {part['document']} re-extracts to no text")
            continue
        start, end = part["start"], part["end"]
        if not (0 <= start < end <= len(text)):
            problems.append(f"{label}: offset {start}-{end} out of bounds in "
                            f"{part['document']} ({len(text)} chars)")
            continue
        span = text[start:end]

        member = ctx.members.get(part["member_id"])
        if member is None:
            problems.append(f"{label}: member_id resolves to no "
                            f"{S}.syndicate_member row")
            continue
        keys = {canonical_key(n) for n in member["raw_names"]}
        if canonical_key(span) == canonical_key(member["legal_name"]):
            by_route["canonical name equality"] += 1
        elif canonical_key(span) in keys:
            by_route["declared filed-name variant"] += 1
        else:
            problems.append(
                f"{label}: cited span {span!r} does not resolve to "
                f"{member['legal_name']!r} (declared filed names: "
                f"{member['raw_names']})")
            continue

        needle = f"{part['commitment_usd']:,}"
        window = text[end:end + AMOUNT_WINDOW_CHARS]
        at = window.find(needle)
        if at < 0:
            problems.append(
                f"{label}: amount {needle} is not within "
                f"{AMOUNT_WINDOW_CHARS} chars of that lender's name in "
                f"{part['document']} -- window {window[:80]!r}")
            continue
        max_amount_distance = max(max_amount_distance, at)

    if problems:
        return False, (f"{len(problems)} of {len(ctx.participations)} share(s) "
                       f"unsupported: " + "; ".join(problems[:4]))
    routes = ", ".join(f"{n} by {route}" for route, n in sorted(by_route.items()))
    return True, (
        f"{len(ctx.participations)} of {total_nodes} participation(s) checked "
        f"across {len(ctx.documents)} re-extracted filing(s); every span in "
        f"bounds; {routes}; every amount found at its own row, furthest "
        f"{max_amount_distance} of {AMOUNT_WINDOW_CHARS} chars past the name")


def envelopes_are_asymmetric(ctx: Context | None = None) -> tuple[bool, str]:
    """FLOOR 2. At least two bilateral disclosure envelopes whose
    request-set and disclose-set DIFFER, compared as sets.

    Counts the unit the condition names: ENVELOPES whose two scopes differ.
    Not scope rows, not counterparties, not elements. No `asymmetric` column
    exists in this estate and none is read.

    Both scopes must also be non-empty. An envelope that discloses nothing
    trivially "differs" from its request set and would inflate the count
    while proving the opposite of what §F wants -- a negotiated asymmetry,
    not a missing half.

    What would make this fail: symmetric scopes (the test sets
    `disclose = request` and requires a "no"), an empty scope on either
    side, or fewer than two envelopes.
    """
    ctx = ctx or load_context()
    if len(ctx.envelopes) < 2:
        return False, (f"{len(ctx.envelopes)} DisclosureEnvelope node(s) in "
                       f"the ledger; §F needs >= 2")

    empty = [local_name(e) for e, s in sorted(ctx.envelopes.items())
             if not s["request"] or not s["disclose"]]
    if empty:
        return False, (f"envelope(s) with an empty scope on one side: "
                       f"{empty} -- an empty disclose set differs from any "
                       f"request set and is a missing term, not a "
                       f"negotiated one")

    asymmetric = []
    for env, scopes in sorted(ctx.envelopes.items()):
        request, disclose = scope_sets(scopes)
        if request != disclose:
            asymmetric.append(
                f"{local_name(env)}: requests {sorted(request)} vs discloses "
                f"{sorted(disclose)}")
    if len(asymmetric) < 2:
        return False, (f"{len(asymmetric)} of {len(ctx.envelopes)} envelope(s) "
                       f"have differing scopes; §F needs >= 2")
    return True, (f"{len(asymmetric)} of {len(ctx.envelopes)} envelope(s) "
                  f"asymmetric -- " + "; ".join(asymmetric))


def precision_is_mixed(ctx: Context | None = None) -> tuple[bool, str]:
    """FLOOR 3. On the PEER fabric: one counterparty discloses exactly, one
    discloses only a band, and the peer's fabric carries no exact figure for
    the banded counterparty.

    **Ruling T14-R1 governs the wording and the scope.** The claim is NOT
    that the concealed figure is unknowable -- it is a filed commitment
    schedule row, it is public, and our own ledger holds it as
    `ex:commitmentUsd` on a `SyndicateParticipation`. The claim is about
    what the PEER discloses. Every scan below runs over
    `ctx.peer_fabric_cells`, which is built only from the peer's tables and
    the peer's ledger literals; our ledger is used to LOCATE the figure and
    is deliberately never scanned for it.

    `ex:disclosurePrecision` exists on the peer ledger and is never read as
    the answer. Precision is recomputed from the position rows themselves.

    The denominator is counted independently. Banded counterparties are
    identified, and then EVERY row the peer holds for them is enumerated --
    not only the rows already null in `share_usd`. A check that selects by
    the property it polices cannot see that property missing; this exact bug
    was found twice in Wave 15 and again in Task 13 of this wave.

    **The absence scan carries a positive control and matches numerically.**
    This arm's green answer is an ABSENCE, which is the one kind that can be
    permanently wrong with nothing looking broken. Two corrections from fix
    round 1 (Important 1): the match is `numeric_values`, so every
    representation of the figure -- `70000000`, `70,000,000`,
    `$70,000,000.00`, `7.0E7` -- normalises to the same float instead of the
    previous substring test which found only the first two; and every figure
    the peer's own TYPED numeric columns say it holds must be findable in the
    text cast of its tables, or the floor FAILS rather than reporting a clean
    absence it never established. That is exactly what `CONTROL_NEEDLES` does
    for the leak scan two floors down.

    What would make this fail: the band peer gaining an exact figure in any
    row (the test plants one), every counterparty going exact, a degenerate
    band whose bounds meet, a band that does not bracket the filed figure,
    the concealed figure appearing in any peer column or peer-ledger literal
    in any of its four representations, or the scan losing sight of its own
    control values. Every one of those six has a falsification test.
    """
    ctx = ctx or load_context()
    rows = ctx.peer_positions
    if not rows:
        return False, "no rows in the peer's position table at all"

    exact_cps = {r["counterparty"] for r in rows if r["share_usd"] is not None}
    band_cps = {r["counterparty"] for r in rows
                if r["share_usd"] is None
                and r["band_low"] is not None and r["band_high"] is not None}
    if not exact_cps:
        return False, (f"no counterparty discloses an exact figure across "
                       f"{len(rows)} peer position row(s)")
    if not band_cps:
        return False, (f"no counterparty discloses only a band across "
                       f"{len(rows)} peer position row(s) -- the "
                       f"mixed-precision condition has nothing behind it")
    both = exact_cps & band_cps
    if both:
        return False, (f"counterparty(ies) {sorted(both)} disclose BOTH ways, "
                       f"so precision is not a property of the counterparty "
                       f"and this floor proves nothing")

    # Independent denominator: every row for the banded counterparties, not
    # the rows already selected as banded.
    problems: list[str] = []
    band_rows = 0
    for cp in sorted(band_cps):
        cp_rows = [r for r in rows if r["counterparty"] == cp]
        band_rows += len(cp_rows)
        for r in cp_rows:
            if r["share_usd"] is not None:
                problems.append(f"{cp} on {r['facility_id']}: exact "
                                f"{r['share_usd']} despite banding")
            elif r["band_low"] is None or r["band_high"] is None:
                problems.append(f"{cp} on {r['facility_id']}: neither an "
                                f"exact figure nor a band")
            elif int(r["band_low"]) >= int(r["band_high"]):
                problems.append(f"{cp} on {r['facility_id']}: degenerate band "
                                f"[{r['band_low']}, {r['band_high']}] -- an "
                                f"exact figure wearing a costume")
    if problems:
        return False, "; ".join(problems[:4])

    # The needle: what each band conceals, located on OUR ledger (public,
    # filed, and resolvable there by design -- Ruling T14-R1) and then hunted
    # ONLY across the peer fabric.
    needles: dict[tuple[str, str], int] = {}
    for cp in sorted(band_cps):
        for r in rows:
            if r["counterparty"] != cp:
                continue
            figure = ctx.our_commitments.get((cp, r["facility_id"]))
            if figure is None:
                return False, (
                    f"{cp} holds a banded position on {r['facility_id']} but "
                    f"our ledger carries no filed commitment for that pair -- "
                    f"there is no concealed figure, and a scan with no needle "
                    f"proves nothing")
            if not int(r["band_low"]) < figure < int(r["band_high"]):
                return False, (
                    f"{cp} on {r['facility_id']}: band [{r['band_low']}, "
                    f"{r['band_high']}] does not contain the filed figure "
                    f"{figure:,} -- the band is a false disclosure")
            needles[(cp, r["facility_id"])] = figure

    if ctx.peer_scan_shape["cells"] == 0:
        return False, ("the peer fabric yielded no cells to scan -- an "
                       "absence scan over nothing reports green while "
                       "looking at nothing")

    # Numeric, not textual. `str(70000000) in value` finds "70000000.00" and
    # misses "70,000,000", "$70,000,000.00" and "7.0E7" -- and an ABSENCE
    # reported by a matcher that cannot see the needle's own formatting is
    # permanently wrong with nothing looking broken. `numeric_values`
    # normalises every representation to the same float.
    found: dict[float, list[str]] = collections.defaultdict(list)
    for location, value in ctx.peer_fabric_cells:
        for number in numeric_values(value):
            found[number].append(location)

    # POSITIVE CONTROL -- the discipline `CONTROL_NEEDLES` applies to the
    # leak scan, applied here to the arm that carries the T14-R1 claim.
    # `ctx.peer_numeric_controls` is read by its own query from the peer's
    # TYPED numeric columns; every one of those figures MUST be findable in
    # the text cast of the peer's own tables. If it is not, this scan is not
    # seeing what it says it searched, and the correct answer is FAIL rather
    # than a clean absence nobody established.
    blind = sorted(v for v in ctx.peer_numeric_controls if v not in found)
    if blind:
        return False, (
            f"the absence scan cannot find {len(blind)} of "
            f"{len(ctx.peer_numeric_controls)} control value(s) that the "
            f"peer's own numeric columns say are there "
            f"({[f'{v:,.0f}' for v in blind[:4]]}) -- the scan is looking at "
            f"nothing or the matcher cannot read the peer's number format, "
            f"so its clean result on the concealed figure establishes "
            f"nothing")

    leaks = [f"{figure:,} ({cp} on {fid}) in {location}"
             for (cp, fid), figure in needles.items()
             for location in found.get(float(figure), [])]
    if leaks:
        return False, ("the concealed figure appears on the peer fabric: "
                       + "; ".join(leaks[:4]))

    return True, (
        f"{len(rows)} peer position row(s): {len(exact_cps)} counterparty(ies) "
        f"exact, {len(band_cps)} band-only over all {band_rows} of its row(s); "
        f"{len(needles)} concealed figure(s) "
        f"({', '.join(f'{v:,}' for v in sorted(needles.values()))}) absent "
        f"from {ctx.peer_scan_shape['cells']} peer cell(s) "
        f"({ctx.peer_scan_shape['columns']} column(s) of "
        f"{ctx.peer_scan_shape['tables']} peer table(s), plus the peer "
        f"ledger's literals) yielding {len(found)} distinct number(s), with "
        f"all {len(ctx.peer_numeric_controls)} positive control(s) found. "
        f"PEER FABRIC ONLY (T14-R1): our own ledger holds the filed figure "
        f"and is deliberately not scanned")


def vote_postures_diverge(ctx: Context | None = None) -> tuple[bool, str]:
    """FLOOR 4. The one open amendment vote carries at least two DISTINCT
    postures, read from the postures themselves.

    §F asks for a live amendment vote with divergent postures. A vote where
    everyone agrees satisfies the count and not the condition. No
    `divergent` flag exists in this estate and none is read; the distinct
    `ex:votePosture` values on the actual `ex:votesOn` edges are what is
    counted.

    Exactly one open vote is required. With two, "THE open vote" names
    nothing, and a posture set pooled across both would report a divergence
    that neither vote exhibits.

    What would make this fail: unanimity (the test flattens every posture to
    `consent` and requires a "no"), a single voter, no open vote, or two.
    """
    ctx = ctx or load_context()
    if len(ctx.open_vote_iris) != 1:
        return False, (f"{len(ctx.open_vote_iris)} open AmendmentVote(s): "
                       f"{[local_name(v) for v in ctx.open_vote_iris]} -- §F "
                       f"needs exactly one for 'the open vote' to mean "
                       f"anything")
    if len(ctx.vote_postures) < 2:
        return False, (f"{len(ctx.vote_postures)} voter(s) on "
                       f"{local_name(ctx.open_vote_iris[0])} -- one voter "
                       f"cannot diverge from anyone")

    tally = collections.Counter(ctx.vote_postures.values())
    if len(tally) < 2:
        return False, (f"all {len(ctx.vote_postures)} voter(s) on "
                       f"{local_name(ctx.open_vote_iris[0])} hold the same "
                       f"posture: {sorted(tally)}")
    return True, (
        f"1 open vote ({local_name(ctx.open_vote_iris[0])}), "
        f"{len(ctx.vote_postures)} voter(s), {len(tally)} distinct posture(s): "
        + ", ".join(f"{p}x{n}" for p, n in sorted(tally.items())))


def federation_bounds_bind(ctx: Context | None = None) -> tuple[bool, str]:
    """FLOOR 5. The peer's product declarations exercise all three federation
    bounds rather than merely carrying values for them.

    Three sub-conditions, each able to fail on its own:

    1. **Latency.** At least one declared latency above
       `MAX_FEDERATION_LATENCY_MS` (§B's 5s), so fail-closed is observable,
       AND at least one below it. A fabric where every peer times out
       demonstrates nothing about fail-closed; it just looks broken.
    2. **Attestation.** At least one unattested claim, so Context Debt is
       exercised, AND at least one attested one to contrast it with. The
       unattested declaration must also appear on OUR side as a
       `context_debt` row keyed to it -- an unattested claim nothing
       recorded is not debt, it is a gap.
    3. **TTL.** `min(remote) < LOCAL_COMPOSITE_TTL_SECONDS < max(remote)`.
       The lower bound is the floor §F names; the upper bound is what stops
       it binding trivially, because if every remote TTL were short the
       "shortest of them wins" rule would never be tested.

    `attestation` is read as PRESENCE (null or not), never as a verdict --
    nothing here trusts what a signature block says about itself.

    What would make this fail: every remote TTL long (the test sets 86,400s
    and requires a "no"), every declaration fast, every claim attested, or
    an unattested claim with no Context Debt row on our side.
    """
    ctx = ctx or load_context()
    rows = ctx.declarations
    if not rows:
        return False, "no peer product declarations at all"

    slow = [r for r in rows if r["declared_latency_ms"] > MAX_FEDERATION_LATENCY_MS]
    fast = [r for r in rows if r["declared_latency_ms"] <= MAX_FEDERATION_LATENCY_MS]
    if not slow:
        return False, (f"no declaration exceeds the {MAX_FEDERATION_LATENCY_MS}ms "
                       f"bound (declared: "
                       f"{sorted(r['declared_latency_ms'] for r in rows)}) -- "
                       f"fail-closed could not be observed")
    if not fast:
        return False, (f"every one of {len(rows)} declaration(s) exceeds the "
                       f"{MAX_FEDERATION_LATENCY_MS}ms bound -- with no "
                       f"contrast the fabric just looks broken")

    unattested = [r for r in rows if r["attestation"] is None]
    attested = [r for r in rows if r["attestation"] is not None]
    if not unattested:
        return False, (f"all {len(rows)} declaration(s) carry an attestation "
                       f"-- Context Debt is never exercised")
    if not attested:
        return False, (f"all {len(rows)} declaration(s) are unattested -- "
                       f"nothing contrasts the missing one")
    undebted = sorted(r["declaration_id"] for r in unattested
                      if r["declaration_id"] not in ctx.context_debt_federation_keys)
    if undebted:
        return False, (f"unattested declaration(s) {undebted} have no "
                       f"federation_attestation row in {S}.context_debt -- an "
                       f"unattested claim nobody recorded is a gap, not debt")

    ttls = [int(r["declared_ttl_seconds"]) for r in rows]
    if not min(ttls) < LOCAL_COMPOSITE_TTL_SECONDS:
        return False, (f"shortest remote TTL is {min(ttls)}s and the local "
                       f"composite is {LOCAL_COMPOSITE_TTL_SECONDS}s, so no "
                       f"remote TTL binds below it")
    if not LOCAL_COMPOSITE_TTL_SECONDS < max(ttls):
        return False, (f"longest remote TTL is {max(ttls)}s, at or below the "
                       f"{LOCAL_COMPOSITE_TTL_SECONDS}s local composite -- "
                       f"every remote TTL binds and the shortest-wins rule "
                       f"is untested")

    return True, (
        f"{len(rows)} declaration(s): latency "
        f"{sorted(r['declared_latency_ms'] for r in rows)}ms against a "
        f"{MAX_FEDERATION_LATENCY_MS}ms bound ({len(slow)} over, {len(fast)} "
        f"under); {len(unattested)} unattested vs {len(attested)} attested, "
        f"all recorded as context_debt; TTLs {sorted(ttls)}s bracket the "
        f"{LOCAL_COMPOSITE_TTL_SECONDS}s local composite "
        f"({min(ttls)} < {LOCAL_COMPOSITE_TTL_SECONDS} < {max(ttls)})")


def lineage_is_separable(ctx: Context | None = None) -> tuple[bool, str]:
    """FLOOR 6. Every peer-sourced element is distinguishable from a local
    one, and no peer claim is reachable through a path that marks it local.

    **Origin is derived, not read.** `ctx.element_origin` is computed from
    `ctx.element_probes`, which record which fabric ANSWERED each element's
    one question -- the same SPARQL asked of both ledgers, the same table
    name counted in both schemas. Nothing in either fabric stores an origin
    and nothing here reads a column, flag or literal that says "remote". A
    marker somebody wrote down cannot establish that no peer claim is
    reachable locally; only asking both fabrics can.

    **The population is derived, too (Ruling T16-R2).** "Every element" used
    to mean eight hand-picked ones, and an element absent from a hand-written
    list can never fail this floor. It now means every base table in either
    Postgres schema and every subject on either ledger -- read from the
    estate on every run, so a table or a node any wave adds joins the
    population without anybody remembering to add it. `PG_ELEMENT_PREFIX`
    above carries the reasoning, including why the ledger side is SUBJECTS
    and not predicates (the two ledgers deliberately share vocabulary;
    sharing a term is not sharing a claim) and what the population does not
    cover.

    Two sub-conditions:

    1. **Every element resolves on exactly one fabric.** An element
       answering on BOTH is precisely a peer claim reachable through a local
       path -- an assembler could satisfy it without ever crossing the
       boundary, and the federation would be a fiction. An element answering
       on NEITHER is an element this floor cannot see, and a floor that
       cannot see something cannot fail on it. At least one element must
       land on each side, or "separable" is vacuous.
    2. **No peer identifier sits in a local row that fails to declare the
       claim remote.** Scanned over every base table in `ccf_v2`, every
       literal on our ledger and every table in the departmental SQLite file
       -- the full denominator, never a Wave 18 subset. The one sanctioned
       exception is `declares_remote()`: a `context_debt` row of kind
       `federation_attestation` naming a real peer identifier and saying so
       in its own text. Every store is scanned for a CONTROL needle in the
       same pass, so a scan that has stopped looking fails instead of
       reporting a clean absence it never established.

    What would make this fail: a peer element also answering locally (the
    test sets its local probe count and requires a "no"), an estate with
    nothing remote at all, a peer identifier planted in a local row, or any
    store's control needle coming back zero.
    """
    ctx = ctx or load_context()
    origin = ctx.element_origin
    if not origin:
        return False, "no elements probed at all"

    both = sorted(n for n, o in origin.items() if o == "both")
    empty, absent = [], []
    for name in sorted(n for n, o in origin.items() if o == "unresolved"):
        probe = ctx.element_probes[name]
        # Ruling T16-R7: an EMPTY table is a normal estate state that
        # nonetheless fails this floor, and a reader who is not told which
        # case they have will spend an hour hunting a separability defect
        # that is not there. Both still fail; only the message differs.
        if probe.get("local_container") or probe.get("peer_container"):
            empty.append(name)
        else:
            absent.append(name)
    if both or empty or absent:
        parts = []
        if both:
            parts.append(
                f"{len(both)} element(s) answer on BOTH fabrics -- a peer "
                f"claim reachable through a local path: "
                + "; ".join(f"{n} (local="
                            f"{ctx.element_probes[n]['local']}, peer="
                            f"{ctx.element_probes[n]['peer']})"
                            for n in both[:4]))
        if empty:
            parts.append(
                f"{len(empty)} base table(s) EXIST but hold no rows, so no "
                f"fabric answers for them -- this is an unloaded table, not "
                f"a separability defect, but an element nobody can see is "
                f"one this floor could never fail on, so it fails loudly "
                f"(known-issues §35): {empty[:6]}")
        if absent:
            parts.append(
                f"{len(absent)} element(s) are present on NEITHER fabric: "
                f"{absent[:6]}")
        return False, " | ".join(parts)

    local_elements = sorted(n for n, o in origin.items() if o == "local")
    remote_elements = sorted(n for n, o in origin.items() if o == "remote")
    if not remote_elements or not local_elements:
        return False, (f"{len(local_elements)} local and "
                       f"{len(remote_elements)} remote element(s) -- with one "
                       f"side empty, 'distinguishable by origin' is vacuous")

    blind = sorted(store for store, n in ctx.control_hits.items() if n == 0)
    if blind:
        return False, (f"the leak scan found none of its control needle(s) in "
                       f"{blind} -- the scan is looking at nothing, so its "
                       f"clean result establishes nothing "
                       f"(controls: {ctx.control_hits})")

    leaks = [h for h in ctx.local_identifier_hits if not h["declares_remote"]]
    if leaks:
        return False, (
            f"{len(leaks)} peer identifier(s) sit in local rows that do not "
            f"declare the claim remote: "
            + "; ".join(f"{h['identifier']} in {h['store']} {h['location']}"
                        for h in leaks[:4]))

    excused = len(ctx.local_identifier_hits)
    shown = [local_name(e) if e.startswith(GRAPH_ELEMENT_PREFIX) else e
             for e in remote_elements[:6]]
    n_pg = sum(1 for e in ctx.element_probes if e.startswith(PG_ELEMENT_PREFIX))
    n_graph = len(ctx.element_probes) - n_pg
    return True, (
        f"{len(local_elements)} local / {len(remote_elements)} remote "
        f"element(s) over a DERIVED population of {len(ctx.element_probes)} "
        f"({n_pg} Postgres table(s) across both schemas, {n_graph} ledger "
        f"subject(s) across both ledgers; MongoDB and SQLite contribute no "
        f"elements to the ORIGIN POPULATION -- the peer provisions "
        f"neither -- while the LEAK SCAN below covers SQLite but not "
        f"MongoDB), each answering on exactly one fabric "
        f"(remote: {shown}); {len(ctx.peer_identifiers)} peer "
        f"identifier(s) scanned across "
        f"{ctx.leak_scan_shape['postgres_tables']} ccf_v2 table(s), "
        f"{ctx.leak_scan_shape['fluree_literals']} ledger literal(s) and "
        f"{ctx.leak_scan_shape['sqlite_tables']} SQLite table(s) "
        f"(controls found {ctx.control_hits}); {excused} local occurrence(s), "
        f"all of them context_debt rows declaring the claim remote")


# ===========================================================================
# Rendering (house style, see validators/conditions.py)
# ===========================================================================

FLOORS = [
    ("1. shares are sourced (offset -> filed row)", shares_are_sourced),
    ("2. envelopes asymmetric (scopes as sets)", envelopes_are_asymmetric),
    ("3. precision mixed (peer fabric only)", precision_is_mixed),
    ("4. vote postures diverge (read live)", vote_postures_diverge),
    ("5. federation bounds bind (latency/attest/TTL)", federation_bounds_bind),
    ("6. lineage separable (origin derived)", lineage_is_separable),
]


def render(state: str, condition: str, detail: str) -> str:
    return f"  [{state}] {condition:48s} {detail}"


def main() -> int:
    ctx = load_context()
    print("SYNDICATED-LENDING-CO-LENDER — §F floors, recomputed from both "
          f"fabrics at as_of={ctx.as_of}\n")

    failures = 0
    for label, floor in FLOORS:
        ok, detail = floor(ctx)
        if not ok:
            failures += 1
        print(render("PASS" if ok else "FAIL", label, detail))

    print(f"\n  {len(FLOORS) - failures} passed · {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
