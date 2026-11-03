import re
from pathlib import Path

import pytest
from portable.manifest import assert_mongo_db_allowed, ALLOWED_MONGO_DBS, MongoScopeError

ALLOWED = ["fibo", "fibo_v2", "bofa_syndicated"]

RESTORE_SCRIPT = Path(__file__).resolve().parents[1] / "restore" / "restore_mongo.sh"


@pytest.mark.parametrize("name", ALLOWED)
def test_allowed_names_pass(name):
    assert assert_mongo_db_allowed(name) == name


@pytest.mark.parametrize("name", ["rtdetect", "rtdetect_test", "admin",
                                  "config", "local", "", "fibo_v2_backup"])
def test_everything_else_is_refused(name):
    with pytest.raises(MongoScopeError):
        assert_mongo_db_allowed(name)


def test_refusal_names_the_database_and_the_allowlist():
    with pytest.raises(MongoScopeError) as e:
        assert_mongo_db_allowed("rtdetect")
    msg = str(e.value)
    assert "rtdetect" in msg
    assert "fibo_v2" in msg


def _parse_shell_allowlist(script_text: str) -> set[str]:
    """Extract the names in restore_mongo.sh's `guard_db` case pattern.

    The script cannot import portable.manifest (it must run on a laptop
    with no repo checkout present), so it carries its own copy of the
    allowlist as a shell `case` pattern. This parses that literal pattern
    out of the shipped script so the two lists can be compared as sets --
    nothing else in the estate asserts they agree.
    """
    match = re.search(
        r"guard_db\(\)\s*\{.*?case\s+\"\$1\"\s+in\s*\n\s*([a-zA-Z0-9_|]+)\)",
        script_text,
        re.DOTALL,
    )
    assert match, "could not find a `case \"$1\" in ...)` pattern inside guard_db() in restore_mongo.sh"
    return set(match.group(1).split("|"))


def test_restore_script_allowlist_matches_manifest():
    """The restore path's shell allowlist must equal manifest.py's.

    restore_mongo.sh gates on a hardcoded shell `case`, not on
    assert_mongo_db_allowed -- it cannot call into Python from a laptop with
    no repo checkout. That copy is safe only if it is IDENTICAL to
    ALLOWED_MONGO_DBS; nothing else checks that. If either list gains or
    loses a name without the other, this test is what catches it.
    """
    script_text = RESTORE_SCRIPT.read_text()
    shell_allowlist = _parse_shell_allowlist(script_text)
    assert shell_allowlist == set(ALLOWED_MONGO_DBS), (
        f"restore_mongo.sh's case pattern {sorted(shell_allowlist)} does not "
        f"match manifest.ALLOWED_MONGO_DBS {sorted(ALLOWED_MONGO_DBS)}"
    )
