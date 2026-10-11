"""`ProductRequestContract.from_declared` refuses an argument that is not a declared artifact.

`D-IMPL-378` item 4 (the `D-IMPL-377` close-out, §7e). Handed ``None`` it raised
``AttributeError: 'NoneType' object has no attribute 'declaration'`` — the
interpreter's complaint about the line that dereferenced the argument, not a refusal
by this method. The estate run reached it through
``from_declared(booted.artifacts.get("request_contract"))``: since `D-IMPL-354` the
boot result holds that artifact under ``{tenant}/request_contract``, so ``.get`` by
the bare key returns ``None`` (estate family R).

The method's own convention for a bad argument is a plain ``ValueError`` naming what
is wrong — its docstring records why that, and not
`ccf.controlplane.artifacts.ArtifactLoadError` — so the refusal asserted here is that
``ValueError``, identified by the text that names THIS guard, never by the absence of
the old error. A raw mapping (the document body, not the envelope a manifest load
returns) is refused by the same guard.
"""

from __future__ import annotations

import pytest

from ccf.products.request import ProductRequestContract
from tests.products.test_request_contract import _declared

#: The guard's own statement, asserted as present text.
NOT_AN_ARTIFACT = "is not a declared artifact"


def test_none_is_refused_by_name_rather_than_raising_attribute_error() -> None:
    """THE RED TEST, the hole as worded: ``None`` is refused, by this method, as a ``ValueError``."""
    with pytest.raises(ValueError) as caught:
        ProductRequestContract.from_declared(None)  # type: ignore[arg-type]
    message = str(caught.value)
    assert NOT_AN_ARTIFACT in message, message
    assert "None" in message, message
    # The hint names where a None on this path comes from: the boot result's mapping
    # holds every artifact under its tenant-placed key.
    assert "BootedFabric.artifacts" in message, message


def test_a_raw_mapping_is_refused_by_the_same_guard() -> None:
    """The document body is not the envelope: refused by the same guard, by name."""
    with pytest.raises(ValueError) as caught:
        ProductRequestContract.from_declared({"schema_name": "x"})  # type: ignore[arg-type]
    assert NOT_AN_ARTIFACT in str(caught.value), str(caught.value)


def test_a_declared_artifact_still_reads() -> None:
    """Positive control: the envelope a manifest load returns is read exactly as before."""
    contract = ProductRequestContract.from_declared(_declared())
    assert isinstance(contract, ProductRequestContract)
