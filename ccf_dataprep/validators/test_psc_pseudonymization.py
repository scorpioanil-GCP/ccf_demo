#!/usr/bin/env python3
"""Prove the PSC person layer cannot carry a real identity.

    uv run validators/test_psc_pseudonymization.py

`docs/wave13b-design.md` §2.1 commits to a rule about intermediate state, not
just output: no real PSC person name reaches any store, any artifact under
`sources/`, or any tracked file, at any point. CLAUDE.md rule 3 is the reason —
PSC records concern real, named, living people, and this repository is
privately distributed, which makes publication a live risk rather than a
theoretical one.

A promise in a docstring is not a control. Four arms, each with the input that
would make it fail:

  1. `shape_of()` returns nothing derived from name text.
  2. `PscShape` has not grown a field that could carry one.
  3. The name-leak gate rejects a name the bank could not have produced.
  4. The committed artifact carries no field that could hold a real identity,
     and records that no mapping was kept.

Arm 3 has an explicit falsification counterpart: a name the bank COULD have
produced must pass. A gate that rejects everything is as useless as one that
rejects nothing, and only running both tells them apart.

This file uses invented PSC-shaped records throughout. It never opens a
snapshot, so it can run long after the raw file is deleted.
"""

from __future__ import annotations

import json
import sys
from dataclasses import fields

from ccf.config import REPO_ROOT
from generators.derive_psc_persons import (
    DISTRIBUTIONS,
    K_ANON,
    SHAPE_FIELDS,
    PscShape,
    check_no_leak,
    shape_of,
)

ARTIFACT = REPO_ROOT / "sources" / "screening" / "wave13b_psc_persons.json"
DIST = REPO_ROOT / "sources" / "screening" / DISTRIBUTIONS

#: Tables in the committed aggregates that could carry a rare combination and
#: must therefore clear k. `dob_months` and `ceased` are deliberately absent:
#: 12 and 2 rows, minimum counts in the tens of thousands.
K_FILTERED_TABLES = ("structural", "joint_nationality_dob",
                     "natures_of_control", "country_of_residence",
                     "dob_bands", "multiplicity")

#: Every key the aggregates may contain. Pinned, so adding one is a review
#: rather than a quiet widening of what gets committed about real people.
DIST_KEYS = {
    "k_anonymity", "dob_band_years", "observations_dropped_below_k",
    "source_records_scanned", "individual_shapes_used", "structural",
    "joint_nationality_dob", "natures_of_control", "country_of_residence",
    "dob_months", "dob_bands", "multiplicity", "ceased",
}

#: Tokens chosen so that any leak is unmistakable: no register and no name
#: bank contains them, and they cannot arise by coincidence.
CANARY_FORENAME = "Zzyzxian"
CANARY_MIDDLE = "Qwertyuiop"
CANARY_SURNAME = "Vorpalsnark"
CANARY_TITLE = "Grandmaster"

CANARY_RECORD = {
    "kind": "individual-person-with-significant-control",
    "name": f"{CANARY_TITLE} {CANARY_FORENAME} {CANARY_MIDDLE} {CANARY_SURNAME}",
    "name_elements": {
        "title": CANARY_TITLE,
        "forename": CANARY_FORENAME,
        "middle_name": CANARY_MIDDLE,
        "surname": CANARY_SURNAME,
    },
    "nationality": "British",
    "country_of_residence": "England",
    "date_of_birth": {"month": 4, "year": 1971},
    "natures_of_control": ["ownership-of-shares-75-to-100-percent"],
    "notified_on": "2017-03-02",
}

CANARIES = (CANARY_FORENAME, CANARY_MIDDLE, CANARY_SURNAME, CANARY_TITLE)


def check_shape_carries_no_name() -> bool:
    print("\n1 · shape_of() returns nothing derived from the name")
    shape = shape_of(CANARY_RECORD)
    if shape is None:
        print("    FAIL  shape_of() rejected a well-formed record; the arm "
              "proves nothing about leakage")
        return False

    # Everything the dataclass holds, rendered — a leak anywhere in it shows.
    rendered = repr(shape)
    leaked = [c for c in CANARIES if c.lower() in rendered.lower()]
    if leaked:
        print(f"    FAIL  name text reached the shape: {leaked}")
        print(f"          {rendered[:200]}")
        return False

    # The shape must still have SEEN the name — otherwise this arm would pass
    # against a function that ignored its input entirely.
    if not (shape.has_title and shape.has_middle and not shape.middle_is_initial):
        print(f"    FAIL  the shape did not reflect the name it was given "
              f"(title/middle not detected); it may not be reading it at all")
        return False
    print(f"    ok    shape reflects the name's STRUCTURE "
          f"(title={shape.has_title}, middle={shape.has_middle}, "
          f"tokens={shape.forename_tokens}) and carries none of its text")
    return True


def check_field_pin() -> bool:
    print("\n2 · PscShape has not grown a name-bearing field")
    actual = {f.name for f in fields(PscShape)}
    if actual != SHAPE_FIELDS:
        print(f"    FAIL  field set changed: {sorted(actual ^ SHAPE_FIELDS)}")
        return False
    print(f"    ok    {len(actual)} fields, all booleans, counts or "
          f"controlled-vocabulary codes")
    return True


def check_leak_gate() -> bool:
    print("\n3 · the name-leak gate rejects a name the bank cannot produce")
    intruder = [{
        "person_id": "CANARY-1",
        "forename": CANARY_FORENAME,
        "surname": CANARY_SURNAME,
        "middle_name": None,
        "title": None,
    }]
    failures = check_no_leak(intruder)
    if not failures:
        print("    FAIL  the gate accepted a name no bank entry could produce")
        return False
    print(f"    ok    rejected: {failures[0][:88]}")
    return True


def check_leak_gate_falsification() -> bool:
    print("\n4 · falsification — a name the bank CAN produce must pass")
    from generators.name_bank import sample_name
    from random import Random

    ok = True
    for family in ("latin_gb", "arabic", "cyrillic", "han"):
        name = sample_name(Random(11), script_family=family, has_middle=True,
                           has_particle=True, hyphenated=False, has_title=True)
        legit = [{
            "person_id": f"BANK-{family}",
            "forename": name.forename(0),
            "surname": name.surname(0),
            "middle_name": name.middle.renderings[0] if name.middle else None,
            "title": name.title,
        }]
        failures = check_no_leak(legit)
        if failures:
            print(f"    FAIL  {family}: the gate rejected its own bank's "
                  f"output — {failures[0][:70]}")
            ok = False
    if ok:
        print("    ok    bank-produced names pass in every script family, so "
              "arm 3 discriminates rather than refusing everything")
    return ok


def check_artifact() -> bool:
    print("\n5 · the committed artifact holds no re-identifying field")
    if not ARTIFACT.exists():
        print(f"    FAIL  {ARTIFACT.name} is missing; run "
              f"generators/derive_psc_persons.py")
        return False

    doc = json.loads(ARTIFACT.read_text())
    ok = True

    controls = doc.get("privacy_controls") or {}
    if controls.get("mapping_retained") is not False:
        print("    FAIL  the artifact does not record that no real -> pseudonym "
              "mapping was kept")
        ok = False
    if not controls.get("raw_file_deleted"):
        print("    FAIL  the artifact records that the raw snapshot was NOT "
              "deleted — it was produced with --keep-raw")
        ok = False

    # A field whose name suggests it links back to the source person.
    forbidden = {"psc_id", "etag", "links", "real_name", "source_name",
                 "company_number", "original_name", "pseudonym_of"}
    present = set()
    for person in doc["persons"]:
        present |= forbidden & set(person)
    if present:
        print(f"    FAIL  person records carry back-reference field(s): "
              f"{sorted(present)}")
        ok = False

    # Every person must be traceable to a privacy decision, not merely assumed
    # to have had one.
    missing = [p["person_id"] for p in doc["persons"]
               if "joint_resampled" not in p or "stratified" not in p]
    if missing:
        print(f"    FAIL  {len(missing)} person(s) do not record how they were "
              f"sampled: {missing[:3]}")
        ok = False

    if ok:
        print(f"    ok    {doc['person_count']} persons; k={controls['k_anonymity']}, "
              f"dob banded to {controls['dob_band_years']}y, no mapping kept, "
              f"raw snapshot deleted")
    return ok


def check_distributions() -> bool:
    """The committed aggregates carry counts, and every rare row is gone.

    This file is what removed the need to ever re-fetch the snapshot, so it is
    permanently in the repository and permanently in the git history. A table
    that reached a count of 1 would publish a fact about one identifiable
    person forever — "one person controls 46 companies" names the register's
    most prolific controller.

    Both failure directions are tested: a table below k FAILS, and a table
    that is empty or absent FAILS too, because an aggregate file that quietly
    stopped carrying a distribution would still look private.
    """
    print(f"\n6 · the committed aggregates carry no identifiable row")
    if not DIST.exists():
        print(f"    FAIL  {DIST.name} is missing; the snapshot would have to "
              f"be re-fetched to rebuild the person layer")
        return False

    doc = json.loads(DIST.read_text())
    ok = True

    extra = set(doc) - DIST_KEYS
    if extra:
        print(f"    FAIL  unexpected key(s) in the aggregates: {sorted(extra)}")
        ok = False

    if doc.get("k_anonymity") != K_ANON:
        print(f"    FAIL  file records k={doc.get('k_anonymity')}, code uses "
              f"K_ANON={K_ANON}")
        ok = False

    for table in K_FILTERED_TABLES:
        rows = doc.get(table)
        if not rows:
            print(f"    FAIL  {table} is absent or empty — an aggregate file "
                  f"that stopped carrying a distribution still looks private")
            ok = False
            continue
        low = min(r["count"] for r in rows)
        if low < K_ANON:
            print(f"    FAIL  {table} has a row at count={low}, below "
                  f"k={K_ANON}")
            ok = False

    # A count is the only value any row may carry beyond its own key. A stray
    # name, date or identifier would be a string that is not a table key.
    for row in doc["joint_nationality_dob"]:
        if set(row) != {"nationality", "dob_band", "count"}:
            print(f"    FAIL  joint row carries unexpected field(s): "
                  f"{sorted(set(row))}")
            ok = False
            break

    if ok:
        mins = {t: min(r["count"] for r in doc[t]) for t in K_FILTERED_TABLES}
        print(f"    ok    {len(doc['structural'])} shape rows, "
              f"{len(doc['joint_nationality_dob'])} nationality/DOB rows; "
              f"every k-filtered table clears {K_ANON} (minima {mins})")
        print(f"          dropped below k: {doc['observations_dropped_below_k']}")
    return ok


def main() -> int:
    print("PSC pseudonymization — the identity cannot survive the pipeline")
    results = [
        check_shape_carries_no_name(),
        check_field_pin(),
        check_leak_gate(),
        check_leak_gate_falsification(),
        check_artifact(),
        check_distributions(),
    ]
    print(f"\n{sum(results)}/{len(results)} arms green")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
