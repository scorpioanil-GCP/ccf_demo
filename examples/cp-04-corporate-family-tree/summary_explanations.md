# Corporate Family Tree — what it is, what it costs you not to have it

**Who this is written for.** Three readers at once: **technical product
managers** deciding whether this is worth funding, **engineers** who have to
believe it, and **banker subject-matter experts** who have to recognize the
problem it solves. Every run below is stated three times over — what came back,
what an ordinary tool would have got wrong, and how it works with the file
named, so a claim can be checked rather than taken.

**The argument, in one paragraph.** A report tells you what the data says. A
Context Product tells you what you may *rely on*: who may rely on it, how long
it stays good, how complete it is, which store asserted each part of it — and it
**refuses rather than guessing** when it cannot answer. The difference is not
presentation. A family tree assembled from a reference table alone looks exactly
like a complete one; a family tree that knows which of its members have no
reference record says so, and can be made to prove it.

**What is new at this rung, in one line.** Every rung before this one reads a
single store and answers a lookup. **This one reads two stores and answers a
walk** — and both facts are visible in the answer rather than in the
architecture diagram.

---

## What this rung adds to the four before it

A reader arriving from rung 03 will not otherwise see the step, so it is stated
plainly. Four things change, and each is a different kind of change:

| | Rungs 00 – 03 | **Rung 04** |
|---|---|---|
| **Stores** | one, per product | **two, per ask** — an ownership graph and a reference table, joined in the assembly rather than in either store |
| **Shape of the question** | a lookup: *tell me about this thing* | **a walk**: *tell me about this thing and everything connected to it, out to a depth I choose* |
| **Ontology** | present, mostly descriptive | **load-bearing in three places** — served in the answer, driving the perspective, and validating the assembly |
| **Reach** | in-process only | **a door a remote agent can reach**, over MCP, in front of the same assembler |

---

## The pipeline

The demonstrated assembly is ten declared steps. Five of them are where every
difference between the runs below comes from; naming them once means each run's
mechanism note can stay short.

| Step | What it does | Layer |
|---|---|---|
| **Resolve** | turns the request's LEI into the graph's own node identity. Nothing in any module can construct a node URI from an LEI — it is a **read**, so the product is never its own system of record for identity | L2, assembly |
| **Policy** | filters the graph to what the asking principal is entitled to see, on a membership value minted by the walk itself | L4, operator |
| **Traversal** | bounds the walk at the caller's `max_depth`, over the six declared family predicates and no others | L4, operator |
| **Enrich** | resolves reference attributes for the members that carry an LEI, in **one batched query for the whole node set** rather than one per member | L2, adapter call |
| **Projection to contract assembly** | conditions the answer on the asking role's FIBO class axis, computes the expiry and the debt figure, seals it with a content address, and writes the replay record | L5 – L6 |

Cycle detection and duplicate-pair surfacing sit between Enrich and Projection
and declare **no operator at all**, deliberately. Circuit enumeration over an
already-collected edge set is not one of the fabric's four scheduling classes,
and registering it as a traversal to make a category fit would put something
untrue in the lineage record.

---

## Run 1 — the default question

### The output

```
make -s example-cp-04
```

Excerpt — the closing summary. The full run also prints the served product
itself: 22 members, their edges, their FIBO class chains and four findings — the
fourth, `traversal`, is the row behind the `depth applied` and `what it cost`
lines below.

```
What a plain SELECT would not have told you:
   asked as of        2026-08-31T12:00:00+00:00
   anchor             54930022CZO1N2UGVW07  SUPER MICRO COMPUTER, INC.
   ...its class chain 7 FIBO classes, from Corporation
   depth asked        absent -> the DECLARED default 3, read from ccf_config.yaml's request_contract defaults by the SDK's own resolution
   depth applied      3   requested, 3 reached — a depth this estate cannot exhibit is SERVED
   ...what it cost    22 node(s) visited, 25 edge(s) walked — STRUCTURAL counts, so two runs of one question seal identically
   ...the hard limit  100, the backend's capability (authority technical, source fluree/fibo-v2); over it the request is refused by name and answered at no narrower depth
   deepest node       3 hop(s) out — an undirected NEIGHBORHOOD, not a directed descendant tree (D-36)
   nodes returned     22
   ...resolved in the attribute store    2
   ...resolved to NO row                 20   — STILL IN THE TREE. A member with no LEI is a member
   jurisdictions      ['NL', 'US-DE']   — SERVED and asserted, never a permission key
   perspective role   credit-officer   (class axis Corporation, 22 member(s) detailed)
   findings           4
     - ownership_cycle: 3 member(s)
         CycCalderIndustrialNv
         CycThornburyCapitalLtd
         CycMeridianHoldingsSa
         closing edge CycMeridianHoldingsSa -> CycCalderIndustrialNv (owns)
     - duplicate_entity_pair: 2 member(s)
         SubSuperMicroComputerBV
         SuperMicroComputerBV
```

### What you'd have missed

**Twenty of these twenty-two companies have no reference record, and a family
built from the reference table alone would have returned two.** That is the
single most consequential number on this page. An exposure roll-up, a
concentration check or a group-limit calculation drawn from the entity master
would have found the parent and one Dutch subsidiary, balanced perfectly, and
been wrong about the shape of the group by a factor of eleven. The twenty are
not noise — they are the subsidiaries a filer lists in its own annual filing and
a reference vendor has never issued an identifier for. **A member with no
identifier is still a member.**

**Two of those twenty-two are the same company, entered twice.** *Super Micro
Computer B.V.* appears once with a legal-entity identifier and once without, one
hop apart, under two spellings. Served as two subsidiaries, a group exposure
counts that entity twice; served as one, the family loses a real record. The
product does neither — it reports the pair as a finding and leaves the decision
where it belongs.

**Three of them own each other in a circle.** `CycCalderIndustrialNv`,
`CycThornburyCapitalLtd` and `CycMeridianHoldingsSa` form a closed ownership
loop. A naive walk over this structure does not return a wrong answer — it
returns *no* answer, because it never terminates. What arrives here instead is
the circle **named**, with the members and the edge that closes it, so an
analyst reads *"these three own each other"* rather than *"the report timed
out"* or, worse, *"this subsidiary has an ultimate parent that is also its
subsidiary"* with no explanation attached.

**And the jurisdictional footprint is `['NL', 'US-DE']` for a group of
twenty-two.** That is not the group's real footprint — it is the footprint of
the two members that have a record. The product serves the number *and* the
twenty members it could not place, as a third finding, so nobody reads a
two-country footprint as a fact about the group.

### How it works

The walk is bounded by the **Traversal** operator over the six family predicates
declared in **`artifacts/source-vocabulary.yaml`**, each with the *direction it
is read in*. Attributes are resolved in one batched query against the
`legal_entity` table named in the same file — never the `crosswalk` decoy beside
it, which resolves 39 of the graph's 181 identifier-bearing nodes where
`legal_entity` resolves 142. Cycle detection runs in the assembler, and the
roster is asserted by name rather than counted: gate **`CFT-G07`** fails on a
three-member roster with one member swapped in from the other cycle, which a
`len(findings) > 0` check accepts. Gate **`CFT-G09`** fails if a member carrying no
identifier is dropped from the tree or from the roster — which, in this family,
is exactly the twenty that resolve to no reference row.

The `assembled by` line names the assembler implementation that produced this run (`cp-04.corporate-family-tree@1.0.2`) — transcript evidence, read off the program's own stdout.

Decision Replay carries the same identity: the assembler id and version land under Perspective Conditioning for fulfilled **and** refused decisions, which `tests/examples/test_cp_04_seams.py::test_replay_carries_the_assembler_identity_for_fulfilled_and_refused` proves. The transcript line is evidence beside the record, not the only carrier.

---

## Run 2 — one hop instead of three

### The output

```
make -s example-cp-04 MAX_DEPTH=1
```

Excerpt — the lines that differ from Run 1.

```
   depth asked        1   (named by the caller)
   depth applied      1   requested, 1 reached — a depth this estate cannot exhibit is SERVED
   deepest node       1 hop(s) out — an undirected NEIGHBORHOOD, not a directed descendant tree (D-36)
   nodes returned     20
   ...resolved to NO row                 18   — STILL IN THE TREE. A member with no LEI is a member
   perspective role   credit-officer   (class axis Corporation, 20 member(s) detailed)
   context debt D_c   0.1000  ->  ok
   ...decomposed      F=1  C=1  S=0.9
   content address    7163d0a1b5b7b9cdd1a6b8c63dd11b970c7d4048f2e8c1f7dbef4884b3ab4e2d
```

### What you'd have missed

**Two different questions, two different answers, two different seals.** Twenty
members at one hop, twenty-two at three. Neither is more correct — *"who does
this company directly own?"* and *"what is this whole group?"* are different
questions, and a credit file that mixed them would compare a first-tier
subsidiary list against a full group roster and read the difference as an
acquisition.

**The consequence is a cache, and it is the reason the depth is inside the
seal.** A system that stored answers under the company's identifier alone could
hand a one-hop answer back to a caller who asked for three. Here it cannot: the
two answers seal to `7163d0a1…` and `fad6e55d…`, so they are different objects
in any store that addresses by content.

**AND THE DEBT MOVES WITH THE DEPTH, which it did not until 2026-09-01.** `D_c`
reads `0.1` here and `0.0909` at the default, because `S` is the fraction of the
members THIS PAYLOAD SERVED whose identity no finding disputes — `18/20` at one
hop, `20/22` at three. The two disputed members sit one hop out, so they survive
every depth this product accepts while the denominator shrinks with it. Until the
close panel found it, `S` was taken over the deployment's *source read* instead,
and this line printed `0.0909` at every depth — a debt score that could not move
with the question. That is what gate **`CFT-G05`**'s third limb now holds, against
two figures pinned in `artifacts/expected.yaml`.

**The dangerous version of this is not a wrong depth — it is a silent one.** Ask
for eight and the run serves the three hops this family has and says so in the
`traversal` finding (Run 5). Ask for more than the backend can walk and it
refuses by name. A build that quietly clamped that request to the backend's
capability would return a payload that looks entirely healthy, seals cleanly,
and answers a question nobody asked.

### How it works

The default of `3` is a Control Plane value under `request_contract.defaults`
in **`ccf_config.yaml`**, applied by the SDK's own request resolution, so a
defaulted depth arrives carrying the authority `default` and the declaration's
pin rather than a number some module substituted. The hard limit is not a number
in this deployment at all: `capability_bindings` names the SDK's
`traversal-depth` token, and the value is read off the substrate at resolution
time. Neither number is typed into any module. Gate **`CFT-G05`** asserts that two
depths produce two answers, and asserts it **on the member roster** and **on the
measured debt** rather than on the seal alone, because the seal moves on its own:
the applied depth is echoed into the payload, so a seal-only check passes its own
sabotage. The debt limb reads its two expected figures from
**`artifacts/expected.yaml`** rather than carrying them in the test, so the edit
that would break the code cannot also fix the literal.

---

## Run 3 — the same family, a different perspective

### The output

```
make -s example-cp-04 ROLE=kyc-analyst
```

Excerpt.

```
   perspective role   kyc-analyst   (class axis Corporation, 0 member(s) detailed)
   content address    79733117121056fe40c6c095e4f7ff7ec6be33b884676fa4e60b38d43979bac8
```

### What you'd have missed

**Two roles, the same twenty-two companies, two different documents.** A credit
officer sees the family detailed; a KYC analyst sees the structure without the
detail, because the two sit on **opposite sides of one class axis** rather than
on opposite sides of a hand-written list of who may see what. That distinction
is what makes the perspective auditable: *"why did this reader see that?"* has
an answer in the ontology, not in a routing table somebody edited.

**And the two seal differently, which is what makes the flag able to fail.** A
perspective that changed the presentation and left the seal identical would be
decoration — a switch that cannot fail. `fad6e55d…` and `79733117…` are
different addresses, so the difference survives into the audit record and into
any cache.

### How it works

The axis is a FIBO class, applied in **`projection.py`**, and the two roles are
declared in **`ccf_config.yaml`**. Gate **`CFT-G16`** fails if the perspective is
re-implemented as a hand-written role map, and a standing check asserts the two
roles seal to different addresses — so a build in which they converge goes red
rather than leaving a switch in place that no longer does anything.

---

## Run 4 — a second anchor, served with the idle declaration named

### The output

```
make -s example-cp-04 LEI=549300F16C4PEFXU0S92
```

Excerpt — the lines that differ from Run 1.

```
   anchor             549300F16C4PEFXU0S92  SUPER MICRO COMPUTER B.V.
   depth applied      3   requested, 0 reached — a depth this estate cannot exhibit is SERVED
   ...what it cost    1 node(s) visited, 0 edge(s) walked — STRUCTURAL counts, so two runs of one question seal identically
   nodes returned     1
   jurisdictions      ['NL']   — SERVED and asserted, never a permission key
   findings           3
     - idle_jurisdictions: 1 member(s)
         US-DE
     - unresolved_jurisdiction: 0 member(s)
   content address    9865568d5abc560e38766644406938a5fd61190fba377c123ff354072adfabe7
```

A one-member family, served, with a finding that names the declared jurisdiction
this family never exhibits. Anchoring on a larger group whose members serve a
jurisdiction the document does *not* declare fails the other way — as a runtime
failure, not a served answer — naming the values the document does not declare.

### What you'd have missed

**The served vocabulary is closed, and the two directions are treated
differently on purpose.** Most systems check that nothing *unknown* comes out;
here a served jurisdiction outside the declared set is a contradiction among the
deployment's own inputs, and the fabric refuses to reach an answer at all. The
other direction — a jurisdiction code sitting in the configuration that no
member of *this* family exhibits — is a fact about this family, not a broken
deployment, so it is served as a finding: a rule that fired on nothing is named
rather than left looking like a rule that is working.

**For a banker, the consequence is about the value in the box, not the box.** A
family whose members serve a jurisdiction nobody declared is the case where a
reporting or screening rule silently has no opinion, and that is the case that
fails loudly. A declared code that this family never touched is reported beside
the answer, so nobody reads the configuration as evidence of coverage.

### How it works

The closed set lives in **`artifacts/source-vocabulary.yaml`**. **`deployment.py`**
still raises on an undeclared served value — an invariant failure that reaches
the command line as `CCF runtime failure` with exit 2 — and, since Phase 24.6,
returns the observed set together with an `idle_jurisdictions` finding for a
declared value that never fired. Because the demonstration family's declared
set is *its observed set*, both declared rows fire under the default anchor and
neither is idle — which is what makes each of them sabotageable at all.
Swapping the demonstration anchor is therefore an artifact edit as well as a
parameter, and the README says so.

---

## Run 5 — a depth that is served, and the four refusals

### The output

```
make -s example-cp-04 MAX_DEPTH=8
```

Excerpt — served, with the gap visible.

```
   depth asked        8   (named by the caller)
   depth applied      8   requested, 3 reached — a depth this estate cannot exhibit is SERVED
   nodes returned     22
   content address    2607d522bcfe0821f635dd86b2d4af08b9a6d0973ed64af11ea7df4fce95fd9d
```

```
make -s example-cp-04 MAX_DEPTH=0
```

```
refused: below-minimum — max_depth
```

```
make -s example-cp-04 MAX_DEPTH=101
```

```
refused: bound-exceeded — max_depth
```

```
make -s example-cp-04 AS_OF=2026-03-31
```

```
refused: not-supported-at-tier — as_of
```

```
make -s example-cp-04 LEI=000000000000000000ZZ
```

```
refused: subject-unavailable
```

The four refusals exit non-zero, and each is one line on stderr with stdout
empty. A refusal is not a crash, but it is also not a success. The line prints
the reason and the parameter it names; the kind — `product-request-violation`,
`constraint-refusal`, `not-supported-at-tier`, `subject-unavailable` — travels
on the envelope the program branched on.

### What you'd have missed

**A depth the family cannot fill is an answer, not an error.** Asked for eight,
the walk reaches three, and the finding says both. Refusing that request would
have told a caller who wanted "the whole group" that they asked wrongly; a
served answer with `requested_depth: 8` beside `depth_reached: 3` tells them the
group is smaller than their question.

**A depth of zero is not a question this product answers, and the contract says
so.** A zero-hop family is the anchor alone — a lookup wearing a walk's name.
The floor of `1` is declared on the request contract as the parameter's valid
domain, beside its type, and the SDK refuses below it by name. It is not a
policy: nobody is being denied anything; the question is malformed for this
product, the way a negative tolerance is.

**The dangerous outcome of a depth beyond the backend is not the refusal — it is
the clamp.** A system that takes `max_depth=101`, walks a hundred, and returns a
healthy payload has answered a narrower question than the one asked, with
nothing in the output saying so. Every downstream conclusion inherits a group
boundary that was never requested. Here the caller finds out at the moment of
asking, and the refusal carries the bound and the authority that set it — the
backend's own capability, not a number somebody typed.

**And a company the ledger does not carry is a governed answer, not an
exception.** `subject-unavailable` is a determination the fabric made and
recorded; at the doors it is disclosed in the same shell an unentitled caller
receives, so the response cannot be used to learn which companies exist.

**And the dangerous outcome of an as-of date is acceptance.** *"Show me this
group as it stood at last year's annual review"* is a reasonable question and
this tier cannot answer it. A system that took the date, ignored it, and served
today's group would have answered a question about today while the caller
believed they asked about last year — and the file would carry a group structure
wearing the wrong date. The parameter is **declared and always refused**, so the
gap is visible in the contract rather than discovered in an audit.

### How it works

Every one of these is declared, and none is a condition written in a module.
The depth's floor is the parameter's valid domain, declared under
`argument_domains` on the request contract in **`ccf_config.yaml`** and held by
the SDK's own request validation (`src/ccf/products/request.py::refuse_request`,
the domain step) as a `product-request-violation` returned as data — deleting
the declaration is the sabotage, and `0` was served before it existed. The
depth's hard limit is the substrate's own capability, bound to `max_depth`
under `capability_bindings` in **`ccf_config.yaml`** and resolved by the SDK
(`src/ccf/products/constraints.py::resolve_effective_request`) into a
`constraint-refusal` carrying the bound with authority `technical`. The `as_of`
verdict is the SDK's too, returned as data by the tier step of `refuse_request`
(`src/ccf/products/request.py::_refuse_tier`, `24.5-L-12`/`L-13`) before the
product's own code runs, from the declaration under `unsupported_arguments`.
The missing anchor is the assembler's own determination, returned as a
`subject-unavailable` refusal rather than raised. Gate **`CFT-G03`** fails if a
depth above the capability is clamped instead of refused, or if a depth the
estate cannot exhibit is refused instead of served; gate **`CFT-G06`** fails if
`as_of` is silently honored.

---

## Vocabulary — what the term means, and what it is

| Term | What it means to you | What it is in the system |
|---|---|---|
| **Content address** | a tamper-evident seal on one answer | `sha256` over the canonical bytes of the served product |
| **Context debt** (`D_c`) | how far short of ideal this answer falls | a composite of freshness, completeness and semantic consistency, `0`–`1`; advisory at every rung of this ladder |
| **Half-life** (`λ_c`) | how fast a fact of this kind goes stale | a per-signal-class decay rate; ownership edges decay on an acquisition-and-restructuring cadence |
| **Max depth** | how far out from the company you asked to look | a request parameter that travels into the content address; absent, the declared default `3`; below the declared floor of `1`, refused as malformed; above the backend's capability, refused by name |
| **Depth reached / cost** | how far the walk actually got, and what it took | the `traversal` finding — requested depth, depth reached, nodes visited and edges walked, all structural counts and never a clock |
| **Perspective / role** | which reader this answer was shaped for | a projection conditioned on a FIBO class axis, not on a list of who may see what |
| **Finding** | something about this family worth telling you | a typed record beside the tree, carrying a roster and — for a cycle — the edge that closes it |
| **Ontology / FIBO class chain** | what kind of thing each member is | the served `type_chain`, so a consuming agent needs no second lookup |
| **`ledger_t`** | which transaction of the graph store this was read at | the store's transaction counter, recorded **beside** the snapshot time and never inside it; it is not a date and it does not implement *as of* |
| **Replay record** | the receipt that lets you reconstruct this decision | the five-dimension record addressed beside the product |

---

## Where each claim is enforced

This is the section that separates a demonstration from a guarantee.

| Claim | Mechanism | Gate that fails if it stops being true |
|---|---|---|
| Every member carries a known FIBO class | the served class chain | `CFT-G01` |
| Only the six declared family predicates enter | the closed predicate vocabulary | `CFT-G02` |
| A depth above the backend's capability is refused by name and answered at no narrower depth; a depth the estate cannot exhibit is served with the gap visible | `capability_bindings` in `ccf_config.yaml`, resolved against the substrate's declared capability | `CFT-G03` |
| An absent depth takes the *declared* default | `request_contract.defaults`, applied by the SDK's resolution | `CFT-G04` |
| A depth below the declared floor of 1 is refused as a malformed question, never served as a one-node family | `request_contract.argument_domains`, held by the SDK's `refuse_request` | `test_the_floor_is_the_sdks_verdict_over_the_declaration_and_needs_no_store` and the two live boundary asks in `tests/examples/test_cp_04_traversal.py` (a test, not a gate id — see the README) |
| Two depths are two answers, on the roster and not the seal alone | the walk bound | `CFT-G05` |
| An as-of date is refused, never silently honored | `unsupported_arguments` | `CFT-G06` |
| A cycle is reported with its exact roster | the assembler's detector | `CFT-G07` |
| A member carrying no identifier stays in the tree *and* in the roster | the join, which does not filter | `CFT-G09` |
| **The assembly** opens both stores, each for its own thing | the two store bindings | `CFT-G10` |
| Attributes are read in one batched query, never one per member | the batched select | `CFT-G11` |
| Each served member carries its class chain | the projection's output shape | `CFT-G15` |
| The perspective conditions on class, not on a role map | `projection.py` | `CFT-G16` |
| An identifier carried by more than one node is refused as ambiguity, never resolved by row order | `resolve_anchor`, which collects every binding | `CFT-G18` |

**All seventeen gates have been made to fail deliberately at least once**, under
their own gate id, and the sabotage applied to each is recorded as data in
`artifacts/gates.yaml`. The seventeenth, **`CFT-G18`**, was added on 2026-09-03:
an LEI carried by more than one node is refused as `AnchorAmbiguityRefusal`
(`D-IMPL-245` (4)) — never a coin flip on the store's row order, never a 404,
never a served family with a finding. **None of the seventeen passed its first
sabotage** — but
that is not the same as saying the risk was absent. Several were rewritten
*before* they were ever run, because the design pass measured that the obvious
version could not discriminate: a gate asserting only *"two depths are two
content addresses"* passes its own sabotage, because the depth is echoed into
the payload and the payload is what is sealed.

---

## Why you can trust these numbers

Every figure in this document came from a real run against a live estate, not
from a design document.

The default run is pinned: asked as of `2026-08-31T12:00:00+00:00`, serving
content address
`fad6e55da2c0e6276b69d9a053e4eff155e5c3266b68f3fffb873b0c5e754fc7`. The census
behind every figure was read at ledger transaction `5112` on 2026-08-31, and
that is the transaction the documentation page names. The transcript was
re-captured on 2026-09-03 with the ledger head at `5296` and reproduced byte for
byte, the one new line being `assembled by`; it was re-captured again on
2026-09-05 with the head still at `5296`, measured before and after the run,
and every changed line is this rung's own rebuild — the `traversal` finding,
the depth and cost lines, the assembler version, the policy bundle's content
version and the seal, which moved from `205ae065…` because the payload gained a
finding and not because the estate moved. **The product reproduces
byte-identical against a quiescent ledger for that run.** That sentence is the
whole of the claim and no stronger one appears anywhere in this example.

**The qualifier "for that run" is load-bearing, and it was measured.** The
ledger's transaction counter moved **4,560 to 5,112 between two sittings six
days apart** — 552 transactions — and **5,112 to 5,296** by the 2026-09-03
re-capture, 184 more, with every seal unchanged. Quiescence is a property of a run, never of the
database. A reader whose figures differ has **re-derived** rather than
reproduced, and the most likely reason is that the ledger moved.

The content address is the single check worth running. It is a hash over the
whole answer, so it only reproduces if every input did: the resolved anchor, the
walked members, the entitlements in force, the reference rows, the debt figure,
the expiry window and the operator plan. One drifted value anywhere and the hash
differs.

Reproduce it with `make -s example-cp-04`, after exporting the four connection
variables as the README describes.

---

## What these runs do not show

- **A type-constrained walk.** The idea that the walk stops when a neighbor's
  class falls outside an admitted set was **struck from this rung**, on two
  independently measured grounds: no identifier-bearing anchor in this estate
  reaches a class-diverse node within the demonstrated depth, so a gate over it
  would go green having proven nothing; and, when the rung was built, the SDK's
  traversal family typed the walk on **edges only**. Phase 24.5 gave the family
  a node-class admission filter (`admitted_entity_classes`, `24.5-L-05`); this
  rung does not bind it, because the estate ground still stands.
- **A directed descendant tree.** The walk is an undirected **neighborhood** —
  it follows a declared edge in both directions — so *depth* here is hops
  through adjacency, not generations of ownership. At the demonstrated depth the
  two shapes agree; at depth 2 they do not, and the specification says so rather
  than letting a reader assume a parent-to-child tree.
- **Reconstruction as of a past date.** Refused here by design; it arrives at a
  later tier with a different product.
- **A complete group.** The demonstration anchor was chosen because **one anchor
  exercises everything this rung teaches** — a family deep enough that depth
  changes the answer, the only cycle reachable from an identifier-bearing anchor
  anywhere in the estate, the two-store split on a small enough subtree to read,
  and the same company entered twice. It was not chosen for having a complete
  reference footprint, and no company in this estate has one.
- **A snapshot-pinned read.** As this rung was built, *the graph adapter
  floors* the read at a minimum transaction rather than pinning it to one —
  the words of the 2026-08-31 measurement, kept. Phase 24.5 closed that
  (`24.5-L-01` through `L-04`, `D-IMPL-240` (2)): the adapter now pins a read
  as a claim at `ledger@t:N` and the lineage carries the pin as
  `store_snapshot_pin`. The reproducibility claim above stays bounded to a
  quiescent ledger for that run because that is what these runs demonstrated —
  a pinned replay is a later rung's demonstration, not this one's.
- **Anything about the companies themselves.** This estate is public reference
  and filing data used to exercise mechanism, together with planted synthetic
  ownership circles. Nothing here is a credit opinion, and the circular
  structures are constructed rather than observed.
