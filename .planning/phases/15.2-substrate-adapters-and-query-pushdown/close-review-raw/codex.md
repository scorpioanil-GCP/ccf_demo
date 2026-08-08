**Verdict**

I would **not approve** this phase gate yet. The package is broadly coherent, and the `allowed_entities` semantics look sound on paper, but there are two rejection-grade issues: one known adapter/fallback byte-divergence is still open, and one threshold-shaped constant is explicitly shipped in `/src` despite the phase ground rule.

**Blocking Findings**

1. **BLOCKING — Known replay-portability / byte-identity divergence remains open.**

   Artifact: `.planning/.../deferred-items.md`, `DI-15.2-03`; claims affected: `SUBQ-04`, `SUBQ-08`, `GQ-31`, replay determinism.

   The package admits that pushed SQL validity filtering excludes non-UTC-offset claim timestamps by rendering them `NULL`, while the fallback compares actual datetime values and may include the same claim. That is a direct prose-implementation divergence: same question, same data, different bytes depending on substrate/path.

   The risk is described as “fail-closed,” but `GQ-31` is byte-identity, not “no over-disclosure.” This cannot ship as a satisfied conformance phase while the central conformance rule has a known counterexample. It needs either a normative prose amendment, a contract/storage normalization decision, or adapter behavior aligned with fallback before the gate.

2. **BLOCKING — `MAX_DEPTH_CEILING = 100` is a threshold in library code.**

   Artifact: `15.2-12-SUMMARY.md`, Neo4j backend claim; invariant affected: “Mechanism, not values: no domain value, threshold, or policy constant may live in `/src`.”

   The summary explicitly says Neo4j ships `MAX_DEPTH_CEILING (100)` and defends it as not Control Plane configuration. That conflicts with the phase ground rule as written. Even if the value only controls native translation vs fallback, it is still a threshold-shaped value in library code that changes execution behavior and telemetry. This should be moved to governed configuration, derived from a substrate capability, or justified through an explicit author decision before presentation.

**Advisory Findings**

1. **ADVISORY — Plan 01’s historical summary still says endpoint closure holds for every answer.**

   Artifact: `15.2-01-SUMMARY.md`, `key-decisions`.

   The final prose fixes this with `GQ-16` / `GQ-35` v1.0.1, but the gate package includes the stale “every answer view is endpoint-closed” claim. Since the amendment is deliberate, this is probably not a semantic defect, but the package should mark that Plan 01 claim as superseded to avoid a false contradiction.

2. **ADVISORY — The Neo4j/Mongo native-pushdown proof should be made explicit in the gate evidence.**

   Artifact: `15.2-12-SUMMARY.md`, `15.2-13-SUMMARY.md`; claim affected: `SUBQ-08`.

   SQL plan 09 clearly states the telemetry proof pattern: assert `translated_answers` increments and fallback does not. The Neo4j/Mongo summaries describe native translation and container-gated differential legs, but the provided gate text does not show the same “not silently degraded” proof as clearly. If the tests do assert this, name them in the phase-close evidence.

3. **ADVISORY — `GQ-01` has a wording trap.**

   Artifact: `docs/GRAPH_QUERY_SEMANTICS.md`, `GQ-01`.

   “A `GraphQuery` is an immutable value with two mandatory fields and no others” is immediately followed by optional vocabulary fields. The intended reading is clear, but the phrase “and no others” is easy to quote against the later optional fields. Rewrite as “with exactly two mandatory fields” or similar.

**Specific Things Checked And Found Sound**

1. The final prose does decide the prior dangling-edge semantic in `GQ-16` / `GQ-35`; the implementation no longer appears to be the only authority for that shape.

2. The `allowed_entities` model is semantically sound against entity resurrection: `None`, empty set, and populated set are distinct; seeds keep only “walk start” meaning; traversal cannot cross outside the survivor set; relationships require both endpoints in-set for constrained answers.

3. The segmentation rule correctly records executed query hashes in execution order rather than predicted plan shape, and the ArtifactStore bytes requirement is the right replay-audit mechanism.

4. `QueryFragment` excluding `seeds` and `allowed_entities` is the right structural guard: operators cannot smuggle segment-boundary data.

5. `ProductSource` being mount-only over `AdmittedProduct`, refusing malformed graph payloads at mount, and answering empty on tenant mismatch is consistent with the tier-2 seam.

6. The single-writer story is directionally sound: the package claims write-shaped implementations are confined to `ccf.graph._writer`, with `GraphWriter` in protocols only as an interface.

Note: I attempted to inspect the live tree, but command execution in the sandbox failed before startup with `bwrap: loopback: Failed RTM_NEWADDR`. This review is therefore based on the provided phase-close artifacts.
