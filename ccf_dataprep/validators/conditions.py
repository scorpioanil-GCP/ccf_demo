#!/usr/bin/env python3
"""The conditions register — every §F `>= N` as an executable check.

A product that passes counts but fails a condition is not done. So each entry
here is a **query against loaded data**, not a tally: the question is whether
the condition is *satisfiable*, which is the only thing that makes the
behaviour demonstrable.

Structure mirrors the specs. Each check names the product it serves, the §F
floor, and the query that proves it. Checks for products whose wave has not
run yet report SKIP rather than FAIL, so this is runnable from Wave 1 onward.

    uv run validators/conditions.py           # all
    uv run validators/conditions.py --product corporate-family-tree

Exit code is non-zero if any non-skipped check fails.
"""

from __future__ import annotations

import argparse
import re

import psycopg
import sys
from dataclasses import dataclass

from ccf import fluree
from ccf.config import (
    AS_OF_IB,
    FLUREE_LEDGER_V2,
    IB_WINDOW_END,
    IB_WINDOW_START,
    PG_SCHEMA_V2,
    REPO_ROOT,
    SQLITE_PATH,
    pg_connect,
)

S = PG_SCHEMA_V2
L = FLUREE_LEDGER_V2
# Wave 8 correction -- see docs/known-issues.md §0.1. The previous constants
# named two properties that do not exist in FIBO. Because this validator held
# the same wrong constants as the loader, it agreed with itself and passed:
# a validator that shares a defect cannot detect it.
OWNS = ("https://spec.edmcouncil.org/fibo/ontology/FND/OwnershipAndControl/"
        "Ownership/owns")
CONTROLS = "https://spec.edmcouncil.org/fibo/ontology/FND/Relations/Relations/controls"
_CC = "https://spec.edmcouncil.org/fibo/ontology/BE/OwnershipAndControl/CorporateControl/"
GLOBAL_ULTIMATE = f"{_CC}hasGlobalUltimateParent"
DOMESTIC_ULTIMATE = f"{_CC}hasDomesticUltimateParent"
EX = "http://example.org/fibo/"
RDF_TYPE_IRI = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
RDFS_LABEL_IRI = "http://www.w3.org/2000/01/rdf-schema#label"
C_LEGAL_ENTITY_IRI = "https://www.omg.org/spec/Commons/Organizations/LegalEntity"
SPECIFIES_TRIGGER = ("https://spec.edmcouncil.org/fibo/ontology/SEC/Debt/"
                     "CollateralizedDebtObligations/specifiesTrigger")


#: The three crosswalk invariants, as SQL returning a COUNT OF VIOLATIONS.
#:
#: Module-level, and not inlined into the checks below, because
#: `validators/test_crosswalk_invariants.py` injects a violation of each into
#: a rolled-back transaction and requires the count to move. A harness holding
#: its own transcription of these queries would go on passing after the real
#: ones drifted -- the shape this file's own header warns about, where a
#: validator sharing a defect with the thing it checks agrees with itself.
CROSSWALK_INVARIANTS: dict[str, str] = {
    # WIDENED 2026-08-28, when Wave 20 gave the crosswalk a second legitimate
    # resolution target. This was `LEFT JOIN legal_entity USING (lei) WHERE
    # e.lei IS NULL`, which counted every no-LEI internal client as an orphan
    # the moment 30 of them landed -- the check's population outgrowing its
    # question, which is §53's shape exactly.
    #
    # The widening is of the RESOLUTION TARGET, not an exemption for the new
    # rows, and the two halves stay sharp rather than collapsing into "resolves
    # to something": a row WITH an LEI must still match a `legal_entity`, and a
    # row WITHOUT one must match an `internal_client`. A NULL-lei row that no
    # internal client backs is still an orphan, which is what makes this a
    # check and not a formality.
    "crosswalk rows pointing at no entity": f"""
        SELECT COUNT(*) FROM "{S}".crosswalk c
        LEFT JOIN "{S}".legal_entity e USING (lei)
        LEFT JOIN "{S}".internal_client i USING (internal_client_id)
        WHERE (c.lei IS NOT NULL AND e.lei IS NULL)
           OR (c.lei IS NULL AND i.internal_client_id IS NULL)""",
    # ADDED 2026-08-28 with the widening above, because the widening created
    # the hole. Once a NULL-lei crosswalk row is legitimate, the thing that
    # makes it legitimate -- an `internal_client` backing it -- needs its own
    # invariant in the other direction. A client the crosswalk cannot reach is
    # the same defect as a crosswalk row reaching nothing, and neither the old
    # check nor the widened one counts it.
    "internal clients no crosswalk row reaches": f"""
        SELECT COUNT(*) FROM "{S}".internal_client i
        LEFT JOIN "{S}".crosswalk c USING (internal_client_id)
        WHERE c.internal_client_id IS NULL""",
    "anchors with no internal client id": f"""
        SELECT COUNT(*) FROM "{S}".legal_entity e
        LEFT JOIN "{S}".crosswalk c USING (lei)
        WHERE e.is_anchor AND c.lei IS NULL""",
    "entities with internal data, no client id": f"""
        SELECT COUNT(*) FROM (
            SELECT borrower_lei AS lei FROM "{S}".facility
            UNION SELECT lei FROM "{S}".deal
            UNION SELECT lei FROM "{S}".coverage_assignment) t
        LEFT JOIN "{S}".crosswalk c USING (lei)
        WHERE c.lei IS NULL""",
}


@dataclass
class Check:
    product: str
    condition: str
    floor: int
    actual: int | None
    note: str = ""
    # True only when the CHECK ITSELF failed to execute (import error, a
    # broken SPARQL query, a Fluree outage, ...) as opposed to `actual is
    # None` meaning "the wave's precondition data does not exist yet". The
    # two must render differently: a genuinely-unrun wave is SKIP; a check
    # that blew up while trying to run is a FAIL, not a silent pass-through.
    errored: bool = False

    @property
    def state(self) -> str:
        if self.errored:
            return "FAIL"
        if self.actual is None:
            return "SKIP"
        return "PASS" if self.actual >= self.floor else "FAIL"

    def render(self) -> str:
        actual = "--" if self.actual is None else str(self.actual)
        return (f"  [{self.state}] {self.condition:44s} "
                f"{actual:>6} / {self.floor:<4} {self.note}")


def pg_scalar(cur, sql: str) -> int | None:
    try:
        cur.execute(sql)
        row = cur.fetchone()
        return int(row[0]) if row else 0
    except Exception:  # noqa: BLE001 — an absent table means the wave has not run
        return None


def fl_scalar(sparql: str) -> int | None:
    try:
        rows = fluree.query(sparql)["results"]["bindings"]
        return int(rows[0]["n"]["value"]) if rows else 0
    except Exception:  # noqa: BLE001
        return None


#: ISO 17442: a LEI is exactly 20 uppercase alphanumerics. This estate's own
#: synthetic identifiers are `SYN-` with hyphens (docs/ccf_dataprep_v2.md,
#: settled 2026-08-23) SPECIFICALLY so the two can never be confused -- which
#: only works if something actually checks.
_REAL_LEI = re.compile(r"[A-Z0-9]{20}")


def count_real_leis(leis) -> int:
    """Distinct REAL GLEIF LEIs among `leis`, ignoring synthetic identifiers.

    Two mistakes are being corrected here, and they pull in opposite
    directions, which is why the fix is a function rather than a tighter
    SPARQL pattern.

    ADJECTIVE: the check this backs is named "entities carrying a real LEI",
    and its old measure counted every `ex:lei` value in the ledger. Wave 17
    loaded 201 `SYN-AML-` parties carrying `ex:lei`, so the number inflated by
    201 the moment AML shipped, and would inflate again with every synthetic
    population after it.

    NOUN: the old measure was `COUNT(?s)`, which counts BINDINGS. The live
    ledger returns 449 bindings for 434 distinct values because some nodes
    carry more than one `ex:lei`. A duplicate is not a second entity.

    Measured 2026-08-28: 449 reported, 233 real. The floor is 50, so this
    passed before and passes after -- it was never going to announce itself.
    """
    return len({s for s in (str(l).strip() for l in leis if l)
                if _REAL_LEI.fullmatch(s)})


def real_lei_entities() -> int | None:
    """`count_real_leis` over the live ledger, None if Fluree is unreachable."""
    try:
        rows = fluree.query(
            f"SELECT ?s ?l FROM <{L}> WHERE {{ ?s <{EX}lei> ?l }}"
        )["results"]["bindings"]
    except Exception:  # noqa: BLE001
        return None
    return count_real_leis(b["l"]["value"] for b in rows)


def mongo_count(collection: str, query: dict | None = None) -> int | None:
    try:
        from ccf.config import mongo_db
        return mongo_db()[collection].count_documents(query or {})
    except Exception:  # noqa: BLE001 — empty collection means the wave has not run
        return None


def sqlite_scalar(path, sql: str) -> int | None:
    """Same contract as `pg_scalar` above, for the departmental store --
    NARROWED, unlike `pg_scalar`/`fl_scalar`/`mongo_count`. Those three are
    pre-existing and out of this task's scope; this one is new code written
    for Wave 17 and feeds one of the four direct §F counts, so it follows
    the brief's own rule: only a real missing-table precondition may SKIP,
    everything else FAILs loud.

    Returns None ONLY for the genuine "wave not yet run" precondition --
    the file absent, or `sqlite3.OperationalError` naming "no such table".
    Any other `sqlite3` error (a locked file, a permissions error, a bad
    query) raises `CheckFailure` so the caller renders FAIL, not SKIP --
    the same narrowing `_aml_delegate` below applies to
    `psycopg.errors.UndefinedTable`.
    """
    import sqlite3

    if not path.exists():
        return None  # the departmental store genuinely does not exist yet
    try:
        with sqlite3.connect(path) as con:
            row = con.execute(sql).fetchone()
        return int(row[0]) if row else 0
    except sqlite3.OperationalError as exc:
        if "no such table" in str(exc):
            return None  # legitimate SKIP -- table not loaded yet
        raise CheckFailure(f"sqlite_scalar query failed: {exc!r}") from exc
    except Exception as exc:  # noqa: BLE001 — any other failure must FAIL
        raise CheckFailure(f"sqlite_scalar query failed: {exc!r}") from exc


def mongo_distinct(collection: str, field: str) -> int | None:
    """Distinct VALUES of a field, not documents.

    RULING F48: `mongo_count("trigger_anchor")` counts anchor documents, while
    the condition it backs is named "thresholds anchored". Those are the same
    number today (10 and 10) and diverge the moment one threshold carries two
    anchors -- the count would rise while coverage fell. The plan said to add
    no new helpers, but counting the unit the condition names needs one, and
    this mirrors fl_distinct directly below.
    """
    try:
        from ccf.config import mongo_db
        return len(mongo_db()[collection].distinct(field))
    except Exception:  # noqa: BLE001 — absent collection means the wave has not run
        return None


def anchored_thresholds() -> int | None:
    """Distinct thresholds that BOTH exist in Fluree and carry a Mongo anchor.

    Neither side alone is the quantity the condition names. Mongo can hold an
    anchor for something that is not a threshold, and Fluree can hold a
    threshold nobody anchored; counting either side lets one error hide the
    other.
    """
    try:
        from ccf.config import mongo_db
        anchors = set(mongo_db()["trigger_anchor"].distinct("trigger_id"))
        rows = fluree.query(
            f"SELECT ?t FROM <{L}> WHERE {{ ?t <{EX}thresholdValue> ?v }}"
        )["results"]["bindings"]
        thresholds = {r["t"]["value"].replace(EX, "").replace("abs-trigger-", "")
                      for r in rows}
        return len(anchors & thresholds)
    except Exception:  # noqa: BLE001
        return None


def narrowing_deals(cur) -> int | None:
    """Deals whose 60+ delinquency closes on its trigger for >= 3 straight periods.

    Recomputed from `abs_cohort_performance`, never read from
    `published_delinquency_percent`. A RUN of consecutive narrowing periods,
    not a count of them: 6-of-11-plus-positive-net is satisfied by a square
    wave with zero drift, and §F's bullet exists precisely to distinguish a
    trajectory from a static distance.
    """
    try:
        cur.execute(f"""
            SELECT c.deal_id, c.period,
                   100 * SUM(c.delinquent_60_plus_balance) / NULLIF(SUM(c.pool_balance), 0)
            FROM "{S}".abs_cohort_performance c
            GROUP BY c.deal_id, c.period ORDER BY c.deal_id, c.period""")
        series: dict[str, list] = {}
        for deal, period, ratio in cur.fetchall():
            series.setdefault(deal, []).append(ratio)
        n = 0
        for ratios in series.values():
            run = best = 0
            for a, b in zip(ratios, ratios[1:]):
                if a is not None and b is not None and b > a:
                    run += 1
                    best = max(best, run)
                else:
                    run = 0
            if best >= 3:
                n += 1
        return n
    except Exception:  # noqa: BLE001
        return None


def fl_distinct(sparql: str, var: str) -> int | None:
    try:
        rows = fluree.query(sparql)["results"]["bindings"]
        return len({r[var]["value"] for r in rows})
    except Exception:  # noqa: BLE001
        return None


def fl_rows(sparql: str) -> list[dict] | None:
    """Raw bindings, for checks whose unit of count is not a single variable."""
    try:
        return fluree.query(sparql)["results"]["bindings"]
    except Exception:  # noqa: BLE001
        return None


def count_stubs_with_two_filers(
        stubs: set[str], edges: list[tuple[str, str]]) -> int:
    """Bridging stubs whose parents include more than one NON-STUB.

    Split out from its check so `validators/test_family_tree_probes.py` can
    hand it a graph whose right answer is known. The subtlety worth testing is
    the exclusion: a stub in an engineered depth chain HAS two parents -- its
    anchor and the stub above it -- and must not be flagged. A gate that
    simply counted parents would fire on 9 legitimate chain members and be
    switched off within a wave.
    """
    parents: dict[str, set[str]] = {}
    for parent, child in edges:
        if child in stubs:
            parents.setdefault(child, set()).add(parent)
    return sum(1 for ps in parents.values()
               if len({x for x in ps if x not in stubs}) > 1)


#: One `validators.syndicate.Context` per `collect()` run, shared by the six
#: Wave 18 delegates. See `_syndicate_delegate` for why it is cached and why
#: caching it is not a second copy of anything.
_SYNDICATE_CTX: dict[str, object] = {}

#: `validators.large_exposure.Context`'s counterpart, one per `collect()`
#: run, shared by the eight Wave 19 delegates. See `_large_exposure_delegate`.
_LARGE_EXPOSURE_CTX: dict[str, object] = {}


def collect() -> list[Check]:
    checks: list[Check] = []
    _SYNDICATE_CTX.clear()
    _LARGE_EXPOSURE_CTX.clear()

    with pg_connect() as conn, conn.cursor() as cur:
        # --- #1 counterparty-reference-snapshot ---------------------------
        checks.append(Check(
            "counterparty-reference-snapshot", "anchor obligors loaded", 50,
            pg_scalar(cur, f'SELECT COUNT(*) FROM "{S}".legal_entity '
                           "WHERE is_anchor"),
        ))
        checks.append(Check(
            "counterparty-reference-snapshot", "entities in LAPSED registration", 5,
            pg_scalar(cur, f'SELECT COUNT(*) FROM "{S}".legal_entity '
                           "WHERE registration_status = 'LAPSED'"),
        ))
        checks.append(Check(
            "counterparty-reference-snapshot", "crosswalk resolves LEI <-> internal", 50,
            pg_scalar(cur, f'SELECT COUNT(*) FROM "{S}".crosswalk c '
                           f'JOIN "{S}".legal_entity e USING (lei)'),
        ))
        # Wave 20. Two addresses are only worth having if they DISAGREE for a
        # material population -- otherwise the schema gained a column and the
        # consumer gained nothing.
        #
        # NORMALISED ON PURPOSE, and the raw number is why: 69 rows differ on
        # a raw comparison and 4 of those differ ONLY BY CASE (AMPHENOL
        # CORP /DE/ carries WILMINGTON against Wilmington). Those are one
        # address typed twice. The question is whether two different PLACES
        # are recorded, not whether two strings differ, and a raw comparison
        # answers the wrong one. Mirrors `_same_place` in spec_coverage.py.
        #
        # THE FLOOR IS OURS, NOT THE SPEC'S. v0.3 states no figure here -- and
        # note §F does NOT, despite the superseded Q019 form's §F being where
        # a number like this would have lived. 20 is chosen so the 4 case
        # artifacts could never satisfy it alone, and so a regression dropping
        # the headquarters load for most entities would fail rather than
        # squeak through. Measured 2026-08-28: 65.
        _norm_hq = ("(lower(btrim(coalesce(hq_address_country, ''))), "
                    "lower(btrim(coalesce(hq_address_city, ''))), "
                    "lower(btrim(coalesce(hq_address_region, ''))))")
        _norm_legal = ("(lower(btrim(coalesce(legal_address_country, ''))), "
                       "lower(btrim(coalesce(legal_address_city, ''))), "
                       "lower(btrim(coalesce(legal_address_region, ''))))")
        checks.append(Check(
            "counterparty-reference-snapshot",
            "entities whose HQ names a different place than legal domicile", 20,
            pg_scalar(cur, f'SELECT COUNT(*) FROM "{S}".legal_entity '
                           "WHERE hq_address_country IS NOT NULL AND "
                           f"{_norm_hq} IS DISTINCT FROM {_norm_legal}"),
            "case/whitespace normalised -- a raw comparison says 69 and 4 of "
            "those are one address typed twice. Floor is ours, not the spec's",
        ))

        # --- Wave 20 gap 1: jurisdiction entitlement ----------------------
        # §B binds the T1 policy as "Entitlement scope only -- JURISDICTION
        # VISIBILITY per calling principal"; §D's Validation gates line names
        # suppression silence. Neither is satisfied by a column whose values
        # differ, so both figures below are RECOMPUTED from
        # legal_entity.legal_jurisdiction against principal_jurisdiction on
        # every run. Nothing reads a stored visibility flag or a cached set.
        #
        # COUNTS DISTINCT SETS, NOT DISTINCT SIZES, and the estate supplies
        # the falsifier for that itself: PRIN-KYC-004 and PRIN-TRD-003 each
        # see exactly 21 entities and the two sets OVERLAP IN NONE OF THEM.
        # There are 4 distinct views and only 3 distinct sizes, so a gate
        # comparing how many each principal can see reports 3 and is wrong.
        #
        # The floor of 3 is OURS. v0.3 states no figure; the "3 principals
        # with differing jurisdiction entitlement" wording came from the
        # superseded Q019 form's §F, and under v0.3 §F is Source binding &
        # readiness -- citing it would be wrong twice over.
        try:
            from validators import entitlement as _ent
            _ent_entities, _ent_scopes = _ent._load()
            _ent_sets = {p: _ent.visible(_ent_entities, pre)
                         for p, pre in _ent_scopes.items()}
            _ent_distinct = _ent.distinct_visible_sets(_ent_sets)
            _ent_suppressed = _ent.every_principal_is_suppressed(
                _ent_sets, len(_ent_entities))
            _ent_asym = _ent.asymmetric_pair(_ent_sets) is not None
        except psycopg.errors.UndefinedTable:
            # ONLY the genuine "wave not yet run" precondition:
            # principal_jurisdiction does not exist. Every other failure --
            # an import error, a bug in entitlement.py, a column renamed out
            # from under it -- must propagate. A bare `except Exception` here
            # would turn a broken gate into three SKIPs, which is the failure
            # this file has recorded five times under other names: a check
            # that stops being able to fail stops being a check.
            _ent_distinct = _ent_suppressed = _ent_asym = None

        checks.append(Check(
            "counterparty-reference-snapshot",
            "principals with DISTINCT VISIBLE SETS", 3, _ent_distinct,
            "recomputed per run; counts sets, not sizes -- two principals "
            "here see 21 entities each and share none of them",
        ))
        checks.append(Check(
            "counterparty-reference-snapshot",
            "an entity visible to one principal and not another", 1,
            None if _ent_asym is None else int(_ent_asym),
            "the concrete statement of suppression: a named entity withheld "
            "from a named principal",
        ))
        checks.append(Check(
            "counterparty-reference-snapshot",
            "every principal is restricted (none sees all)", 1,
            None if _ent_suppressed is None else int(_ent_suppressed),
            "distinctness alone is satisfiable while one principal is "
            "unrestricted, and for that principal the operator is a no-op",
        ))

        # --- Wave 20 gap 2: no-LEI internal clients -----------------------
        # §D: an LEI-only anchor silently excludes privately-held
        # middle-market borrowers, and every downstream product inherits the
        # exclusion. The estate held ZERO of them until 2026-08-28.
        #
        # The floor immediately above this block -- "crosswalk resolves
        # LEI <-> internal", an INNER JOIN ON lei -- is why nobody saw it. It
        # cannot report the absence of entities that have no LEI, and read a
        # healthy 50 throughout. These checks delegate to
        # validators/internal_client.py, which asserts that blindness on every
        # run rather than trusting anyone to remember it.
        try:
            from validators import internal_client as _ic
            _ic_clients, _ic_xw, _ic_ents = _ic._load()
            _ic_n = len(_ic_clients)
            _ic_resolve = sum(1 for c in _ic_clients if _ic.resolves(c))
            _ic_ceiling = sum(1 for c in _ic_clients if _ic.reports_lower_ceiling(
                c["freshness_ceiling_days"] or 0))
            _ic_nolei = _ic.no_lei_clients(_ic_xw)
            _ic_blind = _ic.lei_keyed_join_count(
                [c for c in _ic_xw if not c.get("lei")], _ic_ents)
        except psycopg.errors.UndefinedTable:
            _ic_n = _ic_resolve = _ic_ceiling = _ic_nolei = _ic_blind = None

        checks.append(Check(
            "counterparty-reference-snapshot", "no-LEI internal clients", 20,
            _ic_n, "the population §D says an LEI-only anchor excludes. "
                   "Floor is ours; v0.3 states no volume for this row",
        ))
        checks.append(Check(
            "counterparty-reference-snapshot",
            "no-LEI clients resolving to name AND jurisdiction", 20, _ic_resolve,
            "a row that exists and carries nothing would satisfy a count",
        ))
        checks.append(Check(
            "counterparty-reference-snapshot",
            "no-LEI clients reporting the lower freshness ceiling", 20,
            _ic_ceiling, "§G acceptance: a no-LEI entity resolves AND reports "
                         "the lower ceiling. Months, against 24h for LEI-registered",
        ))
        checks.append(Check(
            "counterparty-reference-snapshot",
            "LEI-keyed join sees none of them (want 0)", 0,
            None if _ic_blind is None else -_ic_blind,
            "the blindness that hid this gap, asserted rather than remembered",
        ))
        # NARROWED 2026-08-24, when 103 GLEIF reference subsidiaries were
        # loaded so that family-tree traversal results resolve.
        #
        # This was one FULL OUTER JOIN counting every `legal_entity` row with
        # no `crosswalk` row as an orphan. That was right while the table held
        # only the bank's own obligors, and wrong the moment it held reference
        # data: a GLEIF subsidiary the bank has no facility, deal or coverage
        # against is not a client, and minting it an `internal_client_id` to
        # satisfy a validator would invent 103 relationships that do not
        # exist. Rule #4's crosswalk is mandatory for entities the bank holds
        # internal data ABOUT -- that is what makes it a correlation key
        # rather than a registry.
        #
        # Split into the three things the old check actually meant, each
        # counting its own quantity so a failure names itself. The third is
        # the one that matters: it is derived from where internal data
        # ACTUALLY IS, so a future client entity added as a non-anchor is
        # still caught the moment anything internal points at it. Widening the
        # exemption to "non-anchors are fine" would have lost that.
        why = {
            "crosswalk rows pointing at no entity":
                "negated: an internal client id resolving to nobody",
            "internal clients no crosswalk row reaches":
                "negated: a no-LEI client the bank side cannot key -- the "
                "hole the 2026-08-28 widening would otherwise have opened",
            "anchors with no internal client id":
                "negated: every obligor must join LEI <-> internal",
            "entities with internal data, no client id":
                "negated: a borrower, pipeline deal or covered name that the "
                "bank side cannot key",
        }
        for name, sql in CROSSWALK_INVARIANTS.items():
            violations = pg_scalar(cur, sql)
            checks.append(Check(
                "counterparty-reference-snapshot", f"{name} (want 0)", 0,
                None if violations is None else -violations, why[name],
            ))

        # --- #3 obligor-financial-spread ----------------------------------
        checks.append(Check(
            "obligor-financial-spread", "anchors with >= 8 periods of facts", 50,
            pg_scalar(cur, f"""
                SELECT COUNT(*) FROM (
                    SELECT lei FROM "{S}".financial_fact
                    GROUP BY lei HAVING COUNT(DISTINCT period_end) >= 8) t"""),
        ))
        checks.append(Check(
            "obligor-financial-spread", "obligors with a genuine restatement", 3,
            pg_scalar(cur, f"""
                SELECT COUNT(DISTINCT cik) FROM (
                    SELECT cik, tag, period_end FROM "{S}".financial_fact
                    GROUP BY cik, tag, period_end
                    HAVING COUNT(DISTINCT accession) > 1
                       AND COUNT(DISTINCT value) > 1) t"""),
            "different VALUE, not just accession",
        ))
        checks.append(Check(
            "obligor-financial-spread", "peer entities loaded", 150,
            pg_scalar(cur, f'SELECT COUNT(*) FROM "{S}".peer_entity'),
        ))
        checks.append(Check(
            "obligor-financial-spread", "anchor+peer share tag AND period", 1,
            pg_scalar(cur, f"""
                SELECT COUNT(DISTINCT f.period_end)
                FROM "{S}".financial_fact f
                JOIN "{S}".peer_fact p
                  ON p.period_end = f.period_end AND p.tag = f.tag"""),
            "peers matched on period, never filing date",
        ))
        checks.append(Check(
            "obligor-financial-spread", "anchors with non-December FYE", 2,
            pg_scalar(cur, f'SELECT COUNT(*) FROM "{S}".legal_entity '
                           "WHERE fiscal_year_end IS NOT NULL "
                           "AND fiscal_year_end <> '' "
                           "AND LEFT(fiscal_year_end, 2) <> '12'"),
        ))

        # --- #8 covenant-in-force-as-of (Wave 4/5) ------------------------
        checks.append(Check(
            "covenant-in-force-as-of", "obligors with real 8-K Item 2.04", 2,
            pg_scalar(cur, f'SELECT COUNT(*) FROM "{S}".filing_profile '
                           "WHERE count_8k_item_2_04 >= 1"),
        ))
        checks.append(Check(
            "covenant-in-force-as-of", "facilities loaded", 40,
            pg_scalar(cur, f'SELECT COUNT(*) FROM "{S}".facility'),
            "Wave 4",
        ))
        checks.append(Check(
            "covenant-in-force-as-of", "facilities with >= 1 amendment", 12,
            pg_scalar(cur, f'SELECT COUNT(*) FROM "{S}".facility '
                           "WHERE amendment_count >= 1"),
            "Wave 4",
        ))
        # --- Wave 5: the flagship's temporal conditions -------------------
        checks.append(Check(
            "covenant-in-force-as-of", "drawdowns inside a booking gap", 1,
            pg_scalar(cur, f'SELECT COUNT(*) FROM "{S}".drawdown '
                           "WHERE falls_in_booking_gap"),
            "THE engineered element; see validators/bitemporal.py",
        ))
        checks.append(Check(
            "covenant-in-force-as-of", "policy versions, distinct dates", 2,
            pg_scalar(cur, f'SELECT COUNT(DISTINCT effective_from) '
                           f'FROM "{S}".covenant_policy'),
        ))
        checks.append(Check(
            "covenant-in-force-as-of", "past-breach-now-compliant covenants", 1,
            pg_scalar(cur, f'SELECT COUNT(*) FROM "{S}".covenant_breach '
                           "WHERE compliant_today"),
            "forensic and live queries disagree",
        ))
        checks.append(Check(
            "covenant-in-force-as-of", "drawdowns across amendment boundaries", 20,
            pg_scalar(cur, f'SELECT COUNT(*) FROM "{S}".drawdown'),
        ))

    # --- #4 corporate-family-tree (Fluree) --------------------------------
    checks.append(Check(
        "corporate-family-tree", "entities in Fluree", 500,
        fl_scalar(f"SELECT (COUNT(DISTINCT ?s) AS ?n) FROM <{L}> "
                  f"WHERE {{ ?s <{EX}provenance> ?p }}"),
    ))
    # BOTH predicates, and now for a second reason. Originally: the T-Box
    # declared control subPropertyOf ownership, Fluree applies no inference, so
    # querying only the superproperty silently undercounted every control edge.
    # This check found that itself. Since Wave 8 that axiom is gone -- FIBO
    # makes `owns` and `controls` siblings, never sub/super -- so matching both
    # is no longer a workaround for missing inference, it is the correct query.
    owns_n = fl_scalar(f"SELECT (COUNT(*) AS ?n) FROM <{L}> WHERE {{ ?a <{OWNS}> ?b }}")
    ctrl_n = fl_scalar(f"SELECT (COUNT(*) AS ?n) FROM <{L}> WHERE {{ ?a <{CONTROLS}> ?b }}")
    # The condition below is named control-WITHOUT-ownership and until Wave 10's
    # follow-up it was measured as a bare COUNT of `controls` edges — which any
    # control edge would satisfy, including one between a pair that also owns.
    # The label promised more than the query checked. This one excludes pairs
    # carrying an `owns` edge, so it now measures the structure it names.
    ctrl_only_n = fl_scalar(
        f"""SELECT (COUNT(*) AS ?n) FROM <{L}> WHERE {{
            ?a <{CONTROLS}> ?b .
            FILTER NOT EXISTS {{ ?a <{OWNS}> ?b }}
        }}""")
    gult_n = fl_scalar(f"SELECT (COUNT(*) AS ?n) FROM <{L}> WHERE {{ ?a <{GLOBAL_ULTIMATE}> ?b }}")
    dult_n = fl_scalar(f"SELECT (COUNT(*) AS ?n) FROM <{L}> WHERE {{ ?a <{DOMESTIC_ULTIMATE}> ?b }}")
    parts = [owns_n, ctrl_n, gult_n, dult_n]
    checks.append(Check(
        "corporate-family-tree", "ownership graph edges (all predicates)", 500,
        None if any(p is None for p in parts) else sum(parts),
        f"{owns_n} owns + {ctrl_n} control + {gult_n} global-ult + {dult_n} domestic-ult",
    ))
    # Control-only edges are the structure the product exists to surface, and
    # the estate has none: the 103 edges that used to sit on `controls` were
    # GLEIF ultimate-parent relationships, now correctly on hasGlobalUltimateParent.
    # Recorded as a visible shortfall rather than left masked by the old mapping.
    checks.append(Check(
        "corporate-family-tree", "control-WITHOUT-ownership edges", 1, ctrl_only_n,
        "golden shares / board rights — outstanding manufacture work"
        if not ctrl_only_n
        else "engineered: golden share, dual-class voting trust, facility-agent "
             "board rights — see loaders/load_control_edges.py",
    ))
    checks.append(Check(
        "corporate-family-tree", "roots reaching 4+ hops", 2,
        fl_distinct(
            f"""SELECT ?a FROM <{L}> WHERE {{
                ?a <{OWNS}> ?b . ?b <{OWNS}> ?c .
                ?c <{OWNS}> ?d . ?d <{OWNS}> ?e .
                FILTER(?a != ?e) }} LIMIT 200""", "a"),
        "so depth=3 visibly truncates",
    ))
    # COUNTS CYCLES, NOT CYCLE MEMBERS.
    #
    # Until Wave 13b this bound `?a` and counted DISTINCT `?a`, which for one
    # 3-cycle is three bindings. The estate's single engineered cycle therefore
    # reported 3 / 3 PASS against a condition asking for two CYCLES, and would
    # have gone on doing so if the second cycle had never been built. A count
    # of members is not a count of cycles.
    #
    # A 3-cycle appears three times in the result set, once per starting node.
    # Canonicalising each triple as a frozenset and counting the distinct sets
    # collapses those rotations to one, so the number returned is the number of
    # cycles a reader would draw on a whiteboard.
    def distinct_cycles() -> int | None:
        rows = fl_rows(
            f"""SELECT ?a ?b ?c FROM <{L}> WHERE {{
                ?a <{OWNS}> ?b . ?b <{OWNS}> ?c . ?c <{OWNS}> ?a }} LIMIT 200""")
        if rows is None:
            return None
        return len({frozenset((r["a"]["value"], r["b"]["value"],
                               r["c"]["value"])) for r in rows})

    checks.append(Check(
        "corporate-family-tree", "cross-shareholding CYCLES present", 2,
        distinct_cycles(),
        "engineered, labelled. Counts cycles, not members — one 3-cycle "
        "used to report as 3",
    ))
    checks.append(Check(
        "corporate-family-tree", "non-LEI bridging stubs", 30,
        fl_scalar(f'SELECT (COUNT(?s) AS ?n) FROM <{L}> '
                  f'WHERE {{ ?s <{EX}provenance> "synthetic — bridging" }}'),
    ))
    # §F: ">= 1 family spanning three jurisdictions, so jurisdiction
    # entitlement filtering is not a no-op". Unregistered until 2026-08-24,
    # and until the same day UNSATISFIABLE -- Exhibit 21 files a jurisdiction
    # for 1,422 of 1,635 subsidiaries and load_fluree_wave3.py dropped every
    # one of them, so the ledger held zero. The floor is 1; 12 families clear
    # it now, the widest spanning 10 countries.
    #
    # COUNTS FAMILIES, NOT PAIRS. The unit §F names is the family, and a
    # parent with ten foreign subsidiaries is one family, not ten.
    def families_spanning_three() -> int | None:
        rows = fl_rows(
            f"""SELECT ?p ?j FROM <{L}> WHERE {{
                ?p <{OWNS}> ?c . ?c <{EX}jurisdictionCode> ?j }} LIMIT 3000""")
        if rows is None:
            return None
        spans: dict[str, set[str]] = {}
        for r in rows:
            spans.setdefault(r["p"]["value"], set()).add(r["j"]["value"])
        return sum(1 for js in spans.values() if len(js) >= 3)

    # INVERTED, and the only gate that would have caught known-issues §19.6.
    #
    # Three Exhibit 21 TABLE HEADERS -- "Subsidiary", "Legal Name", "Company
    # Name" -- were parsed as subsidiary names and normalised to one local
    # each, so a single node ended up owned by two unrelated filers. The worst
    # read as THE HAIN CELESTIAL GROUP, a natural-foods company, owning Genesis
    # Energy's offshore pipelines three hops down. Every registered condition
    # passed throughout: the phantom was one more entity, one more edge, one
    # more stub, and every check here counts.
    #
    # A stub legitimately has TWO parents when it sits in an engineered depth
    # chain -- its anchor, plus the stub above it. What is never legitimate is
    # two FILER parents, because that means two companies' Exhibit 21s were
    # merged into one entity. So stub-parents are excluded and the rest counted.
    def stubs_with_two_filers() -> int | None:
        stub_rows = fl_rows(f'SELECT ?s FROM <{L}> WHERE {{ '
                            f'?s <{EX}provenance> "synthetic — bridging" }} '
                            f"LIMIT 2000")
        edges = fl_rows(f"SELECT ?p ?c FROM <{L}> WHERE {{ "
                        f"?p <{OWNS}> ?c }} LIMIT 4000")
        if stub_rows is None or edges is None:
            return None
        return count_stubs_with_two_filers(
            {r["s"]["value"] for r in stub_rows},
            [(e["p"]["value"], e["c"]["value"]) for e in edges])

    # INVERTED, and it exists because the check above it CANNOT SEE the
    # population it is supposed to police.
    #
    # "entities in Fluree" counts `?s ex:provenance ?p`. An entity with no
    # provenance is therefore not merely unlabelled — it is absent from the
    # count, so the floor of 500 was cleared by the 624 nodes that carried a
    # class while 192 that did not could never have failed it. Rule #1 says
    # every element carries one; nothing checked it for twelve waves.
    #
    # Counted the other way round: type first, provenance second, so the
    # denominator is every LegalEntity and a missing label subtracts.
    def unlabelled_entities() -> int | None:
        typed = fl_distinct(
            f"SELECT ?s FROM <{L}> WHERE {{ ?s <{RDF_TYPE_IRI}> "
            f"<{C_LEGAL_ENTITY_IRI}> }} LIMIT 9000", "s")
        labelled = fl_distinct(
            f"SELECT ?s FROM <{L}> WHERE {{ ?s <{RDF_TYPE_IRI}> "
            f"<{C_LEGAL_ENTITY_IRI}> . ?s <{EX}provenance> ?p }} LIMIT 9000",
            "s")
        if typed is None or labelled is None:
            return None
        return typed - labelled

    checks.append(Check(
        "corporate-family-tree", "entities with NO provenance class (want 0)", 0,
        None if (n := unlabelled_entities()) is None else -n,
        "negated: rule #1 labels every element, and the entity count above "
        "is blind to a node that carries no class",
    ))
    checks.append(Check(
        "corporate-family-tree", "stubs owned by two filers (want 0)", 0,
        None if (n := stubs_with_two_filers()) is None else -n,
        "negated: two companies' Exhibit 21 lists merged into one entity",
    ))
    checks.append(Check(
        "corporate-family-tree", "families spanning 3+ jurisdictions", 1,
        families_spanning_three(),
        "so jurisdiction entitlement filtering is not a no-op. Counts "
        "FAMILIES, not parent-subsidiary pairs",
    ))
    checks.append(Check(
        "corporate-family-tree", "entities carrying a real LEI", 50,
        real_lei_entities(),
        "REAL, and ENTITIES: excludes SYN- synthetics and counts distinct "
        "values, not bindings. Reported 449 for 233 until 2026-08-28",
    ))
    checks.append(Check(
        "corporate-family-tree", "engineered elements labelled", 3,
        fl_scalar(f'SELECT (COUNT(?s) AS ?n) FROM <{L}> '
                  f'WHERE {{ ?s <{EX}provenance> "synthetic — engineered" }}'),
        "provenance honesty, rule #1",
    ))

    # --- #8 Wave 5 temporal assertions in Fluree --------------------------
    checks.append(Check(
        "covenant-in-force-as-of", "covenants asserted in Fluree", 160,
        fl_scalar(f'SELECT (COUNT(?s) AS ?n) FROM <{L}> '
                  f'WHERE {{ ?s <{EX}covenantType> ?t }}'),
    ))
    checks.append(Check(
        "covenant-in-force-as-of", "amendments with BOTH time axes", 12,
        fl_scalar(f'SELECT (COUNT(?s) AS ?n) FROM <{L}> WHERE {{ '
                  f'?s <{EX}validFrom> ?v . ?s <{EX}assertedAt> ?a }}'),
        "valid time AND assertion time",
    ))
    checks.append(Check(
        "covenant-in-force-as-of", "engineered booking lags labelled", 3,
        fl_scalar(f'SELECT (COUNT(?s) AS ?n) FROM <{L}> '
                  f'WHERE {{ ?s <{EX}isEngineeredBookingLag> "true" }}'),
        "rule #1: engineered elements labelled honestly",
    ))
    checks.append(Check(
        "covenant-in-force-as-of", "facilities with >= 4 covenant types", 40,
        fl_distinct(
            f"""SELECT ?f (COUNT(DISTINCT ?ct) AS ?n) FROM <{L}> WHERE {{
                ?c <{EX}covenantOf> ?f . ?c <{EX}covenantType> ?ct
            }} GROUP BY ?f HAVING (COUNT(DISTINCT ?ct) >= 4)""", "f"),
    ))

    # --- #13 covenant-cross-reference (Wave 6) ----------------------------
    checks.append(Check(
        "covenant-cross-reference", "credit agreements as full text", 15,
        # FILTERED. This was `mongo_count("document")` with no query at all,
        # so it counted all 175 documents of every form -- 8-K, 10-K, 10-Q,
        # 10-D, 424B5 -- and would have cleared a floor of 15 with zero credit
        # agreements in the corpus. §F asks for ~15 CREDIT AGREEMENTS. The
        # answer happened to hold; the check could not have told us if it had
        # not.
        mongo_count("document", {"text": {"$regex": "CREDIT AGREEMENT"}}),
        "§F counts credit agreements, not documents",
    ))
    checks.append(Check(
        "covenant-cross-reference", "structure-aligned passages", 2500,
        mongo_count("passage", {"structure_aligned": True}),
        "§F prefers structure over a fixed window",
    ))
    checks.append(Check(
        "covenant-cross-reference", "passages with embeddings", 2500,
        mongo_count("passage", {"embedding_model": {"$ne": None}}),
        "separate model-versioned pass",
    ))
    checks.append(Check(
        "covenant-cross-reference", "internal credit memoranda", 20,
        mongo_count("memorandum"),
    ))
    checks.append(Check(
        "covenant-cross-reference", "memoranda classification-tagged", 20,
        mongo_count("memorandum",
                    {"classification": {"$in": ["internal-confidential",
                                                "internal-restricted"]}}),
        "so corpus_scope has something to gate",
    ))
    checks.append(Check(
        "covenant-cross-reference", "verified passage anchors", 5,
        fl_scalar(f'SELECT (COUNT(?s) AS ?n) FROM <{L}> '
                  f'WHERE {{ ?s <{EX}anchorVerified> "true" }}'),
        "§8.4: anchor is a candidate until sha256 matches",
    ))
    # Near-duplicate pairs are computed by validators/near_duplicates.py and
    # cached, because a pairwise scan over embeddings is too slow for a gate.
    try:
        import json as _json
        _nd = _json.loads(
            (REPO_ROOT / "sources" / "screening" / "near_duplicates.json").read_text()
        )
        _cross = _nd.get("cross_filer_count")
    except Exception:  # noqa: BLE001
        _cross = None
    checks.append(Check(
        "covenant-cross-reference", "near-duplicate covenants across filers", 2,
        _cross,
        "textually similar, structurally distinct — the fusion counterfactual",
    ))
    checks.append(Check(
        "covenant-cross-reference", "Context Debt asserted, not hidden", 1,
        fl_scalar(f'SELECT (COUNT(?s) AS ?n) FROM <{L}> '
                  f'WHERE {{ ?s a <{EX}ContextDebt> }}'),
        "completeness shortfall must be visible",
    ))
    # §F's bullet is NOT "some Context Debt exists" -- it is ">= 1 covenant
    # with an UNRESOLVABLE DEFINITION, so Context Debt is emitted rather than
    # theoretical". The check above was passing on DEBT-0000, whose reason
    # reads "no passage span contains the extracted offset": an unresolvable
    # OFFSET. Different failure, different remedy, and it does not exercise
    # the definition chain at all. Counted here on the quantity §F names.
    checks.append(Check(
        "covenant-cross-reference", "covenants with an UNRESOLVABLE DEFINITION", 1,
        fl_scalar(f'SELECT (COUNT(DISTINCT ?c) AS ?n) FROM <{L}> WHERE {{ '
                  f'?c <{EX}definedBy> ?d . ?d <{EX}unresolvedTerm> ?term . '
                  f'?debt a <{EX}ContextDebt> ; <{EX}unresolvedTerm> ?term }}'),
        "§F: the debt must be about a definition that does not resolve",
    ))
    # Depth 3 is covenant -> definition -> a term that definition depends on.
    # Counted as covenants, which is the unit §F names, not as edges.
    checks.append(Check(
        "covenant-cross-reference", "covenants whose definition chain reaches depth 3", 5,
        fl_scalar(f'SELECT (COUNT(DISTINCT ?c) AS ?n) FROM <{L}> WHERE {{ '
                  f'?c <{EX}definedBy> ?d . ?d <{EX}crossReferences> ?t . '
                  f'?t a <{EX}DefinedTerm> }}'),
        "covenant to definition to defined term, all in filed EX-10 text",
    ))
    # A cross-DOCUMENT reference means the target is in a different document
    # than the definition. Comparing documentIds is what makes it cross-
    # document; counting `crossReferences` edges would count the 214
    # intra-document component citations too.
    checks.append(Check(
        "covenant-cross-reference", "cross-document definition references", 1,
        fl_scalar(f'SELECT (COUNT(DISTINCT ?d) AS ?n) FROM <{L}> WHERE {{ '
                  f'?d <{EX}crossReferences> ?r . '
                  f'?d <{EX}documentId> ?d1 . ?r <{EX}documentId> ?d2 . '
                  f'FILTER(?d1 != ?d2) }}'),
        "§F: a definition incorporating a convention stated in the 10-K",
    ))

    # --- #17 mnpi-wall-enforcement (Wave 7) -------------------------------
    import sqlite3 as _sq
    from ccf.config import SQLITE_PATH as _SP

    def _sqlite_count(sql: str) -> int | None:
        if not _SP.exists():
            return None
        try:
            with _sq.connect(_SP) as _c:
                return int(_c.execute(sql).fetchone()[0])
        except Exception:  # noqa: BLE001
            return None

    checks.append(Check(
        "mnpi-wall-enforcement", "restricted list in the DEPARTMENTAL store", 3,
        _sqlite_count("SELECT COUNT(*) FROM restricted_list "
                      "WHERE removed_date IS NULL"),
        "SQLite, read before anything else runs",
    ))
    checks.append(Check(
        "mnpi-wall-enforcement", "departmental tables populated", 4,
        _sqlite_count("SELECT COUNT(DISTINCT name) FROM sqlite_master "
                      "WHERE type='table' AND name IN ('restricted_list',"
                      "'covenant_tracker','prospect_note',"
                      "'risk_limit_workbook')"),
    ))
    with pg_connect() as conn, conn.cursor() as cur:
        checks.append(Check(
            "mnpi-wall-enforcement", "test principals with ProjectionPlans", 3,
            pg_scalar(cur, f'SELECT COUNT(*) FROM "{S}".projection_plan'),
            "projection_plan_id enters the lineage record",
        ))
        checks.append(Check(
            "mnpi-wall-enforcement", "MNPI-tagged deals", 10,
            pg_scalar(cur, f'SELECT COUNT(*) FROM "{S}".deal '
                           "WHERE mnpi_bearing"),
        ))
        checks.append(Check(
            "mnpi-wall-enforcement", "deal and engagement records", 30,
            pg_scalar(cur, f'SELECT COUNT(*) FROM "{S}".deal'),
        ))
    checks.append(Check(
        "mnpi-wall-enforcement", "research notes", 40,
        mongo_count("research_note"),
    ))
    checks.append(Check(
        "mnpi-wall-enforcement", "draft research under embargo", 8,
        mongo_count("research_note", {"status": "draft"}),
    ))
    checks.append(Check(
        "mnpi-wall-enforcement", "wall crossings with a recorded date", 1,
        fl_scalar(f'SELECT (COUNT(?s) AS ?n) FROM <{L}> '
                  f'WHERE {{ ?s a <{EX}WallCrossing> }}'),
        "wall state is T as much as P",
    ))
    checks.append(Check(
        "mnpi-wall-enforcement", "Reg FD event that WIDENS access", 1,
        fl_scalar(f'SELECT (COUNT(?s) AS ?n) FROM <{L}> '
                  f'WHERE {{ ?s <{EX}widensAccess> "true" }}'),
        "the only widening supersession in the catalog",
    ))
    try:
        import json as _j
        _rd = _j.loads(
            (REPO_ROOT / "sources" / "screening" / "ranking_difference.json").read_text()
        )
        _restricted_in_top = _rd.get("restricted_in_naive_top_n")
    except Exception:  # noqa: BLE001
        _restricted_in_top = None
    checks.append(Check(
        "mnpi-wall-enforcement", "measured ranking difference", 1,
        _restricted_in_top,
        "restricted docs that WOULD have shaped a public-side result",
    ))

    # --- #6 collateral-and-setoff-coverage (Wave 9) -----------------------
    # Every one of these is a QUERY against loaded data, not a count carried
    # over from the generator. A generator reporting its own success proves
    # only that it ran.
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT COUNT(*) FROM "{S}".collateral_asset')
        n_assets = cur.fetchone()[0]
        cur.execute(f'SELECT COUNT(DISTINCT facility_id) FROM "{S}".collateral_pledge')
        n_facs = cur.fetchone()[0]
        cur.execute(f"""
            SELECT COUNT(*) FROM (
              SELECT asset_id FROM "{S}".collateral_pledge
              GROUP BY asset_id HAVING COUNT(DISTINCT facility_id) > 1
            ) s""")
        n_shared = cur.fetchone()[0]
        # §C assigns lien priority to FLUREE (`R`, `T`), and since Wave 15
        # that is where it lives -- on the reified pledge node, as a FIBO
        # LenderLienPosition value. This used to read
        # `collateral_pledge.priority`, which satisfied the §F floor out of
        # the wrong store: the graph held 95 indistinguishable collateral
        # edges the whole time. Counted from the ledger so the condition
        # proves what the spec asks, not merely that a Postgres column
        # disagrees with itself.
        n_split = _differing_lien_positions()
        cur.execute(f'SELECT COUNT(*) FROM "{S}".deposit_account')
        n_dep = cur.fetchone()[0]
        cur.execute(f'SELECT COUNT(*) FROM "{S}".deposit_account '
                    "WHERE setoff_contractual AND NOT setoff_enforceable")
        n_unenf = cur.fetchone()[0]
        cur.execute(f'SELECT COUNT(DISTINCT category) FROM "{S}".collateral_asset '
                    "WHERE category IN ('real_property','marketable_securities',"
                    "'receivables','equipment')")
        n_cats = cur.fetchone()[0]
        cur.execute(f'SELECT MAX(valuation_age_days) FROM "{S}".collateral_asset')
        oldest = cur.fetchone()[0] or 0
        # The condition that cannot be counted, only computed: a facility whose
        # collateral covers it GROSS and fails to cover it after haircuts. If
        # this is zero, `apply_haircuts` moves decimals instead of conclusions
        # and the parameter is decorative.
        cur.execute(f"""
            SELECT COUNT(*) FROM (
              SELECT p.facility_id,
                     SUM(a.valuation)                      AS gross,
                     SUM(a.valuation * (1 - a.haircut))     AS net,
                     MAX(f.commitment_amount)               AS commitment
              FROM "{S}".collateral_pledge p
              JOIN "{S}".collateral_asset a USING (asset_id)
              JOIN "{S}".facility f USING (facility_id)
              GROUP BY p.facility_id
              HAVING SUM(a.valuation) > MAX(f.commitment_amount)
                 AND SUM(a.valuation * (1 - a.haircut)) < MAX(f.commitment_amount)
            ) s""")
        n_flip = cur.fetchone()[0]

    checks.append(Check("collateral-and-setoff-coverage",
                        "collateral assets", 60, n_assets))
    checks.append(Check("collateral-and-setoff-coverage",
                        "facilities carrying collateral", 40, n_facs))
    checks.append(Check("collateral-and-setoff-coverage",
                        "asset categories spanned", 4, n_cats))
    checks.append(Check("collateral-and-setoff-coverage",
                        "shared-collateral cases", 3, n_shared,
                        "one asset securing two or more facilities"))
    checks.append(Check("collateral-and-setoff-coverage",
                        "shared at DIFFERING priority", 1, n_split))
    checks.append(Check("collateral-and-setoff-coverage",
                        "covered gross, under-covered after haircuts", 2, n_flip,
                        "computed from loaded valuations; makes apply_haircuts "
                        "change the conclusion"))
    checks.append(Check("collateral-and-setoff-coverage",
                        "deposit accounts", 20, n_dep))
    checks.append(Check("collateral-and-setoff-coverage",
                        "set-off contractual but NOT enforceable", 4, n_unenf,
                        "makes jurisdiction_basis consequential"))
    checks.append(Check("collateral-and-setoff-coverage",
                        "valuation staleness spread (days)", 540, oldest,
                        "§F wants same-day through ~18 months"))

    # --- #5 credit-exposure-rollup (Wave 9) -------------------------------
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT COUNT(*) FROM "{S}".guarantee_terms')
        n_guar = cur.fetchone()[0]
        cur.execute(f"SELECT COUNT(*) FROM \"{S}\".guarantee_terms "
                    "WHERE kind = 'upstream'")
        n_upstream = cur.fetchone()[0]
        cur.execute(f'SELECT COUNT(*) FROM "{S}".limit_definition')
        n_limits = cur.fetchone()[0]
        cur.execute(f'SELECT COUNT(*) FROM "{S}".debt_reconciliation WHERE plausible')
        n_plausible = cur.fetchone()[0]
        cur.execute(f'SELECT guarantor_lei, obligor_uri, covered_pct '
                    f'FROM "{S}".guarantee_terms')
        guarantees = cur.fetchall()
        cur.execute(f'SELECT borrower_lei, SUM(commitment_amount) '
                    f'FROM "{S}".facility GROUP BY 1')
        commitments = {r[0]: float(r[1] or 0) for r in cur.fetchall()}

    # Cross-default edges live in Fluree, so count them there.
    xd = fl_scalar(f"SELECT (COUNT(*) AS ?n) FROM <{L}> "
                   f"WHERE {{ ?a <{EX}crossDefaultsWith> ?b }}")
    fac_edges = fl_scalar(
        f"SELECT (COUNT(*) AS ?n) FROM <{L}> WHERE {{ ?f <"
        "https://spec.edmcouncil.org/fibo/ontology/FBC/DebtAndEquities/Debt/"
        "hasBorrower> ?o }")

    # THE condition that cannot be counted. A guarantee over an obligor that
    # ALSO holds facilities is double-counted by a borrower-keyed sum: the
    # exposure is captured once at the subsidiary and again at the guarantor.
    # Computed from what is loaded — resolve each guaranteed obligor back to an
    # LEI through the ledger, then look up whether it actually borrows.
    lei_by_uri = {}
    try:
        res = fluree.query(f"SELECT ?s ?l FROM <{L}> WHERE {{ ?s <{EX}lei> ?l }}")
        lei_by_uri = {b["s"]["value"]: b["l"]["value"]
                      for b in res["results"]["bindings"]}
    except Exception:  # noqa: BLE001
        pass
    differing = 0
    for guarantor_lei, obligor_uri, pct in guarantees:
        obligor_lei = lei_by_uri.get(obligor_uri)
        if not obligor_lei or obligor_lei == guarantor_lei:
            continue
        overlap = commitments.get(obligor_lei, 0.0) * float(pct)
        group = commitments.get(guarantor_lei, 0.0) + commitments.get(obligor_lei, 0.0)
        # "materially" — the double-count has to move the number, not round it.
        if group and overlap / group > 0.05:
            differing += 1

    checks.append(Check("credit-exposure-rollup", "guarantee edges", 25, n_guar))
    checks.append(Check("credit-exposure-rollup",
                        "upstream to a non-borrowing subsidiary", 3, n_upstream,
                        "the exposure a borrower-keyed sum cannot find"))
    checks.append(Check("credit-exposure-rollup", "cross-default edges", 15, xd))
    checks.append(Check("credit-exposure-rollup",
                        "facility -> borrower edges in Fluree", 40, fac_edges,
                        "exposure must be reachable BY TRAVERSAL, not just joined"))
    checks.append(Check("credit-exposure-rollup",
                        "families where naive != guarantee-adjusted", 3, differing,
                        "computed: guarantee overlaps a borrowing obligor by >5% "
                        "of group commitments"))
    checks.append(Check("credit-exposure-rollup",
                        "group-limit definitions by intent", 3, n_limits))
    checks.append(Check("credit-exposure-rollup",
                        "borrowers with a plausible debt share", 10, n_plausible,
                        "committed <= 150% of XBRL-reported debt"))

    # --- #? client-360-coverage-graph (Wave 10) ---------------------------
    with pg_connect() as conn, conn.cursor() as cur:
        # Named people per anchor. Natural persons only -- the 39 entity
        # reporting-owners never enter this count, per Wave 10's design.
        cur.execute(f"""
            SELECT r.lei, COUNT(DISTINCT r.person_key) AS n
            FROM "{S}".person_role r
            JOIN "{S}".person p
              ON p.person_key = r.person_key AND p.owner_kind = 'natural'
            JOIN "{S}".legal_entity e ON e.lei = r.lei AND e.is_anchor
            GROUP BY r.lei
        """)
        anchor_counts = [n for _, n in cur.fetchall()]
        n_in_band = sum(1 for n in anchor_counts if 8 <= n <= 25)

        cur.execute(f'SELECT COUNT(*) FROM "{S}".banker')
        n_bankers = cur.fetchone()[0]

        cur.execute(f'SELECT COUNT(*) FROM "{S}".interaction')
        n_interactions = cur.fetchone()[0]

        # The recency gradient -- written out per the brief, because it is
        # the one condition a flat count would silently satisfy.
        #
        # Anchored on MAX(interaction_date), not current_date. A prior
        # ruling here held that a few days' drift between generation and
        # validation "cannot move a row across a quarter boundary" because
        # the buckets are 91 days wide. That inverts the mechanism: drift
        # does not move ROWS across buckets, it moves the BUCKETS across a
        # frozen dataset -- every day removes rows from `newest` and adds
        # them to `oldest`, while the floor `max(oldest * 2, 1)` moves
        # against the assertion from the other side too. Measured: PASS at
        # +0d and +30d of calendar drift, FAIL by +60d, with a failure
        # message that reads as a data regression rather than a clock
        # artifact. Anchoring on the data's own newest row makes the check
        # measure the gradient the dataset actually has, not how long ago it
        # was generated.
        cur.execute(f"""
            WITH bounds AS (
              SELECT max(interaction_date) AS latest FROM "{S}".interaction
            )
            SELECT
              count(*) FILTER (WHERE i.interaction_date >= b.latest - 91)  AS newest,
              count(*) FILTER (WHERE i.interaction_date <  b.latest - 638) AS oldest
            FROM "{S}".interaction i, bounds b
            WHERE i.provenance LIKE 'synthetic%'
        """)
        newest, oldest = cur.fetchone()

        cur.execute(f'SELECT COUNT(DISTINCT person_key) FROM "{S}".person_name_variant')
        n_variants = cur.fetchone()[0]

        # Coverage gaps -- senior client officers who never appear as a party
        # to any interaction. This IS the insight the product sells, so it
        # has to be a real anti-join against interaction_participant, not a
        # count carried over from the generator's own gap list.
        cur.execute(f"""
            SELECT COUNT(DISTINCT r.person_key)
            FROM "{S}".person_role r
            JOIN "{S}".person p
              ON p.person_key = r.person_key AND p.owner_kind = 'natural'
            WHERE r.role = 'officer'
              AND NOT EXISTS (
                SELECT 1 FROM "{S}".interaction_participant ip
                WHERE ip.party_kind = 'person' AND ip.party_key = r.person_key
              )
        """)
        n_gaps = cur.fetchone()[0]

        cur.execute(f'SELECT COUNT(*) FROM "{S}".interaction WHERE need_to_know')
        n_ntk = cur.fetchone()[0]

        cur.execute(f"SELECT COUNT(*) FROM \"{S}\".person_crosswalk "
                    "WHERE match_band = 'false_positive'")
        n_false_positive = cur.fetchone()[0]

        # The tenth check: need-to-know as a policy binding DISTINCT from
        # MNPI. Read live from Postgres rather than hardcoded, so a loader
        # regression that leaves sees_need_to_know at its column default
        # (TRUE) is caught, not assumed away.
        cur.execute(f'SELECT principal_id, sees_need_to_know FROM "{S}".principal '
                    "ORDER BY 1")
        flags = dict(cur.fetchall())
        blind_ok = all(flags.get(pid) is False
                       for pid in ("PRIN-RES-002", "PRIN-TRD-003"))
        sighted_ok = flags.get("PRIN-COV-001") is True

    checks.append(Check(
        "client-360-coverage-graph", "anchors with 8-25 named people", 45,
        n_in_band,
        f"of {len(anchor_counts)} anchors carrying a person_role row"))
    checks.append(Check(
        "client-360-coverage-graph", "synthetic bankers", 40, n_bankers))
    checks.append(Check(
        "client-360-coverage-graph", "interaction records", 2000, n_interactions))
    checks.append(Check(
        "client-360-coverage-graph", "recency gradient, newest vs oldest quarter",
        max(oldest * 2, 1), newest,
        f"newest={newest} oldest={oldest} — a flat distribution satisfies the "
        "count and makes the relationship score meaningless"))
    try:
        depth2_actual = _depth2_over_limit_count()
        depth2_note = ("delegates to validators/traversal.py; cannot be "
                        "established by counting")
        depth2_errored = False
    except CheckFailure as exc:
        print(f"  [ERROR] depth-2 traversal check failed to execute: {exc}",
              file=sys.stderr)
        depth2_actual = None
        depth2_note = f"CHECK FAILED TO EXECUTE — {exc}"
        depth2_errored = True
    checks.append(Check(
        "client-360-coverage-graph", "depth-2 traversal exceeds limit=200", 1,
        depth2_actual, depth2_note, errored=depth2_errored))
    checks.append(Check(
        "client-360-coverage-graph", "name variants, distinct persons", 5,
        n_variants))
    checks.append(Check(
        "client-360-coverage-graph", "coverage gaps (senior officer, 0 interactions)",
        3, n_gaps))
    checks.append(Check(
        "client-360-coverage-graph", "need-to-know interactions", 10, n_ntk))
    checks.append(Check(
        "client-360-coverage-graph", "false-positive person-crosswalk pair", 1,
        n_false_positive))
    checks.append(Check(
        "client-360-coverage-graph",
        "sees_need_to_know=FALSE principal sees zero need-to-know interactions",
        1, 1 if (blind_ok and sighted_ok and n_ntk > 0) else 0,
        f"PRIN-RES-002/PRIN-TRD-003 blind={blind_ok}, PRIN-COV-001 sighted="
        f"{sighted_ok}, {n_ntk} need-to-know interaction(s) exist to test "
        "suppression against — need-to-know is a policy binding distinct "
        "from MNPI"))

    # --- rating-and-spread-migration (Wave 11a) ----------------------------
    # The seven §F conditions from docs/wave11a-design.md §5. #5 and #7
    # delegate to validators/series.py rather than being reimplemented here:
    # both describe a RELATIONSHIP in the loaded series (spread widened AND
    # grade held; dates are genuinely ABSENT, not interpolated) that a
    # row-count query cannot express, exactly the reason traversal.py was
    # split out in Wave 10.
    FIBO_ = "https://spec.edmcouncil.org/fibo/ontology/"
    with pg_connect() as conn, conn.cursor() as cur:
        # #1 — cross-checked independently against financial_fact directly,
        # not trusted from debt_instrument alone: every obligor carrying an
        # instrument must ALSO carry a real reported LongTermDebt XBRL fact,
        # which is the public selection criterion §5's condition 1 names.
        n_debt_obligors = pg_scalar(cur, f"""
            SELECT COUNT(DISTINCT d.lei) FROM "{S}".debt_instrument d
            JOIN "{S}".financial_fact f
              ON f.lei = d.lei AND f.tag = 'LongTermDebt'""")
        n_instruments = pg_scalar(cur, f'SELECT COUNT(*) FROM "{S}".debt_instrument')
        # "laddered by maturity" is a claim about SPREAD, not count — a count
        # check would pass 60 instruments clustered on one maturity date.
        n_maturity_years = pg_scalar(cur, f"""
            SELECT COUNT(DISTINCT EXTRACT(YEAR FROM maturity))
            FROM "{S}".debt_instrument""")
        n_obs_dates = pg_scalar(cur, f'SELECT COUNT(DISTINCT obs_date) '
                                     f'FROM "{S}".spread_observation')
        # Every observation date must land on a REAL curve date — proof that
        # the benchmark leg is tenor-matched against an actual published
        # curve, not merely present as a column.
        n_obs_dates_curved = pg_scalar(cur, f"""
            SELECT COUNT(DISTINCT o.obs_date)
            FROM "{S}".spread_observation o
            JOIN "{S}".benchmark_curve c ON c.curve_date = o.obs_date""")

    # #4 — read from the assertion chain itself, not from
    # wave11a_grades.json["cadence"]["off_cycle_actual"], which is the
    # generator's own count of what it placed.
    n_off_cycle = fl_scalar(f"""
        SELECT (COUNT(?a) AS ?n) FROM <{L}> WHERE {{
          ?a a <{FIBO_}FBC/DebtAndEquities/CreditRatings/OrganizationCreditRating> .
          ?a <{EX}trigger> ?trigger .
          FILTER(?trigger NOT IN ("quarterly review",
                                   "initial rating (window start)"))
        }}""")
    # #6 — a RatingAssessmentEvent node exists in Fluree ONLY for a
    # confirmed rating action (see load_fluree_wave11a.py); an unconfirmed
    # candidate lands in context_debt instead, so this count cannot be
    # inflated by a hit that only named an agency in passing.
    n_rating_actions = fl_scalar(f"""
        SELECT (COUNT(?a) AS ?n) FROM <{L}> WHERE {{
          ?a a <{FIBO_}FND/Arrangements/Ratings/RatingAssessmentEvent> . }}""")

    checks.append(Check(
        "rating-and-spread-migration",
        "obligors with publicly traded debt (real LongTermDebt fact)", 25,
        n_debt_obligors,
        "condition 1: cross-checked directly against financial_fact, not "
        "trusted from debt_instrument alone"))
    checks.append(Check(
        "rating-and-spread-migration", "debt instruments loaded", 55,
        n_instruments, "condition 2"))
    checks.append(Check(
        "rating-and-spread-migration",
        "instruments laddered across distinct maturity years", 10,
        n_maturity_years,
        "condition 2: a spread claim, not a count — rejects a cluster on "
        "one or two maturity dates"))
    checks.append(Check(
        "rating-and-spread-migration", "observation dates (~24 months)", 450,
        n_obs_dates, "condition 3"))
    checks.append(Check(
        "rating-and-spread-migration",
        "observation dates matched to a real published curve date", 450,
        n_obs_dates_curved,
        "condition 3: proves tenor-matching against a real curve, not just "
        "a populated column"))
    checks.append(Check(
        "rating-and-spread-migration",
        "off-cycle rerating triggers (not quarterly/initial)", 4,
        n_off_cycle, "condition 4"))
    try:
        n_windows, n_confirmed = _rsm_divergence()
        div_note = ("condition 5: delegates to validators/series.py — "
                     "recomputed from spread_bp - market_oas_bp vs each "
                     "obligor's sector threshold; cannot be established by "
                     "counting")
        div_errored = False
    except CheckFailure as exc:
        print(f"  [ERROR] divergence recomputation failed to execute: {exc}",
              file=sys.stderr)
        n_windows = n_confirmed = None
        div_note = f"CHECK FAILED TO EXECUTE — {exc}"
        div_errored = True
    checks.append(Check(
        "rating-and-spread-migration",
        "divergence windows (spread widened, grade held throughout)", 3,
        n_windows, div_note, errored=div_errored))
    checks.append(Check(
        "rating-and-spread-migration",
        "divergence later confirmed by a worse rerating", 1, n_confirmed,
        div_note, errored=div_errored))
    checks.append(Check(
        "rating-and-spread-migration",
        "rating action disclosed in a real 8-K", 1, n_rating_actions,
        "condition 6"))
    try:
        n_sparse = _rsm_sparse()
        sparse_note = ("condition 7: delegates to validators/series.py — a "
                        "count would pass a fully interpolated series")
        sparse_errored = False
    except CheckFailure as exc:
        print(f"  [ERROR] sparsity recomputation failed to execute: {exc}",
              file=sys.stderr)
        n_sparse = None
        sparse_note = f"CHECK FAILED TO EXECUTE — {exc}"
        sparse_errored = True
    checks.append(Check(
        "rating-and-spread-migration",
        "instruments with genuine observation gaps (dates absent, not "
        "interpolated)", 2, n_sparse, sparse_note, errored=sparse_errored))

    # --- credit-surveillance-early-warning (Wave 11b) ---------------------
    # Nine §F floors. Every value below is read straight from Postgres or
    # Fluree as loaded -- never from sources/screening/wave11b_*.json, and
    # never re-derived from a constant the loader itself used to build that
    # data (see the Wave 8 note at the top of this file: a validator that
    # shares the loader's own wrong constants agrees with itself and passes).
    # Two of the nine -- composite cases and scripted cascades -- delegate to
    # validators/surveillance.py rather than reimplementing its recomputation,
    # exactly as conditions 5 and 7 above delegate to validators/series.py.
    with pg_connect() as conn, conn.cursor() as cur:
        checks.append(Check(
            "credit-surveillance-early-warning", "anchors under surveillance",
            50, pg_scalar(cur, f'SELECT COUNT(*) FROM "{S}".legal_entity '
                               "WHERE is_anchor"),
        ))

    try:
        n_window = _wave11b_signal_events_in_window()
        window_note = ("count PLUS an assertion: MIN/MAX(observed_at) "
                        "checked against WINDOW_START/WINDOW_END imported "
                        "from generators.fetch_8k_items (not re-derived) "
                        "-- a bare COUNT(*) cannot see a row straying "
                        "outside the fetch window; a violation renders as "
                        "a negative sentinel so it FAILS rather than "
                        "silently inflating the count")
        window_errored = False
    except CheckFailure as exc:
        print(f"  [ERROR] signal-events-in-window bound check failed to "
              f"execute: {exc}", file=sys.stderr)
        n_window = None
        window_note = f"CHECK FAILED TO EXECUTE — {exc}"
        window_errored = True
    checks.append(Check(
        "credit-surveillance-early-warning", "signal events in window", 400,
        n_window, window_note, errored=window_errored))

    with pg_connect() as conn, conn.cursor() as cur:
        checks.append(Check(
            "credit-surveillance-early-warning",
            "obligors with a real in-window Item 2.04", 2,
            pg_scalar(cur, f"""
                SELECT COUNT(DISTINCT lei) FROM "{S}".signal_event
                WHERE signal_type = '8k_event' AND provenance = 'public'
                  AND source_ref->>'item' = '2.04'"""),
            # CORRECTED per fix round 1 review: this clause is defence-in-
            # depth, not currently load-bearing. No signal_event row of ANY
            # provenance today carries signal_type='8k_event' AND
            # source_ref->>'item'='2.04' except these 4 real public rows --
            # the engineered cascade's item="2.04" marker lives only in
            # Fluree, on a SignalSource node, and was never materialised as
            # a signal_event row. Dropping provenance='public' from this
            # query still returns 3 today. The clause is kept because a
            # future load COULD materialise an engineered item=2.04 row in
            # this table, and provenance='public' is what would exclude it
            # then -- verified by planting such a row (rolled back) and
            # confirming the filter changes the answer.
            "'real' means provenance='public'; today the item mismatch "
            "alone already excludes the engineered cascade (never "
            "materialised as a signal_event row), so this clause is "
            "defence-in-depth against a future load, not load-bearing now",
        ))
        checks.append(Check(
            "credit-surveillance-early-warning",
            "obligors with resolved WARN matches", 3,
            pg_scalar(cur, f"""
                SELECT COUNT(DISTINCT lei) FROM "{S}".warn_match
                WHERE verdict = 'resolved'"""),
        ))
        checks.append(Check(
            "credit-surveillance-early-warning",
            "ambiguous WARN matches retained", 1,
            pg_scalar(cur, f"""SELECT COUNT(*) FROM "{S}".warn_match
                               WHERE verdict = 'ambiguous'"""),
            "rule #5: some joins must be imperfect on purpose",
        ))
        checks.append(Check(
            "credit-surveillance-early-warning", "GDELT mentions", 200,
            pg_scalar(cur, f'SELECT COUNT(*) FROM "{S}".gdelt_mention'),
        ))

    try:
        n_composite = _wave11b_composite_case()
        composite_note = ("delegates to validators/surveillance.py's "
                           "composite_case_check -- weighted score "
                           "recomputed from signal_weight / "
                           "escalation_threshold AS LOADED, is_subthreshold "
                           "imported not reimplemented; cannot be "
                           "established by counting")
        composite_errored = False
    except CheckFailure as exc:
        print(f"  [ERROR] composite case recomputation failed to execute: "
              f"{exc}", file=sys.stderr)
        n_composite = None
        composite_note = f"CHECK FAILED TO EXECUTE — {exc}"
        composite_errored = True
    checks.append(Check(
        "credit-surveillance-early-warning", "composite cases", 1,
        n_composite, composite_note, errored=composite_errored))

    try:
        n_cascade = _wave11b_cascade()
        cascade_note = ("delegates to validators/surveillance.py's "
                         "cascade_completeness -- signalAbout targets "
                         "checked EXACTLY against the facility's own "
                         "collateral_pledge and drawdown sets, not merely "
                         "nonempty; cannot be established by counting")
        cascade_errored = False
    except CheckFailure as exc:
        print(f"  [ERROR] scripted cascade recomputation failed to execute: "
              f"{exc}", file=sys.stderr)
        n_cascade = None
        cascade_note = f"CHECK FAILED TO EXECUTE — {exc}"
        cascade_errored = True
    checks.append(Check(
        "credit-surveillance-early-warning", "scripted cascades", 1,
        n_cascade, cascade_note, errored=cascade_errored))

    checks.append(Check(
        "credit-surveillance-early-warning",
        "obligors with a prior observation point", 50,
        fl_distinct(
            f"""SELECT ?lei FROM <{L}> WHERE {{
                ?p a <{EX}PriorObservation> .
                ?p <{EX}signalAbout> ?o .
                ?o <{EX}lei> ?lei .
            }}""", "lei"),
    ))

    # --- treasury-liquidity-position (Wave 12) -----------------------------
    # §F: ~15 clients, ~120 deposit accounts across 4 currencies, ~200
    # positions with laddered maturities, 30 trading days of 5-minute ticks,
    # >=1 day with an 8bp intraday move, >=2 clients breaching a
    # concentration limit, >=1 stale signal.
    #
    # HONESTY NOTE (per docs/wave12-design.md §3 and the Task 16 brief): the
    # 8bp-day and breaching-clients checks below are ROW-PRESENCE checks.
    # They read what the GENERATOR computed and cached to sources/screening/
    # wave12_ticks.json / wave12_treasury.json -- never a recomputation from
    # loaded ticks or a naive allocation rebuilt here. The ACTUAL proof --
    # that the condition holds against the LOADED data, not merely against
    # what the generator believed it built -- is validators/intraday.py,
    # which recomputes both independently from `intraday_tick` /
    # `investment_position` / `concentration_limit` / `permitted_instrument`.
    # A PASS below establishes only that the generator's own artifact still
    # claims the condition; each such check's note says so, so a future
    # reader cannot mistake a cached count for a recomputed proof.
    with pg_connect() as conn, conn.cursor() as cur:
        checks.append(Check(
            "treasury-liquidity-position", "treasury clients", 15,
            pg_scalar(cur, f'SELECT COUNT(*) FROM "{S}".treasury_client'),
        ))
        checks.append(Check(
            "treasury-liquidity-position",
            "deposit accounts (Wave 12 W12-* rows)", 100,
            pg_scalar(cur, f"""SELECT COUNT(*) FROM "{S}".deposit_account
                               WHERE account_id LIKE 'W12-%'"""),
            "deposit_account is a TWO-WRITER table -- Wave 9's 20 DEP-* "
            "rows are deliberately excluded from this count; see "
            "docs/ccf_dataprep_v2.md's Wave 12 extension register",
        ))
        checks.append(Check(
            "treasury-liquidity-position",
            "currencies spanned by deposit accounts", 4,
            pg_scalar(cur, f'SELECT COUNT(DISTINCT currency) '
                           f'FROM "{S}".deposit_account'),
        ))
        checks.append(Check(
            "treasury-liquidity-position", "investment positions", 150,
            pg_scalar(cur, f'SELECT COUNT(*) FROM "{S}".investment_position'),
        ))
        checks.append(Check(
            "treasury-liquidity-position",
            "positions laddered across distinct maturity dates", 10,
            pg_scalar(cur, f'SELECT COUNT(DISTINCT maturity_date) '
                           f'FROM "{S}".investment_position'),
            "a spread claim, not a count -- rejects a cluster on one or "
            "two maturity dates",
        ))
        checks.append(Check(
            "treasury-liquidity-position",
            "trading days of 5-minute ticks", 25,
            pg_scalar(cur, f'SELECT COUNT(DISTINCT trading_day) '
                           f'FROM "{S}".intraday_tick'),
        ))
        checks.append(Check(
            "treasury-liquidity-position",
            "ticks at 5-minute granularity", 10000,
            pg_scalar(cur, f'SELECT COUNT(*) FROM "{S}".intraday_tick'),
        ))
        checks.append(Check(
            "treasury-liquidity-position",
            "stale signal, age measured against the row's own as_of", 1,
            pg_scalar(cur, f"""SELECT COUNT(*) FROM "{S}".stale_signal
                               WHERE EXTRACT(EPOCH FROM (as_of - observed_at))
                                     / 60 > 15"""),
            "a genuine recomputation, NOT row-presence -- computed directly "
            "from the loaded as_of/observed_at pair, never against now() "
            "(RULING F15: age-vs-now() can never fail once minutes have "
            "passed). validators/intraday.py adds only the well-formedness "
            "and fresh-signal-exists cross-checks on top of this",
        ))

    import json as _json
    try:
        _tick_meta = _json.loads(
            (REPO_ROOT / "sources" / "screening" / "wave12_ticks.json")
            .read_text())
        _n_8bp = len(_tick_meta.get("eight_bp_days", []))
    except Exception:  # noqa: BLE001
        _n_8bp = None
    checks.append(Check(
        "treasury-liquidity-position",
        "day carrying an engineered >=8bp intraday move", 1, _n_8bp,
        "ROW-PRESENCE ONLY -- read from the generator's own cached "
        "eight_bp_days list (sources/screening/wave12_ticks.json), NOT "
        "recomputed from loaded data. The proof is validators/intraday.py's "
        "maximum-90-minute-rolling-move recomputation from `intraday_tick`; "
        "a PASS here shows only that the generator's artifact still claims "
        "the day, not that the loaded ticks still carry the move",
    ))

    try:
        _treasury_meta = _json.loads(
            (REPO_ROOT / "sources" / "screening" / "wave12_treasury.json")
            .read_text())
        _n_breach = sum(1 for a in _treasury_meta.get("measured_allocations", [])
                        if a.get("breaches"))
    except Exception:  # noqa: BLE001
        _n_breach = None
    checks.append(Check(
        "treasury-liquidity-position",
        "clients breaching a concentration limit", 2, _n_breach,
        "ROW-PRESENCE ONLY -- read from the generator's own cached "
        "measured_allocations (sources/screening/wave12_treasury.json), NOT "
        "recomputed. The proof is validators/intraday.py's independent "
        "rebuild of the naive optimal allocation from loaded positions, "
        "limits and permitted-instrument lists; a PASS here shows only "
        "that the generator's artifact still claims the breach",
    ))

    # --- fx-post-trade-reconciliation (Wave 12) -----------------------------
    # §F: ~500 trades, 6 pairs, 3 systems with distinct clock offsets, ~60
    # breaks at ~2/3 timing / ~1/3 genuine, >=10 chained trades, >=3 with 2+
    # amendments, >=1 inversion, >=1 survivor, full rate coverage.
    #
    # Same honesty rule as the treasury block above: the inversion and
    # survivor checks are ROW-PRESENCE, read from the generator's cached
    # classification fields, never recomputed here. The actual proof is
    # validators/reconcile.py, which recomputes both the raw and the
    # clock-aligned classification from Postgres `system_trade_record`
    # values plus Fluree `ex:systemObservedAt` / `ex:clockOffsetSeconds` --
    # exactly the recomputation RULING F24 made possible (before that fix,
    # every system's value was identical and the raw difference always
    # recomputed to zero, so no inversion or survivor could ever have been
    # ESTABLISHED, only asserted).
    with pg_connect() as conn, conn.cursor() as cur:
        checks.append(Check(
            "fx-post-trade-reconciliation", "FX trades", 400,
            pg_scalar(cur, f'SELECT COUNT(*) FROM "{S}".fx_trade'),
        ))
        checks.append(Check(
            "fx-post-trade-reconciliation", "currency pairs", 6,
            pg_scalar(cur, f'SELECT COUNT(DISTINCT pair) FROM "{S}".fx_trade'),
        ))
        checks.append(Check(
            "fx-post-trade-reconciliation", "breaks", 50,
            pg_scalar(cur, f'SELECT COUNT(*) FROM "{S}".break_record'),
        ))
        n_timing = pg_scalar(cur, f"""SELECT COUNT(*) FROM "{S}".break_record
                                      WHERE designed_class = 'timing'""")
        n_genuine_designed = pg_scalar(cur, f"""
            SELECT COUNT(*) FROM "{S}".break_record
            WHERE designed_class = 'genuine'""")
        checks.append(Check(
            "fx-post-trade-reconciliation",
            "break mix ~2/3 timing / ~1/3 genuine", 40, n_timing,
            f"{n_timing} timing + {n_genuine_designed} genuine of "
            f"{(n_timing or 0) + (n_genuine_designed or 0)} -- this counts "
            "the loaded break_record.designed_class column (the generator's "
            "own classification), NOT a recomputation; "
            "validators/reconcile.py recomputes each break's raw AND "
            "aligned classification independently and is what would catch "
            "a mismatch between designed_class and what the loaded system "
            "values actually produce",
        ))
        checks.append(Check(
            "fx-post-trade-reconciliation",
            "every (pair, value_date) has an fx_reference_rate row", 0,
            n if (n := pg_scalar(cur, f"""
                SELECT -COUNT(*) FROM (
                  SELECT DISTINCT pair, value_date FROM "{S}".fx_trade
                  EXCEPT
                  SELECT pair, obs_date FROM "{S}".fx_reference_rate
                ) missing""")) is not None else None,
            "negated so 0 missing (pair, value_date) combos passes -- full "
            "rate coverage",
        ))

    n_offset_nodes = fl_distinct(
        f"SELECT ?s ?o FROM <{L}> WHERE {{ ?s <{EX}clockOffsetSeconds> ?o }}",
        "s")
    n_distinct_offsets = fl_distinct(
        f"SELECT ?s ?o FROM <{L}> WHERE {{ ?s <{EX}clockOffsetSeconds> ?o }}",
        "o")
    checks.append(Check(
        "fx-post-trade-reconciliation",
        "systems carrying distinct clock offsets", 3, n_distinct_offsets,
        f"{n_offset_nodes} system nodes, {n_distinct_offsets} distinct "
        "offset values -- distinctness is load-bearing: three EQUAL "
        "offsets would make align_clocks a no-op and no inversion could "
        "occur through it",
    ))

    n_chained, n_two_plus = _fx_chain_shape()
    checks.append(Check(
        "fx-post-trade-reconciliation",
        "trades carrying an amendment chain", 10, n_chained,
        "a real recomputation from Fluree ex:amendmentSeq on amd-* "
        "subjects (see _fx_chain_shape below) -- chain SHAPE needs no "
        "clock alignment or business-rule rebuild, unlike the inversion/"
        "survivor checks, so counting it directly here is honest",
    ))
    checks.append(Check(
        "fx-post-trade-reconciliation",
        "trades with 2+ amendments", 3, n_two_plus,
    ))

    try:
        _fx_meta = _json.loads(
            (REPO_ROOT / "sources" / "screening" / "wave12_fx.json")
            .read_text())
        _fx_breaks = _fx_meta.get("breaks", [])
        _n_inversion = sum(
            1 for b in _fx_breaks
            if b.get("classification_raw") == "genuine"
            and b.get("classification_aligned") != "genuine")
        _n_survivor = sum(
            1 for b in _fx_breaks
            if b.get("classification_raw") == "genuine"
            and b.get("classification_aligned") == "genuine")
    except Exception:  # noqa: BLE001
        _n_inversion = _n_survivor = None
    checks.append(Check(
        "fx-post-trade-reconciliation",
        "break that inverts under clock alignment", 1, _n_inversion,
        "ROW-PRESENCE ONLY -- read from the generator's own cached "
        "classification_raw / classification_aligned fields "
        "(sources/screening/wave12_fx.json), NOT recomputed. The proof is "
        "validators/reconcile.py's independent alignment, computed from "
        "Postgres system_trade_record values plus Fluree systemObservedAt/"
        "clockOffsetSeconds; a PASS here shows only that the generator's "
        "artifact still claims the flip, not that the loaded data still "
        "produces it",
    ))
    checks.append(Check(
        "fx-post-trade-reconciliation",
        "break surviving alignment as genuine", 1, _n_survivor,
        "ROW-PRESENCE ONLY -- same cached-artifact caveat as the inversion "
        "row directly above; validators/reconcile.py's independent "
        "alignment recomputation is the actual proof, not this count",
    ))

    # ---- credit-memo-context (Wave 13a) ---------------------------------
    # Every row here is ROW-PRESENCE or a plain count. The actual proof that
    # the debt arithmetic is right is validators/memo_debt.py, which
    # recomputes all four components from the stores and is mutation-tested
    # six ways. A PASS below shows the data exists, not that it computes.
    with pg_connect() as conn, conn.cursor() as cur:
        n_memo_grade = pg_scalar(cur, f"""
            SELECT count(*) FROM (
              SELECT f.borrower_lei FROM "{S}".facility f
              JOIN "{S}".collateral_pledge p ON p.facility_id = f.facility_id
              GROUP BY f.borrower_lei) x""")
        # Filter on `section`, NOT on `form`: the EX-10 corpus was fetched
        # FROM 10-K and 8-K filings and carries those same form values, so a
        # form filter returns the whole 136-document corpus and reports it as
        # narrative coverage. Only Wave 13a's section documents carry `section`.
        n_narrative = mongo_count("document", {"section": {"$exists": True}})
        n_memoranda = mongo_count("memorandum")
        n_templates = pg_scalar(cur, f'SELECT count(DISTINCT memo_type) '
                                     f'FROM "{S}".memo_section_template')
        n_breach = pg_scalar(cur, f'SELECT count(*) FROM "{S}".memo_context_debt '
                                  "WHERE aggregate_debt > 0.25")
        n_below = pg_scalar(cur, f'SELECT count(*) FROM "{S}".memo_context_debt '
                                 "WHERE aggregate_debt <= 0.25")
        n_rich = pg_scalar(cur, f'SELECT count(DISTINCT sic) FROM "{S}".peer_cohort '
                                "WHERE expected_active >= 15")
        n_thin = pg_scalar(cur, f'SELECT count(DISTINCT sic) FROM "{S}".peer_cohort '
                                "WHERE expected_active BETWEEN 1 AND 3")

    checks.append(Check(
        "credit-memo-context", "narrative documents (10-K/10-Q/8-K sections)",
        60, n_narrative,
        "10-K Item 1A/Item 7, 10-Q Item 2 MD&A and 8-K EX-99 as separate "
        "section documents; the EX-10 corpus inherited from "
        "covenant-cross-reference is counted separately",
    ))
    checks.append(Check(
        "credit-memo-context", "internal credit memoranda", 38, n_memoranda,
        "§F3 asks ~40",
    ))
    checks.append(Check(
        "credit-memo-context", "memo types with distinct section templates",
        4, n_templates,
        "distinctness is asserted by validators/memo_debt.py -- four templates "
        "differing only in name would satisfy this count",
    ))
    checks.append(Check(
        "credit-memo-context", "obligors breaching debt_tolerance", 1, n_breach,
        "§F5. A breach count ALONE proves nothing -- a weighting that pushes "
        "every obligor over satisfies it while demonstrating nothing, which is "
        "why the row below exists and why memo_debt.py requires the covenant "
        "term to be load-bearing rather than merely present",
    ))
    checks.append(Check(
        "credit-memo-context", "obligors BELOW debt_tolerance (the spread)",
        1, n_below,
        "the other half of §F5: without obligors on both sides the tolerance "
        "discriminates nothing. Paired deliberately with the row above",
    ))
    checks.append(Check(
        "credit-memo-context", "SIC cohorts with >= 15 active peers", 1, n_rich,
        "§F4, measured against an ACTIVE denominator (peers reporting any "
        "tracked concept in the period), not the full SIC cohort -- see "
        "generators/fetch_peer_cohorts.py",
    ))
    checks.append(Check(
        "credit-memo-context", "SIC cohorts with <= 3 active peers", 1, n_thin,
        "§F4's thin end. Natural, not engineered: 176 of 1,119 cohorts are "
        "genuinely thinned by frames coverage",
    ))
    checks.append(Check(
        "credit-memo-context", "obligors with collateral coverage", 13,
        n_memo_grade,
        "exposure+collateral is the binding leg of §F1's five-way coverage; "
        "three further memo-grade obligors are UNSECURED rather than "
        "uncovered (no grant clause in the filed agreement) and correctly "
        "carry no pledge",
    ))

    # --- kyc-refresh-beneficial-ownership (Wave 13b) ----------------------
    #
    # Six of these eight floors are ALSO gated, with falsification arms, by
    # `validators/beneficial_ownership.py`. The two registers do different
    # jobs: this one proves the floor is met, that one proves the CONDITION
    # behind the floor is real. §F5's 571 pre-existing variants are exactly
    # why both are needed — they cleared a floor of 8 while satisfying none of
    # the condition (`docs/wave13b-design.md` §1.2).
    with pg_connect() as conn, conn.cursor() as cur:
        checks.append(Check(
            "kyc-refresh-beneficial-ownership",
            "entities with a chain reaching a natural person", 50,
            pg_scalar(cur, f'SELECT COUNT(DISTINCT entity_id) FROM "{S}".bo_chain'),
            "§F1",
        ))
        checks.append(Check(
            "kyc-refresh-beneficial-ownership",
            "pseudonymized person nodes", 200,
            pg_scalar(cur, f'SELECT COUNT(*) FROM "{S}".psc_person'),
            "§F2. No real name, DOB or mapping was retained — "
            "validators/test_psc_pseudonymization.py",
        ))
        checks.append(Check(
            "kyc-refresh-beneficial-ownership",
            "chains reaching depth 5+", 3,
            pg_scalar(cur, f'SELECT COUNT(*) FROM "{S}".bo_chain WHERE depth >= 5'),
            "§F3. Depth is RE-WALKED in Fluree by beneficial_ownership.py — "
            "GLEIF's real maximum for this cast is 4",
        ))
        checks.append(Check(
            "kyc-refresh-beneficial-ownership",
            "persons with variants across 2+ registries", 8,
            pg_scalar(cur, f"""
                SELECT COUNT(*) FROM (
                    SELECT v.person_key FROM "{S}".person_name_variant v
                    JOIN "{S}".person p USING (person_key)
                    WHERE p.person_key_source = 'psc'
                    GROUP BY v.person_key
                    HAVING COUNT(DISTINCT v.source) >= 2) t"""),
            "§F5. ACROSS sources — the estate's 571 def14a variants are one "
            "source in one rendering and satisfy none of this",
        ))
        checks.append(Check(
            "kyc-refresh-beneficial-ownership",
            "transliteration-capable persons", 2,
            pg_scalar(cur, f'SELECT COUNT(*) FROM "{S}".psc_person '
                           "WHERE is_transliterated"),
            "§F5. Reconstructed from nationality — Companies House publishes "
            "PSC names already romanized",
        ))
        checks.append(Check(
            "kyc-refresh-beneficial-ownership",
            "false-positive person pairs", 1,
            pg_scalar(cur, f"""
                SELECT COUNT(*) FROM "{S}".person_crosswalk c
                JOIN "{S}".person p USING (person_key)
                WHERE p.person_key_source = 'psc'
                  AND c.match_band = 'false_positive'"""),
            "§F5. RE-SCORED by beneficial_ownership.py; the band is not read "
            "back",
        ))
        checks.append(Check(
            "kyc-refresh-beneficial-ownership",
            "sanctions matches below certainty", 1,
            pg_scalar(cur, f'SELECT COUNT(*) FROM "{S}".sanctions_screening_result '
                           "WHERE in_review_band"),
            "§F6. Bounds come from resolution_policy, never from the gate",
        ))
        checks.append(Check(
            "kyc-refresh-beneficial-ownership",
            "entities with an EU-resident beneficial owner", 2,
            pg_scalar(cur, f'SELECT COUNT(DISTINCT entity_id) FROM "{S}".bo_chain '
                           "WHERE person_is_eu_resident"),
            "§F7. Invisibility proved by a two-principal traversal diff, not "
            "by this count",
        ))
        checks.append(Check(
            "kyc-refresh-beneficial-ownership",
            "beneficial-ownership thresholds bound to intent", 2,
            pg_scalar(cur, f"""
                SELECT COUNT(*) FROM (
                    SELECT jurisdiction FROM "{S}".bo_threshold
                    GROUP BY jurisdiction
                    HAVING COUNT(DISTINCT threshold_pct) > 1) t"""),
            "§B. Jurisdictions where intent CHANGES the answer — without "
            "these the intent parameter is decorative",
        ))
        checks.append(Check(
            "kyc-refresh-beneficial-ownership",
            "clients with a refresh overdue", 1,
            pg_scalar(cur, f'SELECT COUNT(*) FROM "{S}".kyc_refresh_state '
                           "WHERE status = 'overdue'"),
            "§E names a refresh falling due as a supersession trigger; "
            "anchored on a fixed as_of, never now()",
        ))
    checks.append(Check(
        "kyc-refresh-beneficial-ownership", "KYC documents with passages", 30,
        mongo_count("kyc_document"),
        "§F8. The registry contradiction is RECOMPUTED from declared_* vs "
        "bo_chain by beneficial_ownership.py, never read from a flag",
    ))
    checks.append(Check(
        "kyc-refresh-beneficial-ownership", "ownership declarations", 5,
        mongo_count("kyc_document", {"kind": "ownership_declaration"}),
        "§F8",
    ))

    # --- facility-terms-snapshot (T1, data landed in Wave 4) ---------------
    #
    # REGISTERED 2026-08-22, eleven waves after its data was loaded. It had no
    # rows here, so it never appeared in the register everyone reads to answer
    # "what is done" — and both `HANDOFF.md` §3 and `spec-digest.md` §5
    # miscounted the catalog as a result.
    #
    # A product is not done because its data exists. It is done when a gate
    # would notice if the data stopped existing. Unregistered is
    # indistinguishable from unbuilt from the outside, and from guarded on the
    # inside.
    with pg_connect() as conn, conn.cursor() as cur:
        checks.append(Check(
            "facility-terms-snapshot", "facilities across the anchor set", 40,
            pg_scalar(cur, f'SELECT COUNT(*) FROM "{S}".facility'),
            "§F ~40",
        ))
        checks.append(Check(
            "facility-terms-snapshot", "distinct facility types", 4,
            pg_scalar(cur, f'SELECT COUNT(DISTINCT facility_type) '
                           f'FROM "{S}".facility'),
            "§F: revolver, term A, term B, delayed draw — a taxonomy, not a "
            "label",
        ))
        checks.append(Check(
            "facility-terms-snapshot", "facilities with >= 1 amendment", 8,
            pg_scalar(cur, f'SELECT COUNT(*) FROM "{S}".facility '
                           "WHERE amendment_count >= 1"),
            "§F ~8. This is the material covenant-in-force-as-of time-travels "
            "over",
        ))
        checks.append(Check(
            "facility-terms-snapshot", "syndicated facilities", 4,
            pg_scalar(cur, f'SELECT COUNT(*) FROM "{S}".facility '
                           "WHERE syndicated"),
            "§F ~4, seeding syndicated-lending-co-lender",
        ))
        # §F's floor is on the DEPTH of a grid, not on how many exist. The two
        # checks are paired deliberately: the inverted one alone would pass
        # vacuously if no facility carried a grid at all.
        checks.append(Check(
            "facility-terms-snapshot", "pricing grids with >= 3 leverage tiers", 1,
            pg_scalar(cur, f'SELECT COUNT(*) FROM "{S}".facility '
                           "WHERE pricing_grid IS NOT NULL "
                           "AND jsonb_array_length(pricing_grid->'tiers') >= 3"),
            "§F: a grid is a structure rather than a scalar",
        ))
        checks.append(Check(
            "facility-terms-snapshot", "grids SHALLOWER than 3 tiers (inverted: want 0)", 0,
            n if (n := pg_scalar(cur, f'SELECT -COUNT(*) FROM "{S}".facility '
                                      "WHERE pricing_grid IS NOT NULL "
                                      "AND jsonb_array_length(pricing_grid->'tiers') < 3")) is not None else None,
            "negated so 0 shallow grids passes; paired with the row above so "
            "neither can pass vacuously",
        ))

        # --- #17 abs-securitization-surveillance (Wave 14) ----------------
        checks.append(Check(
            "abs-securitization-surveillance", "deals loaded", 2,
            pg_scalar(cur, f'SELECT COUNT(*) FROM "{S}".abs_deal'),
            "spec says 2-3; depth not breadth",
        ))
        checks.append(Check(
            "abs-securitization-surveillance", "deals with all 12 periods", 3,
            pg_scalar(cur, f"""
                SELECT COUNT(*) FROM (
                    SELECT deal_id FROM "{S}".abs_loan_period
                    GROUP BY deal_id HAVING COUNT(DISTINCT period) >= 12) t"""),
        ))
        checks.append(Check(
            "abs-securitization-surveillance", "minimum loans in any deal-period", 15000,
            pg_scalar(cur, f"""
                SELECT COALESCE(MIN(n), 0) FROM (
                    SELECT COUNT(*) AS n FROM "{S}".abs_loan_period
                    GROUP BY deal_id, period) t"""),
            "the MINIMUM, not the mean -- a mean hides a thin period. "
            "COALESCE because MIN over an empty table returns NULL, and a "
            "NULL renders SKIP, which does not fail the run",
        ))
        checks.append(Check(
            "abs-securitization-surveillance", "deals with >= 4 distinct tranches", 3,
            pg_scalar(cur, f"""
                SELECT COUNT(*) FROM (
                    SELECT deal_id FROM "{S}".abs_tranche
                    GROUP BY deal_id HAVING COUNT(DISTINCT class_name) >= 4) t"""),
            "COUNT(DISTINCT class_name): abs_tranche's PK is tranche_id alone, "
            "so four rows all named A-1 satisfied a bare COUNT(*)",
        ))
        # RULING F46: `FROM <{L}>` is mandatory on both Fluree checks below.
        # Without it Fluree answers HTTP 500, fl_scalar swallows the error and
        # returns None, None renders SKIP, and SKIP does not fail the run --
        # the condition would be registered and then never evaluated, with the
        # register still exiting 0. Measured before the fix: both raised.
        # RULING F56: §F reads ">= 3 trigger definitions" PER DEAL, and this
        # counted the estate -- 10 across three deals against a floor of 9,
        # while every deal sits at exactly 3. Move one trigger from one deal to
        # another and the estate total is still 10 and it still passes, with a
        # deal carrying 2. Counted the way the tranche check above already
        # counts: deals meeting the floor, floor = number of deals.
        checks.append(Check(
            "abs-securitization-surveillance", "deals with >= 3 trigger definitions", 3,
            fl_distinct(f"""
                SELECT ?d FROM <{L}> WHERE {{
                  ?d <{SPECIFIES_TRIGGER}> ?t .
                  ?t <{EX}thresholdValue> ?v }}
                GROUP BY ?d HAVING (COUNT(?t) >= 3)""", "d"),
            "per deal, as §F reads it -- not 10 summed across three",
        ))
        # RULING F57: the INTERSECTION, not either side. F48 fixed documents
        # -> ids and stopped one step short. Measured before this fix: the
        # register read 10 against a floor of 9, but `TAOT-2022-B-yield_supplement`
        # is an anchor for something Fluree carries no thresholdValue for, and
        # `SDART-2022-6-delinquency-amendment` is a threshold with no anchor.
        # Two errors cancelling into a false margin -- the true figure is 9,
        # exactly ON the floor, so deleting any one real anchor still passed.
        checks.append(Check(
            "abs-securitization-surveillance", "distinct thresholds carrying an anchor", 9,
            anchored_thresholds(),
            "the INTERSECTION of anchored ids and thresholds -- an anchor for "
            "a non-threshold used to pad the margin",
        ))
        # RULING F47: the `?s ex:thresholdValue ?v` line is what makes this an
        # ABS check. Without it the pattern counts ANY engineered supersession
        # in the estate -- measured 3, of which two belong to other waves
        # (Wave 11b's engineered 8-K signal and an engineered entity), so
        # deleting Wave 14's amendment outright would still return 2 and PASS.
        # All 10 nodes carrying ex:thresholdValue are abs-trigger-*, so the
        # predicate scopes the check without inventing a marker for it.
        checks.append(Check(
            "abs-securitization-surveillance", "engineered ABS trigger amendments", 1,
            fl_scalar(f"""
                SELECT (COUNT(?s) AS ?n) FROM <{L}> WHERE {{
                  ?o <{EX}supersededBy> ?s .
                  ?s <{EX}provenance> "synthetic — engineered" .
                  ?s <{EX}thresholdValue> ?v }}"""),
            "labelled engineered; no real auto ABS amends a trigger",
        ))
        checks.append(Check(
            "abs-securitization-surveillance", "principals restricted below loan level", 1,
            pg_scalar(cur, f"""
                SELECT COUNT(*) FROM "{S}".abs_granularity_entitlement
                WHERE max_granularity <> 'loan'"""),
        ))
        # RULING F58: only the LATEST batch, and only if it was measured
        # against the pool as it stands now. Counting DISTINCT granularity over
        # the whole table meant three historical batches satisfied it forever:
        # truncate abs_loan_period tomorrow and this stayed 4/4. `row_basis` was
        # recorded by abs_cost.py and read by nothing, which is what made the
        # staleness invisible.
        checks.append(Check(
            "abs-securitization-surveillance", "granularities costed against TODAY's pool", 4,
            pg_scalar(cur, f"""
                SELECT COUNT(DISTINCT granularity)
                FROM "{S}".abs_cost_measurement
                WHERE row_basis = (SELECT COUNT(*) FROM "{S}".abs_loan_period)
                  AND measured_at = (SELECT MAX(measured_at)
                                     FROM "{S}".abs_cost_measurement)"""),
            "latest batch only, and only if row_basis still matches the pool",
        ))

        # RULING F59 -- §F bullet 5, which lived ONLY in abs_surveillance.py.
        # `conditions.py --product abs-securitization-surveillance` reported
        # 9/9 green without ever evaluating it. Unregistered is invisible.
        checks.append(Check(
            "abs-securitization-surveillance", "deals whose trigger gap narrows monotonically", 1,
            narrowing_deals(cur),
            "§F: a trajectory, not a static distance. Counts deals with a "
            "run of >= 3 consecutive narrowing periods",
        ))

        # RULING F60 -- §F bullet 7, registered nowhere at all, and it could
        # afford to be: keyed on (asset_class, vintage, credit_tier) every cell
        # held exactly one deal, so deal_count was 1 in all 36 rows and every
        # "benchmark" compared a deal against itself. Re-keyed in Task 15's fix
        # round; this is the check that would have caught it.
        checks.append(Check(
            "abs-securitization-surveillance", "vintage cells benchmarking >= 2 deals", 1,
            pg_scalar(cur, f"""
                SELECT COUNT(*) FROM (
                    SELECT vintage FROM "{S}".abs_vintage_benchmark
                    WHERE deal_count >= 2 GROUP BY vintage) t"""),
            "a cohort of one is not a benchmark",
        ))

    # --- #18 ib-opportunity-synthesis (Wave 16) -----------------------------
    # Only the four §F floors that carry a CONDITION are registered. The
    # envelope figures -- ~40 bankers, ~200 prospects, ~600 signals, ~50
    # notes -- are shape, not targets (Dave, 2026-08-24), and are not floors.
    #
    # R1 -- the 13D condition queries FLUREE, not Postgres: §C assigns
    # activist stakes to Fluree, and `signal_event` belongs to a DIFFERENT
    # product (credit-surveillance-early-warning); counting its rows would
    # report another product's data as this one's. `ex:signalType` is
    # deliberately NOT asserted on an OpportunitySignal node -- it is
    # Postgres-owned vocabulary (loaders/load_fluree_wave16.py), and
    # partition.py's POSTGRES_OWNED_ATTRS scan is what catches it if it ever
    # were -- so the signal type is read off the rdfs:label prefix that
    # loader writes instead ("{signal_type} -- {lei} -- {observed_at}").
    #
    # R3 -- IN-WINDOW CURRENT signals only. 1,270 rows exist total, 916 are
    # is_current, and only 723 of those also fall inside
    # IB_WINDOW_START..IB_WINDOW_END; the other 193 current-but-stale rows
    # are real discrete catalysts kept for replay, decayed to zero weight by
    # the ranking's half-life. Counting the raw 1,270 (or even the 916)
    # would claim coverage this product does not have.
    checks.append(Check(
        "ib-opportunity-synthesis", "real Schedule 13D filings", 5,
        fl_scalar(f"""
            SELECT (COUNT(?s) AS ?n) FROM <{L}> WHERE {{
              ?s a <{EX}OpportunitySignal> .
              ?s <{RDFS_LABEL_IRI}> ?label .
              ?s <{EX}isCurrent> "true" .
              ?s <{EX}validFrom> ?d .
              FILTER(STRSTARTS(?label, "activist_stake_13d -- "))
              FILTER(?d >= "{IB_WINDOW_START}" && ?d <= "{IB_WINDOW_END}") }}"""),
        "in-window AND is_current -- not the 1,270-row raw signal ledger",
    ))
    with pg_connect() as conn, conn.cursor() as cur:
        checks.append(Check(
            "ib-opportunity-synthesis", "weight-vector versions", 2,
            pg_scalar(cur, f'SELECT COUNT(DISTINCT weight_version) '
                           f'FROM "{S}".perspective_weight'),
        ))
    # R2 -- restricted_list lives in SQLITE, coverage_assignment lives in
    # POSTGRES. A single SQL JOIN across them cannot execute; wrapped in a
    # bare try/except (as pg_scalar is) that failure is swallowed to None
    # and the condition renders SKIP -- a broken query wearing the costume
    # of an unrun wave. Read each side from its own store and intersect in
    # Python instead.
    checks.append(Check(
        "ib-opportunity-synthesis", "restricted entities inside coverage", 2,
        ib_restricted_in_coverage(),
        "candidate-set absence proved separately by validators/ib_rank.py",
    ))
    # R4 -- divergence and note-materiality are ORDERINGS, not cardinalities;
    # no COUNT(*) expresses either. Both import validators/ib_rank.py's own
    # recomputation rather than reimplementing it, so a broken ranking
    # surfaces as FAIL, not SKIP -- `actual is None` renders SKIP in this
    # register, and a SKIP reads as "wave not yet run", not "check is broken".
    try:
        div_holds = _ib_divergence()
        div_note = ("one LEI ranks top-3 under PSP-MA weights and outside "
                     "top-20 under PSP-DCM, from the SAME signal set -- "
                     "delegates to validators/ib_rank.py's divergence_holds; "
                     "an ordering, not a count")
        div_errored = False
    except CheckFailure as exc:
        print(f"  [ERROR] ib-opportunity-synthesis divergence recomputation "
              f"failed to execute: {exc}", file=sys.stderr)
        div_holds = None
        div_note = f"CHECK FAILED TO EXECUTE — {exc}"
        div_errored = True
    checks.append(Check(
        "ib-opportunity-synthesis", "perspective divergence (M&A vs DCM)", 1,
        None if div_holds is None else int(div_holds),
        div_note, errored=div_errored,
    ))
    try:
        n_notes = _ib_note_materiality()
        note_note = ("banker-local NOTES whose OWN entity's rank position "
                     "moves when included -- delegates to "
                     "validators/ib_rank.py's note_materiality_counts; the "
                     "§F unit is notes, not (banker, LEI) position changes")
        note_errored = False
    except CheckFailure as exc:
        print(f"  [ERROR] ib-opportunity-synthesis note-materiality "
              f"recomputation failed to execute: {exc}", file=sys.stderr)
        n_notes = None
        note_note = f"CHECK FAILED TO EXECUTE — {exc}"
        note_errored = True
    checks.append(Check(
        "ib-opportunity-synthesis", "notes moving their own entity's rank", 5,
        n_notes, note_note, errored=note_errored,
    ))

    # --- #19 aml-typology-match (Wave 17) -----------------------------------
    # Only the six §F floors that carry a CONDITION are registered, plus the
    # graph-disconnect safety property. The envelope figures -- ~200 parties,
    # ~5,000 transactions, ~150 alerts/~30 genuine -- are shape, not targets
    # (same Dave ruling Wave 16's block cites above), and are not floors. The
    # name-guard safety property (Tasks 5/6) is likewise not registered here:
    # it is not a §F `>= N` and is already proven live by
    # validators/test_aml_typology.py::test_no_generated_party_collides_with_a_real_entity,
    # re-run against the FINAL artifact on every test run.
    #
    # Four of the six floors are COMPOUND -- an existence count plus an
    # ordering/absence condition that no count can establish -- so each gets
    # TWO checks: the count registered directly against Fluree/Postgres/
    # SQLite, and the condition delegated to validators/aml_typology.py's own
    # seven floor functions, exactly as the ib-opportunity-synthesis block
    # above delegates to validators/ib_rank.py. The other two floors (depth-3,
    # three renderings) and the safety property are pure ordering/absence with
    # no separate count to register.
    checks.append(Check(
        "aml-typology-match", "typologies loaded", 4,
        fl_distinct(f"SELECT ?t FROM <{L}> WHERE {{ ?t a <{EX}Typology> }}", "t"),
        "structuring/funnel/trade-based/shell -- the ANCHORING half of this "
        "floor (each cites a real advisory passage) is not a count; see the "
        "delegated check below",
    ))
    checks.append(Check(
        "aml-typology-match", "filing posture versions with distinct dates", 2,
        fl_distinct(f"SELECT ?d FROM <{L}> WHERE {{ "
                    f"?p a <{EX}FilingPosture> ; <{EX}postureEffectiveFrom> ?d }}",
                    "d"),
        "distinct EFFECTIVE DATES, not node count -- two postures sharing a "
        "date could not be told apart by as_of",
    ))
    with pg_connect() as conn, conn.cursor() as cur:
        checks.append(Check(
            "aml-typology-match", "parties declaring an OFAC near-match", 1,
            pg_scalar(cur, f'SELECT COUNT(*) FROM "{S}".aml_party '
                           f"WHERE ofac_near_match IS NOT NULL"),
            "the matched sanctions entry is real and public; the party is "
            "invented -- the BAND the similarity lands in is not a count; "
            "see the delegated check below",
        ))
    try:
        sar_count = sqlite_scalar(
            SQLITE_PATH, "SELECT COUNT(*) FROM sar_classification")
        sar_errored = False
    except CheckFailure as exc:
        print(f"  [ERROR] aml-typology-match SAR-record count query failed "
              f"to execute: {exc}", file=sys.stderr)
        sar_count = None
        sar_errored = True
    checks.append(Check(
        "aml-typology-match", "SAR records with confidentiality classification", 3,
        sar_count,
        "raw SQLite count -- INVISIBLE TO AT LEAST ONE test principal is not "
        "a count; see the delegated SAR-confidentiality check below",
        errored=sar_errored,
    ))
    checks.append(_run_aml_floor(
        "typology anchoring (Fluree -> Mongo passage)", "typology_anchoring",
        "ordering/absence, not a count -- delegates to "
        "validators/aml_typology.py's typology_anchoring, which also "
        "asserts the >=4 typology population above and 0 unanchored "
        "matchesTypology targets"))
    checks.append(_run_aml_floor(
        "network requiring depth 3 (walked live, not labelled)",
        "depth_three_holds",
        "ordering/absence, not a count -- delegates to "
        "validators/aml_typology.py's depth_three_holds, which walks the "
        "live ex:transactedWith graph for a pair at EXACTLY distance 3; "
        "`requires_depth` is a label and is never read"))
    checks.append(_run_aml_floor(
        "posture flip (same disposition, two as_of values)",
        "posture_flip_holds",
        "ordering/absence, not a count -- delegates to "
        "validators/aml_typology.py's posture_flip_holds, which evaluates "
        "the SAME disposition under two as_of values resolving to two "
        "different postures and requires the answers to DIFFER"))
    checks.append(_run_aml_floor(
        "SAR confidentiality (l1 assembles blind)",
        "sar_confidentiality_holds",
        "ordering/absence, not a count -- delegates to "
        "validators/aml_typology.py's sar_confidentiality_holds, which "
        "assembles l1's stored projection plan over every alert and "
        "requires nothing it yields to reveal a SAR exists"))
    checks.append(_run_aml_floor(
        "OFAC band (similarity recomputed live)", "ofac_band_holds",
        "ordering/absence, not a count -- delegates to "
        "validators/aml_typology.py's ofac_band_holds, which recomputes "
        "the declared near-match's similarity with ccf.aml.similarity, "
        "never difflib's quick_ratio"))
    checks.append(_run_aml_floor(
        "three renderings differ (element sets + content)",
        "renderings_differ",
        "ordering/absence, not a count -- delegates to "
        "validators/aml_typology.py's renderings_differ, which requires "
        "the three perspectives to assemble different ELEMENT SETS and to "
        "render different VALUES for every SAR-bearing element they share"))
    checks.append(_run_aml_floor(
        "no path AML island -> real entity (safety property)",
        "no_path_to_real_entity",
        "ordering/absence, not a count -- delegates to "
        "validators/aml_typology.py's no_path_to_real_entity, CLAUDE.md "
        "rule 2's graph-disconnect proof, walked from both ends"))

    # --- #20 syndicated-lending-co-lender (Wave 18) -------------------------
    # Same shape as the Wave 17 block above. The envelope's scale figures --
    # ~6 facilities, ~25 members, 1 peer fabric -- are shape rather than
    # targets (Dave, 2026-08-24), but each of the three names a population
    # WITHOUT WHICH a condition below cannot be evaluated at all, so they are
    # registered as counts and the conditions are registered separately.
    #
    # Six of the nine §F rows are ordering/absence properties no count can
    # establish -- asymmetry between two SETS, one peer exact and another
    # band-only, two postures DIFFERING, a latency over a bound with a
    # contrast under it. Those delegate to `validators/syndicate.py`'s six
    # floor functions through `_run_syndicate_floor`, exactly as the
    # aml-typology-match block above delegates to validators/aml_typology.py.
    #
    # `lineage_is_separable` is registered here as a SAFETY PROPERTY, not a
    # §F condition -- §D's validation gates name "lineage provenance
    # separation" and §F does not list it as a `>= N`. Same treatment Wave 17
    # gave `no_path_to_real_entity` immediately above.
    with pg_connect() as conn, conn.cursor() as cur:
        checks.append(Check(
            "syndicated-lending-co-lender",
            "syndicate members on a real public identifier", 25,
            pg_scalar(cur, f'SELECT COUNT(*) FROM "{S}".syndicate_member '
                           f"WHERE lei IS NOT NULL OR rssd IS NOT NULL"),
            "resolved members only -- 40 carry a real GLEIF LEI, 16 of those "
            "also an FFIEC RSSD, and 5 name-only funds are EXCLUDED rather "
            "than counted; a raw row count would read 45 and would go on "
            "reading 45 if identifier resolution regressed to zero",
        ))
        checks.append(Check(
            "syndicated-lending-co-lender", "competition-law constraint rules", 1,
            pg_scalar(cur, f'SELECT COUNT(*) FROM "{S}".competition_law_rule'),
            "§C `P`, Postgres -- the Policy Operator reads these alongside "
            "the envelope; not a §F floor, registered because §C assigns the "
            "element and nothing else counts it",
        ))
    checks.append(Check(
        "syndicated-lending-co-lender",
        "syndicated facilities with a parsed schedule", 6,
        fl_distinct(f"SELECT ?f FROM <{L}> WHERE {{ "
                    f"?p <{EX}participationIn> ?f ; <{EX}sourcePassage> ?sp }}",
                    "f"),
        "distinct FACILITIES whose participations cite a filed offset, not "
        "participation nodes -- twelve participations on one facility would "
        "otherwise clear a floor about six facilities",
    ))
    checks.append(Check(
        "syndicated-lending-co-lender", "bilateral disclosure envelopes", 2,
        fl_distinct(f"SELECT ?e FROM <{L}> WHERE {{ "
                    f"?e a <{EX}DisclosureEnvelope> }}", "e"),
        "the ASYMMETRY half of this floor is not a count -- see the "
        "delegated check below",
    ))
    checks.append(_syndicate_peer_check(
        "peer counterparty identities", 2, "counterparties",
        "distinct counterparties declared on BOTH the peer's Postgres and "
        "its ledger, as the MINIMUM of the two -- a peer that held positions "
        "for two counterparties but published only one identity node would "
        "not pass silently"))
    checks.append(_syndicate_peer_check(
        "peer product declarations", 3, "declarations",
        "one per remote product the peer exposes; the TTL/latency/attestation "
        "CONTRASTS these carry are not a count -- see the delegated "
        "federation-bounds check below"))
    checks.append(_run_syndicate_floor(
        "shares are sourced (offset -> filed row)", "shares_are_sourced",
        "ordering/absence, not a count -- delegates to "
        "validators/syndicate.py's shares_are_sourced, which RE-EXTRACTS "
        "each filing and requires the cited offset to land on the lender "
        "the node claims, with its amount at that row"))
    checks.append(_run_syndicate_floor(
        "envelopes asymmetric (scopes compared as sets)",
        "envelopes_are_asymmetric",
        "ordering/absence, not a count -- delegates to "
        "validators/syndicate.py's envelopes_are_asymmetric, which requires "
        "request-scope and disclose-scope to DIFFER as sets, both non-empty"))
    checks.append(_run_syndicate_floor(
        "precision mixed (peer fabric only)", "precision_is_mixed",
        "ordering/absence, not a count -- delegates to "
        "validators/syndicate.py's precision_is_mixed, scoped to the PEER "
        "fabric per Ruling T14-R1: our own ledger holds the band peer's "
        "exact commitment, so the claim is about what the peer DISCLOSES"))
    checks.append(_run_syndicate_floor(
        "vote postures diverge (read live)", "vote_postures_diverge",
        "ordering/absence, not a count -- delegates to "
        "validators/syndicate.py's vote_postures_diverge, which requires the "
        "one open vote to carry >= 2 DISTINCT ex:votePosture values"))
    checks.append(_run_syndicate_floor(
        "federation bounds bind (latency/attest/TTL)",
        "federation_bounds_bind",
        "ordering/absence, not a count -- delegates to "
        "validators/syndicate.py's federation_bounds_bind, which covers "
        "three §F rows at once: a declared latency OVER the bound with a "
        "contrast under it, an unattested claim with a matching Context Debt "
        "row, and a remote TTL SHORTER than the local composite"))
    checks.append(_run_syndicate_floor(
        "lineage separable (origin derived, safety property)",
        "lineage_is_separable",
        "ordering/absence, not a count, and NOT a §F floor -- §D's "
        "validation gates name lineage provenance separation and §F lists no "
        "`>= N` for it. Delegates to validators/syndicate.py's "
        "lineage_is_separable, whose element_origin is derived from which "
        "fabric answered, never from a stored marker"))

    # --- #21 large-exposure-rwa-concentration (Wave 19) ----------------------
    # The capstone. Same shape as the Wave 18 block above: direct counts
    # registered as counts, and the eight §F rows that are ordering / flip /
    # aggregation claims -- no COUNT can establish them -- delegated to
    # validators/large_exposure.py through `_run_large_exposure_floor`,
    # modelled on `_run_syndicate_floor` immediately above. That file's own
    # module docstring states the rule this block exists to honour: every
    # number is recomputed from the stores on every run, no stored score, no
    # cached rank, no boolean breach flag is ever read as an answer.
    #
    # One of the four direct counts below is not a mere population floor --
    # it closes a gap Task 15's own review left as a named minor: `Context.
    # carries_methodology` / `carries_replay_attribution` are loaded from
    # `large_exposure_projection_plan` but read by NO floor in
    # validators/large_exposure.py. §F's own words -- "the examiner
    # rendering carrying full methodology and replay attribution" -- are a
    # real condition, and the count below is what was missing, not a new
    # column invented to answer it.
    with pg_connect() as conn, conn.cursor() as cur:
        checks.append(Check(
            "large-exposure-rwa-concentration",
            "bank capital reports loaded (real Call Report data)", 4,
            pg_scalar(cur, f'SELECT COUNT(*) FROM "{S}".bank_capital'),
            "FDIC-sourced, bank-level, genuinely real -- §C also names "
            "FR Y-9C (holding-company) and a separate FFIEC 101 "
            "(advanced-approaches) row; neither is loaded. Recorded as a "
            "divergence in validators/spec_coverage.py's LARGE_EXPOSURE "
            "manifest, not silently invented here",
        ))
        checks.append(Check(
            "large-exposure-rwa-concentration",
            "exposure proposals loaded (hypothetical, both cases)", 2,
            pg_scalar(cur, f'SELECT COUNT(*) FROM "{S}".exposure_proposal'),
            "population floors 4 and 5 need TWO DISTINCT proposals to find "
            "in -- one proposal cannot be both the breach that survives "
            "mitigation and the case mitigation cures",
        ))
        checks.append(Check(
            "large-exposure-rwa-concentration",
            "ProjectionPlans loaded (one per perspective)", 3,
            pg_scalar(cur, f'SELECT COUNT(*) FROM '
                          f'"{S}".large_exposure_projection_plan'),
            "population floor 7 below compares for pairwise distinctness, "
            "not mere existence of three rows",
        ))
        checks.append(Check(
            "large-exposure-rwa-concentration",
            "examiner plan carries methodology AND replay attribution", 1,
            pg_scalar(cur, f"""
                SELECT COUNT(*) FROM "{S}".large_exposure_projection_plan
                WHERE perspective = 'examiner'
                  AND carries_methodology AND carries_replay_attribution"""),
            "§F's own words: 'the examiner rendering carrying full "
            "methodology and replay attribution' -- Task 15's review found "
            "these two columns loaded into Context but read by no floor; "
            "this count is what was missing",
        ))

    def _le_dependency_edge_count() -> int | None:
        """Edge PAIRS, not distinct subjects -- one entity economically
        dependent on two others must count as two, matching the unit §F
        names ('>= 4 economic-dependency edges'), not the population of
        dependent entities."""
        rows = fl_rows(f"SELECT ?a ?b FROM <{L}> WHERE {{ "
                       f"?a <{EX}economicallyDependentOn> ?b }}")
        return None if rows is None else len(rows)

    def _le_regime_effective_dates() -> int | None:
        rows = fl_rows(f"SELECT ?s ?ef FROM <{L}> WHERE {{ "
                       f"?s a <{EX}RegimeVersion> ; <{EX}effectiveFrom> ?ef }}")
        if rows is None:
            return None
        return len({r["ef"]["value"] for r in rows})

    checks.append(Check(
        "large-exposure-rwa-concentration",
        "economic-dependency edges (control-blind, Fluree)", 4,
        _le_dependency_edge_count(),
        "§F's own floor -- edges the control-basis grouping alone would "
        "miss. That >= 1 of them CHANGES the binding limit is a distinct "
        "ordering claim, floor 2 below, not this count",
    ))
    checks.append(Check(
        "large-exposure-rwa-concentration",
        "regime versions with distinct effective dates", 2,
        _le_regime_effective_dates(),
        "floor is 2, not the 3 actually loaded (CRR from 2014-01-01, PRA "
        "takes over UK large exposures 2022-01-01, Reg O 2026-01-01) -- "
        "as_of reconstruction differing from the live answer needs only "
        "ONE date boundary to cross, i.e. two distinct dates; the third is "
        "headroom, not the requirement. Each independently required to "
        "carry >= 1 citesProvision by the loader's own "
        "assert_regime_anchoring, re-verified live at every load",
    ))
    checks.append(Check(
        "large-exposure-rwa-concentration",
        "Reg O related-party case (real DEF 14A precedent cited)", 1,
        fl_distinct(f"SELECT ?s FROM <{L}> WHERE {{ "
                    f"?s a <{EX}InsiderDesignation> }}", "s"),
        "the insider is INVENTED (CLAUDE.md rule 3 territory -- a real "
        "DEF 14A names a real living person); the related interest "
        "(Digital Turbine, a real GLEIF LEI) and the cited JPMorgan proxy "
        "compliance sentence are real and filed -- "
        "sources/screening/wave19_insider_case.json's own def14a_precedent",
    ))

    checks.append(_run_large_exposure_floor(
        "groups recompute (26 components, >=9 span >=3 countries)",
        "groups_recompute",
        "not the ~15 of §F's own shape figure (Dave, 2026-08-24: envelope "
        "figures are a shape, not a target) -- delegates to "
        "validators/large_exposure.py's groups_recompute, which forms "
        "connected components FRESH from ex:connectedTo (there is no "
        "stored group id anywhere to read instead) and reports "
        "country-spanning SEPARATELY from the component count"))
    checks.append(_run_large_exposure_floor(
        "dependency edge changes binding limit",
        "dependency_changes_binding_limit",
        "ordering/flip, not a count -- delegates to "
        "validators/large_exposure.py's dependency_changes_binding_limit, "
        "which recomputes a group's % of tier 1 WITH and WITHOUT each "
        "economicallyDependentOn edge and requires the breached-limit SET "
        "to differ between the two"))
    checks.append(_run_large_exposure_floor(
        "regime divergence (CRR/PRA compliant, Reg O breach)",
        "regime_divergence",
        "ordering/flip, not a count -- delegates to "
        "validators/large_exposure.py's regime_divergence, which "
        "recomputes the SAME exposure figure against both the live "
        "CRR/PRA percentage limit and Reg O's absolute cap and requires "
        "them to disagree"))
    checks.append(_run_large_exposure_floor(
        "proposal breaches net of mitigation, distinct from the cure",
        "proposal_breaches",
        "not a count -- delegates to validators/large_exposure.py's "
        "proposal_breaches, which requires a breach that SURVIVES the "
        "product's own apply_mitigation=true default, distinct from a "
        "second, DIFFERENT proposal that mitigation cures"))
    checks.append(_run_large_exposure_floor(
        "mitigation is load-bearing (gross over, net under)",
        "mitigation_is_load_bearing",
        "ordering/flip, not a count -- delegates to "
        "validators/large_exposure.py's mitigation_is_load_bearing, which "
        "requires a proposal to cross the limit between gross and net of "
        "real post-haircut collateral"))
    checks.append(_run_large_exposure_floor(
        "debt tolerance breached (live policy_tolerance)",
        "debt_tolerance_breached",
        "ordering/absence, not a count -- delegates to "
        "validators/large_exposure.py's debt_tolerance_breached, which "
        "sums memo_context_debt.aggregate_debt across a live-recomputed "
        "connectedTo group and compares to validators/memo_debt.py's "
        "policy_tolerance, read live rather than hard-coded"))
    checks.append(_run_large_exposure_floor(
        "three ProjectionPlans pairwise distinct",
        "projection_plans_differ",
        "ordering, not a count -- delegates to "
        "validators/large_exposure.py's projection_plans_differ, which "
        "requires the three elements_included SETS to be pairwise "
        "distinct, not merely three rows to exist (see the direct count "
        "above for existence)"))
    checks.append(_run_large_exposure_floor(
        "no public row in a breach (provenance floor)",
        "no_public_row_in_a_breach",
        "ordering/absence, not a count -- delegates to "
        "validators/large_exposure.py's no_public_row_in_a_breach, which "
        "requires every enumerated narrative row to carry a synthetic "
        "provenance label AND scans free text for a sentence asserting "
        "that the REAL reporting bank breached a regulatory limit"))

    return checks


class CheckFailure(Exception):
    """The check itself failed to execute -- must render as FAIL, not SKIP.

    Distinct from the legitimate "wave not yet run" case (the `interaction`
    table does not exist), which _depth2_over_limit_count reports as a plain
    `None`. Everything else -- a broken import, a Fluree/SPARQL error, any
    other exception inside the traversal -- raises this instead of being
    swallowed, so `Check.state` cannot silently downgrade a real outage or a
    code break to "0 skipped (wave not yet run)" with exit code 0.
    """


def _depth2_over_limit_count() -> int | None:
    """Delegate to validators/traversal.py rather than reimplementing.

    Only the candidate-selection loop is repeated here -- the traversal logic
    itself (the thing that cannot be established by counting) comes straight
    from traversal.depth2_nodes.

    Returns None ONLY for the genuine "wave not yet run" precondition: the
    `interaction` table not existing. Any other failure raises CheckFailure
    so the caller can render this check as FAIL with the exception printed,
    per known-issues.md — a Fluree outage, an import break, or a SPARQL
    syntax error must not silently pass this wave's flagship condition, the
    one the design says cannot be established by counting.
    """
    import psycopg

    try:
        from loaders.load_collateral_wave9 import entity_uri_by_lei
        from validators.traversal import LIMIT, depth2_nodes
    except Exception as exc:  # noqa: BLE001 — import break must FAIL loudly
        raise CheckFailure(f"import failed: {exc!r}") from exc

    try:
        with pg_connect() as conn, conn.cursor() as cur:
            cur.execute(f'SELECT lei, count(*) AS n FROM "{S}".interaction '
                        "GROUP BY lei ORDER BY n DESC LIMIT 5")
            candidates = cur.fetchall()
    except psycopg.errors.UndefinedTable:
        return None  # the wave genuinely has not run yet -- legitimate SKIP
    except Exception as exc:  # noqa: BLE001 — any other DB failure must FAIL
        raise CheckFailure(f"candidate query failed: {exc!r}") from exc

    try:
        entity_uri = entity_uri_by_lei()
        exceeded = 0
        for lei, _ in candidates:
            node = entity_uri.get(lei)
            if node is None:
                continue
            if len(depth2_nodes(node)) > LIMIT:
                exceeded += 1
        return exceeded
    except Exception as exc:  # noqa: BLE001 — Fluree/SPARQL failure must FAIL
        raise CheckFailure(f"traversal query failed: {exc!r}") from exc


def _rsm_divergence() -> tuple[int | None, int | None]:
    """Delegate to validators/series.py's independent recomputation.

    Returns (n_windows, n_confirmed). Returns (None, None) ONLY for the
    genuine "wave not yet run" precondition — `spread_observation` or
    `debt_instrument` not existing. Any other failure (import break, a
    Fluree/SPARQL error inside the grade-history query, a bad join) raises
    CheckFailure so the caller renders this as FAIL, not SKIP — per
    known-issues.md, an outage must not silently downgrade the one
    condition this wave says "cannot be established by counting".
    """
    import psycopg

    try:
        from validators.series import divergence_windows
    except Exception as exc:  # noqa: BLE001 — import break must FAIL loudly
        raise CheckFailure(f"import failed: {exc!r}") from exc

    try:
        windows = divergence_windows()
    except psycopg.errors.UndefinedTable:
        return None, None  # the wave genuinely has not run yet
    except Exception as exc:  # noqa: BLE001 — any other failure must FAIL
        raise CheckFailure(f"divergence recomputation failed: {exc!r}") from exc

    qualifying = [w for w in windows if w.notch_during is not None]
    n_confirmed = sum(1 for w in qualifying if w.confirmed)
    return len(qualifying), n_confirmed


def _rsm_sparse() -> int | None:
    """Delegate to validators/series.py's genuine-absence check.

    Same None-vs-CheckFailure contract as `_rsm_divergence` above.
    """
    import psycopg

    try:
        from validators.series import sparse_instruments
    except Exception as exc:  # noqa: BLE001
        raise CheckFailure(f"import failed: {exc!r}") from exc

    try:
        with pg_connect() as conn, conn.cursor() as cur:
            sparse = sparse_instruments(cur)
    except psycopg.errors.UndefinedTable:
        return None
    except Exception as exc:  # noqa: BLE001
        raise CheckFailure(f"sparsity recomputation failed: {exc!r}") from exc
    return len(sparse)


def _wave11b_signal_events_in_window() -> int | None:
    """Count `signal_event` rows, but ASSERT every row's `observed_at`
    falls inside the fetch window rather than merely counting.

    A bare COUNT(*) is blind to contamination: a stray row dated outside
    the surveillance window raises the count and still clears the floor
    (proven by the reviewer inserting a 2030-01-01 row and watching this
    check pass unchanged before this fix). WINDOW_START/WINDOW_END are
    IMPORTED from generators.fetch_8k_items -- the same "import shared
    logic, do not re-derive a number" discipline already applied to
    is_subthreshold and sector_for elsewhere in this file -- not re-derived
    as a local constant, so this cannot silently drift from what the fetch
    actually used, and does not reintroduce the conditions.py:32 trap
    (that trap was two independently-typed, and differently WRONG,
    constants; this is one constant imported once).

    Returns None ONLY for the genuine "wave not yet run" precondition --
    signal_event not existing. Any other failure (import break, a broken
    query) raises CheckFailure so the caller renders FAIL, not SKIP. A row
    found outside the window is not a check-execution failure -- it is a
    genuinely failed condition -- so it is reported as a negative sentinel
    (guaranteed to render FAIL against the floor of 400) rather than as
    errored=True, exactly the same "-COUNT(*)" inversion the crosswalk-
    orphans check above already uses to force a violation to FAIL.
    """
    import psycopg

    try:
        from generators.fetch_8k_items import WINDOW_END, WINDOW_START
    except Exception as exc:  # noqa: BLE001 — import break must FAIL loudly
        raise CheckFailure(f"import failed: {exc!r}") from exc

    try:
        with pg_connect() as conn, conn.cursor() as cur:
            cur.execute(f'SELECT COUNT(*), MIN(observed_at), MAX(observed_at) '
                        f'FROM "{S}".signal_event')
            n, lo, hi = cur.fetchone()
    except psycopg.errors.UndefinedTable:
        return None  # the wave genuinely has not run yet -- legitimate SKIP
    except Exception as exc:  # noqa: BLE001 — any other failure must FAIL
        raise CheckFailure(f"signal_event window query failed: {exc!r}") from exc

    if n:
        from datetime import date
        window_start = date.fromisoformat(WINDOW_START)
        window_end = date.fromisoformat(WINDOW_END)
        if lo < window_start or hi > window_end:
            return -1  # forces FAIL: contamination outside the fetch window
    return n


def _wave11b_composite_case() -> int | None:
    """Delegate to validators/surveillance.py's composite_case_check.

    Returns 1 if the composite case's every claim holds (three signals on
    one obligor, individually subthreshold, sum breaching escalation), 0 if
    it does not, and None ONLY for the genuine "wave not yet run"
    precondition -- `signal_event` not existing. Any other failure (import
    break, a broken query inside the recomputation) raises CheckFailure so
    the caller renders this as FAIL, not SKIP -- per known-issues.md, an
    outage must not silently downgrade a condition the design says cannot
    be established by counting.
    """
    import psycopg

    try:
        from validators.surveillance import composite_case_check
    except Exception as exc:  # noqa: BLE001 — import break must FAIL loudly
        raise CheckFailure(f"import failed: {exc!r}") from exc

    try:
        with pg_connect() as conn, conn.cursor() as cur:
            ok, _detail = composite_case_check(cur)
    except psycopg.errors.UndefinedTable:
        return None  # the wave genuinely has not run yet -- legitimate SKIP
    except Exception as exc:  # noqa: BLE001 — any other failure must FAIL
        raise CheckFailure(f"composite case recomputation failed: {exc!r}") from exc
    return 1 if ok else 0


def _wave11b_cascade() -> int | None:
    """Delegate to validators/surveillance.py's cascade_completeness.

    Returns 1 if the engineered Item 2.04 cascade reaches EXACTLY the
    facility's own collateral_pledge and drawdown sets (found structurally
    in Fluree, checked against Postgres), 0 if it does not. Same
    None-vs-CheckFailure contract as `_wave11b_composite_case` above --
    None only for `signal_event` genuinely not existing; any other failure,
    including a Fluree/SPARQL error or the structural-resolution assertion
    inside `resolve_cascade_signal`, raises CheckFailure.
    """
    import psycopg

    try:
        from validators.surveillance import cascade_completeness
    except Exception as exc:  # noqa: BLE001
        raise CheckFailure(f"import failed: {exc!r}") from exc

    try:
        with pg_connect() as conn, conn.cursor() as cur:
            cur.execute(f'SELECT 1 FROM "{S}".signal_event LIMIT 1')
            ok, _detail = cascade_completeness(cur)
    except psycopg.errors.UndefinedTable:
        return None  # the wave genuinely has not run yet -- legitimate SKIP
    except Exception as exc:  # noqa: BLE001 — any other failure must FAIL
        raise CheckFailure(f"cascade recomputation failed: {exc!r}") from exc
    return 1 if ok else 0


def _fx_chain_shape() -> tuple[int | None, int | None]:
    """Count of distinct FX trades carrying >=1 / >=2 amendment(s), read
    live from Fluree `ex:amendmentSeq` on `amd-*` subjects.

    A REAL recomputation from the graph, not a row-presence read of a
    cached artifact -- unlike the 8bp/breaching/inversion/survivor checks
    above, chain shape needs no clock alignment and no business-rule
    rebuild (permitted instruments, materiality thresholds), so it is
    honest to count it directly here rather than deferring to
    validators/reconcile.py, which also computes it (from the same Fluree
    predicate, independently) as part of its own gate.

    Returns (None, None) only if the Fluree query itself fails -- there is
    no "wave not yet run" precondition worth distinguishing here, since
    every other Wave 12 FX check in this file already establishes the wave
    has run before this one is reached.
    """
    try:
        rows = fluree.query(
            f"SELECT ?s FROM <{L}> WHERE {{ ?s <{EX}amendmentSeq> ?o }}"
        )["results"]["bindings"]
    except Exception:  # noqa: BLE001
        return None, None
    from collections import defaultdict as _dd
    chain_len: dict[str, int] = _dd(int)
    for b in rows:
        local = b["s"]["value"].rsplit("/", 1)[-1]
        if not local.startswith("amd-"):
            continue
        trade_id, seq_s = local[len("amd-"):].rsplit("-", 1)
        chain_len[trade_id] = max(chain_len[trade_id], int(seq_s))
    chained = sum(1 for n in chain_len.values() if n >= 1)
    two_plus = sum(1 for n in chain_len.values() if n >= 2)
    return chained, two_plus



def _differing_lien_positions() -> int:
    """Assets pledged to two or more facilities at DIFFERENT lien positions.

    Reads Fluree, which owns lien priority. Groups by the pledged asset and
    counts distinct positions, so an asset pledged twice at the SAME position
    does not count -- the §F condition is about differing priority, not about
    sharing.
    """
    from ccf import fluree
    from ccf.config import FLUREE_LEDGER_V2

    q = (f"SELECT ?a ?pos FROM <{FLUREE_LEDGER_V2}> WHERE {{ "
         f"?p <{EX}pledgedAsset> ?a . ?p <{EX}lienPosition> ?pos }}")
    by_asset: dict[str, set[str]] = {}
    for b in fluree.query(q)["results"]["bindings"]:
        by_asset.setdefault(b["a"]["value"], set()).add(b["pos"]["value"])
    return sum(1 for positions in by_asset.values() if len(positions) > 1)


def ib_restricted_in_coverage() -> int | None:
    """Restricted LEIs (active, SQLite) present in RAW coverage (Postgres),
    read separately and intersected in Python -- R2.

    `restricted_list` lives in SQLite and `coverage_assignment` lives in
    Postgres; a single SQL JOIN across them cannot execute at all, and
    swallowing that into a bare `pg_scalar()` try/except renders the
    condition SKIP -- a broken query wearing the costume of an unrun wave.
    Returns None only for the genuine "wave not yet run" precondition
    (SQLite file absent, or either table missing). Any other failure --
    a typo'd column, a renamed table, a bad query -- must raise CheckFailure
    so the caller renders FAIL, not SKIP: a SKIP here reads as "that wave
    has not run yet" when the truth is "this check is broken".
    """
    import sqlite3

    import psycopg

    if not SQLITE_PATH.exists():
        return None  # the wave genuinely has not run yet -- legitimate SKIP

    try:
        with sqlite3.connect(SQLITE_PATH) as sq:
            restricted = {
                r[0] for r in sq.execute(
                    "SELECT lei FROM restricted_list WHERE removed_date IS NULL")
            }
    except sqlite3.OperationalError as exc:
        if "no such table" in str(exc):
            return None  # legitimate SKIP -- restricted_list not loaded yet
        raise CheckFailure(f"restricted_list query failed: {exc!r}") from exc
    except Exception as exc:  # noqa: BLE001 — any other SQLite failure must FAIL
        raise CheckFailure(f"restricted_list query failed: {exc!r}") from exc

    try:
        with pg_connect() as conn, conn.cursor() as cur:
            cur.execute(f'SELECT DISTINCT lei FROM "{S}".coverage_assignment')
            coverage = {r[0] for r in cur.fetchall()}
    except psycopg.errors.UndefinedTable:
        return None  # legitimate SKIP -- coverage_assignment not loaded yet
    except Exception as exc:  # noqa: BLE001 — any other DB failure must FAIL
        raise CheckFailure(f"coverage_assignment query failed: {exc!r}") from exc

    return len(restricted & coverage)


def _ib_divergence() -> bool | None:
    """Delegates to validators/ib_rank.py's `divergence_holds` -- R4.

    Returns None ONLY for the genuine "wave not yet run" precondition
    (`perspective_weight` / `ib_signal_class` not existing, or
    `sources/screening/wave16_signals.json` absent). Any other failure --
    import break, an empty or identical weight vector, a bad query -- raises
    CheckFailure so the caller renders FAIL, not SKIP: this is one of the two
    conditions R4 says cannot be established by counting, and a SKIP here
    would read as "wave not yet run" rather than "this check is broken".
    """
    import psycopg

    try:
        from validators.ib_rank import (
            divergence_holds,
            load_current_signals,
            load_half_lives,
            load_weights,
            require_nonempty_weights,
        )
    except Exception as exc:  # noqa: BLE001 — import break must FAIL loudly
        raise CheckFailure(f"import failed: {exc!r}") from exc

    try:
        signals = load_current_signals()
        with pg_connect() as conn, conn.cursor() as cur:
            ma_v2 = load_weights(cur, "PSP-MA", "v2")
            dcm_v2 = load_weights(cur, "PSP-DCM", "v2")
            half_lives = load_half_lives(cur)
    except FileNotFoundError:
        return None  # the signal ledger genuinely has not been generated yet
    except psycopg.errors.UndefinedTable:
        return None  # the wave genuinely has not run yet -- legitimate SKIP
    except Exception as exc:  # noqa: BLE001 — any other DB failure must FAIL
        raise CheckFailure(f"load failed: {exc!r}") from exc

    try:
        require_nonempty_weights({"PSP-MA v2": ma_v2, "PSP-DCM v2": dcm_v2})
        return divergence_holds(signals=signals, ma_weights=ma_v2,
                                 dcm_weights=dcm_v2, half_lives=half_lives,
                                 as_of=AS_OF_IB)
    except Exception as exc:  # noqa: BLE001 — recomputation failure must FAIL
        raise CheckFailure(f"divergence recomputation failed: {exc!r}") from exc


def _ib_note_materiality() -> int | None:
    """Delegates to validators/ib_rank.py's `note_materiality_counts` -- R4.

    Returns the count of NOTES whose own entity's rank position moves --
    the §F unit -- never the (banker, LEI) position-change count, which is a
    different, larger number. Same None-vs-CheckFailure contract as
    `_ib_divergence` above: None only for the genuine "wave not yet run"
    precondition (Postgres tables absent, signal ledger absent, or the
    departmental SQLite file absent); any other failure raises CheckFailure.

    FINAL FIX WAVE, item 5: `coverage` is filtered to exclude active
    `restricted_list` LEIs before ranking, the same way
    `validators/ib_rank.py`'s `main()` now does. This module has its own
    copy of the load-and-rank sequence rather than calling `main()`, so the
    same fix has to be applied here too -- otherwise this condition would
    still count notes sitting on a walled entity as "moving a rank",
    contradicting the restricted-entities-inside-coverage condition just
    above, which asserts those entities are absent from a banker's real
    candidate set.
    """
    import sqlite3

    import psycopg

    try:
        from validators.ib_rank import (
            load_bankers,
            load_coverage,
            load_current_signals,
            load_half_lives,
            load_notes,
            load_weights,
            note_materiality_counts,
            require_nonempty_weights,
        )
    except Exception as exc:  # noqa: BLE001 — import break must FAIL loudly
        raise CheckFailure(f"import failed: {exc!r}") from exc

    try:
        signals = load_current_signals()
        with pg_connect() as conn, conn.cursor() as cur:
            ma_v2 = load_weights(cur, "PSP-MA", "v2")
            dcm_v2 = load_weights(cur, "PSP-DCM", "v2")
            sector_v2 = load_weights(cur, "PSP-SECTOR", "v2")
            half_lives = load_half_lives(cur)
            coverage = load_coverage(cur)
            desks = load_bankers(cur)
    except FileNotFoundError:
        return None  # the signal ledger genuinely has not been generated yet
    except psycopg.errors.UndefinedTable:
        return None  # the wave genuinely has not run yet -- legitimate SKIP
    except Exception as exc:  # noqa: BLE001 — any other DB failure must FAIL
        raise CheckFailure(f"load failed: {exc!r}") from exc

    try:
        if not SQLITE_PATH.exists():
            return None  # departmental store genuinely not created yet
        with sqlite3.connect(SQLITE_PATH) as sq:
            notes = load_notes(sq)
            restricted_leis = {
                r[0] for r in sq.execute(
                    "SELECT lei FROM restricted_list WHERE removed_date IS NULL")
            }
    except Exception as exc:  # noqa: BLE001 — any other failure must FAIL
        raise CheckFailure(f"note load failed: {exc!r}") from exc

    filtered_coverage = [(b, l) for b, l in coverage if l not in restricted_leis]

    try:
        require_nonempty_weights({"PSP-MA v2": ma_v2, "PSP-DCM v2": dcm_v2,
                                   "PSP-SECTOR v2": sector_v2})
        weight_vectors = {"PSP-MA": ma_v2, "PSP-DCM": dcm_v2,
                           "PSP-SECTOR": sector_v2}
        notes_moving, _pairs = note_materiality_counts(
            notes, filtered_coverage, desks, weight_vectors, signals,
            half_lives, AS_OF_IB)
        return len(notes_moving)
    except Exception as exc:  # noqa: BLE001 — recomputation failure must FAIL
        raise CheckFailure(
            f"note materiality recomputation failed: {exc!r}") from exc


def _aml_delegate(fn_name: str) -> bool | None:
    """Shared plumbing for the seven aml-typology-match ordering/absence
    delegates in `collect()`. Builds one `validators.aml_typology.Context`
    and calls `getattr(aml_typology, fn_name)` on it -- one of the seven
    exact floor functions Task 17 wrote, never reimplemented here.

    Returns None ONLY for the genuine "wave not yet run" precondition --
    `aml_party` absent (table does not exist). A table that EXISTS but is
    EMPTY is a different case and raises CheckFailure, not None -- see
    below. Any other failure -- an import break, a Fluree, Mongo or SQLite
    outage, a broken recomputation -- also raises CheckFailure so the
    caller renders FAIL, not SKIP: these are exactly the properties §F says
    cannot be established by counting, and a SKIP here would read as
    "wave not yet run" rather than "this check is broken".
    """
    import psycopg

    try:
        with pg_connect() as conn, conn.cursor() as cur:
            cur.execute(f'SELECT 1 FROM "{S}".aml_party LIMIT 1')
            row = cur.fetchone()
    except psycopg.errors.UndefinedTable:
        return None  # the wave genuinely has not run yet -- legitimate SKIP
    except Exception as exc:  # noqa: BLE001 — any other DB failure must FAIL
        raise CheckFailure(f"precondition query failed: {exc!r}") from exc

    if row is None:
        # `aml_party` EXISTS but is EMPTY -- a genuinely different case from
        # "wave not yet run" (UndefinedTable, above), and not a legitimate
        # pass either. The prior version of this precondition only checked
        # that the query did not raise, never inspected the fetched row, so
        # a truncated table fell straight through into the real floor
        # function -- silently occupying the seam between SKIP and FAIL
        # this estate keeps losing things down. A truncated `aml_party` is
        # exactly the "hitting the count while missing the condition"
        # failure this whole file exists to catch, so this FAILs loud
        # (distinguishable in the printed error from every other failure
        # mode below) rather than SKIPping or silently proceeding.
        raise CheckFailure(
            f'"{S}".aml_party exists but is EMPTY -- not the same '
            "precondition as the table never having been created")

    try:
        from validators import aml_typology
        floor_fn = getattr(aml_typology, fn_name)
    except Exception as exc:  # noqa: BLE001 — import break must FAIL loudly
        raise CheckFailure(f"import failed: {exc!r}") from exc

    try:
        ctx = aml_typology.load_context()
        ok, _detail = floor_fn(ctx)
        return bool(ok)
    except Exception as exc:  # noqa: BLE001 — recomputation failure must FAIL
        raise CheckFailure(f"{fn_name} recomputation failed: {exc!r}") from exc


def _run_aml_floor(label: str, fn_name: str, note: str) -> Check:
    """Wraps `_aml_delegate` with the same CheckFailure-to-FAIL translation
    the ib-opportunity-synthesis block above performs by hand for each of
    its two delegates -- pulled into one helper here because Wave 17
    registers seven, not two."""
    try:
        ok = _aml_delegate(fn_name)
        return Check("aml-typology-match", label, 1,
                     None if ok is None else int(ok), note)
    except CheckFailure as exc:
        print(f"  [ERROR] aml-typology-match {label} recomputation failed "
              f"to execute: {exc}", file=sys.stderr)
        return Check("aml-typology-match", label, 1, None,
                     f"CHECK FAILED TO EXECUTE — {exc}", errored=True)


def _syndicate_peer_count(what: str) -> int | None:
    """One count read from the CO-LENDER's fabric.

    `counterparties` is the MINIMUM of two independent reads -- the peer's
    Postgres and the peer's ledger -- because the §F row is "1 simulated peer
    fabric ... holding one co-lender's position data AND exposing one product
    under an envelope", and a peer whose two halves disagree about who its
    counterparties are is not one fabric. Taking the minimum means the
    half-loaded case fails rather than being papered over by the fuller half.

    Returns None ONLY for the genuine "wave not yet run" precondition: the
    co-lender fabric unconfigured. Every other failure raises CheckFailure,
    so a peer that is configured but unreachable renders FAIL, not SKIP.
    """
    from ccf.config import (
        CO_LENDER_FLUREE_LEDGER, CO_LENDER_PG_SCHEMA, co_lender_configured,
        co_lender_pg_connect,
    )

    if not co_lender_configured():
        return None

    P = CO_LENDER_PG_SCHEMA
    try:
        with co_lender_pg_connect() as conn, conn.cursor() as cur:
            if what == "declarations":
                cur.execute(f'SELECT COUNT(*) FROM "{P}".peer_product_declaration')
                return int(cur.fetchone()[0])
            cur.execute(
                f'SELECT COUNT(DISTINCT counterparty) FROM ('
                f'  SELECT counterparty FROM "{P}".peer_position'
                f'  UNION SELECT counterparty '
                f'  FROM "{P}".peer_product_declaration) t')
            in_pg = int(cur.fetchone()[0])
    except Exception as exc:  # noqa: BLE001 — a configured-but-broken peer FAILs
        raise CheckFailure(f"peer Postgres read failed: {exc!r}") from exc

    try:
        rows = fluree.co_lender_query(
            f"SELECT DISTINCT ?s FROM <{CO_LENDER_FLUREE_LEDGER}> WHERE "
            f"{{ ?s <{EX}lei> ?lei }}")["results"]["bindings"]
    except Exception as exc:  # noqa: BLE001
        raise CheckFailure(f"peer ledger read failed: {exc!r}") from exc
    return min(in_pg, len(rows))


def _syndicate_peer_check(condition: str, floor: int, what: str,
                          note: str) -> Check:
    try:
        return Check("syndicated-lending-co-lender", condition, floor,
                     _syndicate_peer_count(what), note)
    except CheckFailure as exc:
        print(f"  [ERROR] syndicated-lending-co-lender {condition} failed to "
              f"execute: {exc}", file=sys.stderr)
        return Check("syndicated-lending-co-lender", condition, floor, None,
                     f"CHECK FAILED TO EXECUTE — {exc}", errored=True)


def _syndicate_delegate(fn_name: str) -> bool | None:
    """Shared plumbing for the six syndicated-lending-co-lender delegates in
    `collect()` -- the exact counterpart of `_aml_delegate` above, and it
    borrows that function's hard-won precondition discipline rather than
    re-deciding it.

    Returns None ONLY for the genuine "wave not yet run" precondition:
    `syndicate_member` absent (table does not exist), or the co-lender fabric
    unconfigured. A table that EXISTS but is EMPTY raises CheckFailure, not
    None -- a truncated `syndicate_member` is "hitting the count while
    missing the condition", not an unrun wave.

    Every other failure -- an import break, a Fluree, Postgres or peer-fabric
    outage, a broken recomputation -- also raises CheckFailure so the caller
    renders FAIL, not SKIP. These are exactly the properties §F says cannot
    be established by counting, and a SKIP here would read as "wave not yet
    run" rather than "this check is broken".

    ONE `Context` is built per `collect()` run and shared across the six
    calls. Measured 2026-08-27: `load_context()` costs 21s -- it re-extracts
    six filings and reads both fabrics -- so six loads would add two minutes
    to every run of this file. The floors read it and mutate nothing (it is a
    mutable dataclass only because Task 16's falsification tests rewrite
    fields on their own copies), and it is still `validators/syndicate.py`
    that decides what a Context is: this file calls that function and holds
    the result, it does not transcribe it. `collect()` clears the cache on
    entry, so two runs in one process do not share a snapshot.
    """
    import psycopg

    from ccf.config import co_lender_configured

    if not co_lender_configured():
        return None  # the peer fabric genuinely is not stood up -- SKIP

    try:
        with pg_connect() as conn, conn.cursor() as cur:
            cur.execute(f'SELECT 1 FROM "{S}".syndicate_member LIMIT 1')
            row = cur.fetchone()
    except psycopg.errors.UndefinedTable:
        return None  # the wave genuinely has not run yet -- legitimate SKIP
    except Exception as exc:  # noqa: BLE001 — any other DB failure must FAIL
        raise CheckFailure(f"precondition query failed: {exc!r}") from exc

    if row is None:
        raise CheckFailure(
            f'"{S}".syndicate_member exists but is EMPTY -- not the same '
            "precondition as the table never having been created")

    try:
        from validators import syndicate
        floor_fn = getattr(syndicate, fn_name)
    except Exception as exc:  # noqa: BLE001 — import break must FAIL loudly
        raise CheckFailure(f"import failed: {exc!r}") from exc

    try:
        if _SYNDICATE_CTX.get("ctx") is None:
            _SYNDICATE_CTX["ctx"] = syndicate.load_context()
        ok, _detail = floor_fn(_SYNDICATE_CTX["ctx"])
        return bool(ok)
    except Exception as exc:  # noqa: BLE001 — recomputation failure must FAIL
        raise CheckFailure(f"{fn_name} recomputation failed: {exc!r}") from exc


def _run_syndicate_floor(label: str, fn_name: str, note: str) -> Check:
    """`_run_aml_floor`'s counterpart for Wave 18."""
    try:
        ok = _syndicate_delegate(fn_name)
        return Check("syndicated-lending-co-lender", label, 1,
                     None if ok is None else int(ok), note)
    except CheckFailure as exc:
        print(f"  [ERROR] syndicated-lending-co-lender {label} recomputation "
              f"failed to execute: {exc}", file=sys.stderr)
        return Check("syndicated-lending-co-lender", label, 1, None,
                     f"CHECK FAILED TO EXECUTE — {exc}", errored=True)


def _large_exposure_delegate(fn_name: str) -> bool | None:
    """Shared plumbing for the eight large-exposure-rwa-concentration
    delegates in `collect()` -- `_syndicate_delegate`'s counterpart for
    Wave 19, borrowing that function's precondition discipline rather than
    re-deciding it.

    Returns None ONLY for the genuine "wave not yet run" precondition:
    `bank_capital` absent (table does not exist). A table that EXISTS but
    is EMPTY raises CheckFailure, not None -- Task 1's own unit-conversion
    guard (`docs/wave19-design.md`'s corrected "28 rows across 16
    institutions" figure) is exactly the kind of silently-wrong load a
    SKIP here would hide instead of catching.

    Every other failure -- an import break, a Fluree/Postgres/Mongo/SQLite
    outage, a broken recomputation -- also raises CheckFailure so the
    caller renders FAIL, not SKIP. These are exactly the properties §F
    says cannot be established by counting, and a SKIP here would read as
    "wave not yet run" rather than "this check is broken".

    ONE `Context` is built per `collect()` run and shared across the eight
    calls -- `validators/large_exposure.py`'s own `load_context()`
    docstring calls it "expensive (Fluree round-trips, a handful of
    Postgres joins, two Mongo reads, one SQLite read)"; eight loads would
    multiply that cost by eight for nothing, the exact shape
    `_syndicate_delegate` above already solved for Wave 18. The floors read
    it and mutate nothing -- `Context` is a mutable dataclass only because
    Task 15's own falsification tests rewrite fields on their own copies.
    `collect()` clears the cache on entry, so two runs in one process do
    not share a snapshot.
    """
    import psycopg

    try:
        with pg_connect() as conn, conn.cursor() as cur:
            cur.execute(f'SELECT 1 FROM "{S}".bank_capital LIMIT 1')
            row = cur.fetchone()
    except psycopg.errors.UndefinedTable:
        return None  # the wave genuinely has not run yet -- legitimate SKIP
    except Exception as exc:  # noqa: BLE001 — any other DB failure must FAIL
        raise CheckFailure(f"precondition query failed: {exc!r}") from exc

    if row is None:
        raise CheckFailure(
            f'"{S}".bank_capital exists but is EMPTY -- not the same '
            "precondition as the table never having been created")

    try:
        from validators import large_exposure
        floor_fn = getattr(large_exposure, fn_name)
    except Exception as exc:  # noqa: BLE001 — import break must FAIL loudly
        raise CheckFailure(f"import failed: {exc!r}") from exc

    try:
        if _LARGE_EXPOSURE_CTX.get("ctx") is None:
            _LARGE_EXPOSURE_CTX["ctx"] = large_exposure.load_context()
        ok, _detail = floor_fn(_LARGE_EXPOSURE_CTX["ctx"])
        return bool(ok)
    except Exception as exc:  # noqa: BLE001 — recomputation failure must FAIL
        raise CheckFailure(f"{fn_name} recomputation failed: {exc!r}") from exc


def _run_large_exposure_floor(label: str, fn_name: str, note: str) -> Check:
    """`_run_syndicate_floor`'s counterpart for Wave 19."""
    try:
        ok = _large_exposure_delegate(fn_name)
        return Check("large-exposure-rwa-concentration", label, 1,
                     None if ok is None else int(ok), note)
    except CheckFailure as exc:
        print(f"  [ERROR] large-exposure-rwa-concentration {label} "
              f"recomputation failed to execute: {exc}", file=sys.stderr)
        return Check("large-exposure-rwa-concentration", label, 1, None,
                     f"CHECK FAILED TO EXECUTE — {exc}", errored=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--product", help="filter to one product")
    args = parser.parse_args()

    checks = collect()
    if args.product:
        checks = [c for c in checks if c.product == args.product]

    print("CONDITIONS REGISTER — every §F floor proven by query, not counted\n")
    current = None
    for check in checks:
        if check.product != current:
            current = check.product
            print(f"\n  {current}")
        print(check.render())

    failed = [c for c in checks if c.state == "FAIL"]
    skipped = [c for c in checks if c.state == "SKIP"]
    passed = [c for c in checks if c.state == "PASS"]

    print(f"\n  {len(passed)} passed · {len(failed)} failed · "
          f"{len(skipped)} skipped (wave not yet run)")
    if failed:
        print("\n  FAILING:")
        for c in failed:
            print(f"    {c.product}: {c.condition} ({c.actual} < {c.floor})")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
