# 383-02 (D-IMPL-383, 2026-10-16) — a distinct `evidence_root`; `scratch` is ephemeral again

`D-IMPL-383`. Dave, 2026-10-16 06:27 MST: *"Leaving it as 'scratch' and using it for durable filesystem
evidence is a hack."* His ruling, 06:30: *"introduce a distinct `evidence_root` parameter. Do not reuse
`scratch` for durable evidence."* This replaces 383-01's *"The evidence root is now the paved road's
`scratch`"*: the evidence root is `evidence_root` when supplied, and `scratch` only when it is not.

## ccf.products.product.open_product

- Surface: ccf.products.product.open_product
- Public surface: true
- Change type: reshaped
- Before: `scratch` held the per-question graphs, the default file-backed replay store (with its erasure index) and the decision → graph index; a deployment that wanted durable replay evidence had to hand over a persistent `scratch`.
- After: a keyword `evidence_root: Path | str | None = None`. Supplied, the per-question graphs, the default replay store and its erasure index, the decision → graph index and the SDK-managed writer-lock directory live under it, and `scratch` holds only what need not survive the process. `None` keeps everything under `scratch`, as before. Refused at open with `ValueError`: an `evidence_root` inside `config_root`, or one that and `scratch` lie one inside the other. The SDK never reads an environment variable for it.
- Why: `D-IMPL-383`, Dave 2026-10-16. Red tests: `tests/replay/test_replay_evidence_383.py` (18 of its 19 tests red on `c09cdd51`; the one green is a docstring check: `open_product() got an unexpected keyword argument 'evidence_root'`).
- Migration: none for a caller that passes no `evidence_root`. A deployment that relied on a persistent `scratch` for durable evidence passes that folder as `evidence_root=` and a temporary directory as `scratch`; the layout under the folder is unchanged.

## ccf.products.product.OpenedProduct

- Surface: ccf.products.product.OpenedProduct
- Public surface: true
- Change type: reshaped
- Before: no `evidence_root`; graphs were minted under `scratch` and `evidence` indexed `scratch`.
- After: an `evidence_root` attribute (the `scratch` path when none was supplied); graphs are minted under it and `evidence` indexes it. `open_product` is the only constructor.
- Why: `D-IMPL-383`, Dave 2026-10-16.
- Migration: none.
