-- The CI container's schema for `examples/cp-01-counterparty-reference-snapshot`.
--
-- WHAT THIS IS. The five tables the example reads, declared column for column
-- and type for type as the real counterparty store declares them, GENERATED
-- from `ccf_v2`'s own `information_schema` rather than hand-transcribed. The
-- SCHEMA NAME matches too, so the example's own SQL runs unchanged against both
-- substrates — one code path, not two. A CI schema that drifted from the real
-- one would make the leg prove something other than what runs locally.
--
-- WHY IT LIVES IN THE TEST TREE. `24-CONTEXT.md` `D-15` accepts a real cost so
-- that the example points at a real store rather than a shipped copy; a fixture
-- under `examples/` would become exactly that shipped copy. `D-27`: the fixture
-- is SEEDED BY THE TEST, never committed as a database.
--
-- ADDITIVE ONLY. It creates the `ccf_v2` schema inside the existing CI database
-- and touches no other schema. cp-00's fixture creates the same schema and two
-- of its tables; both are `if not exists`, so the two modules converge rather
-- than collide. `legal_entity` is shared between them BY DESIGN — it is the
-- same table in the real estate — and the two fixtures seed disjoint LEIs.

create schema if not exists ccf_v2;

create table if not exists ccf_v2.legal_entity (
    lei varchar(20) not null,
    legal_name text not null,
    legal_jurisdiction text,
    entity_status text,
    registration_status text,
    legal_form text,
    legal_address_country text,
    legal_address_city text,
    legal_address_region text,
    provenance text not null,
    retrieved_at date not null,
    hq_address_country text,
    hq_address_city text,
    hq_address_region text
);

create table if not exists ccf_v2.internal_client (
    internal_client_id text not null,
    legal_name text not null,
    legal_jurisdiction text,
    legal_form text,
    legal_address_country text,
    legal_address_city text,
    legal_address_region text,
    hq_address_country text,
    hq_address_city text,
    hq_address_region text,
    kyc_last_refresh date not null,
    kyc_cycle_days integer not null,
    kyc_next_due date not null,
    freshness_ceiling_days integer not null,
    provenance text not null,
    source text not null,
    retrieved_at date not null
);

create table if not exists ccf_v2.crosswalk (
    internal_client_id text not null,
    lei varchar(20),
    cik integer,
    ticker text,
    provenance text not null,
    source text not null,
    created_at timestamptz not null
);

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
alter table ccf_v2.legal_entity add column if not exists entity_status text;
alter table ccf_v2.legal_entity add column if not exists registration_status text;
alter table ccf_v2.legal_entity add column if not exists legal_form text;
alter table ccf_v2.legal_entity add column if not exists legal_address_country text;
alter table ccf_v2.legal_entity add column if not exists legal_address_city text;
alter table ccf_v2.legal_entity add column if not exists legal_address_region text;
alter table ccf_v2.legal_entity add column if not exists hq_address_country text;
alter table ccf_v2.legal_entity add column if not exists hq_address_city text;
alter table ccf_v2.legal_entity add column if not exists hq_address_region text;
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
