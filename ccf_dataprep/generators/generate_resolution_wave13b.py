#!/usr/bin/env python3
"""Wave 13b Task 5 — the resolution layer: variants, crosswalk, screening.

§C rows served here:

    Name-variant and transliteration rules   synthetic — internal   Postgres  P
    identifiedAs / sameAs edges w/ confidence  derived              Fluree    R

§F5 wants **>= 8 persons with name variants ACROSS SOURCES**, including **>= 2
transliteration cases** and **>= 1 genuine false-positive pair**. §F6 wants
**>= 1 person crossing a sanctions list below certainty**.

## What was already wrong, and why this is not "add a few more variants"

The estate holds 571 name variants. Every one is `source='def14a'`,
`rendering='display_order'` — one source, one rendering, zero transliterations
(`docs/wave13b-design.md` §1.2). Counting 571 against a floor of 8 satisfies
the count and misses the condition entirely. These are the first variants in
this estate that cross a registry boundary at all.

## The false-positive pair is FOUND, not planted

`generators/resolve_persons.py` established the principle in Wave 10: a found
collision proves the case occurs, a planted one proves only that the resolver
handles a case built for it. Here the collisions arise on their own — the name
bank is closed, so two unrelated persons land on the same name the way two
unrelated people share "Eleanor Ashworth". This script RUNS the scorer over
every pair and reports what it finds; it never writes a pair it did not score.

Measured on the current person layer: 75 pairs at or above 0.90, 68 of them
exact name collisions, and 74 of those carry a conflicting birth year or
nationality — which is what makes them false positives rather than duplicates.

## Screening is exhaustive, deliberately

Every person is scored against all 45,511 `sanctions_name` rows: 9.6M
comparisons, ~4 minutes. There is no blocking, because blocking on any token
key separates `Al-Husseini` from `Al-Husayni` and would make the
transliteration cases invisible to the screening leg while every count still
looked right. See `ccf/resolve.py`.

Thresholds are read from `ccf_v2.resolution_policy` — never from constants
here. `--seed-policy` writes the default rows on a first run.

Output: sources/screening/wave13b_resolution.json

    uv run generators/generate_resolution_wave13b.py --seed-policy
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from itertools import combinations
from random import Random

from ccf.config import PG_SCHEMA_V2, REPO_ROOT, pg_connect
from ccf.resolve import (
    BAND_FALSE_POSITIVE,
    BAND_REVIEW,
    CONFLICT,
    Evidence,
    Thresholds,
    band,
    combined_score,
    corroboration,
    explain,
    in_review_band,
)
from generators.name_bank import PARTICLES

S = PG_SCHEMA_V2
SCREEN = REPO_ROOT / "sources" / "screening"
PERSONS = SCREEN / "wave13b_psc_persons.json"

#: The registries a person can appear in. §F5 asks for variants ACROSS sources;
#: a variant is only cross-registry if the sources are genuinely different
#: systems with different rendering conventions.
REGISTRIES = {
    "psc_register": "display_order",       # 'Robert J Smith'
    "uk_companies_house": "surname_first",  # 'SMITH, ROBERT JAMES'
    "us_state_registry": "initials",        # 'R. J. Smith'
    "sanctions_watchlist": "upper_surname_first",   # 'SMITH, ROBERT'
}

#: Variant rules, the §C "name-variant and transliteration rules" element.
#: Each is a rule a resolver must apply, not a description of one.
VARIANT_RULES = [
    ("transliteration", "A name whose native form is non-Latin admits several "
     "Latin renderings; treat them as the same token, not as a spelling error."),
    ("particle_spacing", "Nobiliary and patronymic particles (van der, de la, "
     "al-, O', Mc) vary in spacing and capitalization between registries."),
    ("rendering_order", "Registries publish either 'First Last' or "
     "'LAST, First'; token order carries no identity information."),
    ("initial_expansion", "A middle initial and a full middle name are the "
     "same element rendered at different precision."),
    ("diacritic_folding", "Fold combining marks before comparison. Deleting "
     "them instead splits the token: 'Müller' becomes 'm ller'."),
]


def render(person: dict, rendering: str, rendering_index: int) -> str:
    """One registry's rendering of a person, at one transliteration index."""
    from generators.name_bank import NO_SPACE_PARTICLES

    forename = person["forename"]
    surname = person["surname"]
    middle = person.get("middle_name")

    # Alternate romanizations come from the person's own rendering budget: a
    # person whose native form admits one Latin form must not sprout a second.
    if rendering_index and person["rendering_count"] > 1:
        forename, surname = alternate(person, rendering_index)

    if rendering == "display_order":
        return " ".join(p for p in (forename, middle, surname) if p)
    if rendering == "surname_first":
        rest = " ".join(p for p in (forename, middle) if p)
        return f"{surname.upper()}, {rest}"
    if rendering == "initials":
        parts = [f"{forename[0]}."]
        if middle:
            parts.append(f"{middle[0]}.")
        parts.append(surname)
        return " ".join(parts)
    if rendering == "upper_surname_first":
        return f"{surname.upper()}, {forename.upper()}"
    raise ValueError(f"unknown rendering {rendering!r}")


def alternate(person: dict, index: int) -> tuple[str, str]:
    """The person's name under an alternate romanization.

    Rebuilt from the bank rather than mutated from the stored string, so an
    'alternate rendering' is always a real romanization of the same native
    form and never a perturbation of Latin characters.
    """
    from generators.name_bank import FORENAMES, SURNAMES

    family = person["script_family"]
    forename, surname = person["forename"], person["surname"]

    for part in FORENAMES.get(family, ()):
        if part.native == person["native_forename"]:
            forename = part.renderings[index % len(part.renderings)]
            break
    for part in SURNAMES.get(family, ()):
        if part.native == person["native_surname"]:
            base = part.renderings[index % len(part.renderings)]
            particle = person.get("particle")
            if particle:
                forms = PARTICLES[particle]
                prefix = forms[index % len(forms)]
                joiner = "" if particle in {"O'", "Mc", "al-"} else " "
                base = f"{prefix}{joiner}{base}"
            surname = base
            break
    return forename, surname


def build_variants(persons: list[dict], rng: Random) -> list[dict]:
    """Cross-registry renderings, one set per person."""
    variants = []
    for person in persons:
        # Every person appears in the PSC register; how many OTHER registries
        # they reach varies, because a person present in every system would
        # make resolution trivially easy.
        extra = rng.sample(
            [r for r in REGISTRIES if r != "psc_register"],
            k=rng.choices([0, 1, 2, 3], weights=[35, 35, 20, 10])[0],
        )
        for i, registry in enumerate(["psc_register", *extra]):
            rendering = REGISTRIES[registry]
            # Registries that received the person later are likelier to hold a
            # different romanization — which is how transliteration variants
            # actually enter a system.
            index = 0 if registry == "psc_register" else rng.randrange(
                max(1, person["rendering_count"]))
            name = render(person, rendering, index)
            variants.append({
                "person_key": person["person_id"],
                "variant_name": name,
                "source": registry,
                "rendering": rendering,
                "rendering_index": index,
                "is_transliteration": bool(index) and person["is_transliterated"],
                "provenance": "synthetic — engineered",
            })
    return variants


def find_false_positives(persons: list[dict], t: Thresholds) -> list[dict]:
    """Distinct persons whose names collide at or above the merge threshold.

    Nothing here is planted: every pair is produced by running the scorer over
    the whole population and keeping what it returns. A pair is a FALSE
    POSITIVE only when the corroborating evidence conflicts — same name, same
    evidence would be a duplicate record of one person, which is a different
    problem with a different remedy.
    """
    found = []
    for a, b in combinations(persons, 2):
        score = combined_score(a["display_name"], b["display_name"])
        if score < t.merge_threshold:
            continue
        ev_a = Evidence(a["dob_month"], a["dob_year"], a["nationality"])
        ev_b = Evidence(b["dob_month"], b["dob_year"], b["nationality"])
        corr = corroboration(ev_a, ev_b)
        verdict = band(score, corr, t)
        if verdict != BAND_FALSE_POSITIVE:
            continue
        found.append({
            "person_key_a": a["person_id"],
            "person_key_b": b["person_id"],
            "name_a": a["display_name"],
            "name_b": b["display_name"],
            "corroboration": corr,
            "conflicting_on": [
                field for field, x, y in (
                    ("dob_year", a["dob_year"], b["dob_year"]),
                    ("dob_month", a["dob_month"], b["dob_month"]),
                    ("nationality", a["nationality"], b["nationality"]),
                ) if x != y
            ],
            **explain(a["display_name"], b["display_name"]),
            "band": verdict,
            "provenance": "synthetic — engineered",
        })
    return found


def screen_sanctions(persons: list[dict], cur, t: Thresholds) -> list[dict]:
    """Score every person against every sanctions name. No blocking."""
    cur.execute(
        f'SELECT n.entry_id, n.name, n.name_kind, n.category, e.sdn_type, '
        f'e.programs, e.nationalities, e.dates_of_birth '
        f'FROM "{S}".sanctions_name n '
        f'JOIN "{S}".sanctions_entry e USING (entry_id) '
        f"WHERE n.name <> '' AND e.sdn_type = 'Individual'"
    )
    listed = cur.fetchall()
    print(f"    screening against {len(listed):,} individual sanctions names")

    hits = []
    for i, person in enumerate(persons):
        name = person["display_name"]
        best = None
        for entry_id, listed_name, kind, category, _t, programs, nats, dobs in listed:
            score = combined_score(name, listed_name)
            if best is None or score > best[0]:
                best = (score, entry_id, listed_name, kind, category,
                        programs, nats, dobs)
        if best is None:
            continue
        score, entry_id, listed_name, kind, category, programs, nats, dobs = best
        if score < t.review_floor:
            continue
        hits.append({
            "person_key": person["person_id"],
            "person_name": name,
            "entry_id": entry_id,
            "listed_name": listed_name,
            "name_kind": kind,
            "alias_category": category,
            "programs": list(programs or []),
            "listed_nationalities": list(nats or []),
            "listed_dates_of_birth": list(dobs or []),
            **explain(name, listed_name),
            "in_review_band": in_review_band(score, t),
            "disposition": (BAND_REVIEW if in_review_band(score, t)
                            else "auto_clear_candidate"),
            "provenance": "synthetic — engineered (person) / public (listing)",
        })
        if (i + 1) % 50 == 0:
            print(f"    scored {i + 1}/{len(persons)} persons", end="\r")
    print()
    return hits


def seed_policy(cur) -> None:
    """Write the default resolution thresholds if the table is empty."""
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS "{S}".resolution_policy (
            threshold_name   text    PRIMARY KEY,
            threshold_value  numeric NOT NULL,
            policy_version   text    NOT NULL,
            rationale        text    NOT NULL,
            provenance       text    NOT NULL
        )
    """)
    rows = [
        ("auto_clear", 0.95, "kyc-resolution-v1",
         "At or above this, a match with agreeing evidence clears without "
         "review. Set high because an auto-cleared sanctions match is an "
         "unreviewed one.", "synthetic — internal"),
        ("review_floor", 0.70, "kyc-resolution-v1",
         "Below this, a candidate is auto-rejected. Set at 0.70 rather than "
         "0.75 because measured transliteration pairs land at 0.74 "
         "('Yusuf Al-Husseini' / 'Youssef Al-Husayni') — a floor above that "
         "auto-rejects the exact cases §F5 exists to test, and the review "
         "queue §F6 needs exercised would never fill.", "synthetic — internal"),
        ("merge_threshold", 0.90, "kyc-resolution-v1",
         "At or above this a naive resolver would MERGE two records. It is "
         "the threshold a false positive has to clear to be dangerous.",
         "synthetic — internal"),
    ]
    cur.executemany(
        f'INSERT INTO "{S}".resolution_policy '
        "(threshold_name, threshold_value, policy_version, rationale, provenance) "
        "VALUES (%s,%s,%s,%s,%s) ON CONFLICT (threshold_name) DO UPDATE SET "
        "threshold_value=EXCLUDED.threshold_value, "
        "policy_version=EXCLUDED.policy_version, "
        "rationale=EXCLUDED.rationale, provenance=EXCLUDED.provenance",
        rows,
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed-policy", action="store_true",
                    help="write the default resolution_policy rows first")
    ap.add_argument("--skip-screening", action="store_true",
                    help="skip the 4-minute exhaustive sanctions pass")
    args = ap.parse_args()

    doc = json.loads(PERSONS.read_text())
    persons = doc["persons"]
    rng = Random(20260822)

    print("Wave 13b Task 5 — resolution layer\n")

    with pg_connect() as conn, conn.cursor() as cur:
        if args.seed_policy:
            seed_policy(cur)
            conn.commit()
        thresholds = Thresholds.load(cur)
        print(f"  thresholds (from {S}.resolution_policy, "
              f"{thresholds.policy_version})")
        print(f"      auto_clear      {thresholds.auto_clear}")
        print(f"      review_floor    {thresholds.review_floor}")
        print(f"      merge_threshold {thresholds.merge_threshold}")

        variants = build_variants(persons, rng)
        by_source = Counter(v["source"] for v in variants)
        cross = Counter(v["person_key"] for v in variants)
        multi_source = [k for k, n in cross.items() if n >= 2]
        translit = [v for v in variants if v["is_transliteration"]]
        translit_persons = {v["person_key"] for v in translit}

        print(f"\n  variants            {len(variants)}")
        print(f"      by source       {dict(by_source)}")
        print(f"      persons in >= 2 registries: {len(multi_source)}  "
              f"(§F5 floor 8)")
        print(f"      transliteration variants:   {len(translit)} across "
              f"{len(translit_persons)} persons  (§F5 floor 2 CASES)")

        false_positives = find_false_positives(persons, thresholds)
        print(f"\n  false positives     {len(false_positives)}  (§F5 floor 1)")
        for fp in false_positives[:3]:
            print(f"      {fp['name_a']!r} = {fp['name_b']!r}  "
                  f"score={fp['score']} carried_by={fp['carried_by']} "
                  f"conflict on {fp['conflicting_on']}")

        hits = [] if args.skip_screening else screen_sanctions(
            persons, cur, thresholds)

    review = [h for h in hits if h["in_review_band"]]
    print(f"\n  sanctions hits      {len(hits)} at or above review_floor")
    print(f"      in REVIEW band  {len(review)}  (§F6 floor 1 — strictly "
          f"between auto-reject and auto-clear)")
    for h in review[:3]:
        print(f"      {h['person_name']!r} ~ {h['listed_name']!r}  "
              f"score={h['score']}  programs={h['programs'][:2]}")

    failures = []
    if len(multi_source) < 8:
        failures.append(f"§F5: only {len(multi_source)} persons appear in 2+ "
                        f"registries, floor is 8")
    if len(translit_persons) < 2:
        failures.append(f"§F5: only {len(translit_persons)} transliteration "
                        f"cases, floor is 2")
    if not false_positives:
        failures.append("§F5: no false-positive pair was FOUND by the scorer")
    if not args.skip_screening and not review:
        failures.append("§F6: no sanctions match landed in the review band")
    if failures:
        print()
        for f in failures:
            print(f"  FAIL  {f}")
        return 1

    out = SCREEN / "wave13b_resolution.json"
    out.write_text(
        json.dumps(
            {
                "generated_for": "Wave 13b — resolution layer "
                                 "(kyc-refresh-beneficial-ownership §C/§F5/§F6)",
                "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "thresholds": {
                    "auto_clear": thresholds.auto_clear,
                    "review_floor": thresholds.review_floor,
                    "merge_threshold": thresholds.merge_threshold,
                    "policy_version": thresholds.policy_version,
                    "source": f"{S}.resolution_policy — read, not hardcoded",
                },
                "variant_rules": [
                    {"rule_name": n, "description": d,
                     "provenance": "synthetic — internal"}
                    for n, d in VARIANT_RULES
                ],
                "variant_count": len(variants),
                "persons_in_multiple_registries": len(multi_source),
                "transliteration_person_count": len(translit_persons),
                "false_positive_count": len(false_positives),
                "sanctions_hit_count": len(hits),
                "sanctions_review_count": len(review),
                "variants": variants,
                "false_positives": false_positives,
                "sanctions_hits": hits,
            },
            indent=1,
            ensure_ascii=False,
        )
        + "\n"
    )
    print(f"\n  written: {out.relative_to(REPO_ROOT)} "
          f"({out.stat().st_size / 1e3:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
