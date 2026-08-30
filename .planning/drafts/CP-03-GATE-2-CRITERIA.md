# CP-03 — Gate 2 success criteria

Weighted toward the census, per Dave 2026-08-29: mechanism sabotage is necessary and is not where this rung failed. Every figure below was measured 2026-08-29 and is re-derived at the gate, never asserted from this file.

**Parsing rule: one criterion per line, never wrapped.** A wrapped criterion is read as one verification truth and hides the half below the fold.

## A · The census — each figure re-derived from the store at the gate

1. The build re-derives the restatement census from `ccf_v2.financial_fact` at gate time and reports exactly 321 groups; a hard-coded or imported constant fails the criterion.
2. The build re-derives the restated-obligor population and reports exactly 37 of 50 distinct `lei`.
3. The build re-derives the material band (relative change >= 5%) and reports exactly 175 cells across 32 obligors.
4. The build re-derives the precision band (relative change < 1%) and reports exactly 100 cells across 23 obligors.
5. The build re-derives the middle band (1% to 5%) and reports exactly 46 cells across 15 obligors, and the three bands sum to 321 with no cell counted twice.
6. The build re-derives the instant/duration split from `period_start IS NULL` and reports exactly 8,088 instant and 6,967 duration facts totalling 15,055.
7. The build re-derives Item 4.02 coverage and reports exactly 11 obligors carrying a filing, 9 of them among the 37 restated, and 28 restated obligors carrying none.
8. The build re-derives the accession census and reports 11,118 total fact-cells, 3,547 carrying more than one accession, and 3,226 carrying more than one accession at an identical value.
9. The build re-derives crosswalk coverage and reports 50 of 50 obligors resolving through `ccf_v2.crosswalk` with 0 orphans.
10. The build re-derives the fiscal-year-end distribution and reports exactly 16 of 50 obligors with a non-December latest fiscal year end, summing to 50.
11. The build re-derives revenue-tag coverage and reports exactly 1 obligor carrying none of the four revenue tags, served `NOT_EVALUABLE` and never `0`.

## B · The negative controls — a wrong method must produce a wrong number AND fail

12. Grouping on the short key `(lei, tag, period_end)` yields 410 rather than 321 and the criterion fails, so a plausible 410 cannot look green.
13. Grouping on this document's earlier invented key `(lei, tag, unit, period_start, period_end)` yields 392 rather than 321 and the criterion fails.
14. Counting distinct accessions instead of distinct values yields 3,547 rather than 321 and the criterion fails, so accession multiplicity can never be read as restatement.
15. Joining with `JOIN ... USING (period_start)` drops all 8,088 instant facts and yields 280 rather than 321 and the criterion fails, so a duration-only census cannot look green.
16. Reading the Fluree predicate count by `COUNT(DISTINCT ?p)` or `GROUP BY ?p` yields 178 or 198 rather than 171 and the criterion fails, so an aggregate can never stand in for enumeration.
17. Each control in 12 to 16 is executed as a test that asserts BOTH the wrong number and the failure, so a control that stops discriminating is itself detected.

## C · Mechanism — every gate sabotaged and observed RED

18. `OFS-G01` is sabotaged by serving a duration-only payload and observed RED.
19. `OFS-G02` is sabotaged by resolving through `financial_fact.cik` instead of `ccf_v2.crosswalk` and observed RED.
20. `OFS-G03` is sabotaged by relaxing the restatement key and observed RED.
21. `OFS-G04` is sabotaged by detecting restatement from Item 4.02 instead of value comparison and observed RED.
22. `OFS-G05` is sabotaged by opening a store other than Postgres and observed RED.
23. `OFS-G06` is sabotaged by silently honoring `as_of` instead of refusing `400 not_supported_at_tier` and observed RED.
24. `OFS-G07` is sabotaged by making an LLM client reachable from a §D step and observed RED.
25. `OFS-G08` is sabotaged by serving `0` for the revenue-less obligor instead of `NOT_EVALUABLE` and observed RED.
26. `OFS-G09` is sabotaged by anchoring the expiry on `asked_at` instead of the latest `filed_date` and observed RED.
27. `OFS-G10` is sabotaged by registering a second operator and observed RED.
28. `OFS-G11` is sabotaged by making `basis` not change the content address for a restated obligor and observed RED.
29. `OFS-G12` is sabotaged by emitting a derived line with an empty `inputs` and observed RED.
30. `OFS-G13` is sabotaged by hard-coding the restatement threshold instead of reading `artifacts/restatement.yaml` and observed RED.
31. No gate is recorded as passing until it has been observed RED at least once, and the sabotage applied to each is recorded with its observed result.

## D · Per-attribute lineage — example-local, nothing in src/

32. Every derived ratio line carries a non-empty `inputs` naming each fact-cell it consumed, asserted in `tests/examples/` and in the recipe artifact.
33. Every `inputs` entry resolves to a fact-cell present in the same served payload, so the check is closed over the payload and needs no SDK type.
34. No file under `src/` is added or modified to satisfy criteria 32 or 33, verified by diff, and an SDK type appearing there is a new ruling rather than a passing build.

## E · Determinism, replay and the printed run

35. The same request at the same pinned `asked_at` produces a byte-identical payload and content address across two runs.
36. `basis=as-reported` and `basis=latest-restated` produce different content addresses for a restated obligor and identical ones for an unrestated obligor.
37. The printed run in the README and the documentation page reproduces byte-for-byte against the named pin, and no `load_*` step appears on the demonstrated path.
38. The replay record pins the graph snapshot, the policy bundle version, the agent version and the prompt-artifact versions, and resolves exact versions rather than latest.

## F · Explicitly out of Gate 2 scope

39. The Fluree policy binding at §C.6, §C.1 element 11 and gate `OFS-G14` are specified and NOT built at this gate, and `policy_version` is sourced from the Control Plane artifact with §D stating so rather than implying Fluree.
40. The thirteen `[TBC]` rows owned by the vault, `ccf_dataprep`, identity-and-access and the product owner are not closed by this build and are not invented by it.
