# Half-life and context debt

Context decays, and how fast it decays is a per-observation-type calibration the SDK never
supplies — it ships the decay formula and the routing predicate, and an observation type with
no declared half-life raises rather than decaying at a rate nobody chose. Context debt is the
quantified shortfall that follows, and it is what gates forced-LLM and fail-closed behavior.

::: ccf.halflife.decay.Observation

::: ccf.halflife.decay.effective_half_life

::: ccf.halflife.debt.context_debt

::: ccf.halflife.debt.DebtFactors

::: ccf.halflife.debt.DebtSignal

::: ccf.halflife.debt.DebtFactorScorerProtocol
