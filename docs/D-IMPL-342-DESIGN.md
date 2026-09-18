# D-IMPL-342 — design: the refusing producer's own evidence, and the historical child question, retained on the parent's store

**Status: IMPLEMENTED (2026-09-18) on `d-impl-342-evidence`, awaiting the review ruling;
not merged. §0–§7 are the design as accepted; §8 records what was built, where it
differs, what the candidate's review found, and every measurement.** Design baseline:
`main @ 61d2af87` (the verified post-`D-GATE-304` baseline), branch `d-impl-342-design`. The decisions of record are `docs/DECISIONS.md`
`D-IMPL-342` (OPEN, 2026-09-15, from `CP03C-F-05`) and the `CP14-F-35` ruling recorded
under it (2026-09-18). This document does what the 2026-09-18 instruction asked and
nothing more: two limbs, each with its failing path on the baseline, the exact fields and
store state today, the owning layer, the minimal change, the write timing, the read path,
compatibility, the persist-fail posture, controls, sabotages and migration — and the
rulings that are actually Dave's.

Every citation below is a `file::symbol` that resolves on `61d2af87`; a method is named
in prose beside the class that owns it.

## 0 · The two limbs, and what keeps them apart

| | **342-A — refused-child producer evidence** | **342-B (`F-35`) — the identity-bearing question bytes** |
|---|---|---|
| Obligation | When a child's own door refuses, the parent-side row carries the producer's refusal **kind**, **reason**, **key** and **replay reference**, as the door disclosed them. | The exact bytes whose `sha256` is `child_question_address` are on the parent's artifact store at that address, for admitted, refused and unavailable outcomes, referenced from the row. |
| Fails today because | `_admit` collapses the producer's `RefusalEnvelope` into a prose `detail` and drops the door's `replay_ref`; the row records the admission verdict (`ineligible`) only. | `question_identity` hashes a rendering that is never written anywhere; the store holds nothing at `child_question_address`; the proofs recompute it by re-running the mapping. |
| Owning layer | Admission (`src/ccf/products/child_resolver.py::GrantBoundChildResolver`, `_admit`) and the row writer (`src/ccf/products/composite.py::resolve_child_outcomes`). | The question-minting seam (`src/ccf/products/child_resolver.py::QuestionBoundChildResolver`, `resolve_for`) and the replay engine's retained-bytes readers. |
| Store writes | **None.** Row members only. | **One artifact per distinct question**, filed before the producer is called. |
| Producer semantics | Unchanged. Nothing new is disclosed; nothing is invented; the door is untouched. | Unchanged. The producer is not consulted at replay. |
| Distinct from | `D-IMPL-304` (a producer-side refusal that escaped as a fault — closed), `D-IMPL-344` (admitted **contracts** retained on refusal), `D-IMPL-341` (expiry anchor). | `D-IMPL-344` (which retains the child's *answer*, not the *question*); the deployment's question mapping (which is configuration, not evidence). |

The two limbs share one row type and one refusal value, and nothing else: A adds
members that are read straight off the row; B adds one artifact class, one row
reference and one replay hold. Either can land, be sabotaged and be reviewed without
the other. They are presented in one document because Dave asked for one design, not
because they are one change.

## 1 · Limb 342-A — the refusing producer's own evidence on the parent-side row

### 1.1 The failing path on `61d2af87`, object by object

1. The producer's door refuses. `src/ccf/products/door.py::DoorOutcome` on that branch
   carries `refusal=<RefusalEnvelope>` (its `kind`, `reason`, `key`, `detail`, `fields`
   and `disclosure` at the producer's own disclosure level), `product_json=None`,
   `content_address=None`, and `replay_ref=_replay_ref_of(refusal)` — the producer's
   replay-record URI, or `None` at the no-record sentinel
   (`src/ccf/products/door.py::_replay_ref_of`). The producer assertion and the echoed
   request ride beside it exactly as on a served outcome.
2. `src/ccf/skills/dispatch.py::dispatch_skill` returns a
   `src/ccf/skills/dispatch.py::McpProductInvocation` whose `contents` is that door
   outcome's text and whose `question_address` is the question's identity.
3. `_admit` on `src/ccf/products/child_resolver.py::GrantBoundChildResolver` decodes the
   outcome, and `hold_producer_claims` on
   `src/ccf/products/composite.py::CompositeAdmissionGate` holds the producer assertion,
   the echo **and the replay reference's tenant** against the registration — so on this
   branch the door's `replay_ref` has already passed the tenant claim before it is
   dropped. Then the refusal is collapsed: the kind, reason and key become the prose
   `"the child's own door refused: {kind} ({reason at key}: {detail})"` on a
   `src/ccf/products/composite.py::ChildAdmissionRefusal` with `reason="ineligible"`,
   and `asked.replay_ref` is not passed at all — the refusal value has no member that
   could carry any of the four.
4. `src/ccf/products/composite.py::resolve_child_outcomes` writes the row from that
   value: `outcome_status="ineligible"`, `refusal_ref=outcome.reason` (`"ineligible"`,
   the admission verdict), the four producer-registration members, the question
   address — and no `child_replay_ref`, no producer kind, reason or key.
5. **The asymmetry that shows this is an omission, not a posture.** The neighboring
   branch in the same function — a child that was *served* and then rejected at the
   gate (`question-mismatch`, `as-of-mismatch`, …) — writes
   `child_replay_ref=outcome.candidate.child_replay_ref`. A rejected served answer
   keeps the producer's reference; a refused answer loses it.
6. What the record does hold: dimension 5's `assembly_refusal` block carries the
   **first blocking** child's prose (kind, reason, key and detail, as one string).
   Every other withheld row carries `ineligible` alone. The shipped gap is pinned by
   name in
   `tests/examples/test_cp_14_first_slice.py::test_the_governed_question_refuses_on_the_withheld_spread_with_five_rows_persisted`
   (*"D-IMPL-342 / F-05, honestly: no producer replay reference on the refused row"*),
   `tests/examples/test_cp_14_fourth_slice.py::test_the_governed_question_withholds_where_producers_withhold_and_refuses_the_composite`
   and
   `tests/products/test_paved_consumer.py::test_a_floor_above_the_served_lane_is_refused_at_the_door_with_both_lanes_retained`
   — three assertions written to go red when this is fixed.

The unavailable branch (`src/ccf/skills/dispatch.py::McpProductFailure`, or a malformed
door answer — `src/ccf/products/child_resolver.py::MalformedDoorAnswer`) refuses
`producer-unavailable` with the question address and no producer refusal, because there
is none: nothing was disclosed. That branch is correct today and this limb does not touch
it.

### 1.2 The record and refusal fields today

`src/ccf/replay/record.py::ChildResolution`, the members this limb reads or writes:

| member | posture (`HASH_TRANSPARENT_KEY`) | written on a refused-door row today |
|---|---|---|
| `outcome_status` | required | `"ineligible"` |
| `refusal_ref` | `False` (generation boundary) | `"ineligible"` — the admission verdict, by design |
| `producer_id`, `producer_tenant`, `producer_registration_address`, `producer_server` | `True` (`D-IMPL-340`) | from the registration |
| `child_question_address` | `True` | the identity |
| `child_replay_ref` | `True`; docstring: *"as its door reported it — retained as the producer's claim, this fabric never resolves it"* | **`None`** (set on admitted and gate-rejected rows only) |

`src/ccf/products/composite.py::ChildAdmissionRefusal`: `product_class`, `reason`
(closed vocabulary `src/ccf/products/composite.py::CHILD_REFUSAL_REASONS`),
`reported_content_address`, `verified_content_address` (both `False`), then the four
producer members and `question_address` (all `True`). No member for the producer's own
refusal.

### 1.3 Ownership

The producer's envelope is in hand in exactly one place — admission — and rows are
written in exactly one place — `resolve_child_outcomes` — and the only object that
travels between them is the `ChildAdmissionRefusal` value. The layer that owns the
evidence is therefore the **consumer's admission**, and the change is confined to
carrying what the door already released across that one value onto the row. The
producer, its door, its disclosure decision and the dispatch module are not touched;
what the producer chose to disclose is what exists to be carried, and nothing more.

### 1.4 The minimal change

**Contract (`D-IMPL-243` posture `True` on every new member — see §1.7 for why):**

- `ChildAdmissionRefusal` gains four optional members, `None` by default:
  `producer_refusal_kind`, `producer_refusal_reason`, `producer_refusal_key`,
  `producer_replay_ref`.
- `ChildResolution` gains three: `producer_refusal_kind`, `producer_refusal_reason`,
  `producer_refusal_key`. The existing `child_replay_ref` is written on the refused-door
  branch too; its docstring drops "admitted" and says *on every row whose door reported
  one*.

**Code (two sites):**

- `_admit`, refused-door branch: pass `asked.refusal.kind`, `.reason`, `.key` and
  `asked.replay_ref` on the refusal value. `reason` stays `"ineligible"`: the
  admission verdict is unchanged, the closed vocabulary is not widened, and **no
  producer reason is ever mapped into `outcome_status`** — a producer's
  `tolerance-exceeded` is the producer's word about its own product, not a
  `src/ccf/products/composite.py::_status_for` token. The prose `detail` stays as it
  is, so dimension 5's first-blocking-child text is byte-for-byte what it was.
- `resolve_child_outcomes`, the `ChildAdmissionRefusal` branch: copy the four onto the
  row (`child_replay_ref=outcome.producer_replay_ref` and the three scalars).

**Row members, not a referenced artifact — Dave's question, answered:**

1. Kind, reason and key are **identity tokens**, not prose: a refusal kind from
   `src/ccf/products/refusal.py::REFUSAL_KINDS`, a reason from a closed vocabulary or
   a declared gate id, a parameter key. They belong on the row for the same reason
   `refusal_ref` does — an examiner reads them without resolving anything.
2. **The referenced governed artifact already exists, and the row already has the
   slot for its reference.** The producer's refusal is a recorded determination on
   the producer's store (that is what `D-IMPL-304` just made unconditional at the
   door), and `child_replay_ref` is exactly the reference to it, retained as the
   producer's claim and never resolved by this fabric. Retaining the producer's whole
   disclosed envelope on the consumer's store (reading 2 of the OPEN entry) would make
   the consumer's store a partial copy of the producer's — the thing the replay
   reference exists so nobody has to do.
3. **`detail` stays off the row.** It is prose at the producer's disclosure level and
   it is already on dimension 5 for the first blocking child. If per-row detail is
   wanted later, the honest form is the envelope-as-artifact of reading 2, as its own
   ruling; putting prose on every row is neither.

**What reaches the caller: nothing new.**
`src/ccf/products/disclosure.py::PERMITTED_AT_MINIMAL` permits only `product_class`
of a `composite-child-refusal` at minimal, so the four new members never cross the
served envelope; `CMC-G26` ("the disclosed envelope stays minimal") holds by
construction.

**What changes on dimension 5, stated because it is a byte change:**
`src/ccf/products/refusal.py::envelope_for` renders **every** declared member of a
refusal contract into the envelope's `fields` — `"null"` included. So every composite
refusal recorded after this limb lands carries four more keys in its `assembly_refusal`
block, and its record address differs from what the same determination would have
hashed to on `61d2af87`. Records already written are untouched bytes;
`src/ccf/replay/engine.py::_rehydrate_refusal_block` re-canonicalizes an old block to
itself and the old block has no new keys, so it still holds.
`tests/products/test_refusal_envelope.py::test_envelope_for_composite_child_refusal`
pins the exact key set and grows by four on purpose. This is **R-1**.

### 1.5 Write timing

At admission, in memory, in the same instant every other producer member is written to
the row. No store write, no I/O, no new failure mode.

### 1.6 Replay and audit read path

- **Direct:** `record.content_generation_path.child_resolutions[i]` — the three scalars
  and `child_replay_ref` are read off the row.
- **`src/ccf/replay/engine.py::replay_refusal`** is unchanged in what it keys on:
  `src/ccf/replay/engine.py::_hold_refusal_to_rows` holds the refusal to
  `outcome_status` / `refusal_ref`, both unchanged. One small positive hold is
  proposed, in that helper: a row carrying `producer_refusal_reason` must read
  `outcome_status == "ineligible"` — producer refusal evidence appears only where the
  producer's own door refused (a gate-rejected served candidate carries
  `child_replay_ref` and **no** producer refusal, which is what makes the two rows
  distinguishable by evidence rather than by narrative).
- **`child_replay_ref` on a refused row is a claim, not a read.** The consumer never
  resolves it; the posture of the admitted row's docstring extends unchanged.

### 1.7 Backward compatibility

Additive on both types. Every new member is `True`-transparent at `None`, so a row
or refusal stored before this limb re-canonicalizes to its stored bytes on reload —
the `D-IMPL-340` precedent for the producer members, and the only posture under which
existing composite records keep their addresses. `False` was considered and refused:
it would make every stored composite record re-hash to a different address when
loaded, which the replay prologue holds against.

The cost of `True`, said plainly: on a refused-door row written after 342, `None`
means *the door disclosed no such member*; on a row written before 342, `None` means
*not retained*. Bytes alone cannot tell them apart. The row's `producer_id`,
`outcome_status` and `child_question_address` say the producer was reached, and the
record's own dimension-5 block carries the four keys after 342 and not before — so an
examiner can tell a pre-342 record from a post-342 one from the record, just not from
the row in isolation. Same acceptance `D-IMPL-340` made.

The three assertions in §1.1 (6) flip to positive proofs. Under `D-IMPL-261` the
example-level tests convert **after** the SDK lands, as a separate validation step,
never inside the 342 change; the two `tests/products` assertions convert with it.

### 1.8 Persist-fail posture

Not applicable: no persistence in this limb. The record write is the existing one and
its failure semantics are unchanged.

### 1.9 Controls — success, refusal, unavailable, and the two look-alikes

SDK-level, no estate, one fixture producer in another process reached through the
paved consumer (the shape `tests/products/test_paved_consumer.py` already drives):

| control | scenario | holds |
|---|---|---|
| C-A1 | the door refuses (`tolerance-exceeded` or a declared gate) | row `ineligible`/`ineligible`; `producer_refusal_kind/reason/key` **equal the values decoded independently from the raw door-outcome text** the fixture door returned (the oracle is the `DoorOutcome`, not `_admit`); `child_replay_ref` equals the door's `replay_ref` and its tenant equals `producer_tenant` |
| C-A2 | served and admitted | the three scalars `None`; `child_replay_ref` as today |
| C-A3 | unavailable (`McpProductFailure`), and separately a malformed answer | `producer-unavailable`; scalars `None`; `child_replay_ref None` |
| C-A4 | served, rejected at the gate (`question-mismatch`) | `child_replay_ref` set, scalars `None` — distinct from C-A1 by evidence |
| C-A5 | disclosure | the served envelope's `fields` == `{product_class}`; the record's block carries the four keys |
| C-A6 | vocabulary | `_status_for` never sees a producer reason; a producer reason passed as `reason=` raises |
| C-A7 | rehydration | a refusal block written without the keys rehydrates and re-canonicalizes to itself |
| C-A8 | replay | `replay_refusal` on the C-A1 record succeeds; a hand-built row with `producer_refusal_reason` on an `admitted` row is refused by the §1.6 hold |

Estate-level, after the SDK lands: the first and fourth CP-14 slices assert
`tolerance-exceeded` **on the spread row itself**, and each other withheld row carries
its own producer's reason — the claim `CP14-F-35`'s close narrowed to "the first
blocking producer only" widens to every refused row.

### 1.10 Sabotages (run by hand, restored by copy, verified by `cmp`)

| sabotage | expected red | expected green |
|---|---|---|
| S-A1 drop `producer_replay_ref=asked.replay_ref` in `_admit` | C-A1 (reference) | C-A2, C-A3, C-A4 |
| S-A2 drop the three scalar assignments in `_admit` | C-A1 (reason) | C-A4 |
| S-A3 keep the refusal members, drop the row copy in `resolve_child_outcomes` | C-A1 | C-A5's record-block assertion — proves refusal-value and row are held separately |
| S-A4 map the producer reason into `outcome_status` (the wrong repair) | C-A1, C-A6 | — |
| S-A5 mark the new members `False` | C-A7-adjacent reload control (a stored pre-342 composite record re-hashes to a different address) | C-A1 |

### 1.11 Migration and versioning

None. No record is regenerated; the record schema exports gain three optional members
(`make schema-headers`); `CP03C-F-05` and `CP14-F-35`'s reason clause move to
`FIXED-342` at the separate validation step.

## 2 · Limb 342-B (`F-35`) — the identity-bearing question bytes on the parent's store

The ruling, verbatim (`docs/DECISIONS.md`, 2026-09-18): *"retain the exact
identity-bearing child-question bytes in the parent's artifact store, for admitted,
refused, and unavailable outcomes. The retained bytes must reproduce the recorded
question identity. Neither the mapping nor the producer may be called to recreate the
historical question during replay."*

### 2.1 The failing path on `61d2af87`

1. `resolve_for` on `src/ccf/products/child_resolver.py::QuestionBoundChildResolver`
   asks the deployment mapping for a `src/ccf/products/child_resolver.py::ChildQuestion`
   (subject, intent, freshness, parameters — the four the producer takes from the
   question), builds a `src/ccf/products/door.py::WireRequest`, and mints a
   `src/ccf/skills/dispatch.py::ProductQuestion` with
   `request_json = canonical_bytes(wire)` and the composite's `asked_at`.
2. `dispatch_skill` stamps `question_address = question.address` on both the
   `McpProductInvocation` and the `McpProductFailure`, where `address` is
   `src/ccf/skills/dispatch.py::question_identity` over
   `(request_json, subject, intent, freshness, asked_at)`.
3. The address flows to the row — through `ChildAdmissionRefusal.question_address` on
   every refused branch, and through `src/ccf/products/composite.py::ChildInvocation`
   (minted by `src/ccf/products/composite.py::invocation_from_dispatch`) into
   `src/ccf/products/composite.py::_row_for_admitted` on the admitted one.
4. **The bytes hashed in step 2 are never written.** `question_identity` renders,
   hashes and returns the hex; the `ProductQuestion` is dropped after dispatch; the
   store has nothing at `child_question_address`. `src/ccf/replay/engine.py::_children_of`
   and `src/ccf/replay/engine.py::_reconstruct_child_contracts` resolve admitted
   **contracts** by `child_content_address`; nothing in the engine reads
   `child_question_address` at all.
5. What the proofs do instead:
   `tests/products/test_paved_consumer.py::test_the_mapping_is_the_authority_on_the_subject_and_the_row_records_what_was_asked`
   and
   `tests/examples/test_cp_14_fourth_slice.py::test_the_covenant_question_names_the_obligors_own_evidence_nodes`
   recompute the identity by re-running the mapping and `question_identity` — the
   re-derivation from current configuration and data that the ruling forbids at replay.

### 2.2 Store and fields today

- Row: `child_question_address` (`True`), nothing referencing an artifact.
- Values carrying `question_address`: `ChildAdmissionRefusal`, `ChildInvocation`,
  `McpProductInvocation`, `McpProductFailure`.
- Store: one child artifact class exists —
  `src/ccf/products/composite.py::ADMITTED_CHILD_CONTRACT_CLASS`
  (`ccf.admitted-child-contract`), filed by `_retain_child_contracts` on
  `src/ccf/products/resolver.py::GovernedResolver` with `name=address` and
  `filed.content_address == address` asserted (`D-IMPL-344`). No question class.
- The store handle: `src/ccf/products/product.py::open_product` constructs the
  question-bound resolver with `artifact_store=store` — the parent's own store — and
  today that class only **reads** it (`_touched_entities` resolves a local child's
  record).

### 2.3 The canonical serialized representation — and the proof it is the same bytes

`question_identity` hashes exactly this, UTF-8:

```
json.dumps({"asked_at": asked_at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "freshness": freshness, "intent": intent,
            "request": request_json, "subject": subject},
           sort_keys=True, separators=(",", ":"), ensure_ascii=False)
```

`src/ccf/contracts/canonical.py::canonical_bytes` renders a `CCFContract` field by
field with sorted keys, the same separators, `ensure_ascii=False`, and a `datetime` as
the same fixed-width UTC format after `astimezone(UTC)`; the contract base adds no
members (`extra="forbid"`, frozen). So a contract whose five member **names are the
identity's five keys** —

```
class ChildQuestionIdentity(CCFContract):
    asked_at: datetime
    freshness: str
    intent: str
    request: str      # the wire request's canonical bytes, as text — NOT `request_json`
    subject: str
```

— canonicalizes to byte-identical output, and `content_hash(ChildQuestionIdentity(...))
== question_identity(...)` with **no change to the identity function**.

**Measured on `61d2af87`**, in-process against the SDK as built (the script is in the
session record; its output verbatim):

```
identity           28e0636070a1da0dac4a6daf16d41835429ad1c05f1aa7347cffc82abf3a1937
content_hash(art)  28e0636070a1da0dac4a6daf16d41835429ad1c05f1aa7347cffc82abf3a1937
BYTE-IDENTICAL     True
bytes equal        True 321        # canonical_bytes(art) == the identity's own rendering
content_hash(ProductQuestion) == identity: False | ProductQuestion.address == identity: True
subject change moves it: True
```

The `asked_at` in that run was spelled at `+02:00`; both sides normalized it to the
same UTC text. The negative control is the one that matters for the ruling: **retaining
the `ProductQuestion` itself would not satisfy it** — its canonical bytes carry a
`parameters` member and the key `request_json`, so its content hash is a different
address. The identity-bearing bytes are the five-key rendering and nothing else, and
`ChildQuestionIdentity` is that rendering as a contract.

Consequence: `src/ccf/artifacts/file_store.py::FileArtifactStore` `put(artifact=
ChildQuestionIdentity(...))` writes exactly the identity bytes and returns an
`src/ccf/artifacts/protocol.py::ArtifactRef` whose `content_address` equals
`child_question_address` — the same equality `_retain_child_contracts` asserts for
contracts, asserted here too. I propose re-expressing `question_identity` as
`content_hash(ChildQuestionIdentity(...))`, so the SDK has one rendering of the question
rather than two that happen to agree (`canonical.py`'s module rule: *"Nothing else in
the SDK may define its own canonical form"*), pinned by a test that keeps today's
`json.dumps` as the oracle. That re-expression is **R-3**; the retention does not depend
on it.

### 2.4 Ownership, and the write seam

The `ProductQuestion` and the parent's store are both in hand in exactly one place:
`resolve_for` on `QuestionBoundChildResolver`. `GovernedResolver` never sees the
question (it receives outcomes), and the dispatch module must not learn what a store
is. So the write goes **in `resolve_for`, immediately after the `ProductQuestion` is
built and before `dispatch_skill` is called**, through the store the class already
holds — its first write, on the parent's own store, under the consumer tenant the gate
was built with.

**Why before dispatch, not after admission:** the ruling covers unavailable outcomes.
A producer that is never reached — connection refused, crash, malformed answer — must
still leave its question. Filing first makes "admitted, refused and unavailable" one
structural property instead of three code paths: *no question artifact ⇒ no dispatch;
a dispatch ⇒ its question is on the store.*

**Class and name:** `CHILD_QUESTION_CLASS = "ccf.child-question"` beside
`ADMITTED_CHILD_CONTRACT_CLASS`; `tenant_id=` the consumer tenant; `name=address`.
Idempotent by construction (`src/ccf/artifacts/protocol.py::ArtifactStoreProtocol`
`put`: byte-identical content returns the same address; the name index is append-only
and short-circuits on a known address), so two compositions asking the same question
file one artifact.

**The reference on the row** (Dave: *prefer referencing the retained artifact from the
row*): `ChildResolution.child_question_ref: str | None` (`True`) carries the
`ArtifactRef.uri` that `put` returned —
`ccf-artifact://<consumer tenant>/ccf.child-question/<address>@<address>`
(`src/ccf/artifacts/protocol.py::artifact_uri`). It is carried from `resolve_for` to
the row through the existing channels and no new one: `_admit` gains a
`question_ref: str | None = None` keyword; the refused branches stamp it on
`ChildAdmissionRefusal.question_ref` (new member, `True`); the admitted branch stamps
it on `ChildInvocation.question_ref` (new defaulted field beside `question_address`,
via `invocation_from_dispatch`); `resolve_child_outcomes` and `_row_for_admitted` copy
it. The legacy argument-bound path passes `None`: it mints no question, its rows carry
no `child_question_address`, and it is out of this limb's scope by ruling.

The URI is computable from `(tenant, class, address)`, and the row could name it without
witnessing the write. It must not: a row that says *the question is retained at this
reference* should say so because the store returned that reference. That is the whole
difference between evidence and narrative, and it is what sabotage S-B5 checks.

### 2.5 Write timing and persist-fail posture

- **Write:** before the producer is called, once per question, from the minting seam.
- **Persist-fail:** a failing `put` (`OSError`, `CanonicalizationError`) **propagates
  as a fault**. The producer is not asked, the door reports the runtime failure, and
  no record is written claiming a question the store does not hold. It is not a
  governed refusal — there is no governed "no" to give; the parent's own substrate
  failed — and it is the posture `D-IMPL-344` R-3 ruled for contract retention. On the
  question-bound path a row is therefore never written with `child_question_address`
  set and `child_question_ref` `None`.

### 2.6 Replay and audit read path

- **The audit read, one function, beside `_reconstruct_child_contracts` in
  `ccf.replay.engine`:** `retained_child_question(*, store, row) ->
  ChildQuestionIdentity`. It requires `row.child_question_ref`; `store.resolve_uri`
  must yield `row.child_question_address` (else
  `src/ccf/replay/engine.py::ReplayDivergence` — the reference names another
  artifact); `store.get` the bytes (missing ⇒
  `src/ccf/replay/engine.py::ReplayUnresolvable`); parse as `ChildQuestionIdentity`;
  `content_hash(parsed) == row.child_question_address` (else `ReplayDivergence`). It
  calls no mapping, no producer, and reads no configuration; a row with no
  `child_question_ref` raises `ReplayUnresolvable` **by name** — *not retained: this
  row predates `D-IMPL-342` retention or came from a resolver that retains no question*
  — never a pass.
- **The replay hold, in both halves:** one helper, `_hold_retained_questions(store,
  record)`, called from the shared child step that `src/ccf/replay/engine.py::replay`
  and `replay_refusal` already share, over **every** row whose `child_question_ref` is
  set — admitted, ineligible, producer-unavailable, gate-rejected — resolving and
  hash-checking each through `retained_child_question`. Rows without a reference are
  not held; that is the three-state reading (pass / fail / not retained), and it is why
  the row carries a reference rather than the engine guessing whether retention was in
  force when the record was written. No outcome type gains a member: the hold passes or
  raises.
- **The proof that neither the mapping nor the producer is needed:** ask, stop the
  producers, monkeypatch the deployment's mapping to raise, and replay from a fresh
  store instance and the record alone. Green means the historical question came from
  the store.

### 2.7 Backward compatibility

Additive: one contract, one class constant, one row member (`True`), one member on
`ChildAdmissionRefusal` (`True`; one more envelope key, covered by **R-1**), one
defaulted field on `ChildInvocation`, one keyword on `_admit`, one helper and one hold
in the engine. `question_identity` produces the same bytes whether or not R-3 is taken.
Records written before this limb replay exactly as before: their rows carry no
`child_question_ref` and are not held. `_children_of` is untouched. The two proofs in
§2.1 (5) stop recomputing and assert from the store instead (example-level conversion
after the SDK lands, per `D-IMPL-261`).

### 2.8 Controls

| control | scenario | holds |
|---|---|---|
| C-B1 | admitted | row `child_question_ref` set; bytes at `child_question_address`; `content_hash(parsed) == address`; the parsed `request` equals the canonical bytes of the `WireRequest` the fixture door **echoed** (`DoorOutcome.request`) — two independent witnesses of one question |
| C-B2 | refused by the door (`ineligible`) | as C-B1: retention precedes the outcome |
| C-B3 | unavailable (unreachable endpoint ⇒ `McpProductFailure`) | `producer-unavailable`; `child_question_ref` set; bytes retained |
| C-B4 | malformed answer ⇒ `producer-unavailable` | retained |
| C-B5 | identity | the retained bytes equal `question_identity`'s own rendering computed in the test from the parsed members, and differ from `content_hash(ProductQuestion)` |
| C-B6 | replay with the world removed | producers stopped, mapping patched to raise: `replay` (served) and `replay_refusal` (refused) succeed; `retained_child_question` returns for every row |
| C-B7 | tamper | the stored bytes replaced by a different subject's ⇒ `ReplayDivergence` from the hold and from the helper |
| C-B8 | missing | the artifact deleted ⇒ `ReplayUnresolvable` |
| C-B9 | pre-342 record | a hand-built row without `child_question_ref`: replay does not hold it; the helper raises the named "not retained" |
| C-B10 | persist-fail | a store whose `put` raises for the question class: the fixture producer's call count stays 0; the fault propagates; no record written |
| C-B11 | idempotent | the same question asked twice ⇒ one artifact, two records referencing it |

Estate-level, after the SDK lands: the fourth-slice covenant test asserts the question
from the store and no longer binds a second `MemoQuestions`; `CP14-F-35` moves to
`FIXED-342` at the validation step.

### 2.9 Sabotages

| sabotage | expected red | expected green |
|---|---|---|
| S-B1 remove the `put` (file nothing; the ref is `None`) | C-B1–C-B4 (ref `None`), C-B6's per-row helper ("not retained") | C-B9 — and this pairing is the reason the ref exists: without it, S-B1 would make every record look pre-342 |
| S-B2 file the `ProductQuestion` instead of `ChildQuestionIdentity` | the `filed.content_address == address` assertion at ask time — C-B1 red before any dispatch | — |
| S-B3 move the `put` after dispatch | C-B3, C-B4 | C-B1, C-B2 — proves the ordering, not just the write |
| S-B4 drop the hash check in `retained_child_question` | C-B7 | C-B8 |
| S-B5 compute the ref from `(tenant, class, address)` instead of `put`'s return, with S-B1 | C-B1's store lookup (a ref with nothing behind it) | — |

### 2.10 Migration and versioning

None. Old records stay replayable exactly as before (unheld rows, by name). The new
artifact class is declared beside the existing one. The public-surface manifest gains
`ChildQuestionIdentity`, `CHILD_QUESTION_CLASS` and `retained_child_question`
(`make surface`); the record schema export gains one optional member
(`make schema-headers`).

## 3 · Compatibility, both limbs

- **Additive everywhere.** No existing return type, refusal kind, disclosure rule,
  vocabulary member or engine entry point changes; `question_identity`'s bytes do not
  change.
- **New composite refusal records hash differently** (five more envelope keys, §1.4);
  old records keep their bytes and still rehydrate. Nothing has shipped that pins a
  composite refusal record's address; the committed golden replay fixture is a served
  record.
- **Row members `True` at `None`** (§1.7): stored rows reload to their addresses.
- **Frozen trees untouched**; example tests convert only at the separate validation
  step (`D-IMPL-261`).
- **Out of scope, unchanged:** `D-IMPL-341`; the paved cp-05 successor; CP-14 memo
  assembly; `replay()` returning anything but a product; any new producer behavior; the
  legacy argument-bound child leg; any broader replay redesign.

## 4 · Rulings asked

Only the four that are Dave's; everything else above is stated as the design.

- **R-1 — widen `ChildAdmissionRefusal`.** Five optional members (A's four, B's
  `question_ref`) on the refusal value, which `envelope_for` renders into every
  composite refusal's `fields`: new refusal records hash differently, old ones still
  hold, the pinned key set in `test_envelope_for_composite_child_refusal` grows on
  purpose, the served envelope is unchanged at minimal. The alternative is a side
  channel parallel to the outcome mapping (a Protocol widening) to keep the refusal
  value as it is; I recommend the widening — the refusal value *is* the record of what
  admission decided, and these are facts admission had.
- **R-2 — Limb A retains row members and the producer's reference; it does not retain
  the producer's envelope bytes on the consumer's store, and `detail` stays off the
  row.** §1.4. If per-row producer prose is wanted, that is reading 2 of the OPEN entry
  as its own follow-on, not a variation of this limb.
- **R-3 — re-express `question_identity` as `content_hash(ChildQuestionIdentity(...))`.**
  One rendering in the SDK instead of two that agree, pinned by a byte-identity test
  against today's `json.dumps`. If refused, the identity function stays as it is and
  the equality is a test rather than a definition; retention is unaffected either way.
- **R-4 — the row reference and the replay hold.** `child_question_ref` on the row
  (from `put`'s return), and both replay halves holding every referenced question to
  its bytes, with unreferenced rows unheld by name. The alternative — hold every row
  that has an address, unconditionally — would make every composite record written
  before 342 unreplayable. I recommend the reference.

## 5 · Scoped verification plan

- New modules: `tests/products/test_d_impl_342_producer_refusal_evidence.py` (C-A1–C-A8)
  and `tests/products/test_d_impl_342_child_question_retention.py` (C-B1–C-B11), both
  through the paved consumer over a fixture producer in another process, no estate;
  the door-outcome oracle decoded in the test, never through `_admit`.
- Existing suites held by exact node id to `61d2af87`: `tests/products`
  (`test_paved_consumer`, `test_d_impl_340_producer_admission`,
  `test_d_impl_344_refusal_reconstruction`, `test_refusal_envelope`), `tests/replay`,
  the four CP-14 slices, the cp-03 canonical paved consumer, the wrapper door. The
  intentional flips are the three §1.1 (6) assertions and the two §2.1 (5) proofs — in
  `tests/products` inside the change, in `tests/examples` at the validation step.
- `make lint`, `make typecheck`, `make product-gates`, `make schema-headers`,
  `make surface`, the docs gates; ten sabotages (S-A1–S-A5, S-B1–S-B5) run by hand,
  restored by copy, verified by `cmp`, recorded in the close.

## 6 · What this document does not do

No code. No CP-14 edit. No producer change. No new refusal reason. No change to
`replay()`'s outcome type. No repair of `D-IMPL-341`. No retention for the legacy
argument-bound child leg. No re-pin of any example transcript or page.

## 7 · Perspective, surfaced for the ruling

1. **The ruling for F-35 is satisfiable exactly, not approximately.** The measurement in
   §2.3 is the design's load-bearing fact: the SDK's canonical encoder already produces
   the identity's bytes for a five-member contract, so "the retained bytes must
   reproduce the recorded question identity" is a store address equality, checked the
   same way `D-IMPL-344` checks contracts. Had it come out false, the honest design
   would have been to change `question_identity` to hash a contract — a generation
   change to every question address. It did not, and no such change is proposed.
2. **Limb A's byte change on dimension 5 is right, and I would not soften it.** A
   composite refusal recorded after 342 says more than one recorded before it; its
   address should differ. The alternative that keeps refusal records byte-stable (a side
   channel around the refusal value) hides the evidence from the one block that
   `replay_refusal` rehydrates and holds.
3. **Filing the question before the producer is called is the point of Limb B, not a
   detail.** It is the only ordering under which "unavailable" is covered structurally.
   If the ruling prefers the resolver as the single filing seam (the `D-IMPL-344`
   precedent), the question would have to travel up through a widened Protocol and be
   filed after the producer answered — and an unreachable producer's question would
   then depend on the failure path remembering to carry it. I recommend the seam in
   §2.4.
4. **Three tests were written to go red when this is fixed, and they will.** They are
   replaced by positive proofs, at the validation step for the example-level ones. That
   is the pattern working, not a regression.

## 8 · As built (2026-09-18, synchronization of this design to the tree)

Implemented on `d-impl-342-evidence` from the accepted design (`51127a2b` on `61d2af87`),
under Dave's implementation GO ("implement both limbs exactly as ruled"). First candidate `5ab20614`; the candidate under review is the tip of the branch, one commit
later, after the review below. What follows names every place the tree differs from §1–§2,
and records the measurements the GO asked for.

### 8.1 Contracts, exactly as built

**Limb A.** `src/ccf/products/composite.py::ChildAdmissionRefusal` gained five optional
members, hash-transparent at `None`: `producer_refusal_kind`, `producer_refusal_reason`,
`producer_refusal_key`, `producer_replay_ref`, and Limb B's `question_ref`.
`src/ccf/replay/record.py::ChildResolution` gained four: `producer_refusal_kind`,
`producer_refusal_reason`, `producer_refusal_key`, `child_question_ref`; `child_replay_ref`
is now written on the refused-door branch. The `_admit` refused-door branch on
`src/ccf/products/child_resolver.py::GrantBoundChildResolver` passes the door's `kind`,
`reason`, `key` and `replay_ref` through `refuse_naming_producer`; the row copies them in
`src/ccf/products/composite.py::resolve_child_outcomes`. The verdict stays `ineligible`;
the prose `detail` is unchanged; nothing new crosses the served envelope at minimal (the
five keys cross as `"undisclosed"`, exactly like the existing producer members — measured
in C-A5).

**One addition beyond §1.6, in place of the proposed replay hold:** a model validator on
`ChildResolution` refuses producer refusal evidence on any row that is not `ineligible` on
BOTH `outcome_status` and `refusal_ref` (the review found that the status token alone is
also minted for the three eligibility-evidence refusals), and a `child_question_ref` without
a `child_question_address`. Structural for every writer and every reader, rather than a
check one replay path runs; the §1.6 hold was not added because the validator makes the
inconsistent row unconstructible. Sabotage S-A4 shows it firing in production code:
mapping the producer's verdict onto the row's status makes every refused-door composition
raise at row construction. One closed-vocabulary limit is recorded in its docstring: the
local invalidation register's own `ineligible` refusal of a locally dispatched child shares
both tokens, and that leg mints no producer evidence.

**Limb B.** `src/ccf/skills/dispatch.py::ChildQuestionIdentity` (five members, as §2.3);
`src/ccf/skills/dispatch.py::ProductQuestion` gained `identity_artifact()`;
`src/ccf/skills/dispatch.py::question_identity` is now `content_hash(ChildQuestionIdentity(...))`
— R-3 taken; the bytes and every address are unchanged (C-B1–C-B3 hold the retained bytes
to the pre-342 rendering copied verbatim into the suite, and the in-process control in §2.3
was repeated on the built tree). `src/ccf/products/composite.py::CHILD_QUESTION_CLASS` =
`ccf.child-question`. `_retain_question` on
`src/ccf/products/child_resolver.py::QuestionBoundChildResolver` files under the gate's
tenant (a read-only `tenant_id` property was added to
`src/ccf/products/composite.py::CompositeAdmissionGate`), named by the address, **before**
`dispatch_skill`; a store that files at another address is refused (`RuntimeError`); a
store that cannot file raises through `resolve_for` with the producer never asked and no
record written (C-B10, with a loopback listener counting connections). The reference is
the `ArtifactRef.uri` the store returned, threaded as `question_ref` through `_admit`, onto
every refusal value minted after dispatch, and onto
`src/ccf/products/composite.py::ChildInvocation` via
`src/ccf/products/composite.py::invocation_from_dispatch` (refused for a non-`mcp-product`
acquisition, as `touched_entities` is for a remote one). The legacy argument-bound leg
passes `None` and retains nothing, as scoped.

**Where the first candidate was wrong, found by its review (§8.6):** the gate's own
`refuse` closure in `admit` on `src/ccf/products/composite.py::CompositeAdmissionGate` — the
site that mints every rejection of a SERVED answer (`producer-mismatch`, `question-mismatch`,
`as-of-mismatch`, `class-mismatch`, the eligibility refusals, …) — carried neither the
retained question's reference nor the door's replay reference, so such a row named a
`child_question_address` with `child_question_ref None`: replay left it unheld and the audit
read called it "not retained" about bytes the store held, contradicting §2.5. The closure
now carries `question_ref=invocation.question_ref` and
`producer_replay_ref=candidate.child_replay_ref` (the reference the door reported for the
answer it served, a claim retained as reported). Two controls were added for that branch
(C-A4b, C-B12) and two sabotages (S-A6, S-B7). §1.1 (5) had described the wrong branch:
the branch that kept `child_replay_ref` on a rejected answer is the re-binding failure in
`resolve_child_outcomes`, not the gate's closure.

**Replay.** `src/ccf/replay/engine.py::retained_child_question` is the audit read;
`_hold_retained_questions` is called at the three child steps — `replay()` after
`_children_of` and before `_re_execute`, and both halves of `replay_refusal()` — over every
row whose `child_question_ref` is set. A row without one is unheld by name, and the helper
raises `ReplayUnresolvable` "not retained" for it. Exception classes as §2.6.

### 8.2 Before and after, both limbs

| | before (`61d2af87`) | after (`5ab20614`) |
|---|---|---|
| Limb A, fixture: a served answer rejected inside the gate (a wrong producer id) | row `producer-mismatch` with `child_replay_ref None` and, at the first candidate, `child_question_ref None` | the same verdict with the door's replay reference and the retained question's reference (C-A4b, C-B12); no producer refusal invented |
| Limb A, fixture: the paved child refused at the door on a lane floor | row `ineligible` / `ineligible`, `child_replay_ref None`, no producer refusal (`tests/products/test_paved_consumer.py::test_a_floor_above_the_served_lane_is_refused_at_the_door_with_both_lanes_retained` asserted the `None`) | the same verdict, plus `producer_refusal_kind = product-request-violation`, `reason = class-mismatch`, `key = schema_version`, `child_replay_ref = ccf-artifact://paved-child-tenant/ccf.replay-record/…` — equal to what the door itself discloses to a second dispatch (C-A1) |
| Limb A, estate: CP-14's withheld spread | row `ineligible`, reason only in the first-blocking prose; the first and fourth slices asserted `child_replay_ref is None` | those two assertions are red by design (the flip they were written for); converted at the separate validation step (`D-IMPL-261`) |
| Limb B, fixture: any dispatched child | `child_question_address` named bytes the store did not hold | `child_question_ref = ccf-artifact://<consumer tenant>/ccf.child-question/<address>@<address>`; the bytes at the address equal the pre-342 preimage rendered independently (C-B1 admitted, C-B2 refused, C-B3 unreachable) |
| Limb B, replay | nothing read `child_question_address` | `replay_refusal` and `replay` hold every referenced question; producers stopped, environment and reader raising if reached (C-B6); tamper and deletion fail by name on both paths (C-B7, C-B8) |

### 8.3 Sabotages, run by hand and restored (`cmp` verified after each)

Targeted suites: the two limb modules, `tests/products/test_paved_consumer.py`,
`tests/products/test_refusal_envelope.py` (113 controls at the first candidate; 115 after the
review's two controls were added). All thirteen were re-run against the 115 at close, each
restored and `cmp`-verified; the counts below are the close-time ones.

| sabotage | red | green |
|---|---|---|
| S-A1 drop `producer_replay_ref` in `_admit` | C-A1 ×2, C-A5, the paved lane-floor test | everything else |
| S-A2 drop the three scalars in `_admit` | C-A1 ×2, C-A5, the paved lane-floor test | everything else |
| S-A3 keep the refusal members, drop the row copy | C-A1 ×2, the paved lane-floor test | C-A5's record-block assertion — refusal value and row held separately |
| S-A4 map the producer's verdict onto the row status | 10, including C-A7 and five Limb B controls: the row validator refuses the fabricated pairing at construction, so every refused-door composition raises | — |
| S-A5 mark the new members `False` | C-A7 only (a pre-342 record's stored bytes, keys deleted, no longer reload to their address) | the other 114 |
| S-B1 file nothing | C-B1–C-B3, C-B6–C-B12, C-A4b, the paved mapping test (12) | the other C-A*, C-B5 |
| S-B2 file the `ProductQuestion` instead of the identity | 29 — every composition raises `RuntimeError` at ask, before any dispatch | — |
| S-B3 file after dispatch | C-B10 only — the ordering, not the write | the other 114 |
| S-B4 drop the bytes-hash check in the audit read | C-B7, C-B12 (the two tamper controls) | the other 113 |
| S-B5 compute the reference from the address instead of witnessing the put (nothing filed) | 14, C-A1 and C-A4b included (their reconstructions now resolve a reference with nothing behind it) | — |
| S-B6 drop the hold from `replay()` | C-B7 only — the served-path tamper | the other 114 |
| S-A6 drop `producer_replay_ref` from the gate's closure | C-A4b only | the other 114 |
| S-B7 drop `question_ref` from the gate's closure | C-A4b, C-B12 | the other 113 |

S-A5 first turned nothing red: C-A7 rebuilt the pre-342 record through `model_copy`, which
under either posture re-canonicalizes consistently. The control was strengthened to delete
the keys from the row and record JSON and file those bytes at their own `sha256` — the
shape a pre-342 store actually holds — before S-A5 was re-run.

**Controls that differ from §1.9 / §2.8, and why.** C-A1 runs two shapes, both conformity
refusals of the same kind (`product-request-violation`): the fixture door's only other
refusal, `subject-unavailable`, arises under a wrong tenant, where the producer's claims
then fail and the evidence is deliberately NOT carried (C-A4a). C-A1 holds the replay
reference to the producer's tenant and class and to a well-formed versioned URI, not to the
oracle's exact reference: each dispatch mints a new producer record, so a second dispatch
cannot witness the first's reference. §1.9's C-A4 ("served, rejected at the gate,
`question-mismatch`") became two controls — C-A4a (door refused, claims failed: nothing
carried) and C-A4b (door served, gate rejected on `producer-mismatch`: references carried,
no producer refusal) — because a question mismatch cannot be induced from the consumer side
of the paved fixture. C-A8 also refuses evidence on an `ineligible` status with an
eligibility-evidence `refusal_ref`.

### 8.4 Deliberate test growth, named

- `tests/products/test_refusal_envelope.py::test_envelope_for_composite_child_refusal` — the
  pinned key set of a composite refusal's `fields` grew by five (R-1).
- `tests/contracts/test_hash_transparency.py` — the ticked roster grew by nine marks.
- `tests/examples/test_cp_03_canonical_paved_consumer.py` — the row-member classification
  table grew by four (`producer_refusal_*` as child identity, `child_question_ref` as
  parent-owned); the dogfood's member-by-member comparison is otherwise unchanged.
- `tests/products/test_paved_consumer.py` — the assertion written to go red when 342 landed
  flipped to a positive one; the mapping-authority test now also reads the retained question
  from a fresh store.

### 8.5 Residual limitations

- A malformed door answer (`MalformedDoorAnswer` → `producer-unavailable`) has no
  cross-process control; the unreachable-endpoint control covers the `McpProductFailure`
  branch and the ordering.
- The served-path replay hold is exercised by the tamper control (C-B7) only; the positive
  served-path reconstruction needs a replay environment the paved fixture does not build
  (`CP06C-F-01`), and is exercised on the estate by CP-14's second slice at the validation
  step.
- The legacy argument-bound child leg retains no question, by scope.

### 8.6 The candidate's review, and what it changed

Five read-only review lenses were run over the first candidate's committed diff (Limb A
correctness; Limb B retention and replay; identity and canonical form; proof strength; docs
and surface agreement), and every finding was handed to a second agent instructed to refute
it. Twenty findings were raised and all twenty were confirmed by their refuters. They reduce
to:

- **One code defect (high):** the gate's `refuse` closure omission above — the same defect
  seen through three lenses. Fixed; C-A4b, C-B12, S-A6, S-B7 added.
- **One validator weakness (medium):** the evidence validator keyed on the status token only.
  Tightened to both tokens; C-A8 extended.
- **One undocumented behavior change (low):** `question_identity` now refuses a naive
  `asked_at`, which the old rendering hashed through the host's zone. Documented in the
  docstring and the surface fragment as the canonical form's own rule; no caller passes one.
- **Two controls weaker or differently placed than the design said (medium, low):** C-A4 as
  first shipped exercised the refused-door branch, not the served-then-rejected one; C-A1's
  reference assertion was a prefix. Both re-specified above. C-B9's match pattern also
  matched the bytes-missing branch; tightened to the no-reference message.
- **Documentation behind the code (medium, low):** this §8 did not yet exist while both
  suites cited it; the design's status header said design-only; the surface fragment cited
  a GO the decision log had not yet recorded (the IMPLEMENTED entry now records it); a 344
  re-citation named `_reconstruct_child_contracts` as its own caller (`_children_of`
  selects, corrected); the `GrantBoundChildResolver` docstring called the store read-only.
  All synchronized in the same commit as the fix.

Nothing on the not-to-re-derive list was re-raised. The refuters' evidence for the closure
defect was an executed cross-process reproduction with a tampered question artifact that
`replay_refusal` did not notice — the "don't know read as pass" shape this project names in
CLAUDE.md §3.1, inside the very change that was meant to close it for questions.
