#!/usr/bin/env python3
"""Wave 17 Task 10 -- generate the ORDINARY 18-month transaction population.

`aml-typology-match` needs a background of unremarkable, party-to-party
payment activity BEFORE Task 11 injects the ~30 engineered structuring,
funnel-account, shell-company and trade-based-laundering cases into the
same artifact (`sources/screening/wave17_transactions.json`). Build order
matters here: this generator runs first and knows nothing about the
typologies it is meant to sit alongside, so the noise it produces is
genuine noise rather than something shaped around the cases that will
later be laid on top of it.

## Why the anti-pattern check exists

TYP-STRUCT's own parameters (`sources/screening/wave17_typologies.json`)
are threshold_usd=10000, band_low=0.8, band_high=0.99, min_transactions=4,
window_days=10 -- i.e. "4+ transactions of $8,000-$9,900 inside 10 days"
IS the structuring shape Task 11 will plant. If this generator's random
draws ever happened to produce that shape for some party by chance, the
engineered cases would not be distinguishable from background and
precision would not be measurable. So every party's drawn batch is
checked against that exact shape before it is accepted, and a batch that
trips it is resampled -- not left for the test to discover later.

## The case-exclusion ruling (controller, Task 10 brief)

`validators/test_aml_typology.py::test_ordinary_population_does_not_already_contain_the_patterns`
reads this artifact and asserts the ordinary population is clear of the
TYP-STRUCT shape. Task 11 appends engineered cases -- built to exhibit
exactly that shape -- to this SAME artifact, so a literal re-read of the
test's own text would start failing the moment Task 11 succeeds, and the
better Task 11 does its job the harder it would break. The ruling: BOTH
the test and this generator's own verification pass exclude every
`txn_id` that appears in any case's `txn_ids` in
`sources/screening/wave17_cases.json` before applying the check, treating
a missing file (true right now -- Task 11 has not run yet) as an empty
exclusion set. `load_case_excluded_txn_ids()` and
`find_structuring_shaped_party()` below are the shared implementation --
the test imports both from this module so the two checks can never drift
apart. At this point in the plan the exclusion set is empty and this
generator's own output is everything the check sees, so the check is
exactly as strict as the brief's literal text; after Task 11 it stays
correct because it now judges the ordinary slice only, which is what its
docstring always said it was checking.

## This script refuses to run once Task 11 has injected

`main()` rewrites `sources/screening/wave17_transactions.json` with the
ordinary rows ONLY. Task 11 appends its engineered cases to that same
file, so an unguarded re-run here deletes the injected block and leaves
every case txn_id in `wave17_cases.json` dangling -- while printing
"Wrote 4095 transactions" and exiting 0. `injected_block_would_be_destroyed()`
below closes that: if `wave17_cases.json` exists, this script refuses,
names `generators/inject_typology_cases.py` as the run that rebuilds both
populations, and exits non-zero. `--regenerate-base` is the deliberate
override. `generate_transactions()` itself is untouched by the guard --
the injector calls it directly, which is how it regenerates this base
in-process.

## Determinism

`SEED` is a fixed constant. All randomness flows through one seeded
`random.Random(SEED)`, consumed in a fixed, sorted order (party_ids drawn
from `wave17_parties.json`, sorted ascending). `txn_id` is assigned only
after the full batch is generated, from a SORTED, content-derived
ordering (by `value_date`, `from_party`, `to_party`, `channel`,
`amount_usd`, with a hash of the full record as a final tiebreaker) --
never from the order transactions happened to be drawn in, which is the
positional-identity defect class this repo already has five recorded
instances of. Re-running this script must produce a byte-identical
`sources/screening/wave17_transactions.json`
(`git diff --exit-code` after a second run is the proof).

## Amounts and dates

Amounts are heavy-tailed: ~80% small (uniform $50-$3,000), ~15% medium
($3,000-$20,000 -- this band naturally overlaps the TYP-STRUCT band, which
is why the anti-pattern check exists), ~4% large ($20,000-$150,000) and
~1% very large ($150,000-$2,000,000). `asset_purchase` transactions are
drawn from a separate, capped range ($2,000-$45,000) regardless of tier --
TYP-SHELL's own `min_amount_usd` is $500,000, so ordinary asset_purchase
activity stays an order of magnitude below the threshold and the channel
alone is not a tell. Value dates are drawn uniformly across the window
with weekday weighting (a weekend date is kept only 25% of the time it is
drawn, then redrawn otherwise).
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sys
import time
from datetime import date, timedelta
from random import Random

from ccf.config import REPO_ROOT

SEED = 170_010  # fixed constant: Wave 17, Task 10. Never re-seeded per run.

AS_OF_AML = "2026-08-24"          # pinned; NEVER datetime.now()
WINDOW_START = "2025-02-24"       # AS_OF_AML minus 18 months

PARTIES_PATH = REPO_ROOT / "sources" / "screening" / "wave17_parties.json"
CASES_PATH = REPO_ROOT / "sources" / "screening" / "wave17_cases.json"
OUT_PATH = REPO_ROOT / "sources" / "screening" / "wave17_transactions.json"

MIN_TRANSACTIONS = 3000

# Per-party outbound transaction count. Floor (16) times 201 parties
# guarantees >= 3216 transactions regardless of how the draws land -- the
# >= 3000 floor does not depend on getting lucky.
MIN_TXNS_PER_PARTY = 16
MAX_TXNS_PER_PARTY = 24

MAX_RESAMPLE_ATTEMPTS = 50

# TYP-STRUCT's own parameters (sources/screening/wave17_typologies.json) --
# the shape this generator must NOT produce by accident.
STRUCT_BAND_LOW = 8000
STRUCT_BAND_HIGH = 10000  # exclusive
STRUCT_MIN_TXNS = 4
STRUCT_WINDOW_DAYS = 10

CHANNELS = [
    "wire_transfer", "ach_credit", "ach_debit", "check_payment",
    "card_settlement", "trade_settlement", "intercompany_transfer",
    "asset_purchase",
]
CHANNEL_WEIGHTS = [30, 20, 15, 10, 10, 8, 5, 2]

ASSET_PURCHASE_MIN = 2_000.0
ASSET_PURCHASE_MAX = 45_000.0  # well below TYP-SHELL's 500,000 threshold

PROVENANCE = "synthetic — engineered"


# --------------------------------------------------------------------------
# Shared anti-pattern detector -- imported by
# validators/test_aml_typology.py so the generator's own check and the
# test's check can never drift apart.
# --------------------------------------------------------------------------

def load_case_excluded_txn_ids() -> set[str]:
    """Every txn_id cited by any case in wave17_cases.json. Missing file
    (true before Task 11 runs) -> empty set, per the controller ruling."""
    if not CASES_PATH.exists():
        return set()
    data = json.loads(CASES_PATH.read_text())
    ids: set[str] = set()
    for case in data.get("cases", []):
        ids.update(case.get("txn_ids", []))
    return ids


def find_structuring_shaped_party(transactions: list[dict],
                                   excluded_txn_ids: set[str]):
    """Return (party, span_days) for the first from_party whose ORDINARY
    transactions -- i.e. excluding any txn_id in excluded_txn_ids -- carry
    4+ transactions inside a 10-day window, all in the [8000, 10000) band.
    Returns None if no such party exists. This is the exact TYP-STRUCT
    shape; see the module docstring for why it must never appear in the
    ordinary population."""
    by_party: dict[str, list[date]] = collections.defaultdict(list)
    for t in transactions:
        if t.get("txn_id") in excluded_txn_ids:
            continue
        if STRUCT_BAND_LOW <= t["amount_usd"] < STRUCT_BAND_HIGH:
            by_party[t["from_party"]].append(date.fromisoformat(t["value_date"]))
    for party, dates in sorted(by_party.items()):
        dates.sort()
        for i in range(len(dates) - (STRUCT_MIN_TXNS - 1)):
            span = (dates[i + STRUCT_MIN_TXNS - 1] - dates[i]).days
            if span <= STRUCT_WINDOW_DAYS:
                return party, span
    return None


def _self_test_detector() -> None:
    """Positive/negative control, same idiom as
    generate_aml_parties.py's RealNameIndex controls: prove the detector
    actually fires on a known-bad shape and stays quiet on a known-clean
    one, BEFORE trusting a clean result on the real data. A rejection
    count of zero on the real run is not evidence the check ran; this is."""
    bad = [
        {"txn_id": f"CTRL-{i}", "from_party": "AMLP-CONTROL",
         "to_party": "AMLP-0002", "amount_usd": amt, "value_date": d,
         "channel": "wire_transfer", "provenance": PROVENANCE}
        for i, (amt, d) in enumerate([
            (8500.0, "2025-06-01"), (8700.0, "2025-06-04"),
            (9200.0, "2025-06-07"), (9600.0, "2025-06-10"),
        ])
    ]
    hit = find_structuring_shaped_party(bad, set())
    assert hit is not None, "detector failed to catch a known-bad batch"
    assert hit[0] == "AMLP-CONTROL"

    clean = [dict(t) for t in bad]
    clean[-1]["value_date"] = "2025-07-15"  # pushes the 4th txn past 10 days
    assert find_structuring_shaped_party(clean, set()) is None, (
        "detector flagged a known-clean batch")

    excluded = {"CTRL-0", "CTRL-1", "CTRL-2", "CTRL-3"}
    assert find_structuring_shaped_party(bad, excluded) is None, (
        "detector did not honor the exclusion set")


def _batch_has_structuring_shape(batch: list[dict]) -> bool:
    """Single-party version used during generation, before txn_id exists.
    All records share one from_party by construction."""
    dates = sorted(
        date.fromisoformat(t["value_date"]) for t in batch
        if STRUCT_BAND_LOW <= t["amount_usd"] < STRUCT_BAND_HIGH
    )
    for i in range(len(dates) - (STRUCT_MIN_TXNS - 1)):
        span = (dates[i + STRUCT_MIN_TXNS - 1] - dates[i]).days
        if span <= STRUCT_WINDOW_DAYS:
            return True
    return False


# --------------------------------------------------------------------------
# Amount / date / channel draws
# --------------------------------------------------------------------------

def _draw_channel(rng: Random) -> str:
    return rng.choices(CHANNELS, weights=CHANNEL_WEIGHTS, k=1)[0]


def _draw_amount(rng: Random, channel: str) -> float:
    if channel == "asset_purchase":
        return round(rng.uniform(ASSET_PURCHASE_MIN, ASSET_PURCHASE_MAX), 2)
    u = rng.random()
    if u < 0.80:
        raw = rng.uniform(50.0, 3_000.0)
    elif u < 0.95:
        raw = rng.uniform(3_000.0, 20_000.0)
    elif u < 0.99:
        raw = rng.uniform(20_000.0, 150_000.0)
    else:
        raw = rng.uniform(150_000.0, 2_000_000.0)
    return round(raw, 2)


_WINDOW_DAYS_TOTAL = (date.fromisoformat(AS_OF_AML)
                      - date.fromisoformat(WINDOW_START)).days + 1


def _draw_value_date(rng: Random) -> str:
    start = date.fromisoformat(WINDOW_START)
    for _ in range(20):  # bounded weekday-weighting retry
        offset = rng.randrange(_WINDOW_DAYS_TOTAL)
        d = start + timedelta(days=offset)
        if d.weekday() < 5:  # Mon-Fri
            return d.isoformat()
        if rng.random() < 0.25:  # keep 25% of weekend draws
            return d.isoformat()
    return d.isoformat()  # fallback: last draw, however landed


# --------------------------------------------------------------------------
# Generation
# --------------------------------------------------------------------------

def _draw_party_batch(rng: Random, from_party: str, others: list[str],
                       count: int) -> list[dict]:
    batch = []
    for _ in range(count):
        channel = _draw_channel(rng)
        batch.append({
            "from_party": from_party,
            "to_party": rng.choice(others),
            "amount_usd": _draw_amount(rng, channel),
            "value_date": _draw_value_date(rng),
            "channel": channel,
            "provenance": PROVENANCE,
        })
    return batch


def generate_transactions():
    t0 = time.monotonic()
    _self_test_detector()

    parties = json.loads(PARTIES_PATH.read_text())["parties"]
    party_ids = sorted(p["party_id"] for p in parties)
    assert len(party_ids) == 201, f"expected 201 parties, got {len(party_ids)}"

    rng = Random(SEED)
    all_txns: list[dict] = []
    resample_events: list[tuple[str, int]] = []

    for from_party in party_ids:  # sorted, fixed draw order
        others = [p for p in party_ids if p != from_party]
        count = rng.randint(MIN_TXNS_PER_PARTY, MAX_TXNS_PER_PARTY)
        attempts = 0
        while True:
            batch = _draw_party_batch(rng, from_party, others, count)
            if not _batch_has_structuring_shape(batch):
                break
            attempts += 1
            if attempts > MAX_RESAMPLE_ATTEMPTS:
                raise RuntimeError(
                    f"{from_party}: could not clear the structuring shape "
                    f"after {attempts} resample attempts")
        if attempts:
            resample_events.append((from_party, attempts))
        all_txns.extend(batch)

    assert len(all_txns) >= MIN_TRANSACTIONS, (
        f"only {len(all_txns)} transactions, need >= {MIN_TRANSACTIONS}")

    # txn_id: sorted, content-derived ordering -- never the draw order
    # above. Sort key is the full content tuple; a sha256 of the record's
    # canonical JSON is the final tiebreaker so the ordering is total even
    # if two records were ever otherwise identical.
    def _sort_key(t: dict) -> tuple:
        digest = hashlib.sha256(
            json.dumps(t, sort_keys=True).encode("utf-8")
        ).hexdigest()
        return (t["value_date"], t["from_party"], t["to_party"],
                t["channel"], t["amount_usd"], digest)

    all_txns.sort(key=_sort_key)
    for i, t in enumerate(all_txns, start=1):
        t["txn_id"] = f"TXN-{i:06d}"

    ordered_txns = [
        {
            "txn_id": t["txn_id"],
            "from_party": t["from_party"],
            "to_party": t["to_party"],
            "amount_usd": t["amount_usd"],
            "value_date": t["value_date"],
            "channel": t["channel"],
            "provenance": t["provenance"],
        }
        for t in all_txns
    ]

    # Final verification pass over the assembled, txn_id-bearing artifact --
    # the case-exclusion ruling applied here too, even though the
    # exclusion set is empty at this point in the plan (wave17_cases.json
    # does not exist until Task 11 runs).
    excluded = load_case_excluded_txn_ids()
    violation = find_structuring_shaped_party(ordered_txns, excluded)
    assert violation is None, (
        f"final artifact still contains a structuring-shaped cluster for "
        f"{violation[0]} ({violation[1]}d) after per-party resampling")

    wall_seconds = time.monotonic() - t0
    return ordered_txns, resample_events, wall_seconds


def injected_block_would_be_destroyed(cases_path=CASES_PATH) -> tuple[int, int] | None:
    """`(case_count, cited_txn_count)` if writing the ordinary population
    over `OUT_PATH` would destroy an injected Task 11 block; `None` if
    there is nothing to destroy.

    `main()` rewrites the artifact with the ordinary rows ONLY. Task 11
    appends its engineered cases to that same file and cites their txn_ids
    from `wave17_cases.json`, and no case cites an ordinary id -- so after
    an unguarded rewrite every single case txn_id dangles. The next test
    run says so, loudly and in five places; the run that does the damage
    said "Wrote 4095 transactions" and exited 0. That gap is exactly the
    "runs clean and produces stores that cannot be assembled" failure
    CLAUDE.md names by hand, so it is closed here rather than only in the
    other file's docstring, which the operator of THIS script is not
    reading."""
    if not cases_path.exists():
        return None
    cases = json.loads(cases_path.read_text()).get("cases", [])
    cited = {i for c in cases for i in c.get("txn_ids", [])}
    return len(cases), len(cited)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate the ordinary Wave 17 AML transaction "
                    "population. Refuses to run once Task 11 has injected "
                    "its engineered cases into the same artifact, because "
                    "this script rewrites that artifact with the ordinary "
                    "rows only.")
    parser.add_argument(
        "--regenerate-base", action="store_true",
        help="regenerate the ordinary population even though "
             "wave17_cases.json exists, DESTROYING the injected block. "
             "generators/inject_typology_cases.py must then be re-run to "
             "rebuild it.")
    args = parser.parse_args(argv)

    at_risk = injected_block_would_be_destroyed()
    if at_risk is not None:
        case_count, cited = at_risk
        lines = [
            "!! REFUSING TO RUN.",
            f"!! {CASES_PATH} exists: {case_count} engineered cases citing "
            f"{cited} transactions.",
            "!! This script rewrites the transaction artifact with the "
            "ORDINARY rows only, so running it now would delete every "
            "injected transaction and leave all "
            f"{cited} case txn_ids dangling.",
            "!! To rebuild BOTH populations, run:",
            "!!     uv run generators/inject_typology_cases.py",
            "!! (it regenerates this ordinary base in-process, then "
            "re-injects the cases).",
            "!! To regenerate the ordinary base alone anyway, pass "
            "--regenerate-base and re-run the injector afterwards.",
        ]
        if not args.regenerate_base:
            for line in lines:
                print(line, file=sys.stderr)
            return 2
        for line in lines[1:3]:
            print(line.replace("!!", "!! WARNING:", 1), file=sys.stderr)
        print("!! WARNING: --regenerate-base given, proceeding. Re-run "
              "generators/inject_typology_cases.py to rebuild the injected "
              "block.", file=sys.stderr)

    txns, resample_events, wall_seconds = generate_transactions()

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(
            {"as_of": AS_OF_AML, "window_start": WINDOW_START,
             "transactions": txns},
            indent=2, sort_keys=True, ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )

    by_channel: dict[str, int] = {}
    for t in txns:
        by_channel[t["channel"]] = by_channel.get(t["channel"], 0) + 1

    print(f"Wrote {len(txns)} transactions to {OUT_PATH}")
    print(f"  window: {WINDOW_START} .. {AS_OF_AML}")
    print(f"  by channel: {dict(sorted(by_channel.items()))}")
    print(f"Anti-pattern self-test: passed (positive control caught a "
          f"known-bad batch, negative control and the exclusion set both "
          f"stayed quiet on known-clean input).")
    if resample_events:
        print(f"Parties resampled for tripping the structuring shape: "
              f"{len(resample_events)} -- {resample_events}")
    else:
        print("Parties resampled for tripping the structuring shape: 0 "
              "(legitimate outcome -- the self-test above, not this "
              "count, is what proves the check ran).")
    print(f"Wall time: {wall_seconds:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
