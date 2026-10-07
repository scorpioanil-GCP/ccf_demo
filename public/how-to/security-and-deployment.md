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
  it is the development reference, not a custody recommendation.
  Production deployments implement the Protocol against their own key
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
  reason can be admitted later. The reference seen-set
  (`src/ccf/peering/issuance.py::InProcessSeenNonceSet`) covers one gate in one
  process and is not pruned; **a deployment running more than one receiver
  must share one** through `src/ccf/peering/issuance.py::SeenNonceSetProtocol`,
  or each receiver refuses only the replays it saw itself. Nonce uniqueness per
  peer is the producer's obligation; the SDK ships no generator.
- **A peered composite child is held to the subject its composite asked**,
  from the question its producer signed (closing SEC-025-U1), by the same check
  every other child leg passes.

What this does not do: it does not bound the bytes a request body may occupy
before parsing on the LF leg (`SEC-021-U1`, open).

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
  rule (CLAUDE.md §2.2: "never a secret in the tree"). Key files for
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

## 4. Deployment posture: what to decide before a surface is up

Five decisions have to be made explicitly. None of them has a safe default
the SDK could pick for you, which is why each of them is a construction-time
argument rather than a setting buried in configuration. The first three
concern the HTTP surface, whose endpoint-by-endpoint contract is on the
[HTTP API page](../reference/http-api.md); the fourth concerns which transport
the MCP product door serves on; the fifth concerns what the Claude Agent SDK
adapter's child process inherits.

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
allowlist: the `claude` child receives exactly the variables named in the
adapter's `child_environment`, and when none is declared it receives only
`PATH` and `HOME` (`TP-02`, `D-IMPL-361`). The adopter starts a session with
`transport=adapter.transport(carrier)`; the carrier fails closed on the
vendor's default transport, which raises `CLINotFoundError` and starts
nothing, because that transport would merge the fabric's whole environment
into the child.

## Validation-error text and caller values (SEC-024, choice C)

Every SDK contract derives from `CCFContract`, which sets pydantic's `hide_input_in_errors`. A rejected value
therefore never appears in the error's `str()`/`repr()`, in the egress door's failure log (which renders exception
type names and traceback frames, never exception text), or in any traceback a deployment captures. **One
consequence is accepted and documented (`D-IMPL-371`):** the text of a validation error that a door returns to the
caller — the MCP egress `door_question` and `parse_product_address` paths, and the HTTP product route's 400
detail — no longer echoes the rejected value. The field location and the message remain; the value does not. The
caller's own parameters in a governed refusal (the C-01 refusals) are unchanged: those are the caller's values
returned to that caller, not a disclosure. Nothing outside logs and `CCFContract` was changed for this finding.
