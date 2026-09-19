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
