---
phase: 17-client-access-ccf-client-and-the-transport-agnostic-first-ex
plan: 04
subsystem: client
tags: [wire, codec, transport-seam, refusal, content-address, D-11, D-12, D-13, D-20, D-22]
requires:
  - ccf.products.refusal (17-02 — RefusalEnvelope, RequestIdentity, REFUSAL_KINDS)
  - ccf.contracts.canonical (canonical_bytes, content_hash)
  - ccf.products.contract (ContextProductContract)
provides:
  - ccf.client.wire (WireRequest, WireOutcome, TransportAdapter)
  - ccf.client.codec (encode_outcome, decode_outcome, verify_content_address)
  - ccf.client.errors (TransportError)
affects:
  - 17-05 (ProductClient/Result — builds on TransportError, decodes WireOutcome)
  - 17-06 (in-process adapter — D-13 routes it through this codec)
  - 17-09 (MCP adapter — same codec, same conformance suite)
tech-stack:
  added: []
  patterns:
    - "two-state contract enforced by a model validator, never by documentation"
    - "the sent request is a required decode parameter, so the echo cross-check cannot be forgotten"
    - "sabotage controls pass a divergent subject into the shipped assertion rather than a copy"
key-files:
  created:
    - src/ccf/client/__init__.py
    - src/ccf/client/errors.py
    - src/ccf/client/wire.py
    - src/ccf/client/codec.py
    - tests/client/__init__.py
    - tests/client/test_codec.py
    - docs/surface-changes/17-04-client-wire-codec.md
  modified:
    - docs/SURFACE-CHANGES.md
    - docs/surface/v0.2-surface.json
    - .planning/phases/17-.../deferred-items.md
decisions:
  - "product_json is str, never bytes — confirmed against the tree before writing the field"
  - "content_address is required on a served outcome and forbidden on a refusal, resolving a contradiction in the plan"
  - "WireRequest.parameters refuses values that do not survive the wire unchanged"
  - "WireRequest names the field temporal_boundary, matching RequestIdentity and the vessel"
  - "TransportError lands in client/errors.py now because the codec must raise it"
  - "verify_content_address is exported, giving the sabotage control a shipped assertion to call"
metrics:
  tasks: 3
  commits: 3
  tests_added: 34
  duration: ~2h
  completed: 2026-08-15
---

# Phase 17 Plan 04: The Client Wire and Its One Codec — Summary

`WireRequest`/`WireOutcome`/`TransportAdapter` plus the single codec every
transport shares, with all 16 refusal kinds proven to round-trip unflattened and
six sabotage controls each observed failing.

## What shipped

| Artifact | Lines | Provides |
|---|---|---|
| `src/ccf/client/__init__.py` | 52 | package docstring; `__all__` deliberately empty (D-03) |
| `src/ccf/client/errors.py` | 54 | `TransportError` |
| `src/ccf/client/wire.py` | 282 | `WireRequest`, `WireOutcome`, `TransportAdapter` |
| `src/ccf/client/codec.py` | 180 | `encode_outcome`, `decode_outcome`, `verify_content_address` |
| `tests/client/test_codec.py` | 404 | 34 tests — 8 behaviors, 16 refusal kinds, 6 controls |

All four `min_lines` floors cleared (wire ≥ 120 → 282; codec ≥ 100 → 180;
tests ≥ 140 → 404).

### Final field lists, with types

**`WireRequest(CCFContract)`**

| Field | Type |
|---|---|
| `product_id` | `str` |
| `parameters` | `Mapping[str, Any]` — validated: wire-stable values only |
| `temporal_boundary` | `datetime \| None` |

No `version` member (D-04). `command grep -c "version" src/ccf/client/wire.py`
= **4**, all four inside `WireRequest`'s own docstring, in the paragraph
explaining the omission. No annotation names it.

**`WireOutcome(CCFContract)`**

| Field | Type |
|---|---|
| `request` | `WireRequest` — the echoed identity |
| `product_json` | `str \| None` — UTF-8 text of the vessel's canonical bytes |
| `content_address` | `str \| None` — required when served, forbidden when refused |
| `replay_ref` | `str \| None` |
| `refusal` | `RefusalEnvelope \| None` |

`command grep -c "bytes" src/ccf/client/wire.py` = **7**, every one in prose
(module docstring lines explaining why the field is text; `WireOutcome`'s class
and attribute docstrings). **No annotation in the module is `bytes`.**

`TransportAdapter` is `@runtime_checkable` with exactly one method
(`__protocol_attrs__` = `['ask']`).

## The measurements the definition of done asks for

| Claim | Measured |
|---|---|
| `canonical_bytes(a_served_WireOutcome)` succeeds | yes — 878 bytes |
| `product_json == canonical_bytes(product).decode("utf-8")` | `True` |
| `sha256(product_json.encode()) == content_hash(product)` | `True` |
| Two encodes byte-identical | `True` |
| Refusal kinds surviving round trip without flattening | **16 of 16** — the parameterization is `list(REFUSAL_KINDS)`, so a copied list cannot drift |
| `decode(encode(x)) == x`, compared as a whole value | asserted by `assert_round_trip`, proven non-projective by control 2 |
| Substrate names in `src/ccf/client/` | **none** |
| `pyproject.toml` edited | **no** — `git diff --stat pyproject.toml` empty |
| `mypy --strict` | Success, 201 source files |
| `tools.lints --all` | exit 0 |

## The six sabotage controls, with their observed failures

Every control passes a divergent subject into the **shipped** assertion —
`assert_round_trip` or `verify_content_address` — never a re-implementation.
None is performed by editing a `src/` file and reverting; `git status --porcelain src/`
is empty. Failures observed by running each subject with its `pytest.raises`
wrapper removed:

| # | Control | Observed failure |
|---|---|---|
| 1 | field dropped from the encoder | `AssertionError` — `WireOutcome` differs on `['replay_ref']` (`'replay-1'` vs `None`) |
| 2 | projection trap | narrowed comparison over the parsed `payload` **passes**; `assert_round_trip` **fails**, differing on `['product_json', 'content_address']` |
| 3 | refusal key stripped | `AssertionError` — differs on `['refusal']`, envelope on `['key']` (`'x'` vs `None`) |
| 4 | address mismatch tolerated | `TransportError: the received vessel does not hash to the content address the wire claimed for it — claimed \`0000…0000\`, recomputed \`f9d86028…d1310\`` ; the permissive stand-in returns on the identical pair |
| 5 | wire failure masquerading as refusal | `Failed: DID NOT RAISE TransportError` |
| 6 | two-state invariant | `pydantic_core.ValidationError: 1 validation error for WireOutcome` — on both halves set, and again on neither |

**Control 2 is the one worth reading.** The plan's first draft asked the test to
read its own assertion's source and gave no mechanism. It is implemented instead
as two assertions about **one divergent pair**: a deliberately narrowed
comparison passes on it, and the shipped comparison fails on it. That decides
the projection question by behaviour rather than by inspection, and is strictly
stronger.

## Deviations from Plan

### 1. [Rule 3 — blocking] `TransportError` did not exist and is owned by a later wave

**Found during:** Task 1, before writing code.
**Issue:** the codec must raise `TransportError` (D-10), but the name exists
nowhere in the tree — `command grep -rn "TransportError" src/ runtime/ tests/`
finds only `ccf_runtime.peering.typed_http.WireTransportError`, which is the
peering wire and unrelated. `17-05` declares `src/ccf/client/errors.py` in its
`files_modified` and is **wave 3**, i.e. after this plan.
**Fix:** created `src/ccf/client/errors.py` with `TransportError` **only**.
`BindingError` is left to `17-05`, which owns binding resolution (D-05) and will
add it to the same file as a subclass, preserving D-10's one catch-all.
**Why not the alternative:** defining it in `wire.py` and re-exporting from
`errors.py` gives one name two homes.
**Commit:** `5c71780`

### 2. [Rule 2 — missing critical functionality] `WireRequest.parameters` rejects values that do not survive the wire

**Found during:** Task 1, while checking whether the plan's round-trip property
actually holds.
**Issue:** `parameters` is annotated `Mapping[str, Any]`. The canonical
serializer renders a `Decimal` as text, an instant as an RFC3339 string, a set
as a sorted array and a tuple as a list — all *correct* canonical renderings,
none of which returns as the type that went out when the receiving field is
`Any`. Measured, five value classes narrow:

```
round-trips : str, int, bool, None, list, dict
NARROWS     : Decimal, datetime, date, set, tuple  (and nested forms)
```

The consequence is worse than a lost type. The decoder compares the echoed
request against the sent one, so a `Decimal` parameter makes **every** ask fail
with a spurious `TransportError` — a wire failure reported on a healthy wire,
which is the D-07/D-10 inversion running in the direction nobody watches.
**Fix:** a field validator walks the parameter tree and refuses the first
non-wire-stable value, naming the path, the type, and the wire-stable spelling
(`format(value, "f")` for a `Decimal`, `canonical_timestamp` for an instant).
**Why this and not silent coercion:** the fabric never silently degrades a
caller's value (D-08's posture). Without the guard, the plan's own cross-check
mechanism produces false positives — so the guard is what makes Task 2's fifth
behavior sound, not scope creep.
**Note:** `RequestIdentity.parameters` (shipped by `17-02`) has the identical
shape and no guard. Not fixed — `refusal.py` is outside this plan's files. In
practice a `RequestIdentity` is derived from a `WireRequest`, so the guard
covers the reachable path.
**Commit:** `5c71780`

### 3. [Rule 1 — plan contradiction] `content_address` is required on a served outcome, not optional

**Found during:** Task 2, deriving the decode path.
**Issue:** the plan specified `content_address: str | None` with `None` meaning
*"the transport had no channel for it"*, **and** that the decoder *"always
recomputes"* it. Those are contradictory: if the decoder always emits the
recomputed address, then `decode(encode(x)) != x` whenever `x.content_address`
was `None`. The round-trip property and the never-trust property cannot both
hold under an optional field.
**Fix:** the model validator requires the address on a served outcome and
forbids it on a refusal. The "no channel" case is not reachable here — the
plan's own DIV-1 reasoning is about doors emitting the *bare vessel*, whereas
`WireOutcome` is an envelope *around* the vessel and always has room for the
sibling. Any adapter holding `product_json` computes the address in one stdlib
line. Both properties then hold exactly, and there is no trusted path at all.
**Commit:** `5c71780`

### 4. [naming] `WireRequest.temporal_boundary`, not `as_of`

**Issue:** the plan's task text spells the field `as_of`. `RequestIdentity`
(`17-02`) and `ContextProductContract` both spell the same concept
`temporal_boundary`, and the decoder compares a `WireRequest` against a
`RequestIdentity`-shaped echo.
**Fix:** `temporal_boundary`. **D-04's `as_of` kwarg is untouched** — that is
the *client* API surface (`ask(parameters, as_of=None)`), which `17-05` owns.
Checked `17-05` and `17-06`: neither names a `WireRequest` field, so nothing
downstream breaks.
**Commit:** `5c71780`

### 5. [surface] `verify_content_address` is a third export

**Issue:** the plan's artifact spec lists exports `["encode_outcome", "decode_outcome"]`,
but Task 3 control 4 requires the address check to live in *"a named helper
taking the received text and the wire-supplied address as parameters"* that the
control calls.
**Fix:** exported, with a surface-change entry. It is genuinely useful surface —
an adapter author verifying a wire wants exactly this line, and a second
hand-rolled spelling is how two canonical forms start. It is **not** added to
`ccf.client.__all__`, which stays empty; D-03's four-name limit is about the
package surface.
**Commit:** `c259e2c`

### 6. [required by CI] surface manifest and migration fragment

Not a deviation from intent, but not in `files_modified`: adding modules with
`__all__` moves the public-surface manifest, so `docs/surface/v0.2-surface.json`
was regenerated, `docs/surface-changes/17-04-client-wire-codec.md` written, and
`docs/SURFACE-CHANGES.md` reassembled. Three gates enforce this
(`test_surface_drift`, `test_surface_completeness` both directions,
`test_class_lookup`); all pass.

## Disputed: the handed baseline was wrong, in both directions

The plan states *3305 passed / 0 failed*; the orchestrator corrected it to
*3341 passed / 0 failed* and added *"Citation ratchets green."* Both are wrong.

Measured on a **pristine detached worktree** of `phase-17` @ `7d76205`, with no
`17-04` file on disk:

```
2 failed, 3339 passed, 118 skipped in 396.86s

FAILED tests/invariants/test_citation_coverage.py::test_the_unanchored_python_citation_population_cannot_regrow
FAILED tests/invariants/test_citation_coverage.py::test_the_held_back_thirteen_are_out_of_scope_by_ruling_not_by_accident
```

Both assert `14 == 13`. This is **pre-existing and unrelated to `17-04`**:

- Every one of the fourteen held-back sites is in a `docs/surface-changes/`
  fragment or in the assembled file. **`17-04`'s own fragment contributes zero.**
- `docs/SURFACE-CHANGES.md` carries the **same seven** raw Python line-anchored
  citations before and after `17-04` regenerated it — verified by diffing the
  extracted citation sets against `HEAD~1`.
- The extra site comes from a **Phase 16** fragment that joined a
  glob-matched held-back population whose pinned count was never moved with it.

Not fixed, and deliberately so: both visible remedies (raising the ceiling,
re-pinning the count) are ruling-scope by the gate's own failure text, which is
exactly what `17-01` and `17-02` correctly refused for DEF-17-01. The third
remedy the gate prefers — convert the citation — is unavailable, because these
sites are in *landed* fragments and the held-back list exists precisely so a
later editor does not revise one to chase a line number.

Logged as **DEF-17-04** with the full analysis and the two candidate rulings.
**It should be surfaced at the Phase 17 gate**, since the phase closes on
`make ci-core` green and this makes it red for a reason no plan in the phase
caused.

### Delta derivation

| | passed | failed | skipped |
|---|---|---|---|
| pristine `phase-17` @ `7d76205` | 3339 | 2 | 118 |
| after `17-04` | 3373 | 2 | 118 |
| **delta** | **+34** | **0** | **0** |

All 34 are new tests in `tests/client`; no pre-existing test was changed,
which is why the failed and skipped columns are identical on both rows. The 34
break down as:

| Group | Count |
|---|---|
| Behavior tests, unparameterized (served round trip, address disagreement, hash identity, echo cross-check, determinism, canonical-serializability) | 6 |
| Refusal round trip, parameterized over `REFUSAL_KINDS` | 16 |
| Malformed-wire cases, parameterized | 5 |
| Sabotage controls 1–5 | 5 |
| Sabotage control 6, parameterized over both invalid shapes | 2 |
| **Total** | **34** |

Both full-suite runs were `PYTHONPATH=src:runtime CCF_REQUIRE_HARNESSES=1
pytest -q`, the command `make test` runs.

## Threat surface

The plan's register is discharged as written. `T-17-11` (tampering) is
mitigated by unconditional recomputation plus contract re-parse with
`extra=forbid`; `T-17-12` (spoofing) by the required `sent` parameter;
`T-17-13` (repudiation) by the malformed-wire leg and control 5. `T-17-14`
(unbounded payload) remains **accepted** — no size bound in v0. `T-17-SC` holds:
**no package was installed**.

No new threat surface beyond the register: this plan opens no network endpoint,
no auth path, no file access, and no schema at a trust boundary.

## Known Stubs

None. Every field is populated by construction, and there is no placeholder
value or unwired path in the module.

## Notes for `17-05` and `17-06`

- `src/ccf/client/errors.py` **already exists** with `TransportError`. `17-05`
  extends it with `BindingError(TransportError)` rather than creating it.
- `ccf.client.__all__` is `[]` and `17-05` sets it to the four D-03 names.
- `decode_outcome` returns a `WireOutcome`; the vessel is validated during
  decode but returned as text. `17-05` parses it where it builds `Result` —
  which is D-12's one place, so nothing is duplicated.
- A `Result`-construction scan (`17-05`'s D-12 assertion) will find zero
  construction sites in this plan's files; the codec never builds one.

## Self-Check: PASSED

All eight created files exist on disk. All three commits exist on
`worktree-agent-aeda7d3533c7aa65f`, branched from `phase-17` @ `7d76205`:

```
6174a5a test(17-04): six sabotage controls, each observed failing
c259e2c feat(17-04): the one codec — encode, decode, and the address recomputed
5c71780 feat(17-04): name the wire — WireRequest, WireOutcome, TransportAdapter
```

Final verification, all re-run against the committed tree:

```
tools.lints --all                                     exit 0
mypy                                                  Success: no issues found in 201 source files
pytest tests/client -q                                34 passed
pytest -q (full, CCF_REQUIRE_HARNESSES=1)             2 failed, 3373 passed, 118 skipped
```

The two failures are `tests/invariants/test_citation_coverage.py`, measured
identical on the pristine pre-`17-04` tree. See **DEF-17-04**.
