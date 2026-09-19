# Correction group 1 — regression evidence

Junit results of the reruns recorded in `docs/QUALIFICATION-f0656746-CORRECTION-1.md`, measured
on `release/qualification-fixes` at `690cce3f` (working tree clean). Inside `evidence.tar.gz`:
`A_regression.xml` (products, replay, contracts, deployment), `B_regression.xml` (invariants),
`C_regression.xml` (client, conformance, controlplane, graph, halflife), `D_regression.xml` (the
remaining SDK/runtime families, smoke, surface), `E_regression.xml` (perf),
`T_gates_lints_regression.xml` (`tools/product_gates_tests` + `tools/lints/tests`),
`T_publish_docs_regression.xml` (`tools/publish_scan_tests` + `tools/docs_tests`). No connection
string appears in any of them. A copy is archived at `~/ccf_qual_evidence/f0656746-correction-1/`
on the measuring host.

## Merge qualification (fresh checkout of `7e70394c`, one-shot `make test`)

`merge-qualification.tar.gz` holds the pre-merge measurement on a fresh detached worktree of the
correction candidate (no ignored sidecars; `ccf` resolving inside it): `targets.xml` (the modules
holding the 14 tests-tree targets and the citation ratchet), `lints_tests.xml` (the 480
lint-runner controls), `one-shot-make-test.xml` + `.log` (the single `make test` invocation,
junit added through `PYTEST_ADDOPTS`, estate and local substrates exported so everything the
qualification executed ran in one process), `one-shot-reconciliation.txt` (every node by id:
pass / known deferred failure / accepted named-unexecutable / new failure / setup or collection
error / skip, xfail, xpass), and the three attribution runs of the one order-dependent failure
(`attribution_f0656746_pair.xml`, `attribution_7e70394c_pair.xml`, `attribution_7e70394c_alone.xml`).
The two manifest generations compared byte-identical to each other and to the committed file
(sha256 `d2e7a2f1f15c91a4…`) and are not stored.
