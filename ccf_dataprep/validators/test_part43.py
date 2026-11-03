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
