-- Ten companies, and the point of the table is the spread in the last column.
--
-- THIS IS NOT CCF. These rows fabricate the demonstration; you delete them.
--
-- `last_updated` runs from twelve days old to almost two years old, ON PURPOSE.
-- Against the one-year half-life declared in
-- `artifacts/config/half-life-table.yaml`, that spread is what makes D_c a
-- measured number rather than a constant — and it is what the SELECT this
-- example is arguing against cannot tell you.
--
-- FIXED ABSOLUTE INSTANTS, never `now() - interval`. The decision instant is
-- supplied by the caller, so a reproducible seed plus a caller-supplied instant
-- is what makes the printed debt figure the same for you as it was for us.
insert into companies (id, name, revenue, last_updated) values
    (1,  'Northwind Traders',     4200000000, '2026-07-20T00:00:00Z'),
    (2,  'Contoso Manufacturing', 1850000000, '2026-07-02T00:00:00Z'),
    (3,  'Fabrikam Industries',    960000000, '2026-05-14T00:00:00Z'),
    (4,  'Tailspin Logistics',   12400000000, '2026-03-01T00:00:00Z'),
    (5,  'Adventure Works',        340000000, '2025-12-11T00:00:00Z'),
    (6,  'Litware Systems',       7750000000, '2025-09-30T00:00:00Z'),
    (7,  'Proseware Health',       210000000, '2025-06-18T00:00:00Z'),
    (8,  'Wingtip Materials',     2900000000, '2025-02-04T00:00:00Z'),
    (9,  'Coho Vineyards',          85000000, '2024-11-22T00:00:00Z'),
    (10, 'Lucerne Publishing',    1500000000, '2024-08-09T00:00:00Z')
on conflict (id) do update set
    name         = excluded.name,
    revenue      = excluded.revenue,
    last_updated = excluded.last_updated;
