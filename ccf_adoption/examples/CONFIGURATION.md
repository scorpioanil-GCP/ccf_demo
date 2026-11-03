# Example setup and configuration

Checked against `drcastillo/ccf_code/v1.0.2@5f85b389efe9e4b1de62e84a5af62ca4b2e12178` on 18 October 2026. The [source inventory](SDK_BASELINE.json) maps adoption guides to SDK examples. Historical specification excerpts and release qualification records keep their original pins; use the current run instructions for this checkout.

## Prepare the SDK checkout

Use an authorized, separate checkout of `ccf_code` at the commit above. Select the release tag explicitly; an unqualified clone does not select this fixed runtime. In a fresh checkout:

```bash
git clone --branch v1.0.2 https://github.com/drcastillo/ccf_code.git
cd ccf_code
git switch --detach 5f85b389efe9e4b1de62e84a5af62ca4b2e12178
python3.12 -m venv .venv
make venv
```

`make venv` installs the SDK's hash-pinned lock and local development packages. The distribution is `ccf-sdk`; Python imports are `ccf` and `ccf_runtime`. See the [SDK installation instructions](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/README.md#install) for migration from a prior installation. Run the SDK commands in these guides from that checkout's root. The local [covenant-review demonstration](agent-skills-covenant-review/README.md) has its own smaller dependency environment.

## Select the estate explicitly

Restore and verify the [data estate](../00-dataprep/README.md) before running the financial-services ladder. Use **Fluree 4.2.4**, the version pinned by the [SDK CI service](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/.github/workflows/ci.yml) and checked by its differential test. It is an engine requirement, not a new data-bundle version.

Replace every `<...>` placeholder before running a command. Ports are deployment settings, not SDK defaults. The `8090` in a Fluree Docker mapping is the port **inside the image**; choose the host-side port yourself.

PostgreSQL DSNs must include host, port, database, user and password. For example:

```bash
export CCF_CP_06C_POSTGRES_DSN='host=<host> port=<port> dbname=<database> user=<read-only-user> password=<password>'
export CCF_CP_06C_POSTGRES_SCHEMA='ccf_v2'
export CCF_CP_06C_FLUREE_URL='http://<fluree-host>:<port>'
export CCF_CP_06C_FLUREE_LEDGER='fibo-v2'
```

Use libpq escaping for password values containing spaces or quotes. A complete PostgreSQL URI is also supported; percent-encode reserved characters in its credentials. A short `dbname=...` or a URI without a port/password inherits omitted settings and is not the documented example configuration. Source roles need read access; a role's name alone does not enforce that restriction.

For a MongoDB-backed example, specify its endpoint, authentication database and data database separately:

```bash
export CCF_CP_13C_MONGO_URI='mongodb://<read-only-user>:<password>@<host>:<port>/?authSource=<auth-database>'
export CCF_CP_13C_MONGO_DB='fibo_v2'
```

Percent-encode reserved characters in MongoDB credentials. Keep credentials in the process environment or your deployment's secret mechanism. The restored v2 namespaces are PostgreSQL `ccf_v2`, Fluree `fibo-v2` and MongoDB `fibo_v2`; do not substitute the older namespaces from a Dataprep `.env`.

To confirm the selected Fluree service, inspect its health response:

```bash
curl --fail --silent --show-error "${CCF_CP_06C_FLUREE_URL}/health"
```

The response must report `version` as `4.2.4`. This verifies the engine, not the presence or correctness of the estate; run the estate verifier separately. S1-01 writes to a **disposable** Fluree instance and must not use the shared curated estate.

## Use the example's own declarations

`ccf_config.yaml` declares product, policy, agent, skill and producer contracts. `ccf_environment.yaml` names environment inputs and their missing-value remedies. Older examples may use `backends.yaml` or artifacts instead. Read the files in the selected example; environment prefixes are not interchangeable. In particular, CP-22 uses CP-21's estate settings, CP-14 has five producer URL/token pairs, and SK-01 has its own Postgres settings plus the collateral producer's URL/token.

Start each MCP producer in a separate terminal. Its door command blocks while serving. Choose its `CCF_CP_*_DOOR_TOKEN` before launch, then give the consumer that same token and the port printed by `READY <port>`. CP-14's family and covenant producers also require the `producer-demonstration` configurations shown in its [runbook](../05-reference/02-context-product-producer/examples/CP14_CREDIT_MEMO_CONTEXT.md).

Keep demonstration clocks and temporal boundaries from the selected configuration together. Do not replace a dated example's instant with today's date and expect its historic estate evidence to remain fresh. Retained replay uses a separate private `CCF_REPLAY_EVIDENCE_ROOT`; see [inspection commands](../05-reference/05-technical-reference/CLI_HTTP_OPERATIONS.md#retained-evidence-commands).

## Interpret verification accurately

The inventory records source reconciliation. It does not certify a live run of every database-dependent example. Run each guide's validation command against your verified estate and distinguish passed tests, prerequisite skips and governed refusals. The local covenant-review demonstration is independently runnable without databases; its nine checks were rerun at this SDK pin.

## Upgrade to 1.0.2

Read the [migration checklist](../05-reference/05-technical-reference/MIGRATION_AND_LIMITATIONS.md) before reusing custom workflow stores or approval transports. The release requires permanent store identity, per-pause request handling and `retire`; older durable suspended runs require a fresh approval after rebind. The release wheel contains the library/runtime only, so keep the tagged source checkout for example commands.

## Host platform and release tooling

The bank launch/verification scripts target Linux (`/proc`, GNU `stat`, `setsid`). The SDK-managed SQLite lock directory also reads Linux `/proc/self/mountinfo` and only accepts its listed local filesystem types. On macOS or an unrecognized/overlay filesystem, the default paved example opening refuses `WriterLeaseRequired`; this is not a successful example run. Use a Linux host with supported storage (including `tmpfs` for disposable tests), or explicitly declare an appropriate private `writer_lease_lock_dir` when authoring a deployment. Do not bypass the lease check.

The release-tag version is exactly `1.0.2`. The SDK's older `packaging/release-check/verify_wheel.sh` expects `+g<commit>` and therefore rejects a correct release wheel; use a checker that validates `1.0.2`, installed import locations, provenance and the packaged checksum. The local distribution supplies that release-aware checker. This does not change the tagged SDK helper.
