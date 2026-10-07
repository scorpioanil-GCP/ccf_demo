"""Child process: the paved fixture PRODUCER, opened and served through the standard door.

`D-IMPL-343`, the consumer half. The producer side of the SDK-level consumer
proof (``tests/products/test_paved_consumer.py``): this process writes the
producer's two documents, opens the product on the paved road with the
fixture's three callables, opens the standard door over it and serves on an
ephemeral loopback port with REAL bearer authentication. It prints ``READY
{port}`` once the server reports started — the `D-16` handshake, no sleep in
the parent's path.

**What the consumer process never gets, and that is the point.** No
assembler, no graph handle, no artifact store, no Control Plane registry, no
connection string — nothing but the logical server name its ``producers:``
declaration selects, the identity its registration expects, and the typed
door bytes that come back.

The bearer credential is read from the variable the environment document
names (``PAVED_CHILD_TOKEN``); the parent SETS it to learn it without a side
channel, exactly as the canonical spread's harness does.

Run as ``python tests/crossproc/servers/paved_fixture_door.py``.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

_TESTS_ROOT = Path(__file__).resolve().parents[2]
_REPO_ROOT = _TESTS_ROOT.parent
# Spawned as a bare `python <file>`, so none of pytest's sys.path work applies.
for _root in (_REPO_ROOT / "src", _REPO_ROOT / "runtime", _TESTS_ROOT, _REPO_ROOT):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))


def main() -> None:
    """Write the producer's documents, open the product, open its door, serve, announce."""
    from ccf.products.product import open_product  # noqa: PLC0415
    from ccf_runtime.mcp.product_door import open_door  # noqa: PLC0415

    from tests.products import paved_fixture as fixture  # noqa: PLC0415

    workspace = Path(tempfile.mkdtemp(prefix="paved-producer-"))
    root = fixture.write_tree(
        workspace / "deployment",
        config=fixture.producer_config(),
        environment=fixture.producer_environment_text(),
    )
    environ = {**os.environ, fixture.CHILD_DSN_VAR: "postgresql://fixture"}
    # `D-IMPL-358` step 5 ruling 11: a deployment declaring no temporal boundary
    # refuses every question — and the PRODUCER is its own deployment, in its own
    # process, with its own tenant. A consumer that declared one for itself would
    # still get a `composite-child-refusal` if the producer had not, which is
    # exactly what the paved-consumer suite measured before this line existed.
    from ccf.controlplane.registry import ControlPlaneRegistry  # noqa: PLC0415

    from tests.composition import declare_wide_temporal_boundary, declared_erasure_trust  # noqa: PLC0415

    control_plane = ControlPlaneRegistry()
    declare_wide_temporal_boundary(
        control_plane, tenant_id=fixture.PRODUCER_TENANT
    )
    with open_product(
        # SEC-009 (fix round 5): the producer's erasure trust root.
        erasure_trust=declared_erasure_trust(fixture.PRODUCER_TENANT),
        config_root=root,
        scratch=workspace / "scratch",
        acquire=fixture.Acquire(),
        project=fixture.plan_factory,
        assess=fixture.assess,
        environ=environ,
        control_plane=control_plane,
        # `D-IMPL-358` step 5 section H, class 1. THE PRODUCER'S FABRIC CLOCK,
        # pinned to the SAME instant the consumer is pinned to. Unpinned, this
        # process served at the real wall clock while the consumer asked in March,
        # so the child arrived claiming validity months beyond anything the
        # consumer's own MAX_TTL admits — and the composition refused a child
        # that was never the subject of the test.
        #
        # The producer is its own process. It reads the instant from the fixture
        # it already imports rather than from an environment variable, because
        # this program is launched with the repo importable and `fixture` is where
        # that instant is declared.
        clock=lambda: fixture.ADMITTED_AT,
    ) as opened:
        open_door(opened, environ=environ).serve_loopback(
            announce=lambda port: print(f"READY {port}", flush=True)
        )


if __name__ == "__main__":
    main()
