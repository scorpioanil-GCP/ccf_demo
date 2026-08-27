-- A small 13F extract for CI, and nothing else.
--
-- WHAT THIS IS. Twenty-four real, public rows read out of the live 13F store
-- during this phase's data probe (`24.1-DATA-PROBE.md`) -- real managers, real
-- CUSIPs, real reported positions, real match bands. It is a hand-sized
-- `insert` script, not a database dump, and it exists so the Postgres leg can
-- run the example's own code path against a container it seeds itself
-- (`24-CONTEXT.md` `D-25`/`D-27`).
--
-- WHAT IT IS NOT. It is not what the example reads. The example points at the
-- real store through the environment-variable name `backends.yaml` declares;
-- `24-CONTEXT.md` `D-15` accepts that cost deliberately. Nothing under
-- `examples/` reads this file, and nothing should.
--
-- No host, no port, no credential appears here, and none may.
--
-- ==========================================================================
-- WHAT THE EXTRACT WAS CHOSEN TO MAKE PROVABLE. A fixture in which every row
-- passes every filter proves that the filters exist, not that they do
-- anything.
-- ==========================================================================
--
--   * SIX candidate securities under one anchor LEI at one reported period, so
--     step 1's dominant-security resolve has a ranking to perform and
--     `candidates_considered` is 6 rather than 1. The dominant CUSIP carries 14
--     of the 22 pinned-period rows; the other five carry 3, 2, 1, 1 and 1, so
--     the winner is unambiguous and the tie-break is not what decides it.
--
--   * SIX managers whose only position is on a NON-dominant security -- IMC,
--     Simplex, National Bank of Canada, Allen, Hazlett and Pacer. These are
--     what step 1 must exclude; without them the resolve is decorative.
--     JPMorgan sits on both the dominant and a non-dominant CUSIP, so the
--     exclusion is proven to be per-row rather than per-manager.
--
--   * A GRADED THRESHOLD SWEEP across four orders of magnitude, from
--     $12.88bn down to $201m on the dominant security, so a threshold admits
--     SOME rows and excludes SOME. At the demonstration threshold declared in
--     `examples/cp-00-institutional-holders/artifacts/question.yaml`, 8 of the
--     14 assembled rows are served.
--
--   * THREE `weak`-band rows, all on the DOMINANT security -- which is what the
--     live estate looks like and is the opposite of the intuition. Filtering to
--     `strong` would drop three real holders and remove zero wrong-security
--     rows. The band travels with the row and is filtered NOWHERE
--     (spec §C.4 trap 3; `24-CONTEXT.md` `D-61`). They are here so `C_match`
--     and product gate `IH-G03` are not vacuous.
--
--   * A ROW EXACTLY AT A THRESHOLD VALUE, which closes §F marker 14. Bank of
--     America's `value_usd` of 2612372879 is the designated one: it has rows
--     above it and rows below it, so a test that asks at exactly that number
--     distinguishes `>=` from `>` -- and product gate `IH-G04` exists precisely
--     because copying `s1-00`'s strict `>` is the obvious way to get this
--     wrong. The test reads the value out of this table rather than repeating
--     it, so the number lives in exactly one place.
--
--   * TWO ROWS OUTSIDE THE PINNED PERIOD, both ABOVE the demonstration
--     threshold, so the period pin is provably load-bearing rather than
--     assumed. Norges Bank appears at `31-MAR-2025` and nowhere else, so an
--     unpinned read would serve a holder that does not exist in the pinned
--     quarter; Morgan Stanley appears at both `31-DEC-2025` and the pinned
--     period, so an unpinned read would also double-count a manager that does.
--     Two different failure shapes, one pin (spec §C.4 trap 1, gate `IH-G02`).
--
-- Idempotent: `on conflict do update`, so a repeated leg against a long-lived
-- server converges rather than duplicating or failing.

insert into ccf_v2.institutional_holder
    (lei, manager_cik, manager_name, cusip, value_usd, shares,
     report_period, issuer_match_score, issuer_match_band, provenance)
values
    -- --- the dominant security, 032095101: 14 rows -----------------------
    -- strong band, above the demonstration threshold
    ('549300D3L3G0R4U4VT04', '0002012383', 'BlackRock, Inc.',                          '032095101', 12883412435, 101966066, '31-MAR-2026', 1.0000, 'strong', 'public'),
    ('549300D3L3G0R4U4VT04', '0000315066', 'FMR LLC',                                  '032095101', 10041984781,  79477521, '31-MAR-2026', 1.0000, 'strong', 'public'),
    ('549300D3L3G0R4U4VT04', '0000093751', 'STATE STREET CORP',                        '032095101',  7266090298,  57396418, '31-MAR-2026', 1.0000, 'strong', 'public'),
    ('549300D3L3G0R4U4VT04', '0000019617', 'JPMORGAN CHASE & CO',                      '032095101',  5870589642,  49270578, '31-MAR-2026', 1.0000, 'strong', 'public'),
    ('549300D3L3G0R4U4VT04', '0001562230', 'Capital International Investors',          '032095101',  4463635126,  35333842, '31-MAR-2026', 1.0000, 'strong', 'public'),
    ('549300D3L3G0R4U4VT04', '0001422848', 'Capital Research Global Investors',        '032095101',  3364162320,  26630629, '31-MAR-2026', 1.0000, 'strong', 'public'),
    -- the designated exactly-at-a-threshold row -- §F marker 14
    ('549300D3L3G0R4U4VT04', '0000070858', 'BANK OF AMERICA CORP /DE/',                '032095101',  2612372879,  20675686, '31-MAR-2026', 1.0000, 'strong', 'public'),
    ('549300D3L3G0R4U4VT04', '0000895421', 'MORGAN STANLEY',                           '032095101',  2212698455,  17512450, '31-MAR-2026', 1.0000, 'strong', 'public'),
    -- strong band, below the demonstration threshold
    ('549300D3L3G0R4U4VT04', '0000884546', 'CHARLES SCHWAB INVESTMENT MANAGEMENT INC', '032095101',   933751896,   7390201, '31-MAR-2026', 1.0000, 'strong', 'public'),
    ('549300D3L3G0R4U4VT04', '0000072971', 'WELLS FARGO & COMPANY/MN',                 '032095101',   897606388,   7104126, '31-MAR-2026', 1.0000, 'strong', 'public'),
    ('549300D3L3G0R4U4VT04', '0001040188', 'VICTORY CAPITAL MANAGEMENT INC',           '032095101',   813956925,   6442036, '31-MAR-2026', 1.0000, 'strong', 'public'),
    -- weak band, all three on the DOMINANT security, and all served
    ('549300D3L3G0R4U4VT04', '0001109147', 'AXIOM INVESTORS LLC /DE',                  '032095101',   539184347,   4267387, '31-MAR-2026', 0.8000, 'weak',   'public'),
    ('549300D3L3G0R4U4VT04', '0001318757', 'MARSHALL WACE, LLP',                       '032095101',   295319120,   2337310, '31-MAR-2026', 0.8889, 'weak',   'public'),
    ('549300D3L3G0R4U4VT04', '0001842702', 'Navera Investment Management Ltd.',        '032095101',   201528152,   1594959, '31-MAR-2026', 0.8000, 'weak',   'public'),

    -- --- the five non-dominant securities: 8 rows, all excluded by step 1 --
    ('549300D3L3G0R4U4VT04', '0001452861', 'IMC-Chicago, LLC',                         '032095901',    51601340,    408400, '31-MAR-2026', 1.0000, 'strong', 'public'),
    ('549300D3L3G0R4U4VT04', '0001488542', 'SIMPLEX TRADING, LLC',                     '032095901',    21403690,    169400, '31-MAR-2026', 1.0000, 'strong', 'public'),
    ('549300D3L3G0R4U4VT04', '0000926171', 'NATIONAL BANK OF CANADA /FI/',             '032095901',    20216000,      1600, '31-MAR-2026', 1.0000, 'strong', 'public'),
    ('549300D3L3G0R4U4VT04', '0001452861', 'IMC-Chicago, LLC',                         '032095951',    55227585,    437100, '31-MAR-2026', 1.0000, 'strong', 'public'),
    -- JPMorgan is on the dominant security TOO -- the exclusion is per row
    ('549300D3L3G0R4U4VT04', '0000019617', 'JPMORGAN CHASE & CO',                      '032095951',    13821400,    116000, '31-MAR-2026', 1.0000, 'strong', 'public'),
    ('549300D3L3G0R4U4VT04', '0001326234', 'Allen Investment Management, LLC',         '81369Y506',   144878878,   2364983, '31-MAR-2026', 1.0000, 'strong', 'public'),
    ('549300D3L3G0R4U4VT04', '0000046392', 'HAZLETT, BURT & WATSON, INC.',             '8033009TT',           3,         2, '31-MAR-2026', 1.0000, 'strong', 'public'),
    ('549300D3L3G0R4U4VT04', '0001616667', 'Pacer Advisors, Inc.',                     '002159795',     8484403,     67150, '31-MAR-2026', 1.0000, 'strong', 'public'),

    -- --- outside the pinned period: 2 rows, both above the demonstration
    --     threshold, both on the dominant security. Neither may ever reach a
    --     served payload.
    ('549300D3L3G0R4U4VT04', '0000895421', 'MORGAN STANLEY',                           '032095101',  2457649369,  18185947, '31-DEC-2025', 0.8000, 'weak',   'public'),
    ('549300D3L3G0R4U4VT04', '0001374170', 'NORGES BANK',                              '032095101',  1306008337,  19911699, '31-MAR-2025', 0.8000, 'weak',   'public')
on conflict (lei, manager_cik, cusip, report_period) do update set
    manager_name       = excluded.manager_name,
    value_usd          = excluded.value_usd,
    shares             = excluded.shares,
    issuer_match_score = excluded.issuer_match_score,
    issuer_match_band  = excluded.issuer_match_band,
    provenance         = excluded.provenance;

-- The anchor's reference row. The example left-joins it for one column,
-- `legal_name`; the whole row is seeded because a fixture that carried only the
-- column today's code reads is a fixture that cannot reproduce tomorrow's
-- defect in the columns it dropped.
insert into ccf_v2.legal_entity
    (lei, legal_name, gleif_legal_name, legal_jurisdiction, entity_status,
     registration_status, next_renewal_date, initial_registration, legal_form,
     address_country, address_city, address_region, sic, sic_description,
     fiscal_year_end, is_anchor, lei_match_band, lei_match_score, provenance,
     source, retrieved_at)
values
    ('549300D3L3G0R4U4VT04', 'AMPHENOL CORP /DE/', 'AMPHENOL CORPORATION',
     'US-DE', 'ACTIVE', 'ISSUED', date '2027-01-09', date '2013-08-06', 'XTIQ',
     'US', 'WILMINGTON', 'US-DE', '3678', 'Electronic Connectors', '1231',
     true, 'exact', 1.000, 'public',
     'GLEIF LEI record API + SEC EDGAR submissions API', date '2026-08-16')
on conflict (lei) do update set
    legal_name          = excluded.legal_name,
    gleif_legal_name    = excluded.gleif_legal_name,
    entity_status       = excluded.entity_status,
    registration_status = excluded.registration_status,
    retrieved_at        = excluded.retrieved_at;
