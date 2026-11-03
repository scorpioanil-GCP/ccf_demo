#!/usr/bin/env python3
"""Wave 17 Task 8 — Postgres DDL for `aml-typology-match`, and the party load.
Extended by Task 12 (see "load_transactions is now called" below) to load
transactions, alerts and alert links. Extended by Task 16 (see
"load_projection_plans" below) to load the three projection plans.

Five tables, all owned outright by this product (§C assigns Party,
Transaction, Alert and ProjectionPlan concepts to Postgres for this spec;
none of them collide with a table another wave already owns — see the
`aml_projection_plan` note below, which follows the precedent Wave 16 set
when its own projection layer collided):

    aml_party            synthetic — engineered   201 rows (loaded here)
    aml_transaction      synthetic — engineered   4,358 rows (Task 12)
    aml_alert            synthetic — internal        150 rows (Task 12)
    aml_alert_link       (no provenance column)        50 rows (Task 12)
    aml_projection_plan  synthetic — internal          3 rows (Task 16)

## Two columns that exist before anything populates them

`aml_party.beneficial_owner_key TEXT NULL` — Task 9 populates this. Adding
it now, instead of letting Task 9 widen a table this task owns, is the
pre-flight ruling recorded in `task-8-brief.md`. `load_parties` below never
writes to this column (not even to NULL) — the INSERT's column list and the
ON CONFLICT ... DO UPDATE SET clause both omit it entirely, so a re-run of
`load_parties` after Task 9 has populated it can never reset it back to
NULL. That is the same "own only what you write" discipline this estate
uses whenever two tasks touch one table over time.

`aml_projection_plan.elements JSONB NOT NULL` — Task 16 populates this.
Same reasoning as Wave 16's `ib_projection_plan`: the estate already has a
`projection_plan` table (Wave 7, `mnpi-wall-enforcement`), with a shape
(`principal_id NOT NULL`, three `permitted_*` columns) that encodes a
different product's vocabulary. This product's projection plan is keyed by
`perspective`, not by a wall-crossing principal, so it gets its own table
rather than widening or relaxing Wave 7's.

## `aml_party.ofac_near_match JSONB NULL` — added by this task, not the brief

Task 7 declared exactly one party (`AMLP-0069`) that near-matches a real
OFAC SDN entry (`sources/screening/wave17_parties.json`, the one row
carrying `ofac_near_match: {sanctions_entry_id, matched_name,
measured_similarity}`). Task 17's `ofac_band_holds()` floor has to
recompute that similarity from LIVE Postgres data (`ccf.aml.similarity()`
against `"{S}".sanctions_name`), not from a `sources/` JSON file, or the one
check whose entire point is "recompute from the estate, don't trust a
stored number" would itself be reading an artifact. `load_parties` owns
this column and sets it from the artifact on every row (NULL on 200 of
them, the recorded object on the one) — unlike `beneficial_owner_key`, this
column IS written by this loader, so it belongs in the ordinary upsert.

## `bind_beneficial_owners(cur, bindings) -> int` — Task 9

Reads `sources/screening/wave17_ownership.json` (built by
`generators/bind_aml_ownership.py`) and UPDATEs `aml_party.beneficial_owner_key`
for the parties it names. Owns exactly this one column and touches nothing
else on `aml_party` — `load_parties` above owns every other column, and the
two never write the same field. Defense in depth: every key is re-checked
with `ccf.aml.is_psc_key()` immediately before the UPDATE runs, even though
the generator already checked it at artifact-build time, because the two
population's opposite safety properties (CLAUDE.md rule 2) make this the one
column in the estate that must never trust a single check.

## `load_transactions(cur, txns) -> int` — written in Task 8, now called

`aml_transaction` was created by Task 8's DDL, but deliberately left with no
caller: Task 10 produced the ordinary transaction artifact, Task 11 appended
the engineered cases to that SAME artifact, and only once both had run was
`wave17_transactions.json` final (4,358 rows: 4,095 ordinary + 263
injected). `load_transactions` was written in Task 8, beside `load_parties`,
with the `ON CONFLICT (txn_id) DO UPDATE` discipline already in place, so
Task 12 — the task that calls it — reuses the DDL contract instead of
re-deriving it. `main()` below now calls it, asserting the loaded count
equals the artifact's transaction count.

## `load_alerts` / `load_alert_links` — Task 12

Load `sources/screening/wave17_alerts.json` (`generators/generate_aml_alerts.py`)
into `aml_alert` and `aml_alert_link`. No FK from `aml_alert.case_id` to
anything — cases live only in `wave17_cases.json` and are never loaded into
a Postgres table by this plan (Global Constraints).

## `load_projection_plans` — Task 16

Reads `sources/screening/wave17_projection.json` and upserts the three
`aml_projection_plan` rows (`l1`, `l2`, `examiner`). Each `elements` array
NAMES what that perspective assembles — envelope floor 6 requires the three
to differ in assembled CONTENT, not a display flag. Full rationale for every
element chosen and rejected -- including WHY `case_id`, a per-alert
`filing_status` and an `is_genuine` boolean were each rejected for `l1` on
SAR-confidentiality grounds, which is a legal constraint and not a style
choice -- is in `docs/ccf_dataprep_v2.md`, "2026-08-25 — Wave 17 Task 16:
projection plans for three perspectives". That is the durable home; the
SDD `task-16-report.md` this used to cite is deleted when the wave closes.
The short version:

  l1        alert_core_facts, disposition_candidates,
            sanctions_screening_result, typology_pattern_summary
  l2        alert_core_facts, counterparty_network, ownership_chain,
            prior_alert_lineage, sar_filing_history, typology_pattern_summary
  examiner  everything l2 has, plus disposition_candidates,
            policy_version_attribution, reasoning_trail,
            sanctions_screening_result

`l1` is the perspective this product's SAR-confidentiality property (Task
15) binds absolutely: no `sar_classification` row names `l1` in
`visible_to_perspectives` at all. So `l1`'s element list carries no
SAR-related name — not `sar_filing_history`, not `sar_id`, and not
`case_id`. `l2` is NOT the blind perspective: it is excluded from the
`confidential` SARs and sees every other one, so `sar_filing_history`
appears in both `l2` and `examiner`'s lists; the actual per-alert filtering
by `visible_to_perspectives` is a read this loader does not perform, it only
names the element that read resolves.

Two figures used to live in this paragraph — a SAR count and a
confidential/visible split — and both were refuted when Task 15's fix rounds
re-selected the filing half. Deliberately not restated. The source is SQLite
`sar_classification`; `validators/aml_typology.py` recomputes and prints the
live numbers on every run.

**Why `case_id` is excluded from `l1` even though a `case_id` no longer
implies a SAR.** Wave 17's engineered cases split into a filed and an
unfiled half, so the old "every alert carrying a `case_id` traces to a
SAR-bearing case" justification is false. The exclusion stands for a
different reason, set out in full beside `ccf.aml.SAR_REVEALING_ELEMENT_NAMES`:
`case_id` identifies WHICH engineered case an alert belongs to, and
narrowing the rule to only the case ids that currently file would require
`l1`'s own plan-builder to consult `sar_classification` to know which those
are — the very departmental-store reach `l1` must never make.

`aml_projection_plan` gained a `provenance` column here (Task 8 created the
table with only `perspective` / `elements`). The `ALTER TABLE ADD COLUMN IF
NOT EXISTS` below covers an estate that already ran Task 8's loader; the
`CREATE TABLE` literal covers a fresh one — the same two-statement pattern
Wave 11b used for `signal_weight.decay_days`. Both carry
`DEFAULT 'synthetic — internal'`: the widening was safe only because the
table happened to be empty when Task 16 first ran it, which is a property
of that day rather than of the DDL. Every row carries that one constant, so
the default costs nothing and makes the `NOT NULL` widening permanently
safe.

Idempotent: `ON CONFLICT (perspective) DO UPDATE`, same discipline as
every other table here.

    uv run loaders/load_postgres_wave17.py --dry-run
    uv run loaders/load_postgres_wave17.py

Idempotent: `load_parties` upserts on `party_id`; `load_transactions` on
`txn_id`; `load_alerts` on `alert_id`; `load_alert_links` on
`(alert_id, related_alert_id)`; `load_projection_plans` on `perspective`.
No DELETE, no TRUNCATE, ever.
"""

from __future__ import annotations

import argparse
import json

from ccf.aml import SAR_REVEALING_ELEMENT_NAMES, is_psc_key
from ccf.config import PG_SCHEMA_V2, REPO_ROOT, assert_v2_schema, pg_connect

SCREEN = REPO_ROOT / "sources" / "screening"
S = PG_SCHEMA_V2

DDL = f"""
CREATE TABLE IF NOT EXISTS "{S}".aml_party (
    party_id              TEXT PRIMARY KEY,
    legal_name             TEXT NOT NULL,
    syn_lei                 TEXT NOT NULL,
    jurisdiction             TEXT NOT NULL,
    party_kind               TEXT NOT NULL,
    incorporated             TEXT NOT NULL,
    provenance               TEXT NOT NULL,
    -- Task 9 populates this. `load_parties` below never sets it (not even
    -- to NULL) so a re-run of this loader after Task 9 has run cannot reset
    -- it. Pre-flight ruling, task-8-brief.md.
    beneficial_owner_key    TEXT NULL,
    -- Populated HERE, from the artifact, on the one declared party
    -- (AMLP-0069). NULL on the other 200. See module docstring.
    ofac_near_match          JSONB NULL
);

CREATE TABLE IF NOT EXISTS "{S}".aml_transaction (
    txn_id        TEXT PRIMARY KEY,
    from_party    TEXT NOT NULL,
    to_party      TEXT NOT NULL,
    amount_usd    NUMERIC NOT NULL,
    value_date    TEXT NOT NULL,
    channel       TEXT NOT NULL,
    provenance    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS "{S}".aml_alert (
    alert_id       TEXT PRIMARY KEY,
    subject_party   TEXT NOT NULL,
    raised_at        TEXT NOT NULL,
    -- Cases live in sources/screening/wave17_cases.json and are never
    -- loaded into a Postgres table by this plan. No FK here — one would
    -- fail at load time. Global Constraints / task-8 instructions.
    case_id           TEXT NULL,
    -- "trigger" is a non-reserved keyword in PostgreSQL. Quoted everywhere
    -- it is named so this table survives a server upgrade that tightens
    -- the reserved-word list, not just today's PostgreSQL.
    "trigger"          TEXT NOT NULL,
    provenance         TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS "{S}".aml_alert_link (
    alert_id            TEXT NOT NULL,
    related_alert_id     TEXT NOT NULL,
    relation              TEXT NOT NULL,
    PRIMARY KEY (alert_id, related_alert_id)
);

-- Own table, not a widening of Wave 7's `projection_plan` -- see module
-- docstring. `perspective` (l1 / l2 / examiner) is the natural key, per
-- the brief's Interfaces section. `provenance` is in the CREATE literal
-- for a fresh install; the ALTER below covers an estate where Task 8
-- already ran this DDL without it.
--
-- The DEFAULT is not decoration. Without it, `ADD COLUMN ... NOT NULL`
-- succeeds only while the table happens to be EMPTY -- true the day Task
-- 16 ran, and false forever after. An estate that loads the three rows,
-- then replays this DDL from a checkout that predates the column, would
-- hit `column "provenance" ... contains null values` and the DDL would
-- stop. Every row carries this one constant (Global Constraints: every
-- projection plan in this wave is synthetic), so the default costs
-- nothing and makes the widening permanently safe rather than contingent
-- on load order. `load_projection_plans` still writes the value
-- explicitly on every row; the default only covers the widening itself.
CREATE TABLE IF NOT EXISTS "{S}".aml_projection_plan (
    perspective    TEXT PRIMARY KEY,
    elements        JSONB NOT NULL,
    provenance      TEXT NOT NULL DEFAULT 'synthetic — internal'
);
ALTER TABLE "{S}".aml_projection_plan
    ADD COLUMN IF NOT EXISTS provenance TEXT NOT NULL
        DEFAULT 'synthetic — internal';
-- `ADD COLUMN IF NOT EXISTS` is a no-op where Task 16 already added the
-- column WITHOUT a default, so the line above cannot retrofit one. This
-- does, and runs after it, so the column always exists by the time it is
-- reached. Idempotent: setting the same default twice is a no-op.
ALTER TABLE "{S}".aml_projection_plan
    ALTER COLUMN provenance SET DEFAULT 'synthetic — internal';
"""


def load_parties(cur, parties: list[dict]) -> int:
    """Upsert `aml_party` rows from the frozen 201-party artifact.

    Owns every column it writes (`party_id` through `ofac_near_match`) and
    touches nothing else — `beneficial_owner_key` is never named in the
    INSERT column list or the ON CONFLICT SET clause, so Task 9's value
    survives a re-run of this function untouched.
    """
    rows = [
        (
            p["party_id"],
            p["legal_name"],
            p["syn_lei"],
            p["jurisdiction"],
            p["party_kind"],
            p["incorporated"],
            p["provenance"],
            json.dumps(p["ofac_near_match"]) if p.get("ofac_near_match") else None,
        )
        for p in parties
    ]
    cur.executemany(
        f'INSERT INTO "{S}".aml_party '
        "(party_id, legal_name, syn_lei, jurisdiction, party_kind, "
        " incorporated, provenance, ofac_near_match) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s) "
        "ON CONFLICT (party_id) DO UPDATE SET "
        "legal_name=EXCLUDED.legal_name, "
        "syn_lei=EXCLUDED.syn_lei, "
        "jurisdiction=EXCLUDED.jurisdiction, "
        "party_kind=EXCLUDED.party_kind, "
        "incorporated=EXCLUDED.incorporated, "
        "provenance=EXCLUDED.provenance, "
        "ofac_near_match=EXCLUDED.ofac_near_match",
        rows,
    )
    return len(rows)


def load_transactions(cur, txns: list[dict]) -> int:
    """Upsert `aml_transaction` rows. Called by `main()` below (Task 12) now
    that `wave17_transactions.json` (Task 10 + Task 11) is final.

    Row shape, from Task 10's interface: txn_id, from_party, to_party,
    amount_usd, value_date, channel, provenance.
    """
    rows = [
        (
            t["txn_id"],
            t["from_party"],
            t["to_party"],
            t["amount_usd"],
            t["value_date"],
            t["channel"],
            t["provenance"],
        )
        for t in txns
    ]
    cur.executemany(
        f'INSERT INTO "{S}".aml_transaction '
        "(txn_id, from_party, to_party, amount_usd, value_date, channel, "
        " provenance) VALUES (%s,%s,%s,%s,%s,%s,%s) "
        "ON CONFLICT (txn_id) DO UPDATE SET "
        "from_party=EXCLUDED.from_party, "
        "to_party=EXCLUDED.to_party, "
        "amount_usd=EXCLUDED.amount_usd, "
        "value_date=EXCLUDED.value_date, "
        "channel=EXCLUDED.channel, "
        "provenance=EXCLUDED.provenance",
        rows,
    )
    return len(rows)


def load_alerts(cur, alerts: list[dict]) -> int:
    """Upsert `aml_alert` rows -- Task 12. `"trigger"` is quoted (it is a
    non-reserved SQL keyword) in both the column list and the ON CONFLICT
    SET clause, matching the DDL's own quoting.

    Row shape, from the Interfaces section: alert_id, subject_party,
    raised_at, case_id (nullable -- noise alerts carry None), trigger,
    provenance.
    """
    rows = [
        (
            a["alert_id"],
            a["subject_party"],
            a["raised_at"],
            a.get("case_id"),
            a["trigger"],
            a["provenance"],
        )
        for a in alerts
    ]
    cur.executemany(
        f'INSERT INTO "{S}".aml_alert '
        '(alert_id, subject_party, raised_at, case_id, "trigger", '
        " provenance) VALUES (%s,%s,%s,%s,%s,%s) "
        "ON CONFLICT (alert_id) DO UPDATE SET "
        "subject_party=EXCLUDED.subject_party, "
        "raised_at=EXCLUDED.raised_at, "
        "case_id=EXCLUDED.case_id, "
        '"trigger"=EXCLUDED."trigger", '
        "provenance=EXCLUDED.provenance",
        rows,
    )
    return len(rows)


def load_alert_links(cur, links: list[dict]) -> int:
    """Upsert `aml_alert_link` rows -- Task 12. Primary key is the pair
    `(alert_id, related_alert_id)`, so re-running only ever updates
    `relation` on an existing pair, never duplicates one."""
    rows = [
        (l["alert_id"], l["related_alert_id"], l["relation"])
        for l in links
    ]
    cur.executemany(
        f'INSERT INTO "{S}".aml_alert_link '
        "(alert_id, related_alert_id, relation) VALUES (%s,%s,%s) "
        "ON CONFLICT (alert_id, related_alert_id) DO UPDATE SET "
        "relation=EXCLUDED.relation",
        rows,
    )
    return len(rows)


def bind_beneficial_owners(cur, bindings: list[dict]) -> int:
    """UPDATE `aml_party.beneficial_owner_key` for the parties named in
    `wave17_ownership.json`. Owns exactly this column -- never writes any
    other `aml_party` field, so it can never collide with `load_parties`.

    Defense in depth (belt and braces with the generator's own check, and
    with the SQL `WHERE person_key LIKE 'PSC-%'` the generator used to
    select these values in the first place): refuses to write anything if
    a single bound key fails `is_psc_key()`. CLAUDE.md rule 2 -- a numeric
    person key here would be a real company's officer entering a
    laundering network.
    """
    bad = [b["beneficial_owner_key"] for b in bindings
           if not is_psc_key(b["beneficial_owner_key"])]
    if bad:
        raise RuntimeError(
            f"refusing to bind: non-PSC beneficial owner key(s) found: {bad[:5]}")
    rows = [(b["beneficial_owner_key"], b["party_id"]) for b in bindings]
    cur.executemany(
        f'UPDATE "{S}".aml_party SET beneficial_owner_key = %s '
        "WHERE party_id = %s",
        rows,
    )
    return len(rows)


REQUIRED_PERSPECTIVES = {"l1", "l2", "examiner"}

#: `SAR_REVEALING_ELEMENT_NAMES` is imported from `ccf.aml`, not defined
#: here. It used to be a verbatim copy, kept in sync with the checking copy
#: in `validators/test_aml_typology.py` by a comment asking the next editor
#: to remember -- and this is a legal guard, so a silent divergence between
#: the copy that ENFORCES and the copy that CHECKS is the worst version of
#: that defect. One definition now, in this wave's shared pure-helper
#: module, imported by both. The load-time re-check below is unchanged: the
#: same "defense in depth, re-checked at the point of write" discipline
#: `bind_beneficial_owners` above already uses for `is_psc_key`.


def load_projection_plans(cur, plans: list[dict]) -> int:
    """Upsert `aml_projection_plan` rows -- Task 16. `perspective` is the
    primary key (Task 8's DDL); `elements` names what that perspective
    assembles, `provenance` is uniformly `synthetic — internal` (Global
    Constraints -- every projection plan in this wave is synthetic).

    Refuses to write if `l1` names any SAR-revealing element (see
    `SAR_REVEALING_ELEMENT_NAMES` above). `l1` is the perspective Task 15's
    confidentiality property binds absolutely -- it appears in NO
    `visible_to_perspectives` set at all, where `l2` is excluded only from
    the `confidential` SARs and sees every other one. So this is the one
    perspective this loader will not let drift, even if a future edit to
    the artifact tried to add an element to it.

    A SAR count and a confidential/visible split used to sit in this
    paragraph. They were refuted when Task 15's fix rounds re-selected the
    filing half, and the module docstring above deleted the same pair for
    the same reason. Deliberately not restated here either. The source is
    SQLite `sar_classification`; `validators/aml_typology.py` recomputes and
    prints the live figures on every run.
    """
    by_perspective = {p["perspective"]: p for p in plans}
    missing = REQUIRED_PERSPECTIVES - set(by_perspective)
    if missing:
        raise RuntimeError(f"projection plan artifact missing perspective(s): "
                            f"{sorted(missing)}")

    l1_elements = set(by_perspective["l1"]["elements"])
    leaked = l1_elements & SAR_REVEALING_ELEMENT_NAMES
    if leaked:
        raise RuntimeError(
            f"refusing to load: l1 projection plan names SAR-revealing "
            f"element(s) {sorted(leaked)} -- l1 must carry no indication "
            f"a SAR exists (CLAUDE.md rule 2's confidentiality sibling, "
            f"task-16-brief.md)")

    rows = [
        (p["perspective"], json.dumps(sorted(p["elements"])), p["provenance"])
        for p in plans
    ]
    cur.executemany(
        f'INSERT INTO "{S}".aml_projection_plan '
        "(perspective, elements, provenance) VALUES (%s,%s,%s) "
        "ON CONFLICT (perspective) DO UPDATE SET "
        "elements=EXCLUDED.elements, "
        "provenance=EXCLUDED.provenance",
        rows,
    )
    return len(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    doc = json.loads((SCREEN / "wave17_parties.json").read_text())
    parties = doc["parties"]
    ownership_doc = json.loads((SCREEN / "wave17_ownership.json").read_text())
    bindings = ownership_doc["bindings"]
    txn_doc = json.loads((SCREEN / "wave17_transactions.json").read_text())
    txns = txn_doc["transactions"]
    alert_doc = json.loads((SCREEN / "wave17_alerts.json").read_text())
    alerts = alert_doc["alerts"]
    links = alert_doc["links"]
    projection_doc = json.loads((SCREEN / "wave17_projection.json").read_text())
    plans = projection_doc["plans"]

    n_ofac = sum(1 for p in parties if p.get("ofac_near_match"))
    n_genuine = sum(1 for a in alerts if a.get("case_id"))

    print(f"Wave 17 Task 8/9/12/16 — load into {S}\n")
    print(f"  aml_party            {len(parties):>6}   "
          f"({n_ofac} carrying ofac_near_match)")
    print(f"  aml_transaction      {len(txns):>6}   "
          f"(Task 10 ordinary + Task 11 engineered)")
    print(f"  aml_alert            {len(alerts):>6}   "
          f"({n_genuine} genuine, {len(alerts) - n_genuine} noise)")
    print(f"  aml_alert_link       {len(links):>6}")
    print(f"  aml_projection_plan  {len(plans):>6}   "
          f"({', '.join(sorted(p['perspective'] for p in plans))})")
    print(f"  beneficial_owner_key {len(bindings):>6}   "
          f"(Task 9 — shell/individual_owned parties bound to the "
          f"existing PSC-*/bo_chain island)")

    if len(parties) != 201:
        raise RuntimeError(
            f"refusing to load: expected the frozen 201-party population, "
            f"found {len(parties)}"
        )
    if n_ofac != 1:
        raise RuntimeError(
            f"refusing to load: expected exactly 1 party carrying "
            f"ofac_near_match, found {n_ofac}"
        )
    if {p["perspective"] for p in plans} != REQUIRED_PERSPECTIVES:
        raise RuntimeError(
            f"refusing to load: projection plan artifact does not name "
            f"exactly {sorted(REQUIRED_PERSPECTIVES)}, "
            f"found {sorted(p['perspective'] for p in plans)}")

    if args.dry_run:
        print("\n  [dry-run] no DDL executed, no rows written")
        return 0

    assert_v2_schema(S)

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(DDL)
        n = load_parties(cur, parties)
        n_bound = bind_beneficial_owners(cur, bindings)
        n_txn = load_transactions(cur, txns)
        assert n_txn == len(txns), (
            f"loaded {n_txn} transactions, artifact has {len(txns)}")
        n_alerts = load_alerts(cur, alerts)
        assert n_alerts == len(alerts), (
            f"loaded {n_alerts} alerts, artifact has {len(alerts)}")
        n_links = load_alert_links(cur, links)
        assert n_links == len(links), (
            f"loaded {n_links} alert links, artifact has {len(links)}")
        n_plans = load_projection_plans(cur, plans)
        assert n_plans == len(plans), (
            f"loaded {n_plans} projection plans, artifact has {len(plans)}")
        print(f"\n  loaded: aml_party {n}, beneficial_owner_key {n_bound}, "
              f"aml_transaction {n_txn}, aml_alert {n_alerts}, "
              f"aml_alert_link {n_links}, aml_projection_plan {n_plans}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
