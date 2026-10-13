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
ruling, and his 2026-10-12 rulings (07:04 type corrections; 08:45
improvement-batch GO; about 10:55 merge and hosted-run GO; 12:50
documentation baseline and follow-ups; 16:03 documentation close-out
accepted, with the limits below; 16:56 handoff sign-off paperwork removed),
all recorded verbatim in
`docs/DECISIONS.md`. What changed for adopters is summarized in
[`RELEASE-NOTES.md`](RELEASE-NOTES.md). This page covers one
controlled deployment configuration. **It is not a claim that the SDK's
security findings are closed.** The open ones are listed by name in
[section 5](#5-security-statement).

**No tag. No public upload.** The PyPI name placeholder
(`packaging/pypi-placeholder/`) is uploaded by Dave from his own account, and
by nobody else.

## Limits of this delivery (read before deploying)

Dave accepted the documentation close-out on 2026-10-12 at 16:03 MST with
these limits, and they hold for every use of this delivery:

- **The handoff covers the tested bank configuration only**: the governed
  product door over MCP streamable HTTP on 127.0.0.1, one engine, store and
  approval queue per instance, a SQLite graph store with its identity lock
  (section 2). The HTTP API door, MCP over stdio, A2A, the MCP artifact
  server and the other graph backends were exercised by the test suite, not
  under this configuration.
- **Erasure completion over the MCP-backed artifact store is unsupported.**
  An erasure over it reaches approval and no further, before and after this
  release (follow-up 6). Complete erasures through an in-process store.
- **Mixed-version erasure requests stay disabled during an upgrade.**
  Upgrade the MCP artifact server first, or with its clients, and submit no
  erasure request through an erasure door client until that client is
  upgraded too: an older door client against an upgraded server admits a
  request naming a client twin of governed evidence, which the upgraded
  client refuses (measured).
- **SEC-020 and the other findings in [section 5](#5-security-statement) stay open.** Green CI is not
  security closure.

## 1. What is delivered

| item | where |
|---|---|
| Source commit | **`01fc424d92f8d15856d5f277e9cf18ef59bc7883`**: the commit the final hosted run ran on, and the commit the wheel was built from. Its code is the checked candidate `0af000f0`; `01fc424d` adds one commit that changes only this page and the decision log, and `main` was fast-forwarded to it. Later commits on `main` change documentation only (this page, the release notes, the decision log, the root and `packaging/` READMEs, the generated `RETIREMENT-COUPLINGS.md` report and public pages), never code; `git diff --name-only 01fc424d main` lists them |
| Wheel and checksums | `ccf_sdk-1.0.2.dev1564+g01fc424d9-py3-none-any.whl`, sha256 `186c9b73960c250a51e8c0ad7952721d9ca80d71055655933b09092c1fa8e9cc`, built from `01fc424d` in a clean detached worktree; `SHA256SUMS` sits next to the wheel. It replaces the Tuesday handoff wheel (`ccf_sdk-1.0.2.dev1551+g2cd96aef8`, sha256 `69a9a7a5…7c18`) |
| Tested deployment configuration | `packaging/bank-controlled/`: `launch.sh`, `stop.sh`, `verify.py`, `instance.env.example`, `question.yaml` |
| Release notes | [`RELEASE-NOTES.md`](RELEASE-NOTES.md): what changed for adopters, migration, functionality removed, follow-ups |
| Delivery folder | `ccf-sdk-delivery-2026-10-13/`, handed over with this page: the wheel, `SHA256SUMS`, `requirements.lock`, the configuration files, the previous wheel for rollback, and every transcript this page cites, with its own `README.md` and `MANIFEST.sha256` |
| Example commands and transcripts | every example's default command and tests, run on the code of the source commit (section 4.0) |
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

**Measured on `c0c43b26`, on `2cd96aef`, and again on the batch candidate `0af000f0`, whose code the final `01fc424d` carries unchanged: 16 of 16 checks passed each time.** The instance served the
demonstration question (content address `611f5dac…03ae`) and refused a
question for another tenant. Transcripts, in the delivery folder:
`evidence/bank-config/bank-launch.txt` and `bank-verify.txt` (`0af000f0`);
the earlier runs are under `evidence/bank-config/earlier/`.

**Disclosure:** the check ran under the developer account (uid 1000), not a
dedicated OS service account, because none could be created on the test host
without root. The ownership and mode checks compare against whichever account
runs the door. Run them again under the bank's own service account.

## 3. Installing the wheel

```bash
sha256sum -c MANIFEST.sha256     # first, at the delivery folder root: every delivered file, including wheel/requirements.lock
sha256sum -c SHA256SUMS          # then in wheel/, before installing anything
python -m venv /opt/ccf/venv
/opt/ccf/venv/bin/pip install --require-hashes -r requirements.lock
/opt/ccf/venv/bin/pip install --no-deps <wheel>
packaging/release-check/verify_wheel.sh <wheel> <commit-prefix> <workdir>
```

`SHA256SUMS` lists the wheel only. `requirements.lock` holds the hashes that
`--require-hashes` trusts for every dependency, so it is checked through
`MANIFEST.sha256` before anything is installed.

`verify_wheel.sh` builds its own throwaway venv and resolves the wheel's
dependencies from the configured package index without hash pinning, so it
needs index access; the checksum it prints is printed, not compared, which is
why `sha256sum -c` runs first. It deletes `<workdir>/venv` before it starts and
checks only its own throwaway install, never an existing one, so never give it
the parent folder of a deployed venv.

`verify_wheel.sh` checks that the installed version names the commit, that
imports resolve from the wheel rather than a source tree, that the adapter
provenance matches the version, and that the CLI runs.

## 4. Verification

### 4.0 The 2026-10-12 improvement batch (Dave's 08:45 GO)

Three packages, built on branch `batch-1012` and merged to `main` only after
these checks passed on the candidate `0af000f0`:

- **A. The HTTP product door's existence leak.** An entitled caller asking
  for an undeclared product class now gets the reply an unentitled caller
  gets for a real class: the same status, headers and body, apart from the
  per-answer replay reference and the echo of the class asked for, at the
  minimal (default) and reasoned disclosure levels. Every deny by the scope
  mapping on the product route is answered this way. The internal reason is
  on the record only.
- **B. Approval eligibility at submit.** A `WorkflowEngine` binds its Control
  Plane into its approval transport, and the reference transport refuses an
  ineligible `approve`/`reject` on a policy-named gate event before it is
  recorded. While the event the transport selects under the gate's key (its
  claimed event, otherwise the oldest queued one) is the gate's own
  approval-gate event, an outsider can no longer wedge the gate with a
  conflicting verdict; two other ways to wedge one remain open (section 5,
  follow-ups 1 and 2).
- **C. SEC-020 package, designs 1.1 + 1.2 + 1.3** (MCP versioned-URI
  resolution, write-then-read, and governed evidence through the erasure
  door), on the reading of Dave's 2026-10-09 10:54 ruling that keeps the
  uniform "cannot verify".

| check, on the candidate | result |
|---|---|
| Full regression suite (`b468cee4`; `0af000f0` adds one docstring) | 14,422 passed, **1 failed**: `tests/test_version_stamp.py::test_the_installed_version_is_not_the_stale_literal_and_is_git_derived`, which reads the installed package's version metadata and compares its commit with the checkout; the local suite environment had no installed metadata for the checked-out tree (`PackageNotFoundError`), a development-environment artifact. Hosted CI, which installs from the checkout, passes it. **The 21 SEC-020 gate cases now pass.** No new failing id |
| `mypy` / lints / tools tests / product gates / perf smoke | 0 errors / 0 / 1,403 passed / 519 of 519 / 10 passed |
| MCP, erasure, invariant and tools suites on `0af000f0` | 4,105 passed |
| Every example default command and the example tests, on `0af000f0` | identical to the morning roster: 35 of 37 serve a product to a client; the same 3 failures and 5 errors, all carried (below) |
| Both Hello World tutorials, on `0af000f0` | identical addresses (below) |
| Existing demonstration recordings | still valid: every serve or refuse outcome, and every content address for a question with a fixed as-of date, is unchanged from the morning runs. Values that depend on the time of the run change on every run, as before (replay-record addresses, timestamps, s1-00's debt and address, cp-06's debt, cp-20's expiry and address, and the record address cp-13-canonical prints), so no new run reproduces a recording byte for byte |
| Bank configuration, on `0af000f0` | 16 of 16 |
| Each package's own proof | a test red on the base and green after, plus severings that turn it red again (A: 1, B: 1, C: 5), each restored and hash-checked |
| One focused independent review (Cursor, the diff inlined, citations checked against the tree) | 0 critical, 0 high, 1 medium: a stale docstring on `match_artifact_subject`, corrected in `0af000f0` |
| Wheel (`verify_wheel.sh`), from `01fc424d` | 5 of 5: version names the commit, imports come from the wheel, adapter provenance matches, CLI runs |
| Hosted CI on `01fc424d` | **every job and step passed** (section 4a) |

Existing tests whose expectations moved, each a consequence of a recorded
ruling and named in its commit: none in A; in B, the inverted defect test (`test_an_ineligible_principals_opposite_verdict_is_refused_at_submit`)
plus three engine-site controls rebuilt over a transport that judges nothing
(assertions unchanged), and seven in C (the six the design predicted, plus
one cause-only assertion).

### 4.1 The Tuesday handoff measurements

The examples were measured on `c0c43b26`. Everything that the nine type
corrections (`cc9e83ab`) could affect was measured again on that handoff's code:
the type check, the full suite, lint, tools tests, product gates, perf
smoke, the 160 example tests on the changed paths, both tutorials, the wheel
and the bank configuration. Every count below is compared by test id against
the recorded baseline.

| check | result |
|---|---|
| `mypy --strict` (the hosted command, `mypy`) | 0 errors in 265 source files (was 9) |
| Full regression suite (`tests/`, local Fluree exported), on `cc9e83ab` | 14,368 passed, 22 failed: the 21 carried SEC-020 ids plus the version-stamp test (a development-environment artifact; see 4.0). Identical failing ids to before the correction; the seven s1-01 tests run and pass |
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

**The batch's hosted run. Estimated cost, recorded before launch:**
about 45 billed Linux minutes, from the last run's jobs (tests 32, docs 5,
lint 5, examples 2), which is about **$0.36** at $0.008 a minute, with
October's free quota already used. The results follow.

**Run `38287169568` on `01fc424d`: completed, conclusion success.** Every job
and every step passed. By job:

| job / step | result |
|---|---|
| lint + `mypy --strict` | **pass**: lint checker tests 982, product-gate checker tests 48, version-stamp gate tests 15 |
| docs gate (strict build and publish scan) | **pass**: 373 checker tests |
| examples suite | **pass** |
| quick suite (includes `tests/perf_smoke`) | **13,919 passed, 0 failed**, 82 skipped, 3 xfailed. **The 21 SEC-020 cases that failed in `38264811239` pass** |
| harness adapter conformance (three legs) | **pass**: 448 passed |
| Postgres, SEC-013 Postgres lease, Neo4j, MongoDB and Fluree legs | **pass**: 363, 1, 29, 38 and 306 passed |
| coverage (informational) | ran, 13,919 passed |

The badge is green because package C fixed what the 21 cases test. Seven existing
tests' expectations moved in package C, each a consequence of a recorded ruling
and named in its commit (section 4.0). No expectation or CI setting was changed
to turn the badge green. **Green does not mean SEC-020 is closed**: its
remaining limitations are listed in section 5, and these 21 cases do not test
them.

**Actual billed time: about 76 minutes** (tests 62, docs 6, lint 6, examples 2,
each job rounded up), **about $0.61**, over the $0.36 estimate. The estimate came
from a run whose quick suite failed. That skips the informational coverage step,
which re-runs the quick suite under coverage for 30 minutes. The coverage step runs
whenever the quick suite passes, so expect about 76 minutes for a passing run.

**Earlier, for the Tuesday handoff. Estimated cost, recorded before launch:** about 67 billed Linux minutes
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

That run's badge was red, and that was accurate: those 21 SEC-020 cases were failing. No test expectation or
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

- An approval queue kept in one process can no longer serve engines over
  two different Control Plane state stores, and an approval queue and its
  state store must both be process-local or both be shared between
  processes. Engines over the same store may still share one queue.
  *In-process SDK refusal at engine wiring; transport-independent.
  Independent shared stores behind one shared queue in different processes
  are not detected by the SDK; this configuration excludes them (SEC-001,
  below).*
- The SQLite writer requires its identity lock, and the paved road creates
  the lock directory. *SQLite graph store only, which is the store this
  configuration uses.*
- A typed registration over an existing untyped one is refused
  (D-IMPL-381). *Control Plane registry, in-process.*
- An entitled caller asking for an undeclared product class gets the same
  reply as an unentitled one, so the reply does not reveal whether the class
  exists (R5-CP17-F01), at the minimal (default) and reasoned disclosure
  levels; a principal granted full disclosure is told the internal cause.
  *The standard MCP door, and since the 2026-10-12 batch, the HTTP API
  product door (package A, tested through the HTTP app; not under the bank
  configuration, which serves MCP).*
- An ineligible approver's `approve`/`reject` on a policy-named approval-gate
  event is refused at submit by the reference transport once a
  `WorkflowEngine` is composed over it (package B). *In-process SDK; the bank
  configuration exposes no approval surface.*
- SEC-020's closing gate, `test_a_pin_filed_in_one_deployment_reads_alike_in_both`,
  passes all 21 cases that failed: three at the MCP versioned-URI resolution
  (design 1.1) and eighteen on write-then-read for the asker and for a second
  principal (design 1.2). The erasure door's own paths (design 1.3) are
  proven by their own tests (`tests/mcp/test_erasure_subject_match.py`,
  `tests/mcp/test_d3b_door_naming_path.py`), not by the closing gate. *Tested over the MCP artifact server in-process and in
  the two-deployment gate; not under the bank configuration, which exposes no
  artifact server.* **SEC-020 itself stays open** (below).

**Functionality removed by the batch** (each a deliberate restriction):

- On the HTTP product route, every deny by the scope mapping now answers
  `404 subject-unavailable`, not `403 request-unauthorized`, matching MCP,
  whichever axis failed (including a path tenant the credential holds that no
  scope entry's tenant pattern admits). A partial question, malformed
  `parameters`, or an `asked_at` with no UTC offset is still `400` first, and
  an `asked_at` that does not parse as a date-time is `422`. Unchanged: no
  credential, or one the auth hook does not recognize, is `401`; a credential
  with no tenant, a path tenant it does not hold at all and a class outside
  its roster are `403`; an allow the gate cannot mint from is `503`; every
  other route answers the deny `403`. A scope-mapping deny, on any route,
  stays on the audit log with the axis that failed; on the product route its
  replay record also carries the cause `unauthorized`, the error code
  `tenant-unauthorized` and the authorization decision id, not the axis. The
  `401` and `403` refusals the gate makes before the authorizer is asked
  write no audit event and no replay record (a known gap,
  `tests/http_api/test_tenant_authz.py::test_a_denial_before_the_authorizer_is_reached_writes_no_decision`).
- Ineligible `approve`/`reject` verdicts are no longer recorded on an
  engine-composed reference transport while the gate's own event is the one
  the transport selects under its key. Two cases still record one, unjudged,
  and it holds the gate if it disagrees with another verdict (section 5,
  follow-ups 1 and 2). A third-party transport composed into a
  `WorkflowEngine` must offer `bind_approver_eligibility`, and must use it:
  at `submit`, judge every `approve` or `reject` on an approval-gate event
  that names an approval policy against each bound plane with
  `ccf.hitl.transport.check_approver_eligibility`, before recording. The
  engine refuses a transport without the method; it cannot see whether one
  that has it judges anything, and no conformance test checks this. A
  transport used without an engine needs no such method. One
  transport shared by engines with different Control Planes needs every plane
  to admit a verdict.
- Over MCP, another principal of the tenant can no longer resolve a governed
  record it may not read, and nobody can resolve a query pin, an admitted
  child contract or a child question. The MCP erasure door's credential needs
  `artifact.subject.match` for every address, so it cannot erase ordinary
  client filings without it. The grant is the action `artifact.subject.match`
  on the resource `artifact.subject.match`, for one tenant, to an
  authenticated bearer; the server's `ErasureTrust` must also hold the
  tenant's `ErasureAuthority`, whose door key signs each query.
- **Upgrade order over MCP.** Upgrade the artifact server first, or with its
  clients. A new erasure door client against an older server is refused for
  every address (measured against `633c4e53`, which has the same code as
  `2cd96aef`, the previous wheel's source): it fails closed. Until the door's
  client is upgraded too, submit no erasure request through it: an older
  door client against an upgraded server admits a request that names a
  client twin of governed evidence, meaning governed evidence whose exact
  bytes, and so whose address, the tenant also filed under an ordinary
  client class (measured). The new door refuses such a request. Upgrade every
  `McpArtifactStore` client with the server: an older client resolving a
  governed versioned URI that an upgraded server refuses gets
  `McpServerUnreachable`, read as an outage, instead of the typed refusal
  (measured; nothing leaks); an admitted principal's resolution is unchanged.
  An erasure over the MCP-backed store does not complete, before or after
  this release (follow-up 6).
  *Not under this configuration, which exposes no artifact server.*

**Constrained by this deployment, not fixed in the SDK:**

- **SEC-001**: the cross-process shared-store case. Excluded by running one
  engine, store and queue per instance.
- **SEC-013**: the identity lock is required; its limits are as stated in the
  design (section 4.6 of the security how-to).
- **Refusals: an unauthorized ask reads as a missing record.** In this
  configuration, a caller who asks about a record it is not entitled to see
  gets the same answer as a caller who asks about a record that does not
  exist: the same status, kind, external reason and fields (`D-IMPL-253` Q27
  and amendment 2 (4); Dave's ruling of 2026-10-12 22:44 MST). Two things
  enforce it. The disclosure level is the default, `minimal`: the door
  registers its one-principal entitlement policy with no level and no
  per-principal override, and this configuration sets none. And every caller
  presents the one shared credential, so every caller is the same principal
  and no per-person setting applies. The decision record keeps the governed
  reason; it does not cross to the caller. **A distinct entitlement refusal
  for a named employee on a named information wall is not implemented:** no
  disclosure level states only "not entitled to this restricted class" (the
  `full` level reveals the whole internal record and is not authorized for
  this configuration), no population can be declared per wall, and the door
  judges the calling credential, not an employee an agent acts on behalf of.
  These are named follow-ups 7, 8 and 9 (below), not built. The ways the
  two answers can still be told apart are SEC-020's, below; SEC-020 stays
  open.

**Still open (named, not closed):**

- **SEC-020**, though its closing gate's 21 cases now pass. Still open:
  the reported limitation blocks, unchanged (D1 (a) 30/88, P6 24/44, E2 (ii)
  82/82); the shared-owner inspection that admits once its bound is reached
  in a long-running service (16 (C), unbuilt); its walk's blind spots; a
  composite child's decision record that names the stand-in; question stores
  reachable by a raw writer of the store directory; a store's own `get`, which
  checks nothing; timing (one extra read per question, measured at one
  scale); and the write timing over the wire, which is disclosed but not
  measured. SEC-020 closes only on Dave's ruling. SEC-009's erasure claim,
  which design 1.3 qualifies, stays open until it is verified.
- Approval, recorded as follow-up items on Dave's instruction of
  2026-10-12 12:50 MST (*"Record the late-verdict and escalation eligibility
  gaps as follow-up items with their exact conditions. Do not silently change
  the earlier ruling or begin another implementation round."*). Neither is
  built; the earlier rulings stand unchanged. Neither is reachable under this
  configuration, which exposes no approval surface. Both were reproduced by
  probe on `55ede124` with the reference transport and the real engine
  (delivery folder, `evidence/follow-ups/`). Both deny service; neither ever
  lets a gate pass wrongly.
  - **Follow-up 1, the late verdict (`D-IMPL-366` H2).** Conditions, all of
    them: a `WorkflowEngine` is suspended at an approval gate; a principal
    holding `HitlSubmit` for the gate's event key (any principal the
    deployment's authorizer admits for that key, whether or not the gate's
    approval policy admits it, the requester included) submits an `approve`
    or `reject` bound to the suspension's content hash; if the transport was
    constructed with a Control Plane whose HITL policy requires signed
    bindings, the submission is signed with a key that policy declares for
    that principal (code reading; a plane an engine binds does not set this,
    and the probes used a transport with no HITL policy); at that moment no
    event is queued or claimed under the key; and the gate has not closed.
    No event is under the key (a) after a deployment-composed
    `ApprovalGate.resolve` has consumed the event and before a resumption
    closes the gate, which the SDK does not time-limit; (b) after deployment
    code has drained the event with the transport's `dequeue`, which records
    no claim (for example, a worker that forwards events to a task system),
    and before the event is queued again or a resumption restores the
    request, which is the window
    `test_t12b_a_missing_state_verdict_still_counts_as_a_conflict` uses; (c)
    inside the engine's suspension, between its state write and its enqueue;
    or (d) after an interrupted suspension, until the starter's retried start
    or a resumption restores the request. The verdict is recorded unjudged
    (`event_state_at_submit` is `missing`) and never becomes authority. If
    it is the opposite of another verdict recorded on the suspension, every
    resumption is refused as a conflict, the gate never closes, and further
    verdicts cannot clear it. After the gate closes, the same submission is
    refused `hitl-gate-closed`. A late `annotate` or `override`, or a late
    verdict that agrees, does not hold the gate. This is what `D-IMPL-366`
    H2 requires (*"a blind opposite verdict still holds the gate as a
    conflict"*); changing it needs Dave's ruling, and
    `tests/workflow/test_sec006_engine_controls.py::test_t12b_a_missing_state_verdict_still_counts_as_a_conflict`
    pins it.
  - **Follow-up 2, a non-gate event under a gate's key (`D-IMPL-366`
    G6 (a)).** Conditions, all of them: deployment code files an
    `exception-escalation` event (or any other non-gate event) under the
    suspended gate's own event key; that event is the one the transport
    selects under the key (its claimed event, otherwise the oldest queued
    one), which holds whenever the gate's own event is neither the claimed
    event nor queued ahead of it: for example after a deployment-composed
    `ApprovalGate.resolve` has consumed the gate's event while the escalation
    is queued, while deployment code holds the gate's event out of the queue
    (measured), after the gate's event was handed back behind the escalation,
    after a refused `ExceptionEscalation.resolve` re-queued the gate's event
    behind the escalation (measured), after a failed `ApprovalGate.resolve`
    re-queued it at the tail, or after the engine restored an interrupted
    suspension's request behind the escalation (the last two by code
    reading); a principal holding `HitlSubmit` for the key submits an
    `approve` or `reject` bound to the suspension's content hash; if the
    transport, or on the escalation path the escalation primitive, was
    constructed with a HITL policy that requires signed bindings, the
    submission is signed with a key that policy declares for that principal
    (code reading; the probes used no HITL policy); the gate has not closed;
    and another recorded verdict on the suspension disagrees with it. The transport judges eligibility on approval-gate
    events only, so the verdict is recorded with no eligibility check. A
    verdict recorded through the escalation primitive never becomes
    authority. One recorded through a submit-only door can become authority
    only while the gate's own event is still queued and the gate's policy
    admits the principal, because the engine applies its own eligibility
    check; a principal the policy does not admit, the requester included,
    never gets authority this way. Either way, the engine counts every
    recorded verdict on the key and hash, so an opposite one holds the gate
    as a conflict. Such a principal can do this through the escalation
    primitive or through a submit-only path of the shape the HTTP action door
    uses (measured at the transport; the door itself by code reading). The
    MCP action door hands each action to a route the deployment supplies; it
    is such a path only where that route submits to the transport. No SDK door or shipped composition
    files an event under a gate's key; a deployment's own composition does.
    No test pins the conflict hold.
  - Signed bindings narrow both follow-ups but do not close them. When the
    transport's HITL policy requires signed bindings, an unsigned or wrongly
    keyed submission is refused even when no event is under the key
    (`tests/hitl/test_signed_binding_authority.py::test_required_and_unsigned_submission_is_a_typed_refusal`
    and `::test_required_and_invalid_or_mismatched_attestation_is_refused`).
    A transport has one HITL policy, and it declares keys per principal, not
    per gate, so a keyed principal who is the gate's requester, or who
    approves only other gates, can still do either.
  - There is no supported way to reopen a conflicted gate, and durable
    approval identity across stores (design 1.4's remainder) is unbuilt.
- **Follow-up 3, source docstrings.** 27 docstrings in `src/` and
  `runtime/` still describe behavior from before the batch (the MCP artifact
  server's module docstring and its names and resolution resources, the MCP
  store's and the artifact protocol's resolution notes, the erasure package
  and subject-match notes, the HITL transport's implementer notes, the
  engine's residual ledger, the HTTP error-code notes). Several are rendered
  on the public reference pages. They were not changed, because the
  delivered wheel is fixed at `01fc424d` and Dave ordered no further
  implementation round; the public how-to pages and this page carry the
  current behavior. The list is in the delivery folder,
  `evidence/follow-ups/source-docstrings.md`.
- **Follow-up 4, the authoring Standard's 403 row.** The Context Product
  Specification Standard v0.3 (section 9) and the spec-generation guide map
  "principal not entitled" to `403`; the SDK's HTTP product door answers it,
  and since 2026-10-12 a scope-mapping deny too, as `404
  subject-unavailable`. Eleven example specifications written to the
  Standard carry the same `403`. The Standard is Dave's document and is
  preserved as written (Dave, 2026-10-12 16:03 MST); the release notes
  identify the outdated status code (their "Changes that need action", item
  4).
- **Follow-up 5, smaller items found while documenting.** No conformance
  test checks that a deployment's own HITL transport judges eligibility.
  Over MCP, the door paths' uniform "cannot verify" is uniform in bytes but
  not in server work (governed evidence that is not a record, such as a query pin, and a
  client twin of governed evidence cost the server one more read than an
  address never filed); a timing
  difference visible to the door was not measured.
- **Follow-up 6, an erasure over the MCP-backed store does not complete.**
  Found while documenting; not a regression of this release. Under the
  declaration the security how-to requires (§4.10: `ccf.erasure-approval`
  and `ccf.erasure-record` under `ArtifactErase`), the door files the
  approval with its `ArtifactErase` capability, but the artifact server's
  only write tool, `put_artifact`, authorizes `artifact.write` and hands the
  store an `ArtifactWrite` capability, which the store refuses for that
  class ("wrong kind"). Measured by probe for an ordinary client filing with
  the upgraded door and server and with the previous ones (`633c4e53`, the
  same code as `2cd96aef`): the completion is refused at the approval's
  save, before any index entry is appended, so the address stays served. No
  test covers completion over MCP. An erasure over the MCP-backed store
  reaches approval and no further; complete erasures through an in-process
  store. Not built: Dave ordered no further implementation round. *Not
  under this configuration, which exposes no artifact server.*
- **Follow-ups 7, 8 and 9, a distinct entitlement refusal for a named
  employee on a named information wall** (Dave, 2026-10-12 22:44 MST: named
  follow-ons, not built; the delivered behavior is under "Refusals" above).
  7: a disclosure level that states only "not entitled to this restricted
  class" and nothing else of the internal record. 8: the population allowed
  to receive that refusal, declared per wall rather than as one insider flag.
  9: on-behalf-of identity, so the door judges the employee an agent acts
  for rather than the agent's calling credential. Each changes the SDK
  surface; 8 and 9 need a design first.
- **SEC-027**: the PyPI name reservation; Dave's upload.
- **SEC-029**: the release version stamp; no tag exists.
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
2. Reinstall the previous wheel,
   `ccf_sdk-1.0.2.dev1551+g2cd96aef8-py3-none-any.whl` (sha256
   `69a9a7a5d9b1e5ee735f4f6ded271c827403940911700f74667d2d91b5677c18`; in
   the delivery folder under `rollback/`, checked with its own `SHA256SUMS`
   first), into the same venv
   (`pip install --no-deps --force-reinstall <previous-wheel>`), or point
   `launch.sh` at the previous SDK tree. Rolling back re-opens what section
   4.0's packages A, B and C fixed.
3. Relaunch and run `verify.py`. Recorded replay artifacts in the instance
   root are content-addressed and are not rewritten by a rollback.

## 7. Owners

| responsibility | owner |
|---|---|
| Release approval, rulings, PyPI placeholder upload | Dave Castillo |
| Build, verification and this packet | Claude Code session for the ccf-sdk agent, under Dave's direction |

## 8. Handoff steps

Dave accepted the documentation close-out on 2026-10-12 at 16:03 MST: the
source and the wheel stay pinned to `01fc424d`, and `main` supplies the
corrected documentation (documentation only after `01fc424d`). No further
checking agents, implementation rounds or paid CI runs before the handoff.
No tag and no public upload.

What remains, in order:

1. **Deliver the sealed folder** `ccf-sdk-delivery-2026-10-13/` with its
   `MANIFEST.sha256`. They travel together; a copy of the folder without its
   manifest, or with any file changed, is not the delivery.
2. **Complete the documentation and the demonstration videos.**
3. **The bank verifies under its own service account**: section 3's
   checksum and install steps, then section 2's launch and `verify.py`,
   which ran under the developer account here.
