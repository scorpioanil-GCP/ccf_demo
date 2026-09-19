# HW-1 — ask one Context Product one question

**What this demonstrates.** A consumer asking a governed question and getting
back an answer plus the things a `SELECT` cannot give you: the measured Context
Debt in force when the answer was assembled, the content address the answer
hashes to, and the replay record that authorized it.

**What you read.** `consume.py`, and nothing else. It fits inside the budget
below and it imports `ccf.client` and stdlib. (The exact line count is
deliberately *not* quoted here: two numbers is two things to keep in step, and
the budget is the one that is enforced.) It knows the product's identity and the
question's parameters; it does not know a manifest, a Control Plane key, an
operator, a projection or a deployment type. `runner/seed.py` is setup — the
program that populates the deployment from `runner/signal-batch.yaml` before the
client runs — and you do not need to read it to understand the example.

**Declared budget: 80 lines.** That number is enforced, not aspirational —
`tests/examples/test_client_example_budget.py` parses it out of *this line* and
fails the build the day `consume.py` grows past it. Phase 16's first attempt at
this example was 722 lines of Python, measured by nobody.

## Run it — two transports, one `consume.py`

**What you are looking at.** The two commands below reach **the same Context
Product**, a different way each: the product is the constant and the access path is
the variable. The first stands nothing up — the client boots the deployment in its
own process, with the SDK, and the product is produced right there. The second asks
the identical question across a real process boundary, and across a boundary
something has to be *running* on the other side to answer, so this example brings a
small MCP server program along for that job. **How a Context Product is assembled
and served is deliberately out of scope here** — it is the subject of a later set of
examples. The server is here to be reached, not to be studied.

From the **repository root**, after the seed step below:

**The seed step.** A clean checkout holds no populated graph; it holds the
example's declared input, `runner/signal-batch.yaml`, and the program that
interprets it. Run it once, and it populates `deployment/` through the fabric's
single writer and lets go:

```
make example-hw1-seed
```

`make example-hw1` and `make example-hw1-mcp` run that step for you first. If you
type either raw command below yourself, run the seed once before the first of
them. Running it again is harmless: it rebuilds the store from the document, so
the printed content address does not move.

```
CCF_BINDING="inprocess:examples/hw1-companies-over-revenue/deployment" .venv/bin/python examples/hw1-companies-over-revenue/consume.py --min-revenue 1000000000 --as-of 2026-08-01T00:00:00+00:00
```

And the same question, the same deployment, over a **real process boundary**
spoken as MCP stdio:

```
CCF_BINDING="mcp+stdio:examples/hw1-companies-over-revenue/deployment" .venv/bin/python examples/hw1-companies-over-revenue/consume.py --min-revenue 1000000000 --as-of 2026-08-01T00:00:00+00:00
```

**Nothing but `CCF_BINDING` differs, and the two runs print the same content
address.** That is the client abstraction's whole claim, demonstrated where an
adopter can see it rather than asserted in a design document. `consume.py`
imports both adapter modules — `D-05` gives the SDK no discovery chain, so a
scheme reaches the registry by its module being imported — and chooses neither.

And *nothing but* is literal, in exactly the sense a test can hold it.
`test_every_documented_command_names_a_distinct_binding_scheme` asserts three
things about the two commands above: the schemes are different, the address
after the scheme is the **same string** in both — one deployment, reached two
ways — and everything after the `CCF_BINDING=` assignment is identical. So
"differs by one word" is measured, not left to your eye. How this deployment is
reached is the deployment's own business, declared in `binding.yaml` beside its
projection and its graph.

`make example-hw1` and `make example-hw1-mcp` run those two strings verbatim —
same flags, same values, same interpreter — after `make example-hw1-seed`. If a
target and its block ever diverge, the target is wrong;
`tests/examples/test_client_example_purity.py` asserts each documented command
is character-identical to the recipe that runs it, because a documented command
nobody runs and a run command nobody documents are the same defect seen from
two sides.

The MCP run also prints a couple of `INFO Processing request of type …` lines.
Those are the child server talking, on **stderr**; the answer is on stdout.

The interpreter is spelled `.venv/bin/python` rather than `python` because
`which python` returns nothing in this repository. If you have activated the
virtual environment, `python` is the same interpreter and you may type that.

### Why the documented command pins `--as-of`

The API default is `as_of=None`, which means *the producing deployment's own
decision instant*. The documented command passes a fixed boundary instead so
the printed debt figure and content address **reproduce exactly** — run it
twice and the address is the same string. Drop the flag and you get today's
answer, which is the right default for a caller and the wrong one for a
document that quotes an address.

The offset in `+00:00` is required, not decoration. `D-IMPL-38` admits no
implicit UTC anywhere in the fabric, so `--as-of 2026-08-01T00:00:00` is
refused by `ProductClient.ask` before any transport is reached — identically
on both bindings above, which is `D-IMPL-151` finding `B0b`. Before that
repair the same flag produced a `CanonicalizationError` on `inprocess:` and a
`TransportError` on `mcp+stdio:`, and the second was the wrong report: nothing
was wrong with the wire.

### Expected output

The in-process command prints exactly this — the whole of its stdout, nothing
elided, and `tests/examples/test_hw1_readme_expected_output.py` compares this
block to a captured run byte for byte on every push:

```

Q: which companies have revenue over 1000000000?
   Ardent Fenwick Holdings        6420000000
   Marrowgate Shipping            2310000000
   Quillbrook Pharmaceuticals     1040000000
   Solstice Ridge Energy          1875000000
   Tarrowline Systems             1290000000

   5 of 8 assembled

and what a SELECT would not have told you:
   context debt D_c   0.4271  →  forced_llm
   content address    a8335bb4cde42117c0efd42bac50fcf67c64c4f341e1e82a224dbcbcec5a2df4
   replay record      ccf-artifact://hw1-demo/hw1.replay-record/eeaa76fccd6b54b42caf3787f614fba8f9d9f411f45ad450130e1792ade7ac0f@b4ae700f3e968892a3bb83e7bd89e38d96479215e80fcafc7e8c39bfe4a2961e
   answer expires     2026-08-01 00:10:00+00:00
```

`D_c` is a **measured** number here, not a constant: the deployment's λ_c
declares a one-year half-life for a revenue observation, and the eight filings
the fabric learned from `runner/signal-batch.yaml` were ingested at instants
spread from one month to twenty-three months before the `--as-of` boundary, so
freshness decays across them, `D_c` measures `0.4271`, and the answer routes to
`forced_llm` — inside the `[0.20, 0.60)` band `deployment/ccf_config.yaml`
declares. That is the sentence the whole example exists to make true.

**Two identities are printed, and they are different things.** The *content
address* is the hash of the served product's bytes — the answer exactly as the
caller received it. The *replay record* line is the record's own address in the
artifact store: the name before `@` is the graph snapshot the record pins, and
the version after `@` is the record's content address. The record names the
product; the product does not name its record. Both moved once, for one
reason: since `D-IMPL-341` every served contract carries `ttl_anchor_at` — the
instant its expiry is measured from — so the served bytes changed, and with
them the product's address and the record that names it. The debt, its routing
and the expiry instant did not move; the calculation is the same, the contract
says one more thing about itself. This fence was re-measured from the run at
the release qualification of `f0656746` (`docs/QUALIFICATION-f0656746.md`);
before it, the address was `cbc7db84…d426` and the record `…@8b68efaf…`.

## How this example is proven — stated plainly

**Both the two-transport claim and the successful seeded run are always-on CI
checks.** `tests/examples/test_hw1_two_transports.py` copies this example into a
temporary directory with no graph in it, runs the copy's own `runner/seed.py`
against the copy's deployment — the committed declared input, through the single
writer — and then runs the shipped `consume.py` twice under the two shipped
bindings, requiring the two runs to agree on every printed line: the answer, the
measured `D_c`, the content address and the replay reference. It also asserts the
seeded run routes to `forced_llm`, which is the demonstration sentence above,
measured. It needs no credentials and no network, so it runs on every push.

**The expected output above is a CI check too.**
`tests/examples/test_hw1_readme_expected_output.py` captures the in-process
command's stdout on the seeded copy and compares it to the fenced block under
*Expected output* byte for byte — and runs a control string that must *not* be
found, so a comparison that could pass on anything is caught before it passes on
this.

**The empty fabric is a separate, negative conformance test — and it is
served, not refused.** `tests/examples/test_hw1_empty_fabric_refusal.py` keeps
its name and runs both documented commands against the *unseeded* copy. Each
exits 0 and prints the same bytes as the other: `0 of 0 assembled`, a content
address, and a `D_c` of `0.0000` routing to `ok`. An operator that evaluates an
empty graph has computed something, so the answer is a computed-empty product
rather than a refusal (`D-IMPL-253` Q11/Q12) — *zero results is not zero
knowledge*. The search behind that zero rides on the product as
`computed_empty`: which operators ran, which of them returned nothing, and the
store head they read against. The `D_c` comes from that evidence and never from
the row count; this deployment declares completeness and semantic consistency as
`1` in `deployment/binding.yaml`, so the figure is `0`. Where a tolerance is
declared and the measured `D_c` exceeds it, the answer is a `tolerance-exceeded`
shell instead — hw1 declares none, in either the product class or the request
contract. Two transports agreeing on an empty answer is a useful conformance
test and a poor primary teaching experience, which is why it is not what a clean
checkout shows you first (`D-IMPL-245`).

**What *is* proven always-on underneath all of that** is the thing a reader
actually depends on — the **client contract**. The four-name surface, the
`Result` shape, the fail-closed guard, the transport inversion and cross-adapter
parity are all asserted by `tests/client/conformance` against a network-free
fixture deployment, on every push. `consume.py` uses that contract and nothing
else, so the contract holding is the guarantee that carries.

## The deployment is opaque, on purpose

`deployment/` is the producer's world. It holds `ccf_config.yaml` (the whole
Control Plane configuration, one document), `binding.yaml` (deployment wiring —
data, including the `server:` key, plus the one permitted `plan:` reference),
`scenario.yaml` (which source field plays which role) and `projection.py` (the
single Python module a deployment is permitted, per `D-IMPL-141`). There is no
`resolver.py`: the SDK builds the resolver from the data, and `binding.yaml`
refuses a `resolver:` key by name.

Open it if you are curious. Nothing in `consume.py` needs you to.

`server/` is the producer's world too, and it is off-stage: `serve.py` is the MCP
server program this deployment declares, `egress-door.yaml` holds the four
governance values it interprets, and you may open either if you are curious.
Where it sits in this example is incidental — the server is not the focus here,
and a real one commonly lives somewhere else entirely, on another machine.

## Populating a deployment

**No populated graph or producer output is committed.** The example includes a
declared signal-batch input (`runner/signal-batch.yaml`) used by its setup
program (`runner/seed.py`) to populate the deployment through the fabric's
normal single-writer path before the client runs (`D-IMPL-245` amendment 2;
`D-32` governs producer output, `D-IMPL-163`). The seed program reads the
document, boots the deployment the same way the client's in-process adapter
does, ingests every envelope through the one writer, and closes that writer
before either transport starts — nothing in the SDK knows it exists.

`binding.yaml` points `connection.database_path` at `graph.sqlite3` inside
`deployment/`, and that file and `artifact-store/` are what the seed generates;
both are `.gitignore`d. Point `binding.yaml` at your own populated graph
instead, and the seed step is not needed.

## What to change first

0. **The rows in `runner/signal-batch.yaml`.** Change a revenue and the answer,
   the count and the content address move; change an `ingestion_timestamp` and
   `D_c` moves — far enough and the routing signal changes with it. Re-run the
   seed after editing; it rebuilds the store from the document.
1. **`--min-revenue`.** A request parameter, so it changes the answer and
   therefore the content address, and it never travels through `make`.
2. **`deployment/ccf_config.yaml`'s `resolution:` and `half_life:` sections** —
   your entity vocabulary and how fast it goes stale. Changing the half-life
   moves `D_c` and can move the routing signal, which is the fastest way to see
   the debt machinery is real.
3. **`CCF_BINDING`.** The same `consume.py` against a different transport is
   the point of the client abstraction, not a feature of this example — and
   both values are above, so the fastest way to see it is to run them back to
   back and diff the two content addresses.

## What it exercises

CLAUDE.md §6.4 (No-Hardcoding — the example's code is thin and generic, the
artifacts carry everything specific), §7.1 (MCP as the SDK's bidirectional
integration surface — `server/serve.py` is the egress role, read from the far
side), §7.3 (the typed contract as the stable seam — *"portability is
demonstrated, not asserted"*), §9 (examples are the adoption contract), §10 (the
single writer — the seed program populates the graph through it and releases
it), §11. Whitepaper §6.3 (the Context Product Contract), §7.1 (the Signal
Layer — `runner/signal-batch.yaml` is a batch of L1 envelopes), §7.6 (delivery),
§7.7 (half-life and debt), §7.10 (Decision Replay), §8.3 Pattern 3 (MCP egress).
