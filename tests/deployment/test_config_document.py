"""`DeploymentConfig` — the parse layer of `D-IMPL-136`'s single-file form.

Whitepaper §7.8 (the Control Plane declares what the fabric may do); CLAUDE.md
§6.4 and §10 for the SDK-defined authoring document these tests cover.

**What these tests enforce, exactly.**

1. A minimal document (`semver`, `tenant_id`, `backend`, `product_class`)
   parses; a document with no `semver` is refused — `VersionedArtifact`'s
   inherited rule, not restated here.
2. An unreserved top-level key is refused by a message naming the offender,
   saying the SDK does not recognise it as a section, and listing the
   reserved names — the `resolutoin` worked case from design spec §4.1.
   **Two** unreserved keys are named together in one refusal.
3. `tenant_id`, `backend_secrets`, `survivor_cap`, `resolution_spec_key` and
   `policy_bundle_key` each carry the type and default design spec §6.3 and
   `D-IMPL-138`(b) rule; `backend` is required and shape-checked.
4. `product_class` is required; every other section is optional and absent
   (`None`) by default, distinguishably from an authored-empty section
   (`{}`).
5. `operators` accepts a mapping keyed by operator id whose values are open
   mappings.
6. `policy` and `request_contract` round-trip **uninterpreted** — arbitrary
   adopter keys, including a key literally named `role` (design spec §6.2's
   override collision), parse unchanged.
7. A float or a zone-less timestamp anywhere in the document is refused by
   `load_artifact`'s existing `_reject_floats` / `_reject_naive_timestamps`
   — inherited, and asserted so the inheritance is not assumed.
8. The full HW-1 deployment (`examples/s1-00-companies-over-revenue`),
   transcribed by hand into one document, parses. The transcription is a
   module-level fixture, :data:`HW1_SINGLE_FILE_DOCUMENT`, exported so
   `16-29` and `16-30` reuse it rather than retyping it.
9. No field of `DeploymentConfig` names a connection value — the negative
   control the threat register commits to at T-16-28-02.

**What these tests do not enforce.** Nothing here derives a section into the
SDK artifact it names, registers anything, or boots a fabric — that is
`16-29`'s loader. Nothing here asserts a `ccf.deployment-manifest` document
built from this one matches the multi-file manifest byte-for-byte — that is
`16-30`'s equivalence proof.
"""

from __future__ import annotations

from typing import Any

import pytest

from ccf.controlplane.artifacts import (
    DEPLOYMENT_CONFIG,
    ArtifactLoadError,
    DeploymentConfig,
    SecretReference,
    load_artifact,
    parse_artifact,
)

#: The full HW-1 deployment (`examples/s1-00-companies-over-revenue/artifacts
#: /config/*.yaml`, ten files), transcribed by hand into the single-file form.
#: `examples/` itself is read-only reference material and is never edited by
#: this plan set (Dave's dual-model ruling, 2026-08-14) — this is a literal
#: fixture, not a loader over the example directory, so it cannot drift the
#: way an example can. `16-29` and `16-30` import this constant rather than
#: retyping the corpus.
HW1_SINGLE_FILE_DOCUMENT: dict[str, Any] = {
    "semver": "1.0.0",
    "tenant_id": "hw1-demo",
    "backend": "postgres",
    "product_class": {
        "schema_name": "hw1.companies-over-revenue",
        "schema_version": "1.0.0",
        "ttl_anchor": "from_decision",
        "assembly_mode": "algorithmic",
        "max_ttl_key": "hw1/product/companies-over-revenue/max-ttl",
        "required_operator_keys": ["temporal.as-of-boundary"],
    },
    "operators": {
        "temporal.as-of-boundary": {"require_valid_at_boundary": True},
    },
    "request_contract": {
        # D-IMPL-138(a): three bookkeeping lines on an adopter-owned section.
        "class_id": "hw1.request-contract",
        "role": "load",
        "registration": "typed",
        "schema_name": "hw1.companies-over-revenue",
        "schema_version": "1.0.0",
        "arguments": {
            "properties": {
                "revenue_threshold": {
                    "type": "number",
                    "description": (
                        "Return companies whose revenue exceeds this amount."
                    ),
                },
            },
            "required": ["revenue_threshold"],
        },
    },
    "resolution": {
        "entity_rules": [
            {
                "match_key": "company_ref",
                "entity_class": "company",
                "identity_keys": ["company_ref"],
                "attribute_keys": ["company_name", "company_revenue"],
            }
        ],
    },
    "half_life": {
        "company": {
            "half_life_seconds": 31536000,
            "decay_driver": "the annual revenue reporting cycle",
            "supersession_event": (
                "a newer filing restating the same company's revenue"
            ),
        },
    },
    "debt_profile": {
        "risk_sensitivity": "1.0",
        "forced_llm_threshold": "0.20",
        "fail_closed_threshold": "0.60",
    },
    "policy": {
        # D-IMPL-138(a): three bookkeeping lines on an adopter-owned section.
        "class_id": "hw1.policy-bundle",
        "role": "register",
        "registration": "typed",
        "regime": "published-annual-revenue-disclosure",
    },
    "default_perspective": {
        "principal_id": "revenue-screening-desk-1",
        "role": "analyst",
    },
}


def _minimal(**overrides: Any) -> dict[str, Any]:
    """The smallest document that satisfies `DeploymentConfig`, ``overrides``
    applied at the top level. Built fresh each call so a test that mutates the
    returned mapping cannot leak the mutation into the next test."""
    document: dict[str, Any] = {
        "semver": "1.0.0",
        "backend": "sqlite",
        "product_class": {"schema_name": "fixture.product"},
    }
    document.update(overrides)
    return document


# --- 1. the minimal document, and the inherited no-default semver rule --------


def test_a_minimal_document_parses() -> None:
    parsed = parse_artifact(
        _minimal(tenant_id="hw1-demo"),
        DEPLOYMENT_CONFIG,
    )
    assert isinstance(parsed, DeploymentConfig)
    assert parsed.tenant_id == "hw1-demo"
    assert parsed.backend == "sqlite"
    assert parsed.product_class == {"schema_name": "fixture.product"}


def test_a_document_with_no_semver_is_refused() -> None:
    document = _minimal()
    del document["semver"]
    with pytest.raises(ArtifactLoadError, match="ccf.deployment-config"):
        parse_artifact(document, DEPLOYMENT_CONFIG)


# --- T-16-28-02: no connection value can enter this document at all -----------


def test_no_field_name_names_a_connection_value() -> None:
    """The negative control the threat register commits to (T-16-28-02).

    `DeploymentConfig` carries `backend_secrets` — credential *references*,
    never values (`SecretReference`) — and no field of any kind that could
    hold a DSN, a URL, a password, or a live connection. D-08's rule is
    that a connection string is deployment environment, never Control Plane
    state; this is that rule asserted against the field list itself rather
    than against one example document.
    """
    field_names = set(DeploymentConfig.model_fields)
    for forbidden in ("dsn", "url", "password", "connection"):
        offending = {name for name in field_names if forbidden in name.lower()}
        assert not offending, (
            f"a field name contains {forbidden!r}: {offending} — no field of"
            " DeploymentConfig may name a connection value (D-08)"
        )


# --- 2. the named unknown-section refusal --------------------------------------


def test_one_unrecognised_top_level_key_is_named_and_the_reserved_names_listed() -> (
    None
):
    document = _minimal()
    document["resolutoin"] = {"entity_rules": []}
    with pytest.raises(ArtifactLoadError) as raised:
        parse_artifact(document, DEPLOYMENT_CONFIG)
    message = str(raised.value)
    assert "'resolutoin'" in message
    assert "does not recognise" in message
    # At least three reserved names actually appear, not merely "some list".
    for name in ("product_class", "policy", "resolution"):
        assert name in message


def test_two_unrecognised_top_level_keys_are_named_together_in_one_refusal() -> None:
    document = _minimal()
    document["resolutoin"] = {}
    document["poilcy"] = {}
    with pytest.raises(ArtifactLoadError) as raised:
        parse_artifact(document, DEPLOYMENT_CONFIG)
    message = str(raised.value)
    assert "'resolutoin'" in message
    assert "'poilcy'" in message


# --- 3. deployment-level fields: types, defaults, the backend shape rule ------


def test_tenant_id_is_optional() -> None:
    parsed = parse_artifact(_minimal(), DEPLOYMENT_CONFIG)
    assert isinstance(parsed, DeploymentConfig)
    assert parsed.tenant_id is None


def test_backend_is_required() -> None:
    document = _minimal()
    del document["backend"]
    with pytest.raises(ArtifactLoadError, match="ccf.deployment-config"):
        parse_artifact(document, DEPLOYMENT_CONFIG)


@pytest.mark.parametrize("backend", ["postgres", "sqlite", "graph_db_9"])
def test_a_well_shaped_backend_name_parses(backend: str) -> None:
    parsed = parse_artifact(_minimal(backend=backend), DEPLOYMENT_CONFIG)
    assert isinstance(parsed, DeploymentConfig)
    assert parsed.backend == backend


@pytest.mark.parametrize("backend", ["Postgres", "9postgres", "postgres!", ""])
def test_a_malformed_backend_name_is_refused(backend: str) -> None:
    with pytest.raises(ArtifactLoadError, match="ccf.deployment-config"):
        parse_artifact(_minimal(backend=backend), DEPLOYMENT_CONFIG)


def test_backend_secrets_defaults_empty_and_accepts_secret_references() -> None:
    default = parse_artifact(_minimal(), DEPLOYMENT_CONFIG)
    assert isinstance(default, DeploymentConfig)
    assert default.backend_secrets == ()

    with_one = parse_artifact(
        _minimal(
            backend_secrets=[{"field": "dsn", "env_var": "CCF_S1_00_POSTGRES_DSN"}]
        ),
        DEPLOYMENT_CONFIG,
    )
    assert isinstance(with_one, DeploymentConfig)
    assert with_one.backend_secrets == (
        SecretReference(field="dsn", env_var="CCF_S1_00_POSTGRES_DSN"),
    )


def test_survivor_cap_accepts_int_or_none_and_defaults_to_none() -> None:
    default = parse_artifact(_minimal(), DEPLOYMENT_CONFIG)
    assert isinstance(default, DeploymentConfig)
    assert default.survivor_cap is None

    capped = parse_artifact(_minimal(survivor_cap=500), DEPLOYMENT_CONFIG)
    assert isinstance(capped, DeploymentConfig)
    assert capped.survivor_cap == 500


@pytest.mark.parametrize("field", ["resolution_spec_key", "policy_bundle_key"])
def test_the_two_pointer_fields_accept_a_string_or_none_and_default_to_none(
    field: str,
) -> None:
    default = parse_artifact(_minimal(), DEPLOYMENT_CONFIG)
    assert isinstance(default, DeploymentConfig)
    assert getattr(default, field) is None

    overridden = parse_artifact(_minimal(**{field: "explicit-key"}), DEPLOYMENT_CONFIG)
    assert isinstance(overridden, DeploymentConfig)
    assert getattr(overridden, field) == "explicit-key"


# --- 4. product_class required; every other section absent-by-default --------


def test_product_class_is_required() -> None:
    document = _minimal()
    del document["product_class"]
    with pytest.raises(ArtifactLoadError, match="ccf.deployment-config"):
        parse_artifact(document, DEPLOYMENT_CONFIG)


@pytest.mark.parametrize(
    "section",
    [
        "operators",
        "request_contract",
        "resolution",
        "half_life",
        "debt_profile",
        "policy",
        "default_perspective",
    ],
)
def test_every_other_section_defaults_to_absent_not_empty(section: str) -> None:
    """`None` — an unauthored section — is distinguishable from `{}` — a
    section heading the adopter wrote with nothing under it."""
    absent = parse_artifact(_minimal(), DEPLOYMENT_CONFIG)
    assert isinstance(absent, DeploymentConfig)
    assert getattr(absent, section) is None

    empty = parse_artifact(_minimal(**{section: {}}), DEPLOYMENT_CONFIG)
    assert isinstance(empty, DeploymentConfig)
    assert getattr(empty, section) == {}
    assert getattr(empty, section) is not None


# --- 5. operators: keyed by operator id, values are open mappings ------------


def test_operators_is_a_mapping_keyed_by_operator_id_of_open_mappings() -> None:
    document = _minimal(
        operators={
            "temporal.as-of-boundary": {"require_valid_at_boundary": True},
            "traversal.typed-neighborhood": {"depth_limit": 2, "anything": "goes"},
        }
    )
    parsed = parse_artifact(document, DEPLOYMENT_CONFIG)
    assert isinstance(parsed, DeploymentConfig)
    assert parsed.operators == document["operators"]


# --- 6. policy / request_contract round-trip uninterpreted --------------------


@pytest.mark.parametrize("section", ["policy", "request_contract"])
def test_adopter_owned_section_round_trips_arbitrary_content_unread(
    section: str,
) -> None:
    body = {
        "class_id": "acme.whatever-this-is",
        "role": "register",
        "registration": "typed",
        "a_field_the_sdk_has_never_heard_of": {"nested": ["anything", 1, "goes"]},
    }
    parsed = parse_artifact(_minimal(**{section: body}), DEPLOYMENT_CONFIG)
    assert isinstance(parsed, DeploymentConfig)
    assert getattr(parsed, section) == body


def test_a_policy_body_with_a_key_literally_named_role_parses() -> None:
    """Design spec §6.2's override collision — a *derivation*-time question
    for `16-29`, not a parse-time refusal."""
    body = {"regime": "published-annual-revenue-disclosure", "role": "analyst"}
    parsed = parse_artifact(_minimal(policy=body), DEPLOYMENT_CONFIG)
    assert isinstance(parsed, DeploymentConfig)
    assert parsed.policy == body
    assert parsed.policy is not None
    assert parsed.policy["role"] == "analyst"


# --- 7. inherited refusals: floats and zone-less timestamps -------------------


def test_a_float_anywhere_in_the_document_is_refused() -> None:
    text = (
        'semver: "1.0.0"\n'
        "backend: sqlite\n"
        "product_class:\n"
        "  schema_name: fixture.product\n"
        "debt_profile:\n"
        "  risk_sensitivity: 1.0\n"  # unquoted -> YAML float
    )
    with pytest.raises(ArtifactLoadError, match="float"):
        load_artifact(text, DEPLOYMENT_CONFIG)


def test_a_zone_less_timestamp_anywhere_in_the_document_is_refused() -> None:
    text = (
        'semver: "1.0.0"\n'
        "backend: sqlite\n"
        "product_class:\n"
        "  schema_name: fixture.product\n"
        "policy:\n"
        "  effective: 2026-01-01T00:00:00\n"  # no zone designator
    )
    with pytest.raises(ArtifactLoadError, match="naive timestamp|no zone"):
        load_artifact(text, DEPLOYMENT_CONFIG)


# --- 8. the full HW-1 deployment, transcribed --------------------------------


def test_the_full_hw1_deployment_transcribed_into_one_document_parses() -> None:
    parsed = parse_artifact(HW1_SINGLE_FILE_DOCUMENT, DEPLOYMENT_CONFIG)
    assert isinstance(parsed, DeploymentConfig)
    assert parsed.tenant_id == "hw1-demo"
    assert parsed.backend == "postgres"
    assert parsed.resolution_spec_key is None
    assert parsed.policy_bundle_key is None
    assert parsed.product_class == HW1_SINGLE_FILE_DOCUMENT["product_class"]
    assert parsed.policy == HW1_SINGLE_FILE_DOCUMENT["policy"]
    assert parsed.request_contract == HW1_SINGLE_FILE_DOCUMENT["request_contract"]
    assert parsed.resolution == HW1_SINGLE_FILE_DOCUMENT["resolution"]
    assert parsed.half_life == HW1_SINGLE_FILE_DOCUMENT["half_life"]
    assert parsed.debt_profile == HW1_SINGLE_FILE_DOCUMENT["debt_profile"]
    assert parsed.default_perspective == HW1_SINGLE_FILE_DOCUMENT["default_perspective"]
    assert parsed.operators == HW1_SINGLE_FILE_DOCUMENT["operators"]
