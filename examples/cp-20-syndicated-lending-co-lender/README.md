# cp-20 — Syndicated Lending Co-Lender

**Rung 20 · two fabrics belonging to two organizations · `cb.syndicate-co-lender`**

Reading a governed Context Product from **another bank's fabric**, under a
negotiated bilateral envelope, and composing it with what we hold ourselves.

## What this demonstrates

A syndicate amendment needs lender consent. The filed credit agreement sets the
standard — **Required Lenders, 50 %**, anchored to the EX-10 span it was parsed
from — and no single member can tell whether it is reachable, because each holds
only its own share. The mechanism today is a phone call.

This rung replaces the phone call with a contract. The composite asks a
**second organization's deployment**, under its own tenant, at an endpoint it
never sees the address of, and admits the answer only if that answer is held to
the registration the consumer declared.

Five things the rung exists to show:

1. **Cross-organizational admission is the same mechanism as any other.** The
   child is governed under `cp-20-peer-demo`; the composite is `cp-20-demo`;
   the two are never set equal to let it pass. "Another organization" is domain
   framing over what `D-IMPL-340` already ships.
2. **The envelope has two sides, and they differ.** Bank of America's envelope
   lets us request `member_commitment` and `own_position`; Citibank's lets us
   request `amendment_vote_posture` only. So **Citibank's position is not
   requestable**, and the refusal is the demonstration.
3. **An unattested claim is refused, not discounted.** The peer publishes no
   attestation record behind one of its positions. It refuses to assert it —
   and that refusal refuses this composite **even though the slot is
   optional**.
4. **A band never becomes a number.** Citibank discloses at band precision.
   The peer serves the two bounds and no `share_usd` key at all; a midpoint is
   a figure nobody disclosed.
5. **Local and remote claims are kept apart.** Ours are
   `local-reconstructible`; the peer's are `remote-attested`, derived from the
   admitted child's own tenant. An examiner can tell which is which, and the
   replay record names who was asked what.

## Run it

Two processes, because there are two organizations. The peer's connection
material lives in `~/.bashrc`, which returns early for non-interactive shells,
so **everything here runs under `bash -ic`**.

```bash
# our own estate
export CCF_CP_20_POSTGRES_DSN='host=… port=… dbname=… user=… password=…'
export CCF_CP_20_POSTGRES_SCHEMA=ccf_v2
export CCF_CP_20_FLUREE_URL=http://192.168.4.76:8090
export CCF_CP_20_FLUREE_LEDGER=fibo-v2           # NOT `fibo:main` — that is v1

# the co-lender's estate (the peer's own deployment reads these, we never do)
export CCF_CP_20_PEER_POSTGRES_DSN="host=$CO_LENDER_HOST port=$CO_LENDER_PG_PORT dbname=$CO_LENDER_PG_DB user=$CO_LENDER_PG_USER password=$CO_LENDER_PG_PASSWORD"
export CCF_CP_20_PEER_POSTGRES_SCHEMA=colender
export CCF_CP_20_PEER_FLUREE_URL="$CO_LENDER_FLUREE_URL"
export CCF_CP_20_PEER_FLUREE_LEDGER="$CO_LENDER_FLUREE_LEDGER"

# 1. the co-lender's door, in its own process
export CCF_CP_20_PEER_DOOR_TOKEN=dev-token
.venv/bin/python examples/peer-cp-20-co-lender/run.py --door
# prints: READY <port>

# 2. our composite, in another
export CCF_CP20_PEER_URL=http://127.0.0.1:<port>/mcp
export CCF_CP20_PEER_TOKEN=dev-token
.venv/bin/python examples/cp-20-syndicated-lending-co-lender/run.py --include-federated
```

Omit `--include-federated` and no boundary is crossed — which is the default,
deliberately.

## The story

### The default is `false`, and that is a legal position

Reaching across an organizational boundary has consequences, so it never
happens because a default made it happen. `include_federated` defaults to
`false`, and the two values are **different questions**: they hash to different
content addresses, so a domestic answer can never be served from a federated
one's cache.

Omitting the child is not free. The class declares what the absence costs —
`completeness_when_absent: 0.50` — and the domestic answer's Context Debt is
measurably worse than the federated one's. Measured on `FAC-6F4065`:
`D_c = 0.50` domestic, `D_c = 0` federated.

### The envelope's two scopes are two sets

| counterparty | may we ask them for | may we tell them |
| --- | --- | --- |
| Bank of America | `member_commitment`, `own_position` | `syndicate_composition`, `amendment_vote_posture` |
| Citibank | `amendment_vote_posture` | `syndicate_composition` |

Read one predicate for both purposes and Citibank becomes askable. It is not.
The ask is refused **by name, before any peer is called** — and the proof that
no peer was called is the refusal's *kind*: `subject-unavailable` comes from
the acquisition seam, which runs strictly before child resolution, while a
refusal reached after a producer answered is `child_admission`. This rung
produces both, against the same live door.

### The consent arithmetic, and what the peer actually adds

Our own share on `FAC-6F4065` is **$61,500,000** against a filed schedule
totalling **$950,000,000** — 6.47 %, nowhere near Required Lenders. Admit Bank
of America's attested **$187,000,000** and the known consent reaches
**26.16 %**. Still short, and that is the honest answer: the two largest
lenders together do not carry an amendment.

Each member counts **once**. Bank of America appears in the filed commitment
schedule *and* declares its own position; summing both would double-count.
What the peer adds is not a bigger number — it is corroboration under
attestation, plus its own rating, posture and declared terms.

### Where two authorities disagree, both are served

The filed participations total $950 m; `ccf_v2.facility.commitment_amount` for
this facility says $500 m. They disagree, the product says so in `findings`,
names which denominator the consent arithmetic used, and serves the other
beside it. Neither is silently dropped.

## Artifact-by-artifact

| file | what it carries |
| --- | --- |
| `ccf_config.yaml` | the class, the one optional child requirement, the operators, the request contract, and the ONE producer registration — an identity and a tenant, never an address |
| `ccf_environment.yaml` | where our two stores live, and the one endpoint the peer is reached at. No peer store appears |
| `artifacts/source-vocabulary.yaml` | our estate's tables, columns and IRIs |
| `artifacts/federation-policy.yaml` | the class we may request across the boundary, the two scope predicates, and the declared-latency bound |
| `artifacts/consumer-chain.yaml` | the agent, the skill and the two pins the paved road would have derived — see *What would fail* |
| `artifacts/gates.yaml` | the twenty declared gates and their observed reds |
| `../peer-cp-20-co-lender/` | **the co-lender's own deployment**, in its OWN tree: its config, its two source legs, its projection, its spine and its door. It is a different organization, so it is not a subdirectory of ours — one `examples/cp-*` tree is one deployment, and this rung is two |

## Whitepaper / CLAUDE.md sections exercised

Whitepaper §8.3 Pattern 4 (A2A federation and the trust boundary), §7.6
(Context Product contract and the three validation gates), §7.4 (operator
composition, Policy first), §7.10 (Decision Replay). CLAUDE.md §7.2 (A2A
first-class), §7.3 (the neutral seams), §10 (single-writer across the
boundary), §6.2 (skilling and the grant the composite's agent holds).

Decisions: `D-IMPL-340` (cross-deployment child acquisition), `D-IMPL-336`
(composition, and F1 — optional means optional absence), `D-IMPL-31`/`D-IMPL-104`
(the composition laws), `D-IMPL-343` (the paved road), `D-IMPL-323`
(illustrative calibration), `D-IMPL-326` (gate acceptance authority).

## What to change first

Point it at your own counterparty. The request contract's `counterparties`
takes LEIs; the envelope is read from your own graph; the producer
registration names a logical server and two environment variable *names*.
Nothing in the code knows a bank.

### Illustrative calibration

> **Illustrative calibration:** This example runs against a point-in-time
> demonstration estate rather than continuously refreshed production data.
> Freshness half-lives and related thresholds are calibrated to make the
> governed behavior observable in that snapshot. They demonstrate how the SDK
> applies these controls and should not be interpreted as recommended
> production coverage-policy thresholds.

Specifically: the four-hour class TTL, the six-hour peer class TTL, the
5 000 ms declared-latency bound, the 0.95 debt tolerance and every `λ_c` in
both `ccf_config.yaml` files. The peer's positions are stamped `2026-08-26`;
the peer anchors its TTL `from_decision` for that reason, and the reason is
stated in its config rather than left to be inferred.

## What would fail

**The `build_children=` cost, and it is the rung's headline friction.**
`include_federated` is a *request* parameter, and the only seam that can honor
one is child resolution — which `open_product` reaches through
`build_children=`. That keyword is **refused beside a declared `agent:` or
`skills:` section**, so this deployment may not declare its chain at all.
Rebuilding it by hand costs **130 executable lines plus 40 lines of artifact**;
the feature itself — the flag check and an empty return — is **four of them**.
Recorded as `CLD-F-04` and raised for a decision, not worked around.

**A governed refusal raised from the child-resolution seam escapes as an
exception.** `GovernedResolver` catches `GovernedRefusalRaised` around the
acquisition seam and nowhere else. The envelope check therefore lives in
`acquire` — where it also belongs, and where no peer has yet been called.
Recorded as `CLD-F-06`.

### What this rung does NOT prove

**`CLD-G04` is `unavailable` by ruling.** An admitted child's expiry becoming
the composite's binding TTL floor is unreachable here: the only two peer
declarations shorter than the four-hour ceiling are exactly the two the
governance rules refuse — Citibank's is out of envelope, Bank of America's is
unattested. That is an **engineered-estate limitation, not an SDK defect**;
`CLD-G05` proves the floor rule on its ceiling-binding arm; and **residual
`341-4` remains carried**. Nothing is manufactured to retire it.

It also does not prove the **reverse direction** — the peer's agent at our
door — which is out of the first proof by ruling, nor Route B peering, nor
anything about A2A transport, which rung 22 settled as outside the contract.
