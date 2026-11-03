#!/usr/bin/env python3
"""Pure tests for Wave 11b signal selection.

Two traps are pinned here, both measured in `docs/wave11b-design.md` §1.

PREFIX MATCHING, NOT SUBSTRING. EDGAR renders the items field as a
comma-separated list like "5.02,9.01" or "Item 2.04". A substring test for
"2.04" also matches "12.04" if EDGAR ever renders one, and a test for "4.01"
matches "14.01". Match on the code as a token, anchored.

WINDOW BOUNDARIES ARE INCLUSIVE AND MEASURED. The 24-month window is a
recorded decision (D1), not a rolling `today - 730 days`. A rolling window
makes the loaded dataset depend on the day the loader ran, which is exactly
the instability Wave 11a diagnosed wrongly as "index movement".

    uv run validators/test_signals.py
"""

from __future__ import annotations

import sys
from datetime import date

from generators.fetch_8k_items import (ITEM_CODES, WINDOW_END, WINDOW_START,
                                       in_window, matching_items)
from generators.generate_signals import (DECAY_DAYS, SIGNAL_TYPES,
                                         _phase_for_trend_event,
                                         _rollup_to_obligor)
from generators.generate_trend_deltas import pct_change
from generators.narrative_wave11b import (CASCADE_LEI, cascade_event,
                                          composite_case, is_subthreshold)


def check_items() -> list[tuple[str, bool]]:
    return [
        ("a bare code matches", matching_items("2.04") == ["2.04"]),
        ("a comma list matches each code",
         sorted(matching_items("5.02,9.01")) == ["5.02"]),
        ("two wanted codes both match",
         sorted(matching_items("1.01,2.03")) == ["1.01", "2.03"]),
        ("whitespace is tolerated", matching_items(" 2.04 , 9.01 ") == ["2.04"]),
        ("an unwanted code yields nothing", matching_items("9.01") == []),
        ("None yields nothing", matching_items(None) == []),
        ("empty yields nothing", matching_items("") == []),
        # The trap: substring matching would return 2.04 here.
        ("12.04 does NOT match 2.04", matching_items("12.04") == []),
        ("14.01 does NOT match 4.01", matching_items("14.01") == []),
        ("all six codes are wanted", len(ITEM_CODES) == 6),
    ]


def check_window() -> list[tuple[str, bool]]:
    return [
        ("window start is the recorded constant", WINDOW_START == "2024-08-19"),
        ("window end is the recorded constant", WINDOW_END == "2026-08-19"),
        ("start boundary is inclusive", in_window("2024-08-19") is True),
        ("end boundary is inclusive", in_window("2026-08-19") is True),
        ("a day before start is out", in_window("2024-08-18") is False),
        ("a day after end is out", in_window("2026-08-20") is False),
        ("a mid-window date is in", in_window("2025-06-01") is True),
        # Tupperware, Container Store and Murphy Oil are the three real
        # in-window Item 2.04 obligors (design §1.2). If any falls out of the
        # window, §F's ">= 2 obligors" fails and the wave fails with it.
        ("Tupperware 2.04 is in window", in_window("2024-09-18") is True),
        ("Murphy Oil 2.04 (2024) is in window", in_window("2024-12-06") is True),
        ("Container Store 2.04 is in window", in_window("2024-12-23") is True),
        ("Murphy Oil 2.04 (2026) is in window", in_window("2026-01-08") is True),
    ]


def _returns_without_raising(fn, *args) -> bool:
    try:
        fn(*args)
        return True
    except Exception:
        return False


def check_pct_change() -> list[tuple[str, bool]]:
    return [
        ("a normal rise computes", pct_change(110.0, 100.0) == 10.0),
        ("a normal fall computes", pct_change(90.0, 100.0) == -10.0),
        ("no change is zero", pct_change(100.0, 100.0) == 0.0),
        # The trap: `if not prior: continue` would drop these rows silently.
        ("a zero prior yields None, not an exception",
         pct_change(50.0, 0.0) is None),
        ("a missing prior yields None", pct_change(50.0, None) is None),
        ("a zero prior does NOT raise",
         _returns_without_raising(pct_change, 50.0, 0.0)),
        # A negative prior is real in XBRL: accumulated deficit, net loss.
        # Dividing by abs(prior) keeps the SIGN OF THE MOVE, not the sign of
        # the base: -100 -> -50 is a loss halving, which is +50%, not -50%.
        # Divide by `prior` itself and every negative-base series silently
        # reports its improvements as deteriorations.
        ("a negative prior still computes",
         pct_change(-50.0, -100.0) == 50.0),
        ("a negative base that worsens is negative",
         pct_change(-150.0, -100.0) == -50.0),
    ]


def check_decay() -> list[tuple[str, bool]]:
    # Spec §E. An 8-K never decays: it is a filed fact, and its relevance is
    # bounded by supersession rather than by time. That None is load-bearing,
    # not a missing value — §7.7 of the whitepaper separates half-life from
    # supersession precisely for this case.
    return [
        ("every signal type has a decay entry",
         set(DECAY_DAYS) == set(SIGNAL_TYPES)),
        ("adverse media decays in ~7 days", DECAY_DAYS["adverse_media"] == 7),
        ("spread widening decays in ~1 day", DECAY_DAYS["spread_widening"] == 1),
        ("WARN decays in ~180 days", DECAY_DAYS["warn_notice"] == 180),
        ("trend deltas decay in ~90 days", DECAY_DAYS["trend_delta"] == 90),
        ("an 8-K event does NOT decay", DECAY_DAYS["8k_event"] is None),
        ("five signal types", len(SIGNAL_TYPES) == 5),
    ]


def _raises(fn, *args) -> bool:
    try:
        fn(*args)
        return False
    except AssertionError:
        return True


def check_phase_for_trend_event() -> list[tuple[str, bool]]:
    # Fix round 2. `_phase_for_trend_event` assigns a spread_widening
    # candidate's phase from ground truth (real crossing `asserted_at`
    # dates, DIVERGENCES windows) rather than from which detector fired --
    # the pre-fix code labelled every rolling-trend candidate "anticipation"
    # unconditionally, which is exactly what case 2 below would have caught:
    # a post-crossing event asserted "anticipation" against the old code,
    # "confirmation" against this one.
    single_crossing = {"OBL1": [{"asserted_at": date(2026, 3, 31)}]}

    multi_crossing = {"OBL3": [{"asserted_at": date(2024, 1, 1)},
                                {"asserted_at": date(2024, 12, 1)}]}

    divergence_windows = {"inst-div": [(date(2026, 3, 1), date(2026, 3, 10))]}

    return [
        # 1. Strictly before the nearest crossing -> anticipation.
        ("strictly before the crossing is anticipation",
         _phase_for_trend_event("inst-1", date(2026, 3, 2), "OBL1",
                                 {}, single_crossing) == "anticipation"),

        # 2. At OR after the nearest crossing -> confirmation. This is the
        # case that actually catches the original defect: pre-fix, this
        # event would have been unconditionally "anticipation".
        ("after the crossing is confirmation, not anticipation",
         _phase_for_trend_event("inst-1", date(2026, 4, 5), "OBL1",
                                 {}, single_crossing) == "confirmation"),

        # 3. A DIVERGENCES window wins even when the event also falls
        # before OR after a real crossing for that obligor -- pins the
        # priority order explicitly; nothing in the 26-row dataset forces
        # this precedence to be exercised at the boundary.
        ("divergence window wins over a crossing that is still ahead",
         _phase_for_trend_event(
             "inst-div", date(2026, 3, 5), "OBL2", divergence_windows,
             {"OBL2": [{"asserted_at": date(2026, 3, 31)}]}) == "divergence"),
        ("divergence window wins over a crossing already in the past",
         _phase_for_trend_event(
             "inst-div", date(2026, 3, 5), "OBL2", divergence_windows,
             {"OBL2": [{"asserted_at": date(2026, 2, 1)}]}) == "divergence"),

        # 4. No crossing anywhere in the chain -> unattributed, not
        # silently dropped and not mislabelled as either phase.
        ("no crossings at all is unattributed",
         _phase_for_trend_event("inst-2", date(2026, 5, 1), "OBL-NONE",
                                 {}, {}) == "unattributed"),

        # 5. Multiple crossings: the NEAREST one governs, not the first or
        # the earliest. Fixture is discriminating on purpose -- the event is
        # 329 days from the 2024-01-01 crossing (which would say
        # "confirmation") and 6 days from the 2024-12-01 crossing (which
        # says "anticipation"); only a correct nearest-crossing selection
        # returns "anticipation" here.
        ("the nearer crossing governs, not the earlier one",
         _phase_for_trend_event("inst-3", date(2024, 11, 25), "OBL3",
                                 {}, multi_crossing) == "anticipation"),

        # 6. THE BOUNDARY: an event dated EXACTLY on the crossing's own
        # asserted_at. No row in the loaded artifact hits this, so it was
        # previously unverified by data, hand inspection, or anything
        # downstream. Pinned: the announcement date itself is
        # "confirmation" (`<`, not `<=`) -- anticipation is by definition
        # something that precedes the fact, and asserted_at IS the date the
        # fact became known, not a date still ahead of it.
        ("exactly on asserted_at is confirmation, not anticipation",
         _phase_for_trend_event("inst-1", date(2026, 3, 31), "OBL1",
                                 {}, single_crossing) == "confirmation"),
    ]


def check_rollup_to_obligor() -> list[tuple[str, bool]]:
    # Fix round 2. `_rollup_to_obligor` did not exist pre-fix -- every one
    # of these cases fails outright (ImportError, or 2 rows instead of 1)
    # against the old code, which emitted one row per instrument.
    dup_candidates = [
        {"lei": "OBL5", "observed_at": "2026-01-01", "severity": 0.4,
         "source_ref": {"instrument_id": "inst-a", "phase": "anticipation",
                         "rolling_mean_delta_bp": 10.0, "sector": "X",
                         "threshold_bp": 100.0, "idiosyncratic_bp": 20.0},
         "provenance": "synthetic — engineered"},
        {"lei": "OBL5", "observed_at": "2026-01-01", "severity": 0.7,
         "source_ref": {"instrument_id": "inst-b", "phase": "anticipation",
                         "rolling_mean_delta_bp": 15.0, "sector": "X",
                         "threshold_bp": 100.0, "idiosyncratic_bp": 25.0},
         "provenance": "synthetic — engineered"},
    ]
    dup_result = _rollup_to_obligor(dup_candidates)
    dup_row = dup_result[0] if dup_result else {}

    singleton = [
        {"lei": "OBL6", "observed_at": "2026-02-02", "severity": 0.55,
         "source_ref": {"instrument_id": "inst-c", "phase": "confirmation",
                         "delta_bp": 60.0, "sector": "Y",
                         "threshold_bp": 100.0, "market_oas_bp": 200.0},
         "provenance": "public"},
    ]
    singleton_result = _rollup_to_obligor(singleton)
    singleton_row = singleton_result[0] if singleton_result else {}

    # 9. The latent fragility named in fix round 2: a confirm-detector
    # candidate and a trend-detector candidate sharing one
    # (lei, observed_at, phase) key must NOT merge silently -- that would
    # drop one detector's distinct fields with no trace. It must raise.
    mixed_kind_candidates = [
        {"lei": "OBL7", "observed_at": "2026-03-03", "severity": 0.5,
         "source_ref": {"instrument_id": "inst-d", "phase": "confirmation",
                         "delta_bp": 60.0, "sector": "Z",
                         "threshold_bp": 100.0, "market_oas_bp": 200.0},
         "provenance": "public"},
        {"lei": "OBL7", "observed_at": "2026-03-03", "severity": 0.6,
         "source_ref": {"instrument_id": "inst-e", "phase": "confirmation",
                         "rolling_mean_delta_bp": 20.0, "sector": "Z",
                         "threshold_bp": 100.0, "idiosyncratic_bp": 30.0},
         "provenance": "synthetic — engineered"},
    ]

    return [
        # 7. Two candidates sharing (lei, observed_at, phase): one row,
        # max-severity fields retained, both instrument_ids present, the
        # collapsed count recorded.
        ("duplicate key collapses to exactly one row",
         len(dup_result) == 1),
        ("collapsed row keeps the max-severity candidate's severity",
         dup_row.get("severity") == 0.7),
        ("collapsed row keeps the max-severity candidate's own detail",
         dup_row.get("source_ref", {}).get("rolling_mean_delta_bp") == 15.0),
        ("both instrument_ids survive the collapse",
         sorted(dup_row.get("source_ref", {}).get("instrument_ids", []))
         == ["inst-a", "inst-b"]),
        ("collapsed_row_count records how many candidates merged",
         dup_row.get("source_ref", {}).get("collapsed_row_count") == 2),
        ("the singular instrument_id key is gone after rollup",
         "instrument_id" not in dup_row.get("source_ref", {})),

        # 8. A singleton candidate passes through unchanged -- not
        # accidentally collapsed with anything else.
        ("a singleton candidate yields exactly one row",
         len(singleton_result) == 1),
        ("a singleton's severity is untouched",
         singleton_row.get("severity") == 0.55),
        ("a singleton's instrument_ids is a 1-element list of its own id",
         singleton_row.get("source_ref", {}).get("instrument_ids")
         == ["inst-c"]),
        ("a singleton's collapsed_row_count is 1, not merged with anything",
         singleton_row.get("source_ref", {}).get("collapsed_row_count") == 1),

        # 9. Cross-detector collision on one key raises rather than
        # silently dropping one detector's fields.
        ("a cross-detector collision on one key raises, not merges",
         _raises(_rollup_to_obligor, mixed_kind_candidates)),
    ]


def check_composite() -> list[tuple[str, bool]]:
    case = composite_case()
    sigs = case["signals"]
    thr = case["threshold"]
    return [
        ("the composite case has exactly three signals", len(sigs) == 3),
        ("all three are individually subthreshold",
         all(is_subthreshold(s, thr) for s in sigs)),
        ("the three are of distinct signal types",
         len({s["signal_type"] for s in sigs}) == 3),
        ("their combined score breaches the threshold",
         sum(s["weighted_score"] for s in sigs) > thr),
        # The condition, not the count: a composite that breaches because one
        # signal was already over the line proves nothing.
        ("no single signal breaches on its own",
         all(s["weighted_score"] <= thr for s in sigs)),
        # is_subthreshold must accept the same threshold shape surveillance.py
        # (Task 12) will hand it -- the full policy-row list, not only the
        # bare number composite_case() happens to also expose as case["threshold"].
        ("is_subthreshold resolves a policy-row list the same as the bare "
         "number",
         all(is_subthreshold(s, [
             {"kind": "escalation", "intent": "credit-committee-referral",
              "threshold_score": 999.0},
             {"kind": "escalation", "intent": "daily-sweep",
              "threshold_score": thr},
         ]) for s in sigs)),
        # The composite sits on a different obligor than the cascade, so a
        # defect in one cannot mask a defect in the other.
        ("the composite obligor is not the cascade anchor",
         case["lei"] != CASCADE_LEI),
        # Fix round 1, MINOR: the cascade block carries a top-level
        # provenance key; composite lacked one (each signals[i] was already
        # labelled, but the block itself was not) -- schema asymmetry.
        ("the composite block itself is labelled synthetic — engineered",
         case["provenance"] == "synthetic — engineered"),
    ]


def check_cascade() -> list[tuple[str, bool]]:
    event = cascade_event()
    targets = event["signal_about"]
    by_type = {}
    for t in targets:
        by_type.setdefault(t["target_type"], []).append(t["target_id"])
    return [
        ("the cascade is asserted against the resolved anchor",
         event["lei"] == CASCADE_LEI),
        ("the cascade event is Item 2.04 (acceleration / triggering event)",
         event["item"] == "2.04"),
        ("the cascade is labelled synthetic — engineered, never public",
         event["provenance"] == "synthetic — engineered"),
        ("signalAbout reaches exactly one facility",
         len(by_type.get("Facility", [])) == 1),
        ("signalAbout reaches at least one collateral pledge",
         len(by_type.get("CollateralPledge", [])) >= 1),
        ("signalAbout reaches at least one drawdown",
         len(by_type.get("Drawdown", [])) >= 1),
        # The design's named anchor -- if this ever resolves to someone
        # else, something upstream changed and this is the tripwire.
        ("the resolved anchor's legal name mentions Avis",
         "AVIS" in event["legal_name"].upper()),
    ]


def check_import_without_postgres() -> list[tuple[str, bool]]:
    """Fix round 1. This is the invariant the whole lazy-resolution fix
    exists to protect: `generators.narrative_wave11b` must be IMPORTABLE,
    and its pure predicate `is_subthreshold` CALLABLE, with no live Postgres
    connection -- because Task 12's `validators/surveillance.py` must import
    `is_subthreshold` rather than reimplement it (see that module's
    docstring, and `validators/conditions.py:32`), and any friction on
    import creates quiet pressure to copy the four-line predicate instead.

    Simulates a Postgres outage by monkeypatching `ccf.config.pg_connect` to
    raise, force-reimporting the module fresh (it is already cached in
    `sys.modules` from this file's own top-of-file import against a live
    DB), and proving both the import and an `is_subthreshold` call succeed
    without ever calling the broken `pg_connect`. `CASCADE_LEI` -- which
    DOES need Postgres -- is checked separately to confirm it still raises
    rather than silently returning a stale or wrong value.
    """
    import importlib
    import sys as _sys

    import ccf.config as _config

    mod_name = "generators.narrative_wave11b"
    saved_module = _sys.modules.pop(mod_name, None)
    original_pg_connect = _config.pg_connect

    def _boom(*_a, **_k):
        raise RuntimeError("simulated Postgres outage")

    _config.pg_connect = _boom
    import_ok = False
    subthreshold_ok = False
    cascade_lei_raises = False
    try:
        fresh = importlib.import_module(mod_name)
        import_ok = True
        subthreshold_ok = fresh.is_subthreshold({"weighted_score": 0.1}, 0.3) is True
        try:
            fresh.CASCADE_LEI
        except RuntimeError:
            cascade_lei_raises = True
    finally:
        _config.pg_connect = original_pg_connect
        _sys.modules.pop(mod_name, None)
        if saved_module is not None:
            _sys.modules[mod_name] = saved_module
        else:
            importlib.import_module(mod_name)

    return [
        ("the module imports with no live Postgres connection",
         import_ok),
        ("is_subthreshold is callable immediately after that import",
         subthreshold_ok),
        ("CASCADE_LEI still raises (not silently wrong) when the DB is down",
         cascade_lei_raises),
    ]


def main() -> int:
    results = (check_items() + check_window() + check_pct_change()
               + check_decay() + check_phase_for_trend_event()
               + check_rollup_to_obligor() + check_composite()
               + check_cascade() + check_import_without_postgres())
    failed = [(n, ok) for n, ok in results if not ok]
    for name, ok in results:
        print(f"  [{'ok  ' if ok else 'FAIL'}] {name}")
    print(f"\n  {len(results) - len(failed)}/{len(results)} cases behave as specified\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
