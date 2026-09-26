"""D-IMPL-357 §D (SEC-029): the version the replay record carries is the tag's."""
import importlib.metadata
import re
import subprocess

from ccf.graph.registry import SDK_DISTRIBUTION, _sdk_version


def test_the_installed_version_is_not_the_stale_literal_and_is_git_derived() -> None:
    version = importlib.metadata.version(SDK_DISTRIBUTION)
    assert version != "0.1.0"
    assert re.match(r"^\d+\.\d+\.\d+", version), version
    assert _sdk_version() == version


def test_on_an_exact_tag_the_stamp_equals_the_tag() -> None:
    described = subprocess.run(
        ["git", "describe", "--tags", "--exact-match"], capture_output=True, text=True
    )
    if described.returncode != 0:
        import pytest
        pytest.skip("HEAD is not an exact tag; the gate binds at release only")
    assert importlib.metadata.version(SDK_DISTRIBUTION) == described.stdout.strip().lstrip("v")
