# `QuestionDeclaration.asked_at` becomes `datetime | None`

**Plan:** Phase 17 close review (`BL-02` remediation)
**Ruled:** Dave, 2026-08-16
**Kind:** reshaped — one field, one type, on one committed class

## What moved

`ccf.client.adapters.binding_document.QuestionDeclaration.asked_at`

| | |
|---|---|
| before | `datetime` — required in the document, required on the dataclass |
| after | `datetime \| None` — optional in the document, `None` when omitted |

Nothing was added and nothing was removed. `dump_surface.py --report` reports
`added (0)`, `removed (0)`, `reshaped (1)`.

## Why

Two rulings, in order, on 2026-08-16.

**First, `BL-02`.** `~ccf.client.client.ProductClient.ask` documents that
`as_of=None` means *the server's decision instant* — "the producing deployment
answers against its own **clock**" — and `D-04` rules the same. The in-process
adapter instead resolved `None` to this declared literal, so the default path
answered as of a fixed moment stated in `binding.yaml`. Measured at the close
review: with no `--as-of`, the shipped example printed
`answer expires 2026-03-02 12:10:00+00:00` on 2026-08-16 — five and a half
months expired — against a README promising "today's answer". Dave ruled that
`None` resolves to now. It now does.

**Then this.** That fix left `asked_at` **read by no code path** while the
loader still required every document to declare it. Dave's ruling: *"A required
field that no code path reads is a latent defect. The next reviewer will
correctly flag it. Keeping it required solely because the schema was closed
earlier is the wrong reason."*

So the requirement was dropped, and the reason is recorded rather than inferred:
**the field became unread, therefore it stopped being mandatory.** This is a
narrow amendment to `D-IMPL-141`'s data shape, not a widening of the binding
document's key set — `DATA_KEYS`, `OPTIONAL_KEYS`, `REFERENCE_KEYS` and
`RULED_OUT_KEYS` are all untouched, and the closed-world refusal of unknown keys
is unchanged.

## What did not change

- **Validation, when the field is declared.** A stated `asked_at` is still held
  to ISO 8601 and still refused if zone-less (`D-IMPL-38` — a zone-less instant
  is a silent default, and which zone it silently meant is the difference
  between two different answers). *Optional is not unvalidated.*
- **The other three question fields.** `subject`, `intent` and `freshness`
  remain required and are still refused by name when absent.
- **The document's key set.** `question:` is still a required section.

## Evidence

- `tests/client/test_binding_document.py::test_binding_document_accepts_a_question_that_omits_asked_at`
  asserts the **absence** path specifically. It exists because every fixture in
  the tree declares the field, so a loader that had gone on requiring it would
  have passed the entire suite and the ruling would have been recorded in prose
  and not in behaviour.
- `tests/client/test_binding_document.py::test_binding_document_refuses_a_zone_less_asked_at`
  is unchanged and still passes, which is what makes "optional is not
  unvalidated" a measurement rather than a claim.
- The requiredness parametrize dropped `asked_at` and kept the other three, so
  the test that proves a missing field is refused still proves it for everything
  that is still required.
