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
| Source commit | **`2cd96aef8050210c30b177f65f47017fb0a30555`**: the commit the final hosted run ran on, and the commit the wheel was built from. Later commits on `main` change this page and the decision log only |
| Wheel and checksums | `ccf_sdk-1.0.2.dev1551+g2cd96aef8-py3-none-any.whl`, sha256 `69a9a7a5d9b1e5ee735f4f6ded271c827403940911700f74667d2d91b5677c18`, built from `2cd96aef` in a clean detached worktree; `SHA256SUMS` sits next to the wheel |
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

**Measured on `c0c43b26` and again on the final `2cd96aef`: 16 of 16 checks passed.** The instance served the
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

The examples were measured on `c0c43b26`. Everything that the nine type
corrections (`cc9e83ab`) could affect was measured again on the final code:
the type check, the full suite, lint, tools tests, product gates, perf
smoke, the 160 example tests on the changed paths, both tutorials, the wheel
and the bank configuration. Every count below is compared by test id against
the recorded baseline.

| check | result |
|---|---|
| `mypy --strict` (the hosted command, `mypy`) | 0 errors in 265 source files (was 9) |
| Full regression suite (`tests/`, local Fluree exported), on `cc9e83ab` | 14,368 passed, 22 failed: the 21 carried SEC-020 ids plus the version-stamp test (no tag). Identical failing ids to before the correction; the seven s1-01 tests run and pass |
| Lints (`tools.lints --all`) | 0 violations |
| Tools tests (lints, docs, publish scan, product gates) | 1,403 passed |
| Product gates | 30 product trees, 519 declared gates, 519 executing |
| Performance smoke (`tests/perf_smoke`) | 10 passed, inside the 300 s cap |
| Bank configuration (`verify.py`), on `2cd96aef` | 16 of 16 checks passed |
| Both Hello World tutorials, exact commands, on `2cd96aef` | hw1 `a8335bb4…2df4` in-process and over MCP; harness clients `c38d30f2…9197`, three legs MATCH; s1-00 6 of 10; s1-01 `b54bd625…`, `9aa1eac8…`, `512d1856…` |
| Wheel (`verify_wheel.sh`), from `2cd96aef` | 5 of 5: version names the commit, imports come from the wheel, adapter provenance matches, CLI runs |
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

**Run `38264811239` on `2cd96aef`: completed, conclusion failure, on the 21
carried SEC-020 ids alone.** By job:

| job / step | result |
|---|---|
| lint + `mypy --strict` | **pass** (0 type errors) |
| docs gate (strict build and publish scan) | **pass** |
| examples suite | **pass** |
| harness adapter conformance (three legs) | **pass** |
| Postgres, SEC-013 Postgres lease, Neo4j, MongoDB and Fluree legs | **pass** |
| quick suite (includes `tests/perf_smoke`, 10 tests) | 13,865 passed; **21 failed, all carried SEC-020** (`tests/products/test_sec020_combined_proof.py::test_a_pin_filed_in_one_deployment_reads_alike_in_both[...]`); no other id |

The badge is red, and that is accurate: SEC-020 is open. No test expectation or
CI setting was changed to turn it green. Actual billed time was about 44
minutes (32 + 5 + 5 + 2), about $0.35, under the estimate.

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
