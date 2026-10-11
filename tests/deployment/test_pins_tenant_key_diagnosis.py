"""`ResolvedPins.version_for` names the actual cause when a bare key misses a placed pin.

`D-IMPL-378` item 3 (the `D-IMPL-377` close-out, §7e; estate family R). Since
`D-IMPL-354` the three loaders — `load_and_boot`, `load_config_and_boot` and the
consumer chain `open_product` derives — place every manifest key under the
deployment's tenant before registering it (`ccf.deployment.manifest.manifest_under_tenant`),
so the pin for an authored ``policy`` is recorded under ``{tenant}/policy``. A caller
asking by the bare key was told the manifest *"either does not name it or names it
with role 'load'"* — both false in that case — which sends an operator to the manifest
rather than to the key.

The red tests assert the diagnosis that IS given, by name: the placed key the pin is
recorded under, and the cause (tenant placement). The controls keep the other outcomes
exact: a placed key still resolves, and a key nothing carries still gets the
absent-or-``role: load`` diagnosis (`D-IMPL-80`), which remains true there.
"""

from __future__ import annotations

import pathlib

import pytest

from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment.config import load_config_and_boot
from ccf.deployment.pins import ArtifactPin, ResolvedPins, UnpinnedArtifactError
from tests.deployment.test_config_equivalence import TENANT, _config_document, write_artifact

#: The fixture tenant for the synthetic pin sets. Not the config fixture's tenant,
#: so the synthetic tests cannot pass by matching a string the boot test uses.
SYNTHETIC_TENANT = "tenant-378"
PLACED = f"{SYNTHETIC_TENANT}/policy"
PLACED_WITH_SEPARATOR = f"{SYNTHETIC_TENANT}/operator-parameters/traversal"

#: The cause, as the diagnosis names it. Asserted as present text: the mechanism by
#: name, never the absence of the old wording.
PLACEMENT = "placed under the deployment's tenant"


def _pins() -> ResolvedPins:
    return ResolvedPins(
        entries=(
            ArtifactPin(
                key=PLACED,
                version="v-placed",
                class_id="fixture.policy-bundle",
                registration="typed",
            ),
            ArtifactPin(
                key=PLACED_WITH_SEPARATOR,
                version="v-traversal",
                class_id="fixture.operator-parameters",
                registration="typed",
            ),
        )
    )


def test_a_bare_key_names_the_placed_key_its_pin_is_recorded_under() -> None:
    """THE RED TEST, synthetic: the bare ``policy`` against a pin under ``tenant-378/policy``."""
    with pytest.raises(UnpinnedArtifactError) as caught:
        _pins().version_for("policy")
    message = str(caught.value)
    assert repr(PLACED) in message, message
    assert PLACEMENT in message, message
    assert "D-IMPL-354" in message, message


def test_a_bare_key_holding_a_separator_is_diagnosed_the_same_way() -> None:
    """A section label may itself contain ``/``; the tenant is the text before the FIRST one."""
    with pytest.raises(UnpinnedArtifactError) as caught:
        _pins().version_for("operator-parameters/traversal")
    message = str(caught.value)
    assert repr(PLACED_WITH_SEPARATOR) in message, message
    assert PLACEMENT in message, message


def test_a_booted_fabrics_pins_name_the_placed_key_for_a_bare_lookup(
    tmp_path: pathlib.Path,
) -> None:
    """THE RED TEST, end to end: the config door's own pins, read by the key the config authored.

    ``policy`` is the section label the single-file config derives; the boot registers it
    under ``{tenant}/policy`` (`tests/deployment/test_namespaced_boot.py` pins that). The
    estate's family R is exactly this call made by example code.
    """
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    booted = load_config_and_boot(
        write_artifact(config_dir, "ccf_config.yaml", _config_document()),
        registry=ControlPlaneRegistry(),
        connection={"database_path": str(tmp_path / "pins-diagnosis.sqlite3")},
    )
    try:
        assert booted.keys is not None
        placed = booted.keys.policy_bundle
        assert placed == f"{TENANT}/policy", placed
        with pytest.raises(UnpinnedArtifactError) as caught:
            booted.pins.version_for("policy")
        message = str(caught.value)
        assert repr(placed) in message, message
        assert PLACEMENT in message, message
        # Positive control on the same fabric: the placed key resolves.
        assert booted.pins.version_for(placed)
    finally:
        booted.handle.close()


def test_the_placed_key_still_resolves() -> None:
    """Control: lookup by the recorded key is unchanged."""
    assert _pins().version_for(PLACED) == "v-placed"
    assert _pins().version_for(PLACED_WITH_SEPARATOR) == "v-traversal"


def test_a_key_nothing_carries_keeps_the_absent_or_load_role_diagnosis() -> None:
    """Control: with no placed pin to point at, the `D-IMPL-80` diagnosis is the true one."""
    with pytest.raises(UnpinnedArtifactError) as caught:
        _pins().version_for("nothing")
    message = str(caught.value)
    assert "role 'load'" in message, message
    assert "D-IMPL-80" in message, message
    assert PLACEMENT not in message, message
