# R-01 — `serve` refuses a replay record that describes a different product

Applied 2026-09-08 under `D-IMPL-279` (Dave), narrowing `D-IMPL-278` row 1 — the
architecture gap cp-05 exposed: *"The fabric must establish correspondence between the
candidate product, the governed execution record, and the replay record before delivery."*
And on the enforcement point: *"I would not put the primary enforcement in MCP. MCP is
transport. The canonical enforcement point should be in the governed fulfillment spine,
before transport encoding."*

## What did NOT change, stated first

- **No runtime change.** `runtime/` is untouched. `ccf.products.door::served_answer` keeps
  its existing shape check and reconstructs nothing; the ruling gives the door only
  *"verifies it received an already-governed, replay-backed deliverable."*
- **No new proof object, protocol or framework.** `serve` already refused a query-pin
  disagreement element-for-element (`QueryPinMismatch`, `D-11`, `GQ-20`). This is one more
  comparison of that exact shape, at that seam, over the fact `D-IMPL-278` named.
- **No governed-refusal surface.** A resolver handing the seam a record for one product and
  a vessel for another has mis-wired its own spine; that raises, like `QueryPinMismatch`,
  and never returns a `RefusalEnvelope` a caller could mistake for an answer.
- **No existing call site changes.** On every correctly-composed path the record's
  `product_content_address` is already `content_hash(product)` by construction
  (`ccf.replay.record::build_replay_record`), so the comparison is silent.
- **The withheld branch is untouched.** A refusal carries no vessel and therefore no
  address to correspond; `RefusalEvidence` already pins the execution.

## ccf.replay.serve.ProductRecordMismatch

- Surface: ccf.replay.serve.ProductRecordMismatch
- Public surface: true
- Change type: added
- Before: absent — `serve` compared the record's pinned query sequence against the queries
  it was handed and refused a disagreement, but nothing compared the record's
  `product_content_address` against the vessel about to be delivered. Measured on cp-05
  (`CP-SPEC-005` §D.10 question 1): a `ServedProduct` whose payload claimed 9,999 family
  members, wrapping a record whose dimension 1 observed 77, crossed
  `ccf.products.door::served_answer` unremarked — the door proved a record *existed* and
  never read it
- After: `serve` compares `record.content_generation_path.product_content_address` against
  `content_hash(product.product)` **first**, before the query-pin checks and before any
  store write, and raises `ProductRecordMismatch` naming both addresses. A `ValueError`
  subclass, the sibling of `QueryPinMismatch`, exported from `ccf.replay.serve`
- Why: `D-IMPL-279` (Dave, 2026-09-08), narrowing `D-IMPL-278` row 1 — the fabric must establish correspondence between the candidate product, the governed execution record and the replay record before delivery, and the enforcement point is the governed fulfillment spine before transport encoding, not MCP
- Migration: none. A deployment whose resolver builds its record from the product it
  serves — every shipped path — sees no change. A deployment that hands the seam a record
  built about a different product is now refused instead of silently serving

## Regression evidence

`tests/replay/test_product_record_correspondence.py`, one test with its control inside it:
a record built about the served product delivers and its reference resolves in the store;
the *same* gated product handed a record about a different one is refused, the message
names both addresses, and the refused call persists nothing (asserted as a store delta, not
an absolute count). Sabotage-verified: with the comparison neutralized the test goes red on
`DID NOT RAISE ProductRecordMismatch`, and green when restored.
