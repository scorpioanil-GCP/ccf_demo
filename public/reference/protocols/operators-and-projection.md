# Operator and projection Protocols

Operators are pure, read-only transformations over graph state, and they compose — the
composition-preservation property is what makes a decision replayable rather than merely
re-runnable. Projection consumes an operator plan and conditions the result for a perspective;
the acquisition surfaces let a projection reach for content at decision time without ever
acquiring a write handle.

::: ccf.operators.base.Operator

::: ccf.projection.plan.ProjectionPlan

::: ccf.projection.acquisition.ContentAcquirer

::: ccf.projection.acquisition.ContentAcquiringPlan
