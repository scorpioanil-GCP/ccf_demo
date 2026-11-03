# Migration Transition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the composed spread series respond to a rating-band migration — the market leg follows the in-force band, and an engineered anticipatory ramp carries the transition.

**Architecture:** A new `generators/narrative_wave11a.py` holds the engineered declarations both generators need, which dissolves the artifact-mediated dependency cycle between them. The pipeline reorders so `generate_spreads.py` runs *after* `generate_grades.py` and reads the grade chains. Band selection becomes per-observation-date; an anticipation ramp scaled by the real inter-band OAS gap is added to the already-engineered idiosyncratic leg.

**Tech Stack:** Python 3.12, stdlib only (`json`, `datetime`, `random`, `statistics`), `psycopg` via `ccf.config.pg_connect`, Fluree over SPARQL via `ccf.fluree`. Tests are plain executable scripts in the `validators/test_*.py` idiom — **not pytest** — each returning a `list[tuple[str, bool]]` of cases and exiting non-zero on failure.

**Spec:** `docs/wave11a-migration-transition-design.md`

## Global Constraints

- **Run every command with `.venv/bin/python`** (or `uv run`). A bare `python3` lacks `dotenv`/`psycopg` and fails at import.
- **`SEED = 20260817`** — identical in `generate_spreads.py` and `generate_grades.py`. The narrative module declares its own copy for the profile shuffle.
- **`WINDOW_START = date(2024, 8, 19)`, `WINDOW_END = date(2026, 8, 18)`.**
- **`DOMINANCE_CEILING = 0.40`.** If a run breaches it, that is a design finding to report — **never** raise the ceiling.
- **Provenance is per column and never blends.** `market_oas_bp` is `public`; `idiosyncratic_bp` is `synthetic — engineered`. The ramp goes in the latter.
- **Generators are idempotent.** Two consecutive runs must produce byte-identical artifacts.
- **Fluree is not touched by this work.** No grade assertion, no supersession edge, no reload.
- **`docs/ccf_dataprep_v2.md` is the current reference and must be updated** (CLAUDE.md standing rule).
- **No new FIBO terms are bound**, so no vault mirror refresh is triggered.

## Deviation from the approved spec — read before Task 5

Spec §5 says a missing `oas[T][d]` or `oas[F][d]` should record no observation, "matching the existing benchmark rule."

**Implement a loud `RuntimeError` instead.** `build_observations`' own docstring documents a measured invariant: *"every curve date inside the window is present in every band's OAS series (measured: 0 gaps across all five bands), so driving by curve dates can never manufacture a missing-OAS case."* Because the loop is driven by curve dates, a skip branch would be unreachable code that silently weakens a guarantee the file currently states. A `RuntimeError` naming the invariant preserves the guarantee and matches how `fetch_market_oas.py` already handles a header mismatch. Recorded here rather than applied silently.

---

## File Structure

| File | Responsibility |
|---|---|
| `generators/narrative_wave11a.py` | **new** — engineered declarations shared by both generators: divergence windows, their artifact projection, migration response profiles, profile assignment |
| `generators/generate_grades.py` | imports declarations instead of reading `wave11a_spreads.json`. No behavioural change |
| `generators/generate_spreads.py` | reads `wave11a_grades.json`; per-date band selection; the anticipation ramp |
| `validators/test_migration.py` | **new** — pure tests for profile assignment, ramp weight, crossing discovery |
| `validators/series.py` | new migration-transition checks recomputed from the loaded series |
| `docs/ccf_dataprep_v2.md`, `docs/known-issues.md`, `docs/HANDOFF.md` | reference, defect record, resume point |

---

## Task 1: Extract the narrative module (pure refactor, zero behaviour change)

**Files:**
- Create: `generators/narrative_wave11a.py`
- Modify: `generators/generate_spreads.py` (remove `DIVERGENCES`, `DIVERGENCE_RAMP_FRACTION`; import them)
- Modify: `generators/generate_grades.py:158-162` (`load_divergence_windows`)

**Interfaces:**
- Consumes: nothing
- Produces: `DIVERGENCES: list[dict]`, `DIVERGENCE_RAMP_FRACTION: float`, `divergence_windows_for_artifact(instruments: list[dict]) -> list[dict]`

The whole point of this task is that **the artifacts must not change one byte.** That is the test.

- [ ] **Step 1: Capture the pre-refactor baseline**

```bash
cd /home/parkave/ccf_dataprep
mkdir -p /tmp/mt-baseline
cp sources/screening/wave11a_spreads.json sources/screening/wave11a_grades.json /tmp/mt-baseline/
sha256sum /tmp/mt-baseline/*.json | tee /tmp/mt-baseline/SHA256
```

Expected: two hashes printed. These are the contract for Steps 6–7.

- [ ] **Step 2: Create the narrative module**

Create `generators/narrative_wave11a.py`. Move the `DIVERGENCES` literal and `DIVERGENCE_RAMP_FRACTION` **verbatim** out of `generate_spreads.py:118-160` (do not retype them — copy, so a transcription slip cannot change a date).

```python
#!/usr/bin/env python3
"""Engineered narrative for Wave 11a, shared by both generators.

WHY THIS MODULE EXISTS. `generate_grades.py` used to recover these
declarations by reading `wave11a_spreads.json` and parsing its
`divergence_windows` key -- which is nothing but a projection of the
`DIVERGENCES` literal below. That made grades depend on the spreads
ARTIFACT, which forced spreads to run first, which is why spreads could not
read the grade chains and so pinned its market leg to the day-1 rating band
(known-issues.md 9.10).

The dependency was on CONFIGURATION, not on computation. Declaring it in one
place both generators import dissolves the cycle at no behavioural cost.
"""

from __future__ import annotations

from datetime import date
from random import Random

SEED = 20260817  # identical to both generators; the shuffle must be stable

# --- divergence windows: MOVED VERBATIM from generate_spreads.py ----------
DIVERGENCES: list[dict] = [
    # ... paste the four entries exactly as they were ...
]
DIVERGENCE_RAMP_FRACTION = 0.25  # each side of the trapezoid


def divergence_windows_for_artifact(instruments: list[dict]) -> list[dict]:
    """The `divergence_windows` projection: DIVERGENCES enriched with each
    instrument's `lei` and `rating_band`.

    Lives here, not in either generator, because BOTH need it -- spreads to
    write it into its artifact, grades to consume it. Two implementations of
    one projection is how they would drift apart.
    """
    by_id = {i["instrument_id"]: i for i in instruments}
    return [
        {
            "instrument_id": dv["instrument_id"],
            "lei": by_id[dv["instrument_id"]]["lei"],
            "rating_band": by_id[dv["instrument_id"]]["rating_band"],
            "start_date": dv["start"].isoformat(),
            "end_date": dv["end"].isoformat(),
            "peak_bp": dv["peak_bp"],
            "confirm_later": dv["confirm_later"],
            "note": dv["note"],
        }
        for dv in DIVERGENCES
    ]
```

- [ ] **Step 3: Point `generate_spreads.py` at the module**

Delete the `DIVERGENCES` literal and `DIVERGENCE_RAMP_FRACTION` from `generate_spreads.py`. Add to its imports:

```python
from generators.narrative_wave11a import (DIVERGENCE_RAMP_FRACTION,
                                          DIVERGENCES,
                                          divergence_windows_for_artifact)
```

Replace the inline `"divergence_windows": [...]` comprehension in the artifact payload (around line 502) with:

```python
        "divergence_windows": divergence_windows_for_artifact(instruments),
```

- [ ] **Step 4: Point `generate_grades.py` at the module**

Replace `load_divergence_windows` (lines 158-162):

```python
def load_divergence_windows() -> list[dict]:
    """The declared windows, enriched -- read from the shared narrative
    module, NOT from wave11a_spreads.json. See narrative_wave11a.py's module
    docstring: that artifact read was the dependency cycle.
    """
    payload = json.loads((SCREEN / "wave11a_instruments.json").read_text())
    return sorted(divergence_windows_for_artifact(payload["instruments"]),
                  key=lambda w: w["instrument_id"])
```

Add the import:

```python
from generators.narrative_wave11a import divergence_windows_for_artifact
```

**Check the key name first** — confirm `wave11a_instruments.json` uses `instruments`:

```bash
.venv/bin/python -c "import json;print(list(json.load(open('sources/screening/wave11a_instruments.json'))))"
```

- [ ] **Step 5: Regenerate both artifacts**

```bash
.venv/bin/python generators/generate_grades.py
.venv/bin/python generators/generate_spreads.py
```

Expected: both succeed. `generate_spreads.py` still prints its condition table and a dominance ratio near `0.1893`.

- [ ] **Step 6: Verify byte-identity — the whole test for this task**

```bash
.venv/bin/python - <<'PY'
import json, pathlib
for name in ("wave11a_spreads.json", "wave11a_grades.json"):
    new = json.loads(pathlib.Path("sources/screening", name).read_text())
    old = json.loads(pathlib.Path("/tmp/mt-baseline", name).read_text())
    new.pop("generated_at", None); old.pop("generated_at", None)
    print(f"{name}: {'IDENTICAL' if new == old else 'DIFFERS'}")
PY
```

Expected: **both `IDENTICAL`.** Anything else means the refactor changed behaviour — stop and diff before continuing.

- [ ] **Step 7: Run the existing suite**

```bash
.venv/bin/python validators/test_curves.py
```

Expected: `29/29 cases behave as specified`.

- [ ] **Step 8: Commit**

```bash
git add generators/narrative_wave11a.py generators/generate_spreads.py generators/generate_grades.py sources/screening/
git commit -m "Extract the shared narrative module; dissolve the generators' dependency cycle

generate_grades.py recovered the DIVERGENCES declarations by reading
wave11a_spreads.json -- a dependency on configuration wearing the costume of
a dependency on computation. Both generators now import one declaration.

Verified: both artifacts byte-identical modulo generated_at. Pure refactor."
```

---

## Task 2: Migration response profiles and permutation assignment

**Files:**
- Modify: `generators/narrative_wave11a.py`
- Create: `validators/test_migration.py`

**Interfaces:**
- Consumes: `SEED` from Task 1's module
- Produces: `MIGRATION_PROFILES: list[dict]`, `assign_profiles(leis: list[str]) -> dict[str, dict]` returning `{lei: {"name": str, "anticipation": float, "lead_obs": int}}`

- [ ] **Step 1: Write the failing test**

Create `validators/test_migration.py`:

```python
#!/usr/bin/env python3
"""Pure tests for the migration-transition mechanics.

    uv run validators/test_migration.py
"""

from __future__ import annotations

import sys

from generators.narrative_wave11a import MIGRATION_PROFILES, assign_profiles

THREE = ["5493003QENHHS261UR94", "5493004HBTOTE9DI9P12", "549300EQD0ZXRSMG3549"]


def check_profiles() -> list[tuple[str, bool]]:
    a = assign_profiles(THREE)
    b = assign_profiles(list(reversed(THREE)))
    names = sorted(p["name"] for p in a.values())
    return [
        ("catalogue holds exactly three profiles", len(MIGRATION_PROFILES) == 3),
        ("anticipation values are 0.30/0.60/0.90",
         sorted(p["anticipation"] for p in MIGRATION_PROFILES) == [0.30, 0.60, 0.90]),
        ("lead is uncorrelated with anticipation -- the weakest has the longest lead",
         max(MIGRATION_PROFILES, key=lambda p: p["lead_obs"])["anticipation"] == 0.30),
        ("three LEIs receive three DISTINCT profiles", len(set(names)) == 3),
        ("assignment is deterministic across runs", a == assign_profiles(THREE)),
        ("assignment does not depend on input order", a == b),
        ("a fourth LEI cycles rather than crashing",
         len(assign_profiles(THREE + ["EXTRA0000000000000X"])) == 4),
        ("no LEI means no assignment", assign_profiles([]) == {}),
    ]


def main() -> int:
    cases = check_profiles()
    failures = sum(not ok for _, ok in cases)
    for label, ok in cases:
        print(f"  [{'ok  ' if ok else 'FAIL'}] {label}")
    print(f"\n  {len(cases) - failures}/{len(cases)} cases behave as specified\n")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run it to confirm it fails**

```bash
.venv/bin/python validators/test_migration.py
```

Expected: `ImportError: cannot import name 'MIGRATION_PROFILES'`.

- [ ] **Step 3: Implement in `narrative_wave11a.py`**

```python
#: Market response to a band migration. Three shapes, DELIBERATELY
#: UNCORRELATED: the faintest signal carries the longest lead. A dataset
#: where strong signals always arrive early teaches a detector to read
#: timing as strength -- an artifact of this generator, not a fact about
#: credit markets, and Wave 11b is measured against exactly this.
#:
#: `lead_obs` is counted in OBSERVATION DATES present in the Treasury curve,
#: never calendar days: a calendar lead silently shortens across holidays.
MIGRATION_PROFILES: list[dict] = [
    {"name": "faint",      "anticipation": 0.30, "lead_obs": 110},
    {"name": "moderate",   "anticipation": 0.60, "lead_obs": 40},
    {"name": "pronounced", "anticipation": 0.90, "lead_obs": 75},
]


def assign_profiles(leis: list[str]) -> dict[str, dict]:
    """{lei: profile} by a seeded SHUFFLE of the catalogue over sorted LEIs.

    A permutation, NOT an independent per-LEI draw. Three independent draws
    from three profiles collide with probability ~0.78, so the "vary across
    the three" requirement would silently fail most of the time and the
    failure would look like data rather than like a bug. Sorting first makes
    the result independent of the caller's ordering.
    """
    ordered = sorted(leis)
    if not ordered:
        return {}
    shuffled = list(MIGRATION_PROFILES)
    Random(f"{SEED}|migration-profiles").shuffle(shuffled)
    return {lei: shuffled[i % len(shuffled)] for i, lei in enumerate(ordered)}
```

- [ ] **Step 4: Run the test**

```bash
.venv/bin/python validators/test_migration.py
```

Expected: `8/8 cases behave as specified`.

- [ ] **Step 5: Record which LEI drew which profile**

```bash
.venv/bin/python -c "
from generators.narrative_wave11a import assign_profiles
for lei, p in sorted(assign_profiles(['5493003QENHHS261UR94','5493004HBTOTE9DI9P12','549300EQD0ZXRSMG3549']).items()):
    print(f'{lei}  {p[\"name\"]:<11} alpha={p[\"anticipation\"]}  lead={p[\"lead_obs\"]}')
"
```

Paste the output into the task notes — it is an **observed outcome**, and Task 8 records it in the design doc and `known-issues.md`. Do not hardcode it anywhere.

- [ ] **Step 6: Commit**

```bash
git add generators/narrative_wave11a.py validators/test_migration.py
git commit -m "Migration response profiles, assigned by seeded permutation

Three shapes (0.30/110, 0.60/40, 0.90/75), anticipation deliberately
uncorrelated with lead. Assignment is a shuffle, not an independent draw:
three draws from three profiles collide ~78% of the time, which would break
the vary-across-obligors requirement invisibly. 8/8 tests."
```

---

## Task 3: The ramp weight and its start date

**Files:**
- Modify: `generators/generate_spreads.py`
- Modify: `validators/test_migration.py`

**Interfaces:**
- Consumes: nothing
- Produces: `migration_ramp_weight(idx: int, start_idx: int, m_idx: int) -> float`, `ramp_start_index(m_idx: int, lead_obs: int, floor_idx: int) -> int`

Indices into the ordered curve-date list, not dates — that is what makes "lead in observation dates" exact and keeps both functions pure and trivially testable.

- [ ] **Step 1: Write the failing tests**

Append to `validators/test_migration.py`:

```python
from generators.generate_spreads import migration_ramp_weight, ramp_start_index


def check_ramp() -> list[tuple[str, bool]]:
    m, start = 100, 60          # 40 observation dates of lead
    w = lambda i: migration_ramp_weight(i, start, m)
    return [
        ("weight is 0 at the ramp start", w(start) == 0.0),
        ("weight is 0 before the ramp start", w(start - 5) == 0.0),
        ("weight is 0 AT the migration -- anticipation is consumed", w(m) == 0.0),
        ("weight is 0 after the migration", w(m + 30) == 0.0),
        ("weight approaches 1 just before the migration", w(m - 1) == 0.975),
        ("weight is monotone non-decreasing across the ramp",
         all(w(i) <= w(i + 1) for i in range(start, m - 1))),
        ("weight never exceeds 1", all(w(i) <= 1.0 for i in range(start, m))),
        ("a zero-length ramp yields no weight rather than dividing by zero",
         migration_ramp_weight(50, 50, 50) == 0.0),
        ("lead is clipped at the window floor",
         ramp_start_index(m_idx=30, lead_obs=110, floor_idx=0) == 0),
        ("lead is clipped at a previous migration",
         ramp_start_index(m_idx=200, lead_obs=110, floor_idx=150) == 150),
        ("an unobstructed lead is taken in full",
         ramp_start_index(m_idx=200, lead_obs=40, floor_idx=0) == 160),
    ]
```

Add `check_ramp()` to `main()`'s `cases`.

- [ ] **Step 2: Run to confirm failure**

```bash
.venv/bin/python validators/test_migration.py
```

Expected: `ImportError: cannot import name 'migration_ramp_weight'`.

- [ ] **Step 3: Implement in `generate_spreads.py`**

Place next to `divergence_weight` so the two ramp idioms sit together:

```python
def ramp_start_index(m_idx: int, lead_obs: int, floor_idx: int) -> int:
    """First observation index of the anticipation ramp for a migration at
    `m_idx`, clipped at `floor_idx`.

    `floor_idx` is whichever comes later: the start of the window, or the
    obligor's PREVIOUS migration. Anticipation cannot begin before the
    announcement it follows -- an obligor that crosses twice would otherwise
    have the second ramp running while the first was still being priced.
    """
    return max(floor_idx, m_idx - lead_obs)


def migration_ramp_weight(idx: int, start_idx: int, m_idx: int) -> float:
    """Linear 0 -> 1 across [start_idx, m_idx), and 0 from m_idx onward.

    Zero AT the migration, not 1: the anticipation is CONSUMED by the
    announcement. That is what leaves the composed spread with a residual
    jump of (1 - alpha) * gap rather than a full one.

    Linear, matching `divergence_weight`'s ramps -- one ramp idiom per file.
    An accelerating profile is arguably more faithful to how anticipation
    builds, but adds a shape parameter with nothing real to validate against.
    """
    span = m_idx - start_idx
    if span <= 0 or idx < start_idx or idx >= m_idx:
        return 0.0
    return (idx - start_idx) / span
```

- [ ] **Step 4: Run the tests**

```bash
.venv/bin/python validators/test_migration.py
```

Expected: `19/19 cases behave as specified`.

- [ ] **Step 5: Commit**

```bash
git add generators/generate_spreads.py validators/test_migration.py
git commit -m "Anticipation ramp weight and its clipped start index

Indices into the ordered curve-date list, so 'lead in observation dates' is
exact and both functions stay pure. Weight is 0 AT the migration -- the
anticipation is consumed by the announcement, which is what produces the
(1-alpha)*gap residual jump. 19/19 tests."
```

---

## Task 4: Discover band crossings from the grade chains

**Files:**
- Modify: `generators/generate_spreads.py`
- Modify: `validators/test_migration.py`

**Interfaces:**
- Consumes: `sources/screening/wave11a_grades.json`
- Produces: `band_of_grade(grade: str) -> str`, `load_band_crossings() -> dict[str, list[dict]]` returning `{lei: [{"asserted_at": date, "from_band": str, "to_band": str}, ...]}` sorted by `asserted_at`

- [ ] **Step 1: Write the failing tests**

Append to `validators/test_migration.py`:

```python
from datetime import date
from generators.generate_spreads import band_of_grade, crossings_from_chain


def check_crossings() -> list[tuple[str, bool]]:
    chain = [
        {"grade": "BB",  "asserted_at": "2024-08-21"},
        {"grade": "BB-", "asserted_at": "2024-11-20"},   # notch move, same band
        {"grade": "B",   "asserted_at": "2025-11-19"},   # DOWNGRADE across band
        {"grade": "BB",  "asserted_at": "2026-05-23"},   # UPGRADE back
    ]
    out = crossings_from_chain(chain)
    return [
        ("band strips a minus modifier", band_of_grade("BB-") == "BB"),
        ("band strips a plus modifier", band_of_grade("A+") == "A"),
        ("a plain grade is its own band", band_of_grade("BBB") == "BBB"),
        ("a notch move inside one band is not a crossing", len(out) == 2),
        ("the downgrade is found with its asserted_at",
         out[0] == {"asserted_at": date(2025, 11, 19), "from_band": "BB", "to_band": "B"}),
        ("the recovery is found as a separate crossing",
         out[1] == {"asserted_at": date(2026, 5, 23), "from_band": "B", "to_band": "BB"}),
        ("crossings come back in asserted_at order",
         out[0]["asserted_at"] < out[1]["asserted_at"]),
        ("a chain that never leaves its band yields nothing",
         crossings_from_chain([{"grade": "A", "asserted_at": "2024-08-21"},
                               {"grade": "A-", "asserted_at": "2025-01-01"}]) == []),
        ("a single-assertion chain yields nothing",
         crossings_from_chain([{"grade": "A", "asserted_at": "2024-08-21"}]) == []),
    ]
```

Add `check_crossings()` to `main()`.

- [ ] **Step 2: Run to confirm failure**

Expected: `ImportError: cannot import name 'band_of_grade'`.

- [ ] **Step 3: Implement in `generate_spreads.py`**

```python
def band_of_grade(grade: str) -> str:
    """Strip the +/- modifier to recover the band letter.

    Deliberately duplicated from generate_grades.py rather than imported:
    importing it would recreate the generators' dependency in the opposite
    direction, which is the defect this whole change exists to remove.
    Three characters of logic; the coupling would cost more.
    """
    return grade.rstrip("+-")


def crossings_from_chain(chain: list[dict]) -> list[dict]:
    """Band crossings in one obligor's grade chain, in asserted_at order.

    Keyed on `asserted_at`, NOT `valid_from`: the market cannot price what it
    has not been told. The 1-5 day booking lag between the two therefore
    stays visible in the series as a window where the grade is already in
    force and the market leg has not yet stepped -- a free illustration of
    the bitemporal distinction this estate exists to teach.
    """
    rows = sorted(chain, key=lambda a: a["asserted_at"])
    out: list[dict] = []
    for prev, cur in zip(rows, rows[1:]):
        f, t = band_of_grade(prev["grade"]), band_of_grade(cur["grade"])
        if f != t:
            out.append({"asserted_at": date.fromisoformat(cur["asserted_at"]),
                        "from_band": f, "to_band": t})
    return out


def load_band_crossings() -> dict[str, list[dict]]:
    """{lei: [crossing, ...]} from the grade chains. Only LEIs that cross."""
    path = SCREEN / "wave11a_grades.json"
    if not path.exists():
        raise RuntimeError(
            "wave11a_grades.json is absent. Since the migration-transition "
            "change, generate_spreads.py runs AFTER generate_grades.py -- run "
            "generators/generate_grades.py first. (See "
            "docs/wave11a-migration-transition-design.md section 4.)")
    by_lei: dict[str, list[dict]] = {}
    for a in json.loads(path.read_text())["assertions"]:
        by_lei.setdefault(a["lei"], []).append(a)
    out = {lei: crossings_from_chain(chain) for lei, chain in by_lei.items()}
    return {lei: c for lei, c in out.items() if c}
```

**Note the `zip(rows, rows[1:])`** — deliberately not `strict=`, because the two slices differ in length by construction. This is the one place in this codebase where an unequal `zip` is correct; `parse_treasury_row` uses `strict=True` for the opposite reason.

- [ ] **Step 4: Run the tests**

Expected: `28/28 cases behave as specified`.

- [ ] **Step 5: Verify against the real chains**

```bash
.venv/bin/python -c "
from generators.generate_spreads import load_band_crossings
c = load_band_crossings()
print('obligors that cross:', len(c), '| crossings:', sum(len(v) for v in c.values()))
for lei, xs in sorted(c.items()):
    for x in xs: print(' ', lei, x['from_band'], '->', x['to_band'], x['asserted_at'])
"
```

Expected exactly:
```
obligors that cross: 3 | crossings: 4
  5493003QENHHS261UR94 BB -> B 2025-11-19
  5493003QENHHS261UR94 B -> BB 2026-05-23
  5493004HBTOTE9DI9P12 BBB -> BB 2026-03-31
  549300EQD0ZXRSMG3549 B -> BB 2026-05-19
```

If the counts differ, **stop** — the seed or the grade chains have changed, and Task 7's existence assertion is the thing to reconcile against.

- [ ] **Step 6: Commit**

```bash
git add generators/generate_spreads.py validators/test_migration.py
git commit -m "Discover band crossings from the grade chains, keyed on asserted_at

Migrations are discovered, not declared -- generate_grades.py is untouched
and all 245 assertions stand. Verified against the loaded chains: 3 obligors,
4 crossings, two downgrades and two upgrades. 28/28 tests."
```

---

## Task 5: Wire the ramp into `build_observations`

**Files:**
- Modify: `generators/generate_spreads.py` (`build_observations`, ~lines 308-375)

**Interfaces:**
- Consumes: everything from Tasks 2–4
- Produces: `spread_observation` rows whose `market_oas_bp` follows the in-force band

- [ ] **Step 1: Add the per-instrument migration schedule**

Inside `build_observations`, before the instrument loop:

```python
    crossings_by_lei = load_band_crossings()
    profile_by_lei = assign_profiles(sorted(crossings_by_lei))
    dates = [d for d, _ in curve]                     # ordered observation dates
    index_of = {d: i for i, d in enumerate(dates)}
```

- [ ] **Step 2: Build each instrument's schedule inside the loop**

After `divergence = divergence_by_instrument.get(iid)`:

```python
        lei = inst["lei"]
        schedule: list[dict] = []
        floor_idx = 0
        for x in crossings_by_lei.get(lei, []):
            # bisect, because asserted_at may fall on a non-observation day
            m_idx = bisect.bisect_left(dates, x["asserted_at"])
            if m_idx >= len(dates):
                continue                              # announced after the window
            prof = profile_by_lei[lei]
            schedule.append({
                "m_idx": m_idx,
                "start_idx": ramp_start_index(m_idx, prof["lead_obs"], floor_idx),
                "from_band": x["from_band"],
                "to_band": x["to_band"],
                "anticipation": prof["anticipation"],
            })
            floor_idx = m_idx        # the next ramp cannot precede this one

        for s in schedule:
            wanted = profile_by_lei[lei]["lead_obs"]
            actual = s["m_idx"] - s["start_idx"]
            if actual < wanted:
                print(f"    [note] {iid} {lei}: ramp truncated "
                      f"{wanted} -> {actual} observation dates "
                      f"(window start or a prior migration)")
```

Spec §5 requires truncation to be **reported, not special-cased** — silent
truncation would make a short ramp indistinguishable from a chosen one.

Add `import bisect` at the top of the file.

- [ ] **Step 3: Replace the fixed band with the in-force band**

Replace `market_oas_bp = oas[band][d]` (line ~360) with:

```python
            idx = index_of[d]
            in_force = band
            for s in schedule:
                if idx >= s["m_idx"]:
                    in_force = s["to_band"]

            if d not in oas[in_force]:
                raise RuntimeError(
                    f"no OAS for band {in_force} on curve date {d}. "
                    "build_observations' invariant is that every curve date "
                    "in the window is present in every band's series "
                    "(measured: 0 gaps across all five bands). Re-measure "
                    "before weakening this.")
            market_oas_bp = oas[in_force][d]

            anticipation_bp = 0.0
            for s in schedule:
                w = migration_ramp_weight(idx, s["start_idx"], s["m_idx"])
                if w:
                    gap = oas[s["to_band"]][d] - oas[s["from_band"]][d]
                    anticipation_bp += s["anticipation"] * gap * w
```

and change the idiosyncratic line to:

```python
            idiosyncratic_bp = baseline + ar1_state + bump + anticipation_bp
```

**`in_force` walks the whole schedule rather than breaking**, so the second crossing correctly overrides the first for an obligor that crosses twice. `anticipation_bp` sums because ramps could in principle overlap; Step 2's `floor_idx` makes that impossible today, and summing keeps it correct if it ever stops being.

- [ ] **Step 4: Confirm `lei` is on the instrument record**

```bash
.venv/bin/python -c "import json;print(list(json.load(open('sources/screening/wave11a_instruments.json'))['instruments'][0]))"
```

Expected: a list containing `lei`. If absent, join via the obligors list rather than inventing a field.

- [ ] **Step 5: Regenerate and read the numbers**

```bash
.venv/bin/python generators/generate_spreads.py
```

Expected: all §F condition lines still `[ok]` — 4 divergence windows, 2 sparse instruments, ≥55 instruments, ≥450 observation dates. **Record the printed dominance ratio.**

- [ ] **Step 6: Gate on dominance**

If the ratio exceeds `0.40`, **stop and report.** Per the spec's §8 risk 1, the honest responses are a lower `α` ceiling or excluding transition dates from the dominance pool the way divergence dates already are — never raising the ceiling.

- [ ] **Step 7: Verify the transition is actually in the series**

```bash
.venv/bin/python - <<'PY'
import json, collections
from datetime import date
d = json.load(open("sources/screening/wave11a_spreads.json"))
obs = collections.defaultdict(dict)
for o in d["observations"]:
    obs[o["instrument_id"]][o["obs_date"]] = o
inst = {i["instrument_id"]: i for i in json.load(
    open("sources/screening/wave11a_instruments.json"))["instruments"]}
from generators.generate_spreads import load_band_crossings
for lei, xs in sorted(load_band_crossings().items()):
    iids = [k for k, v in inst.items() if v["lei"] == lei]
    for x in xs:
        m = x["asserted_at"].isoformat()
        for iid in iids:
            ds = sorted(obs[iid])
            after = [k for k in ds if k >= m]
            before = [k for k in ds if k < m]
            if not after or not before:
                continue
            b, a = obs[iid][before[-1]], obs[iid][after[0]]
            print(f"{iid} {lei[:8]} {x['from_band']}->{x['to_band']} @{m}  "
                  f"market {b['market_oas_bp']:.0f}->{a['market_oas_bp']:.0f}  "
                  f"idio {b['idiosyncratic_bp']:.0f}->{a['idiosyncratic_bp']:.0f}  "
                  f"spread {b['spread_bp']:.0f}->{a['spread_bp']:.0f}")
PY
```

Expected for each of the 4 crossings: `market_oas_bp` **steps** in the direction of the crossing, `idiosyncratic_bp` **steps back toward baseline**, and `spread_bp` moves by roughly `(1-α)` of the market step.

- [ ] **Step 8: Verify idempotency**

```bash
sha256sum sources/screening/wave11a_spreads.json
.venv/bin/python generators/generate_spreads.py >/dev/null
.venv/bin/python -c "
import json;d=json.load(open('sources/screening/wave11a_spreads.json'))
print('observations:', len(d['observations']))"
```

Then re-run the Step 6 comparison from Task 1 against a copy taken before the second run, ignoring `generated_at`. Expected: identical.

- [ ] **Step 9: Commit**

```bash
git add generators/generate_spreads.py sources/screening/wave11a_spreads.json
git commit -m "The market leg follows the in-force band; the engineered leg carries the transition

market_oas_bp is now the real published index for whichever band is in force,
stepping at asserted_at. An anticipation ramp scaled by the real inter-band
gap is added to idiosyncratic_bp, so provenance stays one class per column --
no blended value, no fourth column.

Dominance ratio after the change: SUBSTITUTE the figure printed in Step 5
before committing -- this line is a measurement, not a description."
```

---

## Task 6: Reload Postgres and re-verify the estate

**Files:**
- Modify: none. This task runs loaders and validators.

- [ ] **Step 1: Reload**

```bash
.venv/bin/python loaders/load_postgres_wave11a.py
```

Expected: `spread_observation` reloaded, ~29,885 rows. Row count may shift slightly if any observation was skipped; record the number.

- [ ] **Step 2: Artifact reproduces store**

```bash
.venv/bin/python validators/artifact_reproduces_store.py
```

Expected: `40/42`. The two failures must be *only* the pre-existing Wave 10 `person_name_variant` and `person_crosswalk` duplicates (known-issues §8.16). **Any spread-related failure is a real divergence — stop.**

- [ ] **Step 3: Conditions and partition**

```bash
.venv/bin/python validators/conditions.py | tail -3
.venv/bin/python validators/partition.py | tail -3
```

Expected: `82 passed · 0 failed` and `13/13`. Neither should move — no §F condition depends on migration response, and no column changed store.

- [ ] **Step 4: Series (pre-new-checks)**

```bash
.venv/bin/python validators/series.py | tail -6
```

Expected: `PASS`, still 4 divergence windows, 1 confirmed-later, 2 sparse, dominance under 0.40.

- [ ] **Step 5: Commit any artifact drift**

```bash
git status --short
git commit -am "Reload spread_observation after the migration transition" || echo "nothing to commit"
```

---

## Task 7: Validate the transition from the loaded series

**Files:**
- Modify: `validators/series.py`

**Interfaces:**
- Consumes: `load_grade_history()` (extended), `load_instrument_series()`
- Produces: a new `MIGRATION TRANSITION` section in `main()`'s output

- [ ] **Step 1: Extend `load_grade_history` to carry assertion time**

`load_grade_history` returns `(valid_from, valid_to, notch, trigger)` — valid time only. The check needs `asserted_at`. `ex:assertedAt` **is** loaded into Fluree (`load_fluree_wave11a.py:266`), so add it to the SPARQL projection and to the tuple:

```python
    SELECT ?grade ?validFrom ?validTo ?assertedAt ?trigger ?lei FROM <{L}> WHERE {{
      ...
      ?a <{EX}assertedAt> ?assertedAt .
```

Return `(vf, vt, notch, trigger, grade, asserted_at)` where `asserted_at` is a
**`date`, not the raw SPARQL string** — parse it the same way `validFrom`
already is:

```python
        aa = date.fromisoformat(b["assertedAt"]["value"])
```

Sorting and comparison in `migration_transitions` depend on this; a string
would sort correctly by luck of ISO format and then fail the `obs_date`
comparison against a `date` column.

**Update every existing unpacking site** — find them first:

```bash
grep -n "load_grade_history\|for vf, vt" validators/series.py
```

- [ ] **Step 2: Add the migration checks**

```python
def migration_transitions(cur, history) -> list[tuple[str, bool, str]]:
    """Recompute each band crossing's market step and residual jump from the
    LOADED series -- never from a generator flag, matching how divergence and
    sparsity are already established here.
    """
    from generators.narrative_wave11a import assign_profiles
    from generators.generate_spreads import band_of_grade

    crossings = {}
    for lei, rows in history.items():
        seq = sorted(rows, key=lambda r: r[5])          # by asserted_at
        xs = [(cur_r[5], band_of_grade(prev[4]), band_of_grade(cur_r[4]))
              for prev, cur_r in zip(seq, seq[1:])
              if band_of_grade(prev[4]) != band_of_grade(cur_r[4])]
        if xs:
            crossings[lei] = xs

    out = [("at least one band crossing exists in the loaded chains",
            len(crossings) >= 1,
            f"{len(crossings)} obligor(s), "
            f"{sum(len(v) for v in crossings.values())} crossing(s)")]
    if not crossings:
        return out          # the assertion above already failed loudly

    profiles = assign_profiles(sorted(crossings))
    for lei, xs in sorted(crossings.items()):
        alpha = profiles[lei]["anticipation"]
        for m, f, t in xs:
            ok, detail = _check_one_transition(cur, lei, m, f, t, alpha)
            out.append((f"{lei[:8]} {f}->{t} @{m}: step and residual jump "
                        f"match alpha={alpha}", ok, detail))
    return out
```

And the per-transition check itself:

```python
TRANSITION_TOLERANCE = 0.15
#: Wide ON PURPOSE. The AR(1) idiosyncratic walk runs underneath every
#: observation, so a tight bound would be asserting that noise is absent
#: rather than that the ramp is present. 15% still fails a pinned band
#: (which produces a 0bp step, not a within-tolerance one).


def _check_one_transition(cur, lei, m, f, t, alpha) -> tuple[bool, str]:
    """Measure one crossing's market step and residual jump from the loaded
    rows. Returns (ok, human-readable detail) -- the detail is printed
    whether or not the check passes, because a number you can read beats a
    boolean you have to trust.
    """
    cur.execute(f'''
        SELECT o.obs_date, o.market_oas_bp, o.spread_bp
          FROM "{S}".spread_observation o
          JOIN "{S}".debt_instrument i USING (instrument_id)
         WHERE i.lei = %s AND o.obs_date BETWEEN %s AND %s
         ORDER BY o.obs_date''', (lei, m - timedelta(days=20), m + timedelta(days=20)))
    rows = cur.fetchall()
    before = [r for r in rows if r[0] < m]
    after = [r for r in rows if r[0] >= m]
    if not before or not after:
        return False, "no observations on one side of the announcement"

    b_date, b_mkt, b_spread = before[-1]
    a_date, a_mkt, a_spread = after[0]
    gap = float(a_mkt) - float(b_mkt)
    if abs(gap) < 1.0:
        return False, (f"market_oas_bp did not step at the announcement "
                       f"({b_mkt} -> {a_mkt}) -- the band is still pinned")

    jump = float(a_spread) - float(b_spread)
    expected = (1.0 - alpha) * gap
    ok = abs(jump - expected) <= TRANSITION_TOLERANCE * abs(gap)
    return ok, (f"market {b_mkt:.0f}->{a_mkt:.0f} (gap {gap:+.0f}bp), "
                f"spread jump {jump:+.0f}bp vs expected {expected:+.0f}bp "
                f"at alpha={alpha}")
```

Add `from datetime import timedelta` if it is not already imported.

The residual jump is checked rather than the pre-announcement ramp because it is the sharper test: a pinned band produces a **0bp** market step, which `abs(gap) < 1.0` rejects outright with a message naming the actual defect. A ramp that failed to build would show up as a jump equal to the full gap, which 15% tolerance also rejects.

- [ ] **Step 3: Wire into `main()` and print**

Add a `MIGRATION TRANSITION (known-issues §9.10)` section alongside the existing DIVERGENCE / SPARSITY / DOMINANCE sections, in the same `[ok  ]` / `[FAIL]` format, and fold its failures into the exit code.

- [ ] **Step 4: Run it**

```bash
.venv/bin/python validators/series.py
```

Expected: `PASS`, with the existence check and all 4 transition checks `[ok]`.

- [ ] **Step 5: Negative-test the new check**

A check that has never failed is not known to work. Temporarily change the tolerance to `0.001` and confirm the transition checks **FAIL**, then restore it.

```bash
.venv/bin/python validators/series.py | grep -c FAIL   # expect > 0 while tightened
```

- [ ] **Step 6: Full suite**

```bash
for t in validators/test_*.py; do echo -n "$(basename $t): "; .venv/bin/python "$t" | grep "cases behave"; done
```

Expected: all 9 files pass, including the new `test_migration.py`.

- [ ] **Step 7: Commit**

```bash
git add validators/series.py
git commit -m "series.py: validate the migration transition from the loaded series

Asserts at least one band crossing EXISTS -- the crossings are a property of
this seed, and a reseed could remove the product's subject silently. Then
recomputes each transition's market step and residual jump against the
obligor's assigned alpha, within 15% relative tolerance.

Negative-tested by tightening the tolerance and confirming failure."
```

---

## Task 8: Documentation

**Files:**
- Modify: `docs/ccf_dataprep_v2.md`, `docs/known-issues.md` (§9.10), `docs/HANDOFF.md`, `docs/wave11a-migration-transition-design.md`

- [ ] **Step 1: `ccf_dataprep_v2.md`**

Add a `2026-08-20 — Wave 11a migration transition` entry recording: the composed-spread formula now using the in-force band, the anticipation ramp and its provenance, **the observed profile assignment from Task 2 Step 5**, the measured dominance ratio, and the new pipeline order. State explicitly that **no FIBO term was added, so the vault mirror needs no refresh.**

- [ ] **Step 2: Add the regeneration sequence — it is documented nowhere today**

`grep` confirms no doc carries the generator run order; only `docs/wave11a-plan.md` implies it through task numbering, and that order is now wrong. Add to `ccf_dataprep_v2.md`:

```
generators/generate_instruments.py
generators/generate_grades.py      # MUST precede spreads
generators/generate_spreads.py     # reads wave11a_grades.json
loaders/load_postgres_wave11a.py
loaders/load_fluree_wave11a.py
```

- [ ] **Step 3: Rewrite `known-issues.md` §9.10**

Retitle to `🟠 FIXED 2026-08-20`. Keep the original defect description and the four-option table — that record is why the fix looks the way it does. Append what was built, the measured before/after, and correct the original entry's "3 crossings" to **4 crossings across 3 obligors, two of them upgrades**.

- [ ] **Step 4: `HANDOFF.md`**

Update §8 to state Wave 11a's spread series now responds to migrations, and **remove the line naming this as Wave 11b's first open question** — it is answered. Point 11b at the design doc instead.

- [ ] **Step 5: Design doc status**

Change the header to `**Status:** implemented 2026-08-20`, and record the two things that were only knowable at implementation time: the observed profile assignment, and the measured dominance ratio.

- [ ] **Step 6: Final verification**

```bash
.venv/bin/python validators/partition.py   | tail -2
.venv/bin/python validators/conditions.py  | tail -2
.venv/bin/python validators/series.py      | tail -2
.venv/bin/python validators/artifact_reproduces_store.py | tail -2
for t in validators/test_*.py; do echo -n "$(basename $t): "; .venv/bin/python "$t" | grep "cases behave"; done
```

Expected: `13/13` · `82 passed · 0 failed` · `PASS` · `40/42` · all 9 test files passing.

- [ ] **Step 7: Commit**

```bash
git add docs/
git commit -m "Document the migration transition; known-issues 9.10 -> FIXED

Records the observed profile assignment and the measured dominance ratio,
adds the generator run order (documented nowhere before this, and now
changed), and retires the Wave 11b open question that this work answers.

No FIBO term added; the vault mirror needs no refresh."
```

---

## Notes for the executor

**Verify before trusting.** Several steps print an expected value. If what you see differs, that is a finding, not a nuisance — say so rather than adjusting the expectation.

**The three gates that must not be quietly relaxed:**
1. Task 1 Step 6 — byte-identical artifacts. A pure refactor that changes output is not a pure refactor.
2. Task 5 Step 6 — dominance ≤ 0.40. Report a breach; never raise the ceiling.
3. Task 7 Step 5 — the new check must be shown to fail when it should.

**Do not touch Fluree.** If you find yourself reloading it, you have left this plan's scope.
