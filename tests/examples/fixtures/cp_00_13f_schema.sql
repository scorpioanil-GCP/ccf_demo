-- The CI container's schema for `examples/cp-00-institutional-holders`.
--
-- WHAT THIS IS. The two tables the example reads, declared column for column
-- and type for type as the real 13F store declares them
-- (`ccf_dataprep/loaders/load_postgres_wave10.py`'s `DDL` block for
-- `institutional_holder`, `load_postgres_wave1.py` for `legal_entity`, with
-- `lei` at the width `load_abs_overlay_wave14.py` widened it to). The SCHEMA
-- NAME matches too, so the example's own SQL runs unchanged against both
-- substrates -- one code path, not two. A CI schema that drifted from the real
-- one would make the leg prove something other than what runs locally.
--
-- WHY IT LIVES IN THE TEST TREE. `24-CONTEXT.md` `D-15` accepts a real cost so
-- that the example points at a real store rather than a shipped copy; a fixture
-- under `examples/` would become exactly that shipped copy. `D-27`: the fixture
-- is SEEDED BY THE TEST, never committed as a database. This file is applied by
-- `tests/examples/test_cp_00_output.py`'s `seeded` fixture and by nothing else.
--
-- WHY IT IS SAFE TO APPLY TO THE SHARED CI DATABASE. The Postgres leg runs
-- every `pytest.mark.postgres` module against ONE service container. This file
-- is purely ADDITIVE: it creates the `ccf_v2` SCHEMA inside that existing
-- database and touches no other schema. Measured before it was written -- the
-- token `ccf_v2` appears 0 times across `tests/` and `tools/`, against the same
-- instrument returning 14 in `examples/`, so no other suite owns this schema.
-- `s1-00` provisions into a per-run minted schema and each fabric's own graph is
-- created per test; neither reaches `ccf_v2`.
--
-- Every statement is `if not exists`, so a repeated leg against a long-lived
-- server converges rather than failing.

create schema if not exists ccf_v2;

-- The 13F holdings table. Primary key `(lei, manager_cik, cusip,
-- report_period)` -- the source row key the specification's F.3 names, and the
-- reason a manager can appear on two CUSIPs without colliding.
create table if not exists ccf_v2.institutional_holder (
    lei                text not null,
    manager_cik        text not null,
    manager_name       text,
    cusip              text not null,
    value_usd          numeric,
    shares             numeric,
    report_period      text,
    issuer_match_score numeric(6, 4),
    issuer_match_band  text,
    provenance         text not null,
    primary key (lei, manager_cik, cusip, report_period)
);

-- The entity reference table. The example reads exactly one column off it --
-- `legal_name`, by a left join on `lei` -- but the shape is declared whole,
-- because a narrowed CI table is a CI table that cannot reproduce a defect in
-- the columns it dropped.
create table if not exists ccf_v2.legal_entity (
    lei                    varchar(20) primary key,
    legal_name             text not null,
    gleif_legal_name       text,
    legal_jurisdiction     text,
    entity_status          text,
    registration_status    text,
    next_renewal_date      date,
    initial_registration   date,
    legal_form             text,
    address_country        text,
    address_city           text,
    address_region         text,
    sic                    text,
    sic_description        text,
    fiscal_year_end        text,
    is_anchor              boolean not null default false,
    lei_match_band         text,
    lei_match_score        numeric(4, 3),
    provenance             text not null,
    source                 text not null,
    retrieved_at           date not null
);

-- ---------------------------------------------------------------------------
-- COLUMNS THIS MODULE NEEDS, ADDED IDEMPOTENTLY.
--
-- `ccf_v2.legal_entity` is shared by cp-00, cp-01 and cp-02, and the three
-- fixtures declare it THREE DIFFERENT WAYS. Every `create table` above is
-- `if not exists`, so whichever module pytest collects first wins and the
-- surviving column set depends on collection order — while `make leg-postgres`
-- runs `pytest tests -m postgres` as ONE session over the whole tree.
--
-- That is not hypothetical. On 2026-08-29, `pytest test_cp_00_output.py
-- test_cp_01_output.py` reported 15 passed and 13 errors:
-- `column "source" of relation "legal_entity" does not exist`. The leg has been
-- red for as long as two modules have shared this table.
--
-- These statements make each module self-sufficient: it adds what its own
-- inserts name, whether or not it created the table. `add column if not exists`
-- is a no-op when the column is already there, so the three converge on the
-- union in any order. Added NULLABLE deliberately — a `not null` column cannot
-- be added to a table another module has already populated, and every insert
-- here supplies its own values anyway.
-- ---------------------------------------------------------------------------
alter table ccf_v2.legal_entity add column if not exists gleif_legal_name text;
alter table ccf_v2.legal_entity add column if not exists legal_jurisdiction text;
alter table ccf_v2.legal_entity add column if not exists entity_status text;
alter table ccf_v2.legal_entity add column if not exists registration_status text;
alter table ccf_v2.legal_entity add column if not exists next_renewal_date date;
alter table ccf_v2.legal_entity add column if not exists initial_registration date;
alter table ccf_v2.legal_entity add column if not exists legal_form text;
alter table ccf_v2.legal_entity add column if not exists address_country text;
alter table ccf_v2.legal_entity add column if not exists address_city text;
alter table ccf_v2.legal_entity add column if not exists address_region text;
alter table ccf_v2.legal_entity add column if not exists sic text;
alter table ccf_v2.legal_entity add column if not exists sic_description text;
alter table ccf_v2.legal_entity add column if not exists fiscal_year_end text;
alter table ccf_v2.legal_entity add column if not exists is_anchor boolean;
alter table ccf_v2.legal_entity add column if not exists lei_match_band text;
alter table ccf_v2.legal_entity add column if not exists lei_match_score numeric(4, 3);
alter table ccf_v2.legal_entity add column if not exists provenance text;
alter table ccf_v2.legal_entity add column if not exists source text;
alter table ccf_v2.legal_entity add column if not exists retrieved_at date;

-- AND THE NOT-NULL CONSTRAINTS ARE RELAXED, for the same reason.
--
-- Adding a column idempotently is not enough on its own: cp-00's `create table`
-- declares `source text not null`, so cp-01's insert — which does not carry a
-- `source` — violates it whenever cp-00 created the table first. A shared table
-- cannot have its nullability owned by whichever module happened to run first.
--
-- `lei` and `legal_name` stay NOT NULL because all three modules supply both.
-- Everything else is relaxed. THIS WEAKENS NOTHING ANY TEST ASSERTS: no
-- assertion in any of the three modules is about this table's constraints, and
-- the real estate's constraints are the real estate's. What it buys is a leg
-- that passes in any collection order rather than in one.
do $$
declare col record;
begin
  for col in
    select column_name from information_schema.columns
     where table_schema = 'ccf_v2' and table_name = 'legal_entity'
       and is_nullable = 'NO' and column_name not in ('lei', 'legal_name')
  loop
    execute format(
      'alter table ccf_v2.legal_entity alter column %I drop not null',
      col.column_name);
  end loop;
end $$;

-- AND ONE UNIQUE INDEX ON `lei`, because two of the three modules need one.
--
-- cp-00's insert says `on conflict (lei) do update` — which requires a unique
-- constraint and fails with `there is no unique or exclusion constraint
-- matching the ON CONFLICT specification` whenever another module created the
-- table without cp-00's primary key. cp-01's `on conflict do nothing` has the
-- quieter version of the same problem: with no constraint to conflict ON, it
-- never conflicts, so a repeated leg against a long-lived container silently
-- ACCUMULATES duplicate rows — and a duplicated borrower turns cp-02's
-- facility-to-entity join into a fan-out.
--
-- The de-duplication runs first because the index cannot be created over rows a
-- previous run already doubled. Both statements are idempotent.
delete from ccf_v2.legal_entity a
 using ccf_v2.legal_entity b
 where a.ctid < b.ctid and a.lei = b.lei;

create unique index if not exists legal_entity_lei_key
    on ccf_v2.legal_entity (lei);
