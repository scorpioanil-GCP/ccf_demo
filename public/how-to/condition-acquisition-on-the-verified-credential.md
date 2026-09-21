# Condition acquisition on the verified credential

Build a product whose **contents** depend on who is asking — not merely whose
access is checked at the door. An analyst and a reviewer ask the same question
of the same subject at the same instant and receive structurally different
Context Products, because the bound on what may be assembled was derived from
each caller's verified credential before anything was assembled.

This page is the generative recipe for that seam. It is deliberately short: the
seam is about fifteen lines, and the four facts below are what make those
fifteen lines correct rather than plausible.

## The rule everything else follows from

**A policy input that arrives in the request is not a policy input.** If the
caller can state which classifications it may see, which jurisdictions it may
reach, or which corpus it may search, then the caller has stated its own
entitlement and the fabric has merely believed it. The bound has to come from
the credential the door already verified.

That credential reaches your code at exactly one place.

## What each side supplies

| | Supplied by |
|---|---|
| The verified identity and role, as `AcquisitionContext.perspective` | **the SDK** — the door resolved it from the credential; the request contract never declares a `perspective` argument |
| The effective request — class defaults and policy bounds already folded — as `AcquisitionContext.request` | **the SDK** |
| Source settings by name, as `AcquisitionContext.sources` | **the SDK**, from your deployment's environment document |
| Reading the envelope's inputs out of your own stores | **you** — this is product-specific policy logic |
| Deciding what that envelope admits | **you** — these are domain values and belong in your artifacts, never in SDK code |
| Emitting only admissible claims as `SignalEnvelope`s | **you** |
| Ingesting them through the single writer, running the operators, gating and recording | **the SDK** |

The division is sharper than it looks. The SDK supplies the *authority* — a
verified principal and role you did not have to establish. You supply the
*meaning* — what that role is entitled to in your domain. Nothing in the SDK
knows what a reviewer may see, and nothing in your code has to decide whether
the caller is really a reviewer.

## The seam

```py
from ccf.products.product import AcquisitionContext, open_product
from ccf.products.refusal import (
    RESOLVED_BY_THE_RESOLVER,
    GovernedRefusalRaised,
    SubjectUnavailableRefusal,
)
from ccf.signal.envelope import SignalEnvelope, SourceIdentity


class NoEnvelopeForRole(RuntimeError):
    """This deployment admits nothing for that role. Yours to define."""


def acquire(context: AcquisitionContext) -> tuple[SignalEnvelope, ...]:
    """The whole of the seam: five steps, and only the middle one is yours."""
    # 1. THE CREDENTIAL. Never `context.request.parameters`.
    role = context.perspective.role

    # 2. YOUR ENVELOPE, from your own stores, keyed by that role. This call is
    #    product-specific policy logic and the SDK has no opinion about it.
    try:
        envelope = admissible_for(role, sources=context.sources)
    except NoEnvelopeForRole as absent:
        # 4. A GOVERNED REFUSAL, as data, through the one recorder — never a
        #    bare raise. The caller receives a refusal with a replay reference;
        #    the record retains the cause the wire shell withholds.
        raise GovernedRefusalRaised(
            SubjectUnavailableRefusal(
                cause="unauthorized",
                detail=str(absent),
                error_code="no-envelope-for-role",
            ),
            resolution=RESOLVED_BY_THE_RESOLVER,
        ) from absent

    # 3. THE EFFECTIVE REQUEST — defaults and bounds already folded by the SDK.
    claims = read_your_estate(
        subject=context.request.subject,
        asked_at=context.request.asked_at,
        parameters=context.request.parameters,
        admits=envelope,          # the bound is an ARGUMENT to the read...
        sources=context.sources,  # ...never a predicate over its results
    )

    # 5. ONLY ADMISSIBLE CLAIMS, edges before attributed nodes.
    return (
        *(_edge(claim, context) for claim in claims),
        *(_node(claim, context) for claim in claims),
    )


def _node(claim, context: AcquisitionContext) -> SignalEnvelope:
    return SignalEnvelope(
        tenant_id=context.tenant_id,
        envelope_id=f"node/{claim.entity_uri}",
        source=SourceIdentity(system_id="your-deployment"),
        ingestion_timestamp=context.instant,
        observed_time=claim.when_it_was_true_in_the_world,  # or None
        raw_payload={"your_match_key": claim.entity_uri, **claim.attributes},
    )


opened = open_product(
    config_root=HERE, scratch=scratch,
    acquire=acquire, project=plan_factory, assess=assess, gate=your_gate,
)
```

Step 2's placement is the load-bearing part. **The envelope is an argument to
the read, never a filter over its results.** A post-filter has already asked
your store for material the caller may not see, and in a confidentiality
context that query is itself the disclosure. A claim the envelope excludes is
never minted, so nothing downstream can serve it by mistake.

## Four facts the rest of this surface does not state

These are the ones adopters rediscover. Each is a property of the SDK, not of
any particular product.

### 1. `AcquisitionContext.perspective` is the only seam

It is the one place a verified credential reaches an operator's bound without
becoming a caller claim. There is deliberately no channel by which the
credential reaches an operator's parameters directly: operator parameters are
Control Plane artifacts, and a per-caller artifact would be a per-caller
Control Plane. So the narrowing happens here, before the fabric exists, and the
operators run over a per-request fabric that already contains only admissible
material.

### 2. The Policy operator's permitted set is class-level

`permitted_classifications` on the Policy operator is a property of the
**product class**, declared once in your deployment configuration. It is not
per-principal and cannot be made per-principal. Its job is containment: a claim
carrying a classification outside the product's whole vocabulary is removed
before anything ranks or walks, whoever is asking.

The consequence is the one worth writing down: **per-perspective narrowing
happens before the Policy operator executes, not inside it.** The operator is
your containment guarantee; the seam above is your entitlement. Expecting the
operator to be the wall is the most common way this pattern is got wrong.

### 3. `observed_time` is the claim's `valid_from`

`SignalEnvelope.observed_time` is when the event occurred *at the source*.
Assembly carries it through as the claim's `valid_from`, while
`ingestion_timestamp` becomes `observed_at` — when the fabric learned it.

Two things follow. A class whose half-life row declares `decay_basis:
valid-from` reads this field as its freshness clock, so a claim you left at
`None` has no age the curve can measure. And `None` **stays** unknown: it is
never backfilled from ingestion, because substituting *when we learned it* for
*when it became true* mints a claim about the world that no source made.

### 4. Emit edges before attributed nodes

Claims at one entity URI form a supersession chain, and the later claim wins.
An edge mints both of its endpoints as **thin** claims — identity only, no
attributes — so an edge written after a rich node replaces that node's
attributes with nothing, and the view serves an entity stripped of everything
you read for it.

Order your emission edges first, attributed nodes last. If one entity is an
endpoint of many edges, write its attributed node after all of them.

## Never from caller-stated request data

The request contract should not declare, and your seam must not read from
`context.request.parameters`:

- the perspective, principal, role, or any alias for them;
- the classification, sensitivity or clearance set the caller may receive;
- the corpus, document class, jurisdiction or population it may reach;
- any identifier whose only purpose is to select a policy row.

A request naming an undeclared parameter is refused by the SDK as a contract
violation, which is the behavior you want: it makes an attempt to state one's
own entitlement a refusal rather than a quiet success.

What legitimately *does* belong on the request is anything that narrows within
an entitlement already held — a decision instant, a traversal depth, a debt
tolerance. The test is simple. If stating a different value could get the
caller **more** than its credential permits, it is envelope input and belongs
at this seam. If it can only get the caller **less**, or the same amount shaped
differently, it is a request parameter.

## Where this is exercised

Three shipped producers derive their envelope this way, over three different
estates and three different bounds:
`examples/cp-13-canonical-covenant-cross-reference`,
`examples/cp-17-mnpi-wall-enforcement` and
`examples/cp-19-aml-typology-match`. Their envelope *implementations* have
almost nothing in common — different stores, different keys, different refusal
conditions — which is why this page teaches the seam and not a helper.
