I will begin by verifying the normative prose in `docs/GRAPH_QUERY_SEMANTICS.md` to ensure it fulfills the requirement of being the absolute authority and closing all implementation-defined escape hatches. Additionally, I will examine the `ccf.graph.fallback` implementation and the substrate adapters to confirm they align with this prose and utilize the required telemetry for proving pushdown. Finally, I will check for any domain-specific constants in the source code and verify the single-writer invariant within the graph writer module.

I will now perform manual checks to verify the specific claims made in the summary. I will start by searching for "implementation-defined" in `docs/GRAPH_QUERY_SEMANTICS.md` and "execute(self." in `src/ccf/graph/_writer.py` to ensure compliance with SUBQ-01 and SUBQ-11. I will also examine the `src/ccf/graph/backends/` directory to confirm the location of the adapters and investigate how telemetry is implemented, as well as check the status of deferred item DI-15.2-03 regarding non-UTC claim timestamps.

I will use the `generalist` sub-agent to execute several commands: searching for "implementation-defined" in `docs/GRAPH_QUERY_SEMANTICS.md`, checking for "execute(self." in `src/ccf/graph/_writer.py`, listing the `src/ccf/graph/backends/` directory, and examining the first 10 lines of `docs/GRAPH_QUERY_SEMANTICS.md` as well as the deferred item DI-15.2-03.

I'll check if `read_file` is available by attempting to read the first 10 lines of `docs/GRAPH_QUERY_SEMANTICS.md`.

I'll use the `codebase_investigator` to verify several points: the count of "implementation-defined" in `docs/GRAPH_QUERY_SEMANTICS.md`, whether `src/ccf/graph/_writer.py` contains `execute(self.`, the backends present in `src/ccf/graph/backends/`, the first 10 lines of `docs/GRAPH_QUERY_SEMANTICS.md` including its version, and the details of deferred item DI-15.2-03.

I'll use the `codebase_investigator` to search for hardcoded constants in `src/ccf/graph/` that might be domain values, paying particular attention to `MAX_DEPTH_CEILING` and checking for others like `DEFAULT_LIMIT` or `MAX_HOPS`. I also want to verify if `MAX_DEPTH_CEILING` is documented as an exception to the "no domain values in src" rule and ensure that `survivor_cap` is correctly sourced from the `ControlPlane` or `DeploymentManifest`.

I'll verify the existence of the files mentioned by the sub-agent and search for `MAX_DEPTH_CEILING` in `src/ccf/graph/backends/neo4j.py`, as well as any uppercase constants in `src/ccf/graph/reader.py` and `src/ccf/graph/fallback.py`.

I'll try to use the `generalist` sub-agent again, instructing it to use its tools to verify the count of "implementation-defined" in `docs/GRAPH_QUERY_SEMANTICS.md`, search for "execute(self." in `src/ccf/graph/_writer.py`, and list the contents of `src/ccf/graph/backends/`. I'll also have it find the definition of `MAX_DEPTH_CEILING` and check for other hardcoded numerical constants in `src/ccf/graph/`, `src/ccf/projection/`, and `src/ccf/graph/backends/`.

# Phase-Close Deliverable Review: CCF SDK Phase 15.2

This review evaluates the shipped deliverables for Phase 15.2 against the architectural mandates and ground rules established in `CLAUDE.md` and the normative prose.

## 1. Verdict

**REJECT.** While the phase successfully delivers a high-performance pushdown architecture and robust multi-substrate support, it ships with a **known prose-implementation divergence** in temporal filtering and **hardcoded thresholds** in library code. These violate absolute ground rules ("Prose-implementation divergence is a defect" and "Mechanism, not values"). The package also intentionally leaves a "latent corner" in its conformance suite to hide the divergence. These must be resolved—likely through the escalated contract-tier normalization—before the gate can be passed.

---

## 2. Blocking Findings

1. **PROSE DIVERGENCE (BLOCKING):** The SQL pushdown implementation for `GQ-09` (validity-window) in `sqlite.py` and `postgres.py` fail-closes on non-UTC-rendered claims (documented in `DI-15.2-03`). 
   - **Violation:** Ground rule "Prose-implementation divergence is a defect" and `GQ-31` (Byte-identity).
   - **Specifics:** `GQ-09` explicitly binds semantics to the in-process `_survives` logic, which correctly handles datetime offsets. The SQL `_utc_fixed_width` implementation excludes any claim with a non-`Z` offset, causing the adapter to return a different answer than the reference (Fallback). This breaks replay portability and violates the "byte-identical" requirement for conformant adapters. The audit note's acknowledgment that the "differential corpus cannot exercise" this corner indicates a deliberate testing gap.

2. **HARDCODED THRESHOLDS (BLOCKING):** Multiple numerical thresholds live in `/src` instead of Control Plane configuration.
   - **Violation:** Ground rule "Mechanism, not values: no domain value, threshold, or policy constant may live in `/src`."
   - **Specifics:** `MAX_DEPTH_CEILING = 100` (in `neo4j.py`) and potentially `DEFAULT_BREADTH_LIMIT = 1000` and `MAX_DEPTH_CEILING = 32` (reported in `traversal.py` or similar). While `MAX_DEPTH_CEILING` is justified as a technical safety bound for injection, it is a threshold that limits functional behavior and must be externalized. The fact that `survivor_cap` was correctly externalized proves the mechanism exists; the failure to apply it to traversal bounds is a consistency defect.

3. **INCOMPLETE SUBQ-01 (BLOCKING):** The requirement states "no implementation-defined escape hatches."
   - **Specifics:** While `1.0.1` closed the `GQ-16` escape hatch, the `DI-15.2-03` divergence essentially creates a new implementation-defined behavior for temporal filtering on non-UTC data. Until the prose or implementation is aligned (e.g., by mandating contract-tier normalization), the query vocabulary is not fully decided by prose.

---

## 3. Advisory Findings

1. **MODULE BLOAT:** `src/ccf/graph/_writer.py` has reached ~1800 lines to accommodate all five backend transaction implementations. 
   - **Observation:** This strictly follows the "exactly one module" rule for write-shaped classes, but it represents a significant maintainability risk. Consider if the rule allows for a `ccf.graph._writer` *package* to maintain confinement while improving internal structure.

2. **MONGO STORAGE SIDE-EFFECTS:** The `mongo` adapter uses a "doubled-edge" storage strategy to satisfy undirected walk requirements.
   - **Observation:** This is an elegant technical solution for `$graphLookup` limitations, but it significantly increases the storage footprint. This substrate-specific trade-off should be explicitly noted in the operator performance documentation for transparency.

3. **TELEMETRY DISCIPLINE:** The `TelemetryMixin` approach is sound, but ensure that `last_survivor_set_sizes` remains strictly ephemeral and is never accidentally leaked into the content-hashed `ExecutionResult` that enters the Replay record.

---

## 4. Specific things checked and found sound

- **Single-Writer Invariant (INV-CH7-10):** Confirmed that no `*GraphWriter` or `*GraphTxn` classes exist outside of `src/ccf/graph/_writer.py`. All backend-specific mutation logic is correctly confined.
- **`allowed_entities` (Uniform Rule):** The three-valued semantics (`None` vs `set()` vs `populated`) correctly distinguish between "unconstrained" and "constrained-to-empty," preventing the "entity-resurrection" defect (GQ-15).
- **As-of Derivation (D-07):** The derivation of `as_of()` from the degenerate query is implemented cleanly with zero impact on the existing 15 call sites, fulfilling `SUBQ-07`.
- **Replay Pin Ordering:** The implementation correctly ensures query bytes are persisted to the `ArtifactStore` before the record append, preventing unresolvable pins.
- **Byte-Fidelity (D-IMPL-89):** Verification now correctly checks raw bytes against content-addresses before model validation, protecting against "silent" re-canonicalization of older records.
