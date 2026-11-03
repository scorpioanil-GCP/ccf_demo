# Wave 12 Implementation Plan — `treasury-liquidity-position` · `fx-post-trade-reconciliation`

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Load the `treasury.liquidity-position.v1` and `markets.fx-reconciliation.v1` data products across Postgres and Fluree so that every §F condition — including the four that counting rows cannot establish — is satisfiable by a real query against loaded data.

**Architecture:** Two public fetchers (FRED rates, DTCC Part 43) feed a shared rate foundation. The treasury product interpolates a 5-minute intraday tick series between real published daily closes, so its 8bp condition is produced by the real data's own geometry rather than injected. The FX product patterns 500 generated trades on distributions derived from ~37,000 real G10 Part 43 records, then engineers two break populations, one of which must invert under clock alignment. Two new validators recompute both engineered conditions from loaded data rather than reading a generator's flag.

**Tech Stack:** Python 3.12 · `uv` · psycopg 3 · Fluree 4.1.4 (SPARQL, explicit `FROM <ledger>`) · `requests` · stdlib `zipfile` + `csv` (no new dependency)

**Spec:** `docs/wave12-design.md` — read it before Task 1. The plan argues from the spec; the spec carries the five measured feasibility probes and the four recorded user decisions.

## Global Constraints

Copied verbatim from CLAUDE.md and `docs/wave12-design.md`. Every task's requirements implicitly include this section.

- **Tick window is 2026-05-11 → 2026-06-23**, 30 trading days, carrying 7 real ≥8bp days. Decision D3, design §1.3. Not the most recent window — that one has zero margin.
- **The 8bp move is never injected.** Every tick day opens at the prior session's published close and terminates at that day's published close, both read unmodified from `benchmark_curve`. Design §3.1.
- **Rate spans match `benchmark_curve`** — 2024-01-02 onward, ~665 trading days. The three rate tables share one calendar.
- **21 FRED series are fetched** — 5 SOFR (rate + 4 percentiles), 11 DGS tenors, 5 FX. They yield **six** pairs: five fetched plus `EUR/GBP`, which FRED does not publish and which is derived as a cross. Ruling F7.
- **The six FX pairs are EUR/USD, USD/JPY, AUD/USD, USD/CAD, GBP/USD, EUR/GBP**, normalised to market convention at the fetch boundary, once. Design §4.3.
- **Part 43 real trades are never loaded as trades.** Only derived distributions cross the boundary. The shape is `public`; every generated instance is `synthetic — engineered`. Design §2.2.
- **Three provenance classes, labelled per element**: `public`, `synthetic — internal`, `synthetic — engineered`. Never two.
- **Single-writer discipline.** One store is authoritative per element. Never duplicate an attribute across stores "for convenience."
- **Do not assume OWL inference.** Fluree runs without reasoning. Type entities explicitly for every role you query against.
- **Fluree 4.1.4 SPARQL requires an explicit `FROM <ledger>`** — omitting it returns HTTP 500, not 400. `ccf/fluree.py` guards this.
- **Every Fluree reconcile scopes retraction by SUBJECT, never by predicate.** `known-issues.md` §10.5. Non-negotiable — this is a deletion bug, not an error.
- **Instance URIs stay under `http://example.org/fibo/`** (`EX` in `ccf/config.py`). Real LEIs live in the `lei` attribute, never in the URI.
- **Every loader is `--dry-run` capable and idempotent.** You will reload many times.
- **Every `ON CONFLICT ... DO UPDATE SET` sets EVERY non-key column**, or the table is delete-then-insert. No column is left to go stale silently.
- **Every generator records `_inputs`** via `ccf.currency.record_inputs`; every consumer calls `ccf.currency.verify_current`. A bare `json.loads` of an upstream artifact is a defect.
- **Baseline that must not regress:** `partition.py` 19/19 · `conditions.py` 91 passed / 0 failed · `series.py` PASS · `surveillance.py` PASS · `intraday.py` 9/0 · `orphan_terms.py` **73/73** · `artifact_reproduces_store.py` 54/56 (the two §8.16 duplicates) · `binding_drift.py` 11 agree / **30** disagree · test suites green. Any other red is a regression.
  - orphan_terms moved 67→73 and binding_drift 29→30 at Task 9: six new Wave 12 `ex:` terms, all reproducible from source, and one new materialized term the vault mirror has not yet been told about. Both are expected movement, recorded so a later reader does not read them as drift.
- **`sources/` is gitignored** except `sources/screening/*.json`. Generator artifacts go to `sources/screening/` **and are COMMITTED with the generator that produced them** — ruling F17. `validators/artifact_reproduces_store.py` proves that *tracked* artifacts reproduce the live store, so an untracked artifact is invisible to it and the wave silently gets zero coverage there. 42 artifacts from earlier waves are tracked; the largest is 7.6MB.
- **Never enumerate MongoDB databases.** The Mongo host also carries `rtdetect` (~5.5M docs). This wave touches no Mongo, but the rule stands.
- **No new FIBO terms are expected.** Design §1.1 measured every term as already bound at Wave 8. This is verified at close (Task 16), not assumed.

---

## File Structure

| File | Responsibility |
|---|---|
| `generators/fred_series.py` | **Pure.** The explicit per-series direction map and normalisation. No I/O |
| `generators/fetch_fred_rates.py` | I/O driver: 21 FRED series + the derived EUR/GBP cross → one artifact |
| `generators/ticks.py` | **Pure.** Brownian bridge, tick calendar, 90-minute rolling move. No I/O |
| `generators/generate_treasury.py` | Clients, deposits, positions, limits, mandates |
| `generators/generate_ticks.py` | I/O driver: reads `benchmark_curve`, writes the tick artifact |
| `generators/part43.py` | **Pure.** G10 filter, pair normalisation, profile derivation. No I/O |
| `generators/fetch_part43.py` | I/O driver: 10 DTCC zips → derived profile artifact |
| `generators/generate_fx_trades.py` | Trades, system records, clock offsets, amendment chains |
| `generators/narrative_wave12.py` | **Pure.** The four engineered conditions' constants and construction |
| `loaders/load_rates_wave12.py` | `reference_rate`, `fx_reference_rate` |
| `loaders/load_postgres_wave12_treasury.py` | 6 treasury tables + `deposit_account` extension |
| `loaders/load_fluree_wave12_treasury.py` | `heldAt`, `concentratedIn`, posture overlay |
| `loaders/load_postgres_wave12_fx.py` | 5 FX tables |
| `loaders/load_fluree_wave12_fx.py` | `observedIn`, `amends`, offsets, timing breaks |
| `validators/intraday.py` | **New gate.** Recomputes the treasury conditions from loaded ticks |
| `validators/reconcile.py` | **New gate.** Recomputes break classification twice, asserts the inversion |
| `validators/conditions.py` | **modify** — append both §F row-count check sets |
| `validators/partition.py` | **modify** — new tables/assertions live only where they should |
| `validators/test_ticks.py` | Pure tests: bridge determinism, anchor fidelity, spacing, rolling move |
| `validators/test_part43.py` | Pure tests: G10 filter, pair normalisation, profile derivation |
| `validators/test_fred_series.py` | Pure tests: the reciprocal-direction trap |
| `docs/ccf_dataprep_v2.md` | **modify** — entity tables, counts, the two-writer fact, pair convention |
| `docs/known-issues.md` | **modify** — Wave 12 defect record, §12 |

**Why the pure/I-O split.** `fred_series.py`, `ticks.py`, `part43.py`, and `narrative_wave12.py` hold no network or database access so they are unit-testable without either. This mirrors `generators/curves.py` (pure) beside `generators/fetch_treasury.py` (I/O), which is what let `test_curves.py` pin the two-date-format trap, and `warn_match.py` beside `fetch_warn.py` in Wave 11b.

**Why the validators do NOT import `narrative_wave12.py`'s computations.** `validators/reconcile.py` and `validators/intraday.py` must recompute independently from loaded rows. They may read *which* trade is the designed inversion case, but they implement their own clock-alignment and rolling-move arithmetic. A validator that imports the generator's arithmetic tests that the generator agrees with itself, which is the failure Wave 11a's `series.py` was written to avoid.

---

## Task 1: The FRED direction map, and the reciprocal trap

FRED's FX conventions are inconsistent by design: `DEXUSEU` is USD-per-EUR, `DEXJPUS` is JPY-per-USD. An inferred map is right for some series and silently inverted for others, producing revaluations wrong by a reciprocal — large, plausible, and not obviously wrong at a glance. Design §7.4.

**Files:**
- Create: `generators/fred_series.py`
- Test: `validators/test_fred_series.py`

**Interfaces:**
- Produces: `SERIES: dict[str, SeriesSpec]`; `normalise_fx(series_id: str, value: float) -> tuple[str, float]` returning `(pair, rate)` in market convention where `rate` is units of the quote currency per one unit of the base.

- [ ] **Step 1: Write the failing test**

```python
# validators/test_fred_series.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from generators.fred_series import (
    SERIES, RATE_SERIES, FX_SERIES, DERIVED_CROSSES, normalise_fx, derive_cross,
)


def test_every_fx_series_has_an_explicit_direction():
    """No series may fall back to an inferred direction."""
    for sid in FX_SERIES:
        spec = SERIES[sid]
        assert spec.base and spec.quote, f"{sid} has no explicit base/quote"
        assert spec.invert in (True, False), f"{sid} direction not explicit"


def test_usd_per_eur_is_not_inverted():
    """DEXUSEU is USD per EUR -- already market convention EUR/USD."""
    pair, rate = normalise_fx("DEXUSEU", 1.1581)
    assert pair == "EUR/USD"
    assert abs(rate - 1.1581) < 1e-9


def test_jpy_per_usd_is_not_inverted_either():
    """DEXJPUS is JPY per USD, and USD/JPY IS the market convention."""
    pair, rate = normalise_fx("DEXJPUS", 159.21)
    assert pair == "USD/JPY"
    assert abs(rate - 159.21) < 1e-9


def test_cad_per_usd_is_not_inverted():
    pair, rate = normalise_fx("DEXCAUS", 1.3872)
    assert pair == "USD/CAD"
    assert abs(rate - 1.3872) < 1e-9


def test_usd_per_aud_is_market_convention_aud_usd():
    pair, rate = normalise_fx("DEXUSAL", 0.7091)
    assert pair == "AUD/USD"
    assert abs(rate - 0.7091) < 1e-9


def test_the_reciprocal_trap_is_caught_by_magnitude():
    """A wrongly-inverted USD/JPY would be ~0.0063, not ~159.

    This is the failure §7.4 names: plausible-looking, wrong by a reciprocal.
    """
    _, rate = normalise_fx("DEXJPUS", 159.21)
    assert rate > 1.0, "USD/JPY inverted -- the reciprocal trap fired"


def test_rate_series_are_percent_not_fraction():
    for sid in RATE_SERIES:
        assert SERIES[sid].unit == "percent"


def test_the_series_count_is_what_it_claims():
    """The docstring said 19 when the dicts held 22. Count, do not trust prose."""
    assert len(RATE_SERIES) == 16, f"{len(RATE_SERIES)} rate series"
    assert len(FX_SERIES) == 5, f"{len(FX_SERIES)} fx series"
    assert len(SERIES) == 21


def test_the_five_fetched_pairs_plus_the_derived_one_cover_the_six():
    """RULING F7: EUR/GBP has no FRED series and must be derived."""
    fetched = {normalise_fx(s, 1.0)[0] for s in FX_SERIES}
    assert fetched == {"EUR/USD", "USD/JPY", "GBP/USD", "USD/CAD", "AUD/USD"}
    assert set(DERIVED_CROSSES) == {"EUR/GBP"}
    assert fetched | set(DERIVED_CROSSES) == {
        "EUR/USD", "USD/JPY", "AUD/USD", "USD/CAD", "GBP/USD", "EUR/GBP"}


def test_no_series_is_fetched_that_nothing_consumes():
    """USD/CHF was fetched by an earlier draft and consumed by nothing."""
    assert "DEXSZUS" not in SERIES, "USD/CHF is not one of the six pairs"


def test_eur_gbp_cross_has_the_right_magnitude():
    """Observed 2026-08-21: DEXUSEU 1.1581, DEXUSUK 1.3556 -> ~0.854."""
    got = derive_cross(1.1581, 1.3556)
    assert 0.80 < got < 0.90, f"EUR/GBP = {got}, expected ~0.85"


def test_cross_rejects_a_zero_quote_leg():
    try:
        derive_cross(1.1581, 0.0)
    except ValueError:
        return
    raise AssertionError("a zero quote leg must raise, not return inf")


def test_pinned_values_for_every_fetched_fx_series():
    """Every FX series pinned, not four of six."""
    for sid, observed, expect_pair in [
        ("DEXUSEU", 1.1581, "EUR/USD"), ("DEXJPUS", 159.21, "USD/JPY"),
        ("DEXUSUK", 1.3556, "GBP/USD"), ("DEXCAUS", 1.3872, "USD/CAD"),
        ("DEXUSAL", 0.7091, "AUD/USD"),
    ]:
        pair, rate = normalise_fx(sid, observed)
        assert pair == expect_pair, f"{sid} -> {pair}"
        assert abs(rate - observed) < 1e-9


def test_the_invert_branch_is_exercised():
    """No current series needs inversion, so the reciprocal path would be
    dead code covered by nothing. Exercise it against a synthetic spec."""
    from generators.fred_series import SeriesSpec
    probe = SeriesSpec("PROBE", "fx", "ratio", "synthetic",
                       base="AAA", quote="BBB", invert=True)
    saved = SERIES.get("PROBE")
    SERIES["PROBE"] = probe
    try:
        pair, rate = normalise_fx("PROBE", 4.0)
        assert pair == "AAA/BBB"
        assert abs(rate - 0.25) < 1e-12, f"inversion gave {rate}, expected 0.25"
    finally:
        SERIES.pop("PROBE", None)
        if saved is not None:
            SERIES["PROBE"] = saved


if __name__ == "__main__":
    import traceback
    passed = failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn(); passed += 1; print(f"  PASS {name}")
            except Exception:
                failed += 1; print(f"  FAIL {name}"); traceback.print_exc()
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run validators/test_fred_series.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'generators.fred_series'`

- [ ] **Step 3: Write minimal implementation**

```python
# generators/fred_series.py
"""The twenty-one FRED series this wave loads, with EXPLICIT directions.

`known-issues.md` §9.6 is the precedent: the Treasury CSV header must be read
per file rather than inferred once. FRED's FX conventions carry the same trap
in a nastier form -- `DEXUSEU` is USD-per-EUR while `DEXJPUS` is JPY-per-USD,
so any rule inferred from one series is wrong for the other, and the error is
a reciprocal rather than a crash.

Every direction below is stated, never derived. `test_fred_series.py` pins
each one against a value observed on 2026-08-21.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SeriesSpec:
    series_id: str
    kind: str            # "rate" | "fx"
    unit: str            # "percent" | "ratio"
    label: str
    base: str = ""       # fx only -- market-convention base currency
    quote: str = ""      # fx only -- market-convention quote currency
    invert: bool | None = None   # fx only -- invert FRED's value to reach base/quote


#: Overnight reference rate and its published intraday percentiles.
_SOFR = {
    "SOFR":   "Secured Overnight Financing Rate",
    "SOFR1":  "SOFR 1st percentile",
    "SOFR25": "SOFR 25th percentile",
    "SOFR75": "SOFR 75th percentile",
    "SOFR99": "SOFR 99th percentile",
}

#: Constant-maturity Treasury tenors, matching `benchmark_curve`'s coverage.
_DGS = {
    "DGS1MO": 1 / 12, "DGS3MO": 0.25, "DGS6MO": 0.5, "DGS1": 1.0,
    "DGS2": 2.0, "DGS3": 3.0, "DGS5": 5.0, "DGS7": 7.0,
    "DGS10": 10.0, "DGS20": 20.0, "DGS30": 30.0,
}

#: FX. `invert` says whether FRED's published value must be reciprocated to
#: reach the market-convention BASE/QUOTE quote. Stated per series, never
#: inferred from the ticker's letters -- `DEXUSEU` and `DEXUSUK` look alike
#: and `DEXUSAL` looks like them too, but all three are USD-per-foreign,
#: which happens to already BE market convention for EUR, GBP, and AUD.
_FX = [
    ("DEXUSEU", "EUR", "USD", False, "US Dollars per Euro"),
    ("DEXJPUS", "USD", "JPY", False, "Japanese Yen per US Dollar"),
    ("DEXUSUK", "GBP", "USD", False, "US Dollars per Pound Sterling"),
    ("DEXCAUS", "USD", "CAD", False, "Canadian Dollars per US Dollar"),
    ("DEXUSAL", "AUD", "USD", False, "US Dollars per Australian Dollar"),
]

#: RULING F7 -- EUR/GBP is one of the six pairs this wave trades, and FRED has
#: NO series for it (`DEXEUUK` returns "series does not exist"). It is derived
#: as a cross of two fetched series. Provenance stays `public` because both
#: legs are public H.10, but the derivation is recorded so nobody mistakes a
#: quotient for an observation.
DERIVED_CROSSES = {
    "EUR/GBP": ("DEXUSEU", "DEXUSUK"),   # (USD per EUR) / (USD per GBP)
}

SERIES: dict[str, SeriesSpec] = {}

for _sid, _label in _SOFR.items():
    SERIES[_sid] = SeriesSpec(_sid, "rate", "percent", _label)

for _sid, _yrs in _DGS.items():
    SERIES[_sid] = SeriesSpec(_sid, "rate", "percent",
                              f"Treasury constant maturity {_yrs:g}y")

for _sid, _b, _q, _inv, _label in _FX:
    SERIES[_sid] = SeriesSpec(_sid, "fx", "ratio", _label,
                              base=_b, quote=_q, invert=_inv)

RATE_SERIES = tuple(s for s, spec in SERIES.items() if spec.kind == "rate")
FX_SERIES = tuple(s for s, spec in SERIES.items() if spec.kind == "fx")

#: Tenor in years for the DGS series, for joining against `benchmark_curve`.
DGS_TENOR_YEARS = dict(_DGS)


def normalise_fx(series_id: str, value: float) -> tuple[str, float]:
    """Return `(pair, rate)` in market convention.

    `rate` is units of the QUOTE currency per one unit of the BASE currency,
    which is what "EUR/USD = 1.1581" means to a trader.
    """
    spec = SERIES[series_id]
    if spec.kind != "fx":
        raise ValueError(f"{series_id} is not an FX series")
    rate = (1.0 / value) if spec.invert else value
    return f"{spec.base}/{spec.quote}", rate


def derive_cross(usd_per_base: float, usd_per_quote: float) -> float:
    """QUOTE units per one BASE unit, from two USD-denominated legs.

    EUR/GBP = (USD per EUR) / (USD per GBP). A quotient, not an inversion --
    a different operation from `normalise_fx`, which is why it is a separate
    function rather than another flag on SeriesSpec.
    """
    if usd_per_quote == 0:
        raise ValueError("quote leg is zero")
    return usd_per_base / usd_per_quote
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run validators/test_fred_series.py`
Expected: `14 passed, 0 failed`

- [ ] **Step 5: Commit**

```bash
git add generators/fred_series.py validators/test_fred_series.py
git commit -m "Wave 12 Task 1: explicit FRED direction map, pinned against the reciprocal trap"
```

---

## Task 2: Fetch the twenty-one FRED series

**Files:**
- Create: `generators/fetch_fred_rates.py`
- Writes: `sources/screening/wave12_rates.json`

**Interfaces:**
- Consumes: `generators.fred_series.SERIES`, `RATE_SERIES`, `FX_SERIES`, `normalise_fx`
- Produces: artifact `wave12_rates.json` with keys `rates: list[{series_id, obs_date, value, unit}]`, `fx: list[{pair, obs_date, rate, series_id}]`, `_inputs`, `_meta: {retrieved_at, observation_start}`

- [ ] **Step 1: Write the fetcher**

```python
# generators/fetch_fred_rates.py
"""Fetch the twenty-one FRED series backing both Wave 12 products.

Design §1.4 measured them live on 2026-08-21. The span matches
`benchmark_curve` (2024-01-02 onward) so the three rate tables share one
calendar rather than three.

FRED returns "." for a non-publication day (holiday, weekend). Those rows are
DROPPED, not carried forward -- a forward-filled rate is an invented
observation wearing a public provenance label.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ccf.currency import record_inputs                       # noqa: E402
from generators.fred_series import (                          # noqa: E402
    DERIVED_CROSSES, FX_SERIES, RATE_SERIES, SERIES,
    derive_cross, normalise_fx,
)

FRED_URL = "https://api.stlouisfed.org/fred/series/observations"
OBSERVATION_START = "2024-01-02"
OUT = Path(__file__).resolve().parent.parent / "sources" / "screening" / "wave12_rates.json"


def fetch_series(series_id: str, api_key: str) -> list[tuple[str, float]]:
    """Return [(obs_date, value)] with non-publication days dropped."""
    resp = requests.get(FRED_URL, timeout=30, params={
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "observation_start": OBSERVATION_START,
    })
    resp.raise_for_status()
    body = resp.json()
    if "observations" not in body:
        raise RuntimeError(f"{series_id}: no observations key -- {body!r:.200}")
    out = []
    for o in body["observations"]:
        v = o["value"]
        if v == ".":            # FRED's non-publication marker
            continue
        out.append((o["date"], float(v)))
    if not out:
        raise RuntimeError(f"{series_id}: zero usable observations")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        print("FRED_API_KEY not set", file=sys.stderr)
        return 2

    retrieved_at = datetime.now(timezone.utc).isoformat()
    rates, fx = [], []

    for sid in RATE_SERIES:
        obs = fetch_series(sid, api_key)
        for d, v in obs:
            rates.append({"series_id": sid, "obs_date": d, "value": v,
                          "unit": SERIES[sid].unit})
        print(f"  {sid:8s} {len(obs):5d} obs")
        time.sleep(0.4)

    by_series: dict[str, dict[str, float]] = {}
    for sid in FX_SERIES:
        obs = fetch_series(sid, api_key)
        by_series[sid] = dict(obs)
        for d, v in obs:
            pair, rate = normalise_fx(sid, v)
            fx.append({"pair": pair, "obs_date": d, "rate": rate,
                       "series_id": sid, "derivation": ""})
        print(f"  {sid:8s} {len(obs):5d} obs -> {normalise_fx(sid, obs[0][1])[0]}")
        time.sleep(0.4)

    # RULING F7 -- EUR/GBP is one of the six pairs and FRED does not publish it
    # (`DEXEUUK` does not exist). Derive it as a cross of two fetched legs,
    # on the dates where BOTH legs published. An inner join, never a
    # forward-fill: a cross built from one stale leg is a made-up rate.
    for pair, (base_sid, quote_sid) in DERIVED_CROSSES.items():
        base_obs, quote_obs = by_series[base_sid], by_series[quote_sid]
        shared = sorted(set(base_obs) & set(quote_obs))
        for d in shared:
            fx.append({
                "pair": pair, "obs_date": d,
                "rate": derive_cross(base_obs[d], quote_obs[d]),
                "series_id": f"{base_sid}/{quote_sid}",
                "derivation": f"({base_sid}) / ({quote_sid})",
            })
        dropped = len(set(base_obs) ^ set(quote_obs))
        print(f"  {pair:8s} {len(shared):5d} obs -> DERIVED "
              f"({dropped} dates dropped, only one leg published)")
        if not shared:
            raise RuntimeError(f"{pair}: the two legs share no dates")

    artifact = {
        "_meta": {"retrieved_at": retrieved_at,
                  "observation_start": OBSERVATION_START,
                  "source": "FRED (Federal Reserve Bank of St. Louis)"},
        "_inputs": record_inputs(),
        "rates": rates,
        "fx": fx,
    }
    print(f"\n  {len(rates)} rate observations, {len(fx)} fx observations")
    if args.dry_run:
        print("  --dry-run: not written")
        return 0
    OUT.write_text(json.dumps(artifact, indent=1))
    print(f"  wrote {OUT.relative_to(Path.cwd())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Dry-run it**

Run: `uv run generators/fetch_fred_rates.py --dry-run`
Expected: 21 series each reporting a non-zero observation count; the five FX lines print their normalised pair (`EUR/USD`, `USD/JPY`, `GBP/USD`, `USD/CAD`, `AUD/USD`), then a sixth line for the **derived** `EUR/GBP` cross. Roughly 12,000 rate and 4,000 fx observations.

- [ ] **Step 3: Run it for real**

Run: `uv run generators/fetch_fred_rates.py`
Expected: writes `sources/screening/wave12_rates.json`

- [ ] **Step 4: Verify the reciprocal trap did not fire in real data**

Run:
```bash
uv run python -c "
import json
a=json.load(open('sources/screening/wave12_rates.json'))
import collections
m=collections.defaultdict(list)
for r in a['fx']: m[r['pair']].append(r['rate'])
for p,v in sorted(m.items()):
    print(f'{p:9s} n={len(v):4d} median={sorted(v)[len(v)//2]:.4f}')
"
```
Expected: `USD/JPY` median ~150–160 (NOT ~0.006); `EUR/USD` ~1.0–1.2; `GBP/USD` ~1.2–1.4; `USD/CAD` ~1.3–1.4; `AUD/USD` ~0.6–0.7; `EUR/GBP` ~0.84–0.88. A median on the wrong side of 1.0 for any pair means an inverted series. All **six** pairs must appear — a missing `EUR/GBP` means the derived cross was skipped.

- [ ] **Step 5: Commit**

```bash
git add generators/fetch_fred_rates.py sources/screening/wave12_rates.json
git commit -m "Wave 12 Task 2: fetch 21 FRED series + the derived EUR/GBP cross, non-publication days dropped not filled"
```

---

## Task 3: The tick engine — pure, deterministic, anchored

This is the module the 8bp condition rests on. Design §3.1.

**Files:**
- Create: `generators/ticks.py`
- Test: `validators/test_ticks.py`

**Interfaces:**
- Produces:
  - `SESSION_TICKS = 78` (6.5 hours at 5-minute granularity)
  - `session_times(day: date) -> list[datetime]` — 78 UTC timestamps, 13:30→19:55
  - `brownian_bridge(open_v: float, close_v: float, n: int, seed: int) -> list[float]` — length `n`, `[0] == open_v`, `[-1] == close_v`
  - `max_rolling_move_bp(values: list[float], window_ticks: int) -> float`
  - `ROLLING_WINDOW_TICKS = 18` (90 minutes)

- [ ] **Step 1: Write the failing test**

```python
# validators/test_ticks.py
import sys
from datetime import date, timedelta
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from generators.ticks import (
    SESSION_TICKS, ROLLING_WINDOW_TICKS,
    session_times, brownian_bridge, max_rolling_move_bp,
)


def test_session_is_78_ticks_five_minutes_apart():
    ts = session_times(date(2026, 5, 11))
    assert len(ts) == SESSION_TICKS == 78
    gaps = {(ts[i] - ts[i - 1]).total_seconds() for i in range(1, len(ts))}
    assert gaps == {300.0}, f"non-uniform spacing: {gaps}"


def test_bridge_hits_both_anchors_exactly():
    """The anchor fidelity property. If this breaks, the series is fiction."""
    v = brownian_bridge(4.1000, 4.1500, SESSION_TICKS, seed=7)
    assert len(v) == SESSION_TICKS
    assert v[0] == 4.1000
    assert v[-1] == 4.1500


def test_bridge_is_deterministic_for_a_seed():
    a = brownian_bridge(4.10, 4.15, SESSION_TICKS, seed=7)
    b = brownian_bridge(4.10, 4.15, SESSION_TICKS, seed=7)
    assert a == b, "reload would not reproduce the series"


def test_different_seeds_give_different_paths_but_same_anchors():
    a = brownian_bridge(4.10, 4.15, SESSION_TICKS, seed=7)
    b = brownian_bridge(4.10, 4.15, SESSION_TICKS, seed=8)
    assert a != b
    assert a[0] == b[0] and a[-1] == b[-1]


def test_flat_day_still_anchors():
    v = brownian_bridge(4.10, 4.10, SESSION_TICKS, seed=1)
    assert v[0] == 4.10 and v[-1] == 4.10


def test_rolling_move_on_a_monotone_ramp():
    """A ramp of 1bp per tick moves exactly window_ticks bp per window.

    UNITS, because this is where the first attempt went wrong: values are
    par yield in PERCENT (4.15 == 4.15%), so one basis point is 0.01, NOT
    0.0001. A ramp of 0.0001/tick is 0.01bp/tick and would move 0.18bp per
    90-minute window, not 18bp.
    """
    vals = [4.0 + i * 0.01 for i in range(SESSION_TICKS)]
    got = max_rolling_move_bp(vals, ROLLING_WINDOW_TICKS)
    assert abs(got - ROLLING_WINDOW_TICKS) < 1e-6


def test_rolling_move_is_absolute():
    """A falling market moves too. A signed max would report ~0 here."""
    vals = [4.0 - i * 0.01 for i in range(SESSION_TICKS)]
    got = max_rolling_move_bp(vals, ROLLING_WINDOW_TICKS)
    assert abs(got - ROLLING_WINDOW_TICKS) < 1e-6


def test_a_real_eight_bp_move_reports_eight():
    """Anchor the units to REAL par-yield magnitudes, not a synthetic ramp.

    The 2y par yield moved 4.10 -> 4.18 on real days in the loaded curve.
    That is 8 basis points. A multiplier that is wrong by 100x still passes
    a ramp test tuned to it -- but not this one, because 4.10 and 4.18 are
    numbers the domain fixes, not the test.
    """
    vals = [4.10] * 30 + [4.18] * 48
    got = max_rolling_move_bp(vals, ROLLING_WINDOW_TICKS)
    assert abs(got - 8.0) < 1e-6, f"a real 8bp move reported {got}bp"


def test_one_basis_point_is_zero_point_zero_one():
    """The unit conversion, stated as its own assertion."""
    assert abs(max_rolling_move_bp([4.00, 4.01], 1) - 1.0) < 1e-9


def test_ninety_minute_window_is_eighteen_ticks():
    assert ROLLING_WINDOW_TICKS == 18
    assert ROLLING_WINDOW_TICKS * 5 == 90


def test_full_session_move_is_at_least_the_endpoint_gap():
    """Anchor fidelity restated as a property, over many seeds.

    Named for what it asserts. It does NOT prove a 90-minute window carries
    8bp -- that is a claim about the PATH, and only `validators/intraday.py`
    recomputing from loaded ticks can establish it. This test pins the
    weaker, exact property: the endpoints never drift, whatever the seed.
    """
    for seed in range(50):
        v = brownian_bridge(4.1000, 4.1800, SESSION_TICKS, seed=seed)
        full = abs(v[-1] - v[0]) * 100
        assert full >= 8.0 - 1e-9, f"seed {seed}: endpoints drifted"


if __name__ == "__main__":
    import traceback
    passed = failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn(); passed += 1; print(f"  PASS {name}")
            except Exception:
                failed += 1; print(f"  FAIL {name}"); traceback.print_exc()
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run validators/test_ticks.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'generators.ticks'`

- [ ] **Step 3: Write minimal implementation**

```python
# generators/ticks.py
"""Interpolate a 5-minute intraday path between two REAL published closes.

Design §3.1. The two endpoints are read unmodified from `benchmark_curve`, so
the day-over-day move is real and only the within-day path is engineered.
That split is the whole provenance claim, and `anchor fidelity` -- first and
last tick equal the published values exactly -- is what keeps it true. A
bridge that merely starts and ends "close to" the anchors has quietly become
fiction.

Determinism matters as much: reloads must reproduce the series, so the path
is a function of (open, close, n, seed) with no ambient randomness.
"""

from __future__ import annotations

import random
from datetime import date, datetime, time, timedelta, timezone

#: A 6.5-hour session at 5-minute granularity.
SESSION_TICKS = 78

#: 90 minutes, the interval the spec's Latency Poisoned counterfactual names.
ROLLING_WINDOW_TICKS = 18

#: US cash-market session in UTC (09:30-16:00 ET, standard offset).
SESSION_OPEN_UTC = time(13, 30)


def session_times(day: date) -> list[datetime]:
    """78 UTC timestamps, 5 minutes apart, starting 13:30Z."""
    start = datetime.combine(day, SESSION_OPEN_UTC, tzinfo=timezone.utc)
    return [start + timedelta(minutes=5 * i) for i in range(SESSION_TICKS)]


def brownian_bridge(open_v: float, close_v: float, n: int,
                    seed: int) -> list[float]:
    """A Brownian bridge from `open_v` to `close_v` in `n` points.

    Both endpoints are returned EXACTLY -- the bridge correction is applied
    in full, and the endpoints are then reassigned rather than left to
    floating-point drift.
    """
    if n < 2:
        raise ValueError("need at least two ticks")

    rng = random.Random(seed)

    # Scale increments to the endpoint gap so a volatile day looks volatile
    # and a quiet day does not. A floor keeps a flat day from being a
    # straight line, which no real session is.
    gap = abs(close_v - open_v)
    step_sd = max(gap / (n ** 0.5), 0.0004)   # >= 0.04bp per tick

    walk = [0.0]
    for _ in range(n - 1):
        walk.append(walk[-1] + rng.gauss(0.0, step_sd))

    # Bridge correction: subtract the linear drift of the raw walk, then add
    # the linear path from open to close.
    drift = walk[-1]
    out = []
    for i, w in enumerate(walk):
        frac = i / (n - 1)
        bridged = w - drift * frac
        out.append(open_v + (close_v - open_v) * frac + bridged)

    # Exact anchors. Do not rely on the arithmetic above landing on them.
    out[0] = open_v
    out[-1] = close_v
    return out


def max_rolling_move_bp(values: list[float], window_ticks: int) -> float:
    """Largest ABSOLUTE move, in basis points, over any window of that width.

    Absolute, because a market that falls 8bp has moved 8bp. A signed max
    would report ~0 for a falling session and silently fail the condition.
    Inputs are percent (4.15 == 4.15%), so one basis point is 0.01.
    """
    if len(values) <= window_ticks:
        return abs(values[-1] - values[0]) * 100 if values else 0.0
    best = 0.0
    for i in range(len(values) - window_ticks):
        move = abs(values[i + window_ticks] - values[i]) * 100
        if move > best:
            best = move
    return best

# UNITS -- do not "fix" the 100 above to satisfy a failing test. Inputs are
# par yield in PERCENT: 4.15 means 4.15%, and one basis point is 0.01. So
# percent-difference x 100 = basis points, and a real 4.10 -> 4.18 move
# reports 8.0. A multiplier of 10000 makes that same move report 800, which
# passes every threshold check in the estate and makes the product's headline
# condition meaningless while showing green.
```

**Do not retune `step_sd` without re-measuring.** Its scaling and its 0.0004
floor were simulated over 2,000 seeds per gap size before this task was
written, and they produce realistic dispersion:

```
gap  8bp -> intraday range 12.2bp median (p90 15.5)   P(max 90-min move >= 8bp) = 47.1%
gap 12bp ->                                            P = 94.5%
gap 15bp ->                                            P = 99.8%
quiet 1bp -> intraday range  1.5bp median
```

Real 2-year Treasury ranges 8–14bp on a day that closes 8bp from the prior
close, so this is in the right neighbourhood. The 47% figure is why design
§1.3 chose a window with seven qualifying days rather than one: a single day
sitting exactly on 8.0bp satisfies §F as a coin flip. Changing `step_sd`
changes that probability, silently, in a place no test would catch — so if you
change it, re-run the simulation and update these numbers.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run validators/test_ticks.py`
Expected: `11 passed, 0 failed`

- [ ] **Step 5: Commit**

```bash
git add generators/ticks.py validators/test_ticks.py
git commit -m "Wave 12 Task 3: deterministic anchored tick engine, exact endpoints"
```

---

## Task 4: Generate the tick series over the real window

**Files:**
- Create: `generators/generate_ticks.py`
- Writes: `sources/screening/wave12_ticks.json`

**Interfaces:**
- Consumes: `benchmark_curve` (read-only), `generators.ticks`
- Produces: artifact with `ticks: list[{tenor_years, obs_ts, value_pct, trading_day, provenance}]`, `window: {start, end, trading_days}`, `eight_bp_days: list[str]`

**Constraint:** the window is **2026-05-11 → 2026-06-23** and the tenors are the five the product quotes: 0.25, 1, 2, 5, 10.

- [ ] **Step 1: Write the generator**

```python
# generators/generate_ticks.py
"""Build the intraday tick series from REAL published daily closes.

Design §1.3 selected the window 2026-05-11 -> 2026-06-23 (30 trading days)
because it carries SEVEN real >=8bp day-over-day moves at the 2y tenor, where
the most recent windows carry exactly one sitting on the 8.0bp threshold.
Wave 11b's D1 is the precedent for choosing margin over recency.

Each day's path opens at the PRIOR session's published close and terminates
at that day's published close. Both are read from `benchmark_curve` and never
modified, so the day-over-day move is real; only the within-day path is
engineered, and every row says so.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ccf.config import pg_connect, PG_SCHEMA_V2                # noqa: E402
from ccf.currency import record_inputs                          # noqa: E402
from generators.ticks import (                                  # noqa: E402
    ROLLING_WINDOW_TICKS, SESSION_TICKS,
    brownian_bridge, max_rolling_move_bp, session_times,
)

WINDOW_START = date(2026, 5, 11)
WINDOW_END = date(2026, 6, 23)
TENORS = (0.25, 1.0, 2.0, 5.0, 10.0)
PROVENANCE = "synthetic — engineered"
OUT = Path(__file__).resolve().parent.parent / "sources" / "screening" / "wave12_ticks.json"


def load_closes(tenor: float) -> list[tuple[date, float]]:
    """Published closes for one tenor, one day BEFORE the window onward.

    The extra leading day supplies the first session's opening anchor.
    """
    with pg_connect() as conn:
        cur = conn.cursor()
        cur.execute(
            f'''SELECT curve_date, par_yield_pct
                  FROM "{PG_SCHEMA_V2}".benchmark_curve
                 WHERE tenor_years = %s AND curve_date <= %s
                 ORDER BY curve_date''',
            (tenor, WINDOW_END))
        rows = cur.fetchall()
    # Keep the window plus exactly one prior trading day.
    inside = [r for r in rows if WINDOW_START <= r[0] <= WINDOW_END]
    before = [r for r in rows if r[0] < WINDOW_START]
    if not before:
        raise RuntimeError(f"tenor {tenor}: no prior close to open against")
    return [before[-1], *inside]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    ticks, eight_bp_days, day_count = [], set(), None

    for tenor in TENORS:
        closes = load_closes(tenor)
        sessions = closes[1:]           # the window itself
        if day_count is None:
            day_count = len(sessions)
        elif day_count != len(sessions):
            raise RuntimeError(
                f"tenor {tenor} has {len(sessions)} sessions, expected {day_count} "
                "-- the curve is not rectangular over this window")

        for i, (day, close_v) in enumerate(sessions):
            open_v = closes[i][1]       # prior session's published close
            # Seed from the day and tenor so a reload reproduces exactly.
            seed = int(day.strftime("%Y%m%d")) * 1000 + int(tenor * 100)
            path = brownian_bridge(open_v, close_v, SESSION_TICKS, seed)
            stamps = session_times(day)

            move = max_rolling_move_bp(path, ROLLING_WINDOW_TICKS)
            if move >= 8.0:
                eight_bp_days.add(day.isoformat())

            for ts, v in zip(stamps, path, strict=True):
                ticks.append({
                    "tenor_years": tenor,
                    "trading_day": day.isoformat(),
                    "obs_ts": ts.isoformat(),
                    "value_pct": round(v, 6),
                    "provenance": PROVENANCE,
                })

    artifact = {
        "_meta": {
            "window_start": WINDOW_START.isoformat(),
            "window_end": WINDOW_END.isoformat(),
            "trading_days": day_count,
            "tenors": list(TENORS),
            "session_ticks": SESSION_TICKS,
            "anchor_source": "ccf_v2.benchmark_curve (Treasury.gov, public)",
            "note": ("Endpoints are real published closes; only the within-day "
                     "path is engineered."),
        },
        "_inputs": record_inputs(),
        "eight_bp_days": sorted(eight_bp_days),
        "ticks": ticks,
    }

    print(f"  {len(ticks)} ticks over {day_count} sessions x {len(TENORS)} tenors")
    print(f"  days carrying a >=8bp 90-minute move: {len(eight_bp_days)}")
    for d in sorted(eight_bp_days):
        print(f"    {d}")
    if not eight_bp_days:
        print("  FAIL: no day carries the 8bp condition", file=sys.stderr)
        return 1
    if args.dry_run:
        print("  --dry-run: not written")
        return 0
    OUT.write_text(json.dumps(artifact, indent=1))
    print(f"  wrote {OUT.relative_to(Path.cwd())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Dry-run and read the 8bp report**

Run: `uv run generators/generate_ticks.py --dry-run`
Expected: `11,700 ticks over 30 sessions x 5 tenors` and **at least one** day listed under the 8bp report. Design §1.3 predicts the 2y tenor alone contributes 7 candidate days, so a count of 0 means the bridge or the window is wrong, not that the market was quiet.

- [ ] **Step 3: Run it for real**

Run: `uv run generators/generate_ticks.py`
Expected: writes `sources/screening/wave12_ticks.json`

- [ ] **Step 4: Verify anchors against the source table directly**

Run:
```bash
uv run python -c "
import json, sys
sys.path.insert(0,'.')
from ccf.config import pg_connect, PG_SCHEMA_V2
a=json.load(open('sources/screening/wave12_ticks.json'))
by={}
for t in a['ticks']: by.setdefault((t['tenor_years'],t['trading_day']),[]).append(t)
with pg_connect() as c:
    cur=c.cursor()
    bad=0
    for (ten,day),rows in sorted(by.items()):
        rows.sort(key=lambda r:r['obs_ts'])
        cur.execute(f'select par_yield_pct from \"{PG_SCHEMA_V2}\".benchmark_curve where tenor_years=%s and curve_date=%s',(ten,day))
        pub=float(cur.fetchone()[0])
        if abs(rows[-1]['value_pct']-pub)>1e-6:
            bad+=1; print('MISMATCH',ten,day,rows[-1]['value_pct'],pub)
        assert len(rows)==78, (ten,day,len(rows))
print('closing-tick mismatches:',bad)
"
```
Expected: `closing-tick mismatches: 0`, no assertion error. This is the anchor-fidelity property checked against the database rather than the artifact.

- [ ] **Step 5: Commit**

```bash
git add generators/generate_ticks.py sources/screening/wave12_ticks.json
git commit -m "Wave 12 Task 4: interpolate 11,700 ticks between real published closes"
```

---

## Task 5: Treasury clients, deposits, positions, limits, mandates

**Files:**
- Create: `generators/generate_treasury.py`
- Writes: `sources/screening/wave12_treasury.json`

**Interfaces:**
- Consumes: `legal_entity`, `deposit_account`, `financial_fact` (read-only)
- Produces: artifact with `clients`, `deposit_accounts` (the ~100 new ones), `positions`, `limits`, `mandates`, `stale_signal`

**Constraints:**
- The client set is **defined, not selected**: the 15 anchors that already hold a deposit account (design §1.2). Assert 15; do not sample.
- `deposit_account` rows use `account_id` prefix `W12-` so the Wave 9 rows (20) are never touched.
- Limits and positions are generated **independently**; the concentration breach is then confirmed by computation, never arranged by setting a limit after the fact (design §3.2).

- [ ] **Step 1: Write the generator**

Key structure — the breach must emerge, not be assigned:

```python
# generators/generate_treasury.py  (core logic; full file follows this shape)
"""Treasury clients, deposits, positions, limits, mandates, and the stale signal.

Design §1.2: the client set is the 15 anchors that ALREADY hold deposit
accounts from Wave 9. Not sampled -- defined. That makes the spec's stated
prerequisite (`collateral-and-setoff-coverage`) genuinely load-bearing.

Design §3.2: limits and positions are generated INDEPENDENTLY. The
concentration breach is then measured. A limit tuned after the fact to make
a breach true would satisfy §F while proving nothing, because the "naively
optimal allocation" would no longer be naive -- it would be the allocation
the limit was drawn around.
"""

CURRENCIES = ("USD", "EUR", "GBP", "JPY")
INSTRUMENT_KINDS = ("money-market-fund", "commercial-paper", "treasury-bill")
STALE_MINUTES = 45          # comfortably past the 15-minute max_staleness bound


def naive_optimal_allocation(client_cash: float, permitted: list[dict],
                             positions: list[dict]) -> dict[str, float]:
    """All available cash into the highest-yielding PERMITTED counterparty.

    This is the allocation the Policy Blind counterfactual describes: an
    agent optimises yield inside the entitlement envelope and never consults
    the concentration limit, because policy was not in the frame.
    """
    eligible = [p for p in positions
                if p["instrument_kind"] in {q["instrument_kind"] for q in permitted}]
    if not eligible:
        return {}
    best = max(eligible, key=lambda p: p["yield_bp"])
    existing = sum(p["notional"] for p in positions
                   if p["counterparty_lei"] == best["counterparty_lei"])
    total = sum(p["notional"] for p in positions) + client_cash
    return {best["counterparty_lei"]: (existing + client_cash) / total}


def breaches(alloc: dict[str, float], limits: list[dict]) -> list[str]:
    """Counterparties whose post-allocation share exceeds their limit."""
    cap = {l["counterparty_lei"]: l["limit_pct"] / 100.0 for l in limits}
    return [lei for lei, share in alloc.items()
            if lei in cap and share > cap[lei]]
```

Generate:
- **clients** — 15, from the deposit-holding anchors, each with `mandate_id`, `home_currency`, and `reported_cash` taken from the most recent XBRL `CashAndCashEquivalentsAtCarryingValue` fact (provenance `public` on that column only).
- **deposit_accounts** — ~100 new, `W12-` prefixed, spread across the 4 currencies, `synthetic — internal`.
- **positions** — ~200 across the 3 instrument kinds, maturities laddered 1–365 days, each with `counterparty_lei` drawn from the anchor set, `yield_bp`, `notional`, `synthetic — internal`.
- **limits** — ~60, 4 per client, `limit_pct` drawn from a fixed band (15–35%), `synthetic — internal`.
- **mandates** — **one mandate per client**, naming its permitted instrument
  kinds. `permitted_instrument` is keyed (mandate_id, instrument_kind) and
  there are only three instrument kinds, so **45 rows is the ceiling**
  (15 clients × 3), not a target to reach.

  **Ruling F14.** This previously read "~75, 5 per client", which is
  arithmetically impossible: with three instrument kinds a mandate can carry at
  most three rows. The first implementation reached 75 by inventing a second
  `-PRV` mandate version per client — but `treasury_client.mandate_id` is
  singular, so nothing referenced them, and **30 of 75 rows were unreachable by
  any join**. That violates the definition of done's "every join the catalog
  implies actually joins". Generate one mandate per client and let the count be
  whatever three kinds allow.
- **stale_signal** — a small set of signals sharing one recorded decision
  reference `as_of`, of which **one** is `STALE_MINUTES` (45) behind it while
  the rest are ~1 minute behind, so the contrast is visible. Otherwise complete
  and well-formed (design §3.3), `synthetic — engineered`. **Ruling F5:** it
  loads into its own `stale_signal` table, never into `reference_rate` — that
  table's provenance column is `public` on every row.

  **Ruling F15 — staleness is measured against a recorded `as_of`, never
  against `now()`.** Every row carries the same `as_of`, and a signal's age is
  `as_of - observed_at`. The first implementation baked absolute wall-clock
  timestamps and left the validator comparing against `now()`, which means that
  fifteen minutes after generation *every* signal is stale, the fresh/stale
  contrast disappears, and the gate can never fail — it stops being a gate. It
  also matches the product's real semantics: the spec evaluates `max_staleness`
  against the decision time, and under replay `as_of` is a request parameter,
  not the wall clock.

**Ruling F1.** Each client carries the `intent` its concentration limits are keyed on, and `concentration_limit` rows are generated for that intent. `treasury_client` gains an `intent` column. Without it, `intraday.py`'s limit lookup returns one row per intent and picks arbitrarily, making the breach claim depend on row order.

- [ ] **Step 2: Dry-run and read the breach count**

Run: `uv run generators/generate_treasury.py --dry-run`
Expected: `15 clients`, `~100 new deposit accounts`, `~200 positions`, and a printed line `clients breaching under naive allocation: N`.

- [ ] **Step 3: If N < 2, widen the position concentration — never narrow the limit**

The §F floor is ≥2. If the measured count is below it, the correct adjustment is to increase how concentrated the *positions* are (more notional on the highest-yielding counterparty), not to lower `limit_pct` until the inequality flips. Design §3.2 is explicit: tuning the limit makes the breach an artifact of the limit rather than of the allocation.

Re-run Step 2 after adjusting. Record the final measured count.

- [ ] **Step 4: Run it for real**

Run: `uv run generators/generate_treasury.py`
Expected: writes `sources/screening/wave12_treasury.json` with `breaching_clients` ≥ 2 recorded in `_meta`.

- [ ] **Step 5: Commit**

```bash
git add generators/generate_treasury.py sources/screening/wave12_treasury.json
git commit -m "Wave 12 Task 5: treasury clients, positions, limits; breach measured not arranged"
```

---

## Task 6: Load the rate foundation into Postgres

**Files:**
- Create: `loaders/load_rates_wave12.py`

**Interfaces:**
- Consumes: `sources/screening/wave12_rates.json` via `ccf.currency.verify_current`
- Produces: tables `reference_rate`, `fx_reference_rate`

- [ ] **Step 1: Write the DDL and loader**

```sql
CREATE TABLE IF NOT EXISTS "ccf_v2".reference_rate (
    series_id    text        NOT NULL,
    obs_date     date        NOT NULL,
    value_pct    numeric     NOT NULL,
    unit         text        NOT NULL,
    label        text        NOT NULL,
    tenor_years  numeric,               -- NULL for SOFR and its percentiles
    provenance   text        NOT NULL,
    source       text        NOT NULL,
    retrieved_at timestamptz NOT NULL,
    PRIMARY KEY (series_id, obs_date)
);

CREATE TABLE IF NOT EXISTS "ccf_v2".fx_reference_rate (
    pair         text        NOT NULL,
    obs_date     date        NOT NULL,
    rate         numeric     NOT NULL,
    series_id    text        NOT NULL,
    derivation   text        NOT NULL DEFAULT '',  -- RULING F7 (see below)
    provenance   text        NOT NULL,
    source       text        NOT NULL,
    retrieved_at timestamptz NOT NULL,
    PRIMARY KEY (pair, obs_date)
);
```

Upsert pattern, per the Global Constraint — **every** non-key column is set:

```python
cur.execute(
    f'''INSERT INTO "{PG_SCHEMA_V2}".reference_rate
        (series_id, obs_date, value_pct, unit, label, tenor_years,
         provenance, source, retrieved_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (series_id, obs_date) DO UPDATE SET
          value_pct    = EXCLUDED.value_pct,
          unit         = EXCLUDED.unit,
          label        = EXCLUDED.label,
          tenor_years  = EXCLUDED.tenor_years,
          provenance   = EXCLUDED.provenance,
          source       = EXCLUDED.source,
          retrieved_at = EXCLUDED.retrieved_at''',
    (...))
```

`provenance` is `public` on every row of both tables. `source` is `FRED (Federal Reserve Bank of St. Louis)`.

**`derivation` must survive the load — ruling F7's whole point.** `EUR/GBP` is
not published by FRED and is computed as `(DEXUSEU) / (DEXUSUK)`; the artifact
carries that string per row and empty string for the five fetched pairs. Dropping
the column at load would make a quotient indistinguishable from an observation
while both wear a `public` label — which is the misrepresentation the spec's §C
warns against. Copy it through, and verify after loading that exactly one pair
has a non-empty `derivation`.

- [ ] **Step 2: Dry-run**

Run: `uv run loaders/load_rates_wave12.py --dry-run`
Expected: reports **10,539** `reference_rate` and **3,942** `fx_reference_rate` rows (measured, not estimated — the earlier ~12,600 figure came from the conflated tenor count corrected in design §1.4), writes nothing.

- [ ] **Step 3: Load**

Run: `uv run loaders/load_rates_wave12.py`

- [ ] **Step 4: Prove idempotency by reloading**

Run:
```bash
uv run python -c "
import sys; sys.path.insert(0,'.')
from ccf.config import pg_connect, PG_SCHEMA_V2
with pg_connect() as c:
    cur=c.cursor()
    for t in ('reference_rate','fx_reference_rate'):
        cur.execute(f'select count(*) from \"{PG_SCHEMA_V2}\".{t}'); print(t, cur.fetchone()[0])
"
uv run loaders/load_rates_wave12.py
uv run python -c "
import sys; sys.path.insert(0,'.')
from ccf.config import pg_connect, PG_SCHEMA_V2
with pg_connect() as c:
    cur=c.cursor()
    for t in ('reference_rate','fx_reference_rate'):
        cur.execute(f'select count(*) from \"{PG_SCHEMA_V2}\".{t}'); print(t, cur.fetchone()[0])
"
```
Expected: identical counts before and after the second load.

- [ ] **Step 5: Commit**

```bash
git add loaders/load_rates_wave12.py
git commit -m "Wave 12 Task 6: load reference_rate and fx_reference_rate"
```

---

## Task 7: Load the treasury tables into Postgres

**Files:**
- Create: `loaders/load_postgres_wave12_treasury.py`

**Interfaces:**
- Consumes: `wave12_treasury.json`, `wave12_ticks.json`, both via `verify_current`
- Produces: `treasury_client`, `investment_position`, `concentration_limit`, `permitted_instrument`, `stale_signal`, `intraday_tick`; extends `deposit_account`

**The two-writer constraint.** `deposit_account` is owned by `load_collateral_wave9.py` for its 20 rows. Design §1.7 measured that loader as delete-free, so extension is safe. This loader:
- inserts only `W12-` prefixed `account_id`s,
- **never** issues a `DELETE` or `TRUNCATE` against `deposit_account`,
- keys idempotency on `account_id`.

- [ ] **Step 1: Write the DDL**

```sql
CREATE TABLE IF NOT EXISTS "ccf_v2".treasury_client (
    lei             char(20)    PRIMARY KEY,
    mandate_id      text        NOT NULL,
    intent          text        NOT NULL,   -- RULING F1: limits are keyed by intent
    home_currency   char(3)     NOT NULL,
    reported_cash   numeric,
    cash_fact_asof  date,
    cash_provenance text        NOT NULL,
    provenance      text        NOT NULL
);

CREATE TABLE IF NOT EXISTS "ccf_v2".investment_position (
    position_id      text        PRIMARY KEY,
    holder_lei       char(20)    NOT NULL,
    counterparty_lei char(20)    NOT NULL,
    instrument_kind  text        NOT NULL,
    instrument_id    text        NOT NULL,
    currency         char(3)     NOT NULL,
    notional         numeric     NOT NULL,
    yield_bp         numeric     NOT NULL,
    maturity_date    date        NOT NULL,
    provenance       text        NOT NULL
);

CREATE TABLE IF NOT EXISTS "ccf_v2".concentration_limit (
    holder_lei       char(20)    NOT NULL,
    counterparty_lei char(20)    NOT NULL,
    limit_pct        numeric     NOT NULL,
    intent           text        NOT NULL,
    provenance       text        NOT NULL,
    PRIMARY KEY (holder_lei, counterparty_lei, intent)
);

CREATE TABLE IF NOT EXISTS "ccf_v2".permitted_instrument (
    mandate_id      text        NOT NULL,
    instrument_kind text        NOT NULL,
    max_tenor_days  integer     NOT NULL,
    provenance      text        NOT NULL,
    PRIMARY KEY (mandate_id, instrument_kind)
);

-- RULING F5: the stale signal gets its own table rather than being smuggled
-- into `reference_rate`, whose provenance column is `public` on every row. An
-- engineered row wearing a public label is the misrepresentation §C warns of.
CREATE TABLE IF NOT EXISTS "ccf_v2".stale_signal (
    signal_id   text        PRIMARY KEY,
    series_id   text        NOT NULL,
    observed_at timestamptz NOT NULL,
    as_of       timestamptz NOT NULL,   -- RULING F15: the decision reference
    value       numeric     NOT NULL,
    provenance  text        NOT NULL
);

CREATE TABLE IF NOT EXISTS "ccf_v2".intraday_tick (
    tenor_years  numeric     NOT NULL,
    obs_ts       timestamptz NOT NULL,
    trading_day  date        NOT NULL,
    value_pct    numeric     NOT NULL,
    provenance   text        NOT NULL,
    PRIMARY KEY (tenor_years, obs_ts)
);
```

- [ ] **Step 2: Dry-run**

Run: `uv run loaders/load_postgres_wave12_treasury.py --dry-run`
Expected: 15 clients, 100 new deposit accounts, 200 positions, 60 limits, **45** `permitted_instrument` rows (ruling F14 — 15 clients × 3 instrument kinds), 4 `stale_signal` rows, 11,700 ticks.

- [ ] **Step 3: Load, then confirm Wave 9's rows survived**

Run:
```bash
uv run loaders/load_postgres_wave12_treasury.py
uv run python -c "
import sys; sys.path.insert(0,'.')
from ccf.config import pg_connect, PG_SCHEMA_V2
with pg_connect() as c:
    cur=c.cursor()
    cur.execute(f'''select case when account_id like 'W12-%%' then 'wave12' else 'wave9' end, count(*)
                      from \"{PG_SCHEMA_V2}\".deposit_account group by 1 order by 1''')
    print(cur.fetchall())
"
```
Expected: `[('wave12', ~100), ('wave9', 20)]`. **Wave 9's 20 must be intact.** A count below 20 means this loader deleted rows it does not own.

- [ ] **Step 4: Reload and confirm counts are stable**

Run the loader again and repeat the query. Expected: identical.

- [ ] **Step 5: Commit**

```bash
git add loaders/load_postgres_wave12_treasury.py
git commit -m "Wave 12 Task 7: load treasury tables; Wave 9 deposit rows verified intact"
```

---

## Task 8: `validators/intraday.py` — the treasury gate

The gate that makes the engineered conditions provable. It recomputes from loaded rows and never reads a generator's flag. Design §6.1.

**Files:**
- Create: `validators/intraday.py`

**Interfaces:**
- Consumes: `intraday_tick`, `benchmark_curve`, `investment_position`, `concentration_limit`, `permitted_instrument`, `treasury_client`, `reference_rate`
- Produces: exit 0 on PASS, 1 on any failed claim

- [ ] **Step 1: Write the validator**

```python
# validators/intraday.py
"""Wave 12's treasury gate -- claims `conditions.py` cannot establish by counting.

Four claims, each RECOMPUTED from loaded rows:

  1. some day carries a >=8bp move within a 90-minute window
  2. every session's first and last tick equal the published close
  3. tick spacing is exactly 5 minutes, 78 per session, no gaps
  4. >=2 clients breach a concentration limit under a naive optimal allocation
  5. >=1 signal is older than the 15-minute bound AND otherwise well-formed

Claim 1 is the Latency Poisoned instance and claim 4 is the Policy Blind
instance. Neither is catchable by a row count, which is why this file exists
rather than nine more rows in `conditions.py`.

This module deliberately does NOT import `generators/ticks.py`'s
`max_rolling_move_bp`. It reimplements the arithmetic, so a bug in the
generator's rolling-move logic cannot hide by being reused here. That is the
lesson `series.py` was written from.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ccf.config import pg_connect, PG_SCHEMA_V2   # noqa: E402

WINDOW_TICKS = 18            # 90 minutes at 5-minute granularity
THRESHOLD_BP = 8.0
MAX_STALENESS_MIN = 15
EXPECTED_SESSION_TICKS = 78

results: list[tuple[bool, str]] = []


def claim(ok: bool, msg: str) -> None:
    results.append((ok, msg))
    print(f"  {'PASS' if ok else 'FAIL'}  {msg}")


def rolling_max_bp(vals: list[float]) -> float:
    """Independent reimplementation -- see the module docstring."""
    if len(vals) <= WINDOW_TICKS:
        return abs(vals[-1] - vals[0]) * 100 if vals else 0.0
    return max(abs(vals[i + WINDOW_TICKS] - vals[i]) * 100
               for i in range(len(vals) - WINDOW_TICKS))


def main() -> int:
    with pg_connect() as conn:
        cur = conn.cursor()

        cur.execute(f'''SELECT tenor_years, trading_day, obs_ts, value_pct
                          FROM "{PG_SCHEMA_V2}".intraday_tick
                         ORDER BY tenor_years, obs_ts''')
        sessions: dict[tuple, list] = defaultdict(list)
        for tenor, day, ts, val in cur.fetchall():
            sessions[(float(tenor), day)].append((ts, float(val)))

        claim(bool(sessions), f"intraday_tick is populated ({len(sessions)} sessions)")

        # --- claim 1: the 8bp move -------------------------------------
        hits = {day for (tenor, day), rows in sessions.items()
                if rolling_max_bp([v for _, v in rows]) >= THRESHOLD_BP}
        claim(len(hits) >= 1,
              f">=1 day carries a >={THRESHOLD_BP}bp 90-minute move "
              f"(recomputed: {len(hits)} days)")
        for d in sorted(hits):
            print(f"          {d}")

        # --- claim 2: anchor fidelity ----------------------------------
        drift = []
        for (tenor, day), rows in sorted(sessions.items()):
            cur.execute(f'''SELECT par_yield_pct FROM "{PG_SCHEMA_V2}".benchmark_curve
                             WHERE tenor_years = %s AND curve_date = %s''',
                        (tenor, day))
            row = cur.fetchone()
            if row is None:
                drift.append((tenor, day, "no published close"))
                continue
            if abs(rows[-1][1] - float(row[0])) > 1e-6:
                drift.append((tenor, day, f"{rows[-1][1]} != {row[0]}"))
        claim(not drift,
              f"every session closes on its published value "
              f"({len(drift)} drifted)")
        if len(drift) > 5:
            print(f"          (showing 5 of {len(drift)})")
        for d in drift[:5]:
            print(f"          {d}")

        # --- claim 3: spacing ------------------------------------------
        bad = []
        for key, rows in sorted(sessions.items()):
            if len(rows) != EXPECTED_SESSION_TICKS:
                bad.append((key, f"{len(rows)} ticks"))
                continue
            gaps = {(rows[i][0] - rows[i - 1][0]) for i in range(1, len(rows))}
            if gaps != {timedelta(minutes=5)}:
                bad.append((key, f"gaps {sorted(gaps)}"))
        claim(not bad,
              f"every session is {EXPECTED_SESSION_TICKS} ticks, 5 minutes apart "
              f"({len(bad)} malformed)")

        # --- claim 4: the concentration breach -------------------------
        cur.execute(f'''SELECT c.lei, c.mandate_id, c.intent, COALESCE(c.reported_cash, 0)
                          FROM "{PG_SCHEMA_V2}".treasury_client c''')
        clients = cur.fetchall()
        breaching = []
        for lei, mandate_id, intent, cash in clients:
            cur.execute(f'''SELECT instrument_kind FROM "{PG_SCHEMA_V2}".permitted_instrument
                             WHERE mandate_id = %s''', (mandate_id,))
            permitted = {r[0] for r in cur.fetchall()}
            cur.execute(f'''SELECT counterparty_lei, instrument_kind, notional, yield_bp
                              FROM "{PG_SCHEMA_V2}".investment_position
                             WHERE holder_lei = %s''', (lei,))
            positions = cur.fetchall()
            if not positions:
                continue
            eligible = [p for p in positions if p[1] in permitted]
            if not eligible:
                continue
            best = max(eligible, key=lambda p: float(p[3]))
            total = sum(float(p[2]) for p in positions) + float(cash)
            existing = sum(float(p[2]) for p in positions
                           if p[0] == best[0])
            share = (existing + float(cash)) / total if total else 0.0
            # RULING F1: `concentration_limit` is keyed (holder, counterparty,
            # intent). Without the intent filter this returns one row per intent
            # and fetchone() picks arbitrarily, so the breach claim would depend
            # on row order rather than on the data.
            cur.execute(f'''SELECT limit_pct FROM "{PG_SCHEMA_V2}".concentration_limit
                             WHERE holder_lei = %s AND counterparty_lei = %s
                               AND intent = %s''',
                        (lei, best[0], intent))
            row = cur.fetchone()
            if row and share > float(row[0]) / 100.0:
                breaching.append((lei, best[0], round(share * 100, 1),
                                  float(row[0])))
        claim(len(breaching) >= 2,
              f">=2 clients breach a limit under a naive optimal allocation "
              f"(recomputed: {len(breaching)})")
        if len(breaching) > 5:
            print(f"          (showing 5 of {len(breaching)})")
        for lei, cp, share, cap in breaching[:5]:
            print(f"          {lei} -> {cp}  {share}% vs {cap}% cap")

        # --- claim 5: the stale signal (RULING F4) ---------------------
        # §6.1 promises a STALENESS check. Asserting that observation dates
        # exist is an easier question wearing the same label -- the failure
        # `known-issues.md` §10.11 records. Both checks now run.
        # RULING F15: age is measured against the row's recorded `as_of`, NOT
        # against now(). With now(), every signal is stale fifteen minutes after
        # generation, the fresh/stale contrast vanishes, and this claim can
        # never fail -- which would make it a decoration, not a gate.
        cur.execute(f'''SELECT signal_id, series_id, observed_at, value,
                               EXTRACT(EPOCH FROM (as_of - observed_at))/60 AS age_min
                          FROM "{PG_SCHEMA_V2}".stale_signal''')
        signals = cur.fetchall()
        stale = [r for r in signals if r[4] is not None and r[4] > MAX_STALENESS_MIN]
        claim(len(stale) >= 1,
              f">=1 signal is older than the {MAX_STALENESS_MIN}m bound "
              f"({len(stale)} of {len(signals)})")
        # A stale signal that is ALSO malformed would fail a consumer's gate for
        # the wrong reason and prove nothing about staleness.
        wellformed = [r for r in stale if r[1] and r[2] is not None and r[3] is not None]
        claim(len(wellformed) == len(stale),
              f"every stale signal is otherwise well-formed "
              f"({len(stale) - len(wellformed)} are not)")
        # The contrast is the point: a set where EVERYTHING is stale does not
        # demonstrate a staleness gate, it demonstrates a broken feed.
        fresh = [r for r in signals if r[4] is not None and r[4] <= MAX_STALENESS_MIN]
        claim(len(fresh) >= 1,
              f">=1 signal is INSIDE the bound, so the gate discriminates "
              f"({len(fresh)} fresh / {len(stale)} stale)")

        cur.execute(f'''SELECT COUNT(*) FROM "{PG_SCHEMA_V2}".intraday_tick
                         WHERE provenance <> 'synthetic — engineered' ''')
        mislabelled = cur.fetchone()[0]
        claim(mislabelled == 0,
              f"every tick is labelled 'synthetic — engineered' ({mislabelled} are not)")

    failed = [m for ok, m in results if not ok]
    print(f"\n{len(results) - len(failed)} passed, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run it**

Run: `uv run validators/intraday.py`
Expected: all claims PASS, exit 0. The 8bp claim should print at least one date.

- [ ] **Step 3: Mutation-test the 8bp claim**

A gate that cannot fail is not a gate. Temporarily raise `THRESHOLD_BP` to `500.0`, re-run, and confirm claim 1 **FAILS**. Then restore it to `8.0` and confirm it passes again.

Run:
```bash
sed -i 's/^THRESHOLD_BP = 8.0/THRESHOLD_BP = 500.0/' validators/intraday.py
uv run validators/intraday.py; echo "exit=$?  (expect 1)"
sed -i 's/^THRESHOLD_BP = 500.0/THRESHOLD_BP = 8.0/' validators/intraday.py
uv run validators/intraday.py; echo "exit=$?  (expect 0)"
```

- [ ] **Step 4: Mutation-test the anchor claim**

Corrupt one tick in the database, confirm claim 2 fails, then reload to restore.

```bash
uv run python -c "
import sys; sys.path.insert(0,'.')
from ccf.config import pg_connect, PG_SCHEMA_V2
with pg_connect(autocommit=True) as c:
    c.cursor().execute(f'''UPDATE \"{PG_SCHEMA_V2}\".intraday_tick SET value_pct = value_pct + 1
                            WHERE (tenor_years, obs_ts) = (
                              SELECT tenor_years, obs_ts
                                FROM \"{PG_SCHEMA_V2}\".intraday_tick
                               ORDER BY obs_ts DESC, tenor_years DESC
                               LIMIT 1)''')
"
uv run validators/intraday.py; echo "exit=$?  (expect 1)"
uv run loaders/load_postgres_wave12_treasury.py
uv run validators/intraday.py; echo "exit=$?  (expect 0)"
```

- [ ] **Step 5: Commit**

```bash
git add validators/intraday.py
git commit -m "Wave 12 Task 8: intraday gate, mutation-tested on 8bp and anchor claims"
```

---

## Task 9: Load treasury edges into Fluree

**Files:**
- Create: `loaders/load_fluree_wave12_treasury.py`

**Interfaces:**
- Produces Fluree assertions: `heldAt` and `concentratedIn` (position → counterparty), plus the time-versioned regulatory posture overlay

**Constraints:**
- Types asserted explicitly for every queryable role (`DepositAccount`, and each position typed for both its instrument class and the roles it must answer). No inference.
- `reconcile()` scopes retraction **by subject** — the node URIs this loader owns — never by predicate. `known-issues.md` §10.5.

- [ ] **Step 1: Verify the dormant Wave 10 hazard does not fire**

Design §7.1: `load_fluree_wave10.py` still carries a predicate-scoped reconcile over six predicates. Wave 12 writes new predicates, so it should not overlap — verify rather than assume.

Run:
```bash
grep -n "reconcile\|_asserted_triples\|PREDICATE" loaders/load_fluree_wave10.py | head -20
```
Then list the six predicates it retracts and confirm none of `heldAt`, `concentratedIn`, `observedIn`, `amends` appear. **Record the six in the commit message.** If any overlaps, stop and fix `load_fluree_wave10.py` to subject-scoping first — that is a prerequisite, not a follow-up.

- [ ] **Step 2: Write the loader following `load_fluree_wave11b.py`'s structure**

Reuse the established shape: `my_node_uris()` computes the subject set this loader owns; `reconcile()` retracts only triples whose **subject** is in that set; `build()` emits the assertion list; `main()` takes `--dry-run` and `--reconcile`.

- [ ] **Step 3: Dry-run, then load**

Run: `uv run loaders/load_fluree_wave12_treasury.py --dry-run`
Then: `uv run loaders/load_fluree_wave12_treasury.py`

- [ ] **Step 4: Prove idempotency on triple count**

```bash
uv run python -c "
import sys; sys.path.insert(0,'.')
from ccf.fluree import count_triples; print('before', count_triples())"
uv run loaders/load_fluree_wave12_treasury.py
uv run python -c "
import sys; sys.path.insert(0,'.')
from ccf.fluree import count_triples; print('after ', count_triples())"
```
Expected: identical counts.

- [ ] **Step 5: Commit**

```bash
git add loaders/load_fluree_wave12_treasury.py
git commit -m "Wave 12 Task 9: treasury edges in Fluree, reconcile scoped by subject"
```

---

## Task 10: Part 43 — the pure profile derivation

**Files:**
- Create: `generators/part43.py`
- Test: `validators/test_part43.py`

**Interfaces:**
- Produces:
  - `G10_PAIRS: tuple[str, ...]` — the six, in market convention
  - `normalise_pair(c1: str, c2: str) -> str | None` — market convention, `None` if not one of the six
  - `derive_profile(rows: Iterable[dict]) -> dict` — `{pair_mix, hour_mix, action_mix, chain_lengths, n_rows}`

**Constraint:** Part 43 emits legs unordered, so `JPY`+`USD` must normalise to `USD/JPY`, not `JPY/USD`. Design §4.3 — the convention is applied once, here.

- [ ] **Step 1: Write the failing test**

```python
# validators/test_part43.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from generators.part43 import G10_PAIRS, normalise_pair, derive_profile


def test_the_six_pairs_are_market_convention():
    assert G10_PAIRS == ("EUR/USD", "USD/JPY", "AUD/USD",
                         "USD/CAD", "GBP/USD", "EUR/GBP")


def test_legs_normalise_regardless_of_order():
    assert normalise_pair("JPY", "USD") == "USD/JPY"
    assert normalise_pair("USD", "JPY") == "USD/JPY"


def test_usd_is_the_base_for_jpy_and_cad_but_the_quote_for_eur_and_gbp():
    """This is the whole reason the convention is a table, not a rule."""
    assert normalise_pair("USD", "CAD") == "USD/CAD"
    assert normalise_pair("EUR", "USD") == "EUR/USD"
    assert normalise_pair("GBP", "USD") == "GBP/USD"


def test_eur_gbp_is_a_cross_with_no_usd_leg():
    assert normalise_pair("GBP", "EUR") == "EUR/GBP"


def test_ndf_pairs_are_rejected():
    """Design §1.5: Part 43's bulk is NDFs. They must not reach the profile."""
    for c in ("KRW", "TWD", "INR", "BRL", "IDR", "PHP", "CLP", "COP"):
        assert normalise_pair(c, "USD") is None, f"{c} leaked into the G10 set"


def test_missing_legs_are_rejected():
    assert normalise_pair("", "USD") is None
    assert normalise_pair("USD", "") is None


def test_profile_counts_pairs_hours_and_actions():
    rows = [
        {"Notional currency-Leg 1": "EUR", "Notional currency-Leg 2": "USD",
         "Execution Timestamp": "2026-08-19T14:22:01Z", "Action type": "NEWT",
         "Original Dissemination Identifier": ""},
        {"Notional currency-Leg 1": "USD", "Notional currency-Leg 2": "JPY",
         "Execution Timestamp": "2026-08-19T10:05:00Z", "Action type": "MODI",
         "Original Dissemination Identifier": "ABC123"},
        {"Notional currency-Leg 1": "KRW", "Notional currency-Leg 2": "USD",
         "Execution Timestamp": "2026-08-19T03:00:00Z", "Action type": "NEWT",
         "Original Dissemination Identifier": ""},
    ]
    p = derive_profile(rows)
    assert p["n_rows"] == 2, "the KRW row should have been filtered out"
    assert p["pair_mix"]["EUR/USD"] == 1
    assert p["pair_mix"]["USD/JPY"] == 1
    assert "KRW/USD" not in p["pair_mix"]
    assert p["hour_mix"]["14"] == 1
    assert p["hour_mix"]["10"] == 1
    assert "03" not in p["hour_mix"], "NDF hours must not shape the profile"
    assert p["action_mix"]["NEWT"] == 1
    assert p["action_mix"]["MODI"] == 1


def test_chain_lengths_count_links_per_original():
    rows = [
        {"Notional currency-Leg 1": "EUR", "Notional currency-Leg 2": "USD",
         "Execution Timestamp": "2026-08-19T14:00:00Z", "Action type": "CORR",
         "Original Dissemination Identifier": "X1"},
        {"Notional currency-Leg 1": "EUR", "Notional currency-Leg 2": "USD",
         "Execution Timestamp": "2026-08-19T15:00:00Z", "Action type": "CORR",
         "Original Dissemination Identifier": "X1"},
        {"Notional currency-Leg 1": "GBP", "Notional currency-Leg 2": "USD",
         "Execution Timestamp": "2026-08-19T15:00:00Z", "Action type": "MODI",
         "Original Dissemination Identifier": "X2"},
    ]
    p = derive_profile(rows)
    assert p["chain_lengths"] == {"1": 1, "2": 1}, p["chain_lengths"]


def test_empty_input_does_not_crash():
    p = derive_profile([])
    assert p["n_rows"] == 0
    assert p["pair_mix"] == {}


if __name__ == "__main__":
    import traceback
    passed = failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn(); passed += 1; print(f"  PASS {name}")
            except Exception:
                failed += 1; print(f"  FAIL {name}"); traceback.print_exc()
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run validators/test_part43.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'generators.part43'`

- [ ] **Step 3: Write minimal implementation**

```python
# generators/part43.py
"""Derive trade-shaping distributions from real CFTC Part 43 FX records.

Design §1.5 -- Part 43's bulk is NON-DELIVERABLE forwards (KRW, TWD, INR,
BRL), because deliverable FX is carved out of the swap definition by Treasury
determination. Patterning on the whole file yields an all-NDF, Asian-hours
dataset that matches nothing else in the estate.

Design §1.6 -- the G10 majors ARE present, at 5.3% of rows, carrying their own
London/NY execution profile and their own amendment chains. So this module
filters to the six pairs first and derives every distribution from real
records OF THOSE PAIRS.

Only distributions cross this boundary. No real trade is ever loaded as a
trade: the SHAPE is public and cited, the INSTANCES are engineered.
"""

from __future__ import annotations

from collections import Counter
from typing import Iterable

#: The six, in market convention. Order is fixed so tests can pin it.
G10_PAIRS = ("EUR/USD", "USD/JPY", "AUD/USD", "USD/CAD", "GBP/USD", "EUR/GBP")

#: Market convention is a TABLE, not a rule: USD is the base for JPY and CAD
#: but the quote for EUR, GBP, and AUD. Any rule inferred from one row is
#: wrong for the others, which is exactly the §7.4 trap in another costume.
_CONVENTION = {
    frozenset(("EUR", "USD")): "EUR/USD",
    frozenset(("USD", "JPY")): "USD/JPY",
    frozenset(("AUD", "USD")): "AUD/USD",
    frozenset(("USD", "CAD")): "USD/CAD",
    frozenset(("GBP", "USD")): "GBP/USD",
    frozenset(("EUR", "GBP")): "EUR/GBP",
}


def normalise_pair(c1: str, c2: str) -> str | None:
    """Market-convention pair name, or None if not one of the six."""
    if not c1 or not c2 or c1 == c2:
        return None
    return _CONVENTION.get(frozenset((c1, c2)))


def derive_profile(rows: Iterable[dict]) -> dict:
    """Distributions over G10 rows only.

    Returns pair mix, execution-hour mix, action-type mix, and the
    chain-length histogram (how many dissemination links each original
    accumulated).
    """
    pair_mix: Counter[str] = Counter()
    hour_mix: Counter[str] = Counter()
    action_mix: Counter[str] = Counter()
    per_original: Counter[str] = Counter()
    n = 0

    for r in rows:
        pair = normalise_pair(r.get("Notional currency-Leg 1", ""),
                              r.get("Notional currency-Leg 2", ""))
        if pair is None:
            continue
        n += 1
        pair_mix[pair] += 1
        action_mix[r.get("Action type", "") or "UNKNOWN"] += 1
        ts = r.get("Execution Timestamp", "") or ""
        if len(ts) > 13:
            hour_mix[ts[11:13]] += 1
        odi = r.get("Original Dissemination Identifier", "") or ""
        if odi:
            per_original[odi] += 1

    chain_lengths = Counter(str(v) for v in per_original.values())

    return {
        "n_rows": n,
        "pair_mix": dict(pair_mix),
        "hour_mix": dict(hour_mix),
        "action_mix": dict(action_mix),
        "chain_lengths": dict(chain_lengths),
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run validators/test_part43.py`
Expected: `9 passed, 0 failed`

- [ ] **Step 5: Commit**

```bash
git add generators/part43.py validators/test_part43.py
git commit -m "Wave 12 Task 10: G10 filter and pair convention, NDF leakage pinned by test"
```

---

## Task 11: Fetch ten days of Part 43

**Files:**
- Create: `generators/fetch_part43.py`
- Writes: `sources/screening/wave12_part43_profile.json`, caches zips under `sources/part43/`

**Interfaces:**
- Consumes: `generators.part43.derive_profile`
- Produces: artifact with the merged profile across all ten days, plus `_meta.days` and `_meta.retrieved_at`

**Constraints:**
- Read the **bytes**, not the status. A 200 that unzips to zero G10 rows is a failure, not a quiet success (`known-issues.md` §8.1).
- Zips are cached; a re-run must not re-download a day it already has.

- [ ] **Step 1: Write the fetcher**

URL pattern, confirmed live in design §1.5:
```
https://pddata.dtcc.com/ppd/api/report/cumulative/cftc/CFTC_CUMULATIVE_FOREX_{YYYY_MM_DD}.zip
```

The fetcher must:
- take the ten most recent **weekdays** ending 2026-08-19,
- skip a day that returns a non-200 or a zero-length body, recording it in `_meta.skipped` rather than aborting,
- stream each zip to `sources/part43/`, unzip in memory, feed `csv.DictReader` to `derive_profile`,
- merge the ten per-day profiles by summing counters,
- **fail** if the merged `n_rows` is below 10,000 (design §1.6 measured ~3,700 G10 rows/day, so ten days well under 10,000 means the filter or the source changed).

- [ ] **Step 2: Dry-run**

Run: `uv run generators/fetch_part43.py --dry-run`
Expected: ten day-lines each reporting total rows and G10 rows; merged `n_rows` around 30,000–40,000.

- [ ] **Step 3: Run it for real**

Run: `uv run generators/fetch_part43.py`

- [ ] **Step 4: Confirm the profile matches the design's measurement**

Run:
```bash
uv run python -c "
import json
p=json.load(open('sources/screening/wave12_part43_profile.json'))
print('G10 rows:', p['n_rows'])
print('pairs   :', sorted(p['pair_mix'].items(), key=lambda kv:-kv[1]))
h=sorted(p['hour_mix'].items(), key=lambda kv:-kv[1])[:5]
print('top hours:', h)
print('chains  :', sorted(p['chain_lengths'].items(), key=lambda kv:int(kv[0])))
"
```
Expected: `EUR/USD` the largest pair; top execution hours in the **London/NY** range (09–16 UTC), **not** 02–05. An Asian-hours peak means NDF rows leaked past the filter — stop and fix `part43.py`.

- [ ] **Step 5: Commit**

```bash
git add generators/fetch_part43.py
git commit -m "Wave 12 Task 11: fetch 10 days of Part 43, G10 profile derived from ~37k real rows"
```

---

## Task 12: Generate the 500 trades, three systems, and the amendment chains

**Files:**
- Create: `generators/generate_fx_trades.py`
- Writes: `sources/screening/wave12_fx.json`

**Interfaces:**
- Consumes: `wave12_part43_profile.json`, `fx_reference_rate`, `legal_entity`
- Produces: `trades`, `system_records`, `clock_offsets`, `amendments`

**Constraints:**
- Pair mix, execution-hour mix, action mix, and chain-length histogram are all **sampled from the derived profile**, not hand-specified.

**Ruling F19 — the observed chain-length histogram slightly UNDERSTATES real
chain lengths, and that is the safe direction.** `derive_profile` counts links
per dissemination id **within one day**, and the merge sums the resulting
histograms rather than the raw per-id counts. A real amendment chain that
crosses midnight — `NEWT` on day N, `CORR` on day N+1 against the same id —
therefore reads as *two* length-1 chains rather than one length-2 chain. About
250 of 5,443 chained originals (4.6%) are affected.

Do **not** re-engineer `part43.py` to fix this. The bias is conservative: it can
only make long chains rarer than reality, never more common, so it cannot
manufacture the §F condition. And §F stays reachable with margin — the measured
profile has 5,443 chained originals in 30,501 G10 rows (17.8%), of which 516
(9.5%) carry two or more links, so 500 generated trades yield roughly **89
chained** against §F's floor of ≥10, and roughly **8 with two or more** against
its floor of ≥3.

What you must not do is *correct upward* for the undercount by inflating chain
lengths during generation. The floors are met by the observed distribution as it
stands; adjusting it toward a condition is how a demonstration stops
demonstrating anything.
- Three systems with fixed, recorded offsets: `trading` +0s, `settlement` +47s, `risk` −112s. The offsets are data, loaded to Fluree, not constants in the reconciliation code.
- Every trade's `value_date` must have a row in `fx_reference_rate` for its pair — checked at generation, not discovered at validation.
- §F floors: ≥10 trades with chains, ≥3 with two or more amendments.

**Ruling F3 — the intraday FX path.** The spec's §D step 4 requires revaluation
"at each system's own observation time, not at a single common rate", and
`narrative_wave12.align()` needs a per-second drift. A daily H.10 series can
express neither. So this task ALSO builds an intraday FX path, using the same
`generators/ticks.py` machinery Task 3 already built and tested:

- for every `(pair, value_date)` in the trade set, interpolate a **288-point
  5-minute path spanning the full 24-hour day** between that date's H.10 close
  and the next publication's, anchored exactly as Task 4 anchors the Treasury
  curve (open at the prior published close, terminate at this date's close);

  **Ruling F21 — the FX path is 24-hour, NOT the treasury's 6.5-hour session.**
  `generators/ticks.py` models a US cash-market session (13:30–19:55 UTC, 78
  ticks) because that is what a Treasury par yield trades in. **FX trades around
  the clock**, and reusing the equity-session window has a consequence that is
  invisible in every row count and fatal to the product's lesson: only ~46% of
  trades execute inside 13:30–19:55, so drift is defined for fewer than half of
  them, and every timing-attributable break must be drawn from that half. The
  measured result was **all 40 timing breaks in hours 14–19 while genuine breaks
  spread across 00–17** — meaning a consumer could separate timing from genuine
  *by hour of day alone*, with no clock alignment at all. That is precisely the
  discrimination `align_clocks` exists to demonstrate, so the dataset would have
  taught the opposite of its lesson while satisfying every §F count.

  Use 288 ticks (24h × 12) per `(pair, value_date)`. `session_times()` in
  `ticks.py` is treasury-specific — do **not** change it; give the FX path its
  own 24-hour tick calendar in the FX generator and leave the treasury one
  alone.;
- write it to `fx_intraday_tick` (Task 14 DDL), labelled
  `synthetic — engineered`, identically to `intraday_tick`;
- the local drift between two adjacent ticks is what Task 15 uses as
  `drift_per_s`.

`fx_reference_rate` still carries the daily closes and still satisfies §F's
"reference rates covering every value date" — the intraday path is additional,
not a replacement, and the daily closes remain its anchors.

- [ ] **Step 1: Write the generator**

Sampling from the profile:

```python
def weighted_choice(rng, mix: dict[str, int]) -> str:
    """Sample a key with probability proportional to its observed count."""
    keys = sorted(mix)
    weights = [mix[k] for k in keys]
    return rng.choices(keys, weights=weights, k=1)[0]
```

Trades carry `trade_id`, `pair`, `notional_band` (banded — **never** a reconstructed true notional, design §2.2 and the spec's own §C caveat), `execution_ts` sampled from `hour_mix`, `value_date`, `counterparty_lei`.

- [ ] **Step 2: Dry-run and check the shape matches the source profile**

Run: `uv run generators/generate_fx_trades.py --dry-run`
Expected output includes a side-by-side of generated vs. observed pair mix (as proportions) and the chain-length histogram, plus `trades with chains: N (>=10)` and `trades with 2+ amendments: M (>=3)`.

- [ ] **Step 3: Run it for real**

Run: `uv run generators/generate_fx_trades.py`

- [ ] **Step 4: Confirm every value date has a rate**

Run:
```bash
uv run python -c "
import json, sys; sys.path.insert(0,'.')
from ccf.config import pg_connect, PG_SCHEMA_V2
a=json.load(open('sources/screening/wave12_fx.json'))
need={(t['pair'],t['value_date']) for t in a['trades']}
with pg_connect() as c:
    cur=c.cursor()
    cur.execute(f'select pair, obs_date::text from \"{PG_SCHEMA_V2}\".fx_reference_rate')
    have=set(cur.fetchall())
missing=need-have
print('trade (pair,value_date) combos:',len(need),'missing a rate:',len(missing))
for m in sorted(missing)[:10]: print('  ',m)
"
```
Expected: `missing a rate: 0`. §F states rate coverage as a condition; this is where it is enforced.

- [ ] **Step 5: Commit**

```bash
git add generators/generate_fx_trades.py
git commit -m "Wave 12 Task 12: 500 FX trades sampled from the real G10 profile"
```

---

## Task 13: The two break populations, and the inversion

The product's entire argument. Design §3.4.

**Files:**
- Create: `generators/narrative_wave12.py`
- Modify: `generators/generate_fx_trades.py` — call into it

**Interfaces:**
- Produces:
  - `SYSTEMS: dict[str, int]` — system name → clock offset in seconds
  - `align(value: float, observed_at: datetime, offset_s: int, as_of: datetime, drift_per_s: float) -> float`
  - `classify(raw_a, raw_b, materiality) -> str` — `"genuine"` or `"within-tolerance"`
  - `build_breaks(trades, rng) -> list[dict]` — ~60, two-thirds timing-attributable

**The construction that must hold.** For the inversion case:
- two systems observe the same trade at different times,
- the underlying rate drifts between those times,
- compared **raw**, the value difference exceeds materiality → `genuine`,
- projected to a common `as_of` using each system's recorded offset, the difference collapses below materiality → `timing`.

For the survivor case: the difference is a genuine booking error that clock alignment cannot explain, so it exceeds materiality under **both** comparisons.

- [ ] **Step 1: Write the failing test for the inversion property**

```python
# validators/test_narrative_wave12.py  (RULING F6: its own file, not appended
# to test_part43.py -- a suite named for one module that tests two stops being
# greppable)
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from generators.narrative_wave12 import (
    SYSTEMS, MATERIALITY, PIP_SIZE, align, classify, pips,
    INVERSION_TRADE_ID,
)
from datetime import datetime, timezone, timedelta


def test_clock_offsets_are_distinct_and_recorded():
    assert set(SYSTEMS) == {"trading", "settlement", "risk"}
    assert len(set(SYSTEMS.values())) == 3, "offsets must differ to matter"


def test_alignment_removes_a_pure_timing_difference():
    """Two systems, same trade, different observation times, drifting rate.

    Raw comparison sees a difference. Aligned comparison must not.
    """
    as_of = datetime(2026, 8, 19, 17, 0, tzinfo=timezone.utc)
    drift = 0.00002                     # per second
    t_a = as_of - timedelta(seconds=300)
    t_b = as_of - timedelta(seconds=60)
    base = 1.1600
    raw_a = base + drift * 300
    raw_b = base + drift * 60
    assert abs(raw_a - raw_b) > 1e-6, "the fixture has no timing difference"

    a = align(raw_a, t_a, SYSTEMS["trading"], as_of, drift)
    b = align(raw_b, t_b, SYSTEMS["settlement"], as_of, drift)
    assert abs(a - b) < 1e-6, "alignment failed to remove a pure timing gap"


def test_alignment_does_not_erase_a_genuine_difference():
    as_of = datetime(2026, 8, 19, 17, 0, tzinfo=timezone.utc)
    drift = 0.00002
    t = as_of - timedelta(seconds=120)
    a = align(1.1600, t, SYSTEMS["trading"], as_of, drift)
    b = align(1.1900, t, SYSTEMS["risk"], as_of, drift)   # a real 300-pip error
    assert abs(a - b) > 0.01, "alignment swallowed a genuine break"


def test_a_pip_is_not_the_same_size_in_every_pair():
    """RULING F13. The trap: one absolute threshold across six pairs."""
    assert PIP_SIZE["USD/JPY"] == 0.01
    assert PIP_SIZE["EUR/USD"] == 0.0001
    # The SAME raw difference is 5 pips of EUR/USD and 0.05 pips of USD/JPY.
    assert abs(pips("EUR/USD", 0.0005) - 5.0) < 1e-9
    assert abs(pips("USD/JPY", 0.0005) - 0.05) < 1e-9


def test_classification_is_scale_correct_across_pairs():
    """A 3-pip difference is the same BREAK in either pair, despite the
    raw numbers differing by 100x."""
    thr = 2.0
    assert classify("EUR/USD", 1.1600, 1.1603, thr) == "genuine"
    assert classify("USD/JPY", 152.85, 152.88, thr) == "genuine"
    assert classify("EUR/USD", 1.1600, 1.1601, thr) == "within-tolerance"
    assert classify("USD/JPY", 152.85, 152.86, thr) == "within-tolerance"


def test_an_unknown_pair_raises_rather_than_guessing_a_pip_size():
    try:
        pips("XXX/YYY", 0.001)
    except ValueError:
        return
    raise AssertionError("an unknown pair must raise, not assume 0.0001")


def test_the_inversion_trade_is_named():
    assert INVERSION_TRADE_ID, "the inversion case must be identifiable"
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run validators/test_narrative_wave12.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'generators.narrative_wave12'`

- [ ] **Step 3: Implement `narrative_wave12.py`**

```python
# generators/narrative_wave12.py
"""The engineered break populations, and the one break that must invert.

Design §3.4. `align_clocks` is the parameter carrying the product's whole
lesson, so the data must contain at least one break where:

    raw comparison      -> variance exceeds materiality -> "genuine"
    clock-aligned       -> variance collapses            -> "timing"

and at least one where alignment changes nothing, so the product is not
merely explaining everything away.

§7.5 is the trap: a break that flips because the materiality threshold
happens to fall between two arbitrary numbers is a coincidence wearing the
argument's costume. The construction below makes the flip follow from the
observation-time gap and the rate drift, which is why `validators/reconcile.py`
asserts variance-decomposition closure rather than just the flip.
"""

from __future__ import annotations

from datetime import datetime, timedelta

#: System name -> recorded clock offset in seconds. Loaded to Fluree as data;
#: the reconciliation must read them from the store, never hardcode them.
SYSTEMS: dict[str, int] = {
    "trading": 0,
    "settlement": 47,
    "risk": -112,
}

#: The designed inversion case. Named so the validator can find it -- but the
#: validator RECOMPUTES the flip rather than trusting this constant.
INVERSION_TRADE_ID = "TRD-W12-0417"

#: The genuine break that survives alignment.
SURVIVOR_TRADE_ID = "TRD-W12-0288"


def align(value: float, observed_at: datetime, offset_s: int,
          as_of: datetime, drift_per_s: float) -> float:
    """Project a system's observed value to the common `as_of` point.

    The system's clock reads `offset_s` seconds away from true, so its
    recorded observation actually happened at `observed_at - offset_s`.
    Projecting forward to `as_of` applies the rate drift over the real
    elapsed interval.
    """
    true_observed = observed_at - timedelta(seconds=offset_s)
    elapsed = (as_of - true_observed).total_seconds()
    return value + drift_per_s * elapsed


#: RULING F13 -- FX pip size is NOT uniform. JPY pairs quote to 2-3 decimals
#: so a pip is 0.01; every other major quotes to 4-5 decimals and a pip is
#: 0.0001. A single ABSOLUTE materiality across six pairs is therefore
#: meaningless: 0.0005 is 5 pips of EUR/USD (a normal spread) and 0.05 pips of
#: USD/JPY (every trade breaks). Thresholds are held in PIPS and converted per
#: pair. Same class of defect as the x100/x10000 units error in `ticks.py`:
#: an arithmetic scale that looks fine until you check it against the domain.
PIP_SIZE = {
    "EUR/USD": 0.0001, "GBP/USD": 0.0001, "AUD/USD": 0.0001,
    "USD/CAD": 0.0001, "EUR/GBP": 0.0001,
    "USD/JPY": 0.01,
}

#: Break-materiality by intent, in PIPS. Produced here rather than in
#: `generate_fx_trades.py` because a threshold chosen apart from the variances
#: it judges is how the inversion becomes an accident (design §7.5).
MATERIALITY = {
    "break-investigation": 2.0,
    "control-review": 5.0,
    "regulatory-report": 1.0,
}


def pips(pair: str, rate_difference: float) -> float:
    """Convert a raw rate difference into pips for that pair."""
    try:
        return abs(rate_difference) / PIP_SIZE[pair]
    except KeyError:
        raise ValueError(f"no pip size for {pair}") from None


def classify(pair: str, raw_a: float, raw_b: float,
             materiality_pips: float) -> str:
    """Two-way comparison, in pips, against the materiality threshold."""
    return ("genuine" if pips(pair, raw_a - raw_b) > materiality_pips
            else "within-tolerance")
```

Plus `build_breaks(trades, rng)` producing ~60 breaks: ~40 timing-attributable (observation-time gaps with no booking error), ~20 genuine (real value discrepancies), including the two named cases.

**Ruling F2.** `narrative_wave12.py` also produces the `materiality_threshold`
rows — one per `intent`, exported as `MATERIALITY: dict[str, float]`. The
threshold is what makes a break a break, so it belongs with the break
construction. Generating the two apart is precisely how §7.5's coincidence
risk gets in: a threshold chosen without reference to the variances it will
judge lands between two arbitrary numbers, and the inversion becomes an
accident of where the line fell.

- [ ] **Step 4: Run to verify it passes**

Run: `uv run validators/test_narrative_wave12.py`
Expected: `8 passed, 0 failed` (plus `test_part43.py` still `10 passed`)

- [ ] **Step 5: Commit**

```bash
git add generators/narrative_wave12.py validators/test_narrative_wave12.py generators/generate_fx_trades.py
git commit -m "Wave 12 Task 13: break populations with the engineered clock-alignment inversion"
```

---

## Task 14: Load the FX tables and edges

**Files:**
- Create: `loaders/load_postgres_wave12_fx.py`, `loaders/load_fluree_wave12_fx.py`

**Postgres DDL:**

```sql
CREATE TABLE IF NOT EXISTS "ccf_v2".fx_trade (
    trade_id         text        PRIMARY KEY,
    pair             text        NOT NULL,
    notional_band    text        NOT NULL,   -- BANDED, never reconstructed
    execution_ts     timestamptz NOT NULL,
    value_date       date        NOT NULL,
    counterparty_lei char(20)    NOT NULL,
    provenance       text        NOT NULL
);

-- RULING F23: NO `observed_at` HERE. The spec's §C assigns "System observation
-- timestamps and clock offsets" to **Fluree**, and "Internal trade records per
-- system" to Postgres. Postgres owns the VALUE; Fluree owns WHEN it was
-- observed. Carrying the timestamp in both is a single-writer violation, and it
-- is the one attribute this product is actually about — §D step 3 reads
-- observations from Fluree and step 4 reads values from Postgres precisely so
-- the reconciliation is a real cross-store assembly.
CREATE TABLE IF NOT EXISTS "ccf_v2".system_trade_record (
    trade_id    text        NOT NULL,
    system_name text        NOT NULL,
    value_rate  numeric     NOT NULL,
    amendment_seq integer   NOT NULL DEFAULT 0,
    provenance  text        NOT NULL,
    PRIMARY KEY (trade_id, system_name, amendment_seq)
);

-- RULING F3: revaluation happens at each system's own observation time, which
-- a daily series cannot express. Anchored to the H.10 closes exactly as
-- `intraday_tick` is anchored to `benchmark_curve`.
CREATE TABLE IF NOT EXISTS "ccf_v2".fx_intraday_tick (
    pair        text        NOT NULL,
    obs_ts      timestamptz NOT NULL,
    value_date  date        NOT NULL,
    rate        numeric     NOT NULL,
    provenance  text        NOT NULL,
    PRIMARY KEY (pair, obs_ts)
);

CREATE TABLE IF NOT EXISTS "ccf_v2".break_record (
    break_id       text     PRIMARY KEY,
    trade_id       text     NOT NULL,
    system_a       text     NOT NULL,
    system_b       text     NOT NULL,
    raw_variance   numeric  NOT NULL,
    designed_class text     NOT NULL,   -- 'timing' | 'genuine' -- NOT trusted by the validator
    provenance     text     NOT NULL
);

-- RULING F13: thresholds are in PIPS, not raw rate units. A pip is 0.01 for
-- JPY pairs and 0.0001 for the rest, so one absolute threshold across six
-- pairs classifies USD/JPY and EUR/USD on scales 100x apart.
CREATE TABLE IF NOT EXISTS "ccf_v2".materiality_threshold (
    intent          text    PRIMARY KEY,
    threshold_pips  numeric NOT NULL,
    provenance      text    NOT NULL
);

CREATE TABLE IF NOT EXISTS "ccf_v2".fx_pip_size (
    pair       text    PRIMARY KEY,
    pip_size   numeric NOT NULL,
    provenance text    NOT NULL   -- public: market convention
);

CREATE TABLE IF NOT EXISTS "ccf_v2".part43_profile (
    dimension   text    NOT NULL,   -- 'pair' | 'hour' | 'action' | 'chain'
    key         text    NOT NULL,
    observed_n  integer NOT NULL,
    provenance  text    NOT NULL,
    source      text    NOT NULL,
    retrieved_at timestamptz NOT NULL,
    PRIMARY KEY (dimension, key)
);
```

`part43_profile` rows are `public` — they are counts of real records. Every other table here is `synthetic — engineered` or `synthetic — internal` per design §2.3.

**Ruling F22 — the loaded schema must not carry a column that separates the two
break classes without alignment.** The generator's artifact necessarily records
its own working values, and two of them are perfect discriminators: `gap_s` is
`0.0` for every genuine break and positive for every timing break, and
`true_a`/`true_b`/`aligned_*` encode the answer directly. If any of those reached
a loaded table, a consumer could classify every break by reading one column and
never perform the clock alignment the product exists to demonstrate — the same
defect as the hour-of-day tell that ruling F21 fixed, arriving through the
schema instead of through the data.

So `break_record` carries **only** the seven columns in the DDL above. Do not add
`gap_s`, `true_a`, `true_b`, `aligned_a`, `aligned_b`, `aligned_diff_pips`, or
`timing_component_pips` "for convenience" — every one of them is the answer.

`designed_class` is the deliberate exception and must be documented in the
loader as such: it is the **answer key**, present so a validator can report
disagreement between what was designed and what recomputation finds. Nothing in
any reconciliation path may consult it. Task 15's gate reads it *only* to count
disagreements, never to classify.

**Verify after loading**: for each of the seven columns, confirm no single column
partitions the 60 breaks exactly along `break_type`. `designed_class` will, by
construction — that is the one expected answer, and it is why it is named.

**Fluree assertions:** `observedIn` (trade → system observation), `amends`
(amendment chains), per-system observation timestamps and clock offsets, and the
timing-artefact break assertions.

**Ruling F23, second half — the predicate is `ex:systemObservedAt`, not
`ex:observedAt`.** `observedAt` is already claimed by Wave 11b as a
Postgres-owned signal attribute, so reusing the bare name makes `partition.py`
report a leak that is really a collision. This wave has already hit and solved
this exact problem once: Task 9 renamed `ex:jurisdiction`/`ex:intent` to
`ex:postureJurisdiction`/`ex:postureIntent` for the same reason. Follow that
precedent. A predicate name is estate-wide, so "it is obvious in context" is not
a property the estate has.

Add `ReconciliationBreak`, `SystemObservation`, and `TradeSystem` to
`validators/partition.py`'s `PERMITTED_EX_TYPES` — all three are legitimate
`ex:` extensions (FIBO models the instrument and the trade, not a bank's
internal system-observation or break-record concepts), and the allowlist simply
has not been told about them.

- [ ] **Step 1: Write both loaders**

Same `--dry-run` / `--reconcile` shape as Task 9. Fluree reconcile scoped by **subject**.

- [ ] **Step 2: Dry-run both**

Run:
```bash
uv run loaders/load_postgres_wave12_fx.py --dry-run
uv run loaders/load_fluree_wave12_fx.py --dry-run
```

- [ ] **Step 3: Load both**

Run:
```bash
uv run loaders/load_postgres_wave12_fx.py
uv run loaders/load_fluree_wave12_fx.py
```

- [ ] **Step 4: Prove idempotency on both**

Re-run each and confirm row counts and `count_triples()` are unchanged.

- [ ] **Step 5: Commit**

```bash
git add loaders/load_postgres_wave12_fx.py loaders/load_fluree_wave12_fx.py
git commit -m "Wave 12 Task 14: load FX trades, system records, breaks, and Fluree edges"
```

---

## Task 15: `validators/reconcile.py` — the FX gate

The hardest claim in the wave, and the one the product exists to make. Design §6.2.

**Files:**
- Create: `validators/reconcile.py`

**Interfaces:**
- Consumes, and **the split is the point** (ruling F23):
  - **From Postgres** — `fx_trade`, `system_trade_record` (the VALUE each system
    holds), `break_record`, `materiality_threshold`, `fx_pip_size`,
    `fx_reference_rate`, `fx_intraday_tick` (ruling F3 — the per-second drift
    comes from adjacent ticks here; a daily series cannot express it).
  - **From Fluree** — each system's **observation timestamp**
    (`ex:systemObservedAt`) and its **clock offset**. `system_trade_record` no
    longer carries `observed_at`; §C assigns observation timestamps to Fluree and
    system values to Postgres.

  This gate is therefore a genuine cross-store assembly, exactly as §D steps 3
  and 4 describe — Temporal Traversal reads observations from Fluree, Batch
  Enrich reads values from Postgres. A version of this validator that could run
  against Postgres alone would be evidence the partition had collapsed.
- Produces: exit 0 on PASS, 1 on any failed claim

**The rule that makes it a gate.** It reads `break_record.designed_class` only to *report disagreement*. Every classification it asserts on is recomputed from `system_trade_record` observation times, the Fluree-held offsets, and the loaded rates.

**Ruling F24 — `system_trade_record` did not actually carry the engineered
discrepancy, and this gate could not have been written honestly until it did.**
Measured before the fix: `system_trade_record.value_rate` was **identical
across all three systems, for every trade, breaking or not** (e.g.
TRD-W12-0417's trading/settlement/risk all read `1.392039`). Cause:
`generate_fx_trades.py`'s `build_chains_and_records()` computes ONE shared
`true_rate` at ONE `event_ts` per `(trade, amendment_seq)` and gives it to all
three systems — correct for the baseline population (module docstring: "every
system observes the SAME true market moment... only their recorded
`observed_at` differs"). `narrative_wave12.py`'s `build_breaks()` (Task 13)
then computes a SEPARATE true instant and value for the two systems an
engineered break actually names — but per ruling F22, only `raw_variance` (a
single pip count) and `designed_class` ever reach Postgres, and NOTHING about
a break's per-system values reaches Fluree. The two per-system numbers
`build_breaks()` computes never reached either store. A validator reading
only Postgres values and Fluree timestamps — which is what this gate is
required to do — would have recomputed a raw difference of exactly zero for
all 60 breaks; neither the inversion nor the survivor claim could ever have
been established by recomputation, only by reading `designed_class` directly,
which is exactly what this gate exists to refuse to do.

**Required fix, in `generate_fx_trades.py`:** `apply_break_overrides()`, called
from `main()` after `build_breaks()`, must override, for each of the 60
breaks, the two named systems' `amendment_seq=0` `system_trade_record` row
with the break's own `raw_a`/`raw_b` (value) and `observed_a`/`observed_b`
(fed to Fluree); the third, uninvolved system stays untouched — exactly
2 × the break count overrides, asserted in `main()`. Regenerating
`wave12_fx.json`/`wave12_fx_ticks.json` and reloading via
`load_postgres_wave12_fx.py` (idempotent upsert) and
`load_fluree_wave12_fx.py --reconcile` must then leave every engineered
break's two named systems genuinely disagreeing in both Postgres value and
Fluree observation timestamp. This is not a Task 15 scope change on
paper — `validators/reconcile.py` itself is read-only — but the data it
reads is, without this fix, structurally incapable of supporting the
recomputation the gate is required to perform.

- [ ] **Step 1: Write the validator**

Seven claims:

| Claim | Assertion |
|---|---|
| Inversion | ≥1 break classifies `genuine` raw and `timing` aligned — recomputed both ways |
| Survivor | ≥1 break classifies `genuine` under **both** comparisons |
| Decomposition closure | `timing_attributable` must be recomputed **independently of `raw_diff_pips`/`aligned_diff_pips`** — as the pip-scaled rate drift across the true observation gap (`drift × (true_b − true_a)`), using the same drift already obtained from adjacent `fx_intraday_tick` rows and the same true instants (`observed_at − clock_offset`) used to build the aligned values. Deriving it instead as `raw_diff_pips − aligned_diff_pips` (the two numbers it is then checked against) makes the check an algebraic identity that is exactly zero for every input and cannot fail — see RULING F26 in `validators/reconcile.py`. Report `abs((timing_attributable + residual) − raw_diff_pips)` per break; because `pips()` takes an absolute value this is not an identity even when independently derived, so pick and justify a gating tolerance against the observed distribution rather than one chosen to make the numbers pass. **State what it catches correctly:** an inconsistency BETWEEN the drift path and the alignment path — an offset applied in one and not the other, or a timestamp that differs between them (measured at 8.97 and 129.8 pips against a 0.1 tolerance). It does **not** catch a collapsed observation gap: with `true_a == true_b` the timing term is zero and `aligned_diff == raw_diff`, so the gap is exactly zero and the check passes. That case belongs to the Inversion claim |
| Break mix | ~⅔ timing / ⅓ genuine across ~60, recomputed |
| Pip scaling | every classification is computed in pips via `fx_pip_size`, never in raw rate units — a USD/JPY break and a EUR/USD break of the same pip size must classify identically |
| Chain shape | ≥10 trades with chains, ≥3 with two or more, recomputed from the Fluree amendment-node structure actually queried (do not claim `ex:amends` is consulted if it is not) |
| Rate coverage | every `(pair, value_date)` in `fx_trade` has an `fx_reference_rate` row |

Plus a **disagreement report**: count breaks where the recomputed class differs from `designed_class`. This is not a failure by itself — a designed-timing break that recomputes as timing for a slightly different reason is fine — but a disagreement rate above ~10% means the generator and the reconciliation disagree about the mechanism, which is §7.5's coincidence risk showing up.

- [ ] **Step 2: Run it**

Run: `uv run validators/reconcile.py`; must exit 0 with every claim in Step 1
PASSing, the Inversion and Survivor claims each printing at least one witness
break, and the closure claim reporting its observed gap distribution (not
merely "0 gaps" — see Step 1's closure row).

**RULING F25 — the zeroed-offset mutation was aimed at the wrong term, and the
data is right.**

Measured on the loaded data: the clock-offset spread is 159s while the median
true observation gap is 458.7s, so the offset is a median **11.9%** of what
alignment corrects. Zeroing it leaves 32 of 40 flips intact — not because the
mechanism is fake, but because the mutation targeted the smaller term.

**Do not inflate the offsets to make this test fail.** §A's narrative is
explicit: the trading system booked *at execution*, settlement recorded
*post-affirmation amendment*, risk revalued *at a different market snapshot*.
Those are genuinely different moments, not clock errors. An observation gap that
dominates the offset is faithful to that story. Enlarging offsets until they
dominate would make the dataset *less* faithful in order to make a test fail —
the same error as tuning a limit until a breach appears.

Two corrections, both to the TEST:

- **Aim the decisive mutation at the observation-time gap.** Collapse every
  system's `ex:systemObservedAt` for a trade to one instant. Alignment can then
  explain nothing and the inversion claim MUST fail.
- **Prove the offset input is live anyway.** Add a claim that alignment *using*
  the recorded offsets differs measurably from alignment *ignoring* them, on at
  least one break. A secondary term is still an input, and a gate that cannot
  tell whether it was applied is not checking it.

**And a general lesson worth carrying past this wave:** the survivor mutation
also failed to flip, because corrupting one `value_rate` cannot falsify a claim
quantified over ~20 witnesses. **Match a mutation's scope to its claim's
quantifier**, or the gate reports green for the wrong reason.

- [ ] **Step 3: Mutation-test the inversion claim**

Zero all three `ex:clockOffsetSeconds` in Fluree (scoped DELETE DATA /
INSERT DATA on the 3 `sys-*` subjects), re-run, restore via
`load_fluree_wave12_fx.py --reconcile`, re-run. Per RULING F25, do **not**
expect the Inversion claim itself to flip from this mutation alone — the
recorded observation-timestamp gap, not the clock offset, does most of the
explanatory work for most timing breaks (see RULING F25 for the measured
ratio and why the offsets must not be inflated to force a different
result). Do expect **Break mix** and the **disagreement rate** to move
detectably, and confirm they do. To exercise the mechanism RULING F25
actually names (§3.4's real claim), aim a second, more decisive mutation at
the true observation instant itself — collapsing `obs_x − offset_x` to a
single point for the two systems in a break — and confirm the Inversion
claim **does** fail against that one, since alignment then has no gap left
to explain.

- [ ] **Step 4: Mutation-test decomposition closure and the survivor claim**

Perturb a named survivor break's second system's value inward, toward its
first system's value, until the pip difference drops under the materiality
threshold, and confirm the disagreement report catches the flip
(`designed=genuine recomputed=timing`) even where the aggregate Survivor
claim (`≥1 genuine under both`) stays green via other witnesses. To witness
the aggregate claim itself fail — not merely one witness among many — a
mutation must be scoped to match the claim's quantifier: neutralize **every**
genuine break's second system to match its first (diff → 0 pips) and confirm
Survivor correctly reports 0 found and the run exits 1. Restore from the
unmodified `wave12_fx.json` artifact via `loaders/load_postgres_wave12_fx.py`
and confirm the run returns to green.

Also mutation-test decomposition closure directly, now that RULING F26 makes
it a real cross-check rather than an identity (IMPORTANT-1, Wave 12 final
review): a mutation that drops or corrupts an observation used to build the
true gap (`true_b − true_a`) without correspondingly correcting the aligned
values must widen the reported closure gap past the gating tolerance — if it
does not, the independence RULING F26 requires has been lost again.

- [ ] **Step 5: Commit**

Commit `validators/reconcile.py`, `generators/generate_fx_trades.py`, and the
regenerated `sources/screening/wave12_fx.json` /
`sources/screening/wave12_fx_ticks.json` artifacts together — the validator
and the data it depends on must land in the same commit, per this repo's
idempotency and single-writer conventions.

---

## Task 16: Conditions, partition, docs, and the punch list

**Files:**
- Modify: `validators/conditions.py`, `validators/partition.py`, `docs/ccf_dataprep_v2.md`, `docs/known-issues.md`, `docs/HANDOFF.md`
- Create: the vault punch-list message under `~/.agent-exchange/ccf-dataprep/outbox/`

- [ ] **Step 1: Extend `conditions.py` with both §F sets**

Treasury: ~15 clients · ~120 deposit accounts across 4 currencies · ~200 positions with laddered maturities · 30 trading days of ticks at 5-minute granularity · ≥1 8bp day · ≥2 breaching clients · ≥1 stale signal.

FX: ~500 trades · 6 pairs · 3 systems with distinct offsets · ~60 breaks at ⅔/⅓ · ≥10 chained trades · ≥3 with 2+ amendments · ≥1 inversion · ≥1 survivor · full rate coverage.

The `≥1 8bp day`, `≥2 breaching`, `≥1 inversion`, and `≥1 survivor` rows here are **row-presence** checks. The *proof* lives in `intraday.py` and `reconcile.py`; `conditions.py` records that the row exists, not that the condition holds. Say so in the check labels so a future reader does not mistake one for the other.

- [ ] **Step 2: Extend `partition.py`**

New checks: every Wave 12 Postgres table holds only what it owns; `heldAt` / `concentratedIn` / `observedIn` / `amends` exist **only** in Fluree; no rate value is duplicated from `reference_rate` into Fluree; no Fluree node carries an attribute that resolves from Postgres.

- [ ] **Step 3: Run every gate**

```bash
uv run validators/partition.py                    # expect 19 + new checks, all pass
uv run validators/conditions.py                   # expect 91 + new checks, 0 FAILED
uv run validators/intraday.py                     # expect PASS
uv run validators/reconcile.py                    # expect PASS
uv run validators/series.py                       # expect PASS -- Wave 11a must not move
uv run validators/surveillance.py                 # expect PASS -- Wave 11b must not move
uv run validators/traversal.py                    # expect unchanged
uv run validators/bitemporal.py                   # expect 3/3
uv run validators/projection.py                   # expect exit 0
uv run validators/orphan_terms.py                 # expect 67/67 or higher, exit 0
uv run validators/artifact_reproduces_store.py    # expect 54/56 + new checks
uv run validators/binding_drift.py                # expect 11 agree / 29 disagree, unchanged
for t in validators/test_*.py; do echo "== $t"; uv run "$t" || echo "RED"; done
```

**`orphan_terms.py` is the one most likely to be skipped** — nothing else in the list resembles it, and it catches Fluree predicates whose writer was deleted. Run it.

- [ ] **Step 4: Verify the "no new FIBO terms" claim**

Design §1.1 expects zero new terms. That is a claim to verify at close, not an assumption:

```bash
uv run generators/verify_fibo_terms.py
uv run validators/binding_drift.py
```
Expected: drift unchanged at 11 agree / 29 disagree. **If a new `ex:` term appeared**, it must be bound in `docs/ccf_dataprep_v2.md` and added to `sources/screening/published_claims.json` before merge, per CLAUDE.md's definition of done item 5.

- [ ] **Step 5: Update the docs**

`docs/ccf_dataprep_v2.md` — entity tables, file names, counts, the new tables, **the two-writer fact on `deposit_account`** (design §7.2 — record it so the next author sees it before writing a DELETE, not after), and the FX pair convention (design §4.3).

`docs/known-issues.md` — open §12 for Wave 12's defect record.

`docs/HANDOFF.md` — §8 gains Wave 12 as complete; the next wave becomes the new "start here."

- [ ] **Step 6: Send the Part 43 punch list to the vault**

Design §7.3. The finding: Part 43 structurally cannot supply deliverable major-pair FX, because deliverable FX is carved out of the swap definition — so §C's presentation of it needs the caveat, and an implementer patterning on the whole file gets an all-NDF dataset.

Read **section 5 of the `obsidian-vault-access` skill** before sending. The message directory is `<YYYY-MM-DDTHH-MM-SSZ>-<slug>` with **hyphens in the time, never colons**, or the vault's reconciler rejects it visibly but unsent.

**Four punch lists (Waves 10, 11a, 11b, 11c) are already uncollected. Do not re-send them.** This is a fifth.

- [ ] **Step 7: Commit and merge**

```bash
git add -A
git commit -m "Wave 12 Task 16: conditions, partition, docs, and the Part 43 punch list"
```

---

## Self-review notes

**Spec coverage.** Every design section maps to a task:

| Design § | Task |
|---|---|
| §1.1 FIBO terms already bound | 16 (verified at close, not assumed) |
| §1.2 client set is the 15 | 5 |
| §1.3 the window and its margin | 4 |
| §1.4 FRED direction map | 1, 2 |
| §1.5–1.6 Part 43 and the G10 subset | 10, 11 |
| §1.7 two-writer deposit table | 7, 16 |
| §2.2 shape public, instances engineered | 10, 11, 14 |
| §2.3 provenance per element | 6, 7, 14 |
| §3.1 tick series and the 8bp move | 3, 4, 8 |
| §3.2 concentration breach | 5, 8 |
| §3.3 stale signal | 5, 8 |
| §3.4 the inversion | 13, 15 |
| §4.1 store partition | 6, 7, 9, 14, 16 |
| §4.2 explicit typing | 9, 14 |
| §4.3 correlation keys, pair convention | 10, 12, 15 |
| §5 pipeline order | task order |
| §6.1 `intraday.py` | 8 |
| §6.2 `reconcile.py` | 15 |
| §6.3 existing gates re-run | 16 |
| §7.1 dormant Wave 10 hazard | 9 step 1 |
| §7.2 two-writer risk | 7, 16 |
| §7.3 punch list | 16 |
| §7.4 reciprocal trap | 1 |
| §7.5 coincidental inversion | 13, 15 |
| §8 definition of done | 16 |

**Gaps deliberately left.** Task 5's full generator body and Task 12's are described by their outputs and constraints rather than written line-by-line, because both are straightforward row generation over a schema this plan states in full — unlike the pure modules (Tasks 1, 3, 10, 13) and the two validators (8, 15), where the exact arithmetic *is* the deliverable and is given verbatim.

**Type consistency.** `normalise_fx` returns `(pair, rate)` in Task 1 and is consumed that way in Task 2. `normalise_pair` returns `str | None` in Task 10 and is consumed with a `None` check in Task 12. `SYSTEMS` is `dict[str, int]` in Task 13 and read from Fluree — not imported — in Task 15. `max_rolling_move_bp` is used in Task 4 and deliberately **reimplemented** as `rolling_max_bp` in Task 8; that duplication is intentional and documented in both files.

**The two gates are mutation-tested, not merely run.** Tasks 8 and 15 each include a step that breaks the data and confirms the gate goes red. A gate never observed failing is a gate nobody has tested.
