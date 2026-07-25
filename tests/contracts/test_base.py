"""Contract-base invariant tests (D-15: contracts are built test-first).

Covers `ccf.contracts.base.CCFContract` — the `extra=forbid` + frozen base
every CCF boundary type derives from (DESIGN.md §2A.2.1, whitepaper §6.3).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ccf.contracts.base import CCFContract


class _Sample(CCFContract):
    name: str


def test_unknown_field_is_rejected() -> None:
    with pytest.raises(ValidationError):
        _Sample(name="a", unexpected="b")  # type: ignore[call-arg]


def test_instances_are_frozen() -> None:
    sample = _Sample(name="a")
    with pytest.raises(ValidationError):
        sample.name = "b"


def test_config_declares_forbid_and_frozen() -> None:
    assert CCFContract.model_config["extra"] == "forbid"
    assert CCFContract.model_config["frozen"] is True


def test_missing_required_field_is_rejected() -> None:
    with pytest.raises(ValidationError):
        _Sample()  # type: ignore[call-arg]
