# dr-02 — findings

Classified under `docs/EXAMPLE-EVALUATION-CRITERIA.md` §B before remediation.
A `PKG-F-NN` id resolves here.

| id | category | disposition |
| --- | --- | --- |
| `PKG-F-01` | — · the gate working | recorded, not repaired — the packager was corrected |
| `PKG-F-02` | example defect (mine) | **fixed** — a module named after an installed distribution |
| `PKG-F-03` | 4 · example limitation | recorded; `D-IMPL-347` B2 is the route if it is ever wanted |
| `PKG-F-04` | — · proof-machinery defect, mine | corrected before close, recorded not swapped |
| `PKG-F-05` | 2 · launch ergonomics | **CLOSED 2026-09-23** — the checker now sees the gated spines |
| `PKG-F-06` | — · working as designed | recorded so it is not re-derived |

---

## `PKG-F-01` — the smoothing gate refused its own author, on the first honest run

**Not a defect. The strongest evidence in this rung.**

The shipped packager's collateral renderer wrote:

> *"3 asset(s) secure this facility: …"*

`3` is `len(assets)` — a figure the packager **computed**, and one the
substrate does not carry anywhere. The serve refused:

> *section `'collateral'` states the figure `'1'`, which the substrate does not
> carry. The packaging moved the conclusion (whitepaper §7.10.4)*

This is exactly the Mode 2 failure mode §7.10.4 names, produced by accident,
caught by the mechanism rather than by review, against the person who wrote
both halves. **The prose was changed, not the gate.** The renderer now states
what it was given and nothing it derived.

Worth keeping because a gate that has never refused anything real is a gate
nobody has tested.

## `PKG-F-02` — a module named `packaging` is shadowed by an installed distribution

**Example defect, mine. FIXED** — renamed `memo_packaging.py`.

`packaging` is an installed distribution in this venv. A tree module by that
name is reachable or shadowed depending on `sys.path` order; measured
2026-09-23, the test suite imported the *distribution* and failed on
`PackagedSection`.

It is `AIA-F-07`'s bare-name collision in a new costume — a tree's module names
share one namespace with everything installed beside them, not only with the
other trees. `tests/examples/tree_import.py` closes the cross-tree half; this
half is a naming discipline nothing enforces.

## `PKG-F-03` — an unreachable upstream door is a defect, not a determination

**Category 4 (example limitation), recorded.**

When the upstream door is unreachable the MCP client raises
`McpServerUnreachable`, and it propagates rather than becoming a governed
refusal. That is correct as it stands: the upstream did not *refuse*, it did
not *answer*, and the two are different claims.

`D-IMPL-347` B2 is the route if a deployment ever wants the conversion — it
would declare `McpServerUnreachable` in the class's `seam_refusals` with a
cause and an error code. This class declares none, deliberately: whether an
unreachable substrate means *unavailable* or *broken* is a product judgement,
and this rung has no reason to make it.

## `PKG-F-04` — the sabotage passed while its own positive control failed

**Proof-machinery defect, mine. Corrected before close, recorded rather than
swapped out.**

`PKG-G04`'s sabotage replaces the packager with one that states an unsupported
figure. The first version patched `memo_packaging.DeterministicPackager` — but
`deployment.py` binds that class by `from`-import at module load, so the
deployment kept whatever it captured first. The liar's run refused (correctly),
and then **the honest control refused too**, because the liar was still in
force.

The patch now targets `deployment.DeterministicPackager`, where the name is
actually used. **The positive control is the only reason this was caught** — a
sabotage asserted on its own would have read as a working gate.

## `PKG-F-05` — this rung's gate roster is not held to its tests by any checker

**Category 2 (launch ergonomics CANDIDATE), raised with the gap measured.**

`tools/check_product_gates.py` globs `examples/cp-*` **by construction** — its
own docstring says `hw1-*` and `s1-*` are outside it. `dr-02` declares eight
gates and serves a product, and the checker reported **29 trees unchanged**
after this thirtieth serving tree appeared.

**A count that does not move when its population does is measuring something
else.** This is the same shape as the `make gate-tools` incident, where the
same `469 passed` was reported before and after ten tests were added to a suite
the target never reached.

### `PKG-F-05` — CLOSED 2026-09-23

Ruled and widened. The checker now reports **30 trees, 518 declared, 518
executing** — the count moved, which is the whole point.

**Two populations, kept apart**, because conflating them was measured wrong:
`spine_trees` answers *what exists* (sibling discovery, rung partitioning) and
`product_trees` answers *what must declare*. A rung-mate that ships no roster
still owns its discriminated test modules, and dropping it hands them to the
base tree — which the checker's own
`test_two_trees_of_one_rung_do_not_see_each_others_modules` caught within
minutes.

**The criterion is structural, never a list of named exemptions**: a tree is in
if it ships a deployment, a roster, or a `spec/`. All three markers were forced
by a failing test — `cp-22` declares gates and ships no config because it is a
consumer; a Gate-1 tree is spec-only and must stay in so `gate_one_trees` can
NAME it, since a tree that vanishes from the output is a tree nobody revisits.
`dr-01` has none of the three and is correctly out.

## `PKG-F-06` — an empty memo refuses at gate 3, not at gate 4

**Working as designed, recorded so it is not re-derived.**

Asking with an audience nobody holds admits no section. The refusal that comes
back is the SDK's **`ttl-anchor-unresolvable`**, not this product's
`packaging.did-not-move-the-conclusion` — because with no section admitted
there is no observation for an evidence-anchored TTL to anchor on, and gate 3
runs first.

Both are correct refusals of an empty memo. `PKG-G05` asserts *either*, rather
than pinning one: the ordering between two gates that both say no is the SDK's
to decide, and a test that pinned it would fail on a reordering that changed
nothing about the answer.

---

## What the SDK taught this rung, and it is a good list

Four designs were wrong and the SDK said so, each time by refusing rather than
by accepting something subtly broken:

1. **Model and temperature in the environment document.** `resolve_value`
   refuses an *empty* variable, so "export it empty to select the stub" is not
   expressible. The refusal is right: these are **values**, and values live in
   artifacts (CLAUDE.md §6.4) while the environment holds connection material.
   Moving them into the prompt artifact also **fixed the pin** — one hash now
   covers the words, the model and the temperature together, so changing any
   of the three produces a new artifact version, which is what §7.10.4 wants
   of a rendering primitive.
2. **A λ_c row named after the concept.** `AssemblyDebtScorer._observations`
   sets `observation_type = claim.entity_class`, so a row named
   `packaged_section` matched no observation at all — and the evidence-anchored
   TTL then refused with `ttl-anchor-unresolvable`, which is a correct refusal
   over an empty observation set rather than a broken anchor.
3. **A separate identity node joined by edges.** The traversal returns what its
   seeds *reach*, and the memo node was never in the view. Carrying the
   packaging identity on **every section** is better rather than merely
   simpler: a section that travels alone — quoted, pasted, forwarded — still
   names the model, the prompt and the substrate that produced it, and a
   separate identity node is exactly the thing that gets left behind.
4. **An edge envelope carrying both endpoints' match keys.** It matches both
   *entity* rules, and the worker refuses to mint a URI from the partial
   identity that results.

None of these was a documentation failure; each was a design the SDK declined
to let through.
