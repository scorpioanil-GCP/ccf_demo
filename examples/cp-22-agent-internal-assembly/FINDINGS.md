# cp-22 — findings

Classified under `docs/EXAMPLE-EVALUATION-CRITERIA.md`. **Nothing here was
repaired by changing the example to make it pass** (`D-IMPL-261`).

Measured 2026-09-21 against the live estate (`CCF_REQUIRE_ESTATE=1`).

---

## Summary

| id | class | disposition |
|---|---|---|
| `AIA-F-01` | 2 · launch ergonomics **candidate** | recorded with the friction measured; not repaired |
| `AIA-F-02` | 4 · example design | deliberate, disclosed |
| `AIA-F-03` | example defect (mine) | fixed during build |
| `AIA-F-04` | proof machinery (mine) | fixed during build |
| `AIA-F-05` | 3 · post-launch enhancement | backlog record below |
| `AIA-F-06` | 4 · estate/example limitation | recorded |

**Active issue cap: 1 of 3** — `AIA-F-01`, and it is a new instance of a known
family rather than a new defect.

**No stop condition fired.** None of the four ruled stop conditions was met:
no capability was missing, no governance behaved incorrectly, nothing leaked
across the extraction seam, and nothing about satisfying A2A required a CCF
protocol, door or peering change.

---

## `AIA-F-01` — a debt tolerance declared the obvious way cannot govern anything

**Category 2 candidate (launch ergonomics). Measured, not repaired.**

Agent B's tolerance is a declared value, so it lives in
`artifacts/agent-b.yaml`. Written the obvious way —

```yaml
debt_tolerance: 0.98
```

— YAML parses it as a Python `float`, and `canonical_bytes` refuses a float as
not bit-stable. The result is **not** a governed refusal naming the problem:
it is a `CanonicalizationError` raised during request canonicalization, before
the request contract is consulted.

**So a tolerance declared the natural way does not loosen or tighten anything
— it raises.** The artifact must say `"0.98"` and the code must convert:

```yaml
debt_tolerance: "0.98"        # a string, deliberately
```
```python
tolerance = Decimal(str(DECLARATION["debt_tolerance"]))
```

**§C launch test.** Step 1: *could we ship without this?* **Yes** — the
supported path works and is two characters of quoting. Step 2: *would the
supported alternative create enough friction or misuse risk to materially
undermine adoption?* **This is the question worth a ruling.** The failure is
loud rather than silent, which is the mitigating half. The aggravating half is
that the natural spelling of a *configuration* value is the wrong one, the
diagnostic names canonicalization rather than the field, and **an adopter's
first encounter with it is at serve time**.

**This is the `D-IMPL-304` / `LEX-F-02` family at a new seam.** Every prior
instance was a *caller-supplied request parameter* typed by someone writing a
client. This one is a **deployment's own declared configuration**, which is a
different author, a different moment, and a different expectation. Recorded as
a distinct instance for that reason, not as a duplicate.

**Not repaired here**, per `D-IMPL-261`.

---

## `AIA-F-02` — Agent A cannot distinguish "unknown subject" from "low confidence"

**Category 4 (example design). Deliberate, and disclosed.**

Two genuinely different internal outcomes — a subject the estate cannot
resolve, and a determination withheld above Agent B's declared tolerance —
produce the **same** A2A non-success text:

```
the question could not be answered with sufficient confidence
```

This is a choice, and the alternative is worse. Distinguishing them would be
more useful to Agent A and would also make Agent B an **oracle**: a caller
could separate "this identifier is unknown to me" from "known, but I am not
confident", and enumerate the peer's subject space from outside. That is the
cp-02 discipline — byte-identical refusals for missing and withheld — applied
at an agent boundary.

**Recorded rather than silently chosen.** An adopter whose use case needs the
distinction should make it deliberately, knowing what it discloses.

---

## `AIA-F-03` — the agent card advertised a port the server was not bound to

**Example defect. Mine. Fixed during the build.**

`agent_card()` built its URL from the **declared** port while `--port` bound
another. A2A discovery worked — the card resolved with `200` — and then every
call dialled the advertised port, where nothing listened.

**It reads exactly like an intermittent network fault:**

```
Network communication error: All connection attempts failed
```

Found only because the test harness runs Agent B on two non-default ports to
prove `AIA-G10`. The single-port demonstration would never have exposed it, and
the failure mode names the network rather than the card.

**The transferable shape:** a service that publishes its own address must
publish the address it actually bound, and a discovery document that succeeds
while every subsequent call fails is a *configuration* bug wearing a
*connectivity* bug's error message.

---

## `AIA-F-04` — `AIA-G08`'s first sabotage did not mutate the claim

**Proof-machinery defect. Mine. Fixed.**

`AIA-G08` is the most important gate in the rung: *a caller cannot steer the
determination*. Its first sabotage read a caller-supplied `debt_tolerance` off
the wire and wrote it to an environment variable — and **nothing read it**.

The gate stayed **green**, correctly: the claim is that a caller-supplied field
cannot change the answer, and a leak that changes no answer does not mutate
that claim. The corrected sabotage routes the caller's value into the
strictness of the governed request; the gate went red.

**The durable rule at its next instance** (`ABS-F-09`, `PEW-F-07`, `WIF-F-05`,
now this): *a sabotage must mutate the CLAIM the gate asserts, not merely one
field the claim mentions.*

---

## `AIA-F-05` — the extraction seam is written by hand, and this is the first instance

**Category 3 (post-launch enhancement). Backlog record.**

| field | value |
|---|---|
| **capability** | a supported way to derive a narrow, non-CCF answer from a governed Context Product, with the guarantee that no CCF-shaped structure survives |
| **evidence / rung(s)** | cp-22, `AIA-F-05` — **first instance** |
| **current supported path** | read the payload and build a dict by hand (`agent_b.py::_answer_from`, 18 lines), and assert the absence of forbidden tokens in the example's own test |
| **friction** | low in lines, but the *guarantee* is the example's, not the SDK's: nothing stops the next adopter exporting `result.payload` wholesale, and that is one line |
| **adoption impact** | every adopter embedding CCF inside an agent that answers a non-CCF protocol — which is the whole "CCF layers onto any harness" posture |
| **launch necessity** | §C step 1 **yes, we can ship without it**; step 2 **no** — the supported path is short and correct, and one rung is one data point (§H) |
| **scope / risk** | a redaction or projection helper touches no governed path; the risk is over-generalizing a seam that has appeared once |
| **recommended release** | post-launch, and **only if a second and third rung write the same thing** |

**Explicitly not requested.** §H is the governing rule: one rung's need is one
data point. This record exists so the second instance is recognized as a
second instance.

---

## `AIA-F-06` — CP-22 reads the estate only through cp-21

**Category 4 (example limitation). Recorded.**

CP-22 declares no environment of its own and no binding document. It consumes
`examples/cp-21-large-exposure` and inherits that rung's six `CCF_CP_21_*`
variables. **That is the ruled design** (`Q2`) and the reason no new binding
mechanism was added — but it has a consequence worth stating: **cp-22's tests
skip when cp-21's estate is unconfigured**, and a change to cp-21's request
surface is a change to cp-22's.

The coupling is deliberate and is what "consume an existing paved product"
means. It is recorded so a reader meets it rather than discovers it.

---

## What held without friction

- **`open_product` from outside the product tree** took Agent B unchanged, and
  the **shipped cost is measured** as `Q2` required. Code lines, docstrings and
  comments excluded:

  | | code lines |
  |---|---|
  | the Gate-1 standalone probe | **25** |
  | shipped `_ask_ccf` — the whole CCF half | **34** |
  | shipped `_answer_from` — the extraction | **16** |
  | `_read_request` — the narrow trust map | **11** |
  | `agent_card` + `app` + `main` — the A2A half | **29** |

  The CCF half grew by **9 lines** over the probe, and every one of them is
  named: the declared envelope, the `Decimal` conversion `AIA-F-01` forces, and
  the refusal branch. **No additional SDK glue.**

  Whole files, same measure: `agent_b.py` **144**, `agent_a.py` **61**,
  `run.py` **61** — and `run.py` is a demonstration runner rather than anything
  an adopter must write.
- **`a2a-sdk` was used as given.** `AgentExecutor`, `DefaultRequestHandler`,
  `create_jsonrpc_routes`, `create_agent_card_routes`, `A2ACardResolver` and
  `ClientFactory` needed **no adapter**, which is what CLAUDE.md §7.3 predicts
  for a harness the SDK does not absorb.
- **The governed refusal arrived as a value, not an exception**, so translating
  it was a branch rather than an interception.
- **The replay record resolved inside Agent B** with no extra wiring beyond
  `opened.record_of(outcome)`.
- **No SDK source file was touched, no new class was declared, no new
  dependency was added, and no new decision id was spent.**
