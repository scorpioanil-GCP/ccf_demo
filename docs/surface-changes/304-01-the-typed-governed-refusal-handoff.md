# 304-01 — the typed governed-refusal handoff

Recorded at the `f0656746` qualification (2026-09-19) from the introducing commit `30c59397`
(*feat(D-IMPL-304): the typed governed-refusal handoff, caught at the delivery boundaries and
the acquisition seam*, 2026-09-18; merged at `D-GATE-304`), which shipped without a
surface-change fragment. The carry `D-IMPL-304` named: pre-assembly request resolution could
refuse before the canonical replay/refusal boundary, producing a runtime failure instead of a
replay-recorded governed refusal. This fragment claims exactly the three public names
`30c59397` added to `ccf.products.refusal`; the catch sites at the delivery boundaries and the
resolver's acquisition seam are behavior inside existing names.

## ccf.products.refusal.GovernedRefusalRaised

- Surface: ccf.products.refusal.GovernedRefusalRaised
- Public surface: true
- Change type: added
- Before: absent — a governed determination made where it could not be returned (a deployment's acquisition hook, a composition root's acquisition callable) surfaced as an ordinary exception and never reached the one recorder
- After: an `Exception` subclass constructed with `refusal` — a value of a type `REFUSAL_KINDS` names, or an envelope built from one — and a required `resolution`: the `EffectiveRequest` evidence the raiser holds, an explicit `ResolutionNotApplicable`, or `RESOLVED_BY_THE_RESOLVER` inside a resolver's own acquisition seam; refused at construction otherwise. The delivery boundaries and the acquisition seam catch exactly this type, record it through the one recorder and deliver it through the normal disclosure and emission path
- Why: `D-IMPL-304` (`30c59397`) — an explicit handoff, never a translation: raised only by code that already holds a refusal the fabric produced, so a refusal made anywhere on the governed spine is replay-recorded and disclosed like every other
- Migration: none for a deployment that returns its refusals; a deployment's acquisition hook that must refuse from where it cannot return raises `GovernedRefusalRaised` with the refusal it holds and the resolution state it is in

## ccf.products.refusal.ResolvedByTheResolver

- Surface: ccf.products.refusal.ResolvedByTheResolver
- Public surface: true
- Change type: added
- Before: absent
- After: the one explicit resolution state a raiser inside a resolver's own seams may state — *the resolver that called me holds the resolution* — because such a raiser holds the effective question and not the `EffectiveRequest` evidence the resolver established on the way there. A statement, never a default
- Why: `D-IMPL-304` (`30c59397`) — the resolution state on the handoff is required, and the acquisition seam needed a truthful value to require
- Migration: none

## ccf.products.refusal.RESOLVED_BY_THE_RESOLVER

- Surface: ccf.products.refusal.RESOLVED_BY_THE_RESOLVER
- Public surface: true
- Change type: added
- Before: absent
- After: `Final[ResolvedByTheResolver]` — the single instance, compared by identity
- Why: `D-IMPL-304` (`30c59397`) — one value to state, one value to compare against
- Migration: none
