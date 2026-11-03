#!/usr/bin/env python3
"""Wave 11b Task 9 — load the early-warning screening artifacts into Postgres.

Seven tables, per `docs/wave11b-design.md` §4.1. Postgres owns `E` and policy
reference for this product; Fluree owns the 8-K event assertions, the
`signalAbout` / `triggeredBy` edges, and the prior-observation ledger points
(Task 10, not here).

    warn_notice           public                    Task 2's 3,514 WARN rows
    warn_match             mixed                    Task 3's 36 candidate pairs
    gdelt_mention            public                 Task 4's 951 mentions
    signal_event               mixed                Task 7's 1,600-row ledger,
                                                      PLUS 3 rows from Task 8's
                                                      composite case (below)
    signal_weight                synthetic — internal ORIGINATED in Task 7
    escalation_threshold           synthetic — internal ORIGINATED in Task 7
    trend_delta                       public         Task 5's 3,705 rows

**Six of the seven tables are DERIVED, loaded verbatim from an artifact this
loader does not originate.** `signal_weight` and `escalation_threshold` are
the exception: both are **ORIGINATED in `generators/generate_signals.py`
(Task 7)**, not here — this loader only carries them across, unchanged, into
Postgres. Say so plainly, the same way `load_postgres_wave11a.py` says so for
`divergence_threshold`: nothing in *this* file invents a weight or a
threshold value. `generate_signals.py`'s own docstring is explicit that
"WEIGHTS AND THRESHOLDS ARE ORIGINATED HERE [Task 7], not derived from any
upstream artifact" — this loader is one further hop downstream of that origin,
not a second origin.

## Reopened: the composite case's three signals were absent from every store

**Added source: `sources/screening/wave11b_narrative.json` -> `composite`.**
DERIVED, loaded verbatim, same as the six artifact-backed tables above —
Task 8's `generators/narrative_wave11b.py` originates the composite case
(design §3.3), this loader only carries its three `signals` rows across into
`signal_event`, unchanged. It was missing from the original Task 9 pass
because the controller's brief never named this artifact and
`wave11b_signals.json["signals"]` (Task 7's ledger, loaded above) does not
contain them — confirmed directly: none of
`sig-composite-B3BS7ACMDUWISF18KY76-{adverse_media,warn_notice,spread_widening}`
appear in that 1,600-row list. `signal_event` therefore goes from 1,600 rows
to **1,603**; the original 1,600 are untouched (same upsert, same key,
nothing about them changes on a rerun that also includes the composite three).

Each of the three rows is on Bausch Health (`B3BS7ACMDUWISF18KY76`), severity
fixed at `0.6`, `provenance: "synthetic — engineered"` **carried through
exactly as the artifact states it** — never relabelled to `public` (nobody
publishes this *pairing* of signal to obligor; it is manufactured to
demonstrate design §3.3's composite condition) and never relabelled to
anything else. The artifact's per-signal `sector` / `weight` / `weighted_score`
fields have no dedicated column on `signal_event` (no other row in the table
carries them as top-level columns either — `spread_widening` rows fold
comparable context into `source_ref` instead), so they are merged into
`source_ref` alongside the artifact's own `source_ref` dict rather than
dropped; verified no key collision (the artifact's `source_ref` for these
three rows carries only `engineered` / `component` / `basis`).

**What is deliberately NOT loaded here: the cascade.** The same artifact's
`cascade` key holds the scripted Item 2.04 acceleration against Avis Budget
Group with `signal_about` edges to a Facility, two CollateralPledges and five
Drawdowns. Design §2.1 assigns "Cascade trigger event" to **Fluree only**
(not "Postgres + Fluree" like the composite case), and the graph edges that
make it demonstrable — `signalAbout` from the 8-K signal to each target — are
Fluree's typed-edge slice, not a Postgres table. Loading the cascade signal
into `signal_event` here would duplicate an element into a store that does
not own it (CLAUDE.md's single-writer rule) without the edges that make it
useful, so it is left to Task 10's Fluree loader entirely.

**The Fluree half of the composite case is a separate, open question — not
answered here.** Design §2.1 assigns the composite signal set to "Postgres +
Fluree", and this loader only writes the Postgres half. See this task's
report, §Fluree recommendation, for the judgment call on what (if anything)
Fluree still needs — that judgment does not translate into a Fluree write in
this file; none is made here.

## The decay constants — ADDED 2026-08-21, and why NULL is not zero

Design §2.1, §4.1 and §8 all place spec §E's **λ_c decay constants** in
Postgres, in this table: *"weight **and decay constant** per signal type /
sector."* Until 2026-08-21 they were in neither store. `DECAY_DAYS` lived only
in `generators/generate_signals.py` and, as a top-level `decay_days` key, in
`wave11b_signals.json` — so §E's three-decay-regimes argument, which the spec
calls the interesting part of this product, was unsupported by any loaded data,
and the SDK project (which cannot read this repository) had no way to apply
decay in the product's §D step 5. `decay_days` is now a column here, carried
verbatim from the artifact exactly like `weight`; nothing in this file
originates a constant.

**Why a column on `signal_weight` rather than a separate policy table.** The
constant is per signal *type*, so nine sector rows repeat one value — real
denormalisation, and it was weighed. It loses to three things: the design names
this table and this column semantics explicitly; a consumer already joins
`signal_weight` for the weight and would otherwise need a second join to score
one signal; and a new table is a store shape the downstream project has no way
to discover, whereas an extra column on a table it already reads is
self-describing. The same repetition already exists in `weight` itself
(`8k_event` is 0.30 in six of the nine sectors).

**`8k_event` is NULL, never 0, and the distinction is load-bearing.** A filed
8-K is a permanent fact; its relevance is bounded by supersession — a later
filing or an amendment — not by a half-life. Under any decay kernel of the
shape `exp(-t/λ)` or `0.5**(t/λ)`, `λ = 0` is either undefined or means
*instant* decay: the exact opposite of what this row asserts. So the column is
NULLABLE with no DEFAULT, and a consumer reading NULL must branch on "does not
decay" rather than arithmetic its way to a wrong answer. The four remaining
types carry §E's regimes: adverse media 7, spread widening 1, WARN 180, trend
delta 90.

Four traps, checked against directly (project history, not hypothetical):

1. PARTIAL `ON CONFLICT ... DO UPDATE SET`. Every upsert below sets EVERY
   non-key column, or the table is delete-then-insert. No column is left to
   go stale silently.

2. WARN MATCH LOSSINESS COLLAPSED TO "RESOLVED ONLY". `warn_match` keeps
   both verdicts: 4 `resolved` across 3 distinct obligors — **Quanex
   Building Products matches twice** (`WARN-01175` and `WARN-01988`, both
   the employer "Quanex Homeshield LLC" at 0.8976), Bausch Health once
   (`WARN-02124`, 0.9538) and Charter Communications once (`WARN-01386`,
   1.0000) — and 32 `ambiguous`. Nothing here filters on `verdict`.
   (CORRECTED 2026-08-21: this paragraph said *"Bausch Health matches
   twice, Charter Communications and one other once each"*. Live query says
   Quanex is the doubled one. The error sat inside the paragraph explaining
   why the lossy join must stay visible, which is the worst place for it —
   a reader who checks one claim and finds it false discounts the rest of
   the trap list.) A table containing only
   the 4 clean matches would pass a row-count check and destroy the
   demonstration `generators/warn_match.py` exists to carry: that a NAME
   join across independently-authored public sources is supposed to be
   lossy, and the lossiness must stay visible, not be resolved away at
   load time.

3. `pct_change` COERCED TO 0 OR REJECTED BY A NEW NOT NULL. 21 of
   `trend_delta`'s 3,705 rows carry `pct_change: null` — a genuine
   zero-to-nonzero (or zero-to-zero) prior, not a missing observation (see
   `generators/generate_trend_deltas.py`). The column is nullable and no
   insert path substitutes 0.0 for `None`; psycopg passes `None` through to
   SQL `NULL` unchanged.

4. THE CELANESE PRECISION-REVIEW FLAG SILENTLY DROPPED. See "The
   `gdelt_mention` down-weight columns" below — this is the one artifact
   fact that lives OUTSIDE any row of any of the seven tables' natural
   record shape (`wave11b_gdelt.json`'s top-level `coverage[lei]`, not a
   `mentions[]` element), so it is the one place a straight "load the array"
   pass would lose something without an explicit decision.

## Natural keys that don't exist on the wire, and how each is supplied

None of the four source artifacts carry a per-row surrogate id for
`warn_notice` or `gdelt_mention` — a decision had to be made for each, not
merely followed.

**`warn_notice.notice_id`.** WARN notices carry no id field at all, and
`source_ref` cannot serve as one: California's is a specific PDF line
(`...pdf:ca-pdf:line205`, unique per notice — 3,099 of 3,099 CA rows), but
Texas's is a *dataset-level* pointer shared by ALL 415 TX rows
(`tx-warn.json:data.texas.gov:8w53-c4f6`) because the TX source is a bulk
JSON file, not a per-notice document. `city` is null for every CA row (the CA
PDF carries no city column) and `county` is null for 16; `effective_date` and
`employees` are null for a handful of rows. No combination of raw fields is
both non-null everywhere and unique everywhere. `notice_id` is therefore
synthesized as `WARN-00000`..`WARN-03513`, the zero-padded 0-based position
of the notice in `wave11b_warn.json["notices"]` — deterministic because the
artifact is committed and never reordered, so the same id always lands on the
same notice across reloads (idempotency requires exactly this).

**`warn_match` -> `warn_notice` resolution.** A match's own `notice_ref`
field is `source_ref` (line-level and unique for the 34 CA matches; the
dataset-level TX pointer for the 2 TX matches). For the TX pair, `notice_ref`
alone is ambiguous across 415 candidate notices; `employer` disambiguates —
verified: every one of the 36 matches resolves to EXACTLY ONE notice via
`(notice_ref, employer)`, checked against the loaded artifact before writing
this file. That pair is the effective join key used to resolve `notice_id`
at load time; `warn_match`'s own primary key is `(notice_id, lei)` — verified
unique for all 36 rows.

**`gdelt_mention` primary key.** `url` alone is not unique: 6 URLs are each
mentioned by TWO different obligors (a shared wire story — e.g. a Las Vegas
Sands / Caesars gaming-industry piece hits both LEIs). `(url, lei)` is unique
across all 951 rows and is the primary key.

**`escalation_threshold`'s six rows are not one shape.** Three are tiered
`kind="escalation"` rows distinguished by `intent`
(`daily-sweep` / `credit-committee-referral` / `board-risk-report`); the
other three (`trend_delta_materiality`, `adverse_media_down_weight`,
`spread_detection`) are each a SINGLE row of their own `kind`, carrying no
`intent` field at all. Rather than leave `intent` nullable inside a primary
key (Postgres forbids a null PRIMARY KEY column, and a nullable non-key
"mostly-key" column invites exactly the accidental-duplicate bug primary
keys exist to prevent), `intent` is populated at load time as
`t["intent"] if kind == "escalation" else kind` — the kind stands in for its
own intent when the source artifact does not name a separate one. This is
recorded here, not left implicit: `(kind, intent, policy_version)` is then
genuinely unique and genuinely NOT NULL, verified against all 6 rows before
writing the DDL.

## The `gdelt_mention` down-weight columns

`wave11b_gdelt.json`'s top-level `coverage` map carries a `precision_review`
block for FOUR LEIs, not one — but three of those four (`"Sabre"`,
`"Griffon"`, `"REGIS"` as blind name queries) were found to return ZERO
genuine hits on inspection and were **replaced** by a re-fetch under a
qualified corporate name that itself returned zero articles; those LEIs have
no rows in `mentions[]` at all, so there is nothing on this table for their
review to attach to. Only `549300FHJQTDPPN41627` (Celanese) was **retained**
at `recommended_use: "down_weight"` — kept because the qualified form would
have discarded genuine chemical-industry coverage, not because the noise
isn't real (25 of 49 sampled titles are Celanese-the-place police blotters,
not Celanese-the-company).

That block lives at `coverage[lei]`, not inside any element of `mentions[]`,
so a straight per-row load of `mentions[]` would carry the 49 Celanese rows
with no trace of the finding attached to them — silently dropped, per the
brief's explicit warning. `generators/generate_signals.py` already solved
this exact problem for `signal_event`: it multiplies the affected LEI's
`adverse_media` severity by `round((sampled - off_topic) / sampled, 4)` and
writes that factor plus a reason string into `source_ref.down_weight_factor`
/ `source_ref.down_weight_reason` on every affected signal row, generically
(triggered by `recommended_use == "down_weight"`, not hardcoded to Celanese).

This loader mirrors that exact shape onto `gdelt_mention`, for the exact same
reason and with the exact same formula and field names, rather than inventing
a third representation (a separate `gdelt_coverage` table, out of scope for
the seven named here, or a JSON blob that would just relocate the problem):
`down_weight_factor NUMERIC` and `down_weight_reason TEXT`, both NULL for
every ordinary row, populated on the 49 rows whose `lei` carries a
`down_weight`-flagged `coverage[lei].precision_review` — currently Celanese
only, but the population rule reads `coverage` generically at load time, so a
future re-fetch that flags a second LEI needs no code change here. A
downstream consumer who sums `gdelt_mention` severities without checking this
column is measuring 49 rows at face value that the source review says should
count as ~0.49 of a row each; the column exists so that mistake is visible in
the schema, not just in a report only Task 9 read.

    uv run loaders/load_postgres_wave11b.py --dry-run
    uv run loaders/load_postgres_wave11b.py

Idempotent: every write is an upsert on a natural (or, where none exists on
the wire, a deterministically-synthesized) key with a full-column SET.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter

from ccf.config import PG_SCHEMA_V2, REPO_ROOT, assert_v2_schema, pg_connect
from ccf.currency import verify_current

SCREEN = REPO_ROOT / "sources" / "screening"
S = PG_SCHEMA_V2

DDL = f"""
CREATE TABLE IF NOT EXISTS "{S}".warn_notice (
    notice_id       TEXT PRIMARY KEY,
    state           TEXT NOT NULL,
    employer        TEXT NOT NULL,
    notice_date     DATE NOT NULL,
    effective_date  DATE,
    employees       INTEGER,
    city            TEXT,
    county          TEXT,
    source_ref      TEXT NOT NULL,
    provenance      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS "{S}".warn_match (
    notice_id    TEXT NOT NULL REFERENCES "{S}".warn_notice(notice_id),
    lei          CHAR(20) NOT NULL REFERENCES "{S}".legal_entity(lei),
    anchor_name  TEXT NOT NULL,
    employer     TEXT NOT NULL,
    state        TEXT NOT NULL,
    score        NUMERIC NOT NULL,
    verdict      TEXT NOT NULL CHECK (verdict IN ('resolved', 'ambiguous')),
    notice_ref   TEXT NOT NULL,
    provenance   TEXT NOT NULL,
    PRIMARY KEY (notice_id, lei)
);

CREATE TABLE IF NOT EXISTS "{S}".gdelt_mention (
    url                 TEXT NOT NULL,
    lei                 CHAR(20) NOT NULL REFERENCES "{S}".legal_entity(lei),
    employer_query      TEXT NOT NULL,
    gdelt_query         TEXT NOT NULL,
    seendate            TEXT NOT NULL,
    domain              TEXT NOT NULL,
    title               TEXT NOT NULL,
    tone                TEXT NOT NULL,
    provenance          TEXT NOT NULL,
    down_weight_factor  NUMERIC,
    down_weight_reason  TEXT,
    PRIMARY KEY (url, lei)
);

CREATE TABLE IF NOT EXISTS "{S}".signal_event (
    signal_id    TEXT PRIMARY KEY,
    lei          CHAR(20) NOT NULL REFERENCES "{S}".legal_entity(lei),
    signal_type  TEXT NOT NULL CHECK (signal_type IN
                 ('adverse_media', '8k_event', 'trend_delta',
                  'spread_widening', 'warn_notice')),
    observed_at  DATE NOT NULL,
    severity     NUMERIC NOT NULL,
    source_ref   JSONB NOT NULL,
    provenance   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS "{S}".signal_weight (
    signal_type     TEXT NOT NULL,
    sector          TEXT NOT NULL,
    policy_version  TEXT NOT NULL,
    weight          NUMERIC NOT NULL,
    decay_days      NUMERIC,
    rationale       TEXT,
    provenance      TEXT NOT NULL,
    PRIMARY KEY (signal_type, sector, policy_version)
);

-- Added 2026-08-21. The table pre-exists this column on any estate loaded
-- before that date, and CREATE TABLE IF NOT EXISTS will not add it.
-- DELIBERATELY NULLABLE, and no DEFAULT: see the module docstring.
ALTER TABLE "{S}".signal_weight ADD COLUMN IF NOT EXISTS decay_days NUMERIC;

CREATE TABLE IF NOT EXISTS "{S}".escalation_threshold (
    kind                                        TEXT NOT NULL,
    intent                                      TEXT NOT NULL,
    policy_version                              TEXT NOT NULL,
    threshold_score                             NUMERIC,
    threshold_pct                               NUMERIC,
    signal_type                                 TEXT,
    rule                                        TEXT,
    affected_leis                               JSONB,
    roll_window_obs                             INTEGER,
    anticipation_fraction_of_sector_threshold   NUMERIC,
    confirmation_fraction_of_sector_threshold   NUMERIC,
    rationale                                   TEXT,
    provenance                                  TEXT NOT NULL,
    PRIMARY KEY (kind, intent, policy_version)
);

CREATE TABLE IF NOT EXISTS "{S}".trend_delta (
    lei               CHAR(20) NOT NULL REFERENCES "{S}".legal_entity(lei),
    tag               TEXT NOT NULL,
    unit              TEXT NOT NULL,
    period_end        DATE NOT NULL,
    prior_period_end  DATE NOT NULL,
    value             NUMERIC NOT NULL,
    prior_value       NUMERIC NOT NULL,
    pct_change        NUMERIC,
    provenance        TEXT NOT NULL,
    PRIMARY KEY (lei, tag, unit, period_end)
);

CREATE INDEX IF NOT EXISTS ix_warn_notice_state ON "{S}".warn_notice (state);
CREATE INDEX IF NOT EXISTS ix_warn_match_lei ON "{S}".warn_match (lei);
CREATE INDEX IF NOT EXISTS ix_gdelt_mention_lei ON "{S}".gdelt_mention (lei);
CREATE INDEX IF NOT EXISTS ix_signal_event_lei ON "{S}".signal_event (lei);
CREATE INDEX IF NOT EXISTS ix_signal_event_type ON "{S}".signal_event (signal_type);
CREATE INDEX IF NOT EXISTS ix_trend_delta_lei ON "{S}".trend_delta (lei);
"""


#: Filled by `load()` so `main()` can print the currency verdict for every
#: artifact it read — coverage visible on each run, not inferred.
CURRENCY_NOTES: list[str] = []


def load(name: str) -> dict:
    """Read one artifact, refusing a STALE one (design §5, built 2026-08-21).

    `ccf.currency.verify_current` re-hashes whatever inputs the artifact
    itself recorded under `_inputs` and raises `StaleArtifact` if any has
    changed on disk since — so a `wave11b_gdelt.json` regenerated after
    `generate_signals.py` last ran stops the load instead of feeding it a
    ledger derived from bytes that no longer exist. What it cannot catch is
    an input that is wrong rather than stale; that boundary is stated in
    `ccf/currency.py` rather than left implicit.
    """
    doc, note = verify_current(name)
    CURRENCY_NOTES.append(note)
    return doc


def down_weight_factor(review: dict) -> float:
    """Mirror `generators/generate_signals.py`'s exact formula, unchanged."""
    return round((review["sampled"] - review["off_topic"]) / review["sampled"], 4)


def build_rows(warn: dict, gdelt: dict, signals: dict, trend: dict,
               narrative: dict):
    notices = warn["notices"]
    matches = warn["matches"]
    warn_provenance = warn["provenance"]

    # --- warn_notice: synthesized notice_id, deterministic on array order ---
    notice_rows: list[tuple] = []
    notice_id_by_key: dict[tuple, str] = {}
    for i, n in enumerate(notices):
        notice_id = f"WARN-{i:05d}"
        notice_id_by_key[(n["source_ref"], n["employer"])] = notice_id
        notice_rows.append((
            notice_id, n["state"], n["employer"], n["notice_date"],
            n["effective_date"], n["employees"], n["city"], n["county"],
            n["source_ref"], warn_provenance,
        ))

    # --- warn_match: resolve notice_id via (notice_ref, employer) ---
    match_rows: list[tuple] = []
    for m in matches:
        key = (m["notice_ref"], m["employer"])
        if key not in notice_id_by_key:
            raise KeyError(
                f"warn_match row for lei={m['lei']!r} does not resolve to any "
                f"warn_notice via (notice_ref, employer)={key!r} — the join "
                "this loader depends on (verified unique for all 36 matches "
                "before this file was written) has broken."
            )
        notice_id = notice_id_by_key[key]
        match_rows.append((
            notice_id, m["lei"], m["anchor_name"], m["employer"], m["state"],
            m["score"], m["verdict"], m["notice_ref"],
            "synthetic — internal",
        ))

    # --- gdelt_mention: down-weight columns from coverage[lei].precision_review ---
    coverage = gdelt["coverage"]
    down_weight_by_lei: dict[str, tuple[float, str]] = {}
    for lei, c in coverage.items():
        review = c.get("precision_review")
        if review and review.get("recommended_use") == "down_weight":
            factor = down_weight_factor(review)
            reason = (
                "coverage[lei].precision_review flags this LEI for "
                "down_weight "
                f"({review['sampled'] - review['off_topic']}/{review['sampled']} "
                "sampled mentions on-topic); severity should be scaled by "
                "this factor"
            )
            down_weight_by_lei[lei] = (factor, reason)

    mention_rows: list[tuple] = []
    for m in gdelt["mentions"]:
        factor_reason = down_weight_by_lei.get(m["lei"])
        factor = factor_reason[0] if factor_reason else None
        reason = factor_reason[1] if factor_reason else None
        mention_rows.append((
            m["url"], m["lei"], m["employer_query"], m["gdelt_query"],
            m["seendate"], m["domain"], m["title"], m["tone"],
            m["provenance"], factor, reason,
        ))

    # --- signal_event: Task 7's 1,600-row ledger ---
    signal_rows: list[tuple] = [
        (s["signal_id"], s["lei"], s["signal_type"], s["observed_at"],
         s["severity"], json.dumps(s["source_ref"]), s["provenance"])
        for s in signals["signals"]
    ]

    # --- signal_event: + Task 8's composite case, 3 more rows (see docstring
    # "Reopened" section) — additions, never a replacement of the 1,600 above.
    # provenance is carried exactly as the artifact states it, never relabelled.
    for s in narrative["composite"]["signals"]:
        source_ref = dict(s["source_ref"])
        for extra in ("sector", "weight", "weighted_score"):
            if extra in source_ref:
                raise KeyError(
                    f"composite signal {s['signal_id']!r} source_ref already "
                    f"has key {extra!r} — the no-collision merge this loader "
                    "depends on (verified before this file was written) has "
                    "broken."
                )
            source_ref[extra] = s[extra]
        if s["provenance"] != "synthetic — engineered":
            # Symmetric with load_fluree_wave11b.py's own guard, added
            # 2026-08-21 (Task 13) after the deferred-minor triage found this
            # loader had none. The two stores hold the SAME three composite
            # signals under the SAME signal_ids; a guard on one side only
            # means a mislabelled artifact is refused by Fluree and silently
            # accepted by Postgres, leaving the halves disagreeing about a
            # provenance class CLAUDE.md rule 1 says must be honest.
            raise RuntimeError(
                f"composite signal {s['signal_id']!r} is not labelled "
                f"synthetic — engineered (got {s['provenance']!r}); "
                "refusing to load a mislabelled engineered condition."
            )
        signal_rows.append((
            s["signal_id"], s["lei"], s["signal_type"], s["observed_at"],
            s["severity"], json.dumps(source_ref), s["provenance"],
        ))

    # --- signal_weight: ORIGINATED in Task 7, carried verbatim ---
    decay = signals["decay_days"]
    weight_rows: list[tuple] = [
        (w["signal_type"], w["sector"], w["policy_version"], w["weight"],
         decay[w["signal_type"]], w["rationale"], w["provenance"])
        for w in signals["weights"]
    ]

    # --- escalation_threshold: heterogeneous by kind; ORIGINATED in Task 7 ---
    threshold_rows: list[tuple] = []
    for t in signals["thresholds"]:
        kind = t["kind"]
        intent = t["intent"] if kind == "escalation" else kind
        affected_leis = t.get("affected_leis")
        threshold_rows.append((
            kind, intent, t["policy_version"],
            t.get("threshold_score"), t.get("threshold_pct"),
            t.get("signal_type"), t.get("rule"),
            json.dumps(affected_leis) if affected_leis is not None else None,
            t.get("roll_window_obs"),
            t.get("anticipation_fraction_of_sector_threshold"),
            t.get("confirmation_fraction_of_sector_threshold"),
            t.get("rationale"), t["provenance"],
        ))

    # --- trend_delta: all 3,705 rows, pct_change NULL preserved ---
    delta_rows: list[tuple] = [
        (d["lei"], d["tag"], d["unit"], d["period_end"], d["prior_period_end"],
         d["value"], d["prior_value"], d["pct_change"], d["provenance"])
        for d in trend["deltas"]
    ]

    return {
        "warn_notice": notice_rows,
        "warn_match": match_rows,
        "gdelt_mention": mention_rows,
        "signal_event": signal_rows,
        "signal_weight": weight_rows,
        "escalation_threshold": threshold_rows,
        "trend_delta": delta_rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    warn = load("wave11b_warn.json")
    gdelt = load("wave11b_gdelt.json")
    signals = load("wave11b_signals.json")
    trend = load("wave11b_trend_deltas.json")
    narrative = load("wave11b_narrative.json")

    rows = build_rows(warn, gdelt, signals, trend, narrative)

    verdicts = Counter(m[6] for m in rows["warn_match"])
    resolved_obligors = {m[1] for m in rows["warn_match"] if m[6] == "resolved"}
    pct_null = sum(1 for d in rows["trend_delta"] if d[7] is None)
    down_weighted = sum(1 for g in rows["gdelt_mention"] if g[9] is not None)
    sig_provenance = Counter(s[6] for s in rows["signal_event"])
    composite_lei = narrative["composite"]["lei"]
    composite_ids = {s["signal_id"] for s in narrative["composite"]["signals"]}
    composite_loaded = sum(1 for s in rows["signal_event"] if s[0] in composite_ids)

    print(f"Wave 11b Task 9 — load into {S}\n")
    print("  artifact currency (design §5):")
    for note in CURRENCY_NOTES:
        print(f"    {note}")
    print()
    print(f"  warn_notice             {len(rows['warn_notice']):>6}  (source: 3,514 notices)")
    print(f"  warn_match               {len(rows['warn_match']):>6}  (source: 36 matches; "
          f"resolved={verdicts['resolved']} [{len(resolved_obligors)} distinct obligors], "
          f"ambiguous={verdicts['ambiguous']})")
    print(f"  gdelt_mention            {len(rows['gdelt_mention']):>6}  (source: 951 mentions; "
          f"{down_weighted} down-weighted, all Celanese)")
    print(f"  signal_event             {len(rows['signal_event']):>6}  (source: 1,600 ledger + "
          f"{composite_loaded} composite [{composite_lei}]; provenance {dict(sig_provenance)})")
    n_null_decay = sum(1 for w in rows["signal_weight"] if w[4] is None)
    print(f"  signal_weight            {len(rows['signal_weight']):>6}  (originated in Task 7: "
          f"5 types x 9 sectors; decay_days NULL on {n_null_decay} "
          f"[8k_event -- a filed 8-K does not decay])")
    print(f"  escalation_threshold     {len(rows['escalation_threshold']):>6}  (originated in Task 7)")
    print(f"  trend_delta              {len(rows['trend_delta']):>6}  (source: 3,705 deltas; "
          f"{pct_null} pct_change NULL, preserved not coerced)")

    if args.dry_run:
        print("\n  [dry-run] no DDL executed, no rows written")
        return 0

    assert_v2_schema(S)

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(DDL)

        cur.executemany(
            f'INSERT INTO "{S}".warn_notice '
            "(notice_id, state, employer, notice_date, effective_date, "
            " employees, city, county, source_ref, provenance) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (notice_id) DO UPDATE SET "
            "state=EXCLUDED.state, employer=EXCLUDED.employer, "
            "notice_date=EXCLUDED.notice_date, "
            "effective_date=EXCLUDED.effective_date, "
            "employees=EXCLUDED.employees, city=EXCLUDED.city, "
            "county=EXCLUDED.county, source_ref=EXCLUDED.source_ref, "
            "provenance=EXCLUDED.provenance",
            rows["warn_notice"],
        )

        cur.executemany(
            f'INSERT INTO "{S}".warn_match '
            "(notice_id, lei, anchor_name, employer, state, score, verdict, "
            " notice_ref, provenance) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (notice_id, lei) DO UPDATE SET "
            "anchor_name=EXCLUDED.anchor_name, employer=EXCLUDED.employer, "
            "state=EXCLUDED.state, score=EXCLUDED.score, "
            "verdict=EXCLUDED.verdict, notice_ref=EXCLUDED.notice_ref, "
            "provenance=EXCLUDED.provenance",
            rows["warn_match"],
        )

        cur.executemany(
            f'INSERT INTO "{S}".gdelt_mention '
            "(url, lei, employer_query, gdelt_query, seendate, domain, "
            " title, tone, provenance, down_weight_factor, down_weight_reason) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (url, lei) DO UPDATE SET "
            "employer_query=EXCLUDED.employer_query, "
            "gdelt_query=EXCLUDED.gdelt_query, seendate=EXCLUDED.seendate, "
            "domain=EXCLUDED.domain, title=EXCLUDED.title, tone=EXCLUDED.tone, "
            "provenance=EXCLUDED.provenance, "
            "down_weight_factor=EXCLUDED.down_weight_factor, "
            "down_weight_reason=EXCLUDED.down_weight_reason",
            rows["gdelt_mention"],
        )

        cur.executemany(
            f'INSERT INTO "{S}".signal_event '
            "(signal_id, lei, signal_type, observed_at, severity, "
            " source_ref, provenance) VALUES (%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (signal_id) DO UPDATE SET "
            "lei=EXCLUDED.lei, signal_type=EXCLUDED.signal_type, "
            "observed_at=EXCLUDED.observed_at, severity=EXCLUDED.severity, "
            "source_ref=EXCLUDED.source_ref, provenance=EXCLUDED.provenance",
            rows["signal_event"],
        )

        cur.executemany(
            f'INSERT INTO "{S}".signal_weight '
            "(signal_type, sector, policy_version, weight, decay_days, "
            " rationale, provenance) VALUES (%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (signal_type, sector, policy_version) DO UPDATE SET "
            "weight=EXCLUDED.weight, decay_days=EXCLUDED.decay_days, "
            "rationale=EXCLUDED.rationale, "
            "provenance=EXCLUDED.provenance",
            rows["signal_weight"],
        )

        cur.executemany(
            f'INSERT INTO "{S}".escalation_threshold '
            "(kind, intent, policy_version, threshold_score, threshold_pct, "
            " signal_type, rule, affected_leis, roll_window_obs, "
            " anticipation_fraction_of_sector_threshold, "
            " confirmation_fraction_of_sector_threshold, rationale, "
            " provenance) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (kind, intent, policy_version) DO UPDATE SET "
            "threshold_score=EXCLUDED.threshold_score, "
            "threshold_pct=EXCLUDED.threshold_pct, "
            "signal_type=EXCLUDED.signal_type, rule=EXCLUDED.rule, "
            "affected_leis=EXCLUDED.affected_leis, "
            "roll_window_obs=EXCLUDED.roll_window_obs, "
            "anticipation_fraction_of_sector_threshold="
            "EXCLUDED.anticipation_fraction_of_sector_threshold, "
            "confirmation_fraction_of_sector_threshold="
            "EXCLUDED.confirmation_fraction_of_sector_threshold, "
            "rationale=EXCLUDED.rationale, provenance=EXCLUDED.provenance",
            rows["escalation_threshold"],
        )

        cur.executemany(
            f'INSERT INTO "{S}".trend_delta '
            "(lei, tag, unit, period_end, prior_period_end, value, "
            " prior_value, pct_change, provenance) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (lei, tag, unit, period_end) DO UPDATE SET "
            "prior_period_end=EXCLUDED.prior_period_end, "
            "value=EXCLUDED.value, prior_value=EXCLUDED.prior_value, "
            "pct_change=EXCLUDED.pct_change, provenance=EXCLUDED.provenance",
            rows["trend_delta"],
        )

        conn.commit()

        for table in ("warn_notice", "warn_match", "gdelt_mention",
                      "signal_event", "signal_weight", "escalation_threshold",
                      "trend_delta"):
            cur.execute(f'SELECT COUNT(*) FROM "{S}".{table}')
            print(f"  {table:24} store count: {cur.fetchone()[0]}")

    print("\n  loaded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
