# Adopter's guide

This is the guided path from a fresh checkout to a governed, replayable
deployment: install the SDK, declare a vocabulary, serve your first typed
Context Product, declare an agent, grant it a capability, wrap it in a
workflow with a human gate, replay the decision that came out, and finally
consume the result from a process that has never heard of CCF.

Every block of code and every artifact on this page is **literal-included
from an example the CI pipeline runs**. Nothing here is pasted, so nothing
here can drift: if one of these sources moves, this page fails to build. Each
section names the one command that runs its example, so you can reproduce
what you are reading as you read it.

The through-line to keep in view: the code you see is thin, generic
machinery, and everything specific to a deployment lives in versioned
definition artifacts. That separation is the No-Hardcoding Rule, and it is
what makes an agent a piece of governed data rather than a fork of the SDK.

## Install

Python 3.12 or newer. From the repository root, create a virtual environment
and install the package with the `dev` extra — that pulls the test toolchain
and all three harness legs:

```sh
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
```

If you also intend to build this documentation site, install the `docs` extra
alongside it (`pip install -e ".[dev,docs]"`), then `make docs`. To verify the
install end to end before going further:

```sh
make ci
```

That runs the invariant lints, `mypy --strict`, the full test suite, and every
example in this guide.

## Declare an ontology and serve your first Context Product

Run: `make example-00`.

A deployment's vocabulary — which entity kinds exist, which attributes
identify them, which relationships connect them — is an artifact, not code.
The quickstart's **entity-resolution spec** is the smallest complete example of
one. Read it as the template for your own domain: the identifier keys mint the
canonical entity URI, so the same real-world thing arriving from two unrelated
source systems converges on one node without either system knowing about the
other.

```yaml
--8<-- "archive/examples/00-quickstart/artifacts/resolution-spec.yaml"
```

That document is one of fourteen. A **deployment manifest** names every one of
them — its path, the Control Plane key it is in force under, the artifact class
it is validated against, and its `role`. `role: register` puts an artifact into
the Control Plane and into the pinned set that is dimension 2 of the Decision
Replay record; `role: load` parses and validates it exactly the same way and
hands it back, but never puts it in force. The event batch is `role: load`, and
the SDK fixes it that way: registering raw events would make re-authoring an
events file look like a change to what the fabric was *permitted* to do.

```yaml
--8<-- "archive/examples/00-quickstart/artifacts/manifest.yaml"
```

Loading that manifest and booting the fabric is one call. Assembly is where the
single-writer invariant lives — every artifact is pinned to a version before
the fabric boots, and only the assembly worker ever writes to the graph:

```py
--8<-- "archive/examples/00-quickstart/run.py:boot"
```

Raw source records enter through L1 as signal envelopes. The envelope carries
the tenant, the source identity, and both timestamps that matter — when the
fabric saw it and when the world produced it. Because the batch came back
already parsed, ingest is one loop over it:

```py
--8<-- "archive/examples/00-quickstart/run.py:ingest"
```

Reading is done by composable operators in four categories — traversal,
temporal, policy, and similarity. Their parameters come from artifacts, which
is what makes an operator plan reproducible later. The mapping handed to the
builder is assembled by naming the deployment's *own* manifest keys — that line
is configuration you read and edit, not type introspection. See the
[operator and projection Protocols](../reference/protocols/operators-and-projection.md)
for the surface each one implements:

```py
--8<-- "archive/examples/00-quickstart/run.py:operators"
```

A projection is the one piece of genuine deployment code in this picture: it
declares which operators its interpretation depends on and interprets their
output. It cannot tell the engine what ran. Its operator set is read from its
**own `projection-requirements` artifact** — never from the operator registry,
and never from the product class. The product class's `required_operator_keys`
is a *second*, separately authored document stating that set as the Control
Plane's claim, and the `refuse_operator_set_divergence` call on the line
between plan construction and `execute` refuses a disagreement between the two.
That refusal is where **authorable** drift fails: a one-key edit to either
document stops the deployment before anything is assembled (design E2,
`D-IMPL-86`).

```py
--8<-- "archive/examples/00-quickstart/run.py:project"
```

Three validation gates stand between a candidate and a servable product:
the empty-operator guard, lineage strict equality, and the TTL bound. Lineage
strict equality is the interesting one, and it is worth being precise about
what it establishes. The product's claim is filled from the product-class
declaration; `engine_resolved` is the engine's own execution record. Comparing
them establishes **assembly-path integrity** — the product served was assembled
by the path the deployment claimed. It is not an independent check on the claim
itself: the engine builds its invoked set and its execution steps in one loop
over the same operator plan, so it transcribes that plan faithfully rather than
witnessing it independently. Drift an author could introduce is caught earlier,
at the binder above (`D-IMPL-86`).

The TTL registration just above it stays in your code on purpose. Registering
the ceiling is what *mints* the pin, so the ceiling and the product's own
`expires_at` remain two independently authored numbers — and Gate 3 compares
them. A helper that did both would be comparing a value against itself. The
[Context Product Protocols](../reference/protocols/context-products.md) and
[product registration](../reference/artifacts/product-registration.md) pages
document the typed surface:

```py
--8<-- "archive/examples/00-quickstart/run.py:gate"
```

Before delivery, the decision is recorded across five dimensions. This is
audit by construction: there is no path that serves a product without
producing its record.

```py
--8<-- "archive/examples/00-quickstart/run.py:record"
```

Serving writes that record to the artifact store, content-addressed, and
hands back the product together with the reference:

```py
--8<-- "archive/examples/00-quickstart/run.py:serve"
```

You now have a fabric. Everything that follows consumes it.

## Declare an agent

Run: `make example-01`.

The SDK ships six archetypes as mechanism. It ships no agents at all — an
agent is a declared, versioned Control Plane artifact, produced by the Agent
Factory from that artifact. This is the definition file in full; the six
specialization axes are all visible in it (archetype binding, context
contract, perspective, policy regime, half-life and debt profile, and
instruction bindings by reference — never inline prompt text):

```yaml
--8<-- "archive/examples/01-agent-basics/artifacts/agent-definition.yaml"
```

The artifacts the definition *references* — its policy regime and its debt
profile — are named by the deployment manifest and registered by the same
`load_and_boot` call that booted the fabric. The definition and the prompt
artifact are not, and that is this example's choice rather than a constraint:
both carry two-field versioning and register through `register_versioned`,
which holds the author's `artifact_version` claim against content identity, and
a manifest entry may ask for exactly that path by declaring `registration:
versioned` — what it may not do is declare `typed`, which is refused at
preflight. Keeping the two calls in adopter code keeps that check visible at
the call site. The
[agent definition reference](../reference/artifacts/agent-definitions.md) and
[prompt artifact reference](../reference/artifacts/prompt-artifacts.md)
document the schemas:

```py
--8<-- "archive/examples/01-agent-basics/run.py:agent-artifacts"
```

Construction goes through the factory and nowhere else. The agent's identity
derives from the content hash of its definition, so identity is a property of
the artifact rather than of anything written in code:

```py
--8<-- "archive/examples/01-agent-basics/run.py:agent-factory"
```

Each of the six axes resolves observably — the context contract admits the
served product, the perspective conditions the view and the record, the policy
regime excludes what it excludes, and the referenced artifacts resolve at
pinned versions or construction refuses. Two of those axes are visible in the
spine itself; `tests/examples/test_agent_basics_output.py` checks all six, one
test per axis. The [agent Protocol surface](../reference/protocols/agents.md)
names the methods used here:

```py
--8<-- "archive/examples/01-agent-basics/run.py:specialization-axes"
```

Which agent, at which version, composed from which archetypes — all of it
lands in the replay record's fourth dimension:

```py
--8<-- "archive/examples/01-agent-basics/run.py:agent-replay"
```

## Grant a skill — and revoke it

Run: `make example-02`.

Skilling is the second, separate specialization channel. Capabilities attach
and detach over an agent's life **without re-declaring the agent**: the
definition artifact is byte-identical before and after the cycle below. Skills
are catalog entries — one artifact each — with declared requirements, which is
what makes the governance check mechanical. This is the entry the cycle below
grants; the same example registers two more it never binds:

```yaml
--8<-- "archive/examples/02-skilling/artifacts/skill-catalog-enrollment-metrics.yaml"
```

Registration puts the entries in the Control Plane catalog and constructs the
agent against a live view of the grant ledger — so grants and revocations take
effect at invocation time on the same constructed agent:

```py
--8<-- "archive/examples/02-skilling/run.py:skill-catalog"
```

A grant is a request through the ledger. It is audited, it changes the
in-force grant-set identity, and only then does the capability appear on the
agent's surface. The
[skill catalog](../reference/artifacts/skill-catalog.md) and
[skill grant](../reference/artifacts/skill-grants.md) references document both
artifact shapes:

```py
--8<-- "archive/examples/02-skilling/run.py:skill-grant"
```

Exercising the granted capability is an ordinary typed invocation:

```py
--8<-- "archive/examples/02-skilling/run.py:skill-exercise"
```

Governance is structural, not advisory. A grant whose declared requirements
exceed the agent's policy regime is refused with a typed value naming the
excess scopes, the refusal is audited, and nothing binds — the capability
simply does not exist from the agent's point of view:

```py
--8<-- "archive/examples/02-skilling/run.py:skill-refusal"
```

Revocation is symmetrical, and equally audited:

```py
--8<-- "archive/examples/02-skilling/run.py:skill-revoke"
```

Adapt this first by writing your own catalog entries and regime scopes. The
refusal path is the part worth exercising deliberately: a deployment that has
never seen its own governance check fire does not know whether it works.

## Compose a workflow with a human gate

Run: `make example-05`.

Workflows are Control Plane artifacts too — states, transitions, terminal
conditions, and exception routes, all declared rather than coded. See the
[workflow definition reference](../reference/artifacts/workflow-definitions.md)
for the schema:

```yaml
--8<-- "archive/examples/05-workflow-hitl/artifacts/workflow-definition.yaml"
```

A workflow definition is one of the six **author-versioned** SDK classes.
Registering it runs a bump check that holds the author's `artifact_version`
against the document's content identity — so re-authoring routing under an
unchanged version is refused. A deployment manifest **may** name it, as
`registration: versioned`, and `load_and_boot` then registers it through that
same checked path; what a manifest may not do is declare `registration: typed`
for such a class, which is refused at preflight. This example's driver
registers its four itself so those calls stay visible as the thing being
taught:

```py
--8<-- "archive/examples/05-workflow-hitl/run.py:register-definitions"
```

The engine is constructed with its injected seams — the artifact store, the
HITL transport, the node bindings, and a clock — and the workflow itself comes
from the factory. The
[orchestration and workflow Protocols](../reference/protocols/orchestration-and-workflow.md)
page documents the surfaces:

```py
--8<-- "archive/examples/05-workflow-hitl/run.py:workflow-construct"
```

Execution runs until it reaches the approval gate, then suspends with
persisted state. Suspension is a declared outcome, not an exception:

```py
--8<-- "archive/examples/05-workflow-hitl/run.py:workflow-suspend"
```

The human's action arrives through the authenticated HTTP door and is bound
to exactly what the approver saw, by content hash, and signed. The
[HITL Protocols](../reference/protocols/hitl.md) and the
[HTTP API reference](../reference/http-api.md) cover the door:

```py
--8<-- "archive/examples/05-workflow-hitl/run.py:hitl-approval"
```

Every failure mode fails closed and typed — unauthenticated, expired,
unsigned, and tampered are four distinct refusals, and none of them reaches
the authority path. The spine drives all four; that each is the *right* typed
refusal is asserted in `tests/examples/test_workflow_hitl_output.py`:

```py
--8<-- "archive/examples/05-workflow-hitl/run.py:hitl-refusals"
```

The valid submission is admitted, and the audited principal is **derived from
the verified token**, never taken from the caller's claim about itself:

```py
--8<-- "archive/examples/05-workflow-hitl/run.py:hitl-admitted"
```

The human decision then drives the workflow to its declared terminal state:

```py
--8<-- "archive/examples/05-workflow-hitl/run.py:workflow-resume"
```

And the human action lands in the record verbatim — approver, signature, and
the hash of what they were shown — alongside the engine's step sequence:

```py
--8<-- "archive/examples/05-workflow-hitl/run.py:hitl-replay"
```

## Replay the decision

Run: `make example-06`.

Replay is the payoff for everything above. From a record address alone, the
engine resolves the graph snapshot, the policy bundle version, the agent
version, the skill-set in force, and the prompt artifact version — each at its
exact recorded version, never at "latest" — and reproduces the product
byte-for-byte through the canonical serializer. The byte-equality assertion
itself lives in `tests/examples/test_decision_replay_output.py`, where a runner
can fail on it; the spine is the call it asserts about:

```py
--8<-- "archive/examples/06-decision-replay/run.py:replay-reproduce"
```

Version resolution is the mechanism that makes the reproduction meaningful.
The agent definition comes back from the store at its recorded content hash,
the prompt artifact at the version that definition pins, and the stored grant
is what the recorded grant-set hash is recomputed from rather than trusted. The
[artifact store Protocol](../reference/protocols/artifact-store.md) is the
seam these resolutions go through:

```py
--8<-- "archive/examples/06-decision-replay/run.py:replay-agent-version"
```

The negative case is the proof that the record is version-sensitive rather
than merely descriptive. The spine prepares it — a **copy** of the record, never
the canonical one, with its recorded policy-bundle version bumped to one the
Control Plane never registered — and the test suite then asserts that replaying
that copy raises `ReplayUnresolvable` rather than reproducing anything:

```py
--8<-- "archive/examples/06-decision-replay/run.py:replay-version-sensitivity"
```

If you take one habit from this guide into production, take this one: assert
byte-equality of reproduction in your own test suite. It is the single check
that catches an artifact quietly becoming a moving target.

## Consume the fabric from outside

Run: `make example-ext-00`.

The last step is the one your consumers will actually experience. An external
agent runtime reaches Context Products over MCP egress and needs **nothing**
from this codebase — no imports, no shared types, no build coupling. The whole
integration surface is a URL and a token:

```py
--8<-- "archive/examples/external/00-hello-context/client_bare.py:mcp-connect"
```

Everything else is discovered from the server: the advertised tools, their
argument schemas, and the products on offer. A consumer written this way keeps
working as the fabric grows new surfaces:

```py
--8<-- "archive/examples/external/00-hello-context/client_bare.py:mcp-discover"
```

Reading a product resource is the terminal step — and this client, with zero
CCF imports, is the strongest available statement that the typed contract on
the wire is the real boundary. The
[runtime surface reference](../reference/protocols/runtime-surfaces.md)
documents the egress side:

```py
--8<-- "archive/examples/external/00-hello-context/client_bare.py:mcp-resource"
```

## Where to go next

You have now walked the whole arc: vocabulary, fabric, agent, capability,
orchestration with a human in the loop, forensic replay, and external
consumption. To adapt it, work outward from the artifacts — a new ontology, a
new agent definition, your own catalog entries and policy regime, your own
workflow — and leave the drivers alone. If you find yourself editing code to
change behaviour, that is the signal that a value belongs in an artifact.

From here, the how-to guides are task-shaped:
[granting and revoking a skill](../how-to/grant-and-revoke-a-skill.md),
[running agents cross-process](../how-to/run-agents-cross-process.md),
[composing a workflow with HITL](../how-to/compose-a-workflow-with-hitl.md),
[swapping the artifact store](../how-to/swap-the-artifact-store.md), and
[binding a harness adapter](../how-to/bind-a-harness-adapter.md). The
[architectural invariants](../concepts/invariants.md) and the
[anatomy of a replay record](../concepts/replay-anatomy.md) explain why the
mechanism is shaped the way it is.
