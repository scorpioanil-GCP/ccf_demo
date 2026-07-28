---
phase: 06-phase-i-3-cross-process-harness-adapters
plan: 05
subsystem: MCP artifact persistence (ArtifactStore reference implementation)
tags: [mcp, artifactstore, xprc-01, d-26, d-impl-26, d-impl-27, d-03]
requires:
  - "06-04 (ccf.mcp.client sync bridge, ccf.mcp.errors, tests/crossproc fixture)"
  - "06-02 (mypy over /runtime; the pinned mcp dependency)"
provides:
  - "ccf_runtime.mcp.artifact_server — the authenticated §7.4 artifact MCP server"
  - "ccf_runtime.mcp.auth — TokenVerifier over a pluggable token source (D-26)"
  - "ccf.artifacts.mcp_store.McpArtifactStore — the MCP-backed ArtifactStore"
  - "ccf.mcp.client.HttpClientFactory — the credentials seam on run_with_session"
  - "tests/crossproc/servers/mcp_artifact_child.py — reusable artifact child server"
affects:
  - "06-17 / gate wave (ROADMAP criteria 1, 4, 5 now have passing observables)"
  - "examples/07-artifact-store-mcp (the swap this plan makes real)"
tech-stack:
  added: []
  patterns:
    - "structured found/not-found answers instead of McpError message matching"
    - "bytes-returning MCP resource handler for byte-exact blob transport"
    - "canonical form as a JSON round-trip fixed point, verified server-side"
key-files:
  created:
    - runtime/ccf_runtime/mcp/artifact_server.py
    - runtime/ccf_runtime/mcp/auth.py
    - src/ccf/artifacts/mcp_store.py
    - tests/crossproc/servers/mcp_artifact_child.py
    - tests/invariants/test_mcp_role_separation.py
  modified:
    - tests/conformance/test_artifactstore.py
    - src/ccf/mcp/client.py
decisions:
  - "The server holds an ArtifactStoreProtocol, not a byte-level backend of its own: put carries base64 canonical bytes, the server parses them and re-derives canonical_bytes, refusing the write if the two disagree. The canonical form is a fixed point under a JSON round trip (floats rejected, Decimal/datetime rendered as strings, keys sorted on both passes), so the address the server files under is exactly the one the client computed — and neither side has to trust the other's serializer."
  - "run_with_session gained an http_client_factory parameter. streamable_http_client accepts no headers, only a pre-built httpx.AsyncClient, so without this seam no consumer could present the bearer token D-26 requires. A factory rather than a client instance because an AsyncClient binds to the loop it runs on and that loop is the bridge's."
  - "A 401 surfaces as McpServerUnreachable, never as ArtifactNotFound. A credential refusal is a fact about reaching the server; letting it read as absence would make an expired token look like a deleted store to a replay."
  - "resolve_uri parses the caller's URI with the shared parser and then re-renders it with artifact_uri before putting it on the wire, so a malformed-but-prefixed URI cannot reach the server as though the grammar accepted it."
metrics:
  duration: ~75 min
  completed: 2026-07-26
---

# Phase 06 Plan 05: MCP-Backed ArtifactStore Summary

The §7.4 promise made real: an authenticated MCP artifact server and a
synchronous `McpArtifactStore` that passes the *same* `ArtifactStoreProtocol`
conformance suite as `FileArtifactStore` with no pre-existing test body changed
— absence discriminated from outage on a structured answer, canonical bytes
crossing the wire byte-exactly, and the artifact role provably a different
module from L6 egress.

## What was built

**`ccf_runtime.mcp.auth`** — `TokenGrant`, a `TokenSourceProtocol`, a
file-backed **development** `FileTokenSource` (re-read per lookup so revoking a
token needs no restart; a missing file refuses everything, which is the
fail-closed direction), and `SourceBackedTokenVerifier` structurally conforming
to `mcp.server.auth.provider.TokenVerifier`. Comparison is
`hmac.compare_digest` over a scan rather than a dict lookup, because a dict
lookup on a secret is a timing oracle over the token space. The docstring names
what a deployment must supply instead (D-21 language): no issuance, no
rotation, no JWT verification, no PKI/HSM custody — out per §13, exactly as
D-13 scopes A2A key custody. No token literal exists in `/src` or `/runtime`.

**`ccf_runtime.mcp.artifact_server`** — a separate module and a separate
`FastMCP` instance from `egress.py`, `stateless_http=True`, over an
`ArtifactStoreProtocol` the deployment supplies:

| Protocol method | MCP surface |
|---|---|
| `get` | Resource `ccf-artifact-blob://{content_address}`, handler `-> bytes` |
| `exists` | Resource `ccf-artifact-meta://{content_address}` → `ArtifactPresence` |
| `resolve_uri` | Resource `ccf-artifact://{tenant}/{class}/{name}@{version}` → `ArtifactResolution` |
| `put` | Tool `put_artifact` returning a declared `ArtifactRef` |

Both metadata resources answer *positively* in the negative case (`found:
false` is a successful read), which is the structured basis the client
discriminates absence from outage on. `token_verifier` and `auth_settings` are
required **together**, because `FastMCP` installs its authentication middleware
only when both are present — a server given a verifier alone would look
authenticated and refuse nothing.

**`ccf.artifacts.mcp_store.McpArtifactStore`** — plain class, no base class,
keyword-only, four synchronous Protocol methods over the 06-04 bridge and the
06-04 `run_with_session`. It builds no bridge (`grep` for `new_event_loop` /
`run_coroutine_threadsafe` is 0), re-derives no URI grammar (it routes through
`parse_artifact_uri`, which is how it inherits the `@latest` refusal for free),
and holds no naming index — the server owns it, which is what makes
`test_the_naming_index_survives_a_new_store_over_the_same_substrate` prove
something about the substrate rather than about a client cache. There is no
`except McpError` handler in the file.

**Tests** — `mcp_artifact_child.py` (a real `FileArtifactStore` behind a real
verifier, reusing 06-04's ephemeral-port/`READY` handshake verbatim), the
`mcp` conformance param, and `test_mcp_role_separation.py`.

## Verification

| Check | Result |
|---|---|
| `pytest tests/conformance/test_artifactstore.py -q` | 40 passed (18 `file`, 18 `mcp`, 4 MCP-only) |
| `pytest tests/invariants/test_mcp_role_separation.py -q` | 9 passed |
| Full suite | **749 passed, 2 skipped** (baseline 718/2; +31) |
| `mypy` | Success, 83 source files (baseline 80) |
| `tools.lints --all` | exit 0 |
| `git diff tests/conformance/test_artifactstore.py` hunks | docstring, imports, constants, `_Artifact`, `store_factory`, new fixtures, appended tests — **no pre-existing test body** |
| `bytes` → `str` on the blob handler | 2 tests fail (`test_get_returns_the_exact_canonical_bytes[mcp]`, `test_non_ascii_canonical_bytes_survive_the_wire_exactly`); restored |

Each `must_haves` truth, checked against the tree rather than asserted:

- Same suite, no test-body change — the hunk list above.
- Swap requires no other deployment change — the `mcp` branch of `store_factory`
  is a constructor call; nothing else in the file or outside it moved.
- Non-ASCII round-trips byte-exactly — `_Artifact.glyph` defaults to
  `"π ≠ 3 — ünïcode ✓ 東京"`, so *every* artifact the suite stores is non-ASCII,
  plus a dedicated test asserting both byte equality and address equality.
- Absence vs unreachable discriminated structurally — `get` falls back to the
  presence resource on a failed read, and only `found: false` becomes
  `ArtifactNotFound`.
- Role separation enforced by test — `test_mcp_role_separation.py`, by AST
  import scan and constant/source inspection, not by docstring.
- Unauthenticated client refused — two tests (no credential, rejected token).
- No fabric state change, no `ccf.graph` import — parametrized import scan over
  all four artifact-side modules, `WRITE_SURFACE_NAMES` attribute scan reused
  from `tests/agents/test_consumption_discipline.py`, and a sha256 of the graph
  file before and after a full put/exists/resolve_uri/get cycle.
- Two stores share one index — the `mcp` factory returns a **new client against
  the same running server** each call.

## Deviations from Plan

**1. [Rule 2 — Missing critical functionality] `http_client_factory` added to `ccf.mcp.client`**
- **Found during:** Task 2. `src/ccf/mcp/client.py` is not in `files_modified`.
- **Issue:** D-26 requires the store to authenticate, but `streamable_http_client`
  accepts no headers — only a pre-built `httpx.AsyncClient`. `run_with_session`
  exposed neither, so *no* consumer could present a credential. Without this the
  plan's own auth acceptance criteria are unsatisfiable.
- **Fix:** optional `http_client_factory: Callable[[], httpx.AsyncClient]` on
  `run_with_session`, entered and closed inside the call (the transport does not
  manage the lifecycle of a client it did not create). Purely additive; the
  existing crossproc suite passes unchanged. A *factory* rather than an instance
  because an `AsyncClient` binds to the loop it is used on and that loop is the
  bridge's background one.
- **Commit:** `1ea9f9b`

**2. [Rule 2] The server re-derives and verifies the canonical form**
- The plan specifies `put` carries base64 `canonical_b64` but does not say how the
  server turns bytes back into something an `ArtifactStoreProtocol` can store. The
  server parses the JSON, re-runs `canonical_bytes`, and raises
  `NonCanonicalPayload` if the result differs from what arrived — otherwise it
  would be possible to file bytes under an address a later reader would not
  recompute, which is the one failure content addressing exists to prevent
  (T-06-22). Not in the plan; added as a correctness requirement.
- **Commit:** `2cc20a4`

**3. [Rule 1] Three self-defeating docstring literals removed**
- Prose naming the scheme/symbol it promised was absent (`ccf-product://` in
  `artifact_server.py`; `new_event_loop` / `run_coroutine_threadsafe` in
  `mcp_store.py`) made the very greps the plan and the invariant test rely on
  fail. Rephrased to describe the absence without spelling the token.
- **Commits:** `2cc20a4`, `1ea9f9b`

### Acceptance criteria checked against the tree

Per the wave-3 discipline note, each criterion was verified rather than assumed.
All held, with two clarifications worth recording:

- **"Changing the `get` handler from `bytes` to `str` makes the non-ASCII test
  fail"** — **true**, verified by temporary edit and restore. Worth stating *why*,
  because the research rationale is slightly off for this codebase: canonical
  bytes here are always valid UTF-8 (`_dumps(...).encode("utf-8")` with
  `ensure_ascii=False`), so the "not round-trippable UTF-8" premise of Pitfall 4
  does not literally apply. The test still fails, and fails loudly, because
  `McpArtifactStore._read_blob` reads **only** `BlobResourceContents` and ignores
  text parts — a deliberate choice, since silently decoding text parts would
  reintroduce exactly the round trip the blob path exists to avoid. The
  protection is real; its mechanism is the client's strictness rather than an
  encoding failure.
- **`grep -c 'ccf-artifact-blob://'`** is satisfied by the docstring surface
  table, not by a code literal — the templates are built from the scheme
  constants so the server cannot drift from the shared grammar. Constant-level
  assertions in `test_mcp_role_separation.py` cover the behaviour the grep only
  approximates.

## Known Stubs

None. `FileTokenSource` is labelled a *development* implementation in its first
line rather than left to be inferred, and the surrounding docstring names what a
production deployment must supply — that is the D-21 honest-claim discipline, not
a stub.

## Threat Flags

None beyond the plan's register. The one new listener (the artifact server) is
authenticated by construction, binds only where the caller says, and is bound to
loopback in every test.

## Self-Check: PASSED

- All five created files present on disk; both modified files present.
- Commits `2cc20a4`, `1ea9f9b`, `f10a203` present in `git log`.
- Suite, mypy, and lints re-verified at the values in the table above.
