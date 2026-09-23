"""Import the cp-05 door's adapter in a process that already holds another tree.

Run as a program by `test_product_tree_import_isolation.py`, never imported —
the whole point is a FRESH interpreter whose `sys.modules` this session has not
touched, so the result depends on nothing about pytest's collection order.

    _cp_import_isolation_probe.py <repo> <door> <intruder> [mode]

Modes:

``(none)``          import the door's adapter as it ships.
``unguarded``       strip the provenance guard first. **The negative control**:
                    it must bind the intruder, because a poisoning that the
                    unguarded adapter survives is a poisoning that proves
                    nothing about the guarded one.
``empty-specimen``  point the adapter at a directory holding no product tree.
                    The guard must REFUSE rather than fall back to whatever is
                    resident.

Prints one JSON line: ``{"resident", "loaded", "outcome"}``. ``outcome`` is
``"bound"`` or the exception type — an exception is a legitimate result here,
not a probe failure, so the probe exits 0 either way and the caller judges.
"""

from __future__ import annotations

import json
import pathlib
import shutil
import sys
import tempfile

GUARDED_CALL = "prod, dep = _specimen_modules()"
UNGUARDED_CALL = (
    "sys.path.insert(0, str(SPECIMEN))\n"
    "import produce as prod  # noqa: E402\n"
    "import deployment as dep  # noqa: E402"
)
SPECIMEN_DIR = "cp-05-credit-exposure-rollup"
SPECIMEN_LINE = f'SPECIMEN = HERE.parent / "{SPECIMEN_DIR}"'


def main(argv: list[str]) -> int:
    repo, door, intruder = (pathlib.Path(argument) for argument in argv[1:4])
    mode = argv[4] if len(argv) > 4 else ""
    sys.path[:0] = [str(repo / "src"), str(repo / "runtime")]

    # POISON. Another product tree is already resident — exactly the state any
    # process reaches after running one example and then reaching for another.
    sys.path.insert(0, str(intruder))
    import produce as resident_module  # noqa: PLC0415

    sys.path.remove(str(intruder))
    resident = pathlib.Path(resident_module.__file__ or "").parent.name

    with tempfile.TemporaryDirectory() as tmp:
        work = pathlib.Path(tmp) / door.name
        shutil.copytree(door, work)
        source = (work / "adapter.py").read_text(encoding="utf-8")

        # The copy sits outside the repository, so `HERE.parent / <specimen>`
        # no longer resolves. Pin it to the REAL specimen, so every mode below
        # differs from the shipped adapter in exactly the one thing it is
        # testing and in nothing else.
        assert SPECIMEN_LINE in source, "the specimen declaration moved"
        source = source.replace(
            SPECIMEN_LINE, f"SPECIMEN = Path({str(door.parent / SPECIMEN_DIR)!r})"
        )

        if mode == "unguarded":
            assert GUARDED_CALL in source, "the guarded call moved; this control is stale"
            source = source.replace(GUARDED_CALL, UNGUARDED_CALL)
        elif mode == "empty-specimen":
            empty = pathlib.Path(tmp) / "not-a-product-tree"
            empty.mkdir()
            source = source.replace(
                f"SPECIMEN = Path({str(door.parent / SPECIMEN_DIR)!r})",
                f"SPECIMEN = Path({str(empty)!r})",
            )

        (work / "adapter.py").write_text(source, encoding="utf-8")
        sys.path.insert(0, str(work))
        try:
            import adapter  # noqa: PLC0415

            loaded = pathlib.Path(adapter.prod.__file__ or "").parent.name
            outcome = "bound"
        except Exception as exc:  # noqa: BLE001 — a refusal is a result, not a failure
            loaded, outcome = "", type(exc).__name__

    print(json.dumps({"resident": resident, "loaded": loaded, "outcome": outcome}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
