# Findings — cp-04-canonical

Findings raised while authoring this successor against the current SDK surface.
Each is adjudicated under `D-IMPL-315`: *"canonical path is richer"* is a
finding to adjudicate, never a licence to edit the example. The question asked
of every one is whether the behavior is **legitimate SDK semantics** or an
**actual mismatch**, with the basis stated.

---

## `CP04C-F-01` — Entity identity is POSITION-DEPENDENT, so endpoint selection cannot build a graph in which a node appears as both subject and object

**Status: FIXED-`D-IMPL-316` (2026-09-10). Adjudicated as a MISMATCH and
repaired as a bounded SDK fix on Dave's ruling. Reading 2 was taken: an entity
rule declares which payload field supplies a declared identity key, and the
DECLARED key is still what is hashed. The global content-hash and identity
model is untouched, the repair is hash-transparent, and no workaround was
applied — `admit_relationship_claim` was explicitly not used.**

### What the successor was doing

Declaring typed family edges through the resolution spec. cp-04 could not do
this — it recorded `24.4-D-35`, *"the declared resolution spec cannot express a
typed edge"*, and shipped one envelope per node plus explicit
`AssemblyWorker.admit_relationship_claim` calls for every edge.

**That gap is genuinely closed**, and finding it closed is the charter working
as intended: `24.5-L-21` added predicate selection and endpoint selection, and
`RelationshipResolutionRule`'s docstring closes `24.4-D-35` by name. Measured
live — three envelopes carrying `{parent, child, predicate}` minted exactly three
correctly-typed edges, with `owns` and `controls` selected by the payload and
the mutual pair preserved. Copying cp-04's shape would have reproduced a
workaround for a gap that no longer exists, and taught it as current practice.

### The miss

`AssemblyWorker` derives a URI as
`f"{rule.entity_class}://{content_hash(identity)}"` where
`identity = {key: str(payload[key]) for key in rule.identity_keys}`
(`src/ccf/assembly/worker.py::SpecDrivenEntityResolution.resolve`). The hash is
over a **mapping**, so the identity key's *name* is inside it.

Endpoint selection requires the two endpoints to come from two different entity
rules reading two different payload keys. Therefore the two endpoints
necessarily hash different key names, and **the same real-world node receives a
different URI depending on which position it was observed in.**

Both limbs measured:

| limb | declaration | result |
|---|---|---|
| different identity key names (`parent_uri`, `child_uri`) | the only shape endpoint selection permits | edges mint, but 3 real nodes became **5 entities** — `A` as parent `d838f82d…` and `A` as child `5e412b3e…` |
| one shared identity key name (`entity_uri`) | makes identities comparable | both rules read the one value the payload can hold, subject == object, the SDK correctly refuses the self-loop → **0 relationships** |

Hash inputs confirmed directly:
`content_hash({"parent_uri": "A"})` = `d838f82d…`,
`content_hash({"child_uri": "A"})` = `5e412b3e…`, not equal — and those are the
same digests the live fabric produced, so the two measurements agree end to end.

### Why this is a mismatch rather than legitimate semantics

Three grounds, and the adjudication does not rest on preference:

1. **The feature's own docstring names the case it cannot serve.** It states
   endpoint selection *"lets one envelope carrying `{parent, child, predicate}`
   mint a single edge between two entities of the same class."* It does — but
   only in a graph where no node is ever both a parent and a child. This
   fixture's family contains **22 mutual pairs**, so the ordinary case is the
   unsupported one.
2. **It contradicts the invariant the field's own docstring cites.**
   `identity_keys` is documented as making *"the URI stable across
   source-system change (INV-CH7-18)."* If the key's name is inside the
   identity, renaming a source field changes every URI, and two sources
   describing one entity under their own vocabularies can never resolve to one
   URI — which also blocks the multi-source lineage accumulation of
   INV-CH7-17.
3. **The existing test cannot see it.**
   `tests/assembly/test_worker.py::test_a_member_to_member_edge_is_expressible_from_one_envelope`
   ingests one envelope with one parent and one child and asserts
   `subject_uri != object_uri`. That passes for two genuinely different nodes
   and would pass equally if identity were position-dependent, which it is. The
   assertion the case needs — *the same node in both positions is one entity* —
   is absent.

### What was NOT done

- **No workaround.** `admit_relationship_claim` would sidestep this entirely,
  and it is exactly cp-04's shape; reaching for it would make the successor a
  cleaned-up cp-04 and would bury a live SDK defect under an example's
  cleverness.
- **No SDK edit.** Remediation is a ruling, not this sitting's to take.
- **cp-04 untouched** (`D-IMPL-261`).

### Readings for the ruling — none asserted

1. **Identity hashes VALUES in `identity_keys` order, not the mapping.** Makes a
   URI independent of the payload key that carried it, which is what
   INV-CH7-18 appears to promise. Changes existing entity URIs, so every pinned
   address moves — pre-v0, `D-IMPL-293` says that is a consequence to
   regenerate rather than a reason to prefer the smaller change.
2. **An entity rule declares an identity ALIAS** — the logical identity name,
   separate from the payload key that supplies it. Additive; existing rules keep
   their URIs by aliasing to their current key name.
3. **Accept the limitation and narrow the claim.** Same-class typed edges keep
   coming through `admit_relationship_claim`; the docstring stops asserting the
   case it cannot serve, and `24.4-D-35` is recorded as narrowed rather than
   closed.

Reading 1 is the one that makes the documented invariant true; reading 2 is the
one that costs nothing already shipped. **The choice is Dave's.**
