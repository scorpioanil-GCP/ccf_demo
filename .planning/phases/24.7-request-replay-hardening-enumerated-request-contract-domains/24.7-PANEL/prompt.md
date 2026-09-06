# Reviewer instruction — Phase 24.7 close-time panel (CLAUDE.md §3.1)

You are one of several independent AI reviewers. The subject is the **shipped code** of Phase 24.7 of the CCF
SDK — `phase-24.7` at commit `ad8dc5a9`, diff base `6a019322` — NOT its plans. The source is INLINED in the
bundle you were given on stdin; do not assume you can read the repository, and do not report what you cannot
see in the bundle.

## Before anything else

1. Quote, verbatim, the `READ-PROOF …` line from the bundle you received (it appears at the top, mid-payload
   and at the end). A review without it is void.
2. Read `known-findings.md` (K1–K8). Those findings are already recorded. **Do not re-derive them.** Your budget
   is for what is ADJACENT to each — the same defect class in a neighboring symbol, the seam a fix did not reach,
   the alternative reading the code admits.

## The phase, in one line

G-26: `ArgumentDomain` declares numeric bounds OR an enumerated member set (exactly one shape), `not-in-domain`
is the ninth request-violation reason, a canonical contract-to-schema render derives `enum` from the declaration
with no publication surface, and `ProductRequest.intent` is judged against `ProductDiscovery.intents` in three
states with the shadow `arguments.properties.intent` refused at construction. G-33: resolution returns a paired
outcome carrying its evidence at every exit, the replay builder and the recorder seam REQUIRE an explicit
resolution state (an `EffectiveRequest` or a typed `ResolutionNotApplicable(reason=…)`), legacy records keep
the hash-transparent sentinel byte-for-byte, and replay refuses a false not-applicable claim against PINNED
contract/constraint state only.

The governing rulings: `D-IMPL-264` (D-00..D-13, P-1 "declaration is not advertisement", P-2 "absence is not
omission", amendments 1 and 3) and `D-IMPL-265` (`archive/examples/` is retired history). The invariants every
finding is judged against are in CLAUDE.md §10–§11: single-writer, composition-preservation, three validation
gates, Algorithmic ⇄ Semantic alternation, audit-by-construction, the No-Hardcoding Rule, zero harness imports
in `src/`, `extra=forbid` at every boundary, hash-transparency on every defaulted contract field.

## What to produce

A list of findings. For each:

- **Citation:** `path.py::Symbol` (module path relative to the repo root, then the class/function/method). A
  finding whose cited symbol does not exist in the bundle is VOID and will be recorded as a fabricated citation.
  Do not cite line numbers alone; the bundle has no line numbers.
- **Class:** `blocking` (a violated invariant, a whitepaper-fidelity defect, a replay/audit hole, a security
  defect, an unsurfaced architectural decision) or `advisory` (style, naming, sequencing, deferred scope).
- **Claim:** one paragraph, concrete, falsifiable, with the input or sequence that exhibits it.
- **Adjacency:** which known finding (K-number) it sits beside, if any.

Order findings blocking first. If you find nothing blocking, say so explicitly. Do not pad. Do not restate the
known findings as your own. Do not review `examples/`, `archive/`, `.planning/`, generated docs, or the criteria
— they are not in the bundle and are not the subject.

## Reading order (recommended)

`bundle-src-part-1` (the diff, `request_schema.py`) → `request.py` → `resolver.py` → `record.py` +
`delivery_boundary.py` → `constraints.py` + `engine.py` → the test bundles. Each part is self-contained and
carries its own read-proof; review the part you were given and cite only what it contains.
