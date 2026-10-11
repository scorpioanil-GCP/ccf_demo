# 380-09 (blocker 1, ruled 2026-10-11 12:35) — `preferred` guidance carries its kind, so a decimal and a name no longer share an address

Ruled by Dave, adopting Grok's review of `GROK-BRIEF-7`: *"Take A. Build it."* *"Explain the address
claim precisely: existing accepted forms retain their addresses; numeric preferred guidance gains a
distinct address. Do not imply that old ambiguous bytes can reveal their original type."* Built in
lane `b1-preferred-kind`, red tests first. The registry is unchanged.

**The defect.** The canonical form renders a `Decimal` as a quoted string, and for `preferred` the
class deliberately does not read a quoted number back as a decimal (*"guessing between them would be the
silent repair this module refuses everywhere else"*). So `PolicyConstraint(preferred, Decimal("4"))` and
`PolicyConstraint(preferred, "4")` were unequal with identical canonical bytes and one content address,
and since the sixth round the registry refused the decimal form, because its reconstruction came back as
text.

**The address claim, precisely.** Every form accepted before this change — a `preferred` name
(including a name that looks like a number, such as `"4"`), `maximum`, `minimum`, `allowed_set`,
`required` — renders byte for byte as before and **keeps its address** (pinned by measured hash in
`tests/controlplane/test_preferred_constraint_kind.py`). **Numeric `preferred` guidance gains a distinct
address**, because its bytes now carry `"preferred_decimal": true`. Bytes written before the flag
existed carry no flag and are read as the name form; **they cannot reveal an original type they never
recorded**, and none needs to, because no accepted decimal form existed — the registry refused it.

**The hash-transparency marker, widened for this field only.** On every other field the marker's
sentinel means *"the field did not exist"*, so yesterday's artifacts keep their bytes. On
`preferred_decimal` the sentinel `False` means *"this is the name form"* — **a kind, not a migration**.
The widening is accepted for this field alone (Grok, 12:35: *"Do not use the marker for any other field
in this lane."*).

**Replay.** A decision pins the constraint version it resolved against; replay resolves that exact
version. Before the flag, a pin to the shared address could not say which of the two values applied.
Now each pins its own address, and `tests/replay/test_engine_rehydration.py::
test_a_decisions_pinned_preferred_constraint_replays_with_its_own_value_and_type` shows replay resolving
`Decimal("4")` as a `Decimal` and `"4"` as a `str`. The recorded resolution's own guidance entries render
values as text (`ParameterBound.value`), so the pin, not that copy, is what carries the type.
`preferred` remains non-refusing guidance; no decision changes.

## ccf.controlplane.artifacts.PolicyConstraint

- Surface: ccf.controlplane.artifacts.PolicyConstraint
- Public surface: true
- Change type: behavior
- Before: `preferred` guidance with a `Decimal` value and with the equal-looking name shared one canonical form and content address; the registry refused the decimal form.
- After: a hash-transparent field `preferred_decimal: bool = False` records the kind: set by the class when the operator is `preferred` and the value a `Decimal`; a document's quoted value is read as a `Decimal` only when it carries `preferred_decimal: true`; any other combination of flag, operator and value is refused. Existing accepted forms keep their bytes and addresses; numeric `preferred` guidance gains its own and round-trips the registry as a `Decimal`.
- Why: blocker 1 of the `D-IMPL-380` sixth round, ruled 2026-10-11 12:35 MST (option A of `GROK-BRIEF-7`).
- Migration: none for existing constraints. In Python the class sets the flag for a `Decimal` or a whole number. In a document, numeric `preferred` guidance is written as a quoted number with `preferred_decimal: true`, because a quoted value under `preferred` is otherwise a name; a document whose flag disagrees with its operator and value is refused. An unquoted whole number under `preferred` still loads as numeric guidance, as it did before the flag.
