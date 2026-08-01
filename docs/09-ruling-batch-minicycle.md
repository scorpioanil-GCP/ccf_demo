# Phase 9 Ruling Batch — Consolidated Phase D Mini-Cycle (HARD-01)

**Status:** COMPLETE — all six items ruled by Dave in the interactive
walkthrough of 2026-08-01 (zero deferrals; every ruling followed the
document's recommendation). Rulings are logged as D-IMPL-68..73 in
`docs/DECISIONS.md`; the per-item status table at the end of this
document records the chosen options. Per CLAUDE.md §11 and REQUIREMENTS
"Out of Scope", no ruling item was defaulted: every outcome below is
Dave's ruling.

**Deferral posture (D-04, partial-proceed):** a deferred item gates only
its downstream consumer, never this phase. Items 1, 2, and 6 gate
Phase 10; item 3 gates Phase 11; items 4 and 5 gate Phase 14. The Phase 9
code plans (WR-02 transport synchronization, WR-03 ADK driver robustness)
proceed regardless of any deferral — the rulings-first ordering (D-02)
exists so fixes never pre-empt rulings on adjacent surfaces, not so
deferrals block fixes.

**Candidate D-IMPL numbers.** The verified tail of `docs/DECISIONS.md` is
D-IMPL-67 (plus the un-numbered Phase-8 context ruling D-15). The six
items below are pre-assigned **D-IMPL-68 through D-IMPL-73** in the order
presented. Per the new-number-not-amend discipline (D-IMPL-66 precedent),
item 5 amends a prior ruling by taking a *new* number; the prior text
stands as approved.

---

## Item 1 — D-IMPL-68: WR-01 per-tenant authorization mapping shape

**Surfacing context.** Code review WR-01 (08-REVIEW.md, carried in
`.planning/v0.1-MILESTONE-AUDIT.md`): the HITL doors *authenticate* when
an auth hook is bound (D-IMPL-67) but do not *authorize* per tenant —
`TokenGrant.scopes` is never enforced at the HTTP door. A verified caller
for tenant A can act on tenant B's HITL events. Phase 10 (HARD-04)
consumes this ruling: deny-by-default, typed 403, authorization decision
in the audit record, and a cross-door × cross-action test matrix. The
envelope is D-IMPL-62 (submit-only doors), D-IMPL-63 (caller-supplied
principal is the v0 posture), D-IMPL-67 (verified-identity binding), and
the T-07-24 accepted residual (default posture stays unauthenticated;
this item governs behavior *when auth is bound*).

The question has two halves: **where** scope enforcement lives, and
**what** a scope string means.

**Option A — enforcement at the doors (HTTP route / MCP tool handler).**
Each door checks `TokenGrant.scopes` against the (tenant, action) of the
submission before touching the transport.
- Pros: matches where D-IMPL-67 already binds identity; door-local typed
  403s reuse the `http_api/errors.py` constants pattern; the transport
  stays a pure queue (no policy in mechanism below the trust boundary).
- Cons: N doors × M actions duplication risk — mitigated only if the
  check is one shared helper both doors call.

**Option B — enforcement in the transport (`InMemoryHitlTransport.submit`).**
The transport refuses out-of-scope submissions the way it refuses
unsigned ones under `signed_binding_required`.
- Pros: single choke point; in-process callers are covered too.
- Cons: the transport currently has no notion of caller identity — the
  submission's principal is data, not a verified credential; pushing
  authorization below the door conflates "who the record says acted" with
  "who the caller proved to be", exactly the confusion D-IMPL-67 closed.
  Also widens WR-02's concurrency surface (the lock work lands in the
  same file this phase).

**Option C — scope mapping as a Control Plane policy artifact,
enforcement at the doors.** The tenant × action grammar for scope strings
(e.g., `hitl:{tenant}:{action}` with `*` support) is *not* hardcoded; a
registered policy artifact (or the existing `HitlPolicy` class extended
in a versioned lane) declares the mapping, and a shared door-side helper
interprets it. Deny-by-default when no mapping matches.
- Pros: honors mechanism-not-values (the scope grammar is a deployment
  statement, like `signed_binding_required`); doors stay the enforcement
  point per Option A's logic; the audit record can cite the policy
  artifact version that authorized the action — replay-honest.
- Cons: more moving parts than a fixed grammar; needs a schema ruling
  inside the artifact (kept small: scopes → tenant patterns × action
  sets).

**Recommendation: Option C** — door-side enforcement through one shared
helper interpreting a versioned Control Plane scope-mapping artifact,
deny-by-default, typed 403 constants, authorization outcome (including
the policy artifact version) recorded in the audit record. This is the
only option that keeps the scope grammar out of `/src` while keeping
enforcement at the boundary where identity is actually verified.

---

## Item 2 — D-IMPL-69: ApprovalGate.resolve × D-16 signed-binding composition

**Surfacing context.** Audit review consensus (v0.1-MILESTONE-AUDIT):
`ApprovalGate.resolve` cannot compose with D-16's
`signed_binding_required`. Verification of the signed principal binding
lives on the transport `submit` path only (`src/ccf/hitl/transport.py` —
`SignedBindingRequiredRefused` / `SignedBindingInvalidRefused` fire in
`InMemoryHitlTransport.submit`). A composition root that calls a
primitive's `resolve` directly — the pattern the MCP channel's
resolve-wiring uses, a *ruled* asymmetry under D-IMPL-62 — bypasses the
policy entirely: a deployment can declare `signed_binding_required: true`
and still have unsigned resolutions land in replay dimension 2.

**Option A — primitives verify too.** `ApprovalGate.resolve` (and the
other three primitives' resolution surfaces) resolve the `HitlPolicy`
artifact and refuse an unsigned/invalid binding when the policy demands
one, with the same typed refusals the transport uses.
- Pros: closes the bypass structurally — no path to a resolution that
  ignores the declared policy; audit-by-construction (§8.2) argues the
  invariant should hold at the authority-bearing call, not only at one
  transport's front door.
- Cons: primitives grow a Control Plane read dependency on the resolve
  path; verification runs twice on transport-fed flows (idempotent, but
  measurable); needs care to keep JWS verification outside any new lock
  (WR-02 adjacency — the rulings-first ordering exists for exactly this
  file).

**Option B — document the boundary; composition roots own it.**
D-16 is defined as a *door* policy: the transport submit path is the
enforcement point, and a composition root that wires `resolve` directly
assumes the verification obligation (as
`tests/crossproc/servers/mcp_hitl_child.py` implicitly does today).
- Pros: zero code motion; consistent with D-IMPL-62's submit-only ruling.
- Cons: "audit-by-construction" degrades to audit-by-convention on the
  resolve path; every future composition root is one forgotten check away
  from unsigned authority; the audit reviewers flagged this exact gap.

**Option C — typed resolve-context requirement.** Primitives' `resolve`
signatures accept a verification token/receipt produced only by the
transport's verification step (or by an explicit
`verify_signed_binding(...)` helper), making an unverified resolution
type-unrepresentable rather than runtime-checked.
- Pros: strongest structural guarantee, matches the project's
  type-unrepresentable doctrine (D-IMPL-21 leg).
- Cons: largest surface change — touches all four primitives' signatures
  and every composition root and test; heavier than Phase 10's HARD-04
  budget implies.

**Recommendation: Option A** — primitives verify against the resolved
`HitlPolicy` on their resolution surfaces, reusing the existing typed
refusals, with verification kept outside any transport lock. It closes
the bypass at the authority point without the signature-churn of
Option C, and Option B leaves a ruled invariant enforceable only by
convention.

---

## Item 3 — D-IMPL-70: Performance governance

**Surfacing context.** Phase 11 (PERF-04) already commits mechanically to
runner-class-keyed baselines, a `thresholds.toml`, relative-median gating,
and an opt-in `perf.yml` workflow. What is unruled is *governance*: who
may re-baseline, who owns thresholds, and whether perf gating is ever
always-on. Ecosystem data (RESEARCH, MEDIUM confidence): absolute-time
gates on shared CI runners are flake-by-construction — CodSpeed's
analysis shows holding a 1% false-positive rate on GitHub-hosted runners
forces a ~7% minimum gate; practice is median/min relative gating with
10–15% thresholds on shared runners, tightened on dedicated hardware;
pytest-benchmark and asv are the standard tools, asv supporting relative
continuous benchmarking natively.

**Option A — Dave-gated re-baseline, repo-owned thresholds, opt-in
forever (v0.2 posture).** Re-baselining is a deliberate act recorded in
DECISIONS.md (or a perf-baselines log) with Dave's approval, exactly like
a D-GATE; `thresholds.toml` changes go through review like any ruled
artifact; `perf.yml` stays `workflow_dispatch` opt-in (the D-11 live-legs
pattern).
- Pros: matches the project's approval discipline; no CI flake exposure;
  cheap.
- Cons: perf regressions surface only when someone runs the workflow —
  detection latency is bounded by ritual, not automation.

**Option B — automated re-baseline on merge to main, always-on relative
gate at 15%.** Every main merge refreshes baselines; PRs gate on relative
regression.
- Pros: continuous detection.
- Cons: shared-runner noise makes a 10–15% gate the *floor*, so real
  ~10% regressions pass silently while flakes still fire; auto-refreshed
  baselines ratchet drift into the baseline (a slow regression
  re-baselines itself); contradicts the D-10/D-11 split where always-on
  CI is deterministic-only.

**Option C — hybrid: opt-in gating now, named promotion criterion.**
Option A's posture, plus a recorded criterion for promoting perf gating
into always-on CI (e.g., dedicated runner availability or a CodSpeed-class
instrumented-measurement service), so "opt-in" is a staged posture, not
an indefinite one.
- Pros: keeps Phase 11 unblocked with Option A's discipline while
  pre-answering "when does this become always-on".
- Cons: the promotion criterion is speculative today; risks ruling on
  infrastructure that may never be acquired.

**Recommendation: Option A** — re-baselining requires Dave's approval and
a logged entry; thresholds live in the reviewed `thresholds.toml` with
changes treated as ruled-artifact changes; perf gating stays opt-in
(`workflow_dispatch`), mirroring D-11's live-legs pattern. Promotion to
always-on can be a later D-IMPL when the runner situation changes —
ruling it now (Option C) commits to hypotheticals.

---

## Item 4 — D-IMPL-71: Docs toolchain and publishing

**Surfacing context.** Phase 14 (DOCS-02) commits to mkdocs-material +
mkdocstrings; the hosting/publishing decision was explicitly deferred in
REQUIREMENTS. The repo is **private and stays private** (CLAUDE.md §2.2:
the canonical whitepaper lives in `docs/` and CCF is proprietary IP).

**Verified constraint (checked against GitHub's official docs,
2026-08-01, not assumed):** private Pages visibility ("access control")
exists only on **GitHub Enterprise Cloud**, and even there only for
project sites published from a private/internal repository **owned by an
organization**. `drcastillo/ccf_code` is a personal-account private repo
on a non-Enterprise plan: a GitHub Pages site published from it would be
**publicly readable on the internet**, regardless of the repo's private
visibility. RESEARCH assumption A2 is confirmed, with the sharpening that
Enterprise alone is not sufficient — org ownership is also required.

**Option A — CI-artifact-only.** `make docs --strict` builds in CI (see
item 5); the rendered site uploads as an Actions artifact. No hosting.
- Pros: zero disclosure risk for proprietary IP; matches DOCS-06 and the
  deferred-hosting posture; reversible at any time.
- Cons: reading the docs means downloading an artifact — no stable URL.

**Option B — GitHub Pages.** Publish the mkdocs site via Pages.
- Pros: free stable URL, first-class mkdocs-material support.
- Cons: **the site would be public** (verified above) — the whitepaper
  and API docs of proprietary IP on the open internet. Only viable if the
  published tree is curated to exclude everything sensitive, which
  contradicts "docs site documents the SDK" and adds a censoring build
  step nobody has scoped. Effectively ruled out by §2.2 unless Dave
  decides some subset is deliberately public.
- Cons (structural): moving to an org + Enterprise Cloud just for private
  Pages is an infrastructure decision far larger than a docs toolchain.

**Option C — mike (versioned docs on a gh-pages branch), deferred
activation.** Adopt mike's versioning layout now so the build is
version-aware, but publish nowhere until a hosting decision exists
(Pages-if-ever-public, or an internal host).
- Pros: version lanes baked in early.
- Cons: pays versioning complexity before there is any consumer; a
  gh-pages branch in a private repo still becomes public the moment Pages
  is enabled — the deferred hazard remains loaded.

**Recommendation: Option A** — CI-artifact-only, with the hosting
question left explicitly open as a future D-IMPL should the repo's
visibility posture ever change. It is the only option with zero
IP-disclosure surface today, and it loses nothing: mkdocs output is
host-agnostic, so any later hosting ruling starts from the same build.

---

## Item 5 — D-IMPL-72: Amend the Phase-8 `make ci` composition — `make docs --strict` joins always-on CI

**Namespace disambiguation, first.** "D-10" here is **Phase 8's context
decision D-10** — the ruling, finalized in plan 08-12, that fixed the
`Makefile` line `ci: ci-core examples` as the phase-gate command,
command-identical to the always-on Actions pipeline. It is **not** this
phase's CONTEXT D-10, which is the WR-03 error-hierarchy decision
(typed `SegmentNotExecutedError` etc.). The two share a number in
different namespaces; this document and the eventual DECISIONS.md entry
cite "Phase-8 D-10 (`make ci` composition)" to keep them straight.

**Surfacing context.** DOCS-06 (Phase 14 requirement) names a "logged
D-10 amendment": `make docs --strict` (mkdocs strict build — broken
refs/nav fail the build) joins always-on CI, so docs rot is a red build,
not a discovery at release time. Per the new-number-not-amend discipline,
the amendment takes this new number; Phase-8 D-10's text stands.

**Option A — amend now, effective when the docs target exists.** Rule the
composition change in this batch: `ci` becomes
`ci-core examples docs-strict` (and ci.yml gains the job) **as of the
Phase 14 plan that creates the docs build**. Between now and then,
nothing changes on disk — the ruling pre-authorizes the wiring.
- Pros: Phase 14 planning is unblocked (its consumer needs the ruling,
  not the Makefile edit); one batch, one walkthrough; no dead `docs`
  target lands early.
- Cons: a ruled-but-not-yet-wired composition exists for a few phases —
  mitigated by DOCS-06 naming the receiving phase explicitly.

**Option B — defer the amendment to Phase 14 itself.** Let Phase 14
surface its own D-IMPL when the docs build exists.
- Pros: ruling and wiring land together.
- Cons: re-runs a mini-cycle for a question already fully specified
  today; Phase 14 planning proceeds against an unruled CI composition —
  exactly what the rulings-first posture (D-02) avoids.

**Recommendation: Option A** — rule the amendment now with deferred
effectivity: always-on CI (`make ci` and ci.yml) grows the strict docs
build in the Phase 14 plan that introduces the `docs` target; the entry
cross-references Phase-8 D-10 without editing it.

---

## Item 6 — D-IMPL-73: `create_app` insecure-default warning

**Surfacing context.** Audit review consensus: `create_app`
(`runtime/ccf_runtime/http_api/app.py`) defaults to the unauthenticated
posture (T-07-24 accepted residual; `AUTH_POSTURE_SENTENCE` is served and
test-asserted) — but the posture sentence is visible only to someone who
reads the API response or the docstring. Adopters need a *loud* signal at
construction time. Phase 10 (HARD-05) implements whatever is ruled here.
Two sub-questions: mechanism, and suppression surface. Note the
No-Hardcoding boundary: the warning is *mechanism* (a security posture
signal from the SDK), not a domain value — inline warning text is
legitimate here, unlike prompts or policy values.

**Option A — `warnings.warn` with a dedicated category.** Emit e.g.
`CcfInsecureDefaultWarning` (a `UserWarning` subclass exported from the
SDK) when `create_app` is called with no auth hook. Suppression: the
standard `warnings` machinery *plus* an explicit acknowledgment kwarg
(e.g., `allow_unauthenticated=True`) that suppresses the warning by
stating intent in code.
- Pros: `warnings` is the Python-native channel for exactly this
  (visible once per process by default, filterable, testable with
  `pytest.warns`); the typed category lets deployments and CI treat it
  as an error (`-W error::CcfInsecureDefaultWarning`); the kwarg makes
  the insecure choice *visible in the caller's code and in review* —
  greppable intent, the same doctrine as typed refusals.
- Cons: warnings can be globally silenced by ambient filters; kwarg adds
  a parameter to a public signature (additive, default `False`).

**Option B — startup log line.** Emit a `logging` WARNING when the app
first serves (or at construction).
- Pros: lands in production log pipelines where operators look.
- Cons: invisible until logging is configured — the exact adopter who
  needs the warning (quickstart, defaults everywhere) often has no
  handler bound; not treatable as an error in CI; no in-code
  acknowledgment surface.

**Option C — both, with the kwarg as the single suppression surface.**
`warnings.warn(CcfInsecureDefaultWarning)` at `create_app` time *and* a
log-record at first request; `allow_unauthenticated=True` (name per
Phase 10's bikeshed) suppresses both. No env-var suppression — env vars
are invisible in code review and encourage fleet-wide silencing.
- Pros: covers both the developer loop (warnings) and the operator loop
  (logs); one explicit, greppable off-switch.
- Cons: two emission points to keep consistent; marginally more test
  surface.

**Recommendation: Option C** — dedicated warning category plus log
record, suppressed only by an explicit acknowledgment kwarg (no env
var). The examples then bind `auth=` (their existing Phase-8 obligation)
or acknowledge explicitly, keeping `make examples` warning-clean and the
D-14 byte-identity manifest intact.

---

## Walkthrough protocol

Items are presented to Dave one at a time (D-01, interactive). As each
ruling lands it is appended to `docs/DECISIONS.md` in the house format
under its pre-assigned number, dated, `Approver: Dave`, with surfacing
context, question, consequences, and Originates line; this document's
per-item status is updated to RESOLVED (with the chosen option) or
DEFERRED (naming the gated downstream phase: items 1/2/6 → Phase 10,
item 3 → Phase 11, items 4/5 → Phase 14). Deferrals remain open D-IMPL
entries flagged for the D-GATE-9 presentation.

| Item | Number | Status |
|------|--------|--------|
| 1 — WR-01 mapping shape | D-IMPL-68 | RESOLVED — Option C (Control Plane scope-mapping artifact, door-side enforcement, deny-by-default), 2026-08-01, Approver: Dave |
| 2 — ApprovalGate × D-16 | D-IMPL-69 | RESOLVED — Option A (primitives verify HitlPolicy on resolve paths, typed refusals reused), 2026-08-01, Approver: Dave |
| 3 — Perf governance | D-IMPL-70 | RESOLVED — Option A (Dave-gated re-baseline, reviewed thresholds.toml, opt-in perf.yml per D-11), 2026-08-01, Approver: Dave |
| 4 — Docs toolchain/publishing | D-IMPL-71 | RESOLVED — Option A (CI-artifact-only; no public publishing), 2026-08-01, Approver: Dave |
| 5 — Phase-8 D-10 `make ci` amendment | D-IMPL-72 | RESOLVED — Option A (amend now, effective at the Phase 14 plan creating the docs target), 2026-08-01, Approver: Dave |
| 6 — create_app warning | D-IMPL-73 | RESOLVED — Option C (warning category + log record; suppression only via explicit acknowledgment kwarg, no env var), 2026-08-01, Approver: Dave |
