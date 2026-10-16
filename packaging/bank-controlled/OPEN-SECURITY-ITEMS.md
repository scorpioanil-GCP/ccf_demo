<!--
Copyright (c) 2026 David Castillo. All rights reserved.
Use, copying, modification, and distribution of the covered material
are governed by the CCF SDK Interim Software and Patent License
in the repository-root LICENSE.md and any controlling signed agreement.
Rights under that interim license begin only upon its execution
and are limited to its stated scope and term.
-->
# Open security items — for review and ordering

Status as of 2026-10-16. Measured against the delivered build `01fc424d`
(`main` at `8193c607` carries only documents after it). The replay-evidence work
on branch `replay-evidence-383` (`D-IMPL-383`) closed none of these items and
changed none of them.

This is the 16-item list shown to Dave on 2026-10-13 09:40 MST and sent to the
bank; the numbers are the ones the bank's answer uses. Token estimates are left
out on purpose: Dave ruled them unvalidated (2026-10-13 03:53 MST).

## The bank's answer (2026-10-15 18:09 MST, relayed by Dave)

1. *"is there an alternative to SqlLite for CCF-SDK and can multiple
   applications share the same repository instead of individual SqlLite."*
   The replay part of this led to `D-IMPL-383`; the shared-store part is open.
2. *"They want a detailed breakdown of the SEC-02 issue more than what was
   presented to them."* Dave, 2026-10-16 14:37 MST: the bank means **SEC-020**
   (item 3 below). Not yet answered.

## A. Security register: 24 of 29 closed, 5 open

| # | Item | What it is | Severity | Reaches the bank's setup? | What closing it takes |
|---|---|---|---|---|---|
| 1 | SEC-001 (residual) | Separate processes sharing one approval store are not detected; approval identity does not carry from one store to another. | CRITICAL (main part fixed) | No: one engine, store and approval queue per instance. | Build the remainder of design 1.4; runs paused before the upgrade then need a fresh approval. |
| 2 | SEC-013 | Limits of the SQLite single-writer lock: a hard-link backup blocks every startup; a live database moved without a declared lock folder can admit a second writer and lose commits. | Not rated | As operating rules only; the setup creates the lock folder. | Verify option (C) (built 2026-10-08) and Dave's ruling on the disclosed limits. |
| 3 | **SEC-020** | A caller may be able to tell a withheld record from one that does not exist. The closing gate's 21 cases pass. Still open: three measured limitation blocks (D1 (a) 30/88, P6 24/44, E2 (ii) 82/82); the shared-owner check in a long-running service (16 (C), unbuilt, HIGH); a composite child's record that names the stand-in (HIGH, disclosed only); question stores reachable by a raw writer; a store `get` that checks nothing; timing (one extra read per question, measured at one scale; write timing over the wire, disclosed, not measured). | Parts HIGH | **Yes: the same door the bank runs.** Not tested under the bank configuration (one shared credential, one read-only tool). The raw-writer and store-`get` gaps need access the setup does not give out. | A design and build per remaining part, then a measurement under the bank configuration. Closes only on Dave's ruling. |
| 4 | SEC-027 | The `ccf-sdk` name is not reserved on PyPI. | Not rated | No runtime effect | Dave's upload of a placeholder (reverses "no PyPI upload"). |
| 5 | SEC-029 | No release tag, so the build carries a development version number (`1.0.2.dev1564+g01fc424d9`). | Not rated | Version string only | A tag (reverses "no tag"). |

## B. Other open items

| # | Item | What it is | Severity | Reaches the bank's setup? |
|---|---|---|---|---|
| 6 | SEC-009 erasure claim | Erasure design 1.3 is not independently verified. | Not rated | No (no artifact server) |
| 7 | Follow-up 1 | A late opposite approval verdict can stall an approval step permanently; it never lets one pass wrongly. Fixing it changes `D-IMPL-366` H2. | MEDIUM | No |
| 8 | Follow-up 2 | The same stall through an escalation filed under the approval step's key. | MEDIUM | No |
| 9 | Follow-up 6 | An erasure through the MCP-backed store never completes. | Functional, not a leak | No |
| 10 | Designs 1.5, 1.6 | Audit recovery and record authenticity: ruled 2026-10-09, not built. | Not rated | Not assessed |
| 11 | Early HTTP refusals | 401/403 answers made before the authorizer is asked leave no audit or replay record. | Not rated | No (no HTTP door) |
| 12 | Resource read without a request | Raises an error instead of returning a clean refusal. | Not rated | Not assessed |
| 13 | Decimal scale | 1.0 and 1.00 get different content addresses; deliberate under Dave's 2026-10-11 20:19 ruling 1. | Not rated | Not assessed |
| 14 | Follow-up 5 | No conformance test that a third-party approval transport checks eligibility; MCP "cannot verify" timing not measured. | Not rated | No |
| 15 | R-1, R-2, R-3 | Test-harness process-id reuse; the wrong message for an empty tenant id; a check that can never run. | LOW | No |
| 16 | Follow-ups 3, 4; MCP door argument | 27 stale docstrings; the 403 row in the authoring Standard v0.3; a request argument a model cannot work out. | Docs and usability | No |

## C. Deferred by ruling (Dave, 2026-10-12 22:44 and 2026-10-13 03:53 MST)

Follow-ups 7, 8 and 9. Dave named this group the one the bank is most likely to require fixed.

- An unauthorized ask about a restricted record gets the same answer as a record that does not exist.
- No disclosure level states only "not entitled to this information wall" for a named employee.
- The door judges the shared credential, not the employee an agent acts on behalf of.

## D. Not in the bank packet

143 smaller review residuals in `docs/D-IMPL-377-CLOSE-OUT.md` section 7h (34 tied
to SEC rows), last statused 2026-10-07.

## Sources

`packaging/bank-controlled/BANK-PACKET.md` section 5; `docs/DECISIONS.md`
(`D-IMPL-376` to `D-IMPL-383` and the 2026-10-11 to 2026-10-13 rulings);
`docs/D-IMPL-377-CLOSE-OUT.md` section 7h.
