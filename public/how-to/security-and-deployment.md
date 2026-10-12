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
  The nonce is spent after every other check and immediately before the
  admission record is filed, so a presentation those checks refuse can be
  admitted later
  (`tests/peering/test_admission_refuses_replay.py::test_d_a_refused_presentation_does_not_spend_the_nonce`),
  while one whose record the store does not persist (`AdmissionNotRecorded`,
  or `ArtifactStoreUnauthenticated` where the store's server did not
  authenticate the deployment's credential, `D-IMPL-378` decision 10 (b))
  or answers with a reference that is not the record's own
  (`AdmissionRecordReferenceMismatch`, `D-IMPL-378` decision 5) is not
  admitted and is refused `replayed` if presented again
  (`tests/peering/test_admission_record_writer_checks_the_returned_reference.py::test_a_crossing_refused_at_its_record_has_spent_its_nonce`,
  `tests/peering/test_admission_record_write_401_is_the_typed_refusal.py::test_a_crossing_refused_at_its_record_for_the_credential_has_spent_its_nonce`).
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

Eleven decisions have to be made explicitly; §4.8 records two limitations the
SDK discloses rather than fixes, §4.12 an open row (SEC-020) a deployment must
plan around, and §4.13 how the SDK keeps one approval to one passage and what it
asks of a deployment's own state store and HITL transport. Each decision is a construction-time argument
or a declared artifact rather than a setting buried in configuration; where the
SDK behaves a particular way when nothing is declared, its section says so. The
first two concern the HTTP surface, whose endpoint-by-endpoint contract is on
the [HTTP API page](../reference/http-api.md): the auth hook and authorizer it
requires, and the authorization posture it applies; the third is where signing-key
custody lives, a decision about the key-source Protocol rather than about any
one surface; the fourth concerns which
transport the MCP product door serves on; the fifth concerns what the Claude
Agent SDK adapter's child process inherits; the sixth is how many processes may
boot one graph, which depends on the graph store; the seventh is which sources
may assert a classification; the eighth is which products a principal's grant
may reach; the ninth is how the erasure index is declared and protected; the
tenth is the default for a parameter a policy constraint bounds; the eleventh,
in §4.14, is how far into the past each tenant answers for.

### 4.1 The HTTP application always authenticates and authorizes

`create_app` requires an auth hook and an authorizer, and no value of either
builds an unauthenticated application (`SEC-001`;
`runtime/ccf_runtime/http_api/app.py::create_app`). The insecure default of
earlier releases is gone: there is no `auth=None` arm, no `authorizer=None`
arm, no acknowledgement argument and no insecure-default warning, so a call
that omits the hook fails at construction rather than warning. The product
entitlement source, the perspective resolver and the refusal recorder are
required for the same reason. What remains for a deployment to decide is
which auth hook and which scope mapping it binds (§4.2).

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

**On the product route, the authorizer's deny reads as "not available"
(dated 2026-10-12; R5-CP17-F01).** This is how the HTTP gate answers a deny,
not a property of the reference interpreter, so it holds for whichever
authorizer you bind. Every HTTP route answers the authorizer's deny
`403 request-unauthorized` except
`GET /product/{tenant}/{product_class}/{version}`. There, every deny the
scope mapping makes is answered `404 subject-unavailable`, whichever axis
failed: for example a class no scope entry the credential holds names, a
credential whose scopes lack the product action, or a path tenant the
credential holds that no scope entry's tenant pattern admits. That is the
reply an unentitled caller gets for a real class, in status, headers and
body, apart from the per-answer replay reference and the echo of the class
asked for. So at the minimal (default) and reasoned disclosure levels,
neither the status nor the body says whether a class exists. At the full
disclosure level the status is still `404`, but the body names the internal
cause, and the two can be told apart.
`tests/http_api/test_undeclared_class_reads_as_unentitled_http.py` holds the
minimal level for a class no scope entry names; the reasoned and full
levels, and the other two deny cases, were measured on 2026-10-12 and are
not yet held by a test. The route checks the request's shape first, the same
for every caller: a partial question, malformed `parameters`, or an
`asked_at` with no UTC offset is still `400`, and an `asked_at` that does not
parse as a date-time is `422`, the framework's validation error. The deny
stays on the audit log with the axis that failed; the replay record carries
the cause `unauthorized`, the error code `tenant-unauthorized` (the same code
whichever axis failed) and the authorization decision id, never the axis.

Unchanged on this route: no credential, or one the auth hook does not
recognize, is `401 unauthenticated`; a credential with no tenant, a path
tenant the credential does not hold at all (the gate checks this before the
scope mapping), and a class outside the credential's product roster (§4.9)
are `403`; an allow the gate cannot mint a capability from is `503`. None of
these refusals writes a replay record, and the gate writes no audit event
for them. The `401` and `403` refusals come before the authorizer is asked,
so no authorization decision is recorded (a known gap,
`tests/http_api/test_tenant_authz.py::test_a_denial_before_the_authorizer_is_reached_writes_no_decision`).
The `503` comes after the authorizer has decided, so whatever your
authorizer recorded for that allow stays on the audit log, with no answer
served. A client that read `403` from the product route for an unknown
class, for a credential lacking the product action, or for a tenant the
scope mapping does not admit, now reads the `subject-unavailable` refusal.

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

The identity lasts as long as the call and no longer (`D-IMPL-378`, item 9
(b)). `serve_stdio` sets it just before the server starts and, in a `finally`,
restores the login identity the caller's context held before the call,
whichever way the call ends: a normal return, an exception raised inside the
transport, or cancellation
(`tests/mcp/test_stdio_door_restores_the_previous_identity.py::test_after_a_normal_return_the_previous_identity_is_restored`,
`tests/mcp/test_stdio_door_restores_the_previous_identity.py::test_after_an_exception_inside_the_transport_the_previous_identity_is_restored`,
`tests/mcp/test_stdio_door_restores_the_previous_identity.py::test_after_cancellation_while_serving_the_previous_identity_is_restored`).
So whatever the calling code does after the call no longer runs as the stdio
identity.

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

The two addresses an HTTP door advertises for OAuth discovery, the issuer and
the resource server, are not needed on stdio (`D-IMPL-378`, ruling C2-A (b)).
An HTTP door publishes them in its protected-resource metadata and in the hint
it sends with a 401, and stdio builds no HTTP application, so the stdio
transport supplies its own reserved `.invalid` values and the door starts with
both environment variables unset. It still refuses a call naming another
tenant and a call for a class outside its scope mapping. The loopback
transport advertises its own bound address, and a deployment that mounts
`ProductDoor.server` under its own host passes both addresses itself: the
method has no default for either.

Because no SDK transport reads the two names, the environment document's
`door:` block need not declare them (`D-IMPL-378`, ruling C2-A2 (a)): both are
optional and the block needs only `credential`. A stdio door started from a
document that names neither still answers, and still refuses another tenant and
a class outside its scope mapping
(`tests/mcp/test_stdio_door_addresses.py::test_a_stdio_door_whose_document_names_neither_address_starts_answers_and_still_refuses`).
A deployment that hosts the mount itself may still declare them for its own
code to resolve; a value it leaves out is refused by name, never defaulted
(`tests/mcp/test_stdio_door_addresses.py::test_a_door_composes_over_a_door_block_naming_only_the_credential`).

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
| SQLite (reference) | `cross-process` | An exclusive `flock` on `<database file>.ccf-writer.lock`, beside the resolved database path; with `writer_lease_lock_dir` declared, also one on `<writer_lease_lock_dir>/<sha256(database file identity)>.lock` (below) |
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

**SQLite: declare a lock directory so the lease follows the database file, not
its name (SEC-013, option (C), D-IMPL-378).** The sidecar is keyed on the
database file's resolved path, so a writer that reaches the same file through
another name is not excluded by it: through a hard link it is refused only
because the file has two names, and through the new name of a renamed live
file it boots. A deployment that declares `writer_lease_lock_dir` on the SQLite
connection settings (the same setting, validation and directory rules as the
network stores above) makes each writer also hold an exclusive `flock` on
`<writer_lease_lock_dir>/<sha256(database file identity)>.lock`, where the
identity is the file's device and inode, read when the store opens the file
(`src/ccf/graph/backends/sqlite.py::SqliteGraphStore`). A second process's
writer through the renamed file's new name is then refused with
`SingleWriterViolation` naming that lock, among writers that declare the same
directory (`tests/graph/test_sqlite_writer_lease_file_identity.py`); one
through a hard link is refused earlier, when its store opens (P2 (b), below).
An in-memory
database with a lock directory declared is refused when its store is built: it
has no file to follow. What the declared lock does not close, each measured in
`tests/graph/test_sqlite_writer_lease_file_identity_limits.py`:

- **Writers that declare different directories, or none, are not excluded**
  through another name. Declare one directory for every process that writes the
  file.
- **Do not rename or move a live database file; no lock makes it safe.** SQLite
  keeps the writer's write-ahead log under the name it opened, so commits not
  yet checkpointed are absent through the new name once the writer closes, and
  SQLite's `integrity_check` still reports `ok`.
- **A lock file stays behind for each database file identity ever leased, and
  is harmless.** The kernel drops the `flock` when its holder exits or crashes,
  so a lock file no process holds never blocks a boot, including one a deleted
  file left whose inode number a new file was given; and while a writer holds
  its file open, no other file can be given that file's inode number. Measured
  on Linux (ext4); macOS not measured.

**SQLite: a database file with more than one name is refused when its store
opens, before any setup, for every open, readers included (SEC-013, P2 (b),
D-IMPL-378).** The writer lease is taken when the writer is minted, after the
store has opened the database and run its setup. Until P2 (b), a process that
opened the file through a hard link, a writer the lease then refused or a
read-only boot, had already written that setup into a write-ahead log beside
the link, and that log rolled back what the holder committed once anything
opened the file through the link, with `integrity_check` still reporting `ok`.
The store (`src/ccf/graph/backends/sqlite.py::SqliteGraphStore`) now counts
the database file's names before SQLite connects and again before the setup's
first statement, and refuses a file with more than one name with
`WriterLeaseHeld`, naming the file and its number of names, so the refused open
writes nothing through any name
(`tests/graph/test_sqlite_open_refuses_a_file_with_more_than_one_name.py`). A
writer boot through a hard link is therefore refused when its store opens,
before the mint, and is reported as `WriterLeaseHeld` rather than
`SingleWriterViolation`. What the two counts do not see: a second name made in
the instant between the second count and the setup; a file swapped in under the
path between SQLite's open and the second count, because Python's `sqlite3`
exposes no descriptor to count the opened file's names through; and any tool
that opens the file with SQLite directly rather than through the SDK. Do not
open a live database file through a second name, and remove hard links to it.

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
- **SQLite: one name per database file, so no hard-link backups (`D-IMPL-378`,
  option (B) and P2 (b)).** The store refuses to open a database file that
  has more than one name, a hard link, through any of its names, for every
  open, readers included: the boot is refused when the store opens, with
  `WriterLeaseHeld`, whose message gives the file's number of names
  (`tests/graph/test_sqlite_writer_lease_hard_link.py::test_a_second_process_cannot_boot_a_writer_through_a_hard_link_to_a_held_graph`),
  and the writer lease refuses a second name made after the store opened.
  A backup that links the database file instead of copying it, as a
  hard-link backup does inside the same filesystem, gives the file a second
  name. While that name exists, every writer boot of the graph is refused, in
  any process and through either name, even with no writer live
  (`tests/graph/test_sqlite_writer_lease_disclosed_limits.py::test_a_hard_link_backup_refuses_every_writer_boot_until_it_is_removed`),
  and so is every read-only boot: an examiner cannot open a SQLite file that
  has a hard-link backup
  (`tests/graph/test_sqlite_open_refuses_a_file_with_more_than_one_name.py::test_a_reader_open_of_a_file_with_two_names_is_refused_by_name_through_either_name`).
  Removing the backup's name ends the refusal.
  Back a SQLite graph up with a copy SQLite writes itself instead: its online
  backup API (`sqlite3.Connection.backup`) or `VACUUM INTO`. Either can run
  while a writer is live, and the database file keeps one name
  (`tests/graph/test_sqlite_writer_lease_disclosed_limits.py::test_a_copy_sqlite_makes_while_the_writer_is_live_leaves_the_file_one_name`).
  Keep the database file out of any backup that hard-links.
- **SQLite: do not move a live database file. Without a declared lock
  directory the lease does not follow a rename, and `SEC-013` stays open on
  it.** A database file moved to a new
  name while a writer holds it still has one name, so option (B) does not
  refuse it, and a writer booted through the new name in a second process is
  not refused while the first is live
  (`tests/graph/test_sqlite_writer_lease_hard_link.py::test_a_second_process_boots_a_writer_through_the_new_name_of_a_moved_live_file`).
  SQLite leaves the live write-ahead log beside the old name, so the new name
  does not see what the writer committed; once both names have been written
  through and closed, what was committed through the old name is gone, and
  SQLite's integrity check still reports `ok`
  (`tests/graph/test_sqlite_writer_lease_disclosed_limits.py::test_a_moved_live_file_leaves_its_write_ahead_log_behind_and_its_commits_are_lost`).
  Stop every process that has the database file open before you move or
  rename it: a file moved while no process has it open is one graph under
  its new name, and its lease refuses a second writer as usual
  (`tests/graph/test_sqlite_writer_lease_disclosed_limits.py::test_a_database_file_moved_while_no_process_has_it_open_is_leased_under_its_new_name`).
  Option (C) (`D-IMPL-378`, 2026-10-08), the lock that follows the database
  file when `writer_lease_lock_dir` is declared (above), refuses that second
  writer among writers that declare the same directory; a deployment that
  declares none keeps this gap, and `SEC-013` stays open.
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
a read-only boot when the store is opened. On SQLite, a database file with more
than one name is refused before that setup, for a read-only boot as for a
writer boot (P2 (b), D-IMPL-378, above): an examiner cannot open a SQLite file
that has a hard-link backup until the link is removed. A read-only boot is not
coordinated with the writer: it reads what the store returns at each read.
Replay reads the recorded snapshot boundary, which an append-only graph does
not move.

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
| MCP `get_replay_record` | the declared `replay_record_product_class`; the tool then refuses every call (section 4.12) |
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
- **Over an MCP-backed store: the door's credential, and the upgrade order
  (dated 2026-10-12; design 1.3, `D-IMPL-378`).** The door names and judges
  every address through the artifact server's two door tools,
  `name_artifact_for_erasure` and `match_artifact_subject`. Grant the door's
  MCP credential (the bearer token its `McpArtifactStore` presents, not the
  requester's or the approver's) the action `artifact.subject.match` on the
  resource `artifact.subject.match`, for exactly one tenant, as an
  authenticated bearer; one grant covers both tools. The server's
  `ErasureTrust` must also hold that tenant's `ErasureAuthority`, whose door
  key signs each query. Without the grant, every address over MCP is refused
  `class-unverifiable`, ordinary client filings included. Upgrade the
  artifact server first, or with the door's client. Until the door's client
  is upgraded too, submit no erasure request through it: an older door
  client against an upgraded server admits a request that names a client
  twin of governed evidence, meaning governed evidence whose exact bytes, and
  so whose address, the tenant also filed under an ordinary client class
  (measured). The new door refuses such a request. A new
  door client against an older server refuses every address
  `class-unverifiable` (measured against `633c4e53`, which has the same code
  as `2cd96aef`, the previous wheel's source), so it fails closed. Upgrading
  does not make an erasure over the MCP-backed store complete: under the
  declaration above, the door files `ccf.erasure-approval` and
  `ccf.erasure-record` with its `ArtifactErase` capability, but the artifact
  server's only write tool, `put_artifact`, authorizes `artifact.write` and
  hands the store an `ArtifactWrite` capability, which the store refuses for
  a class declared under `ArtifactErase`. Measured: the completion is refused
  at the approval's save, before any index entry is appended, so the address
  stays served; the same before this release. Over the MCP-backed store an
  erasure reaches approval and no further (follow-up 6 in
  `packaging/bank-controlled/BANK-PACKET.md` section 5); complete erasures
  through an in-process store.
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
- Over the MCP-backed store, a names read that the server answers with its
  refusal shell reaches the reader as a typed refusal, never as an outage: the
  client raises `ArtifactReadRefused`, carrying the shell
  (`src/ccf/artifacts/protocol.py::ArtifactReadRefused`; decision 1 (A),
  D-IMPL-378). The server refuses it for an address the reader's tenant filed
  only as governed evidence the reader may not read, and for an address that
  tenant never filed (F1-1, D-IMPL-378); where the tenant also filed the
  address on its client lane, the reader gets the client-lane names instead
  (rule A6, design 1.2).
  An address nobody filed and a governed address that holds no record, a
  query pin above all, get the same answer, the governed read's `nonexistent`
  shell
  (`tests/mcp/test_f1_names_present_governed_and_absent_alike.py::test_a_present_governed_pin_and_an_address_nobody_filed_answer_alike`).
  As of 2026-10-12 (design 1.3, D-IMPL-378) the erasure door over the
  MCP-backed store no longer reads the names resource at all: it names every
  address through its own naming path (described below), which answers it
  the same one refusal for all of these addresses. The door refuses them
  `class-unverifiable` ("cannot verify"), with that path's decline as the
  cause
  (`tests/mcp/test_f1_names_refusal_typed_through_the_client.py::test_the_erasure_door_over_the_mcp_store_refuses_class_unverifiable_because_of_the_typed_refusal`),
  so it fails closed, but the causes are not told apart: over the MCP-backed
  store an address the tenant never filed is refused `class-unverifiable`,
  where the door in process refuses it `address-not-in-tenant`
  (`tests/mcp/test_erasure_subject_match.py::test_the_mcp_backed_door_reaches_the_in_process_doors_outcome`).
  A credential the server's guard does not authenticate (HTTP 401) is
  neither that refusal nor an outage: every read of the client, and its
  write, raises the typed authentication refusal
  `ArtifactStoreUnauthenticated` instead
  (`src/ccf/artifacts/protocol.py::ArtifactStoreUnauthenticated`; repair 2.5
  (a) for the reads and decision 10 (b) for the write, D-IMPL-378;
  `tests/mcp/test_auth_401_typed_through_the_client.py`,
  `tests/mcp/test_auth_401_typed_on_a_write.py`), a third type beside the two
  (`tests/mcp/test_auth_401_typed_through_the_client.py::test_a_401_an_access_refusal_and_an_outage_reach_the_caller_as_three_types`),
  and the door refuses it `class-unverifiable` with that cause
  (`tests/mcp/test_auth_401_never_read_as_absence.py::test_the_erasure_door_over_a_store_whose_credential_is_refused_refuses_class_unverifiable_with_the_typed_cause`).
  The guard's other refusals, a credential without a required scope (HTTP
  403) and the tenancy guard's denials, still reach a read as
  `McpServerUnreachable`, an outage
  (`tests/mcp/test_auth_401_typed_through_the_client.py::test_the_guards_other_refusals_are_not_the_authentication_refusal`).
  A write meets the 403 the same way
  (`tests/mcp/test_auth_401_typed_on_a_write.py::test_at_one_write_a_401_a_403_and_a_refused_connection_reach_the_writer_as_two_types`)
  and the tenancy guard's denial as the server's decline, `ArtifactStoreError`
  (`tests/mcp/test_mcp_store_put_decline.py::test_a_write_the_servers_authorizer_refuses_is_a_decline_too`).
  At the store layer, a write's 401 is raised as the typed refusal,
  `ArtifactStoreUnauthenticated`, not as an outage
  (`tests/conformance/test_artifactstore.py::test_a_store_presenting_a_rejected_token_is_refused_with_the_typed_authentication_refusal`),
  and the peering admission gate lets it through by name rather than
  reporting `AdmissionNotRecorded`
  (`tests/peering/test_admission_record_write_401_is_the_typed_refusal.py`).
  Whether a caller over HTTP can tell a rejected credential from an outage
  depends on the door, and only the three below make that distinction.
  The HTTP evidence doors, `GET /replay/decisions`, `GET /replay/resolutions`
  and `GET /artifact/{content_address}`, answer the typed refusal `503` with
  `error_code` `artifact-store-unauthenticated` and one constant message,
  the same for every ask, while an outage of the store is still answered
  with the framework's opaque `500 Internal Server Error` (decision 21 (a),
  D-IMPL-378;
  `tests/http_api/test_evidence_doors_answer_a_401_and_an_outage_apart.py`).
  Only these three doors tell a rejected credential from an outage (D-IMPL-378,
  ruled by Dave on 2026-10-09 at 20:23 MST): no other HTTP door catches the
  typed refusal, and `POST /artifact`, measured, answers it and an outage with
  the same `500`, filing nothing
  (`tests/http_api/test_upload_door_answers_a_rejected_credential_and_an_outage_with_one_500.py::test_post_artifact_answers_a_rejected_store_credential_and_an_outage_with_one_500_and_files_nothing`).

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
- **A HITL transport can stall a gate and change the queue key the caller is
  told; it cannot change the approval binding** (`D-IMPL-380`, fifth round;
  `runtime/ccf_runtime/workflow/engine.py::WorkflowEngine._suspend` and
  `::WorkflowEngine._restore_request`). A HITL transport is handed the
  engine's own pending event, which is not copied. A transport that alters it
  can change the `event_key` the caller is told in `WorkflowSuspended`, and,
  because resume looks for the key it recomputes (`_event_key`) among the
  events the transport holds, a transport that alters the key can keep the
  gate from ever opening, and each recovery queues another request. Nothing is
  wrongly approved: the approval binding, the hash of the suspension record as
  built, does not change.
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
  same function and hold the same way. Before any hold, the governed read
  serves a record only where the store's naming shows the fabric's own record
  writer filed it — under a class the store's `WriteKinds` declares under
  `ReplayMint`, a kind no door can mint — under the tenant the record was
  decided under. Bytes shaped as a record and filed any other way, on another
  tenant's client lane or on this tenant's, answer exactly as a missing address
  does, and a store that cannot say who filed an address is refused by name
  (`runtime/ccf_runtime/authz/delivery_boundary.py::UnattributableDeliveryBoundaryError`).
  Within a tenant nothing changes: the
  owner reads its own record where owner read-back is open for it (section
  4.12), and another principal's genuine record answers `unauthorized` at
  `full`. A tenant's own client-lane filing decides its client-lane reads
  (design 1.2, F1-1c, D-IMPL-378; Dave, 2026-10-09 10:54 MST; built
  2026-10-12): an address the tenant filed under a class the store does not
  declare under `ReplayMint` is served from the client lane to every principal
  of that tenant even where the same tenant also filed it as governed
  evidence, so a query pin's bytes that the asker files back read the same
  whether or not the record writer filed the pin
  (`tests/mcp/test_f1_1c_write_then_read.py`). Record-shaped bytes and bytes
  not at their address still take the governed read. The names resource
  answers the tenant's client-lane names and adds the governed names only for
  a principal the governed read admits (rule A6), so a record's owner keeps
  its provenance. The versioned-URI resolution resource
  (`ccf-artifact://{tenant}/{class}/{name}@{version}`) decides a class
  declared under `ReplayMint` through the governed read too (design 1.1,
  F1-1b; `runtime/ccf_runtime/authz/delivery_boundary.py::govern_resolution`):
  an admitted principal still gets the address, and every other caller gets
  the one recorded shell, the same for a present query pin and a URI nobody
  filed, which the MCP store raises as
  `ccf.artifacts.protocol.ArtifactResolutionRefused`
  (`tests/mcp/test_f1_1b_resolution_decides_governed_classes.py`). Another
  principal of the tenant no longer resolves a governed record it may not
  read, and no principal resolves a query pin, an admitted child contract or
  a child question over MCP. Upgrade every `McpArtifactStore` client with
  the server: where an upgraded server refuses a governed versioned URI, a
  client older than `01fc424d` raises `McpServerUnreachable`, which reads as
  an outage, instead of `ArtifactResolutionRefused` (measured with a client
  from `633c4e53`, for a present query pin and for a URI nobody filed; the two
  still answer alike, so nothing leaks, but retry logic keyed on outages
  treats the refusal as a transport fault). A principal the governed read
  admits gets the same `found: true` answer as before, which an older client
  reads normally. So a tenant's blob, presence, names and
  resolution answers,
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
- **Record-shaped bytes on the MCP client lane answer as a missing address
  (forged-record review, D-IMPL-376; client-lane ruling, D-IMPL-378).** The
  artifact server serves a tenant's own client-lane filings to every principal
  of that tenant as the exact stored bytes
  (`runtime/ccf_runtime/mcp/artifact_server.py::build_artifact_server`), and
  the answer does not say which lane served it. It serves them only while
  they hash to their address: bytes altered under it answer as a missing
  address, decided by the governed read (Dave's E1 (a), D-IMPL-378;
  `tests/replay/test_record_content_address_integrity.py::test_the_artifact_servers_client_lane_never_serves_bytes_altered_under_their_address`).
  It does not serve bytes that validate as a Decision Replay record that way
  either. "Validate" means
  `DecisionReplayRecord.model_validate_json`, the parse the replay engine
  (`src/ccf/replay/engine.py::resolve_artifact`) and every SDK reader of a
  record make. The governed read decides those bytes, and on the blob and
  presence resources it answers bytes a principal filed on its tenant's
  client lane exactly as a missing address. Read through the MCP-backed store
  (`src/ccf/artifacts/mcp_store.py::McpArtifactStore`) they are absent, so
  the replay engine, `replay_refusal` and child admission do not take them as
  a record when they read through it. Two things are not refused. The write
  is not: the bytes are stored, and the names resource lists the tenant's own
  filing under its stored class (to a principal the governed read does not
  admit it lists the client-lane names only, never the governed ones and never
  the refusal shell: rule A6, design 1.2, D-IMPL-378). Bytes the validator
  refuses, one key away from a record included, are served as client
  artifacts. Read in process —
  a store handed to the SDK directly — the same filing is refused too
  (D-IMPL-378): `resolve_artifact`, `resolve_artifact_at_uri`, `replay`,
  `replay_refusal`, child admission and `OpenedProduct.record_of` accept a
  record only where the store's naming shows the fabric's record writer
  filed it, under a class its `WriteKinds` declares under `ReplayMint`, under
  the tenant the record names
  (`src/ccf/replay/provenance.py::require_filed_by_record_writer`); the
  replay engine answers anything else as a missing record,
  `ReplayUnresolvable`; child admission and `record_of` raise
  `RecordNotFiledByRecordWriter`, an `ArtifactNotFound`; a store that cannot
  say who filed an address is refused by name
  (`src/ccf/replay/provenance.py::UnattributableRecordStore`). Treat a record as
  evidence only when a governed read returned it. The erasure door applies
  record retention, the `replay-input` refusal, only to a record the fabric's
  record writer filed under the requesting tenant, decided by the same
  provenance check (`src/ccf/replay/provenance.py::filed_by_record_writer`;
  D-IMPL-378). It judges the subject and that rule from the bytes at each
  requested address only after re-hashing them against the address: bytes
  altered under it are refused `subject-unverifiable`, and no approval starts
  (Dave's E1 (a), D-IMPL-378;
  `tests/replay/test_record_content_address_integrity.py::test_the_erasure_door_refuses_to_judge_a_record_from_bytes_altered_under_its_address`).
  A door over the store in process reads such a filing directly
  and erases it like any client artifact, even with the subject in a
  replay-input field; a record the writer filed, with the subject in the same
  field, is still refused `replay-input`. A store that cannot say who filed an
  address is refused `class-unverifiable` rather than judged on the bytes' own
  word: one that declares no `WriteKinds`, for an address whose subject is in
  a replay-input field, and an erasure-consulting composition over a store
  that answers no `names_at`, for any address
  (`tests/erasure/test_replay_input_retention_provenance.py`). An erasure door
  built over the MCP-backed store reads no requester-facing resource to
  verify an address (design 1.3, OWED-RULINGS-3 item 5 (B), D-IMPL-378; Dave,
  2026-10-09 06:21 and 10:54 MST; built 2026-10-12). It names each address
  through the artifact server's `name_artifact_for_erasure` tool, which
  answers the door's tenant's names at the address and whether its record
  writer filed it there, never the bytes, and it judges the subject through
  the `match_artifact_subject` tool, which judges the bytes where they are
  with the in-process door's own judgment
  (`src/ccf/erasure/subject_match.py::judge_subject`), re-hashing them first,
  and answers one verdict, never the bytes. A decline or a failure of either
  path refuses the address, with no fallback to the names, blob or presence
  resources. Measured: a request naming a client filing, record-shaped or
  not, reaches the in-process door's outcome, and no message of the exchange,
  in either direction, carries the document
  (`tests/mcp/test_erasure_subject_match.py`); a record the fabric's record
  writer filed reaches the in-process outcome too, `replay-input` where the
  subject sits in a replay-input field and admitted where it sits at a key
  path only
  (`tests/mcp/test_erasure_subject_match.py::test_a_record_the_record_writer_filed_reaches_the_in_process_outcome_over_mcp`).
  Both tools answer the erasure door of the caller's tenant alone, decided
  before the substrate is read: the deployment must grant
  `artifact.subject.match` by name to the door's MCP credential; the caller's
  tenant must have an `ErasureAuthority` in the server's `ErasureTrust`; and
  the query, rebuilt under the caller's tenant, must carry a signature by that
  authority's declared door key, made for that path
  (`src/ccf/erasure/subject_match.py::verify_subject_match_query`,
  `::verify_door_naming_query`; a signature made for one path does not verify
  on the other). Every other caller gets one constant refusal on each path —
  measured for a caller with no identity, another tenant's bearer, this
  tenant's reader without the grant, and a principal holding the grant but
  not the door key: the same bytes whether the address exists, whether the
  filing is record-shaped or governed, whether the subject matches, and no
  read of the substrate (`tests/mcp/test_d3b_door_naming_path.py`). The door
  paths keep the uniform "cannot verify" of 2026-10-09 06:21 (design 1.3,
  Q1 (b), read as the batch coordinator ruled it on 2026-10-12): an address
  the door's tenant never filed, governed evidence that is not a record (a
  query pin, an admitted child contract, a child question), and a client
  twin of such evidence are refused `class-unverifiable` over MCP, where the
  door in process refuses them `address-not-in-tenant` or
  `class-label-mismatch`. A client twin of governed evidence is never erased
  over MCP
  (`tests/mcp/test_erasure_subject_match.py::test_a_client_twin_of_governed_evidence_is_never_erased_over_mcp`).
  Not closed by this: the door key is the trust root here as for the door's
  records, so a party holding it and a credential granted
  `artifact.subject.match` can ask about any of that tenant's client-lane
  addresses and writer-filed records, as the door does, and its signatures
  carry no freshness; the erasure requester learns through the door's reason
  codes what the in-process door would tell it about a writer-filed record;
  the door's MCP credential now needs `artifact.subject.match` for every
  address, so a door without it can no longer erase ordinary client filings
  over MCP; a new door client against an older artifact server is refused
  for every address (measured against `633c4e53`), while an older door client
  against an upgraded server admits a request naming a client twin of
  governed evidence (measured), so the door's client is upgraded with the
  server, or no erasure is submitted through it until it is (the checklist
  at the top of §4.10); completing an erasure over the MCP-backed store is
  covered by no test, and under the checklist at the top of §4.10 it does not
  complete: the artifact server's only write tool refuses the door's approval
  as the wrong kind (measured, before and after this release), so an erasure
  over the MCP-backed store reaches approval and no further; and the erasure
  claim this bullet qualifies (SEC-009) stays open until a panel verifies
  it.
- **Content-addressed deduplication shows in write timing (design 1.2, Q4 (a),
  D-IMPL-378; disclosed 2026-10-12, not closed).** `FileArtifactStore.put`
  writes the file only when the bytes are not already stored, by any filing:
  governed evidence, another principal's, another tenant's. So a client-lane
  `put_artifact` of bytes that are already stored can return slightly faster
  than one of new bytes. Measured by the design seat at the store level, 300
  interleaved repetitions each: median 447.7 µs with the bytes already
  stored against 455.7 µs new, with p10–p90 of roughly 160–3,000 µs for
  both; over the wire, not measured. Dave ruled that the storage layer does
  not change (design 1.2, 10:54 MST), so closing it would be a separate
  substrate decision.
- **A read-refusal record names who asked; one minted before its marker
  reads as missing for everyone, its owner included (forged-record re-review,
  D-IMPL-376; D-IMPL-378).** The governed read records each refusal through
  the recorder of the door that refused it. The record names the tenant the
  refused capability was verified for, beside its principal, and carries a
  marker saying so (`src/ccf/products/refusal.py::ResourceRequestIdentity`,
  member `tenant_from`) that only the governed read writes
  (`runtime/ccf_runtime/authz/delivery_boundary.py::govern_dereference`), so
  the tenant and principal holds bind a later reader to that pair. On a door
  that serves several tenants through one recorder, as the MCP artifact server
  is built, a principal holding a capability for the door's tenant with the
  same client id as another tenant's refused principal gets that principal's
  read-refusal record answered exactly as a missing address is — measured at
  the MCP blob and presence resources and at HTTP `/replay/decisions`,
  `/replay/resolutions` and `/artifact`
  (`tests/mcp/test_read_refusal_attribution_mcp.py`,
  `tests/http_api/test_read_refusal_attribution_http.py`). The refused
  principal cannot read its record back through that door either: the record
  is decided under its tenant and filed under the recorder's, and the governed
  read serves a record only where it is filed under the tenant it was decided
  under. **Owner read-back of a read-refusal record minted before the marker
  is lost.** Such a record named the door's tenant whichever tenant asked and
  is byte-for-byte a legitimate record of the door's own principal, so the
  governed read answers every read-refusal record without the marker exactly
  as a missing address, for every caller — measured for the principal it
  names and another tenant's principal with the same client id at both doors,
  and for another principal of the door's tenant at the MCP door. The records
  are not rewritten: they stay in the store and still reconstruct at their own
  addresses through `replay_refusal` (the replay case in
  `tests/mcp/test_read_refusal_attribution_mcp.py`); read them from the store,
  not through a door. The marker counts only on a record the provenance check proved the
  fabric's record writer filed: a marked read-refusal record filed on another
  tenant's client lane or on the tenant's own answers as a missing address at
  both doors and to the governed read called in process (same test modules).
  The disclosure level a governed read is held to and the level a refusal
  shell is disclosed at are each read for the caller's tenant and principal
  together, never for a principal of the door's tenant with the same client id
  (`tests/mcp/test_read_refusal_attribution_mcp.py`,
  `tests/http_api/test_read_refusal_attribution_http.py`); so is the level
  that picks the Experience door's answer to an erasure — measured on
  `get_context` (`tests/mcp/test_experience_level_binds_the_tenant.py`).
- **Above `minimal`, an erasure raised inside `invoke_agent` or `list_agents`
  is not rendered by disclosure level (N-3, D-IMPL-374).** The Experience door
  maps an `ErasedContentRefused` from its product resolver and from the
  `get_context` and `get_lineage` seams (FW-3); `get_replay_record` refuses
  every call before its seam (section 4.12). It maps
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

### 4.12 A withheld subject can still be told from a nonexistent one (SEC-020, open; D-IMPL-376)

A projection that must not tell the asking principal about a subject sets
`withheld=True` on its `ProjectionOutput` and returns the payload it returns
for a subject it cannot see. The governed call then computes the product's
Context Debt, empty finding and TTL anchor from the same plan run without the
request's subject as a walk start, over the fabric as it stood immediately
before the call's declared acquisition seam ran
(`src/ccf/products/resolver.py::GovernedResolver`).

**What that makes equal, as measured.** On the paved road's test fixture, a
withheld subject's served product, every member of it, and its refusal shell,
every member except `replay_reference`, matched a nonexistent subject's on both
TTL anchors. That is a measurement, not a proof. The fixture meets three
conditions, and the list below includes a measured break of each: your
`acquire` is keyed on the subject, so an identifier it does not hold acquires
nothing; the fabric is booted for the question, as the paved road boots one
per question; and the product class composes no child about the subject.
The test is
`tests/products/test_withheld_is_indistinguishable_from_absent.py::test_the_paved_road_acquisition_seam_does_not_reveal_a_withheld_subject`.

**Similarity over an entity the acquisition refreshed (D-IMPL-378).** The
plan run for a withheld subject now scores with an operator registry built
from that same read before acquisition, so a similarity operator matches the
subject's text as it stood before acquisition. On a test fabric that already
held the subject, an acquisition keyed on the subject that changed its
similarity text to the query used to make the two products differ at the empty
finding and the debt. With the change they matched on both TTL anchors: every
member of the served product, and the refusal shell except `replay_reference`.
A subject the projection does not withhold is still matched against the text
its own acquisition wrote. The test is
`tests/products/test_withheld_similarity_registry.py`. This follows the rule
the walk already follows, so it shares that rule's limit: with an acquisition
not keyed on the subject left inside your `acquire` (below), a nonexistent
subject's question is matched against the text the acquisition wrote and the
withheld rendering is not. On that test fabric with such an acquisition, the
two products differed at the empty finding and the debt under `from_decision`,
and under `from_entity_freshness` the withheld subject was refused
`ttl-anchor-refusal` while the nonexistent one was served. Before the change,
the same shape differed at the debt and the expiry, with both served. With the
same read declared as the population phase, or with the withhold decided early
(both below), the two products matched on both anchors:
`tests/products/test_withheld_similarity_registry.py::test_channel_1_a_population_read_still_tells_the_two_apart_with_similarity`.

**Population reads, composites and question fabrics (D-IMPL-378, Q7 to
Q10).** The governed call now enforces four of Dave's rulings
(`src/ccf/products/resolver.py::GovernedResolver`). Each was measured on test
fixtures, in
`tests/products/test_withheld_subject_population_composite_and_fabric.py`
unless another test is named.

- **One question per fabric that acquires (Q9).** When an acquisition phase is
  declared, the fabric must be booted for its question:
  `load_and_boot(..., for_question=True)` or
  `load_config_and_boot(..., for_question=True)`, onto a store path that does
  not exist yet. A path that exists is refused at boot
  (`QuestionFabricNotFresh`). Under P4 (a), which Dave ruled on 2026-10-08,
  the boot then reserves the path for itself alone: it creates the question
  marker beside the path exclusively, before the store exists, so a second
  boot for a question at a path another boot holds, and a store that appeared
  at the path after the check, are refused by the same name
  (`tests/products/test_unmarked_and_unverifiable_question_stores.py`, which
  measures every P4 (a) refusal in this bullet). Under P4s-A (b), which Dave
  ruled on 2026-10-08 at 16:40 MST, the store the adapter opened is then read
  once through the governed reader, at the latest instant a timestamp can
  name, after the boot takes its writer lease and before the fabric is handed
  back. A store holding anything for the tenant is refused
  (`QuestionStoreNotEmpty`), before any acquisition phase runs, with the same
  refusal whatever the question asks. A boot for a question that is also
  read-only would hold no writer lease, so it is refused before anything is
  registered (`QuestionFabricNotExclusive`). From the read to the question's
  end, a second boot for a question at the path, another writer boot of the
  path and a read-only boot asked a governed question are each refused by
  name, in this process and from another process, and so is a second governed
  call over the question's fabric
  (`tests/products/test_question_store_empty_at_boot_and_held_through_use.py`,
  which measures the order too). A store whose settings name
  no path, a network graph store and also the in-memory development store
  although each boot of that one is new, cannot be shown fresh: a boot for a
  question over it is refused (`QuestionFabricNotFresh`, measured for every
  shipped adapter by lane probe `probe_per_adapter.py`, not by a test in this
  tree), and an acquisition or population phase composed over it is refused
  when the resolver is constructed (measured over the in-memory store), as is
  the paved road over such a substrate when it is opened (measured over the
  in-memory store and a network adapter, before anything connects), so before
  any question runs (`AcquisitionOverUnverifiableStore`). Over a store with a
  path, just before its first acquisition phase the call refuses a fabric not
  booted for its question (`AcquisitionNeedsAQuestionFabric`) and claims the
  fabric for its question. Every governed call over a fabric booted for its
  question claims it, with an acquisition phase or without one, so a second
  question on that fabric, after the first or at the same time, is refused
  (`AcquiredFabricReused`) before anything is read or fetched for it (a
  second call with no acquisition phase is measured in
  `tests/products/test_withheld_subject_child_arguments_and_question_stores.py`).
  A question's store booted again is refused for every governed call, and so
  is a store that existed with no marker beside it (see "A question's store
  the markers do not reach" below). The paved road already booted a new
  fabric for each question; it now declares it.
- **A population read as its own phase (Q7).** A read that fetches the same
  content whatever is asked is declared as the population phase:
  `open_product(..., population=...)` on the paved road, or
  `GovernedResolver(population_acquisition=...)` by hand. It runs once per
  question, first, and is handed no subject: a `PopulationAcquisitionContext`
  on the paved road and a `PopulationQuestion` by hand. A walk of every object
  reachable from what it is handed found no trace of the asked identifier.
  Then the fabric is read (the state a withheld subject is rendered from), and
  then your ordinary `acquire` runs once, with the asked subject. Two phases on
  one object, or either phase holding the other or the object the other is
  bound to, are refused at construction and at open
  (`PopulationPhaseSharesAnOwner`). The check walks what each phase holds
  (`D-IMPL-378` decision 3 (a)): the object a method is bound to and its
  function; a function's closure cells, default arguments and attributes; an
  object's declared slots and instance attributes; the members of a list,
  tuple, set or frozenset and the keys and values of a dictionary. It follows
  at most `src/ccf/products/resolver.py::SHARED_OWNER_WALK_DEPTH` (12)
  references in a row, reads at most
  `src/ccf/products/resolver.py::SHARED_OWNER_WALK_OBJECTS` (5,000) references
  from each phase, and calls nothing your objects define. A declared slot
  never assigned and an empty closure cell hold nothing, and the walk reads
  them so
  (`tests/products/test_q7_walk_unreadable_member_and_unread_holders.py::test_q7_control_a_slot_never_assigned_still_reads_as_holding_nothing`,
  `tests/products/test_q7_walk_unreadable_member_and_unread_holders.py::test_q7_control_an_empty_closure_cell_still_reads_as_holding_nothing`).
  Where reading what an object holds raises otherwise, such as another
  class's member descriptor in a slotted class's namespace, the walk cannot
  complete, and the two phases are refused rather than admitted
  (`SharedOwnerWalkIncomplete`, a `PopulationPhaseSharesAnOwner`;
  `D-IMPL-378` repair 1.8;
  `tests/products/test_q7_walk_unreadable_member_and_unread_holders.py::test_q7_a_member_the_walk_cannot_read_is_refused_by_name`).
  What it cannot
  detect: anything past either bound; state the two phases share through a
  third object, such as a common dictionary; state reached only through a
  property, another descriptor, `__getattr__` or `__getattribute__`, or held
  by a class that replaces `__dict__`; what a C-extension object keeps in its
  own fields, which the walk does not read: a `functools.partial`'s
  arguments, a `collections.deque`'s members, a `types.MappingProxyType`'s
  mapping, a generator's frame, an `operator.methodcaller`'s arguments, and a
  closure cell's contents where the cell is held anywhere but in a function's
  closure; module globals and class attributes; and anything reached only
  through a weak reference or an external store. Each limit is asserted as
  the documented behavior in
  `tests/products/test_q7_shared_owner_bounded_walk.py::test_q7_limit_state_the_walk_does_not_read_is_not_seen`,
  `tests/products/test_q7_walk_unreadable_member_and_unread_holders.py::test_q7_limit_a_holder_the_walk_does_not_read_is_not_seen`
  and the tests beside them. The walk also reads the SDK's own state a phase
  holds, which grows as a service runs. On the paved road each question's
  walk reads the L2 worker, the Control Plane registry and the registry's
  audit log, which gains events at every question, so after a few questions
  of one opened product the walk needs more than its reference bound, is cut
  off, and admits the two phases: what lies past the cut-off is not checked.
  A resolver you build whose population phase holds its fabric reads the same
  state: a holding of the other phase's object that the walk reached and
  refused on a fresh registry was admitted once resolvers built against that
  registry had grown its audit log. So, as built (`D-IMPL-378` decision 3
  (a); repair 2.4 is not built), the guard's coverage shrinks as a service
  runs (both measured in
  `tests/products/test_q7_paved_road_keeps_answering_as_questions_accumulate.py`).
  So keep the population phase free of anything the other phase writes.
  Declared this way, a population source and a hybrid source each matched a
  nonexistent subject's answer on both anchors.
  A declared parameter that itself names an entity still reaches the
  population phase.
- **An early decision, before anything is fetched (Q8).** A plan factory may
  declare a `SubjectDisclosurePolicy` through `subject_disclosure()`: the
  subjects each principal or role is not told about, and an identifier that
  names nothing, to ask in their place. The decision reads only the asked
  identifier, the principal's identity and role, and that declaration, and it
  was the same for a subject the source holds and one it does not. For a
  subject not disclosed, your ordinary `acquire`, the composite's children and
  the walk are asked about that stand-in instead (the population phase is
  never handed a subject), and the product is computed once, along the path a
  nonexistent subject's question takes. Your projection must withhold the same
  subjects; if it answers one, the call raises `UndisclosedSubjectAnswered`
  before the decision is recorded or served. A class that composes children
  withholds only this way. Construction refuses a composite whose plan
  factory's `subject_disclosure()` returns no policy
  (`CompositeNeedsAnEarlyPolicy`), and an early policy over a child resolver
  that is never handed the request (`EarlyPolicyNeedsRequestAwareChildren`).
  It also refuses a composite that declares no stance at all, neither an
  early policy nor `subject_withholding: never` on its class
  (`CompositeNeedsAWithholdingStance`, measured by
  `tests/products/test_sec020_p2c_composite_stance.py`): Dave's ruling P2 (c),
  2026-10-08. Since his E2 (ii) (d), later that day, `never` is a stance only
  over a plan factory that positively declares it never withholds (the bullet
  on the record behind an answer, below).
  With the early policy, a withheld composite matched a nonexistent subject's
  on both child anchors. That the stand-in names nothing is checked, not
  assumed (Dave's decision 4 (a), `D-IMPL-378`, 2026-10-09). For every
  question of a class with an early policy, whatever the policy decides for
  the asked subject: the graph read before your subject-keyed acquisition must
  not name the stand-in (an entity, or a relationship end); your acquisition
  is asked about `UNHELD_SUBJECT_PROBE` and then about the stand-in, and must
  acquire nothing for the stand-in that it does not acquire for the probe
  identifier; and the graph the plan reads must not name it. A failed check
  refuses the question as `UndisclosedSubjectSubstituteIsHeld`, with one message
  whatever was asked, before your acquisition is handed the question (the
  check after acquisition: before anything is computed or recorded). On test
  fixtures, a source holding the stand-in under its own URI or under another,
  or a population phase writing it, was refused alike for a withheld subject,
  two nonexistent ones and a served one, and the withheld and nonexistent
  answers did not differ by the closing test's rules at any door
  (`tests/products/test_sec020_stand_in_is_verified_absent.py`); before the
  check, a source holding the stand-in told them apart, at the empty finding
  and the debt under `from_decision` and by the refusal kind under
  `from_entity_freshness`. What the two calls leave is compared as entities,
  relationships and claim values, with each lineage entry's source and passage
  anchor; the envelope id and the receipt instant a delivery carries are set
  aside (Dave's repair 1.3, `D-IMPL-378`, 2026-10-09). So a read that acquires
  the same content whatever is asked is not refused, also when your adapter
  gives each delivery its own envelope id or receipt instant, while a claim
  value, a relationship, a source or a passage anchor that only the stand-in's
  call brings is still refused, for every question alike
  (`tests/products/test_sec020_stand_in_delivery_lineage.py`; on that fixture
  an envelope id reached neither an answer nor any artifact in the
  deployment's store, only the question's own graph store). It costs two more
  calls to your acquisition and two more graph
  reads per question of such a class (measured on the paved road's test
  fixture: three calls and five reads, against one and three for a class
  affirming `never`). Not detected: a source that recognizes the stand-in and
  answers nothing for it while it answers other identifiers it does not hold
  with content, and what a composite's children's sources hold for it; and
  the check after acquisition reads what the question's own acquisition wrote,
  so a source that writes the stand-in for some subjects only is refused for
  those questions only. Declare a stand-in that nothing in your deployment
  holds. For every question of a class with an early policy, a refusal your
  subject-keyed acquisition raises (a `GovernedRefusalRaised`, whatever it
  carries, or a type your class or the SDK declares at the seam) is served and
  recorded as one constant, `EARLY_POLICY_ACQUISITION_REFUSAL`:
  `subject-unavailable`, cause `undisclosed`, no code, and one SDK sentence
  (Dave's 2.2 (a), `D-IMPL-378`, 2026-10-09). Before it, a source answering
  "no record for" the identifier it was asked put the stand-in's identifier in
  the withheld subject's answer and record, and a source could choose a
  refusal's code, cause or kind by what it was asked. On test fixtures the
  withheld and nonexistent refusals now differ, in process, only at the hash of
  each caller's own question, and the closing test's own rules find no other
  difference at any door
  (`tests/products/test_sec020_early_policy_acquisition_refusal.py`). Neither
  the answer nor the record keeps your source's own text, code, cause or kind
  for such a refusal; a declared population phase's refusal is kept as your
  source stated it.
- **Each phase once for the question, and one computation (Q10, as
  amended).** Each declared phase runs once per question for the question
  itself. Before that call, a class that may withhold and declares no early
  policy asks your subject-keyed acquisition once more, about
  `UNHELD_SUBJECT_PROBE` (ruling P6 (a)), and a class with an early policy asks
  it twice more, about `UNHELD_SUBJECT_PROBE` and then its stand-in (decision
  4 (a)); a class affirming `never` asks it nothing more. On the paved road's
  test fixture that is three calls and five graph reads per question with an
  early policy, two and four with the probe, and one and three for `never`
  (the early sequence is pinned by
  `tests/products/test_withheld_subject_population_composite_and_fabric.py::test_q10_each_phase_is_called_once_and_the_stand_in_replaces_the_subject`).
  Under the early decision the stand-in replaces the
  subject; the subject is never fetched as well. The product is computed once
  on that path, counted at the projection, including when the fabric already
  held the withheld subject, and the decision replays to its own address. The
  record keeps the caller's question and names the stand-in the walk started
  from (`ContentGenerationPath.executed_seeds`, absent from every other
  record), so anyone who can read the record can tell the subject was not
  disclosed (see "The record behind it" below). A withhold decided inside the
  projection of a class with no children still re-runs the plan as described
  above (`D-IMPL-371`, `D-IMPL-376`).

**Migrating a composition you build by hand (Q9).** If you construct
`GovernedResolver` yourself with an acquisition phase, boot a new fabric for
every question with `for_question=True` onto a store path that does not exist
yet, ask it one question, and close it, as the paved road does. A composition
that asks one long-lived fabric several questions now raises
`AcquisitionNeedsAQuestionFabric` at its first question. State
`population_acquisition=None` where you construct `GovernedResolver` directly;
`build_governed_resolver` and the paved road default it. A composition with no
acquisition phase is unaffected by Q9 alone. Under P4 (a), a fabric booted for
its question answers one governed call even with no acquisition phase, and a
question's store booted again answers none: a composition that asked one
question fabric several questions with no acquisition phase now raises
`AcquiredFabricReused` at the second (lane probe
`probe_question_fabric_two_plain_calls.py`). A composition over a store whose
connection names no path raises `AcquisitionOverUnverifiableStore` when it is
constructed if it declares an acquisition or population phase; without one it
serves as before (lane probe `probe_pathless_serves_without_acquisition.py`).
Every boot through a deployment door that creates its store at a path leaves a
marker beside it (`<resolved path>.ccf-deployment-store`, or the question
marker), so delete or copy a store together with its marker. A store created
before this change, or outside the doors, still boots, and every governed call
over it is refused (`UnmarkedStoreNotPresumedFresh`, or
`AcquisitionNeedsAQuestionFabric` with an acquisition phase) until it is
recreated through a door. Boot a question's fabric as a writer:
`for_question=True` with `read_only=True` raises `QuestionFabricNotExclusive`.
To read a question's store back for replay, boot it read-only and not for a
question; a record served over a fresh question store still replays to its
own address that way (P4s-A (b)).

**When a boot is refused over its deployment marker (`D-IMPL-378` repairs 1.1
and 1.2).** A plain boot through a deployment door that creates its store at a
path first creates the deployment marker beside it
(`<resolved path>.ccf-deployment-store`) reading `state: pending`, with a third
line naming the boot (`boot: <token>`), and rewrites it to read
`state: verified` only once its one read has found the store empty for its
tenant. A boot that fails anywhere after creating the marker removes it, and a
boot killed before its read completed leaves it reading `pending`. Every plain
boot whose store's directory exists, read-only included, holds
`<resolved path>.ccf-store-creation.lock`, an
exclusive `flock`, from its look at the path until it hands the fabric back,
so no two boots of the path create or verify its store at once. A boot that
finds the lock held is never left waiting without bound (`D-IMPL-378`
decision 19 (b), ruled by Dave on 2026-10-09 at 16:38 MST, adopting Grok's
recommendation: *"Wait a bounded time, then refuse by name. An unbounded wait
is not a lock."*). It is refused by name, `DeploymentStoreNotVerified` with
reason `lock-held`, naming the lock, and no store and no marker is created
at the path (the lock file itself is created when the boot opens it):
at once, unless the deployment declares `store_creation_lock_wait_seconds`, a
positive whole number of seconds, in its manifest or its `ccf_config.yaml`
(question 2, option (a), adopted by Dave at 17:53 MST); the SDK supplies no
value. With one declared, the boot first waits up to that long for the holder
to let go
(`tests/products/test_deployment_store_creation_lock_bounded.py`), and a boot
that gets the lock within it reopens the store the first boot verified,
reading nothing (measured across two processes, with a wait declared,
`tests/products/test_deployment_marker_serialized_and_stale_refused.py::test_1_2_a_boot_that_meets_another_boot_creating_the_store_waits_for_its_verification_then_reopens`).
A deployment whose boots of one store can overlap, several workers starting
together for example, declares a wait; without one, a boot that meets another
boot's creation is refused and must be booted again.
A boot whose store's directory does not exist takes no lock and creates
nothing there, not even the directory: it is left to the adapter, and the
SDK's SQLite adapter refuses it with SQLite's own error
(`sqlite3.OperationalError`), so there is nothing to serialize
(`tests/products/test_deployment_marker_serialized_and_stale_refused.py::test_1_2_measure_a_plain_boot_whose_store_directory_does_not_exist_takes_no_lock_and_creates_nothing`).
Which stale markers a boot verifies again by itself, and which it refuses:

- **Verified again, with no operator step: a deployment marker of any state
  with no store beside it, that the boot can read.** That covers `pending` from
  a boot killed before its store existed, `verified` with its store deleted or
  moved, a marker written before repair 1.1 (one line, no state), text the SDK
  does not write, and a symbolic link. One the boot cannot read is refused
  instead (below). The boot is creating a new store there, so, holding the
  lock, it replaces that marker with its own (`pending`), reads the new store
  once and marks it verified, exactly as at a fresh path
  (`tests/products/test_deployment_marker_serialized_and_stale_refused.py::test_1_2_b_a_stale_marker_with_no_store_beside_it_is_replaced_and_the_new_store_read_once_and_verified`).
  A store planted at the path before the boot opens it is refused by that read
  (`DeploymentStoreNotEmpty`) and the boot's marker removed
  (`tests/products/test_deployment_marker_serialized_and_stale_refused.py::test_1_2_b_a_store_planted_after_the_look_beside_a_stale_marker_is_refused_by_the_read_and_the_marker_removed`),
  and of two boots racing there under a declared wait, one creates and
  verifies the store and the other waits and reopens it
  (`tests/products/test_deployment_marker_serialized_and_stale_refused.py::test_1_2_b_two_plain_boots_racing_on_stale_no_store_paths_never_serve_a_store_they_did_not_verify`).
  The lock is what makes the replacement safe: every boot that creates or
  verifies a marker holds it until it has handed its fabric back or removed
  its own marker, so the marker a boot finds there belongs to no boot still
  running.
- **Refused until an operator resolves it**, with
  `DeploymentStoreNotVerified`, which names the marker and its `reason` and
  leaves the marker as it is: a marker beside
  an existing store that reads `pending`
  (`tests/products/test_deployment_marker_owned_and_crash_safe.py::test_1_1_a_boot_killed_before_its_read_completes_leaves_a_marker_no_later_boot_reads_as_verified`)
  or is `unreadable`, which includes the one-line marker written before repair
  1.1 (`tests/products/test_deployment_marker_owned_and_crash_safe.py::test_1_1_a_marker_whose_state_cannot_be_read_is_refused_by_name_and_left_for_an_operator`);
  with no store beside it, a marker the boot cannot read (a file it has no
  permission to open), also `unreadable`, whether left untouched or rewritten
  in place after the boot looked: its bytes cannot be compared, so the boot
  does not replace it (P-1 (b), ruled by Dave on 2026-10-09 at 20:13 MST: *"1. b and 2. a"*; the option's text, from lane
  `378j-bootlock`'s final report: *"Refuse it `unreadable` before replacing
  it."*; `tests/products/test_deployment_marker_rewritten_in_place_refused.py::test_p1_b_a_stale_marker_the_boot_cannot_read_is_refused_unreadable_and_left`);
  with or without a store beside it, anything at the marker's path that is
  neither a regular file nor a symbolic link (a FIFO, a socket, a device, a
  directory), also `unreadable`: its type is checked from `lstat` before any
  open and it is not replaced. The `lstat` narrows, and does not close, one
  race: a special file swapped in for a regular one between the `lstat` and
  the open is opened, without blocking and without following a link, and then
  refused from its descriptor's type (`D-IMPL-380` ruling 3, Dave, 2026-10-10
  05:34 MST, and the second round's ruling 1 (a), 07:39 MST;
  `tests/products/test_deployment_marker_special_file_refused.py`);
  a marker that appeared at a fresh path while the boot held the lock
  (`tests/products/test_deployment_marker_serialized_and_stale_refused.py::test_1_2_a_marker_that_appears_after_the_boot_looked_is_refused_as_claimed`),
  or a stale marker replaced by another file, or rewritten with other bytes,
  between the boot's look and its replacement of it
  (`tests/products/test_deployment_marker_serialized_and_stale_refused.py::test_1_2_b_a_stale_marker_replaced_by_another_file_after_the_look_is_refused_as_claimed_and_left`,
  `tests/products/test_deployment_marker_rewritten_in_place_refused.py::test_17_b_a_stale_marker_rewritten_in_place_after_the_look_is_refused_as_claimed_and_left`), `claimed`;
  and a store-creation lock that cannot be taken, `lock-unavailable`
  (`tests/products/test_deployment_marker_serialized_and_stale_refused.py::test_1_2_a_store_creation_lock_that_cannot_be_taken_refuses_the_boot_by_name`).
  Each of these is refused at the boot's look, before the boot creates a store
  or a marker. A `claimed` refusal can also come later, after the boot has
  created its store and read it empty: the marker the boot created was
  replaced by another file, or rewritten in place, before the boot could mark
  it verified. The boot then closes that store and leaves it where it stands,
  beside the foreign marker, and every later boot of the path meets that
  marker beside a store. Measured with a marker whose text the SDK does not
  write, each later boot, writer or read-only, is refused `unreadable` and
  changes nothing there
  (`tests/products/test_deployment_marker_serialized_and_stale_refused.py::test_1_2_measure_a_claimed_refusal_at_promotion_leaves_the_store_the_boot_created_and_read_and_the_next_boot_refuses`).
  The SDK never clears a marker that stands beside a store. A stale marker's
  bytes, or a symbolic link's target, read at the boot's look, are compared
  again immediately before the boot replaces it (`D-IMPL-378` decision 17 (b),
  ruled by Dave on 2026-10-09 at 16:38 MST, adopting Grok's recommendation:
  *"(b) Compare the marker’s bytes."*). So a stale marker rewritten in place
  with other bytes is refused `claimed` and left, and so is one deleted and
  created again with other bytes under the same inode number (lane
  `378j-bootlock`'s probe `probe_recreated_same_inode.py`, for a regular file
  and a symbolic link, where the filesystem reused the inode). What remains: a
  change made after that comparison and before the rename; a rewrite to
  identical bytes, which changes nothing a boot reads
  (`tests/products/test_deployment_marker_rewritten_in_place_refused.py::test_17_b_measure_a_stale_marker_rewritten_in_place_to_the_same_bytes_is_replaced_and_the_new_store_verified`).
  In each, the boot replaces the marker like any stale one and verifies the
  new store itself, so it serves nothing it did not read, but it does not
  report that something outside the SDK wrote there. A marker whose bytes the
  boot cannot read is not replaced at all: it is refused `unreadable` (above).
  A marker longer than the longest marker the SDK writes, with or without a
  store beside it, is refused `oversized`: the boot reads at most one byte
  past that length and neither compares nor replaces the file (`D-IMPL-380`
  ruling 4 (a), Dave, 2026-10-10 05:34 MST;
  `tests/products/test_deployment_marker_oversized_refused.py`).
- **Refused with nothing to resolve unless the holder has stopped or hung: a
  store-creation lock another holds**, `lock-held`, at once or after the
  declared wait
  (`tests/products/test_deployment_store_creation_lock_bounded.py::test_19_b_a_boot_that_finds_the_lock_held_and_no_wait_declared_is_refused_at_once_by_name`,
  `tests/products/test_deployment_store_creation_lock_bounded.py::test_19_b_a_boot_with_a_declared_wait_waits_that_long_for_a_held_lock_then_is_refused_by_name`).
  Nothing is created at the path and the marker is not touched; a later boot
  proceeds once the holder lets go.

To resolve a refusal:

1. Make sure no process is booting or serving the store. `fuser` or `lsof` on
   `<resolved path>.ccf-store-creation.lock` shows a boot in progress, and on
   the SQLite writer lease `<resolved path>.ccf-writer.lock` a writer's open
   fabric, but neither shows a read-only fabric: one that is open and reading
   holds neither lock. So run them on the store file itself too, `<path>`,
   and on its `<path>-wal` and `<path>-shm` files: an open fabric, read-only
   or not, holds its store file open until it is handed back
   (`tests/products/test_deployment_marker_serialized_and_stale_refused.py::test_runbook_a_read_only_fabric_holds_neither_lock_file_and_holds_its_store_file_open`).
   Change nothing while any of them shows a holder.
2. Read the marker. `pending` (the boot that created it never finished its
   read), `unreadable` (one line and no `state:`, text the SDK does not
   write, or a file the deployment's user cannot read) and `claimed` (a marker
   that appeared, or was replaced by another
   file or rewritten, while a boot held the lock; find what writes into the
   store's directory first) all mean that
   nothing shows the store beside it was read. Move the store (`<path>`,
   `<path>-wal`, `<path>-shm`) aside, with the marker if you want to keep it
   as evidence, and boot again: with no store beside it, any marker the boot
   can read is replaced, and the boot creates a new store, reads it once and
   marks it verified. One it cannot read is refused again until you remove it
   or make it readable. Then write the deployment's data into it again through its
   writer.
3. `lock-unavailable`: make `<resolved path>.ccf-store-creation.lock` a regular
   file the deployment's user can open and lock, on a local filesystem whose
   `flock` works. The store and its marker are untouched.
4. `lock-held`: another holds `<resolved path>.ccf-store-creation.lock`. A boot
   in progress lets go when it hands its fabric back or fails; boot again
   then. If `fuser` or `lsof` on the lock file shows a process that has
   stopped or hung, end that process; its lock goes with it. Never delete the
   lock file while a process holds it: the next boot creates a new one and
   runs beside that holder (lane `378j-bootlock`'s probe
   `probe_lock_file_removed_while_held.py`). The store and its marker are
   untouched.

Never write or edit a deployment marker by hand: a marker an operator writes
vouches for a store nobody read, which is what the refusal exists to prevent.
A marker binds to its store by path, beside it rather than inside it, so it
does not stand against an actor who can write into the store's directory
(below).

**SEC-020 is open.** Its closing test, the module
`tests/products/test_sec020_combined_proof.py`, passes in full since
2026-10-12. The 21 cases in it that failed before, all in
`::test_a_pin_filed_in_one_deployment_reads_alike_in_both` (three at the MCP
versioned-URI resolution, eighteen on write-then-read for the asker and for a
second principal), pass after designs 1.1 and 1.2 (`D-IMPL-378`; hosted run
`38287169568` on `01fc424d`). A green run is not closure. Every run of the
closing test also reports three limitations outside its gate, in the blocks
headed `SEC-020 D1 (a) LIMITATION`, `SEC-020 P6 PROBE LIMITATION` and
`SEC-020 E2 (ii) FALSE-DECLARATION LIMITATION`, and their cells still tell the
two apart. SEC-020 closes only on Dave's ruling. Each of the
following still tells a withheld subject from a nonexistent one. Each was
measured on test fixtures.

- **The answer's replay reference (D-IMPL-378, Q11; Dave approved it as E1 (a)
  on 2026-10-08).** Every answer names its decision record: `ServedProduct.replay_ref`,
  the MCP egress door's `replay_ref`, the HTTP product route's
  `X-CCF-Replay-Ref` header, and a refusal's `replay_reference`. The record
  was filed under its graph snapshot id, a hash of what the plan actually
  read, and the withheld answer's reference carried a different record name
  from the one two nonexistent subjects' answers shared, on both anchors, with
  no dereference at all. Now each product answer's record carries a fresh
  256-bit issuance identifier (`src/ccf/replay/record.py::new_issuance`) and is
  filed under its own content address
  (`src/ccf/replay/serve.py::ReplayWriter`), so equal references name
  byte-identical records. Measured in process, at the HTTP product route and
  at the MCP product door, served and refused, on both anchors: the same
  question asked twice is handed two references, two answers whose records
  differ never share a reference identifier, and neither a reference nor a
  name the store holds for the record is dimension 1's snapshot id
  (`tests/http_api/test_sec020_replay_reference_issuance.py`). The price: one
  question asked twice in the same governed state at the same instant is now
  two records with two references (it was one, `D-IMPL-253` amendment 3), so
  a deployment that compared two answers' references for equality can no
  longer do so. E1 (a) restates the three rulings that promised one record,
  `D-IMPL-253` amendment 3, `D-IMPL-358` ruling 1 and `D-IMPL-148` Addendum A,
  modulo the per-answer issuance: two answers to one question are one
  determination whose records differ only in their issuance
  (`tests/products/test_delivery_determinism.py`), and the client
  conformance suite compares `replay_ref` by the record it resolves to rather
  than by its string (`tests/client/conformance/suite.py::assert_served_parity`).
  SEC-020's closing test judges references by distribution, not equality: the
  two sides' references have one form, and their references and issuances
  pass a two-sample test pooled over every cell of a comparison
  (`tests/products/test_sec020_combined_proof.py::test_withheld_and_nonexistent_references_are_drawn_from_one_distribution`,
  which states the test's power). A reference names a record by the hash of
  its stored bytes, so its integrity is arithmetic. These SDK readers of a
  record by its reference re-hash the bytes before anything uses them, and
  refuse bytes altered under it: the replay engine's reads
  (`resolve_artifact`, `resolve_artifact_at_uri`, `replay`,
  `replay_refusal`), `OpenedProduct.record_of`, the governed evidence read,
  child admission's read of a child's record
  (`src/ccf/products/child_resolver.py::GrantBoundChildResolver._touched_entities`,
  which raises `ChildRecordAltered` before the admission gate sees anything),
  and the erasure door's read of each requested address, refused
  `subject-unverifiable` before an approval starts
  (`tests/replay/test_record_content_address_integrity.py`). A store's own
  `get` returns whatever it holds and checks nothing: code that reads a
  record straight from a store, rather than through one of those readers,
  must re-hash it itself.
- **The record behind it (D-IMPL-378, Q12; Dave ruled its three details on
  2026-10-08 as E2: (i) and (iii) approved, (ii) rejected at 12:29 and ruled
  option (d) at 16:40).**
  Dimension 1 of a withheld decision's record lists what the plan actually
  read, the acquired subject included. Before this change, read end to end
  through the governed dereference by their owner at full disclosure, the
  records behind a withheld answer and a nonexistent subject's answer differed
  at dimension 1 and nowhere else; the same test now finds both reads refused
  alike (`tests/http_api/test_sec020_withheld_record_dereference.py`). Owner
  read-back is now default-deny. The governed read hands a product
  record to its owner only when the tenant's entitlement policy lists the
  record's class in `evidence_readable_classes` and the record carries its
  class's affirmation that its answers never withhold their subject
  (`subject_withholding: never` on the class declaration, stamped on each
  record), or the record read nothing. No record written before the
  affirmation existed carries it, so existing records stay sealed. A tenant
  that lists a class without the affirmation, composite or not, is refused
  when the resolver is built
  (`src/ccf/products/resolver.py::WithholdingClassListedReadable`); a class
  that affirms it and then withholds a subject is refused before anything is
  recorded (`src/ccf/products/resolver.py::NeverWithholdingContradicted`). The
  MCP Experience door's `get_replay_record` names no address and refuses every
  call (`runtime/ccf_runtime/mcp/experience.py::ExperienceReplayReadRefused`).
  Measured at HTTP `/replay/decisions`, `/replay/resolutions` and
  `/artifact`, at the MCP artifact server's blob, presence and names
  resources and, since 2026-10-12, its versioned-URI resolution (design 1.1,
  D-IMPL-378;
  `tests/mcp/test_f1_1b_resolution_decides_governed_classes.py::test_q12_the_mcp_resolution_resource_holds_the_owner_read_back_rule`),
  at the Experience door and through the `ccf` CLI
  (`tests/http_api/test_sec020_q12_owner_read_back.py`). Read-refusal records
  keep their owner read-back (section 4.10). A class that affirms `never` over
  a plan factory declaring that it withholds (an early policy that withholds
  some subject, or `subject_disclosure()` returning `None`) is refused when its
  resolver is built, the same for every subject
  (`src/ccf/products/resolver.py::NeverWithholdingProjectionCanWithhold`;
  `tests/products/test_sec020_never_capability.py`). The SDK cannot see a
  withhold that the plan factory does not declare, so under Dave's E2 (ii)
  option (d) a class that affirms `never` is built only over a plan factory
  that positively declares that its projection never withholds:
  `withholds_no_subject()` returning `True`
  (`src/ccf/products/resolver.py::NonWithholdingPlanFactoryProtocol`). Silence,
  or any other value, counts as able to withhold and is refused when the
  resolver is built, before anything is fetched, the same for every subject
  (`src/ccf/products/resolver.py::NeverWithholdingNeedsAPositiveDeclaration`;
  `tests/products/test_sec020_never_capability.py::test_e2ii_d_the_paved_road_refuses_every_subject_alike_before_anything_is_fetched`).
  In the closing test every configuration whose plan factory declares that it
  withholds, or declares nothing, is now refused that way on every side, held
  against a positively declaring twin that answers
  (`tests/products/test_sec020_combined_proof.py::test_a_withheld_subject_under_a_never_class_is_indistinguishable`).
  **The positive declaration is trusted deployment code, an explicit
  assumption limited to code no caller can influence.** The SDK reads it once,
  with no argument, where the resolver is built, from the plan factory you
  composed it with; no request, parameter, door payload, harness or agent
  input, or caller-supplied document supplies, selects or alters it (measured
  statically and at the in-process, HTTP and MCP doors, with a control in which
  deployment code lets a caller in:
  `tests/products/test_sec020_e2ii_trusted_declaration.py::test_e2ii_d_no_caller_input_supplies_selects_or_alters_the_positive_declaration`).
  A FALSE declaration is the residual and stays visible: the class is built,
  and its withheld question raises where a nonexistent subject's is served (an
  HTTP 500 against a 200)
  (`tests/products/test_sec020_e2ii_trusted_declaration.py::test_e2ii_d_counterexample_a_false_positive_declaration_still_tells_the_withheld_subject_apart`),
  and every run of the closing test reports it outside its gate
  (`tests/products/test_sec020_combined_proof.py::test_e2ii_limitation_the_false_declaration_cells_are_measured_not_gated`).
  Declare `withholds_no_subject()` only over a projection that never sets the
  withheld signal, never let it read anything a caller sends, and do not
  affirm `never` for a class whose projection can withhold.
  **Where default-deny applies, and where it does not (E2 (i)).** Every read
  an agent can reach holds it: the governed evidence reads above, and the
  Experience door, which refuses. In process, what an agent, a harness
  adapter or a product client is handed (`ProductClient`, its `Result`, the
  in-process adapter) carries a record's reference and never the record. The
  reads that do not hold it are the operator's and the auditor's:
  `OpenedProduct.record_of` and the replay engine (`replay`,
  `replay_refusal`, `resolve_artifact`, `resolve_artifact_at_uri`). Each is
  handed, or carries, your ArtifactStore, and its caller can read the same
  bytes straight from the store, so Dave ruled them unrestricted. Never hand
  an opened product, or anything else holding the store, to an agent: that
  hands the agent the store. Measured on one withheld answer by
  `tests/http_api/test_sec020_e2i_operator_boundary.py`: the owner's governed
  read is refused `evidence-class-sealed`, and the operator's handles return
  the record.
  **A refusal recorder must take `subject_withholding=` (E2 (iii)).** The
  resolver passes it on every refusal it records. A recorder written to the
  earlier signature, without the keyword or `**kwargs`, is refused where the
  resolver or an entitling door is built (`IncompatibleRefusalRecorder`),
  instead of raising `TypeError` at its first refusal
  (`tests/products/test_sec020_e2iii_recorder_at_construction.py`).
- **Composite children whose arguments come from captured state (P3 (a), which
  Dave approved on 2026-10-08 "as the API improvement, but not as enforcement
  proof").** The deployment's child-arguments mapping is handed the request
  its composite asks the children about, the same request the child questions
  are minted from (`src/ccf/products/child_resolver.py::ChildArguments`); under
  the early policy it names the stand-in in place of the subject. A mapping
  that took the child's subject from that request asked its child about the
  stand-in, and the composite was answered as a nonexistent subject's
  composite was, on both child anchors
  (`tests/products/test_withheld_subject_child_arguments_and_question_stores.py`).
  **Trusted deployment code is an explicit assumption.** The SDK cannot see
  where a mapping's values come from. A mapping that ignores what it is
  handed and uses a subject it captured itself still asks the child about the
  withheld subject: under `from_decision` the composite was then refused
  `composite-child-refusal` (the child answered a question other than the one
  the composite asked) where a nonexistent subject's composite was served,
  and under `from_entity_freshness` both were refused alike. That
  counterexample is kept as a measured limitation:
  `tests/products/test_sec020_p3_captured_subject_counterexample.py`. A
  mapping is your code, bound where your child resolver is built: no request,
  parameter, door payload, harness or agent input, or document supplies or
  selects one (measured: a mapping-shaped parameter is refused
  `undeclared-parameter` before any child is asked,
  `tests/products/test_sec020_p3_captured_subject_counterexample.py::test_p3_condition_iii_no_caller_input_supplies_or_selects_the_child_arguments_mapping`).
  A caller's declared parameters do reach your mapping, unchanged, so take
  every child's subject from the request's `subject`, never from a parameter.
  A composite that declares nothing is refused when its resolver is built
  (P2 (c), above), and `CompositeWithheldLate` remains for a composite whose
  early policy does not cover a subject its projection withholds
  (`tests/products/test_sec020_never_capability.py::test_ct_d_control_composite_withheld_late_remains_for_a_composite_whose_early_policy_misses_the_subject`).
  A composite whose class affirms `never` is built only over a plan factory
  positively declaring that it never withholds (E2 (ii) (d)); one whose
  declaration is false and that withholds anyway is refused as
  `NeverWithholdingContradicted`, which is checked first (`D-IMPL-378` CT-D
  (a), diagnostic precedence only;
  `tests/products/test_sec020_never_capability.py::test_ct_d_a_never_composite_that_withholds_late_is_refused_as_never_withholding_contradicted_first`);
  its withheld question still raises where a nonexistent subject's is
  answered, the residual the bullet on the record behind an answer names.
- **A composite child's own decision record, under an early policy (disclosed
  by Dave's decision 18 (A), `D-IMPL-378`, 2026-10-09).** The parent's early
  policy asks its children about the stand-in in place of a withheld subject,
  and each child's own door files the child's own decision record, under the
  child's product class, in the deployment's store. That record keeps the
  question the child was asked: for a withheld subject it names the stand-in,
  whatever the child's source answers, and for a nonexistent subject the
  identifier asked. A child source that refuses an identifier it does not
  hold with text that names it (`no record for <identifier>`) puts it in that
  record's refusal text too: repair 2.2 (a)'s constant applies to the
  parent's subject-keyed acquisition, not to a child's, and is not extended to
  children in this batch. The parent's answers to the two were alike at every
  door by the closing test's own rules, the answers name neither the child's
  record nor the stand-in, and the parent's records do not name the child's
  record, so no door shows it; whatever reads the deployment's store, as the
  operator's and the auditor's handles above do, tells the two apart at rest
  (`tests/products/test_sec020_composite_child_record_names_the_stand_in.py`).
  Whether a governed read hands a child's record to a principal, where the
  child's class affirms `never` and is listed in `evidence_readable_classes`,
  is not measured here.
- **A question's store the markers do not reach.** The withheld subject's
  acquisition stays in the store its question wrote, and the paved road leaves
  that store on disk when it closes the fabric (the replay road reopens it).
  Under P4 (a) a store booted for a question carries a marker beside it, and a
  governed call over that store booted again, in the same process or another,
  is refused before the graph is read: `QuestionStoreReopened` with no
  acquisition phase, `AcquisitionNeedsAQuestionFabric` with one. A store that
  existed with no marker beside it, booted for a question before the markers
  existed, copied without its marker, or created outside the deployment doors,
  is not presumed fresh and is refused the same way, with
  `UnmarkedStoreNotPresumedFresh` in place of `QuestionStoreReopened`, on both
  anchors and with the same text whatever its first question acquired
  (`tests/products/test_unmarked_and_unverifiable_question_stores.py`; for a
  store booted again,
  `tests/products/test_withheld_subject_child_arguments_and_question_stores.py`;
  for a call with an acquisition phase, lane probe
  `probe_acquiring_call_over_reopened.py`). Records served over such stores
  still replay to their own addresses (both test modules). What the markers do
  not reach is measured by lane probes, not by a test in this tree
  (`probe_p4_strict_limits.py`, `probe_question_boot_window.py`,
  `probe_unreached_stores_distinguish.py`, `probe_p4_marker_limits.py`,
  `probe_emptiness_limits.py`). A marker binds to its store by path, beside
  it rather than inside it, and the SDK checks and reserves a path while the
  adapter creates the store at the boot. So a copy of a used question store with a deployment marker forged
  beside it answered a later question: after a question
  about a withheld subject the source holds, that later answer about an
  identifier that names nothing moved at `debt.debt` and
  `debt.factors.freshness`, and under `from_entity_freshness` also at
  `expires_at` and `ttl_anchor_at`, against the same store after a question
  that acquired nothing. A used question store written at a path after a
  plain boot left its marker there answered too, until OWED-RULINGS-3 item 2A
  (b) (`D-IMPL-378`, Dave, 2026-10-09), with the trigger repair 1.2 restores
  (Dave, 2026-10-09 10:54 MST): every plain boot that creates its store, at a
  path that held no store when the boot looked, whoever made a marker beside
  it, now reads the store it opened once, the read a question boot takes,
  and refuses one holding anything for its tenant
  (`DeploymentStoreNotEmpty`), removing the marker it created, so a later
  boot of that path answers no governed call
  (`tests/products/test_plain_boot_creating_its_store_finds_it_empty.py`,
  `tests/products/test_deployment_marker_serialized_and_stale_refused.py`).
  Under repair 1.1 (Dave, 2026-10-09 10:54 MST) that holds for every failed
  boot, not only a refused read: a boot that fails in `boot()` (a planted
  store given a second name, or its writer lease held elsewhere), in its
  read, while marking its marker verified, or in `close()` removes the
  deployment marker it created, only while that marker is still the one it
  created, and a retry over a store planted in that window opens it
  unmarked and answers no governed call
  (`tests/products/test_deployment_marker_owned_and_crash_safe.py`); before
  the repair the marker stayed and the retry served the plant (the panel's
  probes `p_2ab_marker_survives_a_failed_boot.py`,
  `p_2ab_variant_b_lease_held.py` and `p_b3_close_raises.py`). A plain boot
  whose path already carried a deployment marker with no store beside it
  (the store deleted, its marker kept) created its store without that read,
  and a used store written there was booted and answered, its later answers
  moving at the same fields as the forged marker's (lane probes
  `probe_stale_deployment_marker.py` and
  `probe_unreached_stores_distinguish_l4b.py`); under repair 1.2 such a boot
  replaces that marker with its own, under the store-creation lock, and takes
  the read a fresh creation takes, so a used store written there before the
  boot opens it is refused (`DeploymentStoreNotEmpty`) and the boot's marker
  removed (above). A store written at a question
  boot's path after the SDK's last check was booted as that question's
  fabric; it is now refused when the boot reads it (`QuestionStoreNotEmpty`,
  above), and that one read does not reach three things. A store whose
  every claim was superseded
  before the latest instant with no current successor, which no SDK writer
  leaves, written there by raw SQL, was booted, and its question read its
  rows. A raw SQLite connection, outside the SDK's writer lease, wrote into a
  question's store while the question ran, and the question read what it
  wrote. A store holding rows only for another tenant was booted, and the
  paved fixture's answer over it matched its answer over a fresh store. A
  deployment's own writes into a reopened store go through. A marker left
  after its store is deleted makes a later boot for a question at that path
  refuse, and every
  governed call over a plain boot there refuse: it fails closed. Ask new
  questions only of fabrics booted for them, and protect a question's store,
  and the directory it sits in, as you would its decision record.
- **A population read left inside your `acquire` (ruling P6 (a); not
  closure).** Declared as the population phase, or under an early policy, such
  a read matched (above). Left inside your ordinary `acquire`, with the
  withhold decided inside the projection, a nonexistent subject's question
  walks that content and the withheld rendering does not; the two differed at
  the empty finding under `from_decision`, and as `ttl-refusal` against
  `ttl-anchor-refusal` under `from_entity_freshness`. Dave's ruling P6 (a)
  (`D-IMPL-378`, 2026-10-08, a conditional implementation go) refuses that
  configuration with a probe. For a class that may withhold and declares no
  early policy, the governed call first asks your subject-keyed acquisition
  about `UNHELD_SUBJECT_PROBE` (`ccf-sdk:unheld-subject-probe`), reads the
  graph again, and refuses the question with
  `PopulationReadInSubjectKeyedPhase` if anything was written. It does so
  before your acquisition is handed the question's subject, and decides by
  nothing about the asked subject, so on test fixtures a withheld subject and
  a nonexistent one were refused alike, with one message, on the paved road
  and the low road: `tests/products/test_sec020_p6_population_read_in_subject_keyed_phase.py`,
  whose order tests log your acquisition's calls and every graph read in one
  sequence. That the probe identifier names nothing is checked, not assumed:
  a graph that names it (an entity, or a relationship end) before the probe,
  or after it, is refused as `UnheldSubjectProbeIsHeld` instead
  (`tests/products/test_sec020_p6_unheld_subject_probe_is_verified_absent.py`).
  The ruling amends Q10's "each phase once" to exactly this one extra call. It
  costs one more call to your acquisition and one more graph read per question
  of such a class (measured on one test fixture: two calls and three reads,
  against one and two). A class affirming `subject_withholding: never` is not
  probed; a class with a declared early policy is not refused by the probe,
  and its stand-in is verified instead, with the probe identifier as the
  baseline (the early-decision bullet above). A source that answers the probe
  identifier with a held refusal (a `GovernedRefusalRaised`, or a type your
  class or the SDK declares at the seam, such as `IdentityRefused`) refused an
  identifier nothing holds while a withheld subject was answered, on both
  roads. Since Dave's OWED-RULINGS-3 item 4 (b) (`D-IMPL-378`, 2026-10-09),
  as repaired by his 2.3 (b) the same day, every question to such a class is
  refused before your acquisition is handed the question's subject, answered
  and recorded as one constant SDK refusal, `UNHELD_SUBJECT_PROBE_REFUSAL`
  (`subject-unavailable`, cause `undisclosed`, no code, one SDK sentence), the
  same for every subject; the decision record files it at the `acquisition`
  seam beside the caller's question
  (`tests/products/test_sec020_held_refusal_at_the_probe_is_recorded.py` and
  `tests/products/test_sec020_held_refusal_at_the_probe.py`). That includes a
  held refusal decided by the question rather than the identifier, such as an
  intent, a parameter or a role your source refuses: such a question keeps one
  decision record, but neither the answer nor the record keeps your source's
  own kind, cause, code or text. Answer an identifier your sources do not hold
  with nothing. To be served, declare the read as the population phase
  (`open_product(population=...)`), declare an early policy, or affirm `never`
  for a projection that never withholds. **The probe
  is defeated by a source that recognizes it.** A source that answers nothing
  for the probe identifier, matched exactly or by its shape, and reads the
  population for every other identifier passes the probe, and the withheld
  subject and a nonexistent one are then still told apart
  (`tests/products/test_sec020_p6_probe_recognizing_source_counterexample.py`;
  reported every run of SEC-020's closing test in its own block,
  `SEC-020 P6 PROBE LIMITATION`). The closing test holds the refused cells as
  the refusal plus a twin that answers: the same source with its read declared
  as the population phase. That is Dave's CT-A rule extended to this refusal,
  not closure.

**Until SEC-020 closes,** do not rely on `withheld=True` alone to keep a
subject's existence from a caller. The composite-child, reopened-store and
population channels above still tell the two apart, and list a class for owner
read-back only if its projection never withholds a subject.

- **One more read per question.** With an acquisition seam declared, every
  governed call reads the tenant's graph once more, before the seam, whether
  or not the projection later withholds. On a test fabric of about 3,000
  entities this raised a governed call's median time to 1.2 to 1.3 times that
  of the same call with no seam, over two runs of six calls. That is one
  fixture's figure, not a sizing guide.
- **The withheld branch's own time, measured at one scale only.** A withheld
  answer decided inside the projection runs the plan a second time and, with
  an acquisition seam declared, builds the operator registry a second time
  (under an early policy the plan runs once; its time was not measured). On a
  test fabric of about 1,500 entities, withheld and nonexistent answers had
  medians within 2 percent of each other and overlapping ranges over eight
  calls each. With a similarity
  operator in the plan, the withheld median was 1.06 to 1.08 times the
  nonexistent one over two runs of eight calls each, with overlapping ranges;
  before the registry change it was 1.11 in one run. Larger fabrics and
  heavier plans are unmeasured.

### 4.13 One approval, one passage: resume over a shared store and a shared transport (D-IMPL-377, D-IMPL-378)

One human approval carries an execution past its gate once
(`runtime/ccf_runtime/workflow/engine.py::WorkflowEngine.resume`). Three
mechanisms stand between an approval and a second passage, and each was
measured going red when it was removed:

- **In one process, the single-flight claim** (`D-IMPL-377`). A resumption
  takes a claim on its execution before it reads the execution's state record,
  and gives it back on every exit: completion, refusal, exception and
  cancellation. The claim is keyed by the Control Plane state store the record
  lives in and by the execution's state key, and every engine in the process
  over that store shares it. While one resumption of an execution is in flight
  in the process, a second is refused rather than queued: a
  `WorkflowResumeRefused` audited `resolved=False`, which
  `POST /workflow/resumptions` answers with the same 409 it gives the
  sequential refusal.
- **The gate's closure on the HITL transport** (`D-IMPL-378`). After every
  check has passed and before it writes anything, the resumption asks the
  transport to close the gate on exactly the verdicts it judged
  (`src/ccf/hitl/transport.py::HITLTransportProtocol.close_gate`). A verdict
  recorded after the resumption read the verdicts makes the closure fail, and
  the resumption is refused; presented again, it judges the verdicts that now
  stand, and a rejection among them refuses it for the conflict. A verdict on a
  gate that is already closed is refused at both doors with `hitl-gate-closed`
  (HTTP 409) and nothing is recorded, and the HITL queue no longer lists the
  closed gate's event.
- **The conditional passage commit** (`D-IMPL-378`). The execution leaving its
  gate is a state write, conditional on the version of the record the
  resumption read (`src/ccf/controlplane/state.py::ConditionalStateStore`),
  committed before the step after the gate runs. Of two resumptions in two
  processes, or through two state-store objects over one durable store,
  exactly one commit lands; the other is refused before it runs anything. The
  attributed `workflow_resumed` row that names the approver is a second write,
  appended to the audit log only after that commit lands
  (`src/ccf/controlplane/state.py::AuditedStateWriter.write_if`), so a refused
  commit leaves no row. The two writes are not atomic. If the append fails
  after the commit landed, the resumption fails with the audit log's error and
  the execution has left its gate with no `workflow_resumed` row. An operator
  then finds its record `running` at the state after the gate, the gate's
  closure on the HITL transport still naming the approver (`decided_by`), the
  gate gone from the queue, and nothing in the audit log naming who approved
  the passage. When that state is a step, the step has not run and every later
  resumption is refused as an interrupted passage; when it is a terminal
  state, a later resumption completes the execution, and the completed record
  still has no `workflow_resumed` row
  (`tests/controlplane/test_audited_write_is_two_writes.py`,
  `tests/workflow/test_passage_commit_two_writes_limits.py`). The SDK does not
  yet detect or repair a passage left without its row: Dave ruled on
  2026-10-09 that such a transition be made detectable and recoverable
  (decision 7 (b), `D-IMPL-378`), and that design is in progress, not built.

Before these mechanisms, the following were measured on 2026-10-07:

- Two resumptions of one approval, through two state-store objects over one
  durable store, both passed the gate and ran the step after it twice.
- A rejection recorded while a resumption was deciding was outvoted: the
  execution completed at the approving terminal with both verdicts on record.
- A passed gate's event stayed in the queue, so a later rejection was recorded
  as a verdict on an open gate.
- An execution id could be started twice.
- A resumption that failed or was cancelled left an attributed
  `workflow_resumed` row for a passage that never committed.

Each is now a test that fails when its mechanism is removed
(`tests/workflow/test_approval_gate_limits.py`,
`tests/http_api/test_approval_gate_limits_door.py`,
`tests/mcp/test_hitl_gate_closed_mcp.py`). An execution id is now started
once, with a create-if-absent write before its first step; a second start of
the same id is refused "already exists".

- **Resume one execution from several processes only over a `shared` state
  store and a `shared` HITL transport.** The engine refuses, at construction
  and by name: a state store that is not a `ConditionalStateStore` declaring
  scope `process` or `shared`; a transport that does not offer the whole
  `HITLTransportProtocol` with such a scope; a `shared` store paired with a
  transport that is not `shared`
  (`tests/workflow/test_engine_refuses_unsupported_seams.py`); a `shared`
  transport paired with a store that is not, and one `process` transport
  already serving another state store
  (`tests/workflow/test_engine_refuses_unsupported_sharing.py`); and, dated
  2026-10-12, a transport that offers no `bind_approver_eligibility`
  (`tests/workflow/test_conflict_population_eligibility.py::test_an_engine_refuses_a_transport_it_cannot_bind_for_eligibility`).
  The shipped `InMemoryStateStore` and `InMemoryHitlTransport` are `process`.
  A deployment that supplies its own store or transport implements the
  conditional write or the gate's closure atomically with its other writes,
  keeps closures as durable as submissions, and runs
  `tests/conformance/test_gate_closure_and_conditional_write.py` against it.
  Its own transport, if a `WorkflowEngine` is composed over it, also
  implements `bind_approver_eligibility(control_plane)` and, at `submit`,
  judges every `approve` or `reject` on an approval-gate event that names an
  approval policy against each bound plane with
  `ccf.hitl.transport.check_approver_eligibility`, before recording it; no
  conformance test checks this. The engine can refuse an implementation that
  lacks the members; it cannot see whether one keeps the atomicity it
  declares, or judges what it is bound to judge.
- **A passage interrupted after its commit is never re-run** (`D-IMPL-378`).
  Suppose a resumption is cancelled, or its process dies, after its passage
  committed. The execution stays `running`, and `GET /workflow/execution`
  answers `status: "running"`. What happens next depends on where it stopped.
  - **At a step.** Every later resumption, in any process, is refused with
    "An interrupted passage is never retried", because that step may already
    have had effects the engine cannot see. The SDK offers no primitive that
    reconciles such an execution: an operator reads the gate's closure
    (`src/ccf/hitl/transport.py::HITLTransportProtocol.closures`) and the
    attributed `workflow_resumed` row, settles what the step did, and acts
    outside the fabric
    (`tests/workflow/test_approval_gate_limits.py::test_an_interrupted_passage_is_never_retried_by_any_process`).
  - **At a gate or a terminal state** (Dave's D2 ruling). This happens when a
    gate's route leads straight to a terminal state, or when an execution's
    first node is a gate, which the engine records as `running` before it
    suspends. No step runs in that window, so a later resumption from any
    process FINISHES the passage. It makes the version-fenced suspension or
    completion write and, at a gate, the one queue event. It invokes no step
    callable and writes no second attributed row. It finishes only when the
    passage's durable claim names it. For a passage past a gate, the claim is
    that gate's closure for the suspension the passage left, and its decided
    verdict must route to that state. For a start, the claim is the
    create-if-absent record, and the starter's own retried start finishes it
    too. A passage no claim names is refused: "no durable claim on the HITL
    authority path names it". If the original passage is still live, one
    fenced write lands and the other raises `ExecutionFenced` in the engine
    (`tests/workflow/test_finish_interrupted_passage.py`). The erasure door's
    retries reach this path. An erasure request or completion interrupted in
    that window completes on retry, and the record it files is the one its
    write-ahead entries name
    (`tests/erasure/test_interrupted_erasure_passage.py`).

  A resumption whose commit never landed (the write itself failed) left the
  execution `suspended` with no step run. Where its approval was resolved
  through the gate primitive (`ApprovalGate`, a stamped verdict), presented
  again from any process, it re-takes the same closure and runs the step
  after the gate once
  (`tests/workflow/test_approval_gate_limits.py::test_a_passage_whose_commit_never_landed_is_retried_once_on_its_own_closure`).
  Where the approval was recorded through the submit-only action door
  instead (`POST /hitl/actions`, which records no stamp), the execution stays
  stuck: the failed passage's closure retired the request, the engine counts
  an unstamped approval only while its request is pending (code reading of
  `runtime/ccf_runtime/workflow/engine.py::WorkflowEngine._gate_authority`),
  so every resumption, from any process, is refused for want of an approval
  and the step after the gate never runs
  (`tests/workflow/test_door_approved_gate_whose_commit_failed_stays_stuck.py`;
  disclosed by Dave's decision 3, `D-IMPL-378`, 2026-10-09 16:38 MST). Reconcile such
  an execution outside the fabric.

  A suspension whose approval request never reached the queue left the
  execution `suspended` with no request: its suspension write landed, and its
  process died, or its artifact store failed, before the enqueue. No verdict on
  it could count. Dave's decision 8 (a) extends D2 to this shape. The starter's
  retried start, or a resumption that finds no approval, restores that one
  request: the request the suspension would have filed, bound to the
  suspension's unchanged content hash. The recovery runs no step, records no
  verdict and closes no gate, a verdict recorded while the request was missing
  still never opens the gate, and a second recovery files nothing more. Such a
  verdict still counts as a disagreement, though: if it is the opposite of a
  verdict recorded after the restore, it holds the restored gate as a
  conflict, whoever submitted it (`D-IMPL-366` H2; follow-up 1 in
  `packaging/bank-controlled/BANK-PACKET.md` section 5). The
  erasure door's retried request reaches this path
  (`tests/workflow/test_restore_missing_approval_request.py`,
  `tests/erasure/test_erasure_request_restored.py`). Three limits are
  measured in the first file. When the suspension's own passage, or another
  recovery, has written the record and not yet queued the request, a recovery
  that runs in that window files a second identical request; the gate still
  opens once on one approval, and its closure retires both. A request that a
  gate primitive has claimed and not yet answered is filed again, and that
  verdict is then recorded without the primitive's stamp and still opens the
  gate once. The recovery files the request on its own engine's HITL
  transport, so run one HITL transport per Control Plane state store: with
  two, a request pending on one is filed again on the other. The recovery
  trusts the record it reads: a writer outside the engine (a single-writer
  violation) that rewinds a record to `suspended` at a gate the run already
  passed gets a request restored for it, and one human approval then runs the
  step after that gate a second time, as the same writer can already make that
  step run again with no human at all by writing the record
  `exception-routed` at it (disclosed by Dave's decision 1 (a), `D-IMPL-378`,
  2026-10-09 16:38 MST;
  `tests/workflow/test_outside_writer_can_rerun_the_step_after_a_gate.py`).
- **A passage fenced by another writer is refused `execution-fenced`**
  (`D-IMPL-378`). Every write that ends a passage is conditional on the
  version the passage wrote
  (`runtime/ccf_runtime/workflow/engine.py::WorkflowEngine._fenced_write`). If
  a writer outside the engine, or a store that does not keep its conditional
  write, moves the execution's record while a passage runs, that write raises
  `ExecutionFenced` and writes, audits and enqueues nothing. So does a
  finisher that loses its write to another finisher or to the original
  passage (the bullet above). `POST /workflow/invocations` and
  `POST /workflow/resumptions` answer it 409 with `error_code`
  `execution-fenced`, a finished start's fenced suspension included; before
  this change it reached the caller as an opaque 500
  (`tests/http_api/test_execution_fenced_door.py`). The erasure door, which
  drives the same engine in process, refuses it as an `ErasureRefused` with
  reason code `execution-fenced`, at a request's start and at a completion's
  last passage; after the last passage no erasure record is filed, and the
  address stays withheld (`index-unsupported`) under the index entries the
  completion appended (`tests/erasure/test_erasure_door_execution_fenced.py`).
  The other writer's record stands. Where the passage ran a step before the
  fenced write, that step may already have had effects, and a resumption
  presented again is refused as an interrupted passage without running it
  again (measured): reconcile the execution outside the fabric. No MCP door
  executes or resumes a workflow, and no HTTP or MCP door serves the erasure
  door.
- **A conflicted gate stays suspended for good. This remains open**
  (`D-GATE-357` (2)). Two recorded verdicts that disagree on one suspension
  refuse every resumption, and the SDK offers no primitive that reopens the
  gate (code reading). Three kinds of principal can hold a gate this way
  (dated 2026-10-12; the second and third are follow-ups 1 and 2 in
  `packaging/bank-controlled/BANK-PACKET.md` section 5, recorded and not
  built):
  - any eligible approver;
  - on any transport, any holder of `HitlSubmit` for the gate's event key
    (on a transport constructed with a Control Plane whose HITL policy
    requires signed bindings, only one whose attestation verifies under a key
    that policy declares for it; a plane an engine binds does not set this)
    whose `approve` or `reject`, bound to the suspension's content hash, is
    recorded while no event is queued or claimed under that key and before
    the gate closes: after a deployment-composed `ApprovalGate.resolve` has
    consumed the event and before a resumption closes the gate; after
    deployment code has drained the event with the transport's `dequeue`,
    which records no claim (for example, a worker that forwards events to a
    task system), and before the event is queued again or a resumption
    restores the request; between the engine's suspension write and its
    enqueue; or after an interrupted suspension, until the request is
    restored. No event is left to judge it
    against, so it is recorded unjudged (`event_state_at_submit` is
    `missing`), it never becomes authority, and an opposite verdict still
    counts as a disagreement (`D-IMPL-366` H2;
    `tests/workflow/test_sec006_engine_controls.py::test_t12b_a_missing_state_verdict_still_counts_as_a_conflict`);
  - on any transport, any holder of `HitlSubmit` for the gate's event key
    (with the same signed-binding condition) whose `approve` or `reject`,
    bound to the suspension's content hash, is recorded against a non-gate
    event (an `exception-escalation` event, or any other class that is not
    `approval-gate`) that a deployment filed under the gate's own event key,
    while that event is the one the transport selects under the key (its
    claimed event, otherwise the oldest queued one). The transport judges eligibility on approval-gate events only
    (`D-IMPL-366` G6 (a)), and the engine counts every recorded verdict that
    names the gate's key and the suspension's hash, whatever event it
    answered. The escalation can become the selected event without the
    gate's event being consumed. While the gate's event is queued ahead of
    the escalation, `ExceptionEscalation.resolve` claims the gate's event,
    because the transport's `remove` takes the first event under the key,
    whatever its class. If the transport then refuses the submission (for
    example, a principal the gate's approval policy does not admit, refused
    as a gate verdict), the rollback re-queues the gate's event behind the
    escalation, and that principal's next `approve` or `reject` under the key
    lands on the escalation unjudged (measured). A resolve refused before the
    claim, such as one bound to a stale content hash, re-queues nothing. No module in
    the SDK files an escalation under a gate's key; a deployment's own
    composition does.

  While the event the transport selects under the gate's key (its claimed
  event, otherwise the oldest queued one) is the gate's own approval-gate
  event, a principal the gate's approval policy does not admit can no longer
  hold the gate, on the transport a
  `WorkflowEngine` is composed over, even when that transport was
  constructed without a Control Plane (dated 2026-10-12). The engine binds
  its own Control Plane into the transport at construction
  (`InMemoryHitlTransport.bind_approver_eligibility`), and the transport
  refuses that principal's `approve` or `reject` at submit, before anything
  is recorded; the doors answer `approver-not-eligible`
  (`tests/workflow/test_conflict_population_eligibility.py::test_an_ineligible_principals_opposite_verdict_is_refused_at_submit`).
  The second and third kinds above are unchanged: with no event under the
  key, nothing is left to judge a later verdict against, and a verdict on a
  non-gate event under the gate's key is not judged.
  The engine refuses at construction a transport that offers no
  `bind_approver_eligibility`. It cannot see whether a third-party transport
  that offers one judges what it is bound to judge.

  Reconcile such an execution outside the fabric, and grant `HitlSubmit` for
  an approval gate's events only to its approvers.
- **Review the gates passed before the upgrade.** An execution that left a
  gate before this change still has that gate's event in the queue, because
  no closure exists for it, so a verdict presented on it is still recorded as
  a verdict on an open gate (code reading). Find the executions that left a
  gate before the upgrade and whose suspension holds both an approve and a
  reject verdict, and route them to human review. For a gate passed after the
  upgrade, the late verdict is refused instead.
- **Present a refused resumption again only after the other one has
  returned.** An in-flight 409 means another resumption of the same execution
  is in flight in this process. A repeat presented after that one has returned
  is judged on the execution as it then stands. If the other passed the gate,
  the repeat is judged at the gate the execution now waits on. A resumption
  refused because a verdict arrived while it was deciding may be presented
  again at once.
- **A step that never returns keeps the claim for the life of the
  process.** The SDK has no timeout and no operator override for the claim.
  The claim is given back only when the resumption itself exits, and
  cancelling the resumption counts as an exit (code reading of
  `runtime/ccf_runtime/workflow/engine.py::WorkflowEngine.resume`). While a
  step after a gate hangs, every later resumption of that execution in the
  process is refused as in flight. Cancelling the hung resumption, or
  restarting the process, makes it an interrupted passage. With a durable
  state store, the execution stays `running`, and every later resumption is
  refused as above rather than running the step again. With the shipped
  composition, which keeps its state store, HITL transport and audit log in
  memory, a restart loses the execution.
  Measured before `D-IMPL-378`: the restarted process held no state record
  and no recorded approval for it, and a resumption was refused "no execution
  exists". Starting it again under the same execution id ran it from its first
  step to its first gate, where it waited for a new approval. The audit rows
  the killed process wrote are gone with its memory (code reading).
- **The in-flight refusal tells a `Resume` holder that a resumption is
  running.** The claim is taken after the `Resume` capability is verified
  and before the gate's authority is checked (code reading of
  `runtime/ccf_runtime/workflow/engine.py::WorkflowEngine.resume`). So a
  principal can learn that another resumption of an execution is running
  if it holds a `Resume` capability for the workflow's definition key in
  that execution's tenant and names the execution id, whether or not it is
  an eligible approver. While another resumption runs, its request is
  refused as in flight. Without one, the same request is answered from the
  execution's state instead. Measured with a principal that neither started
  nor approved the run. A `Resume` capability minted for another tenant on
  the same definition key is answered "no execution exists" under its own
  tenant, so it learns nothing about this one (measured). Each refused
  request is audited as a refused resumption with no actor (measured).
  Grant `Resume` only to principals entitled to know when a run is being
  resumed.
- **At the erasure door, read the reason code, not the message, and
  retry.** When two completions of one erasure request run at once, the one
  the claim refuses raises `ErasureRefused` with reason code
  `workflow-refused` (measured). The door builds the message from the
  engine's refusal and cuts it at 400 characters (code reading of
  `runtime/ccf_runtime/erasure/door.py::ErasureDoor.complete`). The
  request's 64-character identity appears twice in that refusal, so the cut
  falls inside the engine's reason. The closing clause the door writes,
  "the address stays withheld (index-unsupported) and the audit says so",
  is therefore missing from the message (measured). Had it appeared, it
  would not hold. Until the other completion returns, a read of the
  address is refused `index-unsupported`, because its index entry is
  written and its record is not yet filed. Once the other completion files
  the record, the read is refused as erased with the request's reason, and
  a retry of the refused completion returns the same record (measured).

### 4.14 Declare a temporal boundary for every tenant (D-IMPL-358)

Every question served through the governed resolver
(`src/ccf/products/resolver.py::GovernedResolver`, which `open_product` and
`build_governed_resolver` compose) is first held to how far into the past its
tenant answers for. The resolver reads the tenant's `TemporalBoundaryPolicy`
(artifact class `ccf.temporal-boundary-policy`) from the Control Plane at the key
`{tenant}/ccf.temporal-boundary-policy`, and judges the question before anything
is acquired or read (`src/ccf/products/refusal.py::refuse_temporal_bound`).

**There is no default, so an undeclared tenant serves nothing.** The SDK holds
no duration (`D-IMPL-38`), and `D-IMPL-358` ruling 11 forbids inventing one:
every governed question for such a tenant that is not refused earlier, for a
reason of its own, is refused here. A deployment upgraded from a release that
predates this check boots normally and then serves no governed question until
it declares a policy for each tenant it serves.

**What the refusal looks like.** It is a governed refusal, returned as data and
recorded in Decision Replay like any other
(`tests/products/test_resolver_seam.py::test_E2_no_declared_temporal_policy_refuses_before_acquisition`):

- Its kind is `temporal-bound-refusal` and its reason is
  `temporal-boundary-undeclared`.
- At `minimal` disclosure the caller sees the statement *"this tenant does not
  answer for the instant this question names"*, `max_past_seconds` and
  `permitted_clock_skew_seconds` as `null`, and `policy_key`, `presented_at` and
  `served_at` as `undisclosed`
  (`tests/products/test_disclosure.py::test_G1_the_undeclared_reason_discloses_nothing_actionable_at_minimal`).
- Over HTTP the status is 400. The request was not at fault, but the status is
  assigned per refusal kind, and two of this kind's three reasons are the
  caller's to fix; the code names this as a residual
  (`runtime/ccf_runtime/http_api/refusal_status.py::_STATUS_BY_TYPE`).
- The recorded refusal names the key that was required and a detail stating the
  remedy, and it carries no policy binding for the absent policy.
- A deployment that composes `IngressTemporalBound` on its own ingest path gets
  `TemporalWriteRefused`, with the same reason, for every envelope of an
  undeclared tenant
  (`tests/signal_layer/test_step8_temporal_write_guard.py::test_a_missing_policy_REFUSES_and_names_the_key_and_the_absence`).
  On the paved road the serve refuses first, before anything is acquired.

**Declare it, once per tenant.**

- **Single-file config (`ccf_config.yaml`).** Add a top-level
  `temporal_boundary:` section holding exactly the two values. It requires a
  top-level `tenant_id`, because the key is derived per tenant, and it refuses
  `key`, `class_id`, `role` and `registration`, so two tenants cannot share one
  boundary (`src/ccf/deployment/config.py::_derive_bare_typed_entry`;
  `tests/deployment/test_namespaced_boot.py::test_CFG6_a_declared_temporal_boundary_registers_resolves_and_pins_exactly`).

  ```yaml
  tenant_id: your-tenant
  temporal_boundary:
    max_past_seconds: 2592000         # illustrative only: 30 days
    permitted_clock_skew_seconds: 300 # illustrative only: 5 minutes
  ```

- **Deployment manifest.** Add an entry whose key is the class id exactly. The
  loader places it under the manifest's `tenant_id`, which is the key the
  resolver reads. The document holds the same two values and nothing else; a
  `semver` line is refused, because the contract is closed.
  `examples/s1-01-hello-context-product/artifacts/manifest.yaml` carries this
  entry, and `examples/s1-01-hello-context-product/artifacts/temporal-boundary.yaml`
  the document.

  ```yaml
  - path: temporal-boundary.yaml
    key: ccf.temporal-boundary-policy
    class_id: ccf.temporal-boundary-policy
    role: register
    registration: typed
  ```

- **More than one tenant.** Each config or manifest boots one tenant, so each
  declares its own. A composition root serving several tenants registers one
  `TemporalBoundaryPolicy` per tenant at the key
  `src/ccf/controlplane/temporal_boundary.py::temporal_boundary_policy_key`
  derives.

**Choose the two values.** Both are your policy decisions; the SDK supplies
neither and recommends neither. The numbers above only show the shape.

- `max_past_seconds` is how far before the serve instant a question may reach.
  The resolver judges the question's `asked_at`, and separately the decision
  instant the product class derives (from a declared as-of parameter, where the
  class has one), against the instant it serves at. An instant further back is
  refused, as `asked-at-outside-temporal-bound` or
  `decision-instant-outside-temporal-bound`, and never narrowed. Set it at least
  as far back as the oldest as-of question the tenant must answer. On the paved
  road the same window holds each acquired envelope at the write.
- `permitted_clock_skew_seconds` is how far ahead of the serve instant a
  presented instant may run before it is refused as impossible rather than
  treated as current. Set it to the clock disagreement you accept between
  callers and the fabric.
- `0` is the strictest value, not "unbounded": a `max_past_seconds` of `0`
  refuses a question asked as of any earlier instant. No value means "no bound";
  a tenant that wants a wide reach declares a large number. Negative values are
  refused.
- A frozen dataset ages. A window chosen so that today's questions about a
  fixed historical date pass will refuse those same questions later, as the
  serve instant moves on.
- The exact version of the policy in force is pinned on the record of every
  served decision and of every refusal its window caused. Changing the window
  registers a new version; records already written keep naming the one that
  governed them
  (`tests/products/test_resolver_seam.py::test_E6_the_resolved_temporal_policy_pins_its_exact_step3_binding`).

**A demonstration over a frozen dataset can declare its serve instant instead**
(`D-IMPL-378` C1; SDK-defined). A `demonstration_serve_instant:` section in
`ccf_config.yaml` makes the resolver serve at the declared instant rather than
today's, so a demonstration's pinned question does not expire. It is refused
unless the fabric runs on the SDK's own approved development backends (decision
6 (b), Dave, 2026-10-09: *"Restrict demonstration time to the SDK's own approved
development backends. Explicitly amend the broader “declares itself”
wording."*). The graph adapter must be one the SDK ships whose own registration
is a development reference: the SQLite or the in-memory adapter. An adapter's
declaration about itself does not count. This amends the earlier wording, under
which a substrate that declared itself a development reference was admitted: a
third-party adapter is refused even when its registration declares
`development_reference` and re-registers one of the SDK's own stores. The
artifact store's class must be the SDK's `FileArtifactStore` itself. That check
is an exact-type test (decision 4 (a), 2026-10-09 16:38 MST (`D-IMPL-378`; the
text is Grok's recommendation, which Dave adopted): *"(a) Exact type."*), so a
subclass of `FileArtifactStore` is refused, even one that overrides nothing;
this amends the earlier `isinstance` test, which a subclass passed
(`tests/client/test_demonstration_serve_instant.py::test_a_third_party_adapter_declaring_development_reference_is_refused_at_composition`,
`::test_a_third_party_adapter_declaring_development_reference_is_refused_at_the_in_process_door`,
`::test_the_sdks_own_development_backends_are_still_admitted_at_composition`,
`::test_a_declaration_over_a_non_development_graph_substrate_is_refused`,
`::test_a_declaration_over_a_non_file_artifact_store_is_refused`,
`::test_a_subclass_of_the_sdks_file_store_is_refused_at_composition`,
`::test_a_subclass_of_the_sdks_file_store_is_refused_at_the_in_process_door`,
`::test_a_subclass_of_the_sdks_file_store_fails_the_store_check`). Every record
made under it, served or refused, pins it in Decision Replay dimension 2
(`tests/client/test_demonstration_serve_instant.py::test_a_served_record_pins_the_declaration`,
`::test_a_refusal_record_pins_the_declaration`). **A running service keeps the
instant it was built with** (ruling C1-late (a), Dave: *"Running services retain
their startup snapshot. Document that later registration takes effect only after
rebuilding."*):

- The declaration is read once, when the resolver is built. One registered
  later does not reach that resolver, so a running service cannot be switched
  into demonstration mode
  (`tests/client/test_demonstration_serve_instant.py::test_a_declaration_registered_after_composition_does_not_reach_the_resolver`).
- It takes effect only in a resolver built after it is registered: a
  composition root's next `build_governed_resolver` call over the same Control
  Plane
  (`tests/client/test_demonstration_serve_instant.py::test_a_declaration_registered_after_composition_takes_effect_only_in_a_resolver_built_after_it`).
  The in-process adapter boots each deployment once per process from its
  `ccf_config.yaml` (`src/ccf/client/adapters/inprocess.py::InProcessAdapter._ensure_booted`),
  so there a declaration takes effect when the process next starts.
- The paved road takes its snapshot at `open_product` (amended 2026-10-11,
  G1-SDK-01; Dave, 16:23 MST, ruling 4). A declaration in the deployment's
  `ccf_config.yaml` when it is opened, with no clock composed by the caller, is
  honored on every question: the dated question is served at the declared
  instant, the ingress write guard judges envelopes at that same instant, and
  every record pins the declaration
  (`tests/products/test_paved_road_demonstration_instant.py::test_a_paved_deployment_with_no_composed_clock_serves_at_its_declared_instant`).
  Every refusal is kept: a caller-composed clock beside a declaration raises
  `DemonstrationServeInstantConflict`
  (`::test_a_caller_composed_clock_beside_the_declaration_is_still_refused`); a
  second declaration raises `DemonstrationServeInstantMisplaced`
  (`::test_several_declarations_are_still_refused`); a store that is not the
  SDK's own is refused even inside the SDK's erasure-consult wrapper, which the
  exact-type test looks through by exact type
  (`::test_a_store_that_is_not_the_sdks_own_is_still_refused`); a question
  outside the window around the declared instant is refused
  `asked-at-outside-temporal-bound`
  (`::test_a_question_outside_the_declared_instants_window_is_refused`). A
  declaration registered after `open_product` is not the snapshot: the next
  question raises `DemonstrationServeInstantConflict`, by name, before anything
  is acquired
  (`tests/client/test_demonstration_serve_instant.py::test_the_paved_road_refuses_a_declaration_registered_after_open_at_the_next_question`).
  The served instant is still a development instant, refused outside the SDK's
  own development backends.

## Validation-error text and caller values (SEC-024, choice C)

Every SDK contract derives from `CCFContract`, which sets pydantic's `hide_input_in_errors`. A rejected value
therefore never appears in the error's `str()`/`repr()`, in the egress door's failure log (which renders exception
type names and traceback frames, never exception text), or in any traceback a deployment captures. **One
consequence is accepted and documented (`D-IMPL-371`):** the text of a validation error that a door returns to the
caller — the MCP egress `door_question` and `parse_product_address` paths, and the HTTP product route's 400
detail — no longer echoes the rejected value. The field location and the message remain; the value does not. The
caller's own parameters in a governed refusal (the C-01 refusals) are unchanged: those are the caller's values
returned to that caller, not a disclosure. Nothing outside logs and `CCFContract` was changed for this finding.
