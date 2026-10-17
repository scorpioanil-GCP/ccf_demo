# 383-04 (D-IMPL-383, 2026-10-16) — an opening that replays and inspects without source settings

`D-IMPL-383`, closing `CP06C-F-07`. Dave, 2026-10-16 10:23 MST, on the finding that opening a product to
inspect or replay its retained decisions demanded every source setting although nothing read a source:
*"fix it"*.

## ccf.products.product.open_product

- Surface: ccf.products.product.open_product
- Public surface: true
- Change type: reshaped
- Before: every source setting the environment document names was resolved at open; an unset one raised `EnvironmentMissing`, so an auditor without database credentials could not open the product even to replay.
- After: a keyword `read_sources: bool = True`. `False` resolves no source setting, so none need be set; every other open-time check still runs. `True` is unchanged.
- Why: `D-IMPL-383`, `CP06C-F-07`. Red tests: `tests/replay/test_replay_inspection_383.py` (2 new tests fail on `2a5c4de0`) and `tests/examples/test_cp_06_canonical_evidence_dir.py::test_the_evidence_commands_need_no_source_setting` (`EnvironmentMissing`).
- Migration: none.

## ccf.products.product.OpenedProduct

- Surface: ccf.products.product.OpenedProduct
- Public surface: true
- Change type: reshaped
- Before: `sources` was a plain attribute, and the acquisition seam read it when the governed resolver was built.
- After: `sources` is a read-only property that raises `SourcesNotRead` for an opening with `read_sources=False`; `reads_sources` says which kind of opening this is; `answer` and `resolve` raise `SourcesNotRead` before a lane is admitted, a graph minted or a record written. The acquisition seam reads `sources` only when it RUNS, so `replay_decision` — which builds the resolver and never acquires — works without them, and a replay that did reach acquisition would raise rather than read a source.
- Why: `D-IMPL-383`, `CP06C-F-07`.
- Migration: none; `opened.sources[...]` reads as before on a default opening.

## ccf.products.product.SourcesNotRead

- Surface: ccf.products.product.SourcesNotRead
- Public surface: true
- Change type: added
- Before: no such error.
- After: a `RuntimeError` naming what was attempted, raised by an opening with `read_sources=False` asked to answer or to hand out its source settings.
- Why: `D-IMPL-383`, `CP06C-F-07`.
- Migration: none.
