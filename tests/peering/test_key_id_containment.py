"""LOW-02 exploit test — ``FileBackedKeySource`` refuses a ``key_id`` that is not one.

The row (``docs/superpowers/specs/2026-10-05-remaining-rows-exploit-tests.md``,
"LOW-02" and its MEASURED block, D-IMPL-372) measured
``src/ccf/peering/identity.py::FileBackedKeySource.signing_key`` joining the
caller's ``key_id`` onto its directory before any check: ``../outside``
returned a key from OUTSIDE the directory, an absolute id replaced the root,
``a/b`` resolved a key ``key_ids()`` never lists, and every hostile id reached
``Path.read_text``. The repair is a TOTAL allowlist match run before the join —
the shape of ``src/ccf/artifacts/protocol.py::held_content_address``
(D-IMPL-345 S-02) — so the test asserts the refusal happens with **no** file
read at all, and that the refusal is a ``KeyUnavailable`` (so a caller that
handles absence handles it identically).

Reachability: only local composition passes ``key_id``
(``DetachedJwsIdentityProvider.sign``); the verify path reads
``public_keys[kid]``, never the file source. The test needs no door.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from ccf.peering.identity import FileBackedKeySource, KeyUnavailable

_JWK = {"kty": "EC", "crv": "P-256", "x": "IN", "y": "IN", "d": "IN"}

HOSTILE_KEY_IDS: tuple[str, ...] = (
    "../outside",
    "../../../../etc/passwd",
    "/etc/hostname",
    "a/b",
    "a\\b",
    ".",
    "..",
    "",
    "good\x00",
    "good\n",
    " good",
)


@pytest.fixture
def layout(tmp_path: pathlib.Path) -> pathlib.Path:
    keys = tmp_path / "keys"
    keys.mkdir()
    (keys / "good.jwk").write_text(json.dumps(_JWK), encoding="utf-8")
    (keys / "a").mkdir()
    (keys / "a" / "b.jwk").write_text(json.dumps(_JWK), encoding="utf-8")
    (tmp_path / "outside.jwk").write_text(json.dumps({**_JWK, "x": "OUT"}), encoding="utf-8")
    return keys


@pytest.fixture
def reads(monkeypatch: pytest.MonkeyPatch) -> list[pathlib.Path]:
    opened: list[pathlib.Path] = []
    real = pathlib.Path.read_text

    def spy(self: pathlib.Path, *args: object, **kwargs: object) -> str:
        opened.append(self)
        return real(self, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(pathlib.Path, "read_text", spy)
    return opened


@pytest.mark.parametrize("key_id", HOSTILE_KEY_IDS)
def test_a_hostile_key_id_is_refused_before_any_file_is_read(
    layout: pathlib.Path, reads: list[pathlib.Path], key_id: str
) -> None:
    source = FileBackedKeySource(directory=layout)
    with pytest.raises(KeyUnavailable) as refused:
        source.signing_key(key_id=key_id)
    assert reads == [], f"{key_id!r} reached a file read: {reads}"
    assert "not a key identifier" in str(refused.value)


def test_the_traversal_case_does_not_return_the_outside_key(layout: pathlib.Path) -> None:
    source = FileBackedKeySource(directory=layout)
    try:
        got = source.signing_key(key_id="../outside")
    except KeyUnavailable:
        return
    pytest.fail(f"../outside returned a key from outside the directory: {got}")


def test_a_well_formed_key_id_still_resolves(
    layout: pathlib.Path, reads: list[pathlib.Path]
) -> None:
    source = FileBackedKeySource(directory=layout)
    assert source.signing_key(key_id="good") == _JWK
    assert reads == [layout / "good.jwk"]


def test_listing_and_lookup_agree_on_the_grammar(layout: pathlib.Path) -> None:
    (layout / "..jwk").write_text(json.dumps(_JWK), encoding="utf-8")
    (layout / "bad name.jwk").write_text(json.dumps(_JWK), encoding="utf-8")
    source = FileBackedKeySource(directory=layout)
    listed = source.key_ids()
    assert listed == ("good",)
    for key_id in listed:
        source.signing_key(key_id=key_id)
