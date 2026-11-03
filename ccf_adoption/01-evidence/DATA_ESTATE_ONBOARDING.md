# Data-estate onboarding decision

## Preferred path

For the real CCF Hello World / assembler experience, use the data estate produced by `drcastillo/ccf_dataprep` rather than inventing a second miniature estate solely for documentation.

The reason is architectural and pedagogical: the examples are intended to teach the actual CCF shape — heterogeneous stores, provenance, engineered limitations, graph + relational composition, temporal state, policy, and replay. Replacing that with a SQLite-only example would remove many of the properties the learner is supposed to understand.

## Existing restore capability

`ccf_dataprep` already contains a portable restore system under `portable/`:

- `portable/bundle/README.md`
- `portable/bundle/INSTALL-macos.md`
- `portable/bundle/INSTALL-ubuntu.md`
- `portable/restore/restore_all.sh`
- `portable/verify_install.py`

The bundle is designed to restore the complete demonstration estate onto a clean laptop without access to the original servers. Its published restore sequence is Fluree → Postgres → MongoDB → SQLite → Neo4j, followed by the verifier.

The adoption portal should not duplicate this machinery. It should provide a concise Data Estate Setup page that explains why the estate exists, points to the pinned Dataprep restore instructions, and then returns the learner to the relevant CCF example once verification passes.

## Data Estate Readiness status

**READY — operationally confirmed by the Dataprep project on 2026-09-13.**

The Dataprep project has confirmed that `portable` is good to use as the restore path for the adoption experience. That satisfies the project-level readiness decision to proceed with the Dataprep estate as the canonical Hello World / assembler prerequisite.

There is an evidence-version nuance that must remain visible. The GitHub `ccf_dataprep/main` ref currently remains pinned at `fcf7dddf79c7f443300d745e90bf39510ef12ab7`; that commit records the earlier restore-landmark maintenance concern. The newer operational readiness confirmation has not produced a newer Git commit at the time this adoption record was updated. Therefore:

1. the **onboarding decision is READY** based on the Dataprep project's operational confirmation;
2. `fcf7dddf79c7f443300d745e90bf39510ef12ab7` remains the pinned repository evidence snapshot until a newer source commit exists;
3. adoption documentation must point to the Dataprep portable instructions rather than copy restore machinery into `ccf_adoption`;
4. before public release, the exact portable bundle/snapshot used for walkthrough validation should be recorded alongside the adoption release so a learner can reproduce the environment that the examples expect.

The earlier landmark issue remains useful historical evidence about why portable estate snapshots must be treated as versioned artifacts rather than assumed to equal a continuously changing live estate.

## Learning-path implication

The portal should separate two ideas:

### Consumer quick start

A learner who only wants to understand how an agent/application consumes a Context Product should not be forced to understand estate construction first. We can use an already-running/restored product endpoint or a small seeded fixture for this path. Its lesson is the consumer contract: ask, receive a governed `Result`, inspect payload/debt/lineage/refusal.

This path may use a lightweight local fixture if necessary, but it must be labeled as a **consumer smoke test**, not the canonical CCF implementation example.

### Assembler / Hello Context Product

The canonical assembler path uses the restored `ccf_dataprep` estate and then runs the actual SDK example. This preserves the real source boundaries, data limitations, engineered scenarios, and multi-store composition that the Financial Services examples depend upon.

The intended learner flow is:

1. obtain the Dataprep portable bundle;
2. follow the platform-specific install guide;
3. run the single restore path;
4. run the Dataprep verifier;
5. only after verification passes, proceed to `Hello, Context Product` and the assembler tutorials.

## Decision posture

Default: **use the Dataprep estate.**

Do not build a parallel SQLite-only Context Product unless onboarding friction proves that a small consumer-only smoke test is necessary. If such a fixture is added, it must remain deliberately narrower than the assembler tutorial and must not become the source of truth for CCF architecture or Financial Services examples.
