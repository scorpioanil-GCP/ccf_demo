---
phase: 19-the-client-seam-integrity-checks-must-be-able-to-fail-insert
reviewed: 2026-08-20T00:00:00Z
depth: deep
files_reviewed: 6
files_reviewed_list:
  - tests/client/test_surface.py
  - tests/client/conformance/suite.py
  - tests/client/conformance/test_inprocess_conformance.py
  - tests/client/conformance/test_mcp_conformance.py
  - runtime/ccf_runtime/http_api/routes/product.py
  - runtime/ccf_runtime/mcp/egress.py
  - tests/products/test_door_answer.py
findings:
  critical: 2
  warning: 6
  info: 0
  total: 8
status: issues_found
---

# Phase 19: Code Review Report

**Reviewed:** 2026-08-20
**Depth:** deep (adversarial, with out-of-tree sabotage runs)
**HEAD:** `2119ca6` on `main`, tree clean, `make ci` green
**Status:** issues_found

## Summary

The phase's own thesis — *a check that cannot fail is the defect* — is the standard
this review applied to the phase's own checks. Three of the artifacts it shipped do
not meet it.

The headline result is **demonstrated, not argued**: an adapter that constructs the
outcome with `WireOutcome.model_validate(...)`, echoes the question it was handed, and
answers a different one, is scored **zero construction sites** by `C-17`'s gate, passes
`mypy --strict`, passes **both** conformance tamper legs, and returns a forged answer to
`ProductClient.ask` with no exception raised. `D-IMPL-151` finding `B0` is re-openable
with the full build green. Every step of that was run, not read.

Two further checks were sabotage-tested and found unable to fail for the reason they
name (`WR-02`, `WR-03`), and one compensating control named in shipped prose was
measured inert (`WR-01`).

Method note: every claim below marked **VERIFIED** was produced by running the shipped
functions against out-of-tree subjects reached by `sys.path`. Nothing under version
control was edited; `git status --porcelain` is empty at the end of this review as it
was at the start.

Two rejected candidate findings, recorded so they are not re-derived: `suite.py`'s
`_reversing_subject` control **is** as honest as `19-04` admitted — its docstring states
both halves of the involution argument including the identity-edit gap and names where
that gap is caught, which is the standard, and the shipped legs do go red on an identity
edit even though the control does not. And `door_answer` itself is correct: one
`canonical_bytes` call over the vessel, `content_address` derived from those same bytes,
`echo` never derived from `resolved_request`.

---

## Critical Issues

### CR-01: The `C-17` outcome gate does not see pydantic's construction spellings, and a forging adapter passes every gate in the build

**File:** `tests/client/test_surface.py::_outcome_construction_sites`
(and its docstring's "Not detectable, and named rather than pretended away" list on
`tests/client/test_surface.py::count_outcome_construction_sites`)

**Issue.** The walk counts exactly two shapes: `ast.Name` calls resolved through
`_outcome_aliases`, and `ast.Attribute` calls whose `attr` is `WireOutcome` or
`DoorOutcome`. Every pydantic construction classmethod is an `ast.Attribute` call whose
`attr` is `model_validate`, `model_validate_json`, `model_construct`, `model_copy`, … —
none of which are in `_OUTCOME_NAMES`. So `WireOutcome.model_validate({...})` scores
**zero**.

This is not a hypothetical spelling. It is the shipped idiom of this very seam:
`ccf.client.codec::decode_outcome` builds the outcome with
`WireOutcome.model_validate_json(raw)`, `ccf.products.door::door_question` builds the
request with `WireRequest.model_validate_json(...)`, and there are 25 `model_validate*`
call sites across `src/` + `runtime/`. An adapter author copying the one-line idiom from
the module the gate is protecting defeats the gate.

Worse, the repo already ships the machine-readable answer one package over:
`ccf.products.gates::PYDANTIC_MODEL_FORMS` is a public frozenset of all twelve
spellings, documented as *"the machine-readable statement of what this type is not"* and
*"adding a spelling here adds the refusal on both channels at once."* `C-17`'s gate,
written to close a construction hole, reuses none of it.

**Failing scenario — VERIFIED end to end.** An in-tree adapter:

```python
from ccf.client.adapters.inprocess import InProcessAdapter
from ccf.client.codec import encode_outcome
from ccf.client.wire import WireOutcome, WireRequest

class ForgingAdapter(InProcessAdapter):
    def ask(self, request: WireRequest) -> bytes:
        crossed = request.model_copy(update={"parameters": {k: v + 1000 for k, v in request.parameters.items()}})
        honest = WireOutcome.model_validate_json(super().ask(crossed))   # answer to question B
        forged = WireOutcome.model_validate({                            # <-- a construction
            "request": request.model_dump(),                             # echo question A
            "product_json": honest.product_json,
            "content_address": honest.content_address,
            "replay_ref": honest.replay_ref,
            "refusal": None,
        })
        return encode_outcome(forged)
```

Measured against `2119ca6`, with the module placed under a directory handed to the
shipped functions:

```
C-17 counts:            {'.../forging_adapter.py': 0}
C-17 gate VERDICT:      PASSES (no adapter constructs the outcome)
client raised:          NO
honest address:         3147e9fb…9a22
forged address:         0e3b2ba4…5871      <- a different question's answer
caller got a DIFFERENT question's answer, undetected: True
```

`check_outcome` passes because the echo is the request that was handed in;
`verify_content_address` passes because the address and the vessel are the honest
producer's matching pair. Both integrity checks are inert again, which is the exact
condition Phase 19 exists to end. `mypy --strict` is satisfied because the seam returns
`bytes`.

**Fix.** Count the construction classmethods on a name that resolves to the outcome
class, and reuse the existing enumeration rather than minting a second one:

```python
from ccf.products.gates import PYDANTIC_MODEL_FORMS

_CONSTRUCTING_FORMS: Final[frozenset[str]] = frozenset(
    {"model_validate", "model_validate_json", "model_validate_strings",
     "model_construct", "model_copy", "construct", "parse_obj", "parse_raw",
     "parse_file", "from_orm"}
) & PYDANTIC_MODEL_FORMS

# inside the walk, in addition to the two existing rules:
elif isinstance(function, ast.Attribute) and function.attr in _CONSTRUCTING_FORMS:
    value = function.value
    if (isinstance(value, ast.Name) and value.id in aliases) or (
        isinstance(value, ast.Attribute) and value.attr in _OUTCOME_NAMES
    ):
        found += 1
```

Ship it with a control in the `CONTROL 13-17` parametrize block carrying
`_FORGES_THROUGH_MODEL_VALIDATE`, and add a vacuity sibling asserting that a *bare*
`SomethingElse.model_validate(...)` is **not** counted, so the new rule cannot pass by
counting everything.

---

### CR-02: The same gate — and `D-12`'s `Result` gate — resolve no relative imports, so an in-package rename defeats both

**File:** `tests/client/test_surface.py::_outcome_aliases` and
`tests/client/test_surface.py::_result_aliases`

**Issue.** Both alias resolvers match on `node.module in _OUTCOME_MODULES` /
`_RESULT_MODULES` — absolute dotted names only. A relative `ast.ImportFrom` carries
`node.level > 0` and a `node.module` that is the *tail* (`"wire"`, `None`, `"result"`),
so it never matches. Adapters live at `src/ccf/client/adapters/`, one package below
`ccf.client.wire`: `from ..wire import WireOutcome` is the idiomatic relative spelling
and the project has **no** lint banning relative imports (there is no ruff configuration
in `pyproject.toml` at all; only `mypy`).

**Failing scenario — VERIFIED** by running the shipped functions:

```
relative-import-two-dots     outcome_sites=0 aliases=[]     # from ..wire import WireOutcome
relative-import-door         outcome_sites=0 aliases=[]     # from ...products.door import DoorOutcome
subclass                     outcome_sites=0 aliases=['WireOutcome']
baseline-plain               outcome_sites=1 aliases=['WireOutcome']

relative-result              result_sites=0                 # from .result import Result
relative-result-2            result_sites=0
baseline-result              result_sites=1
```

Note the third row: `class Forged(WireOutcome): ...` then `Forged(request=…)` is a
construction of the outcome shape that the gate scores zero. The docstring's
"not detectable" list names only `getattr` dispatch and `model_copy` re-labelling —
relative imports and subclassing are neither named nor caught, so the gate's stated
limits are narrower than its actual ones, which is the honesty standard this phase set
for itself.

The `D-12` half is the same defect against a Dave ruling:
`assert_one_result_construction_site` and
`test_the_one_construction_site_is_the_client_decoder` would both stay green if a second
module constructed `Result` through `from .result import Result`.

**Fix.** Resolve relative imports against the module's own package path, and refuse what
cannot be resolved rather than silently scoring zero — the discipline this module's own
header states for unreadable roots and unparsable files:

```python
def _outcome_aliases(tree: ast.Module, *, module_package: str) -> set[str]:
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        resolved = (
            node.module
            if node.level == 0
            else _resolve_relative(module_package, node.level, node.module)
        )
        if resolved in _OUTCOME_MODULES:
            ...
```

For the subclass shape, count `ast.ClassDef` whose bases resolve to an outcome alias and
add the resulting local name to `aliases` before the call walk. Add a control per
spelling.

---

## Warnings

### WR-01: The compensating control the gate's docstring names for re-labelling is inert — both tamper legs pass against a fully forging adapter

**File:** `tests/client/test_surface.py::count_outcome_construction_sites` (its closing
paragraph), against `tests/client/conformance/suite.py::assert_a_crossed_echo_is_caught`
and `tests/client/conformance/suite.py::assert_an_altered_vessel_is_caught`

**Issue.** The docstring concedes that `model_copy` re-labelling is invisible to the
walk and then says: *"What covers the second is not this gate. It is `19-04`'s
conformance obligation, which wraps every registered adapter in a byte-corrupting
decorator and requires the client to raise — a leg an adapter author neither writes nor
can opt out of."*

That obligation does not cover it, and cannot. `_Tampering` proves the **client's**
checks fire on corrupted bytes. A forging adapter's bytes are honest-looking and
self-consistent; corrupting them still makes the client raise, so the leg passes. The
leg measures the client, never the adapter's honesty.

**Failing scenario — VERIFIED.** Running the shipped legs against the `CR-01`
`ForgingAdapter` bound as an `AdapterSubject`:

```
assert_a_crossed_echo_is_caught:   PASSES against a FORGING adapter
assert_an_altered_vessel_is_caught: PASSES against a FORGING adapter
```

Limb 1 passes (the tamper is caught), limb 2 passes (one factory, one type), limb 3
passes (the untampered forging client serves rather than raising — it serves the *wrong*
answer, which the limb does not look at).

**Fix.** Delete the compensating-control sentence and replace it with the measured
statement, in the two-sided form this phase uses elsewhere: *"the tamper legs prove the
client's checks are live on every registered adapter; they do not and cannot prove an
adapter is honest, because a forging adapter's bytes are self-consistent and a corrupted
copy of them still raises — measured."* If a real control is wanted, the shape is a
conformance leg that asks question A through the subject and asserts the served
`content_address` equals the address the **door** produced for A when driven directly —
i.e. an operand the adapter did not supply.

---

### WR-02: `test_door_answer.py`'s named sabotage control for the content address cannot fail

**File:** `tests/products/test_door_answer.py::test_a_single_space_inside_the_vessel_breaks_the_address_it_claims`

**Issue.** The module header sets the standard — *"Every assertion carries a control
that shows it can fail"* — and this test's docstring claims to be it: *"the named
sabotage control: the assertion above can fail."* It does not sabotage the assertion's
subject. It edits `parsed.product_json` **after** the door produced it and asserts
`sha256(edited) != parsed.content_address`. That inequality is a property of SHA-256, not
of `door_answer`. It holds for **any** value of `content_address`.

**Failing scenario — VERIFIED.** Replaying the control's arithmetic against three
doors — an honest one, one whose address came from a second serialization, and one
emitting a constant:

```
B[honest                  ] main_assertion_passes=True   control_passes=True
B[second-serialization bug] main_assertion_passes=False  control_passes=True
B[constant garbage        ] main_assertion_passes=False  control_passes=True
```

The control's verdict is invariant under the sabotage it claims to detect. (The
*primary* assertion, `test_the_claimed_address_is_sha256_of_the_vessel_beside_it`, is
sound and does go red under both sabotages — the property is measured; what is not
measured is the claim that it can be.)

**Fix.** Sabotage the producer, not the wire. Monkeypatch or locally shadow the address
computation and assert the primary test's assertion goes red:

```python
def test_control_the_address_assertion_fires_when_the_door_claims_a_second_render(
    a_served_value: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    real = hashlib.sha256
    monkeypatch.setattr(
        ccf.products.door.hashlib, "sha256",
        lambda data: real(data + b" "),   # a door that hashes a second rendering
    )
    parsed = _answer(a_served_value, _echo(), asked_at=RESOLVED_AT)
    assert parsed.content_address != hashlib.sha256(
        parsed.product_json.encode("utf-8")
    ).hexdigest()
```

Keep the existing test — its `ContextProductContract.model_validate_json(tampered)` limb
is a genuine discrimination guard — but relabel its docstring to what it holds: *the
edited vessel still parses, so a client-side address failure is attributable to the
address rather than to the parser.*

---

### WR-03: The "and the fact it was not derived from" assertion in the echo test cannot fail

**File:** `tests/products/test_door_answer.py::test_an_absent_boundary_is_echoed_absent_though_the_door_answered_at_one`

**Issue.** The second assertion reads
`assert RESOLVED_AT.isoformat() not in canonical_bytes(parsed.request).decode("utf-8")`
and is commented *"the door answered at an instant, and that instant is nowhere in the
echo."* The two sides use different renderings of the same instant, so the substring can
never be present regardless of what the door does.

**Failing scenario — VERIFIED.** Canonical rendering of `datetime(2026, 8, 19, 9, 30,
tzinfo=UTC)` inside a `WireRequest`:

```
canonical echo text: {"parameters":{},"product_id":"p","temporal_boundary":"2026-08-19T09:30:00.000000Z"}
H: RESOLVED_AT.isoformat() in canonical text ? False
```

`datetime.isoformat()` yields `2026-08-19T09:30:00+00:00`; the canonical serializer
yields `2026-08-19T09:30:00.000000Z`. A door that substituted its resolved instant
straight into `echo.temporal_boundary` would leave this line green. The leg is not
vacuous overall — the preceding `assert parsed.request.temporal_boundary is None` does
hold the property — but the assertion advertised as the independent second witness is
decoration.

**Fix.** Compare against the canonical spelling the wire actually carries, or drop the
line as redundant with the `is None` above it:

```python
from ccf.contracts.canonical import canonical_timestamp
assert canonical_timestamp(RESOLVED_AT) not in canonical_bytes(parsed.request).decode("utf-8")
```

---

### WR-04: The MCP door's cross-check covers only the three axes `WireRequest` carries; three of the four §6.3 axes it names as "the question" have no second copy and are not in the declared residual

**File:** `runtime/ccf_runtime/mcp/egress.py::build_egress_server::request_context_product`

**Issue.** The handler's own docstring defines the question as *"whitepaper §6.3's four
axes — `subject`, `intent`, `freshness`, `asked_at`"*, and then declares exactly one
residual: *"`asked_at` is a value with no second copy anywhere, and a transport altering
`asked_at` alone is **undetected**."*

The cross-check (`asked_wire.product_id` vs `product_class`, `asked_wire.parameters` vs
`parameters`, `asked_wire.temporal_boundary` vs `asked_at`) covers exactly the three
members `ccf.products.door::WireRequest` declares. `subject`, `intent` and `freshness`
are tool arguments the adapter sources from client-side `binding.yaml`
(`ccf.client.adapters.mcp_stdio` builds them from `question.subject/intent/freshness`),
they are forwarded verbatim into `ProductRequest`, and they appear **nowhere** in the
outcome. So `asked_at` is not the only single-copy axis; it is one of four.

**Failing scenario — VERIFIED (structure), READ (consequence).** Driving the shipped
in-process path and dumping the envelope:

```
echo fields: ['parameters', 'product_id', 'temporal_boundary']
'subject' anywhere in outcome envelope (excl vessel): False
```

A proxying transport that alters `subject` reaches `ProductRequest.subject`, which
`ccf.products.request::request_seed_uris` turns into the graph-query seed set and which
lands in the Decision Replay record's `ContentGenerationPath.request`. The echo, the
content address and every client-side check agree perfectly. Honesty caveat, stated
because this review's own standard requires it: against the **shipped fixture** the
substitution does not change the served address (measured: identical addresses under an
altered `subject`), because that deployment's projection does not seed from the subject.
The gap is therefore *currently* an audit-record gap rather than a served-content gap —
but it is a gap in a list documented as complete, and any deployment whose projection
seeds from the subject converts it into a served-content gap with no code change.

**Fix.** Two edits, neither of which widens the seam:

1. In `egress.py`, replace *"`asked_at` is a value with no second copy anywhere"* with
   the true statement: *"three of the four §6.3 axes — `subject`, `intent`, `freshness`
   — cross this pipe exactly once, because `WireRequest` carries none of them; the
   fourth, `asked_at`, crosses twice only when the caller sent a concrete `as_of`."*
2. Add a fifth entry to `ccf.client.codec`'s "What they do not detect" list naming those
   three axes, and record whether closing it (by carrying them on `WireRequest`) is a
   `D-IMPL` question or an accepted limit. The list is currently introduced as
   *"Four cases, named because a claim that does not state its limits is the claim this
   phase exists to replace"* — it is short by three.

---

### WR-05: `test_every_exported_leg_has_a_control_here` measures table membership, not control existence

**File:** `tests/client/conformance/test_the_suite_fires.py::test_every_exported_leg_has_a_control_here`
(the control module for the in-scope `tests/client/conformance/suite.py`)

**Issue.** The test asserts `exported == set(LEG_CALLS)`. `LEG_CALLS` is used in exactly
two places (verified by grep): this equality, and the parametrize list for
`test_every_leg_refuses_an_empty_collection_of_adapters`. It is a table of *empty-
collection call kwargs*, not a registry of controls. A new leg added to `suite.__all__`
with a `LEG_CALLS` row and **no** failure-observing control passes this gate — which is
precisely the state its docstring says it prevents: *"A leg added to the suite without a
control is a leg nobody has watched fail."*

The same weakness applies within existing legs: `assert_a_crossed_echo_is_caught`'s
second limb (`type(inner) is not type(witness)`) has no control anywhere in the module —
no subject exists whose factory returns two types — and the third limb (untampered does
not raise) is never observed firing either. Only limb 1 is controlled, by
`_reversing_subject`.

**Fix.** Make the registry name the controls rather than the kwargs, so the equality
measures what the docstring claims:

```python
#: leg name -> the controls that have been observed making it fail.
LEG_CONTROLS: Mapping[str, tuple[str, ...]] = {
    "assert_a_crossed_echo_is_caught": (
        "test_the_crossed_echo_leg_fires_when_the_tamper_is_not_caught",
    ),
    ...
}

def test_every_exported_leg_has_a_control_here() -> None:
    assert exported == set(LEG_CONTROLS)
    for leg, controls in LEG_CONTROLS.items():
        assert controls, f"`{leg}` is registered with no control"
        for control in controls:
            assert callable(globals().get(control)), (
                f"`{leg}` names control `{control}`, which does not exist here"
            )
```

Then add the missing limb-2 control: an `AdapterSubject` whose `connect` returns
`InProcessAdapter` on its first call and a trivial subclass on its second, and assert the
leg fires naming both type names.

---

### WR-06: `test_door_answer.py::_answer` hands `door_answer` a `resolved_request` that contradicts the value being rendered, so the refusal-echo leg exercises a composition no door emits

**File:** `tests/products/test_door_answer.py::_answer`, consumed by
`tests/products/test_door_answer.py::test_a_refused_outcome_carries_the_echo_and_nothing_of_the_served_half`

**Issue.** `_answer` hard-wires
`resolved_request=_typed({PARAMETER: THRESHOLD}, asked_at=asked_at)` for every call. The
refusal fixture `a_refusal_value` is produced by resolving `_typed({})` — the question
that omits the required parameter and is therefore refused. So `door_answer` is called
with a refusal caused by question *X* and a `resolved_request` naming question *Y*, and
`ccf.products.door::door_refusal` builds the refusal's request identity from *Y*.

Both shipped doors pass one object (`egress.py` passes `asked`;
`ccf.client.adapters.inprocess::InProcessAdapter.ask` passes `typed`), so the outcome
this test inspects is a shape no door produces. The leg it supports —
*"a crossed refusal must be exactly as detectable as a crossed vessel"* — is the one
where the request identity riding on the refusal matters most, and
`suite.py::_refusal_view` compares `refusal.request` across transports.

**Fix.** Thread the resolved question through, so the fixture that produced the value
and the request handed to the door are the same object:

```python
def _answer(
    resolved: object, echo: WireRequest, *, asked_at: datetime,
    resolved_request: ProductRequest | None = None,
) -> DoorOutcome:
    return DoorOutcome.model_validate_json(
        door_answer(
            resolved,
            echo=echo,
            resolved_request=resolved_request
                or _typed({PARAMETER: THRESHOLD}, asked_at=asked_at),
            product_class=PRODUCT_ID,
            version=PRODUCT_VERSION,
        )
    )
```

and have the refusal leg pass `_typed({}, asked_at=RESOLVED_AT)` — the question that
actually caused the refusal. Then assert `parsed.refusal.request` names *that* question,
which is the property the leg is really about and which nothing asserts today.

---

## Reviewed and found sound

Recorded so a later reader does not re-derive them:

- `ccf.products.door::door_answer` — one `canonical_bytes` call over the vessel,
  `content_address` derived from those same bytes, `echo` carried verbatim and never
  derived from `resolved_request`. The `C-02`/`C-15` separation holds structurally.
- `tests/client/conformance/suite.py::_cross_the_echo` and `_alter_the_vessel` — both
  are genuine involutions for every input, both discriminate on their own refusal
  wording, and both check the **exact** exception type rather than catching
  `BindingError` as a caught tamper.
- `tests/client/conformance/test_the_suite_fires.py::_reversing_subject` — its
  "fails safe" claim is stated two-sidedly, including the identity-edit case it does
  *not* catch and where that case is caught instead. This is the honesty standard; it
  meets it.
- `runtime/ccf_runtime/http_api/routes/product.py::build_router::_echo` — the echo is
  built from what the route parsed off the request line, `_echo` runs before the
  resolver so an unrepresentable question is refused rather than served with a missing
  sibling, and the absence of a `C-18` cross-check on this door is correctly recorded as
  a measurement (there is genuinely one operand). `DIV-4` — the HTTP door's missing
  refusal channel — is declared in the module docstring rather than hidden.
- `runtime/ccf_runtime/http_api/routes/product.py::build_router::_parameters` — refuses
  non-JSON and non-object rather than defaulting to `{}`; no injection surface (parsed
  with `json.loads`, carried verbatim, validated at the resolver).
- No hardcoded secrets, no `eval`, no path traversal, no harness import in `src/` was
  found in any reviewed file. `test_inprocess_conformance.py` and
  `test_mcp_conformance.py` read every product identity and parameter name out of the
  deployment's own documents, satisfying the No-Hardcoding Rule (§6.4) as scoped to
  `tests/`.

## Tree state

`git status --porcelain` empty at HEAD `2119ca6` before and after this review. All
sabotage subjects were written under the session scratchpad and reached by `sys.path`;
no tracked file was modified. No foreign uncommitted state was observed.

---

_Reviewed: 2026-08-20_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
