#!/usr/bin/env python3
"""Prove the committed `sources/screening/` artifacts reproduce the live store.

Of the thirteen defects found in this plan's literal reference code, THREE
passed every count check that existed before this validator: the appointment
fold that silently dropped 1,022 of 1,564 records, `owner_kind` mistyping two
corporate reporting owners as `Person`, and a partial `ON CONFLICT ... SET`
that left `deal_id` / `interaction_type` / `interaction_date` stale after a
reload. Two of those three were found BY ACCIDENT, during reconciliation aimed
at something else. Nothing in `validators/` was designed to catch a silent
fold, a silent mistype, or a silent partial upsert -- the check that caught the
third was improvised ad hoc while chasing an unrelated reconciliation. This
validator makes that check permanent.

**The claim under test:** for every tracked JSON artifact this project commits
to `sources/screening/`, loading that exact file into an EMPTY database would
reproduce the table(s) currently sitting there -- not approximately, exactly.
A commit is not a real record of what was loaded if replaying it produces
something different from what is actually live.

**Scope of this run:** the Wave 10 artifacts (`wave10_persons.json`,
`wave10_name_variants.json`, `wave10_appointments.json`, `wave10_holders.json`,
`wave10_crosswalk.json`, `wave10_coverage.json`), because that is where all
three defects above were found and it is where this validator's need was
proven -- plus, as of Wave 11a, every artifact that wave produced
(`wave11a_curve.json`, `wave11a_oas.json`, `wave11a_instruments.json`,
`wave11a_spreads.json`, `wave11a_grades.json`, `wave11a_issuance.json`,
`wave11a_rating_actions.json`), split across whichever store each row
actually landed in -- Postgres for the first four, Fluree for the grade
supersession chain and the two disclosure-event node types, and BOTH for
`wave11a_rating_actions.json` (confirmed candidates become a Fluree
`RatingAssessmentEvent`; unconfirmed ones become a Postgres `context_debt`
row instead, per `generators/fetch_rating_actions.py`). Earlier waves'
artifacts under `sources/screening/` are NOT yet covered -- extending this
validator to them is future scope, not a claim this run makes silently.
`main()` prints which artifacts are in scope so that scope is visible on
every run rather than only in this docstring.

Read-only throughout: every table this script touches is `SELECT`ed, never
written. It never opens a transaction that could mutate anything.

    uv run validators/artifact_reproduces_store.py
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from ccf import fluree
from ccf.config import EX, FLUREE_LEDGER_V2, PG_SCHEMA_V2, REPO_ROOT, pg_connect

S = PG_SCHEMA_V2
L = FLUREE_LEDGER_V2
FIBO = "https://spec.edmcouncil.org/fibo/ontology/"
C_ORG_RATING = f"{FIBO}FBC/DebtAndEquities/CreditRatings/OrganizationCreditRating"
C_ISSUANCE_EVENT = f"{EX}IssuanceEvent"
C_RATING_ASSESSMENT_EVENT = f"{FIBO}FND/Arrangements/Ratings/RatingAssessmentEvent"
P_CONCERNS_PARTY = f"{FIBO}FBC/DebtAndEquities/CreditRatings/concernsParty"
P_FILED_BY = f"{EX}filedBy"
P_SUPERSEDED_BY = f"{EX}supersededBy"

SCREEN = REPO_ROOT / "sources" / "screening"

#: Wave 10 wrote every `person` row carrying this source, and only those.
#:
#: Until Wave 13b, three comparisons here asserted set equality between a
#: Wave 10 artifact and an ENTIRE table -- `person`, `person_name_variant`,
#: `person_crosswalk`. That is a claim Wave 10's artifact was never in a
#: position to make: it says "no other wave may ever write to this table",
#: which is not what "this artifact reproduces what it loaded" means. Wave 13b
#: adds 210 pseudonymized PSC persons to `person` (the FKs from
#: `person_name_variant` and `person_crosswalk` leave no alternative), and an
#: unscoped comparison would report that as a Wave 10 regression.
#:
#: This is the same defect shape as the `context_debt` TRUNCATE
#: (`known-issues.md` §12.8): a wave treating a shared table as its own. The
#: fix is the same -- scope the claim to the rows the wave actually wrote.
WAVE10_PERSON_SOURCE = "sec_cik"

IN_SCOPE = [
    "wave10_persons.json", "wave10_name_variants.json",
    "wave10_appointments.json", "wave10_holders.json",
    "wave10_crosswalk.json", "wave10_coverage.json",
    "wave11a_curve.json", "wave11a_oas.json", "wave11a_instruments.json",
    "wave11a_spreads.json", "wave11a_grades.json", "wave11a_issuance.json",
    "wave11a_rating_actions.json",
    "wave11b_warn.json", "wave11b_gdelt.json", "wave11b_signals.json",
    "wave11b_trend_deltas.json", "wave11b_narrative.json",
]


def _local(node_uri: str) -> str:
    """Strip the `ex:` namespace off a Fluree node URI back to its local id
    (`uri()` in loaders/load_collateral_wave9.py is `f"{EX}{local}"`, so this
    is its exact inverse)."""
    return node_uri.rsplit("/", 1)[-1]


def _fl_rows(sparql: str) -> list[dict]:
    return fluree.query(sparql).get("results", {}).get("bindings", [])


@dataclass
class Result:
    check: str
    table: str
    passed: bool
    detail: str

    def render(self) -> str:
        mark = "PASS" if self.passed else "FAIL"
        return f"  [{mark}] {self.table:22s} {self.check:46s} {self.detail}"


def _load(name: str, key: str) -> list[dict]:
    return json.loads((SCREEN / name).read_text())[key]


def _norm(v):
    """Normalise one value for cross-representation comparison.

    Postgres hands back `date` and `Decimal`; the JSON artifact holds ISO date
    strings and plain Python floats/ints for the same values. Neither side is
    wrong -- they simply do not compare equal, or hash equal, until put in the
    same shape. Rounding floats/Decimals to 4 places matches this schema's
    `NUMERIC(6,4)` columns and avoids a false divergence from binary-float
    representation noise (e.g. `Decimal('0.8421') != 0.8421` as a raw float).
    """
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, Decimal):
        return round(float(v), 4)
    if isinstance(v, float):
        return round(v, 4)
    return v


def _canon(v):
    """`_norm`, plus a canonical form for JSON columns.

    Wave 11b's `signal_event.source_ref` and
    `escalation_threshold.affected_leis` are `JSONB`. Postgres hands them back
    as Python `dict`/`list` (unhashable, and key order is not stable across
    the two sides); the loader hands them to `executemany` as a `json.dumps`
    string. Neither is wrong and neither compares equal, so both are folded to
    a sorted-key JSON string before the tuples are put in a set.
    """
    if isinstance(v, (dict, list)):
        return json.dumps(v, sort_keys=True, default=str)
    if isinstance(v, str) and v[:1] in "{[":
        try:
            return json.dumps(json.loads(v), sort_keys=True, default=str)
        except ValueError:
            return v
    return _norm(v)


def _row(d: dict, cols: list[str]) -> tuple:
    return tuple(_norm(d.get(c)) for c in cols)


def _pg_rows(cur, sql: str, params: tuple = ()) -> set[tuple]:
    cur.execute(sql, params)
    return {tuple(_norm(v) for v in row) for row in cur.fetchall()}


def compare(label: str, table: str, artifact_rows: list[tuple],
            store_rows: set[tuple]) -> list[Result]:
    """Row-count AND full-tuple set equality -- the count check alone is
    exactly the class of check that missed all three defects this validator
    exists to catch.

    `artifact_rows` is the RAW list from the JSON, duplicates included, not
    pre-deduplicated -- a byte-identical duplicate entry in the committed
    artifact is a real divergence from the store worth naming (even if the
    table's own PK/`ON CONFLICT DO NOTHING` happens to absorb it harmlessly at
    load time), because the row-count check exists precisely to catch
    anything a naive `len(rows) == len(table)` sanity check would miss. The
    CONTENT check below still compares the two as sets, since a duplicate
    that collapses to the same distinct value is not a content divergence.
    """
    artifact_set = set(artifact_rows)
    out = [Result(
        f"{label} row count", table, len(artifact_rows) == len(store_rows),
        f"artifact={len(artifact_rows)} store={len(store_rows)}"
        + (f" ({len(artifact_rows) - len(artifact_set)} duplicate row(s) in "
           "the artifact itself)" if len(artifact_rows) != len(artifact_set)
           else ""))]

    only_artifact = artifact_set - store_rows
    only_store = store_rows - artifact_set
    ok = not only_artifact and not only_store
    if ok:
        detail = "content matches exactly"
    else:
        parts = []
        if only_artifact:
            parts.append(f"{len(only_artifact)} in artifact not in store "
                         f"(e.g. {next(iter(only_artifact))})")
        if only_store:
            parts.append(f"{len(only_store)} in store not in artifact "
                         f"(e.g. {next(iter(only_store))})")
        detail = "; ".join(parts)
    out.append(Result(f"{label} content", table, ok, detail))
    return out


# --------------------------------------------------------------------------
def check_persons(cur) -> list[Result]:
    persons = _load("wave10_persons.json", "persons")
    cols = ["person_key", "person_key_source", "cik", "name_as_filed",
            "display_name", "owner_kind"]
    artifact = [_row(p, cols) for p in persons]
    store = _pg_rows(cur, f'SELECT person_key, person_key_source, cik, '
                          f'name_as_filed, display_name, owner_kind '
                          f'FROM "{S}".person '
                          f"WHERE person_key_source = '{WAVE10_PERSON_SOURCE}'")
    out = compare("wave10_persons.json -> person", "person", artifact, store)

    # person_role identity + tenure columns. Deliberately EXCLUDES
    # appointment_date/appointment_source -- those are a many-to-one FOLD
    # over wave10_appointments.json, not a straight projection, and are
    # checked separately in check_appointments() where the fold logic lives.
    role_cols = ["lei", "role", "officer_title", "first_seen", "last_seen"]
    artifact_roles = [(p["person_key"],) + _row(r, role_cols)
                       for p in persons for r in p["roles"]]
    store_roles = _pg_rows(cur, f'SELECT person_key, lei, role, '
                                f'officer_title, first_seen, last_seen '
                                f'FROM "{S}".person_role')
    out += compare("wave10_persons.json -> person_role (identity/tenure)",
                   "person_role", artifact_roles, store_roles)
    return out


def check_appointments(cur) -> list[Result]:
    """Reproduce the loader's fold: earliest appointment per (person, lei),
    then null out any row where that date postdates the ROLE's own
    first_seen (the self-contradiction rule this fix wave added).

    This is the check the appointment-fold defect needed and never had. A
    plain row-count comparison cannot work here -- the loader legitimately
    reduces 1,564 raw records to <= 542 (person_key, lei) pairs by design, so
    "the counts differ" is expected, not a defect. The defect was reducing
    them to the WRONG surviving set. Reproducing the fold and the null-rule
    here, independently of the loader's own copy of that logic, and comparing
    the RESULT rather than the count is what makes this check meaningful.
    """
    from loaders.load_postgres_wave10 import earliest_appointment

    appointments = _load("wave10_appointments.json", "appointments")
    best = earliest_appointment(appointments)  # {(person_key, lei): appt}

    cur.execute(f'SELECT person_key, lei, role, first_seen '
                f'FROM "{S}".person_role')
    role_rows = cur.fetchall()

    expected: set[tuple] = set()
    for pk, lei, role, first_seen in role_rows:
        appt = best.get((pk, lei))
        if appt is None:
            expected.add((pk, lei, role, None))
            continue
        d = appt["appointment_date"]
        fs = first_seen.isoformat() if first_seen else None
        # loaders/load_postgres_wave10.py: UPDATE ... WHERE appointment_date
        # > first_seen nulls a self-contradictory row after load.
        expected.add((pk, lei, role, None if (fs is not None and d > fs) else d))

    actual = _pg_rows(cur, f'SELECT person_key, lei, role, appointment_date '
                          f'FROM "{S}".person_role')

    return compare(
        "wave10_appointments.json -> person_role.appointment_date "
        "(earliest-per-role, self-contradictory rows nulled)",
        "person_role", expected, actual)


def check_name_variants(cur) -> list[Result]:
    variants = _load("wave10_name_variants.json", "variants")
    cols = ["person_key", "variant_name", "source", "rendering", "provenance"]
    artifact = [_row(v, cols) for v in variants]
    store = _pg_rows(cur, f'SELECT v.person_key, v.variant_name, v.source, '
                          f'v.rendering, v.provenance '
                          f'FROM "{S}".person_name_variant v '
                          f'JOIN "{S}".person p USING (person_key) '
                          f"WHERE p.person_key_source = '{WAVE10_PERSON_SOURCE}'")
    return compare("wave10_name_variants.json -> person_name_variant",
                   "person_name_variant", artifact, store)


def check_holders(cur) -> list[Result]:
    holders = _load("wave10_holders.json", "holders")
    cols = ["lei", "manager_cik", "manager_name", "cusip", "value_usd",
            "shares", "report_period", "issuer_match_score",
            "issuer_match_band", "provenance"]
    artifact = [_row(h, cols) for h in holders]
    store = _pg_rows(cur, f'SELECT lei, manager_cik, manager_name, cusip, '
                          f'value_usd, shares, report_period, '
                          f'issuer_match_score, issuer_match_band, '
                          f'provenance FROM "{S}".institutional_holder')
    return compare("wave10_holders.json -> institutional_holder",
                   "institutional_holder", artifact, store)


def check_crosswalk(cur) -> list[Result]:
    rows = _load("wave10_crosswalk.json", "rows")
    cols = ["source_system", "source_id", "source_name", "person_key",
            "match_score", "match_band", "is_true_match", "provenance", "note"]
    artifact = [_row(r, cols) for r in rows]
    store = _pg_rows(cur, f'SELECT c.source_system, c.source_id, '
                          f'c.source_name, c.person_key, c.match_score, '
                          f'c.match_band, c.is_true_match, c.provenance, '
                          f'c.note FROM "{S}".person_crosswalk c '
                          f'JOIN "{S}".person p USING (person_key) '
                          f"WHERE p.person_key_source = '{WAVE10_PERSON_SOURCE}'")
    return compare("wave10_crosswalk.json -> person_crosswalk",
                   "person_crosswalk", artifact, store)


def check_coverage(cur) -> list[Result]:
    coverage = json.loads((SCREEN / "wave10_coverage.json").read_text())
    out: list[Result] = []

    cols = ["banker_id", "full_name", "role", "seniority", "desk", "provenance"]
    artifact = [_row(b, cols) for b in coverage["bankers"]]
    store = _pg_rows(cur, f'SELECT banker_id, full_name, role, seniority, '
                          f'desk, provenance FROM "{S}".banker')
    out += compare("wave10_coverage.json[bankers] -> banker", "banker",
                   artifact, store)

    cols = ["banker_id", "lei", "is_primary", "assigned_date", "provenance"]
    artifact = [_row(a, cols) for a in coverage["coverage_assignments"]]
    store = _pg_rows(cur, f'SELECT banker_id, lei, is_primary, assigned_date, '
                          f'provenance FROM "{S}".coverage_assignment')
    out += compare("wave10_coverage.json[coverage_assignments] -> "
                   "coverage_assignment", "coverage_assignment",
                   artifact, store)

    # Scoped to Wave 10's own rows: Wave 7's 50 pre-existing `INT-` interactions
    # (no `-W10-` segment) are a disjoint id space this artifact does not own
    # and must not be compared against -- this is the exact scope the loader's
    # own `DELETE ... WHERE interaction_id LIKE 'INT-W10-%'` uses. This is also
    # the check that would have caught the stale-ON-CONFLICT defect: full-row
    # equality, not just an interaction_id key set, is what exposes a column
    # left stale by a partial `DO UPDATE SET`.
    cols = ["interaction_id", "lei", "deal_id", "interaction_type",
            "interaction_date", "mnpi_bearing", "provenance", "channel",
            "subject", "need_to_know"]
    artifact = [_row(i, cols) for i in coverage["interactions"]]
    store = _pg_rows(cur, f'SELECT interaction_id, lei, deal_id, '
                          f'interaction_type, interaction_date, mnpi_bearing, '
                          f'provenance, channel, subject, need_to_know '
                          f'FROM "{S}".interaction '
                          f"WHERE interaction_id LIKE %s", ("INT-W10-%",))
    out += compare("wave10_coverage.json[interactions] -> interaction "
                   "(INT-W10-% only)", "interaction", artifact, store)

    cols = ["interaction_id", "party_kind", "party_key", "provenance"]
    artifact = [_row(p, cols) for p in coverage["participants"]]
    store = _pg_rows(cur, f'SELECT interaction_id, party_kind, party_key, '
                          f'provenance FROM "{S}".interaction_participant')
    out += compare("wave10_coverage.json[participants] -> "
                   "interaction_participant", "interaction_participant",
                   artifact, store)

    cols = ["weight_name", "policy_version", "weight_value", "effective_date",
            "provenance"]
    artifact = [_row(w, cols) for w in coverage["scoring_weights"]]
    store = _pg_rows(cur, f'SELECT weight_name, policy_version, weight_value, '
                          f'effective_date, provenance '
                          f'FROM "{S}".scoring_weight')
    out += compare("wave10_coverage.json[scoring_weights] -> scoring_weight",
                   "scoring_weight", artifact, store)

    return out


# --------------------------------------------------------------------------
# Wave 11a
# --------------------------------------------------------------------------

def check_curve(cur) -> list[Result]:
    """`tenor_years` carries SIX decimal places ("0.083333" for the 1-month
    point) -- `_pg_rows`'s shared `_norm` rounds to four, tuned for this
    schema's OTHER `NUMERIC(6,4)` columns. Reusing it here would silently
    collapse the artifact/store comparison's own precision below the data's
    real precision and manufacture a divergence that is an artefact of the
    check, not of the load (0.083333 vs the round-to-4 0.0833) -- so this
    check normalises both sides to 6dp itself rather than going through the
    generic helper.
    """
    curve = json.loads((SCREEN / "wave11a_curve.json").read_text())
    provenance = curve["provenance"]
    artifact = [
        (row["date"], round(float(tenor), 6), yld, provenance)
        for row in curve["curve"] for tenor, yld in row["tenors"].items()
    ]
    cur.execute(f'SELECT curve_date, tenor_years, par_yield_pct, provenance '
                f'FROM "{S}".benchmark_curve')
    store = {
        (d.isoformat(), round(float(tenor), 6), float(yld), prov)
        for d, tenor, yld, prov in cur.fetchall()
    }
    return compare("wave11a_curve.json -> benchmark_curve", "benchmark_curve",
                   artifact, store)


def check_oas(cur) -> list[Result]:
    oas = json.loads((SCREEN / "wave11a_oas.json").read_text())
    provenance = oas["provenance"]
    artifact = [
        (point["date"], band, obj["fred_id"], point["oas_bp"], obj["unit"],
         provenance)
        for band, obj in oas["series"].items() for point in obj["points"]
    ]
    store = _pg_rows(cur, f'SELECT obs_date, rating_band, fred_series_id, '
                          f'oas_bp, unit, provenance '
                          f'FROM "{S}".market_oas_series')
    return compare("wave11a_oas.json -> market_oas_series",
                   "market_oas_series", artifact, store)


def check_instruments(cur) -> list[Result]:
    instruments = _load("wave11a_instruments.json", "instruments")
    cols = ["instrument_id", "lei", "coupon_pct", "maturity", "issue_date",
            "face_amount_usd", "rating_band", "seniority", "tenor_years",
            "anchored_to_real_filing", "anchor_accession", "provenance",
            "provenance_note"]
    artifact = [_row(i, cols) for i in instruments]
    store = _pg_rows(cur, f'SELECT instrument_id, lei, coupon_pct, maturity, '
                          f'issue_date, face_amount_usd, rating_band, '
                          f'seniority, tenor_years, anchored_to_real_filing, '
                          f'anchor_accession, provenance, provenance_note '
                          f'FROM "{S}".debt_instrument')
    return compare("wave11a_instruments.json -> debt_instrument",
                   "debt_instrument", artifact, store)


def check_spreads(cur) -> list[Result]:
    """The 29,885-row artifact. `provenance_*` are NOT per-row fields in the
    JSON -- they are a single dict (`spreads_doc["provenance"]`) applied to
    every row by the loader, exactly as loaders/load_postgres_wave11a.py
    does it, so the artifact reconstruction has to fold that in the same
    way rather than look for a column that was never there.
    """
    spreads = json.loads((SCREEN / "wave11a_spreads.json").read_text())
    prov = spreads["provenance"]
    observations = spreads["observations"]
    artifact = [
        (o["instrument_id"], o["obs_date"], o["years_to_maturity"],
         o["benchmark_bp"], o["market_oas_bp"], o["idiosyncratic_bp"],
         o["spread_bp"], o["yield_bp"], prov["benchmark_bp"],
         prov["market_oas_bp"], prov["idiosyncratic_bp"])
        for o in observations
    ]
    store = _pg_rows(cur, f'SELECT instrument_id, obs_date, '
                          f'years_to_maturity, benchmark_bp, market_oas_bp, '
                          f'idiosyncratic_bp, spread_bp, yield_bp, '
                          f'provenance_benchmark, provenance_market_oas, '
                          f'provenance_idiosyncratic '
                          f'FROM "{S}".spread_observation')
    return compare("wave11a_spreads.json -> spread_observation",
                   "spread_observation", artifact, store)


def check_rating_scale(cur) -> list[Result]:
    """`rating_scale` is DERIVED, not a straight column projection -- Task 7
    folds `wave11a_grades.json["grade_scale"]["grades"]` through
    `grade_to_notch` before it becomes rows. Reproducing that fold here
    (rather than re-deriving a second, independent mapping) is what makes
    this a reproduction check and not a second opinion that could quietly
    drift from the loader's own logic.
    """
    from loaders.load_postgres_wave11a import POLICY_VERSION, grade_to_notch

    grades_doc = json.loads((SCREEN / "wave11a_grades.json").read_text())
    scale = grades_doc["grade_scale"]["grades"]
    artifact = [
        (grade, POLICY_VERSION, notch, band, modifier, "synthetic — internal")
        for grade, notch, band, modifier in grade_to_notch(scale)
    ]
    store = _pg_rows(cur, f'SELECT grade, policy_version, notch, rating_band, '
                          f'modifier, provenance FROM "{S}".rating_scale')
    return compare("wave11a_grades.json[grade_scale] -> rating_scale",
                   "rating_scale", artifact, store)



def check_wave11b(cur) -> list[Result]:
    """All seven Wave 11b Postgres tables, against the five artifacts that fed
    them.

    **Why this exists (added 2026-08-21).** Until this function, no
    artifact-reproduces-store check covered ANY Wave 11b table. The whole-branch
    review demonstrated the cost concretely: delete half of `trend_delta`
    (3,705 rows) or half of `warn_notice` (3,514) and the entire estate still
    reported `partition.py` 19/19, `conditions.py` 91/0 and `surveillance.py`
    PASS. Two of the biggest tables in the wave had no check that could see a
    silent truncation.

    **It reuses the loader's own `build_rows`, on purpose.** That is the same
    decision `check_rating_scale` makes for `grade_to_notch`, and for the same
    reason: the claim under test is *"loading this exact file into an empty
    database would reproduce these tables"*, and the only faithful way to
    evaluate it is with the transform the loader actually performs. Writing a
    second, independent transform here would test a different claim — that two
    implementations agree — which is the `conditions.py:32` self-agreement trap
    wearing a reproduction-check costume, and it would drift the first time the
    loader changed.

    What it therefore CAN catch: a truncated or half-loaded table, a partial
    `ON CONFLICT ... DO UPDATE SET` leaving a column stale after a reload, a
    row edited in the store, a reload that never happened after the artifact
    was regenerated. What it CANNOT catch: a bug inside `build_rows` itself.
    That boundary is stated rather than implied.
    """
    from loaders.load_postgres_wave11b import build_rows, load as _l11b

    rows = build_rows(_l11b("wave11b_warn.json"), _l11b("wave11b_gdelt.json"),
                      _l11b("wave11b_signals.json"),
                      _l11b("wave11b_trend_deltas.json"),
                      _l11b("wave11b_narrative.json"))

    # (table, artifact label, column list in the loader's INSERT order)
    specs: list[tuple[str, str, list[str]]] = [
        ("warn_notice", "wave11b_warn.json[notices]",
         ["notice_id", "state", "employer", "notice_date", "effective_date",
          "employees", "city", "county", "source_ref", "provenance"]),
        ("warn_match", "wave11b_warn.json[matches]",
         ["notice_id", "lei", "anchor_name", "employer", "state", "score",
          "verdict", "notice_ref", "provenance"]),
        ("gdelt_mention", "wave11b_gdelt.json[mentions]",
         ["url", "lei", "employer_query", "gdelt_query", "seendate", "domain",
          "title", "tone", "provenance", "down_weight_factor",
          "down_weight_reason"]),
        ("signal_event", "wave11b_signals.json + wave11b_narrative.json",
         ["signal_id", "lei", "signal_type", "observed_at", "severity",
          "source_ref", "provenance"]),
        ("signal_weight", "wave11b_signals.json[weights+decay_days]",
         ["signal_type", "sector", "policy_version", "weight", "decay_days",
          "rationale", "provenance"]),
        ("escalation_threshold", "wave11b_signals.json[thresholds]",
         ["kind", "intent", "policy_version", "threshold_score",
          "threshold_pct", "signal_type", "rule", "affected_leis",
          "roll_window_obs", "anticipation_fraction_of_sector_threshold",
          "confirmation_fraction_of_sector_threshold", "rationale",
          "provenance"]),
        ("trend_delta", "wave11b_trend_deltas.json[deltas]",
         ["lei", "tag", "unit", "period_end", "prior_period_end", "value",
          "prior_value", "pct_change", "provenance"]),
    ]

    out: list[Result] = []
    for table, label, cols in specs:
        artifact = [tuple(_canon(v) for v in r) for r in rows[table]]
        cur.execute(f'SELECT {", ".join(cols)} FROM "{S}".{table}')
        store = {tuple(_canon(v) for v in r) for r in cur.fetchall()}
        out += compare(f"{label} -> {table}", table, artifact, store)
    return out


def check_grades_fluree() -> list[Result]:
    """The supersession chain lives in Fluree, not Postgres (see
    loaders/load_fluree_wave11a.py's module docstring) -- so this is the one
    check in this file that reproduces a store OTHER than Postgres. Two
    parts: every assertion node's own attributes, and the `supersededBy`
    edges that carry the chain itself.
    """
    grades_doc = json.loads((SCREEN / "wave11a_grades.json").read_text())
    assertions = grades_doc["assertions"]

    cols = ["grade", "valid_from", "asserted_at", "trigger", "provenance", "lei"]
    artifact_nodes = {
        (a["assertion_id"],) + tuple(a[c] for c in cols) + (a["valid_to"],)
        for a in assertions
    }
    rows = _fl_rows(f"""
        SELECT ?a ?grade ?validFrom ?assertedAt ?trigger ?provenance ?lei ?validTo
        FROM <{L}> WHERE {{
          ?a a <{C_ORG_RATING}> .
          ?a <{EX}grade> ?grade . ?a <{EX}validFrom> ?validFrom .
          ?a <{EX}assertedAt> ?assertedAt . ?a <{EX}trigger> ?trigger .
          ?a <{EX}provenance> ?provenance .
          ?a <{P_CONCERNS_PARTY}> ?party . ?party <{EX}lei> ?lei .
          OPTIONAL {{ ?a <{EX}validTo> ?validTo }}
        }}""")
    store_nodes = {
        (_local(r["a"]["value"]), r["grade"]["value"], r["validFrom"]["value"],
         r["assertedAt"]["value"], r["trigger"]["value"], r["provenance"]["value"],
         r["lei"]["value"], r.get("validTo", {}).get("value"))
        for r in rows
    }
    out = compare("wave11a_grades.json[assertions] -> Fluree CreditRating "
                  "node attributes", "fluree:CreditRating",
                  list(artifact_nodes), store_nodes)

    # `ex:supersededBy` is SHARED. It carried only Wave 11a's 215 grade-chain
    # edges until 2026-08-21, when load_fluree_wave11b.py added 535 more (486
    # on `sig-8k-*` subjects, 49 on `prior-obs-*`) for the surveillance chain.
    # A blind predicate scan therefore compares a Wave 11a artifact against
    # 750 edges and reports 535 "in store not in artifact" — a divergence that
    # is not one. Scoped by SUBJECT to the assertion ids this artifact itself
    # carries, which is the same correction made to that loader's
    # `--reconcile` on the same day (docs/known-issues.md §10.5).
    #
    # Scoping to the artifact's own ids does not weaken the check. The two
    # halves still both bite: an artifact edge missing from the store fails as
    # before, and a store edge on a `syn-g-*` subject the artifact does not
    # name still fails, because that subject IS in `assertion_ids`.
    assertion_ids = {a["assertion_id"] for a in assertions}
    artifact_super = {(a["supersedes"], a["assertion_id"])
                       for a in assertions if a["supersedes"]}
    super_rows = _fl_rows(
        f"SELECT ?s ?o FROM <{L}> WHERE {{ ?s <{P_SUPERSEDED_BY}> ?o }}")
    store_super = {(_local(r["s"]["value"]), _local(r["o"]["value"]))
                   for r in super_rows
                   if _local(r["s"]["value"]) in assertion_ids}
    out += compare("wave11a_grades.json[assertions.supersedes] -> Fluree "
                   "supersededBy edges", "fluree:supersededBy",
                   list(artifact_super), store_super)
    return out


def check_issuance_fluree() -> list[Result]:
    issuance = _load("wave11a_issuance.json", "issuance")
    artifact = {
        (r["accession"], r["file_date"], r["provenance"], r["lei"])
        for r in issuance
    }
    rows = _fl_rows(f"""
        SELECT ?a ?validFrom ?accession ?provenance ?lei FROM <{L}> WHERE {{
          ?a a <{C_ISSUANCE_EVENT}> .
          ?a <{EX}validFrom> ?validFrom . ?a <{EX}sourceAccession> ?accession .
          ?a <{EX}provenance> ?provenance .
          ?a <{P_FILED_BY}> ?party . ?party <{EX}lei> ?lei .
        }}""")
    store = {
        (r["accession"]["value"], r["validFrom"]["value"],
         r["provenance"]["value"], r["lei"]["value"])
        for r in rows
    }
    return compare("wave11a_issuance.json -> Fluree IssuanceEvent nodes",
                   "fluree:IssuanceEvent", list(artifact), store)


def check_rating_actions() -> list[Result]:
    """Two disjoint destinations for one artifact, per
    generators/fetch_rating_actions.py: a CONFIRMED candidate becomes a
    Fluree RatingAssessmentEvent node; an UNCONFIRMED one becomes a
    Postgres `context_debt` row instead. Checked against each store the row
    actually landed in, not against one store for the whole file.
    """


    actions = _load("wave11a_rating_actions.json", "rating_actions")
    confirmed = [r for r in actions if r["confirmed"]]
    unconfirmed = [r for r in actions if not r["confirmed"]]

    artifact_confirmed = {
        (r["accession"], r["file_date"], r["provenance"], r["evidence"], r["lei"])
        for r in confirmed
    }
    rows = _fl_rows(f"""
        SELECT ?a ?validFrom ?accession ?provenance ?evidence ?lei
        FROM <{L}> WHERE {{
          ?a a <{C_RATING_ASSESSMENT_EVENT}> .
          ?a <{EX}validFrom> ?validFrom . ?a <{EX}sourceAccession> ?accession .
          ?a <{EX}provenance> ?provenance . ?a <{EX}evidence> ?evidence .
          ?a <{P_CONCERNS_PARTY}> ?party . ?party <{EX}lei> ?lei .
        }}""")
    store_confirmed = {
        (r["accession"]["value"], r["validFrom"]["value"],
         r["provenance"]["value"], r["evidence"]["value"], r["lei"]["value"])
        for r in rows
    }
    out = compare("wave11a_rating_actions.json[confirmed] -> Fluree "
                  "RatingAssessmentEvent nodes", "fluree:RatingAssessmentEvent",
                  list(artifact_confirmed), store_confirmed)

    # The artifact's OWN `reason` string is compared against the store column.
    # Two earlier versions got this wrong in opposite directions and BOTH
    # misattributed divergence: the first froze a copy of the sentence here
    # (while its own comment claimed otherwise); the second imported the
    # generator's constant. Either way, an edit to the generator that had not
    # been re-run made this check report "artifact and store disagree" when
    # artifact and store agreed exactly. Reading `r["reason"]` is the only
    # form that tests what this file is named for -- and it closes a second
    # hole, because a hand-edited or corrupted `reason` in the artifact passed
    # both earlier forms unnoticed. See known-issues.md §9.1.
    with pg_connect() as conn, conn.cursor() as cur:
        artifact_debt = {
            (r["accession"], "rating_action", r["accession"], r["reason"])
            for r in unconfirmed
        }
        store_debt = _pg_rows(cur, f'SELECT accession, subject_kind, '
                                   f'subject_key, reason FROM "{S}".context_debt '
                                   "WHERE subject_kind = 'rating_action'")
    out += compare("wave11a_rating_actions.json[unconfirmed] -> "
                   "context_debt", "context_debt",
                   list(artifact_debt), store_debt)
    return out


def main() -> int:
    print("ARTIFACT REPRODUCES STORE — every tracked source artifact vs the "
          "live tables it fed\n")
    print(f"  in scope this run: {', '.join(IN_SCOPE)}")
    print("  NOT yet covered: pre-Wave-10 artifacts under sources/screening/, "
          "and ALL FIVE Wave 14 artifacts under sources/absee/ "
          "(deals, manifest, overlay, prospectus_extract, trigger_amendment) "
          "-- they sit outside this validator's SCREEN root, so their absence "
          "here is silent rather than reported. Future extension, not claimed "
          "here.\n")

    results: list[Result] = []
    with pg_connect() as conn, conn.cursor() as cur:
        results += check_persons(cur)
        results += check_appointments(cur)
        results += check_name_variants(cur)
        results += check_holders(cur)
        results += check_crosswalk(cur)
        results += check_coverage(cur)
        results += check_curve(cur)
        results += check_oas(cur)
        results += check_instruments(cur)
        results += check_spreads(cur)
        results += check_rating_scale(cur)
        results += check_wave11b(cur)
        # Read-only: no INSERT/UPDATE/DELETE/DDL issued anywhere above, and
        # nothing here calls conn.commit() -- rolling back on exit costs
        # nothing to discard.
        conn.rollback()

    # Fluree-backed checks -- these reproduce a store OTHER than Postgres,
    # so they sit outside the `with pg_connect()` block above (two of them
    # open their own short-lived Postgres connection internally instead).
    results += check_grades_fluree()
    results += check_issuance_fluree()
    results += check_rating_actions()

    for r in results:
        print(r.render())

    failed = [r for r in results if not r.passed]
    print(f"\n  {len(results) - len(failed)}/{len(results)} checks passed")
    if failed:
        print("\n  DIVERGENCE — artifact and store disagree. Name the "
              "artifact and table above; do not paper over this by re-running "
              "the loader without first finding WHY they disagree.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
