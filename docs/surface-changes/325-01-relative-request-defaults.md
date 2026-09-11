# D-IMPL-325 — a request default may be declared relative to the request's own instant

Applied 2026-09-10 under `D-IMPL-325` (Dave), on cp-07's `CP07-F-03`:
`ProductRequestContract.defaults` holds literal values, so `CP-SPEC-007` §B.2's
declared `since` default of *minus 365 days* could only be authored as the
absolute date `"2024-09-01"` — a value that **ages silently**. On the day it was
written it meant two years of history; a year on it means three, the fan-out
grows, and nothing anywhere says the default drifted.

## What did NOT change, stated first

- **`defaults` is untouched and stays literal-only.** Dave, ruling 1: *"Keep
  `defaults` literal-only and add `relative_defaults`. Do not overload
  `defaults` with marker objects."* Every existing default resolves exactly as
  it did, through the same loop, with the same authority and the same pin.
- **No committed contract's content address moves.** `relative_defaults` is
  hash-transparent at the empty mapping (`D-IMPL-243`), which is what every
  contract written before this field says and still says. Measured by
  `tests/contracts/test_hash_transparency.py`, whose `ProductRequestContract`
  base-tree digest still reproduces.
- **Nothing is recomputed at replay.** What the Decision Replay record carries
  is the **resolved literal** under authority `default` with the contract's own
  pin — never the offset. Dave: *"Replay records the resolved absolute value and
  `authority=default`, not a rule that gets recomputed later."*
- **No example changed.** The SDK capability lands and is tested by itself;
  cp-07's adoption of it is a separate step, per Dave: *"Don't mix example
  republishing into the SDK repair."*
- **`resolve_effective_request` is still pure.** It reads no clock. The instant
  is `request.asked_at`, which the function already evaluates constraint
  effectivity at.

## THE VALIDATION SPLIT, because it is the part a reader will get wrong

A relative default's value **does not exist until `asked_at` exists**, so the
declaration-time contradiction check that `defaults` gets against
`argument_domains` has nothing to read here. Dave ruled against forbidding the
combination: *"Do not forbid `relative_defaults` when an `argument_domain`
exists."* Instead:

- **At declaration** — the parameter exists, is not inert, carries exactly one
  default authority, and its declared type can hold the requested render.
- **At request time** — compute `asked_at + offset_seconds`, render it, then run
  the normal domain and conformity checks on the resulting value.

So a computed date outside its governed domain is a request-time refusal. Dave:
*"That is not weaker governance; the value simply does not exist until
`asked_at` exists."*

## ccf.products.request.RelativeDefault

- Surface: ccf.products.request.RelativeDefault
- Public surface: true
- Change type: added
- Before: absent — a request contract could declare only literal defaults, so a relative window had to be authored as an absolute date that ages, or computed in deployment code (a governance value back in the spine, and a second authority for one bound — `D-IMPL-315`)
- After: a typed sub-contract carrying `offset_seconds: int` (negative; the SDK's existing duration vocabulary, per `HalfLifeEntry.half_life_seconds`) and `render: Literal["date", "timestamp"]` (declared, never inferred from JSON Schema `type: string`), plus `resolve(asked_at)` returning the literal that instant means
- Why: a default that ages silently is a governance value nobody can see drift; declaring the offset keeps the value a Control Plane artifact and keeps it honest on every day the product is asked
- Migration: none required — `ProductRequestContract.relative_defaults` defaults to the empty mapping, which is what every existing contract declares and hashes as. To adopt, move a literal date default into `relative_defaults` as an offset and a render; a parameter may appear in `defaults` or `relative_defaults`, never both

## Regression evidence

`tests/products/test_relative_defaults.py`: 29 tests across the declared shape,
the four declaration-time refusals (named together in one message), resolution
against `asked_at`, both renders, caller precedence, the replay literal, the
domain split in both directions, the declared-artifact round trip, and the hash
distinction in both directions (transparent at empty; a populated mapping — and
each distinct window and render — a distinct contract identity).

Sabotage-verified, five ways, each on a restored tree: the resolution branch
removed (8 red), a zero offset accepted (1 red), duplicate default authority
allowed (2 red), the render/type check removed (2 red), and the
hash-transparency marker flipped to `False` (1 red). The clock control is a
scratch copy of `constraints.py` resolving from `datetime.now` instead of
`request.asked_at`, asserted GREEN on the tree and RED on the copy, with the
needle count checked before the mutation so a drifted needle fails loudly
rather than producing a copy identical to the original.
