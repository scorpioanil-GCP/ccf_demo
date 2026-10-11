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

## Before you start

Everything below runs from the **repository root** of a fresh clone, on Python
3.12 or later, with nothing else set up:

```
make venv
```

That creates `.venv` and installs the hash-locked dependencies and the SDK into
it (it needs access to the package index once). After that the example needs
**no database, no network, no credentials and no environment variable** other
than the `CCF_BINDING` each command below sets on its own line — it was
re-measured on 2026-10-11 from a shell with no `CCF_*` variable and no database
credential exported. The graph is a local SQLite file the seed step writes
inside `deployment/`; nothing outside the repository is read or written.

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

The MCP run also prints, on **stderr**, the child server talking —
`Processing request of type CallToolRequest` and `… ListToolsRequest` — and,
from a dependency of the MCP server, a `pydantic_settings`
`IncompleteFieldDefinitionWarning` about a field named `lifespan`. Neither is
part of the answer; the answer is on stdout, and it is the same bytes as the
in-process run's but for the one per-answer value named below.

The interpreter is spelled `.venv/bin/python` rather than `python` because
`which python` returns nothing in this repository. If you have activated the
virtual environment, `python` is the same interpreter and you may type that.

### Why the documented command pins `--as-of`

The API default is `as_of=None`, which means *the producing deployment's own
decision instant*. The documented command passes a fixed boundary instead so
the printed debt figure and content address **reproduce exactly** — run it
twice and the address is the same string. Drop the flag and the deployment
answers as of its own decision instant, which here is not today: this
deployment declares a demonstration serve instant (next section), so both
transports answer as of 2026-08-01 00:05 UTC — the same five companies and the
same `D_c`, under a different content address, expiring at 00:15. That default
is right for a caller and wrong for a document that quotes an address.

### Why this deployment declares when it serves

The documented question is asked as of 2026-08-01 00:00 UTC, and its answer
lives ten minutes (`product_ttl_seconds` in `deployment/binding.yaml`). Since
`D-IMPL-358` an answer's expiry is judged when it is *served*, so on a fabric
whose clock reads today that answer expired long ago and is refused —
correctly. `deployment/ccf_config.yaml` therefore declares two things in this
deployment's own Control Plane (`D-IMPL-378` C1):

- a `temporal_boundary:` — how far into the past this tenant answers for (one
  hour) and how far ahead of its clock (not at all); an undeclared boundary
  refuses every question;
- a `demonstration_serve_instant:` — the instant this deployment serves at,
  2026-08-01 00:05 UTC, five minutes after the question's instant and inside
  the answer's lifetime.

Nothing a question carries can move the serve instant. The SDK refuses the
declaration unless the fabric runs on its development substrates (this
deployment's SQLite graph and file-backed store), and every replay record
written under it names the declaration, so a reader can tell a demonstration
record from a real one. Remove the section and the deployment serves on the real
clock again — and refuses the documented question on both transports with
`refused: asked-at-outside-temporal-bound`, because it asks as of a moment more
than the declared hour before today.

> **Illustrative calibration:** This example runs against a point-in-time
> demonstration estate rather than continuously refreshed production data.
> Freshness half-lives and related thresholds are calibrated to make the
> governed behavior observable in that snapshot. They demonstrate how the SDK
> applies these controls and should not be interpreted as recommended
> production coverage-policy thresholds.

The offset in `+00:00` is required, not decoration. `D-IMPL-38` admits no
implicit UTC anywhere in the fabric, so `--as-of 2026-08-01T00:00:00` is
refused by `ProductClient.ask` before any transport is reached — identically
on both bindings above, which is `D-IMPL-151` finding `B0b`. Before that
repair the same flag produced a `CanonicalizationError` on `inprocess:` and a
`TransportError` on `mcp+stdio:`, and the second was the wrong report: nothing
was wrong with the wire.

### Expected output

The in-process command prints exactly this — the whole of its stdout, nothing
elided — except one value: the replay record's address, which is issued afresh
for every answer and is therefore shown here by its shape, `<issued per answer>`.
`tests/examples/test_hw1_readme_expected_output.py` compares every other byte of
this block to a captured run on every push, and holds that one address to its
shape:

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
   replay record      ccf-artifact://hw1-demo/hw1.replay-record/<issued per answer>@<issued per answer>
   answer expires     2026-08-01 00:10:00+00:00
```

**What changes from run to run, and what does not.** Only the replay record's
address (both `<issued per answer>` segments) changes — between two runs, and
between the two transports. The five companies, `5 of 8 assembled`, `D_c
0.4271 → forced_llm`, the content address `a8335bb4…2df4` and the expiry
`2026-08-01 00:10:00+00:00` are the same on every run and on both transports,
because the question pins its instant and the deployment serves at its declared
demonstration instant (below). Change the question and the content address
changes with it: `--min-revenue 2000000000` answers two companies (Ardent
Fenwick Holdings, Marrowgate Shipping), `2 of 8 assembled`, the same `D_c`, under
content address `86afaa6251bdf5f9494117633990b714c20a16d676a3c6511698adbc99867d1f`.

### An expired question is refused, by name

The demonstration instant is a labelled clock, not a switched-off check. Ask
either documented command with its `--as-of` moved further back than the
declared hour before the serve instant — `--as-of 2026-07-31T22:00:00+00:00` —
and it prints `refused: asked-at-outside-temporal-bound` and exits 1. Move it
inside the hour but more than the answer's ten-minute lifetime before the serve
instant — `--as-of 2026-07-31T23:50:00+00:00` — and it prints
`refused: ttl-bounds` and exits 1. No content address is printed for either:
a refusal never reaches a caller as a product.
`tests/examples/test_hw1_expired_question_refusal.py` runs both, over both
transports, as ordinary passing tests.

`D_c` is a **measured** number here, not a constant: the deployment's λ_c
declares a one-year half-life for a revenue observation, and the eight filings
the fabric learned from `runner/signal-batch.yaml` were ingested at instants
spread from one month to twenty-three months before the `--as-of` boundary, so
freshness decays across them, `D_c` measures `0.4271`, and the answer routes to
`forced_llm` — inside the `[0.20, 0.60)` band `deployment/ccf_config.yaml`
declares. That is the sentence the whole example exists to make true.

**Two identities are printed, and they are different things.** The *content
address* is the hash of the served product's bytes — the answer exactly as the
caller received it — and it reproduces: ask the same question again, over
either transport, and it is the same string. The *replay record* line is the
record's own address in the artifact store, the same address in both segments.
It does not reproduce, by design: every answer's record carries an issuance
minted for that answer alone (Dave's Q11, `D-IMPL-378` E1 (a)), so every run
prints a different reference and no caller can compute one in advance. The
record names the product; the product does not name its record. The content
address moved once, for one reason: since `D-IMPL-341` every served contract
carries `ttl_anchor_at` — the instant its expiry is measured from — so the
served bytes changed, and with them the product's address. The debt, its
routing and the expiry instant did not move; the calculation is the same, the
contract says one more thing about itself. This fence was re-measured from the
run at the release qualification of `f0656746` (`docs/QUALIFICATION-f0656746.md`)
— before it, the address was `cbc7db84…d426` — and again when the example set of
`D-IMPL-378` landed: the content address, `D_c`, its routing and the expiry did
not move, and the replay line became per answer.

## How this example is proven — stated plainly

**Both the two-transport claim and the successful seeded run are always-on CI
checks.** `tests/examples/test_hw1_two_transports.py` copies this example into a
temporary directory with no graph in it, runs the copy's own `runner/seed.py`
against the copy's deployment — the committed declared input, through the single
writer — and then runs the shipped `consume.py` twice under the two shipped
bindings, requiring the two runs to agree on every printed line: the answer, the
measured `D_c`, the content address and the expiry — and on the replay line's
tenant and record class, while each run prints a well-formed reference of its
own: the two references differ, because each answer's is issued for it alone. It
also asserts the seeded run routes to `forced_llm`, which is the demonstration
sentence above, measured. It needs no credentials and no network, so it runs on
every push.

**The expected output above is a CI check too.**
`tests/examples/test_hw1_readme_expected_output.py` captures the in-process
command's stdout on the seeded copy and compares it to the fenced block under
*Expected output* byte for byte, but for the replay record's per-answer address,
which it holds to its shape — and runs a control string that must *not* be
found, so a comparison that could pass on anything is caught before it passes on
this.

**The empty fabric is a separate, negative conformance test — and it is
served, not refused.** `tests/examples/test_hw1_empty_fabric_refusal.py` keeps
its name and runs both documented commands against the *unseeded* copy. Each
exits 0 and prints the same bytes as the other, but for its replay record's
per-answer address: `0 of 0 assembled`, a content address, and a `D_c` of
`0.0000` routing to `ok`. An operator that evaluates an
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
server program this deployment declares, and it runs the SDK's standard door
(`open_door`) over the deployment `compose.py` boots; `egress-door.yaml` holds
the four values that door asserts and advertises, and `ccf_environment.yaml`
names the one variable its credential is read from (left unset, the door mints
one per boot). You may open any of them if you are curious.
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
`deployment/`, and that file and `artifact-store/` are what the seed generates.
Beside the graph the SDK also files its store marker, store-creation lock and
writer lease (`graph.sqlite3.ccf-deployment-store`,
`graph.sqlite3.ccf-store-creation.lock`, `graph.sqlite3.ccf-writer.lock`), and
the binding declares the writer's identity-lock directory, `.ccf-writer-locks/`.
All of it is generated state in the deployment's declared location, none of it
is committed, and the tests never read it: every test that runs this example
copies it into its own temporary directory **without** those files and seeds the
copy itself, so a developer's populated tree cannot make a test pass or fail.
Point `binding.yaml` at your own populated graph instead, and the seed step is
not needed.

**Checking it yourself.** The same three suites CI runs:

```
PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tests/examples/test_hw1_two_transports.py tests/examples/test_hw1_readme_expected_output.py tests/examples/test_hw1_empty_fabric_refusal.py tests/examples/test_hw1_expired_question_refusal.py -q
```

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
