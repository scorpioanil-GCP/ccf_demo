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

### 1.2 SignedPrincipalBinding (D-IMPL-21, HITL identity)

`SignedPrincipalBinding` (`src/ccf/hitl/identity_binding.py`) reuses the
same D-IMPL-15 machinery — the joserfc-backed detached JWS envelope of
the injected `IdentityProvider`. The module holds no key machinery, no
JOSE registry, and no algorithm choice of its own: which keys exist and
which provider signs are the deployment's Control Plane configuration.
Verification (`verify_principal_binding`) takes its acceptable public
keys from the caller, mirroring the A2A posture. Whether a HITL door
*requires* a signed binding is the `ccf.hitl-policy` Control Plane
artifact's statement (`signed_binding_required`, D-16 — default false),
never a code constant. The typed decision values and the door surfaces are
documented on the [HITL Protocols](../reference/protocols/hitl.md) page;
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

## 4. Deployment posture: what to decide before a surface is up

Four decisions have to be made explicitly. None of them has a safe default
the SDK could pick for you, which is why each of them is a construction-time
argument rather than a setting buried in configuration. The first three
concern the HTTP surface, whose endpoint-by-endpoint contract is on the
[HTTP API page](../reference/http-api.md); the fourth concerns which transport
the MCP product door serves on.

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
host. The door states the one identity that boundary warrants rather than
admitting an unverified caller, and the consequence is worth stating plainly
because a deployment has to design around it:

> `ProductDoor.serve_stdio` serves one pre-set identity for every caller of
> the process (`ambient_stdio_identity`); a multi-principal deployment uses
> `serve_loopback` or composes its own transport. The composition control is
> designed with the harness adapters in 1.0.3 (`D-IMPL-361`).

Two bounds hold on that stated identity, and both are mechanism rather than
convention. It is scoped to exactly the one tenant the door was opened to
serve, and it is marked *ambient*, which makes every surface the egress
registers as mutating refuse it before the authorizer is even asked. Process
ownership is a defensible warrant for reading what the child process exists
to serve; it is not a warrant for writing on an authority nobody presented.

So a single-principal child process spawned by its own client is what stdio
is for, and it is a legitimate posture. Anything that has to tell two callers
apart — different entitlements, different perspectives, an audit trail that
distinguishes them — belongs on `serve_loopback` or on a transport you
compose yourself.
