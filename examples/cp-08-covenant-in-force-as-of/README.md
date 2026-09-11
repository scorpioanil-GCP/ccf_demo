# Covenant-in-Force As-Of — rung 8

`credit-risk.covenant-in-force.v1` · Tier 3 · Fluree `fibo-v2` for covenants,
amendments and both time axes; PostgreSQL `ccf_v2` for facilities, drawdowns
and the breach-threshold register. **Both read-only.**

> **Which amendments bound this facility on the drawdown date, and which of
> them had the institution actually booked by then?**
>
> One question, on two clocks.

---

## What this demonstrates

**A question with two independent time axes, where moving either one alone
changes the answer.** Every rung before this one has a single notion of "when".
This one has two, and they disagree on real estate data:

```
as_of = 2025-09-09,  known_as_of = 2025-09-09   ->  1 amendment admitted
as_of = 2025-09-09,  known_as_of = 2025-12-31   ->  2 amendments admitted
```

Same facility, same effective date, same store. The second amendment
(`AMD-01BB3F-2`) took effect on 2025-08-14 and the bank did not book it until
2025-10-05. On the day of the drawdown it **was in force and was not known**.

- **Valid time** — `as_of` cuts on `validFrom` / `validTo`: *was this in force?*
- **Assertion time** — `known_as_of` cuts on `assertedAt`: *had we booked it?*

A `SELECT` against current state answers neither. It returns today's amendments
with full confidence and no signal that it answered a different question than
the one asked. **That is the point of the rung**: at this tier the gap between
"what was true" and "what we knew" stops being a modelling nicety and becomes
the difference between a defensible answer and an indefensible one.

### What it refuses to claim, and why that is half the demonstration

The original framing for this rung was *"ledger time-travel with supersession
preserved rather than overwritten."* **The supersession half was withdrawn on
measurement**, before any code was written: no covenant in this estate is ever
superseded — 0 of 180 carry `supersededBy`, thresholds are unchanged from
`t:1500` to head, no interval is ever closed.

> **Booking lag proves two clocks. It does not prove covenant supersession.**

So the product serves **current** covenant terms beside a **historical**
amendment answer, and labels them unversioned as a payload field rather than a
footnote. A product may not teach a property its data does not have. See
`FINDINGS.md` `CP08-F-02` and `CP08-F-04`.

### Three further things it shows

- **A refusal that is a refusal, not an empty answer.** `include_superseded` is
  declared and refused *by name with its reason*, because an empty superseded
  set is an affirmative claim — it reads as *"nothing was superseded"* — and
  this estate cannot support that claim.
- **An exclusion record that names the axis.** Every omitted amendment says
  which clock excluded it and why, so a consumer can tell "not yet in force"
  from "not yet booked" from "cannot be placed at all".
- **A historical ledger pin that is lineage, never identity.** Re-serving at a
  recorded transaction point reproduces the content address; the pin bounds the
  *store* and enters lineage as execution provenance (`D-IMPL-309`). It is
  **not** a third clock — Fluree's `t` orders writes, not observations, and
  substituting it for `as_of` is the error `D-IMPL-240` (2) forbids.

---

## Run it

The estate lives on `192.168.4.76`. Connection material comes from
`ccf_dataprep/.env`; **the namespaces do not** — `.env` names the v1 estate and
this example reads v2.

```bash
export CCF_CP_08_FLUREE_URL=http://192.168.4.76:8090
export CCF_CP_08_FLUREE_LEDGER=fibo-v2
export CCF_CP_08_POSTGRES_DSN='postgresql://<user>:<pw>@192.168.4.76:5432/<db>'
export CCF_CP_08_POSTGRES_SCHEMA=ccf_v2

python examples/cp-08-covenant-in-force-as-of/run.py
pytest tests/examples/test_cp_08_output.py      # 18 tests, same env
```

Both stores are read with `SELECT`. **Nothing in this product, its examples or
its tests writes to either** — the ledger is append-only, so a seeded assertion
is permanent, and a product that had to mutate its sources to demonstrate
itself would be demonstrating the mutation.

---

## What the run prints

```
facility FAC-01BB3F
  as_of        2025-09-09   — was it in force?
  known_as_of  2025-09-09   — had we booked it?

  IN FORCE AND KNOWN  (1)
    AMD-01BB3F-1       effective 2025-05-17  booked 2025-05-21  (4-day lag)

  EXCLUDED  (1)
    AMD-01BB3F-2       assertion-time
                       in force, but not yet booked at known_as_of

  COVENANTS CARRIED  (4) — terms as they stand TODAY
    ...

  D_c 0  signal ok   — the platform's reference assessment; this product declares none
```

**`D_c` is 0 on every answer, and that is stated rather than dressed up.** This
product declares no Context Debt metric of its own: every facility amendment in
this estate carries both clocks, so there is no shortfall of that kind to
report, and every observation is minted from a live read inside the run, so
freshness is 1 by construction. An earlier draft computed a per-run ratio that
read the same on every answer; it was withdrawn rather than kept as decoration.
`spec/MEASUREMENT-NOTE.md` §2 carries the measurement.

---

## Artifact by artifact

| file | what it carries |
|---|---|
| `spec/CP-SPEC-008_…md` | the build specification — decision frame, contract, catalog, recipe, gates |
| `spec/MEASUREMENT-NOTE.md` | what was measured against the estate, including two corrections to this product's own claims |
| `artifacts/source-vocabulary.yaml` | every IRI, table and column the sources expose. **The SDK ships adapters that reach a backend and no opinion about what the backend holds** — that `validFrom` is a valid-time axis is a fact about *this estate*, declared here |
| `artifacts/projection.yaml` | Π's declaration — the three axis tokens and the unversioned label |
| `artifacts/gates.yaml` | the 12 declared gates, each with an executing test and a named sabotage |
| `artifacts/debt-declaration.yaml` | the two `D_c` factors the SDK cannot measure, declared rather than computed |
| `ccf_config.yaml` | Control Plane state — λ_c, debt bands, policy, the request contract, resolution rules |
| `acquisition.py` | the two source legs. **Imports no `ccf`** — it reaches stores, nothing more |
| `deployment.py` | this deployment's seams: envelopes, config keys, the declared temporal-coherence gate |
| `projection.py` | Π — the two-axis cut and the exclusion record |
| `produce.py` | boot / acquire / govern, one `build_governed_resolver`, a named `plan_factory` |
| `FINDINGS.md` | the authoritative findings record. Every `CP08-F-NN` id cited in this tree resolves there |

---

## Sections exercised

**Whitepaper** — §5.2 and §7.3 (the graph's T axis, here as two independent
temporal dimensions); §7.4 (Temporal and Policy operators); §7.5 (Π as typed
transformation — the two-axis cut and the exclusion record are Π's, not the
graph's); §7.6 (the Context Product Contract and its validation gates); §7.7
(half-life and Debt — the reference assessment); §7.10.1 (the five-dimension
Decision Replay record).

**CLAUDE.md** — §9 (the examples charter; the curated estate is evidence, not a
fixture; illustrative calibration per `D-IMPL-323`); §6.4 (the No-Hardcoding
Rule — every value in an artifact, including the two declared debt factors);
§10 (L1–L6, and the single-writer invariant); §11 (mechanism, not values —
§0.6 of the spec states the consequence in this product's own terms).

**Decisions** — `D-IMPL-325` and `D-IMPL-328` (relative defaults, and the
identity offset this rung needed); `D-IMPL-329` (the shipped scope and the two
inherited constraints); `D-IMPL-240` (2) (`t` is transaction time, not `as_of`);
`D-IMPL-282` (the declared product gate); `D-IMPL-309` (the store pin is
execution provenance); `D-IMPL-319` (the canonical producer shape);
`D-IMPL-326` (a gate's acceptance authority may be a cited `CP-SPEC` clause).

---

## What to change first

**Change the facility.** `run.py`'s `DEMONSTRATION_FACILITY` is one of three
with an engineered booking lag and a drawdown inside it. Point it at a facility
without one and the two clocks return identical answers — which is the honest
behavior, and is why the lag had to be engineered rather than found.

**Then move `known_as_of` past `2025-10-05`** and watch `AMD-01BB3F-2` cross
from the exclusion record into the answer. That single move is the whole
product.

**Then change the λ_c table** in `ccf_config.yaml`. It is keyed on the
**observation type** — `amendment`, `covenant`, `facility` — because that is
what the SDK's reference scorer looks up. It was once keyed on descriptive
labels nothing resolved, and that went unnoticed for the whole build:
*configuration that nobody reads is documentation, not control.*

**What to adapt for your own estate.** The vocabulary, in
`artifacts/source-vocabulary.yaml` — every predicate, table and column name is
declared there and nowhere else. The assembly reads them; it does not know
them.

---

## What would fail, and is meant to

- **Serving an amendment that violates either bound.** The declared product
  gate `cp-08.temporal-coherence` refuses the answer before a consumer sees it.
  Sabotaged in-test on both limbs independently.
- **A `facility_id` that resolves to nothing.** Refused, not answered with an
  empty set.
- **A transaction point the ledger has not reached.** Refused by the store.
- **A policy bundle cited by the product but missing from the decision record.**
  `CIF-G16`, both limbs sabotaged in-test.

## What is declared and not built

`CIF-G15` — a closed as-of answer should carry a longer TTL than a live one.
Where *closed* ends and *live* begins is an operator's policy decision rather
than one this deployment may take, so the gate is **declared and visibly
unimplemented** rather than dropped or counted as running. `CIF-G07`,
`CIF-G13` and `CIF-G14` are gaps in the numbering and are not reused;
`FINDINGS.md` says why for each.
