# 20261011-12 — a wrong expected producer tenant is recorded `producer-tenant-mismatch`, not an outage

Dave, 2026-10-11 20:19 MST, ruling 1 (*"wrong-tenant refusal attribution"*; the `SEC353-J-02` half reported for
ruling). A consumer whose producer registration expects a tenant the producer's door will not act as for it was
refused correctly by the door's SEC-018 tenancy guard, but the dispatch filed the denial as a `tool-error` and the
row read `producer-unavailable` — "could not answer" — where the cause is a tenancy disagreement (cp-03C OFC-G18,
cp-06C CSCC-G18, cp-13C CXRC-G19, door-cp-05).

What changed: the SDK door's SEC-018 denial leads with a stable code, `ccf-tenant-not-granted`; the consumer's
`mcp_product` dispatch recognizes the code (word-bounded) and returns `McpProductFailure(failure="tenant-not-granted")`;
the question-bound child resolver records that failure as `producer-tenant-mismatch` (`outcome_status`
`unauthorized`), the reason the served path already gives the same disagreement. Any other tool error, a timeout
and an unreachable producer keep `producer-unavailable`.

Disclosure: nothing new. The denial names only the tenant the consumer itself sent, and its first line was already
the recorded `detail`. The code is the producer's word about why it refused; it can only choose between two
refusals and never admits anything.

## ccf.skills.dispatch.McpProductFailureKind

- Surface: ccf.skills.dispatch.McpProductFailureKind
- Public surface: false
- Change type: reshaped
- Before: `Literal["timeout", "unreachable", "tool-error"]`
- After: `Literal["timeout", "unreachable", "tool-error", "tenant-not-granted"]`; a tool error whose text carries `TENANT_NOT_GRANTED_CODE` is `"tenant-not-granted"`
- Why: Dave 2026-10-11 20:19 MST ruling 1. Red test: `tests/skills/test_mcp_product_dispatch.py::test_a_producer_that_cannot_answer_is_a_minted_value[tenancy-denial]`
- Migration: code that switches on `McpProductFailure.failure` handles the fourth kind

## ccf.skills.dispatch.TENANT_NOT_GRANTED_CODE

- Surface: ccf.skills.dispatch.TENANT_NOT_GRANTED_CODE
- Public surface: true
- Change type: added
- Before: absent
- After: `"ccf-tenant-not-granted"`, the code the SDK door's SEC-018 tenancy denial leads with
- Why: Dave 2026-10-11 20:19 MST ruling 1
- Migration: none

## ccf.products.child_resolver.QuestionBoundChildResolver

- Surface: ccf.products.child_resolver.QuestionBoundChildResolver
- Public surface: true
- Change type: behavior
- Before: every `McpProductFailure` became a `producer-unavailable` row
- After: a `tenant-not-granted` failure becomes a `producer-tenant-mismatch` row (`outcome_status` `unauthorized`) naming the registered producer; every other failure is unchanged
- Why: Dave 2026-10-11 20:19 MST ruling 1. Red test: `tests/products/test_d_impl_340_producer_admission.py::test_a_tenancy_refusal_by_the_producers_door_is_recorded_as_a_producer_tenant_mismatch`; control kept: `::test_any_other_tool_error_from_the_producer_stays_producer_unavailable`
- Migration: a reader that treated a wrong-tenant registration as `producer-unavailable` reads `producer-tenant-mismatch`

## ccf_runtime.mcp.tenancy.CrossTenantRefused

- Surface: ccf_runtime.mcp.tenancy.CrossTenantRefused
- Public surface: true
- Change type: behavior
- Before: the message began "the verified caller's grant does not carry tenant ..."
- After: the message begins "ccf-tenant-not-granted: the verified caller's grant does not carry tenant ..."; the rest is unchanged
- Why: Dave 2026-10-11 20:19 MST ruling 1; the code lets a consumer name the refusal without parsing prose
- Migration: none
