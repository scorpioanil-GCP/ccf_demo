# Deferred Items — Phase 24.4

Out-of-scope discoveries logged during execution. **Nothing here is fixed in
this phase**; each is recorded so it is a known item rather than a surprise.

## 1. `cp-01` and `cp-02`'s Postgres fixtures are not idempotent against a reused container

**Found during:** plan `24.4-04`, while running `make leg-postgres` repeatedly
against one long-lived `postgres:16` container.

**What happens:** `tests/examples/test_cp_01_output.py` and
`test_cp_02_output.py` seed into a FIXED schema (`ccf_v2`) whose SQL inserts
without first dropping. Six runs against the same container left
`ccf_v2.facility` holding six times the fixture's rows, and fourteen tests
across the two modules went red with figures that are exact multiples of the
declared ones (`360` facilities where `60` is declared).

**Why it is out of scope here:** CI starts a FRESH service container per job, so
the leg is green there and was green here the moment a fresh container was used
— verified: `141 passed, 1 skipped` on a clean `postgres:16`. Nothing in plan
`24.4-04` touches those modules, and `tests/examples/test_cp_04_census.py` is
immune by construction (it seeds a per-module schema from
`cp_04_seed.schema_for`, and passed unchanged against the polluted container).

**What it would take:** lead the two fixtures' SQL with
`DROP SCHEMA IF EXISTS ... CASCADE` or move them to per-module schemas, the way
`tests/examples/cp_04_seed.py` does. A decision for whoever owns those modules.

## 2. `deployment._rotate` cannot change its input under the walk that calls it

**Found during:** plan `24.4-05`, while sabotaging the shipped rotation
convention. Replacing `_rotate`'s body with `return tuple(circuit)` — the whole
convention removed — left both roster assertions GREEN.

**What is true:** `detect_cycles`'s depth-first walk explores a neighbour only
when `neighbour > start`, so every circuit it closes is already entered at its
lexicographically smallest member. Measured on the committed fixture by spying
on `_rotate`: it is handed **two** circuits and **both** already start at their
minimum. It is a no-op on this estate, and on any estate that walk produces.

**Why this is not a defect:** the convention is a property of the OUTPUT, and
the output has it. `_rotate` is defensive: it makes the ordering true of the
function rather than true only as a consequence of the caller's pruning. Aimed
at something it can change — rotating to the LARGEST member instead — the
sabotage went RED on both roster assertions, so the rosters are genuinely
order-sensitive.

**Why it is out of scope here:** `deployment.py` belongs to plan `24.4-06` and
is not in plan `24.4-05`'s `files_modified`. The only thing worth changing is
`_rotate`'s docstring, which presents the rotation as the mechanism that makes
the roster order true rather than as a belt-and-braces restatement of it.
