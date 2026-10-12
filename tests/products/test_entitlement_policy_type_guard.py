# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""The two ``ProductEntitlementPolicy`` narrowing guards are real refusals.

Dave, 2026-10-12 07:04 MST (option (a)): the nine ``mypy --strict`` errors are
fixed with accurate types and narrowing, and any runtime path the correction
adds is identified and tested. Two paths were added:
``deployment/config.py`` (deriving the ``product_entitlement:`` section) and
``products/product.py::_register_declared_entitlement`` each now refuse with
``TypeError`` when ``parse_artifact`` returns anything other than the
``ProductEntitlementPolicy`` that ``PRODUCT_ENTITLEMENT_POLICY`` declares,
rather than reading ``tenant_id`` / ``principals`` off an unknown contract.
``ArtifactClass.validate`` already guarantees the type, so neither guard fires
on a reachable path. These tests force each guard and keep a positive control,
so that neither the test nor the guard can be vacuous.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import ccf.deployment.config as config_module
import ccf.products.product as product_module
from ccf.contracts.base import CCFContract
from ccf.products.entitlement import PRODUCT_ENTITLEMENT_POLICY

from tests.mcp.test_door_declared_principals import _open, _policy


class _NotAPolicy(CCFContract):
    """A contract that is not a ``ProductEntitlementPolicy``."""


def _substituting(original: Any) -> Any:
    def parse(document: object, artifact_class: Any) -> CCFContract:
        if artifact_class is PRODUCT_ENTITLEMENT_POLICY:
            return _NotAPolicy()
        return original(document, artifact_class)

    return parse


def test_positive_control_a_declared_policy_opens(tmp_path: Path) -> None:
    opened = _open(tmp_path, policy=_policy())
    assert opened.tenant_id


def test_the_derivation_refuses_a_parse_that_is_not_the_policy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(config_module, "parse_artifact", _substituting(config_module.parse_artifact))
    with pytest.raises(TypeError, match="`product_entitlement:` section parsed as _NotAPolicy"):
        _open(tmp_path, policy=_policy())


def test_the_open_time_registration_refuses_a_parse_that_is_not_the_policy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(product_module, "parse_artifact", _substituting(product_module.parse_artifact))
    with pytest.raises(TypeError, match="parsed as _NotAPolicy, not the ProductEntitlementPolicy"):
        _open(tmp_path, policy=_policy())
