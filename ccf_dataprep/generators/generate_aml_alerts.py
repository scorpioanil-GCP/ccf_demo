#!/usr/bin/env python3
"""Wave 17 Task 12 -- generate the alert population a monitoring system would
raise over the Task 10/11 transaction estate, and the prior-alert links
between them.

## Genuine alerts

Every one of the 24 engineered cases (`sources/screening/wave17_cases.json`)
gets a PRIMARY alert on its own `subject_party`, carrying that case's
`case_id` and a `trigger` built from the case's own `pattern` fields -- never
a hardcoded copy of a typology's params, so a case that drifted from its
typology would produce a trigger that still describes what actually
happened. The six TYP-SHELL cases also get a SECONDARY alert on the last
named intermediary in the ownership chain (the party that received the
upstream transfer and made the purchase): a real monitoring system would
just as plausibly flag the intermediary's account as the ultimate subject's,
since the unusual activity (a large incoming transfer immediately followed
by an asset purchase) sits on the intermediary's own ledger. That yields
24 + 6 = 30 genuine alerts.

## Noise

The envelope's whole point is that precision has to be MEASURABLE, which
means noise must dominate (brief: "an alert set that is all genuine
measures nothing"). 120 noise alerts are drawn from the ORDINARY
transaction pool (every txn_id NOT cited by any case -- 4,259 of the
4,358 rows), weighted by `amount_usd` so a monitoring system's most
obvious rule -- "this was unusually large" -- is what fires, without ever
touching the engineered shapes. Each drawn transaction becomes exactly one
noise alert: `subject_party` is its `from_party` and `case_id` is always
`None`. For **78 of the 120**, `trigger` is derived mechanically from the
transaction's own amount/channel -- the round-dollar rule, the
asset-purchase rule, or the generic large-transaction rule. The other
**42** are relabelled with a typology-named trigger by the next section;
their draw is unchanged, only the text differs.

### Typology-named noise -- why a MINORITY of the noise names a typology

Whole-branch review finding CT-1. The first cut drew every noise alert
from the three rules above, which are DISJOINT from the four typology
names the genuine triggers carry. `trigger` sits in `_alert_core_facts`,
which all three perspectives receive, so `trigger.split(":")[0] in
{structuring, funnel_account, trade_based, shell_company_ownership}` was
an EXACT classifier for "genuine" -- 30 of 30, no false positives, no
inference. §F asks for noise so that "precision is measurable rather than
assumed"; precision of 1.0 by construction measures nothing.

This is the same defect the Task 11 ruling fixed for CHANNEL -- "a
typology whose every instance is findable by one string match demonstrates
nothing this product exists to demonstrate" -- applied one layer up, to
the trigger text rather than the transaction channel. The remedy is the
same move: a minority of the noise names a typology, on ORDINARY parties
that do not form that typology's shape. A structuring-named alert on a
party with no structuring cluster is a false positive, and false positives
are the only thing that makes precision a measurement.

**How the typology-named noise is built.** The 120 draws above are NOT
re-drawn -- `subject_party` and `raised_at` are left exactly as drawn, so
the genuine alerts' content-derived `alert_id`s cannot move (see
"Determinism and IDs"). What changes is `trigger`, on a deterministic
subset, and only where the party's OWN ordinary transactions genuinely
fire a loosened version of the typology's screening rule:

  * `structuring`   -- >= `min_transactions - 1` outgoing payments inside a
                       widened sub-threshold band within `window_days`.
  * `funnel_account`-- >= 2 `cash_deposit_geographic_dispersion` credits
                       inside a widened window, with the senders'
                       jurisdictions as the deposit locations.
  * `trade_based`   -- >= 1 same-day, same-counterparty pair of
                       `over_under_invoicing` rows (a double invoice), with
                       the real measured price variance.
  * `shell_company_ownership`
                    -- an `asset_purchase` with a real inbound transfer in
                       the 30 days before it, and the party's real
                       ownership depth.

Every number in the resulting trigger is MEASURED from
`wave17_transactions.json`, and the text is produced by the SAME builder
functions the genuine alerts use, so the 42 relabelled records introduce
no format tell of their own.

**That is true of the 42 and NOT true of the alert set** -- an earlier
wording here claimed the stronger thing, and the scoped re-review refuted
it. `_shell_secondary_trigger` (below) emits a format no noise alert can
carry: the literal phrase "within the same case" appears on the 6
TYP-SHELL intermediary alerts and nowhere else, so it is a 6/6 classifier
sitting in a field every perspective receives. Measured, not argued. It is
recorded, with the rest of the residual, in `docs/known-issues.md` #31.

**Each one is proved to be below its typology's gate before it is
emitted** (`_below_gate`): a false positive that actually satisfied the
published parameters would not be a false positive, it would be an
un-injected case. That inherency is real and unavoidable -- any dataset
whose ground truth is "exhibits the published shape" makes
gate-satisfaction equivalent to genuineness.

**What this fix achieved, and what it did not.** The PREFIX tell is dead:
best single-prefix precision is 0.500, measured, down from 1.000. What
remains is NOT, as an earlier wording here claimed, an inference over two
artifacts. Every residual separation is available from `l1`'s own
assembled view alone: `typology_pattern_summary.typology_id` compared
against the typology named by `alert_core_facts.trigger`'s prefix (27/27),
OR the literal "within the same case" in that same trigger (6/6) -- two of
`l1`'s own fields, no external artifact and no threshold. Single numeric
thresholds inside the trigger text separate each typology on its own too,
at measured margins of 1.5x to 16.8x. `docs/known-issues.md` #31 records
the rule, the measurements, and why closing it is an open data-design
question rather than a patch.

Parties are excluded per typology: a typology-named noise alert never
lands on a party that appears in ANY case of the typology it names --
subject, intermediary, importer, or counterparty to one of that case's
own transactions.

## Prior-alert links

Two relations, both derived from the assembled alert set itself, never
from how the alerts were built:

  * `same_case_prior_alert` -- links a TYP-SHELL case's secondary
    (intermediary) alert back to its primary (subject) alert. Represents
    "this alert and that one came out of the same underlying case".
  * `prior_alert_on_subject` -- for every `subject_party` that carries more
    than one alert (genuine or noise, and this happens organically: 150
    alerts drawn across 201 possible subjects produces real repeats by
    the birthday effect, not by any deliberate quota), each alert past the
    first links back to the immediately preceding one on that SAME
    subject, chronologically by `raised_at`. Represents "this subject has
    been flagged before" -- the thing an examiner actually wants to see
    when a new alert lands.

No pair of alerts can ever receive both relations: `same_case_prior_alert`
only ever connects two alerts on DIFFERENT subjects (subject vs.
intermediary), and `prior_alert_on_subject` only ever connects two alerts
on the SAME subject.

## Determinism and IDs

`SEED` is a fixed constant; every draw runs through one seeded
`random.Random`, consumed over sorted, content-fixed inputs. `alert_id` is
assigned the same way this estate assigns `txn_id`/`case_id`: sort the
fully-built alert records by their own content (with a sha256 tiebreaker
for a total order), THEN number sequentially -- never from the order the
records were built in, which is the positional-identity defect class this
repo already has five recorded instances of. Re-running this script must
produce a byte-identical `sources/screening/wave17_alerts.json`.

**Why the genuine alerts' ids survived the CT-1 fix.** The sort key is
`(raised_at, subject_party, case_id or "", trigger, digest)`. The
typology-named noise relabels `trigger` and NOTHING else, so a relabelled
record can only move relative to records it ties with on the first three
fields -- and a genuine record never ties with a noise record there, since
`case_id or ""` is empty for noise and non-empty for genuine. Two noise
records may swap places with each other; the NUMBER of records preceding
any genuine record cannot change, so every genuine `alert_id` is fixed.
`_verify` re-asserts this against the previously written artifact when one
is present, rather than leaving it as an argument.
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

from generators.generate_aml_transactions import AS_OF_AML

SEED = 170_012  # fixed constant: Wave 17, Task 12. Never re-seeded per run.

SCREEN = REPO_ROOT / "sources" / "screening"
TYPOLOGIES_PATH = SCREEN / "wave17_typologies.json"
PARTIES_PATH = SCREEN / "wave17_parties.json"
CASES_PATH = SCREEN / "wave17_cases.json"
TXN_PATH = SCREEN / "wave17_transactions.json"
OWNERSHIP_PATH = SCREEN / "wave17_ownership.json"
OUT_PATH = SCREEN / "wave17_alerts.json"

PROVENANCE = "synthetic — internal"  # alerts are bank-internal by nature

NOISE_COUNT = 120  # + 30 genuine = 150 total, genuine fraction 20%
NOISE_MAX_DRAW_ATTEMPTS = 5_000  # generous headroom over a 4,259-row pool

#: CT-1. How many of the 120 noise alerts get a typology-named trigger
#: instead of a generic one. 42 of 120 -- a minority of the noise, and a
#: minority of every typology's own alert population except none: with 6
#: genuine structuring / funnel / trade-based alerts and 12 genuine shell
#: alerts, these quotas put the best single-prefix rule's precision under
#: 0.55 instead of at 1.0. The numbers are bounded by what the ordinary
#: population can actually SUPPORT (a typology-named noise alert is only
#: emitted where the party's own transactions fire the loosened rule), so
#: they are not free parameters -- `_relabel_typology_named_noise` raises
#: rather than quietly emitting fewer.
NOISE_TYPOLOGY_QUOTA = {
    "TYP-STRUCT": 12,
    "TYP-FUNNEL": 9,
    "TYP-TBML": 6,
    "TYP-SHELL": 15,
}

#: Loosening factors for the noise screening rules. Each one makes the rule
#: STRICTLY weaker than the typology's own published gate, which is the
#: point: firing must not imply the shape. `_below_gate` proves the result
#: for every emitted alert rather than trusting these numbers.
NOISE_STRUCT_BAND_LOW_FACTOR = 0.10   # vs the typology's own `band_low`
NOISE_FUNNEL_WINDOW_DAYS = 45         # vs the typology's `max_window_days`
NOISE_SHELL_FUNDING_LOOKBACK_DAYS = 30

GENUINE_PRIMARY_LAG_DAYS = 3     # alert raised N days after the case's last leg
GENUINE_SECONDARY_LAG_DAYS = 5   # secondary alert follows the primary
NOISE_LAG_MIN_DAYS = 1
NOISE_LAG_MAX_DAYS = 10

SAME_CASE_RELATION = "same_case_prior_alert"
PRIOR_SUBJECT_RELATION = "prior_alert_on_subject"
ALLOWED_RELATIONS = {SAME_CASE_RELATION, PRIOR_SUBJECT_RELATION}


def _shift_capped(day: str, n: int) -> str:
    """`day` plus `n` days, capped at AS_OF_AML -- an alert can never be
    raised in the future relative to the pinned as-of date."""
    shifted = (date.fromisoformat(day) + timedelta(days=n)).isoformat()
    return min(shifted, AS_OF_AML)


# --------------------------------------------------------------------------
# Genuine alerts -- one per case, plus a second on TYP-SHELL's intermediary.
# --------------------------------------------------------------------------

def _struct_trigger(pattern: dict) -> str:
    lo, hi = pattern["band_usd"]
    return (f"structuring: {pattern['in_band_transactions']} transactions "
            f"between ${lo:,.0f}-${hi:,.0f} within "
            f"{pattern['window_days_measured']}d via "
            f"{pattern['channel_used']}")


def _funnel_trigger(pattern: dict) -> str:
    locs = pattern["deposit_locations"]
    return (f"funnel_account: {pattern['deposit_count']} deposits from "
            f"{len(locs)} jurisdictions ({', '.join(locs)}) aggregating "
            f"${pattern['aggregated_out_usd']:,.2f} within "
            f"{pattern['deposit_window_days_measured']}d")


def _tbml_trigger(pattern: dict) -> str:
    max_variance = max(m["variance_pct"] for m in pattern["shipment_variance"])
    return (f"trade_based: {pattern['shipments']} shipment(s) double-invoiced "
            f"to importer {pattern['importer']}, max variance "
            f"{max_variance:.1f}%")


def _shell_primary_trigger(pattern: dict) -> str:
    return (f"shell_company_ownership: purchase of "
            f"${pattern['purchase_usd']:,.2f} funded by upstream transfer "
            f"of ${pattern['funded_by_upstream_transfer_usd']:,.2f}, subject "
            f"sits {pattern['ownership_hops']} ownership hops deep")


def _shell_secondary_trigger(pattern: dict) -> str:
    return (f"shell_company_ownership: intermediary received "
            f"${pattern['funded_by_upstream_transfer_usd']:,.2f} then "
            f"purchased for ${pattern['purchase_usd']:,.2f} within the same "
            "case")


_TRIGGER_BUILDERS = {
    "TYP-STRUCT": _struct_trigger,
    "TYP-FUNNEL": _funnel_trigger,
    "TYP-TBML": _tbml_trigger,
    "TYP-SHELL": _shell_primary_trigger,
}


def _build_genuine_alerts(cases: list[dict], txns_by_id: dict[str, dict]) -> list[dict]:
    records = []
    for c in sorted(cases, key=lambda c: c["case_id"]):
        rows = [txns_by_id[i] for i in c["txn_ids"]]
        last_leg = max(r["value_date"] for r in rows)
        primary_raised = _shift_capped(last_leg, GENUINE_PRIMARY_LAG_DAYS)
        builder = _TRIGGER_BUILDERS[c["typology_id"]]
        records.append({
            "subject_party": c["subject_party"],
            "raised_at": primary_raised,
            "case_id": c["case_id"],
            "trigger": builder(c["pattern"]),
            "provenance": PROVENANCE,
        })
        if c["typology_id"] == "TYP-SHELL":
            intermediary = c["pattern"]["intermediaries"][-1]
            records.append({
                "subject_party": intermediary,
                "raised_at": _shift_capped(primary_raised,
                                           GENUINE_SECONDARY_LAG_DAYS),
                "case_id": c["case_id"],
                "trigger": _shell_secondary_trigger(c["pattern"]),
                "provenance": PROVENANCE,
            })
    return records


# --------------------------------------------------------------------------
# Noise -- drawn from the ordinary (non-case) transaction pool, weighted by
# amount_usd, one alert per drawn transaction.
# --------------------------------------------------------------------------

def _noise_trigger(t: dict) -> str:
    amount = t["amount_usd"]
    channel = t["channel"]
    is_round = amount >= 5_000 and amount % 1000 == 0
    if is_round:
        return (f"round_dollar_amount: {channel} payment of ${amount:,.0f} "
                "matches round-dollar screening rule")
    if channel == "asset_purchase":
        return (f"large_asset_purchase: {channel} of ${amount:,.2f} flagged "
                "for review")
    return (f"large_transaction_amount: {channel} transaction of "
            f"${amount:,.2f} exceeds internal large-transaction threshold")


def _draw_noise_alerts(rng: Random, pool: list[dict]) -> list[dict]:
    used_txn_ids: set[str] = set()
    records = []
    weights = [t["amount_usd"] for t in pool]
    attempts = 0
    while len(records) < NOISE_COUNT:
        attempts += 1
        if attempts > NOISE_MAX_DRAW_ATTEMPTS:
            raise RuntimeError(
                f"_draw_noise_alerts: exhausted {NOISE_MAX_DRAW_ATTEMPTS} "
                f"draw attempts with only {len(records)}/{NOISE_COUNT} "
                "noise alerts drawn -- the pool may be too small or too "
                "concentrated for distinct picks")
        t = rng.choices(pool, weights=weights, k=1)[0]
        if t["txn_id"] in used_txn_ids:
            continue
        used_txn_ids.add(t["txn_id"])
        lag = rng.randint(NOISE_LAG_MIN_DAYS, NOISE_LAG_MAX_DAYS)
        records.append({
            "subject_party": t["from_party"],
            "raised_at": _shift_capped(t["value_date"], lag),
            "case_id": None,
            "trigger": _noise_trigger(t),
            "provenance": PROVENANCE,
        })
    return records


# --------------------------------------------------------------------------
# Typology-named noise (CT-1) -- a MINORITY of the noise names a typology,
# on ordinary parties that do NOT form that typology's shape.
#
# Nothing below re-draws an alert. `subject_party` and `raised_at` are the
# ones `_draw_noise_alerts` produced; only `trigger` is rewritten, and only
# where the party's own ORDINARY transactions genuinely fire a loosened
# version of the typology's screening rule. Every number in the emitted
# trigger is measured from `wave17_transactions.json`, and the text comes
# out of the SAME builder the genuine alerts use -- so the prefix tell is
# diluted without a format tell replacing it.
# --------------------------------------------------------------------------

def _day_gap(a: str, b: str) -> int:
    return abs((date.fromisoformat(b) - date.fromisoformat(a)).days)


def _cluster(rows: list[dict], window_days: int, minimum: int) -> list[dict] | None:
    """Earliest maximal run of `rows` (already sorted) spanning at most
    `window_days`, of at least `minimum` rows. Returns None if none."""
    for i in range(len(rows)):
        j = i
        while (j + 1 < len(rows)
               and _day_gap(rows[i]["value_date"], rows[j + 1]["value_date"])
               <= window_days):
            j += 1
        if j - i + 1 >= minimum:
            return rows[i:j + 1]
    return None


def _struct_noise_pattern(subject, out_by_party, params, **_) -> dict | None:
    lo = params["threshold_usd"] * NOISE_STRUCT_BAND_LOW_FACTOR
    hi = params["threshold_usd"] * params["band_high"]
    rows = sorted((r for r in out_by_party.get(subject, ())
                   if lo <= r["amount_usd"] <= hi),
                  key=lambda r: (r["value_date"], r["txn_id"]))
    grp = _cluster(rows, params["window_days"], params["min_transactions"] - 1)
    if grp is None:
        return None
    amounts = [r["amount_usd"] for r in grp]
    channels = collections.Counter(r["channel"] for r in grp)
    return {
        "band_usd": [min(amounts), max(amounts)],
        "in_band_transactions": len(grp),
        "window_days_measured": _day_gap(grp[0]["value_date"],
                                         grp[-1]["value_date"]),
        # Deterministic tie-break: most frequent channel, then alphabetical.
        "channel_used": min(sorted(channels), key=lambda c: (-channels[c], c)),
    }


def _funnel_noise_pattern(subject, in_by_party, params, juris, **_) -> dict | None:
    rows = sorted((r for r in in_by_party.get(subject, ())
                   if r["channel"] == params["channel"]),
                  key=lambda r: (r["value_date"], r["txn_id"]))
    grp = _cluster(rows, NOISE_FUNNEL_WINDOW_DAYS, 2)
    if grp is None:
        return None
    return {
        "deposit_count": len(grp),
        "deposit_locations": sorted({juris[r["from_party"]] for r in grp}),
        "aggregated_out_usd": round(sum(r["amount_usd"] for r in grp), 2),
        "deposit_window_days_measured": _day_gap(grp[0]["value_date"],
                                                 grp[-1]["value_date"]),
    }


def _tbml_noise_pattern(subject, out_by_party, params, **_) -> dict | None:
    shipments: dict[tuple[str, str], list[dict]] = collections.defaultdict(list)
    for r in out_by_party.get(subject, ()):
        if r["channel"] == params["channel"]:
            shipments[(r["to_party"], r["value_date"])].append(r)
    doubled = []
    for key in sorted(shipments):
        amounts = sorted(x["amount_usd"] for x in shipments[key])
        if len(amounts) < 2:
            continue
        variance = max((b - a) / a * 100
                       for a, b in itertools.combinations(amounts, 2) if a > 0)
        doubled.append((key[0], variance))
    if not doubled:
        return None
    importer, _ = max(doubled, key=lambda d: (d[1], d[0]))
    return {
        "shipments": len(doubled),
        "importer": importer,
        "shipment_variance": [{"variance_pct": v} for _, v in doubled],
    }


def _shell_noise_pattern(subject, out_by_party, in_by_party, params, hops,
                          **_) -> dict | None:
    buys = [r for r in out_by_party.get(subject, ())
            if r["channel"] == params["channel"]]
    if not buys:
        return None
    buy = max(buys, key=lambda r: (r["amount_usd"], r["txn_id"]))
    funding = [r for r in in_by_party.get(subject, ())
               if r["txn_id"] != buy["txn_id"]
               and 0 <= (date.fromisoformat(buy["value_date"])
                         - date.fromisoformat(r["value_date"])).days
               <= NOISE_SHELL_FUNDING_LOOKBACK_DAYS]
    if not funding:
        return None
    return {
        "purchase_usd": buy["amount_usd"],
        "funded_by_upstream_transfer_usd": max(r["amount_usd"] for r in funding),
        "ownership_hops": hops.get(subject, 0),
    }


_NOISE_PATTERN_BUILDERS = {
    "TYP-STRUCT": _struct_noise_pattern,
    "TYP-FUNNEL": _funnel_noise_pattern,
    "TYP-TBML": _tbml_noise_pattern,
    "TYP-SHELL": _shell_noise_pattern,
}


def _below_gate(typology_id: str, pattern: dict, params: dict) -> bool:
    """True when the measured features FAIL the typology's own published
    gate -- i.e. this really is a false positive and not an un-injected
    case. Every emitted typology-named noise alert is checked here; a
    candidate that passes its gate is refused, not shipped."""
    if typology_id == "TYP-STRUCT":
        return not (pattern["in_band_transactions"] >= params["min_transactions"]
                    and pattern["band_usd"][0]
                    >= params["threshold_usd"] * params["band_low"]
                    and pattern["window_days_measured"] <= params["window_days"])
    if typology_id == "TYP-FUNNEL":
        return not (len(pattern["deposit_locations"])
                    >= params["min_deposit_locations"]
                    and pattern["deposit_window_days_measured"]
                    <= params["max_window_days"])
    if typology_id == "TYP-TBML":
        worst = max(m["variance_pct"] for m in pattern["shipment_variance"])
        return not (pattern["shipments"] >= params["min_shipments"]
                    and worst >= params["invoice_price_variance_pct"])
    if typology_id == "TYP-SHELL":
        return not (pattern["purchase_usd"] >= params["min_amount_usd"]
                    and pattern["ownership_hops"] >= params["min_ownership_hops"])
    raise KeyError(typology_id)


def _case_involved_parties(cases, txns_by_id) -> dict[str, set[str]]:
    """Per typology, every party that appears in ANY of its cases -- the
    subject, the ownership-chain intermediaries, the named importer, and
    both ends of every transaction the case cites. A typology-named noise
    alert may never land on one of these: a false positive has to be a
    party that genuinely does not exhibit the typology it is named for."""
    involved: dict[str, set[str]] = collections.defaultdict(set)
    for c in cases:
        bucket = involved[c["typology_id"]]
        bucket.add(c["subject_party"])
        pattern = c["pattern"]
        bucket.update(pattern.get("intermediaries", []))
        if isinstance(pattern.get("importer"), str):
            bucket.add(pattern["importer"])
        for txn_id in c["txn_ids"]:
            row = txns_by_id[txn_id]
            bucket.add(row["from_party"])
            bucket.add(row["to_party"])
    return involved


def _relabel_typology_named_noise(noise, ordinary, cases, txns_by_id,
                                   typology_params, juris, hops) -> dict:
    """Rewrite `trigger` on `NOISE_TYPOLOGY_QUOTA` of the drawn noise
    alerts, in place. Returns {typology_id: count} for reporting.

    Deterministic with no randomness: candidates are enumerated over a
    content-sorted view of the noise records, and typologies are filled in
    ASCENDING order of how many candidates each has, so the scarce ones
    (trade-based has the fewest ordinary double invoices) are not starved
    by a greedy earlier typology.
    """
    out_by_party: dict[str, list[dict]] = collections.defaultdict(list)
    in_by_party: dict[str, list[dict]] = collections.defaultdict(list)
    for t in ordinary:
        out_by_party[t["from_party"]].append(t)
        in_by_party[t["to_party"]].append(t)

    involved = _case_involved_parties(cases, txns_by_id)
    order = sorted(range(len(noise)),
                   key=lambda i: (noise[i]["raised_at"],
                                  noise[i]["subject_party"],
                                  noise[i]["trigger"]))

    #: index -> {typology_id: pattern}, for every eligible pairing.
    eligible: dict[int, dict[str, dict]] = {}
    for i in order:
        subject = noise[i]["subject_party"]
        for typology_id, build in sorted(_NOISE_PATTERN_BUILDERS.items()):
            if subject in involved.get(typology_id, ()):
                continue
            params = typology_params[typology_id]
            pattern = build(subject=subject, out_by_party=out_by_party,
                            in_by_party=in_by_party, params=params,
                            juris=juris, hops=hops)
            if pattern is None:
                continue
            if not _below_gate(typology_id, pattern, params):
                continue
            eligible.setdefault(i, {})[typology_id] = pattern

    assigned: dict[int, str] = {}
    counts: dict[str, int] = {}
    remaining = dict(NOISE_TYPOLOGY_QUOTA)
    while remaining:
        supply = {
            typology_id: [i for i in order
                          if i not in assigned and typology_id in eligible.get(i, {})]
            for typology_id in remaining
        }
        typology_id = min(sorted(remaining), key=lambda t: (len(supply[t]), t))
        want = remaining.pop(typology_id)
        picks = supply[typology_id][:want]
        if len(picks) < want:
            raise RuntimeError(
                f"_relabel_typology_named_noise: only {len(picks)} of the "
                f"{want} {typology_id}-named noise alerts the quota asks for "
                "could be placed on an ordinary party that fires the loosened "
                "rule, is below the gate, and is not involved in any case of "
                "that typology -- lower the quota deliberately rather than "
                "letting the tell come back")
        for i in picks:
            assigned[i] = typology_id
            noise[i]["trigger"] = _TRIGGER_BUILDERS[typology_id](
                eligible[i][typology_id])
        counts[typology_id] = len(picks)
    return counts


# --------------------------------------------------------------------------
# alert_id: content-derived, never positional.
# --------------------------------------------------------------------------

def _content_key(rec: dict) -> tuple:
    digest = hashlib.sha256(
        json.dumps(rec, sort_keys=True).encode("utf-8")).hexdigest()
    return (rec["raised_at"], rec["subject_party"], rec["case_id"] or "",
            rec["trigger"], digest)


def _assign_alert_ids(records: list[dict]) -> list[dict]:
    ordered = sorted(records, key=_content_key)
    out = []
    for i, rec in enumerate(ordered, start=1):
        out.append({"alert_id": f"ALT-{i:06d}", **rec})
    return out


# --------------------------------------------------------------------------
# Links -- derived entirely from the assembled, alert_id-bearing records.
# --------------------------------------------------------------------------

def _build_links(alerts: list[dict]) -> list[dict]:
    links = []

    by_case = collections.defaultdict(list)
    for a in alerts:
        if a["case_id"]:
            by_case[a["case_id"]].append(a)
    for case_id, group in sorted(by_case.items()):
        if len(group) < 2:
            continue
        chain = sorted(group, key=lambda a: (a["raised_at"], a["alert_id"]))
        for later, earlier in zip(chain[1:], chain[:-1]):
            links.append({"alert_id": later["alert_id"],
                          "related_alert_id": earlier["alert_id"],
                          "relation": SAME_CASE_RELATION})

    by_subject = collections.defaultdict(list)
    for a in alerts:
        by_subject[a["subject_party"]].append(a)
    for subject, group in sorted(by_subject.items()):
        if len(group) < 2:
            continue
        chain = sorted(group, key=lambda a: (a["raised_at"], a["alert_id"]))
        for later, earlier in zip(chain[1:], chain[:-1]):
            links.append({"alert_id": later["alert_id"],
                          "related_alert_id": earlier["alert_id"],
                          "relation": PRIOR_SUBJECT_RELATION})

    links.sort(key=lambda l: (l["alert_id"], l["related_alert_id"]))
    return links


# --------------------------------------------------------------------------
# Assembly
# --------------------------------------------------------------------------

def generate():
    typologies = json.loads(TYPOLOGIES_PATH.read_text())["typologies"]
    typology_ids = {t["typology_id"] for t in typologies}

    cases = json.loads(CASES_PATH.read_text())["cases"]
    assert len(cases) == 24, f"expected 24 cases, found {len(cases)}"

    parties = json.loads(PARTIES_PATH.read_text())["parties"]
    party_ids = sorted(p["party_id"] for p in parties)
    assert len(party_ids) == 201, f"party population not frozen: {len(party_ids)}"
    party_set = set(party_ids)

    txns = json.loads(TXN_PATH.read_text())["transactions"]
    txns_by_id = {t["txn_id"]: t for t in txns}
    case_txn_ids = {i for c in cases for i in c["txn_ids"]}
    noise_pool = sorted((t for t in txns if t["txn_id"] not in case_txn_ids),
                        key=lambda t: t["txn_id"])
    assert noise_pool, "no non-case transactions to draw noise alerts from"

    ownership = json.loads(OWNERSHIP_PATH.read_text())["bindings"]
    hops = {b["party_id"]: b["reused_chain_depth"] for b in ownership}
    juris = {p["party_id"]: p["jurisdiction"] for p in parties}
    typology_params = {t["typology_id"]: t["params"] for t in typologies}

    rng = Random(SEED)

    genuine = _build_genuine_alerts(cases, txns_by_id)
    noise = _draw_noise_alerts(rng, noise_pool)
    relabelled = _relabel_typology_named_noise(
        noise, noise_pool, cases, txns_by_id, typology_params, juris, hops)

    alerts = _assign_alert_ids(genuine + noise)
    links = _build_links(alerts)

    _verify(alerts, links, cases, party_set, typology_ids)
    return alerts, links, relabelled


def _verify(alerts, links, cases, party_set, typology_ids) -> None:
    """Recompute every claim from the assembled artifact before writing."""
    ids = [a["alert_id"] for a in alerts]
    assert len(ids) == len(set(ids)), "duplicate alert_id"
    import re
    assert all(re.fullmatch(r"ALT-\d{6}", i) for i in ids), "malformed alert_id"

    case_ids = {c["case_id"] for c in cases}
    genuine = [a for a in alerts if a["case_id"]]
    noise = [a for a in alerts if not a["case_id"]]
    assert len(alerts) >= 100, f"only {len(alerts)} alerts"
    assert len(genuine) >= 20, f"only {len(genuine)} genuine alerts"
    assert len(genuine) < len(alerts) * 0.5, (
        "genuine alerts are not a minority -- noise must dominate")
    dangling = [a["alert_id"] for a in genuine if a["case_id"] not in case_ids]
    assert not dangling, f"alerts citing nonexistent cases: {dangling[:5]}"
    assert not noise or all(a["case_id"] is None for a in noise)

    for c in cases:
        hits = [a for a in genuine if a["case_id"] == c["case_id"]]
        assert hits, f"{c['case_id']} has no alert at all"

    for a in alerts:
        assert a["subject_party"] in party_set, (
            f"{a['alert_id']} subject {a['subject_party']} is not a frozen "
            "party")
        assert a["provenance"] == PROVENANCE, a["alert_id"]

    # CT-1. The trigger prefix must not be an exact classifier for
    # "genuine". Recomputed from the assembled set, never from the quota
    # constants -- a quota that silently failed to place its alerts would
    # be caught here rather than in a review six weeks later.
    prefixes = collections.Counter(a["trigger"].split(":", 1)[0] for a in alerts)
    genuine_prefixes = collections.Counter(
        a["trigger"].split(":", 1)[0] for a in genuine)
    best = max(genuine_prefixes,
               key=lambda p: (genuine_prefixes[p] / prefixes[p], p))
    best_precision = genuine_prefixes[best] / prefixes[best]
    assert best_precision < 0.75, (
        f"the trigger prefix {best!r} is precision {best_precision:.3f} for "
        "'genuine' -- a single string match on a field every perspective "
        "receives, which is exactly the tell CT-1 removed")
    named = set(genuine_prefixes)
    combined = sum(genuine_prefixes.values()) / sum(
        prefixes[p] for p in named)
    assert combined < 0.75, (
        f"the four typology prefixes together are precision {combined:.3f} "
        "for 'genuine'")

    # CT-1's stability claim, asserted rather than argued: relabelling a
    # noise trigger must not move any GENUINE alert's content-derived id.
    if OUT_PATH.exists():
        previous = json.loads(OUT_PATH.read_text())["alerts"]
        was = {(a["case_id"], a["subject_party"], a["raised_at"]): a["alert_id"]
               for a in previous if a["case_id"]}
        now = {(a["case_id"], a["subject_party"], a["raised_at"]): a["alert_id"]
               for a in genuine}
        moved = sorted(k for k in was.keys() & now.keys() if was[k] != now[k])
        assert not moved, (
            f"{len(moved)} genuine alert(s) changed alert_id -- "
            "sar_classification.alert_id and aml_alert_link reference them: "
            f"{[(k, was[k], now[k]) for k in moved[:3]]}")

    by_id = {a["alert_id"]: a for a in alerts}
    for l in links:
        assert l["alert_id"] in by_id, f"link references unknown {l['alert_id']}"
        assert l["related_alert_id"] in by_id, (
            f"link references unknown {l['related_alert_id']}")
        assert l["alert_id"] != l["related_alert_id"], "self-link"
        assert l["relation"] in ALLOWED_RELATIONS, l["relation"]
        a, rel = by_id[l["alert_id"]], by_id[l["related_alert_id"]]
        if l["relation"] == SAME_CASE_RELATION:
            assert a["case_id"] and a["case_id"] == rel["case_id"]
            assert a["subject_party"] != rel["subject_party"], (
                "same_case_prior_alert connected two alerts on the SAME "
                "subject -- that is prior_alert_on_subject's job")
        else:
            assert a["subject_party"] == rel["subject_party"]
        assert rel["raised_at"] <= a["raised_at"], (
            f"{l['related_alert_id']} is not chronologically prior to "
            f"{l['alert_id']}")


def main() -> int:
    alerts, links, relabelled = generate()

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps({"alerts": alerts, "links": links},
                   indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8")

    genuine = [a for a in alerts if a["case_id"]]
    noise = [a for a in alerts if not a["case_id"]]
    per_case = collections.Counter(a["case_id"] for a in genuine)
    by_relation = collections.Counter(l["relation"] for l in links)

    print(f"Wrote {len(alerts)} alerts to {OUT_PATH}")
    print(f"  genuine: {len(genuine)} ({len(genuine)/len(alerts):.1%}), "
          f"noise: {len(noise)} ({len(noise)/len(alerts):.1%})")
    print(f"  cases with exactly 1 alert: "
          f"{sum(1 for v in per_case.values() if v == 1)}, "
          f"cases with 2 alerts: {sum(1 for v in per_case.values() if v == 2)}")
    print(f"Wrote {len(links)} links: {dict(sorted(by_relation.items()))}")

    # CT-1: precision of the best single trigger-prefix rule, measured on
    # the artifact just written.
    prefixes = collections.Counter(a["trigger"].split(":", 1)[0] for a in alerts)
    gen_prefixes = collections.Counter(
        a["trigger"].split(":", 1)[0] for a in genuine)
    print(f"  typology-named noise: {dict(sorted(relabelled.items()))}")
    print("  trigger-prefix precision for 'genuine':")
    for prefix in sorted(prefixes):
        hit = gen_prefixes.get(prefix, 0)
        print(f"    {prefix:<28} {hit:>3} genuine / "
              f"{prefixes[prefix] - hit:>3} noise  "
              f"precision {hit / prefixes[prefix]:.3f}")
    named = set(gen_prefixes)
    print(f"  best single-prefix rule: "
          f"{max(gen_prefixes, key=lambda p: (gen_prefixes[p] / prefixes[p], p))}"
          f" at {max(gen_prefixes[p] / prefixes[p] for p in named):.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
