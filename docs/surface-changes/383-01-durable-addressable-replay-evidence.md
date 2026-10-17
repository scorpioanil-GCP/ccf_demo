# 383-01 (D-IMPL-383, 2026-10-15) — durable, addressable replay evidence for per-question graphs

`D-IMPL-383`, Dave, 2026-10-15 20:27 MST (the reviewer's six instructions) and 22:05 (*"20:27 rules +
front-end"*). The bank asked how decision replay works when each question's SQLite graph is destroyed;
the delivered launcher deleted every graph and the replay store on a normal stop, and nothing mapped a
decision to its graph. The evidence root is now the paved road's `scratch`: a persistent scratch keeps
every decision replayable after a restart, a temporary one keeps today's behavior. The five-dimension
record, the fingerprint and the low-level engine calls are unchanged.

**Not claimed:** the decision record's store does not `fsync`, so after an operating-system crash a
published mapping can name a record that did not survive (lookup reports it unavailable); retained
evidence consumes disk and nothing deletes it.

## ccf.replay.evidence.ReplayEvidenceIndex

- Surface: ccf.replay.evidence.ReplayEvidenceIndex
- Public surface: true
- Change type: added
- Before: no mapping from a decision to the graph it read; replay callers located a graph themselves.
- After: a file index under the evidence root keyed by the decision's record address (`decisions/<address>.json`), with a `pending/<graph>.json` marker as the explicit incomplete state; `entry(address)`, `decisions(since=, until=, involving=)`, `incomplete()`, `graph_path(entry)`; writes are staged, `fsync`-ed and renamed.
- Why: `D-IMPL-383` instructions 2 and 3, and the bank front-end's listing by time and company.
- Migration: none. Reached as `OpenedProduct.evidence`.

## ccf.replay.evidence.EvidenceEntry

- Surface: ccf.replay.evidence.EvidenceEntry
- Public surface: true
- Change type: added
- Before: no such contract.
- After: one decision's published mapping: record address, tenant, served or refused, refusal reason, product class and lane, subject, request parameters, `asked_at`, `decided_at`, the graph relative to the evidence root, `graph_required` (false, explicitly, for a refusal before any graph) and the graph's sha256 when its question closed it.
- Why: `D-IMPL-383` instructions 2 and 5.
- Migration: none.

## ccf.replay.evidence.PendingEvidence

- Surface: ccf.replay.evidence.PendingEvidence
- Public surface: true
- Change type: added
- Before: no such contract.
- After: the incomplete-state marker written before a question's graph is minted and removed only after its mapping is durable.
- Why: `D-IMPL-383` instruction 3.
- Migration: none.

## ccf.replay.evidence.ReplayEvidenceUnavailable

- Surface: ccf.replay.evidence.ReplayEvidenceUnavailable
- Public surface: true
- Change type: added
- Before: no such error.
- After: a `ReplayError` carrying `record_address` and, when one file is missing, its `path`; raised for no mapping (unknown, or incomplete), a missing graph, or a record the store no longer holds.
- Why: `D-IMPL-383` instruction 4.
- Migration: none.

## ccf.replay.evidence.ReplayEvidenceAltered

- Surface: ccf.replay.evidence.ReplayEvidenceAltered
- Public surface: true
- Change type: added
- Before: no such error.
- After: a `ReplayDivergence` raised when a retained graph exists but its bytes are not those its question closed.
- Why: `D-IMPL-383` instruction 4 — corruption is never collapsed into "missing".
- Migration: none; a caller that treats `ReplayDivergence` as a finding treats this identically.

## ccf.replay.evidence.EVIDENCE_SCHEMA_VERSION

- Surface: ccf.replay.evidence.EVIDENCE_SCHEMA_VERSION
- Public surface: true
- Change type: added
- Before: no such constant.
- After: `1`, the index document schema.
- Why: `D-IMPL-383`.
- Migration: none.

## ccf.replay.evidence.file_sha256

- Surface: ccf.replay.evidence.file_sha256
- Public surface: true
- Change type: added
- Before: no such function.
- After: `file_sha256(path) -> str`, the chunked sha256 of a file.
- Why: `D-IMPL-383` — the graph's bytes are held to what its question closed.
- Migration: none.

## ccf.replay.evidence.require_record_address

- Surface: ccf.replay.evidence.require_record_address
- Public surface: true
- Change type: added
- Before: no such function.
- After: returns a content address unchanged or raises `ValueError`, before any index path is built from it.
- Why: `D-IMPL-383` — lookup never reaches the filesystem through a non-address.
- Migration: none.

## ccf.products.product.OpenedProduct

- Surface: ccf.products.product.OpenedProduct
- Public surface: true
- Change type: behavior
- Before: `answer` and `resolve` returned the governed outcome with no record of which graph it read; replay needed the caller to boot the right graph and supply the reader.
- After: every decision publishes its evidence mapping under `scratch` before it returns (a pending marker first, the mapping after the graph is closed); a failure to publish propagates rather than returning an outcome as durably replayable. New: `evidence` (the decision's `ReplayEvidenceIndex`) and `replay_decision(record_address)`, which resolves the mapping, checks the graph is present and byte-identical, boots it read-only and hands the existing engine the reader and a `RecordedEnvironment`; an erased record is handed to the engine, which discloses it.
- Why: `D-IMPL-383`.
- Migration: none for existing callers. `scratch` now also holds `<store_dirname>-evidence-index/`; a deployment that wants replay to survive a restart passes a persistent `scratch`.

## Fluree server pin (CI)

- Surface: Fluree server pin (CI)
- Public surface: false
- Change type: behavior
- Before: `ci.yml` pinned `fluree/server:4.1.4`; the drift job tracked the floating `4.1`.
- After: `ci.yml` pins `4.2.4`; the drift job tracks `4.2`. `4.2.4` refuses a relationship-property read over an undirected variable-length path with `400 err:parse/CypherLower` where `4.1.4` answered `[null, null]`; the SDK never issues that read.
- Why: `D-IMPL-384`, Dave, 2026-10-15 21:54.
- Migration: run the Fluree leg and any local Fluree container on `fluree/server:4.2.4`.
