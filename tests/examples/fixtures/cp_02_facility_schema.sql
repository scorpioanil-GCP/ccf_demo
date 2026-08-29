-- The CI container's schema for `examples/cp-02-facility-terms-snapshot`.
--
-- WHAT THIS IS. The four tables this example reads that no earlier fixture
-- creates, declared column for column and type for type as the real facility
-- store declares them, GENERATED from `ccf_v2`'s own `information_schema`
-- rather than hand-transcribed. The SCHEMA NAME matches too, so the example's
-- own SQL runs unchanged against both substrates — one code path, not two. A CI
-- schema that drifted from the real one would make the leg prove something
-- other than what runs locally.
--
-- WHY IT LIVES IN THE TEST TREE. `24-CONTEXT.md` `D-15` accepts a real cost so
-- that the example points at a real store rather than a shipped copy; a fixture
-- under `examples/` would become exactly that shipped copy. `D-27`: the fixture
-- is SEEDED BY THE TEST, never committed as a database.
--
-- ADDITIVE ONLY, AND IT SHARES THREE TABLES WITH cp-00 AND cp-01 BY DESIGN.
-- `legal_entity`, `principal` and `principal_jurisdiction` are the same tables
-- in the real estate, so every statement here is `if not exists` and the row
-- fixture uses `on conflict do nothing` for them. Unlike cp-00 and cp-01, whose
-- LEIs are disjoint, THIS PRODUCT'S BORROWERS LEGITIMATELY OVERLAP cp-01's —
-- AVIS BUDGET GROUP is cp-01's demonstration anchor and this product's
-- inverted-date-pair borrower. Seeding them disjointly would have meant
-- inventing a second Avis.

create schema if not exists ccf_v2;

-- Shared with cp-00 and cp-01, AND THE THREE FIXTURES DECLARE IT DIFFERENTLY.
-- cp-00's has `source` and a primary key on `lei`; cp-01's has neither, and carries
-- address columns cp-00 does not. Every statement is `if not exists`, so WHICHEVER
-- MODULE RUNS FIRST WINS and the surviving column set depends on pytest's collection
-- order — which is exactly what broke when this module first ran after cp-01's:
-- `column "source" of relation "legal_entity" does not exist`.
--
-- So this declares only what cp-02 READS, and the row fixture inserts only the columns
-- all three definitions share. It never widens the table, because widening it would
-- make the other two modules' behavior depend on whether this one ran.
create table if not exists ccf_v2.legal_entity (
    lei varchar(20) not null,
    legal_name text not null,
    legal_jurisdiction text,
    provenance text not null,
    retrieved_at date not null
);

create table if not exists ccf_v2.facility (
    facility_id text not null,
    borrower_lei char(20) not null,
    facility_type text not null,
    commitment_amount numeric,
    currency char(3) not null,
    effective_date date,
    maturity_date date,
    administrative_agent text,
    syndicated boolean not null,
    amendment_count integer not null,
    is_amended_restated boolean not null,
    pricing_grid jsonb,
    outstanding_balance numeric,
    undrawn_availability numeric,
    balance_as_of date,
    internal_risk_rating text,
    -- PRESENT IN THE SCHEMA AND NEVER READ BY THIS EXAMPLE. §C.4 trap 3: the
    -- character offsets into the credit agreement sit in the same row as the
    -- terms, so the tier boundary is one the DATA does not enforce. They are
    -- carried into the fixture DELIBERATELY — a gate asserting that no source
    -- pointer reaches the payload proves nothing against a schema that has none
    -- to leak.
    source_accession text,
    source_document text,
    source_offsets jsonb,
    provenance_public text not null,
    provenance_internal text not null,
    source text not null,
    retrieved_at date not null
);

create table if not exists ccf_v2.debt_reconciliation (
    lei text not null,
    committed numeric not null,
    reported_debt numeric not null,
    share numeric not null,
    plausible boolean not null
);

-- Shared with cp-01.
create table if not exists ccf_v2.principal (
    principal_id text not null,
    name text not null,
    side text not null,
    perspective text not null,
    sees_mnpi boolean not null,
    provenance text not null,
    sees_need_to_know boolean not null,
    sees_eu_person_data boolean not null
);

create table if not exists ccf_v2.principal_jurisdiction (
    principal_id text not null,
    jurisdiction_prefix text not null,
    provenance text not null
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
alter table ccf_v2.legal_entity add column if not exists legal_jurisdiction text;
alter table ccf_v2.legal_entity add column if not exists provenance text;
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
