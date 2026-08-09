# `ccf-demo-adapter` — the out-of-tree proof

A second installable distribution that registers a graph adapter named `demo`
with the CCF SDK through the `ccf.graph_backends` entry-point group.

**It exists to prove the seam, not to be used.** Nothing here is a substrate
anyone should store a graph in. Its backing store is two Python dictionaries
that live and die with the process.

## The one fact it rests on

Adding this adapter changed no line under `src/ccf`.

That is the whole claim of D-11, and it is why this is a separate distribution
rather than a seventh backend inside the SDK. An in-tree backend would prove the
in-repo path works, which is the weaker statement. What needed proving is the
path an actual third party takes: install a package, name it in a manifest, and
have it answer.

Plan 15.4-11 measures the claim over a recorded commit range rather than
asserting it here.

## What it demonstrates, concretely

- **Discovery finds it without importing it.** `declared_names()` reads
  packaging metadata; only `resolve("demo")` imports this package. Listing what
  a deployment has installed does not execute an installed package's
  module-level code.
- **Resolution imports exactly one adapter.** `resolve("demo")` loads this
  distribution's write module and no other adapter's.
- **The registry derives the pin, this package does not declare it.** The
  adapter's version and distribution name on `FabricHandle.adapter` come from
  this distribution's own installed metadata, so a third-party adapter gets its
  replay pin for free and cannot misstate it.
- **Single-writer holds across the boundary.** Two boots on one `graph_name`
  are refused; two boots on different names both succeed. The refusal comes from
  the SDK's boot-token mint, which is the mechanism — not from anything this
  package chose to honour.
- **A reserved name is refused.** `demo` matches the registry's required name
  shape and is not one of the six names the SDK's own adapter package holds. A
  distribution declaring one of those is refused during discovery, before
  anything loads, so a third party cannot answer for a built-in name.

## Installing it

```
python -m pip install -e ./tests/fixtures/ccf-demo-adapter
```

`make install` runs this for you, immediately after the SDK's own editable
install. Order matters: this package imports `ccf`.

Entry points live in build-time metadata, not in `pyproject.toml` as read from
disk, so without an install there is no declaration for discovery to find.

## The install posture is always-on, and here is the ruling

Every development checkout and every CI runner has this adapter installed, so
`ccf backends list` reports a seventh name. That is expected, and it is the
command answering correctly: the question it asks is *what is installed here*,
and here, this is installed.

Three things keep that from reading as a supported substrate:

1. `demo` is a test fixture, not a substrate CCF supports.
2. It is **not** a dependency of the `ccf` distribution, so `pip install ccf`
   never pulls it. The `ccf` distribution's own dependency lists name it
   nowhere, and a test asserts that rather than leaving it to inspection.
3. `make install` is the developer bootstrap, not an adopter's install path.

**The alternative was considered and rejected.** An opt-in
`make install-demo-adapter`, with CI always installing it, keeps a developer's
`ccf backends list` at six names. It was rejected for one concrete reason: plan
15.4-11 adds a parity test asserting that the conformance parameter lists and
`declared_names()` agree **in both directions**. Under opt-in, a developer who
runs `make install` and then `make ci-core` gets a red parity test, because
`demo` is a parameter and is not installed. The proof would then be conditional
on a step nothing reminds anyone to take — which is the exact failure mode that
parity test exists to close.

The accepted cost is real and bounded, and the boundedness is what point 2
above asserts.

## Two scope statements, said rather than left to be discovered

**This tree is not type-checked.** `[tool.mypy] files` in the SDK's own
`pyproject.toml` covers `src` and `runtime`; this fixture is in neither. The
*contracts* it implements are strict-checked, and the conformance suite is what
proves this adapter satisfies them. A third-party adapter is in exactly this
position, which is part of what makes the fixture representative.

**The CINV-02 structural lints do not walk this package.** Their tree scope is
`("src", "runtime")` — CCF's lints govern this repository's core, and a
third-party adapter is governed by the Protocol contracts and the conformance
suite instead. That is a scope statement, not a hole, and saying so is the
difference between the two. The one lint that *does* walk this tree is the
No-Hardcoding rule, whose scope includes `tests`.

Concretely, the rule that matters here is the one restricting imports of the
SDK's neutral write base. It denies that module to core modules outside L2 and
the composition root, and it cannot reach a third-party adapter. **The
single-writer invariant does not depend on it reaching one.** The mechanism is
the boot-token mint, which refuses a second live writer for one graph identity
whoever asks; the lint is the layer that stops a core module reaching for the
writer by accident. Both halves are true and both are stated, here and in the
write module's own docstring.

## What is in here

| Path | What it holds |
| --- | --- |
| `pyproject.toml` | The distribution, and the `ccf.graph_backends` declaration |
| `src/ccf_demo_adapter/store.py` | The dicts, the store, and the read seam |
| `src/ccf_demo_adapter/demo_write.py` | The connection contract, the transaction, the writer, and `REGISTRATION` |

The entry point names the **write** module's `REGISTRATION`. Naming the read
module would put the writer factory on an unguarded import path; the write
module may import the read module freely, and the reverse is forbidden.

## What it does not do

It answers no query natively. Every query is answered through the SDK's shared
fallback over materialized records, which is a first-class outcome rather than a
degraded one — a conformant answerer answers any well-formed query, degrading
internally where it holds no native translation. That is the tier a third-party
adapter reaches without reimplementing the query surface, so it is the tier this
proof exercises.

## What to change first, if you are adapting it

`store.py`'s two dictionaries and `demo_write.py`'s nine transaction operations.
Everything else — the record, the connection contract, the entry-point
declaration — is the shape any adapter has, and is closer to boilerplate than to
substrate work.
