"""Shared fixtures for the ``tests/deployment`` package.

An on-disk artifacts directory, minimal valid artifact documents, a complete
manifest-plus-artifacts deployment, and one helper that serializes a mapping to
YAML. Nothing is added ahead of a test that uses it.

Every document here is a *fixture*, not a default — the values exist only so
that a test has something valid to parse. No SDK code may read a value from one.

**The fixture manifest is also the reference authoring pattern.** It marks the
signal batch ``role: load`` and everything else ``role: register``, per
D-IMPL-80, and it states ``registration`` on **every** entry, per D-IMPL-85 —
both fields are required with no default, and the fixture shows them as
explicitly as an example manifest does. A fixture that got either wrong would
teach the wrong thing twice.
"""

from __future__ import annotations

import dataclasses
import pathlib
from collections.abc import Mapping
from typing import Any

import pytest
import yaml

#: Fixture vocabulary. Test-side names, never SDK values (CINV-01).
TENANT = "tenant-fixture"
RESOLUTION_SPEC_KEY = "tenant-fixture/resolution-spec"
POLICY_BUNDLE_KEY = "tenant-fixture/policy-bundle"
HALF_LIFE_KEY = "tenant-fixture/half-life-table"
TRAVERSAL_KEY = "tenant-fixture/operator-parameters/traversal"
TEMPORAL_KEY = "tenant-fixture/operator-parameters/temporal"
POLICY_PARAMS_KEY = "tenant-fixture/operator-parameters/policy"
SIMILARITY_KEY = "tenant-fixture/operator-parameters/similarity"
PERSPECTIVE_KEY = "tenant-fixture/perspective"
PRODUCT_CLASS_KEY = "tenant-fixture/product-class"
SIGNAL_BATCH_KEY = "tenant-fixture/signal-batch"

#: ``key -> (filename, class_id, role, registration, document)`` for the complete
#: artifact set. Declaration order is manifest order, and the tests depend on it:
#: the parse-then-register test needs to know which entry is the fourth.
ARTIFACT_SET: tuple[tuple[str, str, str, str, str, dict[str, Any]], ...] = (
    (
        RESOLUTION_SPEC_KEY,
        "resolution-spec.yaml",
        "ccf.resolution-spec",
        "register",
        "typed",
        {
            "semver": "1.0.0",
            "entity_rules": [
                {
                    "match_key": "account_ref",
                    "entity_class": "account",
                    "identity_keys": ["account_ref"],
                    "attribute_keys": ["classification", "label"],
                }
            ],
        },
    ),
    (
        POLICY_BUNDLE_KEY,
        "policy-bundle.yaml",
        "fixture.policy-bundle",
        "register",
        "typed",
        {
            "semver": "1.0.0",
            "class_id": "fixture.policy-bundle",
            "declaration": {"permitted_classifications": ["fixture-open"]},
        },
    ),
    (
        HALF_LIFE_KEY,
        "half-life.yaml",
        "ccf.half-life-table",
        "register",
        "typed",
        {
            "semver": "1.0.0",
            "entries": {
                "fixture-observation": {
                    "half_life_seconds": 3600,
                    "decay_driver": "fixture",
                    "supersession_event": "fixture-superseded",
                }
            },
        },
    ),
    (
        TRAVERSAL_KEY,
        "operator-traversal.yaml",
        "ccf.operator-parameters.traversal",
        "register",
        "typed",
        {
            "semver": "1.0.0",
            "seed_entity_classes": ["account"],
            "relationship_types": ["fixture-relates-to"],
            "depth_limit": 2,
        },
    ),
    (
        TEMPORAL_KEY,
        "operator-temporal.yaml",
        "ccf.operator-parameters.temporal",
        "register",
        "typed",
        {"semver": "1.0.0", "require_valid_at_boundary": True},
    ),
    (
        POLICY_PARAMS_KEY,
        "operator-policy.yaml",
        "ccf.operator-parameters.policy",
        "register",
        "typed",
        {
            "semver": "1.0.0",
            "classification_attribute_by_class": {"account": "classification"},
            "permitted_classifications": ["fixture-open"],
        },
    ),
    (
        SIMILARITY_KEY,
        "operator-similarity.yaml",
        "ccf.operator-parameters.similarity",
        "register",
        "typed",
        {
            "semver": "1.0.0",
            "query": "fixture query",
            "minimum_score_percent": 10,
            "ranked_entity_classes": ["account"],
            "similarity_corpus_attribute_by_class": {"account": "label"},
            # The corpus's version identity, declared where `24.11-02b` /
            # `D-IMPL-292` made it canonical: on the artifact, never as a
            # builder argument. A fixture value like every other here.
            "index_version": "fixture-corpus-1",
        },
    ),
    (
        PERSPECTIVE_KEY,
        "perspective.yaml",
        "ccf.perspective",
        "register",
        "typed",
        {
            "semver": "1.0.0",
            "principal_id": "principal-fixture",
            "role": "role-fixture",
        },
    ),
    (
        PRODUCT_CLASS_KEY,
        "product-class.yaml",
        "ccf.product-class",
        "register",
        "typed",
        {
            "semver": "1.0.0",
            "schema_name": "fixture.manifest-product",
            "schema_version": "1.0.0",
            "ttl_anchor": "from_decision",
            "assembly_mode": "algorithmic",
            "max_ttl_key": "tenant-fixture/max-ttl",
            "required_operator_keys": ["traversal.typed-neighborhood"],
        },
    ),
    (
        SIGNAL_BATCH_KEY,
        "events.yaml",
        "ccf.signal-batch",
        # D-IMPL-80: parsed and returned, never registered and never pinned.
        "load",
        # D-IMPL-85 gives `registration` no default either, so a `load` entry
        # states the path it would have travelled even though it never travels
        # one. The field is required of every entry, not of registered ones.
        "typed",
        {
            "semver": "1.0.0",
            "tenant_id": TENANT,
            "envelopes": [
                {
                    "tenant_id": TENANT,
                    "envelope_id": "envelope-fixture-1",
                    "source": {"system_id": "fixture-system"},
                    "ingestion_timestamp": "2026-03-02T11:00:00Z",
                    "raw_payload": {
                        "account_ref": "acct-1",
                        "classification": "fixture-open",
                        "label": "fixture account",
                    },
                }
            ],
        },
    ),
)


@dataclasses.dataclass(frozen=True)
class Deployment:
    """A complete on-disk deployment: a manifest and every artifact it names.

    Attributes:
        root: The directory holding the manifest and the artifact documents.
        manifest_path: The manifest itself.
        manifest_document: The manifest as a mapping, so a test can vary one
            field and rewrite it with :meth:`rewrite_manifest`.
    """

    root: pathlib.Path
    manifest_path: pathlib.Path
    manifest_document: dict[str, Any]

    def rewrite_manifest(self, document: Mapping[str, Any]) -> pathlib.Path:
        """Overwrite the manifest with ``document`` and return its path."""
        return write_artifact(self.root, self.manifest_path.name, document)

    def variant_manifest(
        self, name: str, document: Mapping[str, Any]
    ) -> pathlib.Path:
        """Write a second manifest beside the first, under ``name``."""
        return write_artifact(self.root, name, document)


@pytest.fixture()
def artifacts_dir(tmp_path: pathlib.Path) -> pathlib.Path:
    """A per-test directory standing in for a deployment's artifacts tree."""
    directory = tmp_path / "artifacts"
    directory.mkdir()
    return directory


@pytest.fixture()
def half_life_document() -> dict[str, Any]:
    """A minimal document that satisfies the λ_c table contract.

    One entry, because ``HalfLifeTable.entries`` has ``min_length=1`` — a table
    with no rows is refused at validation, so the smallest *valid* document is
    the smallest useful fixture.
    """
    return {
        "semver": "1.0.0",
        "entries": {
            "fixture-observation": {
                "half_life_seconds": 3600,
                "decay_driver": "fixture",
                "supersession_event": "fixture-superseded",
            }
        },
    }


def write_artifact(
    directory: pathlib.Path, name: str, document: Mapping[str, Any]
) -> pathlib.Path:
    """Serialize ``document`` to ``directory/name`` as YAML and return the path.

    ``default_flow_style=False`` and ``sort_keys=True`` so the written file is
    diffable, and the mapping is copied into a plain ``dict`` first so a
    ``Mapping`` that is not a ``dict`` does not serialize as a Python object tag.
    """
    path = directory / name
    path.write_text(
        yaml.safe_dump(dict(document), default_flow_style=False, sort_keys=True),
        encoding="utf-8",
    )
    return path


def manifest_document(**overrides: Any) -> dict[str, Any]:
    """The fixture manifest, with ``overrides`` applied at the top level.

    Built fresh each call so a test that mutates the returned mapping cannot
    leak the mutation into the next test.
    """
    document: dict[str, Any] = {
        "semver": "1.0.0",
        "backend": "sqlite",
        "tenant_id": TENANT,
        "resolution_spec_key": RESOLUTION_SPEC_KEY,
        "policy_bundle_key": POLICY_BUNDLE_KEY,
        "artifacts": [
            {
                "path": filename,
                "key": key,
                "class_id": class_id,
                "role": role,
                "registration": registration,
            }
            for key, filename, class_id, role, registration, _ in ARTIFACT_SET
        ],
    }
    document.update(overrides)
    return document


@pytest.fixture()
def deployment(tmp_path: pathlib.Path) -> Deployment:
    """A complete manifest-plus-artifacts deployment under ``tmp_path``.

    Everything ``tests/deployment`` needs to boot a real fabric, written to
    disk here rather than reached for in ``examples/`` — a test that read an
    example's artifacts would fail whenever that example was rewritten, for
    reasons having nothing to do with the manifest.
    """
    root = tmp_path / "deployment"
    root.mkdir()
    for _key, filename, _class_id, _role, _registration, document in ARTIFACT_SET:
        write_artifact(root, filename, document)
    body = manifest_document()
    return Deployment(
        root=root,
        manifest_path=write_artifact(root, "manifest.yaml", body),
        manifest_document=body,
    )
