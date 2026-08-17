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
operator, a projection or a deployment type.

**Declared budget: 80 lines.** That number is enforced, not aspirational —
`tests/examples/test_client_example_budget.py` parses it out of *this line* and
fails the build the day `consume.py` grows past it. Phase 16's first attempt at
this example was 722 lines of Python, measured by nobody.

## Run it

From the **repository root**, with the deployment already populated:

```
CCF_BINDING="inprocess:examples/hw1-companies-over-revenue/deployment" .venv/bin/python examples/hw1-companies-over-revenue/consume.py --min-revenue 1000000000 --as-of 2026-08-01T00:00:00+00:00
```

`make example-hw1` runs that string verbatim — same flags, same values, same
interpreter. If the target and this block ever diverge, the target is wrong;
`tests/examples/test_client_example_purity.py` asserts they are
character-identical, because a documented command nobody runs and a run command
nobody documents are the same defect seen from two sides.

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

### Expected output

```
Q: which companies have revenue over 1000000000?
   Contoso Manufacturing          1850000000
   ...
   6 of 10 assembled

and what a SELECT would not have told you:
   context debt D_c   0.3886  →  forced_llm
   content address    090b1b701d02f4be1711a9b645761959fec8502283e07144dc3a23dbdbc46737
   replay record      ccf-artifact://hw1-demo/hw1.replay-record/...
   answer expires     2026-08-01 00:10:00+00:00
```

`D_c` is a **measured** number here, not a constant: the deployment's λ_c
declares a one-year half-life for a revenue observation, and the filings the
fabric learned span twelve days to almost two years, so freshness decays and
the answer routes to `forced_llm`. That is the sentence the whole example
exists to make true.

## How this example is proven — stated plainly

**No CI pipeline runs this example, and the README does not claim one does.**
It needs a populated deployment, and the always-on pipeline is network-free and
holds no credentials. `.github/workflows/live-legs.yml` is *not* the answer
either: its three jobs are all `runs-on: ubuntu-latest` and carry no database
secrets, so naming it here would name a workflow that could not reach the data.
A red check nobody can make green is worse than no check.

What proves it: a **local run**, recorded at the phase's human-verification
checkpoint, with the printed content address captured from two consecutive runs
and compared.

**What *is* proven always-on** is the thing a reader actually depends on — the
**client contract**. The four-name surface, the `Result` shape, the fail-closed
guard, the transport inversion and cross-adapter parity are all asserted by
`tests/client/conformance` against a network-free fixture deployment, on every
push. `consume.py` uses that contract and nothing else, so the contract holding
is the guarantee that carries.

## The deployment is opaque, on purpose

`deployment/` is the producer's world. It holds `ccf_config.yaml` (the whole
Control Plane configuration, one document), `binding.yaml` (deployment wiring —
data, plus the one permitted `plan:` reference), `scenario.yaml` (which source
field plays which role) and `projection.py` (the single Python module a
deployment is permitted, per `D-IMPL-141`). There is no `resolver.py`: the SDK
builds the resolver from the data, and `binding.yaml` refuses a `resolver:` key
by name.

Open it if you are curious. Nothing in `consume.py` needs you to.

## Populating a deployment

**Nothing here is committed as data** — no store file, no seed artifact, no
fixture data (`D-32`, Dave, 2026-08-15). This example asks a question of an
*already-running* Context Product; getting data into one is producer-side work
and belongs to a later example.

`binding.yaml` points `connection.database_path` at `graph.sqlite3` inside
`deployment/`, which is `.gitignore`d. Point it at your own populated graph, or
populate that one, before running.

## What to change first

1. **`--min-revenue`.** A request parameter, so it changes the answer and
   therefore the content address, and it never travels through `make`.
2. **`deployment/ccf_config.yaml`'s `resolution:` and `half_life:` sections** —
   your entity vocabulary and how fast it goes stale. Changing the half-life
   moves `D_c` and can move the routing signal, which is the fastest way to see
   the debt machinery is real.
3. **`CCF_BINDING`.** The same `consume.py` against a different transport is
   the point of the client abstraction, not a feature of this example.

## What it exercises

CLAUDE.md §6.4 (No-Hardcoding — the example's code is thin and generic, the
artifacts carry everything specific), §7.3 (the typed contract as the stable
seam), §9 (examples are the adoption contract), §11. Whitepaper §6.3 (the
Context Product Contract), §7.6 (delivery), §7.7 (half-life and debt), §7.10
(Decision Replay).
