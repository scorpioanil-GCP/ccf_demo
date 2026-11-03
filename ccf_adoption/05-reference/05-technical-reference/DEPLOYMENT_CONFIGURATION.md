# Deployment and Configuration

**Current SDK reference baseline:** `drcastillo/ccf_code/v1.0.2@5f85b389efe9e4b1de62e84a5af62ca4b2e12178`\
**Release:** `v1.0.2` @ `5f85b389efe9e4b1de62e84a5af62ca4b2e12178` (17 October 2026)

Deployment wiring assembles a fabric from governed declarations and runtime/environment values.

## `ccf_config.yaml`

Current `DeploymentConfig` can include:

- tenant / backend;
- product class and request contract;
- operators / policy / policy constraints;
- resolution;
- half-life / debt;
- perspective;
- Replay / TTL;
- door / producers;
- skills / agent;
- **grants**;
- **product_entitlement**;
- **temporal_boundary**;
- **demonstration_serve_instant**;
- store survivor/creation-lock settings.

The current generated [governance API](api/governance.md) is the exact shape authority.

### Multi-principal entitlement

Use `product_entitlement:` for a standard product deployment that serves several principals. The declared body must match the deployment tenant and may only grant classes the deployment serves.

### Declared skill grants

Use `grants:` to name the entries under `skills:` that this deployment asks composition to put in force. A grant is still judged by the policy regime and approval sink; declaration is not unconditional grant authority.

### Demonstration serve instant

For dated demonstrations on the paved road, declare both a `demonstration_serve_instant` and the corresponding temporal boundary, pass no custom clock to `open_product`, and use the supported SDK development store/backend posture.

Do not use this mechanism as a production clock override.

## `ccf_environment.yaml`

Runtime resource names/remedies include:

- endpoints / DSNs;
- local substrate paths;
- credential references;
- remote door settings.

It carries runtime values/names, not secrets embedded in governed artifacts. Use [the current example configuration guide](../../examples/CONFIGURATION.md) for Fluree **4.2.4**, complete DSNs, explicit ports, producer tokens and per-example environment prefixes.

## Store/boot integrity

Current boot/deployment surfaces include additional refusals for question/deployment stores that are not fresh, exclusive or verified, including:

- `DeploymentStoreNotEmpty`;
- `DeploymentStoreNotVerified`;
- `QuestionStoreNotEmpty`;
- `QuestionFabricNotFresh`;
- `QuestionFabricNotExclusive`;
- `ManifestKeysPlaceToOneKey`.

Store-creation locking and SQLite identity/lease controls are deployment concerns. Follow the current SDK constructors; do not copy pre-Oct-13 boot snippets.

## Invalidation composition

`open_product` composes a tenant-scoped invalidation sink. If your deployment records external invalidation boundaries, use `opened.invalidation_sink`; do not fabricate `InvalidationRecordRegister` or construct an unscoped writer.

## Product doors

Current choices include:

- paved `open_product` + standard `open_door` / `open_door_with_verifier`;
- `compose_for_door(...)` for a hand-composed governed product;
- optional governed product resource via `expose_product_resource=True`;
- `open_review_door(...)` for authorized ReviewQueue release/reject authority.

Stdio remains single-principal/process-owned; use loopback/HTTP or a composed authenticated transport when caller identity must vary.

## Install/version posture

The proprietary distribution name is `ccf-sdk`; Python imports remain `ccf` and `ccf_runtime`, and the CLI remains `ccf`.

The SDK version is derived through `setuptools_scm`. CI/install paths use the hash-pinned lock and no dependency-resolving editable install.

## License/delivery boundary

Current SDK root `LICENSE.md` contains the CCF SDK software license. Its Schedule A identifies the fixed delivered source commit `01fc424d92f8d15856d5f277e9cf18ef59bc7883` and wheel.

The adoption reference now describes released SDK 1.0.2. Schedule A still names October 13: a later release needs the licensor's written grant/amendment naming its source. Building a local distribution does not amend that record.

## Exact current shapes

Use [Governance API](api/governance.md), [Context Product API](api/products.md), and [Runtime API](api/runtime.md).

## Context Skill and evidence declarations

Declare `policy.skill_governance`, `producers`, `skills`, `agent` and `grants` together; the SDK derives the binding and requests grants at open. The paved path derives only `mcp_product` and refuses other stated skill types. See [Context Skills](CONTEXT_SKILLS.md). For durable evidence pass `evidence_root=` separately from temporary `scratch`; `read_sources=False` creates an inspection/replay opening that cannot answer or resolve new questions. See [Decision Replay](DECISION_REPLAY.md).

A custom refusal recorder used with an agent-conditioned child resolver must accept `agent_conditioning=` (or compatible keyword arguments). `GovernedResolver` checks this at construction so refused decisions can retain the composing identity.
