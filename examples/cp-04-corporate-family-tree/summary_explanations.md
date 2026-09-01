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
itself: 22 members, their edges, their FIBO class chains and three findings.

```
What a plain SELECT would not have told you:
   asked as of        2026-08-31T12:00:00+00:00
   anchor             54930022CZO1N2UGVW07  SUPER MICRO COMPUTER, INC.
   ...its class chain 7 FIBO classes, from Corporation
   depth asked        absent -> the DECLARED default 3, read from ccf_config.yaml::request_contract.argument_defaults
   depth applied      3   (ceiling 6; over it is refused by name, never clamped)
   deepest node       3 hop(s) out — an undirected NEIGHBORHOOD, not a directed descendant tree (D-36)
   nodes returned     22
   ...resolved in the attribute store    2
   ...resolved to NO row                 20   — STILL IN THE TREE. A member with no LEI is a member
   jurisdictions      ['NL', 'US-DE']   — SERVED and asserted, never a permission key
   perspective role   credit-officer   (class axis Corporation, 22 member(s) detailed)
   findings           3
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

---

## Run 2 — one hop instead of three

### The output

```
make -s example-cp-04 MAX_DEPTH=1
```

Excerpt — the lines that differ from Run 1.

```
   depth asked        1   (named by the caller)
   depth applied      1   (ceiling 6; over it is refused by name, never clamped)
   deepest node       1 hop(s) out — an undirected NEIGHBORHOOD, not a directed descendant tree (D-36)
   nodes returned     20
   ...resolved to NO row                 18   — STILL IN THE TREE. A member with no LEI is a member
   perspective role   credit-officer   (class axis Corporation, 20 member(s) detailed)
   content address    4a859218f41930c19d7aee63850d120a0b6ca2dcf370fd005b29d48c2de19cdf
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
two answers seal to `4a859218…` and `205ae065…`, so they are different objects
in any store that addresses by content.

**The dangerous version of this is not a wrong depth — it is a silent one.** Ask
for eight and the run refuses (Run 5). A build that quietly clamped eight to the
ceiling of six would return a payload that looks entirely healthy, seals
cleanly, and answers a question nobody asked.

### How it works

The default of `3` and the bounds `1..6` are Control Plane values in
**`ccf_config.yaml`**, read by **`run.py`** and interpolated into its own help
text — so a config edit moves the walk *and* the documentation together, and
neither number is typed into any module. Gate **`CFT-G05`** asserts that two
depths produce two answers, and asserts it **on the member roster** rather than
on the seal alone, because the seal moves on its own: the applied depth is
echoed into the payload, so a seal-only check passes its own sabotage.

---

## Run 3 — the same family, a different perspective

### The output

```
make -s example-cp-04 ROLE=kyc-analyst
```

Excerpt.

```
   perspective role   kyc-analyst   (class axis Corporation, 0 member(s) detailed)
   content address    838afbb037a8ca820a2854b1ac7eedd296262508ce00d747369bf48ee6077ea8
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
decoration — a switch that cannot fail. `205ae065…` and `838afbb0…` are
different addresses, so the difference survives into the audit record and into
any cache.

### How it works

The axis is a FIBO class, applied in **`projection.py`**, and the two roles are
declared in **`ccf_config.yaml`**. Gate **`CFT-G16`** fails if the perspective is
re-implemented as a hand-written role map, and a standing check asserts the two
roles seal to different addresses — so a build in which they converge goes red
rather than leaving a switch in place that no longer does anything.

---

## Run 4 — a second anchor, refused in both directions

### The output

```
make -s example-cp-04 LEI=549300F16C4PEFXU0S92
```

```
artifacts/source-vocabulary.yaml declares jurisdiction(s) ['US-DE'] that no member of this family serves. The declared set is the family's OBSERVED set; a row that never fires is how an idle gate looks, and the observed set is ['NL'].
```

Anchoring on a larger group is refused the other way, naming the jurisdictions
that group serves and this document does not declare.

### What you'd have missed

**The served vocabulary is closed in both directions, and that is the stricter
half of the promise.** Most systems check that nothing *unknown* comes out.
This one also checks that nothing *declared* goes unused. A jurisdiction code
sitting in the configuration that no member of the family ever exhibits is a
rule that fires on nothing — which looks identical to a rule that is working
right up until the day it should have caught something.

**For a banker, the consequence is about the value in the box, not the box.** A
family whose members serve a jurisdiction nobody declared is the case where a
reporting or screening rule silently has no opinion. The refusal names which
direction failed and which codes were involved, so the fix is a one-line
document edit rather than an investigation.

### How it works

The closed set lives in **`artifacts/source-vocabulary.yaml`**, and
**`deployment.py`** refuses both an undeclared value and an unfired declaration.
Because the declared set is *this family's observed set*, both declared rows
fire and neither is idle — which is what makes each of them sabotageable at all.
Swapping the demonstration anchor is therefore an artifact edit as well as a
parameter, and the README says so.

---

## Run 5 — the two refusals

### The output

```
make -s example-cp-04 MAX_DEPTH=8
```

```
assembly refused: 400 max_depth=8 is outside the declared bounds 1..6. REFUSED BY NAME, never clamped — a clamped depth answers a question nobody asked, with no error
```

```
make -s example-cp-04 AS_OF=2026-03-31
```

```
assembly refused: 400 not_supported_at_tier. Reconstructing the corporate family as it stood on a past date requires ledger time-travel on the CCF temporal axis, which arrives at Tier 3 with covenant-in-force-as-of. This tier serves the family as it stands, recording the `ledger_t` the Fluree leg read at BESIDE `graph_snapshot_at` and never inside it.: as_of — declared by this class and always refused (Standard §2.4). This verdict is raised rather than returned because ProductRequestViolation.reason is a closed Literal with no member for it; see CP-SPEC-004 §F.4
```

Both exit non-zero. A refusal is not a crash, but it is also not a success.

### What you'd have missed

**The dangerous outcome of an out-of-range depth is not the refusal — it is the
clamp.** A system that takes `max_depth=8`, walks six, and returns a healthy
payload has answered a narrower question than the one asked, with nothing in the
output saying so. Every downstream conclusion inherits a group boundary that was
never requested. Here the caller finds out at the moment of asking.

**And the dangerous outcome of an as-of date is acceptance.** *"Show me this
group as it stood at last year's annual review"* is a reasonable question and
this tier cannot answer it. A system that took the date, ignored it, and served
today's group would have answered a question about today while the caller
believed they asked about last year — and the file would carry a group structure
wearing the wrong date. The parameter is **declared and always refused**, so the
gap is visible in the contract rather than discovered in an audit.

### How it works

Both refusals are declared in **`ccf_config.yaml`** — the depth bounds under
`argument_bounds`, the refused parameter under `unsupported_arguments` — and
neither is a condition written in a module. Gate **`CFT-G03`** fails if an
over-ceiling depth is clamped instead of refused; gate **`CFT-G06`** fails if
`as_of` is silently honored.

---

## Vocabulary — what the term means, and what it is

| Term | What it means to you | What it is in the system |
|---|---|---|
| **Content address** | a tamper-evident seal on one answer | `sha256` over the canonical bytes of the served product |
| **Context debt** (`D_c`) | how far short of ideal this answer falls | a composite of freshness, completeness and semantic consistency, `0`–`1`; advisory at every rung of this ladder |
| **Half-life** (`λ_c`) | how fast a fact of this kind goes stale | a per-signal-class decay rate; ownership edges decay on an acquisition-and-restructuring cadence |
| **Max depth** | how far out from the company you asked to look | a request parameter, bounded `1..6`, that travels into the content address |
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
| An over-ceiling depth is refused, never clamped | `argument_bounds` in `ccf_config.yaml` | `CFT-G03` |
| An absent depth takes the *declared* default | `argument_defaults`, read at serve time | `CFT-G04` |
| Two depths are two answers, on the roster and not the seal alone | the walk bound | `CFT-G05` |
| An as-of date is refused, never silently honored | `unsupported_arguments` | `CFT-G06` |
| A cycle is reported with its exact roster | the assembler's detector | `CFT-G07` |
| A member carrying no identifier stays in the tree *and* in the roster | the join, which does not filter | `CFT-G09` |
| **The assembly** opens both stores, each for its own thing | the two store bindings | `CFT-G10` |
| Attributes are read in one batched query, never one per member | the batched select | `CFT-G11` |
| Each served member carries its class chain | the projection's output shape | `CFT-G15` |
| The perspective conditions on class, not on a role map | `projection.py` | `CFT-G16` |

**All sixteen gates have been made to fail deliberately at least once**, under
their own gate id, and the sabotage applied to each is recorded as data in
`artifacts/gates.yaml`. **None of the sixteen passed its first sabotage** — but
that is not the same as saying the risk was absent. Several were rewritten
*before* they were ever run, because the design pass measured that the obvious
version could not discriminate: a gate asserting only *"two depths are two
content addresses"* passes its own sabotage, because the depth is echoed into
the payload and the payload is what is sealed.

---

## Why you can trust these numbers

Every figure in this document came from a real run against a live estate, not
from a design document.

The default run is pinned: asked as of `2026-08-31T12:00:00+00:00`, read at
ledger transaction `5112`, serving content address
`205ae0658ea626982b9d2923d81a226a00899b0c43ba74bbae4dfea8a140d498`. **The
product reproduces byte-identical against a quiescent ledger for that run.**
That sentence is the whole of the claim and no stronger one appears anywhere in
this example.

**The qualifier "for that run" is load-bearing, and it was measured.** The
ledger's transaction counter moved **4,560 to 5,112 between two sittings six
days apart** — 552 transactions. Quiescence is a property of a run, never of the
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
  would go green having proven nothing; and the SDK's traversal family types the
  walk on **edges only**, so the stop has no expression to build against. Both
  are recorded as open gaps rather than closed.
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
- **A snapshot-pinned read.** The graph adapter *floors* the read at a minimum
  transaction rather than pinning it to one, which is exactly why the
  reproducibility claim above is bounded to a quiescent ledger for that run and
  to nothing wider. Recorded as an open gap.
- **Anything about the companies themselves.** This estate is public reference
  and filing data used to exercise mechanism, together with planted synthetic
  ownership circles. Nothing here is a credit opinion, and the circular
  structures are constructed rather than observed.
