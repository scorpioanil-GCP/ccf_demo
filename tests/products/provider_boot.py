"""Boot a fabric and produce the atomic child product — the provider's side.

`D-IMPL-336` **Amendment 5 §5**. Imported by two callers that must not drift:
the in-process integration test, and
``tests/crossproc/servers/mcp_atomic_product_child.py``, which runs it in a
**separate process** over its **own** database.

**That is the whole demonstration.** The same provider code produces the same
atomic product on both sides of the boundary; what changes is only where it
runs and how the composite reaches it. If the composite had to know anything
about this module, the claim *"the composite does not own the atomic
product's assembly"* would be false — and it is measurable rather than
asserted, because the parent imports nothing from here.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

CHILD_CLASS = "fixture.child-product"
CHILD_CLASS_KEY = "fixture/product-class-child"
CHILD_REQUEST_CONTRACT_KEY = "fixture/request-contract-child"


def child_product_class() -> dict[str, Any]:
    """The atomic product's class declaration.

    Its `required_operator_keys` name an operator the composite's own class
    does not, which is what makes the composed lineage a genuine union.
    """
    return {
        "semver": "1.0.0",
        "schema_name": CHILD_CLASS,
        "schema_version": "1.0.0",
        "ttl_anchor": "from_decision",
        "assembly_mode": "algorithmic",
        "max_ttl_key": "fixture/max-ttl",
        "required_operator_keys": ["similarity.corpus-select"],
    }


def child_request_contract() -> dict[str, Any]:
    """The atomic product's OWN request contract.

    A request contract is per class. Validating the child against the parent's
    is a `product-request-violation`, which is what the first run of the
    integration proof measured — the door proving it is a real door.
    """
    return {
        "semver": "1.0.0",
        "class_id": "fixture.request-contract",
        "declaration": {
            "schema_name": CHILD_CLASS,
            "schema_version": "1.0.0",
            "arguments": {
                "properties": {
                    "revenue_threshold": {
                        "type": "number",
                        "description": "Fixture parameter; no default anywhere.",
                    }
                },
                "required": ["revenue_threshold"],
            },
        },
    }


def serve_atomic_child(workspace: Path) -> str:
    """Boot, resolve, and return the door bytes for the atomic product.

    Args:
        workspace: A directory this provider owns entirely — its deployment
            artifacts, its SQLite database, its artifact store. **Nothing here
            is shared with a consumer**, which is the property the
            cross-process demonstration exists to make visible.

    Returns:
        The canonical :func:`~ccf.products.door.door_answer` bytes, decoded —
        the same wire form an in-process door emits, so a consumer cannot tell
        from the answer where it was produced.
    """
    from ccf.artifacts.file_store import FileArtifactStore
    from ccf.controlplane.registry import ControlPlaneRegistry
    from ccf.deployment import load_and_boot
    from ccf.products.door import WireRequest, door_answer
    from ccf.products.request import ProductRequest

    from tests.deployment.conftest import (
        ARTIFACT_SET,
        PRODUCT_CLASS_KEY,
        SIGNAL_BATCH_KEY,
        TENANT,
        manifest_document,
        write_artifact,
    )
    from tests.products.test_resolver_seam import (
        ASKED_AT,
        DEBT_PROFILE_KEY,
        OBLIGATION_ON_OK,
        PERSPECTIVE,
        REQUEST_CONTRACT_CLASS_ID,
        THRESHOLD_PARAMETER,
        _arguments,
        _Booted,
    )

    root = workspace / "deployment"
    root.mkdir(parents=True, exist_ok=True)
    for key, filename, _cid, _role, _reg, document in ARTIFACT_SET:
        if key == PRODUCT_CLASS_KEY:
            document = copy.deepcopy(document)
        write_artifact(root, filename, document)
    write_artifact(root, "product-class-child.yaml", child_product_class())
    write_artifact(root, "request-contract-child.yaml", child_request_contract())
    write_artifact(
        root,
        "debt-profile.yaml",
        {
            "semver": "1.0.0",
            "risk_sensitivity": "1",
            "forced_llm_threshold": "0.30",
            "fail_closed_threshold": "0.70",
            "signal_obligations": [{"signal": "ok", "obligation_ref": OBLIGATION_ON_OK}],
        },
    )
    body = manifest_document()
    body["artifacts"] = [
        *body["artifacts"],
        {
            "path": "product-class-child.yaml",
            "key": CHILD_CLASS_KEY,
            "class_id": "ccf.product-class",
            "role": "register",
            "registration": "typed",
        },
        {
            "path": "request-contract-child.yaml",
            "key": CHILD_REQUEST_CONTRACT_KEY,
            "class_id": REQUEST_CONTRACT_CLASS_ID,
            "role": "load",
            "registration": "typed",
        },
        {
            "path": "debt-profile.yaml",
            "key": DEBT_PROFILE_KEY,
            "class_id": "ccf.debt-profile",
            "role": "register",
            "registration": "typed",
        },
    ]
    manifest = write_artifact(root, "manifest.yaml", body)
    control_plane = ControlPlaneRegistry()
    fabric = load_and_boot(
        manifest,
        registry=control_plane,
        connection={"database_path": str(workspace / "provider.sqlite3")},
    )
    for envelope in fabric.artifacts[SIGNAL_BATCH_KEY].envelopes:
        fabric.handle.worker.ingest(envelope)
    booted = _Booted(
        fabric=fabric,
        control_plane=control_plane,
        store=FileArtifactStore(root=workspace / "artifacts"),
        root=root,
    )
    try:
        from ccf.deployment.operators import build_operator_registry  # noqa: F401
        from ccf.products.resolver import GovernedResolver

        from tests.deployment.conftest import SIMILARITY_KEY

        arguments = _arguments(booted)
        arguments.update(
            product_class_key=CHILD_CLASS_KEY,
            request_contract_key=CHILD_REQUEST_CONTRACT_KEY,
            operator_parameter_keys=(SIMILARITY_KEY,),
            composite_children=None,
        )
        request = ProductRequest(
            schema_name=CHILD_CLASS,
            schema_version="1.0.0",
            subject="acct-1",
            intent="fixture-intent",
            freshness="fixture-freshness",
            asked_at=ASKED_AT,
            parameters={THRESHOLD_PARAMETER: 1000},
        )
        resolved = GovernedResolver(**arguments)(
            tenant=TENANT,
            product_class=CHILD_CLASS,
            version="1.0.0",
            perspective=PERSPECTIVE,
            request=request,
        )
        return door_answer(
            resolved,
            echo=WireRequest(
                product_id=CHILD_CLASS,
                parameters={"subject": "acct-1"},
                temporal_boundary=ASKED_AT,
            ),
            resolved_request=request,
        ).decode()
    finally:
        fabric.handle.close()
