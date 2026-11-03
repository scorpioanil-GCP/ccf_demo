# Artifacts and Artifact Stores

**Current SDK reference baseline:** `drcastillo/ccf_code/v1.0.2@5f85b389efe9e4b1de62e84a5af62ca4b2e12178`\
**Release:** `v1.0.2` @ `5f85b389efe9e4b1de62e84a5af62ca4b2e12178` (17 October 2026)

## Artifact vs store

A Control Plane artifact is a typed/versioned declaration.

An artifact store is the content-addressed persistence boundary used by Replay, retained child questions/contracts, HITL/workflow evidence, erasure records and related governed state.

## FileArtifactStore security

Current `FileArtifactStore` construction requires an explicit safe root and declared `write_kinds`.

Unsafe roots refuse through `InsecureArtifactStoreRoot`. Treat that as one control, not a claim that arbitrary filesystem threats disappear.

## Content addressing and read integrity

A content address names canonical bytes. A filename/address alone is not proof that the bytes currently stored under it are still the bytes that produced the address.

The bare store `get` contract does not make every backend an integrity oracle. **Readers that depend on integrity re-hash before use.**

Current main includes checks for, among other paths:

- Replay/record reads;
- locally dispatched child-record reads;
- retained child questions;
- erasure-door reads;
- MCP artifact client-lane reads;
- governed evidence reads.

`ChildRecordAltered` and related typed failures prevent altered bytes from reaching child admission.

## Writer/reference integrity

Writers that return or record a store-supplied `ArtifactRef` verify that the returned reference is exactly the reference of what they wrote.

Current named failures include:

- `ReplayReferenceMismatch`;
- `QueryPinReferenceMismatch`;
- `ChildQuestionReferenceMismatch`;
- `AdmissionRecordReferenceMismatch`;
- `WorkflowTraceReferenceMismatch`.

A mismatch is refused before the incorrect reference is delivered/recorded.

These checks verify the store's **answer**; read-side hash checks verify the bytes later retrieved. They are complementary.

## Artifact read/refusal types

Current artifact protocol also exposes typed read/resolution failures including:

- `ArtifactReadRefused`;
- `ArtifactResolutionRefused`;
- `ArtifactStoreUnauthenticated`.

Use the current generated [governance API](api/governance.md) for exact shapes.

## Governed record provenance

Current `ccf.replay.provenance` verifies whether a record was filed by the governed record writer.

Governed evidence additionally needs the deciding tenant's filing/naming evidence. Record-shaped client data is not promoted to governed evidence based on shape alone.

## Control Plane verified bytes

`ControlPlaneRegistry` now retains the write-verified canonical bytes beside its protected reconstruction.

Read doors:

1. verify record integrity;
2. parse the verified bytes through the artifact's own type;
3. verify parsed type/value/identity against the protected reconstruction;
4. return a fresh object.

`RegistryIntegrityFailure` means an existing registry entry's protected byte/reconstruction record is inconsistent; it is not reported as merely "missing."

## Governed erasure consult

Current main includes the erasure core and runtime door.

Erasure is whole-artifact read withholding backed by an immutable record, signed human approval and deployment-declared trust/index configuration. It does not destroy stored bytes or graph attributes.

Current erasure surfaces also include **subject match / door naming** contracts under `ccf.erasure.subject_match`. The artifact server exposes governed subject-match/naming tools used by erasure paths to determine what a remote artifact names without granting general read authority.

Erasure readers verify addressed bytes before judging the subject.

## Per-entity invalidation records

Invalidation boundaries are now stored per entity:

`{tenant}/ccf.entity-invalidation/{sha256(entity_uri)}`

Each entity has its own version history. The former whole-register artifact is no longer the current class model.

The `InvalidationRecordRegister` composition authority is confined to its tenant's invalidation-record class/prefix.

## MCP artifact lane

Artifact blob/presence/versioned-resolution paths distinguish governed evidence from the tenant's client lane. Current main adds governed-resolution support and typed read/refusal behavior rather than treating a tenant-unfiled address as a normal readable filing.

Do not bypass these decisions by calling a raw store directly when the caller expects governed evidence semantics.

## Exact current shapes

Use [Governance API](api/governance.md), [Replay API](api/replay.md), and [Runtime API](api/runtime.md).

## MCP erasure completion and upgrades

**Erasure completion over the MCP-backed artifact store is unsupported.** The
door reaches approval but cannot save that approval: the artifact server's
`put_artifact` tool supplies `ArtifactWrite`, while the approval's class requires
`ArtifactErase`. The operation refuses before the index append, so the address
remains served. This limitation predates the controlled delivery. Complete
erasures through an in-process store.

For the remote naming/judgment path, the door's authenticated bearer credential
needs action `artifact.subject.match` on resource `artifact.subject.match` for the
tenant, and the server's `ErasureTrust` must hold that tenant's authority and door
key. Without the grant, even ordinary client filings refuse. A tenant-unfiled
address, non-record governed evidence and a client twin of governed evidence
refuse `class-unverifiable`.

Upgrade the MCP artifact server first, or with all its clients. Keep erasure
requests disabled until the erasure door client is also upgraded. An older door
client against an upgraded server can admit a client twin of governed evidence;
a new door client against an older server refuses every address. Upgrade
`McpArtifactStore` clients too: older clients can report a governed-resolution
refusal as `McpServerUnreachable` rather than `ArtifactResolutionRefused`.

See [Migration and Delivery Limits](MIGRATION_AND_LIMITATIONS.md) and the
[SDK delivery notes](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/packaging/bank-controlled/RELEASE-NOTES.md).

## Retained replay evidence

A persistent `evidence_root` retains the default replay store, erasure index, question graphs and decision-to-graph mappings independently of temporary scratch. Retention is deployment-managed and consumes disk. The record store does not fsync, so an OS crash can leave an index entry whose record is unavailable. This durable file evidence does not make SK-01's in-memory grant/catalog state durable. See [Decision Replay](DECISION_REPLAY.md).

## Name-index concurrency in 1.0.2

`FileArtifactStore` serializes the full `.artifact-names.json` read/modify/write under `.artifact-names.lock` using exclusive blocking `flock`, and uses unique artifact staging files. Threads/processes on one host no longer overwrite each other's naming additions. A killed process releases the kernel lock; there is no wait timeout, and network filesystems without reliable locking are unsuitable.

This fixes the naming race, not general multi-application shared-root deployment qualification. Evidence retention and disk capacity remain operational responsibilities; record writes still lack an fsync guarantee. See the [release artifact-store contract](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/public/reference/protocols/artifact-store.md).
