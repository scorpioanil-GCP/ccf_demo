# Package a Context Product — Assembly Mode 2 Specification

> **`dr-02`** · Decision Replay series · authored to the Context Product
> Specification Standard v0.3 · **Gate 1 ACCEPTED 2026-09-23. The four
> rulings are folded below; this is the Gate-2 baseline.**

---

## 0 · What this document is

The Assembly Mode 2 half of the Decision Replay program. It specifies a
Context Product whose payload is produced by a model over an
algorithmically-assembled Context Product — the whitepaper's Mode 2 — and the
gate that keeps the packaging honest.

**It is `dr-02`, not `cp-25`.** The Context Product ladder closed at 24 of 24
and stays closed (Dave, 2026-09-23). This is a capability exercised *over*
products, which is what the `dr-NN` series enumerates.

### 0.1 Already proven — reused unchanged, NOT reopened

| already shipped | where |
| --- | --- |
| a served product reached through its standard MCP door | every rung from cp-05 |
| a consumer that knows only the product's shape | `cp-22`, `hw1-harness-clients` |
| a model in an example's path, determinized for CI | `hw1-harness-clients` leg 2 (`runner/model_stub.py`) |
| the `content_generation` archetype | `src/ccf/agents/archetypes.py` |
| the four Mode 2 record pins | `ModelVersionRecord.packaging_trace` (`D-IMPL-346`) |
| prompts as versioned artifacts | the No-Hardcoding Rule, CLAUDE.md §6.4 |

**No SDK change is expected.** If the build finds one, it stops and returns the
measurement rather than implementing it.

### 0.2 What `dr-02` actually adds

**One genuinely new thing: the first Context Product on the ladder whose
payload a model wrote.** Everything else is arrangement.

Three claims follow from it, and only the third is hard:

1. **`assembly_mode: llm_packaged` is declared and carried.** Dimension 3 of
   the served record reads it; 29 of 29 shipped trees today read `algorithmic`.
2. **The four §7.10.4 rendering primitives are pinned** — model version,
   temperature, prompt artifact URI and hash, output hash — so an examiner
   reads the packaging off the record without dereferencing anything.
3. **The packaging did not move the conclusion.** §7.10.4's own watchpoint,
   and this product's fourth validation gate. See §D.4.

### 0.3 Deliberately OUT of scope

- **No model in the algorithmic path.** The model runs at the acquisition
  seam over a *finished* product; its output enters as a claim and is then
  projected and gated like any other. A model inside the projection would be
  a model whose output nothing gates.
- **No change to the upstream tree.** It is the artifact-of-record and is read
  through its published door, unmodified.
- **No estate retuning**, no new SDK capability, no CP rung.
- **No judgement about whether the prose is *good*.** The gate asks whether it
  is *faithful*. Quality is not a governed property.

### 0.4 The four-question build test (Standard v0.3)

| question | answer |
| --- | --- |
| Is the decision real? | Yes — a credit officer reads prose, not a JSON payload of haircuts and realizable values. |
| Does it need a Context Product? | Yes. The packaged form must carry its own expiry, debt, lineage and address, or it is an ungoverned rendering of a governed thing. |
| Can the estate answer it? | Yes — the substrate is an already-served product, so the estate question is the upstream tree's, already answered. |
| Does it exercise something new? | **Yes: Assembly Mode 2, the ninth contract element, unexercised on the ladder.** |

---

## A · Decision frame

**Decision & trigger.** A credit officer is preparing a facility review and
needs the coverage position in the form a memo takes. The governed product
that answers the underlying question serves asset-level figures; the officer
needs those figures *in prose*, with nothing added and nothing softened.

**Principals.** The credit officer who reads the memo; the reviewer who has to
tell whether a sentence is supported; the examiner who later asks which model
wrote which paragraph and over what evidence.

**The counterfactual this refutes.** A rendering pipeline that reads a
governed product and emits prose **outside the fabric** produces text with no
expiry, no debt reading, no lineage and no address. It looks like the product
and is not governed like it. The moment it is pasted into a memo, the
governance the product carried is gone.

---

## B · Contract

### B.1 The nine elements

| # | element | value |
| --- | --- | --- |
| 1 | schema | `credit-risk.packaged-memo` `1.0.0` |
| 2 | freshness SLA | inherited from the substrate; the packaging adds none |
| 3 | TTL | `ttl_anchor: from_entity_freshness` over the **upstream product's** `expires_at`. A rendering cannot be fresher than what it renders |
| 4 | policy binding | `packaged-memo-audience` — section-level, admitted before materialization |
| 5 | lineage | `lineage_inputs_at: [upstream_product, packaging]` |
| 6 | semver | per-product lane, `1.0.0` |
| 7 | discovery | domain `credit-risk`, intent `credit-memo-drafting` |
| 8 | addressability | content-addressed like any product |
| 9 | **Assembly Mode** | **`llm_packaged` — the element this product exists to exercise** |

### B.2 Request parameter surface

| argument | domain | meaning |
| --- | --- | --- |
| `facility_id` | subject | passed to the upstream product unchanged |
| `borrower_scope` | entitlement | carried verbatim; **the packaging cannot widen what the substrate narrowed** |
| `audience` | entitlement | which sections this principal receives |

### B.3 Prerequisites

The upstream product's door, reachable and credentialed. **The upstream is
`cp-06-canonical-collateral-and-setoff-coverage`** (R1) — one process, and the
same tree `dr-01` reconstructs against.

The door URL is configuration rather than a constant, because a connection
value belongs in the environment document either way. That is **not** a claim
of portability: one upstream is demonstrated and no other is tested, and the
README says exactly that rather than implying a generality nobody measured.

---

## D · Assembly recipe

### D.1 The four steps, in order

1. **Ask the upstream product** through its door, with the caller's own
   subject and entitlements. A refusal upstream is `dr-02`'s refusal.
2. **Package** — the model is handed the product's JSON and a versioned prompt
   artifact, and returns one prose section per declared heading.
3. **Emit** each section as a claim, carrying its audience classification, the
   upstream content address it derives from, and the figures it cites.
4. **Project, gate, serve** — the ordinary algorithmic path.

### D.2 Determinism class

**Deterministic given a pinned model, temperature and prompt** — which is what
the four pins record. For CI the model is a fail-loud loopback stub answering
a declared conversation (`hw1-harness-clients` leg 2's discipline). The real
model is opt-in and never required for a green build.

### D.3 Where the model sits — Algorithmic ⇄ Semantic Alternation

```
upstream product (algorithmic)  →  MODEL packages  →  claim
                                                        ↓
                        algorithmic projection → three gates → serve
```

Algorithmic → semantic → algorithmic. The model never sees raw signal, and
everything it produced is gated before it is served.

### D.4 The smoothing gate — the point of this rung

`packaging.did-not-move-the-conclusion` `1.0.0`. The served prose is checked
against the substrate that produced it. It **refuses** when:

- a figure appears in the prose that the upstream payload does not carry;
- a section is rendered for an audience the Policy operator excluded;
- a `fail_closed` or withheld disposition is rendered as an answer;
- the upstream content address on a section does not resolve to the product
  actually asked for.

**Why this is the hard claim.** The other two are declarations that either hold
or do not. This one is a real failure mode a model introduces, it is invisible
to every existing gate, and nothing in the suite tests it today.

---

## G.1 · Declared gates

Ids are `PKG-G01`..`PKG-G08`. **Declared and observed RED** — `artifacts/gates.yaml`
carries each one's sabotage and the observation made against it. This section is
the acceptance authority for every id (`D-IMPL-326`).

| id | claim |
| --- | --- |
| `PKG-G01` | the served record's dimension 3 reads `llm_packaged`, and the class declares it |
| `PKG-G02` | all four §7.10.4 pins are populated and non-sentinel on a served record |
| `PKG-G03` | the prompt is a versioned artifact; its URI and hash on the record resolve to the bytes used |
| `PKG-G04` | **no figure in the prose is absent from the substrate** (the smoothing gate) |
| `PKG-G05` | a section outside the `audience` set never materializes |
| `PKG-G06` | an upstream refusal becomes this product's refusal, with the upstream reason retained |
| `PKG-G07` | the memo's `expires_at` follows the upstream product's, never the request instant |
| `PKG-G08` | same subject, same pins, same model → same content address |

---

## The Gate-1 rulings of 2026-09-23, folded

All four answered by Dave. Folded here **before any code was written**.

### R1 — the upstream product is `cp-06-canonical-collateral-and-setoff-coverage`

Not a default with a richer alternative behind it: **it is the upstream.** One
process, already `dr-01`'s own default, asset-level figures that give the
smoothing gate something real to check. `cp-14-credit-memo-context` is not
built against and is not a documented target of this rung.

Consequence for §B.3: the upstream stays *configuration* rather than a
constant — the environment document names the door — but only one upstream is
demonstrated, and the README says so rather than implying portability nobody
tested.

### R2 — `dr-02` is the 30th shipped tree

Ruled onto the roster at build time **if it claims the `D-IMPL-141`
SDK-supplied exemption**, with `DR-SPEC-002` / 2026-09-23 as the citation.
Whether it claims that exemption is a property of the tree, not a choice: it
qualifies only if it authors no operator set of its own and its
`plan_factory` consumes what the resolver supplies. **If it does not qualify,
no roster entry is made and the absence is recorded** — a roster entry for a
tree that does not claim the exemption would be worse than none.

`tools/check_product_gates.py` moves from 29 trees to 30, and from 510
declared gates to 518.

### R3 — the smoothing gate REFUSES

`packaging.did-not-move-the-conclusion` produces a governed refusal, not a
served product carrying a finding. **An unsupported figure in a credit memo is
the failure this rung exists to prevent**, and a product that serves it with a
caveat has served it.

The accepted cost, stated rather than discovered: a model that is merely
verbose makes the product refuse. That is the correct trade for this subject
and it is what the gate's own sabotage will demonstrate.

### R4 — the deterministic stub suffices

CI runs the fail-loud loopback stub and never requires a live model. One
recorded real-model run is evidence in `FINDINGS.md`, not a test. A green
build must never depend on a network call to a model provider.

---

## What Gate 2 will return

The candidate, its gate roster with each id's observed-red sabotage, the
measured glue, the SDK/runtime diff (expected empty), findings, and the active
issue cap. **Nothing merges without a separate GO.**
