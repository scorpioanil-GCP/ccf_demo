#!/usr/bin/env python3
"""Wave 17 Task 11 -- inject the engineered typology cases.

Task 10 produced 4,095 ORDINARY transactions
(`sources/screening/wave17_transactions.json`). This module appends the
engineered money-laundering cases -- the patterns `aml-typology-match`
exists to demonstrate -- to that same artifact, and writes
`sources/screening/wave17_cases.json` describing them.

## Every case is built from its typology's LIVE params

Nothing in this module hardcodes a threshold. `threshold_usd`,
`band_low`, `band_high`, `min_transactions`, `window_days`,
`min_deposit_locations`, `max_window_days`, `invoice_price_variance_pct`,
`min_shipments`, `min_ownership_hops`, `min_amount_usd`, `financing_leg`
and both typology `channel`s are read from
`sources/screening/wave17_typologies.json` at run time, so a case cannot
drift away from the advisory it cites. Edit the advisory params and the
cases move with them.

## The ordering claim (envelope floor 2)

One case requires depth 3: subject -> intermediary A -> intermediary B ->
target, where the target is UNREACHABLE from the subject in two hops and
reachable in three. That is an ordering claim, and no count establishes
it. The graph the floor walks is undirected and contains all 4,095
ordinary transactions plus everything this module injects, so a subject's
existing ordinary counterparties can trivially create a two-hop shortcut
to any target. `_search_depth_three_chain` therefore does not reason about
the construction -- it builds the trial graph, runs the SAME reachability
walk the test runs, and rejects any candidate whose target turns out to be
visible at depth 2. Rejection counts are printed.

## Tell dilution (controller ruling, Task 11)

Task 10 diluted `asset_purchase` -- TYP-SHELL's channel -- so that the
channel alone is not a tell (82 ordinary rows, all far below the 500,000
gate). TYP-FUNNEL's `cash_deposit_geographic_dispersion` and TYP-TBML's
`over_under_invoicing` did not exist in the ordinary vocabulary at all,
which made those two typologies clean by ABSENCE rather than by dilution:
one string match on `channel` would have found every case with trivially
perfect precision and no inference whatsoever. So this module also emits a
low rate (~2% of the population, matching Task 10's asset_purchase rate)
of ORDINARY, non-case traffic on both channels.

That traffic is deliberately SHAPELESS, and shapeless the interesting way
-- adjacent to each typology without forming it:

  * funnel channel: some accounts receive several dispersed deposits but
    spread far wider than `max_window_days`; others receive a tight
    cluster inside the window but all from ONE jurisdiction, so
    `min_deposit_locations` is never met. Amounts straddle
    `threshold_usd` in both directions.
  * invoicing channel: some counterparty pairs are invoiced twice on the
    same day -- a naive double-invoice detector with no variance test
    would flag them -- but the two amounts sit far under
    `invoice_price_variance_pct`.

`find_funnel_shaped_account` and `find_double_invoiced_pair` are the
detectors that enforce this. They are imported by
`validators/test_aml_typology.py` so the generator's check and the test's
check can never drift apart, in the same shared-detector idiom
`generate_aml_transactions.find_structuring_shaped_party` established.
Both carry positive AND negative controls (`_self_test_detectors`), which
must fire before any clean result on the real data is believed.

## Re-run order

`generate_aml_transactions.py`'s own `main()` REWRITES
`wave17_transactions.json` with its 4,095 ordinary rows only, so running
Task 10's script on its own drops everything this module injected. The
order is always: Task 10's generator, then this one -- or just this one,
which regenerates the ordinary base itself. Nothing silently survives the
wrong order: the cases still cite txn_ids that would no longer exist, and
`validators/test_aml_typology.py` fails on the first missing id.

## Determinism and re-runnability

`SEED` is a fixed constant, all randomness flows through one seeded
`random.Random`, and every iteration is over sorted collections. The
ordinary base is not read off disk and appended to -- it is regenerated
in-process by Task 10's own `generate_transactions()`, so a second run of
this script cannot append a second copy of anything, and the regenerated
rows are asserted to match the ordinary rows already in the artifact
before anything is written. `txn_id` extends Task 10's scheme: the
injected block is sorted by the same content-derived key (value_date,
from_party, to_party, channel, amount_usd, sha256 of the record) and
numbered on from TXN-004095. `case_id` is likewise content-derived, never
positional -- cases are sorted by (typology_id, subject_party, digest)
before numbering.
"""

from __future__ import annotations

import collections
import hashlib
import itertools
import json
import sys
from datetime import date, timedelta
from random import Random

from ccf.config import REPO_ROOT

from generators.generate_aml_transactions import (
    AS_OF_AML,
    WINDOW_START,
    PROVENANCE,
    find_structuring_shaped_party,
    generate_transactions,
)

SEED = 170_110  # fixed constant: Wave 17, Task 11. Never re-seeded per run.

SCREEN = REPO_ROOT / "sources" / "screening"
TYPOLOGIES_PATH = SCREEN / "wave17_typologies.json"
PARTIES_PATH = SCREEN / "wave17_parties.json"
OWNERSHIP_PATH = SCREEN / "wave17_ownership.json"
TXN_PATH = SCREEN / "wave17_transactions.json"
CASES_PATH = SCREEN / "wave17_cases.json"

# Cases per typology. 24 total, over the envelope's floor of 20, with the
# four typologies evenly represented so no one of them is a token entry.
CASES_PER_TYPOLOGY = 6

# ~2% of Task 10's 4,095 ordinary rows, per channel -- the same rate Task
# 10 used to dilute asset_purchase.
DILUTION_RATE = 0.02

# Ordinary payment channels a structuring case may use. Deliberately NOT a
# typology channel: threshold avoidance is a SHAPE, and a case that also
# announced itself with a bespoke channel would be findable without it.
STRUCT_CHANNELS = ["wire_transfer", "ach_credit", "check_payment"]

LAYERING_CHANNEL = "intercompany_transfer"
FUNNEL_OUTBOUND_CHANNEL = "wire_transfer"

MAX_DRAW_ATTEMPTS = 200

_WINDOW_START_D = date.fromisoformat(WINDOW_START)
_AS_OF_D = date.fromisoformat(AS_OF_AML)
_WINDOW_DAYS_TOTAL = (_AS_OF_D - _WINDOW_START_D).days + 1


def _days_between(a: str, b: str) -> int:
    return abs((date.fromisoformat(a) - date.fromisoformat(b)).days)


# --------------------------------------------------------------------------
# Shared detectors -- imported by validators/test_aml_typology.py.
# --------------------------------------------------------------------------

def find_funnel_shaped_account(transactions, excluded_txn_ids, params,
                                jurisdictions):
    """Return `(account, sorted_locations, window_start_date)` for the first
    account receiving deposits on the funnel channel from at least
    `min_deposit_locations` DISTINCT jurisdictions inside
    `max_window_days`; `None` if no such account exists.

    That is TYP-FUNNEL's own shape, read from its params. Transactions in
    `excluded_txn_ids` (every txn_id cited by a case) are skipped, so this
    judges the ORDINARY slice only -- the same case-exclusion scoping the
    Task 10 anti-pattern check uses."""
    by_account = collections.defaultdict(list)
    for t in transactions:
        if t.get("txn_id") in excluded_txn_ids:
            continue
        if t["channel"] != params["channel"]:
            continue
        by_account[t["to_party"]].append(t)
    for account, rows in sorted(by_account.items()):
        rows.sort(key=lambda r: (r["value_date"], r.get("txn_id", "")))
        for i, anchor in enumerate(rows):
            locations = set()
            for r in rows[i:]:
                if _days_between(anchor["value_date"],
                                 r["value_date"]) > params["max_window_days"]:
                    break
                locations.add(jurisdictions.get(r["from_party"]))
            if len(locations) >= params["min_deposit_locations"]:
                return account, sorted(locations), anchor["value_date"]
    return None


def find_double_invoiced_pair(transactions, excluded_txn_ids, params):
    """Return `((from_party, to_party, value_date), variance_pct)` for the
    first counterparty pair invoiced more than once on the same day on the
    TBML channel with a spread of at least `invoice_price_variance_pct`;
    `None` if no such pair exists. Same case-exclusion scoping as above."""
    by_shipment = collections.defaultdict(list)
    for t in transactions:
        if t.get("txn_id") in excluded_txn_ids:
            continue
        if t["channel"] != params["channel"]:
            continue
        by_shipment[(t["from_party"], t["to_party"],
                     t["value_date"])].append(float(t["amount_usd"]))
    for key, amounts in sorted(by_shipment.items()):
        if len(amounts) < 2:
            continue
        for low, high in itertools.combinations(sorted(amounts), 2):
            if low <= 0:
                continue
            variance = (high - low) / low * 100.0
            if variance >= params["invoice_price_variance_pct"]:
                return key, variance
    return None


def _self_test_detectors(funnel_params, tbml_params) -> None:
    """Positive AND negative controls for both detectors, run before the
    real data is judged. A detector that answers 'clean' on every input is
    decoration; this estate has recorded two checks that hid for seven
    waves each. Require DIFFERENT answers on known-bad and known-clean."""
    juris = {"P-A": "USA", "P-B": "DEU", "P-C": "USA", "P-F": "GBR"}
    bad = [
        {"txn_id": "CTRL-F1", "from_party": "P-A", "to_party": "P-F",
         "amount_usd": 9000.0, "value_date": "2025-06-02",
         "channel": funnel_params["channel"]},
        {"txn_id": "CTRL-F2", "from_party": "P-B", "to_party": "P-F",
         "amount_usd": 8000.0, "value_date": "2025-06-04",
         "channel": funnel_params["channel"]},
    ]
    assert find_funnel_shaped_account(bad, set(), funnel_params, juris), \
        "funnel detector missed a known-bad account"
    one_place = [dict(bad[0]), dict(bad[1], from_party="P-C")]
    assert find_funnel_shaped_account(one_place, set(), funnel_params,
                                      juris) is None, \
        "funnel detector fired on deposits from a single jurisdiction"
    far_apart = [dict(bad[0]), dict(bad[1], value_date="2025-07-30")]
    assert find_funnel_shaped_account(far_apart, set(), funnel_params,
                                      juris) is None, \
        "funnel detector ignored max_window_days"
    assert find_funnel_shaped_account(bad, {"CTRL-F1", "CTRL-F2"},
                                      funnel_params, juris) is None, \
        "funnel detector did not honor the exclusion set"

    dbl = [
        {"txn_id": "CTRL-T1", "from_party": "P-A", "to_party": "P-B",
         "amount_usd": 10_000.0, "value_date": "2025-06-02",
         "channel": tbml_params["channel"]},
        {"txn_id": "CTRL-T2", "from_party": "P-A", "to_party": "P-B",
         "amount_usd": 14_000.0, "value_date": "2025-06-02",
         "channel": tbml_params["channel"]},
    ]
    assert find_double_invoiced_pair(dbl, set(), tbml_params), \
        "invoice detector missed a known-bad double invoice"
    narrow = [dict(dbl[0]), dict(dbl[1], amount_usd=10_500.0)]
    assert find_double_invoiced_pair(narrow, set(), tbml_params) is None, \
        "invoice detector ignored invoice_price_variance_pct"
    apart = [dict(dbl[0]), dict(dbl[1], value_date="2025-06-09")]
    assert find_double_invoiced_pair(apart, set(), tbml_params) is None, \
        "invoice detector paired invoices from different days"
    assert find_double_invoiced_pair(dbl, {"CTRL-T1", "CTRL-T2"},
                                     tbml_params) is None, \
        "invoice detector did not honor the exclusion set"


# --------------------------------------------------------------------------
# Graph reachability -- the SAME walk validators/test_aml_typology.py runs.
# --------------------------------------------------------------------------

def build_adjacency(transactions, extra_edges=()):
    adj = collections.defaultdict(set)
    for t in transactions:
        adj[t["from_party"]].add(t["to_party"])
        adj[t["to_party"]].add(t["from_party"])
    for a, b in extra_edges:
        adj[a].add(b)
        adj[b].add(a)
    return adj


def reach(adj, start, depth):
    seen, frontier = {start}, {start}
    for _ in range(depth):
        nxt = set()
        for n in frontier:
            nxt |= adj[n] - seen
        seen |= nxt
        frontier = nxt
    return seen


# --------------------------------------------------------------------------
# Draws
# --------------------------------------------------------------------------

def _draw_date(rng: Random) -> str:
    return (_WINDOW_START_D
            + timedelta(days=rng.randrange(_WINDOW_DAYS_TOTAL))).isoformat()


def _draw_anchor_date(rng: Random, tail_days: int) -> str:
    """A start date leaving `tail_days` of room before as_of, so a case's
    later legs never fall outside the pinned window."""
    span = _WINDOW_DAYS_TOTAL - tail_days
    assert span > 0, "tail_days exceeds the whole window"
    return (_WINDOW_START_D + timedelta(days=rng.randrange(span))).isoformat()


def _shift(day: str, n: int) -> str:
    return (date.fromisoformat(day) + timedelta(days=n)).isoformat()


def _txn(from_party, to_party, amount_usd, value_date, channel) -> dict:
    return {
        "from_party": from_party,
        "to_party": to_party,
        "amount_usd": round(float(amount_usd), 2),
        "value_date": value_date,
        "channel": channel,
        "provenance": PROVENANCE,
    }


# --------------------------------------------------------------------------
# Ordinary tell-dilution traffic
# --------------------------------------------------------------------------

def dilution_candidate_is_shapeless(candidate, existing, funnel_params,
                                     tbml_params, jurisdictions) -> bool:
    """Would adding `candidate` to the ordinary population `existing` leave
    that population clear of EVERY shape the typologies define -- the
    TYP-STRUCT cluster, the TYP-FUNNEL account and the TYP-TBML double
    invoice?

    This single predicate is what both dilution loops accept on, so a test
    can exercise the loop's actual decision rather than only the detectors
    it happens to call. Pass `funnel_params`/`tbml_params` as None to skip
    a shape that cannot apply to the channel being drawn; `jurisdictions`
    is only needed for the funnel shape."""
    trial = list(existing) + [candidate]
    if find_structuring_shaped_party(trial, set()) is not None:
        return False
    if funnel_params is not None and find_funnel_shaped_account(
            trial, set(), funnel_params, jurisdictions) is not None:
        return False
    if tbml_params is not None and find_double_invoiced_pair(
            trial, set(), tbml_params) is not None:
        return False
    return True


def _generate_funnel_dilution(rng, party_ids, jurisdictions, params, count,
                               ordinary, stats):
    """Ordinary cash_deposit_geographic_dispersion traffic that is adjacent
    to TYP-FUNNEL without forming it. Three deliberate shapes, none of
    which satisfies the params: dispersed deposits spread far wider than
    max_window_days; tight clusters from a SINGLE jurisdiction; and lone
    deposits. Amounts straddle threshold_usd in both directions."""
    by_juris = collections.defaultdict(list)
    for p in party_ids:
        by_juris[jurisdictions[p]].append(p)
    juris_keys = sorted(by_juris)
    out: list[dict] = []

    def amount() -> float:
        if rng.random() < 0.80:
            return round(rng.uniform(200.0, params["threshold_usd"] * 0.98), 2)
        return round(rng.uniform(params["threshold_usd"], 60_000.0), 2)

    def accept(candidate: dict) -> bool:
        ok = dilution_candidate_is_shapeless(
            candidate, ordinary + out, params, None, jurisdictions)
        if not ok:
            stats["funnel_rejected"] += 1
        return ok

    attempts = 0
    while len(out) < count:
        attempts += 1
        if attempts > MAX_DRAW_ATTEMPTS:
            raise RuntimeError(
                f"_generate_funnel_dilution: exhausted {MAX_DRAW_ATTEMPTS} "
                f"draw attempts with only {len(out)}/{count} rows accepted "
                "-- the acceptance predicate is rejecting almost every draw "
                "(check params, notably min_deposit_locations)")
        account = rng.choice(party_ids)
        mode = rng.random()
        if mode < 0.30:
            # dispersed but far too slow to be a funnel: distinct
            # jurisdictions, spaced well beyond max_window_days.
            n = rng.randint(2, 3)
            js = rng.sample(juris_keys, n)
            anchor = _draw_anchor_date(rng, 120)
            gap = params["max_window_days"] + 1
            legs = [
                (rng.choice(by_juris[j]),
                 _shift(anchor, i * rng.randint(gap + 14, gap + 45)))
                for i, j in enumerate(js)
            ]
        elif mode < 0.60:
            # tight cluster, but every depositor sits in ONE jurisdiction,
            # so min_deposit_locations is never met.
            j = rng.choice([k for k in juris_keys if len(by_juris[k]) >= 2])
            n = rng.randint(2, 3)
            anchor = _draw_anchor_date(rng, params["max_window_days"] + 2)
            legs = [
                (rng.choice(by_juris[j]),
                 _shift(anchor, rng.randint(0, params["max_window_days"])))
                for _ in range(n)
            ]
        else:
            legs = [(rng.choice(party_ids), _draw_date(rng))]

        for depositor, value_date in legs:
            if len(out) >= count:
                break
            if depositor == account:
                continue
            candidate = _txn(depositor, account, amount(), value_date,
                             params["channel"])
            if accept(candidate):
                out.append(candidate)
    return out


def _generate_invoicing_dilution(rng, party_ids, params, count, ordinary,
                                  stats):
    """Ordinary over_under_invoicing traffic adjacent to TYP-TBML without
    forming it: roughly a fifth of it is same-day, same-pair PAIRS -- which
    a naive double-invoice detector with no variance test would flag --
    whose two amounts sit far below invoice_price_variance_pct."""
    out: list[dict] = []

    def accept(candidate: dict) -> bool:
        ok = dilution_candidate_is_shapeless(
            candidate, ordinary + out, None, params, None)
        if not ok:
            stats["invoice_rejected"] += 1
        return ok

    attempts = 0
    while len(out) < count:
        attempts += 1
        if attempts > MAX_DRAW_ATTEMPTS:
            raise RuntimeError(
                f"_generate_invoicing_dilution: exhausted {MAX_DRAW_ATTEMPTS} "
                f"draw attempts with only {len(out)}/{count} rows accepted "
                "-- the acceptance predicate is rejecting almost every draw "
                "(check params, notably invoice_price_variance_pct)")
        seller = rng.choice(party_ids)
        buyer = rng.choice([p for p in party_ids if p != seller])
        value_date = _draw_date(rng)
        base = round(rng.uniform(5_000.0, 250_000.0), 2)
        legs = [(base, value_date)]
        if rng.random() < 0.20 and len(out) + 2 <= count:
            # a same-day restatement, spread kept well under the gate
            spread = rng.uniform(0.02, params["invoice_price_variance_pct"]
                                 / 100.0 * 0.6)
            legs.append((round(base * (1 + spread), 2), value_date))
        for amount, day in legs:
            if len(out) >= count:
                break
            candidate = _txn(seller, buyer, amount, day, params["channel"])
            if accept(candidate):
                out.append(candidate)
    return out


# --------------------------------------------------------------------------
# Cases
# --------------------------------------------------------------------------

class _Case:
    """A case under construction. `rows` are the transaction dicts it owns;
    txn_ids are attached after the whole injected block is sorted and
    numbered, never from the order the rows were built in."""

    def __init__(self, typology_id, subject_party, requires_depth, rows,
                 pattern, depth_three_counterparty=None):
        self.typology_id = typology_id
        self.subject_party = subject_party
        self.requires_depth = requires_depth
        self.rows = rows
        self.pattern = pattern
        self.depth_three_counterparty = depth_three_counterparty


def _struct_case(rng, subject, party_ids, params):
    low = params["threshold_usd"] * params["band_low"]
    high = params["threshold_usd"] * params["band_high"]
    n = params["min_transactions"] + rng.randint(0, 2)
    anchor = _draw_anchor_date(rng, params["window_days"] + 2)
    beneficiaries = rng.sample([p for p in party_ids if p != subject],
                               rng.randint(1, 2))
    channel = rng.choice(STRUCT_CHANNELS)
    rows = []
    offsets = sorted(rng.randint(0, params["window_days"]) for _ in range(n))
    for offset in offsets:
        rows.append(_txn(subject, rng.choice(beneficiaries),
                         rng.uniform(low, high), _shift(anchor, offset),
                         channel))
    span = _days_between(rows[0]["value_date"], rows[-1]["value_date"])
    pattern = {
        "in_band_transactions": n,
        "band_usd": [round(low, 2), round(high, 2)],
        "window_days_measured": span,
        "channel_used": channel,
    }
    return _Case("TYP-STRUCT", subject, 1, rows, pattern)


def _funnel_case(rng, subject, party_ids, jurisdictions, params):
    by_juris = collections.defaultdict(list)
    for p in party_ids:
        if p != subject:
            by_juris[jurisdictions[p]].append(p)
    n = params["min_deposit_locations"] + rng.randint(1, 2)
    js = rng.sample(sorted(by_juris), n)
    anchor = _draw_anchor_date(rng, params["max_window_days"] + 5)
    rows = []
    for j in js:
        depositor = rng.choice(by_juris[j])
        rows.append(_txn(depositor, subject,
                         rng.uniform(2_500.0, params["threshold_usd"] * 0.95),
                         _shift(anchor,
                                rng.randint(0, params["max_window_days"])),
                         params["channel"]))
    total = sum(r["amount_usd"] for r in rows)
    beneficiary = rng.choice([p for p in party_ids if p != subject])
    rows.append(_txn(subject, beneficiary, total * 0.97,
                     _shift(anchor, params["max_window_days"] + 1),
                     FUNNEL_OUTBOUND_CHANNEL))
    deposit_dates = sorted(r["value_date"] for r in rows[:-1])
    pattern = {
        "deposit_locations": sorted(js),
        "deposit_count": n,
        "deposit_window_days_measured": _days_between(deposit_dates[0],
                                                      deposit_dates[-1]),
        "aggregated_out_usd": round(total * 0.97, 2),
    }
    return _Case("TYP-FUNNEL", subject, 1, rows, pattern)


def _tbml_case(rng, subject, party_ids, params):
    importer = rng.choice([p for p in party_ids if p != subject])
    shipments = params["min_shipments"] + rng.randint(0, 1)
    anchor = _draw_anchor_date(rng, 120)
    rows, measured = [], []
    for i in range(shipments):
        day = _shift(anchor, i * rng.randint(18, 45))
        base = round(rng.uniform(40_000.0, 400_000.0), 2)
        variance = rng.uniform(params["invoice_price_variance_pct"] + 5,
                               params["invoice_price_variance_pct"] + 90)
        rows.append(_txn(subject, importer, base, day, params["channel"]))
        rows.append(_txn(subject, importer, base * (1 + variance / 100.0),
                         day, params["channel"]))
        measured.append({"value_date": day,
                          "variance_pct": round(variance, 2)})
    pattern = {
        "importer": importer,
        "shipments": shipments,
        "double_invoice": params["double_invoice"],
        "shipment_variance": measured,
    }
    return _Case("TYP-TBML", subject, 1, rows, pattern)


def _shell_case(rng, subject, intermediary, seller, hops, params):
    purchase = round(rng.uniform(params["min_amount_usd"] * 1.05,
                                 params["min_amount_usd"] * 4.0), 2)
    anchor = _draw_anchor_date(rng, 60)
    funding = _txn(subject, intermediary, purchase * 1.05, anchor,
                   LAYERING_CHANNEL)
    buy = _txn(intermediary, seller, purchase,
               _shift(anchor, rng.randint(2, 21)), params["channel"])
    pattern = {
        "ownership_hops": hops,
        "intermediaries": [intermediary],
        "seller": seller,
        "purchase_usd": purchase,
        "financing_leg": params["financing_leg"],
        "funded_by_upstream_transfer_usd": funding["amount_usd"],
    }
    return _Case("TYP-SHELL", subject, 2, [funding, buy], pattern)


def _shell_depth_three_case(rng, subject, a, b, target, hops, params):
    purchase = round(rng.uniform(params["min_amount_usd"] * 1.05,
                                 params["min_amount_usd"] * 4.0), 2)
    anchor = _draw_anchor_date(rng, 90)
    leg1 = _txn(subject, a, purchase * 1.10, anchor, LAYERING_CHANNEL)
    leg2 = _txn(a, b, purchase * 1.05, _shift(anchor, rng.randint(3, 14)),
                LAYERING_CHANNEL)
    buy = _txn(b, target, purchase,
               _shift(leg2["value_date"], rng.randint(3, 20)),
               params["channel"])
    pattern = {
        "ownership_hops": hops,
        "intermediaries": [a, b],
        "seller": target,
        "purchase_usd": purchase,
        "financing_leg": params["financing_leg"],
        "funded_by_upstream_transfer_usd": leg2["amount_usd"],
        "chain": [subject, a, b, target],
    }
    return _Case("TYP-SHELL", subject, 3, [leg1, leg2, buy], pattern,
                 depth_three_counterparty=target)


# --------------------------------------------------------------------------
# The depth-3 search
# --------------------------------------------------------------------------

def _search_depth_three_chain(transactions, subjects, intermediaries,
                               party_ids, stats):
    """Find (subject, A, B, target) such that, in the FINAL graph -- every
    ordinary transaction, every diluting transaction, every other case's
    transactions AND the three chain edges themselves -- the target is
    absent from the subject's depth-2 reachable set and present in its
    depth-3 set.

    Nothing here is inferred from the construction. Every candidate is
    checked by building the trial adjacency and running the same walk
    `validators/test_aml_typology.py` runs. The ordinary population is
    dense (201 parties, 4,095 edges, mean degree ~35), so almost every
    party is already within two hops of almost every other; candidates
    rejected for exactly that reason are counted, not hidden."""
    base_adj = build_adjacency(transactions)
    everyone = set(party_ids)
    for subject in subjects:
        visible_at_two = reach(base_adj, subject, 2)
        blind_spot = sorted(everyone - visible_at_two)
        stats["pairs_tested"] += len(party_ids) - 1
        stats["pairs_rejected_depth_two_shortcut"] += (
            len(party_ids) - 1 - len(blind_spot))
        if not blind_spot:
            stats["subjects_with_no_blind_spot"] += 1
            continue
        for target in blind_spot:
            for a in intermediaries:
                if a in (subject, target):
                    continue
                for b in intermediaries:
                    if b in (subject, target, a):
                        continue
                    stats["chains_tested"] += 1
                    trial = build_adjacency(
                        transactions,
                        extra_edges=[(subject, a), (a, b), (b, target)])
                    if target in reach(trial, subject, 2):
                        stats["chains_rejected_depth_two_shortcut"] += 1
                        continue
                    if target not in reach(trial, subject, 3):
                        stats["chains_rejected_not_reachable_at_three"] += 1
                        continue
                    stats["measured_depth_two_size"] = len(
                        reach(trial, subject, 2))
                    stats["measured_depth_three_size"] = len(
                        reach(trial, subject, 3))
                    return subject, a, b, target
    raise RuntimeError(
        "no (subject, A, B, target) chain leaves the target invisible at "
        "depth 2 -- the injected traffic has closed every blind spot; "
        f"stats: {dict(stats)}")


# --------------------------------------------------------------------------
# Assembly
# --------------------------------------------------------------------------

def _content_key(t: dict) -> tuple:
    """Task 10's txn_id sort key, extended unchanged: the record's own
    content, with a sha256 of its canonical JSON as a total-order
    tiebreaker. Never the order the rows were built in."""
    body = {k: t[k] for k in ("from_party", "to_party", "amount_usd",
                              "value_date", "channel", "provenance")}
    digest = hashlib.sha256(
        json.dumps(body, sort_keys=True).encode("utf-8")).hexdigest()
    return (t["value_date"], t["from_party"], t["to_party"], t["channel"],
            t["amount_usd"], digest)


def inject():
    typologies = {t["typology_id"]: t
                  for t in json.loads(TYPOLOGIES_PATH.read_text())["typologies"]}
    params = {k: v["params"] for k, v in typologies.items()}
    _self_test_detectors(params["TYP-FUNNEL"], params["TYP-TBML"])

    parties = json.loads(PARTIES_PATH.read_text())["parties"]
    party_ids = sorted(p["party_id"] for p in parties)
    assert len(party_ids) == 201, f"party population not frozen: {len(party_ids)}"
    jurisdictions = {p["party_id"]: p["jurisdiction"] for p in parties}
    kinds = {p["party_id"]: p["party_kind"] for p in parties}
    hops = {b["party_id"]: b["reused_chain_depth"]
            for b in json.loads(OWNERSHIP_PATH.read_text())["bindings"]}

    # The ordinary base is REGENERATED, not read and appended to, so a
    # second run of this script cannot append a second copy of anything.
    ordinary, _, _ = generate_transactions()
    if TXN_PATH.exists():
        on_disk = [t for t in json.loads(TXN_PATH.read_text())["transactions"]
                   if int(t["txn_id"].split("-")[1]) <= len(ordinary)]
        assert on_disk == ordinary, (
            "the regenerated ordinary population does not match the rows "
            "already in wave17_transactions.json -- Task 10's output is no "
            "longer reproducible and appending to it would corrupt it")

    rng = Random(SEED)
    stats = collections.Counter()

    # ---- ordinary tell-dilution traffic --------------------------------
    dilution_count = round(len(ordinary) * DILUTION_RATE)
    funnel_noise = _generate_funnel_dilution(
        rng, party_ids, jurisdictions, params["TYP-FUNNEL"],
        dilution_count, ordinary, stats)
    invoice_noise = _generate_invoicing_dilution(
        rng, party_ids, params["TYP-TBML"], dilution_count,
        ordinary + funnel_noise, stats)
    dilution = funnel_noise + invoice_noise

    # ---- cases ----------------------------------------------------------
    shell_subjects = sorted(
        p for p in party_ids
        if kinds[p] == "shell"
        and hops.get(p, 0) >= params["TYP-SHELL"]["min_ownership_hops"])
    assert len(shell_subjects) >= CASES_PER_TYPOLOGY + 1, len(shell_subjects)

    used_subjects: set[str] = set()

    def take(pool):
        choices = [p for p in pool if p not in used_subjects]
        pick = rng.choice(choices)
        used_subjects.add(pick)
        return pick

    cases: list[_Case] = []
    for _ in range(CASES_PER_TYPOLOGY):
        cases.append(_struct_case(rng, take(party_ids), party_ids,
                                  params["TYP-STRUCT"]))
    for _ in range(CASES_PER_TYPOLOGY):
        cases.append(_funnel_case(rng, take(party_ids), party_ids,
                                  jurisdictions, params["TYP-FUNNEL"]))
    for _ in range(CASES_PER_TYPOLOGY):
        cases.append(_tbml_case(rng, take(party_ids), party_ids,
                                params["TYP-TBML"]))
    for _ in range(CASES_PER_TYPOLOGY - 1):
        subject = take(shell_subjects)
        intermediary = rng.choice([p for p in shell_subjects if p != subject])
        seller = rng.choice([p for p in party_ids
                             if p not in (subject, intermediary)])
        cases.append(_shell_case(rng, subject, intermediary, seller,
                                 hops[subject], params["TYP-SHELL"]))

    # ---- the depth-3 case, chosen against the FINAL graph ---------------
    so_far = ordinary + dilution + [r for c in cases for r in c.rows]
    depth_subjects = [p for p in shell_subjects if p not in used_subjects]
    intermediaries = [p for p in shell_subjects]
    subject, a, b, target = _search_depth_three_chain(
        so_far, depth_subjects, intermediaries, party_ids, stats)
    used_subjects.add(subject)
    cases.append(_shell_depth_three_case(rng, subject, a, b, target,
                                         hops[subject], params["TYP-SHELL"]))

    # ---- txn_id: content-derived, continuing Task 10's numbering --------
    injected = dilution + [r for c in cases for r in c.rows]
    order = sorted(range(len(injected)), key=lambda i: _content_key(injected[i]))
    for rank, idx in enumerate(order, start=len(ordinary) + 1):
        injected[idx]["txn_id"] = f"TXN-{rank:06d}"

    all_txns = ordinary + [
        {"txn_id": t["txn_id"], "from_party": t["from_party"],
         "to_party": t["to_party"], "amount_usd": t["amount_usd"],
         "value_date": t["value_date"], "channel": t["channel"],
         "provenance": t["provenance"]}
        for t in sorted(injected, key=_content_key)
    ]

    # ---- case_id: content-derived, never positional ---------------------
    def case_key(c: _Case) -> tuple:
        digest = hashlib.sha256(json.dumps(
            {"typology_id": c.typology_id, "subject_party": c.subject_party,
             "txn_ids": sorted(r["txn_id"] for r in c.rows)},
            sort_keys=True).encode("utf-8")).hexdigest()
        return (c.typology_id, c.subject_party, digest)

    cases.sort(key=case_key)
    records = []
    for i, c in enumerate(cases, start=1):
        records.append({
            "case_id": f"CASE-{i:03d}",
            "typology_id": c.typology_id,
            "subject_party": c.subject_party,
            "txn_ids": sorted(r["txn_id"] for r in c.rows),
            "requires_depth": c.requires_depth,
            "depth_three_counterparty": c.depth_three_counterparty,
            "pattern": c.pattern,
            "provenance": PROVENANCE,
        })

    _verify(all_txns, records, params, jurisdictions, hops, len(ordinary))
    return all_txns, records, stats, len(ordinary), len(funnel_noise), \
        len(invoice_noise)


def _verify(all_txns, records, params, jurisdictions, hops, ordinary_count):
    """Recompute every claim from the assembled artifacts before writing.
    Nothing here reads a stored flag."""
    case_ids = {i for c in records for i in c["txn_ids"]}
    assert len(case_ids) == sum(len(c["txn_ids"]) for c in records), \
        "a transaction is cited by two cases"
    assert not (case_ids & {f"TXN-{i:06d}" for i in range(1, ordinary_count + 1)}), \
        "a case cites an ordinary Task 10 transaction"

    by_id = {t["txn_id"]: t for t in all_txns}
    assert len(by_id) == len(all_txns), "duplicate txn_id"
    for t in all_txns:
        assert WINDOW_START <= t["value_date"] <= AS_OF_AML, t
        assert t["provenance"] == PROVENANCE, t

    # ordinary slice must stay clear of all three shapes
    assert find_structuring_shaped_party(all_txns, case_ids) is None, \
        "the ordinary slice now carries the structuring shape"
    assert find_funnel_shaped_account(all_txns, case_ids,
                                      params["TYP-FUNNEL"],
                                      jurisdictions) is None, \
        "the ordinary slice now carries the funnel shape"
    assert find_double_invoiced_pair(all_txns, case_ids,
                                     params["TYP-TBML"]) is None, \
        "the ordinary slice now carries a double invoice"

    # every typology channel must survive a bare string match
    for p in params.values():
        channel = p.get("channel")
        if not channel:
            continue
        used = [t for t in all_txns if t["channel"] == channel]
        ordinary = [t for t in used if t["txn_id"] not in case_ids]
        assert ordinary, f"{channel} is used by cases only"
        assert 1 - len(ordinary) / len(used) <= 0.9, (
            f"a bare channel == {channel} filter is still nearly perfect")

    # the ordering claim, recomputed from the final artifact
    adj = build_adjacency(all_txns)
    deep = [c for c in records if c["requires_depth"] >= 3]
    assert deep, "no case requires depth 3"
    for c in deep:
        target = c["depth_three_counterparty"]
        assert target, f"{c['case_id']} claims depth 3 and names no target"
        assert target not in reach(adj, c["subject_party"], 2), (
            f"{c['case_id']}: {target} is visible at depth 2")
        assert target in reach(adj, c["subject_party"], 3), (
            f"{c['case_id']}: {target} is not reachable at depth 3 either")


def main() -> int:
    all_txns, records, stats, ordinary_count, n_funnel, n_invoice = inject()

    TXN_PATH.write_text(
        json.dumps({"as_of": AS_OF_AML, "window_start": WINDOW_START,
                    "transactions": all_txns},
                   indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8")

    deep = [c for c in records if c["requires_depth"] >= 3][0]
    CASES_PATH.write_text(
        json.dumps({
            "generated_for": ("Wave 17 Task 11 — engineered typology cases "
                              "injected into the Task 10 transaction "
                              "population. Every threshold is read from "
                              "wave17_typologies.json at run time."),
            "seed": SEED,
            "provenance": PROVENANCE,
            "case_count": len(records),
            "ordinary_transaction_count": ordinary_count,
            "injected_transaction_count": len(all_txns) - ordinary_count,
            "cases": records,
        }, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8")

    per = collections.Counter(c["typology_id"] for c in records)
    print(f"Wrote {len(records)} cases to {CASES_PATH}")
    print(f"  per typology: {dict(sorted(per.items()))}")
    print(f"Wrote {len(all_txns)} transactions to {TXN_PATH} "
          f"({ordinary_count} ordinary + {len(all_txns) - ordinary_count} "
          f"injected)")
    print(f"  tell dilution: {n_funnel} ordinary "
          f"cash_deposit_geographic_dispersion, {n_invoice} ordinary "
          f"over_under_invoicing")
    print(f"  dilution draws rejected by dilution_candidate_is_shapeless: "
          f"funnel {stats['funnel_rejected']}, invoice "
          f"{stats['invoice_rejected']} (a zero here is not evidence the "
          f"predicate ran -- its known-present/known-absent controls in "
          f"validators/test_aml_typology.py are)")
    print(f"Depth-3 case {deep['case_id']}: "
          f"{' -> '.join(deep['pattern']['chain'])}")
    print(f"  measured depth-2 reachable set: "
          f"{stats['measured_depth_two_size']} parties (target absent)")
    print(f"  measured depth-3 reachable set: "
          f"{stats['measured_depth_three_size']} parties (target present)")
    print(f"  candidate (subject, target) pairs tested "
          f"{stats['pairs_tested']}, rejected for an existing depth-2 "
          f"shortcut {stats['pairs_rejected_depth_two_shortcut']}")
    print(f"  candidate subjects with NO blind spot at all (every other "
          f"party already within two hops): "
          f"{stats['subjects_with_no_blind_spot']}")
    print(f"  candidate chains tested {stats['chains_tested']}, rejected "
          f"for a depth-2 shortcut {stats['chains_rejected_depth_two_shortcut']}"
          f", rejected for not reaching at depth 3 "
          f"{stats['chains_rejected_not_reachable_at_three']}")
    print("Detector self-test: passed (both detectors fired on known-bad "
          "input, stayed quiet on known-clean input, and honored the "
          "exclusion set).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
