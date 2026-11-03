# SK-01 — Declare and govern agent skills

**SDK source baseline:** `drcastillo/ccf_code/v1.0.2@5f85b389efe9e4b1de62e84a5af62ca4b2e12178` — reviewed 17 October 2026.

**SDK example:** `examples/sk-01-declare-and-govern-agent-skills/`. Run it from a separate authorized `ccf_code` checkout. This page is the implementation walkthrough; the [analysis companion](SK01_DECLARE_AND_GOVERN_AGENT_SKILLS_ANALYSIS.md) explains the bank's decisions and how to express them using the standard specification structure.

## Banking question and implementation boundary

A collateral analyst asks for a facility's collateral and set-off coverage within a named obligor's scope. The agent must acquire that answer from the registered collateral product, within its granted authority. The demonstration asks whether the grant is effective, whether an over-reaching declaration is refused, and what the resulting decision records prove.

`collateral-analyst` holds `collateral-ask`. Its host product is `credit-risk.facility-collateral-brief` version `1.0.0`, tenant `sk-01-demo`, using SQLite for fabric state. The host reads obligor identity from Postgres; cp-06-canonical provides the collateral answer through its standard MCP door. SQLite does not replace either upstream data source.

## Exact declarations

This is an excerpt of the shipped `ccf_config.yaml`, not a complete replacement file:

```yaml
policy:
  class_id: sk-01.policy-bundle
  role: register
  registration: typed
  key: sk-01-demo/policy-bundle/facility-collateral-brief
  regime: facility-collateral-brief
  skill_governance:
    grant_requires_approval: false
    permitted_scopes:
      - collateral-coverage.read
producers:
  collateral:
    server: collateral-coverage-producer
    producer_id: cp-06-canonical-collateral-and-setoff-coverage-egress
    producer_tenant: cp-06-canonical-demo
    endpoint_from_env: CCF_SK_01_COLLATERAL_URL
    credential_from_env: CCF_SK_01_COLLATERAL_TOKEN
    offers:
      - product_class: credit-risk.collateral-coverage
        versions_from: "1.0.0"
agent:
  schema_version: "1.0.0"
  artifact_version: "1.0.0"
  name: collateral-analyst
  archetypes: [context_assembly]
grants: [collateral-ask]
skills:
  collateral-ask:
    schema_version: "1.0.0"
    artifact_version: "1.0.0"
    description: asks the registered collateral producer for one facility's collateral and set-off coverage
    produces: credit-risk.collateral-coverage
    requirements:
      required_scopes: [collateral-coverage.read]
      required_context_products: []
```

The SDK derives `mcp_product`, its binding and argument schema. `required_context_products: []` is the skill requirements field; the product still has a **required** child `credit-risk.collateral-coverage`, compatible from `1.0.0`, in `product_class.requires`.

`variants/over-reach/ccf_config.yaml` changes only the skill block: artifact version becomes `1.1.0` and `collateral-ledger.write` is added to the required scopes. The policy still permits only `collateral-coverage.read`; opening must raise `DeclaredGrantRefused` for `tier-1-policy-compatibility`, with `grant_requested` then `grant_refused` in audit. This tests label compatibility, not attempted database writes.

## Question mapping

| Field | Parent question | Child question |
| --- | --- | --- |
| Subject | Obligor LEI `2549001IGRCG4F0RLD36` (BGC Group) | Facility `FAC-5B8418` |
| Intent | `collateral-brief` | `lgd-assessment` |
| Freshness | `decision-scoped` | `as-filed` |
| Arguments | `facility_id: FAC-5B8418` | Same facility ID, `borrower_scope` containing the parent LEI |
| Asked at | `2026-09-07T12:00:00+00:00` | Passed through from the parent |

The demonstration serves at `2026-09-07T12:05:00+00:00` with a one-hour past boundary and zero clock skew. The host's maximum/product TTL is 43,200 seconds, floored by admitted child expiry. Its identity half-life is 31,536,000 seconds; debt thresholds are `0.30` forced-LLM and `0.60` fail-closed, with risk sensitivity `1.0`. These are illustrative snapshot calibrations, not bank production policy recommendations.

## Run from the SDK root

1. Run `make venv` to install the locked environment, including `claude-agent-sdk` for adapter inspection.
2. Configure cp-06-canonical's own `CCF_CP_06C_*` variables using its [current README](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/examples/cp-06-canonical-collateral-and-setoff-coverage/README.md). Its Fluree server is **4.2.4**. Use your estate endpoints and read-only database credentials.
3. Start that producer in a separate terminal, with a token you choose. Replace the placeholders before running:

```bash
export CCF_CP_06C_DOOR_TOKEN='<chosen-token>'
.venv/bin/python examples/cp-06-canonical-collateral-and-setoff-coverage/run.py --door
```

The producer prints `READY <port>`. Set all four SK-01 variables in the terminal running the consumer:

```bash
export CCF_SK_01_POSTGRES_DSN='host=<host> port=<port> dbname=<database> user=<read-only-user> password=<password>'
export CCF_SK_01_POSTGRES_SCHEMA=ccf_v2
export CCF_SK_01_COLLATERAL_URL='http://127.0.0.1:<port>/mcp'
export CCF_SK_01_COLLATERAL_TOKEN='<same-chosen-token>'
make example-sk-01
```

Use a complete Postgres DSN: a short `dbname=...` silently inherits other connection settings from the shell. The example does not set its own read-only SQL session; the database role supplies that restriction. No model credentials are needed because no model is called.

## Read the five movements

| Movement | Expected observation | What it establishes |
| --- | --- | --- |
| 1. Open | Grant requested and effective; agent/scopes/grant hash shown | Declared grant passed the policy regime |
| 2. Ask | Served or governed-refused parent; dimension-4 agent/set checks | The composing identity is recorded on either outcome |
| 3. Inspect adapter | Empty `tools` and `allowed_tools` | `mcp_product` does not become a model tool |
| 4. Open over-reach variant | Named grant refusal in a fresh registry | An additional, unpermitted scope is rejected at composition |
| 5. State limitations | Explicit unavailable capabilities | No runtime grant management, standalone agent or record-only skill enumeration is implied |

For an admitted child, dimension 5 also records the skill name/version and grant hash. A refused child row records refusal evidence without those skill/grant fields. A temporal refusal may occur before any child row exists.

The program exits `0` when all movements behave as declared, **including a governed-refused question**. It exits `1` if the over-reach variant opens or a record check prints `NO`. Missing environment settings fail before the run; they are not a governed answer.

## Exercise two negative questions

```bash
make example-sk-01 FACILITY=--facility=FAC-D3D1A4 LEI=--lei=B3BS7ACMDUWISF18KY76
make example-sk-01 ASKED_AT=--asked-at=2026-09-07T10:00:00+00:00
```

The SDK README reports the first as `composite-child-refusal`, with an ineligible child carrying producer `ttl-refusal` / `ttl-bounds`; the second is `asked-at-outside-temporal-bound`. Both retain dimension-4 identity. Those estate results are the SDK's recorded 16 October measurements, not executions performed for this documentation refresh.

## Files to read and limitations

Read [README](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/examples/sk-01-declare-and-govern-agent-skills/README.md), [configuration](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/examples/sk-01-declare-and-govern-agent-skills/ccf_config.yaml), [deployment/question mapping](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/examples/sk-01-declare-and-govern-agent-skills/deployment.py), [run](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/examples/sk-01-declare-and-govern-agent-skills/run.py), [adapter inspection glue](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/examples/sk-01-declare-and-govern-agent-skills/tool_surface.py) and [findings](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/examples/sk-01-declare-and-govern-agent-skills/FINDINGS.md).

The SDK tests are [offline](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/tests/examples/test_sk_01_offline.py) and [estate](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/tests/examples/test_sk_01_estate.py). SK-01 does not run a replay gate or an LLM call. Its grant/catalog state is in memory; a record hash does not recover the granted members or their requirements. See [Context Skills](../../05-technical-reference/CONTEXT_SKILLS.md) for the supported boundary and [Decision Replay](../../05-technical-reference/DECISION_REPLAY.md) for current composite replay.
