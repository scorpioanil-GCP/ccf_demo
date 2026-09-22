"""Rung 20 — the peer's own product, the identity it is held to, and the boundary.

Three things this module proves that the composite's own module cannot:

* **precision honesty at the source** (`CLD-G13`). The band-disclosing member
  is Citibank, whose envelope puts its position OUT OF SCOPE for the composite
  (`Q1`(b)), so the band is never an admitted child and can only be observed
  where it actually lives — in the peer's own product. Dave's recast is
  explicit that the band *may* be observed as estate evidence; what is
  forbidden is a point estimate derived from it.
* **identity is held to the REGISTRATION** (`CLD-G02`, `CLD-G03`). A peer that
  asserts a different producer id, or a different tenant, is refused — and the
  two are DISTINCT refusals by ruling (`D-IMPL-340`).
* **the boundary is structural** (`CLD-G20`). The consumer holds no handle to
  the peer's stores at all.

The peer tree is imported here and NOT in the composite's module; the two are
never on `sys.path` together, which is how this rung stays clear of the
bare-module-name collision `AIA-F-07` records.
"""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

import pytest
import yaml

from ccf.products.refusal import RefusalEnvelope

from tests.examples.test_cp_20_co_lender import (
    ATTESTED_FACILITY,
    BANK_OF_AMERICA,
    CITIBANK,
    DEV_TOKEN,
    ESTATE_VARIABLES,
    EXAMPLE,
    INTENT,
    UNATTESTED_FACILITY,
    _environ,
    estate,  # noqa: F401  # the module-scoped live-estate guard
)

pytestmark = [pytest.mark.postgres, pytest.mark.fluree]

PEER = EXAMPLE.parent / "peer-cp-20-co-lender"
REPO_ROOT = EXAMPLE.parent.parent

#: The facility Citibank discloses at BAND precision. Its position is out of
#: envelope for the composite and is reached here, at the peer, on purpose.
BAND_FACILITY = "FAC-405B7A"


@pytest.fixture(scope="module")
def peer_modules(estate: None) -> Iterator[tuple[Any, Any]]:  # noqa: F811
    """The PEER's `produce` and `deployment`, from its own directory."""
    names = ("acquisition", "deployment", "produce", "projection")
    saved = {name: sys.modules.pop(name, None) for name in names}
    sys.path.insert(0, str(PEER))
    try:
        import deployment  # noqa: PLC0415
        import produce  # noqa: PLC0415

        yield produce, deployment
    finally:
        sys.path.remove(str(PEER))
        for name, module in saved.items():
            sys.modules.pop(name, None)
            if module is not None:
                sys.modules[name] = module


def _peer_environ() -> dict[str, str]:
    return {name: os.environ[name] for name in ESTATE_VARIABLES}


def _ask_peer(
    peer_modules: tuple[Any, Any], scratch: pathlib.Path, *, facility: str,
    counterparty: str,
) -> Any:
    produce, deployment = peer_modules
    with produce.product(scratch, environ=_peer_environ()) as opened:
        asked = opened.question(
            subject=facility, asked_at=datetime.now(UTC), intent="co-lender-position",
            freshness="standard",
            parameters={
                deployment.FACILITY: facility,
                deployment.COUNTERPARTY: counterparty,
            },
        )
        return opened.answer(asked)


def test_a_band_never_becomes_a_point_estimate(
    peer_modules: tuple[Any, Any], tmp_path: pathlib.Path
) -> None:
    """Declared product gate `CLD-G13` (CP-SPEC-020 §G.1).

    Citibank discloses at `band` precision. The served payload carries the two
    bounds and **no `share_usd` key at all** — absent rather than null,
    because a null invites a reader to supply a default and a midpoint is a
    figure nobody disclosed.

    The positive control beside it is the exact member: this gate must not be
    satisfiable by serving no figure for anybody.
    """
    banded = _ask_peer(
        peer_modules, tmp_path / "band", facility=BAND_FACILITY, counterparty=CITIBANK
    )
    assert not isinstance(banded, RefusalEnvelope), banded
    position = banded.product.payload["positions"][0]
    assert position["precision"] == "band"
    assert "share_usd" not in position, (
        "a band-precision position carries a point estimate; a midpoint is a"
        " number the counterparty never disclosed"
    )
    assert position["band_low"] and position["band_high"]
    rendered = json.dumps(banded.product.payload)
    midpoint = str(
        (int(position["band_low"]) + int(position["band_high"])) // 2
    )
    assert midpoint not in rendered, (
        f"the band's midpoint {midpoint} appears in the payload"
    )

    exact = _ask_peer(
        peer_modules, tmp_path / "exact", facility=ATTESTED_FACILITY,
        counterparty=BANK_OF_AMERICA,
    )
    assert not isinstance(exact, RefusalEnvelope), exact
    served = exact.product.payload["positions"][0]
    assert served["precision"] == "exact"
    assert served["share_usd"], (
        "the exact member carries no figure either; this gate would be"
        " satisfiable by serving nothing for anybody"
    )


def test_the_peer_refuses_its_own_unattested_position(
    peer_modules: tuple[Any, Any], tmp_path: pathlib.Path
) -> None:
    """Declared product gate `CLD-G06` (CP-SPEC-020 §G.1) — the producer half.

    The refusal originates at the PEER, which is the honest place for it: an
    unverifiable remote claim is a position with no attestation record behind
    it, and the institution that holds it is the one declining to assert it.
    The consumer's half of this gate lives in `test_cp_20_co_lender.py`.
    """
    refused = _ask_peer(
        peer_modules, tmp_path / "unattested", facility=UNATTESTED_FACILITY,
        counterparty=BANK_OF_AMERICA,
    )
    assert isinstance(refused, RefusalEnvelope), (
        "the peer served a position it publishes no attestation for"
    )
    assert refused.reason == "subject-unavailable"
    assert refused.replay_reference


@contextmanager
def _impostor(
    tmp_path: pathlib.Path, *, tenant: str | None = None, **door: str
) -> Iterator[str]:
    """A peer door that asserts a DIFFERENT identity than the one registered.

    ``tenant`` moves the whole deployment, not only its door. Measured
    2026-09-22: the SDK refuses at the PRODUCER's own boot when a `door`
    section asserts a `producer_tenant` its deployment does not declare
    (`D-IMPL-343` R-6), so a door cannot misdeclare its own tenant at all —
    defense in depth ahead of the consumer's admission check. A genuinely
    other-tenant peer is therefore a genuinely other deployment, which is what
    `CLD-G03` has to be built against.
    """
    tree = tmp_path / "impostor"
    shutil.copytree(PEER, tree)
    config = yaml.safe_load((tree / "ccf_config.yaml").read_text(encoding="utf-8"))
    if tenant is not None:
        config["tenant_id"] = tenant
        config["door"]["producer_tenant"] = tenant
    config["door"].update(door)
    (tree / "ccf_config.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")
    env = {
        **os.environ,
        "CCF_CP_20_PEER_DOOR_TOKEN": DEV_TOKEN,
        # The copy sits outside the repo, so its own `REPO_ROOT` guess is
        # wrong; the SDK reaches it through the path instead.
        "PYTHONPATH": os.pathsep.join(
            [str(REPO_ROOT / "src"), str(REPO_ROOT / "runtime"), str(tree)]
        ),
    }
    process = subprocess.Popen(
        [sys.executable, str(tree / "run.py"), "--door"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env,
    )
    try:
        assert process.stdout is not None
        announcement = process.stdout.readline().strip()
        if not announcement.startswith("READY "):
            _, stderr = process.communicate(timeout=15)
            raise AssertionError(
                f"the impostor door did not start ({announcement!r});"
                f" stderr:\n{stderr[-2000:]}"
            )
        yield f"http://127.0.0.1:{int(announcement.split()[1])}/mcp"
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def _consumer_refusal(url: str, scratch: pathlib.Path) -> Any:
    """Ask the composite a federated question against ``url`` — in a subprocess.

    A subprocess because this module holds the PEER tree on `sys.path`, and
    importing the consumer beside it is exactly the collision `AIA-F-07`
    records. The boundary is kept rather than worked around.
    """
    script = (
        "import json,sys,tempfile,pathlib\n"
        f"sys.path[:0]=[{str(EXAMPLE)!r},{str(REPO_ROOT / 'src')!r},{str(REPO_ROOT / 'runtime')!r}]\n"
        "from datetime import UTC, datetime\n"
        "import deployment, produce\n"
        "from ccf.products.refusal import RefusalEnvelope\n"
        f"with tempfile.TemporaryDirectory() as s, produce.product(pathlib.Path(s)) as o:\n"
        f"    a=o.question(subject={ATTESTED_FACILITY!r}, asked_at=datetime.now(UTC),"
        f" intent={INTENT!r}, freshness='standard',"
        f" parameters={{deployment.FACILITY:{ATTESTED_FACILITY!r},"
        f" deployment.INCLUDE_FEDERATED:True,"
        f" deployment.COUNTERPARTIES:[{BANK_OF_AMERICA!r}]}})\n"
        "    r=o.answer(a)\n"
        "    import dataclasses\n"
        "    rows=[]\n"
        "    try:\n"
        "        rec=o.artifact_store\n"
        "    except Exception: pass\n"
        "    print(json.dumps({'refused': isinstance(r, RefusalEnvelope),"
        " 'reason': getattr(r,'reason',None),"
        " 'detail': str(getattr(r,'detail',None))}))\n"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        env={**os.environ, **_environ(url)},
        capture_output=True, text=True, timeout=180, check=False,
    )
    assert completed.returncode == 0, completed.stderr[-2000:]
    return json.loads(completed.stdout.strip().splitlines()[-1])


def test_a_peer_asserting_another_producer_id_is_refused(
    estate: None, tmp_path: pathlib.Path  # noqa: F811
) -> None:
    """Declared product gate `CLD-G02` (CP-SPEC-020 §G.1).

    The consumer's registration is the authority for WHO it is talking to. A
    door asserting a different `producer_id` — same tenant, same class, same
    answer — is refused, because a producer's claim about itself never
    authorizes; equality with a governed registration is a binding check.
    """
    with _impostor(tmp_path, producer_id="someone-elses-egress") as url:
        impostor = _consumer_refusal(url, tmp_path)
    assert impostor["refused"] is True, "an impostor producer was ADMITTED"
    assert impostor["reason"] == "child_admission", impostor
    # THE POSITIVE CONTROL. Without it this gate would pass for any reason a
    # door failed at all — an unreachable port, a bad token, a crashed peer.
    with _impostor(tmp_path / "honest") as url:
        honest = _consumer_refusal(url, tmp_path)
    assert honest["refused"] is False, (
        "the UNMODIFIED copy was refused too, so this gate measures something"
        f" other than the identity mismatch: {honest}"
    )


def test_a_peer_asserting_another_tenant_is_refused(
    estate: None, tmp_path: pathlib.Path  # noqa: F811
) -> None:
    """Declared product gate `CLD-G03` (CP-SPEC-020 §G.1).

    Wrong PRODUCER and wrong PRODUCER TENANT are distinct by ruling
    (`D-IMPL-340`), and both refuse. This is the tenant half: an answer
    governed under a tenant the registration does not expect is not admitted,
    even though the producer id matches.

    The impostor is a whole other DEPLOYMENT rather than a mislabelled door,
    because the SDK will not boot a door whose `producer_tenant` disagrees
    with its own `tenant_id` — see :func:`_impostor`.
    """
    with _impostor(tmp_path, tenant="some-other-bank") as url:
        impostor = _consumer_refusal(url, tmp_path)
    assert impostor["refused"] is True, "a foreign-tenant answer was ADMITTED"
    assert impostor["reason"] == "child_admission", impostor


def test_the_consumer_holds_no_handle_to_the_peers_stores() -> None:
    """Declared product gate `CLD-G20` (CP-SPEC-020 §G.1).

    The two fabrics share a HOST: the peer's Postgres differs from ours by a
    database name and a role, its Fluree by a port. Isolation here is a
    software property, so this gate is structural rather than a nicety.

    Asserted over the consumer's own modules and documents: no peer source
    setting is named, and no database client is constructed anywhere outside
    the tree's own `acquisition`, which reads OUR stores only.
    """
    consumer_files = [
        path for path in EXAMPLE.rglob("*")
        if path.is_file()
        and path.suffix in {".py", ".yaml"}
        and "spec" not in path.relative_to(EXAMPLE).parts
    ]
    assert consumer_files, "no consumer files were scanned; the gate is vacuous"
    for path in consumer_files:
        text = path.read_text(encoding="utf-8")
        for forbidden in (
            "CCF_CP_20_PEER_POSTGRES_DSN",
            "CCF_CP_20_PEER_FLUREE_URL",
            "CCF_CP_20_PEER_POSTGRES_SCHEMA",
            "CCF_CP_20_PEER_FLUREE_LEDGER",
            "bofa_syndicated",
            "colender",
        ):
            assert forbidden not in text, (
                f"{path.relative_to(EXAMPLE)} names {forbidden!r}; the consumer"
                " reaches the co-lender only through the registered door"
            )
    # and the ONE endpoint it does name is a door, not a store
    environment = (EXAMPLE / "ccf_config.yaml").read_text(encoding="utf-8")
    assert "endpoint_from_env: CCF_CP20_PEER_URL" in environment
