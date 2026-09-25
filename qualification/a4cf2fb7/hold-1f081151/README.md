# Qualification evidence — candidate `1f081151` (RELEASE HOLD, 2026-09-25)

`main` after D-GATE-353, tree `915ea82bdbb08ea35086cffb52dd30ccc3593a29`, qualified in a fresh
detached worktree under the same procedure as `a4cf2fb7` and ruled **RELEASE HOLD** on two new
findings: `s1_01` failed on a fresh empty Fluree (6 failed + 36 errors, all `KeyError: 'events'`,
gap-ledger `SEC353-G-07`), and the committed public-surface manifest was nine D-IMPL-353 entries
behind the live surface (`dump_surface.py --check` exit 1; the D-15 test gate green because the
`353-0*` fragments claimed every entry). Everything else on the board was green or already
dispositioned: focused suites 5818/0; 33/33 severings RED and restored (two anchors re-anchored to
the frozen code before they could apply, M23 and M27); canonical `make test` 9128 passed / 25 failed
(exact R10) / 0 errors / 856 skipped / 74 xfailed, 13:01; Mongo 38; Neo4j 29; Postgres 224 passed +
12 failed = exact R10 members; CP-03 PASS; DR-01 4 and DR-02 9 + 17 (estate read-only); estate
30 / 1608 / 5878 unchanged.

The hold was resolved by the narrow repair `f23f0a03` and re-qualified at `a4cf2fb7` (see the
parent directory). `evidence.tar.gz` holds the same artifact set as the parent's, for this
candidate; the junit files are inside; credentials redacted; no environment script.
