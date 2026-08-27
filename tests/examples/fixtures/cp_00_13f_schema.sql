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
