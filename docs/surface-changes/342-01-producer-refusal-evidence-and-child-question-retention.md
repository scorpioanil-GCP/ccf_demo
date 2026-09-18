# 342-01 — the refusing producer's own evidence on the row; the historical child question retained

Applied 2026-09-18 under `D-IMPL-342` (Dave's implementation GO on the accepted two-limb design,
`docs/D-IMPL-342-DESIGN.md`). Two measurements opened it: `CP03C-F-05` — a child refused by its
own door reached the parent's record as `ineligible` with neither the producer's reason nor its
replay reference — and `CP14-F-35` — the row named a `child_question_address` the consumer's
store could not resolve, so the historical question could only be re-derived by re-running the
mapping. Dave's F-35 ruling: *"retain the exact identity-bearing child-question bytes in the
parent's artifact store, for admitted, refused, and unavailable outcomes. The retained bytes must
reproduce the recorded question identity. Neither the mapping nor the producer may be called to
recreate the historical question during replay."*

## What did NOT change, stated first

- **`question_identity`'s bytes.** The identity is now expressed as the content hash of
  `ChildQuestionIdentity`; the rendering (sorted keys, compact separators, `ensure_ascii=False`,
  the canonical UTC timestamp) is byte-identical to the pre-342 preimage, and
  `tests/products/test_d_impl_342_child_question_retention.py` holds the retained bytes to that
  preimage rendered independently. No `child_question_address` moves.
- **The admission verdict.** A child refused by its door still reads `ineligible` on
  `outcome_status` and `refusal_ref`; no producer reason enters `CHILD_REFUSAL_REASONS`.
- **What a caller sees at minimal disclosure.** The five new envelope fields cross as
  `"undisclosed"`, exactly like the existing producer members; `PERMITTED_AT_MINIMAL` is unchanged.
- **`replay()`'s product-only contract**, `replay_refusal()`'s outcome type, and every record
  written before this change: the new row members are hash-transparent at `None`, so stored rows
  reload to their addresses, and a row without a `child_question_ref` is left unheld by name.

## ccf.products.composite.ChildAdmissionRefusal

- Surface: ccf.products.composite.ChildAdmissionRefusal
- Public surface: true
- Change type: reshaped
- Before: the refused-door branch collapsed the producer's kind, reason and key into the prose `detail` and dropped the door's `replay_ref`; no member could carry them
- After: five optional, hash-transparent members — `producer_refusal_kind`, `producer_refusal_reason`, `producer_refusal_key`, `producer_replay_ref` (Limb A) and `question_ref` (Limb B); `envelope_for` renders them into every composite refusal's `fields`, so a composite refusal recorded after 342 hashes differently from the same determination before it, while an older block still rehydrates. Every mint site carries what it has: the refused-door branch the four Limb A members and the reference; the unreachable and claims-refused branches the reference; the gate's own `refuse` closure in `admit()` (a served answer rejected inside the gate) the reference and the door's replay reference for the answer it served — the closure the candidate's review found minting rows without either
- Why: D-IMPL-342 — a parent's record must say why the child's own door refused and where the producer's record is, without disclosing more than the door did
- Migration: none for callers; a test pinning the exact `fields` key set of a composite refusal grows by five (`tests/products/test_refusal_envelope.py` did)

## ccf.replay.record.ChildResolution

- Surface: ccf.replay.record.ChildResolution
- Public surface: true
- Change type: reshaped
- Before: a refused-door row carried `refusal_ref: ineligible` and the producer registration members only; `child_replay_ref` was written on admitted and gate-rejected rows, never on a refused one; nothing referenced a retained question
- After: `producer_refusal_kind`, `producer_refusal_reason`, `producer_refusal_key` and `child_question_ref`, all hash-transparent at `None`; `child_replay_ref` is written on the refused-door branch too; a validator refuses producer refusal evidence on any row whose door did not refuse, and a question reference without a question address
- Why: D-IMPL-342 — the row is where an examiner reads the child's outcome; evidence the door released belongs beside the verdict, and a retained artifact is referenced from the row rather than inferred from an address
- Migration: none; records written before this change reload to their stored addresses

## ccf.skills.dispatch.ChildQuestionIdentity

- Surface: ccf.skills.dispatch.ChildQuestionIdentity
- Public surface: true
- Change type: added
- Before: absent — the identity's five-key preimage existed only as a transient `json.dumps` inside `question_identity`
- After: a five-member contract (`asked_at`, `freshness`, `intent`, `request`, `subject`) whose canonical bytes ARE the preimage, so `content_hash(instance) == question_identity(...)`; the artifact a parent retains under `CHILD_QUESTION_CLASS`
- Why: D-IMPL-342 / CP14-F-35 — the retained bytes must reproduce the recorded identity, and a `ProductQuestion` (which carries `parameters` and names the request `request_json`) does not hash to it
- Migration: none

## ccf.skills.dispatch.ProductQuestion

- Surface: ccf.skills.dispatch.ProductQuestion
- Public surface: true
- Change type: reshaped
- Before: `address` only
- After: `identity_artifact()` returns the `ChildQuestionIdentity` this question hashes to
- Why: D-IMPL-342 — one place derives the retained artifact from the question sent
- Migration: none

## ccf.skills.dispatch.question_identity

- Surface: ccf.skills.dispatch.question_identity
- Public surface: true
- Change type: behavior
- Before: a private `json.dumps` rendering hashed with `hashlib`
- After: `content_hash(ChildQuestionIdentity(...))` — the SDK's one canonical form over the same five keys; the bytes and every address are unchanged for every aware `asked_at`. One input the old rendering accepted is now refused: a naive `asked_at`, which the old `astimezone(UTC)` hashed through the host's zone (the same question minted a different identity on two hosts); `ChildQuestionIdentity` refuses it (`D-IMPL-38`). Every caller in the tree passes an aware instant; `ProductQuestion` already required one
- Why: D-IMPL-342 R-3 — one rendering in the SDK instead of two that happen to agree; the naive refusal is that form's own rule
- Migration: none

## ccf.products.composite.CHILD_QUESTION_CLASS

- Surface: ccf.products.composite.CHILD_QUESTION_CLASS
- Public surface: true
- Change type: added
- Before: absent — nothing retained a child question
- After: `"ccf.child-question"`, the artifact class under which `QuestionBoundChildResolver` files each question's identity bytes on the parent's own store, named by the address, BEFORE the producer is called; a store that files them at another address is refused (`RuntimeError`), and a store that cannot file raises before any dispatch
- Why: D-IMPL-342 / CP14-F-35 — admitted, refused and unavailable outcomes alike must leave the exact historical question behind, which only the pre-dispatch ordering makes structural
- Migration: none for the paved road; a custom child resolver that wants its rows to reference retained questions files under this class and passes the store's URI through `invocation_from_dispatch(question_ref=...)` or the refusal value

## ccf.products.composite.ChildInvocation

- Surface: ccf.products.composite.ChildInvocation
- Public surface: true
- Change type: reshaped
- Before: `question_address` only
- After: `question_ref` (constructor keyword and read-only property), the parent store's URI for the retained question on an `mcp-product` child
- Why: D-IMPL-342 — the admitted row copies it from the invocation exactly as it copies the question address
- Migration: none; the constructor is token-minted and the keyword defaults to `None`

## ccf.products.composite.invocation_from_dispatch

- Surface: ccf.products.composite.invocation_from_dispatch
- Public surface: true
- Change type: reshaped
- Before: `(producer, dispatched, *, touched_entities=None)`
- After: `question_ref: str | None = None` added; a reference supplied for a non-`mcp-product` acquisition is refused as `ProvenanceForgeryError`, as `touched_entities` is for a remote one
- Why: D-IMPL-342 — only an mcp-product acquisition mints a question, so only it can have retained one
- Migration: none

## ccf.products.composite.CompositeAdmissionGate

- Surface: ccf.products.composite.CompositeAdmissionGate
- Public surface: true
- Change type: reshaped
- Before: the consumer tenant was held privately
- After: a read-only `tenant_id` property
- Why: D-IMPL-342 — the question-bound resolver files under the tenant the gate admits for, and reads it rather than being handed a second copy
- Migration: none

## ccf.replay.engine.retained_child_question

- Surface: ccf.replay.engine.retained_child_question
- Public surface: true
- Change type: added
- Before: absent — nothing in the engine read `child_question_address`
- After: the audit read: resolves the row's `child_question_ref`, requires it to resolve to the row's address, reads the bytes, holds their sha256 to the address, rehydrates a `ChildQuestionIdentity` and holds its content hash to the same address; `ReplayUnresolvable` by name for a row with no reference ("not retained") or missing bytes, `ReplayDivergence` for other bytes or a reference to another question; calls no mapping, no producer
- Why: D-IMPL-342 / CP14-F-35 — the historical question is resolved from the parent's store and from nowhere else
- Migration: none

## ccf.replay.engine.replay

- Surface: ccf.replay.engine.replay
- Public surface: true
- Change type: behavior
- Before: no row's question was held
- After: after the admitted children are reconstructed and before the plan is re-derived, every row carrying a `child_question_ref` is held to its retained bytes through `retained_child_question`; rows without one are unheld by name; the return type and every other check are unchanged
- Why: D-IMPL-342 R-4 — replay holds what the record references, and a pre-342 record replays as it did
- Migration: none

## ccf.replay.engine.replay_refusal

- Surface: ccf.replay.engine.replay_refusal
- Public surface: true
- Change type: behavior
- Before: no row's question was held
- After: the same hold as `replay()`, on both the pre-projection and the post-projection path, after `_children_of`
- Why: D-IMPL-342 R-4
- Migration: none
