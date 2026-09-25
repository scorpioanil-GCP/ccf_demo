# D-IMPL-345 — design: a replay reference dereferences to exactly what the serve was allowed to disclose, for exactly the principal it was served to

**Status: DESIGN DELIVERED (2026-09-20) on `d-impl-345-design`, awaiting the
implementation GO. Documentation only — no SDK, runtime, example or test code
changed; the CP-17 candidate `f5e22e6b` is untouched.** Design baseline
`main @ f5e22e6b` (`origin/main` = `main` = `f5e22e6b`, verified before the
fork). The decisions of record are `docs/DECISIONS.md` `D-IMPL-345` (OPEN —
DESIGN, 2026-09-20, from the CP-17 close-panel finding `S-01`), `D-IMPL-253`
Q17/Q19/Q27 and amendment 2 (4), `D-IMPL-254`, `D-IMPL-258` (2)/(3) and its
applied reading, `D-IMPL-260` (2), `D-IMPL-129`, `D-IMPL-128`, `D-IMPL-73`,
`D-IMPL-67`, `D-IMPL-26`, `D-IMPL-23`, `D-IMPL-22`.

**Decision id, verified:** `docs/DECISIONS.md` carried no `D-IMPL-345` entry
before this design; its last footer read *"Next free decision id:
`D-IMPL-345` (unchanged)"*, and the three 2026-09-19 mentions of the id listed
it only among things not authorized during release qualification. The entry
this design opens is `D-IMPL-345`; the footer advances to `346`.

**Reviewed before delivery, twice.** A first draft of this document was put
through an adversarial review (five refuting lenses and a completeness critic,
each grounded in the tree and executing where that settled a claim);
twenty-one findings were accepted and folded in, and the two that mattered
most are named where they bit (§4.3 hold 3's reader; §4.4's `request`
member). The revised draft went through a second round (three lenses, one
critic) that found the four-hold mechanism sound and the document around it
wrong in three places — the comparator the proof relied on could not pass on
a correct implementation; three absence rows were distinguishable at `full`
for classes whose addresses a prober can compute; the trail claimed for an
allowed read did not name the read — all folded in below, none re-reviewed.
A design that hides the defects its own reviews found would be the thing
this project refuses everywhere else. One finding outside 345's scope is
returned separately (§1, `S-02`).

**The problem statement, as ruled (Dave, 2026-09-20, verbatim):** *"The HTTP
product door authenticates the bearer but the replay/artifact dereference path
does not enforce the same principal/grant boundary as the governed serve."*
Measured consequences: *"an ungranted principal receives a minimal withheld
shell, then dereferences its replay reference and learns the withheld
cause/tenant; a different entitled principal who knows another principal's
record address can read that principal's record/evidence; artifact PUT is
bearer-authenticated but not grant-authorized. The first two violate the launch
contract. The third remains separately governed by D-IMPL-73 unless the design
establishes that it cannot be cleanly separated."*

**The contract this design must satisfy (Dave, verbatim):** *"The
authorization decision must be held to the same authenticated principal and
applicable product grant that governs serve."* Required outcomes: *"A
withheld/minimal-disclosure serve remains withheld when its references are
dereferenced. Principal A cannot read Principal B's replay record merely by
knowing its address. Principal A cannot use an artifact address to bypass the
disclosure boundary. An authorized principal can still dereference evidence it
is entitled to inspect. Unknown/nonexistent addresses do not become an
existence oracle through differing unauthorized responses."* And the fence:
*"Do not solve this by hiding addresses, removing replay references, weakening
CP-17's HTTP tests, or deleting evidence."*

Every citation below is a `file::symbol` that resolves on `f5e22e6b`; a
handler, a method or a nested function is named in prose beside the
module-level symbol that owns it. This document does what the 2026-09-20
instruction asked and nothing more: it designs HTTP authorization for
replay-record GET and artifact GET, answers the five design questions, fixes
the disclosure matrix, determines PUT's scope, and lays out the proof — it
changes no code and opens no other work.

---

## 1 · The defect, as measured

Reproduced on the CP-17 candidate's own HTTP door
(`examples/cp-17-mnpi-wall-enforcement/server/serve.py::http_app`, four
credentials, the live estate; close-panel scratch `q2_attack3.py`, re-run by
hand 2026-09-20):

1. **Self-dereference of a withheld cause.** `PRIN-KYC-004` (a recognized
   bearer with no grant) asks `GET /product/cp-17-demo/cib.mnpi-wall/1.0.0` →
   `404`, body `{kind: subject-unavailable, refusal: {disclosure: minimal,
   fields: {cause: "undisclosed", error_code: "undisclosed"}, replay_reference:
   ccf-artifact://cp-17-demo/…@a12216…}}`. The **same bearer** then asks
   `GET /replay/resolutions?uri=<that reference>` → `200` with the whole record:
   `assembly_refusal.detail = "no entitlement entry for principal
   'PRIN-KYC-004' under tenant 'cp-17-demo'"`, `fields.cause = "unauthorized"`,
   `fields.error_code = "principal-not-entitled"`. The disclosure step
   (`src/ccf/products/disclosure.py::disclose`, `D-IMPL-253` Q27) is undone on
   the same door one round-trip later. (The tenant name in the reference URI
   itself — `ccf-artifact://<tenant>/…` — is the addressed tenant carried at
   every level by design and is not the leak; the record behind it is.)
2. **Cross-principal record read.** Given the banker's record address (the
   `X-CCF-Replay-Ref` header of the banker's own serve), the analyst bearer and
   the KYC bearer ask `GET /replay/decisions?content_address=…` and
   `GET /artifact/<address>` → `200` with the banker's record:
   `perspective_conditioning.principal_id = PRIN-COV-001`, the subject LEI, the
   product address, and 47 class-prefixed `touched_entities` (4
   `deal_engagement://…`, 42 `interaction://…`); then `GET /artifact/<pin>` for a
   `graph_query_sequence` member → the banker's pinned traversal query (`seeds`,
   `allowed_entities`). The analyst learns that the bank holds deal engagements
   on the issuer — the fact the wall exists to keep from the analyst.
3. **Bearer-only write.** The KYC bearer `POST /artifact` with a body naming
   `tenant_id: cp-17-demo` and `artifact_class: ccf.replay-record` → `200`; the
   analyst reads it back. Products are never filed
   (`src/ccf/products/resolver.py::GovernedResolver` retains child contracts
   only), so payload bytes did not cross; the write is nonetheless unbounded.
4. **Two more reads the review of this design measured, on the shipped test
   app.** `GET /artifact/.artifact-names.json` → `200` with the file store's
   entire naming index (every `tenant/class/name → [addresses]`) — a
   cross-tenant enumeration of every record and pin address, to any bearer.
   And in-process, `src/ccf/artifacts/file_store.py::FileArtifactStore` reads
   `root / content_address` with no shape check on the address: `get` with a
   traversal string returned the host's `/etc/hostname`. The HTTP router
   rejects an encoded slash in the path parameter (measured `404`), so the
   traversal is not reachable over this door; the index read is. **345 closes
   both over HTTP** (§4.3: the address must be 64 lowercase hex before the
   store is touched; the index is not a record and is withheld). **The store's
   own traversal is returned to Dave as `S-02`**, a separate SDK finding: it
   sits in `src/ccf/artifacts`, is reachable by every caller of `get` including
   the MCP artifact blob resource
   (`runtime/ccf_runtime/mcp/artifact_server.py::build_artifact_server`),
   which 345 must leave untouched, and its repair belongs in the store.

**The failing paths, symbol by symbol.**

- `runtime/ccf_runtime/http_api/app.py::create_app` builds one router-level
  dependency, `_require_grant`, which calls the bound
  `runtime/ccf_runtime/http_api/auth.py::HttpAuthProtocol` hook, answers `401`
  when no `runtime/ccf_runtime/mcp/auth.py::TokenGrant` comes back, and stashes
  the grant on `request.state.token_grant`. It decides nothing. The `/replay`
  and `/artifact` routers are mounted with that dependency and **nothing
  else**: `replay.build_router(deps)` and `artifact.build_router(deps)` receive
  no entitlement source, no perspective resolver, no refusal recorder. Only the
  product router (`runtime/ccf_runtime/http_api/routes/product.py::build_router`)
  receives the three governance seams `create_app` already holds as keyword
  arguments (`product_entitlement`, `perspective_resolver`,
  `refusal_recorder`).
- `runtime/ccf_runtime/http_api/routes/replay.py::build_router` registers
  `decision(content_address)` and `resolution(uri)`. Neither takes the
  `Request`, so neither can read the grant; each calls
  `src/ccf/replay/engine.py::resolve_artifact` /
  `src/ccf/replay/engine.py::resolve_artifact_at_uri` and returns the **whole**
  `src/ccf/replay/record.py::DecisionReplayRecord` through
  `runtime/ccf_runtime/http_api/routes/__init__.py::canonical_response`. Absence
  is `HTTPException(404, detail=str(ReplayUnresolvable))` — FastAPI's
  `{"detail": <prose>}`, not the governed shell — so presence and absence are
  already told apart by status class, body schema and message text, three of
  the six leak channels `D-IMPL-253` amendment 2 (4) names. Bytes at a valid
  address that are **not** a record raise pydantic's `ValidationError` out of
  `resolve_artifact` uncaught (measured through the test app): a `500`, the
  status-class channel again.
- `runtime/ccf_runtime/http_api/routes/artifact.py::build_router` registers
  `get(content_address)` — raw stored bytes of **any** class at any address,
  no hash re-verification, no header, `404` with the store's prose on
  `src/ccf/artifacts/protocol.py::ArtifactNotFound` — and `put(request)` over
  `runtime/ccf_runtime/http_api/routes/artifact.py::ArtifactPutRequest`, whose
  body-supplied `tenant_id`, `artifact_class` and `name` are forwarded to
  `src/ccf/artifacts/protocol.py::ArtifactStoreProtocol` verbatim and compared
  with nothing. Because the store is content-addressed and tenant-agnostic on
  read, `GET /artifact/<address>` is a strict superset of
  `GET /replay/decisions?content_address=<address>` for a record's bytes.

**What the recorded posture already says, and what it does not.**
`runtime/ccf_runtime/http_api/app.py::AUTH_POSTURE_SENTENCE` (the `D-22`
honesty sentence, byte-pinned and thrice affirmed unchanged) describes the
`auth=None` construction; `D-IMPL-73` rules the insecure-default warning and
its single suppression kwarg and nothing else; `D-IMPL-129` rules that the MCP
Experience tool `get_replay_record` ships *authenticated and not entitled*
because `src/ccf/products/entitlement.py::ProductEntitlementPolicy` *"says
nothing … about replay records"*, and names *"a concrete harm"* as the trigger
for reopening. None of the three records that a minimal-disclosure shell is
self-dereferenceable over HTTP by the principal it refused, or that a record
address is a read key for any bearer; `D-IMPL-253` Q27 rules the opposite
posture — *"retain richer internal/replay cause only where policy permits"* —
and no policy step exists on the read. `S-01` is the concrete harm `D-IMPL-129`
named, on the HTTP door.

---

## 2 · The invariant, locked

> **A replay reference dereferences, over a door, to exactly what the
> determination it names was allowed to disclose, and only for the principal
> it was determined for.** Retrieval of a record is itself a governed
> determination: authenticated, authorized against the same principal and the
> same product grant that governed the serve, disclosed at the principal's own
> level by the door's reader — the reader that disclosed the serve wherever
> resolver and door hold one recorder, which the paved road guarantees — then
> delivered. Below `full`, an unauthorized dereference and a dereference of
> nothing are consumer-observationally equivalent; at every level, a
> dereference of nothing and a dereference of bytes that are not a readable
> record are one outcome.

This is `D-IMPL-254` (*Determination → Authority → Disclosure → Delivery*)
applied to the read path, where today only Delivery runs. Three things stay
distinct, stated once so no section below blurs them:

| concern | what 345 does to it | owner today |
|---|---|---|
| **Replay correctness** — whether a record can be reconstructed, and to what | **nothing.** `src/ccf/replay/engine.py::replay` and `src/ccf/replay/engine.py::replay_refusal` are not touched; record bytes, record identity, product identity, `D-IMPL-342` retained evidence, `D-IMPL-344` admitted-child retention and `D-IMPL-341` expiry are read by 345 and never written | `src/ccf/replay` (identity-free by invariant: `tests/invariants/test_mcp_role_separation.py::test_replay_feeds_the_recorded_perspective_and_resolves_none`) |
| **Replay visibility** — who may *retrieve* a record or an artifact over HTTP | **this design.** One governed step in the delivery boundary, called by the two routes, which encode what it returns | `runtime/ccf_runtime/authz/delivery_boundary.py` |
| **Write authority** — who may file an artifact over HTTP | **unchanged** (§7): PUT's grant-authorization is unruled today; Dave's ruling keeps it under `D-IMPL-73`'s posture; the one coupling with GET is named and deferred with it | `runtime/ccf_runtime/http_api/routes/artifact.py::build_router` |

---

## 3 · Question 1 — what authority is available at dereference time

### 3.1 At the request

- The verified identity is `runtime/ccf_runtime/mcp/auth.py::TokenGrant` —
  `client_id` and `scopes`, nothing else: no tenant, no role, no product grant.
  On HTTP it is read through `runtime/ccf_runtime/http_api/grants.py::grant_from_request`.
- The seams `create_app` already holds: `product_entitlement`
  (`runtime/ccf_runtime/authz/product_entitlement.py::ProductEntitlementSourceProtocol`
  — `authorize(grant, tenant, product_class, role)` returning a
  `src/ccf/products/entitlement.py::ProductEntitlementGrant` or raising
  `runtime/ccf_runtime/authz/product_entitlement.py::ProductEntitlementRefused`,
  audited either way), `perspective_resolver`, and `refusal_recorder`
  (`src/ccf/products/resolver.py::RefusalRecorderProtocol`, whose one method
  is `record`).
- **The reader that disclosed the serve.** The level of every shell the door
  has ever returned was chosen by the **recorder's own** `disclosure_level_for`
  callable under the **recorder's own** tenant —
  `src/ccf/products/resolver.py::ReplayRefusalRecorder` reads
  `self.disclosure_level_for(tenant=self.tenant_id, principal_id=…)` inside
  `record`. That callable is not on `RefusalRecorderProtocol` and is not
  necessarily the runtime source's method: in CP-17 the recorder is
  `opened.refusal_recorder`, whose reader is `src/ccf/products/resolver.py::_disclosure_reader`
  over the product's Control Plane, while the door's entitlement source is the
  runtime `runtime/ccf_runtime/authz/product_entitlement.py::ControlPlaneProductEntitlementSource`
  — two reader implementations over one registry in the shipped example, and
  a recorder built with its default reader answers `minimal` regardless of any
  policy. The review of this design's first draft found hold 3 (§4.3) reading
  the level through the *source* under the *record's* tenant; that is a
  second reading on a different object under a different key, and it would
  hand a whole record to a principal whose serve had been disclosed at
  `minimal` by the recorder. **The dereference must read the level through the
  same callable, under the same tenant, that disclosed the serve.** §4.2 says
  how it reaches it. One qualification, measured: that is *the same* reader
  only when the resolver and the door hold **one** recorder — the paved
  road's shape (`D-IMPL-343`; `OpenedProduct` hands the door its own
  `refusal_recorder`, as CP-17 does). A resolver-side refusal returned as a
  value is rendered by the product route exactly as the *resolver's* recorder
  disclosed it, and `create_app` receives an opaque `product_resolver` it
  cannot check shares the door's recorder; under hand-wired two-recorder
  composition hold 3 reads the *door's* reader, which is the reader the door
  itself discloses with. That residual is named in §9.2 and is not reachable
  in the tree (every shipped composition is one-recorder).
- `runtime/ccf_runtime/http_api/dependencies.py::ApiDependencies` carries the
  `artifact_store` and the `control_plane`.

### 3.2 On a replay record — present on every generation

`src/ccf/replay/record.py::DecisionReplayRecord` retains, on every record
ever filed (these members are required, not hash-transparent sentinels):

| binding | field | note |
|---|---|---|
| recorder tenant | `tenant_id` (and `context_fabric_snapshot.tenant_id`) | the **deployment** tenant the recorder was bound to (`ReplayRefusalRecorder` `tenant_id`) — the tenant that *disclosed* |
| decided tenant, boundary denials | `assembly_refusal` → `src/ccf/products/refusal.py::ResourceRequestIdentity` `tenant_id` | the tenant the caller *addressed*, which the entitlement source decided under (its key is derived from the `tenant` argument, *"never from any deployment tenant a door happens to hold"*); present only on delivery-boundary denials |
| principal | `perspective_conditioning.principal_id` (`src/ccf/replay/record.py::PerspectiveConditioning`) | on a door this is `grant.client_id`, held equal by `runtime/ccf_runtime/authz/product_entitlement.py::entitled_perspective` (`D-IMPL-67`) |
| role | `perspective_conditioning.role` | the entitled role for a serve; the decided-against role or `no-role-resolved` (`src/ccf/replay/record.py::NO_ROLE_RESOLVED`) for a boundary denial |
| kind | `content_generation_path.product_content_address` vs `assembly_refusal` | served vs refused is decidable from dimension 5 alone (`src/ccf/replay/engine.py::_record_kind`) |

and, **not on every generation**:

| binding | field | present on |
|---|---|---|
| product class and lane | `content_generation_path.request.schema_name` / `.schema_version` (`src/ccf/replay/record.py::ContentGenerationPath` `request: ProductRequest \| None`) | served records whose caller passed a request (15.5-13 onward); `None` on delivery-boundary denials (`govern_*` pass no request) and on older records |
| product class and lane, refusal path | `assembly_refusal` → `src/ccf/products/refusal.py::RequestIdentity` `product_id` / `product_version` | every refusal record from 24.6-07 onward (the envelope member is required); absent on the legacy `ProductRequestViolation` block that predates it |
| disclosure posture at determination | `content_generation_path.disclosure_decision` (`src/ccf/products/disclosure.py::DisclosureDecision`: level, policy pin, withheld) | refusal records from 24.6-08 onward; the sentinel on served records |
| the entitlement pin | `policy_bindings.bindings` | boundary denials pin the `ProductEntitlementPolicy` version that decided; an ordinary serve pins **no** entitlement policy |

Conclusion for records: **the principal and the role serve was decided on
are retained on every record; the tenant serve was decided under is
`record.tenant_id` for a resolver-side determination and
`assembly_refusal.resource.tenant_id` for a boundary denial; the product class
is recoverable on every record written since 24.6-07 (refusals) or with a
request (serves).** No new durable metadata is needed to authorize a record
read; §9.1 states what happens to the records on which the class is not
recoverable. One assumption this rests on, stated rather than assumed: a
deployment keeps **one principal namespace** across its doors and its
in-process writers — `client_id` on a bearer and `principal_id` on a
`Perspective` are the same vocabulary, as `D-IMPL-67` already requires of the
doors. A deployment that lets an HTTP `client_id` coincide with an unrelated
in-process principal string has broken that before 345 reads it; the
structural binding of identities is `D-IMPL-15`/`D-IMPL-21` territory. A
second, smaller assumption: on a resolver-side refusal record the decided
tenant equals `record.tenant_id` because the recorder was bound to the fabric's
tenant — true by construction on the paved road
(`src/ccf/products/resolver.py::build_governed_resolver` falls back to a
recorder bound to `fabric.tenant_id`, and served records cannot cross
tenants), and only a hand-wired deployment that hands the resolver a recorder
bound elsewhere could break it. Named, not defended.

### 3.3 On the other artifact classes

Every `ArtifactStoreProtocol.put` site in `src/` and `runtime/`, and what the
bytes bind to. Every class is bound to a tenant **at put time through the
naming index** (`tenant/class/name → addresses`), which `get` never consults;
the column says what the *bytes* carry:

| class (deployment vocabulary in italics) | filed by | tenant in the bytes | principal | product class |
|---|---|---|---|---|
| *replay record* | `src/ccf/replay/serve.py::ReplayWriter` under `record.tenant_id`, name `graph_snapshot_id` | yes | **yes** | recoverable (§3.2) |
| *graph-query pin* | `src/ccf/replay/serve.py::QueryPinWriter` under `record.tenant_id`, name = content hash | `GraphQuery.tenant_id` | no | no |
| `ccf.admitted-child-contract` | `src/ccf/products/resolver.py::GovernedResolver` (`D-IMPL-339`/`344`) | `tenant_id` on the contract | no | `schema_name` on the contract |
| `ccf.child-question` | `src/ccf/products/child_resolver.py` (`D-IMPL-342`-B), under the consumer gate's tenant | no | no | no |
| `ccf.admission-record` | `src/ccf/peering/admission.py` | yes | no | no |
| `ccf.workflow-trace` | `runtime/ccf_runtime/workflow/engine.py` | no | no | no |
| anything | `POST /artifact`; the MCP artifact server's put tool | caller's claim | no | no |

The store itself knows nothing per address: `src/ccf/artifacts/protocol.py::ArtifactStoreProtocol`
exposes `put / get / exists / resolve_uri`; `get` and `exists` take the
content address alone; `src/ccf/artifacts/file_store.py::FileArtifactStore`
holds *"the canonical bytes and nothing else — no envelope, no metadata
sidecar"*, its naming index runs name → addresses only, and one address can be
registered under several tenants (byte-identical content). `src/ccf/artifacts/protocol.py::ArtifactRef`
exists at put time and is not persisted. `src/ccf/artifacts/protocol.py::parse_artifact_uri`
yields (tenant, class, name, version) structurally from a versioned URI —
a **claim carried by the string**, not a fact about the bytes.

Conclusion for non-record artifacts: **only the replay record carries a
principal.** A per-artifact, principal-scoped authorization cannot be
evaluated from retained metadata for any other class; a tenant-scoped one can
be evaluated for some classes and for none of them reliably (the bytes may be
a caller's own dict). The record is therefore the only authorization root the
tree retains, and §4.4 builds on that fact rather than inventing a second one.

### 3.4 What is deliberately not added

No new retained member. Adding a binding to a stored record type is
constrained to a sentinel-defaulted, hash-transparent member (`D-IMPL-243`
generation boundaries; the `D-IMPL-340`/`342` precedent), and nothing in §4
needs one: the serve-time tuple is already on the record. Duplicating the
grant or the product envelope onto records or artifacts *"merely for
convenience"* is refused by the instruction, and it would also move new
records' identity for no authorization gain. No sidecar index on the store:
a reverse map address → (tenant, class, name, principal) is a new Protocol
obligation on both shipped store implementations and a migration of the
naming index; §4.4 shows it is not needed for the records-only reach 345
delivers.

---

## 4 · Question 2 — where authorization lives, and the rule

### 4.1 Owning layer

`runtime/ccf_runtime/authz/delivery_boundary.py` — the module that already
owns the three governed steps the product door calls
(`runtime/ccf_runtime/authz/delivery_boundary.py::govern_entitlement`,
`runtime/ccf_runtime/authz/delivery_boundary.py::govern_absence`,
`runtime/ccf_runtime/authz/delivery_boundary.py::govern_raised_refusal`) and
the construction-time guard `runtime/ccf_runtime/authz/delivery_boundary.py::recorded_boundary`.
Not the routes (they encode, they do not decide — the product-route discipline
pinned by `tests/http_api/test_product_entitlement.py::test_the_route_imports_the_seams_rather_than_re_declaring_them`),
not the FastAPI handlers, and not `src/ccf/replay` (identity-free by two
invariant pins: no `principal_id` parameter below the door, no `ccf_runtime`
import). The MCP doors are untouched (§6.3).

### 4.2 One governed step for both routes

One new function, **`govern_dereference`**, beside the three existing ones:

```
govern_dereference(
    *, grant: TokenGrant, reference: DereferenceRequest,
    store: ArtifactStoreProtocol,
    entitlement_source: ProductEntitlementSourceProtocol,
    refusal_recorder: DisclosingRecorderProtocol,
    audit_log: AuditLog,
    surface: str, address: str,
) -> DereferencedEvidence | RefusalEnvelope
```

- `DereferenceRequest` names *what was asked*, verbatim: `content_address: str`
  **or** `uri: str`, and `wants: Literal["record", "bytes"]` (`/replay/*` asks
  for a record; `/artifact/*` asks for bytes). Nothing else is an input; the
  caller supplies no class, no role, no tenant beyond what a URI string
  carries.
- `DereferencedEvidence` carries the resolved `DecisionReplayRecord` (record
  asks) or the resolved bytes (bytes asks, records only — §4.3), exactly as
  `resolve_artifact` / the store handed them over, byte for byte; the routes
  render one or the other with `X-CCF-Content-Address` as today.
- `DisclosingRecorderProtocol` is a narrow structural Protocol **declared in
  `runtime/ccf_runtime/authz/delivery_boundary.py`** (not under
  `src/ccf/products`, where a member spelled with a `principal_id` keyword
  would trip the role-separation invariant): `record` (the existing
  `RefusalRecorderProtocol` method) **plus** `disclosure_level_for`, typed as
  the same `Callable[..., tuple[DisclosureLevel, ProvenanceSource | None]]`
  attribute `ReplayRefusalRecorder` carries, and `tenant_id: str` — the two
  members the reference recorder already has as fields. This is how hold 3
  reads the level *through the recorder that disclosed the serve, under the
  recorder's tenant* (§3.1), not through the entitlement source and not under
  the record's. No change to `RefusalRecorderProtocol` itself.
- `audit_log` is the door's Control Plane audit log
  (`ApiDependencies.control_plane.audit_log`), the one audit plane; §4.4 says
  what every dereference appends to it.

Both routes gain the `Request` parameter and call `grant_from_request`, then
this one step, then encode: a `RefusalEnvelope` → the shared renderer,
otherwise the evidence. Neither route catches `ProductEntitlementRefused`,
mints a record, chooses a level, or reads a clock. The shared renderer is the
product route's `_refusal_response` body — `{kind, refusal_type, refusal}`,
status from `runtime/ccf_runtime/http_api/refusal_status.py::status_for` —
moved to `runtime/ccf_runtime/http_api/routes/__init__.py` under a **new**
name (`governed_refusal_response`; the module already exports a different
`refusal_response(refusal, *, status_code)`, and the name is not reused),
with `product.py` keeping `_refusal_response` as a one-line alias so that the
sabotage control anchored on the literal call text
(`tests/invariants/test_delivery_boundary_replay.py::_plant`, which asserts
the anchor `return _refusal_response(decided)` appears exactly once) holds,
and that invariant gains the two new call sites as anchors in the same
change.

The two routers gain keyword seams — `replay.build_router(deps, *,
entitlement_source=None, refusal_recorder=None)` and the same for artifact —
and `create_app` threads what it already holds: `product_entitlement` and
`refusal_recorder`. The product router has three seams; the evidence routers
need two (no perspective is resolved on a read: the record carries the role).
Construction posture, in order:

- `product_entitlement` unbound → the evidence routers are mounted ungoverned
  and answer `503 product-door-ungoverned` (the product route's constant,
  `runtime/ccf_runtime/http_api/errors.py::ERROR_PRODUCT_DOOR_UNGOVERNED`) on
  every dereference (R-1).
- `product_entitlement` bound and the recorder does not satisfy
  `DisclosingRecorderProtocol` → a **sibling** guard, `disclosing_boundary`,
  refuses to build with the same `UnrecordableDeliveryBoundaryError` shape
  `recorded_boundary` raises for a recorder that cannot record (`D-IMPL-256`
  (2); `D-IMPL-253` §4, quoted from the 24.6 rulings file at
  `.planning/phases/24.6-sdk-gap-phase-the-delivery-boundary-realized-refusal-as-a-go/24.6-RULINGS.md`:
  *"unauthorized and nonexistent requests must not diverge merely because the
  door is misconfigured"*). A sibling rather than a widening of
  `recorded_boundary`, because that one function is shared with the two MCP
  builders, which 345 leaves byte-for-byte unchanged (§6.3): a record-only
  recorder stub passes `recorded_boundary` today and must go on passing it
  there. Every recorder in the tree that a `create_app` caller binds is a
  `ReplayRefusalRecorder` and conforms.

### 4.3 The rule — four holds, in order, all from retained state

**Address shape first, before the store is touched.** A content address that
is not exactly 64 lowercase hexadecimal characters is *absence* (nothing can
be stored there; the naming index and any path are not addresses). A URI is
parsed by `parse_artifact_uri` first: `@latest` stays the `409` it is today
(`src/ccf/artifacts/protocol.py::MovingTargetRefused` is raised structurally
before any lookup and reveals nothing); any other parse failure is *absence*.
**On the URI leg the holds run before the naming index is consulted.** The
version segment is the content address; the boundary shape-checks it, reads
the bytes at it, and runs holds 1–3 on the record — and only *after* they
pass does it verify, through `resolve_uri`, that the URI's (tenant, class,
name) triple registers that address, mapping a mismatch to *absence*. The
order matters: `src/ccf/artifacts/file_store.py::FileArtifactStore` resolves a
URI only under its exact triple, so consulting the index first would let a
caller who holds an address confirm the tenant, class and name it is
registered under by varying the segments and watching `cause` at `full`.
With the holds first, a caller that may not read the record learns nothing
from any segment.

For a **record** (the bytes at the address validate as `DecisionReplayRecord`
and re-hash to the address):

1. **Principal.** `grant.client_id == record.perspective_conditioning.principal_id`.
   Otherwise: unauthorized, and **the record's identity is not read
   further** — nothing about its principal, class, role or tenant reaches the
   read-refusal record or the shell (§4.4). This is the whole of *"Principal A
   cannot read Principal B's replay record merely by knowing its address"*,
   and it uses the member every record carries. No supervisory or auditor
   read exists in 345 (§11): a principal reads its own determinations.
2. **Product grant, re-decided now — for records that carry a product
   determination.** The product class and lane are recovered from the record
   (`request.schema_name` on a served record; on a refusal record from the
   `assembly_refusal` block, which the record holds as a JSON string and the
   boundary parses with `RefusalEnvelope.model_validate_json` — a block that
   does not validate as a `RefusalEnvelope`, the legacy shape included, is
   *class unrecoverable*, row 5; §3.2); the decided tenant is
   `assembly_refusal.resource.tenant_id` when the internal envelope carries a
   resource identity (a boundary denial), else `record.tenant_id`. With a
   class in hand, the boundary makes **the identical `authorize` call the
   serve's entitlement made** —
   `entitlement_source.authorize(grant=grant, tenant=<decided tenant>,
   product_class=<class>, role=record.perspective_conditioning.role)` —
   keyed the same way (`product_entitlement_key(tenant)`,
   `principals[client_id]`, `require_schema`, `require_role`), resolved per
   call so a revoked grant stops the read immediately, and audited by the
   source as every entitlement decision is. The deployment's perspective
   resolver is **not** re-run: the record already carries the role it
   resolved, and `entitled_perspective`'s subject-conflict check is hold 1.
   A record whose class is not recoverable is **not** dereferenceable
   (conservative; §9.1). A role of `no-role-resolved` fails `require_role`
   and is therefore withheld, which is the right answer for a product denial
   the door never resolved a role for.
   **A read-refusal record carries no product determination** and is
   recognized by **both** of its constants together — its
   `RequestIdentity.product_id` is the mechanism constant and its
   `resource.surface` is one of the two evidence tokens (§4.4); one without
   the other is row 5. Hold 2 does not apply to it — holds 1 and 3 govern it.
   That is what makes the chain in §5 readable by its own principal at
   `full`, and it is safe rather than convenient because hold 1 binds every
   record to its author: a record forged through the open write path with
   those constants (§4.5) is readable by its forger alone.
3. **Disclosure level, current, read by the recorder.**
   `refusal_recorder.disclosure_level_for(tenant=refusal_recorder.tenant_id,
   principal_id=grant.client_id)` must be `full`. Below `full`, the record is
   withheld. The reason is structural, not cautious: a record *is* the
   internal truth — dimension 5 carries the internal envelope with the true
   cause, the policy pin, the resource identity and the `DisclosureDecision`
   that withheld them; a served record carries the `D-IMPL-342` producer
   refusal members that *"the served envelope discloses nothing new at
   minimal"* about — and `D-IMPL-254` allows only the *shell* to express a
   permitted disclosure below `full`. `src/ccf/products/disclosure.py::disclose`
   withholds the same members at `reasoned` as at `minimal` for this kind
   (verified: `reasoned` permits nothing further for `subject-unavailable`),
   so there is no intermediate level at which a record could partly cross.
   There is no disclosed *view* of a record without minting bytes that do not
   hash to the record's address (`D-IMPL-26`), which is refused (§4.5). So
   the only level at which the whole record may cross is the level at which
   nothing is withheld, and `full` is by ruling *"policy-controlled"* per
   tenant and per principal (`D-IMPL-253` Q17). This hold is what makes *"a
   withheld/minimal-disclosure serve remains withheld when its references are
   dereferenced"* true for the principal it was served to — the `S-01` (1)
   case — without hiding the reference or removing it. Two notes by decision:
   a reader that *raises* on a malformed policy artifact (both shipped readers
   do, on a tenant mismatch under the key) propagates exactly as it does
   inside the product door's `record` — a deployment defect, not a governed
   outcome — and 345 does not map it. And the level is read twice on a hold-3
   denial — once here, once inside `record` when the denial is disclosed —
   with the registry free to move between the two readings; the window is
   harmless because hold 1 has already passed and only the caller's own
   record is at stake, and it is not closed because closing it would put a
   level-accepting method on the recorder that no other path needs.
4. **Delivery.** The record, byte for byte, with `X-CCF-Content-Address`.

For **`/artifact/{content_address}`** the bytes at the address are classified
first:

- they validate as a `DecisionReplayRecord` and re-hash → holds 1–4 exactly as
  above; the bytes are returned as the artifact route returns bytes today. The
  artifact route can no longer be the unguarded twin of the replay route.
- anything else — a pin, a child contract, a child question, an admission
  record, a trace, a caller's dict, the naming index — → **withheld over HTTP
  in 345**, recorded as unauthorized with the typed code
  `evidence-not-dereferenceable`, disclosed, `404` shell. §4.4 says why this
  is the honest reach and what extends it.

### 4.4 One outcome for every failure, and what the read-refusal record may say

Holds 1–3 and every absence fail into **one** external outcome, built the
way `govern_entitlement` and `govern_absence` build theirs:

- **Internal envelope.** `src/ccf/products/refusal.py::SubjectUnavailableRefusal`
  with `cause="unauthorized"` (a hold failed on a genuine record) or
  `cause="nonexistent"` (**every** other outcome: no address shape, no bytes,
  an unregistered URI, bytes that are not a record on a record ask, bytes that
  do not hash, bytes that are a pin or a child or the naming index or a posted
  dict on a bytes ask — one internal envelope, one typed code
  `evidence-absent`, one `detail` sentence, for all of them, at every level).
  The first draft distinguished those absences by code and treated divergence
  as a `409`; the second review showed why neither survives: the non-record
  classes 345 withholds are content-addressed over inputs a prober can
  reconstruct (a pin's address is the hash of its `GraphQuery`; a child
  question's, the hash of its five members), so a `full` principal that could
  tell *bytes-but-not-a-record* from *nothing* by `error_code` would learn
  that a particular traversal or question had happened — and 345 authorizes
  no reader for those bytes at any level, so the distinction has no
  legitimate consumer. The fine-grained absence reason is therefore not
  retained on the record; a divergent store surfaces to a record's owner
  through `replay()` in-process as it does today. The typed codes a hold
  failure records are `evidence-principal-mismatch`, the source's own
  `principal-not-entitled` / `product-class-unentitled` /
  `product-role-ungranted` / `product-policy-absent`,
  `evidence-class-unrecoverable`, `evidence-disclosure-withheld`; with
  `evidence-absent` they are `ERROR_EVIDENCE_*` constants declared in
  `runtime/ccf_runtime/http_api/errors.py`, exported through its `__all__`,
  hyphenated like the existing vocabulary, listed in the `345-01` fragment,
  and imported by `govern_dereference` rather than spelled.
- **`RequestIdentity` — built from what the caller supplied and nothing
  else.** `product_id` is one mechanism constant for every dereference,
  `runtime/ccf_runtime/authz/delivery_boundary.py` `DEREFERENCE_PRODUCT_ID =
  "ccf.evidence-dereference"`; `product_version=None`; `parameters =
  {"reference": <the address or URI exactly as asked>}`;
  `temporal_boundary=None`. Constant across causes for one ask — its only
  varying member is the echoed reference, which is what the caller sent and
  is the same string for every outcome of that ask. **Never the target's
  class or lane.** The first
  draft of this design put the *recovered* class on this member, and the
  review executed the consequence: `disclose` leaves `request` untouched at
  every level (*"the second is what the caller itself asked"*), so two
  shells built that way — one for an existing record, one for nothing —
  differed only at `request`, the CP-17 `_shell` comparator called them
  equal, and every control in the first draft's proof stayed green over an
  existence oracle that also named the target's product class. `D-IMPL-260`
  (2) is the ruling: authorization state must never change an identity
  field's presence *or value* in the shell. The recovered class now feeds
  `authorize` and the internal record only.
- **`ResourceRequestIdentity`.** `surface` is one of two new tokens beside
  `runtime/ccf_runtime/authz/delivery_boundary.py::SURFACE_HTTP_ROUTE`
  (`SURFACE_HTTP_REPLAY_READ = "http-replay-read"`,
  `SURFACE_HTTP_ARTIFACT_READ = "http-artifact-read"`); `address` is the route
  path plus the reference as asked; `tenant_id` is **the recorder's tenant**
  for every outcome (an address ask carries no tenant and an absent target
  has none; a URI's tenant segment is already inside `address`);
  `determined_at` from the source's clock. This member is normalized below
  `full` by `disclose` and crosses nothing.
- **Dimension 4 of the read-refusal record.** `Perspective(principal_id=
  grant.client_id, role=NO_ROLE_RESOLVED)` — the caller, and no role, because
  no perspective is resolved on a read. Dimension 2:
  `ResolutionNotApplicable(reason="no-resolution-step")` — one of the two
  tokens of the closed `src/ccf/replay/record.py::ResolutionNotApplicableReason`
  literal, and the true one: there is no resolver step on this path. Policy
  bindings: the entitlement pin the source returned when hold 2 ran, else
  none.
- **What the read-refusal record retains about the target.** When the target
  was the caller's own record (holds 2 or 3 failed): the target's recovered
  class, lane and role, inside `detail` — the caller's own determination, at
  `full` the caller's to see. When hold 1 failed or the target is absent:
  **nothing about the target** — not its principal, class, role or tenant —
  only the reference as asked and the typed code. The ordering makes that
  structural rather than careful: on a hold-1 failure the boundary stops
  reading the record, `authorize` is never called (so the source appends no
  event and returns no pin that could land in `policy_bindings`), and the
  recorder receives only what the boundary passes. An examiner who needs to
  know whose record was probed dereferences the address in-process. This is
  the `D-IMPL-253` Q27 balance: the audit truth that a cross-principal read
  was attempted and refused is retained; another principal's identity is not
  copied into a record its prober can read at `full`.
- **One audit event per dereference, allowed or refused.** The boundary
  appends one `authz_decision` event to the door's Control Plane audit log —
  the shape the entitlement source and the HITL authorizer already write —
  with `authz_action_id` one of two new ids declared beside
  `src/ccf/authz/actions.py::ACTION_PRODUCT_RETRIEVE`
  (`ACTION_REPLAY_READ = "replay.read"`, `ACTION_ARTIFACT_READ =
  "artifact.read"`; the seam `D-IMPL-129` named for exactly this), `actor` the
  caller, `key` the reference as asked, `version` the content address
  delivered (the empty string when nothing was), `resolved` whether the read
  was allowed. This is the trail of an **allowed** read — it names *which*
  record crossed — and of a hold-2-skipped read of the caller's own chain,
  which the entitlement source's own `product.retrieve` event (fired only when
  hold 2 runs, and carrying actor, tenant, policy version and verdict but no
  address) could not be. The first draft claimed the source's event as the
  trail; the second review showed it names no address and is absent on the
  chain. Whether this event discharges the boundary's *"fulfilled or refused
  … must reach the replay writer"* sentence for reads, or a fulfilled-read
  record is wanted, is R-5.
- **Recording and disclosure.** `refusal_recorder.record(envelope,
  perspective=…, recorded_at=…, resolution=…, policy_bindings=…)` — the same
  call `govern_entitlement` makes — mints the record and returns the shell
  disclosed at the caller's level with `replay_reference` set. The routes
  render it: `404` + the canonical body. Both causes leave the door
  indistinguishable below `full` by `src/ccf/products/disclosure.py::INDISTINGUISHABLE_BELOW_FULL`
  (`detail`, `cause`, `error_code`, `policy_bindings`, `resource` withheld or
  normalized) with `request` constant across causes for one ask by
  construction. Executed by the second review on the real SDK: rows 2–8 for
  one ask, disclosed at `minimal` and at `reasoned`, render to byte-equal
  bodies once `replay_reference` is removed, and no new code, token, cause or
  reference crosses below `full`.

### 4.5 Why non-record evidence is withheld rather than authorized by reachability

The natural extension — *"a pin is readable by whoever may read a record that
names it"* — is fully expressible from retained state: a record enumerates
its evidence (`graph_query_sequence`, `child_resolutions[].child_content_address`,
`child_question_address`, `child_question_ref`), so
`GET /artifact/<pin>?via=<record>` could authorize the pin through holds 1–3
on `<record>` plus membership. It was designed and then set aside for 345,
for one reason that is not convenience: **the record it trusts can be forged
by the write path this design leaves alone.** `POST /artifact` files any
bytes under any tenant, class and name; `DecisionReplayRecord` has no
validator that could tell a door-written record from a posted one; a bearer
with a `full` disclosure grant for one class writes a "record" naming itself
as principal, that class, its granted role, and `graph_query_sequence =
[<the banker's pin>]`, then reads the banker's pinned traversal — `S-01` (2)
again, one hop longer. The reachability rule and the write rule share one
trust root, and the root is open. That is exactly the inseparability the
instruction asked to be returned rather than silently expanded (§7).

Withholding non-record classes keeps 345 separable from PUT: a forged record
can only ever be read by the principal who wrote it, and grants no reach into
anything genuine. What a principal loses is the standalone HTTP read of a
pin, an admitted child contract, a child question, an admission record or a
workflow trace — bytes the record already names and that `replay()` reads
in-process from the same store, untouched. What a principal keeps is every
evidence *the record carries*: dimensions 1–5 whole, including the touched
manifest, the query addresses, the child rows with their retained refusal
members, the disclosure decision. Nothing is deleted, hidden or renamed; the
addresses stay in the record for the day the write path is governed and the
`via` extension can trust what it reads (§10, R-3). This narrows `D-IMPL-23`'s
*"artifact get"* and `D-IMPL-22`'s `artifact inspect` to records over HTTP,
and §9.3 names that as an amendment of both entries, not a footnote.

### 4.6 What was rejected, and why

- **A disclosed *view* of a record** (strip `assembly_refusal` internals per
  the principal's level and return that): the bytes would not hash to the
  address the caller asked for, breaking `D-IMPL-26` identity on the read
  surface and inviting a second representation of the record. Refused.
- **The HITL door's shape** (`runtime/ccf_runtime/authz/protocol.py::TenantAuthorizerProtocol`
  + a new action id + a `403`): it decides *grant × tenant × action*, knows
  no principal-of-record and no product class, and its `403` is itself the
  first leak channel; `D-IMPL-258` (3) refused a `403` for unauthorized beside
  a `404` for nonexistent. `D-IMPL-129` named that shape for closing the *MCP
  agent tools*, where no record exists to bind to; for a record read the
  tighter, already-retained binding exists and is the one the instruction
  asks for.
- **A record-level authorization inside `src/ccf/replay`** (`resolve_artifact`
  taking a principal): forbidden by the role-separation pins and by the
  *"replay reconstruction semantics unchanged"* bound.
- **Reusing `govern_entitlement` verbatim**: it minds a *requested* class and
  role from the caller and resolves a perspective; a dereference has no
  requested class — the class is the record's — and no role to propose. It
  shares the source, the recorder, the shell and the renderer; it needs its
  own step because its inputs are retained state, not request parameters.
- **Reading hold 3 through the entitlement source**: rejected by the review
  for the reason in §3.1.

---

## 5 · Question 3 — the disclosure matrix

Every row is the observable at the door for a **bearer the hook recognizes**;
rows 2–8 share one shell below `full`. The `full` column states what a
`full` principal sees under this design; which of those differences are
*permitted* at `full` is R-4, because the passage that lists the members
that may differ at `full` (`detail`, `fields.cause`, `fields.error_code`) is
the orchestrator's **applied reading of `D-IMPL-258`, recorded for
confirmation**, not a ruling of Dave's, and 24.6 built the product door on it.

| # | the reference | below `full` | at `full` | the read-refusal record retains |
|---|---|---|---|---|
| 1 | authorized, existing (own record; grant holds now; level `full`) | n/a — below `full` this is row 3 | `200`, record bytes, `X-CCF-Content-Address` | no record is written for an allowed read (R-5); the source's `authz_decision` audit event is the trail |
| 2 | existing, another principal's record | `404`, shell `{kind: subject-unavailable, refusal_type, refusal: {disclosure, detail: <the one external sentence>, fields: {cause: "undisclosed", error_code: "undisclosed"}, request: {product_id: "ccf.evidence-dereference", product_version: null, parameters: {reference: <as asked>}, temporal_boundary: null}, replay_reference}}` | `404`, shell with `cause: unauthorized`, `error_code: evidence-principal-mismatch`, `resource` present (recorder tenant, surface, address) | the caller; the reference as asked; the typed code; **nothing about the target** |
| 3 | existing, own record, level below `full` — **the withheld serve's reference** | as row 2 | (not reachable at `full`) | typed code `evidence-disclosure-withheld`; the level in force and its policy pin; the target's class, lane, role in `detail` |
| 4 | existing, own record, grant no longer holds / class unentitled / role ungranted / policy absent | as row 2 | `404`, shell with the source's typed code | the entitlement policy pin that decided; the target's class, lane, role |
| 5 | existing, own record, class unrecoverable (historical shapes, §9.1) | as row 2 | `404`, `evidence-class-unrecoverable` | that no class was recoverable |
| 6 | nonexistent: address not 64-hex, no bytes, a URI whose triple does not register the address, bytes that are not a record on a record ask (pydantic `ValidationError`, `ReplayRecordKindMismatch` — all mapped, none escapes as a `500`) | as row 2 | `404`, shell with `cause: nonexistent`, `evidence-absent` | the ask; one sentence |
| 7 | existing bytes that do not hash to the address | as row 2 | **as row 6, byte for byte** | as row 6 |
| 8 | `/artifact/{address}` whose bytes are not a record (a pin, a child, the naming index, a posted dict) | as row 2 | **as row 6, byte for byte** | as row 6 |
| 9 | `@latest` in a URI | `409`, `{"detail": …}` (unchanged) | same | none — a request-shape refusal before any lookup, as today |
| 10 | `product_entitlement` unbound (auth bound or not) | `503`, `product-door-ungoverned` (R-1) | same | none — construction posture |
| 11 | no bearer / unrecognized bearer, auth bound | `401`, `unauthenticated` (unchanged) | same | none |

Rows 2–8 share status (`404`), kind, external sentence, body schema and field
presence, `disclosure` value, `request` (constant across causes for one ask;
its echoed reference is the caller's own string), and *replay-reference
behavior* (each carries a fresh reference to its own read-refusal record,
which dereferences by these same rows — a below-`full` principal following
the chain meets row 3 forever; a `full` principal reads each hop of its own
chain under holds 1 and 3 and finds only its own asks). Message text and
serialization are the same renderer's; `_refusal_response` sets no headers,
so header sets are equal. That is the six-channel equivalence `D-IMPL-253`
amendment 2 (4) defines, on the read surface. Timing is not among the six
ruled channels and 345 does not equalize it (an existing record costs a
store read, a hash, a validation and an audited `authorize` that a miss does
not; both are dominated by the record mint) — stated so it is out of scope
by decision, not by omission. The comparator a control uses is the
whole-body comparison of §8.1 — every key and value of the `refusal` object
after deleting `replay_reference`, with each body's `request` first held to
the constant shape carrying that body's own ask — which is stricter than the
CP-17 `_shell` tuple the first draft named (that tuple compares key sets and
`fields` values and would not have seen a differing `request`) and, unlike
the second draft's, can pass across two different asks.

A note on the bearer-less posture (row 10, R-1): today an unauthenticated
`create_app` answers `200` on the three evidence GETs to a caller with no
credential at all, which is the *"full authority of the injected fabric
handles"* sentence made literal. The product route already left that posture
in 24.6 — with the entitlement seams unbound or no verified grant it refuses
`503 product-door-ungoverned` rather than serve ungoverned. 345 has the
evidence routes follow the product route, for the reason `D-IMPL-253` §4
gives. The `AUTH_POSTURE_SENTENCE` constant is not touched (it describes
`auth=None`, is byte-pinned, and was affirmed unchanged three times); the
served OpenAPI description gains one appended sentence in the
`_AUTH_HOOK_LINE` manner, outside the pinned constant, naming the governed
nouns.

---

## 6 · Question 4 — replay correctness versus replay visibility

### 6.1 Unchanged, by construction

- `src/ccf/replay/engine.py::replay`, `src/ccf/replay/engine.py::replay_refusal`,
  `src/ccf/replay/engine.py::resolve_artifact`,
  `src/ccf/replay/engine.py::resolve_artifact_at_uri`: no signature, no
  behavior, no import. The boundary calls the two resolvers **as the routes do
  today** and reads the result; it adds nothing below the door.
- Record identity and product identity: no record member is added or moved;
  `src/ccf/replay/record.py::build_replay_record` is not touched; the
  read-refusal records the boundary mints are **new** records of the existing
  shape written by the existing recorder (`ReplayRefusalRecorder.record`),
  so they carry the `D-IMPL-341` sentinel where a served product would carry
  an anchor, and nothing about them changes an existing record's bytes or
  address.
- `D-IMPL-342` retained evidence (`ChildResolution` producer-refusal members,
  `ccf.child-question` artifacts), `D-IMPL-344` admitted-child retention
  (`ccf.admitted-child-contract`), `D-IMPL-341` expiry (`ttl_anchor_at`, the
  replay hold, `not-recorded`): read by nothing in 345 except as evidence a
  record names; written by nothing in 345.
- The MCP doors (§6.3).

### 6.2 What a read-refusal record is, and is not

It is a full five-dimension record of a governed *no* (`D-IMPL-253` Q13:
*"Do not create second-class replay"*), written through the one recorder the
door already holds, with dimension 1 `unread`, dimension 4 the caller and no
role, dimension 2 `no-resolution-step`, dimension 5 the internal envelope
naming the surface, the reference as asked, the typed code, and — only when
the target was the caller's own — its class, lane and role. It is not a
change to the target record, not a product, and not a new artifact class. It
does mean denied dereferences accumulate records the way denied serves do —
the unread snapshot id is a hash over (tenant, boundary instant), so under a
live clock each denial files under its own name and the naming index grows by
one key per denial, sharing a name only when instants coincide (the pinned
clocks of the test fixtures); `FileArtifactStore` rewrites the whole index
per put, so a flood of fabricated-address asks is an index-size cost; no URI
ambiguity follows either way (exact version under exact triple). A
below-`full` principal chasing its own references produces one record per
hop. That growth is the existing posture of the delivery boundary
(`govern_entitlement` writes one record per denial) and is stated here, not
hidden.

An **allowed** dereference writes no record; it appends the audit event of
§4.4, which names the reference asked and the address delivered. The
delivery boundary's own sentence — *"every governed determination that
crosses a CCF delivery boundary — fulfilled or refused — must reach the
replay writer"* — is met on the serve path because the resolver records the
fulfilled determination; on the read path there is no new determination
content to record: what is delivered *is* a record, already in the store. No
existing invariant test asserts that fulfilled determinations reach the
writer (`tests/invariants/test_delivery_boundary_replay.py` enforces that no
transport mints, discloses or catches, and that the entitlement refusal is
caught in one module), so this is a ruling, not a pin the tree already holds:
whether the audit event discharges the sentence for reads, or a
fulfilled-read record shape is wanted, is R-5.

### 6.3 MCP, stated precisely

`runtime/ccf_runtime/mcp/experience.py::ReplayRecordReaderProtocol` stays
zero-argument; the Experience tool `get_replay_record` keeps
`verified_grant()` then the seam, *authenticated and not entitled* as
`D-IMPL-129` ruled, and
`tests/crossproc/test_experience_edge.py::test_the_agent_and_replay_tools_are_authenticated_but_not_entitled_open_gap`
keeps asserting that an unentitled credential reads a record. The MCP
artifact role (`runtime/ccf_runtime/mcp/artifact_server.py::build_artifact_server`)
stays authenticated-only on its blob, presence and name resources and its put
tool — which is also why `S-02` is returned rather than folded in: the store
it reads through is the one with the traversal. The egress role and the
standard product door (`runtime/ccf_runtime/mcp/product_door.py::open_door`)
expose no replay or artifact read and are not touched. 345 therefore leaves
the two front doors disagreeing about who may read a record — the *"live
inconsistency"* `D-IMPL-129` itself recorded — deliberately, because the
instruction fixes MCP replay behavior as unchanged. §11 names the follow-on.

---

## 7 · Question 5 — artifact PUT

**Determination: PUT is technically separable from the GET authorization
this design delivers, and it stays out of 345.** Its grant-authorization is
**unruled** today — `D-IMPL-73` rules only the insecure-default warning and
its suppression kwarg, and `D-IMPL-23` names *"artifact get/put"* as nouns
without an authorization semantic; Dave's ruling keeps PUT under `D-IMPL-73`'s
posture, and this design records that posture as *authenticated when a hook
is bound, otherwise open*, which is what the tree does. The GET primitive
binds a read to the record's own retained principal, grant and disclosure
level; PUT has no record to bind to and would need a different primitive —
*grant × tenant × `artifact.put`* through the tenant authorizer, with the
body's `tenant_id` held equal to an authorized tenant rather than taken as
the caller's claim, the way `D-IMPL-67` had the HITL door derive *"the
submission principal from the verified `request.state.token_grant`"* and
treat *"a body principal conflicting with the verified identity"* as *"a
typed 4xx refusal, not an accepted claim."* Correcting GET does not require
touching `put`, `ArtifactPutRequest`, or the store's `put`; §8's controls
prove GET without a single write through the route.

**The coupling, named so it is not silently expanded.** The one GET behavior
that *would* share PUT's trust root is the reachability extension of §4.5:
authorizing non-record evidence through a record that names it trusts the
record, and an open PUT mints records. 345 withholds non-record evidence over
HTTP precisely so that no such trust is placed while PUT is open. The
reachability extension and PUT governance are therefore **one design
question** to be opened together, and are returned as R-3 rather than
folded in. Two further observations for that later entry, recorded here and
not acted on: the MCP artifact server's `put_artifact` tool takes `tenant_id`
from the client the same way; and a bearer can today file bytes under the
deployment's replay-record class and name, which cannot hijack a versioned
reference (`@latest` is refused everywhere a replay reads) but does pollute
the naming index.

---

## 8 · Proof and sabotage plan — defined before implementation

### 8.1 Where the proof lives

- **SDK-level:** a new module `tests/http_api/test_evidence_dereference.py`
  built on the `_entitled` shape of `tests/http_api/test_product_entitlement.py`
  with one deliberate difference: the recorder is bound over **the same store
  handed to `ApiDependencies.artifact_store`**, so that the references the
  door hands out resolve *through the door* (every existing HTTP entitlement
  test reads records in-process from a store the app never sees, which is why
  none of them could have seen `S-01`). Two recognized bearers with grants for
  one class at one role and a third with none; a tenant policy at `minimal`
  with a per-principal `full` override on exactly one principal, so the same
  fixture exercises both levels; the recorder's reader and the source read
  the same registry, and one control deliberately breaks that (C19).
- **Example-level, CP-17:** untouched by 345 (the candidate is frozen; the
  instruction forbids weakening its HTTP tests). After 345 lands and CP-17's
  gate is ruled, `MWE-G14`'s comparator gains one limb — the KYC shell's
  reference dereferenced over the HTTP door answers the same shell — as
  CP-17 work under its own ruling, not here.
- **Invariant-level:** `tests/invariants/test_mcp_role_separation.py` must
  stay green as-is; the two evidence routes call no product resolver (so they
  do not become discovered product doors), and `src/ccf/replay` gains no
  import. `tests/invariants/test_delivery_boundary_replay.py` keeps its roster
  (`catch_sites` lists a module once, and the new `except
  ProductEntitlementRefused` sits in the same permitted module); its plant
  anchor is the three-line block around `return _refusal_response(decided)`
  counted in `product.py`'s source alone, so the call text there is kept
  verbatim (§4.2) and the invariant gains equivalent anchors for the two new
  call sites in the same change. That module asserts nothing about fulfilled
  determinations reaching the writer (§6.2).

**The comparator.** `same_shell(a, b)`: delete `replay_reference` from each
`refusal` object; assert each body's `request` equals `{product_id:
DEREFERENCE_PRODUCT_ID, product_version: None, parameters: {reference: <that
body's own ask>}, temporal_boundary: None}` — the S7 defect fails here; then
the two remainders are equal key for key and value for value (including the
absence of `resource` and `policy_bindings`), and the two status codes and
header-name sets are equal. Two shells for two *different* asks can pass it;
two shells for one ask that differ anywhere but `replay_reference` cannot.
Stricter than the CP-17 `_shell` tuple by design (§5), and — unlike the
second draft's whole-body equality, which the second review executed and
showed false across asks because the echoed reference differs — satisfiable
on a correct implementation.

### 8.2 Controls

| # | case (Dave's eight first) | control | required result |
|---|---|---|---|
| C1 | ungranted principal → withheld serve → replay-ref GET | KYC-shaped bearer asks the product (`404` shell), then `GET /replay/resolutions?uri=<its replay_reference>` | `404` shell; on the wire `cause`/`error_code` read `undisclosed`, `detail` is the external sentence, no `assembly_refusal`, `resource` or `policy_bindings` key; `same_shell` with C6; the read-refusal record, read in-process, carries `evidence-disclosure-withheld`; the product-denial record carries `principal-not-entitled` (the tenant in the reference URI is the addressed tenant, accepted disclosure) |
| C2 | analyst with banker's record address | bearer B reads bearer A's served record by address and by URI, and by `/artifact/<address>` | `404` shell on all three; `same_shell` with C6; the read-refusal record names no class, role or tenant of A's record |
| C2′ | **shared-grant pair** | two principals both granted the same class at the same role, both at `full`; B reads A's record | `404` shell — the principal hold alone must carry this (the grant hold passes) |
| C3 | cross-principal artifact GET | B reads a pin named by A's record, by address | `404` shell (row 8) |
| C4 | same-principal authorized record GET | A at `full`, grant in force, reads A's served record by address and by URI | `200`, bytes hash to the address, `X-CCF-Content-Address` equals it |
| C5 | same-principal authorized artifact GET | A at `full` reads A's record through `/artifact/<address>` | `200`, identical bytes to C4 |
| C6 | nonexistent vs unauthorized existing, below `full` | a fabricated 64-hex address and a URI naming nothing, versus C2's existing address, same bearer below `full` | `same_shell` true; bodies differ only at `replay_reference` and at the echoed `request.parameters.reference` |
| C6′ | the same pair at `full` | as C6 with the bearer at `full` | whichever outcome R-4 rules, asserted exactly; rows 6, 7 and 8 `same_shell` among themselves at `full` regardless |
| C7 | normal governed serve unchanged | the product-route entitlement suite and `tests/http_api/test_product_disclosure.py` | green, unchanged assertions |
| C8 | MCP replay behavior unchanged | the `D-IMPL-129` pin and an in-process `get_replay_record` call under an unentitled contextvar identity | green, unchanged; the record still crosses on MCP |
| C9 | own record below `full` | A's tenant level `minimal`, no override; A reads A's own served record | `404` shell (row 3) — positive control for hold 3 |
| C10 | grant revoked after serve | re-register the tenant policy without A's class, then A reads A's record | `404` shell (row 4) — per-call re-decision |
| C11 | class unrecoverable | a record filed directly into the store with `request=None` and no refusal, owned by A at `full` | `404` shell (row 5) |
| C12 | divergent bytes | bytes registered at a wrong address (a store fixture), owned by A | `404` shell (row 7), not `409` |
| C13 | `@latest` | a moving-target URI | `409`, unchanged |
| C14 | ungoverned door | `product_entitlement` unbound | `503`, the product route's constant, on the **three GET** operations (PUT is untouched, §7) |
| C15 | the read-refusal chain, below `full` | A below `full` dereferences the `replay_reference` of its own C9 shell, twice | each hop a `404` shell `same_shell` with C6; each hop's reference resolves in-process to a record whose dimension 4 is (A, `no-role-resolved`) and whose dimension 2 is `no-resolution-step` |
| C16 | negative control for the comparator | two shells for one ask that differ only in `request.product_id` (one carrying a recovered class) | `same_shell` **false** — the comparison sees the S7 shape; C4's `200` body versus C6's is a second limb |
| C17 | non-record bytes on a record ask | a `ccf.test-blob` at a valid address asked through both `/replay/*` routes | `404` shell (row 6), `same_shell` with C6; no `500` |
| C18 | the index and the shape check | `GET /artifact/.artifact-names.json`, and a 63-character, an uppercase and a traversal-shaped address on both nouns | `404` shell, `same_shell` with C6; the store is not touched for the non-hex asks (a store spy) |
| C19 | the reader that discloses | a recorder built with its default `minimal` reader bound beside a source whose policy grants A `full`; A reads A's record | `404` shell (row 3) — hold 3 read the recorder, not the source |
| C20 | own read-refusal record at `full` | A at `full` dereferences the `replay_reference` of its own C2 shell | `200`; the record names A, the reference A asked, `evidence-principal-mismatch`, and nothing of the target |
| C21 | boundary denial decided under another tenant | A's product denial addressed to tenant T2 (a cross-tenant URL) on a recorder bound to T1; A at `full` under T1 dereferences it | hold 2 is decided under T2; withheld unless A holds the grant under T2 |
| C22 | the URI naming probe | B at `full` asks A's record address as a URI under A's registered (tenant, class, name) and under a foreign tenant segment | `same_shell` — the holds ran before the index was consulted |
| C23 | content-addressed existence probe | a `full` bearer asks `/artifact/<content_hash of a GraphQuery another principal's serve executed>` and a fabricated 64-hex address | `same_shell` at `full` — rows 6 and 8 are one outcome |
| C24 | the audit trail of an allowed read | A at `full` reads A's record (C4) and its own read-refusal record (C20) | one `authz_decision` event each, `authz_action_id` `replay.read`, `key` the reference asked, `version` the address delivered, `resolved` true, `actor` A |

### 8.3 Sabotages — each restores or bypasses one hold, by hand, restored by copy and verified by `cmp`

| sabotage | expected RED | expected GREEN |
|---|---|---|
| S1 — the replay router mounted without the governed step (today's shipped shape) | C1, C2, C9, C10, C15, C17 | C4, C5, C7, C8, C13 |
| S2 — the artifact router mounted without the governed step | C2 (artifact limb), C3, C18 (index) | C1, C4 |
| S3 — hold 3 removed (any level treated as `full`) | C1, C9, C15, C19 | C2, C2′, C4, C6 |
| S4 — hold 1 removed (grant and level only) | **C2′ only** — C2 stays green on the CP-17-shaped fixture because the roles differ, which is why C2′ exists | C4, C6 |
| S5 — absence rendered as today's `HTTPException(404, detail=…)` instead of the recorded shell | C6, C15, C17, C18 | C4 |
| S6 — hold 2 removed (principal and level only) | C10, C11, C21 | C4 |
| S7 — the recovered class written onto `request.product_id` (the first draft's defect) | C6 (the `request` value differs), C2 (the read-refusal record names A's class) | C4 |
| S8 — hold 3 read through the entitlement source instead of the recorder | C19 | C9 (both readers agree there) |
| S9 — the address-shape check removed | C18 (the index returns, the store spy fires) | C4 |
| S10 — the URI leg consults the naming index before the holds | C22 | C4, C6 |
| S11 — rows 6, 7, 8 given distinct internal codes (the second draft) | C6′, C23 | C6 (below `full` they still collapse) |
| S12 — the audit event not appended on the hold-2-skipped path | C24 | C4 |

A control that stays green under every sabotage is not measuring this design
and is struck; C16 guards the comparator itself. The `D-IMPL-129` pin is not
inverted by 345 and is listed under C8 precisely so that an over-reaching
implementation that touches MCP turns it red.

### 8.4 What "done" means at implementation review

All twenty-six controls green on the candidate (C6′ as ruled); every
sabotage's expected reds and greens observed and recorded in the as-built
section; `make lint` clean (the citation rules included); the invariant
suites green; the existing route and CLI tests re-derived as §9.2 names;
`openapi.json` regenerated and the diff reviewed; one digit-first
`docs/surface-changes/345-01-<slug>.md` fragment for the new exports and the
behavior change (§9.4).

---

## 9 · Compatibility

### 9.1 Existing records — authorized from metadata already present, conservatively

| record generation | tenant, principal, role | product class | over HTTP after 345 |
|---|---|---|---|
| served, with a request (15.5-13 onward) | present | `request.schema_name` | dereferenceable by its principal at `full` with the grant in force |
| served, `request` is `None` (older, or a caller that passed no question) | present | **unrecoverable** — the product bytes are not in the store | withheld (row 5); in-process `replay()` unaffected |
| refusal, 24.6-07 onward (every door denial, every resolver refusal since) | present; the decided tenant on boundary denials | `assembly_refusal.request.product_id` | dereferenceable by its principal at `full` with the grant in force under the decided tenant |
| refusal, legacy `ProductRequestViolation` block before 24.6-07 | present | unrecoverable | withheld (row 5) |
| any product record whose role is `no-role-resolved` | present | (either) | withheld (row 4) |
| read-refusal records (new, 345 onward) | present; no role by construction | none by construction | dereferenceable by its principal at `full` (holds 1 and 3) |

No ownership is invented from current state: the principal compared is the
one the record carries; the grant re-decided is the one the tenant's policy
holds *now* for that principal, class and role under the tenant the record
says decided; the level is the one the recorder's reader gives *now*. No
record byte is migrated or rewritten. The consequence is stated plainly:
**records that predate the request or the refusal-identity member are not
readable over HTTP by anyone**, and stay readable in-process and by replay
exactly as today. Nothing has shipped; that is a smaller cost than a guess.

### 9.2 Existing tests and callers — measured, not assumed

- `tests/http_api/test_routes.py` held six tests on the four operations, all
  on the module app with **no auth hook**, asserting `200`/`404`/`409` for a
  credential-less caller — the posture R-1 ends on these nouns. As built, all
  six were re-dispositioned in place rather than moved: that module is about
  routing, so it now asserts the ungoverned posture
  (`tests/http_api/test_routes.py::test_replay_decisions_refuses_on_an_ungoverned_door`
  and its siblings, including
  `tests/http_api/test_routes.py::test_replay_of_nothing_is_refused_the_same_way_as_something`,
  which pins that the `503` is not a channel either), the write path keeps its
  own control
  (`tests/http_api/test_routes.py::test_artifact_put_still_stores_and_returns_its_reference`),
  and every positive read — an authorized `200`, the `404` shell, the `409` for
  `@latest`, the no-oracle equality — is proven against a door that has the
  seams to decide, in `tests/http_api/test_evidence_dereference.py`. Their
  present form is kept in the as-built record (§13) as the measurement of what
  shipped, the `D-IMPL-108` precedent for the product happy-path tests.
- **The CLI.** `runtime/ccf_runtime/cli/main.py` builds its local app with
  `create_app(dependencies, acknowledge_insecure_default=True)` — no auth
  hook, no seams — and sends no bearer in `--base-url` mode; nothing under
  `runtime/ccf_runtime/cli` carries a credential. Under R-1 the three read
  verbs (`replay query`, `replay resolve`, `artifact inspect`) answer row 10
  locally and `401` against any governed server; `tests/cli/test_cli.py::test_read_verbs_dispatch`
  currently asserts they succeed against the fixture record and goes red for
  those three. The disposition is the one that test already records for
  `product get` under `D-IMPL-108`: the verb reaches the route and the route
  answers `product-door-ungoverned`, asserted by name. The CLI does **not**
  inherit authorization — it has no way to present a credential — and
  `D-IMPL-22`'s `--local` mode loses two nouns until `ccf` can bind one. That
  is a `D-IMPL-22` amendment if wanted, named here, not made here.
- `examples/cp-17-mnpi-wall-enforcement/server/serve.py::http_app` binds
  every seam `create_app` offers over the product's one store and one recorder
  and passes exactly three `ApiDependencies` handles; 345 adds no required
  keyword to `create_app` and no field to `ApiDependencies`, so it builds
  unchanged and its door tests (`tests/examples/test_cp_17_doors.py::test_the_unconfigured_principal_is_refused_like_a_nonexistent_product`
  and the module's other gates) — which read records in-process and never
  call `/replay` or `/artifact` — stay green as written.
- `tests/crossproc`, `tests/mcp`: untouched surfaces; the `D-IMPL-129` pin is
  a control (C8). `recorded_boundary` is not widened, so the two MCP builders'
  construction posture is unchanged (§4.2).
- **Hand-wired two-recorder composition** (a resolver holding one recorder,
  the door another): hold 3 reads the door's reader; the reader that disclosed
  a resolver-side refusal may differ. Not reachable in the tree — every
  shipped composition and every test fixture is one-recorder — and named here
  as the residual of §3.1 rather than closed, because `create_app` cannot see
  through an opaque resolver.

### 9.3 Behavior changes, named as such

1. `GET /replay/decisions`, `GET /replay/resolutions`,
   `GET /artifact/{address}`: a governed determination; `404` + the canonical
   shell replaces `200`-to-any-bearer, `{"detail": …}`-on-absence and the
   `500` on non-record bytes; `503 product-door-ungoverned` when the
   entitlement seam is unbound. Breaking on the delivery surface in the way
   `D-IMPL-258` (3) called *"an intentional wire change required by the
   suppression-silence ruling"*.
2. Non-record artifacts are not dereferenceable over HTTP (row 8) until the
   reachability extension is opened with PUT (R-3). **This amends `D-IMPL-23`'s
   "artifact get" and `D-IMPL-22`'s `artifact inspect` to records over HTTP**,
   and the CLI's help text for the verb says so.
3. Read denials write replay records (§6.2); every dereference appends one
   `authz_decision` audit event under a new action id (§4.4).
4. The CLI's local mode answers row 10 on the three read verbs (§9.2).
5. An entitling **HTTP** door now requires a recorder that can state a
   disclosure level (`disclosing_boundary`, §4.2); the MCP builders do not.

### 9.4 Coupled artifacts an implementation must move

`openapi.json` (regenerated by `make openapi`; the three GET operations gain
declared responses and their `description`), `docs/surface/v0.2-surface.json`
via a `345-01` fragment (`runtime/ccf_runtime/authz/delivery_boundary.py`,
`runtime/ccf_runtime/authz/refusals.py` (the two action ids),
`runtime/ccf_runtime/http_api/errors.py` (the `ERROR_EVIDENCE_*` constants),
`runtime/ccf_runtime/http_api/routes/replay.py`,
`runtime/ccf_runtime/http_api/routes/artifact.py`,
`runtime/ccf_runtime/http_api/routes/__init__.py`,
`runtime/ccf_runtime/http_api/app.py` exports; `Change type: behavior` for the
routes), the `delivery_boundary` module docstring (its sentence that the one
`except` for the entitlement refusal is the one in `govern_entitlement`
becomes *the two, in `govern_entitlement` and `govern_dereference`*),
`tests/invariants/test_delivery_boundary_replay.py` (the two new renderer
anchors), `tests/cli/test_cli.py` (§9.2), the app module docstring,
`public/how-to/security-and-deployment.md` §4 (one paragraph: what a replay
reference dereferences to, and that the three evidence nouns are governed
like the product noun), `public/reference/protocols/runtime-surfaces.md` (the
new symbols), `public/concepts/replay-anatomy.md` (one sentence under
*Resolution* on who may resolve over a door). `AUTH_POSTURE_SENTENCE`,
`_INSECURE_DEFAULT_MESSAGE` and their pins: unchanged.

---

## 10 · Rulings asked

- **R-1 — the ungoverned posture on the evidence nouns.** With the
  entitlement seam unbound, or with no verified grant, the three evidence GETs
  refuse `503 product-door-ungoverned` as the product route does; the
  credential-less route tests move to a governed fixture; the CLI's local
  mode loses `replay` and `artifact` reads until `ccf` can bind a credential.
  Alternative: keep bearer-less reads open when `auth=None` (the literal
  `AUTH_POSTURE_SENTENCE`), which preserves those tests and the CLI as written
  and keeps the acknowledged-insecure app leaking on these nouns while the
  product noun does not. Recommended: as designed.
- **R-2 — a record crosses a door only at `full`, read by the recorder.**
  Hold 3 as stated in §4.3: below `full` a principal's own record dereferences
  to the shell, and the level is the one the door's recorder reads under the
  recorder's tenant. Alternative: allow own-record reads at every level,
  which makes the withheld serve's reference reveal the withheld cause to the
  very principal it was withheld from (`S-01` (1)) and cannot be squared with
  `D-IMPL-254` without a second representation of the record. Recommended:
  as designed.
- **R-3 — non-record evidence over HTTP, and PUT.** Withhold non-record
  artifacts over HTTP in 345 (§4.5) and open the reachability extension
  (`?via=<record>`) *together with* PUT governance under a later id, because
  they share one trust root; record the `D-IMPL-22`/`D-IMPL-23` amendment
  (§9.3). Alternative A: bring PUT into 345 now (tenant authorization on
  `put`, the body tenant held to the grant, the replay-record class refused
  over HTTP) so that reachability can ship in 345 — a wider change than the
  launch contract asked for. Alternative B: ship reachability now trusting
  stored records — unsafe while PUT is open, and not recommended.
  Recommended: as designed.
- **R-4 — what a `full` principal may learn about an address that is not
  its own.** With every absence one outcome at every level (§4.4) and the
  URI leg's holds run before its naming index (§4.3), the only difference
  left at `full` is on a **genuine record of another principal**: the shell's
  `cause` crosses as it does on the product door — `unauthorized` for that,
  `nonexistent` for everything else — and the read-refusal record retains
  nothing of the target. A record's address is a hash over its bytes,
  `recorded_at` included, and is not computable by a prober; the classes
  whose addresses *are* computable are the ones now collapsed into
  `nonexistent`. This follows the applied reading of `D-IMPL-258` that 24.6
  built the product door on, which is recorded *for confirmation* and has not
  been ruled. Alternative: collapse hold-1 failures to the `nonexistent`
  shell at every level too, which requires either recording `nonexistent` as
  the internal cause (destroying the audit truth that a cross-principal read
  was attempted, which Q27 forbids) or a per-kind disclosure row that maps a
  retained `unauthorized` to an external `nonexistent` at `full` — a new
  disclosure-table entry. Recommended: as designed, confirming the applied
  reading in the same ruling.
- **R-5 — allowed dereferences and the replay writer.** As designed, an
  allowed read writes no replay record; every dereference, allowed or
  refused, appends one `authz_decision` audit event under `replay.read` /
  `artifact.read` naming the reference asked and the address delivered
  (§4.4, §6.2). Alternative: a fulfilled-read record shape, one record per
  allowed read, through the recorder. Recommended: as designed — the audit
  event names the read; a record would duplicate a record.

Decisions this document makes without a ruling, each with its alternative
named in place: the class-recovery rule and conservative withholding for
records without a recoverable class (§9.1); every absence as one outcome at
every level (§4.4); the entitlement source's own `authz_decision` event
keeps `product.retrieve` when hold 2 runs, because the question the boundary
asks it *is* the product-retrieve entitlement (`D-IMPL-129`'s own "field of
the vessel" argument), while the dereference itself is audited under the two
new read action ids by the boundary (§4.4) — no Protocol change.

---

## 11 · What this document does not do

- It does not change `CP17-F-08` (computed-empty replay), `CP17-F-09`
  (acquisition-seam contract-version registration), CP-17's product logic,
  the HTTP role-request behavior already proven at `MWE-G15`, AML, IB, the
  A2 review, the freshness-scorer normalization, or the gate perspective seam.
- It does not touch PUT (§7), the MCP doors (§6.3), `src/ccf/replay`, or
  `src/ccf/artifacts` — `S-02`, the store's own traversal, is returned to
  Dave as a separate finding because its repair belongs in the store and its
  MCP exposure is outside 345.
- It does not add a supervisory or auditor read: a principal reads its own
  determinations. Whether an examiner role may read others' records is a
  policy dimension the entitlement artifact does not carry — the same fact
  `D-IMPL-129` recorded for agents — and is a separate entry if wanted.
- It does not close `D-IMPL-129`. The record-bound primitive designed here
  is the one an Experience-server replay read *could* adopt once that tool
  takes an address rather than "the most recent record"; that is a follow-on
  under `D-IMPL-129`'s own trigger, and the instruction fixes MCP as unchanged.
- It does not hide addresses, remove or blank a `replay_reference`, weaken a
  CP-17 test, or delete evidence.

---

## 12 · Perspective, surfaced for the ruling

The leak was measured on the door the project had just declared governed,
and every mechanism the repair needs already existed on that door: the grant
on the request, the entitlement source that decides per call, the recorder
that writes a full record and returns a disclosed shell, the renderer that
maps one kind to one status, and a record that already carries the tuple the
serve was decided on. What was missing was the sentence that says a
*dereference is a determination*. The two routes were written under `D-IMPL-23`
as *"serialization, auth hooks, and routing, no new semantics"* — and a read
of the internal truth was not, then, understood to carry a semantic of its
own. 345's whole weight is that sentence. Its first draft got two of the
consequences wrong in ways only execution showed — it read the level through
the wrong object, and it let the shell carry a value the caller never
supplied — which is the strongest argument this document can make for the
proof plan being mostly about proving equivalence rather than mechanism.

---

## 13 · As built (2026-09-20, synchronization of this design to the tree)

Implemented on `d-impl-345-authz`, forked from the design commit `014705b0`,
under Dave's implementation GO of 2026-09-20 (R-1..R-5 and `S-02` in scope).
CP-17 is untouched and remains frozen at `f5e22e6b`. Sections 1–12 are the
design as ruled; this section is what the tree now holds, including the four
places the implementation departed from the design and why.

### 13.1 What was built

| file | what |
|---|---|
| `src/ccf/artifacts/protocol.py` | `CONTENT_ADDRESS_PATTERN`, `held_content_address`, `MalformedContentAddress` (an `ArtifactNotFound` subclass) — the one shape check, on the Protocol module that owns addressing (`S-02`) |
| `src/ccf/artifacts/file_store.py` | `_path` runs the check before the join, so the join can only produce a child of the root; `exists` answers `False` for a non-address rather than raising, and still touches no filesystem |
| `src/ccf/artifacts/mcp_store.py` | the same check before each resource URI is composed, so the MCP store spends no round trip on a string a server could not hold |
| `src/ccf/products/disclosure.py` | `DISCLOSURE_FULL`, named beside `DISCLOSURE_MINIMAL` |
| `runtime/ccf_runtime/authz/delivery_boundary.py` | `govern_dereference` with the four holds, `DisclosingRecorderProtocol`, `disclosing_boundary`, `DereferenceRequest`, `DereferencedEvidence`, the two evidence surface tokens, `EVIDENCE_SURFACES`, `DEREFERENCE_PRODUCT_ID` |
| `runtime/ccf_runtime/authz/refusals.py` | `ACTION_REPLAY_READ`, `ACTION_ARTIFACT_READ` |
| `runtime/ccf_runtime/http_api/errors.py` | the four `ERROR_EVIDENCE_*` codes |
| `runtime/ccf_runtime/http_api/routes/__init__.py` | `governed_refusal_response` — the renderer lifted out of the product route, with the kind→type-name map beside it |
| `runtime/ccf_runtime/http_api/routes/product.py` | imports that renderer under its historical local name; its own call text is byte-unchanged |
| `runtime/ccf_runtime/http_api/routes/replay.py`, `.../artifact.py` | authenticate, call the governed step, encode; `_route_path` so the caller's string is echoed in exactly one member |
| `runtime/ccf_runtime/http_api/app.py` | both construction checks in one block; the evidence recorder threaded into both routers |
| `tests/http_api/test_evidence_dereference.py` | 32 controls (new module) |
| `docs/surface-changes/345-01-…md` | 20 entries |

### 13.2 The four departures from §1–§12, named

1. **The four `ERROR_EVIDENCE_*` codes live in `ccf_runtime.http_api.errors`,
   and `delivery_boundary` imports them from there** — so that module now
   names a transport module, which its own docstring previously said it did
   not. The alternative was a second error vocabulary in the authz package. The
   enforced invariant permits it in as many words
   (`tests/invariants/test_delivery_boundary_replay.py`: *"The determination
   layer is allowed to know a door's error vocabulary; a door is not allowed to
   make the determination"*), it is the permission the entitlement seam beside
   it already uses, and the module docstring was corrected rather than left
   true-by-omission.
2. **`resource.address` is the route's own path, not the route path plus the
   reference** (§4.4 said the latter). Measured: with the concrete path, two
   refusals for two different asks differed at `resource.address` as well as at
   `request.parameters.reference`, which would have forced the comparator to
   normalize two members instead of one. The caller's string is now echoed in
   exactly one place and every other member of the shell is constant across
   asks, which makes the comparator strict on `resource` rather than blind to
   it.
3. **Both construction checks sit in one block in `create_app`**, and
   `tests/http_api/test_product_refusal_statuses.py`'s sabotage anchor was
   widened to cover both. The design said `disclosing_boundary` would be called
   at the mount site; that would have been a second construction check the
   existing recorder-check sabotage does not remove, silently defeating a
   shipped control. The test's own anchor assertion asks to be re-anchored when
   the builder's checks change; it was, and its assertions are unchanged.
4. **`tests/authz/test_delivery_boundary.py`'s minting-sabotage anchor was
   narrowed** to `govern_entitlement`'s mint by including the comment that
   precedes only it. `govern_dereference` added a second
   `return refusal_recorder.record(` at the same indentation, and a control
   that sabotaged whichever one it found first would measure a different
   function on a later edit.

### 13.3 Controls, measured

`tests/http_api/test_evidence_dereference.py`: **32 passed**. They cover every
behavior the ruling required, including the four the design added after its
second review (the URI naming probe, the computed-pin probe, the audit trail
of an allowed read, and the own-read-refusal-record read), plus the MCP
inheritance of the store-level refusal and the store-level refusal itself.

One control's expectation was corrected against the implementation rather than
the other way round, and the correction is the more interesting property: in
C1 the ungranted principal dereferences the reference of **its own** product
denial, so hold 1 passes and **hold 2** refuses with the source's own
`principal-not-entitled`. The same entitlement decision that refused the serve
refuses the record of that serve, which is *"held to the applicable product
grant"* at its tightest.

### 13.4 Sabotages, run by hand and restored byte-clean (`cmp`)

| sabotage | reds | greens |
|---|---|---|
| S1 — the shipped pre-345 replay handler restored | 23 | the 8 that do not read a record through the replay routes |
| S2 — the shipped pre-345 artifact handler restored | C2 (artifact limb), C3, C5, C23, C24 | 26 others |
| S3 — hold 3 removed | C9, C15, C19 | 28 others, C2/C2′/C4/C6 included |
| S4 — hold 1 removed | C2, **C2′**, C6′, C20, C22 | 26 others |
| S6 — hold 2 removed | C1, C10, C11, C21 | 27 others |
| S7 — the recovered class written onto `request.product_id` | C1, C9 | 29 others |
| S9 — the store shape check removed | the store-level control | 30 others |
| S10 — the URI's naming consulted before the holds | C22 | 30 others |
| S11 — absences given distinct internal codes | C3, C12, C17, C23 | 27 others |
| S12 — the allowed read's audit event dropped | C24 | 30 others |
| S14 — the unbound-seam guard bypassed | C14 | 30 others |

Every sabotage is load-bearing and each reds a distinct set. Three results are
worth recording because they differ from what §8.3 predicted:

- **S4 reds C2′ and C2 both.** The design expected only C2′, reasoning that
  C2's principals differ in role; in the built fixture `A` and `B` hold the
  same role, so both catch it. C2′ remains the control that would catch hold-1
  removal even if that changed.
- **S7 reds C1 and C9, not C6.** Because hold 1 stops before the record's
  identity is read, no class is ever recovered on a cross-principal ask — so
  the leak the first draft carried is reachable only on the caller's *own*
  records. That is the ordering property of §4.4 showing up as a narrower blast
  radius than the design assumed, and the two controls that do catch it are
  enough.
- **S9 reds only the store-level control.** At the HTTP door the record
  validation already refuses the naming index, so the shape check is
  defence-in-depth there. It is not redundant: it is the only defence for the
  MCP blob resource and for every in-process caller, which is exactly why the
  ruling placed it at the store.

`S5` (absence rendered as today's prose 404) is subsumed by S1 and S2, which
restore precisely that behavior along with the rest of the shipped handlers;
it was not run separately.

### 13.5 Regression package, measured at the candidate

`tests/http_api`, `tests/authz`, `tests/cli`, `tests/invariants`, `tests/mcp`,
`tests/products`, `tests/replay`, `tests/contracts`: **4 460 passed, 1
skipped**, with the single remaining red being
`tests/invariants/test_determination_authority_disclosure_delivery.py::test_no_control_here_edits_the_real_source_tree`,
which asserts `git status --porcelain -- src runtime` is empty and is therefore
a statement about an uncommitted working tree rather than about this change;
it passes at the commit. `python -m tools.lints --all` is clean, the citation
ratchet holds, the surface manifest and its fragment agree, and `openapi.json`
is byte-identical (the committed spec is generated from an app with no auth
hook, and no route's declared request or response model moved).

Three test dispositions changed, each named in §9.2/§9.3 before it happened:
the six `test_routes.py` evidence-route tests now assert the ungoverned
posture, `tests/cli/test_cli.py::test_read_verbs_dispatch` records that the
CLI's three evidence verbs answer `product-door-ungoverned` until `ccf` can
carry a credential (a `D-IMPL-22` amendment, named and not made), and the two
sabotage anchors of §13.2 were re-anchored.

### 13.6 What remains open

R-1..R-5 are implemented as recommended; `S-02` is closed at the store. The
reachability extension (`?via=<record>`) and artifact PUT governance stay
closed together under a later id, as R-3 ruled. `D-IMPL-129` is untouched and
its pin still asserts that an unentitled credential reads a record over MCP.
