# `D-IMPL-362` — SEC-007 empty-`identity_keys` leg: CLOSE PANEL reviews

**Subject: the SHIPPED TREE.** Candidate `253dcc408b662c5072668d5aa67f02788f8f1a89`
on branch `repair-sec007-empty-identity-keys`, base `621173a1123b9d33be51fcbec3de117628af571a`
(= `main` = `origin/main` at review time). Commits under review: `c096b35b` (RED tests),
`7483e831` (the repair + surface), `cc6e9b21` (`D-IMPL-362` recorded), `253dcc40`
(`D-IMPL-362` amended). Review GO given by Dave on 2026-10-03 for this leg only.

**Judged against** the acceptance criterion recorded verbatim in `D-IMPL-362`:
*"A resolution rule that declares zero identity keys constructs. When an envelope matches it,
the mint raises IdentityRefused with reason "undeclared" and does not hash {}. The governed
path records that refusal. content_hash({}) is not an entity URI."*

**Scope:** this leg only. The adjacent partial-identity `ValueError` in
`src/ccf/assembly/worker.py::SpecDrivenEntityResolution.resolve` is outside scope by ruling
and was excluded from every reviewer's brief. **Every reviewer was told the SDK is destined
for a BANK** and to be more conservative than for ordinary code.

**What this record does NOT do:** no production edit, no merge, no tag, no release, no
`SEC-007` closure. Findings are recorded and verified; none is fixed here. The merge is Dave's
act.

## 1. Reviewer seats and evidence status

Two kinds of evidence are kept apart throughout: **INSPECTED** (the reviewer read the tree or
the inlined source) and **INDEPENDENTLY EXECUTED** (the reviewer ran the tests or probes
itself and captured the output). "Reported" means evidence captured by the author's session,
not re-executed by that reviewer.

| seat | model / tool | subject | evidence | disposition | findings |
| --- | --- | --- | --- | --- | --- |
| **codex** | codex-cli 0.137.0, API-key auth | inlined payload on stdin | INSPECTED (48,621 tokens read) | **PROCEED** | 0 |
| **cursor** | cursor 3.19.13 | inlined payload on stdin, from a scratch cwd | INSPECTED | **PROCEED** | 1 ADVISORY |
| **gemini** | gemini CLI, `GOOGLE_API_KEY` | inlined payload on stdin | INSPECTED | **PROCEED** | 0 |
| **independent executor** | Claude Opus 5 subagent, no session context | its own detached worktree at the pin | **INDEPENDENTLY EXECUTED** | `ALL_FOUR_PASS_AND_SEVERING_DISCRIMINATES` | — |
| **independent adversarial review** | Claude Opus 5 subagent, no session context | its own detached worktrees at the pin and at the base | INSPECTED + **INDEPENDENTLY EXECUTED** (the four tests, its own severing, suites, probes) | **PROCEED** | 2 ADVISORY |
| **refuters** | 4 × Claude Opus 5 subagents, one per finding per lens | their own detached worktrees at the pin | INSPECTED + INDEPENDENTLY EXECUTED | per finding, §3 | — |

The executing model (Claude Fable 5.1, the author of the repair) is excluded from every seat
above; it assembled the payload, resolved every citation against the pinned tree, re-ran each
reviewer's reproducing command itself (§3), and wrote this record.

**Read-proof before any reply was counted.** A canary (`Reply with exactly the single word
GRIFFIN`) was sent to each CLI first; all three answered `GRIFFIN` (rc 0, identical output,
sha256 `09b07c4b…`). The payload began with a token (`HERON-007`) that a reply must repeat;
all three replies carry it. Every citation in every reply was then resolved against the
pinned tree by `grep`/`sed` (codex 9/9, cursor 3/3 including `_refuse_declared_at_seam`,
gemini 2/2). No fabricated symbol or quotation was found in this round.

### Exact invocations (all from a scratch directory outside the repository)

```
printenv CODEX_API_KEY | codex login --with-api-key
timeout 570 codex exec --skip-git-repo-check - < payload.txt      # rc 0, 17 s, 3,745 B
timeout 570 cursor agent -p --mode ask -f          < payload.txt      # rc 0, 68 s, 4,076 B
timeout 570 gemini -p -                            < payload.txt      # rc 0, 55 s, 2,163 B
```

`CODEX_API_KEY`, `CURSOR_API_KEY` and `GOOGLE_API_KEY` were read from the untracked
`homecams_v2/.env`; nothing was committed from it. Gemini's stderr carried only the known
`Both GOOGLE_API_KEY and GEMINI_API_KEY are set` notice. Payloads went on **stdin** (a single
argv string caps at 128 KB and dies rc=126 with empty output).

## 2. The payload was HAND-ASSEMBLED, and here is what it left out

`get-shit-done/workflows/review.md` gathers plans and asks for a plan review, which is wrong
at close; the close-time payload was assembled by hand from the shipped subjects, which
CLAUDE.md §3.1 calls conforming provided the omissions are named. It was **inlined with line
numbers, not referenced by path**, because codex's sandbox on this host can exit 0 having read
nothing. 182,398 bytes / 2,656 lines, sha256 `286c5316…`, scanned for secrets (0 hits).

Inlined: the three commit messages after the base; the complete `git diff` base..candidate;
**all of `src/ccf/assembly/worker.py`**; `src/ccf/products/resolver.py` at the SDK seam map
(`SDK_SEAM_REFUSALS`, `_refuse_sdk_owned_seam_refusal`) and at the conversion
(`GovernedResolver._declared_seam_refusal` and the minting of the declared refusal);
`src/ccf/products/product.py` at the acquisition seam; the four retained tests with their
fixtures; the SDK-map roster test; the surface fragment; the amended `D-IMPL-362` entry.

**NOT in the payload, so NOT reviewed by the external panel:** the rest of
`src/ccf/products/resolver.py` and `src/ccf/products/product.py`, `runtime/` (the MCP and
HTTP doors, `ccf_runtime/cdc/envelope_map.py`), `src/ccf/replay/`, every example tree, and
`public/`. The external panel's silence about those is not evidence about them. They were
covered by the **independent adversarial review**, which had full tree access and checked the
federated relay (`AssemblyWorker.ingest_admitted`), the CDC path, every reader of
`IdentityRefused.key`/`.field` across `src/`, `runtime/`, `tests/`, `examples/` and
`archive/`, and `public/` + `docs/schemas` (zero mentions of the class).

The brief listed what is **known and ruled** and forbade re-deriving it (mint-time site; the
reason word; `SDK_SEAM_REFUSALS` unchanged; partial identity out of scope; the deleted
demonstration test and its coverage mapping) and asked eight adjacent questions (readers of
`key`/`field` that assume `str`; federated and CDC relay; validator interplay; URI stability;
per-test discriminating power; accuracy of fragment / manifest / `SURFACE-CHANGES.md` /
`D-IMPL-362` against the tree; the undeclared message; hash transparency).

## 3. Findings — verified against the pinned tree before being recorded

### CR-362-01 — ADVISORY, CONFIRMED. The message template is selected by `key is None`, not by `reason`, and the widened constructor admits contradictory combinations

Raised independently by **cursor** (its finding 1) and by the **independent review**
(`OP5-A-01`); both refuters of `OP5-A-01` returned *not refuted, severity agreed*.

**Claim (TREE):** `src/ccf/assembly/worker.py::IdentityRefused.__init__` now declares `key` and
`field` as `str | None = None` and branches the message on `if key is None:`. At the base both
were required, so the value fault and the declaration fault could not be confused. The
constructor is public (`__all__`), is the single key of
`src/ccf/products/resolver.py::SDK_SEAM_REFUSALS`, and that map's own commentary states that a
deployment's seam callable "can obtain the same conversion by importing
`ccf.assembly.worker.IdentityRefused` and raising it" — so deployment code is an invited raiser,
and the acquisition seam copies `str(error)` unedited into the replay record's
`assembly_refusal` detail.

**Reproduced (RUN, by the author on `253dcc40`, and independently by the review and both
refuters):**

- `IdentityRefused(envelope_id="e1", entity_class="company", reason="null")` (key omitted) →
  *"… matched rule for 'company', which declares no identity keys (null); …"* — a declaration
  fault that did not happen, with a value reason inside it.
- `IdentityRefused(envelope_id="e", entity_class="c", reason="null", key="lei")` (field
  omitted) → *"… key 'lei' read from payload field None; …"* — the literal text `None`, the
  defect class `D-IMPL-357` B4 removed from attributes in this same file.
- Driven through the real governed path by the independent review: a seam callable raising the
  first form produced a `RefusalEnvelope` at seam `acquisition` whose RECORDED detail was the
  false declaration sentence. At the base the same construction was a `TypeError`.

**Not reached by any SDK path:** the two production raise sites are consistent — the empty
branch passes `reason="undeclared"` and no key; the value branch passes `key`, `field` and the
value reason.

**Severity:** ADVISORY under §3.1 — no invariant is violated, the acceptance criterion is met,
and no SDK path produces the combination; the exposure is a public-constructor misuse by
deployment code that then lands in an audit record. **Not fixed here** (no production edits in
this review). The repair shape every seat converged on: a constructor guard holding
`reason == "undeclared"` equivalent to `key is None and field is None` (both required
otherwise), branching the message on `reason`; one file, red test first. **Whether to take it,
and when, is Dave's call.**

### CR-362-02 — raised ADVISORY; narrow fact CONFIRMED; REJECTED as a §3.1 finding; carried as optional polish

Raised by the **independent review** (`OP5-A-02`): the `identity_keys` entry of
`src/ccf/assembly/worker.py::EntityResolutionRule`'s docstring says nothing about the empty
tuple, and no validator or boot path judges it, so "the docstring is the only pre-runtime
warning surface and it is empty."

**Refuters split** — one *not refuted*, one *refuted*. Adjudicated by the author against the
tree:

- **The narrow fact is true (TREE):** the `identity_keys:` entry and the class note mention
  only the `*_ref: True` boolean case; zero mentions of `()`, `undeclared`, "zero" or "at
  least" in the class docstring (measured by `grep` over its lines).
- **The load-bearing sentence is false (TREE):** it is not the only pre-runtime surface. The
  empty case is documented on `IdentityRefused`'s own docstring ("an EMPTY DECLARATION — a
  rule whose `identity_keys` is `()`"), in the surface fragment's Migration section and in the
  assembled `docs/SURFACE-CHANGES.md` ("a deployment whose resolution spec declares a rule
  with `identity_keys: []` now receives a governed refusal …"), i.e. in the adopter's own
  artifact form.
- **The harm premise is ruled:** "constructs" is the first clause of the recorded acceptance
  criterion and the construction pin exists on purpose; a runtime refusal being the first
  signal is the adopted design, not an omission.
- **The reviewer's third evidence output was a hand-written summary**, not a captured output
  (it named a comment at a line the grep does not return) — the reading rule this project
  applies to every count.

**Recorded as:** not a defect against §3.1 (no invariant, no fidelity defect, no missing
deliverable element — fragment, assembled log and exception docstring are present — and no
unsurfaced decision). **Carried as optional polish:** one cross-reference sentence on the
`identity_keys` docstring entry pointing at the `undeclared` refusal. Zero risk; outside this
leg's acceptance criterion; not a blocker on the merge decision.

### Retractions

None offered by any seat. Nothing in the "known and ruled" list was contradicted.

## 4. Independent execution — exact commands and results (INDEPENDENTLY EXECUTED by the Opus 5 executor, in its own worktree)

Worktree: a detached checkout of `253dcc40` under the session scratchpad (`exec-253dcc40`);
`git rev-parse HEAD` verified equal to the pin and `git status --porcelain` empty before
anything else; `ccf` and `ccf_runtime` verified to import from inside that worktree.

Interpreter and environment for every command below:
`PYTHONPATH=.:src:runtime:tests /home/parkave/ccf_wt/qual-a4cf2fb7/.venv/bin/python -B`.

1. **Baseline** — `-m pytest -p no:cacheprovider -q -rA --tb=short` on the four node ids
   (`tests/assembly/test_worker.py::test_a_rule_declaring_no_identity_keys_constructs`,
   `tests/assembly/test_worker.py::test_a_matching_envelope_under_an_empty_identity_declaration_is_refused_by_name`,
   `tests/assembly/test_worker.py::test_an_empty_identity_declaration_mints_no_entity_and_no_relationship`,
   `tests/products/test_d_impl_347_seam_refusals.py::test_the_REAL_route_converts_an_empty_identity_declaration_with_the_workers_own_reason`):
   **4 passed in 0.72s**, all four listed PASSED.
2. **Sever only the empty-key raise.** Bytes saved; sha256 of the original recorded
   (`e61e699e…`). An exact-match replacement of the `if not source_of: raise IdentityRefused(…)`
   block with the base's bare `ValueError` text plus a `# SABOTAGE` marker — occurrence count
   asserted **1** before writing. `__pycache__` purged under `src/` and `tests/`. Same command:
   **3 failed, 1 passed in 0.80s** — the construction pin PASSED; the three behavioral tests
   FAILED, each with `builtins.ValueError` whose message contains *"declares no identity keys"*,
   raised in `src/ccf/assembly/worker.py::SpecDrivenEntityResolution.resolve`, reached by three
   distinct routes: the direct `resolve` call; `AssemblyWorker.ingest`; and the real product
   route `OpenedProduct.answer` → `GovernedResolver.__call__` → the acquisition seam → the
   test's `acquire` → `resolve`.
3. **Restore byte-for-byte.** `cp` of the saved bytes; `sha256sum -c` printed
   `src/ccf/assembly/worker.py: OK`; `grep -c SABOTAGE` = **0**; `git status --porcelain`
   **empty**; `__pycache__` purged; same command: **4 passed in 0.66s**.
4. **Diff checks (TREE):** files in `git diff 621173a1..253dcc40`: `docs/DECISIONS.md`,
   `docs/SURFACE-CHANGES.md`, the `007-…` fragment, `docs/surface/v0.2-surface.json`,
   `src/ccf/assembly/worker.py`, the two test files. `src/ccf/products/resolver.py` **not** in
   the diff; lines containing "lacks identity keys" in the worker diff: **0**.
5. **Anomalies:** none.

The **independent adversarial review** repeated steps 1–3 on its own, in its own worktree,
with the same outcome (4 passed; 3 failed + 1 passed under its own severing; `OK` / 0 markers /
clean / 4 passed after restore), and additionally corroborated the RED claim at `c096b35b`
from the tree: `git diff --stat 621173a1..c096b35b` touches only the two test files, so the
production state the severing reproduced is exactly `c096b35b`'s.

## 5. Checked, not defects — consolidated across the four seats

- **Readers of `IdentityRefused.key`/`.field`:** none in `src/`, `runtime/`, `examples/` or
  `archive/` reads either attribute; the conversion uses `str(error)` only. The `.refusal.key`
  readers in `src/ccf/client` and `src/ccf/products/child_resolver.py` are `RefusalEnvelope`'s
  `key`, a different object (all three externals and the review said so explicitly).
- **Federated and CDC relay:** exactly one mint caller exists (`AssemblyWorker.ingest`);
  `AssemblyWorker.ingest_admitted` relabels and calls `ingest`, and the paved acquisition seam
  calls `worker.ingest`, so an empty-keys rule raises the identical `IdentityRefused` on every
  route; nothing mints or crashes before it (codex, cursor, gemini, review).
- **Validator interplay (RUN by the review):** `identity_keys=()` with a non-empty
  `identity_sources` is refused at construction by the existing validator with a truthful
  message; with `attribute_keys` it constructs and refuses at the mint; two empty rules — the
  first matching one refuses before any mint; a relationship whose endpoint rule is empty
  refuses during entity resolution before any edge.
- **URI stability (TREE):** the five diff hunks sit inside `IdentityRefused` and the
  `if not source_of:` branch; `_identity_text` is byte-identical across base and candidate
  (the review hashed the extracted function body); the only diff line mentioning
  `content_hash` is a docstring line. No previously-minted URI moves.
- **Discriminating power:** each test has a named blind spot and another of the four closes it
  — the pin would stay green under a boot-time refusal or a restored `{}` mint; the by-name test
  under a broken seam conversion; the ingest test under broken governed recording; the real-route
  test under a `{}` mint on a non-acquire path. As a set they pin construct / named refusal /
  no `{}` URI / governed record (codex, cursor, review).
- **Documents against the tree:** no sentence in the fragment, the manifest shape line, the
  `SURFACE-CHANGES.md` entry or the `D-IMPL-362` entry was found untrue of the tree; the
  before/after signatures match `inspect.signature` exactly; the six-member value roster is
  exactly what `_identity_text` returns (all four seats).
- **Published pages and schemas:** zero mentions of `IdentityRefused` under `public/` or
  `docs/schemas/`; nothing can disagree (review, by grep).
- **Replay record for the undeclared case (RUN by the review):** with nothing declared on the
  product class, `RefusalEnvelope` at seam `acquisition`; the recorded block carries cause
  `nonexistent`, error code `identity-refused`, and the worker's own detail with
  `(undeclared)` and "declares no identity keys"; the SERVED detail stays the minimal
  disclosure.
- **Hash transparency:** `IdentityRefused` is an exception, not a `CCFContract`; no hashed
  shape or generation boundary moves (all four seats).
- **Regression surface (RUN by the review, in its worktree):** `tests/assembly` +
  `tests/products` 1773 passed; `tests/test_surface_drift.py` + `tests/test_surface_completeness.py`
  26 passed; `tools.lints --all` rc 0; mypy on the changed file clean; the citation ratchet
  (365) and the retirement-sweep red are **identical at the base**, i.e. pre-existing.
- **Scope discipline:** the partial-identity `ValueError` appears in no diff line and is
  reported on nowhere; `SDK_SEAM_REFUSALS` keeps its single key.

## 6. Disposition

All four reviewing seats returned **PROCEED**. Verified findings: **one ADVISORY carried
(CR-362-01)** and **one optional polish item (CR-362-02)**; **no BLOCKING finding**. No
retractions. Nothing in this record merges, tags, releases, or closes `SEC-007`; the
identifier's row stays OPEN and the merge decision is Dave's.

## 7. Provenance of the raw material (withheld from the tree, available on request)

Kept in the session scratchpad and delivered to Dave as files: `payload.txt` (sha256
`286c5316…`), `codex.out` (`2964ec95…`), `cursor.out` (`6adcb05c…`), `gemini.out`
(`5ae77efe…`), the three canary outputs, the executor's saved bytes and hash, the workflow
journal with every subagent's structured return, and the author's own verification outputs.
They are not committed because they carry hundreds of line-number citations that would move
the citation-coverage population; this record cites by `path::Symbol` only.
