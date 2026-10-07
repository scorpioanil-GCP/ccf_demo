# Manage keys and secrets when deploying (v0)

> SDK-defined documentation (CLAUDE.md §7.2, §8.2; D-IMPL-15, D-IMPL-21).
> Records the shipped v0 key-management posture — where signing keys come
> from, how rotation is handled, and the CI-secrets discipline. This note
> is factual to shipped mechanism; it commits to nothing the SDK does not
> already do. Authored under plan 08-04 (D-14 documentation obligation,
> carried out of D-GATE-I.4.1).

You are here because you are about to stand a fabric up somewhere real, and
you need to know what the SDK does for you and — more usefully — what it
leaves to you. This page answers four questions: where signing keys come
from, how a graph adapter's credentials reach it without entering a versioned
document, what the rotation story is, and what you must decide before exposing
the HTTP surface. It is written from shipped mechanism only.

What it does **not** cover: how to run a key-management service, how to
choose an identity provider, or how to deploy anything. Those are your
deployment's decisions, and the SDK deliberately takes no dependency on any
vendor for them. Where a decision is yours, this page says so rather than
implying a default.

Read it alongside the [HTTP API contract](../reference/http-api.md) and the
[runtime surface Protocols](../reference/protocols/runtime-surfaces.md),
which document the typed shapes named below.

## 1. Where signing keys come from

**No key material ever lives in the repository tree.** The SDK ships key
*machinery* (Protocols and reference implementations); which keys exist is
deployment configuration.

### 1.1 A2A identity (D-IMPL-15)

Cross-boundary Context Product signing uses the `IdentityProvider`
Protocol over a `SigningKeySource` Protocol
(`src/ccf/peering/identity.py`; see the
[peering Protocols](../reference/protocols/peering.md)): the provider signs canonical product
bytes into a detached JWS; the key source resolves a `key_id` to private
key material and raises `KeyUnavailable` when it holds none.

- **Sourcing:** the deployment injects a `SigningKeySource` at the
  composition root. The shipped reference, `FileBackedKeySource`, reads
  JWK files from an operator-designated directory *outside* the tree —
  it is the development reference, not a custody recommendation. A
  `key_id` is a flat name, never a path: anything that does not fullmatch
  `FileBackedKeySource.KEY_ID_PATTERN` (a letter or digit, then letters,
  digits, `.`, `_` or `-`) is refused with `KeyUnavailable` before any path
  is formed, so `..`, an absolute path, a separator or an empty id never
  reaches the filesystem (`src/ccf/peering/identity.py::FileBackedKeySource`,
  `LOW-02`). Production deployments implement the Protocol against their own key
  custody (KMS, HSM, vault); the SDK takes no dependency on any vendor.
- **Verification:** verifiers take candidate *public* keys from the
  caller (trust-policy resolution, D-IMPL-16). No key is baked into
  mechanism; a validly signed product from a key the consumer's Control
  Plane does not trust is refused at admission.

### 1.1a A2A replay defense and the signed question (SEC-022, D-IMPL-371)

A signature proves who produced an envelope; it says nothing about when, or how
often, the envelope is presented. Every inbound Peering envelope therefore
carries **issuance claims** in one signed protected-header member
(`src/ccf/peering/issuance.py::IssuanceClaims`): the instant the producer issued
it, a nonce the producer chose, and the question it answered. The payload is
unchanged, so a product's content address is unchanged.

- **Absent claims are refused** (`claims-missing`), never admitted with a
  warning.
- **The window is the peer's entitlement.** Each `PeerTrustGrant` declares
  `signature_max_age_seconds` and `permitted_clock_skew_seconds`, both
  required; the SDK ships no default. The comparison is directional — at most
  the skew after the admission instant, at most the max age before it — and is
  judged against the `now` the gate is handed, never a clock of its own
  (`stale-issuance`).
- **Replays are refused** (`replayed`) and write no second admission record.
  Only an admission spends a nonce, so a presentation refused for any other
  reason can be admitted later.
- **The replay scope is the signing key, not the peer id** (`SEC-022-C-01`).
  A nonce is spent under the key the envelope's signature verified under,
  named by its RFC 7638 thumbprint
  (`src/ccf/peering/identity.py::jwk_thumbprint`); verification is offered
  only the key the protected header names, so the gate knows which key that
  was. The same signed bytes are therefore refused under any peer id whose
  grant lists that key, however the grant writes the key, while two different
  keys that share a `kid` label keep separate scopes, so one peer cannot spend
  another key's nonces. Never reusing a nonce under the same signing key is the
  producer's obligation; the SDK ships no generator.
- **Where spent nonces live** (`SEC-022-R1`). Unless a gate is handed a
  seen-set, every gate in the process consults ONE reference set
  (`src/ccf/peering/issuance.py::InProcessSeenNonceSet`), so a second receiver
  in the same process refuses the replay the first admitted. A seen-set handed
  to a gate is used instead of the default, never beside it. The default covers
  one process only and is not pruned; it is not persisted either, so after a
  restart an envelope still inside its peer's issuance window can be admitted
  once more. It gains an entry for every envelope admitted, across every
  tenant's gates, for the life of the process, and only an admission, which
  needs a signature verified under a trusted peer's key, adds one, so a
  deployment under sustained load supplies a pruning implementation of
  `SeenNonceSetProtocol` that keeps each entry for at least its peer's
  `signature_max_age_seconds` plus `permitted_clock_skew_seconds` after the
  admission.
  **Receivers that run in more than one process must share one
  seen-set**, an implementation of
  `src/ccf/peering/issuance.py::SeenNonceSetProtocol` over a store they all
  reach. That is the deployment's obligation, and the SDK ships no such store;
  without it, each process refuses only the replays it saw itself.
- **A peered composite child is held to the subject its composite asked**,
  from the question its producer signed (closing SEC-025-U1), by the same check
  every other child leg passes.

**A request body is bounded before it is parsed, on both legs** (`SEC-021-U1`,
`D-IMPL-370`). Each Peering transport declares its size limits, with no SDK
default, and each limit bounds one thing:

- **The body cap, `max_request_bytes`, on both legs, bounds the HTTP request
  body before anything parses it.** A declared `Content-Length` over it is
  answered `413` without being read. Any other body is counted as it arrives
  and answered `413` the moment it crosses the limit, whether or not a length
  was declared. On the LF leg this happens in front of `a2a-sdk`'s JSON-RPC
  dispatcher, which is never handed more than the limit
  (`runtime/ccf_runtime/peering/lf_a2a.py::LfA2AWire.routes`; exploit tests in
  `tests/peering/test_request_body_is_bounded_before_parsing.py`).
- **The document cap bounds the carried document.** On the typed-HTTP leg the
  body *is* the canonical document, so `max_request_bytes` is also its
  document cap. On the LF leg the body is a JSON-RPC request that carries the
  document base64-encoded, so the leg declares a second limit,
  `max_message_bytes`, checked on the decoded document after parsing and on
  the outbound document in `emit`.
- **Declare the LF body cap for the encoded request.** A request carrying a
  document of `max_message_bytes` is larger than that document: about four
  thirds of it, plus a JSON-RPC envelope that depends on your identifiers.
  Measure it and set `max_request_bytes` above it, or the body cap refuses that
  document first (the sender sees `PeerUnreachable`). The SDK derives neither
  limit from the other.
- **The authoritative ceiling is the Control Plane's.**
  `InboundPayloadCeiling.max_payload_bytes` is applied by the admission gate on
  both legs before anything canonicalizes (`src/ccf/peering/admission.py`). The
  transport limits are defense in depth.

What the body cap does not do:

- **It is per request.** It does not limit how many requests are in flight at
  once, so the bytes held across concurrent requests can reach the limit times
  the number of requests your server admits. Bound concurrency at the server.
- **It cannot bound what the ASGI server buffers** before it hands the
  application a message, nor what the server does with the bytes the
  application never reads. Configure those limits in your server.
- **It bounds what this process receives, not what it reads from a peer.**
  Neither leg bounds the response an emission reads back. The typed-HTTP leg's
  `emit` reads the whole HTTP response
  (`runtime/ccf_runtime/peering/typed_http.py::TypedHttpWire.emit`), and the LF
  leg's `emit_async` fetches the peer's Agent Card and its JSON-RPC reply
  through `a2a-sdk`, which reads each in full
  (`runtime/ccf_runtime/peering/lf_a2a.py::LfA2AWire.emit_async`). A peer, or
  whatever answers at a peer's card URL, can make the emitting process buffer
  and parse as much as it chooses to send. The SDK ships no such bound: bound
  it at your egress proxy or in the HTTP client you inject into the leg.

### 1.2 SignedHitlAction (D-IMPL-21 / D-IMPL-363, HITL identity)

> **Dated note, 2026-10-03 (`D-IMPL-363`, SEC-005).** This section
> previously described `SignedPrincipalBinding` — a signature over the
> binding the door itself mints, `action_time` included, which meant a
> production signer had to predict the server's clock reading. That
> mechanism is replaced, not deprecated: the human now signs its own
> statement. The archived tutorial program under
> `archive/examples/05-workflow-hitl/` still calls the replaced API and no
> longer imports (`D-IMPL-351`: the archive is a dated reference surface
> and is not repaired); the in-tree reference for the current mechanism is
> `tests/http_api/test_sec005_attestation_door.py` (the HTTP door) and
> `tests/mcp/test_sec005_attestation_door.py` (the MCP door).

> **Dated note, 2026-10-05 (`D-IMPL-366`, SEC-006).** Identity says WHO
> acted; eligibility says whether that principal MAY approve this gate, and
> the SDK now judges it. `ApprovalPolicy` (`src/ccf/hitl/approval_policy.py`)
> carries the eligible `subject_id`s — the same axis `HitlPolicy.trusted_keys`
> is keyed by — and never keys or secrets; the pinned policy version an event
> names at suspension is the version that judges, resolved exactly, never
> "latest". The judgment runs at the transport BEFORE attestation, at the
> primitive before the claim, and at the engine before the conflict count;
> the requester (the starter) never approves their own gate; a refusal names
> no eligible principal on the wire. An execution suspended before this
> change records no starter and REFUSES at resolution under a bound plane
> (fail-closed): re-run it after upgrading.

`SignedHitlAction` (`src/ccf/hitl/identity_binding.py`) carries the
human's own signed statement about one action — `HitlActionClaims`:
tenant, event key, the action, the content hash of what they saw, their
subject id, their own `issued_at`, and a nonce — together with a detached
JWS over the claims' canonical bytes. It reuses the same D-IMPL-15
machinery as A2A, the joserfc-backed detached JWS envelope of the injected
`IdentityProvider`. The module holds no key machinery, no JOSE registry,
and no algorithm choice of its own: which keys exist and which provider
signs are the deployment's Control Plane configuration.

The binding the door records stays door-minted and unsigned. The shared
verifier (`enforce_attestation`, `src/ccf/hitl/transport.py`) compares
every signed claim with the capability, the request and the minted
binding — the verdict included — and judges the signer's `issued_at`
against the **recorded** `action_time` inside a directional window; it
reads no clock of its own, so a replay re-verifies identically. Whether a
HITL door *requires* an attestation, how wide the window is, and which
public keys each approver may sign under are all statements of the
`ccf.hitl-policy` Control Plane artifact (`signed_binding_required`,
`signature_max_age_seconds`, `permitted_clock_skew_seconds`,
`trusted_keys` — D-16 / `D-IMPL-363`), never code constants: a policy that
requires signing without stating the other three is refused when it is
registered, and the policy's per-subject key map is the **one** trust
source — there is no deployment-wide key list in code. A signature that
verifies but says something other than what is presented is refused as
`signed-binding-mismatch`; one outside the window, or whose nonce was
already presented, as `signed-binding-stale`.

**The CLI door is unsigned-only.** `ccf hitl submit` posts the action
document from the file you give it verbatim and has no signing of its
own; under a policy that requires attestation, a document that carries
none is refused. Attestation arguments for the CLI are a `D-IMPL-22`
item.

The typed decision values and the door surfaces are documented on the
[HITL Protocols](../reference/protocols/hitl.md) page;
[compose a workflow with HITL](compose-a-workflow-with-hitl.md) shows the
setting being flipped and the behavior changing with no code edit.

### 1.3 Graph adapter credentials (`D-IMPL-93`)

A graph adapter that authenticates to something — a token, a password, a
connection secret — reaches its credential over a path built so the value
cannot land in a versioned document. Three pieces, and the third is what makes
the guarantee mechanism rather than discipline.

- **The manifest names, never holds.** `DeploymentManifest.backend_secrets`
  carries `SecretReference` entries, and each entry is a *pair*: an adapter
  config field, and the environment variable whose value satisfies it. The
  value itself never appears in the document. Each config field may be
  satisfied by exactly one reference — two entries naming one field make
  "which reference was in force" ambiguous, and that answer feeds the replay
  record, so the ambiguity is refused at parse.
- **Resolution happens at boot, into a typed carrier.** `ResolvedSecret` binds
  the config field, the reference name and the resolved value in one object, so
  the adapter pin can record *which reference* was in force without recording
  what it resolved to. A reference the resolved adapter never declared as a
  credential field is refused, and so is a reference whose variable is unset or
  empty — a manifest that names a reference has asserted a credential is
  required, so the fabric refuses rather than connecting anonymously.
- **A credential cannot be content-hashed, even by accident.** The SDK's
  canonical-bytes function **refuses a `SecretStr` outright**. That is the load-
  bearing half: it means no artifact anywhere can carry a resolved credential
  into a content hash by an author's mistake, rather than everyone being asked
  to remember not to.

**The deployment rule that follows, and this project's CI follows it.** A
connection string is a deployment *environment* value, not a governance
statement. It belongs in the caller-supplied `connection=` mapping handed to
the fabric at boot — never in a versioned, content-hashed manifest, which is
why the manifest has no connection field of any kind. The manifest names the
adapter; the deployment supplies the settings that adapter's own contract
declares; the two are reconciled loudly at load. Adapter authors: see
[write a graph backend adapter](write-a-graph-backend-adapter.md) for the
`secret_fields` side of the same boundary.

## 2. Rotation posture

**Key rotation is out of v0 scope and is an operator responsibility.**
The SDK's seams are rotation-*compatible* — every signature carries a
`key_id`, verifiers accept a caller-supplied set of public keys (so old
and new keys can be trusted during a rollover), and `SigningKeySource`
resolution is per-call — but the SDK ships no rotation schedule, no
revocation list, and no key-lifecycle automation. Deployments that need
managed rotation implement it behind the `SigningKeySource` /
`IdentityProvider` Protocols.

## 3. CI-secrets discipline

Per the Phase I.4 gate (§1.2) and CLAUDE.md §3.1:

- `ANTHROPIC_API_KEY` is provided to CI exclusively as a GitHub Actions
  secret. It is never committed, never echoed in workflow logs, and never
  written to any file in the tree.
- Cross-AI reviewer credentials (`CODEX_API_KEY`, `CURSOR_API_KEY`) are
  sourced at review time from the operator-local homecams `.env` file,
  which is outside this repository and never committed here.
- The `.gitignore` excludes environments and credentials as a standing
  rule (CLAUDE.md §2.2: "never a secret in the tree"): `.env` and `.env.*`,
  and the key-material shapes `*.pem`, `*.jwk`, `*.key`, `*.p12`, `*.pfx`,
  `*.jks`, `*.keystore` and `tokens.json`. The `ignored-secrets` lint
  (`tools/lints/ignored_secrets.py::check_tree`, `LOW-04`) refuses the tree
  if any of those patterns is missing or re-opened by a `!` negation, or if a
  tracked file matches one; outside a git checkout it reports that the
  tracked-file half did not run rather than passing. Key files for
  `FileBackedKeySource` belong in operator-designated directories outside
  the checkout for the same reason.
- Every workflow under `.github/workflows/` runs with a read-only token
  (top-level `permissions: {contents: read}`), and every action is pinned
  to a full commit SHA with a trailing `# vN` comment naming the tag it was
  resolved from, so a moved upstream tag never reaches CI unreviewed.
  `.github/dependabot.yml` proposes pin bumps weekly as pull requests. The
  `ci-posture` lint enforces both (`tools/lints/ci_posture.py::check_tree`,
  `SEC-015`).
- CI installs only from the committed, hash-pinned `requirements.lock`
  (`pip install --require-hashes -r requirements.lock`), which carries the
  build set (`setuptools`, `setuptools-scm`) as well as the runtime and test
  dependencies; every editable project install is
  `pip install -e <path> --no-deps --no-build-isolation`, so nothing is
  resolved or fetched unhashed at run time. The `dependency-lock` lint
  enforces it (`tools/lints/dependency_lock.py::check_tree`, `SEC-028`);
  `README.md` gives the regeneration command. The lock cannot drift from the
  declaration: the `dependency-lock-freshness` lint
  (`tools/lints/dependency_lock_freshness.py::check_tree`, `SEC-028-F1`)
  refuses a lock that is missing a declared requirement (including the
  `[build-system].requires` build set), pins a version the declared specifier
  does not admit, or whose compile header does not name the ruled extras.

### 3.1 The distribution name is `ccf-sdk` (SEC-027)

The SDK's distribution is named `ccf-sdk`; its import name is `ccf`. The PyPI
name `ccf` belongs to Microsoft's Confidential Consortium Framework, which also
installs a top-level `ccf` package, so a distribution named `ccf` made
`pip install ccf` a dependency-confusion path. The SDK is not published to any
public index: install it from the repository, never by name, and never into an
environment that holds Microsoft's `ccf`. pip installs the two side by side
without a warning, and each overwrites or deletes the other's
`ccf/__init__.py`. `README.md` ("The distribution is `ccf-sdk`") gives the
install and migration steps. The SDK's own metadata carries the classifier
`Private :: Do Not Upload`, which PyPI refuses on every upload, so a stray
upload of the SDK to PyPI is rejected rather than published. Every reader of the SDK's own installed metadata
names `ccf-sdk`: the built-in adapter's replay pin reads its version through
`src/ccf/graph/registry.py::SDK_DISTRIBUTION`, and the release version gate
discovers through `tools/check_version_stamp.py::DISTRIBUTION`. The test
`tests/test_distribution_name.py::test_every_reader_of_the_sdks_own_metadata_names_the_declared_distribution`
holds both to `[project] name`.

## 4. Deployment posture: what to decide before a surface is up

Ten decisions have to be made explicitly, and §4.8 records two limitations the
SDK discloses rather than fixes. Each decision is a construction-time argument
or a declared artifact rather than a setting buried in configuration; where the
SDK behaves a particular way when nothing is declared, its section says so. The
first two concern the HTTP surface, whose endpoint-by-endpoint contract is on
the [HTTP API page](../reference/http-api.md): whether it authenticates at all,
and the authorization posture it applies; the third is where signing-key
custody lives, a decision about the key-source Protocol rather than about any
one surface; the fourth concerns which
transport the MCP product door serves on; the fifth concerns what the Claude
Agent SDK adapter's child process inherits; the sixth is how many processes may
boot one graph, which depends on the graph store; the seventh is which sources
may assert a classification; the eighth is which products a principal's grant
may reach; the ninth is how the erasure index is declared and protected; the
tenth is the default for a parameter a policy constraint bounds.

### 4.1 Acknowledge the insecure default, or bind an auth hook

The application factory takes an optional auth hook. Called without one, the
application performs no authentication and no authorization at all, and every
request it serves carries the full authority of the fabric handles injected
into it. That posture is legitimate for a local development loop and
catastrophic anywhere else, so it is not silent: constructing without an auth
hook emits a warning at construction *and* logs one on the first request, and
the only way to quiet it is to pass the explicit acknowledgement argument.

Decide which of the two you are doing, and make it visible at the call site.
An acknowledgement that nobody can find in a code review is the same failure
as no acknowledgement at all.

There is a second, subtler shape to avoid: binding a tenant authorizer while
leaving the auth hook unbound. The authorizer consumes the principal the auth
hook produces, so without one it can never run — a bound-but-inert authorizer
that reads like protection and provides none. The factory warns about this
case separately, because the two mistakes need different fixes.

### 4.2 Choose the authorization posture

Tenant authorization sits behind its own Protocol
([runtime surfaces](../reference/protocols/runtime-surfaces.md)), and the
reference interpreter that ships with it has three properties worth
designing around:

- **Deny by default.** No registered mapping, no matching scope, no tenant
  match, no action match — each one yields a refusal. An allow exists only
  where your scope-mapping artifact explicitly says so.
- **Re-resolved on every call.** The mapping artifact is fetched from the
  Control Plane per authorization call, with no cache and no expiry window,
  so a version change takes effect immediately — and the exact version string
  in force lands on the audit record.
- **Both outcomes audited.** Allows and denials alike append one event to the
  single Control Plane audit log, carrying the principal, the tenant, the
  action, the verdict, the matched pattern if any, the artifact version, and
  the timestamp. See [replay anatomy](../concepts/replay-anatomy.md) for how
  that material is read back.

Authorization stays at the door. It does not sink below the trust boundary
into the transport, which stays a plain queue — so do not plan a design that
relies on a second enforcement point further in.

### 4.3 Decide where key custody lives

Section 1 covers the mechanism; the deployment decision is which side of the
Protocol your keys sit on. The file-backed key source is a development
reference and nothing more. For anything else, implement the key-source
Protocol against your existing custody — a managed key service, a hardware
module, a secrets manager — and inject it at the composition root.

Two constraints follow from that and are not negotiable. No key material,
and no path that resolves to key material, belongs in the repository tree.
And because verification takes candidate public keys from the caller rather
than from anywhere inside the mechanism, the set of keys a peer is trusted
under is a Control Plane statement you author and version — see
[run agents cross-process](run-agents-cross-process.md) for that artifact in
use, and the
[Control Plane artifacts reference](../reference/artifacts/control-plane-artifacts.md)
for how it is versioned.

### 4.4 Decide which transport the product door serves on

The standard MCP product door serves on either of two transports, and they
differ in who the caller is taken to be. On the loopback transport bearer
authentication is real — the middleware sits on the HTTP application — so a
caller presenting no recognized credential is refused at the door rather than
admitted, and a caller is whoever its own credential says it is. Telling two
callers apart there means opening the door with your own identity provider's
verifier, the second of the door's two constructors; opened on the paved road
instead, the door recognizes one boot credential and nothing else.

Stdio has no HTTP application and therefore no authentication channel to
carry a credential. Its security boundary is process ownership: the server is
a child the deployment's own client spawned, under the same user, on the same
host. So stdio serves one identity, set once before anything is served, for
every caller of the process, and the door composes none of its own
(`D-IMPL-361`):

> `ProductDoor.serve_stdio` takes the identity as a required argument,
> `identity=`, which the caller composes — typically with
> `ambient_stdio_identity` — and passes explicitly. Calling it without one is
> refused with `StdioIdentityRequired` before the server is built. Stdio
> remains single-principal by construction; a multi-principal deployment uses
> `serve_loopback` or composes its own transport.

Two bounds hold on an identity composed with `ambient_stdio_identity`, and
both are mechanism rather than convention. It is scoped to exactly the one
tenant it names — pass the tenant the door was opened to serve — and it is
marked *ambient*, which makes every surface the egress registers as mutating
refuse it before the authorizer is even asked. Process
ownership is a defensible warrant for reading what the child process exists
to serve; it is not a warrant for writing on an authority nobody presented.

So a single-principal child process spawned by its own client is what stdio
is for, and it is a legitimate posture. Anything that has to tell two callers
apart — different entitlements, different perspectives, an audit trail that
distinguishes them — belongs on `serve_loopback` or on a transport you
compose yourself.

### 4.5 Declare the Claude adapter's child environment

The Claude Agent SDK adapter's child environment is a deployment-declared
allowlist (`TP-02`, `D-IMPL-361`). The `claude` child receives the variables
named in the adapter's `child_environment`, or only `PATH` and `HOME` when none
is declared, plus the variables the vendor's own spawn always sets and that
carry no fabric value: `CLAUDE_CODE_ENTRYPOINT`, `CLAUDE_AGENT_SDK_VERSION`,
`CLAUDE_CODE_ENABLE_SDK_FILE_CHECKPOINTING` when file checkpointing is on, and
`PWD`, set to the session's working directory. Nothing else is inherited from
the fabric's environment.

The adopter starts a session with `transport=adapter.transport(carrier)`. The
carrier fails closed on the vendor's default transport: its `cli_path` is a
path below `os.devnull`, which can never exist, so that transport raises
`CLIConnectionError` and starts nothing, because it would merge the fabric's
whole environment into the child. Before it connects, `adapter.transport`
checks that the system-prompt file is a regular file owned by the effective
user with mode `0600`, in a directory owned by the effective user with mode
`0700`, and raises `PromptFileRefused` otherwise.

The carrier also isolates the CLI from the host's own configuration: it sets
`tools=[]` (no built-in tools such as Bash or the file tools; only the agent's
governed skills), `setting_sources=[]` (no `~/.claude/settings.json` or project
settings, whose allow-rules could otherwise permit a tool without consulting
the adapter's permission gate) and `strict_mcp_config=True` (no MCP server but the carrier's). The
child's working directory is the per-call owner-only directory unless the
deployment declares `cwd` on the adapter. `max_turns` is the deployment's to
declare; it is a turn budget, not a security boundary.

Each carrier writes the assembled system prompt, including the canonical bytes
of every product it delivered, to that owner-only directory at rest. **Removing
it is the deployment's obligation:** call `adapter.remove_prompt_directories()`
once the sessions that used the adapter's carriers have ended. A carrier whose
directory was removed cannot start a session again.

### 4.6 Decide how many processes share a graph (SEC-013)

The fabric permits exactly one writer per graph (INV-CH7-10). Inside one
process the boot refuses a second writer from its own live-writer table. Across
processes the exclusion is the graph store's **writer lease**, and what it
covers depends on the store. Each lease declares its scope by name, and the
boot token records it.

| Store | Lease scope | What enforces it |
| --- | --- | --- |
| SQLite (reference) | `cross-process` | An exclusive `flock` on `<database file>.ccf-writer.lock`, beside the resolved database path |
| Postgres (reference) | `cross-process` | A session `pg_try_advisory_lock`, keyed server-side on the schema |
| In-memory | `process` | Nothing across processes, and nothing is needed: no second process can reach the graph |
| Fluree, MongoDB, Neo4j | `cross-process`, declared by the deployment | An exclusive `flock` on `<writer_lease_lock_dir>/<sha256(graph identity)>.lock`; the deployment declares only the absolute directory |

**On the persistent network stores the deployment declares the lease, and a
boot with none declared is refused with `WriterLeaseRequired` (SEC-013,
D-IMPL-374).** The SDK derives the lock file from the graph identity, and the
identity is the server address *as spelled* in the connection setting — its
host and port, with letter case and an omitted default port normalized and the
userinfo and the scheme dropped — plus the ledger or database and the
partition. Writers of one graph that declare the same directory contend for
the same file only if they spell the server identically, so **declare one
spelling of the server address across every writer of a graph** (FW-4,
D-IMPL-374). On Fluree, `http://localhost:8090` and `http://127.0.0.1:8090` are
two identities, two lock files and two writers on one ledger; so are a hostname
and its IP address, or two names for one load balancer, on MongoDB and Neo4j
alike. A MongoDB multi-host or replica-set URI is identified by its host list
as written: list the same hosts in the same order in every writer (a different
order, a subset, or a `mongodb+srv://` seed name against its expanded host list
is a different identity). A host list with a port on any host but the last —
the usual replica-set form `mongodb://h1:27017,h2:27017,h3:27017/?replicaSet=rs0`
included — does not parse as an identity at all, and the store refuses it with
a `ValueError` when it is constructed; that is a limit of the identity
derivation, carried, not a lease rule. A Neo4j cluster is identified by the
routing address each writer names, so name one. A relative directory is
refused by name.
**A file lease excludes only
writers that share that filesystem with real `flock` semantics: across hosts it
enforces nothing, unless the directory is on a shared filesystem whose locks
work across hosts, and two writers declaring different directories are not
excluded at all.** A cross-host lock (the reference advisory-lock lease) is
reachable only by constructing the store directly with `writer_lease=`;
`ccf.boot.boot` cannot declare it, because the connection settings carry no
credential for it. The booted `FabricHandle` reports the lease in force as
`lease_scope` and `lease_mechanism`.

**Declare the lock directory by its real path, private to the writers' user
(PC3, D-IMPL-374).** Connection validation refuses, by name, a
`writer_lease_lock_dir` reached through a symbolic link in any component (the
refusal names the real path to declare instead), one that does not exist or is
not a directory, one not owned by the booting process's effective user, and one
that is group- or world-writable. The link is refused because the directory was
resolved at each acquisition: a link retargeted between two writers'
acquisitions, as at a release cut-over through `/srv/ccf/current`, gave one
graph two lock files and both writers minted. Every lease acquisition judges
the same rule again (real path, existence, owner and mode; N-5, D-IMPL-374), so
a directory widened, swapped or reassigned after validation is refused at the
boot mint before a lock file is opened in it. A lease constructed directly with
`ccf.graph.leases.lock_directory_writer_lease` refuses a linked directory when
it is constructed and is held to the whole rule at every acquisition. Every
process that writes the graph therefore runs as the directory's owner. **Only
the declared directory's own owner and mode are checked, not its ancestors'**
(a symbolic link anywhere in the path is still refused): a principal who can
write a parent directory can rename the lock directory and put another in its
place between the check and the lock file's open, so keep every ancestor
writable only by the writers' user or root.

Consequences for a deployment on the stores that do lease:

- **Two processes that each boot the same deployment are mutually exclusive.**
  For example, two in-process client adapters or two MCP egress servers on one
  deployment root over one SQLite file or one Postgres schema. The second is
  refused at boot with `SingleWriterViolation`, naming the lease it could not
  take. A holder that dies, however it dies, gives the lease back (the kernel
  drops the `flock`; the server ends the session), so a crash never wedges a
  later boot.
- **SQLite.** The lease is only as good as the filesystem's `flock`. WAL-mode
  SQLite is already unsupported on network filesystems, so keep the database
  file and its sidecar on a local filesystem. A process forked while holding
  the lease shares it until that child exits. The sidecar is opened without
  `O_NOFOLLOW` (`src/ccf/graph/backends/sqlite.py::SqliteWriterLease`), so a
  symbolic link placed at `<database file>.ccf-writer.lock` is followed: an
  account that can write to the database file's directory can redirect the
  lease to a file of its choosing. Keep that directory writable only by the
  account the SDK runs as (disclosed 2026-10-07, `D-IMPL-377`; `D-IMPL-375`
  recorded this residual as disclosed here before it was).
- **Postgres.** Connect directly or through a *session*-pooled connection. A
  transaction- or statement-pooled connection (PgBouncer in those modes)
  cannot carry a session lock. A dropped connection loses the lease silently:
  the writer fails on its next statement, but a competing boot may already
  have succeeded. The lease is visible to an operator in `pg_locks` with
  `locktype = 'advisory'`, and it shares the database's advisory-lock key
  space with anything else using it.

**A process that only reads boots read-only, and takes no lease (FW-2,
D-IMPL-374).** The exclusion above is between *writers*. `ccf.boot.boot(...,
read_only=True)`, and `load_and_boot` or `load_config_and_boot` with the same
keyword, opens the store and the same governed reader a writer boot hands out,
but mints no writer: it takes no writer lease, marks no graph live, and is
never refused because a writer holds the graph. Boot anything that only reads a
graph a live writer serves this way, an examiner's replay first of all
(`ccf.replay.environment.RecordedEnvironment` reads through such a fabric, see
§4.7). The handle reports `lease_scope` as `read-only`, its worker refuses
every write with `ReadOnlyFabricRefused`, and its `close` closes only the
store. Because it takes no lease, a read-only boot sets `writer_lease_lock_dir`
aside before validation and never uses it (N-2, D-IMPL-374), so an examiner on
another host or under another account declares the deployment's connection
settings unchanged. **A read-only boot writes no graph content, but it is not
write-free at the substrate** (N-6, D-IMPL-374): opening the store still runs
the store's own open-time setup, exactly as a writer boot's open does. Each
store creates what it needs if it is absent: SQLite its database file, tables
and indexes; Postgres its schema, tables and indexes; MongoDB and Neo4j their
indexes; Fluree its ledger. Credentials that cannot perform that setup can fail
a read-only boot when the store is opened. A read-only boot is not coordinated
with the writer: it reads what the store returns at each read. Replay reads the
recorded snapshot boundary, which an append-only graph does not move.

### 4.7 Declare which sources may assert a classification (SEC-023, D-IMPL-372)

The Policy operator admits an entity by the value of one attribute, the one
`classification_attribute_by_class` names. That attribute comes from source
payloads like any other attribute. For each entity, the claim with the latest
ingestion timestamp replaces the whole attribute set, so without a declaration
any source can relabel a `restricted` entity as `public` simply by sending a
later record.

Name the sources that may assert the attribute on every resolution rule that
writes it:

```yaml
resolution:
  entity_rules:
    - match_key: counterparty_lei
      entity_class: counterparty
      identity_keys: [counterparty_lei]
      attribute_keys: [counterparty_name, classification]
      attribute_authorities: {classification: [core-banking]}
```

Three things follow, and all three are mechanism:

- **A claim from any other source is refused whole and recorded.** The L2
  worker writes nothing from that envelope for that entity. It does not strip
  the attribute, and it does not merge the attribute with the authoritative
  value. It appends an `attribute_assertion_refused` event to the Control
  Plane audit log, and it lists the refusal on `IngestResult`
  (`src/ccf/assembly/worker.py::AssemblyWorker.ingest`). The refused value is
  not copied anywhere. The refusal is never raised, so a source without
  authority cannot block your serves. An authorized source may move the label
  in either direction.
- **An empty source set means no source may assert the attribute.**
- **A deployment that omits the declaration does not boot.** If a Policy
  operator admits on an attribute that a rule writes with no
  `attribute_authorities`, `load_and_boot` and `load_config_and_boot` refuse
  with `UngovernedClassificationAttribute`
  (`src/ccf/graph/protocols.py::UngovernedClassificationAttribute`)
  before anything is registered.

Authority is only as strong as your binding of `SourceIdentity.system_id` to a
real system. The SDK does not attest source identity: the adapter declares it.
The same refusal also fires when a classification consumer is built or used:
`build_operator_registry`, `PolicyFilter.apply` and the booted reader's
`query` refuse a classification map the authority does not cover, including an
attribute the resolution spec neither writes nor governs, so a hand-built
operator, a hand-composed `ccf.boot.boot` and a per-request registry are
covered too (`D-IMPL-374`;
`src/ccf/graph/protocols.py::require_classification_authority`). The authority
is minted only by `ccf.boot.boot`, from the resolution spec its L2 enforces,
and carries that spec's content address. A view or query with no authority is
refused with `ClassificationAuthorityMissing`, and one carrying an authority
boot did not mint is refused with `ClassificationAuthorityNotMinted`. The
shipped store readers (every `BaseGraphReader` backend, the memory reader,
Fluree's pinned read) and a mounted peer product refuse a classification query
that did not come through a booted reader. A claim from an unauthorized source
that omits a governed attribute is still written, and blanks the label if one
was present, but it is recorded as a `governed_attribute_omitted` audit event
(`src/ccf/assembly/worker.py::AssemblyWorker.ingest`). Three boundaries
remain: an out-of-tree graph reader that does not subclass `BaseGraphReader`
is unguarded unless it calls `require_query_classification_authority` itself;
the declared-read boundary (an operator that filters on a classification
attribute without declaring it in `read_intent` is not checked when it is
registered, so its own `apply` must call `require_classification_authority`);
and a source that is authorized for an attribute may set it in either
direction, including by omitting it, without an event.

**Replaying a classification decision beside a live writer needs a read-only
boot (FW-2, D-IMPL-374).** Only a booted reader carries an authority, and a
writer boot takes the store's writer lease (§4.6). On a persistent store that
a live writer holds, the writer boot is refused and a raw store reader refuses
the classification query, so a replay tool in another process had no road.
`boot(..., read_only=True)` is that road. It resolves the pinned resolution
spec and mints the authority from it through the same private mint as a writer
boot, so its views carry an authority `ClassificationAuthorityNotMinted` does
not refuse, and the Policy operator re-executes. It mints no writer, takes no
lease and writes no graph content, although opening the store still runs the
store's own open-time setup (§4.6, N-6). Open the fabric you pass to
`RecordedEnvironment` this way. A raw store reader is still refused, and an
authority built by hand is still refused on a read-only view.

### 4.8 Two deployment limitations, disclosed rather than fixed

Two behaviors are deliberate designs with recorded reasons, so they are stated
here as limitations a deployment plans around rather than changed (`D-IMPL-372`,
Q2 (a)).

- **A reserved graph-backend name denies boot.** Any installed distribution
  that declares a `ccf.graph_backends` entry point under a name the SDK's own
  adapters hold refuses every backend resolution, by design, rather than
  letting the adapter set depend on discovery order
  (`src/ccf/graph/registry.py::ReservedBackendName`,
  `src/ccf/graph/registry.py::declared_names`; the
  [storage and graph Protocols page](../reference/protocols/storage-and-graph.md)
  states the fail-closed rule). One misbehaving package in the environment is
  therefore a boot outage, not a silently ignored adapter: control what is
  installed beside the SDK, and treat a `ReservedBackendName` at boot as a
  supply-chain finding.
- **The stdio client adapter hands its child the whole parent environment.**
  `src/ccf/client/adapters/mcp_stdio.py::McpStdioAdapter` spawns the
  deployment's own server program with `env=dict(os.environ)`, deliberately: it
  is the deployment's code, reaching the same substrate settings and the same
  credentials, and the MCP library's filtered default environment would
  silently run a different checkout. The consequence is that every secret in
  the client process's environment is visible to the child. A process holding
  credentials its child must not see should not use the stdio adapter from
  that process; spawn the client from an environment that carries only what
  the server needs, or use the loopback transport.

### 4.9 Declare a product roster for principals that must not reach every product (SEC-017, D-IMPL-374)

Tenancy decides whose data a credential reaches. Within its tenant, a principal
whose grant declares no product roster reaches every Context Product class that
the doors serve it. **Declaring the roster is your obligation as the
deployment.** The SDK ships no default roster, and a grant without one is
tenant-wide.

Declare the roster on the principal's grant, as Context Product class names:

```json
{"<token>": {"client_id": "analyst-7", "scopes": ["ccf:experience"],
             "tenants": ["bank-a"], "products": ["credit-risk.spread"]}}
```

`"products": null`, or no `products` key, means tenant-wide. `"products": []`
means no product at all.

One rule applies wherever a product class is known at the call. A request that
reaches a class off the roster is refused by name, after the tenant check and
**before** the authorizer is asked, so no allow is recorded for it
(`runtime/ccf_runtime/mcp/tenancy.py::ProductOutsideRosterRefused` on MCP,
`product-outside-roster` with a 403 on HTTP).

| Surface | The class it is held to |
| --- | --- |
| MCP Experience `context_product` resource | the class in the URI |
| MCP `get_context`, `get_lineage` | the declared `entitled_product_class` |
| MCP `invoke_agent` | the agent's `product_classes`, from your agent directory |
| MCP `list_agents` | lists only the agents `invoke_agent` would dispatch |
| MCP `get_replay_record` | the declared `replay_record_product_class` |
| MCP egress product resource, product tool, addressed resource | the class in the call |
| HTTP `GET /product/{tenant}/{product_class}/{version}` | the class in the path |
| HTTP `GET /replay/decisions`, `GET /replay/resolutions` | `create_app`'s declared `replay_record_product_class` |

Surfaces that cannot know a product class at the call are not bound by the
roster: the MCP artifact server and the HTTP `/artifact` routes (addressed by
content address or by class and name), the MCP HITL server and HTTP `/hitl`
routes, and the HTTP `/agent`, `/skill`, `/workflow`, `/config`, `/schema` and
`/backends` routes. Control those with the scope mapping.

Two things you must supply:

- **Build agent directory entries with `exposed_agent`**
  (`runtime/ccf_runtime/mcp/agent_directory.py::exposed_agent`). It derives
  the entry's `product_classes` from the definition's context contract
  (`consumes ∪ emits`). An entry that states its own `product_classes` is
  refused when it is built. A rostered principal is refused an agent whose
  entry carries no derived classes.
- **Declare `replay_record_product_class`** on `build_experience_server` and on
  `create_app` if rostered principals should read replay records. The SDK
  names no class. `build_experience_server` takes `None` when you pass nothing.
  `create_app` has no default: you state the value, and `None` is how you say
  you name no class. Either way, `None` means a rostered caller is refused every
  replay read.

`invoke_agent` reads your agent directory before the authorizer decides, so a
rostered caller the authorizer would refuse still reaches that lookup. The
refusal it gets is therefore the same for an unknown agent, an agent not
exposed, an agent without derived classes and an agent reaching an off-roster
class: it names no agent and no class. The specific reason is logged
server-side (logger `ccf_runtime.mcp.tenancy`, level INFO).

### 4.10 Declare and protect the erasure index (SEC-009, D-IMPL-374)

An erasure is recorded, never performed: every store construction site
withholds an erased address, reading the deployment's durable erasure index
(`src/ccf/erasure/index.py::FileErasureIndex`), declared at every site with no
default.

**What an erasure is not (FW-4, D-IMPL-374).** It is not graph erasure. The
Context Graph (L3) keeps the subject's attributes, and every Context Product
assembled after the erasure reads them and carries them. An erasure withholds
whole artifacts only; nothing narrower than an artifact is withheld. It
destroys nothing: the bytes stay on the substrate, and the SDK makes no claim
that anything was deleted. And it makes no legal-compliance claim: whether
withholding these artifacts satisfies any obligation — a right-to-erasure
request, for example — is the deployment's own legal determination, made
knowing that the graph and every new product still hold the subject.

Decide these things before an erasure is ever approved.

- **Where the index lives, and who can write it.** The file index opens with
  `O_NOFOLLOW` and refuses, by name (`ErasureIndexInsecure`), a file that is a
  symlink, not owned by the process's user, or not mode 0600, or a directory
  that is not owned by that user or not mode 0700. Every line carries the hash
  of the one before it, so an edited, reordered or removed line refuses at boot
  (`ErasureIndexCorrupt`, which withholds every address under the index).
  **An attacker with write access to the index file can un-erase its tail;
  file modes and the deployment's filesystem controls are the mitigation.** A
  hash chain cannot show that its last lines were cut off.
- **Which classes the erase capability may write.** Declare
  `ccf.erasure-record` and `ccf.erasure-approval` under `ArtifactErase` in the
  store's `WriteKinds`, and grant `artifact.erase` only to the principals who
  may file an erasure request. Neither class can be declared erasable.
- **Which HITL policy signs the approvals.** An erasure approval is bound to
  a SIGNED HITL attestation (`D-IMPL-363`), so the HITL policy the erasure
  gate runs under must require signed bindings and pin each approver's public
  key. The door refuses, by name, an approval that is unsigned
  (`approval-unsigned`) or whose signature does not verify
  (`approval-signature-invalid`). It files the approval, with its signed claim
  set, signature and key id verbatim, as an immutable `ccf.erasure-approval`
  before the index append, and every store construction site verifies that
  signature again, against the key the pinned policy declares for the
  approver, resolved through its own Control Plane
  (`src/ccf/erasure/approval.py::verify_erasure_approval`). An approval that
  does not verify is `index-unsupported`: the address stays withheld and the
  audit says so.
- **Which erasure authority each site trusts, fixed at composition.** Every
  store construction site — `create_app` (through
  `ApiDependencies.erasure_trust`), `build_artifact_server`, `open_product`,
  `build_governed_resolver`, the in-process adapter (through `binding.yaml`'s
  `erasure_authority`) and the local CLI dependencies — takes an
  `ErasureTrust`: for each tenant that may erase, an `ErasureAuthority`
  naming the HITL policy key its HITL transport is bound to, the content hash
  of its erasure workflow definition, and the erasure door's public signing
  key (`src/ccf/erasure/trust.py`). The record's tenant selects the
  authority; a tenant with none reads `index-unsupported`. A multi-tenant
  site declares one authority per erasing tenant. The door refuses each of
  the following by name, before anything is written; the consult, which never
  says which check failed, withholds the address as `index-unsupported` and
  audits `erasure_index_unsupported`: an approval that pins any other HITL
  policy key, that names any workflow but the declared one or any tenant but
  the authority's, by the requester, by an approver the declared workflow's
  erasure-gate policy does not name, for a gate that is not that workflow's
  erasure gate, or signed after the pinned policy version was superseded by
  the next one. The
  requester's artifacts may name a policy version, never the key, the
  workflow or the policy. A legitimate approval made while the old policy
  version was current stays valid after a rotation.
- **Who holds the erasure door's signing key.** The door signs the canonical
  bytes of every erasure record it files with a key the deployment holds and
  requesters never do; each authority declares its public half, and a
  declared key carrying private material is refused by name. Every consult
  verifies that signature before it reads the record, so the record's
  `requested_by` — the starter the engine recorded, which the door observed —
  is the door's statement, not a filer's: a record without a verifying door
  signature is `index-unsupported`, and so is one whose signature header
  cannot even be decoded — a deeply nested header included, which once
  crashed every store construction site (FW-1). The door refuses, at construction, a
  signing key that does not verify under the declared door key, and a HITL
  transport bound to any HITL policy key but its authority's.
- **What the trust is as strong as.** Three custodies, and the erasure
  door's private key is the root of them: its holder can sign a record naming
  any requester. The other two are each insufficient alone: Control Plane
  registration under a tenant's declared HITL policy key (a party who can
  register a new version there can pin a key it holds for an erasure
  officer), and an approver's private key. Through the consult, either one
  also needs the door key — a record without a verifying door signature reads
  `record-signature-invalid` and its address is withheld as
  `index-unsupported`, never erased on that party's word. Through the door,
  either one also needs that officer's own authentication at the HITL door.
  The signed instant is the signer's own claim: revocation refuses a signature
  dated after the supersession, but a holder of a dropped key who backdates a
  signature to before it still verifies. The window's lower bound (the
  version's registration instant) is not enforced, because the in-memory
  Control Plane re-registers every version at boot and would refuse every
  approval made before the last restart. There is no fresh-registry
  fallback: a site that composes without the deployment's Control Plane, or
  re-composes a store with a different Control Plane, identity provider or
  trust, is refused by name. **An adopter-supplied identity provider that
  verifies nothing accepts everything; that is the adopter's trust choice** —
  door signatures included. The validation cache is keyed by the identity
  provider instance, so a do-nothing provider's verdict is never served to a
  site composed with another provider. It is keyed by the Control Plane's
  `policy_head` too — the digest of its registration history's metadata
  (action, key, version, instant), not of the content registered. That holds
  for the reference registry, where a version IS its content hash and a stored
  version is never overwritten; a third-party Control Plane must uphold the
  same, or two histories with different content could share a head and a
  verdict judged under one would serve the other.
- **The in-process adapter boots its own registry.** It composes with the
  authority its `binding.yaml` declares (`erasure_authority: {}` declares
  none). Its Control Plane holds only what its `ccf_config.yaml` registers,
  and the HITL policy, the approval policy and the erasure workflow are not
  manifest-addressable, so a genuine erasure consulted through the in-process
  adapter reads `index-unsupported` until the deployment registers them into
  that booted registry by its own code. The content stays withheld either
  way. The `--local` CLI arm declares no erasure authority at all: the local
  dev fabric runs no erasure door.
- **Which HITL transport holds pending approvals.** A completed erasure stays
  verified across restarts and processes, because its approval is in the
  store and its keys are in the pinned policy. A gate still **pending** in the
  in-memory transport does not survive a restart: that is the transport's
  limit, not the record's. A deployment that needs pending approvals to
  outlive a process wires a durable transport.
- **How a torn index line is repaired.** A process killed in the middle of an
  append can leave a partial line that the next append merges into. The index
  then refuses as `ErasureIndexCorrupt` and every read under it is withheld:
  that is deliberate, and the SDK ships no repair tool. With every process
  that composes the index stopped, copy the file aside as evidence, truncate
  it to the longest prefix of complete lines whose hash chain verifies, then
  restore the removed suffix before any reader starts: re-run the door's
  completion for the torn entry, whose execution is still suspended, and
  re-append every later complete line under the erase capability for its own
  request. The full procedure is in the `ccf.erasure.index` module docstring.

Two behaviors follow from the design and are stated rather than changed:

- A retry of a completion must present the same erase authorization. A retry
  under a fresh one is refused as `retry-mismatch`, because the record names
  the authorizing decision and the index entries already pin the record. The
  approval itself is re-filed unchanged, because its instant is the signed
  `issued_at`, and the retry reuses the door signature its prior attempt
  appended (an ES256 signature is not deterministic, and the index takes only
  an identical entry again), after verifying it.
- Over the MCP-backed store, a names read that the server refuses for a
  governed address reaches the door looking like an outage. The door refuses
  `class-unverifiable` either way, so it fails closed, but the two causes are
  not told apart.

Residuals, disclosed rather than changed (FW-4, D-IMPL-374):

- **A forged entry in one tenant withholds another tenant's content on
  tenantless reads.** A holder of the erase capability in tenant B can append
  an entry — genuine, or forged and so `index-unsupported` — naming an
  address of tenant A. Every tenantless read (the replay engine, `record_of`,
  child admission) then withholds A's artifact, with the reason redacted;
  reads scoped to tenant A still serve it. The MCP artifact server's client
  lane is scoped to its caller's tenant and is not among them (corrected
  2026-10-07, `D-IMPL-377`: this list named it, and a measured read of
  another tenant's erased address over that lane is served). The by-URI naming
  check inside the governed evidence read (`govern_dereference`) was one such
  tenantless read, and answered A's examiner "absent", recorded as
  `nonexistent`; it now reads through the caller's tenant view, and an
  address erased there reads as erased content (FW-7).
- **The erasure door is single-tenant.** An `ErasureDoor` holds one tenant's
  `ErasureAuthority` and refuses a request, or an erase capability, for any
  other tenant by name (`tenant-mismatch`). A deployment that erases for
  several tenants constructs one door per tenant, each over a HITL transport
  bound to that tenant's HITL policy key.
- **The door signature lives in the index entry, not in the record.** The
  `ccf.erasure-record` artifact carries no signature; the door's signature
  over it, and the key id it was made under, are fields of the index entry.
  A reader holding only an exported record cannot verify it without the
  entry.
- **Rotating a door key out of an authority strands a completion still in
  flight.** A retry verifies its prior attempt's entry signature against the
  authority's current door keys; once the key that signed it is no longer
  declared, the retry is refused as `retry-mismatch` and the address stays
  withheld under its write-ahead entry. Complete every pending erasure before
  dropping a door key.
- **A third-party HITL transport must expose `hitl_policy_key`.** The door
  reads that attribute to hold the transport to its authority's HITL policy
  key, but `HITLTransportProtocol` does not declare it. A transport that
  satisfies the Protocol without the attribute is refused, by name, when the
  door is constructed; the reference `InMemoryHitlTransport` exposes it.
- **The index assumes a filesystem whose `flock` and `O_APPEND` work.**
  Appends are serialized by an exclusive `flock` on the index file and
  written with `O_APPEND`. On a multi-host shared filesystem where `flock`
  does not exclude across hosts, concurrent appends can interleave and break
  the hash chain: the index then refuses as `ErasureIndexCorrupt` and every
  read under it is withheld. Keep the index on a filesystem every appender
  shares a working `flock` on. A write that stops short — a full disk, a
  file-size limit, a network filesystem's short write — is finished, or
  undone: the file is truncated back to its length before the append and
  fsynced, and the append raises `ErasureIndexWriteFailed`, which the door's
  completion propagates by name, filing no record (PC1). The completion can
  be retried once the cause is cleared.
- **Another tenant's filings do not change a tenant's answers (C8 and C-2,
  D-IMPL-376).** The MCP artifact server decides whether an address is
  governed evidence over the names the caller's own tenant filed it under,
  never another tenant's. An address the caller's tenant never filed goes to
  the governed evidence read
  (`runtime/ccf_runtime/authz/delivery_boundary.py::govern_dereference`),
  which holds the caller to the tenant a record was decided under before any
  other hold: another tenant's record answers exactly as a missing address
  does, `nonexistent`, at every disclosure level. The HTTP evidence routes
  (`/replay/decisions`, `/replay/resolutions`, `/artifact`) read through the
  same function and hold the same way. Within a tenant nothing changes: the
  owner reads its own record, and another principal's genuine record answers
  `unauthorized` at `full`. So a tenant's blob, presence and names answers,
  and its erasure door over the MCP-backed store, do not depend on whether
  any other tenant filed the same bytes, under any class. Two properties of
  the store keep that attribution sound. A name is filed only together with
  its bytes: the address is derived from the bytes `put` receives
  (`src/ccf/artifacts/protocol.py::ArtifactStoreProtocol.put`), and no verb
  registers a name for an address by reference. A deployment's own substrate
  behind the artifact server
  (`runtime/ccf_runtime/mcp/artifact_server.py::ArtifactSubstrate`) must keep
  that property; one that can register a name without receiving the bytes
  must not back a store several tenants share. And a tenant id is one naming
  segment: a write whose tenant contains `/` is refused at the store's write
  boundary (`src/ccf/artifacts/protocol.py::authorized_write_target`), because
  the naming index is read back by splitting `tenant/class/name` and such a
  filing would be attributed to another tenant (M-4). Names filed before that
  refusal existed are not re-read: a store that already holds a filing under a
  tenant id containing `/` still attributes it to the id's prefix. Erasure
  still crosses tenants on tenantless reads, as described above: an erasure
  destroys no bytes and is recorded for the erasing tenant only, so once
  tenant A erases an address that tenant B also filed, B's tenant-scoped reads
  still serve it and every tenantless read of it withholds it, with the
  reason redacted.
- **Above `minimal`, an erasure raised inside `invoke_agent` or `list_agents`
  is not rendered by disclosure level (N-3, D-IMPL-374).** The Experience door
  maps an `ErasedContentRefused` from its product resolver and from the
  `get_context`, `get_lineage` and `get_replay_record` seams (FW-3). It maps
  one raised by the deployment's own agent invoker (`invoke_agent`) or agent
  directory (`list_agents`) at `minimal` only: a `minimal` caller of either
  tool gets the opaque `ccf-runtime-failure:<id>`, and the door records
  nothing, so the fact of an erasure does not cross. For a `reasoned` or
  `full` caller the erasure crosses as the tool's error text, not as the
  recorded `erased-content` shell: `the requested content was erased by a
  recorded decision and is not served (SEC-009)`. The text names no address,
  but it tells the caller that an erasure occurred, and the door records no
  determination for it. Rendering it above `minimal` needs a product identity
  to record an agent dispatch's or an agent listing's erasure under, and no
  ruling names one, so it is disclosed rather than changed. An invoker or a
  directory that reads through an erasure-composed store, and must not reveal
  an erasure to a caller above `minimal` either, catches `ErasedContentRefused`
  and answers with its own not-found rendering (a directory leaves the agent
  out of its listing).

### 4.11 Declare a default for a parameter a policy constraint bounds (SEC-019, D-IMPL-356)

A registered `ccf.policy-constraint` whose `maximum`, `minimum` or
`allowed_set` reaches a parameter the caller omitted and no default fills is
never skipped: the request is refused as `constraint-refusal` with reason
`required-absent` and the constraint's `policy` authority
(`src/ccf/products/constraints.py::resolve_effective_request`). Declare a
default for every bounded parameter a caller may leave out, because the SDK
supplies none: the class's serve obligation `default_debt_tolerance` for the
tolerance, or the request contract's `defaults` or `relative_defaults` for any
parameter. The tolerance step refuses an absent `debt_tolerance` that a policy
bounds in the same way, instead of serving it at any Context Debt, but only
for a caller that composes it directly and states the bound
(`src/ccf/products/gates.py::refuse_over_tolerance`, whose `policy_bound`
argument is required).

- **Narrow a constraint's `applies_to` to the classes that declare its
  parameter.** A constraint that reaches a class whose request contract does
  not declare the parameter now refuses every request to that class in its
  scope: as `required-absent` when the caller omits the parameter, and as
  `undeclared-parameter` when the caller supplies it, so nothing the caller
  can send cures it. An `applies_to` with no `product_class` reaches every
  class, so an enterprise-wide constraint is the usual way to meet this. The
  fix is in the constraint, not the request: narrow `applies_to` to the
  classes that carry the parameter.
- **A deployment's own `PolicyConstraintResolver` must refuse the case
  itself.** On the governed path the tolerance step is handed no policy bound
  for an absent tolerance, because the governed resolver relies on the
  resolution having refused a bounded one already; the step's refusal above is
  a second line for a direct caller only. A resolver that skips an absent
  bounded tolerance therefore has the product served at any Context Debt, and
  one that skips any other absent bounded parameter has the request served as
  though the bound did not exist. Adopt the same rule, or delegate to
  `resolve_effective_request`.
- **A numeric bound on a non-numeric parameter holds vacuously.** A `maximum`
  or `minimum` on a parameter its request contract declares as something other
  than a number, a string for example, admits every value of it, and the
  replay record's effective request still shows the parameter as bounded by
  that policy. The SDK does not check a constraint's bound against the
  parameter's declared type, so declare `maximum` and `minimum` on numeric
  parameters only, and `allowed_set` for the rest. This predates SEC-019 and is
  disclosed rather than changed.
- **The reference resolver's `1.1.0` label is pinnable, not yet pinned.**
  `PolicyConstraintResolver` carries `resolver_id` and `resolver_version` so
  that the resolver in force can be pinned into replay, and the reference
  resolver moved from `1.0.0` to `1.1.0` for this refusal. Nothing in the SDK
  yet reads either property into a Decision Replay record, so no record shows
  which resolver version made its resolution; do not read the version bump as
  already replay-pinned.

### 4.12 Acquire by subject when a projection withholds a subject (SEC-020, D-IMPL-376)

A projection that must not tell the asking principal about a subject sets
`withheld=True` on its `ProjectionOutput` and returns the payload it returns
for a subject it cannot see. The governed call then computes everything the
product says about its evidence (its Context Debt, its empty finding, its TTL
anchor) from the same plan run without the request's subject as a walk start,
over the fabric as it stood immediately before the call's declared acquisition
seam ran (`src/ccf/products/resolver.py::GovernedResolver`). A subject that
names nothing has nothing acquired for it, so that is the fabric its own
question walks, and the two products match member for member.

- **The match holds when an identifier that names nothing acquires nothing.**
  That is what a source read keyed on the subject returns for an identifier it
  does not hold. If your `acquire` reads the same content whatever the subject
  (a population read), a nonexistent subject's question walks that content
  and a withheld subject's rendering does not, so the two differ: measured, at
  the empty finding under `from_decision`, and as `ttl-refusal` against
  `ttl-anchor-refusal` under `from_entity_freshness`. For a product whose
  projection withholds subjects, key the acquisition on the subject.
- **One more read per question.** With an acquisition seam declared, every
  governed call reads the tenant's graph once more, before the seam, whether
  or not the projection later withholds. On the paved road the fabric is
  booted fresh for each question, so that read is of a fabric holding only
  what boot put there.
- **The replay record keeps the real read.** Dimension 1 of a withheld
  decision's record lists what the plan actually read, the acquired subject
  included. The record is the audit plane, so protect access to it as you
  would the subject itself.

### 4.13 Resume a suspended run from one process, and serialize resumes beyond it (D-IMPL-377)

A resumption takes a single-flight claim on its execution before it reads
the execution's state record, and gives the claim back on every exit:
completion, refusal, exception and cancellation
(`runtime/ccf_runtime/workflow/engine.py::WorkflowEngine.resume`). The claim
is keyed by the Control Plane state store the record lives in and by the
execution's state key, and every engine in the process over that store
shares it. While one resumption of an execution is in flight in the
process, a second is refused rather than queued. The refusal is a
`WorkflowResumeRefused` audited `resolved=False`, and
`POST /workflow/resumptions` answers it with the same 409 it gives the
sequential refusal. Before the claim existed, two resumptions of one
approved suspension both passed the gate. On one human approval, the step
after the gate ran twice, two `workflow_resumed` rows named the one
approver, and the next gate held two pending events, one of them bound to a
state record that had already been overwritten.

- **Present a refused resumption again only after the other one has
  returned.** The 409 means another resumption of the same execution is in
  flight in this process. A repeat presented after that one has returned is
  judged on the execution as it then stands: if the other passed the gate,
  at the gate the execution now waits on.
- **Serialize resumptions per execution in front of the door when more
  than one process can resume.** The claim lives in one process's memory.
  It does not cover several processes, or several state-store objects that
  front one durable store, because the state-store Protocol has no
  compare-and-set (`src/ccf/controlplane/state.py::ControlPlaneStateStore`).
  The shipped `InMemoryStateStore` is per process, so the shipped
  composition never shares an execution between processes. A deployment
  that supplies a shared store must route every resumption of one
  execution through one process, or take its own per-execution lock before
  the door.
- **Keep the steps after a gate idempotent.** A resumption that fails or is
  cancelled after its step has started gives the claim back, so a retry is
  admitted and runs that step again.
- **A verdict recorded while a resumption is in flight is still not seen.
  This remains open.** A rejection recorded between a resumption's conflict
  check and its commit is outvoted: the execution completes at the
  approving terminal with both verdicts on record
  (`runtime/ccf_runtime/workflow/engine.py::WorkflowEngine._gate_authority`,
  residual 2(b)). The claim cannot reach this, because verdicts are recorded
  through the HITL transport
  (`src/ccf/hitl/transport.py::HITLTransportProtocol`), which the claim
  never touches. Covering it means the submission path taking the same
  per-execution claim, which changes the transport's contract for every
  transport a deployment supplies. Until then, reconcile: find every
  execution that has left a gate whose suspension holds both an approve and
  a reject verdict, and route it to human review.

## Validation-error text and caller values (SEC-024, choice C)

Every SDK contract derives from `CCFContract`, which sets pydantic's `hide_input_in_errors`. A rejected value
therefore never appears in the error's `str()`/`repr()`, in the egress door's failure log (which renders exception
type names and traceback frames, never exception text), or in any traceback a deployment captures. **One
consequence is accepted and documented (`D-IMPL-371`):** the text of a validation error that a door returns to the
caller — the MCP egress `door_question` and `parse_product_address` paths, and the HTTP product route's 400
detail — no longer echoes the rejected value. The field location and the message remain; the value does not. The
caller's own parameters in a governed refusal (the C-01 refusals) are unchanged: those are the caller's values
returned to that caller, not a disclosure. Nothing outside logs and `CCFContract` was changed for this finding.
