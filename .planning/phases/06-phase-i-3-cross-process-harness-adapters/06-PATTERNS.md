# Phase 6: Phase I.3 — Cross-Process & Harness Adapters - Pattern Map

**Mapped:** 2026-07-26
**Files analyzed:** 22 new/modified files (from 06-RESEARCH.md § Recommended Project Structure + CONTEXT decisions)
**Analogs found:** 20 / 22 (2 have no analog)

Brownfield phase. Everything below is what the code **actually** looks like on `main`
today (I.1 + I.2 shipped), read directly, with line numbers.

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/ccf/mcp/client.py` | service (client lib) | request-response | `runtime/ccf_runtime/cdc/adapter.py` (async I/O adapter shape) | partial (role differs: `/src`, sync facade) |
| `src/ccf/mcp/errors.py` | utility (typed errors) | — | `src/ccf/artifacts/protocol.py:58-92` (typed error hierarchy) | exact |
| `src/ccf/signal/mcp_source.py` | adapter (L1 ingress) | streaming | `runtime/ccf_runtime/cdc/adapter.py` + `cdc/envelope_map.py` | exact |
| `src/ccf/artifacts/mcp_store.py` | service (store impl) | CRUD / file-I/O | `src/ccf/artifacts/file_store.py` | exact |
| `src/ccf/a2a/wire.py` | protocol decl | request-response | `src/ccf/signal/source.py` (Protocol + omission doctrine) | exact |
| `src/ccf/a2a/identity.py` | protocol decl + reference impl | transform | `src/ccf/artifacts/protocol.py` + `file_store.py` pairing | exact |
| `src/ccf/a2a/admission.py` | middleware (gate) | request-response | `src/ccf/products/gates.py` (`GateRefusal` + `ServableProduct` token) | exact |
| `src/ccf/a2a/trust_policy.py` (implied by Pattern 6) | config/artifact class | — | `src/ccf/controlplane/artifacts.py` (`HalfLifeTable`, `DeclaredArtifact`) | exact |
| `src/ccf/harness/protocol.py` | protocol decl | event-driven | `src/ccf/signal/source.py` + `src/ccf/artifacts/protocol.py` | exact |
| `src/ccf/skills/callables.py` (D-19) | registry | — | `src/ccf/operators/registry.py` | exact |
| `src/ccf/skills/dispatch.py` (modified) | service | request-response | itself — `_invoke_local_callable` is the block being replaced | self |
| `src/ccf/skills/catalog.py` (docstring modified) | model | — | itself (`LocalCallableBinding` docstring) | self |
| `src/ccf/replay/record.py` (modified, D-25) | model | — | itself — the I.2 dimension-4 extension of `PerspectiveConditioning` | self (exact precedent) |
| `runtime/ccf_runtime/mcp/egress.py` | server | request-response | `runtime/ccf_runtime/cdc/adapter.py` (placement + "what this cannot do" docstring) | role-match |
| `runtime/ccf_runtime/mcp/artifact_server.py` | server | CRUD | same as above; behavior mirrors `file_store.py` | role-match |
| `runtime/ccf_runtime/a2a/typed_http.py` | transport | request-response | `runtime/ccf_runtime/cdc/adapter.py` | role-match |
| `runtime/ccf_runtime/a2a/lf_a2a.py` | transport | request-response | `runtime/ccf_runtime/a2a/typed_http.py` (built first, D-11) | exact (once written) |
| `runtime/ccf_runtime/adapters/{claude_agent,adk,langgraph}/adapter.py` | adapter | event-driven | **none** — first harness-importing modules in the repo | none |
| `tools/lints/harness_imports.py` (modified, D-24) | config/lint | — | itself — `LLM_ADAPTER_MODULES` branch at lines 46-50, 61, 77 | self (exact precedent) |
| `tools/lints/tests/test_harness_imports.py` (modified) | test | — | itself, lines 19-53 | self |
| `tests/crossproc/conftest.py` | test fixture | event-driven | `tests/conftest.py:100-125` (skip/require env discipline); RESEARCH Pattern 4 for the subprocess shape | partial |
| `tests/conformance/test_harness_adapter.py` | test | — | `tests/conformance/test_approval_sink.py` | exact |
| `tests/conformance/test_artifactstore.py` (modified) | test | — | itself — the `params=["file"]` fixture at lines 69-95 | self |
| `pyproject.toml` (modified, D-08 + B2) | config | — | itself — `chroma` extra (line 24) and the `yaml` mypy override (lines 51-56) | self |

---

## Pattern Assignments

### `runtime/ccf_runtime/**` — placement precedent (all runtime files)

**Analog:** `runtime/ccf_runtime/cdc/adapter.py` — the **only** existing `/runtime` module.

The whole tree today is:

```
runtime/ccf_runtime/__init__.py
runtime/ccf_runtime/cdc/{__init__.py, adapter.py, envelope_map.py}
```

**Module docstring pattern** (`cdc/adapter.py:1-25`) — four mandatory blocks, in order:
citation line, "what this is not", "what this cannot do", CINV-03 tag:

```python
"""`CDCSourceAdapter` — the v0 reference ingress for Pattern 1 (FABR-09).

Whitepaper §8.3 Pattern 1 (...); DESIGN.md §2A.4.1; D-IMPL-04(b) (ingestion is
async and lives in ``ccf-runtime`` while the fabric core stays synchronous).

**What this adapter is not.** It is not a CDC transport. It holds no Kafka
consumer, no Debezium client, ... the transport is deployment infrastructure.

**What this adapter cannot do.** It cannot write. There is no ``GraphWriter``
and no ``GraphReader`` on this object, because ``SignalSourceProtocol`` has no
place to put one (DESIGN.md §2A.2.2). ...that is the only route into L3
(INV-CH7-10, INV-CH8-05, T-04-22).

Algorithmic module (CINV-03).
"""
```

> **Copy the "what this cannot do" paragraph shape verbatim into every new
> `/runtime` module**, restated for its own seam: the MCP egress server cannot
> write; the A2A transport holds no path to L2 (D-12); the harness adapter holds
> no `GraphWriter` (criterion 4). This is where criterion 4's structural claim
> is *documented*; the conformance suite is where it is *proven*.

**Note the one deviation for adapters (RESEARCH § Anti-Patterns):** harness
adapter modules must **not** carry `__ccf_mode__ = "algorithmic"` — they are the
semantic boundary. `cdc/adapter.py:39` sets it; adapters do not.

**Import direction** (`cdc/adapter.py:35-37`) — `/runtime` imports `/src`, never
the inverse, with a blank line separating the groups:

```python
from ccf.signal.envelope import SignalEnvelope, SourceIdentity

from ccf_runtime.cdc.envelope_map import CDCMappingError, to_envelope
```

**Constructor pattern** (`cdc/adapter.py:85-103`) — keyword-only, injected clock,
mutual-exclusion validated in `__init__` with a `ValueError` that names D-IMPL-38:

```python
def __init__(
    self, *, system_id: str, change_op_key: str,
    source_path: Path | str | None = None, lines: Sequence[str] | None = None,
    clock: Callable[[], datetime] | None = None,
) -> None:
    if (source_path is None) == (lines is None):
        raise ValueError(
            "CDCSourceAdapter takes exactly one feed: either source_path or lines"
        )
```

**Tenancy is a method argument, never a constructor field** (`cdc/adapter.py:78-82`,
`126`): `async def envelopes(self, *, tenant_id: str)`. The docstring states why —
"so one adapter over a shared source cannot leak an emission into the wrong tenant
by positional accident (INV-CH7-16, T-04-20)". Apply to every new multi-tenant
runtime surface (egress server, A2A receive).

---

### `src/ccf/signal/mcp_source.py` (adapter, streaming)

**Analog:** `src/ccf/signal/source.py` (the Protocol) + `runtime/ccf_runtime/cdc/adapter.py`.

The Protocol the new adapter implements — note what it *omits* (`source.py:9-13`):

```python
"""...What the Protocol deliberately omits is as load-bearing as what it declares:
there is no graph handle of any kind on this surface. An ingress adapter holds
neither ``GraphReader`` nor ``GraphWriter``, so adapter isolation and the
single-writer invariant (INV-CH7-10) are properties of the seam's shape, not
of adapter discipline."""

@runtime_checkable
class SignalSourceProtocol(Protocol):
    def source_identity(self) -> SourceIdentity: ...
    def envelopes(self, *, tenant_id: str) -> AsyncIterator[SignalEnvelope]: ...
```

**Normalization is a separate module from the adapter.** CDC splits
`adapter.py` (feed + lifecycle) from `envelope_map.py` (`to_envelope`, `CDCMappingError`).
The MCP source should split identically: transport/session in one, the
RESEARCH-Pattern-2 field mapping in another, with its own `McpMappingError`.

**Error-wrapping-with-position pattern** (`cdc/adapter.py:144-159`) — every failure
re-raised carrying which record failed:

```python
except json.JSONDecodeError as error:
    raise CDCMappingError(
        f"line {number} of the change feed is not valid JSON: {error}"
    ) from error
```

**Off-the-loop blocking I/O** (`cdc/adapter.py:115-124`): `await asyncio.to_thread(...)`
with the docstring reason "blocking the event loop in an ingestion adapter is how
one slow source stalls every other one."

---

### `src/ccf/artifacts/mcp_store.py` (service, CRUD)

**Analog:** `src/ccf/artifacts/file_store.py` — the behavioral target; and
`src/ccf/artifacts/protocol.py` — the contract.

`FileArtifactStore` is a plain class, keyword-only constructor, no base class
(`file_store.py:50-60`):

```python
__ccf_mode__ = "algorithmic"
__all__ = ["FileArtifactStore"]

_INDEX_FILENAME = ".artifact-names.json"   # module-private naming index

class FileArtifactStore:
    """Content-addressed artifacts as files under one directory.

    Args:
        root: Directory the artifacts live in. Created if absent — a store
            that refused to initialize its own directory would push that
            concern into every caller's setup path for no gain.
    """
    def __init__(self, *, root: Path | str) -> None:
        self._root = Path(root)
```

**The four sync methods the MCP store must present** (`protocol.py:192-241`), all
keyword-only:

```python
def put(self, *, tenant_id: str, artifact_class: str, name: str, artifact: object) -> ArtifactRef: ...
def get(self, *, content_address: str) -> bytes: ...
def exists(self, *, content_address: str) -> bool: ...
def resolve_uri(self, *, uri: str) -> str: ...
```

**The typed error hierarchy the MCP store must raise** (`protocol.py:58-92`) — this is
Pitfall 2's whole point; `McpError` must be discriminated into these, never
string-matched:

```python
class ArtifactStoreError(Exception):
    """...a caller can distinguish "the artifact this decision was recorded
    against is not here" from "the substrate is unreachable"..."""

class ArtifactNotFound(ArtifactStoreError, KeyError): ...
class ArtifactUriUnresolvable(ArtifactStoreError, LookupError): ...
class MovingTargetRefused(ArtifactStoreError, ValueError): ...
```

**Reuse, do not re-derive, the URI grammar** (`protocol.py:111-163`): `artifact_uri()`
and `parse_artifact_uri()` already exist and already refuse `@latest` — the docstring
says re-deriving is "how two stores would drift into resolving the same string
differently." The MCP store calls them; the MCP *server* need not know the grammar.

**The `@latest` refusal lives in the shared parser**, so the MCP store gets
`test_resolving_latest_is_refused_rather_than_answered` for free only if it routes
through `parse_artifact_uri`.

---

### `tests/conformance/test_artifactstore.py` (modified — add the `mcp` param)

**Analog:** itself. The suite was written *for* this moment (`test_artifactstore.py:1-26`
says so). The only change is one param branch:

```python
StoreFactory = Callable[[], ArtifactStoreProtocol]

@pytest.fixture(params=["file"])            # ← becomes params=["file", "mcp"]
def store_factory(request, tmp_path) -> Iterator[StoreFactory]:
    """...The MCP-backed store adds its own param here in I.3; the test bodies
    below do not change."""
    if request.param == "file":
        root = tmp_path / "artifacts"
        def factory() -> ArtifactStoreProtocol:
            return FileArtifactStore(root=root)
        yield factory
        return
    raise NotImplementedError(request.param)
```

**Constraints the suite already imposes on the MCP store** (do not plan around them):

- `test_the_naming_index_survives_a_new_store_over_the_same_substrate` (lines 319-333)
  builds **two stores over one substrate** — the MCP factory must return a new client
  against the *same* server, so the server (not the client) owns the naming index.
- `test_the_store_holds_no_graph_write_surface` (lines 189-201) does
  `inspect.getsource(module)` and asserts `"ccf.graph" not in source`. `mcp_store.py`
  may not mention `ccf.graph` even in a comment.
- `test_the_store_offers_no_mutation_or_removal_surface` (185-186) — no
  `update/delete/remove/overwrite/put_at/set` attributes.
- Pitfall 4 (non-ASCII bytes) is **not** yet covered: `_Artifact(label="alpha", ...)`
  is ASCII-only (lines 54-63). Add a non-ASCII artifact to make the blob/text
  distinction fail loudly.

---

### `tests/conformance/test_harness_adapter.py` (test)

**Analog:** `tests/conformance/test_approval_sink.py` — this is the D-09 pattern verbatim.

**Header + marker + factory type alias** (lines 1-15, 33, 53):

```python
"""The ``ApprovalSink`` conformance suite — the acceptance bar for every sink.
...the D-16 discipline of ``tests/conformance/test_artifactstore.py``:
the suite exists before the implementation it will accept.
"""
pytestmark = pytest.mark.conformance
SinkFactory = Callable[[bool], ApprovalSink]
```

**The parametrized factory** (lines 56-73) — one param per implementation, factory
takes the *argument that lets the suite drive both branches*:

```python
@pytest.fixture(params=["scripted-double"])
def sink_factory(request: pytest.FixtureRequest) -> Iterator[SinkFactory]:
    """A factory for the sink under test, one param per implementation.

    Takes the verdict the produced sink must return, because a conformance
    suite that could only observe approvals would never assert the rejection
    path. ..."""
    if request.param == "scripted-double":
        ...
        yield factory
        return
    raise NotImplementedError(request.param)
```

> For D-09 this becomes `params=["claude-agent", "adk", "langgraph"]` and the factory
> argument becomes the effects-capability the leg must exercise (D-10's inert path).
> The `raise NotImplementedError(request.param)` tail is the house style for an
> unknown param — keep it.

**The four assertion shapes to mirror** (lines 76-108): structural conformance
(`isinstance(x, Protocol)`), typed-outcome, **rejection is the same typed value not
an exception**, and canonically-serializable-so-it-can-be-audited
(`assert content_hash(outcome)`).

**Skip mechanism (Claude's Discretion).** Two in-repo precedents:

- `tests/conftest.py:107-112` — skip that becomes a **failure** when the environment
  declared the leg mandatory. This is the better fit for CI: `CCF_REQUIRE_HARNESSES`
  mirrors `CCF_REQUIRE_POSTGRES`.
  ```python
  def _unavailable(reason: str) -> None:
      """Skip, or fail if this environment declared Postgres mandatory."""
      if os.environ.get(POSTGRES_REQUIRED_ENV):
          pytest.fail(f"{POSTGRES_REQUIRED_ENV} is set but Postgres is unusable: {reason}")
      pytest.skip(reason)
  ```
  With the rationale already written at `conftest.py:102-104`: *"a postgres leg that
  quietly skips is a green build that proved nothing."*
- `tests/invariants/test_replay_by_construction.py:180-190` — the self-explaining
  deferral skip naming the activating phase, surfaced by `pytest -rs`.

---

### `src/ccf/a2a/admission.py` (middleware, request-response)

**Analog:** `src/ccf/products/gates.py`.

**Refusal-as-typed-value hierarchy** (`gates.py:75-108`) — base carries `gate` +
`detail`, subclasses carry the machine-readable fields:

```python
class GateRefusal(CCFContract):
    """Base of the structured refusals the gates return.

    Attributes:
        gate: Which gate refused.
        detail: Human-readable statement of what was wrong. The typed subclass
            fields carry the machine-readable version — the text is for the
            operator reading a log, not for a caller to parse.
    """
    gate: str
    detail: str

class LineageMismatchRefusal(GateRefusal):
    """Gate 2: declared and engine-resolved operator sets differ.

    Both sets are carried so the caller can see *which* direction failed —
    forgery, omission, or drift — without re-deriving either.
    """
    declared: frozenset[str]
    resolved: frozenset[str]
```

The same shape recurs twice more — copy whichever reads closest:
- `src/ccf/skills/grants.py:253-300` (`GrantRefusal` → `PolicyRegimeUnresolvable`,
  `GovernanceUndeclared`, `RequirementsExceedRegime`) with the explicit cross-reference
  *"The `GateRefusal` discipline: a refusal is a returned value a caller cannot swallow
  with a bare `except` and cannot accidentally proceed past."*
- `src/ccf/controlplane/registry.py:73-110` (`RegistrationRefusal` → `RefuseUnbumpedChange`,
  `RefuseEmptyBump`) — and note line 77: *"Both refusals are audited with
  `resolved=False` (T-05-04), because a version history is only trustworthy if the
  attempts it turned away are on record."* **Inbound A2A refusals land in the journal
  the same way.**

**The admitted-value token pattern** (`gates.py:113-146`) — this is how D-12's "wire
implementations never hold a path to L2" becomes structural rather than conventional:

```python
_GATE_TOKEN = object()

class ServableProduct:
    """A product that passed all three gates — the only servable form.

    Not constructible outside this module: :meth:`__init__` requires the
    module-private gate token. Holding one of these *is* the evidence that the
    gates ran, which is why the delivery path takes this type and not a bare
    :class:`~ccf.products.contract.ContextProductContract`.
    """
    def __init__(self, product: ContextProductContract, token: object) -> None:
        if token is not _GATE_TOKEN:
            raise GateBypassError(...)
```

> **Recommended:** L2's admission entry point accepts an `AdmittedProduct` carrying a
> module-private token minted only by `admission.py`. Then "a transport cannot reach L2"
> is a type fact, and D-21's strong wording is earned. Note the counter-precedent:
> D-12 of I.2 (Dave's ruling) removed the construction token from `Agent` in favour of a
> lint (`src/ccf/agents/agent.py:34-38`) — so a token is not automatic house style. If
> the plan chooses a token here, say why the A2A case differs from the `Agent` case.

---

### `src/ccf/a2a/wire.py` + `src/ccf/harness/protocol.py` (Protocol declarations)

**Analog:** `src/ccf/signal/source.py` (shown above) and `src/ccf/artifacts/protocol.py:188-241`.

House Protocol conventions, all present in both analogs:
- `@runtime_checkable class X(Protocol):` with the docstring caveat from
  `source.py:41-44`: *"`runtime_checkable` supports composition-root wiring checks; it
  verifies method presence only, so static conformance still rests on mypy."*
- Every method keyword-only after `self`.
- Bodies are `...`, never `pass`, never `raise NotImplementedError`.
- `__all__` is sorted and explicit; `__ccf_mode__ = "algorithmic"` above it.
- The docstring names **what the Protocol omits** and why (the single-writer
  argument). `wire.py` omits any L2 handle; `harness/protocol.py` omits any
  `GraphWriter` and any fabric reader — RESEARCH § Anti-Patterns: the adapter's
  fabric-side input is `Agent` and nothing else.

`Agent` is the seam the adapters bind (`src/ccf/agents/agent.py:14-30`):

```python
"""...``Agent`` is the fabric-side representation a harness adapter binds
against, exposing exactly three fabric seams (DESIGN.md §3.1):

* :meth:`consume` — a typed Context Product in, ... No other fabric-read
  surface exists — no path from ``Agent`` to L1–L5.
* :meth:`invoke_skill` — a currently-bound capability by name; an unbound
  name is a typed refusal (channel 2, CLAUDE.md §6.2).
* :meth:`emit_effect` — emission as a **returned typed value**. The agent
  never holds a graph write handle...
"""
```

---

### `src/ccf/skills/callables.py` (registry — the D-19 control)

**Analog:** `src/ccf/operators/registry.py`. This is an exact structural port; RESEARCH
recommends it because D-IMPL-37 already ruled the shape.

**Docstring doctrine to restate** (`operators/registry.py:1-26`):

```python
"""...D-IMPL-37 (explicit boot-time registration, never import side effects).

Registration is an explicit call at the composition root. No entry points, no
decorators, no import side effects — a registry populated by imports has a
population that depends on import order, and an operator plan is only
deterministic if the registry it resolves against is.

**Append-only, like the Control Plane it mirrors.** There is no ``unregister``
and no overwrite: a duplicate key is fatal at boot rather than a silent
last-writer-wins.

Algorithmic module (CINV-03).
"""
```

**Error pair + class shape** (lines 49-54, 85-143):

```python
class DuplicateOperatorKey(ValueError):
    """An operator key was registered twice (INV-CH7-29 — a boot failure)."""

class UnregisteredOperator(LookupError):
    """A plan declared an operator key the registry does not hold."""

class OperatorRegistry:
    def __init__(self) -> None:
        self._registrations: dict[str, OperatorRegistration] = {}

    def register(self, operator: Operator, *, version: str | None = None) -> None:
        if operator.key in self._registrations:
            raise DuplicateOperatorKey(
                f"operator key {operator.key!r} is already registered"
            )
        ...

    def resolve(self, key: str) -> Operator:
        try:
            return self._registrations[key]
        except KeyError:
            raise UnregisteredOperator(f"no operator registered under {key!r}") from None
```

Note `from None` on the re-raise, `keys()` returning `tuple(sorted(...))` for
introspection (line 145-147), and `__contains__` / `__len__` dunders (169-173).

**What `dispatch.py` currently does and must stop doing** (`src/ccf/skills/dispatch.py:78-108`):

```python
def _invoke_local_callable(entry, binding, arguments) -> SkillInvocation:
    """...**Accepted risk, stated so it stays visible (IN-06; T-05-18.)** The
    ``importlib.import_module`` + ``getattr`` below executes arbitrary module
    code at dispatch time. ... That precondition does not survive I.3."""
    module_name, _, attribute = binding.callable_ref.rpartition(".")
    ...
    module = importlib.import_module(module_name)
    target = getattr(module, attribute)
```

D-19 deletes `import importlib` (line 30) from this module entirely. Three docstrings
change with it: the module docstring bullet at `dispatch.py:5-12`, this function's
accepted-risk block, and `catalog.py:78-87` (`LocalCallableBinding`, *"a dotted callable
reference"*). Fixtures at `tests/fixtures/banking/skills/*.yaml` become keys registered
in `tests/conftest.py`.

**Where `mcp`/`a2a` dispatch plugs in** (`dispatch.py:151-165`) — the `NotYetBound`
tail is the exact code D-05 replaces, wave by wave:

```python
binding = entry.binding
if isinstance(binding, LocalCallableBinding):
    return _invoke_local_callable(entry, binding, arguments)
if isinstance(binding, ToolBinding):
    return ToolInvocation(...)
raise NotYetBound(
    f"skill {entry.name!r} is a {entry.skill_type!r} entry, and this"
    " build ships no dispatch transport for that type — I.3 binds the"
    " MCP/A2A transports (D-08); the entry itself is valid and remains granted"
)
```

The bindings are already declared and typed (`catalog.py:100-121`):

```python
class McpBinding(CCFContract):
    """An ``mcp`` skill's descriptor: which server and resource it names."""
    server: str
    resource: str

class A2ABinding(CCFContract):
    """An ``a2a`` skill's descriptor: the remote endpoint it names."""
    endpoint: str
```

---

### `src/ccf/replay/record.py` (modified — D-25 `harness_trace`)

**Analog:** itself. The I.2 dimension-4 extension is the exact pattern to copy.

**How the I.2 extension was done** — three coordinated edits, all still visible:

1. **The doctrine line in the module docstring** (`record.py:16-21`) records which
   phase extends which dimension:
   ```python
   4. **Perspective Conditioning** — principal and role in I.1 (INV-CH7-84);
      agent identity, version, and skill-set in force extend this dimension in
      I.2 per CLAUDE.md §6.2.
   5. **Content Generation Path** — ... workflow step sequences extend it in I.4
      per CLAUDE.md §8.1.
   ```
   D-25 adds the equivalent sentence to bullet 3.

2. **New optional fields with defaulted positive sentinels, never `None`**
   (`record.py:61-76`, `196-202`):
   ```python
   #: Dimension 3's value when no model was invoked (INV-CH7-83, Mode 1). The
   #: whitepaper's own wording; recorded rather than omitted so that "no model
   #: participated" is something the record asserts.
   MODE_1_MODEL_VERSION = "none"

   #: Dimension 4's grant-set value when no skill grant is in force (D-06/D-07).
   #: A positive claim mirroring :data:`MODE_1_MODEL_VERSION`...
   NO_GRANTS_SET_HASH = "no-grants"
   ```
   ```python
   agent_definition_hash: str = NO_AGENT_DEFINITION
   archetype_composition: tuple[str, ...] = ()
   grant_set_hash: str = NO_GRANTS_SET_HASH
   ```
   > D-25's `harness_trace` needs the same treatment: a `NO_HARNESS` sentinel
   > sub-structure, so "no harness participated" is asserted, not absent.

3. **The builder takes an optional pre-serialized block, recorded verbatim**
   (`record.py:255`, `287-292`, and the rationale at `247-274`):
   ```python
   def build_replay_record(
       *, execution, product, perspective, policy_bindings, assembly_mode,
       recorded_at, agent_conditioning: PerspectiveConditioning | None = None,
   ) -> DecisionReplayRecord:
       """...``agent_conditioning`` is the I.2 agent seam (D-06): when an agent
       made the decision, the caller passes the conditioning the agent serialized
       from its construction-time identity ... and it is recorded verbatim —
       derived, never reconstructed here."""
       ...
       model_version=ModelVersionRecord(assembly_mode=assembly_mode),
       perspective_conditioning=agent_conditioning or PerspectiveConditioning(...),
   ```
   D-25 adds `harness_trace: HarnessTrace | None = None` and threads it into
   `ModelVersionRecord(...)`.

**The five-block record is untouched** (`record.py:230-244`) — `DecisionReplayRecord`
gains no sixth field. INV-CH7-80.

**The class being extended** (`record.py:152-163`):

```python
class ModelVersionRecord(CCFContract):
    """Dimension 3 — the models invoked (INV-CH7-83)."""
    assembly_mode: AssemblyMode
    model_version: str = MODE_1_MODEL_VERSION
```

**D-18 consequence:** the fields D-18 excludes from portability comparison are exactly
the fields going into `harness_trace`. The equivalence assertion compares
`DecisionReplayRecord` with `model_version.harness_trace` excluded, and asserts exact
equality on `content_generation_path.product_content_address`,
`perspective_conditioning.grant_set_hash`, `.agent_definition_hash`, and
`policy_bindings` — all already present and already canonical-hashable.

---

### `src/ccf/a2a/trust_policy.py` (Control Plane artifact class — RESEARCH Pattern 6)

**Analog:** `src/ccf/controlplane/artifacts.py:1-33`.

The doctrine block to restate, near-verbatim:

```python
"""...**Registering the wrong thing is a detectable error.** A bare mapping stored
under a λ_c key looks exactly like a correct one until a decay computation
reads it. A typed class turns that into a validation failure at registration,
before anything can be decided against it.

**Every artifact carries its own semver lane.** ``semver`` is a declared field
with no default, so an artifact whose author never stated its lane cannot be
registered.

**Values stay out of code.** These classes declare *shape* only. ...
(CLAUDE.md §11, CINV-01; D-IMPL-38).
"""
```

`DeclaredArtifact` (exported at `artifacts.py:57`) is the escape hatch for
deployment-owned schemas — *"The SDK does not get to invent a policy-bundle schema on a
user's behalf"* (lines 27-31). The A2A trust-policy artifact is closer to
`HalfLifeTable` (SDK-owned shape, deployment-owned values): peer→JWK set,
peer→permitted producer hashes, peer→permitted schema names. And, per RESEARCH
Pattern 6, **no field that could express a verification skip**.

---

### `tools/lints/harness_imports.py` (modified — D-24 carve-out)

**Analog:** itself. `LLM_ADAPTER_MODULES` is the exact precedent, three lines apart.

**The constant** (lines 46-50):

```python
#: Vendor LLM SDKs, permitted only inside the LLM adapter path below.
VENDOR_LLM_DENY: frozenset[str] = frozenset({"anthropic"})

#: Modules allowed to import a vendor LLM SDK (the LLMClientProtocol adapters).
LLM_ADAPTER_MODULES: frozenset[str] = frozenset({"ccf.llm", "ccf_runtime.llm"})
```

**The branch** (lines 61, 66-87) — note the deny is currently an unconditional `if`,
and the LLM case an `elif` with `and not in_llm_adapter`:

```python
in_llm_adapter = matches_module(module_name, LLM_ADAPTER_MODULES)
...
if matches_module(name, HARNESS_DENY):
    findings.append(format_finding(path, lineno, RULE_HARNESS,
        f"harness import {name!r} is forbidden in core"
        " (CLAUDE.md §7.3); bind harnesses in runtime/adapters/<harness>/ instead"))
elif matches_module(name, VENDOR_LLM_DENY) and not in_llm_adapter:
    findings.append(...)
```

D-24 adds `HARNESS_ADAPTER_MODULES: frozenset[str] = frozenset({"ccf_runtime.adapters"})`
and `and not matches_module(module_name, HARNESS_ADAPTER_MODULES)` to the first branch.

**The module docstring at lines 21-22 must be amended, not left standing:**

```python
Neither rule takes an allowlist. Import restrictions have no legitimate
exceptions — an exception here would void the invariant it exists to enforce.
```

Per D-21/D-24 this becomes a scope statement: *"lint-enforced: no module outside
`ccf_runtime.adapters.*` may import a harness package."* The `LLM_ADAPTER_MODULES`
comment style ("permitted only inside…, where it is the adapter's whole purpose") is
the wording to mirror.

**The negative boundary test D-24 requires** — analog at
`tools/lints/tests/test_harness_imports.py:19-53`. `check_source` takes
`(source, path, module_name)`, so the boundary test is three lines:

```python
def test_plain_harness_import_is_flagged() -> None:
    findings = check_source("import langgraph\n", SRC, "ccf.operators.traversal")
    assert _rules(findings) == [RULE_HARNESS]
```

New cases: `"ccf_runtime.adapters.langgraph.adapter"` → clean;
`"ccf_runtime.a2a.lf_a2a"` and `"ccf_runtime.cdc.adapter"` → still `[RULE_HARNESS]`;
`"ccf_runtime.adapters_evil"` → still flagged (guards the prefix match — check what
`matches_module` does with a shared prefix).

**`LINTED_TREES` stays as-is** (`tools/lints/__main__.py:31`): the carve-out is by
module path, not by tree. Do not touch that line.

---

### `tests/crossproc/conftest.py` (test fixture, event-driven)

**Analog:** partial. No subprocess fixture exists in the repo today — RESEARCH Pattern 4
is the source for the mechanics (bind `("127.0.0.1", 0)` in the child, hand the socket
to uvicorn via `sockets=[sock]`, stdout `READY {port}` handshake, `finally: terminate()`).

What the repo *does* supply is the **failure-posture** discipline
(`tests/conftest.py:100-112`, quoted above under the harness skip) and the async-in-sync
convention (`tests/integration/test_cdc_slice.py:173-183`):

```python
def _drain(adapter: CDCSourceAdapter, *, tenant_id: str) -> tuple[SignalEnvelope, ...]:
    """Run the adapter's async emission to completion.

    ``asyncio.run`` per drain, because the fabric core is synchronous
    (D-IMPL-04(b)): the async surface is ingestion's, not L2's.
    """
    async def collect() -> tuple[SignalEnvelope, ...]:
        return tuple([e async for e in adapter.envelopes(tenant_id=tenant_id)])

    return asyncio.run(collect())
```

**No async pytest plugin is installed** — confirmed against `pyproject.toml` `[dev]`
(pytest, hypothesis, testcontainers, mypy, pytest-cov, and nothing else). RESEARCH
recommends keeping it that way.

---

### `tests/integration/test_*_slice.py` (the wave proofs)

**Analog:** `tests/integration/test_cdc_slice.py`.

**The invariant table in the module docstring** (lines 1-31) is the house form for a
slice test, and is exactly what D-23/the Cursor process note demand (rows drafted from
what would fail, not from plan intent):

```
=========================================  ===================================
Invariant / requirement                    What would fail here
=========================================  ===================================
single-writer (INV-CH7-10, INV-CH8-05)     the adapter has no writer to hand
                                           out; every claim below arrives via
                                           ``worker.ingest``
idempotent replay (INV-CH7-16/17)          re-running the same feed would
                                           manufacture claims or lineage
typed rejection (T-04-21)                  a malformed event would be skipped
                                           silently instead of raising
=========================================  ===================================
```

closing with the No-Hardcoding assertion (lines 27-30):

> *"Every domain value — entity classes, column names, identifiers, the change-op key —
> comes from `tests/fixtures/banking/ontology.yaml` and `.../cdc_events.jsonl`. Delete
> the fixtures and this file has nothing to run (CLAUDE.md §6.4 applied to fixture code)."*

**The single-writer proof shape** (lines 186-191):

```python
def _ingest_feed(fabric: FabricHandle, *, tenant_id: str) -> tuple[SignalEnvelope, ...]:
    """Drive one pass of the feed through L2 — the only route into L3."""
    envelopes = _drain(_adapter(), tenant_id=tenant_id)
    for envelope in envelopes:
        fabric.worker.ingest(envelope)
    return envelopes
```

The A2A admission slice is this with the gate in front: transport → gate →
`worker.ingest`, and no other call site.

---

### `pyproject.toml` (modified — D-08 extras, B2 mypy)

**Analog:** itself.

**The extras precedent** (lines 22-31) — note the "NEVER a core dependency" comment
carries the reason inline; D-08 asks for the same with a stronger rationale:

```toml
[project.optional-dependencies]
# chromadb is NEVER a core dependency (heavy transitive tree) — 04-RESEARCH.md Standard Stack.
chroma = ["chromadb==1.5.9"]
dev = ["pytest==9.1.1", "hypothesis==6.161.5", "testcontainers==4.15.0",
       "mypy==2.3.0", "pytest-cov==7.1.0"]
```

Dependencies are pinned with `==`, each block carrying a comment citing the RESEARCH doc
that audited it (lines 13-20). Keep that: `# Pins per 06-RESEARCH.md Standard Stack (slopcheck-audited 2026-07-26).`

**The B2 mypy override precedent** (lines 46-56) — a justified, per-module override with
a comment stating why the untyped boundary is safe:

```toml
[tool.mypy]
files = ["src"]              # ← B2: becomes ["src", "runtime"]
python_version = "3.12"
strict = true
warn_unreachable = true

# PyYAML ships no inline types and the stub package is not a runtime dependency
# of the SDK. The single `src` import of it (the Control Plane artifact loader)
# immediately validates whatever it parses through a typed artifact contract, so
# the untyped boundary is one call deep and closed by validation, not by trust.
[[tool.mypy.overrides]]
module = ["yaml"]
ignore_missing_imports = true
```

Each new override (`google.adk.*`, `langgraph.*`, `claude_agent_sdk.*`, `a2a.*`) needs
its own justification comment in this shape — not one blanket block.

**Pytest markers** (lines 39-44) — a new marker is a documented row naming its decision:

```toml
markers = [
  "postgres: requires a Postgres backend (...) — D-10",
  "chroma: requires the optional `chroma` extra — D-13",
  "conformance: shared parametrized Protocol conformance suite — D-16",
]
```

Add `crossproc:` and per-harness markers here.

**Packaging is already correct for `/runtime`** (lines 34-36) — `packages.find` already
scans `where = ["src", "runtime"]`, so new `ccf_runtime.*` subpackages ship with no
change beyond `__init__.py` files.

---

## Shared Patterns

### Module header (every new `/src` and `/runtime` module)

**Source:** universal — `src/ccf/artifacts/protocol.py:1-34`, `src/ccf/operators/registry.py:1-39`,
`runtime/ccf_runtime/cdc/adapter.py:1-41`.
**Apply to:** all 15 new source modules.

```python
"""<One-line what-and-why, naming the primitive.>

<Citation line: whitepaper §, or "SDK-defined (CLAUDE.md §7.x)"; DESIGN.md §; D-IMPL-NN.>

**<Bolded doctrine block>** <Why the shape is the shape, in prose, naming the
failure mode the alternative would produce.>

Algorithmic module (CINV-03).
"""

from __future__ import annotations

<stdlib>

<ccf.*>

<ccf_runtime.*>

__ccf_mode__ = "algorithmic"

__all__ = ["...", "..."]   # sorted
```

Per CLAUDE.md §11 / C7: every module in this phase is an SDK extension, so the citation
is **CLAUDE.md §7.1–§7.4 marked as an extension**, not a whitepaper section — except the
A2A/MCP integration patterns, which additionally cite whitepaper §8.3 Patterns 3 and 4.

**Exception:** the three harness adapters omit `__ccf_mode__` (RESEARCH § Anti-Patterns —
they are the semantic boundary; CINV-03 would deny their imports anyway).

### Constructor injection

**Source:** `runtime/ccf_runtime/cdc/adapter.py:85-103`; `src/ccf/operators/registry.py:88-89`.
**Apply to:** every new service — MCP client, artifact store, admission gate, identity
provider, adapters.

Keyword-only, private underscore attributes, injected clock, no service holds a wall
clock or a key of its own. `_utc_now` (`cdc/adapter.py:44-51`) is the default-clock shape:

```python
def _utc_now() -> datetime:
    """Wall-clock ingestion time, always tz-aware.

    The clock is an injected seam ... so replay and tests can drive ingestion
    time deterministically; this is the default a deployment gets when it has
    no reason to override.
    """
    return datetime.now(UTC)
```

### Refusals are typed values; misuse is an exception

**Source:** `src/ccf/products/gates.py:75-108`, `src/ccf/skills/grants.py:253-300`,
`src/ccf/controlplane/registry.py:73-110`.
**Apply to:** A2A admission (D-12), skill-grant checks touched by `mcp`/`a2a` dispatch.

Base contract carries `<which-check>: str` + `detail: str`; subclasses carry the
machine-readable fields; **both sides of a mismatch are carried** so the caller never
re-derives. A bad *artifact* or a missing transport is still an exception
(`NotYetBound`, `SkillNotInCatalog`, `ArtifactNotFound`) — the split is
"expected governance verdict" vs "the deployment is wrong".

### Refusals are audited with `resolved=False`

**Source:** `src/ccf/controlplane/registry.py:77-79` (T-05-04).
**Apply to:** every inbound A2A refusal.

> *"Both refusals are audited with `resolved=False` (T-05-04), because a version history
> is only trustworthy if the attempts it turned away are on record."*

### Typed errors distinguish "absent" from "unreachable"

**Source:** `src/ccf/artifacts/protocol.py:58-65`.
**Apply to:** `src/ccf/mcp/errors.py`, `mcp_store.py` (Pitfall 2).

> *"...a caller can distinguish 'the artifact this decision was recorded against is not
> here' from 'the substrate is unreachable'. The two demand opposite responses, and a
> replay that conflated them would report a missing record as an outage."*

### Sentinels are positive claims, never `None` or absence

**Source:** `src/ccf/replay/record.py:61-76`; `src/ccf/operators/registry.py:70-74`.
**Apply to:** D-25 `harness_trace`, adapter capability metadata (D-10 `effects:
unsupported` is a *declared value*, not a missing field).

> *"`None` is a positive statement — 'this deployment did not version this operator' —
> and never a placeholder the SDK invented, which is why it is not the string `"0"` or
> `"unknown"`."*

### Conformance suites are factory-parametrized and written before the impl

**Source:** `tests/conformance/test_approval_sink.py:56-73`;
`tests/conformance/test_artifactstore.py:1-26, 69-95`.
**Apply to:** `test_harness_adapter.py`, the `mcp` param on `test_artifactstore.py`.

`pytestmark = pytest.mark.conformance`; `XFactory = Callable[..., Protocol]`;
`@pytest.fixture(params=[...])` with `yield factory; return` per branch and
`raise NotImplementedError(request.param)` as the tail.

### Fixture-driven values, code-free of domain

**Source:** `tests/integration/test_cdc_slice.py:27-30`;
`tests/conformance/test_approval_sink.py:35-50`.
**Apply to:** every new test and fixture in this phase.

Fixtures live under `tests/fixtures/banking/`; loaded with `yaml.safe_load` +
`parse_artifact(...)`; the test asserts nothing a deleted fixture would leave meaningful.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `runtime/ccf_runtime/adapters/{claude_agent,adk,langgraph}/adapter.py` | adapter | event-driven | No harness-importing module has ever existed in this repo — the lint forbade it (B1/D-24). Placement comes from `runtime/ccf_runtime/cdc/`; the seam bindings come from RESEARCH § Four-Seam Binding Matrix; the *docstring and constructor* conventions above still apply. `src/ccf/llm/` is the nearest structural cousin (the other module-path carve-out) — worth a read before writing the first adapter. |
| `tests/crossproc/conftest.py` (subprocess mechanics) | test fixture | event-driven | No subprocess-spawning fixture exists. The repo's `testcontainers`/Postgres fixture (`tests/conftest.py:115+`) is session-scoped external-service management, not process spawning. Use RESEARCH Pattern 4 verbatim for mechanics; use `tests/conftest.py:100-112` for the skip/require posture. |

---

## Metadata

**Analog search scope:** `src/ccf/**`, `runtime/ccf_runtime/**`, `tests/**`,
`tools/lints/**`, `pyproject.toml`
**Files read in full or in targeted ranges:** 18
**Pattern extraction date:** 2026-07-26
