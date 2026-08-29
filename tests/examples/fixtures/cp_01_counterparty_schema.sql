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
