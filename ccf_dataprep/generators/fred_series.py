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
