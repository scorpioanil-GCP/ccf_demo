<!--
Copyright (c) 2026 David Castillo. All rights reserved.
Use, copying, modification, and distribution of the covered material
are governed by the CCF SDK Interim Software and Patent License
in the repository-root LICENSE.md and any controlling signed agreement.
Rights under that interim license begin only upon its execution
and are limited to its stated scope and term.
-->
# CCF SDK 1.0.2 release notes

**Released 17 October 2026. Not yet delivered to the bank.** The build the bank runs is still the
October 13 delivery (`01fc424d`, version `1.0.2.dev1564+g01fc424d9`). Its notes are
[`RELEASE-NOTES.md`](RELEASE-NOTES.md), and its handoff record is [`BANK-PACKET.md`](BANK-PACKET.md).

| | |
|---|---|
| Release tag | `v1.0.2`, on commit `5f85b389` |
| Package | `ccf_sdk-1.0.2-py3-none-any.whl`, version `1.0.2` |
| SHA-256 | `1d18f600b121268aa58b6438507f682e7b877c78fedf3ea33b2e13e90be51a71` |
| Dependencies | Hash-pinned lock file, byte-identical to the October 13 delivery's |
| Security register | 27 of 30 closed. SEC-013, SEC-020 (across the SDK; parts rated HIGH) and SEC-027 are open and disclosed |
| Release decision | Tagged by an explicit override of the rule that held release tags until every critical, high and medium item was closed (`D-IMPL-392`) |
| Hosted CI | None for 1.0.2. Every result in these notes comes from local runs (section 1) |
| Decision records | `D-IMPL-383` to `D-IMPL-392` in `docs/DECISIONS.md` |

Each item below is marked **New** (not in the October 13 build) or **Already delivered** (in the
build the bank has). The examples, the bank configuration scripts and the documentation ship with the
repository; the installable package contains the SDK library and runtime only.

**Terms used.** The *MCP door* is the network endpoint, using the Model Context Protocol, through which
an AI agent or client asks a product a question; it is the only door the bank's tested configuration
opens. A *harness* is an agent framework: the Claude Agent SDK, Google ADK or LangGraph. A *content
address* is a fingerprint of an answer's exact content.

## At a glance

- **Vulnerability remedies.** Three security findings closed since October 13: SEC-001's remaining
  gap (approvals now bind to the records store that paused the work), SEC-030 (unexpected errors on the
  MCP product request no longer leak their text) and SEC-029 (a real version number). SEC-020 Parts 1
  to 3 are closed on the bank's tested product; SEC-020 stays open across the SDK.
- **Decision replay persistence.** When a deployment declares an evidence folder, as the bank launcher
  does, replay evidence survives a restart, and three operator commands answer the bank's four
  questions from it. Nothing changed specifically for LLM integration; what already works is described
  below.
- **Context Skills.** A new worked example, sk-01, shows an agent being granted a governed skill.
  Every decision the agent composes now names the agent and carries a fingerprint of the skills it
  held.
- **Bug remedies.** Five defects present in the delivered build are fixed, including the evidence
  store losing index entries when two writers raced (register item 18).
- **Documentation corrections.** Examples now require complete connection strings, and database
  addresses show a `<port>` placeholder. Four known corrections are still pending.
- **Reference manual updates.** The security guide, the controls register, the artifact-store and
  replay pages, the HTTP API description and the developer change log are updated.
- **New videos.** Four new videos, one of them on Context Skills, join the eleven made earlier, for
  fifteen in all (section 7).
- **Bank-ready form.** There is no form to sign. A bank-ready package for 1.0.2 has not been
  assembled yet; what it needs is listed in section 8.

## 1. Vulnerability remedies

### New since October 13

**SEC-001's remaining gap: an approval counts only in the store that paused the work (CRITICAL).**
An approval did not record which records store it belonged to. Two independent stores behind one
shared approval queue that paused the same workflow at the same clock readings looked identical, so
one human approval could release the work in both (measured: one approval, two passages). Now every
records store has a permanent identity that is stamped on every record:

- An approval counts only in the store that paused the run, and a record from another store is
  refused by name.
- One approval request is filed per paused run, and an approval sent straight to the approval queue
  counts only while the request for that exact pause is waiting.
- A store or queue labeled single-process holds a lock, so a second process is refused by name.
- Runs paused before the upgrade are refused until they are paused again, and then need a fresh
  approval.

This does not reach the bank's tested configuration: its door builds no approval queue (measured).
The October 13 packet and notes describe that configuration as having "one approval queue per
instance"; that wording is wrong and is listed for correction in section 5. The change does affect
teams that supply their own records store or approval queue; see "Changes that need action" at the
end. *Limits:* the SDK checks the identity's format, while uniqueness and persistence are the store's
responsibility. A copied store must refuse to open, and re-issuing its identity strands every run it
has in flight. The lock has the same file-locking limits as SEC-013, and because the SDK ships no
file-backed approval store, the cross-process lock was proved only on a test stand-in. Three rare
failure or race cases can stall an approval until an operator acts or the run asks again; none lets an
approval pass wrongly. (`D-IMPL-391`.)

**SEC-020 Parts 1 to 3: "does this facility exist?" closed on the bank's product.** The bank asked for
a detailed breakdown of SEC-020; it is in `SEC-020-DECOMPOSITION.md` beside this file, in five parts,
and has not yet been sent. Parts 1 to 3 cover the existence leak on the bank's tested product (cp-06C,
collateral and set-off coverage): an invented facility ID got a technical error about three times
faster than a real facility outside the caller's scope, which got a formal refusal. Both now get the
same recorded, replayable "subject unavailable" answer, within the timing threshold agreed before the
fix. The closure rests on a provisional ruling (Part 4): with one shared credential, the borrower scope
is a value the caller supplies, not a permission, and the tenant is the permission boundary. The bank
verification script gains checks so the bank can test this itself; its optional timing check asks
about 400 questions, and each leaves a permanent record in the evidence folder. The fix is in the
cp-06C example and the bank verification kit, not in the SDK library. *Limits:* a small timing
difference remains (an existing facility returns one database row, an unknown one returns none), a
caller who names the right borrower scope can still learn that a facility exists, and SEC-020 stays
open across the SDK and for every other product. (`D-IMPL-387`.)

**SEC-030: unexpected errors no longer leak their text through the MCP door.** If a product hit an
unexpected error while fetching data, the MCP door returned the error's own message. This was found
through a deliberately broken test build, where the message named a facility ID and the borrower scope;
which real failures reach this path on the delivered build was not investigated. Now the caller sees
only an opaque reference (`ccf-runtime-failure:<id>`), and the server log keeps the error types under
the same reference. This is the door the bank's configuration uses. *Limits:* it covers the product
request and its answer on the MCP door; entitlement failures, the HTTP API door, the standing product
resource, the agent tools and the approval resources are outside it. (`D-IMPL-388`.)

**SEC-029: a real version number.** The delivered build reports a development version, and that is
what its decision records name. Version 1.0.2 is a tagged release, and its package reports `1.0.2`.
The release check was run on the tag in a clean environment and passed (`v1.0.2 == 1.0.2`).
(`D-IMPL-392`.)

**Hardening of the new replay evidence before release.** Reviewers of the new replay-evidence feature
(section 2) found that one tenant could look up another tenant's evidence entry and that a symbolic
link could redirect the evidence folder. Both were fixed before the feature reached the release; the
delivered build never contained this code. (`D-IMPL-383`.)

### Still open and disclosed

- **SEC-013.** Limits of the SQLite single-writer lock: a hard-link backup blocks every startup, and a
  live database moved without a declared lock folder can admit a second writer and lose committed
  data. For the bank's configuration these are operating rules, and the SDK's standard product path
  creates the lock folder.
- **SEC-020 across the SDK (parts rated HIGH).** A caller may be able to tell a withheld subject from
  one that does not exist. On cp-06C, Parts 1 to 3 are closed, but the small timing difference and the
  caller-chosen borrower scope remain; on every other product the item is fully open.
- **SEC-027.** The `ccf-sdk` name is not reserved on the public Python package index. It has no
  effect on how the software runs.

The register beside this file (`OPEN-SECURITY-ITEMS.md`, as updated after the tag) also lists open
follow-up items that 1.0.2 does not change, each with whether it reaches the bank's configuration. The
copy inside the tagged commit reads 26 of 30 closed, because SEC-029 closed with the tag itself and was
recorded just after it.

### Already delivered

Between v1.0.1 and the October 13 build, 18 SEC rows closed, and the bank already has them: signed
human approvals and approver eligibility (SEC-005, SEC-006); refusal of blank or malformed identifiers
(SEC-007); the fabric's own clock in place of the caller's (SEC-008, SEC-010, SEC-011); minimum governed
erasure (SEC-009); per-credential product limits, required policy parameters, authorized classification
sources and same-subject composites (SEC-017, SEC-019, SEC-023, SEC-025); agent-to-agent message bounds
and replay defense (SEC-021, SEC-022); and operational hygiene and supply-chain controls (SEC-014,
SEC-015, SEC-024, SEC-026, SEC-028). SEC-009's erasure claim is still not independently verified, and an
erasure through the MCP-backed artifact store reaches approval and never completes (register items 6 and
9, unchanged in 1.0.2).

### How the fixes were checked

Each code fix was written test-first: tests that reproduce the defect failed before the fix and pass
after it, and some new tests are controls that passed before as well. Selected protecting lines were
then deliberately broken to confirm that a test catches each break: 35 such breaks for SEC-001, three
of them in the test stand-in rather than the SDK. Some protecting code is still not caught by any test;
the decision log records these gaps (for example `D-IMPL-389`, advisory A1). The SEC-001 design brief
was checked by Grok before any code was written, and two read-only review rounds of the built code by
separate AI agents found three blocking defects, all fixed before release. The project's usual
multi-vendor review panel was waived for this round.

No hosted test run was made for 1.0.2: every merge since the October 13 build, and the tagged commit,
carried a skip marker, so the hosted suite that passed on the October 13 build was not repeated. The
results here come from local runs. The test suites pass on the released code, apart from one
version-number test that needs a release tag in the local checkout; tests that read the live
demonstration estate were skipped in that run, and the bank-door tests passed against the estate,
read-only. The installed 1.0.2 package passed 20 of 20 checks in a clean environment, including the fix
tests run against the installed copy. The hosted release-check job did not start for the same reason;
the same check passed locally, and that result was accepted.

## 2. Decision replay persistence, and compatibility for LLM integration

### New since October 13

In the delivered build, the bank launcher kept each question's graph and the replay store in a
temporary folder, so a normal stop deleted them, and nothing linked a decision to the graph it read.
Decisions answered on the October 13 build therefore cannot be replayed after the upgrade; replayable
evidence starts with the first question answered on 1.0.2. In 1.0.2:

- **Evidence survives a restart** when the deployment declares an evidence folder (`evidence_root`; the
  bank launcher always does). Each question's graph and the decision records are kept there, with an
  index from each decision to its graph. After a restart, an earlier decision can be replayed with the
  data sources switched off. Missing evidence is reported as unavailable, and altered evidence as a
  divergence; neither is reported as a successful replay. Without a declared folder, evidence is still
  deleted with the temporary folder.
- **A separate, private evidence folder.** The bank launcher creates a folder named `evidence` in the
  instance root and passes it to the service as `CCF_REPLAY_EVIDENCE_ROOT`; the bank sets nothing new.
  The launcher and the service each refuse to start unless the folder is private to the service
  account. The temporary working folder stays temporary.
- **The bank's four questions, answered from retained evidence.** Three operator commands,
  `decisions`, `why` and `replay`, answer "show decisions involving this company last Tuesday", "why
  was this request refused?", "which policies and data supported this answer?" and "replay this
  decision and verify that it reproduces". The explanation is copied word for word from the stored
  record; no model writes it.
- **Replay without database credentials.** An auditor can replay or explain past decisions without
  the data-source settings. An opening made this way cannot answer new questions.
- **A declared data-source outage is a recorded refusal.** When a source cannot be reached and the
  product has declared that failure as an outage (cp-06C declares its PostgreSQL and Fluree connection
  errors), the caller gets a governed "source unavailable" refusal instead of the database driver's
  error, and the refusal can be listed, explained and replayed like any other decision. A failure the
  product has not declared is still not a governed answer, and on the MCP door it crosses only as an
  opaque reference (SEC-030).
- **The record names the agent and carries a fingerprint of its skills** (section 3), and **decisions
  built from other products replay from their record alone**.
- **Fluree 4.2.4.** The SDK's automated tests and the 1.0.2 bank-door checks ran against Fluree 4.2.4
  (previously 4.1.4); the records show no 1.0.2 test against 4.1.4. The one known difference between
  the versions is a query the SDK never sends.

*Limits:* the decision records and graphs are not forced to disk before they are indexed, so after a
power loss a decision can be reported unavailable, by name. Nothing is deleted automatically. Retained
evidence uses disk and must be backed up with the instance by copying it, not with a backup tool that
makes hard links: each question's graph is a SQLite file, and while a hard-linked copy exists the SDK
refuses to open it, so that decision cannot be replayed (SEC-013). Retention rules are future work. One
unreadable index file makes the decision listing fail. `decisions --involving` takes an identifier (a
facility ID or LEI), not a company name. Replaying a product built from other products still needs the
producers' setting names, though replay never contacts them. Apart from composite replay, which the
published "Reconstruct a governed determination" page now covers, these features are not yet in the
published manual; they are documented in the cp-06C and sk-01 READMEs and the developer change log.
(`D-IMPL-383`, `D-IMPL-384`, `D-IMPL-385`, `D-IMPL-389`.)

**The bank's SQLite question.** The bank asked whether there is an alternative to SQLite and whether
several applications can share one store. 1.0.2 answers the replay-records part: records and each
question's graph are kept in a declared folder that survives a restart, and backing it up is the
operator's job. 1.0.2 does not replace SQLite in the bank's configuration, and several applications
sharing one store has not been built or ruled on.

### Compatibility for LLM integration

Nothing in 1.0.2 changed specifically for LLM integration: the decision-record format, the replay
engine and the three harness adapters are the same as in the October 13 build. What works today, and is
already delivered:

- Adapters connect a governed agent to the Claude Agent SDK, Google ADK and LangGraph. Before
  delivery they gained five security fixes: a read-only agent cannot trigger actions, the Claude child
  process does not inherit the service environment, only skills an agent may expose appear as tools,
  tool arguments are checked before anything runs, and the system prompt is kept off the process
  command line.
- The hw1 example reaches one governed product through all three frameworks, and every framework gets
  the same content address as a client that uses no framework. Its Claude Agent SDK leg uses a local
  model stand-in by default and a real Claude model when run with `--live`.
- Decision records have fields for the model version, the agent framework and the prompt used.
- An AI agent reached through a harness adapter or the product client receives only a reference to a
  decision record, never the record itself. Over the HTTP and MCP doors, reading a record back is
  refused by default and allowed only for product classes a deployment explicitly allow-lists. 1.0.2's
  new replay and explanation commands are operator and auditor tools.

*Not available:* an LLM front end that asks the retained evidence questions in plain language is not
built, the bank's tested configuration runs no AI model, and no agent-facing endpoint exposes the new
commands.

## 3. Context Skills

In this SDK, a **Context Skill** is a governed permission for an agent to ask a Context Product. It
is not code, and it is not a tool the AI model sees. A deployment declares it in its configuration
file in two parts: a skill (what may be asked, and of which product) and a grant (which agent holds
it). At startup the deployment's policy regime decides whether each grant is allowed. Each grant
request and its outcome go to an audit log that is held in memory and ends with the process, and three
configuration mistakes are refused by name before any grant is requested, so they leave no grant
record. An **Agent Skill** is different: it is whatever instructions a developer writes inside their
own agent framework. The fabric does not parse, grant or record an Agent Skill's text, and no decision
record contains it. (The SDK can import an Agent Skill file as a governed procedure skill with `ccf skill
import`, but the supported configuration path cannot declare one.)

### New since October 13

- **A worked example, sk-01.** A named agent (`collateral-analyst`) is granted one Context Skill
  (`collateral-ask`: ask the collateral product about one facility) under a policy. The grant is
  audited, and every decision records which agent decided and a fingerprint of the skills it held. A
  second configuration asks for more than the policy allows, and the product refuses to start. It was
  built because the bank said there was no skills example. The bank's tested configuration declares no
  skills. A video, `SK01_Context_Skills.mp4`, covers the example (section 7).
- **Decisions name the agent and carry a fingerprint of its skills.** In the delivered build, a
  decision assembled by an agent from other products recorded "no agent" and "no grants". Now it
  records the agent (by fingerprint, version and type) and a fingerprint of the skills it held. The
  fingerprint is not a list of skill names; turning it back into names needs grant records that are
  today kept only in memory.
- **Those decisions can be replayed** from their record and the retained copy of the other product's
  answer, without asking that product again. This is proven on SDK test fixtures, not yet on sk-01's own
  decisions, and replay still needs the other product's setting names (section 2).

### Already delivered

Skills are declared in configuration and granted at startup through the same policy check, approval
rule and audit trail as a manual grant. Under an agent framework, only skills of a model-callable type
appear as tools, and the grant ledger keeps its own copy of every grant.

### Not yet available

These are stated openly in the example: granting or revoking a skill while a product runs; a granted
skill appearing as a tool the AI model can call; an agent asking products on its own, outside a
product; and listing the skills behind a decision from the record alone, or keeping the grant audit
trail after the process stops. The published how-to "Grant and revoke a skill" still describes an
older, archived example and has not been updated to match sk-01.

## 4. Bug remedies

### Present in the delivered build, fixed in 1.0.2

- **A database outage was not a governed answer.** On the bank's product the database driver's own
  error reached the caller, and a product that declared the error could only report it as "not
  available to this principal", which reads like a missing permission. A product that declares its
  connection errors now gets its own "source unavailable" refusal, and cp-06C does (CP06C-F-06).
- **Replaying a past decision required database credentials.** It no longer does (CP06C-F-07).
- **Decision records did not name the agent or carry its skill fingerprint** (`D-IMPL-385`).
- **Decisions built from other products could not be replayed from their record alone**
  (`D-IMPL-389`).
- **The file-based evidence store could lose index entries when two writers saved at once.** In the
  measured runs every evidence file was written, but an entry linking a name to its file could go
  missing, and two writers in one process saving the same file could make one save fail. Index updates
  now hold an exclusive lock, and each writer stages its files under its own name. The bank's door uses
  this store for its replay evidence; whether it ever writes from two places at once was not measured.
  *Limits:* a writer waits for the lock with no timeout, and the lock is unsuitable for a network file
  system without reliable file locking (`D-IMPL-390`, register item 18).

### Examples and test suite

The example instructions now require a complete database connection string (host, port, database,
user and password); a short form silently borrowed whatever login the user's shell held. The example
test suite (`tests/examples`) no longer prints database passwords in failure reports. The same leak very
likely exists in other test folders when a database connection fails; it was not measured or fixed
there. Both changes affect the repository, not the installed package.

### Fixed within the release work

Some defects were introduced and fixed inside the 1.0.2 work and were never in the delivered build: an
approval tool racing another approval could pick up a different paused run's request; the HTTP approval
receipt reported "pending" for the wrong paused run; and review fixes to the new replay evidence before
it reached the release.

### Already delivered

The October 13 notes list the final pre-delivery fixes: the HTTP product route no longer reveals
whether a product class exists; an ineligible approver can no longer wedge an approval step while the
step's own request is the one the queue selects (two other ways to wedge one remain open, follow-ups 1
and 2, and the bank's configuration exposes no approval surface); and SEC-020's closing test gate passes
its 21 previously failing cases.

## 5. Documentation corrections

### New since October 13

- Database addresses for Fluree, PostgreSQL and MongoDB show a `<port>` placeholder instead of a fixed
  port number.
- The shared example instructions and five older example READMEs require complete connection strings.
- The sk-01 README says in plain words what is not yet available and defines Context Skill and Agent
  Skill.

### Still pending

- The October 13 packet and notes describe the tested configuration as "one engine, one store, and one
  approval queue per instance". Measured, the bank's door builds no workflow engine or approval queue.
  To be corrected in the next bank package.
- The bank packet's sentence that an unauthorized question looks exactly like a question about a
  missing record holds at the tenant boundary but not for a caller-supplied borrower scope. To be
  qualified in the next bank package.
- A list of 27 source docstrings, several of them shown in the reference manual, was made on October
  12; they describe behavior from before that day's security batch. None was corrected for the
  delivery, and the list has not been re-checked against 1.0.2.
- The Context Product Specification Standard v0.3 still says an unentitled caller gets HTTP 403. The
  HTTP product route answers 404 "subject unavailable"; the October 13 notes flag the row.

## 6. Reference manual updates

### New since October 13

- **Security and deployment guide, section 4.13:** how approvals bind to the store that paused the
  work, what a team's own store and approval queue must provide, and the remaining limits.
- **Controls register:** 13 new rows and 3 rewritten, each naming the test that fails if the control is
  removed.
- **Artifact store reference:** the file store's name index is now safe for several writers on one host,
  though the lock is not reliable on network file systems without proper file locking. Whether several
  applications may share one store as a supported setup has not been ruled on (section 2).
- **Reconstructing a decision:** decisions built from other products replay from the stored record,
  with the remaining limit stated.
- **HTTP API description (`openapi.json`):** workflow status records can carry the identity of the
  store that wrote them, and the approval receipt's "pending" field refers to the specific paused run
  named. No endpoints were added or removed.
- **Developer change log (`docs/SURFACE-CHANGES.md`):** 47 new entries with migration advice.

### Not yet in the published manual

Durable replay evidence, the `decisions`, `why` and `replay` commands, the "source unavailable"
refusal and agent identity in decision records are documented only in the developer change log and in
example READMEs (cp-06C for the evidence, the commands and the refusal; sk-01 for agent identity).

## 7. New videos on using the SDK

The videos are kept in the project's Google Drive folder, not in the repository, and are shared
separately; a viewer needs access to that folder.

### New since October 13

- `CCF_Engineering_Decision_Context.mp4`
- `CCF_LinkedIn_Governed_Context.mp4`
- `Cognitive Context Fabric Intro.mp4`
- `SK01_Context_Skills.mp4`, on the sk-01 Context Skills example (section 3)

### Already available

- `CCF_SDK_Video_1_DaveC.mp4` to `CCF_SDK_Video_10_DaveC.mp4` (ten videos)
- `CCF_Technical_Overview.mp4`

The October 13 notes state that recordings of that build remain valid; this was not re-checked against
1.0.2. A recording made on 1.0.2 would show a few differences: a newer Fluree image and the `<port>`
placeholder in one tutorial's setup, and the bank launcher creating an evidence folder and the checker
printing the new SEC-020 checks. No tutorial has been re-run on the 1.0.2 tag.

## 8. Bank-ready form

**There is no form to sign.** An acceptance form was drafted on October 12 and removed before
handover, and the license states that no signature or separate acceptance form is needed. Source and
document headers that name an interim license, or say rights begin only on execution, are superseded by
section 1 of `LICENSE.md`.

**What the bank-ready package is.** The October 13 delivery is a sealed folder: the installable
package with its checksums, the hash-pinned dependency list, scripts to launch, check and stop one
tested configuration, the previous build for rollback, test transcripts, the bank packet, the release
notes, the license and a dated delivery notice, all covered by a checksum manifest. The bank's
remaining step is to repeat the checks under its own service account.

**For 1.0.2, a bank-ready package has not been assembled.** It would need:

- an updated bank packet and these notes in place of the October 13 ones, with the corrections listed
  in section 5;
- the updated launch and check scripts (the private evidence folder and the SEC-020 checks), run against
  a clean checkout of the `v1.0.2` tag, because the launcher runs the service from the SDK source tree
  rather than from the installed package;
- a check that replays a decision after a restart, which the verification script does not yet do;
- a hosted CI run on the release commit, which 1.0.2 has not had;
- the video folder (section 7) shared with the bank;
- a written grant or amendment naming 1.0.2. The license's Schedule A names only the October 13 build,
  and its section 1 says later source commits are included only when the licensor names them in
  writing.

## Changes that need action

These apply to teams that supply their own components. The bank's tested configuration needs none of
them: its door builds no approval queue and declares no skills.

- **Your own records store** must carry a permanent identity (64 lowercase hexadecimal characters),
  persisted with its records, and a copied store must refuse to open. A store labeled single-process
  must hold a lock from open to close.
- **Your own approval queue** must file one request per paused run, offer the new `retire` step (the
  engine refuses a queue without it), judge each approval against the paused run it names, and, if
  labeled single-process, hold a lock.
- **Durable stores with runs paused before the upgrade** must re-pause each run with
  `rebind_legacy_suspension` and collect a fresh approval.
- **Your own refusal recorder**, if composed over an agent-conditioned child resolver, must accept the
  new `agent_conditioning` keyword (or `**kwargs`); otherwise the product refuses it at construction.

The changes, with migration advice, are in `docs/SURFACE-CHANGES.md` (fragments `391-01` and
`385-01`), and the conformance tests a team runs against its own components are in
`tests/conformance/test_gate_closure_and_conditional_write.py`.
