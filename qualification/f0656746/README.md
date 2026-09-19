# Qualification evidence — candidate `f0656746`

Sanitized results of the measurement-only qualification recorded in
`docs/QUALIFICATION-f0656746.md` (report commit `5c404e3f` on `main`). Every file here was
produced on the detached worktree at `f0656746ec7cfeb734dfff717f388ce8c3623b6f`; connection
strings are masked (`://***:***@`); no environment script is included.

Everything below is inside `evidence.tar.gz` (text files; packed because the repository's
documentation sweeps read loose text as documentation and counted the node lists as couplings).

| file | what it is |
|---|---|
| `A.log` … `K.log` | the ten `tests/` chunks' pytest output with `-rfEsxX` (node-level failures, skips, expected failures) |
| `leg-fluree.log`, `leg-mongo.log`, `leg-neo4j.log`, `leg-postgres.log` | the four substrate legs (`make leg-*`), run directly |
| `T_*.log` | `tools/lints/tests`, `tools/product_gates_tests`, `tools/publish_scan_tests` + `tools/docs_tests`, `tools/proof/tests` (collected 0: not in the candidate) |
| `lint.log`, `typecheck.log`, `product-gates.log`, `schema-headers.log`, `docs-strict.log`, `examples.log` | the static, schema and documentation checks |
| `collected.txt` | the single `--collect-only` of `tests/` (8 843 node ids) the chunks were reconciled against |
| `inventory.txt` | every failed and skipped node by id, with its message |
| `class_lookup.txt` | the node-by-node run of `tests/deployment/test_class_lookup.py` |
| `leg_<marker>_collected.txt` | each leg's `--collect-only -m <marker>` selection, behind the node-level skip reconciliation |

The junit XML files behind the totals are archived outside the repository at
`~/ccf_qual_evidence/f0656746/` on the measuring host; they carry the same content as the logs.
