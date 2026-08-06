# Context Product registration

Before the delivery layer will serve a Context Product, its class has to be registered and its
maximum TTL declared. The TTL has no SDK default on purpose: how long a product stays servable
is a deployment's statement about its own risk tolerance, and a silent default would make the
TTL validation gate meaningless. Registration belongs to the Data and Context Layer pillar, and
you author it as part of the Control Plane bundle the fabric boots under.

::: ccf.products.contract.RegisteredProductClass

::: ccf.products.contract.MaxTTL

## Worked example

The product class a deployment authors. Note what it does **not** declare:
`max_ttl_version` is minted by *registering* the ceiling, so an artifact
declaring it would be authoring a hash of something it does not contain — and
Gate 3 would then be comparing a value against itself.

`required_operator_keys` is the Control Plane **claim** — the authored declared
side of the lineage gate, and the value that fills `lineage.operators_invoked`.
It is not the set the projection reads: that is a separate document,
`ccf.projection-requirements`. `ccf.deployment.refuse_operator_set_divergence`
compares the two and refuses a disagreement before the engine runs, and that is
where drift an author could introduce actually fails. Gate 2 sits downstream of
both and verifies assembly-path integrity — the engine transcribes the plan
faithfully rather than witnessing it independently, so it cannot catch a
misdeclaration (`D-IMPL-86`).

```yaml
--8<-- "examples/00-quickstart/artifacts/product-class.yaml"
```

The TTL ceiling itself, and the product's own lifetime, are two separately
authored numbers in the deployment's own governance document — which is exactly
what leaves Gate 3 something to check:

```yaml
--8<-- "examples/00-quickstart/artifacts/product-governance.yaml"
```
