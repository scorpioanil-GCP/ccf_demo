#!/usr/bin/env python3
"""Wave 17 Task 6 -- generate the 200 invented AML parties.

`aml-typology-match` needs a cast of synthetic entities to run typologies,
transactions, alerts and SARs against. CLAUDE.md rule 2 is a hard legal
constraint for this product: no named real company and no real natural
person may ever appear. `ccf.aml.RealNameIndex` is how that is enforced at
GENERATION time, not caught in review afterwards -- every candidate legal
name is checked with `.blocks()` before it is accepted, and a blocked
candidate is regenerated, never silently kept.

## The "zero rejections is suspicious" heuristic in the brief is wrong

The brief text says a rejection count of zero across 200 draws "usually
means the guard is not wired in". Task 5's own re-review measured the
opposite for exactly this generator's naming style (two invented real-word
tokens + a common corporate suffix): **0 blocked out of 200**, with the
guard fully wired and confirmed working via known-present/known-absent
controls run in the same session. A "zero rejections is suspicious"
warning printed here would be simply wrong for a clean word bank, and an
implementer who "fixed" it by degrading the word bank to manufacture
collisions with real companies would be making the data worse to satisfy a
false heuristic.

So this module does NOT implement that check. Instead it implements the
decidable version -- the same idiom `ccf.fibo.fibo_absent()` already uses,
requiring a positive control to fire before any negative result is
trusted:

    * `blocks()` is called on a name KNOWN to be in the index
      ("Charter Communications, Inc.", also used as the known-present
      control in `validators/test_aml_typology.py`) and must return a
      match.
    * `blocks()` is called on a name KNOWN to be absent
      ("Vermillion Quayside Holdings Ltd", also the known-absent control
      there) and must return `None`.

Either failing aborts the run before a single party is generated. This is
what actually distinguishes "the guard ran and found nothing to reject"
from "the guard was never wired in" -- a rejection count alone cannot.

The rejection count IS still tracked and printed, because it is useful
data, just not evidence of anything on its own.

## Word banks

`generators/name_bank.py`'s DISCIPLINE is reused, not its vocabulary: a
closed set of parts, a seeded `random.Random`, structured composition
rather than free-form strings, so a real name cannot appear by accident.
That module is a PERSON name bank; this one builds its own closed corporate
word bank in the same style, built from ordinary English words rather than
random letter strings -- Task 5's re-review measured that random short
letter-salad prefixes ("Nava", "Faya") collide with real short-name
companies at roughly 1-in-11, while two-real-word combinations measured
**0/200**. This module's corporate names follow the proven shape.

Person names ARE drawn from `name_bank` for `party_kind == "individual_owned"`
parties -- not as the party's own name, but as an ingredient in a small
owner-operated business's legal name (e.g. "Vandersteen Trading LLC"), the
same naming convention real sole-proprietor businesses use. Those names are
already synthetic and safe per that module's own docstring.

## `party_kind` is an ownership-structure label, not "person vs. company"

All three kinds -- `corporate`, `individual_owned`, `shell` -- are legal
entities with a company-shaped `legal_name`, `jurisdiction` and
`incorporated` date. They differ in how they are OWNED, which is what
Task 9's beneficial-ownership binding keys off:

    corporate         diffuse / institutional ownership -- no single BO bound
    individual_owned  simple, direct single-person ownership
    shell             layered ownership built specifically to obscure the
                      beneficial owner

`shell` entities are also deliberately skewed toward classic secrecy
jurisdictions and more recent incorporation dates than `corporate` --
CLAUDE.md's "synthetic -- engineered" class exists precisely for a planted
condition like this one, and it is labelled as such below.

## Determinism

`SEED` is a fixed constant. All randomness flows through one seeded
`random.Random(SEED)`. `party_id` is assigned only after the full batch is
generated, from a SORTED, content-derived ordering (by `legal_name`) --
never from the order candidates happened to be drawn or accepted in, which
is exactly the "positional identity" defect class this repo already has
five recorded instances of. Re-running this script must produce a
byte-identical `sources/screening/wave17_parties.json`
(`git diff --exit-code` after a second run is the proof).

## Task 7 -- the one declared OFAC near-match

`generate_declared_ofac_near_match()` below is the single permitted
exception to the "every candidate goes through `idx.blocks()` and a
blocked candidate is regenerated" rule above. It is not a hole in the
guard: the guard is EXPECTED to block this one name (proved by
`validators/test_aml_typology.py::test_the_guard_would_have_rejected_the_declared_match`,
which re-runs `idx.blocks()` over it on the ordinary path), and the party
carries an `ofac_near_match` key that names exactly which real sanctions
entry it was deliberately built to resemble, so the exception is declared
rather than silently smuggled past `test_no_generated_party_collides_with_a_real_entity`
(which exempts only party ids carrying that key).

The matched sanctions entry (`SDN-10118`, OFAC SDN list, program DRCONGO,
primary name "GREAT LAKES BUSINESS COMPANY", one a.k.a. "GLBC") is REAL and
public. The party itself, "Granite Lakes Business Corp", is invented: one
distinguishing token changed ("Great" -> "Granite"), the rest of the shape
kept, in a different jurisdiction and with no connection to the real
entity's DRC/Rwanda sanctions programs. Measured
`ccf.aml.similarity("Granite Lakes Business Corp", "GREAT LAKES BUSINESS
COMPANY") == 0.9047619047619048` -- inside the reachable band
`BLOCK_THRESHOLD <= x <= 0.92`. See `docs/ccf_dataprep_v2.md`,
"2026-08-25 — Wave 17 whole-branch review: three notes for a reader of this
data", for why the brief's stated `0.70` floor is unreachable for a name
that must also block, and for what "moderate confidence" honestly means at
0.9048 -- the SDD `task-7-report.md` this used to cite is deleted when the
wave closes.

This one party is IN ADDITION to the 200 generated above -- Task 6's own
title and target constants ("the 200 parties") are unchanged by this task;
`generate_parties()` appends the declared party after the 200 are drawn,
so the final artifact carries 201 parties, and `party_id`/`syn_lei`
assignment (the sorted-by-`legal_name` pass below) applies to all 201
uniformly, exactly as if it were just another row.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import date, timedelta
from random import Random

from ccf.aml import RealNameIndex
from ccf.config import REPO_ROOT
from generators.name_bank import FORENAMES, SURNAMES, sample_name

SEED = 170_006  # fixed constant: Wave 17, Task 6. Never re-seeded per run.

OUT_PATH = REPO_ROOT / "sources" / "screening" / "wave17_parties.json"

# Positive/negative controls -- also used as the known-present/known-absent
# controls in validators/test_aml_typology.py, so a failure here and a
# failure there point at the same fact.
KNOWN_PRESENT_CONTROL = "Charter Communications, Inc."
KNOWN_ABSENT_CONTROL = "Vermillion Quayside Holdings Ltd"

TARGET_CORPORATE = 100
TARGET_INDIVIDUAL_OWNED = 60
TARGET_SHELL = 40
TARGET_TOTAL = TARGET_CORPORATE + TARGET_INDIVIDUAL_OWNED + TARGET_SHELL

MAX_RETRIES_PER_PARTY = 50

# --------------------------------------------------------------------------
# Corporate word bank -- ordinary English words, closed vocabulary, no
# random letter strings. Two disjoint prefix pools plus disjoint business-
# word pools per kind give `corporate` and `shell` a slightly different
# naming flavor (operating-company words vs. paper-holding-company words)
# without changing the proven-safe two-real-word + suffix shape.
# --------------------------------------------------------------------------

PREFIX_WORDS = [
    "Ashford", "Ashworth", "Blackwood", "Brightwater", "Cedarbrook",
    "Clearwater", "Deepwater", "Dunmore", "Eastgate", "Elmsworth",
    "Fairhaven", "Fenwick", "Glenridge", "Greystone", "Harborview",
    "Hollowbrook", "Ironwood", "Ivyridge", "Juniper", "Kestrel",
    "Kingsley", "Larchwood", "Lonsdale", "Meridian", "Millbrook",
    "Northgate", "Norwood", "Oakhaven", "Oxbridge", "Parkside",
    "Pinegrove", "Quarrystone", "Ridgemont", "Rosewood", "Silverline",
    "Stonebridge", "Thornfield", "Underhill", "Vantage", "Westbrook",
]

CORPORATE_BUSINESS_WORDS = [
    "Industries", "Technologies", "Manufacturing", "Logistics", "Resources",
    "Materials", "Foods", "Chemicals", "Aviation", "Systems", "Solutions",
    "Properties", "Fisheries", "Timber", "Minerals", "Petroleum",
]

SHELL_BUSINESS_WORDS = [
    "Holdings", "Trading", "Capital", "Ventures", "International",
    "Overseas", "Group", "Partners", "Consolidated", "Enterprises",
    "Investments", "Universal",
]

LEGAL_FORM_SUFFIXES = [
    "LLC", "Ltd", "Inc", "Corp", "S.A.", "GmbH", "B.V.", "Pte Ltd", None, None,
    # `None` twice so roughly a third of names carry no bare legal-form
    # suffix at all -- not every real filing does either.
]

INDIVIDUAL_BUSINESS_WORDS = [
    "Trading", "Consulting", "Enterprises", "Holdings", "Imports",
    "& Sons", "& Associates", "Trading Co",
]

# --------------------------------------------------------------------------
# Jurisdictions -- ISO 3166-1 alpha-3. Weighted lists, sampled with
# rng.choice (uniform over the list, so repeating a code increases its
# weight) rather than a separate weights structure -- one closed list per
# kind is easier to audit than parallel probability tables.
# --------------------------------------------------------------------------

ONSHORE_JURISDICTIONS = (
    ["USA"] * 4 + ["GBR"] * 3 + ["DEU"] * 2 + ["FRA"] * 2 + ["NLD"] * 2
    + ["IRL"] + ["SGP"] * 2 + ["HKG"] * 2 + ["CHE"] + ["CAN"] + ["AUS"]
    + ["JPN"]
)

OFFSHORE_JURISDICTIONS = (
    ["CYM"] * 3 + ["VGB"] * 3 + ["PAN"] * 2 + ["SYC"] * 2 + ["MHL"] * 2
    + ["MLT"] + ["CYP"] + ["LUX"] + ["BMU"] + ["BHS"] + ["MUS"] + ["BLZ"]
    + ["LIE"] + ["IMN"] + ["JEY"]
)

# Kind -> (onshore pool, offshore pool, offshore weight fraction). Sampled
# by drawing one uniform float and comparing to the offshore fraction, so
# each kind's onshore/offshore mix is an explicit, named number rather than
# implied by pool sizes.
JURISDICTION_MIX = {
    "corporate": (ONSHORE_JURISDICTIONS, OFFSHORE_JURISDICTIONS, 0.10),
    "individual_owned": (ONSHORE_JURISDICTIONS, OFFSHORE_JURISDICTIONS, 0.20),
    # Engineered condition, labelled: shells cluster in classic secrecy
    # jurisdictions far more than the other two kinds.
    "shell": (ONSHORE_JURISDICTIONS, OFFSHORE_JURISDICTIONS, 0.85),
}

# Incorporation-date windows per kind, as (earliest, latest) ISO dates.
# Engineered condition, labelled: shells skew recent -- a classic AML red
# flag is a shell formed shortly before it starts moving money.
INCORPORATION_WINDOWS = {
    "corporate": (date(1994, 1, 1), date(2022, 6, 30)),
    "individual_owned": (date(1998, 1, 1), date(2023, 6, 30)),
    "shell": (date(2017, 1, 1), date(2026, 3, 31)),
}

ALL_SCRIPT_FAMILIES = sorted(FORENAMES)  # sorted: deterministic choice order


class GuardNotWiredError(RuntimeError):
    """Raised when the positive/negative control pair does not behave as
    expected -- see the module docstring's "zero rejections" section for
    why this replaces a rejection-count heuristic."""


class RetryBudgetExhausted(RuntimeError):
    """A single party slot could not find an unblocked, unused name within
    `MAX_RETRIES_PER_PARTY` attempts. Fail loudly rather than spin -- per
    the measured ~9%-worst-case block rate this should never fire for the
    word banks above."""


class GuardStats:
    """Counts every `.blocks()` call made during this run, split into the
    two positive/negative controls and the generation-loop calls, plus how
    many of the generation-loop calls were rejections. Reported at the end
    of the run and returned to callers (e.g. the test suite / report) that
    want the exact numbers."""

    def __init__(self) -> None:
        self.control_calls = 0
        self.generation_calls = 0
        self.rejections = 0

    @property
    def total_calls(self) -> int:
        return self.control_calls + self.generation_calls


def run_positive_control(idx: RealNameIndex, stats: GuardStats) -> None:
    """Abort the run if the guard cannot prove it is wired in. See the
    module docstring: a zero rejection COUNT proves nothing either way; a
    known-present hit and a known-absent miss, in the same session, do."""
    stats.control_calls += 1
    present = idx.blocks(KNOWN_PRESENT_CONTROL)
    if present is None:
        raise GuardNotWiredError(
            f"Positive control failed: blocks({KNOWN_PRESENT_CONTROL!r}) "
            "returned None. The guard did not block a name known to be in "
            "the index -- aborting before generating a single party.")

    stats.control_calls += 1
    absent = idx.blocks(KNOWN_ABSENT_CONTROL)
    if absent is not None:
        raise GuardNotWiredError(
            f"Negative control failed: blocks({KNOWN_ABSENT_CONTROL!r}) "
            f"returned {absent!r} instead of None. The guard blocks "
            "everything, which is as useless as blocking nothing -- "
            "aborting before generating a single party.")


def _guarded(idx: RealNameIndex, stats: GuardStats, candidate: str) -> bool:
    """True if `candidate` is clear to use. Counts the call and, if
    blocked, the rejection."""
    stats.generation_calls += 1
    hit = idx.blocks(candidate)
    if hit is not None:
        stats.rejections += 1
        return False
    return True


def _pick_jurisdiction(rng: Random, kind: str) -> str:
    onshore, offshore, offshore_fraction = JURISDICTION_MIX[kind]
    pool = offshore if rng.random() < offshore_fraction else onshore
    return rng.choice(pool)


def _pick_incorporated(rng: Random, kind: str) -> str:
    start, end = INCORPORATION_WINDOWS[kind]
    span_days = (end - start).days
    offset = rng.randrange(span_days + 1)
    return (start + timedelta(days=offset)).isoformat()


def _draw_corporate_name(rng: Random) -> str:
    prefix = rng.choice(PREFIX_WORDS)
    business = rng.choice(CORPORATE_BUSINESS_WORDS)
    suffix = rng.choice(LEGAL_FORM_SUFFIXES)
    name = f"{prefix} {business}"
    if suffix:
        name = f"{name} {suffix}"
    return name


def _draw_shell_name(rng: Random) -> str:
    prefix = rng.choice(PREFIX_WORDS)
    business = rng.choice(SHELL_BUSINESS_WORDS)
    suffix = rng.choice(LEGAL_FORM_SUFFIXES)
    name = f"{prefix} {business}"
    if suffix:
        name = f"{name} {suffix}"
    return name


def _draw_individual_owned_name(rng: Random) -> str:
    family = rng.choice(ALL_SCRIPT_FAMILIES)
    person = sample_name(
        rng, script_family=family, has_middle=False, has_particle=False,
        hyphenated=False, has_title=False,
    )
    business = rng.choice(INDIVIDUAL_BUSINESS_WORDS)
    if rng.random() < 0.5:
        base = person.surname()
    else:
        base = f"{person.forename()} {person.surname()}"
    return f"{base} {business}"


_DRAWERS = {
    "corporate": _draw_corporate_name,
    "individual_owned": _draw_individual_owned_name,
    "shell": _draw_shell_name,
}


def _generate_kind(rng: Random, idx: RealNameIndex, stats: GuardStats,
                    kind: str, count: int, used_names: set[str]) -> list[dict]:
    drawer = _DRAWERS[kind]
    out = []
    for _ in range(count):
        for attempt in range(MAX_RETRIES_PER_PARTY):
            candidate = drawer(rng)
            key = candidate.casefold()
            if key in used_names:
                continue  # in-batch duplicate; retry without spending a guard call
            if not _guarded(idx, stats, candidate):
                continue  # blocked by the real-name guard; retry
            used_names.add(key)
            out.append({
                "legal_name": candidate,
                "syn_lei": None,  # filled in after party_id assignment
                "jurisdiction": _pick_jurisdiction(rng, kind),
                "party_kind": kind,
                "incorporated": _pick_incorporated(rng, kind),
                "provenance": "synthetic — engineered",
            })
            break
        else:
            raise RetryBudgetExhausted(
                f"Could not find an unblocked, unused {kind} name after "
                f"{MAX_RETRIES_PER_PARTY} attempts.")
    return out


def generate_declared_ofac_near_match() -> dict:
    """The single permitted exception to the name guard (Wave 17 Task 7,
    envelope floor 5). See the module docstring's "Task 7" section for the
    full rationale.

    Fixed, hand-chosen fields -- not drawn from `rng` -- because this is
    exactly one specific engineered record, not a batch draw with a
    statistical shape to preserve. Determinism follows from the values
    being literal constants, same as everywhere else in this module.
    """
    matched_name = "GREAT LAKES BUSINESS COMPANY"  # SDN-10118 primary name
    return {
        "legal_name": "Granite Lakes Business Corp",
        "syn_lei": None,  # filled in after party_id assignment, like every other party
        "jurisdiction": "USA",  # deliberately unrelated to SDN-10118's DRC/Rwanda programs
        "party_kind": "corporate",
        "incorporated": "2015-03-12",
        "provenance": "synthetic — engineered",
        "ofac_near_match": {
            "sanctions_entry_id": "SDN-10118",
            "matched_name": matched_name,
            # Recomputed live by the test suite, never trusted from here --
            # see validators/test_aml_typology.py.
            "measured_similarity": 0.9047619047619048,
        },
    }


def generate_parties(seed: int = SEED) -> tuple[list[dict], GuardStats, float]:
    """Build the full 200-party batch. Returns (parties, guard_stats,
    wall_seconds) so callers -- the CLI entry point and any later task --
    get the exact instrumentation numbers rather than having to re-derive
    them."""
    t0 = time.monotonic()
    rng = Random(seed)
    idx = RealNameIndex.build()
    stats = GuardStats()

    run_positive_control(idx, stats)

    used_names: set[str] = set()
    parties: list[dict] = []
    # Fixed, sorted kind order -- not that it affects the OUTPUT order
    # (party_id assignment re-sorts by legal_name below), but a stable
    # draw order is part of what makes the whole run reproducible.
    for kind, count in (
        ("corporate", TARGET_CORPORATE),
        ("individual_owned", TARGET_INDIVIDUAL_OWNED),
        ("shell", TARGET_SHELL),
    ):
        parties.extend(_generate_kind(rng, idx, stats, kind, count, used_names))

    assert len(parties) == TARGET_TOTAL, (
        f"generated {len(parties)}, expected {TARGET_TOTAL}")

    # Task 7's one declared OFAC near-match -- IN ADDITION to the 200 above,
    # not a swap. Deliberately NOT passed through _guarded(): the whole
    # point is that the ordinary guard WOULD block it (proved separately in
    # validators/test_aml_typology.py), so running it through _guarded()
    # here would just raise RetryBudgetExhausted for a candidate that was
    # never meant to pass. Still checked against used_names so it cannot
    # silently collide with one of the 200 random draws above.
    declared = generate_declared_ofac_near_match()
    declared_key = declared["legal_name"].casefold()
    assert declared_key not in used_names, (
        f"declared OFAC near-match name collides with a generated party: "
        f"{declared['legal_name']!r}")
    used_names.add(declared_key)
    parties.append(declared)

    assert len(parties) == TARGET_TOTAL + 1, (
        f"generated {len(parties)}, expected {TARGET_TOTAL + 1} "
        "(200 plus the one declared OFAC near-match)")

    # party_id: sorted, content-derived ordering -- never the draw order
    # above, which is exactly the positional-identity defect class this
    # repo already has five recorded instances of. Sort key is the
    # normalized legal_name (case-insensitive) with the raw legal_name as
    # tiebreaker for total ordering; legal_name is unique within this batch
    # by construction (used_names), so the tiebreaker never actually fires.
    parties.sort(key=lambda p: (p["legal_name"].casefold(), p["legal_name"]))
    for i, p in enumerate(parties, start=1):
        party_id = f"AMLP-{i:04d}"
        p["party_id"] = party_id
        p["syn_lei"] = f"SYN-AML-{i:04d}"

    # Re-key each dict so field order is identical and readable regardless
    # of insertion order above -- json.dump below also sorts keys, so this
    # is for readability of the in-memory structure, not correctness.
    # `ofac_near_match` is carried through only for the one declared party
    # (Task 7) -- every other party dict simply has no such key.
    ordered_parties = [
        {
            "party_id": p["party_id"],
            "legal_name": p["legal_name"],
            "syn_lei": p["syn_lei"],
            "jurisdiction": p["jurisdiction"],
            "party_kind": p["party_kind"],
            "incorporated": p["incorporated"],
            "provenance": p["provenance"],
            **({"ofac_near_match": p["ofac_near_match"]} if "ofac_near_match" in p else {}),
        }
        for p in parties
    ]

    wall_seconds = time.monotonic() - t0
    return ordered_parties, stats, wall_seconds


def main() -> int:
    parties, stats, wall_seconds = generate_parties()

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps({"parties": parties}, indent=2, sort_keys=True,
                    ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    by_kind: dict[str, int] = {}
    for p in parties:
        by_kind[p["party_kind"]] = by_kind.get(p["party_kind"], 0) + 1

    print(f"Wrote {len(parties)} parties to {OUT_PATH}")
    print(f"  by kind: {dict(sorted(by_kind.items()))}")
    print(f"Positive/negative controls: both passed -- the guard is "
          f"confirmed wired in (see module docstring; a rejection count "
          f"of zero would NOT by itself indicate a problem here).")
    print(f"blocks() calls: {stats.total_calls} total "
          f"({stats.control_calls} control, {stats.generation_calls} "
          f"during generation)")
    print(f"Rejections during generation: {stats.rejections} "
          f"(zero is an EXPECTED outcome for a clean, real-word corporate "
          f"word bank -- see module docstring; the positive control above, "
          f"not this count, is what establishes the guard ran)")
    print(f"Wall time: {wall_seconds:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
