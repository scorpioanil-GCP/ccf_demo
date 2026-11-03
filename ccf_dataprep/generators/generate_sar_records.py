#!/usr/bin/env python3
"""Wave 17 Task 15 -- SAR narratives and their confidentiality classification.

Envelope floor 4. This is the reason the departmental SQLite store exists in
this architecture at all: the classification of a filed Suspicious Activity
Report is exactly the kind of enterprise-critical, narrowly-held policy fact
CLAUDE.md's SQLite section describes -- a small, locally-maintained system the
fabric must reach to enforce it. If the classification also lived in
Postgres, nothing would force a reach into the departmental store and the
demonstration would collapse. See `docs/wave17-plan.md` Task 15 and Global
Constraints.

## What this produces

**Not** one SAR per case. Coordinator review (fix round 2) caught a defect
in the original 1:1 version: with all 24 engineered cases filing a SAR,
`ex:matchesTypology` (Task 16's `l1`-visible `typology_pattern_summary`
element) let `l1` infer, with certainty, "this party's case has a filed
SAR" from nothing but the edge's existence -- an inference route is exactly
the "indication of existence" the brief's confidentiality property forbids,
even with every SAR *field* correctly hidden from `l1`. See
`docs/wave17-plan.md` Task 15 and `docs/known-issues.md` #30, which is
the durable record of both rejected designs (the SDD `task-15-report.md`
this used to cite is deleted when the wave closes).

**Fix round 3 (coordinator ruling).** Fix round 2 selected the filing
half by `case_exposure_usd` -- a materiality ranking that SOUNDED safe but
was not: `l1`'s own projection plan (`alert_core_facts`) exposes
`aml_alert.trigger`, and `trigger`'s text states the very transaction
counts and dollar amounts that ranking used. Measured against the loaded
estate, that let an `l1` reader recover the filing decision with certainty
for 20 of the 24 cases, and the rule was even stated verbatim in every
SAR's own `filing_rationale`. An edge-existence inference route had been
closed by opening a value-correlation one -- weakened, not broken.

The fix is a **deterministic content digest**, chosen specifically because
it can be constructed to carry NO relationship to anything `l1` can see
(`trigger`, `raised_at`, transaction facts, the typology, the OFAC
screening result) -- a property that must be engineered by construction,
not discovered by measuring some plausible-sounding business rule and
hoping it comes out uncorrelated. `select_filed_case_ids()` hashes each
`case_id` with a fixed salt (`FILING_DIGEST_SALT`), sorts each typology's 6
cases by that digest, and keeps the first half. The per-typology split is
unchanged from fix round 2 and is still doing real work: it is what stops
the typology name ITSELF becoming a discriminator (a global, un-scoped
selection would have let SHELL/TBML "always file" or "never file" gate the
same inference one level up). 12 of 24 cases file a SAR; 12 do not.
Verified interleaved, not merely assumed -- see `docs/known-issues.md`
#30 for the actual filed/unfiled values, per typology, for every quantity
`l1` can extract.

`filing_rationale` states this honestly: the selection is a
`synthetic — engineered` device (CLAUDE.md's third provenance class --
"invented deliberately to create a condition public data will not
supply"), deliberately uncorrelated with any first-line-visible signal by
construction, and is NOT a materiality or business rule. Fix round 2's
`case_exposure_usd` field was carried on each record for a while after
that, as "case-fact metadata" with a warning label; the whole-branch
review (CT-8) removed it. It had no consumer, it was a derived aggregate
of Postgres-owned transaction amounts sitting in a Mongo document, and the
only reason it needed a warning label was that its presence misled. The
FUNCTION survives, unused by the record builder, because the salt comment
below names it as the quantity the rejected design ranked on.

Each surviving SAR is anchored to its case's PRIMARY genuine alert (the
alert on the case's own `subject_party`, carrying that `case_id` -- see
`generators/generate_aml_alerts.py`). A SAR on a noise alert (no `case_id`)
would be incoherent, per the brief, so this generator only ever resolves
alerts that already carry one.

Each SAR carries a `classification` and a `visible_to_perspectives` set drawn
from the three perspectives Task 16 builds projection plans for: `l1`
(front-line / relationship), `l2` (compliance analyst), `examiner`
(regulatory). TYP-SHELL cases -- beneficial-ownership concealment, the most
sensitive pattern this envelope models -- are classified `confidential` and
visible to `examiner` ONLY. Every other typology is `restricted`: visible to
`l2` and `examiner`, but never `l1`. `l1` is excluded from every single SAR
regardless of typology, which is the point: in many jurisdictions disclosing
that a SAR exists at all is itself an offence ("tipping off"), and the
front-line relationship perspective is precisely the one that must never see
an indication that a filing occurred. Task 16 and 17 build the projection
plan and the recomputed-live floor that prove no SAR *field* reaches `l1` --
this generator only needs to make that property TRUE of the data, not prove
it (that is Task 17's job, over the loaded stores).

## Provenance

`synthetic — internal`, both for the narrative text and the classification.
SAR filings are bank-internal by nature (CLAUDE.md's three-class rule);
nothing here is fetched from a public source.

## The name guard, applied correctly

`ccf.aml.RealNameIndex.blocks()` compares ONE NAME against 72,869 indexed
real names -- feeding it a whole narrative paragraph would compare the
paragraph as a single string and prove nothing (Task 5's module docstring).
This generator never needs to *call* the guard itself: every entity name a
narrative can contain comes from `wave17_parties.json`'s frozen 201-party
set, which already passed `blocks()` at Task 6 generation time and is
re-checked at every subsequent wave. What this generator must not do is
introduce a NEW proper name of its own -- so the template's own fixed
non-party vocabulary is kept to exactly one phrase, `ALLOWED_VOCAB` below,
and `validators/test_aml_typology.py` runs the actual guard over that finite
set (plus a regex sweep of the finished text, to catch anything the
template might introduce by accident) rather than over free text.

## Determinism and IDs

No randomness is used -- every field is derived deterministically from the
frozen case/alert/party artifacts. `sar_id` follows this estate's standard
positional-identity-avoidance pattern (`generate_aml_alerts.py`'s own
docstring): cases are sorted by their own content (`case_id`, already a
stable natural key) BEFORE numbering, never numbered in whatever order a
loop happens to visit them. Re-running this script over the same (frozen)
inputs produces byte-identical output.

    uv run generators/generate_sar_records.py --dry-run
    uv run generators/generate_sar_records.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date, timedelta

from ccf.config import REPO_ROOT
from generators.generate_aml_transactions import AS_OF_AML

SCREEN = REPO_ROOT / "sources" / "screening"
CASES_PATH = SCREEN / "wave17_cases.json"
ALERTS_PATH = SCREEN / "wave17_alerts.json"
PARTIES_PATH = SCREEN / "wave17_parties.json"
TXN_PATH = SCREEN / "wave17_transactions.json"  # read-only; never modified
OUT_PATH = SCREEN / "wave17_sar_records.json"

#: A SAR is filed only for half of each typology's 6 cases -- see
#: `select_filed_case_ids()`. `1, 2` means "keep 1/2", i.e. 3 of 6;
#: expressed as a fraction (not a hardcoded "3") so the rule states its own
#: intent if the per-typology case count ever changes.
FILING_FRACTION_NUM = 1
FILING_FRACTION_DEN = 2

#: Fixed salt for the filing-selection digest (fix round 3). MUST NEVER
#: change: changing it would silently reassign which cases file, which
#: would in turn break every test and report that names a specific filed
#: or unfiled case_id/party. There is no security property here -- this is
#: not a secret, it is a constant chosen once so the digest is reproducible
#: forever, the same way FILING_LAG_DAYS or SEED constants elsewhere in
#: this wave are fixed rather than re-rolled per run.
#:
#: **Why this literal string, not the first one tried.** The digest
#: mechanism is uncorrelated with every l1-visible quantity BY
#: CONSTRUCTION -- a hash has no relationship to its input's magnitude or
#: any other property of the record it names. But with only 6 cases per
#: typology, some SPECIFIC realization of "which 3 land in the top half"
#: can still coincide with an existing pattern in the (fixed, given) case
#: data purely by chance -- e.g. a value that only appears twice in a
#: typology's 6 cases landing on the same side both times, about a 1-in-5
#: chance for a generic 2-of-6 pair under a 3-of-6 split. That happened on
#: the first candidate string tried here (TYP-SHELL and TYP-TBML each
#: showed a discrete case attribute -- ownership_hops, shipment count --
#: landing entirely on one side). This is NOT "picking a salt whose
#: correlation happens to look clean" (the failure mode fix round 2 made
#: with a MEASURED ranking) -- the mechanism never depends on any
#: case attribute either way, so no choice of salt can introduce a
#: designed relationship. It is closer to discarding an unlucky die roll:
#: several literal strings were tried and checked against every
#: l1-reconstructable quantity (trigger's embedded transaction/shipment
#: counts and dollar amounts, case_exposure_usd, raised_at) for a clean or
#: repeated one-sided split, and this is the first one where none of the 4
#: typologies showed one. See `docs/known-issues.md` #30 for the full
#: per-typology numbers this was checked against, and for what floor 4's
#: PASS line does and does not establish given that this salt was chosen
#: against the same quantities floor 4 recomputes.
FILING_DIGEST_SALT = "ccf-wave17-sar-filing"

PROVENANCE = "synthetic — internal"

FILING_LAG_DAYS = 5  # SAR filed this many days after the triggering alert

TYPOLOGY_LABEL = {
    "TYP-STRUCT": "structuring",
    "TYP-FUNNEL": "funnel account activity",
    "TYP-SHELL": "shell company ownership concealment",
    "TYP-TBML": "trade-based value transfer",
}

#: TYP-SHELL (beneficial-ownership concealment) is the most sensitive
#: pattern modeled -- examiner-only. Every other typology defaults to
#: `DEFAULT_CLASSIFICATION` below. `l1` never appears in ANY set: that is
#: the blind perspective the envelope floor requires.
CLASSIFICATION: dict[str, tuple[str, list[str]]] = {
    "TYP-SHELL": ("confidential", ["examiner"]),
}
DEFAULT_CLASSIFICATION: tuple[str, list[str]] = ("restricted", ["l2", "examiner"])

#: Fixed, non-party proper-noun-shaped phrases this generator's own template
#: deliberately introduces -- finite and known, so the name guard (Task 5)
#: can be run over exactly this set rather than over free text. If a future
#: edit to `_narrative_body` or the preamble introduces a new capitalized
#: multi-word phrase, add it here deliberately (and it will be guard-checked
#: by `validators/test_aml_typology.py`) rather than letting it slip through
#: unexamined.
ALLOWED_VOCAB = frozenset({"Suspicious Activity Report"})


def _load(path):
    return json.loads(path.read_text())


def case_exposure_usd(case: dict, txn_amounts: dict[str, float]) -> float:
    """Aggregate USD moved across a case's own cited transactions.

    **Nothing calls this any more, and that is the point.** Fix round 2
    ranked cases by this quantity to decide which filed a SAR; fix round 3
    REMOVED that ranking, because `l1`'s own projection plan exposes
    `aml_alert.trigger`, whose text states the very transaction counts and
    dollar amounts the ranking used -- measured at 20 of 24 cases
    recoverable with certainty. `select_filed_case_ids()` now uses a
    content digest instead. Whole-branch review CT-8 then removed the
    residual `case_exposure_usd` FIELD from the emitted records too: it had
    no consumer and misled anyone auditing the filing property.

    The function is kept deliberately, and only, so `FILING_DIGEST_SALT`'s
    comment has something concrete to point at when it names the design
    that was rejected. Do not reintroduce it into the filing decision, into
    a record, or into any store: it is a derived aggregate of
    Postgres-owned transaction amounts, and it is recoverable from
    `wave17_transactions.json` by anyone who wants it."""
    return sum(txn_amounts[t] for t in case["txn_ids"])


def filing_digest(case_id: str) -> str:
    """A stable hash of `case_id` salted with `FILING_DIGEST_SALT`,
    hex-encoded. Deliberately CONSTRUCTED to have no relationship to
    anything derived from the case's own transactions, alert trigger text,
    typology, or any other content -- sha256 output does not correlate with
    its input's magnitude, timing, or any other property, which is the
    whole reason this replaces a measured "materiality" ranking (fix round
    2's mistake) rather than refining one. `case_id` is the only input:
    stable, content-derived, never a row's position."""
    return hashlib.sha256(f"{FILING_DIGEST_SALT}:{case_id}".encode()).hexdigest()


def select_filed_case_ids(cases: list[dict]) -> set[str]:
    """Which cases get a SAR filed.

    Coordinator ruling (fix round 2): filing a SAR for every case that
    matched a typology let `l1` infer, from the mere existence of a Fluree
    `ex:matchesTypology` edge, that a SAR must exist. Fix round 2's
    materiality-by-exposure ranking closed that route but opened another:
    `l1`'s own plan exposes `aml_alert.trigger`, whose text states the same
    transaction counts and dollar amounts the ranking used, so the filing
    decision was recoverable from data `l1` can already see (coordinator
    ruling, fix round 3 -- measured at 20/24 cases recoverable with
    certainty).

    The fix here is a **content digest, uncorrelated by construction**: a
    cryptographic hash of `case_id` has no relationship to the case's
    transactions, alert, typology, or anything else, by the definition of
    what a hash function does, so there is nothing left for `l1` to
    recover it from. Within each of the 4 typologies (still scoped
    per-typology, exactly as fix round 2 established -- this is what stops
    the typology ITSELF from becoming a discriminator: a global,
    un-scoped digest ranking risks one typology's cases clustering
    unevenly, and per-typology scoping keeps the 3-of-6 split exact and
    typology-blind either way), cases are sorted by `filing_digest(case_id)`
    and the first half is kept.

    **What that does NOT mean** (whole-branch review, CT-4). An earlier
    wording here said "no measured quantity was checked for correlation
    and found clean by luck." That is false as written, and
    `FILING_DIGEST_SALT`'s own comment above says so plainly: several
    literal salts were tried, each checked against every
    `l1`-reconstructable quantity, and the first with no one-sided split
    was kept. The distinction the salt comment draws is real and worth
    reading -- the MECHANISM cannot carry a designed relationship whichever
    salt is chosen, so this is not fix round 2's mistake repeated -- but
    the SPECIFIC realisation was selected against measurements, not merely
    accepted as it fell.

    The substantive consequence, stated where an auditor will meet it:
    `validators/aml_typology.py`'s floor 4, sub-condition 4 recomputes the
    same quantities this salt was selected against. The instrument and the
    data were, in part, tuned to each other. Floor 4 can still fail -- its
    poison tests are real, and it recomputes from the stores rather than
    reading anything written here -- but a reader of its PASS line should
    know the property was partly ARRANGED rather than wholly DISCOVERED.
    Floor 4's own docstring carries the same note.

    Deterministic and content-derived: the sort key is `(filing_digest(
    case_id), case_id)` -- the trailing `case_id` is a tie-break for the
    astronomically unlikely case of a hash collision, never a case's
    position in whatever list it arrived in. Returns the set of filed
    `case_id` values; carries no order of its own -- callers sort by
    `case_id` again before numbering, same as before.
    """
    by_typology: dict[str, list[dict]] = {}
    for c in cases:
        by_typology.setdefault(c["typology_id"], []).append(c)

    filed: set[str] = set()
    for typology_id in sorted(by_typology):
        group = by_typology[typology_id]
        ranked = sorted(
            group,
            key=lambda c: (filing_digest(c["case_id"]), c["case_id"]),
        )
        n_file = max(1, len(ranked) * FILING_FRACTION_NUM // FILING_FRACTION_DEN)
        filed.update(c["case_id"] for c in ranked[:n_file])
    return filed


def _narrative_body(typology_id: str, pattern: dict, subject_name: str,
                     names: dict[str, str]) -> str:
    """The typology-specific paragraph. Every number comes from the case's
    own `pattern` dict -- never a hardcoded copy of a typology's params --
    so a case that drifted from its typology would still describe what
    actually happened. Kept deliberately lower-case throughout (aside from
    party names, which are inserted verbatim) so no incidental two-word
    capitalized span is introduced -- see the module docstring's name-guard
    section and the corresponding test."""
    if typology_id == "TYP-STRUCT":
        lo, hi = pattern["band_usd"]
        channel = pattern["channel_used"].replace("_", " ")
        return (
            f"over a {pattern['window_days_measured']} day window, "
            f"{subject_name} conducted {pattern['in_band_transactions']} "
            f"{channel} transactions, each between ${lo:,.0f} and "
            f"${hi:,.0f}, consistently below the $10,000 currency "
            f"transaction reporting threshold -- consistent with "
            f"structuring to avoid currency transaction reporting."
        )
    if typology_id == "TYP-FUNNEL":
        locations = ", ".join(pattern["deposit_locations"])
        return (
            f"over a {pattern['deposit_window_days_measured']} day window, "
            f"{pattern['deposit_count']} cash deposits originating from "
            f"{locations} were made into an account associated with "
            f"{subject_name}, aggregating "
            f"${pattern['aggregated_out_usd']:,.2f} before rapid "
            f"consolidated outbound transfer -- consistent with funnel "
            f"account activity concentrating geographically dispersed "
            f"deposits ahead of aggregated withdrawal."
        )
    if typology_id == "TYP-SHELL":
        seller_name = names[pattern["seller"]]
        intermediary_names = "; ".join(names[i] for i in pattern["intermediaries"])
        financing_note = (
            "no linked financing was used" if not pattern["financing_leg"]
            else "a linked financing leg was also identified"
        )
        return (
            f"{subject_name} purchased an asset for "
            f"${pattern['purchase_usd']:,.2f}, funded by an upstream "
            f"transfer of ${pattern['funded_by_upstream_transfer_usd']:,.2f} "
            f"routed through {pattern['ownership_hops']} layer(s) of "
            f"ownership involving {intermediary_names} before reaching "
            f"{seller_name} as seller; {financing_note}. the layered "
            f"ownership structure obscures the ultimate beneficial owner "
            f"of the funds used in the purchase -- consistent with shell "
            f"company ownership concealment."
        )
    if typology_id == "TYP-TBML":
        importer_name = names[pattern["importer"]]
        max_var = max(s["variance_pct"] for s in pattern["shipment_variance"])
        return (
            f"{subject_name} was party to {pattern['shipments']} shipments "
            f"with a counterparty ({importer_name}) in which invoiced "
            f"values diverged from expected shipment value by as much as "
            f"{max_var:.1f} percent, with double-invoiced documentation -- "
            f"consistent with trade-based value transfer used to move "
            f"value outside formal banking channels."
        )
    raise ValueError(f"unknown typology_id {typology_id!r}")


def build_sar_records() -> list[dict]:
    """Pure function over the frozen case/alert/party/transaction artifacts
    -> the finished, deterministically-ordered SAR record list. Never
    touches any store and never writes `wave17_cases.json`,
    `wave17_transactions.json`, or any other pre-existing artifact --
    read-only over all four inputs.

    Only the cases `select_filed_case_ids()` selects produce a record --
    see that function's docstring for why coverage is a proper subset of
    the 24 cases, not all of them.
    """
    cases = _load(CASES_PATH)["cases"]
    alerts = _load(ALERTS_PATH)["alerts"]
    parties = _load(PARTIES_PATH)["parties"]
    names = {p["party_id"]: p["legal_name"] for p in parties}
    # `wave17_transactions.json` is no longer read here. It was, to compute
    # `case_exposure_usd` for the record; CT-8 removed that field and
    # nothing else in a SAR record derives from a transaction row (every
    # number in the narrative comes from the case's own `pattern`).
    # `TXN_PATH` is still checked for existence in `main()`, because a run
    # against a half-built estate should still refuse rather than emit
    # narratives for cases whose transactions were never generated.

    alerts_by_case: dict[str, list[dict]] = {}
    for a in alerts:
        if a.get("case_id"):
            alerts_by_case.setdefault(a["case_id"], []).append(a)

    filed_case_ids = select_filed_case_ids(cases)
    cases_by_id = {c["case_id"]: c for c in cases}

    records = []
    # Sort by case_id -- a stable, content-derived natural key -- BEFORE
    # numbering. sar_id must never depend on the order this loop happens to
    # visit records in; see generate_aml_alerts.py's own docstring for the
    # same discipline applied to alert_id. Iterating only the FILED subset
    # (sorted) is what keeps numbering content-derived even though the
    # subset itself now depends on a computed ranking rather than "all 24".
    for case_id in sorted(filed_case_ids):
        case = cases_by_id[case_id]
        candidates = alerts_by_case.get(case_id, [])
        primary = next(
            (a for a in candidates if a["subject_party"] == case["subject_party"]),
            None,
        )
        if primary is None:
            # Every one of the 24 cases has a primary alert on its own
            # subject_party (verified against the live artifact); a case
            # missing one would mean the Task 12 alert generator and this
            # generator have drifted apart, not that this SAR should be
            # silently skipped.
            raise RuntimeError(
                f"{case_id} has no primary alert on subject_party "
                f"{case['subject_party']} -- cannot file an incoherent SAR")

        subject_name = names[case["subject_party"]]
        typology_id = case["typology_id"]
        classification, visible = CLASSIFICATION.get(
            typology_id, DEFAULT_CLASSIFICATION)

        text = (
            "Suspicious Activity Report narrative. Internal alert "
            f"{primary['alert_id']} (case {case_id}) matched typology "
            f"{typology_id} ({TYPOLOGY_LABEL[typology_id]}). subject: "
            f"{subject_name} (internal party {case['subject_party']}). "
            + _narrative_body(typology_id, case["pattern"], subject_name, names)
            + " this narrative is filed as a suspicious activity report; "
              "its existence is confidential, and in many jurisdictions "
              "disclosure of that fact is itself an offense."
        )

        filed_at = min(
            (date.fromisoformat(primary["raised_at"])
             + timedelta(days=FILING_LAG_DAYS)).isoformat(),
            AS_OF_AML,
        )

        records.append({
            "case_id": case_id,
            "alert_id": primary["alert_id"],
            "subject_party": case["subject_party"],
            "typology_id": typology_id,
            "classification": classification,
            "visible_to_perspectives": visible,
            "filed_at": filed_at,
            "text": text,
            "provenance": PROVENANCE,
            "filing_rationale": (
                f"synthetic — engineered selection (CLAUDE.md's third "
                f"provenance class): {case_id} was chosen to file by "
                f"filing_digest(case_id) landing in the lower half of "
                f"{typology_id}'s 6 cases, salted with FILING_DIGEST_SALT. "
                f"This is deliberately NOT a materiality or business rule "
                f"-- it is constructed to carry no relationship to the "
                f"case's aggregate transaction exposure, the alert trigger "
                f"text, raised_at, or any other quantity an analyst-facing "
                f"view can extract, so that which cases file cannot be "
                f"inferred from a first-line (l1) perspective. See "
                f"generate_sar_records.py select_filed_case_ids() and "
                f"docs/known-issues.md #30."
            ),
        })

    for i, rec in enumerate(records):
        rec["sar_id"] = f"SAR-{i + 1:04d}"

    return records


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    for path in (CASES_PATH, ALERTS_PATH, PARTIES_PATH, TXN_PATH):
        if not path.exists():
            print(f"missing {path} -- run the earlier Wave 17 tasks first")
            return 1

    all_cases = _load(CASES_PATH)["cases"]
    records = build_sar_records()

    filed_ids = {r["case_id"] for r in records}
    unfiled = sorted(c["case_id"] for c in all_cases if c["case_id"] not in filed_ids)

    n_confidential = sum(1 for r in records if r["classification"] == "confidential")
    n_restricted = len(records) - n_confidential
    typologies = sorted({r["typology_id"] for r in records})

    print("Wave 17 Task 15 — generate SAR records\n")
    print(f"  {len(all_cases)} cases total, {len(records)} filed a SAR, "
          f"{len(unfiled)} closed without one")
    print(f"  filed across {len(typologies)} typologies ({', '.join(typologies)})")
    print(f"  {n_confidential} confidential (examiner-only), "
          f"{n_restricted} restricted (l2 + examiner)")
    print("  l1 excluded from every single record (0 of "
          f"{len(records)} visible_to_perspectives sets include l1)")
    print(f"  cases with NO SAR (breaks the matchesTypology -> SAR "
          f"inference): {', '.join(unfiled)}")
    assert not any("l1" in r["visible_to_perspectives"] for r in records), (
        "l1 must never appear in any SAR's visible_to_perspectives")
    assert len(records) >= 3, "envelope floor: >= 3 SARs"
    assert unfiled, "coverage must be a proper subset -- some case must have no SAR"

    if args.dry_run:
        print("\n  DRY RUN — nothing written.")
        return 0

    OUT_PATH.write_text(
        json.dumps({"sar_count": len(records), "sars": records,
                     "provenance": PROVENANCE},
                   indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"\n  wrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
