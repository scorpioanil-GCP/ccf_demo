# How the surface record works

**Maintainer-facing.** This page is for people working *on* the SDK, not with
it. It describes the machinery that records what the SDK's public surface is,
how that record is kept honest, and why one specific rule about *when* it is
regenerated is the thing that makes any of it mean something.

Nothing here is a Protocol you implement or a contract you author. If you are
adopting the SDK, the pages you want are under Reference → Protocols and
Reference → Definition artifacts.

## The generated manifest

`tools/dump_surface.py` walks `src/` and `runtime/`, and for every module
carrying an `__all__` it records that module's public names and their shapes.
The output is committed at `docs/surface/v0.2-surface.json`.

It records signatures, not prose: docstrings are deliberately excluded, so a
reworded docstring is not a surface change. It is written deterministically —
sorted keys, sorted `__all__`, keyed rather than positional per-name entries,
one trailing newline — so the file is reviewable as a diff and does not shift
under the order a directory walk happened to take.

Three modes, and the difference between them is what keeps the file usable while
work is in flight:

| Mode | Writes | Exit | For |
| --- | --- | --- | --- |
| `make surface` | yes | 0 | Regenerating the committed manifest |
| `--check` | no | 1 on any difference | The phase gate |
| `--report` | no | always 0 | A plan mid-phase, asserting the names it claims to add actually appear |

## Baseline immutability is the load-bearing rule

**`make surface` runs exactly twice in a phase: once at phase start, once at
phase close.** It is not run when a plan lands, and it is not run to make a red
build green.

This is the rule the whole record rests on, and the reasoning is worth carrying:
a manifest regenerated whenever it disagreed with the tree can never disagree
with the tree, so it asserts nothing. Holding it still for the length of a phase
is what turns "the surface changed" into a detectable event rather than a
tautology. The phase-start copy is additionally frozen under its own name, so
the unqualified path is always the *live* manifest and a stale read is
impossible by naming — the alternative, freezing the plain name, would leave
every future maintainer reaching for "the surface manifest", finding the frozen
one, and reading history as present tense.

The rule has a second, more practical half. A whole-tree file cannot be
concurrently regenerated in a dozen parallel worktrees: each would pass its own
check before merge and the tree would be stale after the second merge, on a file
no plan then owns. Single-owner regeneration is why `--report` exists.

## The drift assertion

`tests/test_surface_drift.py` is always on, because `tests/` is an always-on
job — a surface change fails CI on the same commit that causes it, with no new
CI wiring to keep alive.

It asserts **documented drift** rather than bare bytes-equality: the committed
manifest must equal what the generator emits right now, *or* every module whose
entry moved must be claimed by a curated migration-log fragment. That
formulation is what lets the gate stay live through a phase that deliberately
changes the surface. A gate that demanded bytes-equality throughout would be red
for the whole phase and would get switched off, which is how gates die. After
the phase-close regeneration nothing is unclaimed and the assertion degenerates
back to bytes-equality with no code change.

Its limits are stated rather than assumed. It is module-granular and
direction-blind: fragments accumulate and are read as a union, so once any plan
names a module, later drift in that module is claimed for the rest of the
phase — including a *removal* claimed by a fragment that says "added".
Name-level and direction-level completeness is a separate, exact check that runs
once at phase close against the frozen baseline. The two are designed as a
pair — one cheap and always-on, one exact and occasional — and weakening either
without the other is a regression.

## The curated half

The generated manifest says *what* moved. It cannot say why, or what an adopter
should do about it. That is a curated migration log, written incrementally as
plans land — a log assembled retroactively at phase close is a log written *from*
the diff, which is the one thing it is supposed to add information to.

`tools/assemble_surface_changes.py` joins the per-plan fragments into that log,
deterministically, so the assembled document is itself reviewable as a diff and
its staleness is detectable. It **refuses** an entry missing any of its seven
fields — the surface, whether it is public, the change type, before, after why,
and the migration. A fragment missing the last two ships a migration note an
adopter cannot act on, so it fails the build rather than being assembled into
one. The public/private flag must parse to exactly `true` or `false`; a third
value would silently opt the entry out of both directions of the phase-close
completeness check, turning a checked classification into an escape hatch.

## The adjacent generators

The same shape recurs three more times: a generator, a committed baseline, and a
drift gate that fails on the same commit that causes the drift.

| Target | Regenerates | Baseline |
| --- | --- | --- |
| `make schemas` | JSON Schema for every authorable artifact class | `docs/schemas/` |
| `make openapi` | The HTTP surface description | the committed `openapi.json` |
| `make schema-headers` | *(verifies rather than writes)* — that each example artifact's `$schema` header names the class that actually accepts it | the schema tree above |

They exist for the same reason as the surface manifest, one level down: a
generated artifact nobody committed is a claim nobody can check, and a committed
artifact nobody regenerates is a claim that quietly stops being true.

## What to do when one of these is red

- **The drift assertion fails and you changed a public name.** That is the gate
  working. Write the fragment; do not regenerate the manifest.
- **The drift assertion fails and you did not change a public name.** Something
  changed a signature or an `__all__` indirectly. Run the generator in `--report`
  mode to see exactly what moved before deciding anything.
- **A schema or description baseline is stale.** Regenerate it with the target
  above and commit the result in the same commit as the change that caused it.
  A baseline regenerated in its own commit is a baseline whose cause nobody can
  find.
