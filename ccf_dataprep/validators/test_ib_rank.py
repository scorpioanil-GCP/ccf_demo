"""Wave 16 — the ranking instrument, and the pins it depends on."""
from __future__ import annotations


def test_as_of_is_pinned_not_today():
    """Pin the three constants that the ranking computation depends on.

    Every signal class decays over time. The ranking must be computed at a
    fixed instant, not at today's date, or the engineered divergence will
    pass on build day and silently expire weeks later as the catalysts age
    past their weight floor.
    """
    from ccf.config import AS_OF_IB, IB_WINDOW_END, IB_WINDOW_START

    assert AS_OF_IB == "2026-08-24"
    assert IB_WINDOW_START == "2025-08-25"
    assert IB_WINDOW_END == "2026-08-24"


def test_wave16_terms_are_bound():
    """A term generated against but never bound validates here and cannot be
    consumed downstream. That failure is silent and expensive, so it is a test.

    FINAL FIX WAVE: this list had three of the seven terms Wave 16 actually
    minted -- `magnitude`, `comparabilityBasis`, `isCurrent`, and
    `primaryBankerId` were asserted by the same loader and missing from
    this exact test the whole time. Now names all seven, so a future
    unbound term this loader introduces has to be added here explicitly
    rather than the list quietly staying a subset forever."""
    from pathlib import Path

    md = Path("docs/ccf_dataprep_v2.md").read_text()
    for local in ("OpportunitySignal", "magnitude", "coveredBy",
                  "comparableTo", "comparabilityBasis", "isCurrent",
                  "primaryBankerId"):
        assert f"http://example.org/fibo/{local}" in md, f"{local} unbound"


def test_every_prospect_note_resolves_to_a_banker():
    """Rule 4. A note whose author is not in the roster cannot be enriched
    into that banker's product, and cannot be shown to have changed a ranking.

    Counting notes proves nothing here -- 50 notes that join to nobody is the
    exact failure this asserts against. Count the notes that RESOLVE.
    """
    import sqlite3

    from ccf.config import PG_SCHEMA_V2 as S
    from ccf.config import REPO_ROOT, pg_connect

    sq = sqlite3.connect(REPO_ROOT / "data" / "departmental.sqlite")
    notes = sq.execute("SELECT note_id, banker_id FROM prospect_note").fetchall()
    assert notes, "no prospect notes at all"

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT banker_id FROM "{S}".banker')
        roster = {r[0] for r in cur.fetchall()}

    orphans = [n for n, b in notes if b not in roster]
    assert not orphans, f"{len(orphans)}/{len(notes)} notes have no banker: {orphans[:5]}"


def test_schedule13d_matches_both_form_name_eras():
    """The SEC renamed the form under the structured-XML mandate in Dec 2024.

    Matching only `SC 13D` returns zero filings after 2024-12-06, which is
    indistinguishable from the source drying up. It had not. This test exists
    because that read cost a probe to catch, and the same shape will recur.
    """
    from generators.fetch_schedule13d import FORMS, matches

    assert matches("SC 13D")            # legacy
    assert matches("SCHEDULE 13D")      # modern
    assert matches("SCHEDULE 13D/A")    # modern amendment
    assert not matches("SC 13G")        # 13G is not a catalyst signal
    assert not matches("SCHEDULE 13E-3")
    assert "SCHEDULE 13D" in FORMS and "SC 13D" in FORMS


def test_schedule13d_role_invariant():
    """Fix round 1. `role` must be resolved for every filing, never None, and
    the resolution must genuinely discriminate -- if SUBJECT and FILER ever
    collapse to a single value across the whole artifact, the resolver has
    stopped looking rather than confirmed uniformity.
    """
    import json

    from ccf.config import REPO_ROOT

    data = json.loads(
        (REPO_ROOT / "sources" / "screening" / "wave16_13d.json").read_text())
    filings = data["filings"]
    assert filings, "no filings in the artifact"

    roles = {f["role"] for f in filings}
    assert None not in roles, "some filing has role=None"
    assert roles <= {"SUBJECT", "FILER", "UNKNOWN"}, f"unexpected role(s): {roles}"

    assert any(f["role"] == "SUBJECT" for f in filings), "no SUBJECT filing at all"
    assert any(f["role"] == "FILER" for f in filings), "no FILER filing at all"

    # Most UNKNOWNs are pre-2011 filings, where EDGAR's older archive layout
    # has no `-index-headers.html` -- a fact about EDGAR's history, not a
    # defect in the resolver. But the ranking signals are built from the
    # 12-month window (IB_WINDOW_START/END), and an UNKNOWN leaking into that
    # window would be silently unusable there. So inside the window, role
    # must always resolve.
    from ccf.config import IB_WINDOW_START

    in_window = [f for f in filings if f["filing_date"] >= IB_WINDOW_START]
    assert in_window, "no filings in the signal window at all"
    window_unknown = [f for f in in_window if f["role"] == "UNKNOWN"]
    assert not window_unknown, (
        f"{len(window_unknown)} filing(s) in the signal window "
        f"(>= {IB_WINDOW_START}) have role UNKNOWN: {window_unknown[:3]}")


def test_8k_item_codes_include_completed_acquisitions():
    """Item 1.01 is entry into a material agreement; 2.01 is COMPLETION of an
    acquisition. The M&A originator's ranking needs both -- an announced deal
    and a closed one are different signals about the same prospect."""
    from generators.fetch_8k_items import ITEM_CODES

    assert "1.01" in ITEM_CODES
    assert "2.01" in ITEM_CODES


def test_merger_doc_forms_exclude_s1():
    """S-1 is dropped, with evidence, not forgotten.

    Probed 2026-08-24: 43 S-1 filings lifetime across the anchor set, ZERO
    since 2023, because the cast are established issuers who do not file IPO
    registrations. S-4 covers the merger-registration half of the same SC row.
    """
    from generators.fetch_merger_docs import FORMS

    assert "DEFM14A" in FORMS and "PREM14A" in FORMS
    assert "S-4" in FORMS and "S-4/A" in FORMS
    assert "S-1" not in FORMS


def test_merger_docs_respect_the_pinned_as_of():
    """Fix round 1. The fetch filter was `date >= WINDOW_START` with no upper
    bound -- unpinned at the top even though `test_as_of_is_pinned_not_today`,
    two tests above this one in the same file, exists to enforce exactly this
    property for the ranking path. A pinned as-of that pins the ranking but
    not the corpus the ranking reads is not pinned: re-running the fetch after
    2026-08-24 would silently pull newly-filed proxies into what is supposed
    to be a reproducible snapshot.

    Guarded against vacuity: an empty artifact would satisfy "every date is
    <= AS_OF_IB" for free, so non-emptiness is asserted first.
    """
    import json

    from ccf.config import AS_OF_IB, REPO_ROOT

    data = json.loads(
        (REPO_ROOT / "sources" / "screening" / "wave16_merger_docs.json").read_text())
    docs = data["documents"]
    assert docs, "no merger documents in the artifact"

    late = [d for d in docs if d["filing_date"] > AS_OF_IB]
    assert not late, f"{len(late)} document(s) filed after the pinned as-of " \
        f"{AS_OF_IB}: {[d['filing_date'] for d in late][:5]}"


def test_usaspending_rows_carry_a_match_band():
    """USASpending joins on NAME. There is no LEI, no CIK, no shared key.

    Its `keywords` filter searches award DESCRIPTION text, which returned
    XPO -> Lockheed Martin and REGIS -> Humana Government Business. Switching
    to `recipient_search_text` narrows it but does not fix it: AMPHENOL ->
    MTS Systems.

    CLAUDE.md rule 5 wants joins that are imperfect ON PURPOSE. These are
    imperfect BY ACCIDENT, and a government-revenue-concentration measure
    built on them is simply wrong. So every row records how it was matched,
    and unverified candidates are dropped rather than guessed.
    """
    from generators.fetch_usaspending import MATCH_BANDS, classify

    assert set(MATCH_BANDS) == {"exact", "verified-subsidiary", "rejected"}
    assert classify("SP PLUS LLC", "SP Plus Corp") == "exact"
    assert classify("LOCKHEED MARTIN CORP", "XPO") == "rejected"


def test_no_award_is_attributed_without_an_allowlist_entry():
    """The real admission path, not classify().

    classify() is only used by --propose; it never touches the artifact.
    The gate that actually decides what gets emitted lives in main() as an
    exact dict lookup keyed on (lei, recipient_name). This test would fail
    if that gate were ever replaced with a fuzzy fallback -- the previous
    test would not notice.

    Guarded against vacuity: the awards list must be non-empty first, or
    "every award maps to an allow-list entry" would hold for free.
    """
    import json

    from ccf.config import REPO_ROOT

    allow = json.loads(
        (REPO_ROOT / "sources" / "usaspending" / "recipient_allowlist.json")
        .read_text())["entries"]
    admissible = {(e["lei"], e["recipient_name"].upper()) for e in allow
                  if e["match_band"] != "rejected"}

    data = json.loads(
        (REPO_ROOT / "sources" / "screening" / "wave16_usaspending.json")
        .read_text())
    awards = data["awards"]
    assert awards, "no awards in the artifact"

    unlisted = [a for a in awards
                if (a["lei"], a["recipient_name"]) not in admissible]
    assert not unlisted, \
        f"{len(unlisted)} award(s) attributed with no allow-list entry: " \
        f"{unlisted[:3]}"

    for a in awards:
        assert a.get("match_band"), f"award missing match_band: {a}"
        assert a.get("verified_against"), f"award missing verified_against: {a}"
        assert a["match_band"] in {"exact", "verified-subsidiary"}, \
            f"award carries an inadmissible match_band: {a}"


def test_weights_separate_ma_from_dcm():
    """§F's centrepiece is that identical signals produce different orderings.

    That is a property of the WEIGHT VECTORS, and it is checkable before any
    data loads: if M&A and DCM weight the same signal types the same way, no
    amount of signal data will make the two lists differ.
    """
    from generators.generate_ib_perspectives import WEIGHTS_V2

    ma = {w["signal_type"]: w["weight"] for w in WEIGHTS_V2 if w["perspective_id"] == "PSP-MA"}
    dcm = {w["signal_type"]: w["weight"] for w in WEIGHTS_V2 if w["perspective_id"] == "PSP-DCM"}

    assert ma["activist_stake_13d"] >= 0.9, "13D is the M&A originator's top signal"
    assert dcm["activist_stake_13d"] <= 0.15, "a 13D is near-noise to a DCM banker"
    assert dcm["maturity_wall"] >= 0.9, "the maturity wall is the DCM banker's top signal"
    assert ma["maturity_wall"] <= 0.15, "a maturity wall is near-noise to an M&A originator"


def test_two_weight_versions_exist_and_differ():
    """SF: two weight-vector versions, so a ranking can be replayed under the
    prior one. Two IDENTICAL versions would satisfy a count and prove nothing."""
    from generators.generate_ib_perspectives import WEIGHTS_V1, WEIGHTS_V2

    v1 = {(w["perspective_id"], w["signal_type"]): w["weight"] for w in WEIGHTS_V1}
    v2 = {(w["perspective_id"], w["signal_type"]): w["weight"] for w in WEIGHTS_V2}
    assert set(v1) == set(v2), "the two versions must cover the same cells"
    assert v1 != v2, "two identical weight vectors replay to the same order"


def test_half_life_lives_once():
    """Lambda_c is a property of the signal class per SE, not of a perspective.

    Storing it per (perspective, signal_type) would triple every value and let
    the three copies drift, so it lives on the signal class alone.
    """
    from generators.generate_ib_perspectives import SIGNAL_CLASSES, WEIGHTS_V2

    # Count the population FIRST. `all(...)` over an empty sequence is True,
    # so without these two lines both assertions below pass when the
    # generator produces nothing at all -- a gate blind to its own
    # denominator, which is this estate's second-most-repeated defect.
    assert len(SIGNAL_CLASSES) >= 10, f"only {len(SIGNAL_CLASSES)} signal classes"
    assert len(WEIGHTS_V2) >= 30, f"only {len(WEIGHTS_V2)} v2 weight rows"

    assert all("half_life_days" in c for c in SIGNAL_CLASSES)
    assert all("half_life_days" not in w for w in WEIGHTS_V2)


def test_every_pair_covers_exactly_the_signal_class_set():
    """A missing cell in one (perspective, version) pair and a stray or
    typo'd cell in another pair cancel out in a raw row count -- 66 either
    way. The real invariant is per-pair coverage: each (perspective,
    version) pair must carry EXACTLY the signal-class set, no more, no
    less. A typo'd signal_type silently zero-weights that signal for that
    perspective with nothing else failing.
    """
    import json

    from ccf.config import REPO_ROOT

    data = json.loads(
        (REPO_ROOT / "sources" / "screening" / "wave16_perspectives.json")
        .read_text())
    weights = data["weights"]
    expected_types = {c["signal_type"] for c in data["signal_classes"]}

    by_pair: dict[tuple[str, str], set[str]] = {}
    for w in weights:
        key = (w["perspective_id"], w["weight_version"])
        by_pair.setdefault(key, set()).add(w["signal_type"])

    # Guard against vacuity first: an empty artifact has zero pairs, and
    # "every pair covers the set" holds for free over zero pairs.
    assert len(by_pair) == 6, f"expected 6 (perspective, version) pairs, got {len(by_pair)}"

    for pair, actual_types in sorted(by_pair.items()):
        assert actual_types == expected_types, (
            f"{pair}: missing {sorted(expected_types - actual_types)}, "
            f"extra {sorted(actual_types - expected_types)}"
        )


def test_debt_ladder_covers_the_prospect_set():
    """§F's divergence condition needs a DCM field wide enough to rank in.

    Counts obligors, not instruments: 100 bonds on 30 issuers leaves the same
    two-fifths of the prospect set unrankable as 60 bonds did.
    """
    from ccf.config import PG_SCHEMA_V2 as S
    from ccf.config import pg_connect

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT COUNT(DISTINCT lei) FROM "{S}".debt_instrument')
        obligors = cur.fetchone()[0]
    assert obligors >= 48, f"only {obligors} obligors carry debt"


def test_every_new_instrument_is_anchored_to_a_real_filing():
    """The bond is invented; the ISSUANCE EVENT must not be.

    Wave 11a's rule: `issue_date` is anchored to a real Item 2.03 8-K. An
    unanchored instrument asserts a financing event that never happened, which
    is a different and worse claim than 'this bond is synthetic'.
    """
    from ccf.config import PG_SCHEMA_V2 as S
    from ccf.config import pg_connect

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT COUNT(*) FROM "{S}".debt_instrument '
                    "WHERE instrument_id LIKE 'w16-i-%'")
        added = cur.fetchone()[0]
        cur.execute(f'SELECT COUNT(*) FROM "{S}".debt_instrument '
                    "WHERE instrument_id LIKE 'w16-i-%' "
                    "AND (anchored_to_real_filing IS NOT TRUE "
                    "     OR anchor_accession IS NULL)")
        unanchored = cur.fetchone()[0]
    assert added > 0, "no Wave 16 instruments were added"
    assert unanchored == 0, f"{unanchored} of {added} are unanchored"


def test_ineligible_obligors_were_not_given_debt():
    """Two anchors lack a LongTermDebt-family XBRL fact. Another product's
    registered condition requires every instrument-bearing obligor to have one,
    so giving these two a ladder would break that product, not this one."""
    from ccf.config import PG_SCHEMA_V2 as S
    from ccf.config import pg_connect

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f"""SELECT COUNT(*) FROM "{S}".debt_instrument d
                        JOIN "{S}".legal_entity e ON e.lei = d.lei
                        WHERE e.legal_name IN ('American Healthcare REIT, Inc.',
                                               'SMITH & WESSON BRANDS, INC.')""")
        bad = cur.fetchone()[0]
    assert bad == 0, f"{bad} instruments on obligors with no LongTermDebt fact"


def test_real_signal_dates_are_never_shifted():
    """A filing date is a public fact.

    Dating a real 13D into the demo window to make the window look full is
    fabrication, and it would be invisible: the count rises, the provenance
    still says `public`, and the date still looks like a date.
    """
    import json
    from pathlib import Path

    from generators.generate_opportunity_signals import build

    doc = build()
    filings = {f["accession"]: f["filing_date"] for f in json.loads(
        Path("sources/screening/wave16_13d.json").read_text())["filings"]}

    checked = 0
    for s in doc["signals"]:
        if s["signal_type"] == "activist_stake_13d" and s["source_ref"] in filings:
            assert s["observed_at"] == filings[s["source_ref"]], (
                f"{s['signal_id']} was re-dated: filing says "
                f"{filings[s['source_ref']]}, signal says {s['observed_at']}")
            checked += 1
    assert checked >= 5, f"only {checked} real 13D signals to check"


def test_synthetic_signals_stay_inside_the_window():
    """Real dates are honoured; SYNTHETIC ones are dated into the 12-month
    window SF describes, so the window is full without anything being moved."""
    from ccf.config import IB_WINDOW_END, IB_WINDOW_START
    from generators.generate_opportunity_signals import build

    doc = build()
    synthetic = [s for s in doc["signals"] if s["provenance"] != "public"]
    assert synthetic, "no synthetic signals at all"
    out = [s for s in synthetic
           if not IB_WINDOW_START <= s["observed_at"] <= IB_WINDOW_END]
    assert not out, f"{len(out)} synthetic signals outside the window: {out[:3]}"


def test_amendments_supersede_their_parent():
    """A SCHEDULE 13D/A supersedes the 13D it amends. SE names supersession as
    a trigger, and the estate's convention is supersession-not-overwrite."""
    from generators.generate_opportunity_signals import build

    doc = build()
    amendments = [s for s in doc["signals"] if s.get("supersedes")]
    assert amendments, "no amendment superseded anything"
    ids = {s["signal_id"] for s in doc["signals"]}
    dangling = [s["signal_id"] for s in amendments if s["supersedes"] not in ids]
    assert not dangling, f"supersedes points at nothing: {dangling[:3]}"


def test_superseded_signals_are_marked_not_current():
    """Fix round 1, finding 1. Recording `supersedes` is not enough -- a
    superseded assertion must stop contributing to a current-value ranking.

    `is_current` must genuinely discriminate (both True and False present,
    never stamped uniformly), and every signal some OTHER signal's
    `supersedes` names must itself be marked NOT current.
    """
    from generators.generate_opportunity_signals import build

    doc = build()
    signals = doc["signals"]
    flags = {s["is_current"] for s in signals}
    assert flags == {True, False}, f"is_current does not discriminate: {flags}"

    by_id = {s["signal_id"]: s for s in signals}
    referenced = {s["supersedes"] for s in signals if s.get("supersedes")}
    still_current = [sid for sid in referenced if by_id[sid]["is_current"]]
    assert not still_current, (
        f"{len(still_current)} superseded signal(s) still marked "
        f"is_current=True: {still_current[:5]}")


def test_signal_label_format_is_the_contract_both_readers_assume():
    """FINAL FIX WAVE, item 10. `"{signal_type} -- {lei} -- {observed_at}"`
    is an undeclared interface: one producer
    (`loaders/load_fluree_wave16.py`, the `ex:rdfs:label` literal on every
    `OpportunitySignal` node) and two consumers
    (`validators/conditions.py:1914`'s `STRSTARTS(?label, "activist_stake_13d
    -- ")` and `validators/spec_coverage.py:1016`'s `STRSTARTS(?label,
    "{signal_type} -- ")`), with nothing anywhere asserting the three parts
    are actually there in that order. A producer that reordered the parts,
    dropped a separator, or changed the delimiter would pass every existing
    check silently -- both consumers would just start matching nothing (or
    matching the wrong rows), which reads as "0 signals of this type", not
    as a format break.

    Two things pinned here, from the artifact itself (not from Fluree, so
    this runs without a live store):

    1. The producer's own label matches the 3-part `sig -- lei -- date`
       shape for every signal, split on the exact `" -- "` separator both
       consumers filter on.
    2. No `signal_type` value itself contains `" -- "` -- if one did, a
       `STRSTARTS` match on it would also match a DIFFERENT signal_type
       whose label happened to start with that same literal text, silently
       merging two signal types under one count.
    """
    import json

    from ccf.config import REPO_ROOT

    doc = json.loads(
        (REPO_ROOT / "sources" / "screening" / "wave16_signals.json").read_text())
    signals = doc["signals"]
    assert signals, "no signals to check the label format against"

    signal_types = {s["signal_type"] for s in signals}
    tainted = [t for t in signal_types if " -- " in t]
    assert not tainted, (
        f"signal_type value(s) containing the label separator itself, "
        f"which would break STRSTARTS-based matching: {tainted}")

    for s in signals:
        label = f"{s['signal_type']} -- {s['lei']} -- {s['observed_at']}"
        parts = label.split(" -- ")
        assert len(parts) == 3, (
            f"label {label!r} does not split into exactly 3 parts on "
            f"' -- ': {parts}")
        assert parts[0] == s["signal_type"]
        assert parts[1] == s["lei"]
        assert parts[2] == s["observed_at"]
        assert label.startswith(f"{s['signal_type']} -- "), (
            f"label does not start with the signal_type prefix both "
            f"conditions.py and spec_coverage.py filter on: {label!r}")


_AGGREGATED_SIGNAL_TYPES = ("insider_activity_form4", "sector_news_gdelt")


def test_aggregated_magnitude_is_normalised_globally_not_per_entity():
    """Fix round 2, finding 1a. The mechanism that took insider filings from
    41.5% to 5.2% of M&A score mass is a SINGLE max across the whole (lei,
    month) dict for a type, not a per-entity max. Under per-entity scaling
    every LEI's busiest month would itself be that LEI's max, so EVERY LEI
    would carry at least one magnitude-1.0 row -- the count of 1.0-magnitude
    rows would be >= the distinct-LEI count. Under the real global
    normalisation, only the single busiest entity-month in the whole type
    can hit 1.0, so that count must be far smaller than the LEI count.
    """
    from generators.generate_opportunity_signals import build

    doc = build()
    signals = doc["signals"]
    for st in _AGGREGATED_SIGNAL_TYPES:
        rows = [s for s in signals if s["signal_type"] == st]
        assert rows, f"no {st} rows at all"
        distinct_leis = {s["lei"] for s in rows}
        at_max = [s for s in rows if s["magnitude"] == 1.0]
        assert len(at_max) < len(distinct_leis), (
            f"{st}: {len(at_max)} row(s) at magnitude 1.0 across "
            f"{len(distinct_leis)} distinct LEIs -- per-entity normalisation "
            f"would give every LEI a 1.0, so this count should be far "
            f"smaller than the LEI count, not close to or above it")


def test_aggregated_magnitudes_genuinely_vary():
    """Fix round 2, finding 1b. A single distinct magnitude value across a
    whole aggregated type means normalisation collapsed (e.g. every bucket
    tied for the max, or the divisor stopped varying) and nothing
    differentiates entities on that signal any more."""
    from generators.generate_opportunity_signals import build

    doc = build()
    signals = doc["signals"]
    for st in _AGGREGATED_SIGNAL_TYPES:
        rows = [s for s in signals if s["signal_type"] == st]
        assert rows, f"no {st} rows at all"
        distinct_magnitudes = {s["magnitude"] for s in rows}
        assert len(distinct_magnitudes) > 1, (
            f"{st}: only one distinct magnitude value "
            f"({distinct_magnitudes}) across {len(rows)} rows")


def test_aggregated_dates_stay_inside_the_window():
    """Fix round 2, finding 1c. Every aggregated (lei, month) bucket's
    observed_at must be a real date no earlier than IB_WINDOW_START and no
    later than AS_OF_IB -- guarded against vacuity first, since "every date
    in an empty set is bounded" holds for free."""
    from ccf.config import AS_OF_IB, IB_WINDOW_START
    from generators.generate_opportunity_signals import build

    doc = build()
    signals = doc["signals"]
    for st in _AGGREGATED_SIGNAL_TYPES:
        rows = [s for s in signals if s["signal_type"] == st]
        assert rows, f"no {st} rows at all"
        out = [s for s in rows
               if not IB_WINDOW_START <= s["observed_at"] <= AS_OF_IB]
        assert not out, f"{st}: {len(out)} row(s) with observed_at outside " \
            f"[{IB_WINDOW_START}, {AS_OF_IB}]: {out[:3]}"


def test_aggregated_asserted_at_is_as_of_not_the_bucket_date():
    """Fix round 2, finding 2. insider_activity_form4 and sector_news_gdelt
    are monthly AGGREGATES this generator computed at load time, not single
    filed documents -- nobody asserted a (lei, month) bucket on the date of
    its newest member. observed_at (valid time) stays the real latest date
    in the bucket; asserted_at (assertion time) must be AS_OF_IB.

    Per-event discrete catalysts are the opposite case and must NOT collapse
    to AS_OF_IB -- they were genuinely asserted when filed.
    """
    from ccf.config import AS_OF_IB
    from generators.generate_opportunity_signals import build

    doc = build()
    signals = doc["signals"]

    for st in _AGGREGATED_SIGNAL_TYPES:
        rows = [s for s in signals if s["signal_type"] == st]
        assert rows, f"no {st} rows at all"
        wrong = [s for s in rows if s["asserted_at"] != AS_OF_IB]
        assert not wrong, f"{st}: {len(wrong)} row(s) with asserted_at != " \
            f"AS_OF_IB: {wrong[:3]}"

    for st in ("activist_stake_13d", "ma_event_8k", "merger_proxy", "registration_s4"):
        rows = [s for s in signals if s["signal_type"] == st]
        assert rows, f"no {st} rows at all"
        mismatched = [s for s in rows if s["asserted_at"] != s["observed_at"]]
        assert not mismatched, f"{st}: {len(mismatched)} row(s) where " \
            f"asserted_at != observed_at -- discrete catalysts are asserted " \
            f"when filed: {mismatched[:3]}"


def test_mandates_are_dated_inside_the_window_and_attach_to_covered_entities():
    """Mandates are synthetic, so they are dated INTO the 12-month window --
    unlike real filings, whose dates are public facts and are never shifted.

    They attach only to entities somebody covers. A mandate against an
    uncovered entity asserts a client relationship the bank does not have,
    which is a worse defect than a thin pipeline: it would join cleanly and
    be wrong.
    """
    from ccf.config import IB_WINDOW_END, IB_WINDOW_START, pg_connect
    from ccf.config import PG_SCHEMA_V2 as S
    from generators.generate_ib_mandates import build

    doc = build()
    mandates = doc["mandates"]
    assert len(mandates) >= 30, f"only {len(mandates)} mandates"

    out = [m for m in mandates
           if not IB_WINDOW_START <= m["opened_date"] <= IB_WINDOW_END]
    assert not out, f"{len(out)} mandates outside the window: {out[:3]}"

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT DISTINCT lei FROM "{S}".coverage_assignment')
        covered = {r[0] for r in cur.fetchall()}
    orphans = sorted({m["lei"] for m in mandates} - covered)
    assert not orphans, f"mandates against uncovered entities: {orphans[:5]}"

    assert all(m["provenance"] == "synthetic — internal" for m in mandates)


def test_mandate_generation_is_reproducible():
    """A seeded generator, so a rerun produces byte-identical output.

    Idempotency proved by naming a VALUE, not a count: two runs must agree on
    a specific mandate's stage and date, not merely on how many there are.
    """
    from generators.generate_ib_mandates import build

    first, second = build(), build()
    assert first == second, "generation is not reproducible across calls"
    probe = sorted(first["mandates"], key=lambda m: m["mandate_id"])[0]
    assert probe["mandate_id"] and probe["stage"] and probe["opened_date"]


# --- Task 11: the Postgres load ---------------------------------------------
#
# `loaders/load_postgres_wave16.py` owns six tables: ib_perspective,
# ib_signal_class, perspective_weight, mandate, gov_contract_concentration,
# and ib_projection_plan -- a table of its own (Fix Round 1). It never writes
# a row into the pre-existing projection_plan table (that belongs to Wave 7's
# mnpi-wall-enforcement); debt_instrument and spread_observation belong to
# Task 8b. Neither is ever touched here -- the first test below is the
# regression guard for that boundary.

def test_loader_never_writes_debt_instrument_or_spread_observation():
    """Scope guard. Task 8b already loaded 36 `w16-i-` instruments and 17,964
    spread observations; this loader must not re-load or touch either table.
    The module docstring names both tables (to document the scope
    correction), so this checks the executable body -- the DDL and every SQL
    string passed to cur.execute/executemany -- with the docstring stripped,
    not the raw source text."""
    import ast
    from pathlib import Path

    src = Path("loaders/load_postgres_wave16.py").read_text()
    tree = ast.parse(src)
    # Drop the module docstring (a plain ast.Expr(ast.Constant(str)) as the
    # first statement) before scanning constants -- that is where the scope
    # note naming both tables legitimately lives.
    body = tree.body[1:] if (tree.body and isinstance(tree.body[0], ast.Expr)
                              and isinstance(tree.body[0].value, ast.Constant)
                              and isinstance(tree.body[0].value.value, str)) \
        else tree.body
    code_without_docstring = ast.unparse(ast.Module(body=body, type_ignores=[]))

    assert "debt_instrument" not in code_without_docstring
    assert "spread_observation" not in code_without_docstring


def test_task11_tables_hold_the_counted_rows():
    """Per-table row counts, recomputed from Postgres -- not read off a
    printed summary. Counts match the artifacts on disk: 3 perspectives, 11
    signal classes, 66 weight rows (3 perspectives x 11 signals x 2
    versions), 3 projection plans, 40 mandates, 104 USASpending awards."""
    from ccf.config import PG_SCHEMA_V2 as S
    from ccf.config import pg_connect

    with pg_connect() as conn, conn.cursor() as cur:
        counts = {}
        for table in ("ib_perspective", "ib_signal_class",
                      "perspective_weight", "ib_projection_plan", "mandate",
                      "gov_contract_concentration"):
            cur.execute(f'SELECT COUNT(*) FROM "{S}".{table}')
            counts[table] = cur.fetchone()[0]

    assert counts == {
        "ib_perspective": 3,
        "ib_signal_class": 11,
        "perspective_weight": 66,
        "ib_projection_plan": 3,
        "mandate": 40,
        "gov_contract_concentration": 104,
    }, counts


def test_perspective_weight_natural_key_is_not_a_surrogate():
    """The ON CONFLICT target must be the natural key
    (perspective_id, signal_type, weight_version), never a row position or a
    generated id column. Read the constraint back from Postgres itself,
    rather than trusting the DDL text, so a future ALTER that quietly adds a
    surrogate PK is caught here."""
    from ccf.config import PG_SCHEMA_V2 as S
    from ccf.config import pg_connect

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT string_agg(kcu.column_name, ',' ORDER BY kcu.ordinal_position)
                 FROM information_schema.table_constraints tc
                 JOIN information_schema.key_column_usage kcu
                   ON tc.constraint_name = kcu.constraint_name
                  AND tc.table_schema = kcu.table_schema
                WHERE tc.table_schema = %s AND tc.table_name = 'perspective_weight'
                  AND tc.constraint_type = 'PRIMARY KEY'""",
            (S,),
        )
        (pk,) = cur.fetchone()

    assert pk == "perspective_id,signal_type,weight_version"


def test_gov_contract_concentration_match_band_is_only_the_two_admitted_values():
    """The CHECK constraint admits only 'exact' and 'verified-subsidiary'.
    If a third value ever appears in the artifact, the loader refuses to
    load rather than widening the constraint -- this test recomputes the
    actual set in the store, so a future load that slipped a bad value past
    the loader's own guard would still be caught here."""
    from ccf.config import PG_SCHEMA_V2 as S
    from ccf.config import pg_connect

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(
            f'SELECT DISTINCT match_band FROM "{S}".gov_contract_concentration'
        )
        bands = {r[0] for r in cur.fetchall()}

    assert bands and bands <= {"exact", "verified-subsidiary"}, bands


def test_perspective_weight_and_ib_projection_plan_signal_types_resolve_to_a_signal_class():
    """Correlation-key check: every signal_type referenced by a weight row or
    a projection plan's permitted list must actually exist in
    ib_signal_class. A typo'd signal_type in perspective_weight is caught by
    the FK itself, but permitted_signal_types is a JSONB list with no FK --
    this is the only thing that would catch a stray entry there."""
    from ccf.config import PG_SCHEMA_V2 as S
    from ccf.config import pg_connect

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT signal_type FROM "{S}".ib_signal_class')
        known = {r[0] for r in cur.fetchall()}

        cur.execute(
            f'SELECT projection_plan_id, permitted_signal_types '
            f'FROM "{S}".ib_projection_plan'
        )
        plans = cur.fetchall()

    assert plans, "no ib_projection_plan rows found"
    for plan_id, permitted in plans:
        unknown = sorted(set(permitted) - known)
        assert not unknown, f"{plan_id}: unknown signal types {unknown}"


def test_ib_projection_plan_is_a_table_of_its_own_not_a_squat_in_projection_plan():
    """Fix Round 1. The first cut of this loader put Wave 16's plans inside
    Wave 7's `projection_plan` table by relaxing its NOT NULL constraints --
    reverted by controller ruling because it broke "every projection plan
    belongs to a principal" for every future reader of that table. This test
    is the regression guard for the reverted behaviour: the three PP-IB-*
    ids must exist in ib_projection_plan and must NOT exist in
    projection_plan, in either direction."""
    from ccf.config import PG_SCHEMA_V2 as S
    from ccf.config import pg_connect

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(
            f'SELECT projection_plan_id FROM "{S}".ib_projection_plan'
        )
        ib_ids = {r[0] for r in cur.fetchall()}

        cur.execute(
            f'SELECT projection_plan_id FROM "{S}".projection_plan '
            "WHERE projection_plan_id LIKE 'PP-IB-%%'"
        )
        leaked = [r[0] for r in cur.fetchall()]

    assert ib_ids == {"PP-IB-MA-v1", "PP-IB-DCM-v1", "PP-IB-SECTOR-v1"}
    assert not leaked, f"PP-IB-* row(s) still in projection_plan: {leaked}"


def test_projection_plan_restored_to_wave7s_original_shape():
    """`projection_plan` belongs to Wave 7 (mnpi-wall-enforcement). After
    Fix Round 1 the loader must leave it exactly as it found it: 3 rows,
    7 columns (the two Fix-Round-1-added columns dropped again), NOT NULL
    restored on principal_id and the three permitted_* columns, and Wave 7's
    own row carrying its original principal_id and permitted_edge_types --
    a named value, not a count, since a count cannot see a column silently
    blanked and restored to a same-looking NULL."""
    from ccf.config import PG_SCHEMA_V2 as S
    from ccf.config import pg_connect

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT COUNT(*) FROM "{S}".projection_plan')
        (row_count,) = cur.fetchone()

        cur.execute(
            "SELECT column_name, is_nullable FROM information_schema.columns "
            "WHERE table_schema = %s AND table_name = 'projection_plan'",
            (S,),
        )
        columns = dict(cur.fetchall())

        cur.execute(
            f"""SELECT principal_id, permitted_edge_types
                  FROM "{S}".projection_plan
                 WHERE projection_plan_id = 'PLAN-coverage-banker-v1'"""
        )
        row = cur.fetchone()

    assert row_count == 3, f"expected 3 rows, found {row_count}"
    assert set(columns) == {
        "projection_plan_id", "principal_id", "plan_version",
        "permitted_edge_types", "permitted_classifications",
        "permitted_document_types", "provenance",
    }, columns
    for not_null_col in ("principal_id", "permitted_edge_types",
                          "permitted_classifications",
                          "permitted_document_types"):
        assert columns[not_null_col] == "NO", \
            f"{not_null_col} is nullable, expected NOT NULL restored"

    assert row is not None, "Wave 7's PLAN-coverage-banker-v1 row is gone"
    assert row[0] == "PRIN-COV-001"
    assert row[1] == ["owns", "controls", "hasDealEngagement",
                       "hasInteraction", "hasMnpiEngagement"]


def test_ib_signal_class_provenance_is_backfilled_and_uniform():
    """`wave16_perspectives.json`'s signal_classes carry no `provenance`
    field (a gap in generate_ib_perspectives.py -- see the loader's module
    docstring, Finding 1). The loader backfills it rather than leaving the
    column NULL; this asserts every row actually got a value, and that it is
    the honest label for hand-chosen decay parameters, not a fetched fact."""
    from ccf.config import PG_SCHEMA_V2 as S
    from ccf.config import pg_connect

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT DISTINCT provenance FROM "{S}".ib_signal_class')
        provenances = {r[0] for r in cur.fetchall()}

    assert provenances == {"synthetic — internal"}


def test_task11_load_is_idempotent_on_a_named_weight_value():
    """Re-run the loader and confirm one specific weight + rationale survive
    unchanged -- the brief's own idempotency proof, made a regression test
    rather than a one-off manual check. A row count cannot see `rationale`
    silently blanked; this reads the actual value."""
    import subprocess

    result = subprocess.run(
        ["uv", "run", "loaders/load_postgres_wave16.py"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    from ccf.config import PG_SCHEMA_V2 as S
    from ccf.config import pg_connect

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(
            f"""SELECT weight, rationale FROM "{S}".perspective_weight
                 WHERE perspective_id = 'PSP-MA'
                   AND signal_type = 'activist_stake_13d'
                   AND weight_version = 'v1'"""
        )
        weight, rationale = cur.fetchone()

    assert float(weight) == 0.45
    assert rationale == "pre-2026 policy: activist stakes under-weighted"


def test_fluree_wave16_dates_are_plain_strings():
    """Fluree 4.1.4 corrupts xsd:date literals on write: 2026-01-02 reads back
    as 1972-01-01 (known-issues 19.4). The obvious 'improvement' to this loader
    is to give dates a proper type, which would silently destroy every date it
    touched -- triple count unchanged, predicate unchanged, value still shaped
    like a date."""
    from pathlib import Path

    src = Path("loaders/load_fluree_wave16.py").read_text()
    assert "xsd:date" not in src, "typed date literals corrupt silently in Fluree 4.1.4"
    assert "^^" not in src, "no typed literals at all on this ledger"



def test_comparable_to_and_basis_counts_match():
    """Fix round 1, Finding 3. Every ex:comparableTo edge must carry its own
    ex:comparabilityBasis -- three edges shipped with no stated grounds in
    the first cut, which is exactly the 'comparable' silently going
    unexplained CLAUDE.md rule 5's spirit warns against. Recomputed live
    against the loaded ledger, not read from a cached count: a query for
    each predicate's cardinality, asserted equal. Guarded against vacuity --
    an empty ledger would satisfy "0 == 0" for free."""
    from ccf.config import EX, FLUREE_LEDGER_V2
    from ccf import fluree

    def count(predicate: str) -> int:
        q = (f"SELECT (COUNT(*) AS ?n) FROM <{FLUREE_LEDGER_V2}> "
             f"WHERE {{ ?s <{EX}{predicate}> ?o }}")
        rows = fluree.query(q)["results"]["bindings"]
        return int(rows[0]["n"]["value"]) if rows else 0

    comparable_to = count("comparableTo")
    comparability_basis = count("comparabilityBasis")

    assert comparable_to > 0, "no comparableTo edges loaded at all"
    assert comparable_to == comparability_basis, (
        f"comparableTo={comparable_to} != comparabilityBasis={comparability_basis} "
        "-- every comparableTo edge must carry a basis, no more and no fewer")


# --- Task 13: MongoDB merger corpus + SQLite departmental notes -------------

def test_at_least_five_notes_are_rank_changing_by_construction():
    """SF: ~50 notes, >= 5 of which CHANGE A RANKING when included.

    Counting 50 notes proves nothing about the five. This checks the
    generator's own claim; `validators/ib_rank.py` proves the effect by
    ranking twice and diffing the order.
    """
    import sqlite3

    from ccf.config import REPO_ROOT

    con = sqlite3.connect(REPO_ROOT / "data" / "departmental.sqlite")
    total = con.execute("SELECT COUNT(*) FROM prospect_note").fetchone()[0]
    flagged = con.execute(
        "SELECT COUNT(*) FROM prospect_note WHERE rank_changing = 1"
    ).fetchone()[0]
    assert total >= 50, f"only {total} notes"
    assert flagged >= 5, f"only {flagged} notes marked rank-changing"


def test_rank_changing_notes_are_high_materiality_banker_local_notes():
    """The claim only has a chance of being true if the flagged rows are
    actually the kind of signal that can move a score: high materiality,
    and the same signal_type the perspective weight vectors already know
    about (`banker_local_note` -- see generate_ib_perspectives.WEIGHTS_V2).
    A rank_changing row with low materiality or an unrecognised signal_type
    would be a claim the ranking engine has no mechanism to honour."""
    import sqlite3

    from ccf.config import REPO_ROOT

    con = sqlite3.connect(REPO_ROOT / "data" / "departmental.sqlite")
    rows = con.execute(
        "SELECT note_id, materiality, signal_type FROM prospect_note "
        "WHERE rank_changing = 1"
    ).fetchall()
    assert rows, "no rank_changing rows to check"
    for note_id, materiality, signal_type in rows:
        assert materiality == "high", f"{note_id}: materiality={materiality!r}"
        assert signal_type == "banker_local_note", \
            f"{note_id}: signal_type={signal_type!r}"


def test_prospect_note_load_is_idempotent_on_a_named_value():
    """Re-run the loader and confirm a specific row's materiality survives
    unchanged and the table does not grow -- a row count alone would miss a
    loader that keeps finding "new" boundary candidates on every run."""
    import sqlite3
    import subprocess

    from ccf.config import REPO_ROOT

    con = sqlite3.connect(REPO_ROOT / "data" / "departmental.sqlite")
    before_total = con.execute("SELECT COUNT(*) FROM prospect_note").fetchone()[0]
    before_flagged = con.execute(
        "SELECT COUNT(*) FROM prospect_note WHERE rank_changing = 1"
    ).fetchone()[0]
    probe_id, probe_materiality = con.execute(
        "SELECT note_id, materiality FROM prospect_note "
        "WHERE rank_changing = 1 ORDER BY note_id LIMIT 1"
    ).fetchone()
    con.close()

    result = subprocess.run(
        ["uv", "run", "loaders/load_sqlite_wave16.py"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    con = sqlite3.connect(REPO_ROOT / "data" / "departmental.sqlite")
    after_total = con.execute("SELECT COUNT(*) FROM prospect_note").fetchone()[0]
    after_flagged = con.execute(
        "SELECT COUNT(*) FROM prospect_note WHERE rank_changing = 1"
    ).fetchone()[0]
    after_materiality = con.execute(
        "SELECT materiality FROM prospect_note WHERE note_id = ?", (probe_id,)
    ).fetchone()[0]

    assert after_total == before_total, \
        f"a rerun grew the table: {before_total} -> {after_total}"
    assert after_flagged == before_flagged, \
        f"a rerun changed the flagged count: {before_flagged} -> {after_flagged}"
    assert after_materiality == probe_materiality == "high"


def test_every_new_prospect_note_lei_is_in_its_banker_coverage():
    """A note from a banker who does not cover that prospect asserts a
    coverage relationship the bank does not have -- worse than a thin
    workbook, because it would join cleanly and be wrong. Checked against
    Postgres `coverage_assignment` directly, not against the loader's own
    selection logic."""
    import sqlite3

    from ccf.config import PG_SCHEMA_V2 as S
    from ccf.config import REPO_ROOT, pg_connect

    con = sqlite3.connect(REPO_ROOT / "data" / "departmental.sqlite")
    notes = con.execute(
        "SELECT note_id, banker_id, lei FROM prospect_note "
        "WHERE banker_id IS NOT NULL"
    ).fetchall()
    assert notes, "no notes with a banker_id"

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT banker_id, lei FROM "{S}".coverage_assignment')
        covers = set(cur.fetchall())

    uncovered = [(n, b, l) for n, b, l in notes if (b, l) not in covers]
    assert not uncovered, \
        f"{len(uncovered)} note(s) reference a (banker, lei) pair not in " \
        f"coverage_assignment: {uncovered[:5]}"


def test_merger_corpus_documents_carry_doc_type_and_the_178_gap_is_untouched():
    """This loader's own 15 documents must carry `doc_type`; the 178
    pre-existing rows (a gap belonging to earlier waves, see
    docs/known-issues.md) must be left exactly as found -- back-filling them
    here would be a silent rewrite of another wave's data disguised as a
    fix."""
    from ccf.config import mongo_db

    db = mongo_db()
    new_docs = list(db["document"].find(
        {"doc_type": {"$in": ["merger_proxy", "registration_s4"]}},
        {"_id": 1, "doc_type": 1, "form": 1},
    ))
    assert len(new_docs) == 15, f"expected 15 new documents, found {len(new_docs)}"
    for d in new_docs:
        assert d["doc_type"] in ("merger_proxy", "registration_s4")

    pre_existing_gap = db["document"].count_documents({"doc_type": None})
    assert pre_existing_gap == 178, \
        f"expected the pre-existing 178-doc gap untouched, found {pre_existing_gap}"


def test_merger_corpus_passages_resolve_by_offset():
    """A span whose offsets do not resolve is worse than no span -- it looks
    like evidence and is not. This re-derives the passage body from
    `document.text[start_offset:end_offset]` and checks it against both the
    stored `text` field and `sha256`, for every passage of one full document,
    not just a hand-picked example."""
    import hashlib

    from ccf.config import mongo_db

    db = mongo_db()
    doc = db["document"].find_one({"doc_type": "merger_proxy"})
    assert doc, "no merger_proxy document loaded"
    full_text = doc["text"]

    passages = list(db["passage"].find({"document_id": doc["_id"]}))
    assert passages, f"no passages for {doc['_id']}"

    for p in passages:
        span = full_text[p["start_offset"]:p["end_offset"]]
        assert span == p["text"], f"{p['_id']}: offsets do not resolve to stored text"
        assert hashlib.sha256(span.encode("utf-8")).hexdigest() == p["sha256"], \
            f"{p['_id']}: passageSha256 does not match the exact span"


def test_merger_corpus_load_is_idempotent_on_a_named_passage():
    """Re-run the Mongo loader and confirm collection sizes and one named
    passage's sha256 survive unchanged -- counts alone cannot see a passage
    silently re-hashed to a different span under the same id."""
    import subprocess

    from ccf.config import mongo_db

    db = mongo_db()
    before_docs = db["document"].count_documents({})
    before_passages = db["passage"].count_documents({})
    probe = db["passage"].find_one(
        {"document_id": {"$regex": "^0001140361-25-024665"}})
    assert probe is not None
    probe_id, probe_sha = probe["_id"], probe["sha256"]

    result = subprocess.run(
        ["uv", "run", "loaders/load_mongo_wave16.py"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    after_docs = db["document"].count_documents({})
    after_passages = db["passage"].count_documents({})
    after_probe = db["passage"].find_one({"_id": probe_id})

    assert after_docs == before_docs, f"{before_docs} -> {after_docs}"
    assert after_passages == before_passages, f"{before_passages} -> {after_passages}"
    assert after_probe["sha256"] == probe_sha


# --- Task 14: the ranking instrument ----------------------------------------
#
# ccf/ib_rank.py is pure arithmetic, no I/O. validators/ib_rank.py does the
# reading and proves the four SF conditions against the loaded stores. Every
# checker below is tested in BOTH directions -- fed a known-absent input it
# must FAIL, fed a known-present input it must PASS -- because a checker that
# only ever says one thing is decoration, and this estate has already lost
# seven waves each to two of those.

def test_decay_halves_at_one_half_life():
    from ccf.ib_rank import decay

    assert decay(age_days=0, half_life_days=30) == 1.0
    assert abs(decay(age_days=30, half_life_days=30) - 0.5) < 1e-9
    assert abs(decay(age_days=60, half_life_days=30) - 0.25) < 1e-9


def test_ranking_is_deterministic_under_ties():
    """Two entities with identical scores must always order the same way, or
    a replay diff reports a change that is really just dict iteration."""
    from ccf.ib_rank import rank

    assert rank({"BBB": 1.0, "AAA": 1.0}) == [("AAA", 1.0), ("BBB", 1.0)]


def test_future_dated_signals_are_rejected_not_capped():
    """`decay()` clamps negative age to 1.0, which is a CAP, not a FILTER.

    A signal dated after the as-of instant would therefore score the maximum
    possible weight and dominate the ranking. The clamp is right -- it stops
    clock skew amplifying a signal past 1.0 -- but the scorer must refuse
    future-dated input rather than silently scoring it at full strength.
    """
    import pytest

    from ccf.ib_rank import score

    with pytest.raises(ValueError, match="after as_of"):
        score(signals=[{"lei": "X", "signal_type": "k",
                        "observed_at": "2026-09-01", "magnitude": 1.0}],
              weights={"k": 1.0}, half_lives={"k": 30}, as_of="2026-08-24")


def test_score_ignores_signal_types_absent_from_the_weight_vector():
    """A signal type with no weight row must contribute ZERO and be reported,
    not silently treated as weight 1.0."""
    from ccf.ib_rank import score

    out = score(
        signals=[{"lei": "X", "signal_type": "unweighted", "observed_at": "2026-08-24",
                  "magnitude": 1.0}],
        weights={"known": 1.0}, half_lives={"known": 30, "unweighted": 30},
        as_of="2026-08-24")
    assert out["X"] == 0.0


def test_divergence_check_can_actually_fail():
    """A check that cannot fail is decoration. Two checks in this estate hid
    for seven waves each because nobody fed them a known-absent input.

    Feed the divergence check a signal set where M&A and DCM agree perfectly,
    and require it to report FAILURE.
    """
    from validators.ib_rank import divergence_holds

    agreeing = [
        {"lei": f"E{i:03d}", "signal_type": "activist_stake_13d",
         "observed_at": "2026-08-24", "magnitude": 1.0 - i / 100}
        for i in range(30)
    ]
    identical = {"activist_stake_13d": 1.0}
    half = {"activist_stake_13d": 30}

    assert not divergence_holds(
        signals=agreeing, ma_weights=identical, dcm_weights=identical,
        half_lives=half, as_of="2026-08-24"), \
        "identical weights cannot produce a divergent ranking"


def test_divergence_check_passes_on_a_known_divergent_set():
    """The other half. A checker that always says FAIL is equally useless."""
    from validators.ib_rank import divergence_holds

    signals = [
        {"lei": "DIVERGENT", "signal_type": "activist_stake_13d",
         "observed_at": "2026-08-24", "magnitude": 1.0},
    ] + [
        {"lei": f"E{i:03d}", "signal_type": "maturity_wall",
         "observed_at": "2026-08-24", "magnitude": 1.0 - i / 100}
        for i in range(30)
    ]
    assert divergence_holds(
        signals=signals,
        ma_weights={"activist_stake_13d": 1.0, "maturity_wall": 0.05},
        dcm_weights={"activist_stake_13d": 0.10, "maturity_wall": 1.0},
        half_lives={"activist_stake_13d": 30, "maturity_wall": 90},
        as_of="2026-08-24")


def test_containment_check_can_actually_fail():
    """A builder that forgets to apply the wall must be CAUGHT, not waved
    through -- otherwise the check is only ever testing its own arithmetic,
    never the property it claims to verify."""
    from validators.ib_rank import containment_holds

    def forgets_to_filter(leis, restricted):
        return {"candidates": list(leis)}  # the wall is never applied

    coverage = [("BKR-X", "RESTRICTED-1"), ("BKR-X", "OK-1")]
    restricted = {"RESTRICTED-1"}

    affected, exercised, violations = containment_holds(
        coverage, restricted, build_fn=forgets_to_filter)
    assert affected == 1
    assert violations, "an unfiltered candidate set must be reported as a violation"
    assert any("leaked" in why for _, why, _ in violations)
    assert not exercised, "a leaked LEI was never confirmed absent"


def test_containment_check_catches_a_marker_naming_the_suppressed_lei():
    """The absence of a marker is PART of the condition, not a nicety -- a
    suppressed row with a marker tells the banker exactly what the wall
    exists to hide."""
    from validators.ib_rank import build_candidate_set, containment_holds

    def leaks_a_marker(leis, restricted):
        cand = build_candidate_set(leis, restricted)
        cand["suppressed"] = sorted(set(leis) & restricted)
        return cand

    coverage = [("BKR-X", "RESTRICTED-1"), ("BKR-X", "OK-1")]
    restricted = {"RESTRICTED-1"}

    affected, exercised, violations = containment_holds(
        coverage, restricted, build_fn=leaks_a_marker)
    assert affected == 1
    assert any("marker" in why for _, why, _ in violations)


def test_containment_check_catches_a_marker_nested_inside_candidates():
    """FIX ROUND 1, minor 2. A flat `set(cand) - {"candidates"}` check only
    ever looks at TOP-LEVEL keys, so a marker embedded inside a candidate
    entry -- not at the top level -- would pass it. This builder's only
    top-level key is 'candidates'; the marker is two levels down."""
    from validators.ib_rank import containment_holds

    def buries_a_marker(leis, restricted):
        hit = sorted(set(leis) & restricted)
        return {"candidates": [l for l in leis if l not in restricted]
                 + [{"suppressed_because": hit}]}

    coverage = [("BKR-X", "RESTRICTED-1"), ("BKR-X", "OK-1")]
    restricted = {"RESTRICTED-1"}

    affected, exercised, violations = containment_holds(
        coverage, restricted, build_fn=buries_a_marker)
    assert affected == 1
    assert violations, "a nested marker must be caught, not just a top-level one"
    assert any("marker" in why for _, why, _ in violations)


def test_containment_check_passes_when_the_wall_is_correctly_applied():
    """The other half: the real builder, correctly applied, must pass clean,
    and the restricted LEI must be counted as EXERCISED (present in raw
    coverage, confirmed absent from the built candidate set) -- the unit
    §F's floor actually names."""
    from validators.ib_rank import containment_holds

    coverage = [("BKR-X", "RESTRICTED-1"), ("BKR-X", "OK-1"),
                ("BKR-Y", "OK-2")]
    restricted = {"RESTRICTED-1"}

    affected, exercised, violations = containment_holds(coverage, restricted)
    assert affected == 1, "only BKR-X's coverage includes a restricted LEI"
    assert exercised == {"RESTRICTED-1"}
    assert not violations


def test_containment_floor_is_distinct_restricted_leis_not_bankers():
    """§F: '>= 2 prospects ... absent from the affected principals'
    candidate sets'. The unit is restricted LEIs, not bankers -- a single
    restricted LEI covered by many bankers must not inflate the count."""
    from validators.ib_rank import containment_holds

    coverage = [("BKR-A", "RESTRICTED-1"), ("BKR-A", "OK-1"),
                ("BKR-B", "RESTRICTED-1"), ("BKR-B", "OK-2"),
                ("BKR-C", "RESTRICTED-1"), ("BKR-C", "OK-3")]
    restricted = {"RESTRICTED-1"}

    affected, exercised, violations = containment_holds(coverage, restricted)
    assert affected == 3, "three bankers share coverage of the one restricted LEI"
    assert exercised == {"RESTRICTED-1"}, \
        "one restricted LEI, no matter how many bankers share it, is one LEI"
    assert not violations


def test_note_materiality_check_can_actually_fail():
    """No note signals added at all -> zero rank positions change."""
    from validators.ib_rank import rank_changed_positions

    candidates = ["A", "B"]
    base_signals = [
        {"lei": "A", "signal_type": "maturity_wall", "observed_at": "2026-08-24",
         "magnitude": 1.0},
        {"lei": "B", "signal_type": "maturity_wall", "observed_at": "2026-08-24",
         "magnitude": 0.5},
    ]
    weights = {"maturity_wall": 1.0, "banker_local_note": 0.6}
    half_lives = {"maturity_wall": 90, "banker_local_note": 60}

    changed = rank_changed_positions(candidates, base_signals, [], weights,
                                      half_lives, "2026-08-24")
    assert not changed, "with no note signals the ranking cannot move"


def test_note_materiality_check_passes_on_a_flipping_note():
    """The other half: a high-weight note on the trailing candidate flips the
    order, and BOTH LEIs' positions must be reported as changed."""
    from validators.ib_rank import rank_changed_positions

    candidates = ["A", "B"]
    base_signals = [
        {"lei": "A", "signal_type": "maturity_wall", "observed_at": "2026-08-24",
         "magnitude": 1.0},
        {"lei": "B", "signal_type": "maturity_wall", "observed_at": "2026-08-24",
         "magnitude": 0.5},
    ]
    note_signals = [
        {"lei": "B", "signal_type": "banker_local_note", "observed_at": "2026-08-24",
         "magnitude": 1.0},
    ]
    weights = {"maturity_wall": 1.0, "banker_local_note": 0.6}
    half_lives = {"maturity_wall": 90, "banker_local_note": 60}

    changed = rank_changed_positions(candidates, base_signals, note_signals,
                                      weights, half_lives, "2026-08-24")
    assert changed == {"A", "B"}, "B overtakes A, so both positions changed"


def test_note_materiality_counts_credits_one_note_once():
    """FIX ROUND 1, finding 2. §F's unit is NOTES, not (banker, LEI)
    position changes. A single note strong enough to vault its entity past
    several others must be credited as ONE note -- not one per entity it
    passed -- while `changed_pairs` (the informative figure) legitimately
    shows every position that moved."""
    from validators.ib_rank import note_materiality_counts

    # E's note vaults it from last to first, passing A, B, C, D -- five
    # position changes (E + the four it passed) from a single note.
    base_signals = [
        {"lei": lei, "signal_type": "maturity_wall", "observed_at": "2026-08-24",
         "magnitude": m}
        for lei, m in [("A", 0.9), ("B", 0.7), ("C", 0.5), ("D", 0.3), ("E", 0.1)]
    ]
    notes = [("PN-0001", "BKR-X", "E", "2026-08-20")]
    coverage = [("BKR-X", lei) for lei in ("A", "B", "C", "D", "E")]
    desks = {"BKR-X": "M&A Advisory"}
    weight_vectors = {"PSP-MA": {"maturity_wall": 1.0, "banker_local_note": 5.0}}
    half_lives = {"maturity_wall": 90, "banker_local_note": 60}

    own_entity, changed_pairs = note_materiality_counts(
        notes, coverage, desks, weight_vectors, base_signals, half_lives,
        "2026-08-24")

    assert own_entity == ["PN-0001"], \
        f"one note must be credited once, got {own_entity}"
    assert len(changed_pairs) == 5, \
        f"the informative figure should still show all 5 displaced entities, got {changed_pairs}"


def test_note_materiality_counts_excludes_a_note_that_never_moves_its_entity():
    """The other half: a note whose entity was already on top (or otherwise
    never crosses anyone) must NOT be credited, even though it is a real
    note with a real (if ineffective) signal."""
    from validators.ib_rank import note_materiality_counts

    base_signals = [
        {"lei": lei, "signal_type": "maturity_wall", "observed_at": "2026-08-24",
         "magnitude": m}
        for lei, m in [("A", 0.9), ("B", 0.1)]
    ]
    # A tiny note on the ALREADY-first entity cannot change its rank.
    notes = [("PN-0002", "BKR-X", "A", "2026-08-20")]
    coverage = [("BKR-X", "A"), ("BKR-X", "B")]
    desks = {"BKR-X": "M&A Advisory"}
    weight_vectors = {"PSP-MA": {"maturity_wall": 1.0, "banker_local_note": 0.01}}
    half_lives = {"maturity_wall": 90, "banker_local_note": 60}

    own_entity, changed_pairs = note_materiality_counts(
        notes, coverage, desks, weight_vectors, base_signals, half_lives,
        "2026-08-24")

    assert own_entity == [], f"a note that cannot cross anyone must not count: {own_entity}"
    assert changed_pairs == []


def test_weight_replay_check_can_actually_fail():
    """Identical weight vectors at the same as_of cannot reorder anything --
    a replay that "differs" here would be a bug in the replay, not a finding."""
    from validators.ib_rank import weight_replay_differs

    signals = [
        {"lei": "A", "signal_type": "maturity_wall", "observed_at": "2026-08-24",
         "magnitude": 1.0},
        {"lei": "B", "signal_type": "maturity_wall", "observed_at": "2026-08-20",
         "magnitude": 0.9},
    ]
    weights = {"maturity_wall": 1.0}
    half_lives = {"maturity_wall": 90}

    assert not weight_replay_differs(["A", "B"], signals, weights, weights,
                                      half_lives, "2026-08-24")


def test_weight_replay_check_passes_on_known_differing_versions():
    """The other half: a weight change strong enough to flip the order must
    be detected, with as_of held fixed."""
    from validators.ib_rank import weight_replay_differs

    signals = [
        {"lei": "A", "signal_type": "activist_stake_13d", "observed_at": "2026-08-24",
         "magnitude": 1.0},
        {"lei": "B", "signal_type": "maturity_wall", "observed_at": "2026-08-24",
         "magnitude": 1.0},
    ]
    half_lives = {"activist_stake_13d": 30, "maturity_wall": 90}
    v1 = {"activist_stake_13d": 0.10, "maturity_wall": 1.0}   # B on top
    v2 = {"activist_stake_13d": 1.00, "maturity_wall": 0.10}  # A on top

    assert weight_replay_differs(["A", "B"], signals, v1, v2, half_lives,
                                  "2026-08-24")


def test_ib_rank_validator_passes_end_to_end():
    """The full validator, run against the loaded stores. This is the actual
    regression suite for the wave's central demonstration -- if any of the
    four conditions stops being provable from the data, this fails loudly
    instead of a human needing to notice a scratchpad result went stale."""
    import subprocess

    result = subprocess.run(["uv", "run", "validators/ib_rank.py"],
                             capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "4 passed · 0 failed" in result.stdout, result.stdout


# --- Task 14, Fix Round 1 ---------------------------------------------------
#
# Finding 1: a missing weight vector made condition 4 (and threatened
# condition 1) PASS from absence rather than signal. `load_weights()`
# returns {} on a version-string or schema drift; score() then yields 0.0
# everywhere and rank() falls back to alphabetical order, which differs from
# a real order for free. Guard against it explicitly, before ranking.

def test_empty_weight_vector_is_rejected_before_ranking():
    """A vector that loaded to nothing must raise, by name and row count --
    not be silently ranked into an alphabetical-order false signal."""
    import pytest

    from validators.ib_rank import require_nonempty_weights

    with pytest.raises(RuntimeError, match="PSP-DCM v2"):
        require_nonempty_weights({"PSP-MA v2": {"activist_stake_13d": 1.0},
                                   "PSP-DCM v2": {}})


def test_nonempty_weight_vectors_are_accepted():
    """The other half: real, non-empty vectors must pass through silently."""
    from validators.ib_rank import require_nonempty_weights

    require_nonempty_weights({"PSP-MA v2": {"activist_stake_13d": 1.0},
                               "PSP-DCM v2": {"maturity_wall": 1.0}})  # no raise


def test_identical_replay_versions_are_rejected():
    """A weight-replay pair that loaded IDENTICAL (e.g. a version-string bug
    resolving both to the same rows) must raise -- an honest 'orders do not
    differ' finding and a masked load bug must not look the same."""
    import pytest

    from validators.ib_rank import require_versions_differ

    same = {"activist_stake_13d": 1.0, "maturity_wall": 0.1}
    with pytest.raises(RuntimeError, match="identical"):
        require_versions_differ("PSP-MA v1", same, "PSP-MA v2", dict(same))


def test_genuinely_different_replay_versions_are_accepted():
    """The other half: two genuinely different vectors must pass through."""
    from validators.ib_rank import require_versions_differ

    require_versions_differ(
        "PSP-MA v1", {"activist_stake_13d": 0.45},
        "PSP-MA v2", {"activist_stake_13d": 1.00})  # no raise
