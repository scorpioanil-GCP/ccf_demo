#!/usr/bin/env python3
"""Wave 11b Task 12 — the early-warning surveillance gate.

In the lineage of `validators/series.py` and `validators/traversal.py`:
`conditions.py` counts rows, and a count cannot establish a claim that
requires walking a graph, recomputing a score, or measuring a distribution.
This estate has already been bitten once by a validator that shared the
loader's own wrong constants and agreed with itself while passing
(`validators/conditions.py:32`). The discipline here is the same one
`series.py` and `traversal.py` already follow: read from the LOADED STORES,
never from a generator artifact (`sources/screening/wave11b_*.json`) and
never from a flag a generator set. The one sanctioned exception is importing
shared *logic* — `is_subthreshold` from `generators.narrative_wave11b` — not
shared data; see claim 2 below for why that import is load-bearing.

Six claims, none of which a row count proves:

1. CASCADE COMPLETENESS. The engineered Item 2.04 signal is found
   STRUCTURALLY in Fluree — provenance `synthetic — engineered` plus a
   `triggeredBy` source whose item is `2.04` — never by matching "Avis
   Budget" as a string anywhere in the query. Its `signalAbout` targets are
   then resolved against Postgres and checked for EXACT membership: the one
   Facility, and every CollateralPledge and every Drawdown that facility
   actually carries — not merely "some pledge, some drawdown exist
   somewhere". A count of 8 edges says nothing about where they terminate;
   this does.

2. THE COMPOSITE CASE. Each of the three engineered `sig-composite-*` rows
   in `signal_event` has its weighted score recomputed here from
   `signal_weight` (via the obligor's sector, resolved the same way
   `series.py` resolves one — `sector_for`, imported not reimplemented) and
   `escalation_threshold`, both AS LOADED in Postgres — never from the
   `weighted_score` the generator already wrote into `source_ref`, which is
   the generator's own claim, not evidence. `is_subthreshold` is IMPORTED
   from `generators.narrative_wave11b` rather than reimplemented: if this
   validator wrote its own `severity <= threshold` comparison, it could
   drift from the generator's and the two would validate each other's bug.

3. SCORE DISTRIBUTION. The composite warning score — sum of
   severity x weight across every `signal_event` row, per obligor, exactly
   the arithmetic `is_subthreshold`'s callers already use — is computed for
   all 50 anchors from the loaded `signal_event` and `signal_weight` tables.
   §F wants scores to "vary rather than cluster"; a user decision (D3, per
   design §7.1) removed the mechanism that was going to DESIGN that
   distribution, so it is MEASURED here instead, and reported honestly
   whichever way it comes out — see `QCD_CLUSTER_FLOOR` below for how
   "cluster" is operationalized, and why.

4. DELTA ANCHORING. Every one of the 50 `is_anchor` obligors — the actual
   Postgres set, not an assumed count of 50 — carries EXACTLY ONE
   `PriorObservation` node in Fluree. §D names this explicitly: without a
   recorded prior, the next sweep double-reports; zero is a gap, two is an
   ambiguous watermark, and both are checked for, not just the total.

5. WARN RESOLUTION QUALITY. Checked in ONE combined condition, per the
   brief: at least 3 distinct obligors carry a `resolved` match AND at
   least 1 pair remains `ambiguous`. A `warn_match` table containing only
   the clean resolutions would pass a row-count floor and destroy the
   demonstration — the lossy join has to stay visible in what actually
   loaded, not merely in what the generator intended.

6. GDELT CONCENTRATION. §F asks for ~200 mentions *"weighted toward a
   handful of names"*. Only the COUNT half of that clause was gated until
   2026-08-21 — `conditions.py` checked 951 >= 200 and nothing checked the
   concentration at all. Added here because the gap is not theoretical:
   §10.1 of `docs/known-issues.md` records that the first sweep's 77.8%
   top-5 concentration was ENTIRELY a noise artifact, so a concentration
   figure nobody recomputes from the loaded store proves nothing. Measured
   in three directions — there is a head; the head is a handful of names
   rather than one; and the head survives dropping every down-weighted
   mention.

    uv run validators/surveillance.py

Exit code is non-zero if any of the six claims fails.
"""

from __future__ import annotations

import statistics
import sys
from collections import Counter

from ccf import fluree
from ccf.config import EX, FLUREE_LEDGER_V2, PG_SCHEMA_V2, pg_connect
from generators.narrative_wave11b import is_subthreshold
from loaders.load_postgres_wave11a import sector_for

S = PG_SCHEMA_V2
L = FLUREE_LEDGER_V2


def bindings(sparql: str) -> list[dict]:
    return fluree.query(sparql).get("results", {}).get("bindings", [])


# ==========================================================================
# 1. Cascade completeness
# ==========================================================================

def resolve_cascade_signal() -> tuple[str, str, list[str]]:
    """The engineered Item 2.04 WarningSignal, found STRUCTURALLY — never by
    name. Returns (signal_uri, source_accession, [local target ids]).

    Raises if the structural query does not resolve to exactly one signal:
    a design that names "Avis Budget Group" as the anchor but finds zero, or
    more than one, engineered-2.04-triggered signal is a real defect, not a
    SKIP.
    """
    q = f"""
    SELECT ?sig ?accession ?o FROM <{L}> WHERE {{
      ?sig a <{EX}WarningSignal> .
      ?sig <{EX}provenance> "synthetic — engineered" .
      ?sig <{EX}triggeredBy> ?src .
      ?src <{EX}item> "2.04" .
      ?src <{EX}sourceAccession> ?accession .
      ?sig <{EX}signalAbout> ?o .
    }}
    """
    rows = bindings(q)
    sig_uris = {r["sig"]["value"] for r in rows}
    if len(sig_uris) != 1:
        raise AssertionError(
            f"expected exactly one engineered Item 2.04 WarningSignal in "
            f"Fluree, found {len(sig_uris)}: {sorted(sig_uris)}"
        )
    sig_uri = next(iter(sig_uris))
    accession = next(iter({r["accession"]["value"] for r in rows}))
    targets = sorted({r["o"]["value"][len(EX):] for r in rows
                       if r["o"]["value"].startswith(EX)})
    return sig_uri, accession, targets


def cascade_completeness(cur) -> tuple[bool, list[tuple[str, bool, str]]]:
    sig_uri, accession, target_ids = resolve_cascade_signal()
    detail: list[tuple[str, bool, str]] = [
        ("engineered Item 2.04 signal resolved by structure (provenance + "
         "triggeredBy item=2.04), not by name", True,
         f"{sig_uri.rsplit('/', 1)[-1]}  accession={accession}  "
         f"{len(target_ids)} signalAbout target(s)"),
    ]

    cur.execute(
        f'SELECT facility_id, borrower_lei FROM "{S}".facility '
        f"WHERE facility_id = ANY(%s)", (target_ids,))
    facility_rows = cur.fetchall()

    ok_facility = len(facility_rows) == 1
    detail.append((
        "target set contains EXACTLY ONE Facility", ok_facility,
        f"{len(facility_rows)} match(es): {facility_rows}"))
    if not ok_facility:
        return False, detail

    facility_id, borrower_lei = facility_rows[0]

    cur.execute(f'SELECT legal_name FROM "{S}".legal_entity WHERE lei = %s',
                (borrower_lei,))
    row = cur.fetchone()
    legal_name = row[0] if row else None
    detail.append((
        "anchor obligor resolved from the facility's own borrower_lei "
        "(never hardcoded)", legal_name is not None,
        f"{borrower_lei} -> {legal_name!r}"))

    # Strongest form of the claim: not "at least one pledge/drawdown", but
    # that the signal's targets are EXACTLY the facility's full pledge and
    # drawdown sets -- no fewer (an incomplete cascade), no more (a target
    # naming something that isn't this facility's). Deliberately NOT a
    # `WHERE asset_id = ANY(target_ids)` lookup checked for a matching
    # `facility_id` on each row: `collateral_pledge.asset_id` is not
    # exclusive to one facility -- COL-00044 is ALSO pledged (priority
    # "second") to a different facility as a planted shared-collateral
    # case elsewhere in the estate, so that broader query returns a row
    # that correctly belongs to another facility and is not a defect here.
    # Intersecting the target set against THIS facility's own pledge/
    # drawdown sets sidesteps that entirely.
    cur.execute(f'SELECT asset_id FROM "{S}".collateral_pledge '
                f'WHERE facility_id = %s', (facility_id,))
    all_pledges = {r[0] for r in cur.fetchall()}
    cur.execute(f'SELECT drawdown_id FROM "{S}".drawdown '
                f'WHERE facility_id = %s', (facility_id,))
    all_drawdowns = {r[0] for r in cur.fetchall()}
    target_set = set(target_ids)
    target_pledges = target_set & all_pledges
    target_drawdowns = target_set & all_drawdowns

    exact_pledges = bool(all_pledges) and target_pledges == all_pledges
    exact_drawdowns = bool(all_drawdowns) and target_drawdowns == all_drawdowns
    detail.append((
        "signalAbout targets == facility's FULL collateral_pledge set "
        "(exact, not merely nonempty)", exact_pledges,
        f"targets {sorted(target_pledges)} vs facility's own "
        f"{sorted(all_pledges)}"))
    detail.append((
        "signalAbout targets == facility's FULL drawdown set "
        "(exact, not merely nonempty)", exact_drawdowns,
        f"targets {sorted(target_drawdowns)} vs facility's own "
        f"{sorted(all_drawdowns)}"))

    cur.execute(f'SELECT count(*) FROM "{S}".covenant_breach '
                f'WHERE facility_id = %s', (facility_id,))
    n_covenant = cur.fetchone()[0]
    detail.append((
        "the facility carries the covenant breach the cascade invalidates "
        "(supporting context, per design §3.1's \"facility that carries "
        "its covenant\")", n_covenant >= 1, f"{n_covenant} covenant_breach "
        f"row(s) on {facility_id}"))

    unclassified = target_set - {facility_id} - all_pledges - all_drawdowns
    detail.append((
        "no signalAbout target is left unclassified (not this facility, "
        "or one of ITS pledges or drawdowns)", not unclassified,
        f"unclassified: {sorted(unclassified)}"))

    ok = (ok_facility and legal_name is not None and exact_pledges
          and exact_drawdowns and n_covenant >= 1 and not unclassified)
    return ok, detail


# ==========================================================================
# 2. The composite case
# ==========================================================================

def composite_signal_rows(cur) -> list[dict]:
    """The 3 engineered `sig-composite-*` rows, matched by id shape AND
    provenance -- never by trusting a count. The other 10 engineered
    `signal_event` rows (`sig-spread-*`, inherited from Wave 11a's own
    engineered spread series) are structurally excluded by the id prefix,
    not by an assumed row count."""
    cur.execute(
        f'SELECT signal_id, lei, signal_type, severity FROM "{S}".signal_event '
        f"WHERE signal_id LIKE 'sig-composite-%%' AND provenance = %s "
        f"ORDER BY signal_id", ("synthetic — engineered",))
    return [
        {"signal_id": sid, "lei": lei, "signal_type": st, "severity": float(sev)}
        for sid, lei, st, sev in cur.fetchall()
    ]


def sector_of(cur, lei: str) -> str:
    cur.execute(f'SELECT sic FROM "{S}".legal_entity WHERE lei = %s', (lei,))
    row = cur.fetchone()
    if row is None:
        raise AssertionError(f"{lei!r} not found in legal_entity")
    return sector_for(row[0])


def weight_for(cur, signal_type: str, sector: str) -> float:
    cur.execute(
        f'SELECT weight FROM "{S}".signal_weight '
        f"WHERE signal_type = %s AND sector = %s", (signal_type, sector))
    rows = cur.fetchall()
    if len(rows) != 1:
        raise AssertionError(
            f"expected exactly one signal_weight row for "
            f"(signal_type={signal_type!r}, sector={sector!r}), found "
            f"{len(rows)} -- policy_version ambiguity, not resolved here")
    return float(rows[0][0])


def escalation_threshold_rows(cur) -> list[dict]:
    cur.execute(f'SELECT kind, intent, threshold_score '
                f'FROM "{S}".escalation_threshold')
    return [
        {"kind": k, "intent": i, "threshold_score": float(t) if t is not None else None}
        for k, i, t in cur.fetchall()
    ]


def composite_case_check(cur) -> tuple[bool, list[tuple[str, bool, str]]]:
    rows = composite_signal_rows(cur)
    detail: list[tuple[str, bool, str]] = []

    n_ok = len(rows) == 3
    detail.append(("exactly 3 sig-composite-* engineered rows in "
                    "signal_event", n_ok, f"found {len(rows)}"))
    if not n_ok:
        return False, detail

    leis = {r["lei"] for r in rows}
    types = {r["signal_type"] for r in rows}
    one_obligor = len(leis) == 1
    three_types = types == {"adverse_media", "warn_notice", "spread_widening"}
    detail.append(("all three signals sit on ONE obligor", one_obligor,
                    f"{sorted(leis)}"))
    detail.append(("the three are of three DISTINCT signal types",
                    three_types, f"{sorted(types)}"))

    lei = rows[0]["lei"]
    sector = sector_of(cur, lei)
    thresholds = escalation_threshold_rows(cur)

    total = 0.0
    all_sub = True
    for r in rows:
        weight = weight_for(cur, r["signal_type"], sector)
        weighted_score = r["severity"] * weight
        total += weighted_score
        sub = is_subthreshold({"weighted_score": weighted_score}, thresholds)
        all_sub = all_sub and sub
        detail.append((
            f"{r['signal_id']} individually AT OR BELOW the daily-sweep "
            f"threshold (is_subthreshold, imported)", sub,
            f"severity {r['severity']} x weight {weight} ({sector}) = "
            f"{weighted_score:.4f}"))

    breaches = not is_subthreshold({"weighted_score": total}, thresholds)
    detail.append((
        "the SUM of the three breaches the daily-sweep threshold "
        "(is_subthreshold, imported, negated)", breaches,
        f"sum = {total:.4f}"))

    ok = one_obligor and three_types and all_sub and breaches
    return ok, detail


# ==========================================================================
# 3. Score distribution — the wave's one genuine empirical question
# ==========================================================================

#: The coefficient of quartile deviation, (Q3-Q1)/(Q3+Q1). Chosen over the
#: coefficient of variation because CQD is a spread-relative-to-CENTER
#: statistic built from robust order statistics (Q1/Q3), not mean/stdev --
#: so a couple of extreme obligors (the real, measured shape here: two or
#: three obligors carry many more real 8-K/adverse-media events than the
#: rest) inflate CV without making the MIDDLE of the distribution any less
#: bunched, whereas CQD asks the more direct question §F actually poses:
#: does the typical (middle-50%) obligor's score sit close to every other
#: typical obligor's, or does it genuinely differ?
#:
#: 0.15 is a floor chosen independently of this run's outcome: a genuinely
#: clustered set (every obligor's score within a few percent of the median)
#: produces a CQD under 0.05; 0.15 requires the middle half of obligors to
#: span at least 15% of (Q3+Q1) -- comfortably discriminating "clustered"
#: from "varies" without being tuned to land just under whatever this run
#: happens to measure.
QCD_CLUSTER_FLOOR = 0.15


def composite_scores(cur) -> dict[str, float]:
    """{lei: sum(severity * weight) over every signal_event row}, for every
    `is_anchor` obligor -- the Postgres set, not an assumed 50. Uses
    severity and weight EXACTLY as loaded, with no decay applied: applying
    decay is the Evaluate operator's job (design §8, explicitly out of
    scope here), and the escalation_threshold rows are themselves stated on
    this same undecayed scale (their own rationale text says so). A
    per-obligor score that used `gdelt_mention` row counts instead of the
    already-loaded `signal_event.severity` would silently UNDO the
    Celanese down-weight baked into that severity at generation time; this
    reads severity as loaded, so the down-weight is honoured for free.
    """
    cur.execute(f'SELECT lei, sic FROM "{S}".legal_entity WHERE is_anchor')
    sector_by_lei = {lei: sector_for(sic) for lei, sic in cur.fetchall()}

    cur.execute(f'SELECT signal_type, sector, weight FROM "{S}".signal_weight')
    weight = {(st, sec): float(w) for st, sec, w in cur.fetchall()}

    scores = {lei: 0.0 for lei in sector_by_lei}
    cur.execute(f'SELECT lei, signal_type, severity FROM "{S}".signal_event')
    for lei, st, sev in cur.fetchall():
        sector = sector_by_lei.get(lei)
        if sector is None:
            continue  # not one of the 50 anchors -- should not occur; see check below
        key = (st, sector)
        if key not in weight:
            raise AssertionError(f"no signal_weight row for {key}")
        scores[lei] += float(sev) * weight[key]
    return scores


def distribution_report(scores: dict[str, float]) -> dict:
    vals = sorted(scores.values())
    n = len(vals)
    q1, q2, q3 = statistics.quantiles(vals, n=4)
    groups = [0, 0, 0, 0]
    for v in vals:
        if v <= q1:
            groups[0] += 1
        elif v <= q2:
            groups[1] += 1
        elif v <= q3:
            groups[2] += 1
        else:
            groups[3] += 1
    qcd = (q3 - q1) / (q3 + q1) if (q3 + q1) else 0.0
    return {
        "n": n, "min": vals[0], "q1": q1, "median": q2, "q3": q3,
        "max": vals[-1], "quartile_counts": groups, "qcd": qcd,
    }


# ==========================================================================
# 4. Delta anchoring
# ==========================================================================

def prior_observation_leis() -> Counter:
    q = f"""
    SELECT ?lei FROM <{L}> WHERE {{
      ?p a <{EX}PriorObservation> .
      ?p <{EX}signalAbout> ?o .
      ?o <{EX}lei> ?lei .
    }}
    """
    return Counter(r["lei"]["value"] for r in bindings(q))


def delta_anchoring_check(cur) -> tuple[bool, str]:
    counts = prior_observation_leis()
    cur.execute(f'SELECT lei FROM "{S}".legal_entity WHERE is_anchor')
    anchors = {r[0] for r in cur.fetchall()}
    fluree_leis = set(counts)

    missing = anchors - fluree_leis          # anchor with NO prior point
    extra = fluree_leis - anchors            # a prior point on a non-anchor
    multi = {lei: c for lei, c in counts.items() if c != 1}  # 0 or 2+, per-lei

    ok = len(anchors) == 50 and not missing and not extra and not multi
    detail = (
        f"{len(anchors)} is_anchor obligor(s) in Postgres; "
        f"{len(fluree_leis)} distinct obligor(s) carry a PriorObservation "
        f"in Fluree; missing={sorted(missing)}; extra={sorted(extra)}; "
        f"obligors with != 1 prior point={multi}"
    )
    return ok, detail


# ==========================================================================
# 5. WARN resolution quality — both directions, one check
# ==========================================================================

def warn_resolution_check(cur) -> tuple[bool, str]:
    cur.execute(f'SELECT verdict, lei FROM "{S}".warn_match')
    rows = cur.fetchall()
    resolved_obligors = {lei for verdict, lei in rows if verdict == "resolved"}
    ambiguous_rows = [1 for verdict, _ in rows if verdict == "ambiguous"]

    resolved_ok = len(resolved_obligors) >= 3
    ambiguous_ok = len(ambiguous_rows) >= 1
    ok = resolved_ok and ambiguous_ok

    detail = (
        f"{len(resolved_obligors)} distinct obligor(s) resolved "
        f"({'ok' if resolved_ok else 'FAIL'}, >= 3) AND "
        f"{len(ambiguous_rows)} pair(s) remain ambiguous "
        f"({'ok' if ambiguous_ok else 'FAIL'}, >= 1) -- a table of only "
        f"true positives would pass the first half and fail the second"
    )
    return ok, detail



#: §F's GDELT clause is *"~200 GDELT mentions ... weighted toward a handful of
#: names."* Only the count half was ever gated (`conditions.py`, 951 >= 200);
#: the concentration half was checked by nothing until 2026-08-21. That gap is
#: not theoretical: §10.1 records that the FIRST sweep's 77.8% top-5
#: concentration was *entirely a noise artifact* — 1,809 of 2,760 mentions
#: belonged to Bognor Regis, a wrestler and a vulture. A concentration figure
#: that nothing recomputes is exactly the shape of claim this wave kept getting
#: wrong.
#:
#: FLOOR, and why it is not a token gate. 30 obligors carry mentions, so a
#: UNIFORM spread would put the top five at 5/30 = 16.7%. 0.40 is 2.4x that,
#: and it sits 26 points below the live 66.5% — a real gate with real margin in
#: both directions, boundary-tested against synthetic flat distributions.
GDELT_TOP_N = 5
GDELT_CONCENTRATION_FLOOR = 0.40
#: ...and "a handful of NAMES", not one name. A single obligor holding half the
#: corpus is concentrated but is not what §F describes, and it is the shape a
#: fresh name-collision would produce.
GDELT_SINGLE_NAME_CEILING = 0.50


def gdelt_concentration_check(cur) -> tuple[bool, list[tuple[str, bool, str]]]:
    """§F: mentions "weighted toward a handful of names" — recomputed from
    `gdelt_mention` AS LOADED, in both directions.

    Three sub-checks, because the count is not the condition:

    1. the top-5 obligors hold at least `GDELT_CONCENTRATION_FLOOR` of the
       corpus (there IS a head);
    2. no single obligor holds `GDELT_SINGLE_NAME_CEILING` or more (the head
       is a handful of names, not one);
    3. the concentration SURVIVES removing every down-weighted mention — the
       rows `coverage[lei].precision_review` flagged as mixed precision. This
       is the closest the store can come to "the head is real coverage, not a
       name-collision artifact", and it is the sub-check the pre-fix sweep
       would have failed on: its head was three obligors whose mentions were
       ~100% off-topic.
    """
    cur.execute(f'SELECT lei, COUNT(*), '
                f'COUNT(*) FILTER (WHERE down_weight_factor IS NULL) '
                f'FROM "{S}".gdelt_mention GROUP BY lei')
    rows = cur.fetchall()
    all_counts = sorted((n for _, n, _ in rows), reverse=True)
    clean_counts = sorted((c for _, _, c in rows if c), reverse=True)
    return _concentration_verdict(all_counts, clean_counts)


def _concentration_verdict(all_counts: list[int], clean_counts: list[int]
                           ) -> tuple[bool, list[tuple[str, bool, str]]]:
    """Split out from the query so the thresholds can be exercised against
    synthetic distributions without touching the store."""
    total = sum(all_counts)
    if not total:
        return False, [("gdelt_mention is empty", False, "no rows to measure")]

    top_share = sum(all_counts[:GDELT_TOP_N]) / total
    single_share = all_counts[0] / total
    clean_total = sum(clean_counts)
    clean_share = (sum(clean_counts[:GDELT_TOP_N]) / clean_total
                   if clean_total else 0.0)

    head_ok = top_share >= GDELT_CONCENTRATION_FLOOR
    spread_ok = single_share < GDELT_SINGLE_NAME_CEILING
    clean_ok = clean_share >= GDELT_CONCENTRATION_FLOOR
    uniform = GDELT_TOP_N / len(all_counts) if all_counts else 0.0

    detail = [
        (f"top-{GDELT_TOP_N} of {len(all_counts)} obligors hold "
         f"{top_share:.2%} of {total} mentions", head_ok,
         f"floor {GDELT_CONCENTRATION_FLOOR:.0%}; a uniform spread over "
         f"{len(all_counts)} obligors would give {uniform:.2%}"),
        (f"largest single obligor holds {single_share:.2%}", spread_ok,
         f"ceiling {GDELT_SINGLE_NAME_CEILING:.0%} — \"a handful of names\", "
         f"not one name"),
        (f"concentration survives dropping down-weighted mentions: "
         f"{clean_share:.2%} of {clean_total}", clean_ok,
         "the head must be real coverage; §10.1's pre-fix head was ~100% "
         "off-topic and would fail here"),
    ]
    return head_ok and spread_ok and clean_ok, detail

# ==========================================================================
def main() -> int:
    print("SURVEILLANCE VALIDATOR — cascade, composite, distribution, "
          "anchoring, WARN resolution, recomputed from the LOADED stores "
          "(not a generator flag)\n")

    with pg_connect() as conn, conn.cursor() as cur:
        try:
            cur.execute(f'SELECT 1 FROM "{S}".signal_event LIMIT 1')
        except Exception as exc:  # noqa: BLE001
            print(f"  [SKIP] signal_event absent -- Wave 11b has not "
                  f"loaded ({type(exc).__name__})")
            return 0
        conn.rollback()

        print("  1. CASCADE COMPLETENESS -- engineered Item 2.04 walked "
              "via signalAbout in Fluree, checked EXACTLY against Postgres "
              "facility / collateral_pledge / drawdown\n")
        cascade_ok, cascade_detail = cascade_completeness(cur)
        for label, ok, info in cascade_detail:
            print(f"    [{'ok  ' if ok else 'FAIL'}] {label} -- {info}")
        print(f"\n    [{'PASS' if cascade_ok else 'FAIL'}] cascade reaches "
              f"the facility, the collateral pledge AND the drawdown\n")

        print("  2. THE COMPOSITE CASE -- weighted score recomputed from "
              "signal_weight / escalation_threshold AS LOADED; is_subthreshold "
              "IMPORTED from generators.narrative_wave11b, not reimplemented\n")
        composite_ok, composite_detail = composite_case_check(cur)
        for label, ok, info in composite_detail:
            print(f"    [{'ok  ' if ok else 'FAIL'}] {label} -- {info}")
        print(f"\n    [{'PASS' if composite_ok else 'FAIL'}] each signal "
              f"individually subthreshold AND their sum breaches escalation\n")

        print("  3. SCORE DISTRIBUTION -- composite warning score "
              "(sum of severity x signal_weight) for all 50 obligors, "
              "measured, not designed (design §7.1)\n")
        scores = composite_scores(cur)
        n_ok = len(scores) == 50
        print(f"    [{'ok  ' if n_ok else 'FAIL'}] scores computed for "
              f"{len(scores)} obligor(s) (target: 50)")
        report = distribution_report(scores)
        print(f"    min={report['min']:.4f}  Q1={report['q1']:.4f}  "
              f"median={report['median']:.4f}  Q3={report['q3']:.4f}  "
              f"max={report['max']:.4f}")
        print(f"    quartile counts (rank-based, of {report['n']}): "
              f"{report['quartile_counts']}")
        print(f"    coefficient of quartile deviation (Q3-Q1)/(Q3+Q1) = "
              f"{report['qcd']:.4f}  (floor for \"varies rather than "
              f"clusters\": {QCD_CLUSTER_FLOOR})")
        dist_ok = n_ok and report["qcd"] >= QCD_CLUSTER_FLOOR
        if dist_ok:
            print(f"\n    [PASS] scores VARY -- the middle half of "
                  f"obligors spans {report['qcd']:.1%} of the (Q3+Q1) "
                  f"scale, well clear of the {QCD_CLUSTER_FLOOR:.0%} floor. "
                  f"The count is not standing in for the condition here: "
                  f"the shape is right-skewed (a few obligors carry far "
                  f"more real 8-K/adverse-media volume than most), but the "
                  f"typical obligor's score still differs materially from "
                  f"the next typical obligor's, which is what \"vary "
                  f"rather than cluster\" asks for.\n")
        else:
            print(f"\n    [FAIL] scores CLUSTER -- reported honestly, not "
                  f"adjusted to pass. §F's distribution condition is not "
                  f"satisfiable by the data as loaded; the count of ~1,600 "
                  f"signal events does not stand in for it.\n")

        print("  4. DELTA ANCHORING -- every is_anchor obligor carries "
              "EXACTLY ONE PriorObservation ledger point\n")
        anchor_ok, anchor_detail = delta_anchoring_check(cur)
        print(f"    {anchor_detail}")
        print(f"\n    [{'PASS' if anchor_ok else 'FAIL'}] delta anchoring "
              f"holds for every obligor\n")

        print("  5. WARN RESOLUTION QUALITY -- both directions, one check\n")
        warn_ok, warn_detail = warn_resolution_check(cur)
        print(f"    {warn_detail}")
        print(f"\n    [{'PASS' if warn_ok else 'FAIL'}] WARN resolution "
              f"stays genuinely lossy\n")

        print("  6. GDELT CONCENTRATION -- \u00a7F's \"weighted toward a "
              "handful of names\", recomputed from gdelt_mention as loaded. "
              "Gated here for the first time on 2026-08-21; before that only "
              "the COUNT half of that clause was checked\n")
        conc_ok, conc_detail = gdelt_concentration_check(cur)
        for label, ok, info in conc_detail:
            print(f"    [{'ok  ' if ok else 'FAIL'}] {label} -- {info}")
        print(f"\n    [{'PASS' if conc_ok else 'FAIL'}] mentions are "
              f"weighted toward a handful of names, and the head is real "
              f"coverage\n")

    failed = not (cascade_ok and composite_ok and dist_ok and anchor_ok
                  and warn_ok and conc_ok)
    print(f"  {'PASS' if not failed else 'FAIL'} -- cascade "
          f"{'ok' if cascade_ok else 'FAIL'}, composite "
          f"{'ok' if composite_ok else 'FAIL'}, distribution "
          f"{'ok' if dist_ok else 'FAIL'}, anchoring "
          f"{'ok' if anchor_ok else 'FAIL'}, WARN resolution "
          f"{'ok' if warn_ok else 'FAIL'}, GDELT concentration "
          f"{'ok' if conc_ok else 'FAIL'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
