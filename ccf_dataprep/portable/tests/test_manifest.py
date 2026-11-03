import hashlib, json
from pathlib import Path
from portable.manifest import add_artifact, write_manifest

def test_sha256_matches_the_shell_tool(tmp_path):
    f = tmp_path / "a.bin"
    f.write_bytes(b"ccf" * 1000)
    entry = add_artifact(tmp_path, "a.bin", store="test", fabric="test",
                         method="write_bytes")
    expected = hashlib.sha256(f.read_bytes()).hexdigest()
    assert entry["sha256"] == expected
    assert entry["bytes"] == 3000

def test_directory_artifact_hashes_its_contents_not_the_dirname(tmp_path):
    d = tmp_path / "dump"
    (d / "sub").mkdir(parents=True)
    (d / "sub" / "x.bson").write_bytes(b"one")
    first = add_artifact(tmp_path, "dump", store="mongo", fabric="v2",
                         method="mongodump")
    (d / "sub" / "x.bson").write_bytes(b"two")
    second = add_artifact(tmp_path, "dump", store="mongo", fabric="v2",
                          method="mongodump")
    assert first["sha256"] != second["sha256"], \
        "a directory hash that ignores content cannot detect a changed dump"

def test_manifest_is_valid_json_with_every_entry(tmp_path):
    (tmp_path / "a.bin").write_bytes(b"x")
    entries = [add_artifact(tmp_path, "a.bin", store="s", fabric="f",
                            method="m")]
    path = write_manifest(tmp_path, entries)
    doc = json.loads(path.read_text())
    assert doc["artifact_count"] == 1
    assert doc["artifacts"][0]["path"] == "a.bin"
    assert "generated_at" in doc

def test_directory_artifact_hash_detects_a_rename(tmp_path):
    d = tmp_path / "dump"
    d.mkdir()
    (d / "before.bson").write_bytes(b"identical bytes")
    first = add_artifact(tmp_path, "dump", store="mongo", fabric="v2",
                         method="mongodump")
    (d / "before.bson").rename(d / "after.bson")
    second = add_artifact(tmp_path, "dump", store="mongo", fabric="v2",
                          method="mongodump")
    assert first["sha256"] != second["sha256"], \
        "a directory hash that ignores file names cannot detect a rename"
    assert first["bytes"] == second["bytes"], \
        "a rename must not change the byte total — that would mask the point"
