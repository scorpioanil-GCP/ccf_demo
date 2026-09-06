# 24.7 close-time panel — bundle-tests-part-3.md

Subject: the SHIPPED tree of `phase-24.7` at `ad8dc5a9` (tests/, perf/, tools/, pyproject.toml), diff base `6a019322`.
Read `prompt.md` for the instruction and `known-findings.md` for what NOT to re-derive.
Feed this file via STDIN, never as an argv string. Quote the line below verbatim in your review;
a review that does not quote it is recorded as a failed reviewer, not a reviewer.

```
READ-PROOF bundle-tests-part-3.md: 32f728a6347fe743
```

Subjects in this part (1): `tests/examples (25 files, markers only)`


<!-- mid-payload read-proof -->
```
READ-PROOF bundle-tests-part-3.md: 32f728a6347fe743
```

## tests/examples — diff 6a019322..HEAD: quarantine markers and D-IMPL-265 module marks ONLY (criterion 21: 0 lines removed)

```diff
diff --git a/tests/examples/test_agent_basics_output.py b/tests/examples/test_agent_basics_output.py
index 52955bea..86e12bdf 100644
--- a/tests/examples/test_agent_basics_output.py
+++ b/tests/examples/test_agent_basics_output.py
@@ -134,6 +134,7 @@ from ccf.controlplane.artifacts import DeclaredArtifact, ProductClassDeclaration
 from ccf.llm import LLMClientProtocol
 from ccf.replay.record import NO_GRANTS_SET_HASH, DecisionReplayRecord
 
+pytestmark = pytest.mark.archived  # D-IMPL-265: exercises archive/examples/01-agent-basics; retired usage model, non-gating
 REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
 EXAMPLE = REPO_ROOT / "archive" / "examples" / "01-agent-basics" / "run.py"
 
diff --git a/tests/examples/test_artifact_store_output.py b/tests/examples/test_artifact_store_output.py
index 4dc3c444..39176ff3 100644
--- a/tests/examples/test_artifact_store_output.py
+++ b/tests/examples/test_artifact_store_output.py
@@ -71,6 +71,7 @@ import yaml
 from ccf.controlplane.artifacts import DeclaredArtifact, ProductClassDeclaration
 from ccf.products.contract import ContextProductContract
 
+pytestmark = pytest.mark.archived  # D-IMPL-265: exercises archive/examples/07-artifact-store-mcp; retired usage model, non-gating
 REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
 EXAMPLE_DIR = REPO_ROOT / "archive" / "examples" / "07-artifact-store-mcp"
 EXAMPLE = EXAMPLE_DIR / "run.py"
diff --git a/tests/examples/test_cp_00_output.py b/tests/examples/test_cp_00_output.py
index d24cc560..81dbf3f9 100644
--- a/tests/examples/test_cp_00_output.py
+++ b/tests/examples/test_cp_00_output.py
@@ -383,6 +383,10 @@ def _over(root: pathlib.Path, threshold: int, **kwargs: Any) -> tuple[Any, Any]:
 # --------------------------------------------------------------------------
 # 1 — the threshold selects.
 # --------------------------------------------------------------------------
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen cp-00 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_resolve_reaches_the_same_security(
     tmp_path: pathlib.Path, seeded: str
 ) -> None:
@@ -401,6 +405,10 @@ def test_the_resolve_reaches_the_same_security(
     assert resolved["candidates_considered"] == len(fanout)
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen cp-00 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_threshold_selects(tmp_path: pathlib.Path, seeded: str) -> None:
     """The payload equals the SELECT oracle, row for row."""
     deployment = _load("deployment")
@@ -425,6 +433,10 @@ def test_the_threshold_selects(tmp_path: pathlib.Path, seeded: str) -> None:
     )
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen cp-00 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_a_row_exactly_at_the_threshold_is_served(
     tmp_path: pathlib.Path, seeded: str
 ) -> None:
@@ -449,6 +461,10 @@ def test_a_row_exactly_at_the_threshold_is_served(
     assert observed.product.payload["threshold"]["comparison"] == deployment.COMPARISON
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen cp-00 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_band_is_carried_and_filtered_nowhere(
     tmp_path: pathlib.Path, seeded: str
 ) -> None:
@@ -475,6 +491,10 @@ def test_the_band_is_carried_and_filtered_nowhere(
 # --------------------------------------------------------------------------
 # 2, 3 — identity, not content.
 # --------------------------------------------------------------------------
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen cp-00 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_two_thresholds_are_two_products(
     tmp_path: pathlib.Path, seeded: str
 ) -> None:
@@ -489,6 +509,10 @@ def test_two_thresholds_are_two_products(
     assert content_hash(first.product) != content_hash(second.product)
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen cp-00 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_same_question_is_stable(tmp_path: pathlib.Path, seeded: str) -> None:
     """Identical question, identical address — determinism, not coincidence."""
     low, _high, _exact = _thresholds(seeded)
@@ -555,6 +579,10 @@ def test_a_missing_threshold_is_refused_not_defaulted(
 # --------------------------------------------------------------------------
 # 5 — the assembler seam is the path.
 # --------------------------------------------------------------------------
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen cp-00 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_assembler_seam_is_the_path(
     tmp_path: pathlib.Path, seeded: str
 ) -> None:
@@ -600,6 +628,10 @@ def test_the_assembler_seam_is_the_path(
 # --------------------------------------------------------------------------
 # 6 — the gate result is RECORDED, not assumed.
 # --------------------------------------------------------------------------
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen cp-00 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_gate_result_is_recorded_not_assumed(
     tmp_path: pathlib.Path, seeded: str
 ) -> None:
@@ -727,6 +759,10 @@ def payload_shape_violations(payload: Any, declared: dict[str, Any]) -> list[str
     return problems
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen cp-00 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_payload_validates_against_the_declared_contract(
     tmp_path: pathlib.Path, seeded: str
 ) -> None:
@@ -861,6 +897,10 @@ def test_the_client_returns_a_non_zero_exit_code_on_a_governed_refusal(
     assert "refused:" in buffer.getvalue(), buffer.getvalue()[:200]
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen cp-00 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_printed_specification_and_json_are_non_empty_and_the_json_validates(
     printed: str, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
 ) -> None:
@@ -940,6 +980,10 @@ def _alternate_period(dsn: str) -> str:
         return str(cursor.fetchone()[0])
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen cp-00 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_debt_is_driven_by_the_declared_freshness_anchor(
     tmp_path: pathlib.Path, seeded: str, monkeypatch: pytest.MonkeyPatch
 ) -> None:
@@ -1008,6 +1052,10 @@ def test_debt_is_driven_by_the_declared_freshness_anchor(
 # --------------------------------------------------------------------------
 # 10 — the record is written before delivery.
 # --------------------------------------------------------------------------
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen cp-00 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_record_is_written_before_delivery(
     tmp_path: pathlib.Path, seeded: str
 ) -> None:
@@ -1219,6 +1267,10 @@ def _integer_leaves(value: Any, path: str = "payload") -> list[tuple[str, int]]:
     return []
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen cp-00 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_ih_g01_every_served_row_cusip_equals_the_resolved_security(
     tmp_path: pathlib.Path, seeded: str
 ) -> None:
@@ -1277,6 +1329,10 @@ def test_ih_g01_every_served_row_cusip_equals_the_resolved_security(
     )
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen cp-00 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_ih_g02_every_served_row_report_period_equals_the_pinned_period(
     tmp_path: pathlib.Path, seeded: str
 ) -> None:
@@ -1329,6 +1385,10 @@ def test_ih_g02_every_served_row_report_period_equals_the_pinned_period(
     )
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen cp-00 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_ih_g03_every_served_row_carries_a_non_null_issuer_match_band(
     tmp_path: pathlib.Path, seeded: str
 ) -> None:
@@ -1365,6 +1425,10 @@ def test_ih_g03_every_served_row_carries_a_non_null_issuer_match_band(
     )
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen cp-00 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_ih_g05_the_boundary_is_at_or_after_ingest_and_the_assembled_set_is_non_empty(
     tmp_path: pathlib.Path, seeded: str
 ) -> None:
@@ -1410,6 +1474,10 @@ def test_ih_g05_the_boundary_is_at_or_after_ingest_and_the_assembled_set_is_non_
     )
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen cp-00 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_ih_g06_every_declared_class_names_and_carries_its_classification_attribute(
     tmp_path: pathlib.Path, seeded: str, monkeypatch: pytest.MonkeyPatch
 ) -> None:
@@ -1530,6 +1598,10 @@ def test_ih_g06_every_declared_class_names_and_carries_its_classification_attrib
         )
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen cp-00 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_ih_g07_an_empty_assembled_set_fails_closed_and_an_empty_served_set_serves(
     tmp_path: pathlib.Path, seeded: str
 ) -> None:
@@ -1584,6 +1656,10 @@ def test_ih_g07_an_empty_assembled_set_fails_closed_and_an_empty_served_set_serv
     )
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen cp-00 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_ih_g08_the_payload_carries_no_count_of_rows_read(
     tmp_path: pathlib.Path, seeded: str
 ) -> None:
diff --git a/tests/examples/test_cp_00_recipe_steps.py b/tests/examples/test_cp_00_recipe_steps.py
index 08192476..553a42ac 100644
--- a/tests/examples/test_cp_00_recipe_steps.py
+++ b/tests/examples/test_cp_00_recipe_steps.py
@@ -334,6 +334,10 @@ def unresolved(steps: list[dict[str, Any]], assembled: Any) -> list[str]:
     ]
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen cp-00 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_every_declared_step_is_witnessed_by_the_run(run: Any) -> None:
     """Criterion 2. A step nothing executes is RED, and this is where it goes red."""
     steps = _recipe_declaration()[KEY_STEPS]
@@ -341,6 +345,10 @@ def test_every_declared_step_is_witnessed_by_the_run(run: Any) -> None:
     assert unresolved(list(steps), run) == []
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen cp-00 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_every_witness_kind_the_vocabulary_declares_is_used(run: Any) -> None:
     """The vocabulary and the steps agree, so no kind is dead vocabulary.
 
@@ -410,6 +418,10 @@ class _NotGated:
 
 
 @pytest.mark.parametrize("kind", sorted(CLOSED_VOCABULARY))
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen cp-00 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_each_witness_kind_can_go_red(kind: str, run: Any) -> None:
     """Five kinds, five controls. A kind that cannot fail must not be in the
     vocabulary.
@@ -451,6 +463,10 @@ def test_each_witness_kind_can_go_red(kind: str, run: Any) -> None:
 # --------------------------------------------------------------------------
 # HALF FOUR — an unknown kind RAISES rather than being skipped.
 # --------------------------------------------------------------------------
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen cp-00 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_an_unknown_witness_kind_raises(run: Any) -> None:
     """A silently-skipped step is criterion 2's failure mode wearing a tick."""
     with pytest.raises(UnknownWitnessKind, match="closed vocabulary"):
diff --git a/tests/examples/test_cp_01_output.py b/tests/examples/test_cp_01_output.py
index 3ef01d05..e29612b6 100644
--- a/tests/examples/test_cp_01_output.py
+++ b/tests/examples/test_cp_01_output.py
@@ -307,6 +307,10 @@ def test_the_seeder_seeded(seeded: str) -> None:
 # --------------------------------------------------------------------------
 # §G acceptance criteria and §D.7 product-specific gates.
 # --------------------------------------------------------------------------
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 D-01/F-2: frozen cp-01 ccf_config.yaml declares intent under arguments.properties (shadow of the top-level field) — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 D-10/D-13: frozen cp-01 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_anchor_resolves_through_the_vendor_authority(seeded: str) -> None:
     """§G criterion 4, and `CPR-G07` — every attribute names its authority."""
     produce = _load("produce")
@@ -317,6 +321,10 @@ def test_the_anchor_resolves_through_the_vendor_authority(seeded: str) -> None:
     assert counterparty["legal_name"] == "AVIS BUDGET GROUP, INC."
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 D-01/F-2: frozen cp-01 ccf_config.yaml declares intent under arguments.properties (shadow of the top-level field) — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 D-10/D-13: frozen cp-01 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_both_addresses_are_present_and_distinguishable(seeded: str) -> None:
     """`CPR-G01` — §C.4 trap 1, the defect that motivated Wave 20.
 
@@ -342,6 +350,10 @@ def test_both_addresses_are_present_and_distinguishable(seeded: str) -> None:
     assert norm(hq["city"]) == "parsippany"
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 D-01/F-2: frozen cp-01 ccf_config.yaml declares intent under arguments.properties (shadow of the top-level field) — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 D-10/D-13: frozen cp-01 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_seven_class_type_chain_is_asserted(seeded: str) -> None:
     """`CPR-G06` — §C.3. A partial chain propagates catalog-wide."""
     assembled = _serve(seeded)
@@ -355,6 +367,10 @@ def test_the_seven_class_type_chain_is_asserted(seeded: str) -> None:
     )
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 D-01/F-2: frozen cp-01 ccf_config.yaml declares intent under arguments.properties (shadow of the top-level field) — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 D-10/D-13: frozen cp-01 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_entitlement_discriminates_as_sets_with_a_negative_control(
     seeded: str,
 ) -> None:
@@ -431,6 +447,10 @@ def test_entitlement_discriminates_as_sets_with_a_negative_control(
     )
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 D-01/F-2: frozen cp-01 ccf_config.yaml declares intent under arguments.properties (shadow of the top-level field) — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 D-10/D-13: frozen cp-01 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_a_suppressed_entity_leaves_no_marker(seeded: str) -> None:
     """`CPR-G04` — §B.2's suppression rule, at the whole product boundary.
 
@@ -473,6 +493,10 @@ def test_a_suppressed_entity_leaves_no_marker(seeded: str) -> None:
     assert not violations, "CPR-G04: " + "; ".join(violations)
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 D-01/F-2: frozen cp-01 ccf_config.yaml declares intent under arguments.properties (shadow of the top-level field) — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 D-10/D-13: frozen cp-01 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_a_lapsed_entity_is_excluded_entirely_by_default(seeded: str) -> None:
     """`CPR-G01`'s second half — §B.4. Excluded, never returned unflagged."""
     assembled = _serve(seeded, anchor="549300TRW1LZMDJZAQ78")
@@ -481,6 +505,10 @@ def test_a_lapsed_entity_is_excluded_entirely_by_default(seeded: str) -> None:
     assert payload["excluded"]["reason"] == "registration-lapsed"
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 D-01/F-2: frozen cp-01 ccf_config.yaml declares intent under arguments.properties (shadow of the top-level field) — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 D-10/D-13: frozen cp-01 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_include_lapsed_returns_it_with_status_first_class(seeded: str) -> None:
     """§B.4 — and the content address must DIFFER from the exclusion's.
 
@@ -504,6 +532,10 @@ def test_an_unresolvable_anchor_fails_closed(seeded: str) -> None:
         _serve(seeded, anchor="NOT-A-REAL-ANCHOR")
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 D-01/F-2: frozen cp-01 ccf_config.yaml declares intent under arguments.properties (shadow of the top-level field) — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_as_of_is_declared_and_always_refused(seeded: str) -> None:
     """`CPR-G05` — Standard §2.4's declared-but-inert parameter.
 
@@ -541,6 +573,10 @@ def test_as_of_is_declared_and_always_refused(seeded: str) -> None:
     )
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 D-01/F-2: frozen cp-01 ccf_config.yaml declares intent under arguments.properties (shadow of the top-level field) — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 D-10/D-13: frozen cp-01 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_product_is_byte_identical_across_identical_requests(
     seeded: str,
 ) -> None:
@@ -588,6 +624,10 @@ def test_a_no_lei_entity_reports_the_lower_freshness_ceiling(seeded: str) -> Non
     )
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 D-01/F-2: frozen cp-01 ccf_config.yaml declares intent under arguments.properties (shadow of the top-level field) — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 D-10/D-13: frozen cp-01 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_a_no_lei_entity_is_refused_by_the_ttl_lower_bound(seeded: str) -> None:
     """`CPR-G09` — and this test is written to FAIL when the defect is fixed.
 
@@ -616,6 +656,10 @@ def test_a_no_lei_entity_is_refused_by_the_ttl_lower_bound(seeded: str) -> None:
 # grant set matches no entity — and a gate with no fixture cannot be watched.
 # The principal is constructed HERE, in the test; no fixture row was added.
 # --------------------------------------------------------------------------
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 D-01/F-2: frozen cp-01 ccf_config.yaml declares intent under arguments.properties (shadow of the top-level field) — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 D-10/D-13: frozen cp-01 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_cpr_g08_a_principal_matching_no_entity_is_refused_and_cannot_be_told_from_a_missing_one(
     seeded: str,
 ) -> None:
@@ -679,6 +723,10 @@ def test_cpr_g08_a_principal_matching_no_entity_is_refused_and_cannot_be_told_fr
     )
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 D-01/F-2: frozen cp-01 ccf_config.yaml declares intent under arguments.properties (shadow of the top-level field) — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 D-10/D-13: frozen cp-01 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_served_outcome_names_the_module_assembler_version(seeded: str) -> None:
     """The Protocol's return names this module's assembler identity, pinned at `1.0.1`.
 
diff --git a/tests/examples/test_cp_02_output.py b/tests/examples/test_cp_02_output.py
index a3e667ec..8f0a0c54 100644
--- a/tests/examples/test_cp_02_output.py
+++ b/tests/examples/test_cp_02_output.py
@@ -301,6 +301,10 @@ def test_the_pricing_grid_is_not_an_array_and_the_naive_read_returns_zero(
 # --------------------------------------------------------------------------
 # FTS-G01 — the primitive. The expiry is a property of the facility.
 # --------------------------------------------------------------------------
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 D-01/F-2: frozen cp-02 ccf_config.yaml declares intent under arguments.properties (shadow of the top-level field) — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 D-10/D-13: frozen cp-02 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_expiry_does_not_move_when_the_question_moves(seeded: str) -> None:
     """`FTS-G01`, and it is the one gate whose failure would mean the product
     had become its own counterfactual.
@@ -339,6 +343,10 @@ def test_the_expiry_does_not_move_when_the_question_moves(seeded: str) -> None:
     ), "the expiry is stable but is not the agreement date plus the window"
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 D-01/F-2: frozen cp-02 ccf_config.yaml declares intent under arguments.properties (shadow of the top-level field) — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 D-10/D-13: frozen cp-02 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_payload_names_the_date_the_expiry_was_measured_from(
     seeded: str,
 ) -> None:
@@ -359,6 +367,10 @@ def test_the_payload_names_the_date_the_expiry_was_measured_from(
 # --------------------------------------------------------------------------
 # FTS-G02 / FTS-G03 / FTS-G04 — the policy step, and it is two conditions.
 # --------------------------------------------------------------------------
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 D-01/F-2: frozen cp-02 ccf_config.yaml declares intent under arguments.properties (shadow of the top-level field) — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 D-10/D-13: frozen cp-02 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_entitlement_discriminates_as_sets_with_a_negative_control(
     seeded: str,
 ) -> None:
@@ -414,6 +426,10 @@ def test_entitlement_discriminates_as_sets_with_a_negative_control(
     )
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 D-01/F-2: frozen cp-02 ccf_config.yaml declares intent under arguments.properties (shadow of the top-level field) — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 D-10/D-13: frozen cp-02 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_need_to_know_is_load_bearing(seeded: str) -> None:
     """`FTS-G03` — the condition that a set-difference check cannot see.
 
@@ -440,6 +456,10 @@ def test_need_to_know_is_load_bearing(seeded: str) -> None:
     )
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 D-01/F-2: frozen cp-02 ccf_config.yaml declares intent under arguments.properties (shadow of the top-level field) — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 D-10/D-13: frozen cp-02 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_a_suppressed_facility_is_indistinguishable_from_a_missing_one(
     seeded: str,
 ) -> None:
@@ -538,6 +558,10 @@ def _assemble_through_seam(seeded: str, **kwargs: Any) -> Any:
 # --------------------------------------------------------------------------
 # FTS-G05 · G06 · G07 · G08 — the parameter surface and the three data traps.
 # --------------------------------------------------------------------------
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 D-01/F-2: frozen cp-02 ccf_config.yaml declares intent under arguments.properties (shadow of the top-level field) — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_as_of_is_refused_and_never_silently_honored(seeded: str) -> None:
     """`FTS-G05` — Standard §2.4's declared-but-inert parameter.
 
@@ -566,6 +590,10 @@ def test_as_of_is_refused_and_never_silently_honored(seeded: str) -> None:
     assert "400" in refused.detail
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 D-01/F-2: frozen cp-02 ccf_config.yaml declares intent under arguments.properties (shadow of the top-level field) — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 D-10/D-13: frozen cp-02 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_no_source_pointer_reaches_the_payload(seeded: str) -> None:
     """`FTS-G06` — the tier boundary the DATA does not enforce.
 
@@ -605,6 +633,10 @@ def test_no_source_pointer_reaches_the_payload(seeded: str) -> None:
         )
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 D-01/F-2: frozen cp-02 ccf_config.yaml declares intent under arguments.properties (shadow of the top-level field) — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 D-10/D-13: frozen cp-02 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_pricing_grid_is_served_as_a_tier_structure(seeded: str) -> None:
     """`FTS-G07` — a grid flattened to a scalar answers the wrong question.
 
@@ -631,6 +663,10 @@ def test_the_pricing_grid_is_served_as_a_tier_structure(seeded: str) -> None:
     assert all(isinstance(tier["margin_bps"], int) for tier in tiers)
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 D-01/F-2: frozen cp-02 ccf_config.yaml declares intent under arguments.properties (shadow of the top-level field) — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 D-10/D-13: frozen cp-02 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_an_inverted_date_pair_serves_without_computing_a_tenor(
     seeded: str,
 ) -> None:
@@ -660,6 +696,10 @@ def test_an_inverted_date_pair_serves_without_computing_a_tenor(
     assert facility["maturity_date"] < facility["effective_date"]
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 D-01/F-2: frozen cp-02 ccf_config.yaml declares intent under arguments.properties (shadow of the top-level field) — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 D-10/D-13: frozen cp-02 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_a_facility_with_no_maturity_date_serves(seeded: str) -> None:
     """The completeness half of the same claim — absent, not inverted.
 
@@ -675,6 +715,10 @@ def test_a_facility_with_no_maturity_date_serves(seeded: str) -> None:
     assert facility["tenor_days"] == deployment.NOT_EVALUABLE
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 D-01/F-2: frozen cp-02 ccf_config.yaml declares intent under arguments.properties (shadow of the top-level field) — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 D-10/D-13: frozen cp-02 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_amendment_count_is_served_and_no_amendment_date_is_claimed(
     seeded: str,
 ) -> None:
@@ -694,6 +738,10 @@ def test_the_amendment_count_is_served_and_no_amendment_date_is_claimed(
 # --------------------------------------------------------------------------
 # FTS-G09 — the shipped finding. THIS TEST GOES RED WHEN THE DEFECT IS FIXED.
 # --------------------------------------------------------------------------
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 D-01/F-2: frozen cp-02 ccf_config.yaml declares intent under arguments.properties (shadow of the top-level field) — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 D-10/D-13: frozen cp-02 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_a_facility_older_than_the_window_is_refused(seeded: str) -> None:
     """`FTS-G09` — the 50-of-60 `ttl-bounds` refusal §F.4 finding 1 records.
 
@@ -760,6 +808,10 @@ def test_the_population_the_finding_describes_is_the_population_that_refuses(
 # --------------------------------------------------------------------------
 # Determinism, and the shape of the served contract.
 # --------------------------------------------------------------------------
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 D-01/F-2: frozen cp-02 ccf_config.yaml declares intent under arguments.properties (shadow of the top-level field) — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 D-10/D-13: frozen cp-02 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_same_question_twice_is_byte_identical(seeded: str) -> None:
     """§D.4 — `deterministic`, asserted as hash equality between two runs.
 
@@ -771,6 +823,10 @@ def test_the_same_question_twice_is_byte_identical(seeded: str) -> None:
     assert content_hash(first.product) == content_hash(second.product)
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 D-01/F-2: frozen cp-02 ccf_config.yaml declares intent under arguments.properties (shadow of the top-level field) — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 D-10/D-13: frozen cp-02 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_pricing_grid_parameter_changes_the_content_address(
     seeded: str,
 ) -> None:
@@ -788,6 +844,10 @@ def test_the_pricing_grid_parameter_changes_the_content_address(
     )
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 D-01/F-2: frozen cp-02 ccf_config.yaml declares intent under arguments.properties (shadow of the top-level field) — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 D-10/D-13: frozen cp-02 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_served_contract_matches_the_declared_expectations(
     seeded: str,
 ) -> None:
@@ -808,6 +868,10 @@ def test_the_served_contract_matches_the_declared_expectations(
         )
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 D-01/F-2: frozen cp-02 ccf_config.yaml declares intent under arguments.properties (shadow of the top-level field) — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 D-10/D-13: frozen cp-02 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_recipe_steps_each_have_a_witness_that_fired(seeded: str) -> None:
     """`artifacts/assembly-recipe.yaml` — a step nothing executes is RED.
 
@@ -851,6 +915,10 @@ def test_the_recipe_steps_each_have_a_witness_that_fired(seeded: str) -> None:
             raise AssertionError(f"unknown witness kind {kind!r}")
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 D-01/F-2: frozen cp-02 ccf_config.yaml declares intent under arguments.properties (shadow of the top-level field) — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 D-10/D-13: frozen cp-02 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_served_outcome_names_the_module_assembler_version(seeded: str) -> None:
     """The Protocol's return names this module's assembler identity, pinned at `1.0.1`.
 
diff --git a/tests/examples/test_cp_03_output.py b/tests/examples/test_cp_03_output.py
index e9928b3c..21576592 100644
--- a/tests/examples/test_cp_03_output.py
+++ b/tests/examples/test_cp_03_output.py
@@ -275,6 +275,10 @@ def test_the_seed_carries_what_these_gates_need(seeded: str) -> None:
 # ---------------------------------------------------------------------------
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 D-01/F-2: frozen cp-03 ccf_config.yaml declares intent under arguments.properties (shadow of the top-level field) — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 D-10/D-13: frozen cp-03 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_ofs_g01_the_payload_carries_both_fact_kinds(seeded: str) -> None:
     """`OFS-G01` — at least one instant AND at least one duration fact.
 
@@ -310,6 +314,10 @@ def test_ofs_g01_the_payload_carries_both_fact_kinds(seeded: str) -> None:
 # ---------------------------------------------------------------------------
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 D-01/F-2: frozen cp-03 ccf_config.yaml declares intent under arguments.properties (shadow of the top-level field) — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 D-10/D-13: frozen cp-03 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_ofs_g09_the_expiry_is_anchored_on_the_filing_not_the_question(
     seeded: str,
 ) -> None:
@@ -506,6 +514,10 @@ def _outcome(seeded: str, lei: str, principal: str) -> str:
     return "served" if getattr(served, "product", None) is not None else "empty"
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 D-01/F-2: frozen cp-03 ccf_config.yaml declares intent under arguments.properties (shadow of the top-level field) — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 D-10/D-13: frozen cp-03 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_ofs_g15_suppression_is_indistinguishable_from_absence(
     seeded: str,
 ) -> None:
@@ -641,6 +653,10 @@ def _executable_strings(path: pathlib.Path) -> list[str]:
     return found
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 D-01/F-2: frozen cp-03 ccf_config.yaml declares intent under arguments.properties (shadow of the top-level field) — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 D-10/D-13: frozen cp-03 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_ofs_g02_resolution_goes_through_the_crosswalk(seeded: str) -> None:
     """`OFS-G02` — identity comes from `crosswalk`, never from `financial_fact.cik`.
 
@@ -762,6 +778,10 @@ def test_ofs_g07_no_llm_client_is_reachable(seeded: str) -> None:
     )
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 D-01/F-2: frozen cp-03 ccf_config.yaml declares intent under arguments.properties (shadow of the top-level field) — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_ofs_g06_as_of_is_refused_and_never_silently_honored(seeded: str) -> None:
     """`OFS-G06` — a parameter this tier declares and always refuses.
 
@@ -854,6 +874,10 @@ def test_ofs_g06_as_of_is_refused_and_never_silently_honored(seeded: str) -> Non
     )
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 D-01/F-2: frozen cp-03 ccf_config.yaml declares intent under arguments.properties (shadow of the top-level field) — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 D-10/D-13: frozen cp-03 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_ofs_g10_exactly_one_operator_and_no_enrich(seeded: str) -> None:
     """`OFS-G10` — one operator in the plan, and no `Enrich` registered.
 
@@ -943,6 +967,10 @@ def _restated_cells(seeded: str, key: list[str]) -> int:
         return int(row[0])
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 D-01/F-2: frozen cp-03 ccf_config.yaml declares intent under arguments.properties (shadow of the top-level field) — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 D-10/D-13: frozen cp-03 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_ofs_g03_the_restatement_key_is_the_estates_own(seeded: str) -> None:
     """`OFS-G03` — the key is declared in an artifact, and it is load-bearing.
 
@@ -1042,6 +1070,10 @@ def test_ofs_g03_the_restatement_key_is_the_estates_own(seeded: str) -> None:
     )
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 D-01/F-2: frozen cp-03 ccf_config.yaml declares intent under arguments.properties (shadow of the top-level field) — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 D-10/D-13: frozen cp-03 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_ofs_g04_item_402_corroborates_and_never_detects(seeded: str) -> None:
     """`OFS-G04` — a non-reliance filing is evidence, not the detector.
 
@@ -1102,6 +1134,10 @@ def test_ofs_g04_item_402_corroborates_and_never_detects(seeded: str) -> None:
     )
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 D-01/F-2: frozen cp-03 ccf_config.yaml declares intent under arguments.properties (shadow of the top-level field) — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 D-10/D-13: frozen cp-03 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_ofs_g08_absence_is_a_word_and_never_a_zero(seeded: str) -> None:
     """`OFS-G08` — the revenue-less obligor serves NOT_EVALUABLE, never `0`.
 
@@ -1160,6 +1196,10 @@ def test_ofs_g08_absence_is_a_word_and_never_a_zero(seeded: str) -> None:
     )
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 D-01/F-2: frozen cp-03 ccf_config.yaml declares intent under arguments.properties (shadow of the top-level field) — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 D-10/D-13: frozen cp-03 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_ofs_g11_basis_changes_the_address_only_where_it_changes_the_answer(
     seeded: str,
 ) -> None:
@@ -1251,6 +1291,10 @@ def test_ofs_g11_basis_changes_the_address_only_where_it_changes_the_answer(
     )
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 D-01/F-2: frozen cp-03 ccf_config.yaml declares intent under arguments.properties (shadow of the top-level field) — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 D-10/D-13: frozen cp-03 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_ofs_g12_every_derived_line_names_what_it_consumed(seeded: str) -> None:
     """`OFS-G12` — a ratio names its inputs, and they are in the same payload.
 
@@ -1299,6 +1343,10 @@ def test_ofs_g12_every_derived_line_names_what_it_consumed(seeded: str) -> None:
     )
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 D-01/F-2: frozen cp-03 ccf_config.yaml declares intent under arguments.properties (shadow of the top-level field) — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 D-10/D-13: frozen cp-03 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_ofs_g13_the_severity_threshold_comes_from_the_artifact(
     seeded: str,
 ) -> None:
@@ -1359,6 +1407,10 @@ def test_ofs_g13_the_severity_threshold_comes_from_the_artifact(
     )
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 D-01/F-2: frozen cp-03 ccf_config.yaml declares intent under arguments.properties (shadow of the top-level field) — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 D-10/D-13: frozen cp-03 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_served_outcome_names_the_module_assembler_version(seeded: str) -> None:
     """The Protocol's return names this module's assembler identity, pinned at `1.0.1`.
 
diff --git a/tests/examples/test_cp_04_anchor.py b/tests/examples/test_cp_04_anchor.py
index e837e2e2..200f1b0e 100644
--- a/tests/examples/test_cp_04_anchor.py
+++ b/tests/examples/test_cp_04_anchor.py
@@ -194,6 +194,10 @@ def _assemble_keeping_the_return(
 # ---------------------------------------------------------------------------
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine)",
+)
 def test_the_served_outcome_names_the_module_assembler_version(
     baseline: tuple[str, str],
     fluree_url: str,
@@ -305,6 +309,10 @@ def ambiguous_estate(
     return ledger, schema, anchor_iri
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine)",
+)
 def test_cft_g18_an_ambiguous_anchor_is_refused_as_typed_ambiguity_data(
     ambiguous_estate: tuple[str, str, str],
     fluree_url: str,
@@ -379,6 +387,10 @@ def _door_record(root: pathlib.Path, result: Any) -> Mapping[str, Any] | None:
         return None
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine) | D-10/F-3 (recorder, ruled; masked)",
+)
 def test_cft_g18_b_the_tool_carries_the_ambiguity_as_a_governed_refusal(
     ambiguous_estate: tuple[str, str, str],
     fluree_url: str,
@@ -479,6 +491,10 @@ def test_cft_g18_b_the_tool_carries_the_ambiguity_as_a_governed_refusal(
     assert isinstance(is_error, bool)
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine)",
+)
 def test_the_ambiguity_gate_measures_the_perturbation_and_not_the_estate(
     baseline: tuple[str, str],
     fluree_url: str,
diff --git a/tests/examples/test_cp_04_debt.py b/tests/examples/test_cp_04_debt.py
index efcdf6ef..bc60aeff 100644
--- a/tests/examples/test_cp_04_debt.py
+++ b/tests/examples/test_cp_04_debt.py
@@ -486,6 +486,10 @@ def moves_up(before: Decimal, after: Decimal) -> bool:
 # ---------------------------------------------------------------------------
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine)",
+)
 def test_the_two_twenties_are_different_populations(
     baseline: tuple[str, str],
     fluree_url: str,
@@ -597,6 +601,10 @@ def test_the_disclosure_check_refuses_a_document_that_dropped_it(
     )
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine)",
+)
 def test_d_c_moves_when_the_identity_boundary_moves(
     baseline: tuple[str, str],
     ledger_without_the_dispute: str,
@@ -661,6 +669,10 @@ def test_d_c_moves_when_the_identity_boundary_moves(
     )
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine)",
+)
 def test_the_attribute_boundary_moves_the_roster_and_not_the_debt(
     baseline: tuple[str, str],
     resolving_estate: tuple[str, str],
@@ -713,6 +725,10 @@ def test_the_attribute_boundary_moves_the_roster_and_not_the_debt(
     )
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine)",
+)
 def test_pinning_the_debt_to_a_constant_breaks_the_movement_assertion(
     baseline: tuple[str, str],
     ledger_without_the_dispute: str,
diff --git a/tests/examples/test_cp_04_payload.py b/tests/examples/test_cp_04_payload.py
index 8f6c827a..ac29b3ac 100644
--- a/tests/examples/test_cp_04_payload.py
+++ b/tests/examples/test_cp_04_payload.py
@@ -584,6 +584,10 @@ def asked_with_as_of(estate: tuple[str, str]) -> Asked:
 # ---------------------------------------------------------------------------
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine)",
+)
 def test_the_seed_carries_what_these_six_gates_need(served: Asked) -> None:
     """Without this, a green gate could be a true statement about nothing.
 
@@ -814,6 +818,10 @@ def inert_parameter_violations(
     return violations
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine) | D-10/F-3 (recorder, ruled; masked)",
+)
 def test_cft_g06_as_of_is_refused_not_supported_at_tier(
     asked_with_as_of: Asked,
 ) -> None:
@@ -1035,6 +1043,10 @@ def cycle_violations(
     return violations
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine)",
+)
 def test_cft_g07_a_cycle_carries_type_ordered_members_and_closing_edge(
     served: Asked,
 ) -> None:
@@ -1201,6 +1213,10 @@ def orthogonality_violations(
     return violations
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine)",
+)
 def test_cft_g08_findings_are_orthogonal_to_the_tree(served: Asked) -> None:
     """`CFT-G08` (criterion 32). Findings are orthogonal to the tree.
 
@@ -1328,6 +1344,10 @@ def unresolved_violations(
     return violations
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine)",
+)
 def test_cft_g09_a_node_with_no_lei_stays_in_the_tree_and_the_roster(
     served: Asked,
 ) -> None:
@@ -1573,6 +1593,10 @@ def class_chain_violations(
     return violations
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine)",
+)
 def test_cft_g15_each_served_node_carries_its_fibo_class_chain(served: Asked) -> None:
     """`CFT-G15` (criterion 39). Ontology role 2 — the chain is SERVED.
 
@@ -1689,6 +1713,10 @@ def test_the_chain_check_refuses_a_wrong_chain_that_is_not_empty() -> None:
     )
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine)",
+)
 def test_no_cycle_two_member_reaches_a_served_payload(served: Asked) -> None:
     """Why `CFT-G15` asserts content for ONE cycle and not for two — measured.
 
@@ -2103,6 +2131,10 @@ def mutated_views(estate: tuple[str, str]) -> tuple[str, Mapping[str, Asked]]:
     }
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine)",
+)
 def test_cft_g16_perspective_conditions_on_fibo_class(
     views: Mapping[str, Asked], mutated_views: tuple[str, Mapping[str, Asked]]
 ) -> None:
@@ -2655,6 +2687,10 @@ def duplicate_violations(
     return violations
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine)",
+)
 def test_the_duplicate_pair_is_surfaced_by_the_product(served: Asked) -> None:
     """Criterion 10, PRODUCT half. The same company entered twice is SURFACED.
 
@@ -2751,6 +2787,10 @@ def test_the_duplicate_check_refuses_a_merged_pair() -> None:
 # ---------------------------------------------------------------------------
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine)",
+)
 def test_the_served_anchor_is_a_member_of_the_served_tree(served: Asked) -> None:
     """The payload's anchor is in its own `nodes` block, by name.
 
diff --git a/tests/examples/test_cp_04_seams.py b/tests/examples/test_cp_04_seams.py
index 980663a0..36fb1635 100644
--- a/tests/examples/test_cp_04_seams.py
+++ b/tests/examples/test_cp_04_seams.py
@@ -759,6 +759,10 @@ def surfaces(estate: tuple[str, str]) -> dict[str, Any]:
 # ---------------------------------------------------------------------------
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine)",
+)
 def test_the_seed_carries_what_these_five_gates_need(
     observed: Observed, estate: tuple[str, str]
 ) -> None:
@@ -1064,6 +1068,10 @@ def provenance(
     return tuple(entries)
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine)",
+)
 def test_cft_g10_the_assembly_opened_both_stores(
     observed: Observed, provenance: tuple[Provenance, ...]
 ) -> None:
@@ -1332,6 +1340,10 @@ def whole_estate_resolution(estate: tuple[str, str]) -> WholeEstateResolution:
     )
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine)",
+)
 def test_cft_g11_attributes_resolve_in_one_batched_query(
     observed: Observed,
     whole_estate_resolution: WholeEstateResolution,
@@ -2063,6 +2075,10 @@ def door_reading(surfaces: dict[str, Any]) -> DoorReading:
     )
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine) | D-10/F-3 (recorder, ruled; masked)",
+)
 def test_cft_g13_the_tool_serves_and_the_registered_resource_refuses(
     door_reading: DoorReading,
 ) -> None:
@@ -2386,6 +2402,10 @@ def standalone_violations(
     return violations
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine)",
+)
 def test_cft_g14_one_standalone_assembler_serves_both_callers(
     observed: Observed, surfaces: dict[str, Any]
 ) -> None:
@@ -3198,6 +3218,10 @@ def _refused_over_capability(
     return client.ask(parameters, as_of=typed.asked_at)
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine) | D-10/F-3 (recorder, ruled; masked)",
+)
 def test_a_refused_outcome_carries_the_assembler_identity_and_resolves(
     tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
 ) -> None:
@@ -3266,6 +3290,10 @@ _SCRATCH_SHADOW_FAMILY = (
 )
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine) | D-10/F-3 (recorder, ruled; masked)",
+)
 def test_a_wrapper_that_skips_the_recorder_is_refused_at_the_door(
     tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
 ) -> None:
@@ -3336,6 +3364,10 @@ def test_a_wrapper_that_skips_the_recorder_is_refused_at_the_door(
             sys.modules.pop(name, None)
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine) | D-10/F-3 (recorder, ruled; masked)",
+)
 def test_replay_carries_the_assembler_identity_for_fulfilled_and_refused(
     estate: tuple[str, str], tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
 ) -> None:
diff --git a/tests/examples/test_cp_04_traversal.py b/tests/examples/test_cp_04_traversal.py
index 459d8d1c..005ec849 100644
--- a/tests/examples/test_cp_04_traversal.py
+++ b/tests/examples/test_cp_04_traversal.py
@@ -677,6 +677,10 @@ def under_a_redeclared_default(
 # ---------------------------------------------------------------------------
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine)",
+)
 def test_the_seed_carries_what_these_five_gates_need(
     at_the_declared_default: Asked, at_the_shallow_depth: Asked
 ) -> None:
@@ -914,6 +918,10 @@ def class_violations(
     return violations
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine)",
+)
 def test_cft_g01_every_returned_node_carries_a_known_fibo_class(
     at_the_declared_default: Asked,
 ) -> None:
@@ -1000,6 +1008,10 @@ def predicate_violations(
     return []
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine)",
+)
 def test_cft_g02_every_returned_edge_is_one_of_the_six_declared_predicates(
     at_the_declared_default: Asked,
 ) -> None:
@@ -1187,6 +1199,10 @@ def refusal_violations(
     return violations
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine) | D-10/F-3 (recorder, ruled; masked)",
+)
 def test_cft_g03_max_depth_above_the_technical_ceiling_is_refused_by_name(
     above_the_technical_capability: Asked,
 ) -> None:
@@ -1215,6 +1231,10 @@ def test_cft_g03_max_depth_above_the_technical_ceiling_is_refused_by_name(
     )
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine)",
+)
 def test_a_depth_the_estate_cannot_exhibit_is_served(
     at_a_depth_the_estate_cannot_exhibit: Asked,
 ) -> None:
@@ -1396,6 +1416,10 @@ def default_violations(
     return violations
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine)",
+)
 def test_cft_g04_a_missing_max_depth_takes_the_declared_default(
     at_the_declared_default: Asked, under_a_redeclared_default: Asked
 ) -> None:
@@ -1624,6 +1648,10 @@ def debt_movement_violations(
     return violations
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine)",
+)
 def test_cft_g05_depth_is_part_of_product_identity(
     at_the_shallow_depth: Asked,
     at_the_declared_default: Asked,
@@ -1654,6 +1682,10 @@ def test_cft_g05_depth_is_part_of_product_identity(
     assert not violations, "CFT-G05 failed:\n" + "\n".join(violations)
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine)",
+)
 def test_requested_depth_is_identity_even_where_it_changes_nothing_served(
     at_the_declared_default: Asked,
     at_a_depth_the_estate_cannot_exhibit: Asked,
@@ -1694,6 +1726,10 @@ def test_requested_depth_is_identity_even_where_it_changes_nothing_served(
     ), "the two payloads report the same requested depth"
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine)",
+)
 def test_cft_g19_findings_carry_depth_and_structural_cost_and_no_clock(
     at_the_declared_default: Asked,
 ) -> None:
@@ -2231,6 +2267,10 @@ def test_report_reads_the_deepest_integer_depth_not_the_sentinel() -> None:
 # Two boundary controls, as ruled: `0` refuses, `1` serves.
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 D-01/F-2: frozen cp-04 ccf_config.yaml declares intent under arguments.properties (shadow of the top-level field) — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_floor_is_the_sdks_verdict_over_the_declaration_and_needs_no_store() -> None:
     """The declaration says 1; the SDK refuses 0 and admits 1; nothing here reads a store.
 
@@ -2275,6 +2315,10 @@ def at_the_declared_floor(estate: tuple[str, str]) -> Asked:
     return ask(asked_as="max_depth=1 (at the declared floor)", max_depth=1)
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine) | D-10/F-3 (recorder, ruled; masked)",
+)
 def test_below_the_declared_floor_is_refused_as_data_and_no_tree_is_returned(
     below_the_declared_floor: Asked,
 ) -> None:
@@ -2290,6 +2334,10 @@ def test_below_the_declared_floor_is_refused_as_data_and_no_tree_is_returned(
     assert asked.envelope.key == _load("deployment").PARAM_MAX_DEPTH
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine)",
+)
 def test_at_the_declared_floor_is_served(at_the_declared_floor: Asked) -> None:
     """`1` serves — inclusive, as *"values 1–100 are valid"* reads."""
     asked = at_the_declared_floor
diff --git a/tests/examples/test_cp_04_two_callers.py b/tests/examples/test_cp_04_two_callers.py
index 605aac83..6308eb63 100644
--- a/tests/examples/test_cp_04_two_callers.py
+++ b/tests/examples/test_cp_04_two_callers.py
@@ -743,6 +743,10 @@ def mcp_answer_at_a_planted_depth(surfaces: dict[str, Any]) -> Answer:
 # ---------------------------------------------------------------------------
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine)",
+)
 def test_the_two_callers_answer_one_request_equivalently(
     in_process_answer: Answer, mcp_answer: Answer
 ) -> None:
@@ -758,6 +762,10 @@ def test_the_two_callers_answer_one_request_equivalently(
     assert not answer_violations(answers), "\n".join(answer_violations(answers))
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine)",
+)
 def test_the_comparison_refuses_a_planted_difference(
     in_process_answer: Answer, mcp_answer_at_a_planted_depth: Answer
 ) -> None:
@@ -792,6 +800,10 @@ def test_the_comparison_refuses_an_answer_carrying_nothing() -> None:
     assert any("nothing to agree about" in entry for entry in violations), violations
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine)",
+)
 def test_the_comparison_refuses_a_single_caller(in_process_answer: Answer) -> None:
     """**Vacuity control.** One caller that ran is not two callers that agreed."""
     violations = answer_violations({in_process_answer.caller: in_process_answer})
@@ -1083,6 +1095,10 @@ def test_cft_g13_b_a_read_of_the_product_resource_refuses_and_never_serves_a_tre
     )
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine)",
+)
 def test_the_refusal_check_refuses_a_resolver_that_returned_a_payload(
     in_process_answer: Answer,
 ) -> None:
@@ -1103,6 +1119,10 @@ def test_the_refusal_check_refuses_a_resolver_that_returned_a_payload(
     assert any("served" in entry for entry in violations), violations
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine)",
+)
 def test_cft_g13_c_the_tool_serves_on_a_client_supplied_lei_and_max_depth(
     mcp_answer_at_a_planted_depth: Answer,
 ) -> None:
@@ -1126,6 +1146,10 @@ def test_cft_g13_c_the_tool_serves_on_a_client_supplied_lei_and_max_depth(
     )
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine) | D-10/F-3 (recorder, ruled; masked)",
+)
 def test_the_tool_refuses_an_over_capability_depth_rather_than_clamping_it(
     surfaces: dict[str, Any],
 ) -> None:
@@ -1202,6 +1226,10 @@ def test_the_tool_refuses_an_over_capability_depth_rather_than_clamping_it(
     )
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine)",
+)
 def test_the_tool_serves_a_depth_the_estate_cannot_exhibit(
     surfaces: dict[str, Any],
 ) -> None:
@@ -1263,6 +1291,10 @@ def _refusing_request(deployment: Any, lei: str) -> Any:
     return typed.model_copy(update={"subject": lei, "parameters": parameters})
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine) | D-10/F-3 (recorder, ruled; masked)",
+)
 def test_a_serve_path_refusal_is_a_governed_error_and_the_door_survives(
     estate: tuple[str, str],
 ) -> None:
@@ -1375,6 +1407,10 @@ def _non_integer_depth_request(deployment: Any, value: Any) -> Any:
     return typed.model_copy(update={"parameters": parameters})
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine) | D-10/F-3 (recorder, ruled; masked)",
+)
 def test_a_non_integer_max_depth_is_refused_by_name_and_the_door_survives(
     estate: tuple[str, str],
 ) -> None:
@@ -1667,6 +1703,10 @@ def test_an_unverified_caller_reaches_neither_surface(
         )
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine)",
+)
 def test_the_resolver_assembles_under_the_perspective_it_was_handed(
     estate: tuple[str, str],
 ) -> None:
@@ -1722,6 +1762,10 @@ def test_the_resolver_assembles_under_the_perspective_it_was_handed(
 # ---------------------------------------------------------------------------
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7 | D-IMPL-264 am.1 D-01/F-2 (construction, ruled; masked by the earlier quarantine)",
+)
 def test_the_two_declared_roles_seal_to_different_content_addresses(
     estate: tuple[str, str],
 ) -> None:
diff --git a/tests/examples/test_cross_process_output.py b/tests/examples/test_cross_process_output.py
index cb07588e..ad1b0f4a 100644
--- a/tests/examples/test_cross_process_output.py
+++ b/tests/examples/test_cross_process_output.py
@@ -115,6 +115,7 @@ from ccf.peering.admission import ADMISSION_RECORD, AdmittedProduct, SignatureRe
 from ccf.peering.protocol import InboundProduct
 from ccf.products.gates import ServableProduct
 
+pytestmark = pytest.mark.archived  # D-IMPL-265: exercises archive/examples/04-cross-process; retired usage model, non-gating
 REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
 EXAMPLE_DIR = REPO_ROOT / "archive" / "examples" / "04-cross-process"
 
diff --git a/tests/examples/test_decision_replay_output.py b/tests/examples/test_decision_replay_output.py
index fd807671..45b51b7b 100644
--- a/tests/examples/test_decision_replay_output.py
+++ b/tests/examples/test_decision_replay_output.py
@@ -167,6 +167,7 @@ from ccf.skills.grants import SKILL_GRANT, grant_set_hash
 from ccf.workflow.definitions import WORKFLOW_DEFINITION
 from ccf_runtime.http_api.errors import ERROR_TENANT_UNAUTHORIZED
 
+pytestmark = pytest.mark.archived  # D-IMPL-265: exercises archive/examples/06-decision-replay; retired usage model, non-gating
 REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
 EXAMPLE = REPO_ROOT / "archive" / "examples" / "06-decision-replay" / "run.py"
 
diff --git a/tests/examples/test_e2e_demo_output.py b/tests/examples/test_e2e_demo_output.py
index 958c0a49..b0c5f1d5 100644
--- a/tests/examples/test_e2e_demo_output.py
+++ b/tests/examples/test_e2e_demo_output.py
@@ -133,6 +133,7 @@ from ccf.replay.record import DecisionReplayRecord
 from ccf.skills.catalog import SKILL_CATALOG_ENTRY
 from ccf.skills.grants import SKILL_GRANT
 
+pytestmark = pytest.mark.archived  # D-IMPL-265: exercises archive/examples/08-e2e-demo; retired usage model, non-gating
 REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
 EXAMPLE_DIR = REPO_ROOT / "archive" / "examples" / "08-e2e-demo"
 EXAMPLE = EXAMPLE_DIR / "run.py"
diff --git a/tests/examples/test_ext00_hardening.py b/tests/examples/test_ext00_hardening.py
index cd64f009..a799506f 100644
--- a/tests/examples/test_ext00_hardening.py
+++ b/tests/examples/test_ext00_hardening.py
@@ -32,6 +32,7 @@ from typing import Any
 
 import pytest
 
+pytestmark = pytest.mark.archived  # D-IMPL-265: exercises archive/examples/external/00-hello-context; retired usage model, non-gating
 REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
 EXAMPLE_DIR = REPO_ROOT / "archive" / "examples" / "external" / "00-hello-context"
 FIXTURES = EXAMPLE_DIR / "fixtures"
diff --git a/tests/examples/test_ext00_serve_output.py b/tests/examples/test_ext00_serve_output.py
index b7fd110d..7a46c7c3 100644
--- a/tests/examples/test_ext00_serve_output.py
+++ b/tests/examples/test_ext00_serve_output.py
@@ -88,6 +88,7 @@ from ccf.contracts.canonical import canonical_bytes
 from ccf.controlplane.artifacts import DeclaredArtifact, ProductClassDeclaration
 from ccf.products.gates import ServableProduct
 
+pytestmark = pytest.mark.archived  # D-IMPL-265: exercises archive/examples/external/00-hello-context; retired usage model, non-gating
 REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
 EXAMPLE_DIR = REPO_ROOT / "archive" / "examples" / "external" / "00-hello-context"
 
diff --git a/tests/examples/test_gate_two_divergence.py b/tests/examples/test_gate_two_divergence.py
index 42b4a3db..ad6f5bc5 100644
--- a/tests/examples/test_gate_two_divergence.py
+++ b/tests/examples/test_gate_two_divergence.py
@@ -92,6 +92,7 @@ from ccf.products.contract import (
 )
 from ccf.products.gates import LineageMismatchRefusal, ServableProduct, run_gates
 
+pytestmark = pytest.mark.archived  # D-IMPL-265: exercises archive/examples/00-quickstart; retired usage model, non-gating
 REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
 EXAMPLE = REPO_ROOT / "archive" / "examples" / "00-quickstart" / "run.py"
 
diff --git a/tests/examples/test_harness_portability_output.py b/tests/examples/test_harness_portability_output.py
index c8cea43e..fd259ee5 100644
--- a/tests/examples/test_harness_portability_output.py
+++ b/tests/examples/test_harness_portability_output.py
@@ -89,6 +89,7 @@ import pytest
 from ccf.contracts.canonical import canonical_bytes
 from ccf.controlplane.artifacts import DeclaredArtifact, ProductClassDeclaration
 
+pytestmark = pytest.mark.archived  # D-IMPL-265: exercises archive/examples/03-harness-portability; retired usage model, non-gating
 REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
 EXAMPLE_DIR = REPO_ROOT / "archive" / "examples" / "03-harness-portability"
 EXAMPLE = EXAMPLE_DIR / "run.py"
diff --git a/tests/examples/test_quickstart_output.py b/tests/examples/test_quickstart_output.py
index b4e751e8..9b1146ba 100644
--- a/tests/examples/test_quickstart_output.py
+++ b/tests/examples/test_quickstart_output.py
@@ -94,6 +94,7 @@ from ccf.contracts.canonical import content_hash
 from ccf.controlplane.artifacts import DeclaredArtifact, ProductClassDeclaration
 from ccf.replay.record import DecisionReplayRecord
 
+pytestmark = pytest.mark.archived  # D-IMPL-265: exercises archive/examples/00-quickstart; retired usage model, non-gating
 REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
 EXAMPLE = REPO_ROOT / "archive" / "examples" / "00-quickstart" / "run.py"
 
diff --git a/tests/examples/test_s1_00_output.py b/tests/examples/test_s1_00_output.py
index 9cbc7057..5c39cfc9 100644
--- a/tests/examples/test_s1_00_output.py
+++ b/tests/examples/test_s1_00_output.py
@@ -141,6 +141,10 @@ LOW = 100_000_000
 HIGH = 3_000_000_000
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen s1-00 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_threshold_selects(tmp_path: pathlib.Path, seeded: str) -> None:
     """A low threshold admits strictly more companies than a high one."""
     low = _over(tmp_path / "low", LOW)
@@ -154,6 +158,10 @@ def test_the_threshold_selects(tmp_path: pathlib.Path, seeded: str) -> None:
     assert sorted(names) == [name for name, _ in _expected(seeded, LOW)]
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen s1-00 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_two_thresholds_are_two_products(
     tmp_path: pathlib.Path, seeded: str
 ) -> None:
@@ -167,6 +175,10 @@ def test_two_thresholds_are_two_products(
     assert content_hash(low.product) != content_hash(high.product)
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen s1-00 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_same_question_is_stable(
     tmp_path: pathlib.Path, seeded: str
 ) -> None:
@@ -188,6 +200,10 @@ def test_a_missing_threshold_is_refused_not_defaulted(
     assert not hasattr(outcome, "product")
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen s1-00 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_debt_is_driven_by_last_updated(
     tmp_path: pathlib.Path, seeded: str
 ) -> None:
@@ -207,6 +223,10 @@ def test_debt_is_driven_by_last_updated(
     assert late.product.debt.debt > early.product.debt.debt
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen s1-00 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_debt_rides_the_product(tmp_path: pathlib.Path, seeded: str) -> None:
     """D_c is delivered WITH the answer and is inside its content address."""
     result = _over(tmp_path / "d", LOW)
@@ -215,6 +235,10 @@ def test_debt_rides_the_product(tmp_path: pathlib.Path, seeded: str) -> None:
     assert result.product.debt.signal is not None
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen s1-00 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_one_operator_and_the_gates_agree(
     tmp_path: pathlib.Path, seeded: str
 ) -> None:
@@ -230,6 +254,10 @@ def test_one_operator_and_the_gates_agree(
     assert result.product.lineage.operators_invoked == frozenset(declared)
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen s1-00 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_record_is_written_before_delivery(
     tmp_path: pathlib.Path, seeded: str
 ) -> None:
@@ -246,6 +274,10 @@ def test_the_record_is_written_before_delivery(
     assert recorded.parameters[deployment.THRESHOLD_PARAMETER] == LOW
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen s1-00 produce.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_answer_is_the_select_plus_four_things_it_cannot_return(
     tmp_path: pathlib.Path, seeded: str
 ) -> None:
diff --git a/tests/examples/test_s1_01_output.py b/tests/examples/test_s1_01_output.py
index b6bad83f..7ea8762e 100644
--- a/tests/examples/test_s1_01_output.py
+++ b/tests/examples/test_s1_01_output.py
@@ -236,6 +236,10 @@ def payload(result: Any) -> Any:
 # ---------------------------------------------------------------------------
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen s1-01 spine.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_run_ingested_the_declared_signal(example: Any, result: Any) -> None:
     """Every assertion below is about what survived four operators. If nothing
     was ingested, they are all assertions about an empty graph."""
@@ -284,6 +288,10 @@ def test_the_driver_loads_beside_a_same_named_module_from_another_tree() -> None
             sys.modules["deployment"] = previous
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen s1-01 spine.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_expectation_document_declares_something(expected: Any) -> None:
     """An empty ``expected.yaml`` would make the comparisons below trivially
     true. It is the source of every domain expectation in this module, so its
@@ -298,6 +306,10 @@ def test_the_expectation_document_declares_something(expected: Any) -> None:
 # ---------------------------------------------------------------------------
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen s1-01 spine.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_product_passed_all_three_gates(result: Any) -> None:
     """``ServableProduct`` is not constructible outside ``run_gates``, so a
     served product IS the evidence the gates ran (INV-CH7-52)."""
@@ -305,6 +317,10 @@ def test_the_product_passed_all_three_gates(result: Any) -> None:
     assert result.served.replay_ref is not None
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen s1-01 spine.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_lineage_strict_equality_holds(result: Any) -> None:
     """What the product claims ran is exactly what the engine resolved
     (INV-CH7-47).
@@ -319,6 +335,10 @@ def test_lineage_strict_equality_holds(result: Any) -> None:
     assert result.product.lineage.operators_invoked == result.operators_invoked
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen s1-01 spine.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_every_declared_operator_actually_ran(result: Any) -> None:
     """The set the product class DECLARED it requires is exactly the set the
     engine RESOLVED, and all four canonical categories are in it.
@@ -345,6 +365,10 @@ def test_every_declared_operator_actually_ran(result: Any) -> None:
 @pytest.mark.parametrize(
     "category", ["traversal", "temporal", "policy", "similarity"]
 )
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen s1-01 spine.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_all_four_operator_categories_ran(result: Any, category: str) -> None:
     """The whitepaper's four canonical categories (§7.4), each represented.
 
@@ -363,6 +387,10 @@ def test_all_four_operator_categories_ran(result: Any, category: str) -> None:
 # ---------------------------------------------------------------------------
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen s1-01 spine.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_run_serves_the_tenant_and_class_the_artifacts_name(
     result: Any,
 ) -> None:
@@ -373,6 +401,10 @@ def test_the_run_serves_the_tenant_and_class_the_artifacts_name(
     assert result.product.tenant_id == result.tenant_id
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen s1-01 spine.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_served_shape_matches_the_declared_expectation(
     expected: Any, payload: Any
 ) -> None:
@@ -395,6 +427,10 @@ def test_the_served_shape_matches_the_declared_expectation(
     ), payload
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen s1-01 spine.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_aggregate_ownership_answer_matches_the_declared_expectation(
     expected: Any, payload: Any
 ) -> None:
@@ -419,6 +455,10 @@ def test_the_aggregate_ownership_answer_matches_the_declared_expectation(
     assert served == declared, payload
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen s1-01 spine.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_answer_is_a_sum_over_paths_not_a_single_hop(
     expected: Any, payload: Any
 ) -> None:
@@ -452,6 +492,10 @@ def test_the_answer_is_a_sum_over_paths_not_a_single_hop(
     }
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen s1-01 spine.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_every_declared_absence_really_is_absent(
     expected: Any, payload: Any
 ) -> None:
@@ -482,6 +526,10 @@ def test_every_declared_absence_really_is_absent(
     )
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen s1-01 spine.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_product_answers_the_question_the_caller_asked(
     result: Any, payload: Any
 ) -> None:
@@ -517,6 +565,10 @@ def test_the_product_answers_the_question_the_caller_asked(
 # ---------------------------------------------------------------------------
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen s1-01 spine.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_replay_record_is_in_the_store_content_addressed(result: Any) -> None:
     """The address being the record's own content hash is an SDK mechanism
     claim, so it is computed here rather than read from an artifact."""
@@ -525,6 +577,10 @@ def test_the_replay_record_is_in_the_store_content_addressed(result: Any) -> Non
     assert address == content_hash(result.record)
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen s1-01 spine.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_stored_record_round_trips_exactly(result: Any) -> None:
     """Not merely parseable — equal."""
     restored = DecisionReplayRecord.model_validate_json(
@@ -533,6 +589,10 @@ def test_the_stored_record_round_trips_exactly(result: Any) -> None:
     assert restored == result.record
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen s1-01 spine.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_record_carries_all_five_dimensions(result: Any) -> None:
     """Whitepaper §7.10.1, asserted against the stored bytes rather than the
     in-memory record, so this covers the round trip as well as the
@@ -580,6 +640,10 @@ def _the_one_policy_version(result: Any) -> str:
     return next(iter(versions))
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen s1-01 spine.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_record_is_written_before_the_product_is_delivered(
     result: Any,
 ) -> None:
@@ -663,6 +727,10 @@ def test_each_question_gets_its_own_graph(
     )
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen s1-01 spine.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_products_address_survives_a_different_graph_identity(
     result: Any, answers: Any
 ) -> None:
@@ -677,6 +745,10 @@ def test_the_products_address_survives_a_different_graph_identity(
     assert content_hash(result.product) == content_hash(answers[0].product)
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen s1-01 spine.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_a_different_company_gets_a_different_answer(
     expected: Any, answers: Any
 ) -> None:
@@ -704,6 +776,10 @@ def test_a_different_company_gets_a_different_answer(
     )
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen s1-01 spine.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_same_company_at_a_later_instant_gets_a_different_answer(
     expected: Any, answers: Any
 ) -> None:
@@ -740,6 +816,10 @@ def test_the_same_company_at_a_later_instant_gets_a_different_answer(
     )
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen s1-01 spine.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_every_pinned_query_resolves_to_the_bytes_it_names(answers: Any) -> None:
     """**SDK mechanism claim.** The record pins which questions were put to the
     graph, and every pin is resolvable.
@@ -764,6 +844,10 @@ def test_every_pinned_query_resolves_to_the_bytes_it_names(answers: Any) -> None
             )
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen s1-01 spine.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_a_later_instant_pins_a_different_question_to_the_graph(
     answers: Any,
 ) -> None:
@@ -808,6 +892,10 @@ def test_a_later_instant_pins_a_different_question_to_the_graph(
     )
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen s1-01 spine.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_delivered_product_carries_its_debt(expected: Any, answers: Any) -> None:
     """**Propagation check.** D_c rides the vessel and reaches the caller.
 
@@ -827,6 +915,10 @@ def test_the_delivered_product_carries_its_debt(expected: Any, answers: Any) ->
     )
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen s1-01 spine.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_debt_figure_is_measured_and_not_constant(
     expected: Any, answers: Any
 ) -> None:
@@ -866,6 +958,10 @@ def test_the_debt_figure_is_measured_and_not_constant(
         )
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen s1-01 spine.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_routing_state_carries_what_this_deployment_says_it_obliges(
     expected: Any, answers: Any
 ) -> None:
@@ -916,6 +1012,10 @@ def test_the_routing_state_carries_what_this_deployment_says_it_obliges(
     assert expected[EXPECTED_DEBT_SIGNAL_FIRST] not in bound
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen s1-01 spine.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_obligation_in_force_is_pinned_into_the_replay_record(
     expected: Any, answers: Any
 ) -> None:
@@ -971,12 +1071,20 @@ def rendered_contrast(example: Any, answers: Any) -> str:
     return str(example.report.render_contrast(answers))
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen s1-01 spine.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_report_opens_the_sections_it_promises(rendered: str) -> None:
     """The heading tokens, and only the tokens."""
     for heading in REPORT_HEADINGS:
         assert heading in rendered, heading
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen s1-01 spine.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_report_carries_the_products_own_content_address(
     result: Any, rendered: str
 ) -> None:
@@ -989,6 +1097,10 @@ def test_the_report_carries_the_products_own_content_address(
     assert content_hash(result.product) in rendered
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen s1-01 spine.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_report_names_every_party_in_the_answer_and_the_near_miss(
     expected: Any, payload: Any, rendered: str
 ) -> None:
@@ -1004,6 +1116,10 @@ def test_the_report_names_every_party_in_the_answer_and_the_near_miss(
     assert expected[EXPECTED_BOUNDARY_CASE] in rendered
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen s1-01 spine.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_report_shows_the_refresh_window_and_names_no_source(
     example: Any, result: Any, rendered: str
 ) -> None:
@@ -1031,6 +1147,10 @@ def test_the_report_shows_the_refresh_window_and_names_no_source(
     assert not leaked, f"the report names upstream sources: {leaked}"
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen s1-01 spine.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_report_invents_no_debt_evidence_pointer(
     result: Any, rendered: str
 ) -> None:
@@ -1051,6 +1171,10 @@ def test_the_report_invents_no_debt_evidence_pointer(
     assert not leaked, f"the report carries entity URIs from the view: {leaked}"
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen s1-01 spine.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_contrast_shows_three_distinct_addresses(
     answers: Any, rendered_contrast: str
 ) -> None:
@@ -1063,6 +1187,10 @@ def test_the_contrast_shows_three_distinct_addresses(
     assert "WHAT THE THREE QUESTIONS SHOW" in rendered_contrast
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen s1-01 spine.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_renderers_return_text_and_print_nothing(
     example: Any, result: Any, answers: Any, capsys: pytest.CaptureFixture[str]
 ) -> None:
@@ -1091,6 +1219,10 @@ def _owners(payload: Any) -> list[tuple[str, str]]:
     ]
 
 
+@pytest.mark.xfail(
+    strict=True,
+    reason="D-IMPL-264 D-10/D-13: frozen s1-01 spine.py calls build_replay_record with no resolution state — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
+)
 def test_the_recorded_boundary_is_data_and_not_a_clock_read(result: Any) -> None:
     """The decision instant and the boundary are authored values.
 
diff --git a/tests/examples/test_skilling_output.py b/tests/examples/test_skilling_output.py
index 6f3f396a..8c07dc0f 100644
--- a/tests/examples/test_skilling_output.py
+++ b/tests/examples/test_skilling_output.py
@@ -116,6 +116,7 @@ from ccf.controlplane.artifacts import DeclaredArtifact, ProductClassDeclaration
 from ccf.replay.record import NO_GRANTS_SET_HASH, DecisionReplayRecord
 from ccf.skills.grants import RequirementsExceedRegime, grant_set_hash
 
+pytestmark = pytest.mark.archived  # D-IMPL-265: exercises archive/examples/02-skilling; retired usage model, non-gating
 REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
 EXAMPLE = REPO_ROOT / "archive" / "examples" / "02-skilling" / "run.py"
 
diff --git a/tests/examples/test_workflow_hitl_output.py b/tests/examples/test_workflow_hitl_output.py
index 0795d106..0d69a738 100644
--- a/tests/examples/test_workflow_hitl_output.py
+++ b/tests/examples/test_workflow_hitl_output.py
@@ -170,6 +170,7 @@ from ccf_runtime.http_api.errors import (
     ERROR_UNAUTHENTICATED,
 )
 
+pytestmark = pytest.mark.archived  # D-IMPL-265: exercises archive/examples/05-workflow-hitl; retired usage model, non-gating
 REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
 EXAMPLE = REPO_ROOT / "archive" / "examples" / "05-workflow-hitl" / "run.py"
```


---
End of bundle-tests-part-3.md. Read-proof, again:
```
READ-PROOF bundle-tests-part-3.md: 32f728a6347fe743
```
