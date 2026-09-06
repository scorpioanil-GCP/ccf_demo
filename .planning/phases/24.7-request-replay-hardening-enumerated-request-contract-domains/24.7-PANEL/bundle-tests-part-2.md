# 24.7 close-time panel — bundle-tests-part-2.md

Subject: the SHIPPED tree of `phase-24.7` at `ad8dc5a9` (tests/, perf/, tools/, pyproject.toml), diff base `6a019322`.
Read `prompt.md` for the instruction and `known-findings.md` for what NOT to re-derive.
Feed this file via STDIN, never as an argv string. Quote the line below verbatim in your review;
a review that does not quote it is recorded as a failed reviewer, not a reviewer.

```
READ-PROOF bundle-tests-part-2.md: 0e1693dab969a353
```

Subjects in this part (14): `tests/products/test_request_contract.py`, `tests/products/test_resolver_seam.py`, `tests/products/test_tolerance_exceeded.py`, `tests/replay/fixtures/golden_13bd250/produce.py`, `tests/replay/test_dimension_extensions.py`, `tests/replay/test_engine_rehydration.py`, `tests/replay/test_harness_trace.py`, `tests/replay/test_query_sequence_pin.py`, `tests/replay/test_refusal_replay_record.py`, `tests/replay/test_trace_correlation.py`, `tests/test_surface_shape_capture.py`, `tests/workflow/test_engine.py`, `tests/workflow/test_slice.py`, `tools/lints/tests/test_hash_transparent_key.py`

## tests/products/test_request_contract.py — diff 6a019322..HEAD (M)

```diff
diff --git a/tests/products/test_request_contract.py b/tests/products/test_request_contract.py
index e72e4200..387c4fc6 100644
--- a/tests/products/test_request_contract.py
+++ b/tests/products/test_request_contract.py
@@ -995,20 +995,22 @@ def test_from_declared_refuses_a_malformed_unsupported_arguments(
     assert "unsupported_arguments" in str(raised.value)
 
 
-def test_the_reason_vocabulary_has_eight_members_tier_proportion_then_domain() -> None:
+def test_the_reason_vocabulary_has_nine_members_tier_proportion_domain_then_membership() -> None:
     """``24.5-L-12``: the fifth member, in the vocabulary's hyphenated spelling;
     ``24.5-WR-02``: the sixth, appended after it; ``D-IMPL-259``: the two
-    domain verdicts, appended after that — appended, never inserted, so a
-    reader of an older record's reason meets the same roster prefix."""
+    domain verdicts, appended after that; ``D-IMPL-264`` D-05: the ninth,
+    ``not-in-domain``, appended LAST — appended, never inserted, so a reader
+    of an older record's reason meets the same roster prefix."""
     import typing
 
     from ccf.products.request import ProductRequestViolationReason
 
     members = typing.get_args(ProductRequestViolationReason)
-    assert len(members) == 8
-    assert members[-4] == "not-supported-at-tier"
-    assert members[-3] == "not-a-proportion"
-    assert members[-2:] == ("below-minimum", "above-maximum")
+    assert len(members) == 9
+    assert members[-5] == "not-supported-at-tier"
+    assert members[-4] == "not-a-proportion"
+    assert members[-3:-1] == ("below-minimum", "above-maximum")
+    assert members[-1] == "not-in-domain"
 
 
 # --- (g) the tolerance interval: a request number that is not a proportion ---
@@ -1508,6 +1510,9 @@ def test_from_declared_refuses_a_malformed_argument_domains(malformed: Any) -> N
 
 
 def test_a_domain_with_neither_end_is_refused() -> None:
+    """Re-derived under `D-IMPL-264` D-03: a domain naming neither end AND no
+    member set declares neither SHAPE, and *"neither shape is also invalid if
+    `ArgumentDomain` is present"* — the word is still "neither"."""
     with pytest.raises(ValueError) as raised:
         ArgumentDomain()
     assert "neither" in str(raised.value)
@@ -1649,3 +1654,588 @@ def test_the_domain_step_is_deterministic_over_domained_names() -> None:
         for _ in range(5)
     }
     assert verdicts == {"another"}
+
+
+# ---------------------------------------------------------------------------
+# The enumerated shape — a domain is numeric bounds OR a closed member set
+# (`D-IMPL-264` D-03/D-04/D-06; plan 24.7-01).
+# ---------------------------------------------------------------------------
+# Dave, 2026-09-05 (Q3): *"Exactly one domain shape: numeric bounds or
+# enumerated values. Non-empty, duplicate-free, and any declared default must
+# be inside the domain. Neither shape is also invalid if `ArgumentDomain` is
+# present."* (Q4): *"Exact canonical match. No trimming, case folding,
+# aliases, or silent substitution."* (Q6): *"Any supported primitive type,
+# with homogeneous members matching the declared property type."* The
+# members below are the fixture's, never the SDK's (CINV-01).
+
+
+def test_an_enumerated_domain_constructs_and_round_trips() -> None:
+    domain = ArgumentDomain(members=("alpha", "beta"))
+    assert domain.members == ("alpha", "beta")
+    assert domain.minimum is None and domain.maximum is None
+    assert ArgumentDomain.model_validate_json(domain.model_dump_json()) == domain
+
+
+def test_the_enumerated_shape_is_silent_at_none_in_the_canonical_bytes() -> None:
+    """`D-IMPL-243`, criterion 19: a numeric domain written before the member
+    set existed canonicalizes byte-for-byte as it did, so no committed request
+    contract's content address moves."""
+    from ccf.contracts.canonical import canonical_bytes
+
+    assert b"members" not in canonical_bytes(ArgumentDomain(minimum=DOMAIN_FLOOR))
+    assert b"members" in canonical_bytes(ArgumentDomain(members=("alpha",)))
+
+
+def test_a_domain_declaring_both_shapes_is_refused_naming_both() -> None:
+    """D-03: numeric bounds OR a member set, never both."""
+    with pytest.raises(ValueError) as raised:
+        ArgumentDomain(minimum=DOMAIN_FLOOR, members=(1, 2))
+    message = str(raised.value)
+    assert "minimum" in message
+    assert "members" in message
+    assert "D-IMPL-264" in message
+
+
+def test_an_empty_enumerated_domain_is_refused() -> None:
+    """D-03: *"Non-empty"* — a set no value can satisfy is a key with nothing
+    under it, the same defect as a domain naming neither end."""
+    with pytest.raises(ValueError) as raised:
+        ArgumentDomain(members=())
+    assert "empty" in str(raised.value)
+
+
+@pytest.mark.parametrize(
+    "members, named",
+    [
+        (("alpha", "alpha"), "'alpha'"),
+        ((1, Decimal("1")), "1"),
+    ],
+)
+def test_a_duplicate_member_is_refused_naming_it(members: tuple[Any, ...], named: str) -> None:
+    """D-03: *"duplicate-free"* — judged by the membership rule itself, so
+    `1` and `Decimal("1")` ARE the same member while `1` and `True` are not."""
+    with pytest.raises(ValueError) as raised:
+        ArgumentDomain(members=members)
+    message = str(raised.value)
+    assert "duplicate" in message
+    assert named in message
+
+
+@pytest.mark.parametrize(
+    "members",
+    [("alpha", 1), (1, True), (True, "alpha"), ("alpha", Decimal("1"))],
+)
+def test_a_heterogeneous_member_set_is_refused_naming_the_classes(
+    members: tuple[Any, ...],
+) -> None:
+    """D-06: *"homogeneous members"* — one class per set, `bool` its own."""
+    with pytest.raises(ValueError) as raised:
+        ArgumentDomain(members=members)
+    message = str(raised.value)
+    assert "homogeneous" in message or "heterogeneous" in message
+    assert "D-IMPL-264" in message
+
+
+def test_a_numeric_member_set_may_mix_int_and_decimal() -> None:
+    """`int` and `Decimal` are one numeric class to this contract, on
+    `_as_decimal`'s reading; `bool` is not (checked first)."""
+    domain = ArgumentDomain(members=(1, Decimal("1.5")))
+    assert domain.members == (1, Decimal("1.5"))
+
+
+def test_a_non_finite_numeric_member_is_refused() -> None:
+    """The numeric shape's own finiteness rule, carried to the member set: a
+    member nothing can equal is a member nobody declared."""
+    with pytest.raises(ValueError) as raised:
+        ArgumentDomain(members=(Decimal("NaN"),))
+    assert "finite" in str(raised.value)
+
+
+@pytest.mark.parametrize(
+    "presented, member",
+    [("AB", "ab"), (" ab", "ab"), (True, 1), ("1", 1), (1, True), ("ab", "ab ")],
+)
+def test_membership_is_exact_typed_equality(presented: Any, member: Any) -> None:
+    """D-04, criterion 4: no case fold, no trim, no `True == 1`, no `"1" == 1`.
+
+    Each pair is one thing a lenient comparison would admit. The three
+    executed sabotage controls (plan 24.7-01 SUMMARY) plant `.casefold()`,
+    `.strip()` and an untyped `==` in turn and watch this test red.
+    """
+    assert ArgumentDomain(members=(member,)).refuses(presented) == "not-in-domain"
+
+
+@pytest.mark.parametrize(
+    "presented, members",
+    [
+        ("ab", ("ab",)),
+        (1, (1, 2)),
+        (Decimal("2"), (1, 2)),
+        (2, (Decimal("1"), Decimal("2.0"))),
+        (True, (True,)),
+        (False, (True, False)),
+    ],
+)
+def test_a_member_is_admitted_by_exact_equality(
+    presented: Any, members: tuple[Any, ...]
+) -> None:
+    """The other half: exact equality within one class admits, and the numeric
+    class compares by value (`Decimal("2") == 2`) rather than by Python type."""
+    assert ArgumentDomain(members=members).refuses(presented) is None
+
+
+def test_a_numeric_bounds_domain_judges_exactly_as_before() -> None:
+    """The widened `refuses(value: object)` keeps the two-end judgment for the
+    numeric shape, and says nothing about a value with no magnitude (the
+    payload comparison names that one — `type-mismatch` wins by order)."""
+    domain = ArgumentDomain(minimum=DOMAIN_FLOOR, maximum=DOMAIN_CEILING)
+    assert domain.refuses(DOMAIN_FLOOR - 1) == "below-minimum"
+    assert domain.refuses(DOMAIN_CEILING + 1) == "above-maximum"
+    assert domain.refuses(DOMAIN_FLOOR) is None
+    assert domain.refuses(Decimal(DOMAIN_CEILING)) is None
+    assert domain.refuses("zero") is None
+    assert domain.refuses(True) is None
+
+
+# ---------------------------------------------------------------------------
+# `not-in-domain` through the contract validator, the domain step and the
+# request-conformity order (`D-IMPL-264` D-03/D-05/D-06; plan 24.7-01 Task 2).
+# ---------------------------------------------------------------------------
+# Dave (Q5): *"New `not-in-domain` reason. Wrong type and valid type/wrong
+# value are materially different failures. The presented value can be named;
+# disclosure controls whether the allowed set is exposed."* The members are
+# the fixture's, never the SDK's (CINV-01).
+
+ENUMERATED_PARAMETER = "required_leaf"
+ENUMERATED_MEMBERS = ("alpha", "beta")
+
+
+def _enumerated(**overrides: Any) -> ProductRequestContract:
+    fields: dict[str, Any] = {
+        "argument_domains": {
+            ENUMERATED_PARAMETER: ArgumentDomain(members=ENUMERATED_MEMBERS)
+        }
+    }
+    fields.update(overrides)
+    return _contract(**fields)
+
+
+def _typed_arguments() -> SkillArgumentSchema:
+    """The fixture surface plus a `number` and a `boolean` leaf, so every
+    primitive type `D-IMPL-264` D-06 admits has a declared parameter."""
+    arguments = _arguments()
+    return SkillArgumentSchema(
+        properties={
+            **dict(arguments.properties),
+            "numeric_leaf": SkillArgumentProperty(type="number", description="a number"),
+            "flag_leaf": SkillArgumentProperty(type="boolean", description="a flag"),
+        },
+        required=arguments.required,
+    )
+
+
+def test_an_enumerated_domain_over_a_string_parameter_is_admitted() -> None:
+    """D-06: the sibling of the magnitude refusal — an enumerated shape over a
+    string is exactly what the shape is for."""
+    contract = _enumerated()
+    assert contract.argument_domains[ENUMERATED_PARAMETER].members == ENUMERATED_MEMBERS
+    assert (
+        ProductRequestContract.model_validate_json(contract.model_dump_json())
+        == contract
+    )
+
+
+@pytest.mark.parametrize(
+    "name, members",
+    [
+        ("required_leaf", ("alpha",)),
+        ("optional_leaf", (1, 2)),
+        ("numeric_leaf", (1, Decimal("1.5"))),
+        ("flag_leaf", (True, False)),
+    ],
+)
+def test_an_enumerated_domain_is_admitted_over_every_primitive_type(
+    name: str, members: tuple[Any, ...]
+) -> None:
+    """Criterion 5: string, integer, number, boolean — *"don't unnecessarily
+    make this string-specific"*."""
+    contract = _contract(
+        arguments=_typed_arguments(),
+        argument_domains={name: ArgumentDomain(members=members)},
+    )
+    assert contract.argument_domains[name].members == members
+
+
+def test_numeric_bounds_over_a_string_parameter_stay_refused_as_unmeasurable() -> None:
+    """Criterion 5's other half: relaxing `unmeasurable` for the enumerated
+    shape must not relax it for the numeric one."""
+    with pytest.raises(ValueError) as raised:
+        _contract(argument_domains={"required_leaf": ArgumentDomain(minimum=1)})
+    assert "required_leaf" in str(raised.value)
+    assert "magnitude" in str(raised.value)
+
+
+@pytest.mark.parametrize(
+    "name, members, declared",
+    [
+        ("optional_leaf", ("alpha",), "integer"),
+        ("required_leaf", (1,), "string"),
+        ("optional_leaf", (Decimal("1.5"),), "integer"),
+        ("flag_leaf", (1, 0), "boolean"),
+        ("numeric_leaf", (True,), "number"),
+        ("nested", ("alpha",), "object"),
+    ],
+)
+def test_a_mistyped_enumerated_domain_is_refused_naming_the_parameter(
+    name: str, members: tuple[Any, ...], declared: str
+) -> None:
+    """D-06: *"homogeneous members matching the declared property type"* —
+    a member set whose class is not the property's is refused at contract
+    construction, naming the parameter and the declared type (criterion 1)."""
+    with pytest.raises(ValueError) as raised:
+        _contract(
+            arguments=_typed_arguments(),
+            argument_domains={name: ArgumentDomain(members=members)},
+        )
+    message = str(raised.value)
+    # The fragment the `mistyped` list renders for THIS parameter, so the
+    # assertion cannot be satisfied by the sentence's other clauses (which
+    # name every offender class, and the words "integer" and "number", on
+    # every refusal).
+    assert f"{name} declares {declared} but enumerates" in message
+    assert "mistyped" in message
+
+
+def test_a_default_outside_an_enumerated_domain_is_refused_at_declaration() -> None:
+    """Criterion 2: the existing default-respects-domain validator, extended to
+    membership — the class contradicting itself fails where the author can
+    fix it, naming the parameter."""
+    with pytest.raises(ValueError) as raised:
+        _enumerated(defaults={ENUMERATED_PARAMETER: "gamma"})
+    # The `contradicted` list, with this parameter IN it — the sentence
+    # carries the fragment on every refusal, so the bare substring would pass
+    # against an `unmeasurable` refusal of the same contract.
+    assert (
+        f"['{ENUMERATED_PARAMETER}'] carry a declared default outside their own domain"
+        in str(raised.value)
+    )
+
+
+def test_a_default_inside_an_enumerated_domain_is_admitted() -> None:
+    contract = _enumerated(defaults={ENUMERATED_PARAMETER: ENUMERATED_MEMBERS[0]})
+    assert contract.defaults[ENUMERATED_PARAMETER] == ENUMERATED_MEMBERS[0]
+
+
+def test_from_declared_reads_an_enumerated_domain() -> None:
+    declaration = dict(_declared().declaration)
+    declaration["argument_domains"] = {
+        ENUMERATED_PARAMETER: {"members": list(ENUMERATED_MEMBERS)}
+    }
+    contract = ProductRequestContract.from_declared(_declared(declaration=declaration))
+    assert contract.argument_domains[ENUMERATED_PARAMETER] == ArgumentDomain(
+        members=ENUMERATED_MEMBERS
+    )
+
+
+def test_a_value_outside_an_enumerated_domain_is_refused_as_not_in_domain() -> None:
+    """Criterion 3: returned as data by the domain step, naming the key and the
+    presented value; the allowed set rides in `detail` (D-05)."""
+    verdict = refuse_request(
+        request=_request(parameters={ENUMERATED_PARAMETER: "gamma"}),
+        declared=_enumerated(),
+    )
+    assert verdict is not None
+    assert verdict.reason == "not-in-domain"
+    assert verdict.key == ENUMERATED_PARAMETER
+    assert verdict.declared_type == "string"
+    assert verdict.presented_type == "str"
+    assert "gamma" in verdict.detail
+    for member in ENUMERATED_MEMBERS:
+        assert member in verdict.detail
+    assert "D-IMPL-264" in verdict.detail
+    assert verdict.declared_keys == frozenset(_arguments().properties)
+    assert verdict.presented_keys == frozenset({ENUMERATED_PARAMETER})
+
+
+def test_a_mistyped_enumerated_parameter_is_still_type_mismatch() -> None:
+    """D-05: *"wrong type and valid type/wrong value are materially different
+    failures"* — the payload comparison still wins by order."""
+    verdict = refuse_request(
+        request=_request(parameters={ENUMERATED_PARAMETER: 1}),
+        declared=_enumerated(),
+    )
+    assert verdict is not None
+    assert verdict.reason == "type-mismatch"
+
+
+def test_a_member_of_an_enumerated_domain_is_admitted_end_to_end() -> None:
+    assert (
+        refuse_request(
+            request=_request(parameters={ENUMERATED_PARAMETER: ENUMERATED_MEMBERS[1]}),
+            declared=_enumerated(),
+        )
+        is None
+    )
+
+
+def test_an_earlier_step_wins_over_the_enumerated_domain_step() -> None:
+    """The order is unchanged and the domain step is still LAST: a request the
+    address or tier step refuses never reaches membership."""
+    inert = _enumerated(unsupported_arguments={INERT_PARAMETER: INERT_REASON})
+    tier = refuse_request(
+        request=_request(
+            parameters={ENUMERATED_PARAMETER: "gamma", INERT_PARAMETER: "x"}
+        ),
+        declared=inert,
+    )
+    assert tier is not None and tier.reason == "not-supported-at-tier"
+    address = refuse_request(
+        request=_request(
+            schema_version="9.9.9", parameters={ENUMERATED_PARAMETER: "gamma"}
+        ),
+        declared=_enumerated(),
+    )
+    assert address is not None and address.reason == "class-mismatch"
+
+
+def test_the_ninth_reason_names_no_runtime_module() -> None:
+    """Criterion 7: `runtime/` is untouched by the new reason — the door maps
+    by CLASS (`ProductRequestViolation` -> 400), never by reason token."""
+    runtime = REQUEST_MODULE.parent.parent.parent.parent / "runtime"
+    hits = [
+        path
+        for path in runtime.rglob("*.py")
+        if "not-in-domain" in path.read_text(encoding="utf-8")
+    ]
+    assert hits == []
+
+
+# --- (h) intent is a top-level request concept, never an argument (24.7-07) --
+#
+# `D-IMPL-264` D-01 (Dave): *"`intent` is a top-level request concept, not an
+# ordinary argument. `ProductDiscovery.intents` is the declaration of what the
+# class serves. A duplicate `arguments.properties.intent` is a shadow
+# declaration and should fail contract construction."* Amendment 1 F-1 a, his
+# sharpened invariant: *"Absence of a discovery declaration is
+# non-applicability. Presence of a discovery declaration makes its intent set
+# authoritative, including an explicitly empty set."* Amendment 1 F-2: the four
+# frozen rungs that declare `intent` as an argument are READ here as positive
+# controls and never edited. Criteria 10 and 11.
+
+_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
+
+#: The frozen declarations that carry `intent` under `arguments.properties`
+#: (RESEARCH F-2, YAML-parsed). Read only; `D-IMPL-261` / `D-IMPL-263`.
+_SHADOWING_RUNGS = (
+    "examples/cp-01-counterparty-reference-snapshot/ccf_config.yaml",
+    "examples/cp-02-facility-terms-snapshot/ccf_config.yaml",
+    "examples/cp-03-obligor-financial-spread/ccf_config.yaml",
+    "examples/cp-04-corporate-family-tree/ccf_config.yaml",
+)
+
+#: The frozen configs that do NOT (the negative control), plus s1-01, whose
+#: contract is a standalone `DeclaredArtifact` document.
+_CLEAN_CONFIGS = (
+    "examples/cp-00-institutional-holders/ccf_config.yaml",
+    "examples/s1-00-companies-over-revenue/ccf_config.yaml",
+)
+_S1_01_ARTIFACT = "examples/s1-01-hello-context-product/artifacts/request-contract.yaml"
+
+
+def _with_intent_argument() -> SkillArgumentSchema:
+    """The fixture surface plus a shadow `intent` property."""
+    return SkillArgumentSchema(
+        properties={
+            **_arguments().properties,
+            "intent": SkillArgumentProperty(
+                type="string", description="a shadow of the top-level field"
+            ),
+        },
+        required=("required_leaf",),
+    )
+
+
+def _rung_request_contract(config_path: str) -> DeclaredArtifact:
+    """The `request_contract:` section of a frozen `ccf_config.yaml`, derived
+    exactly as the rung derives it — `DeploymentConfig` → `derive_deployment`
+    → the materialised `DeclaredArtifact` document — so the control fails
+    through the entry the rung actually fails through. Nothing is written."""
+    from ccf.deployment.config import DeploymentConfig, derive_deployment
+
+    document = yaml.safe_load(
+        (_REPO_ROOT / config_path).read_text(encoding="utf-8")
+    )
+    derived = derive_deployment(DeploymentConfig.model_validate(document))
+    return DeclaredArtifact(**derived.documents["request_contract"])
+
+
+def test_an_intent_property_is_refused_as_a_shadow_of_the_top_level_field() -> None:
+    """Direct construction and `from_declared` alike, naming the shadow."""
+    with pytest.raises(ValueError) as direct:
+        _contract(arguments=_with_intent_argument())
+    with pytest.raises(ValueError) as declared:
+        ProductRequestContract.from_declared(
+            _declared(
+                declaration={
+                    "schema_name": CLASS_NAME,
+                    "schema_version": CLASS_VERSION,
+                    "arguments": _with_intent_argument().model_dump(mode="json"),
+                }
+            )
+        )
+    for caught in (direct, declared):
+        message = str(caught.value)
+        assert "intent" in message
+        assert "shadow" in message
+        assert "ProductRequest.intent" in message
+        assert "D-IMPL-264" in message
+
+
+@pytest.mark.parametrize("config_path", _SHADOWING_RUNGS)
+def test_the_frozen_cp_rung_declarations_are_the_positive_controls(
+    config_path: str,
+) -> None:
+    """cp-01..cp-04 declare `intent` as an argument; each fails construction.
+
+    `D-IMPL-264` amendment 1 F-2 (Dave): *"cp-01 through cp-04 may go red
+    for this reason and those tests are quarantined under D-IMPL-261 with
+    their assertions unchanged. Do not rewrite those contracts during 24.7."*
+    The declarations are READ from the frozen tree and never written.
+    """
+    artifact = _rung_request_contract(config_path)
+    assert "intent" in artifact.declaration["arguments"]["properties"], (
+        "the frozen declaration no longer carries the shadow — the control"
+        " would be measuring nothing"
+    )
+    with pytest.raises(ValueError) as caught:
+        ProductRequestContract.from_declared(artifact)
+    assert "intent" in str(caught.value)
+    assert "shadow" in str(caught.value)
+
+
+@pytest.mark.parametrize("config_path", _CLEAN_CONFIGS)
+def test_the_frozen_rungs_without_an_intent_property_construct(
+    config_path: str,
+) -> None:
+    """cp-00 and s1-00 through the same entry — the negative control."""
+    artifact = _rung_request_contract(config_path)
+    assert "intent" not in artifact.declaration["arguments"]["properties"]
+    contract = ProductRequestContract.from_declared(artifact)
+    assert "intent" not in contract.arguments.properties
+
+
+def test_the_s1_01_standalone_artifact_constructs() -> None:
+    document = yaml.safe_load(
+        (_REPO_ROOT / _S1_01_ARTIFACT).read_text(encoding="utf-8")
+    )
+    contract = ProductRequestContract.from_declared(DeclaredArtifact(**document))
+    assert "intent" not in contract.arguments.properties
+
+
+def _refuse_intent(*, intent: str, discovery: Any) -> Any:
+    from ccf.products.request import refuse_intent
+
+    return refuse_intent(request=_request(intent=intent), discovery=discovery)
+
+
+def _discovery(*intents: str, domain: str = "fixture-domain") -> Any:
+    from ccf.products.contract import ProductDiscovery
+
+    return ProductDiscovery(
+        domain=domain, intents=frozenset(intents), capabilities=frozenset()
+    )
+
+
+def test_refuse_intent_is_unjudged_without_a_discovery_declaration() -> None:
+    """`NOT_DISCOVERABLE` means no declaration exists — intent is unjudged.
+
+    F-1 a: *"Absence of a discovery declaration is non-applicability."* Any
+    intent at all passes, including one no class anywhere declares. The
+    comparison is by EQUALITY with the sentinel, so a deployment that writes
+    the sentinel's exact content has written the not-discoverable state and
+    is read as such (the second call).
+    """
+    from ccf.products.contract import NOT_DISCOVERABLE, ProductDiscovery
+
+    assert _refuse_intent(intent="fixture-intent", discovery=NOT_DISCOVERABLE) is None
+    assert _refuse_intent(intent="never-declared", discovery=NOT_DISCOVERABLE) is None
+    same_content = ProductDiscovery(
+        domain="not-discoverable",
+        intents=frozenset(),
+        capabilities=frozenset(),
+        audiences=frozenset(),
+    )
+    assert same_content is not NOT_DISCOVERABLE
+    assert _refuse_intent(intent="never-declared", discovery=same_content) is None
+
+
+def test_refuse_intent_admits_a_declared_intent() -> None:
+    assert (
+        _refuse_intent(
+            intent="fixture-intent", discovery=_discovery("fixture-intent", "other")
+        )
+        is None
+    )
+
+
+def test_refuse_intent_refuses_an_undeclared_intent_as_class_mismatch_on_key_intent() -> None:
+    """Returned as data; the declared set rides in `detail` ONLY.
+
+    `class-mismatch` is reused rather than a tenth token (criterion 7 fixes
+    the vocabulary at nine): §6.3 makes intent an addressing token, and a
+    class not registered to serve the intent is addressed to the wrong class
+    in the same family as a lane mismatch — `key="intent"` distinguishes it.
+    `D-IMPL-264` amendment 3 A-8 a (Dave): *"a refusal shell reveals it only
+    according to the disclosure level"* — so the set is in `detail`, never
+    in `declared_type`, which `PERMITTED_AT_MINIMAL` lets cross.
+    """
+    violation = _refuse_intent(
+        intent="other", discovery=_discovery("fixture-intent", "second-intent")
+    )
+    assert violation is not None
+    assert violation.reason == "class-mismatch"
+    assert violation.key == "intent"
+    assert violation.declared_type is None
+    assert violation.presented_type == "other"
+    assert violation.declared_keys == frozenset()
+    assert violation.presented_keys == frozenset()
+    assert violation.overrides == ()
+    assert "other" in violation.detail
+    assert "fixture-intent" in violation.detail
+    assert "second-intent" in violation.detail
+    # Sorted, so two refusals of one declaration are byte-identical.
+    assert violation.detail.index("fixture-intent") < violation.detail.index(
+        "second-intent"
+    )
+    # And in NO typed member: the set has one channel.
+    typed = {k: v for k, v in violation.model_dump().items() if k != "detail"}
+    assert "fixture-intent" not in repr(typed)
+
+
+def test_refuse_intent_refuses_every_intent_against_a_declared_empty_set() -> None:
+    """F-1 a: *"An explicitly declared empty set means 'serves none.'"*
+
+    The set is empty exactly as the sentinel's is; what differs is that a
+    declaration EXISTS (its `domain` is the deployment's, not the sentinel's).
+    """
+    closed = _discovery(domain="fixture-domain")
+    assert closed.intents == frozenset()
+    for intent in ("fixture-intent", "never-declared", ""):
+        violation = _refuse_intent(intent=intent, discovery=closed)
+        assert violation is not None, intent
+        assert violation.reason == "class-mismatch" and violation.key == "intent"
+
+
+@pytest.mark.parametrize(
+    "presented", ["A", " a", "a ", "ab", ""], ids=["case", "lead", "trail", "longer", "empty"]
+)
+def test_refuse_intent_is_exact(presented: str) -> None:
+    """D-04's spirit, one field over: no trimming, no folding, no aliases."""
+    assert _refuse_intent(intent="a", discovery=_discovery("a")) is None
+    assert _refuse_intent(intent=presented, discovery=_discovery("a")) is not None
+
+
+def test_refuse_intent_is_exported() -> None:
+    import ccf.products.request as request_module
+
+    assert "refuse_intent" in request_module.__all__
```

## tests/products/test_resolver_seam.py — diff 6a019322..HEAD (M)

```diff
diff --git a/tests/products/test_resolver_seam.py b/tests/products/test_resolver_seam.py
index 99b556e2..a501643b 100644
--- a/tests/products/test_resolver_seam.py
+++ b/tests/products/test_resolver_seam.py
@@ -50,6 +50,7 @@ from __future__ import annotations
 
 import copy
 import dataclasses
+import inspect
 import pathlib
 from collections.abc import Iterator, Mapping
 from datetime import UTC, datetime, timedelta
@@ -78,10 +79,12 @@ from ccf.replay.record import (
     NO_PRODUCT_ADDRESS,
     DecisionReplayRecord,
     PolicyBinding,
+    ResolutionNotApplicable,
 )
 from ccf.products.resolver import (
     GovernedResolver,
     ProductNotResolvable,
+    RefusalRecorderProtocol,
     ReplayRefusalRecorder,
     ServedProductResolverProtocol,
 )
@@ -350,6 +353,41 @@ def booted_with_ceiling(tmp_path: pathlib.Path) -> Iterator[_Booted]:
     )
 
 
+def _product_class_declaring(intents: list[str]) -> dict[str, Any]:
+    """The fixture class document with a ``discovery`` block DECLARED.
+
+    24.7-07, `D-IMPL-264` D-01 as amended (F-1 a). The block is authored
+    HERE, in a test-side document, never in ``src/`` (CINV-01): the domain
+    and the intent vocabulary are fixture figures. A declared set — even an
+    empty one — is the state the stock document (no ``discovery:`` block,
+    which reads as :data:`~ccf.products.contract.NOT_DISCOVERABLE`) is NOT.
+    """
+    product_class = copy.deepcopy(
+        next(doc for key, *_rest, doc in ARTIFACT_SET if key == PRODUCT_CLASS_KEY)
+    )
+    product_class["discovery"] = {
+        "domain": "fixture-domain",
+        "intents": intents,
+        "capabilities": [],
+        "audiences": [],
+    }
+    return product_class
+
+
+@pytest.fixture
+def booted_with_intents(tmp_path: pathlib.Path) -> Iterator[_Booted]:
+    """The same deployment, with the class DECLARING that it serves exactly
+    the fixture intent — the authoritative state."""
+    yield from _boot(tmp_path, product_class=_product_class_declaring(["fixture-intent"]))
+
+
+@pytest.fixture
+def booted_with_no_intents(tmp_path: pathlib.Path) -> Iterator[_Booted]:
+    """The same deployment, with the class declaring an EMPTY intent set —
+    *"serves none"* (F-1 a), which is not the sentinel's state."""
+    yield from _boot(tmp_path, product_class=_product_class_declaring([]))
+
+
 def _boot(
     tmp_path: pathlib.Path,
     *,
@@ -497,6 +535,184 @@ def test_the_reference_resolver_conforms_to_the_protocol(booted: _Booted) -> Non
     assert isinstance(_resolver(booted), ServedProductResolverProtocol)
 
 
+# --- 24.7-04: the recorder seam requires the explicit resolution state -------
+
+
+def _requires_the_resolution_state(function: Any) -> bool:
+    """True when ``resolution`` is keyword-only with NO default.
+
+    ``D-IMPL-264`` D-10 am.1 (F-3 a), Dave verbatim: *"Any API that
+    constructs or delegates construction of a replay record must require an
+    explicit resolution state: effective/partial resolution or explicit
+    not-applicable marker. No intermediate layer may manufacture the marker
+    from omission."* The ``@runtime_checkable`` Protocol check covers the
+    presence of ``record``, not its signature, so the signature is read
+    here directly.
+    """
+    parameter = inspect.signature(function).parameters["resolution"]
+    return (
+        parameter.default is inspect.Parameter.empty
+        and parameter.kind is inspect.Parameter.KEYWORD_ONLY
+    )
+
+
+@pytest.mark.parametrize(
+    "seam",
+    [
+        pytest.param(RefusalRecorderProtocol.record, id="RefusalRecorderProtocol.record"),
+        pytest.param(ReplayRefusalRecorder.record, id="ReplayRefusalRecorder.record"),
+        pytest.param(GovernedResolver._record_refusal, id="GovernedResolver._record_refusal"),
+    ],
+)
+def test_no_recorder_signature_defaults_the_resolution_state(seam: Any) -> None:
+    """The three APIs that construct or delegate construction of a record all
+    require the state; a default on any of them would be the one call frame
+    of omission the ruling closed.
+    """
+    assert _requires_the_resolution_state(seam), inspect.signature(seam)
+
+
+def test_the_conformance_check_sees_a_defaulted_signature() -> None:
+    """The planted decoy: a recorder whose ``record`` defaults the state is
+    exactly what the check above refuses. If this ever passes the check,
+    the check has stopped reading signatures and the test above is vacuous.
+    """
+
+    class _Defaulting:
+        def record(
+            self,
+            envelope: RefusalEnvelope,
+            *,
+            perspective: Perspective,
+            recorded_at: datetime,
+            resolution: Any = None,
+        ) -> RefusalEnvelope:
+            return envelope
+
+    class _Positional:
+        def record(
+            self, envelope: RefusalEnvelope, resolution: Any
+        ) -> RefusalEnvelope:
+            return envelope
+
+    # Presence is what `@runtime_checkable` sees; the signature is not.
+    assert isinstance(_Defaulting(), RefusalRecorderProtocol)
+    assert not _requires_the_resolution_state(_Defaulting.record)
+    assert not _requires_the_resolution_state(_Positional.record)
+
+
+# --- 24.7-07: intent is judged against the DECLARED discovery set -----------
+#
+# `D-IMPL-264` D-01 as amended by amendment 1 F-1 a (Dave, verbatim):
+# *"Absence of a discovery declaration is non-applicability. Presence of a
+# discovery declaration makes its intent set authoritative, including an
+# explicitly empty set."* Three states, hosted in `GovernedResolver.resolve`
+# beside the address check, before any resolution step (D-09: no resolution
+# ran, said so positively) — and the deciding class declaration IS pinned on
+# the record (amendment 3 B-3 a: *"replay should preserve the declaration
+# that actually governed the outcome"*). Criterion 10.
+#
+# Sabotage (recorded in the plan SUMMARY, F-1 reading (b)): judge whenever
+# `discovery.intents == frozenset()` and the FIRST test below reds — along
+# with every other test in this module, because every fixture serves under
+# `NOT_DISCOVERABLE`. That is the reading Dave rejected.
+
+
+def test_intent_is_unjudged_when_no_discovery_is_declared(booted: _Booted) -> None:
+    """The stock fixture declares no `discovery`: any intent serves.
+
+    The D-01 am.1 control — including an intent no class anywhere declares.
+    Every existing deployment, hw1 and the governed-resolver roster serve
+    exactly as they did before this phase.
+    """
+    assert isinstance(
+        _ask(_resolver(booted), _request(intent="fixture-intent")), ServedProduct
+    )
+    assert isinstance(
+        _ask(_resolver(booted), _request(intent="never-declared")), ServedProduct
+    )
+
+
+def test_a_declared_intent_serves_and_an_undeclared_one_is_refused_as_data(
+    booted_with_intents: _Booted,
+) -> None:
+    """Declared → authoritative: the member serves, a non-member is refused
+    as data, before the graph is touched, with the deciding declaration pinned.
+
+    The record: dimension 2 says positively that no resolution ran
+    (`refused-before-resolution`), its bindings are EXACTLY the recorder's
+    bundle pin plus the class-declaration pin — minted the way `class_source`
+    mints it, so it resolves to the exact bytes that declared the intent set
+    — and NO request-contract pin, because none was resolved against (which
+    is why plan 09's D-11 inference reads request-contract + constraint pins
+    and never a class-declaration pin). Sabotage (recorded in the SUMMARY):
+    drop the pin and the bindings assertion reds.
+    """
+    reader = _RecordingReader(booted_with_intents.fabric.handle.reader)
+    fabric = dataclasses.replace(
+        booted_with_intents.fabric,
+        handle=_HandleWithReader(booted_with_intents.fabric.handle, reader),
+    )
+    resolver = _resolver(booted_with_intents, fabric=fabric)
+
+    served = _ask(resolver, _request(intent="fixture-intent"))
+    assert isinstance(served, ServedProduct)
+    reads_for_the_served_product = len(reader.calls)
+    assert reads_for_the_served_product > 0
+
+    outcome = _ask(resolver, _request(intent="other"))
+    assert isinstance(outcome, RefusalEnvelope)
+    assert outcome.kind == "product-request-violation"
+    assert outcome.reason == "class-mismatch"
+    assert outcome.key == "intent"
+    assert outcome.pre_assembly_lineage is None
+    assert outcome.request.product_id == PRODUCT_CLASS
+    # An addressing verdict costs nothing: no read beyond the served product's.
+    assert len(reader.calls) == reads_for_the_served_product
+
+    assert outcome.replay_reference != NO_REPLAY_REFERENCE
+    record = DecisionReplayRecord.model_validate_json(
+        booted_with_intents.store.get(
+            content_address=booted_with_intents.store.resolve_uri(
+                uri=outcome.replay_reference
+            )
+        )
+    )
+    assert ResolutionNotApplicable.model_validate_json(
+        record.policy_bindings.request_resolution
+    ) == ResolutionNotApplicable(reason="refused-before-resolution")
+    class_pin = PolicyBinding(
+        key=PRODUCT_CLASS_KEY,
+        version=booted_with_intents.fabric.pins.version_for(PRODUCT_CLASS_KEY),
+    )
+    # The pin the manifest minted IS the declaration's content address — the
+    # same address `class_source` carries on a defaulted value.
+    assert class_pin.version == content_hash(resolver._declaration())
+    bundle_pin = PolicyBinding(
+        key=POLICY_BUNDLE_KEY,
+        version=booted_with_intents.fabric.pins.version_for(POLICY_BUNDLE_KEY),
+    )
+    assert set(record.policy_bindings.bindings) == {bundle_pin, class_pin}
+    assert all(
+        binding.key != REQUEST_CONTRACT_KEY for binding in record.policy_bindings.bindings
+    )
+    # Dimension 1 says nothing was read; dimension 5 says no product came of it.
+    assert record.context_fabric_snapshot.store_watermark == NO_FABRIC_READ
+    assert record.content_generation_path.product_content_address == (
+        NO_PRODUCT_ADDRESS
+    )
+
+
+def test_a_declared_empty_set_serves_none(booted_with_no_intents: _Booted) -> None:
+    """F-1 a: *"An explicitly declared empty set means 'serves none.'"*"""
+    outcome = _ask(_resolver(booted_with_no_intents), _request(intent="fixture-intent"))
+
+    assert isinstance(outcome, RefusalEnvelope)
+    assert outcome.kind == "product-request-violation"
+    assert outcome.reason == "class-mismatch"
+    assert outcome.key == "intent"
+
+
 # --- behavior 1: a bad question is refused before the graph is touched -------
```

## tests/products/test_tolerance_exceeded.py — diff 6a019322..HEAD (M)

```diff
diff --git a/tests/products/test_tolerance_exceeded.py b/tests/products/test_tolerance_exceeded.py
index e8df7c4c..84103bcc 100644
--- a/tests/products/test_tolerance_exceeded.py
+++ b/tests/products/test_tolerance_exceeded.py
@@ -628,7 +628,8 @@ def test_a_class_default_the_contract_does_not_declare_is_refused() -> None:
         class_defaults={DEBT_TOLERANCE_PARAMETER: CLASS_DEFAULT},
         class_source=pin,
     )
-    tolerance = resolved.parameter(DEBT_TOLERANCE_PARAMETER)  # type: ignore[union-attr]
+    assert resolved.refusal is None, resolved.refusal
+    tolerance = resolved.evidence.parameter(DEBT_TOLERANCE_PARAMETER)
     assert tolerance is not None
     assert tolerance.authority == "default"
     assert tolerance.source == pin
```

## tests/replay/fixtures/golden_13bd250/produce.py — diff 6a019322..HEAD (M)

```diff
diff --git a/tests/replay/fixtures/golden_13bd250/produce.py b/tests/replay/fixtures/golden_13bd250/produce.py
index 4ff958fb..8c9cb2c1 100644
--- a/tests/replay/fixtures/golden_13bd250/produce.py
+++ b/tests/replay/fixtures/golden_13bd250/produce.py
@@ -61,7 +61,12 @@ from ccf.products.contract import (
 from ccf.products.gates import ServableProduct, run_gates
 from ccf.projection.engine import ExecutionResult, OperatorRegistry, ProjectionEngine
 from ccf.projection.plan import Perspective, ProjectionOutput, ProjectionPlan
-from ccf.replay.record import DecisionReplayRecord, PolicyBinding, build_replay_record
+from ccf.replay.record import (
+    DecisionReplayRecord,
+    PolicyBinding,
+    ResolutionNotApplicable,
+    build_replay_record,
+)
 from ccf.replay.serve import ReplayWriter, serve
 from ccf.signal.envelope import SignalEnvelope, SourceIdentity
 
@@ -329,6 +334,15 @@ def produce(fixture_dir: Path) -> dict[str, Any]:
             ),
             assembly_mode="algorithmic",
             recorded_at=NOW,
+            # 24.7-06 (D-IMPL-264 D-10 / D-12): the builder now requires an
+            # explicit resolution state, and this path ran no resolution step.
+            # This script is a REGENERATION AID whose OUTPUT is the committed
+            # D-12 control (`artifacts/`, `manifest.json`, `fabric.sqlite3`),
+            # captured at 13bd250 with the legacy sentinel. It is edited so it
+            # stays a valid script against the ruled API; it is NOT run inside
+            # 24.7, and `test_golden_13bd250.py` never calls `produce()` -- it
+            # replays the STORED record. Running it would move the control.
+            resolution=ResolutionNotApplicable(reason="no-resolution-step"),
         )
         served = serve(
             product=gated,
```

## tests/replay/test_dimension_extensions.py — diff 6a019322..HEAD (M)

```diff
diff --git a/tests/replay/test_dimension_extensions.py b/tests/replay/test_dimension_extensions.py
index 36ac4254..ca683ad4 100644
--- a/tests/replay/test_dimension_extensions.py
+++ b/tests/replay/test_dimension_extensions.py
@@ -50,6 +50,7 @@ from ccf.replay.record import (
     PerspectiveConditioning,
     PolicyBinding,
     PolicyBindingsSnapshot,
+    ResolutionNotApplicable,
     build_replay_record,
 )
 from tests.replay.test_harness_trace import PRE_CHANGE_CANONICAL
@@ -98,6 +99,12 @@ def _product(*, tenant_id: str = "tenant-a") -> ContextProductContract:
 def _build(**overrides: Any) -> DecisionReplayRecord:
     tenant_id = overrides.pop("tenant_id", "tenant-a")
     principal_id = overrides.pop("principal_id", "principal-1")
+    # 24.7-04 (D-IMPL-264 D-09/D-10): this fixture mints records with no
+    # resolver in the path and states so explicitly; a test that wants to
+    # probe the guard passes its own `resolution=`.
+    resolution = overrides.pop(
+        "resolution", ResolutionNotApplicable(reason="no-resolution-step")
+    )
     return build_replay_record(
         execution=_execution(tenant_id=tenant_id),
         product=_product(tenant_id=tenant_id),
@@ -105,6 +112,7 @@ def _build(**overrides: Any) -> DecisionReplayRecord:
         policy_bindings=(PolicyBinding(key="policy.bundle", version="v1"),),
         assembly_mode="algorithmic",
         recorded_at=NOW,
+        resolution=resolution,
         **overrides,
     )
```

## tests/replay/test_engine_rehydration.py — diff 6a019322..HEAD (M)

```diff
diff --git a/tests/replay/test_engine_rehydration.py b/tests/replay/test_engine_rehydration.py
index e4f89c23..751dbf87 100644
--- a/tests/replay/test_engine_rehydration.py
+++ b/tests/replay/test_engine_rehydration.py
@@ -43,7 +43,12 @@ from ccf.graph.protocols import (
     SnapshotPinnable,
     StoreSnapshotPin,
 )
-from ccf.controlplane.artifacts import DebtProfile
+from ccf.controlplane.artifacts import (
+    ConstraintApplicability,
+    DebtProfile,
+    PolicyConstraint,
+    ProductClassDeclaration,
+)
 from ccf.halflife.assessment import (
     NO_DEBT_EVIDENCE,
     NO_OBLIGATION_IN_FORCE,
@@ -71,25 +76,31 @@ from ccf.products.contract import (
     register_product_class,
 )
 from ccf.products.gates import ServableProduct, run_gates
-from ccf.products.request import ProductRequest, request_seeds
+from ccf.products.provenance import EffectiveRequest, ProvenanceSource
+from ccf.products.request import ProductRequest, ProductRequestContract, request_seeds
 from ccf.projection.engine import ExecutionResult, OperatorRegistry, ProjectionEngine
 from ccf.projection.plan import Perspective, ProjectionOutput, ProjectionPlan
 from ccf.replay import engine as engine_module
 from ccf.replay import snapshots as snapshots_module
 from ccf.replay.engine import (
     ReplayDivergence,
+    ReplayError,
     ReplayOutcome,
+    ReplayResolutionClaimMismatch,
     ReplayUnresolvable,
     replay,
 )
 from ccf.replay.record import (
+    NO_REQUEST_RESOLUTION,
     ContentGenerationPath,
     ContextFabricSnapshot,
     DecisionReplayRecord,
     PolicyBinding,
+    ResolutionNotApplicable,
     build_replay_record,
 )
 from ccf.replay.serve import ReplayWriter, serve
+from ccf.skills.catalog import SkillArgumentProperty, SkillArgumentSchema
 from ccf.replay.snapshots import (
     SnapshotPinUnresolvable,
     SnapshotReader,
@@ -554,6 +565,7 @@ def _serve(
         ),
         assembly_mode="algorithmic",
         recorded_at=NOW,
+        resolution=ResolutionNotApplicable(reason="no-resolution-step"),
         request=request,
     )
     served = serve(
@@ -792,6 +804,7 @@ def test_a_record_written_before_the_debt_seam_still_replays(
         ),
         assembly_mode="algorithmic",
         recorded_at=NOW,
+        resolution=ResolutionNotApplicable(reason="no-resolution-step"),
     )
     served = serve(
         product=gated,
@@ -973,6 +986,7 @@ def test_a_record_written_before_the_evidence_seam_still_replays(
         ),
         assembly_mode="algorithmic",
         recorded_at=NOW,
+        resolution=ResolutionNotApplicable(reason="no-resolution-step"),
     )
     served = serve(
         product=gated,
@@ -1314,6 +1328,7 @@ def test_a_record_written_before_the_recency_seam_still_replays(
         ),
         assembly_mode="algorithmic",
         recorded_at=NOW,
+        resolution=ResolutionNotApplicable(reason="no-resolution-step"),
     )
     served = serve(
         product=gated,
@@ -1585,6 +1600,7 @@ def test_a_record_written_before_the_obligation_seam_still_replays(
         ),
         assembly_mode="algorithmic",
         recorded_at=NOW,
+        resolution=ResolutionNotApplicable(reason="no-resolution-step"),
     )
     served = serve(
         product=gated,
@@ -1772,6 +1788,7 @@ def test_omitting_the_question_is_indistinguishable_from_passing_none(
         ),
         "assembly_mode": "algorithmic",
         "recorded_at": NOW,
+        "resolution": ResolutionNotApplicable(reason="no-resolution-step"),
     }
     assert content_hash(build_replay_record(**common)) == content_hash(
         build_replay_record(**common, request=None)
@@ -1981,6 +1998,7 @@ def test_a_record_written_before_the_pin_seam_still_replays(
         ),
         assembly_mode="algorithmic",
         recorded_at=NOW,
+        resolution=ResolutionNotApplicable(reason="no-resolution-step"),
     )
     served = serve(
         product=gated,
@@ -2171,3 +2189,283 @@ def test_the_replay_path_never_resolves_latest() -> None:
     for module in (engine_module, snapshots_module):
         source = inspect.getsource(module)
         assert "resolve_latest" not in source, module.__name__
+
+
+# --- 24.7-09: replay verifies the not-applicable claim against pinned state ---
+#
+# ``D-IMPL-264`` D-11 (Dave, verbatim): "Construction prevents new incomplete
+# records. Replay verification protects against a false `not-applicable` claim.
+# The verification must use the pinned historical contract/constraint state,
+# not today's configuration." Amendment 3, B-3 a, narrows the evidence base:
+# "request-contract pin + applicable constraint pins are the evidence that
+# effective-request resolution ran. Do not use 'any class declaration pin
+# exists' as the proxy, because the intent check can legitimately pin the class
+# declaration before parameter resolution occurs." D-12 / F-4: a record carrying
+# the legacy sentinel is exempt, by the ``NO_GRAPH_QUERIES`` precedent.
+#
+# Every artifact below is test fixture: the engine under test knows nothing of
+# a "leaf" parameter or a "replay-fixture" regime. It knows two artifact
+# CLASSES, and that is the whole of what these tests hold it to.
+
+REQUEST_CONTRACT_KEY = "test/request-contract"
+POLICY_CONSTRAINT_KEY = "test/policy-constraint"
+CLASS_DECLARATION_KEY = "test/class-declaration"
+
+
+def _request_contract() -> ProductRequestContract:
+    """The smallest request contract that constructs — one declared leaf."""
+    return ProductRequestContract(
+        semver="1.0.0",
+        schema_name=SCHEMA_NAME,
+        schema_version=SCHEMA_VERSION,
+        arguments=SkillArgumentSchema(
+            properties={
+                "leaf": SkillArgumentProperty(
+                    type="string", description="a declared leaf parameter"
+                )
+            },
+            required=("leaf",),
+        ),
+    )
+
+
+def _policy_constraint() -> PolicyConstraint:
+    """One governed boundary on the fixture's leaf, in force at BOUNDARY."""
+    return PolicyConstraint(
+        semver="1.0.0",
+        policy_id="replay-fixture",
+        applies_to=ConstraintApplicability(product_class=SCHEMA_NAME),
+        parameter="leaf",
+        operator="maximum",
+        value=Decimal("1"),
+        source_authority="fixture-authority",
+        effective_from=T_MARCH,
+        reason="fixture reason",
+    )
+
+
+def _class_declaration() -> ProductClassDeclaration:
+    """The class's authored governance — what plan 07's intent refusal pins."""
+    return ProductClassDeclaration(
+        semver="1.0.0",
+        schema_name=SCHEMA_NAME,
+        schema_version=SCHEMA_VERSION,
+        ttl_anchor="from_decision",
+        assembly_mode="algorithmic",
+        max_ttl_key=MAX_TTL_KEY,
+        required_operator_keys=("temporal.as-of-boundary",),
+    )
+
+
+def _serve_claiming(
+    deployment: _Deployment,
+    *,
+    bindings: tuple[PolicyBinding, ...],
+    resolution: EffectiveRequest | ResolutionNotApplicable,
+) -> tuple[str, DecisionReplayRecord]:
+    """The real serve path, with the dimension-2 pair under the test's control.
+
+    ``_serve`` pins the bundle and states ``no-resolution-step``. The D-11
+    check reads exactly two things off a record — what it PINNED and what it
+    CLAIMED — so these tests set the two independently and hold the engine to
+    their combination. The bundle pin is always present, as it is on every
+    record this module serves; ``bindings`` are added beside it.
+
+    The candidate's lineage names every version the record pins, because
+    ``_Environment.rehydrate_product`` rebuilds ``policy_bundle_versions``
+    from the record's bindings — a product that pinned less than its record
+    would diverge on its content address, which is the fixture's own
+    rehydration contract and not the claim under test here.
+    """
+    all_bindings = (
+        PolicyBinding(key=POLICY_BUNDLE_KEY, version=deployment.policy_version),
+        *bindings,
+    )
+    execution = deployment.execute()
+    product_class = deployment.product_class()
+    candidate = deployment.candidate(execution)
+    candidate = candidate.model_copy(
+        update={
+            "lineage": candidate.lineage.model_copy(
+                update={
+                    "policy_bundle_versions": frozenset(
+                        binding.version for binding in all_bindings
+                    )
+                }
+            )
+        }
+    )
+    gated = run_gates(
+        candidate,
+        engine_resolved=execution.operators_invoked,
+        now=NOW,
+        registry=deployment.registry,
+        product_class=product_class,
+    )
+    assert isinstance(gated, ServableProduct)
+    record = build_replay_record(
+        execution=execution,
+        product=gated.product,
+        perspective=deployment.perspective(),
+        policy_bindings=all_bindings,
+        assembly_mode="algorithmic",
+        recorded_at=NOW,
+        resolution=resolution,
+    )
+    served = serve(
+        product=gated,
+        record=record,
+        replay_writer=ReplayWriter(
+            store=deployment.store, artifact_class=ARTIFACT_CLASS
+        ),
+    )
+    return served.replay_ref.content_address, record
+
+
+@pytest.mark.parametrize(
+    ("key", "artifact", "class_name"),
+    [
+        (REQUEST_CONTRACT_KEY, _request_contract(), "ProductRequestContract"),
+        (POLICY_CONSTRAINT_KEY, _policy_constraint(), "PolicyConstraint"),
+    ],
+    ids=["request-contract", "policy-constraint"],
+)
+def test_a_false_not_applicable_claim_is_refused_against_the_pinned_contract(
+    deployment: _Deployment, key: str, artifact: CCFContract, class_name: str
+) -> None:
+    """D-11: a record that CLAIMS no resolution applies while it PINS a request
+    contract (or an applicable policy constraint) is refused by name.
+
+    In ``src/`` + ``runtime/`` those two artifact classes reach a record's
+    bindings only through ``GovernedResolver._applied_bindings(effective)`` —
+    which exists only when a resolution ran (am.3 B-3 a). So the pin is the
+    evidence, and the claim contradicts it. Not a divergence (nothing
+    re-executed differed), not unresolvable (the pin resolves — that is the
+    point): its own finding, its own token.
+    """
+    version = deployment.registry.register(key, artifact)
+    address, _record = _serve_claiming(
+        deployment,
+        bindings=(PolicyBinding(key=key, version=version),),
+        resolution=ResolutionNotApplicable(reason="no-resolution-step"),
+    )
+
+    with pytest.raises(ReplayResolutionClaimMismatch) as excinfo:
+        _replay(deployment, address)
+
+    assert excinfo.value.reason == "resolution_claim_mismatch"
+    assert excinfo.value.claimed_reason == "no-resolution-step"
+    assert excinfo.value.pinned == ((key, version, class_name),)
+    assert excinfo.value.content_address == address
+    assert key in str(excinfo.value)
+    assert isinstance(excinfo.value, ReplayError)
+    assert not isinstance(excinfo.value, (ReplayDivergence, ReplayUnresolvable))
+
+
+def test_the_same_bindings_with_a_resolution_replay(
+    deployment: _Deployment,
+) -> None:
+    """The control for the pin: the identical contract pin beside the
+    resolution that consulted it replays. The check reads the pair, not the
+    pin alone — a record that pins a contract AND says it resolved against
+    it is exactly what the governed resolver writes."""
+    version = deployment.registry.register(REQUEST_CONTRACT_KEY, _request_contract())
+    resolution = EffectiveRequest(
+        parameters=(),
+        guidance=(),
+        overrides=(),
+        applied=(
+            ProvenanceSource(
+                kind="artifact", identity=REQUEST_CONTRACT_KEY, version=version
+            ),
+        ),
+        asked_at=BOUNDARY,
+    )
+    address, record = _serve_claiming(
+        deployment,
+        bindings=(PolicyBinding(key=REQUEST_CONTRACT_KEY, version=version),),
+        resolution=resolution,
+    )
+
+    outcome = _replay(deployment, address)
+
+    assert outcome.record == record
+    assert (
+        EffectiveRequest.model_validate_json(
+            outcome.record.policy_bindings.request_resolution
+        )
+        == resolution
+    )
+
+
+def test_a_marker_beside_no_resolution_artifact_replays(
+    deployment: _Deployment,
+) -> None:
+    """D-09: legitimate non-applicability. The stock record pins the bundle
+    only and states ``no-resolution-step`` — nothing in its bindings says a
+    resolution ran, so nothing contradicts the claim, and it replays."""
+    address, record = _serve(deployment)
+
+    outcome = _replay(deployment, address)
+
+    assert outcome.record == record
+    assert ResolutionNotApplicable.model_validate_json(
+        outcome.record.policy_bindings.request_resolution
+    ) == ResolutionNotApplicable(reason="no-resolution-step")
+
+
+def test_a_marker_beside_only_a_class_declaration_pin_is_not_refused(
+    deployment: _Deployment,
+) -> None:
+    """The am.3 B-3 a control, Dave verbatim: *"Do not use 'any class
+    declaration pin exists' as the proxy, because the intent check can
+    legitimately pin the class declaration before parameter resolution
+    occurs."* This is the shape plan 07's intent refusal writes — the deciding
+    declaration pinned beside ``refused-before-resolution`` — and it MUST
+    replay. Sabotage: add ``ProductClassDeclaration`` to the engine's trigger
+    tuple and this test reds while the false-claim test stays green.
+    """
+    version = deployment.registry.register(CLASS_DECLARATION_KEY, _class_declaration())
+    address, record = _serve_claiming(
+        deployment,
+        bindings=(PolicyBinding(key=CLASS_DECLARATION_KEY, version=version),),
+        resolution=ResolutionNotApplicable(reason="refused-before-resolution"),
+    )
+
+    outcome = _replay(deployment, address)
+
+    assert outcome.record == record
+
+
+def test_a_legacy_sentinel_record_is_exempt(deployment: _Deployment) -> None:
+    """D-12 / F-4: the legacy sentinel is a compatibility claim, not a
+    not-applicable claim, and the check does not read it — the
+    ``NO_GRAPH_QUERIES`` precedent. Take the record the false-claim test
+    refuses, rewrite its dimension-2 value to the sentinel, and it replays:
+    *"Do not retroactively declare previously valid replay artifacts
+    defective because the SDK acquired a stronger contract."*
+    """
+    version = deployment.registry.register(REQUEST_CONTRACT_KEY, _request_contract())
+    _address, record = _serve_claiming(
+        deployment,
+        bindings=(PolicyBinding(key=REQUEST_CONTRACT_KEY, version=version),),
+        resolution=ResolutionNotApplicable(reason="no-resolution-step"),
+    )
+    legacy = record.model_copy(
+        update={
+            "policy_bindings": record.policy_bindings.model_copy(
+                update={"request_resolution": NO_REQUEST_RESOLUTION}
+            )
+        }
+    )
+    assert legacy.policy_bindings.request_resolution == NO_REQUEST_RESOLUTION
+    address = deployment.store.put(
+        tenant_id=TENANT,
+        artifact_class=ARTIFACT_CLASS,
+        name="written-before-the-marker-existed",
+        artifact=legacy,
+    ).content_address
+
+    outcome = _replay(deployment, address)
+
+    assert outcome.record == legacy
```

## tests/replay/test_harness_trace.py — diff 6a019322..HEAD (M)

```diff
diff --git a/tests/replay/test_harness_trace.py b/tests/replay/test_harness_trace.py
index d8240dfb..0965b5f8 100644
--- a/tests/replay/test_harness_trace.py
+++ b/tests/replay/test_harness_trace.py
@@ -36,6 +36,7 @@ from ccf.replay.record import (
     HarnessTrace,
     ModelVersionRecord,
     PolicyBinding,
+    ResolutionNotApplicable,
     build_replay_record,
 )
 
@@ -126,6 +127,7 @@ def _build(**overrides: Any) -> DecisionReplayRecord:
         policy_bindings=(PolicyBinding(key="policy.bundle", version="v1"),),
         assembly_mode="algorithmic",
         recorded_at=NOW,
+        resolution=ResolutionNotApplicable(reason="no-resolution-step"),
         **overrides,
     )
 
@@ -218,6 +220,17 @@ def test_every_pre_change_field_is_byte_for_byte_unchanged() -> None:
     ).replace(
         b',"hitl_actions":"no-hitl-actions"',
         b"",
+    ).replace(
+        # 24.7-06, D-IMPL-264 D-10 / P-2: the builder REQUIRES an explicit
+        # resolution state, so `_build` states the typed not-applicable
+        # marker (this fixture runs no resolution step). Unlike every other
+        # key above, the marker is NOT a sentinel default: the legacy
+        # `no-request-resolution` stays the field default and hash-transparent
+        # for records written before (D-12), while a NEW record renders its
+        # stated state once (24.6-03). Removing the stated key reproduces the
+        # captured literal — the literal itself is still never edited.
+        b'"request_resolution":"{\\"reason\\":\\"no-resolution-step\\"}",',
+        b"",
     ).replace(
         b',"workflow_step_sequence":"no-workflow-trace"',
         b"",
```


<!-- mid-payload read-proof -->
```
READ-PROOF bundle-tests-part-2.md: 0e1693dab969a353
```

## tests/replay/test_query_sequence_pin.py — diff 6a019322..HEAD (M)

```diff
diff --git a/tests/replay/test_query_sequence_pin.py b/tests/replay/test_query_sequence_pin.py
index b9c7fff5..7445d518 100644
--- a/tests/replay/test_query_sequence_pin.py
+++ b/tests/replay/test_query_sequence_pin.py
@@ -71,6 +71,7 @@ from ccf.replay.record import (
     PerspectiveConditioning,
     PolicyBinding,
     PolicyBindingsSnapshot,
+    ResolutionNotApplicable,
     build_replay_record,
 )
 from ccf.replay.serve import (
@@ -207,6 +208,7 @@ def _record_for(
         ),
         assembly_mode=fabric.control["product_class"]["assembly_mode"],
         recorded_at=fabric.now,
+        resolution=ResolutionNotApplicable(reason="no-resolution-step"),
     )
     return gated, record
```

## tests/replay/test_refusal_replay_record.py — diff 6a019322..HEAD (M)

```diff
diff --git a/tests/replay/test_refusal_replay_record.py b/tests/replay/test_refusal_replay_record.py
index aeed5063..1e2a6bca 100644
--- a/tests/replay/test_refusal_replay_record.py
+++ b/tests/replay/test_refusal_replay_record.py
@@ -76,9 +76,11 @@ from ccf.replay.record import (
     NO_ASSEMBLER,
     NO_FABRIC_READ,
     NO_PRODUCT_ADDRESS,
+    NO_REQUEST_RESOLUTION,
     NO_ROLE_RESOLVED,
     DecisionReplayRecord,
     PolicyBinding,
+    ResolutionNotApplicable,
     build_replay_record,
 )
 
@@ -419,6 +421,9 @@ def test_the_assembler_in_force_reaches_dimension_four_on_either_outcome(
         "recorded_at": _RECORDED_AT,
         "assembler_id": "fixture.assembler",
         "assembler_version": "2.1.0",
+        # 24.7-04 (D-IMPL-264 D-09/D-10): a fixture-minted record states
+        # that no resolution step ran in this path.
+        "resolution": ResolutionNotApplicable(reason="no-resolution-step"),
     }
     if outcome == "served":
         record = build_replay_record(
@@ -445,6 +450,7 @@ def test_no_assembler_is_asserted_rather_than_left_absent(outcome: str) -> None:
         "policy_bindings": (),
         "assembly_mode": "algorithmic",
         "recorded_at": _RECORDED_AT,
+        "resolution": ResolutionNotApplicable(reason="no-resolution-step"),
     }
     if outcome == "served":
         record = build_replay_record(
@@ -492,6 +498,7 @@ def test_the_recorded_shell_never_carries_a_replay_reference() -> None:
         policy_bindings=(),
         assembly_mode="algorithmic",
         recorded_at=_RECORDED_AT,
+        resolution=ResolutionNotApplicable(reason="no-resolution-step"),
     )
     recorded = _recorded_shell(record)
     assert recorded.replay_reference == NO_REPLAY_REFERENCE
@@ -509,6 +516,7 @@ def test_the_recorded_shell_never_carries_a_replay_reference() -> None:
         policy_bindings=(),
         assembly_mode="algorithmic",
         recorded_at=_RECORDED_AT,
+        resolution=ResolutionNotApplicable(reason="no-resolution-step"),
     )
     assert canonical_bytes(record) == canonical_bytes(without)
 
@@ -520,6 +528,7 @@ def test_the_builder_records_exactly_one_outcome() -> None:
         "policy_bindings": (),
         "assembly_mode": "algorithmic",
         "recorded_at": _RECORDED_AT,
+        "resolution": ResolutionNotApplicable(reason="no-resolution-step"),
     }
     with pytest.raises(ValueError, match="exactly one outcome"):
         build_replay_record(execution=None, product=None, **common)
@@ -545,6 +554,115 @@ def test_the_builder_records_exactly_one_outcome() -> None:
         )
 
 
+# --- 24.7-04: the resolution state is explicit or the record is not built ---
+
+
+def _resolution_common() -> dict[str, Any]:
+    """Every builder argument EXCEPT ``resolution`` — the subject under test."""
+    return {
+        "execution": None,
+        "product": None,
+        "refusal": _a_shell(),
+        "tenant_id": "tenant-a",
+        "perspective": Perspective(principal_id="p-1", role="analyst"),
+        "policy_bindings": (),
+        "assembly_mode": "algorithmic",
+        "recorded_at": _RECORDED_AT,
+    }
+
+
+def test_the_builder_refuses_a_none_resolution_by_name() -> None:
+    """``D-IMPL-264`` D-10 and P-2: *"Missing resolution information is an
+    internal integrity failure."* ``None`` is the omission the ruling closed,
+    and the builder refuses it BY NAME rather than writing the sentinel.
+
+    The second call has neither outcome AND no resolution, and the message
+    it gets is the resolution guard's — that guard is the first in the
+    block, so an integrity failure is named before any outcome is judged.
+    """
+    with pytest.raises(ValueError, match="an explicit resolution state"):
+        build_replay_record(resolution=None, **_resolution_common())
+    neither = _resolution_common()
+    neither["refusal"] = None
+    with pytest.raises(ValueError, match="an explicit resolution state"):
+        build_replay_record(resolution=None, **neither)
+
+
+def test_the_builder_refuses_an_omitted_resolution() -> None:
+    """D-10: *"No implicit omission for new records."* The signature makes
+    omission impossible to express — there is no default to fall back to, so
+    Python itself refuses the call and names the missing keyword."""
+    with pytest.raises(TypeError, match="resolution"):
+        build_replay_record(**_resolution_common())
+    served: dict[str, Any] = {
+        "execution": _an_execution(),
+        "product": _a_product(),
+        "perspective": Perspective(principal_id="p-1", role="analyst"),
+        "policy_bindings": (),
+        "assembly_mode": "algorithmic",
+        "recorded_at": _RECORDED_AT,
+    }
+    with pytest.raises(TypeError, match="resolution"):
+        build_replay_record(**served)
+
+
+def test_the_builder_refuses_a_pre_serialized_resolution() -> None:
+    """The one-render rule (24.6-03): the marker and the resolution land as
+    bytes rendered from the VALUE, never accepted as a block a caller
+    serialized — a pre-serialized string could be a family of blocks."""
+    block = canonical_bytes(
+        ResolutionNotApplicable(reason="no-resolution-step")
+    ).decode("utf-8")
+    with pytest.raises(ValueError, match="never accepted pre-serialized"):
+        build_replay_record(resolution=block, **_resolution_common())
+    with pytest.raises(ValueError, match="never accepted pre-serialized"):
+        build_replay_record(
+            resolution=NO_REQUEST_RESOLUTION, **_resolution_common()
+        )
+
+
+@pytest.mark.parametrize(
+    "reason", ["no-resolution-step", "refused-before-resolution"]
+)
+def test_the_marker_renders_once_from_the_value(reason: str) -> None:
+    """D-09: not-applicable is a first-class fact with a reason, rendered
+    through ``canonical_bytes`` exactly as a resolution is — distinguishable
+    from the legacy sentinel by shape, and round-tripping as itself."""
+    marker = ResolutionNotApplicable(reason=reason)
+    record = build_replay_record(resolution=marker, **_resolution_common())
+    rendered = record.policy_bindings.request_resolution
+    assert rendered == canonical_bytes(marker).decode("utf-8")
+    assert rendered != NO_REQUEST_RESOLUTION
+    assert ResolutionNotApplicable.model_validate_json(rendered) == marker
+    assert ResolutionNotApplicable.model_validate_json(rendered).reason == reason
+
+
+def test_the_marker_states_its_reason_from_a_closed_vocabulary() -> None:
+    """The reason is required and closed: an author who never stated WHY
+    resolution does not apply has not stated non-applicability (P-2)."""
+    with pytest.raises(ValueError):
+        ResolutionNotApplicable()  # type: ignore[call-arg]
+    with pytest.raises(ValueError):
+        ResolutionNotApplicable(reason="because")  # type: ignore[arg-type]
+    with pytest.raises(ValueError):
+        ResolutionNotApplicable(reason=None)  # type: ignore[arg-type]
+
+
+def test_a_fixture_minted_record_states_no_resolution_step() -> None:
+    """D-09 / criterion 16 for the test-fixture class of direct minting: a
+    record minted with no resolver in the path SAYS so, with the reason, and
+    the claim is readable back off dimension 2 as the typed marker."""
+    record = build_replay_record(
+        resolution=ResolutionNotApplicable(reason="no-resolution-step"),
+        **_resolution_common(),
+    )
+    stated = ResolutionNotApplicable.model_validate_json(
+        record.policy_bindings.request_resolution
+    )
+    assert stated.reason == "no-resolution-step"
+    assert record.policy_bindings.request_resolution != NO_REQUEST_RESOLUTION
+
+
 # --- (e) the append happens first -------------------------------------------
 
 
@@ -657,6 +775,9 @@ def test_the_recorder_answers_a_caller_with_a_principal_and_no_role(
         recorded_at=determined_at,
         request=None,
         execution=None,
+        # 24.7-04 (D-IMPL-264 D-10 am.1): the seam requires the state too;
+        # this fixture ran no resolution step and says so.
+        resolution=ResolutionNotApplicable(reason="no-resolution-step"),
     )
 
     assert returned.replay_reference != NO_REPLAY_REFERENCE
@@ -708,6 +829,7 @@ def test_a_recorder_with_no_bundle_pin_records_exactly_the_callers_bindings(
         perspective=Perspective(principal_id="p-1", role=NO_ROLE_RESOLVED),
         recorded_at=ASKED_AT,
         policy_bindings=passed,
+        resolution=ResolutionNotApplicable(reason="no-resolution-step"),
     )
     record = _record_at(booted, returned.replay_reference)
     assert record.policy_bindings.bindings == passed
@@ -729,6 +851,7 @@ def test_a_recorder_holding_a_bundle_pin_prepends_it(booted: _Booted) -> None:
         perspective=Perspective(principal_id="p-1", role=NO_ROLE_RESOLVED),
         recorded_at=ASKED_AT,
         policy_bindings=passed,
+        resolution=ResolutionNotApplicable(reason="no-resolution-step"),
     )
     record = _record_at(booted, returned.replay_reference)
     assert record.policy_bindings.bindings == (pin, *passed)
@@ -812,6 +935,7 @@ def test_a_recorded_refusal_round_trips_through_the_builders_own_guard() -> None
         "policy_bindings": (),
         "assembly_mode": "algorithmic",
         "recorded_at": _RECORDED_AT,
+        "resolution": ResolutionNotApplicable(reason="no-resolution-step"),
     }
     record = build_replay_record(refusal=_a_shell(), **common)
     assert _recorded_shell(record).kind == "product-request-violation"
@@ -833,6 +957,7 @@ def test_a_recorded_refusal_round_trips_through_the_builders_own_guard() -> None
             policy_bindings=(),
             assembly_mode="algorithmic",
             recorded_at=_RECORDED_AT,
+            resolution=ResolutionNotApplicable(reason="no-resolution-step"),
             assembly_refusal='{"looks":"like a refusal"}',
         )
```

## tests/replay/test_trace_correlation.py — diff 6a019322..HEAD (M)

```diff
diff --git a/tests/replay/test_trace_correlation.py b/tests/replay/test_trace_correlation.py
index 710b54c7..b1cf2ebb 100644
--- a/tests/replay/test_trace_correlation.py
+++ b/tests/replay/test_trace_correlation.py
@@ -34,6 +34,7 @@ from ccf.replay.record import (
     HarnessTrace,
     ModelVersionRecord,
     PolicyBinding,
+    ResolutionNotApplicable,
     build_replay_record,
 )
 
@@ -95,6 +96,7 @@ def _build(**overrides: Any) -> DecisionReplayRecord:
         policy_bindings=(PolicyBinding(key="policy.bundle", version="v1"),),
         assembly_mode="algorithmic",
         recorded_at=NOW,
+        resolution=ResolutionNotApplicable(reason="no-resolution-step"),
         **overrides,
     )
```

## tests/test_surface_shape_capture.py — diff 6a019322..HEAD (M)

```diff
diff --git a/tests/test_surface_shape_capture.py b/tests/test_surface_shape_capture.py
index e4912edf..db80c01d 100644
--- a/tests/test_surface_shape_capture.py
+++ b/tests/test_surface_shape_capture.py
@@ -473,14 +473,22 @@ _SHAPE_MOVED_BY_FRAGMENT = {
     "ccf.agents.DeterministicAssembler": (
         "24.1.1-03-a-refusal-returns-as-data.md"
     ),
-    # D-IMPL-214 Reading B — `assembly_refusal: str | None = None`, threaded
-    # with the `if X is not None else SENTINEL` expression the three
-    # `hitl_actions`-family precedents use, so a refusal gains an identity on
-    # dimension 5 and no existing call site moves. `ContentGenerationPath`'s
-    # own move is invisible here: it is a `contract`-kind export and the loop
-    # below skips every kind that is not `class` or `function`.
+    # 24.7-04 (`D-IMPL-264` D-10, P-2) — `resolution` is a REQUIRED keyword:
+    # `"EffectiveRequest | ResolutionNotApplicable"`, no default, beside the
+    # other required inputs. The 24.1.1-04 entry this supersedes claimed an
+    # additive widening (`assembly_refusal: str | None = None`, sentinel-
+    # threaded, no call site moved); this move is the opposite kind — every
+    # caller must now state the resolution that ran or a typed marker saying
+    # why none applies, and omission is a `TypeError`. One name maps to one
+    # fragment, and the citation is the NEWEST reshaping (the 24.5-13/15
+    # precedent's reasoning, inverted: there the later change was the
+    # additive one; here it is the breaking one). The 24.1.1-04 fragment
+    # stays on disk untouched and still documents its own widening. The 41
+    # SDK test sites are re-derived in plans 24.7-04 and 24.7-06; the seven
+    # frozen example sites are quarantined evidence under `D-IMPL-263`/
+    # `D-IMPL-261`, never migrated.
     "ccf.replay.record.build_replay_record": (
-        "24.1.1-04-a-refusal-has-an-identity-in-the-record.md"
+        "24.7-04-the-replay-builder-requires-an-explicit-resolution-state.md"
     ),
     "ccf_runtime.http_api.dependencies.ApiDependencies": (
         "16-22-consumption-papercuts.md"
@@ -589,6 +597,25 @@ _SHAPE_MOVED_BY_FRAGMENT = {
     "ccf.projection.engine.ExecutionResult": (
         "24.5-15-the-empty-operator-gate-s-two-halves-by-name.md"
     ),
+    # Phase 24.7 plan 02 (`D-IMPL-264` D-08; criterion 12). The seam's return
+    # went from the four-way union `EffectiveRequest | ConstraintRefusal |
+    # PolicyResolutionConflict | ProductRequestViolation` to the one
+    # `ResolutionOutcome` pair, so a caller reads the refusal off `.refusal`
+    # and the evidence off `.evidence` — and a refusal reached halfway through
+    # now carries what resolution established before it. Not an additive
+    # widening: the return type changed and every call site that branched on
+    # the union had to move — the SDK's one, in `GovernedResolver.resolve`,
+    # did; cp-04's frozen `assembler.py` `isinstance` over the retired union
+    # is accepted evidence under `D-IMPL-264` am.1 (Dave: *"Do not distort
+    # the new SDK return type to preserve an old example `isinstance`
+    # check"*), never a reason to keep the union. The entry does not pretend
+    # otherwise: the fragment claims the name as `reshaped`. The two `resolve`
+    # methods moved with it and are invisible here — `PolicyConstraintResolver`
+    # is a Protocol and the loop skips it, and `ReferencePolicyConstraintResolver`'s
+    # captured shape is its dataclass `__init__`, which did not change.
+    "ccf.products.constraints.resolve_effective_request": (
+        "24.7-02-resolution-returns-a-paired-outcome.md"
+    ),
 }
```

## tests/workflow/test_engine.py — diff 6a019322..HEAD (M)

```diff
diff --git a/tests/workflow/test_engine.py b/tests/workflow/test_engine.py
index aa8d75f6..68cdc3fa 100644
--- a/tests/workflow/test_engine.py
+++ b/tests/workflow/test_engine.py
@@ -66,6 +66,7 @@ from ccf.replay.record import (
     DecisionReplayRecord,
     PerspectiveConditioning,
     PolicyBinding,
+    ResolutionNotApplicable,
     build_replay_record,
 )
 from ccf.workflow.definitions import (
@@ -241,6 +242,7 @@ def _replay_record(
         policy_bindings=(PolicyBinding(key="policy.bundle", version="v1"),),
         assembly_mode="algorithmic",
         recorded_at=datetime(2026, 3, 1, tzinfo=UTC),
+        resolution=ResolutionNotApplicable(reason="no-resolution-step"),
         agent_conditioning=PerspectiveConditioning(
             principal_id="principal-1",
             role="analyst",
```

## tests/workflow/test_slice.py — diff 6a019322..HEAD (M)

```diff
diff --git a/tests/workflow/test_slice.py b/tests/workflow/test_slice.py
index c741c81b..4a47751e 100644
--- a/tests/workflow/test_slice.py
+++ b/tests/workflow/test_slice.py
@@ -62,6 +62,7 @@ from ccf.replay.record import (
     DecisionReplayRecord,
     PerspectiveConditioning,
     PolicyBinding,
+    ResolutionNotApplicable,
     build_replay_record,
 )
 from ccf.workflow.definitions import WORKFLOW_DEFINITION, WorkflowDefinition
@@ -264,6 +265,7 @@ def _replay_record(
         policy_bindings=(PolicyBinding(key="policy.bundle", version="v1"),),
         assembly_mode="algorithmic",
         recorded_at=datetime(2026, 3, 1, tzinfo=UTC),
+        resolution=ResolutionNotApplicable(reason="no-resolution-step"),
         agent_conditioning=PerspectiveConditioning(
             principal_id="principal-1",
             role="analyst",
```

## tools/lints/tests/test_hash_transparent_key.py — diff 6a019322..HEAD (M)

```diff
diff --git a/tools/lints/tests/test_hash_transparent_key.py b/tools/lints/tests/test_hash_transparent_key.py
index d0289ba0..95ce926c 100644
--- a/tools/lints/tests/test_hash_transparent_key.py
+++ b/tools/lints/tests/test_hash_transparent_key.py
@@ -361,6 +361,10 @@ NAMED_SINCE_THE_SWEEP: tuple[str, ...] = (
     "ccf.products.request.ProductRequestContract.argument_domains",
     "ccf.products.request.ArgumentDomain.minimum",
     "ccf.products.request.ArgumentDomain.maximum",
+    # 24.7-01, the enumerated shape (`D-IMPL-264` D-03/D-06): the closed
+    # member set beside the two numeric ends. Silent at `None`, so no
+    # committed request contract's address moves.
+    "ccf.products.request.ArgumentDomain.members",
 )
```


---
End of bundle-tests-part-2.md. Read-proof, again:
```
READ-PROOF bundle-tests-part-2.md: 0e1693dab969a353
```
