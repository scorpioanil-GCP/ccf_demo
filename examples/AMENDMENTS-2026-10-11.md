# Example amendments — 2026-10-11 ("make examples actually run", Dave 14:51 MST)

One line per compatibility repair: example · file · what changed · why · finding id. Historical
transcripts and findings are preserved; nothing here changes a governed value, threshold, expected
business result or security assertion.

- s1-00-companies-over-revenue · deployment.py `read()` · reads every Control Plane key from `booted.keys` (placed `{tenant}/…` strings) instead of bare section names, and hands the same placed keys to the resolver · the loader places keys under the tenant (D-IMPL-354); bare read raised `KeyError: 'request_contract'` · SEC353-G-07
- s1-00-companies-over-revenue · produce.py · `FileArtifactStore(..., write_kinds=WriteKinds.declare({replay, query-pin, admitted-child: ReplayMint}))`, s1-01's shape · `write_kinds` became a required argument (D-IMPL-353 §1.2) · G1-S100-F02
- s1-00-companies-over-revenue · ccf_config.yaml · added `temporal_boundary: {max_past_seconds: 3600, permitted_clock_skew_seconds: 0}` (hw1-companies-over-revenue's values, labeled illustrative) · undeclared boundary refuses every serve (D-IMPL-358 ruling 11) · SEC358-G-01
- s1-00-companies-over-revenue · README.md §1 · labeled the old output block historical, showed the current governed refusal for the default question, and documented the `--as-of now` command that serves · pinned 2026-08-01 instant is outside the bound and past TTL on Postgres (demonstration serve instant is dev-substrate only, D-IMPL-378 C1) · G1-S100-F03
