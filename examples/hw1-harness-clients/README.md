# HW-1 over three harnesses — one product, one door, three clients

**What this demonstrates.** The same governed Context Product, reached through
the same MCP door, by three programs written against three different agent
harnesses: Google ADK, the Anthropic Claude Agent SDK, and LangGraph. All three
print the same content address, and so does a reference client that uses no
harness at all. The product is the constant; the harness is the variable.

**What you read.** `client_adk.py`, `client_anthropic.py` and
`client_langgraph.py`, and nothing else. Each imports its harness, an MCP client
and the standard library, and **nothing from `ccf`** — the whole claim of this
example is that a client learns nothing about CCF to use a Context Product. That
is not a promise in this paragraph: `tests/examples/test_client_example_purity.py`
asserts it as an AST property over all four import shapes, and refuses a `ccf`
import **by name** rather than merely leaving it out of a permitted list.

**Declared budget: 300 lines.** Enforced per client program, not aspirational —
`tests/examples/test_client_example_budget.py` parses that number out of *this
line* and fails the build the day a client grows past it. (The exact line counts
are deliberately *not* quoted beside it: two numbers is two things to keep in
step, and the budget is the one that is enforced.) The budget sits close above
the largest client on purpose. A ceiling with room for another example's worth
of code is a ceiling that measures nothing, and no sabotage control can catch
one set too high — only the number can.

## Run it — three harnesses, one door

From the **repository root**. Each command drives one leg: it seeds a private
copy of the deployment, starts the door, runs that leg's client against it, and
compares what came back with the reference answer.

```
.venv/bin/python examples/hw1-harness-clients/runner/drive.py --legs adk
```

```
.venv/bin/python examples/hw1-harness-clients/runner/drive.py --legs anthropic
```

```
.venv/bin/python examples/hw1-harness-clients/runner/drive.py --legs langgraph
```

**Nothing but the leg name differs.** Not the door, not the deployment, not the
question, not the temporal boundary — one token, and it is the name of the
harness. That is this example's analogue of the single-word `CCF_BINDING` change
in `examples/hw1-companies-over-revenue`, and it is checked rather than left to
your eye: `tests/examples/test_client_example_purity.py` splits the three
commands and asserts they differ at exactly one token position, with a guard
that refuses to draw the conclusion from fewer than three commands.

`make example-hw1-harness-clients-adk`, `…-anthropic` and `…-langgraph` run
those three strings verbatim — same script, same flag, same interpreter — and
the same test asserts each documented command is character-identical to the
recipe that runs it. A documented command nobody runs and a run command nobody
documents are the same defect seen from two sides.

`make example-hw1-harness-clients` runs all three legs plus the reference in one
pass; that is the target CI runs.

The interpreter is spelled `.venv/bin/python` rather than `python` because
`which python` returns nothing in this repository. If you have activated the
virtual environment, `python` is the same interpreter and you may type that.

## What is a client here, and what is not

`runner/` is **not** part of what you read. It is the harness for the example
rather than an example of a harness: it seeds the subjects, resolves the door
from the deployment's own declarations, computes the reference answer, and
compares the three legs. It imports `ccf` and it should.

That separation is structural, not a carve-out. The purity gate's
`reader_visible_modules` globs `*.py` **directly** in this directory and does
not recurse, so a program one directory down is outside it by where it lives —
no exemption, no name in a skip list. Move `drive.py` up beside the clients and
the gate fires on it, which is the correct outcome.

## What this README does not cover

The teaching material — what each harness's binding actually looks like, why
leg 2 needs a model stand-in, what the door refuses and why a refusal is the
fabric working — is written up in the full walkthrough that lands with this
example's documentation plan. This file exists early because the two things
below it are *gated from now on*: the budget, and the three commands.
