# Context Product registration

Before the delivery layer will serve a Context Product, its class has to be registered and its
maximum TTL declared. The TTL has no SDK default on purpose: how long a product stays servable
is a deployment's statement about its own risk tolerance, and a silent default would make the
TTL validation gate meaningless. Registration belongs to the Data and Context Layer pillar, and
you author it as part of the Control Plane bundle the fabric boots under.

::: ccf.products.contract.RegisteredProductClass

::: ccf.products.contract.MaxTTL

## Worked example

A Control Plane bundle declaring the product class and its TTL bound alongside the operator
parameters and policy bundle the same fabric boots under.

```yaml
--8<-- "examples/00-quickstart/artifacts/controlplane.yaml"
```
