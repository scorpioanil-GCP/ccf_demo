# cp-09 — Treasury Liquidity Position

**Rung 9.** Cash and rate posture at one instant, over four kinds of time.

## What this demonstrates

One `as_of` governs the whole determination — and does **not** flatten four
different kinds of timestamp into one freshness claim:

| class | example | what `as_of` does to it | decays? |
| --- | --- | --- | --- |
| `market-observation` | the intraday rate tick | **selects** the observation | yes, against its own λ_c |
| `policy-effectivity` | the regulatory posture | **selects** the version in force | no — in force or not |
| `reporting-period-end` | the client's filed cash | **bounds** it | slowly, on filing cadence |
| `unobserved-holding` | a deposit balance | **nothing** | undefined, and the payload says so |

Three more things it shows:

- **A source outside its coverage window is absent, not stale.** Two engineered
  rate feeds cover disjoint windows. Ask the June feed for an August rate and a
  naive query returns the June close, 59 days old — a number made by the query,
  not claimed by the feed.
- **Scope decides participation before freshness decides admission.** A
  USD-only request on a USD-home client needs no conversion, so no FX
  observation participates and no FX bound can fire.
- **Three concentration verdicts, not two.** `limit-unknown` is an answer.
  Four of this client's seven counterparties carry a limit; a product with two
  verdicts calls the other three compliant.

## Run it

```bash
make venv
```

Export the four estate variables. **The role must be read-only** — nothing this
example runs writes to either store, and a role that *could* write would make
that a promise rather than a guarantee. The Fluree ledger is append-only, so a
write there is permanent.

```bash
export CCF_CP_09_POSTGRES_DSN='host=… user=… password=… dbname=…'
export CCF_CP_09_POSTGRES_SCHEMA=ccf_v2
export CCF_CP_09_FLUREE_URL=http://…:8090
export CCF_CP_09_FLUREE_LEDGER=fibo-v2
```

Both libpq spellings work and neither is preferred: a `host=… user=…` keyword
string and a `postgresql://…` URI. libpq also reads `PGHOST`/`PGPORT`/`PGUSER`/
`PGPASSWORD` from the environment, so the value can be as short as
`dbname=parkavedb`. **`CCF_CP_09_POSTGRES_SCHEMA` is `ccf_v2` and
`CCF_CP_09_FLUREE_LEDGER` is `fibo-v2`** — the v2 namespaces, which are *not*
the names in the estate's own `.env`.

```bash
make -s example-cp-09
```

`-s` suppresses make's echo of the recipe. That echo is the only thing that
differs between this target's output and the transcript published on the
documentation page.

Without make:

```bash
PYTHONPATH=src:runtime:examples/cp-09-treasury-liquidity-position \
    .venv/bin/python examples/cp-09-treasury-liquidity-position/run.py
```

Every request parameter is optional. Omitted, the program asks the
demonstration question in `artifacts/question.yaml`.

**Variations that change the answer, not the formatting:**

```bash
# the posture flip — same client, same question, two days earlier
make -s example-cp-09 AS_OF=2026-06-15T18:05:00+00:00

# fail closed on a stale signal
make -s example-cp-09 AS_OF=2026-08-21T16:00:00+00:00 CURRENCIES=USD

# scope to one currency at a live instant
make -s example-cp-09 CURRENCIES=USD
```

**The stale-signal variation exits non-zero, and that is correct.** You will see
`make: *** [Makefile:515: example-cp-09] Error 1`. A refusal is not a crash, but
it is also not a success, so the program returns 1 and make reports it.

## The story

The client is `2549004GGE2APGNT6O92` — American Healthcare REIT, Inc. It is the
only treasury client in the estate holding US-NY deposits under a
`reserve-buffer` mandate, which puts it under the one regulatory posture that
has two versions.

**Run 1, `2026-06-17T18:05Z`.** The posture flipped to `enhanced-scrutiny` the
day before, and the answer says so (excerpt):

```
REGULATORY POSTURE IN FORCE
  FR     standard           effective 2024-01-02   posture-FR-reserve-buffer-v1
  US-NY  enhanced-scrutiny  effective 2026-06-16   posture-US-NY-reserve-buffer-v2
```

**Run 2, two days earlier.** Same client, same question, one parameter moved.
The posture reads `standard`, the version is `-v1`, and the content address
differs. The posture was *selected by effectivity*, not read from the ledger
head.

**Run 3, `2026-08-21T16:00Z`.** The product refuses. The consumer envelope says
only that a declared invariant does not hold; the replay record names the
signal, its age and the bound: `SIG-000`, 2700 seconds old, against a bound of
900. **Those are two different surfaces on purpose** — the determination is
preserved for audit, and the boundary discloses less.

## Artifact-by-artifact

| file | what it holds |
| --- | --- |
| `spec/CP-SPEC-009_…md` | the specification everything else discharges |
| `ccf_config.yaml` | the Control Plane document — product class, operators, resolution rules, the λ_c table and its `decay_basis` per class |
| `backends.yaml` | environment-variable **names** only. No host, no port, no credential, anywhere in this tree |
| `artifacts/signal-sources.yaml` | the two rate feeds and **the window each claims to cover** |
| `artifacts/staleness-profile.yaml` | the refusal rule, per signal class. `ccf_config.yaml`'s `half_life:` is the *decay* model; this is the *refusal* rule, and they are not the same thing |
| `artifacts/question.yaml` | the demonstration question, including its `as_of` pin |
| `artifacts/gates.yaml` | the 22 declared gates, each with its test and its sabotage outcome |
| `acquisition.py` | the two source reads. No fabric call, no clock |
| `deployment.py` | this deployment's vocabulary, its ingestion, and the deployment half of one declared gate |
| `projection.py` | Π — where the four temporal classes would otherwise be flattened |
| `produce.py` | the spine: boot, acquire, govern. One `build_governed_resolver` |
| `run.py` | the client. Prints what came back |

## Whitepaper / CLAUDE.md sections exercised

- Whitepaper §7.3 (the T axis and its two clocks), §7.4 (operators), §7.5 (Π),
  §7.6 (the delivery contract and its gates), §7.7 (half-life and Context
  Debt), §7.10 (Decision Replay).
- CLAUDE.md §6.4 (No-Hardcoding — delete `ccf_config.yaml` and the spine has
  nothing to interpret), §9 (the curated estate is evidence: this example reads
  `.76` and writes nothing), §10 (single-writer — `booted.handle.worker` is the
  only write handle to L3), §11 (Protocols, typed contracts, replay by
  construction).
- `D-IMPL-331` and `D-IMPL-332` — a λ_c row declares which instant it decays
  against, and an unsupplied valid-time stays absent. `TLP-G15` proves that
  chain end to end at the product level.

## What to change first

1. **`artifacts/question.yaml`** — the anchor and the `as_of`. Everything else
   follows from the question.
2. **`artifacts/staleness-profile.yaml`** — the bound per signal class, and
   which classes are mandatory. This is what the product refuses on.
3. **`ccf_config.yaml`'s `half_life:`** — the decay rate per class, and
   `decay_basis`. A class whose source carries a real observation time declares
   `valid-from`; one whose source does not must not.
4. **`artifacts/signal-sources.yaml`** — point the feeds at your own tables and
   state the window each covers.

None of this is code. That is the point.

## What would fail

**`debt_tolerance` must be a `Decimal`, never a float.** The canonicalizer
refuses floats outright — *not bit-stable across platforms* — and it is right
to: the value rides the request's content address, so a figure that rounded
differently on two hosts would give one question two identities. Pass
`Decimal("0.25")`, not `0.25`.

**The 22 gates in `artifacts/gates.yaml` carry a `sabotage_state`, and the
values mean different things.** Eighteen are `passed` — the specific invariant
was broken and the gate went red. **Four are `unavailable`: their bad state is
unreachable from this example because an upstream SDK guard prevents it, so
they are evidenced by the working path plus that guard, never by a local
negative control.** Do not read them as "tested and passed":

| gate | enforced upstream by |
| --- | --- |
| `TLP-G01`, `TLP-G02` | `D-IMPL-86` — the SDK refuses a divergent operator set at *bind* time, before a product exists |
| `TLP-G05` | the SDK's disclosure layer — it replaces a refusal's detail with its own sentence, so no text written here can leak |
| `TLP-G08` | the SDK's type boundary — a refusal and a served product are different types; one cannot carry the other's payload |

Two sabotages that turned out to test nothing are recorded rather than deleted
(`TLP-G07`, `TLP-G14`). `TLP-G07`'s first draft searched the whole replay
record for `900` and stayed green under the very sabotage it was written to
catch — the λ_c table carries 900 as well.

**Other ways this breaks:** point the estate variables at the v1 namespaces and
the anchor resolves with no graph behind it; give a holding an `observed_time`
and `TLP-G15` reds, because the estate never recorded one; widen a feed's
coverage window and `TLP-G22` reds, because an out-of-window source would then
report an age it never claimed.

**The snapshot.** The transcript published on the documentation page was
produced at commit `db559c65`, asking `as_of=2026-06-17T18:05:00+00:00`, and
serves content address `6d29b32bbeef78e6…`.
