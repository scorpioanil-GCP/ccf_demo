#!/usr/bin/env python3
"""The portable bundle's landmark counts must not go stale silently.

`portable/verify_install.py` asserts hardcoded row counts against a RESTORED
estate. That is deliberate and should stay: a verifier deriving its
expectations from the artifact it verifies can only prove the restore matched
the dump, and cannot see a DUMP that silently lost rows.

The cost is staleness, and it has bitten twice. Before Wave 20 the file
expected `ccf_v2 base tables` = 113 and `crosswalk rows` = 53; Wave 20 made
those 115 and 83. Nothing in the repo noticed, because the file only runs on a
laptop after a restore. A rebuilt bundle would have reported **two failures
and 30 phantom crosswalk orphans** on a restore that was entirely correct --
a broken-looking estate that was fine, discovered at the worst moment.

So the landmarks are asserted HERE, against the live estate, in the suite that
runs on every change. Staleness now fails in the repo, before a rebuild can
ship it.

**If this test fails, that is the signal to update `PG_LANDMARKS` -- and to
rebuild the bundle**, because the deployed one no longer describes the estate.

    uv run --with pytest pytest validators/test_bundle_landmarks.py
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "verify_install", REPO / "portable" / "verify_install.py")
vi = importlib.util.module_from_spec(_spec)
sys.modules["verify_install"] = vi
_spec.loader.exec_module(vi)

#: How each landmark is measured against the live estate. Written out rather
#: than reusing the verifier's own SQL: two copies that must agree is the
#: point, since a shared query would make both wrong together.
QUERIES = {
    "ccf_v2 base tables":
        "SELECT count(*) FROM information_schema.tables "
        "WHERE table_schema = 'ccf_v2' AND table_type = 'BASE TABLE'",
    "public (v1) base tables":
        "SELECT count(*) FROM information_schema.tables "
        "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'",
    "legal_entity rows": "SELECT count(*) FROM ccf_v2.legal_entity",
    "crosswalk rows": "SELECT count(*) FROM ccf_v2.crosswalk",
    "internal_client rows": "SELECT count(*) FROM ccf_v2.internal_client",
    "principal_jurisdiction grants":
        "SELECT count(*) FROM ccf_v2.principal_jurisdiction",
}


def test_every_landmark_has_a_query():
    """A landmark nobody measures is a landmark nobody can find stale."""
    assert set(vi.PG_LANDMARKS) == set(QUERIES)


@pytest.mark.parametrize("name", sorted(QUERIES))
def test_landmark_matches_the_live_estate(name):
    from ccf.config import pg_connect
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(QUERIES[name])
        live = cur.fetchone()[0]
    expected = vi.PG_LANDMARKS[name]
    assert live == expected, (
        f"{name}: bundle verifier expects {expected}, live estate has {live}. "
        f"Update PG_LANDMARKS in portable/verify_install.py AND rebuild the "
        f"bundle — the deployed one no longer describes this estate.")
