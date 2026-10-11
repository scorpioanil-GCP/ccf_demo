# Example amendments — 2026-10-11 (Dave's Tuesday GO: compatibility repairs authorized)

One line per repair: example · file · what changed · why · finding id.

- cp-03-canonical-obligor-financial-spread · ccf_config.yaml · appended `temporal_boundary: {max_past_seconds: 3600, permitted_clock_skew_seconds: 0}` with the illustrative-calibration disclosure (hw1-companies-over-revenue precedent values) · every governed serve refused `temporal-boundary-undeclared` (D-IMPL-358 ruling 11 made the declaration mandatory; the tree predates it) · SEC358-G-01 / G2-F-02
- cp-04-canonical-corporate-family-tree · ccf_config.yaml · same `temporal_boundary:` declaration · same reason · SEC358-G-01 / G2-F-02
- cp-06-canonical-collateral-and-setoff-coverage · ccf_config.yaml · same `temporal_boundary:` declaration · same reason · SEC358-G-01 / G2-F-02
- cp-04-canonical-corporate-family-tree · tests/examples/test_cp_04_canonical_output.py (CFC-G05) · the dimension-2 key assertions read the tenant-placed keys (`{tenant}/request_contract`, `{tenant}/policy`) instead of the bare names; the assertion (request contract recorded in dimension 2, dimension 2 strictly wider than the policy) is unchanged · D-IMPL-354 places every manifest key under the tenant · SEC353-G-07 class / G2-F-03
- cp-06-canonical-collateral-and-setoff-coverage · tests/examples/test_cp_06_canonical_output.py (CSCC-G11) · `{tenant}/request_contract` instead of `request_contract` in the dimension-2 assertion · same · SEC353-G-07 class / G2-F-03
- cp-03-canonical-obligor-financial-spread · tests/examples/test_cp_03_canonical_output.py (OFC-G09) · the shadow probe reads `booted.artifacts[booted.keys.request_contract]` instead of the bare `"request_contract"`; the asserted refusal ("shadow") is unchanged and now observed again · same · SEC353-G-07 class / G2-F-03
