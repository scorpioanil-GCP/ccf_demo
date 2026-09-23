# dr-02 — package a Context Product

**Assembly Mode 2.** The first Context Product on either spine whose payload a
model wrote.

`dr-02` asks `cp-06-canonical` for a collateral-coverage product through its
standard door, hands the JSON to a model with a versioned prompt, and serves
the prose as a governed Context Product of its own — with the substrate it
rendered named on every section.

## What this demonstrates

| | |
| --- | --- |
| **`assembly_mode: llm_packaged`** | 29 of 29 other shipped trees declare `algorithmic`. Assembly Mode is the **ninth element** of the Context Product Contract and had never been exercised past Mode 1 |
| **§7.10.4's four pinned rendering primitives** | model, temperature, prompt artifact URI and hash — on the payload *and* on dimension 3, so an examiner reads the packaging without dereferencing anything |
| **The smoothing gate** | `packaging.did-not-move-the-conclusion` **refuses** a memo stating a figure the substrate does not carry |
| **The substrate stays the artifact-of-record** | every section names the upstream content address, so any sentence is checkable against the bytes that produced it |

**Where the model sits is the architectural claim.** It runs at the
**acquisition** seam, over a product that is already finished; its output
enters the fabric as a claim, and the ordinary projection and the ordinary
validation gates then judge it. Algorithmic → semantic → algorithmic
(whitepaper §7.6.6). **A model inside the projection would be a model whose
output nothing gates** — which is also why a composite cannot host this: a
composite acquires its children *after* acquisition.

## Run it

`dr-02`'s substrate is another product, so start that product's door first:

```sh
.venv/bin/python examples/cp-06-canonical-collateral-and-setoff-coverage/run.py --door
# prints: READY <port>

export CCF_DR_02_UPSTREAM_URL=http://127.0.0.1:<port>/mcp
export CCF_DR_02_UPSTREAM_TOKEN=<the credential that door accepts>
.venv/bin/python examples/dr-02-package-a-context-product/run.py
```

The upstream needs its own `CCF_CP_06C_*` estate names; `dr-02` reads no store
of its own. `ccf_environment.yaml` names every variable and the remedy for
each.

**One upstream is demonstrated.** The door URL is configuration because a
connection value belongs in the environment document — that is not a claim of
portability, and no other upstream is tested (`DR-SPEC-002` R1).

## The story

A coverage product carries assets, haircuts, realizable values and a ratio. A
credit officer reads prose. The obvious move is a rendering script outside the
fabric — and it produces text with no expiry, no debt reading, no lineage and
no address. It looks like the product and is not governed like it, and the
moment it is pasted into a memo the governance the product carried is gone.

Mode 2 is that seam done inside the fabric. The packaged form is a
**derivative view**: the algorithmic substrate remains the artifact-of-record,
and §7.10.4's watchpoint is that the packaging must not have altered the
algorithmic conclusion.

**The gate caught its own author.** On this rung's first honest run the
shipped packager wrote *"3 asset(s) secure this facility"* — a **computed
count** the substrate never carried — and the serve refused. That is the
failure mode, caught by the mechanism rather than by review, against the
person who wrote both (`PKG-F-01`).

## Artifact-by-artifact

| file | what it carries |
| --- | --- |
| `ccf_config.yaml` | the class, `assembly_mode: llm_packaged`, the declared smoothing gate, the audience-admitting Policy operator |
| `ccf_environment.yaml` | one source — the upstream door — as **names, never values** |
| `artifacts/memo-prompt.yaml` | the prompt **as a versioned artifact**, with the model and temperature beside it so one hash pins all three |
| `artifacts/gates.yaml` | the eight declared gates and each one's sabotage |
| `acquisition.py` | ask the door → package → emit claims. The Mode 2 seam |
| `memo_packaging.py` | the fail-loud deterministic packager, and the opt-in real-model one |
| `projection.py` | Π over the packaged claims. Nothing semantic happens here, and that is the point |
| `deployment.py` | the three verbs and **the smoothing gate** |

## Whitepaper / CLAUDE.md sections exercised

- **§7.10.4** — Assembly Mode 2's replay footprint and its four pinned
  rendering primitives; the smoothing watchpoint this rung turns into a gate.
- **§7.6.6** — Algorithmic ⇄ Semantic Alternation, honored by where the model
  sits rather than asserted.
- **§6.3** — the nine-element contract; Assembly Mode is the ninth.
- **CLAUDE.md §6.4** — the No-Hardcoding Rule: the prompt is an artifact, and
  so are the model and temperature.
- **CLAUDE.md §9** — reads only; the estate is evidence.

## What to change first

Change the **prompt artifact**. Add a heading, and the deterministic packager
refuses by name because it was never told how to render it — which is the
fail-loud half working. Then teach it that heading and watch the smoothing
gate judge the result.

After that, set `model:` in the prompt artifact to a real provider model. The
packaging path is identical; only the packager changes.

## What would fail

- **Writing a figure the substrate does not carry** — refused, by name, with
  the figure quoted. This is the gate's whole purpose.
- **Rendering a section for an audience the caller does not hold** — the
  Policy operator admits before materialization, so the section never exists.
- **Anchoring the expiry on the request** — a rendering would become fresher
  than what it renders. The class anchors on entity freshness.
- **Putting the model in the projection** — its output would reach the caller
  without passing a gate.
- **Naming a module `packaging`** — it collides with an installed
  distribution and is shadowed depending on `sys.path` order (`PKG-F-02`).
