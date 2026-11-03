"""Wave 16 Task 9 -- verify the divergence prospect's DCM gap is MEASURED.

See docs/wave16-design.md sec 6. This does NOT generate anything: the brief
was rewritten because the original plan engineered a debt ladder for Boston
Omaha Corp, which was wrong on two counts -- its freshest Schedule 13D has
role=FILER (it files 13Ds about *other* companies, so reading that filing as
an activist stake taken *in* Boston Omaha inverts the signal), and it carried
zero debt_instrument rows, so its low DCM score was ABSENT DATA rather than a
measured low signal.

The current pair (corrected 2026-08-25 to match the shipped data --
`validators/ib_rank.py`'s `DIVERGENT_PROSPECT` / `MIRROR_PROSPECT`; an
earlier draft of this module named "Anywhere Real Estate Inc." as the
comparator, which was never the entity actually loaded):

  PROSPECT (Braemar Hotels & Resorts Inc.)  -- 13 in-window Schedule 13D
    filings, all role=SUBJECT; a long-dated debt ladder (2043, 2045) with a
    flat spread band across the window. This half is MEASURED: nothing in
    this wave touched Braemar's debt data.
  COMPARATOR (Thermon Group Holdings, Inc.) -- a maturity inside the DCM
    horizon and a widening spread band, so the contrast is measured on the
    DCM side too, not just asserted by the prospect's absence of a wall.
    This half is ENGINEERED, not measured: `w16-i-01a242`
    (maturity 2028-06-13) was minted by this wave's
    `generators/extend_debt_ladder_wave16.py` (Task 8b), whose near rung is
    dated inside the 24-month horizon by construction for every eligible
    obligor. Labelled `synthetic -- engineered` in
    `sources/screening/wave16_debt_ladder.json`; see
    `docs/wave16-design.md` sec 6.2 for the fuller account.

Both entities are resolved by `legal_name` to their LEI, inside each test,
never by scanning for "whichever entity currently satisfies the condition".
That scan pattern is exactly what let MasTec pass this class of check earlier
in Wave 16 -- it qualified only because it had no debt data loaded at all, and
stopped qualifying the moment real debt rows arrived. Pinning to a name make
a future data shift fail loudly instead of silently swapping in a new entity
for the wrong reason.
"""
from __future__ import annotations

import datetime as dt
import json

from ccf.config import (
    AS_OF_IB,
    IB_WINDOW_END,
    IB_WINDOW_START,
    PG_SCHEMA_V2 as S,
    REPO_ROOT,
    pg_connect,
)

PROSPECT_NAME = "Braemar Hotels & Resorts Inc."
COMPARATOR_NAME = "Thermon Group Holdings, Inc."

# The DCM refinancing horizon: 24 months beyond the pinned as-of, derived from
# AS_OF_IB rather than restated as a literal so the two can never drift apart.
_as_of = dt.date.fromisoformat(AS_OF_IB)
DCM_HORIZON = _as_of.replace(year=_as_of.year + 2).isoformat()


def _resolve_lei(cur, legal_name: str) -> str:
    """Resolve a named entity to its LEI. Fails loudly on 0 or >1 matches --
    a fuzzy or partial match here would silently let a different entity stand
    in for the named one."""
    cur.execute(f'SELECT lei FROM "{S}".legal_entity WHERE legal_name = %s',
                (legal_name,))
    rows = cur.fetchall()
    assert len(rows) == 1, (
        f"expected exactly one legal_entity row for {legal_name!r}, "
        f"got {len(rows)}: {rows}")
    return rows[0][0]


def test_prospect_ladder_is_long_dated_and_flat_while_comparator_has_a_near_wall():
    with pg_connect() as conn, conn.cursor() as cur:
        prospect_lei = _resolve_lei(cur, PROSPECT_NAME)
        comparator_lei = _resolve_lei(cur, COMPARATOR_NAME)

        # 1. The prospect carries a ladder, not a single bond.
        cur.execute(
            f'SELECT maturity FROM "{S}".debt_instrument WHERE lei = %s '
            "ORDER BY maturity", (prospect_lei,))
        prospect_maturities = [r[0].isoformat() for r in cur.fetchall()]
        assert len(prospect_maturities) >= 2, (
            f"{PROSPECT_NAME}: only {len(prospect_maturities)} "
            "debt_instrument row(s) -- need a ladder (>= 2)")

        # 2. No wall inside the DCM horizon: every prospect maturity is
        #    beyond it, computed by counting how many fall inside.
        prospect_walls = [m for m in prospect_maturities if m <= DCM_HORIZON]
        assert not prospect_walls, (
            f"{PROSPECT_NAME}: {len(prospect_walls)} of "
            f"{len(prospect_maturities)} maturities fall inside the "
            f"{DCM_HORIZON} horizon: {prospect_walls} -- a real wall would "
            "legitimately rank this prospect for DCM")

        # 3. The flat spread is MEASURED, not absent: observations must
        #    exist, and the computed band must be narrow.
        cur.execute(f"""
            SELECT so.spread_bp FROM "{S}".spread_observation so
            JOIN "{S}".debt_instrument di ON di.instrument_id = so.instrument_id
            WHERE di.lei = %s AND so.obs_date BETWEEN %s AND %s
        """, (prospect_lei, IB_WINDOW_START, IB_WINDOW_END))
        prospect_spreads = [float(r[0]) for r in cur.fetchall()]
        assert prospect_spreads, (
            f"{PROSPECT_NAME}: 0 in-window spread_observation rows -- "
            "'flat' cannot be measured from nothing")
        prospect_band = max(prospect_spreads) - min(prospect_spreads)
        assert prospect_band < 50, (
            f"{PROSPECT_NAME}: spread band {prospect_band:.3f}bp over "
            f"{len(prospect_spreads)} observations is not flat (>= 50bp)")

        # 4. Comparator: a maturity DOES fall inside the horizon -- a real
        #    near-term wall, not merely the prospect's absence of one.
        cur.execute(
            f'SELECT instrument_id, maturity FROM "{S}".debt_instrument '
            "WHERE lei = %s ORDER BY maturity", (comparator_lei,))
        comparator_rows = cur.fetchall()
        comparator_maturities = [r[1].isoformat() for r in comparator_rows]
        near_wall_instruments = [r[0] for r in comparator_rows
                                  if r[1].isoformat() <= DCM_HORIZON]
        assert near_wall_instruments, (
            f"{COMPARATOR_NAME}: no maturity inside {DCM_HORIZON} among "
            f"{comparator_maturities} -- the comparator needs a real "
            "near-term wall for the contrast to be measured on both sides")

        # 5. The near-wall instrument's spread is measurably WIDENING, not
        #    flat -- checked as net drift (last obs - first obs) rather than
        #    max-min band. Band alone is the wrong statistic here: this
        #    comparator can carry more than one bond, and mixing spreads
        #    from two different instruments at two different baseline
        #    levels inflates a max-min band with a level gap that has
        #    nothing to do with widening. Scoped to the near-wall
        #    instrument(s) specifically, since that is the one a DCM banker
        #    is actually pricing the refinancing risk against.
        cur.execute(f"""
            SELECT so.obs_date, so.spread_bp FROM "{S}".spread_observation so
            WHERE so.instrument_id = ANY(%s)
              AND so.obs_date BETWEEN %s AND %s
            ORDER BY so.obs_date
        """, (near_wall_instruments, IB_WINDOW_START, IB_WINDOW_END))
        comparator_series = [(r[0], float(r[1])) for r in cur.fetchall()]
        assert comparator_series, (
            f"{COMPARATOR_NAME}: 0 in-window spread_observation rows for "
            f"{near_wall_instruments} -- 'widening' cannot be measured "
            "from nothing")
        comparator_drift = comparator_series[-1][1] - comparator_series[0][1]
        assert comparator_drift > 20, (
            f"{COMPARATOR_NAME}: near-wall instrument spread drifted "
            f"{comparator_drift:.3f}bp ({comparator_series[0]} -> "
            f"{comparator_series[-1]}) across the window -- not "
            "measurably widening (need > 20bp net drift) to contrast with "
            "the prospect's flat band")


def test_prospect_has_subject_13d_filings_inside_the_window():
    """The M&A half of the contrast: the prospect's activist-stake signal
    must be real (role == SUBJECT), inside the 12-month window, and counted
    -- never read off a stored role_split summary field."""
    with pg_connect() as conn, conn.cursor() as cur:
        prospect_lei = _resolve_lei(cur, PROSPECT_NAME)

    data = json.loads(
        (REPO_ROOT / "sources" / "screening" / "wave16_13d.json").read_text())
    filings = data["filings"]
    assert filings, "no Schedule 13D filings in the artifact at all"

    prospect_filings = [f for f in filings if f["lei"] == prospect_lei]
    in_window = [f for f in prospect_filings
                 if IB_WINDOW_START <= f["filing_date"] <= IB_WINDOW_END]
    subject_in_window = [f for f in in_window if f["role"] == "SUBJECT"]

    assert subject_in_window, (
        f"{PROSPECT_NAME} ({prospect_lei}): 0 of {len(in_window)} in-window "
        "filings have role=SUBJECT -- a FILER-only prospect would invert "
        "the signal exactly as Boston Omaha's did")
