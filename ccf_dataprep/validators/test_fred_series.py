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
