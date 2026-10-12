<!--
Copyright (c) 2026 David Castillo. All rights reserved.
Use, copying, modification, and distribution of the covered material
are governed by the CCF SDK Interim Software and Patent License
in the repository-root LICENSE.md and any controlling signed agreement.
Rights under that interim license begin only upon its execution
and are limited to its stated scope and term.
-->
# Release notes: `ccf_sdk 1.0.2.dev1564+g01fc424d9`, the 2026-10-13 delivery

This is a controlled delivery, not a release. **No tag. No public upload.**
The handoff record is [`BANK-PACKET.md`](BANK-PACKET.md). Where this page and
the packet differ, the packet governs.

| | |
|---|---|
| Source commit | `01fc424d92f8d15856d5f277e9cf18ef59bc7883` (code identical to the checked candidate `0af000f0`) |
| Wheel | `ccf_sdk-1.0.2.dev1564+g01fc424d9-py3-none-any.whl`, sha256 `186c9b73960c250a51e8c0ad7952721d9ca80d71055655933b09092c1fa8e9cc` |
| Hosted CI | run `38287169568` on `01fc424d`: every job and step passed |
| Replaces | `ccf_sdk-1.0.2.dev1551+g2cd96aef8` (source `2cd96aef`, the earlier wheel for this delivery, built the morning of Monday 2026-10-12) |

Later commits on `main` change documentation only. Every serve or refuse
outcome of the examples and both Hello World tutorials is unchanged, so
existing demonstration recordings stay valid; values that depend on the time
of the run differ on every run, as before.

## Changes that need action from an adopter

### 1. HTTP product route: a scope-mapping deny is now `404`

On `GET /product/{tenant}/{product_class}/{version}`, every deny by the
deployment's scope mapping is answered `404 subject-unavailable` instead of
`403 request-unauthorized`, whichever axis failed: for example a class no
scope entry the credential holds names, a credential whose scopes lack the
product action, or a path tenant the credential holds that no scope entry's
tenant pattern admits. That is the
reply an unentitled caller gets for a real class, so the status no longer says
whether a product class exists (R5-CP17-F01). It holds at the minimal
(default) and reasoned disclosure levels; at the full level the body names the
internal cause.

- **Unchanged:** no credential, or one the auth hook does not recognize, is
  `401 unauthenticated`. A credential with no tenant, a path tenant the
  credential does not hold at all (checked before the scope mapping), and a
  class outside the credential's product roster are `403`. An allow the gate
  cannot mint from is `503`. A partial question, malformed `parameters`, or
  an `asked_at` with no UTC offset is `400`; an `asked_at` that does not
  parse as a date-time is `422`. Every other route answers the authorizer's
  deny `403 request-unauthorized`.
- **Recorded:** the deny is on the Control Plane audit log with the axis that
  failed. The replay record carries the cause `unauthorized`, the error code
  `tenant-unauthorized` (the same code whichever axis failed) and the
  authorization decision id. It does not name the axis.
- **Migration:** a client that read `403` from the product route for any of
  these denies (an unknown class, a credential lacking the product action, or
  a tenant the credential holds that its scope entries do not admit) now
  reads the `subject-unavailable` refusal. A path tenant the credential does
  not hold at all is still `403`.

### 2. Approval transports composed into a `WorkflowEngine`

A `WorkflowEngine` binds its Control Plane into its HITL transport at
construction through `bind_approver_eligibility(control_plane)`, and refuses,
with `WorkflowWiringError`, a transport that offers no such method. The
reference `InMemoryHitlTransport` then refuses an `approve` or `reject` on an
approval-gate event that names an approval policy, by a principal the policy
does not admit or by the requester, at `submit`, before anything is recorded
(`ApproverNotEligible`; `approver-not-eligible` at the HTTP and MCP doors).

- **Migration for a custom transport composed into an engine:** offer
  `bind_approver_eligibility(control_plane)`, and at `submit` judge every
  `approve` or `reject` on an approval-gate event that names an approval
  policy against each bound plane with
  `ccf.hitl.transport.check_approver_eligibility`, before recording it. The
  engine cannot see whether a transport that offers the method judges
  anything, and no conformance test checks it. The method is not part of
  `HITLTransportProtocol`; a transport used without an engine does not need
  it.
- **Not covered:** `annotate` and `override`; approval-gate events that name
  no policy; a verdict recorded while no event is under the gate's key; a
  verdict on a non-gate event, such as an escalation, filed under the gate's
  key (follow-ups 1 and 2 below).

### 3. MCP artifact server: confidentiality rules (SEC-020 designs 1.1, 1.2, 1.3)

These apply only where the MCP artifact server is deployed.

- **Versioned-URI resolution (1.1).** For a class the server declares under
  `ReplayMint`, resolution goes through the governed read: an admitted
  principal gets the address, every other caller gets one recorded refusal,
  the same for a filed and an unfiled URI. The client raises
  `ArtifactResolutionRefused`. Nobody resolves a query pin, an admitted child
  contract or a child question over MCP.
- **Client-lane read-back (1.2).** A tenant's own client-lane filing decides
  its client-lane reads, for every principal of that tenant. Record-shaped
  bytes and bytes not at their address still take the governed read.
  Disclosed, not closed: writing bytes that are already stored is slightly
  faster than writing new bytes.
- **Erasure door over MCP (1.3).** The door names and judges every address
  through the server's two door tools and reads no requester-facing resource.
  An address the tenant never filed, governed evidence that is not a record,
  and a client twin of governed evidence are all refused
  `class-unverifiable`.
- **Credential:** the erasure door's MCP credential needs the action
  `artifact.subject.match` on the resource `artifact.subject.match`, for one
  tenant, as an authenticated bearer; the server's `ErasureTrust` must hold
  that tenant's `ErasureAuthority`, whose door key signs each query. Without
  the grant, every address is refused, ordinary client filings included.
- **Upgrade order:** upgrade the artifact server first, or with its clients.
  Until the erasure door's client is upgraded, submit no erasure request
  through it: an older door client against an upgraded server admits a
  request naming a client twin of governed evidence (measured). A new door
  client against an older server refuses every address (measured), so it
  fails closed. An older `McpArtifactStore` client resolving a governed URI
  that an upgraded server refuses gets `McpServerUnreachable` instead of the
  typed refusal (measured; nothing leaks). "Or with its clients" comes from
  the committed migration line and is safe because a new door client against
  an older server fails closed.
- **Erasure completion over MCP:** an erasure over the MCP-backed store
  reaches approval and no further, before and after this release: the
  artifact server's only write tool refuses the door's approval as the wrong
  kind (follow-up 6). Complete erasures through an in-process store.

## Fixed

- The HTTP product door's class-existence oracle (R5-CP17-F01), as above.
- An ineligible principal wedging an approval gate while the event the
  transport selects under the gate's key (its claimed event, otherwise the
  oldest queued one) is the gate's own approval-gate event, on an
  engine-composed reference transport.
- SEC-020's closing gate: its 21 failing cases (three at MCP versioned-URI
  resolution, eighteen on write-then-read) pass.

## Still open

- **SEC-020 stays open.** Green CI is not closure: the 21 cases do not test
  its other documented limitations, which are listed in the packet's
  section 5 and in `public/how-to/security-and-deployment.md` §4.12.
  SEC-020 closes only on Dave's ruling. SEC-009's erasure claim stays open
  until it is verified.
- SEC-001 (durable approval identity across stores, design 1.4's remainder),
  SEC-013's stated limits, SEC-027, SEC-029, designs 1.5 and 1.6, and the
  rest of the packet's section 5 list.

## Follow-up items (recorded, not built)

Exact conditions are in the packet's section 5.

1. **Late verdict** (`D-IMPL-366` H2, unchanged): a verdict recorded while no
   event is queued or claimed under the gate's key is not judged for
   eligibility, never becomes authority, and an opposite one holds the gate
   as a conflict.
2. **A non-gate event under a gate's key** (`D-IMPL-366` G6 (a),
   unchanged): a verdict recorded against an escalation (or other non-gate)
   event a deployment filed under the gate's own key is not judged, and an
   opposite one holds the gate.
3. Source docstrings that still describe pre-batch behavior (the delivered
   wheel is fixed at `01fc424d`).
4. The authoring Standard's `403` row for "principal not entitled".
5. No conformance test for a custom transport's eligibility judgment; the
   door paths' uniform "cannot verify" is uniform in bytes, not in server
   work (timing not measured).
6. An erasure over the MCP-backed store does not complete (found while
   documenting; the same before this release).
