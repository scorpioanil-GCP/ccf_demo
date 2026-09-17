# CP-14 completion — the focused cross-AI close review

**Candidate reviewed:** `cp-14-gate-2-slice-1 @ c80d7815` (immutable; every repair below
landed in the commits that follow it). **Reviewers:** codex (`codex exec`, API-key
auth, the payload over stdin) and cursor (`cursor agent -p --mode ask --trust`). The
executing model is excluded for independence. **Payload:** a brief naming the known
findings (`CP14-F-34`/`F-35`, `CP05D-F-01`/`F-04`/`F-05`, `CP13C-F-03`, `D-IMPL-341`/`342`)
and six categories of adjacent defect to look for, with ten source files inlined and
line-numbered (2,330 lines) — the consolidated GO's *"one focused cross-AI close review
against an immutable candidate"*. Both reviewers cited line numbers that resolve against
the tree; neither review is empty. **Every claim was verified against the tree before
a disposition was recorded**; rejected claims are recorded as rejected, with the reason.

| # | reviewer | claim | verdict | disposition |
|---|---|---|---|---|
| 1 | codex 1–2, cursor 11, 16, 17 | `MemoQuestions` was a shared module-level object rebound by every `produce.product()` open; two opened products could see each other's sources; the variant test bound the shared instance and never restored it | **CONFIRMED** | `produce.product` now constructs ONE mapping per opened product and binds it; the module-level instance is gone; the tests construct their own |
| 2 | codex 3–4, cursor 13 | SPARQL `FROM <…>` and the three vocabulary IRIs are interpolated raw | **CONFIRMED (hardening)** — the values are the deployment's own declared documents, the same pattern every tree uses, but nothing held them to an IRI's character set | `acquisition._iri` refuses a value outside an IRI / ledger name before it is placed in a `<…>` position |
| 3 | codex 6, cursor 8, 18 | the adapter's pre-assembly refusals stamped `recorded_at` with the wall clock; identical refusals were distinct records | **CONFIRMED** — the SDK's own pre-resolution refusals stamp `request.asked_at` (`resolver.py:2787`) | now the question's instant (the pin for a resource read) — `CP05D-F-07` |
| 4 | codex 7–9 | the inherited-debt assertions used `<=` and would pass for a memo worse than every child | **CONFIRMED** | equality with the per-factor minimum over the children |
| 5 | cursor 15 | `checked_citations >= 0` is vacuous | **CONFIRMED** | the section's figures are asserted equal to the retained covenant child's own summary, and positive |
| 6 | cursor 3 | Π took `seeded_on` from a module constant through the plan factory while the anchor carried it as a claim | **CONFIRMED** | Π reads it off the admitted anchors; the constructor takes no seed — `CP13C-F-05` |
| 7 | cursor 4 | the envelope and governing register were taken from `anchors[0]` after a sort — first-wins by sort order | **CONFIRMED as a latent identity hazard** (one read writes them identically, so it cannot fire today) | Π now requires the admitted anchors to agree and refuses a divergent view rather than picking a winner |
| 8 | cursor 1–2 | `view_completeness` / `view_semantic_consistency` return 1 over an empty view | **CONFIRMED for `C`; REJECTED for `S`** — nothing admitted is a coverage shortfall (the SDK states the same rule for `F` over no observations); an absence set with no unexplained member is honestly `S = 1` | `C` reads 0 over an empty view (reaches only the refusal's record; disclosed in `CP-SPEC-013C` §G.3) |
| 9 | codex 5 | the entitlement source's clock is the wall clock, so disclosure posture could vary by time | **REJECTED** — `open_door` sets exactly this clock by design (*"a door decision happens when it happens; the audit instant is never the question's"*); the frozen door did the same; no time-sensitive grant exists | none |
| 10 | cursor 5 | `citation_gate` indexes the payload's shape without guarding and would raise on a malformed payload | **REJECTED** — the payload is Π's own; the gate is the specimen's, unchanged; a shape error there is a programming error that must surface loudly, not a refusal | none |
| 11 | cursor 6 | a foreign `tenant` raises `ProductNotResolvable` (opaque at the door) instead of recording | **REJECTED** — the paved `OpenedProduct.resolve` raises exactly this for a foreign tenant (`product.py:599`); the adapter mirrors the road | none |
| 12 | cursor 7 | the success path never uses the door-resolved `perspective`; the frozen `produce_governed` serves under the specimen's declared perspective | **CONFIRMED as a frozen-tree limitation** — `produce_governed` takes no perspective; the door's declared-role resolver serves every caller under the same declared role, so the role agrees and only the verified caller's `principal_id` differs between the door's record and the product's | disclosed under `CP05D-F-01`; not fixable in a wrapper |
| 13 | cursor 9 | one `ExposureProducer` (one recorder, one store, one registry) serves the door's whole lifetime | **REJECTED** — every paved door serves one `OpenedProduct` for its lifetime the same way; the recorder is the SDK's and is built for it | none |
| 14 | cursor 10 | `sys.path.insert` binds `deployment`/`produce` to the frozen tree for the process | **ACCEPTED, no change** — that process IS the frozen producer's door; the specimen's own door does the same; the tests evict the names when they import the frozen tree in-process | none |
| 15 | cursor 12 | `_summary` computes `latest_period_end` with `max` over strings | **REJECTED** — slice-1 code; ISO dates order lexicographically; a maximum over the child's own served field is a reading, not a domain computation | none |
| 16 | cursor 14 | the first `CLASS_OBLIGOR` record wins | **ACCEPTED, no change** — one resolve writes one obligor node; a second would be a fabric defect surfaced elsewhere | none |

**Categories both reviewers reported empty:** cp-13-canonical's Π and assess reading
anything outside the governed view beyond item 6 (codex: none; cursor: only items 1–3);
below-anchor reads in the consumer (both: none); tenant/class/lane serving in the
adapter beyond item 11 (both: none); fixture leakage between tests beyond item 1 (both:
none).

**After the repairs:** the six suites the repairs touch were rerun against the estate
(cp-13-canonical 26, the exposure door 10, the four CP-14 slices 23), the roster
checker, lint, the docs gates and the page rebuilt; the results are in the review
package and the commits that follow `c80d7815`.
