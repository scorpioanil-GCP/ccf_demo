# HW-1 over three harnesses — one product, one door, three clients

**What this demonstrates.** The same governed Context Product, reached through
the same MCP door, by three programs written against three different agent
harnesses: Google ADK, the Anthropic Claude Agent SDK, and LangGraph. All three
print the same content address, and so does a reference client that uses no
harness at all. The product is the constant; the harness is the variable.

**Same product, same door, three harnesses.** That is the frame, and it is why
this is one README and not three: sibling directories would multiply the prose
and obscure that the only variable here is the harness. What differs between
the three programs is entirely harness API. None of it is CCF.

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

## What you must install

Measured from what the three programs actually import, not remembered:

| Leg | The client imports | What provides it |
| --- | --- | --- |
| 1 — Google ADK | `google.adk.tools.mcp_tool`, `mcp` | `google-adk`, `mcp` |
| 2 — Claude Agent SDK | `claude_agent_sdk` | `claude-agent-sdk` |
| 3 — LangGraph | `langgraph.graph`, `langchain_core.tools`, `mcp` | `langgraph`, `langchain-core`, `mcp` |

**Inside this repository, nothing needs installing to run the example.** All
four distributions are already dev dependencies: `pyproject.toml`'s `harnesses`
extra composes `ccf[adk,claude-agent,langgraph]` and `dev` includes it, so
`make install` has already put them there. Leg 2 additionally needs the
`claude` CLI binary, which it does not install either — the `claude-agent-sdk`
wheel bundles one at `claude_agent_sdk/_bundled/claude`, and that is what the
harness drives.

**Outside this repository, an adopter installs their own harness, an MCP
client, and nothing from CCF.** That is the claim of this example written as a
shopping list. There is no `pip install ccf` on the client side, because a
program that consumes a Context Product through an MCP tool has no CCF
dependency to acquire — which is CLAUDE.md §7.3's *"a harness that already
speaks MCP needs no adapter for consumption"*, demonstrated rather than
asserted. The fabric-side runner under `runner/` does import `ccf`, and the
next section is about why that is not a hole in the claim.

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

## The one argument tool discovery cannot teach you

The door advertises eight required arguments. Seven are self-describing — ask
the door for its tools and the JSON Schema says what each one is. The eighth,
`request`, has the schema `{"type": "string"}`, and a string is not a shape.
**A reader cannot learn this argument from tool discovery**, which is why it is
written out here in full rather than left to be discovered.

`request` carries the caller's own question, canonically encoded: a three-field
mapping, sorted keys, compact separators.

    request = json.dumps(
        {
            "product_id": arguments["product_class"],
            "parameters": arguments["parameters"],
            "temporal_boundary": question["temporal_boundary"],
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

That is the whole encode, in the standard library, and it is what
`examples/hw1-harness-clients/client_adk.py::encoded_request` and
`examples/hw1-harness-clients/client_langgraph.py::encoded_request` both
contain — character-identical to each other, so the same question document
produces the same `request` string from either program. Leg 2 does not build it
at all: the *model* fills the tool call in, which is one more consequence of the
asymmetry below.

The door parses this string rather than comparing its bytes, so the canonical
rendering is courtesy and not obligation; `json.dumps` is the entire client-side
burden and `json.loads` the entire decode.

**This is the one seam in the "an MCP tool registration and nothing else"
story, and it is a documentation obligation rather than a defect to fix.** The
encoded request is a **required** argument of the product tool by ruling `C-16`
(Phase 19) — the wire form is what carries a caller's question across the door,
and a door that accepted a loose bag of arguments would be a door with no wire
form. Publishing a richer schema for it would be a change to the codec, which
is SDK mechanism, which this phase's success criterion 7 forbids. So the phase
teaches the argument instead of widening the surface, and this section is where
that debt is paid.

## Who holds the MCP session — the asymmetry, stated

In the default path **the three programs are not the same program three ways**,
and the difference is worth knowing before you pick a harness.

| Leg | Where the MCP client lives | What this program does |
| --- | --- | --- |
| 1 — Google ADK | in **your** process | opens the session, lists the door's tools, calls one |
| 3 — LangGraph | in **your** process | the same, inside a two-node compiled graph |
| 2 — Claude Agent SDK | in an **agent binary you configure** | hands the door over as configuration and never holds a session |

Leg 2's difference is structural rather than stylistic. `claude_agent_sdk`
routes everything it does — its MCP client included — through the `claude` CLI
subprocess it bundles. So that program describes the door
(`ClaudeAgentOptions(mcp_servers={...: McpStdioServerConfig(command=..., args=[...])})`,
which is `examples/hw1-harness-clients/client_anthropic.py::session_options`),
the agent binary spawns it, speaks to it, and carries the answer back onto this
process's message stream as a tool result.

**Who holds the MCP session differs by harness. What does not differ is CCF:
one tool registration, one call, in all three legs, against the same door,
producing the same content address.** The asymmetry is the lesson, not the
embarrassment — an adopter is better off learning it here than after choosing.

And it is exactly what makes the claim testable. If the three legs printed the
same address only when they were the same program, the demonstration would be
about the programs. They are not the same program, and they still agree.

## What is deterministic, and how — per leg

Every leg is deterministic in the default path, but **the two proofs are
different instruments and the split is worth saying out loud.**

**Legs 1 and 3 make no network call at all.** Not "no model call" — no egress
of any kind. `tests/examples/test_hw1_harness_clients_no_model.py::install_no_model_guard`
patches name resolution and socket connection to refuse, drives both clients
in-process behind the guard, and requires them to still print the reference
content address. The MCP door is a spawned child speaking over pipes, so it is
unaffected; anything reaching for a host is not.

**Leg 2 does make a call, to a local fail-loud stand-in over loopback.** A
socket guard is therefore the wrong instrument for it, and this README does not
pretend otherwise. `examples/hw1-harness-clients/runner/model_stub.py` is a
Messages-API stand-in that answers a declared conversation
(`runner/model-conversation.yaml`) and nothing else: it checks every declared
exchange is paired before it says `READY`, fingerprints each request against the
declared exchange and refuses **by name** on a mismatch, and refuses on
exhaustion rather than repeating its last answer. Its determinism proof is that
refusal — a drifted conversation fails the run loudly instead of quietly
serving the nearest thing.

## Where the agent's prompt comes from

Leg 2 is the only leg that sends prompt text, and **the prompt is data the
runner supplies through the `CCF_HARNESS_PROMPT` environment variable, never a
literal in the client.** The client reads it with
`examples/hw1-harness-clients/client_anthropic.py::required`, which subscripts
rather than defaults: a defaulted read is a prompt in code wearing an
environment variable as a hat, and the default is the branch that actually runs
the day the variable goes missing.

This is the thing an adopter copying leg 2 is most likely to get wrong, so it is
not left to a reviewer: `cinv01a-prompt-shape` in `tools/lints/no_hardcoding.py`
refuses a prose-candidate literal that reaches a model-instruction sink, without
consulting any prose score at all. CLAUDE.md §6.4 is enforced here, not merely
cited.

## `--live` — one flag, one meaning

`--live` means one thing across all three legs: **point at a real populated
deployment** instead of the seeded temporary copy. No leg gains a model it did
not already have. For leg 2 it additionally drops the model stand-in, so that
leg's model is real.

Three opt-in `make` targets, one per harness. **None of them is in `examples:`
and none of them ever runs in CI** — they need a populated deployment, and for
leg 2 a real endpoint, neither of which the always-on pipeline has:

```
make example-hw1-harness-clients-live-adk
make example-hw1-harness-clients-live-anthropic
make example-hw1-harness-clients-live-langgraph
```

**Under `--live`, leg 2 requires `ANTHROPIC_BASE_URL` to be set explicitly.**
`--live` is exactly the mode that stops injecting it, and the client treats an
unset value as an error rather than defaulting to a vendor endpoint — so an
operator with a valid key who does not set it gets a refusal, and that refusal
is deliberate. It is the no-silent-live-fallback property: the runner
deliberately stops injecting the variable, and the client refuses rather than
falling back to a vendor endpoint. Set it to a real endpoint, or to a proxy.

## What to change first

1. **The deployment.** The runner copies
   `examples/hw1-companies-over-revenue/deployment` into a temporary directory
   and seeds it from `runner/scenario-rows.yaml`. Point it at your own
   deployment — or run one of the `--live` targets above against a populated
   one — and nothing about the three clients changes, which is the point.
2. **The question.** `runner/question.yaml` declares the parameters and the
   `as_of` boundary every leg pins. Change the threshold and the content
   address changes with it, in all three legs and in the reference, together.
3. **For an adopter outside this repository: the `command + args` pair and the
   eight question values.** They arrive on `argv` — `--server-command`, repeated
   `--server-arg`, and `--question-json` — precisely so they are *inputs* to a
   client rather than knowledge inside it. Swap in the command that starts your
   own MCP server and the tool name plus arguments your own door advertises, and
   the client programs are unedited. That is the whole of what an adopter
   changes, and it is what makes the client's experience *exactly what an
   adopter sees when configuring any MCP server*.

## What is deliberately out of scope

**How the MCP server is assembled and served is deliberately out of scope
here** — it stays off-stage until the assembly examples, exactly as
`examples/hw1-companies-over-revenue/README.md` says of the same door. The
server is here to be reached, not to be studied. Open
`examples/hw1-companies-over-revenue/server/` if you are curious; nothing in
these three clients needs you to, and in a real deployment it commonly lives on
another machine entirely.

Also out of scope, and stated so their absence is not read as an oversight: a
fourth harness; a model-driven leg for ADK or LangGraph (an agent *choosing* to
call CCF context is a stronger demonstration and it wants its own phase and its
own fixtures); and any new SDK mechanism at all — no new transport, no new
adapter, no change to `ccf.client` or the codec, no `HarnessAdapterProtocol`
implementation. That last one is asserted rather than promised:
`tests/examples/test_hw1_harness_clients_readme.py` compares this phase's whole
diff against `src/` and requires it to be empty.

## What it exercises

CLAUDE.md §7.3 (harness neutrality — *"a harness that already speaks MCP needs
no adapter for consumption"*, demonstrated by three of them), §6.4 (the
No-Hardcoding Rule — every deployment value in a declared document, the prompt
included), §9 (examples are the adoption contract), §11. Whitepaper §6.3 (the
Context Product Contract, which is what crosses the door), §7.6 (delivery),
§8.3 Pattern 3 (MCP egress, read from the far side).
