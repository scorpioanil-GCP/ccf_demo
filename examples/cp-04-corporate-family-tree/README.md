# cp-04 — Corporate Family Tree

**Rung 04 of the vault's Context Product ladder, and the first of Tier 2.** One
corporate family walked from an anchor LEI, where every member carries its FIBO
class chain, members that resolve to no reference row stay in the tree, and a
circular ownership structure is reported with its roster and the edge that
closes it.

Specification: [`spec/CP-SPEC-004_Corporate_Family_Tree.md`](spec/CP-SPEC-004_Corporate_Family_Tree.md).

> **This is the first rung that opens more than one store.** Edges, ontology,
> labels and LEIs come from a Fluree ledger; reference attributes come from a
> PostgreSQL table. Both are read on every ask, and the split is visible in the
> answer: **2 of the 22 members under the demonstration anchor carry a legal
> entity record and 20 do not.** A build that quietly served only the two that
> resolve would return a smaller, tidier, wrong family.

## What this demonstrates

**Two systems of record in one answer, and the join is the product.** Rungs 00
through 03 each read one store. This one reads two per ask — a graph leg for who
owns whom and what each thing is, and an attribute leg for what the reference
data says about the members that have a record. Neither store holds the answer;
the assembly does.

**A walk instead of a lookup, and the depth is part of the answer's identity.**
`max_depth` is the parameter this rung exists for. Four properties ride on it
and each is gated separately: absent, it takes the **declared default of 3**,
read from `ccf_config.yaml`'s `request_contract.defaults` by the SDK's own
request resolution rather than invented at serve time; a depth **this estate
cannot exhibit is served** — asked 8, the walk reaches 3, and the payload's
`traversal` finding carries the depth requested beside the depth reached; a
depth above the **backend's technical capability** (100 here, read off the
substrate in force, authority `technical`) is **refused by name** as
`constraint-refusal` and answered at no narrower depth; and **two depths are
two content addresses**, because they are two answers to two different
questions. A silent clamp is the failure this rung is most exposed to — the
request says 101, the walk does 100, the payload looks fine and the seal greens.

**Ontology load-bearing in three places, not one.** The class chain is *served*,
so a consuming agent knows what each member is without a second lookup. The
perspective *conditions on FIBO class* rather than on a hand-written role map.
And a declared gate *validates* the assembly, so an untyped node or an
off-vocabulary predicate cannot enter quietly. A fourth role — types constraining
the walk — was struck from this rung on 2026-08-31, on two grounds measured
then: this estate cannot exhibit the stop, and the SDK's Traversal family typed
the walk on edges only. Phase 24.5 added a node-class admission filter
(`admitted_entity_classes`, `24.5-L-05`); this rung does not bind it, the estate
ground stands, and role 1 stays struck. **Nothing here claims a
type-constrained walk.**

**A circular ownership structure, reported rather than survived.** The
demonstration family contains a three-member ownership cycle. It is served as a
finding carrying its roster *and* the edge that closes it, so a reader sees
which companies form the circle instead of an unexplained anomaly — and the walk
terminates rather than looping.

**A door a remote agent can reach.** The same assembler answers in-process
through `ProductClient` and over MCP through a product tool. One assembler, two
callers, one seal.

## Run it

**1 · Create the virtual environment.** This repository has no `python` on
`PATH`; the `Makefile` uses `.venv/bin/python`, and nothing creates it for you.

```
make venv
```

**2 · Export the four connection variables.** `backends.yaml` holds each
variable's *name* and its remedy string and nothing else — no host, no port, no
path, no credential ever enters the tree. **All four are required and none has a
default**, which was measured rather than assumed: unset the schema and the run
refuses by name.

```
export CCF_CP_04_FLUREE_URL='http://…:8090'
export CCF_CP_04_FLUREE_LEDGER='fibo-v2'
export CCF_CP_04_POSTGRES_DSN='host=… port=5432 dbname=… user=… password=…'
export CCF_CP_04_POSTGRES_SCHEMA='ccf_v2'
```

**Both roles must be read-only.** Nothing this example runs writes to either
store it reads, and a role that *could* write would make that a promise rather
than a guarantee. On the PostgreSQL side the role needs `SELECT` on the
`legal_entity` table and nothing else — no `INSERT`, no `UPDATE`, no `DELETE`,
no `CREATE`. On the Fluree side the example issues only `/v1/fluree/query`; it
never creates, updates or deletes a ledger.

Both libpq spellings work for the DSN and neither is preferred — the keyword
string above, or a `postgresql://user:pass@host:5432/dbname` URI. libpq also
reads `PGHOST` / `PGPORT` / `PGUSER` / `PGPASSWORD` from the environment on its
own, so the variable's contents can be as short as `dbname=<database>`.

**The ledger name and the schema name are variables rather than defaults on
purpose.** Each selects *which* namespace of a store the product reads, and a
defaulted one is a namespace nobody chose. Every Fluree query this example
issues also carries an explicit `FROM <ledger>`; the server answers HTTP 500
without one.

**3 · Run the demonstration question.**

```
make -s example-cp-04
```

`-s` suppresses make's echo of the recipe. That echo is the only difference
between this target's output and the transcript published on the documentation
page.

The `assembled by` line names the assembler implementation that produced this run (`cp-04.corporate-family-tree@1.0.2`) — transcript evidence, read off the program's own stdout.

Decision Replay carries the same identity: the assembler id and version land under Perspective Conditioning for fulfilled **and** refused decisions, which `tests/examples/test_cp_04_seams.py::test_replay_carries_the_assembler_identity_for_fulfilled_and_refused` proves. The transcript line is evidence beside the record, not the only carrier.

**4 · Without make**, spelling the interpreter explicitly:

```
.venv/bin/python examples/cp-04-corporate-family-tree/run.py
```

**5 · Variations worth trying.** Every request parameter is optional — omitted,
the run asks the question declared in `artifacts/question.yaml`.

| Command | What changes |
|---|---|
| `make -s example-cp-04 MAX_DEPTH=1` | one hop instead of the declared three. **20 members instead of 22**, the seal moves from `fad6e55d…` to `7163d0a1…`, and **`D_c` moves from `0.0909` to `0.1`** because `S` is taken over what was served — `18/20` here against `20/22` at the default. Two depths are two answers |
| `make -s example-cp-04 MAX_DEPTH=2` | the same **22** members as the default — and still a different seal, `763faf5a…`. The only payload difference is the depth echoed into `max_depth_applied` and the `traversal` finding, so this pair shows that the depth asked travels into the answer's identity; it is `MAX_DEPTH=1` that shows the walk itself moving |
| `make -s example-cp-04 MAX_DEPTH=8` | **served, not refused.** The same 22 members, with `requested_depth: 8` beside `depth_reached: 3` in the `traversal` finding, sealing to `2607d522…`. A depth this estate cannot exhibit is an answer with the gap visible; the estate's own deepest tree (6, measured in `CP-SPEC-004` §B.4.1) is history, not a bound |
| `make -s example-cp-04 ROLE=kyc-analyst` | the other declared perspective. The same 22 members, **0 detailed instead of 22**, sealing to `79733117…`. The two roles sit on opposite sides of one FIBO class axis, which is why this flag can fail rather than decorate |
| `make -s example-cp-04 ROLE=credit-officer` | the default perspective, named explicitly. Identical to the default run, `fad6e55d…` |
| `make -s example-cp-04 LEI=549300F16C4PEFXU0S92` | a second anchor **inside the same family**. **Served** as a one-member family (`1 node(s) visited, 0 edge(s) walked`) carrying an `idle_jurisdictions` finding that names `US-DE`, the declared jurisdiction no member of *this* family serves; seals to `9865568d…`. See below |

**6 · Three variations exit non-zero, and that is correct.** A refusal is not a
crash, but it is also not a success, so `make` reports `Error 1`. The program's
own exit code is `1`; `make`'s is `2`, which is make's status for a failed
recipe rather than anything this program chose. Each refusal is one line on
**stderr** — stdout is empty — and the three blocks below quote that line byte
for byte from a 2026-09-05 capture. The line prints the refusal's *reason* and
the parameter it names; the *kind* travels on the envelope the program branched
on, and each kind is named beneath its block.

```
make -s example-cp-04 MAX_DEPTH=101
```

> `refused: bound-exceeded — max_depth`

That is the `constraint-refusal` kind. The backend's technical capability is
100 for this substrate (`fluree/fibo-v2`); the bound rides on the envelope with
authority `technical`, and the request is answered at no narrower depth. The
number is authored nowhere in this example — `ccf_config.yaml` binds `max_depth`
to the SDK's `traversal-depth` capability token under `capability_bindings`, and
the value is read off the substrate at resolution time.

```
make -s example-cp-04 AS_OF=2026-03-31
```

> `refused: not-supported-at-tier — as_of`

That line is the SDK's verdict returned as **data**: the tier step of
`refuse_request` (`src/ccf/products/request.py::_refuse_tier`, `24.5-L-12`/`L-13`)
answers `not-supported-at-tier` before the product's own code runs, and the
program prints the reason and the parameter it names. The declaration's own
explanation of *why* this tier refuses a past date lives in `ccf_config.yaml`
under `unsupported_arguments`.

```
make -s example-cp-04 LEI=000000000000000000ZZ
```

> `refused: subject-unavailable`

An anchor the ledger does not carry is a governed determination, not an
exception: the assembler returns a `subject-unavailable` refusal and the program
prints it. A family with no members would read as "this company has no
subsidiaries", which is a claim about the world rather than about the request,
so an empty payload is not what comes back either. At the doors, the disclosed
shell for a subject that does not exist and for a subject the caller is not
entitled to is the same shell at the same disclosure level — the SDK's
disclosure step normalizes the two, and the internal record keeps the truth.

**Three conditions are not refusals at all, and the runner says so with a
different exit code.** A node the walk admitted that the minting step did not
cover, a served member set carrying no jurisdiction against a declared
requirement, and a served jurisdiction outside the closed vocabulary in
`artifacts/source-vocabulary.yaml` are contradictions among the deployment's own
inputs — the fabric cannot reach a valid answer. Each is an invariant failure:
at the command line it prints `CCF runtime failure: …` and exits **2**, not 1,
so a broken deployment never reads as a governed refusal; over the MCP door it
arrives as an opaque tool error under a fresh id, never as a refusal shell.

**The closed jurisdiction vocabulary is asymmetric on purpose, since this
phase.** A family serving a jurisdiction the document does not declare still
fails, as the third condition above. A document declaring a jurisdiction no
family member serves is no longer a refusal: the family is served and the row
that never fired is reported as an `idle_jurisdictions` finding — which is what
anchoring on `549300F16C4PEFXU0S92` shows for `US-DE`. The demonstration family
exhibits exactly `NL` and `US-DE`, so under the default anchor both declared
rows fire and neither is idle, which is what makes each of them sabotageable.
Swapping the anchor to a family with a wider jurisdiction footprint is therefore
an **artifact edit as well as a parameter**, and the failure names the values
the document does not declare.

A fourth refusal is not one command away, because the committed estate cannot
exhibit it: an LEI carried by **more than one node** is refused as
`AnchorAmbiguityRefusal` (`CFT-G18`, `D-IMPL-245` (4)) — never a coin flip on the
store's row order, never a 404, never a served family with a finding.
`tests/examples/test_cp_04_anchor.py` perturbs a ledger to show it.

## The story

A credit officer asks for one company's corporate family. What comes back is not
a list of subsidiaries.

**Twenty-two members, and only two of them have a reference record.** The anchor
and one Dutch subsidiary resolve in the attribute store; the other twenty resolve
to no row at all and are served with `attributes: null`. They are **still in the
tree**, and that is the whole point of reading two stores rather than one: a
family assembled from the reference table alone would have returned two members
and looked complete.

**A three-member ownership circle, named.** Cycle 1 —
`CycCalderIndustrialNv`, `CycThornburyCapitalLtd`, `CycMeridianHoldingsSa` — is
served as a finding with its roster and its closing edge,
`CycMeridianHoldingsSa -> CycCalderIndustrialNv`. The walk visits each member
once and terminates. Across the whole estate there are exactly two such circles
and **exactly one external edge enters either of them** — this anchor's edge into
cycle 1 — which is why the demonstration anchor is the one that can show it at
all.

**The same company entered twice, one hop away.** `SuperMicroComputerBV`
(LEI `549300F16C4PEFXU0S92`) and `SubSuperMicroComputerBV` (no LEI) are the same
Dutch entity recorded under two identities. The product surfaces the pair as a
`duplicate_entity_pair` finding rather than serving them as two distinct
subsidiaries and letting an exposure calculation double-count.

**Twenty members with no jurisdiction.** The third finding,
`unresolved_jurisdiction`, is the twenty members that carry no reference row and
therefore no legal jurisdiction. It is served as a finding rather than as a
silence, because a family whose jurisdictional footprint is *unknown* for twenty
of twenty-two members is a different object from one whose footprint is
`['NL', 'US-DE']`.

**And a fourth finding about the walk itself.** The `traversal` row carries the
depth requested (`3`), the depth reached (`3`) and what the walk cost —
`22` nodes visited, `25` edges walked. All four are structural counts of a walk
that already ran; nothing in the payload reads a clock, so two runs of one
question seal identically. This is the row that makes a depth the estate cannot
exhibit an *answer*: asked `8`, it reads `requested_depth: 8`, `depth_reached:
3`, and the gap is visible rather than clamped away.

**Ontology, in three load-bearing places.** *Served* — every member carries its
FIBO class chain, so the answer explains its own vocabulary. *Projecting* — the
perspective conditions on FIBO class, which is why `credit-officer` details 22
members and `kyc-analyst` details 0 against the same 22-member family, and why
the two seal differently. *Validating* — declared gates refuse an untyped node
and refuse a seventh predicate, so nothing off-vocabulary enters quietly. A
fourth role, types constraining the walk, is **struck from this rung** and is not
claimed anywhere in this example.

**Context debt reads `0.0909` → `ok` at the declared default depth, and the
twenty are not what drives it.** The signal is advisory at every rung of this
ladder. The figure decomposes as `F=1  C=1  S=0.9090…`, and the movement is on
the semantic-consistency axis, not on completeness — the twenty members with no
reference row are reported as a finding, not as missing data. Two twenties appear
in this run and they are different populations; the specification says so on a
gated line.

**And the figure is not a constant — it is a function of the question.** `S` is
the fraction of the members THIS PAYLOAD SERVED whose identity no finding
disputes, so a shallower ask moves it: `MAX_DEPTH=1` serves 20 and reads
`S = 18/20 = 0.9`, `D_c = 0.1`. The depth qualifier above is therefore
load-bearing rather than pedantic. Both figures are pinned in
`artifacts/expected.yaml::debt_by_depth` and held by gate `CFT-G05`, which was
watched going red under a restored source-read denominator and under a corrupted
pin.

**The product reproduces byte-identical against a quiescent ledger for that run.**
That sentence is the whole of the claim and no stronger one appears here. The
qualifier is load-bearing and it was measured: the ledger's transaction counter
moved 4,560 → 5,112 between two sittings six days apart, and 5,112 → 5,296 by the
2026-09-03 re-capture, which reproduced the transcript byte for byte with the one
added `assembled by` line. The 2026-09-05 re-capture read the head at 5,296
before and after the run — the ledger had not moved — and every line that
changed is this rung's own rebuild: the `traversal` finding, the depth and cost
report lines, the assembler version, the policy bundle's content version (its
declaration in `ccf_config.yaml` changed) and the seal. Quiescence is a property
of a run, never of the database. A reader whose figures differ has **re-derived**,
not replayed, and the most likely reason is that the ledger moved.

## Artifact-by-artifact

| File | What it carries |
|---|---|
| `artifacts/question.yaml` | the demonstration question — the anchor LEI, the parameters and the `asked_at` pin. **Nothing in any module names an LEI**; changing the subject here re-asks the same question of another family |
| `artifacts/source-vocabulary.yaml` | where every value comes from: the six family predicates with the **direction each is read in**, the node predicates, the attribute table and its columns, the duplicate-identity rule, and the closed served-jurisdiction set |
| `artifacts/ttl.yaml` | the 24-hour window, its ceiling, and the anchor — the latest assertion time among the admitted family edges, which moves as relationship records are published |
| `artifacts/assembly-recipe.yaml` | the steps, in order, with a witness per step |
| `artifacts/expected.yaml` | what the served product must contain, **declared rather than derived from a run**, plus the census of the estate and three deliberately wrong methods with the numbers each would have produced |
| `artifacts/gates.yaml` | the **seventeen** product gates as data (`CFT-G18`, the ambiguous anchor, since 2026-09-03), each with the sabotage applied to it and the observed red recorded |
| `backends.yaml` | the two store bindings — four environment variable names and their remedy strings, and nothing else |
| `ccf_config.yaml` | the product class, the two operators, the request contract, the depth default and the capability binding that bounds it, and the declared-but-inert parameters |
| `deployment.py` | everything domain-specific: the ledger queries, the tables, the columns, the estate's vocabulary. Makes no fabric call |
| `produce.py` | the fabric's call spine. Names no table, no column and no domain word |
| `projection.py` | the perspective — the FIBO class axis that separates the two roles |
| `assembler.py` | the governed seam, reached identically by both callers |
| `transport.py` | the in-process transport adapter behind `ProductClient` |
| `run.py` | the command-line driver — the first of the two thin callers |
| `server/serve.py`, `server/compose.py`, `server/egress-door.yaml` | the MCP door — the second caller, and the ladder's first |

## Whitepaper / CLAUDE.md sections exercised

| Section | How |
|---|---|
| Whitepaper §7.3 — Context Graph | the family graph, assembled from a ledger's triples and normalized to a single parent → child orientation in one place |
| Whitepaper §7.4 — Context Operators | **two** in the plan — Policy and Traversal. Every rung before this one declared exactly one, and the traversal is where the count moves off one |
| Whitepaper §7.5 — Context Projection | `FamilyTreeProjection`, whose perspective conditions on FIBO class rather than on a role map |
| Whitepaper §7.6 — Context Product Contract | the three validation gates, and the request contract that refuses a depth above the backend's capability by name |
| Whitepaper §7.7 — Half-life and Context Debt | the debt figure and its decomposition, advisory at this rung and served beside the answer |
| Whitepaper §7.10 — Decision Replay | the replay record, addressed beside the product |
| Whitepaper §8.3 Pattern 3 — MCP | the product tool, and a registered product resource that refuses by name because this class is parameterized |
| `CLAUDE.md` §6.4 — the No-Hardcoding Rule | no prompt, no threshold, no LEI, no predicate IRI and no routing value in any module |
| `CLAUDE.md` §7.1 — bidirectional MCP | MCP as egress, in front of a product that opens two stores per ask |
| `CLAUDE.md` §10 — single-writer | this example is read-only against both stores; nothing it runs holds a write handle |

## What to change first

**Point it at your own estate.** `backends.yaml` names the four environment
variables; `deployment.py` names the ledger queries, the table and the columns.
Those two files are the whole adaptation surface for different stores.

**Then change the vocabulary.** `artifacts/source-vocabulary.yaml` decides which
predicates count as family, **which direction each one is read in**, and what
makes two records the same company. The direction is the highest-value line in
the file: read `hasGlobalUltimateParent` the wrong way round and the graph still
looks reasonable — 825 edges where the correct reading gives 722 — while the root
count moves 83 to 59 and every ultimate parent points backwards.

**Then change the question.** `artifacts/question.yaml` carries the anchor and
the parameters. Nothing in any module names an LEI, so a different family is an
artifact edit rather than a code change — but read the closed jurisdiction set
above first, because a different family will exhibit a different footprint.

**Then change the perspective.** `projection.py` and the roles declared in
`ccf_config.yaml` decide what each role sees. The axis is a FIBO class, so a
third role is a class predicate rather than another branch.

## What would fail

**Seventeen gates, and every one has been made to fail deliberately** — the
sabotage applied to each and the observed result are recorded as data in
`artifacts/gates.yaml` and in `CP-SPEC-004` §G.2. A gate that has never been
observed red is not evidence that it runs.

**None of the seventeen passed its first sabotage**, and that is not the same as
saying the risk was absent. Several were rewritten *before* they were ever run,
because the design pass measured that the obvious version could not
discriminate. `CFT-G05` written as *"two depths are two content addresses"* —
the criterion's own wording — passes its own sabotage, because the depth is
echoed into the payload and the payload is what is sealed; the roster limb
exists because of that measurement. `CFT-G04` written as *"the walked depth is
3"* passes against a serve-time literal `3`. **A check that reads a token
present in both the compliant and the violating case is measuring vocabulary,
not content.**

**The three wrong methods are declared with the numbers they produce**, in
`artifacts/expected.yaml`, so each control can be shown to *discriminate* rather
than merely to differ. Run the cycle detector over the raw triples instead of the
normalized edges and it reports **130** circuits where the family graph has
**2**. Read one ultimate-parent predicate backwards and the root count moves
**83 → 59** while the edge count stays plausible. Assert `len(findings) > 0` and
a three-member roster with one member swapped in from the other cycle passes —
a circuit that does not exist in the graph at all.

**The snapshot.** The transcript published on the documentation page is the
default run at commit — named on the page — asked as of the pinned
`2026-08-31T12:00:00+00:00`, serving content address
`fad6e55da2c0e6276b69d9a053e4eff155e5c3266b68f3fffb873b0c5e754fc7`. The page's
snapshot names ledger transaction `5112`: that is `census.ledger_t_read_at`, the
read the reviewed artifact holds from the 2026-08-31 measurement pass, and the
program does not print the counter. The transcript itself was re-captured on
2026-09-05 with the ledger head at `5296` — measured before and after the run,
and unchanged since the 2026-09-03 capture — so the seal moved from `205ae065…`
because the payload gained the `traversal` finding, not because the estate
moved. Every figure in it came from that run.

**Eleven SDK-surface and estate gaps were raised here, in Phase 24.4, and
recorded.** They are `D-26` through `D-36`, recorded under that phase's
criterion 49. Seven of the eleven are written up as findings in `CP-SPEC-004`
§F.4; the other four are recorded where they were ruled. Phase 24.5 closed
these in the SDK (each finding carries its dated note in §F.4): the Fluree
adapter, which *floored* the read with `Fluree-Min-T`, now pins a read to a
transaction — a JSON-LD claim read at `ledger@t:N`, carried in the lineage as
`store_snapshot_pin` (`24.5-L-01` through `L-04`, `D-IMPL-240` (2)); the egress
builder takes `expose_product_resource` (`24.5-L-09`), so a tool-only door is
expressible — this rung keeps its resource registered and refusing by ruling;
and the Traversal family has a node-class admission filter
(`admitted_entity_classes`, `24.5-L-05`), which this rung does not bind. `D-30`
(`24.5-L-08`) and `D-31` (`24.5-L-10`, the gate checker) are closed too. `D-32`
and `D-33` are the two grounds role 1 was struck on and are recorded where they
were ruled; whether any of `D-26`..`D-36` beyond those named is open is a
question for its own record, not a status invented here (`D-IMPL-227`). **An
executor surfaces gaps; it does not close them**, and no file under `src/` or
`runtime/` was touched by Phase 24.4 or by the return trip that wrote this
paragraph.
