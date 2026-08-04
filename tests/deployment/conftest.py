"""Shared fixtures for the ``tests/deployment`` package.

Kept deliberately small: an on-disk artifacts directory, one minimal valid
artifact document, and one helper that serializes a mapping to YAML. Later plans
in this phase add manifest fixtures here; nothing is added ahead of a test that
uses it.

The artifact document is a *fixture*, not a default — it carries numbers only so
that a test has something valid to parse. No SDK code may read a value from it.
"""

from __future__ import annotations

import pathlib
from collections.abc import Mapping
from typing import Any

import pytest
import yaml


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
