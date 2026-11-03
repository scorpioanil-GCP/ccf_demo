#!/usr/bin/env python3
"""Wave 17 Task 4 — derive the four typology structural patterns from Task 3's
Mongo passages, and bind the vocabulary those patterns need before any later
task generates against it.

For each typology named in `sources/fincen/selection.json`, this locates the
passage within ITS OWN advisory that states the laundering MECHANISM (not a
filing-threshold aside, not a footnote), and attaches the structural
parameters `generators/inject_aml_cases.py` (Task 10) will build synthetic
cases against.

## Passage selection is keyword-scored, not hand-picked by id

A hardcoded `passage_id` would be a positional reference dressed as content —
exactly the "keyed to a row's position" failure this estate has recorded
before, except here the position is "the id I happened to read off a
printout" rather than a row index. Instead, every passage in the typology's
advisory is scored by how many of a small, typology-specific set of mechanism
keywords it contains (regex, case-insensitive), a `shell_company_ownership`-
only exclusion list subtracts heavily for GTO/dollar-trigger language (the
controller ruling below), and the highest-scoring passage wins — ties broken
on `passage_id` text so the choice is reproducible from the corpus alone.
Measured against the live corpus while writing this: the four scores separate
cleanly (2/1/0, 4/3/2, 3/0/0, 4/2/1) — no typology's answer is a coin flip.

## The `shell_company_ownership` controller ruling

`shell_company_ownership` replaced `rapid_pass_through` in Task 1 (FinCEN
publishes no advisory on the latter). Its advisory, FIN-2017-A003, states the
mechanism through a residential-real-estate case study, and this estate models
no property register. So the passage picked here is the one stating the
MECHANISM — a shell company formed without disclosing its beneficial owner —
never a passage about GTO filing thresholds or Form 8300's $10,000 trigger,
which describe a reporting regime this estate does not model. The exclusion
list encodes that choice structurally rather than leaving it to be re-derived
by eye next time this script runs.

`params["abstracted_from_advisory"]` says this in the artifact itself: the
advisory's own case is real estate, this estate exhibits the concealment
mechanism with the asset class abstracted, and no property entities, deeds,
or GTO thresholds are fabricated to manufacture a real-estate domain nothing
else in this wave uses.

## `params_source` / `params_locator`: which numbers are read off the page,
which are chosen, and where the page says so

Per typology, `params_source` maps every structural key to `"advisory"` (the
advisory states this number, e.g. the BSA's $10,000 CTR / funnel-account
threshold) or `"chosen"` (no such number is stated in the text; this estate
picked one and says so here). Presenting a chosen number as though the
advisory stated it is the exact failure the brief warns against — this field
exists so nothing downstream has to take the number's provenance on faith.

Every key labelled `"advisory"` also gets a `params_locator` entry: the
`passage_id` where the value is ACTUALLY stated. This may differ from the
typology's main `passage_id` (the one anchoring the mechanism) --
`funnel_account`'s mechanism definition never states a dollar figure; its
$10,000 is stated three passages later, in the "Typical steps" walkthrough.
Citing the mechanism passage for the number too would be a citation that
resolves to unrelated text -- the exact failure `test_every_typology_cites_a_resolvable_passage`
exists to catch, just one level down (per-parameter rather than
per-typology). `test_advisory_labelled_params_are_grounded_in_a_real_passage`
resolves every locator against Mongo and asserts the value's text actually
appears there.

## New vocabulary bound, not yet asserted

`ex:Typology`, `ex:TypologyPattern`, `ex:matchesTypology`, `ex:transactedWith`,
`ex:AMLParty`, `ex:FilingPosture`, `ex:DispositionRule`,
`ex:postureEffectiveFrom`, `ex:permitsDisposition`, `ex:anchoredToPassage` are
bound in `docs/ccf_dataprep_v2.md` (Wave 17 section) BEFORE this script's
output is used by anything. None has a Fluree/Postgres writer yet — per
`docs/wave17-plan.md`, Tasks 13-14 are what assert them. Binding ahead of the
writer is deliberate: CLAUDE.md's rule is "bind upstream, verify, generate,
then flag the mirror," not "bind once something already writes it."

**`ex:Alert` is deliberately NOT in this list.** §C assigns alert records to
Postgres; Task 12 keeps them there (`aml_alert` / `aml_alert_link`) with no
Fluree representation. A Postgres-owned element gets no RDF class -- the same
rule Task 3's own note already applied ("this task writes only MongoDB rows
... no Fluree types or predicates, so the binding table ... [is] untouched").
An earlier cut of this task bound `Alert` anyway; corrected on review, see
`docs/known-issues.md` #25.

Output: sources/screening/wave17_typologies.json

Run: uv run generators/derive_typology_patterns.py
"""
from __future__ import annotations

import json
import re
import sys

from ccf.config import REPO_ROOT, mongo_db

SELECTION = REPO_ROOT / "sources" / "fincen" / "selection.json"
ARTIFACT = REPO_ROOT / "sources" / "screening" / "wave17_typologies.json"

#: typology -> (typology_id, mechanism keywords to score UP, keywords to
#: score DOWN). Exclusion is only non-empty for `shell_company_ownership`
#: (the controller ruling); the other three advisories carry no reporting-
#: regime aside strong enough to need steering away from.
TYPOLOGY_KEYWORDS: dict[str, dict] = {
    "structuring": {
        "typology_id": "TYP-STRUCT",
        "include": [r"\$10,000", r"break(?:ing)?\s+up"],
        "exclude": [],
    },
    "funnel_account": {
        "typology_id": "TYP-FUNNEL",
        "include": [r"funnel account", r"geographic area", r"cash deposits",
                    r"withdraw"],
        "exclude": [],
    },
    "trade_based": {
        "typology_id": "TYP-TBML",
        "include": [r"misrepresenting the price", r"over and under invoicing",
                    r"double invoicing"],
        "exclude": [],
    },
    "shell_company_ownership": {
        "typology_id": "TYP-SHELL",
        "include": [r"shell compan", r"beneficial owner", r"mailing address",
                    r"anonymity"],
        # The controller ruling: never let the GTO / Form 8300 reporting
        # regime outscore the concealment-mechanism passage.
        "exclude": [r"geographic targeting order", r"\bGTOs?\b",
                    r"form 8300", r"\$10,000"],
    },
}

#: Structural parameters per typology. Every key is labelled in the sibling
#: `params_source` dict as "advisory" (the number is stated in the text) or
#: "chosen" (this estate picked it and says so).
PARAMS: dict[str, dict] = {
    "structuring": {
        "threshold_usd": 10000,
        "band_low": 0.80,
        "band_high": 0.99,
        "min_transactions": 4,
        "window_days": 10,
        "abstracted_from_advisory": (
            "the advisory's own case is casino patrons and personnel "
            "(\"Structuring by Casino Patrons and Personnel\"); this "
            "estate exhibits the threshold-avoidance mechanism with the "
            "casino setting abstracted"
        ),
    },
    "funnel_account": {
        "threshold_usd": 10000,
        "min_deposit_locations": 2,
        "max_window_days": 5,
        "channel": "cash_deposit_geographic_dispersion",
    },
    "trade_based": {
        "invoice_price_variance_pct": 30,
        "min_shipments": 2,
        "channel": "over_under_invoicing",
        "double_invoice": True,
    },
    "shell_company_ownership": {
        "min_ownership_hops": 2,
        "channel": "asset_purchase",
        "min_amount_usd": 500000,
        "financing_leg": False,
        "abstracted_from_advisory": (
            "the advisory's own case is residential real estate; this "
            "estate models no property register, so the concealment "
            "mechanism is exhibited with the asset class abstracted"
        ),
    },
}

PARAMS_SOURCE: dict[str, dict] = {
    "structuring": {
        "threshold_usd": "advisory",
        "band_low": "chosen",
        "band_high": "chosen",
        "min_transactions": "chosen",
        "window_days": "chosen",
        "abstracted_from_advisory": "narrative",
    },
    "funnel_account": {
        "threshold_usd": "advisory",
        "min_deposit_locations": "chosen",
        "max_window_days": "chosen",
        "channel": "chosen",
    },
    "trade_based": {
        "invoice_price_variance_pct": "chosen",
        "min_shipments": "chosen",
        "channel": "chosen",
        "double_invoice": "chosen",
    },
    "shell_company_ownership": {
        "min_ownership_hops": "chosen",
        "channel": "chosen",
        "min_amount_usd": "chosen",
        "financing_leg": "chosen",
        # Not a structural threshold -- a disclosure about scope, not a
        # number to source. Recorded here for completeness, not scored.
        "abstracted_from_advisory": "narrative",
    },
}


#: keys labelled `"advisory"` in PARAMS_SOURCE -> the passage_id where that
#: value is ACTUALLY stated. May differ from the typology's main cited
#: passage (the mechanism passage) -- e.g. funnel_account's mechanism
#: definition never states a dollar figure; the $10,000 is three passages
#: later, in the "Typical steps" walkthrough. Only advisory-labelled keys
#: get an entry here; a "chosen" value has nothing in the text to locate.
PARAMS_LOCATOR: dict[str, dict] = {
    "structuring": {
        "threshold_usd": "fincen-advisory-fin-2009-a003#f86ed792d5f4",
    },
    "funnel_account": {
        "threshold_usd": "fincen-advisory-fin-2014-a005#cca080fb109e",
    },
    "trade_based": {},
    "shell_company_ownership": {},
}


def best_passage(db, advisory_number: str, cfg: dict) -> dict:
    """The highest-scoring passage in `advisory_number`, per `cfg`'s keyword
    lists. Ties broken on `passage_id` text -- deterministic, content-keyed,
    never positional."""
    candidates = list(db.passage.find({"advisory_number": advisory_number}))
    if not candidates:
        raise RuntimeError(f"no passages loaded for {advisory_number} -- "
                            f"run loaders/load_mongo_wave17.py first")
    scored = []
    for p in candidates:
        text = p["text"]
        pos = sum(1 for pat in cfg["include"] if re.search(pat, text, re.I))
        neg = sum(1 for pat in cfg["exclude"] if re.search(pat, text, re.I))
        scored.append((pos - 5 * neg, p["passage_id"], p))
    scored.sort(key=lambda row: (-row[0], row[1]))
    top_score = scored[0][0]
    if top_score <= 0:
        raise RuntimeError(
            f"no passage in {advisory_number} scored positively on "
            f"{cfg['include']} -- keyword list is wrong for this corpus, "
            f"not evidence the mechanism is absent")
    return scored[0][2]


def main() -> int:
    if not SELECTION.exists():
        print(f"missing {SELECTION} -- run "
              f"generators/select_fincen_advisories.py first")
        return 1

    selection = json.loads(SELECTION.read_text())
    by_typology = {t["typology"]: t for t in selection["typologies"]}

    db = mongo_db()

    typologies = []
    for typology, cfg in TYPOLOGY_KEYWORDS.items():
        sel = by_typology.get(typology)
        if sel is None:
            print(f"missing {typology} in {SELECTION}")
            return 1
        advisory_number = sel["advisory_number"]
        passage = best_passage(db, advisory_number, cfg)
        typologies.append({
            "typology_id": cfg["typology_id"],
            "typology": typology,
            "advisory_number": advisory_number,
            "advisory_url": sel["url"],
            "passage_id": passage["passage_id"],
            "params": PARAMS[typology],
            "params_source": PARAMS_SOURCE[typology],
            "params_locator": PARAMS_LOCATOR[typology],
            "provenance": "public",
        })

    print("Wave 17 Task 4 — typology structural patterns\n")
    for t in typologies:
        print(f"  {t['typology_id']:<10} {t['typology']:<24} "
              f"{t['advisory_number']:<16} {t['passage_id']}")

    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps({"typologies": typologies}, indent=2) + "\n")
    print(f"\n  wrote {ARTIFACT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
