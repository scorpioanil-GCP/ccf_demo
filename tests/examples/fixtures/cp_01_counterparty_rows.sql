-- Rows for `examples/cp-01-counterparty-reference-snapshot`, seeded by
-- `tests/examples/test_cp_01_output.py` and by nothing else (`D-27`).
--
-- GENERATED FROM THE LIVE ESTATE on 2026-08-29, not hand-transcribed, so the
-- fixture and the local run cannot disagree about what the store holds. Every
-- row below is a copy of a real row in `ccf_v2`.
--
-- WHAT EACH ROW IS FOR — Standard §6's first-build volumetrics, as a fixture:
--
--   AVIS BUDGET GROUP    the demonstration anchor. US-DE, ISSUED, and its
--                        legal address (WILMINGTON) differs from its
--                        headquarters (Parsippany) — the Delaware pattern that
--                        §C.4 trap 1 exists to make visible. Carries crosswalk
--                        CLI-000008, so §C.3's correlation key is exercised.
--                        Loaded 2026-08-16, so it is LIVE at the pinned
--                        asked_at and the TTL gate admits it.
--   B&G Foods            registration LAPSED — `CPR-G01`'s fixture. Same
--                        jurisdiction and load date as the anchor, so the only
--                        thing that differs between them is the status.
--   CLI-000101           a no-LEI internal client. `CPR-G03`'s lower freshness
--                        ceiling, `CPR-G07`'s second identity authority, and
--                        `CPR-G09`'s TTL refusal all act on this row.
--   4 principals         `CPR-G02` and `CPR-G04`. The anchor is US-DE, so
--                        PRIN-COV-001 (US) and PRIN-RES-002 (US CA GB) see it
--                        while PRIN-KYC-004 (EU) and PRIN-TRD-003 (GB HK JP SG)
--                        do not — two answers and two silences from one row.
--
-- ONE CASE HAS NO INSTANCE HERE, and it is recorded rather than faked:
-- `CPR-G08` needs a principal whose grant set matches NO entity, and all four
-- real principals see at least one. Spec §F.3 registers it as owed
-- (`[TBC — ccf_dataprep]`, §F.2 row 20).
--
-- `on conflict do nothing` throughout, so a repeated leg against a long-lived
-- server converges rather than failing.

insert into ccf_v2.legal_entity (lei,legal_name,legal_jurisdiction,entity_status,registration_status,legal_form,legal_address_country,legal_address_city,legal_address_region,provenance,retrieved_at,hq_address_country,hq_address_city,hq_address_region) values ('529900E95812SYWMCE44','AVIS BUDGET GROUP, INC.','US-DE','ACTIVE','ISSUED','XTIQ','US','WILMINGTON','US-DE','public','2026-08-16','US','Parsippany','US-NJ') on conflict do nothing;
insert into ccf_v2.legal_entity (lei,legal_name,legal_jurisdiction,entity_status,registration_status,legal_form,legal_address_country,legal_address_city,legal_address_region,provenance,retrieved_at,hq_address_country,hq_address_city,hq_address_region) values ('549300TRW1LZMDJZAQ78','B&G Foods, Inc.','US-DE','ACTIVE','LAPSED','XTIQ','US','Wilmington','US-DE','public','2026-08-16','US','Parsippany-Troy Hills','US-NJ') on conflict do nothing;

insert into ccf_v2.internal_client (internal_client_id,legal_name,legal_jurisdiction,legal_form,legal_address_country,legal_address_city,legal_address_region,hq_address_country,hq_address_city,hq_address_region,kyc_last_refresh,kyc_cycle_days,kyc_next_due,freshness_ceiling_days,provenance,source,retrieved_at) values ('CLI-000101','Underhill Medical Devices LLC','US-TX','LLC','US',null,'US-TX','US',null,'US-TX','2026-02-23',270,'2026-11-20',270,'synthetic — internal','internal client master (invented: public sources cannot supply a no-LEI entity)','2026-08-28') on conflict do nothing;

insert into ccf_v2.crosswalk (internal_client_id,lei,cik,ticker,provenance,source,created_at) values ('CLI-000101',null,null,null,'synthetic — internal','internal client master: privately held, no LEI exists','2026-08-29 03:17:19.925940+00:00') on conflict do nothing;
insert into ccf_v2.crosswalk (internal_client_id,lei,cik,ticker,provenance,source,created_at) values ('CLI-000008','529900E95812SYWMCE44',723612,'CAR','synthetic — internal','generated: no public LEI<->internal-id mapping exists','2026-08-16 19:25:51.165844+00:00') on conflict do nothing;
insert into ccf_v2.crosswalk (internal_client_id,lei,cik,ticker,provenance,source,created_at) values ('CLI-000042','549300TRW1LZMDJZAQ78',1278027,'BGS','synthetic — internal','generated: no public LEI<->internal-id mapping exists','2026-08-16 19:25:51.165844+00:00') on conflict do nothing;

insert into ccf_v2.principal (principal_id,name,side,perspective,sees_mnpi,provenance,sees_need_to_know,sees_eu_person_data) values ('PRIN-COV-001','coverage banker','private','coverage-banker',true,'synthetic — internal',true,false) on conflict do nothing;
insert into ccf_v2.principal (principal_id,name,side,perspective,sees_mnpi,provenance,sees_need_to_know,sees_eu_person_data) values ('PRIN-KYC-004','EU KYC analyst','private','kyc-analyst',false,'synthetic — internal',false,true) on conflict do nothing;
insert into ccf_v2.principal (principal_id,name,side,perspective,sees_mnpi,provenance,sees_need_to_know,sees_eu_person_data) values ('PRIN-RES-002','research analyst','public','research-analyst',false,'synthetic — internal',false,false) on conflict do nothing;
insert into ccf_v2.principal (principal_id,name,side,perspective,sees_mnpi,provenance,sees_need_to_know,sees_eu_person_data) values ('PRIN-TRD-003','trader','public-surveilled','trader',false,'synthetic — internal',false,false) on conflict do nothing;

insert into ccf_v2.principal_jurisdiction (principal_id,jurisdiction_prefix,provenance) values ('PRIN-COV-001','US','synthetic — internal') on conflict do nothing;
insert into ccf_v2.principal_jurisdiction (principal_id,jurisdiction_prefix,provenance) values ('PRIN-KYC-004','AT','synthetic — internal') on conflict do nothing;
insert into ccf_v2.principal_jurisdiction (principal_id,jurisdiction_prefix,provenance) values ('PRIN-KYC-004','BE','synthetic — internal') on conflict do nothing;
insert into ccf_v2.principal_jurisdiction (principal_id,jurisdiction_prefix,provenance) values ('PRIN-KYC-004','DE','synthetic — internal') on conflict do nothing;
insert into ccf_v2.principal_jurisdiction (principal_id,jurisdiction_prefix,provenance) values ('PRIN-KYC-004','ES','synthetic — internal') on conflict do nothing;
insert into ccf_v2.principal_jurisdiction (principal_id,jurisdiction_prefix,provenance) values ('PRIN-KYC-004','HU','synthetic — internal') on conflict do nothing;
insert into ccf_v2.principal_jurisdiction (principal_id,jurisdiction_prefix,provenance) values ('PRIN-KYC-004','IT','synthetic — internal') on conflict do nothing;
insert into ccf_v2.principal_jurisdiction (principal_id,jurisdiction_prefix,provenance) values ('PRIN-KYC-004','LU','synthetic — internal') on conflict do nothing;
insert into ccf_v2.principal_jurisdiction (principal_id,jurisdiction_prefix,provenance) values ('PRIN-KYC-004','NL','synthetic — internal') on conflict do nothing;
insert into ccf_v2.principal_jurisdiction (principal_id,jurisdiction_prefix,provenance) values ('PRIN-KYC-004','SE','synthetic — internal') on conflict do nothing;
insert into ccf_v2.principal_jurisdiction (principal_id,jurisdiction_prefix,provenance) values ('PRIN-RES-002','CA','synthetic — internal') on conflict do nothing;
insert into ccf_v2.principal_jurisdiction (principal_id,jurisdiction_prefix,provenance) values ('PRIN-RES-002','GB','synthetic — internal') on conflict do nothing;
insert into ccf_v2.principal_jurisdiction (principal_id,jurisdiction_prefix,provenance) values ('PRIN-RES-002','US','synthetic — internal') on conflict do nothing;
insert into ccf_v2.principal_jurisdiction (principal_id,jurisdiction_prefix,provenance) values ('PRIN-TRD-003','GB','synthetic — internal') on conflict do nothing;
insert into ccf_v2.principal_jurisdiction (principal_id,jurisdiction_prefix,provenance) values ('PRIN-TRD-003','HK','synthetic — internal') on conflict do nothing;
insert into ccf_v2.principal_jurisdiction (principal_id,jurisdiction_prefix,provenance) values ('PRIN-TRD-003','JP','synthetic — internal') on conflict do nothing;
insert into ccf_v2.principal_jurisdiction (principal_id,jurisdiction_prefix,provenance) values ('PRIN-TRD-003','SG','synthetic — internal') on conflict do nothing;
