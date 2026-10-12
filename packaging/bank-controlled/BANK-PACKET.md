<!--
Copyright (c) 2026 David Castillo. All rights reserved.
Use, copying, modification, and distribution of the covered material
are governed by the CCF SDK Interim Software and Patent License
in the repository-root LICENSE.md and any controlling signed agreement.
Rights under that interim license begin only upon its execution
and are limited to its stated scope and term.
-->
# Bank packet: Tuesday 2026-10-13 delivery

Dave's Tuesday delivery GO (2026-10-11 14:51 MST, item 7) and his 23:44 MST
ruling, both recorded verbatim in `docs/DECISIONS.md`. This page covers one
controlled deployment configuration. **It is not a claim that the SDK's
security findings are closed.** The open ones are listed by name in
[section 5](#5-security-statement).

**No tag. No public upload.** The PyPI name placeholder
(`packaging/pypi-placeholder/`) is uploaded by Dave from his own account, and
by nobody else.

## 1. What is delivered

| item | where |
|---|---|
| Source commit | the commit the hosted run in [section 4a](#4a-hosted-ci) ran on: `5fb28b6f` plus the nine type corrections (`cc9e83ab`) and this page. Its SHA, and the wheel built from it, are recorded in section 4a |
| Wheel and checksums | built from that commit in a clean detached worktree; `SHA256SUMS` sits next to the wheel (section 3) |
| Tested deployment configuration | `packaging/bank-controlled/`: `launch.sh`, `stop.sh`, `verify.py`, `instance.env.example`, `question.yaml` |
| Example commands and transcripts | every example's default command and tests, run on the final code commit (section 4) |
| Installation and security docs | `public/how-to/security-and-deployment.md`, `public/tutorial/`, this page |

## 2. The controlled configuration

One instance of the governed product door, launched by `launch.sh` and
checked by `verify.py`:

- **One engine, one store, and one approval queue per instance.** No two
  processes share a graph store or an approval queue. This is what excludes
  SEC-001's cross-process shared-store case (section 5).
- **SQLite writer identity lock required** (SEC-013); the lock directory is
  SDK-managed.
- **Listens on 127.0.0.1 only**, behind a credential: no credential and a
  wrong credential are each refused with 401.
- **Exactly one tool, the read-only product request.** No upload,
  storage-administration, audit or replay handle is exposed.
- **An environment allow-list**: the door process holds only the names the
  configuration declares.
- **Instance root mode 0700; secrets file mode 0600.**

Launch, verify, stop:

```bash
packaging/bank-controlled/launch.sh <instance-root> <sdk-tree> <python>
python packaging/bank-controlled/verify.py <instance-root> <sdk-tree>
packaging/bank-controlled/stop.sh <instance-root>
```

**Measured on `c0c43b26`: 16 of 16 checks passed.** The instance served the
demonstration question (content address `611f5dac…03ae`) and refused a
question for another tenant. Transcript: `bank-launch.txt`,
`bank-verify.txt`.

**Disclosure:** the check ran under the developer account (uid 1000), not a
dedicated OS service account, because none could be created on the test host
without root. The ownership and mode checks compare against whichever account
runs the door. Run them again under the bank's own service account.

## 3. Installing the wheel

```bash
python -m venv /opt/ccf/venv
/opt/ccf/venv/bin/pip install --require-hashes -r requirements.lock
/opt/ccf/venv/bin/pip install --no-deps <wheel>
sha256sum -c SHA256SUMS
packaging/release-check/verify_wheel.sh <wheel> <commit-prefix> <workdir>
```

`verify_wheel.sh` checks that the installed version names the commit, that
imports resolve from the wheel rather than a source tree, that the adapter
provenance matches the version, and that the CLI runs.

## 4. Verification on the final code commit

Measured on `c0c43b26`, then re-checked on `5fb28b6f`, which adds only the five
specimen-digest re-pins the banner required. Every count below is compared by
test id against the recorded baseline.

| check | result |
|---|---|
| Full regression suite (`tests/`, local Fluree exported) | 14,365 passed, 22 failed: the 21 carried SEC-020 ids plus the version-stamp test (no tag). No new failure; the seven s1-01 tests now run and pass |
| Lints (`tools.lints --all`) | 0 violations |
| Tools tests (lints, docs, publish scan, product gates) | 1,403 passed |
| Product gates | 30 product trees, 519 declared gates, 519 executing |
| Performance smoke (`tests/perf_smoke`) | 10 passed, inside the 300 s cap |
| Bank configuration (`verify.py`) | 16 of 16 checks passed |
| Example default commands | 37 runnable; **35 serve a product to a client**; 2 refuse as their READMEs promise (below) |
| Example tests with estate credentials | 1,425 passed; 3 failed and 5 errors remain, all carried (below), after the 3 specimen re-pins (76 passed in those modules) |

**Example count.** 34 examples serve from their default command. door-cp-05
counts as serving because a client receives its product: cp-14's diagnostic
run (`DEBT_TOLERANCE=1.0`) admitted door-cp-05's product as a child (child
address `c00a02bb…40c5`), and
`test_door_cp_05_exposure.py::test_the_door_and_the_in_process_run_serve_one_content_address`
passes. Booting alone was not counted. cp-05 is WITHHELD for
tolerance-exceeded at its default, and cp-14 refuses at its default because
door-cp-05's child exceeds tolerance; cp-14 serves at the diagnostic
tolerance. `external` is a charter with nothing to run.

**Carried example-test failures** (open, named):

- `test_cp_05_mcp_door.py`, 5 setup errors: these drive cp-05's own
  `server/serve.py`, which **door-cp-05 superseded**. They are not failures
  of the supported door: door-cp-05's 12 tests pass.
- `test_cp_04_seams.py::test_replay_carries_the_assembler_identity_for_fulfilled_and_refused`:
  `KeyError 'assembler_id'` (assembler identity on served records).
- `test_cp_04_seams.py::test_the_seed_carries_what_these_five_gates_need`:
  the live estate holds 253 more LEIs than the committed fixture it compares
  against.
- `test_cp_06_mcp_door.py::test_a_question_with_no_anchor_is_refused_by_GOVERNANCE`:
  an identity refusal reaches the caller as a transport error instead of a
  governed refusal.

**cp-04 jurisdiction (Dave, 23:44).** The failing ask was **not** served. It
was refused for anchor ambiguity, because its LEI now names five graph nodes.
The test is re-aimed at a single-node GB family, and the post-refusal ask
must now carry a product, not just a cleared error flag. Disabling the
out-of-set check makes the same request serve a product, and the test goes
red. The declared set `{NL, US-DE}` is unchanged.

## 4a. Hosted CI

**Estimated cost, recorded before launch:** about 67 billed Linux minutes
(the previous run, `38222562272`, ran its jobs for 51.3 + 6.0 + 5.4 + 1.7
minutes, and GitHub rounds each job up). At $0.008 a minute, with October's
free quota already used, that is about **$0.54**. The previous commit is not
re-run.

Results are recorded after the run, in the follow-up commit.

## 5. Security statement

**What was actually tested.** The deployment claims in this page cover one
transport and one configuration: the governed product door over **MCP
streamable HTTP on 127.0.0.1**, behind a bearer credential, launched by
`launch.sh` with one engine, store and queue per instance, a SQLite graph
store and the SDK-managed identity lock. The HTTP API door, MCP over stdio,
A2A, and the other graph backends were exercised by the test suite and the
hosted database legs, **not** under this configuration. Nothing here claims
more than that.

**Fixed in this delivery** (each has a regression test and one deliberate
break that turns it red), with where each was tested:

- Approval queue and approval store can no longer be shared across engines.
  *In-process SDK refusal at engine wiring; transport-independent.*
- The SQLite writer requires its identity lock, and the paved road creates
  the lock directory. *SQLite graph store only, which is the store this
  configuration uses.*
- A typed registration over an existing untyped one is refused
  (D-IMPL-381). *Control Plane registry, in-process.*
- An entitled caller asking for an undeclared product class gets the same
  reply as an unentitled one, so the reply does not reveal whether the class
  exists (R5-CP17-F01). *The standard MCP door only. The HTTP door still
  distinguishes the case (listed under "still open").*

**Constrained by this deployment, not fixed in the SDK:**

- **SEC-001**: the cross-process shared-store case. Excluded by running one
  engine, store and queue per instance.
- **SEC-013**: the identity lock is required; its limits are as stated in the
  design (section 4.6 of the security how-to).

**Still open (named, not closed):**

- **SEC-020**: 21 standing test ids in `tests/products/test_sec020_combined_proof.py`.
- **SEC-027**: the PyPI name reservation; Dave's upload.
- **SEC-029**: the release version stamp; no tag exists.
- The HTTP door distinguishes an undeclared product class by status code
  (403 vs 404).
- A paved-road resource read without a request raises instead of refusing.
- Designs 1.5 (audit recovery) and 1.6 (record authenticity).
- R-1 (harness process-id reuse), R-2 (empty-tenant wording), R-3
  (unreachable reader check).
- Equal decimals at different scales take different content addresses.
- The MCP door's request argument is an opaque string a model cannot derive
  (backlog).

## 6. Rollback

1. `packaging/bank-controlled/stop.sh <instance-root>`; confirm that the
   announced port is no longer listening.
2. Reinstall the previous wheel into the same venv
   (`pip install --no-deps --force-reinstall <previous-wheel>`), or point
   `launch.sh` at the previous SDK tree.
3. Relaunch and run `verify.py`. Recorded replay artifacts in the instance
   root are content-addressed and are not rewritten by a rollback.

## 7. Owners

| responsibility | owner |
|---|---|
| Release approval, rulings, PyPI placeholder upload | Dave Castillo |
| Build, verification and this packet | Claude Code session for the ccf-sdk agent, under Dave's direction |
| Bank-side service account, host and operations | **to be named by the bank** |
