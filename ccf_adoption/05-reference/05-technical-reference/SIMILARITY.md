# Similarity

**Primary package:** `ccf.similarity`  
**Current SDK reference baseline:** `drcastillo/ccf_code/v1.0.2@5f85b389efe9e4b1de62e84a5af62ca4b2e12178`\
**Release:** `v1.0.2` @ `5f85b389efe9e4b1de62e84a5af62ca4b2e12178` (17 October 2026)

Similarity is one L4 computation category, not a replacement for policy or temporal semantics.

## Public mechanisms

The qualified surface includes:

- similarity-index protocol;
- embedder protocol/reference utilities;
- SQLite-vector index;
- Chroma index.

## Operator use

`SimilaritySelect` is the canonical L4 operator for similarity selection.

Its corpus must come from a governed view/boundary. Do not build a similarity index over rows that policy would have removed.

## Policy before Similarity

This ordering is load-bearing for restricted-context products.

If similarity runs first over a wider corpus and policy filters later, ranking behavior can leak facts about restricted candidates even when the final row is hidden.

CP-17 and CP-19 are the clearest examples.

## Configuration

Similarity parameters belong in declared operator-parameter artifacts/configuration.

Embedding/index implementation belongs to the deployment/platform.

## When not to use similarity

Do not insert vector search merely because data is unstructured.

If the decision can be answered deterministically with exact relationships, temporal filters or structured claims, prefer the deterministic mechanism.

## Evidence and Debt

Similarity selection does not exempt the product from:

- source provenance;
- temporal validity;
- policy;
- completeness;
- Debt assessment;
- product gates.

