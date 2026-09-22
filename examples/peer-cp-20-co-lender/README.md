# peer-cp-20-co-lender — the other bank's deployment

**A SECOND ORGANIZATION's fabric.** This tree is not ours. It stands in for
**Bank of America as syndicate co-lender**, where the estate behind
`examples/cp-20-syndicated-lending-co-lender` is JPMorgan Chase Bank, N.A.

It is a supporting producer for rung 20 and **not a ladder rung**, which is
why it sits outside the `examples/cp-*` glob — the same place
`door-cp-05-credit-exposure-rollup` sits, and for the same reason.

**It is a separate directory because it is a separate deployment.** One
`examples/cp-*` tree is one deployment, with one spine and one runner; rung 20
is two organizations, so it is two trees. Nesting this inside the consumer's
would have said the opposite, and `tests/examples/test_spine_separation.py`
says so too.

## What it serves

One Context Product — `cb.co-lender-position` v1.0.0, under tenant
`cp-20-peer-demo` — answering *what is this member's position in this
syndicated facility*, at **the precision that member discloses at**:

* an `exact` member carries `share_usd`;
* a `band` member carries `band_low` and `band_high` and **no `share_usd` key
  at all**, because a midpoint is a figure nobody disclosed;
* a position with **no attestation record** behind it is **refused**, not
  served with a caveat and not discounted by Context Debt.

Its own stores are its own: Fluree on port `8091` (ledger `bofa/syndicate`)
and Postgres schema `colender` in database `bofa_syndicated`. The consumer
never touches either — it reaches this deployment at one endpoint, through the
door below.

## Run it

The peer's connection material lives in `~/.bashrc`, which returns early for
non-interactive shells, so everything runs under `bash -ic`.

```bash
export CCF_CP_20_PEER_POSTGRES_DSN="host=$CO_LENDER_HOST port=$CO_LENDER_PG_PORT dbname=$CO_LENDER_PG_DB user=$CO_LENDER_PG_USER password=$CO_LENDER_PG_PASSWORD"
export CCF_CP_20_PEER_POSTGRES_SCHEMA=colender
export CCF_CP_20_PEER_FLUREE_URL="$CO_LENDER_FLUREE_URL"
export CCF_CP_20_PEER_FLUREE_LEDGER="$CO_LENDER_FLUREE_LEDGER"

# ask it directly
.venv/bin/python examples/peer-cp-20-co-lender/run.py
.venv/bin/python examples/peer-cp-20-co-lender/run.py --facility FAC-A4A5EE          # refused: unattested
.venv/bin/python examples/peer-cp-20-co-lender/run.py \
    --facility FAC-405B7A --counterparty E57ODZWZ7FF32TWEFA76                        # band precision

# or serve it, which is what rung 20 does
.venv/bin/python examples/peer-cp-20-co-lender/run.py --door                          # prints READY <port>
```

## The attestation control is two mechanisms, and neither satisfies the other

1. **`deployment.acquire` raises a governed refusal** when no attestation
   record stands behind the declaration. That is the control that fires: a
   `RefusalEnvelope`, as data, with a replay reference and the typed code
   `unattested-position`.
2. **The policy operator removes an `unattested` entity from the view** if one
   ever reaches assembly.

The second alone would be insufficient, and the reason is worth knowing: **a
policy-emptied view is SERVED, not refused** (`D-IMPL-242` amendment 1, and
cp-17's `Q8`). Measured 2026-09-22 — the first version of this tree had only
(2) and served an empty product where a refusal was owed.

## Gates

This tree carries no roster of its own; the invariants it must hold are
rung 20's, declared in
`examples/cp-20-syndicated-lending-co-lender/artifacts/gates.yaml` and
exercised by `tests/examples/test_cp_20_peer_and_identity.py`. `CLD-G06` and
`CLD-G13` are the two that live here.
