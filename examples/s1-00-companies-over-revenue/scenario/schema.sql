-- The source system, as it exists before any fabric does.
--
-- THIS IS NOT CCF. It is the table an adopter already has, and it is the whole
-- of what this example borrows from the world. You delete this file for your
-- own product and point the deployment at whatever you already run.
--
-- Four columns, and the fourth is the one this example is about: `last_updated`
-- is what CCF turns into a measured staleness figure. A plain SELECT over this
-- table returns the first three and tells you nothing about the fourth.
create table if not exists companies (
    id           bigint      primary key,
    name         text        not null,
    revenue      numeric     not null,
    last_updated timestamptz not null
);
