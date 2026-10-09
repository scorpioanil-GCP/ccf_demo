# 378-53-a (decision 5 (a)) — the record writer hands out only the reference of the record it wrote

`D-IMPL-378` decision 5 (a), ruled by Dave on 2026-10-09 (06:06 MST, confirmed at 06:21 MST, "5a"):
*"(a). Verify the returned record address against the record actually written."* The final panel's
G-REF-UNCHECKED. Built in lane `378i-small`.

**What was measured before the change**, on `dl-378-integ` @ `a539c215`: `ReplayWriter.write_replay_record`
returned whatever `ArtifactRef` the store's `put` answered. A store that filed record A faithfully and answered
record B's genuine reference had B's reference handed out for A (the panel's probe `p_b05_returned_ref.py`,
re-run on the paved road's own served and refused records). A store answering A's reference with one field
changed (the content address, the URI, the tenant, the class or the name) had that reference handed out too,
on the served path and on the refusal path, and so did one whose changed field was a `str` subclass claiming
to equal A's.

**What holds now**, in `tests/replay/test_replay_writer_checks_the_returned_reference.py` (18 tests; 16 failed
before the change, 2 controls passed before and after). The writer derives the reference of the record it
files: under `D-IMPL-26` and Q11 the content address is `content_hash` of the record, the name is that address,
the URI is `ccf-artifact://{tenant}/{class}/{address}@{address}`, and the tenant and class are its capability's.
Every field of the store's answer is held to that as an exact string; any difference raises
`ReplayReferenceMismatch` after `put` returns and before any delivery capability exists, so nothing is
delivered and no reference leaves. The URI is held, not only the address, because the refusal path hands its
caller the URI. The reference handed out is the one the writer derived. Both controls hold: the file store's
answer is exactly the record's own, through the writer and through the paved road's served and refused
answers. Severing (the check dropped and the store's answer handed out again) reddened the same 16 tests.

**What it does not check.** The bytes the store holds: the writer reads the store's answer, not the store. A
store that answers the record's own reference while holding other bytes under it is found by the readers, which
re-hash before use (`tests/replay/test_record_content_address_integrity.py`). The other writers that hand out a
store's answer (`QueryPinWriter.write_query_bytes`, the peering admission record) are unchanged.

## ccf.replay.serve.ReplayReferenceMismatch

- Surface: ccf.replay.serve.ReplayReferenceMismatch
- Public surface: true
- Change type: added
- Before: absent; the record writer handed out whatever reference the store answered.
- After: an `ArtifactStoreError` raised by `ReplayWriter.write_replay_record` when any field of the reference the store's `put` answered (content address, URI, tenant, class, name) is not, as an exact string, the record's own. It carries `fields`, the names of the differing fields; its text names those fields and no value the store answered.
- Why: `D-IMPL-378` decision 5 (a). Red test: `tests/replay/test_replay_writer_checks_the_returned_reference.py::test_a_store_answering_another_records_reference_is_refused_by_name`.
- Migration: none; additive. A handler for `ArtifactStoreError` also catches it.

## ccf.replay.serve.ReplayWriter

- Surface: ccf.replay.serve.ReplayWriter
- Public surface: true
- Change type: behavior
- Before: `write_replay_record` returned a `DeliveryCapability` over whatever reference the store's `put` answered.
- After: `write_replay_record` derives the record's own reference and raises `ReplayReferenceMismatch` unless the store's answer equals it field for field; the capability carries the derived reference.
- Why: `D-IMPL-378` decision 5 (a). Red test: `tests/replay/test_replay_writer_checks_the_returned_reference.py::test_the_served_path_refuses_a_reference_with_any_field_not_the_records_own`.
- Migration: none for a store conforming to `D-IMPL-26` (the URI's version is the content address); a store answering any other reference for a record is refused.

## ccf.replay.serve.record_refusal

- Surface: ccf.replay.serve.record_refusal
- Public surface: true
- Change type: behavior
- Before: returned whatever reference the store answered for the refusal's record, whose URI the resolver hands to the caller.
- After: raises `ReplayReferenceMismatch`, through the writer, when that answer is not the record's own reference; returns the record's own reference otherwise.
- Why: `D-IMPL-378` decision 5 (a). Red test: `tests/replay/test_replay_writer_checks_the_returned_reference.py::test_the_refusal_path_refuses_a_reference_with_any_field_not_the_records_own`.
- Migration: none for a conforming store.

## ccf.replay.serve.serve

- Surface: ccf.replay.serve.serve
- Public surface: true
- Change type: behavior
- Before: delivered the product with whatever reference the store answered for its record.
- After: raises `ReplayReferenceMismatch`, through the writer, when that answer is not the record's own reference, so nothing is delivered.
- Why: `D-IMPL-378` decision 5 (a).
- Migration: none for a conforming store.
