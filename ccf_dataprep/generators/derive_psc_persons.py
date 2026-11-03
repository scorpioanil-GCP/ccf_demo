#!/usr/bin/env python3
"""Wave 13b Task 3 — derive a pseudonymized person layer from UK PSC data.

UK Companies House PSC records concern **real, named, living people**.
CLAUDE.md rule 3 and `docs/wave13b-design.md` §2 govern everything here. The
user approved fetching on 2026-08-22 on the condition that pseudonymization
happens **at ingestion**, which the design states as a rule about intermediate
state, not merely about output:

> No real PSC person name is written to any store, any artifact under
> `sources/`, or any file this repository tracks — at any point.

## How that rule is enforced, mechanically

1. The snapshot part is fetched to a scratch directory **outside the
   repository** (`ccf.fetch.fetch(..., dest_dir=...)`). The manifest records
   URL, retrieval date, sha256 and byte count — provenance that names the
   snapshot without carrying anyone's identity — and no payload.
2. `shape_of()` is the only function that sees a name. It returns a
   `PscShape` holding booleans, counts and controlled-vocabulary codes. No
   field of that dataclass derives from name text, and `SHAPE_FIELDS` pins the
   field list so that adding one is a deliberate act that trips an assertion
   rather than a quiet leak.
3. **No real -> pseudonym mapping is written anywhere.** Person identity across
   records is grouped by a salted hash whose salt is generated per run and
   discarded with the process. A mapping table is a re-identification key.
4. The raw file is deleted after the derivation runs.
5. The headline gate: every token of every emitted name must come from the
   closed vocabulary in `generators/name_bank.py`. A real name leaking into
   the output would not be in the bank, so this check can genuinely fail —
   which is the only reason it is worth running.

## What survives pseudonymization, and one thing that cannot

Preserved: name-shape distribution (titles, middle names, initials, particles,
hyphenation), nature-of-control codes **verbatim** (a public controlled
vocabulary, not personal data), and the joint nationality / date-of-birth
distribution.

**Transliteration structure has to be reconstructed, not preserved, and that
changes its provenance label.** Companies House publishes PSC names already
romanized, so the ambiguity §F5 wants — one native form admitting several Latin
renderings — is not observable in the source at all. It is rebuilt from the
nationality distribution using an invented name bank. Those cases are therefore
`synthetic — engineered`, and recording them as `public` would misrepresent
what the data proves.

## Privacy: k-anonymity on the resampled attributes

Nationality and date of birth are resampled from the observed JOINT
distribution, because sampling them independently would destroy the
correlation with name shape. A rare combination could be near-unique to one
living person, so only combinations with at least `K_ANON` observations are
eligible; rarer ones fall back to independent sampling. Years are banded
before resampling, never copied.

## The snapshot is fetched ONCE, ever

Everything this generator needs from Companies House is a **distribution**,
never a record. Those distributions are extracted, k-anonymised and committed
to `sources/screening/wave13b_psc_distributions.json` (114 KB, counts only).
After that this script prefers the committed file and does not download at all;
`--refresh-snapshot` forces a re-fetch and should almost never be needed.

That closes a real hole. `docs/wave13b-design.md` §7 accepted that re-deriving
would mean re-downloading 70 MB of real living people's records, and that the
snapshot is dated and gets replaced — so re-derivation was both a repeated
exposure and, increasingly, impossible. Committing the aggregates removes both:
the value was extracted once, and the thing that carried identities is gone.

`generate()` takes AGGREGATES ONLY, on both paths. There is no second code
path that could quietly depend on something the committed file does not carry.

## Idempotency, honestly stated

Re-running produces a DIFFERENT but structurally equivalent draw — the salt is
per-run and the sampling is random. That is why a plain run **refuses** to
overwrite an existing person artifact: the 210 persons are loaded, and
`bo_chain`, `person_name_variant`, `person_crosswalk`,
`sanctions_screening_result` and 32 KYC documents all reference them by
`person_key`, several by `display_name`. Redrawing is a data migration, not a
regeneration, and `--regenerate` says so.

Output: sources/screening/wave13b_psc_persons.json

    uv run generators/derive_psc_persons.py
    uv run generators/derive_psc_persons.py --keep-raw   # debugging only
"""

from __future__ import annotations

import argparse
import io
import json
import os
import secrets
import sys
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass, fields
from datetime import datetime, timezone
from hashlib import blake2b
from pathlib import Path
from random import Random

from ccf.config import REPO_ROOT
from ccf.fetch import SourceManifest, fetch
from generators.name_bank import (
    ELIGIBLE_PARTICLES,
    FORENAMES,
    SURNAMES,
    TITLES,
    sample_name,
)

SCREEN = REPO_ROOT / "sources" / "screening"
SNAPSHOT_DATE = "2026-08-22"
PART = "1of32"
URL = (f"https://download.companieshouse.gov.uk/"
       f"psc-snapshot-{SNAPSHOT_DATE}_{PART}.zip")

#: Outside the repository, deliberately. Never a path under REPO_ROOT.
SCRATCH = Path(
    os.getenv("CCF_SCRATCH", "/tmp/claude-1000/-home-parkave-ccf-dataprep/"
                             "a76f9e18-95c3-45b9-ae6a-6447d9e1b3dd/scratchpad")
) / "psc_raw"

#: §F2 asks for ~200 pseudonymized person nodes.
TARGET_PERSONS = 210

#: **A deliberate departure from the observed distribution, recorded here so
#: it is not mistaken for one.** PSC is dominated by British nationals (147k of
#: 184k in part 1), and a faithful resample of 210 persons yields ZERO
#: transliteration-capable names — §F5 asks for >= 2 transliteration cases, so
#: a faithful draw cannot satisfy it at all. These minima force a cohort that
#: can. Every person drawn this way carries `stratified: true`, and the
#: artifact records both the natural and the stratified distribution, because
#: presenting an over-represented cohort as emergent would misrepresent what
#: the data proves (CLAUDE.md rule 1).
MIN_PER_SCRIPT = {
    "cyrillic": 7,
    "arabic": 7,
    "han": 6,
    "greek": 5,
    "devanagari": 5,
    "latin_continental": 12,
}

#: Nationality -> a plausible country of residence for the EU-resident cohort
#: §F7 requires. PSC's own `country_of_residence` is overwhelmingly England,
#: so EU RESIDENCE (as distinct from EU nationality) has to be engineered.
EU_RESIDENCE = {
    "german": "Germany", "french": "France", "dutch": "Netherlands",
    "belgian": "Belgium", "italian": "Italy", "spanish": "Spain",
    "portuguese": "Portugal", "polish": "Poland", "romanian": "Romania",
    "swedish": "Sweden", "danish": "Denmark", "finnish": "Finland",
    "austrian": "Austria", "irish": "Ireland", "greek": "Greece",
    "czech": "Czechia", "slovak": "Slovakia", "hungarian": "Hungary",
    "lithuanian": "Lithuania", "latvian": "Latvia", "estonian": "Estonia",
    "bulgarian": "Bulgaria", "croatian": "Croatia", "slovenian": "Slovenia",
    "cypriot": "Cyprus", "luxembourgish": "Luxembourg", "maltese": "Malta",
}

#: Minimum observations before a (nationality, dob band) combination may be
#: resampled. Rarer combinations could point at one living person.
K_ANON = 20

#: Date-of-birth years are banded before resampling. An individual's year is
#: never copied to a synthetic person.
DOB_BAND_YEARS = 5

INDIVIDUAL_KIND = "individual-person-with-significant-control"

#: The committed aggregate tables. Once this file exists, the snapshot is
#: never needed again — see `to_distributions()` for what it may contain.
DISTRIBUTIONS = "wave13b_psc_distributions.json"

#: Nationality -> naming tradition. PSC publishes romanized names, so the
#: script a name came from cannot be read off the data; this mapping is how
#: transliteration structure is RECONSTRUCTED. It is a stated assumption, not
#: an observation — see the module docstring.
NATIONALITY_SCRIPT = {
    "russian": "cyrillic", "ukrainian": "cyrillic", "bulgarian": "cyrillic",
    "serbian": "cyrillic", "belarusian": "cyrillic", "kazakh": "cyrillic",
    "egyptian": "arabic", "syrian": "arabic", "lebanese": "arabic",
    "iraqi": "arabic", "jordanian": "arabic", "saudi": "arabic",
    "saudi arabian": "arabic", "moroccan": "arabic", "algerian": "arabic",
    "emirati": "arabic", "kuwaiti": "arabic", "libyan": "arabic",
    "tunisian": "arabic", "yemeni": "arabic", "palestinian": "arabic",
    "greek": "greek", "cypriot": "greek", "greek cypriot": "greek",
    "chinese": "han", "taiwanese": "han", "singaporean": "han",
    "hong kong": "han", "malaysian": "han",
    "indian": "devanagari", "nepalese": "devanagari", "nepali": "devanagari",
    "sri lankan": "devanagari", "bangladeshi": "devanagari",
}

#: Nationalities that romanize trivially but are not British — they carry
#: particles and spelling variants rather than transliterations.
CONTINENTAL = {
    "polish", "german", "dutch", "belgian", "swedish", "norwegian", "danish",
    "finnish", "austrian", "swiss", "portuguese", "spanish", "french",
    "italian", "romanian", "hungarian", "czech", "slovak", "lithuanian",
    "latvian", "estonian", "icelandic", "luxembourgish", "maltese",
}

#: EU/EEA nationalities, needed by §F7 (entities with EU-RESIDENT persons).
#: Residency is a separate field; this list only seeds plausible pairings.
EU_NATIONALITIES = {
    "german", "french", "dutch", "belgian", "italian", "spanish",
    "portuguese", "polish", "romanian", "swedish", "danish", "finnish",
    "austrian", "irish", "greek", "czech", "slovak", "hungarian",
    "lithuanian", "latvian", "estonian", "luxembourgish", "maltese",
    "bulgarian", "croatian", "slovenian", "cypriot",
}


@dataclass(frozen=True)
class PscShape:
    """The structure of one real PSC record, carrying none of its identity.

    Every field is a boolean, a count, or a controlled-vocabulary code. If
    this list ever grows a field holding name text, `SHAPE_FIELDS` below stops
    matching and the run aborts.
    """

    has_title: bool
    has_middle: bool
    middle_is_initial: bool
    forename_tokens: int
    surname_hyphenated: bool
    surname_has_particle: bool
    surname_has_apostrophe: bool
    has_diacritics: bool
    nationality: str
    country_of_residence: str
    dob_month: int
    dob_year: int
    natures_of_control: tuple[str, ...]
    ceased: bool


#: Pinned deliberately. Adding a field is a review, not an accident.
SHAPE_FIELDS = frozenset({
    "has_title", "has_middle", "middle_is_initial", "forename_tokens",
    "surname_hyphenated", "surname_has_particle", "surname_has_apostrophe",
    "has_diacritics", "nationality", "country_of_residence", "dob_month",
    "dob_year", "natures_of_control", "ceased",
})

PARTICLE_PREFIXES = (
    "van ", "van der ", "von ", "de ", "de la ", "del ", "della ", "di ",
    "da ", "dos ", "al ", "al-", "el-", "bin ", "ibn ", "mc", "mac", "o'",
    "st ", "st. ", "ter ", "ten ",
)


def shape_of(data: dict) -> PscShape | None:
    """Reduce one PSC record to its shape. THE ONLY function that sees a name.

    Returns None for records that cannot contribute a shape (no DOB, no
    nationality). Nothing derived from the name text escapes this function.
    """
    elements = data.get("name_elements") or {}
    forename = (elements.get("forename") or "").strip()
    middle = (elements.get("middle_name") or "").strip()
    surname = (elements.get("surname") or "").strip()
    title = (elements.get("title") or "").strip()
    if not surname:
        return None

    dob = data.get("date_of_birth") or {}
    month, year = dob.get("month"), dob.get("year")
    nationality = (data.get("nationality") or "").strip()
    if not month or not year or not nationality:
        return None

    lowered = surname.lower()
    ascii_name = f"{forename}{middle}{surname}".isascii()

    return PscShape(
        has_title=bool(title),
        has_middle=bool(middle),
        # A single-letter middle name is an initial. Registries differ on
        # whether they publish it at all, which is one of the variant
        # mechanisms §F5 counts.
        middle_is_initial=bool(middle) and len(middle.replace(".", "")) == 1,
        forename_tokens=len([t for t in forename.split() if t]),
        surname_hyphenated="-" in surname,
        surname_has_particle=lowered.startswith(PARTICLE_PREFIXES),
        surname_has_apostrophe="'" in surname or "’" in surname,
        has_diacritics=not ascii_name,
        nationality=nationality,
        country_of_residence=(data.get("country_of_residence") or "").strip(),
        dob_month=int(month),
        dob_year=int(year),
        natures_of_control=tuple(sorted(data.get("natures_of_control") or ())),
        ceased=bool(data.get("ceased_on")),
    )


def identity_group(data: dict, salt: bytes) -> str:
    """An in-memory grouping key for 'probably the same person'.

    Salted and never written anywhere. Its only job is to let the multiplicity
    distribution — how many companies one person controls — be measured. The
    salt dies with the process, so the key cannot be recomputed later even by
    someone holding both this code and the snapshot.
    """
    elements = data.get("name_elements") or {}
    dob = data.get("date_of_birth") or {}
    raw = "|".join([
        (elements.get("forename") or "").lower(),
        (elements.get("surname") or "").lower(),
        str(dob.get("month")), str(dob.get("year")),
    ]).encode("utf-8")
    return blake2b(raw, key=salt, digest_size=16).hexdigest()


def script_family_for(nationality: str) -> str:
    n = nationality.strip().lower()
    if n in NATIONALITY_SCRIPT:
        return NATIONALITY_SCRIPT[n]
    if n in CONTINENTAL:
        return "latin_continental"
    return "latin_gb"


def nationalities_by_family(joint: "Counter") -> dict[str, "Counter"]:
    """Observed nationalities, grouped by the naming tradition they map to.

    The stratified draw still samples REAL nationalities in their observed
    relative weights — it only changes how many persons are drawn from each
    family, never inventing a nationality PSC does not carry.
    """
    from collections import Counter as _C
    pools: dict[str, _C] = {}
    for (nat, _), n in joint.items():
        pools.setdefault(script_family_for(nat), _C())[nat] += n
    return pools


def band(year: int) -> int:
    return (year // DOB_BAND_YEARS) * DOB_BAND_YEARS


def scan(zip_path: Path, salt: bytes, limit: int | None) -> dict:
    """One pass. Emits distributions only — never a name, never a mapping."""
    zf = zipfile.ZipFile(zip_path)
    member = zf.namelist()[0]

    shapes: list[PscShape] = []
    joint: Counter = Counter()          # (nationality, dob band) -> count
    months: Counter = Counter()
    noc_combos: Counter = Counter()
    per_company: Counter = Counter()
    per_identity: Counter = Counter()
    kinds: Counter = Counter()
    scanned = 0

    with zf.open(member) as fh:
        for line in io.TextIOWrapper(fh, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            data = record.get("data") or {}
            kinds[data.get("kind")] += 1
            scanned += 1
            if data.get("kind") != INDIVIDUAL_KIND:
                continue

            shape = shape_of(data)
            if shape is None:
                continue

            shapes.append(shape)
            joint[(shape.nationality, band(shape.dob_year))] += 1
            months[shape.dob_month] += 1
            noc_combos[shape.natures_of_control] += 1
            per_company[record.get("company_number")] += 1
            per_identity[identity_group(data, salt)] += 1

            if limit and len(shapes) >= limit:
                break

    return {
        "scanned": scanned,
        "kinds": kinds,
        "shapes": shapes,
        "joint": joint,
        "months": months,
        "noc_combos": noc_combos,
        "per_company": per_company,
        "multiplicity": Counter(per_identity.values()),
    }


def to_distributions(stats: dict) -> dict:
    """Reduce the scan to committable aggregates. THE ONLY thing kept.

    ## Why this is committed and the snapshot is not

    Everything the person layer needs from Companies House is a
    **distribution**, never a record. Keeping the distributions means the
    snapshot is fetched once, ever: `derive_psc_persons.py` prefers this file
    and only downloads when it is missing.

    That matters beyond convenience. The snapshot is dated and Companies House
    replaces it, so re-deriving from source is already not reproducible — and
    every re-fetch is a fresh 70 MB of real living people's records on disk for
    the length of a run. Extracting the value once and committing the
    aggregates removes a standing, repeatable exposure for something already
    extracted.

    ## Why k-anonymity is applied HERE, not only at sampling time

    `generate()` already refuses to sample a (nationality, dob band)
    combination with fewer than `K_ANON` observations. That protects the
    output. It does nothing for a committed FILE, which would otherwise
    publish rows like "1 person, Tuvaluan, born 1920-24" — a re-identification
    signal in its own right, sitting in a git history forever.

    So every table that could carry a rare combination is filtered to
    `>= K_ANON` before writing, and the number of observations dropped is
    recorded rather than hidden.

    **`dob_bands` and `multiplicity` are filtered too, and an earlier version
    of this docstring was wrong to call them safe.** Measured: both bottomed
    out at a count of **1**. A single-axis table is not automatically
    anonymous — "one person controls 46 companies" names the most prolific
    controller in the register, and that person is findable. Only `dob_months`
    (12 rows, minimum 35,577) and `ceased` (2 rows, minimum 83,890) are left
    unfiltered, because their cardinality genuinely cannot isolate anyone.
    """
    dropped: dict[str, int] = {}

    def keep(counter: Counter, label: str) -> Counter:
        kept = Counter({k: v for k, v in counter.items() if v >= K_ANON})
        dropped[label] = sum(counter.values()) - sum(kept.values())
        return kept

    # Structural shape, stripped of nationality, DOB and control codes — the
    # 8 fields that describe how a name is WRITTEN and nothing about who wrote
    # it. Counted as combinations so the correlations survive (a title and a
    # middle initial travel together).
    structural: Counter = Counter()
    residence: Counter = Counter()
    ceased: Counter = Counter()
    bands: Counter = Counter()
    for sh in stats["shapes"]:
        structural[(sh.has_title, sh.has_middle, sh.middle_is_initial,
                    sh.forename_tokens, sh.surname_hyphenated,
                    sh.surname_has_particle, sh.surname_has_apostrophe,
                    sh.has_diacritics)] += 1
        residence[sh.country_of_residence] += 1
        ceased[sh.ceased] += 1
        bands[band(sh.dob_year)] += 1

    kept_structural = keep(structural, "structural")
    kept_joint = keep(stats["joint"], "joint_nationality_dob")
    kept_noc = keep(stats["noc_combos"], "natures_of_control")
    kept_residence = keep(residence, "country_of_residence")
    kept_bands = keep(bands, "dob_bands")
    kept_multiplicity = keep(stats["multiplicity"], "multiplicity")

    return {
        "k_anonymity": K_ANON,
        "dob_band_years": DOB_BAND_YEARS,
        "observations_dropped_below_k": dropped,
        "source_records_scanned": stats["scanned"],
        "individual_shapes_used": len(stats["shapes"]),
        "structural": [
            {"has_title": k[0], "has_middle": k[1], "middle_is_initial": k[2],
             "forename_tokens": k[3], "surname_hyphenated": k[4],
             "surname_has_particle": k[5], "surname_has_apostrophe": k[6],
             "has_diacritics": k[7], "count": v}
            for k, v in sorted(kept_structural.items(), key=lambda kv: -kv[1])
        ],
        "joint_nationality_dob": [
            {"nationality": k[0], "dob_band": k[1], "count": v}
            for k, v in sorted(kept_joint.items(), key=lambda kv: -kv[1])
        ],
        "natures_of_control": [
            {"codes": list(k), "count": v}
            for k, v in sorted(kept_noc.items(), key=lambda kv: -kv[1])
        ],
        "country_of_residence": [
            {"country": k, "count": v}
            for k, v in sorted(kept_residence.items(), key=lambda kv: -kv[1])
        ],
        "dob_months": [{"month": k, "count": v}
                       for k, v in sorted(stats["months"].items())],
        "dob_bands": [{"band": k, "count": v}
                      for k, v in sorted(kept_bands.items())],
        "multiplicity": [{"companies": k, "count": v}
                         for k, v in sorted(kept_multiplicity.items())],
        "ceased": [{"ceased": k, "count": v} for k, v in sorted(ceased.items())],
    }


def load_distributions(doc: dict) -> dict:
    """Rehydrate the committed aggregates into the Counters generate() uses."""
    return {
        "structural": Counter({
            (r["has_title"], r["has_middle"], r["middle_is_initial"],
             r["forename_tokens"], r["surname_hyphenated"],
             r["surname_has_particle"], r["surname_has_apostrophe"],
             r["has_diacritics"]): r["count"]
            for r in doc["structural"]}),
        "joint": Counter({(r["nationality"], r["dob_band"]): r["count"]
                          for r in doc["joint_nationality_dob"]}),
        "noc_combos": Counter({tuple(r["codes"]): r["count"]
                               for r in doc["natures_of_control"]}),
        "residence": Counter({r["country"]: r["count"]
                              for r in doc["country_of_residence"]}),
        "months": Counter({r["month"]: r["count"] for r in doc["dob_months"]}),
        "bands": Counter({r["band"]: r["count"] for r in doc["dob_bands"]}),
        "multiplicity": Counter({r["companies"]: r["count"]
                                 for r in doc["multiplicity"]}),
        "ceased": Counter({r["ceased"]: r["count"] for r in doc["ceased"]}),
        "scanned": doc["source_records_scanned"],
        "shapes_used": doc["individual_shapes_used"],
    }


def weighted_choice(rng: Random, counter: Counter):
    items, weights = zip(*counter.items())
    return rng.choices(items, weights=weights, k=1)[0]


def generate(dist: dict, rng: Random) -> list[dict]:
    """Invent the person layer from the observed distributions.

    Takes AGGREGATES only — never a list of per-record shapes. That is the
    single code path whether the aggregates came from a fresh scan or from the
    committed `wave13b_psc_distributions.json`, which is what makes the
    committed file provably sufficient: there is no second path that could
    quietly depend on something the file does not carry.
    """
    eligible_joint = Counter(
        {k: v for k, v in dist["joint"].items() if v >= K_ANON}
    )
    if not eligible_joint:
        raise RuntimeError(
            f"no (nationality, dob band) combination reaches K_ANON={K_ANON}; "
            f"refusing to resample from combinations that could identify "
            f"an individual"
        )

    nationalities_only = Counter()
    for (nat, _), n in dist["joint"].items():
        nationalities_only[nat] += n

    pools = nationalities_by_family(dist["joint"])

    # The stratified quota, drawn first; the remainder follows the observed
    # distribution. `natural_families` records what a faithful draw looked
    # like, so the artifact can state the departure rather than hide it.
    quota: list[str] = []
    for family, n in MIN_PER_SCRIPT.items():
        if family in pools:
            quota.extend([family] * n)
        else:
            raise RuntimeError(
                f"no observed nationality maps to script family {family!r}; "
                f"the stratified minimum cannot be met from real nationalities"
            )
    rng.shuffle(quota)

    people = []
    for i in range(TARGET_PERSONS):
        # One draw from the structural distribution: title, middle name,
        # particle and hyphenation arrive together, so the correlations
        # between them survive the aggregation.
        (has_title, has_middle, _middle_is_initial, _forename_tokens,
         hyphenated, has_particle, _apostrophe,
         _diacritics) = weighted_choice(rng, dist["structural"])
        stratified = i < len(quota)

        if stratified:
            family_wanted = quota[i]
            nationality = weighted_choice(rng, pools[family_wanted])
            year_band = weighted_choice(rng, dist["bands"])
            joint_sampled = False
        # Joint resample where the combination is common enough; independent
        # fallback where it is not. Which path was taken is recorded per
        # person, so the privacy control is visible in the artifact rather
        # than asserted in a comment.
        elif rng.random() < 0.9:
            nationality, year_band = weighted_choice(rng, eligible_joint)
            joint_sampled = True
        else:
            nationality = weighted_choice(rng, nationalities_only)
            year_band = weighted_choice(rng, dist["bands"])
            joint_sampled = False

        dob_year = year_band + rng.randrange(DOB_BAND_YEARS)
        dob_month = weighted_choice(rng, dist["months"])
        family = script_family_for(nationality)

        name = sample_name(
            rng,
            script_family=family,
            has_middle=has_middle,
            has_particle=has_particle,
            hyphenated=hyphenated,
            has_title=has_title,
        )

        noc = list(weighted_choice(rng, dist["noc_combos"]))
        multiplicity = weighted_choice(rng, dist["multiplicity"])

        nat_l = nationality.strip().lower()
        # §F7 needs EU-RESIDENT persons, which PSC's own residence field will
        # not supply — it is overwhelmingly England. Residence is engineered
        # for a majority of EU nationals and flagged per person.
        residence = weighted_choice(rng, dist["residence"])
        residence_engineered = False
        if nat_l in EU_RESIDENCE and rng.random() < 0.65:
            residence = EU_RESIDENCE[nat_l]
            residence_engineered = True
        people.append(
            {
                "person_id": f"PSC-{i + 1:04d}",
                "display_name": name.display(0),
                "forename": name.forename(0),
                "surname": name.surname(0),
                "middle_name": (
                    name.middle.renderings[0] if name.middle else None
                ),
                "title": name.title,
                "script_family": name.script_family,
                "native_forename": name.given.native,
                "native_surname": name.family.native,
                "particle": name.particle,
                "is_transliterated": name.transliterated,
                "rendering_count": name.rendering_count(),
                "nationality": nationality,
                "is_eu_national": nat_l in EU_NATIONALITIES,
                "country_of_residence": residence,
                "residence_engineered": residence_engineered,
                "dob_month": dob_month,
                "dob_year": dob_year,
                "dob_band": year_band,
                "natures_of_control": noc,
                "controls_n_companies": multiplicity,
                "ceased": weighted_choice(rng, dist["ceased"]),
                "joint_resampled": joint_sampled,
                "stratified": stratified,
                "provenance": "synthetic — engineered",
            }
        )
    return people


def bank_vocabulary() -> set[str]:
    """Every token the name bank can emit. The leak gate compares against this."""
    vocab: set[str] = set()
    for pool in (FORENAMES, SURNAMES):
        for parts in pool.values():
            for part in parts:
                for rendering in part.renderings:
                    vocab.update(rendering.replace("-", " ").split())
    for forms in ELIGIBLE_PARTICLES.values():
        for particle in forms:
            from generators.name_bank import PARTICLES
            for rendered in PARTICLES[particle]:
                vocab.update(rendered.replace("-", " ").split())
    vocab.update(TITLES)
    return vocab


def check_no_leak(people: list[dict]) -> list[str]:
    """The headline gate: every emitted name token comes from the bank.

    A real PSC name reaching the output would carry tokens the bank does not
    contain. This is the check that can actually fail, and therefore the only
    one that proves the claim.
    """
    from generators.name_bank import NO_SPACE_PARTICLES, PARTICLES

    # Flush-bound particles (O'Brien, McLeod, al-Najjar) produce ONE token, so
    # the bare token is not in the vocabulary even though both halves are. The
    # prefix is stripped before comparison rather than added to the vocabulary,
    # so `O'` + an unknown surname still fails.
    flush = tuple(sorted(
        (form for particle in NO_SPACE_PARTICLES for form in PARTICLES[particle]),
        key=len, reverse=True,
    ))

    def known(token: str) -> bool:
        """A token passes as-is, or after removing a flush-bound particle.

        As-is is tried FIRST and that ordering is load-bearing: `O` is one of
        the renderings of the `O'` particle, so stripping unconditionally
        turned the bank's own `Oleksandr` into `leksandr` and failed it. The
        strip is a fallback for tokens the bank does not contain, never a
        rewrite of tokens it does.
        """
        if token in vocab:
            return True
        for prefix in flush:
            if token.startswith(prefix) and len(token) > len(prefix):
                if token[len(prefix):] in vocab:
                    return True
        return False

    vocab = bank_vocabulary()
    failures = []
    for p in people:
        tokens: list[str] = []
        for field_name in ("forename", "surname", "middle_name", "title"):
            value = p.get(field_name)
            if value:
                tokens.extend(value.replace("-", " ").split())
        unknown = [t for t in tokens if not known(t)]
        if unknown:
            failures.append(f"{p['person_id']}: token(s) outside the name "
                            f"bank: {unknown}")
    return failures


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--keep-raw", action="store_true",
                    help="do not delete the snapshot after derivation "
                         "(debugging only — it holds real person data)")
    ap.add_argument("--limit", type=int, default=None,
                    help="stop after N individual records (faster iteration)")
    ap.add_argument("--distributions-only", action="store_true",
                    help="scan the snapshot, write the aggregate tables, "
                         "delete the raw file, and stop. Never touches the "
                         "person artifact")
    ap.add_argument("--refresh-snapshot", action="store_true",
                    help="re-fetch the snapshot even though the aggregates "
                         "exist. Downloads 70MB of real person records")
    ap.add_argument("--regenerate", action="store_true",
                    help="REDRAW the person layer, overwriting the committed "
                         "artifact. See the guard in main() first")
    args = ap.parse_args()

    # Structural guard: the shape dataclass has not grown a name-bearing field.
    actual = {f.name for f in fields(PscShape)}
    if actual != SHAPE_FIELDS:
        raise RuntimeError(
            f"PscShape fields changed: {actual ^ SHAPE_FIELDS}. Every field "
            f"must be a boolean, a count, or a controlled-vocabulary code. "
            f"Update SHAPE_FIELDS deliberately after confirming no field "
            f"carries name text."
        )

    manifest = SourceManifest(
        source="psc",
        description=(
            "UK Companies House PSC snapshot, part 1 of 32. PROVENANCE ONLY — "
            "the payload is fetched outside the repository, pseudonymized in "
            "the reading pass, and deleted. No PSC person name is stored here "
            "or anywhere this repository tracks."
        ),
        licence="Companies House data is published under the Open Government "
                "Licence v3.0. The OGL permits reuse; UK data protection law "
                "still governs the personal data within it, which is why this "
                "project pseudonymizes at ingestion.",
    )

    print("Wave 13b Task 3 — pseudonymized PSC person layer\n")

    dist_path = SCREEN / DISTRIBUTIONS
    persons_path = SCREEN / "wave13b_psc_persons.json"
    raw = None

    # --- where do the distributions come from? ----------------------------
    #
    # The committed aggregates are preferred, always. Everything this
    # generator needs from Companies House is a distribution, and the
    # snapshot is dated and gets replaced — so re-fetching is both a fresh
    # exposure and, increasingly, not even reproducible.
    if dist_path.exists() and not args.refresh_snapshot:
        doc = json.loads(dist_path.read_text())
        dist = load_distributions(doc)
        print(f"  source     {dist_path.name}  (committed aggregates; "
              f"NO snapshot fetched)")
        print(f"             derived from {doc['source_records_scanned']:,} "
              f"records, {doc['individual_shapes_used']:,} usable shapes")
        print(f"             k={doc['k_anonymity']}, dropped below k: "
              f"{doc['observations_dropped_below_k']}")
    else:
        why = ("--refresh-snapshot" if args.refresh_snapshot
               else f"{dist_path.name} is absent")
        print(f"  snapshot   {SNAPSHOT_DATE} part {PART}   ({why})")
        print(f"  scratch    {SCRATCH}  (outside the repository)")
        raw = fetch(URL, manifest, f"psc-{SNAPSHOT_DATE}_{PART}.zip",
                    dest_dir=SCRATCH, timeout=600)

        salt = secrets.token_bytes(32)   # per-run, discarded with the process
        stats = scan(raw, salt, args.limit)

        print(f"\n  scanned    {stats['scanned']:,} PSC records")
        for kind, n in stats["kinds"].most_common():
            print(f"      {(kind or '?')[:52]:<52} {n:>7,}")
        print(f"  usable individual shapes: {len(stats['shapes']):,}")
        print(f"  distinct (nationality, dob band): {len(stats['joint']):,}  "
              f"({sum(1 for v in stats['joint'].values() if v >= K_ANON)} reach "
              f"K_ANON={K_ANON})")
        print(f"  nature-of-control combinations: {len(stats['noc_combos']):,}")

        doc = to_distributions(stats)
        dist = load_distributions(doc)
        dist_path.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
        print(f"\n  written: {dist_path.relative_to(REPO_ROOT)}  "
              f"({dist_path.stat().st_size / 1e3:.0f} KB)")
        print(f"      k={K_ANON} applied to every table that could carry a "
              f"rare combination; dropped: "
              f"{doc['observations_dropped_below_k']}")

        # The raw file goes NOW, before anything else can read it.
        if args.keep_raw:
            print(f"  WARNING: --keep-raw left real PSC data at {raw}")
        else:
            raw.unlink(missing_ok=True)
            print(f"  deleted raw snapshot ({raw.name}) — provenance kept in "
                  f"sources/psc/manifest.json, contents not")

    if args.distributions_only:
        print("\n  --distributions-only: person layer untouched")
        return 0

    # --- the guard on redrawing -------------------------------------------
    #
    # The 210 persons in the committed artifact are LOADED and referenced by
    # `bo_chain`, `person_name_variant`, `person_crosswalk`,
    # `sanctions_screening_result` and 32 KYC documents — all by `person_key`
    # and several by `display_name`. A redraw invents different people and
    # silently orphans every one of those references. It is a data migration,
    # not a regeneration.
    if persons_path.exists() and not args.regenerate:
        print(f"\n  {persons_path.name} already exists and is LOADED.")
        print(f"  Refusing to redraw: bo_chain, person_name_variant, "
              f"person_crosswalk, sanctions_screening_result and the KYC "
              f"documents all reference these person_keys.")
        print(f"  Pass --regenerate only as part of a deliberate migration "
              f"that reloads every one of them.")
        return 0

    people = generate(dist, Random(secrets.randbits(32)))

    failures = check_no_leak(people)
    translit = [p for p in people if p["is_transliterated"]]
    eu = [p for p in people if p["is_eu_national"]]
    scripts = Counter(p["script_family"] for p in people)
    natural_scripts = Counter(p["script_family"] for p in people
                              if not p["stratified"])
    eu_resident = [p for p in people
                   if p["country_of_residence"] in set(EU_RESIDENCE.values())]
    joint_share = sum(1 for p in people if p["joint_resampled"]) / len(people)

    print(f"\n  generated  {len(people)} persons")
    print(f"      script families      {dict(scripts.most_common())}")
    print(f"      transliteration      {len(translit)} persons "
          f"(§F5 wants >= 2 CASES; the resolution layer draws them from here)")
    print(f"      EU nationals         {len(eu)}, of whom "
          f"{len(eu_resident)} are EU-RESIDENT (§F7)")
    print(f"      stratified quota     {sum(1 for p in people if p['stratified'])} "
          f"persons; the unstratified remainder drew "
          f"{dict(natural_scripts.most_common(4))}")
    print(f"      joint-resampled      {joint_share:.0%} "
          f"(remainder used the independent fallback)")

    print(f"\n  NAME-LEAK GATE: every emitted token must come from the bank")
    if failures:
        for f in failures[:5]:
            print(f"      FAIL  {f}")
        print(f"      {len(failures)} person(s) failed. Nothing written.")
        return 1
    print(f"      ok    {len(people)} persons, "
          f"{len(bank_vocabulary())} tokens in the bank vocabulary")

    out = SCREEN / "wave13b_psc_persons.json"
    out.write_text(
        json.dumps(
            {
                "generated_for": "Wave 13b — pseudonymized person layer derived "
                                 "from UK Companies House PSC "
                                 f"snapshot {SNAPSHOT_DATE} part {PART}",
                "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "provenance": "synthetic — engineered",
                "provenance_note": (
                    "Identities are invented. Name-shape, nature-of-control and "
                    "the joint nationality/DOB distributions are derived from the "
                    "PSC snapshot named above; no real name, DOB or mapping is "
                    "retained. Transliteration structure is RECONSTRUCTED from "
                    "nationality rather than observed — Companies House publishes "
                    "PSC names already romanized, so the ambiguity is not present "
                    "in the source."
                ),
                "source_snapshot": {
                    "url": URL,
                    "snapshot_date": SNAPSHOT_DATE,
                    "part": PART,
                    "records_scanned": dist["scanned"],
                    "individual_shapes_used": dist["shapes_used"],
                    # Which path this run took. A person layer drawn from the
                    # committed aggregates never touched the snapshot at all,
                    # and saying so is the point of keeping them.
                    "derived_from": ("committed aggregates "
                                     f"({DISTRIBUTIONS})" if raw is None
                                     else "a fresh snapshot fetch"),
                },
                "privacy_controls": {
                    "k_anonymity": K_ANON,
                    "dob_band_years": DOB_BAND_YEARS,
                    "mapping_retained": False,
                    # True when no snapshot was fetched at all, which is the
                    # steady state once the aggregates are committed.
                    "raw_file_deleted": raw is None or not args.keep_raw,
                    "snapshot_fetched": raw is not None,
                },
                "stratification": {
                    "note": "MIN_PER_SCRIPT forces a transliteration-capable "
                            "cohort. A faithful resample of PSC yields zero "
                            "such persons, so §F5 could not be satisfied by "
                            "one. This over-represents non-British "
                            "nationalities relative to the source.",
                    "minima": MIN_PER_SCRIPT,
                    "stratified_persons": sum(1 for p in people if p["stratified"]),
                    "unstratified_script_mix": dict(natural_scripts),
                },
                "eu_resident_count": len(eu_resident),
                "person_count": len(people),
                "transliterated_count": len(translit),
                "eu_national_count": len(eu),
                "persons": people,
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
