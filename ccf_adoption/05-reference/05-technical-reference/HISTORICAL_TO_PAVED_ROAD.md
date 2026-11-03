# From Historical Examples to the Paved Road

The repository intentionally preserves historical examples. They are evidence of SDK evolution, not a mandate to keep writing products the old way.

## The smell

If a new product's `produce.py` contains substantial code for:

- Control Plane registry creation;
- boot;
- effective-request derivation;
- direct ingest loop;
- operator registry assembly;
- product-class registration;
- `run_gates`;
- record construction;
- artifact-store plumbing;
- `serve`;
- manual door wiring;

stop and compare it with a qualified canonical successor.

## Paved-road replacement

Normal new product code should bind its domain callables to:

`ccf.products.product.open_product(...)`

and ask via:

`OpenedProduct.answer(...)`

The SDK owns the invariant-heavy path.

## Canonical successor pairs

| Historical | Current copy target |
|---|---|
| `cp-03-obligor-financial-spread` | `cp-03-canonical-obligor-financial-spread` |
| `cp-04-corporate-family-tree` | `cp-04-canonical-corporate-family-tree` |
| `cp-06-collateral-and-setoff-coverage` | `cp-06-canonical-collateral-and-setoff-coverage` |
| `cp-13-covenant-cross-reference` | `cp-13-canonical-covenant-cross-reference` |

## What moved

### Into the SDK facade

- config/environment loading;
- boot;
- effective request;
- ingestion boundary;
- product registration/binding;
- standard gates;
- governed refusal recording;
- artifact-store/evidence plumbing;
- serving.

### Stays with the product author

- source access;
- product/domain vocabulary;
- envelope mapping;
- projection;
- Debt measurement over the governed view;
- product-specific declared predicate;
- presentation/demo.

## What did not change

The SDK getting easier does not reduce the specification obligation.

A paved road with an unapproved or invented design only makes it faster to build the wrong product.

## AI codegen instruction

When Cowork finds both a historical and canonical tree:

1. read historical only to understand the business problem/evolution if needed;
2. take structural implementation precedent from the canonical successor;
3. retain the historical evidence pin when explaining a specimen; the former cp-example freeze was lifted by D-IMPL-386, so current execution guidance must follow the current SDK README;
4. never copy historical low-road plumbing into the new product merely because it is explicit.
