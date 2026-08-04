# Context Product contract

The Context Product Contract is the SDK's stable wire surface: everything that crosses a
process, a harness or an organizational boundary crosses as one of these. `CCFContract` is the
typed base every contract inherits. The gate surfaces below are the three validation gates a
product must clear before the delivery layer will serve it — an empty operator plan, a lineage
mismatch and a TTL breach are each a refusal, never a warning.

::: ccf.contracts.base.CCFContract

::: ccf.products.contract.ContextProductContract

::: ccf.products.contract.ProductLineage

::: ccf.products.contract.RegisteredProductClass

::: ccf.products.contract.MaxTTL

::: ccf.products.gates.run_gates

::: ccf.products.gates.ServableProduct

::: ccf.products.gates.EmptyOperatorRefusal

::: ccf.products.gates.LineageMismatchRefusal

::: ccf.products.gates.TTLRefusal
