"""`python -m tools.estate_census` — the census command line.

Four subcommands, in the order a census uses them::

    python -m tools.estate_census watermarks --out before.json
    python -m tools.estate_census capture --out-json run.json --estate-before before.json -- tests/examples
    python -m tools.estate_census attach-estate --bundle run.json --after after.json
    python -m tools.estate_census classify --base base.json --candidate run.json

Exit codes are the house split `tools/estate_census/classify.py::EXIT_CODES`
declares: ``0`` PASS, ``1`` HOLD, ``2`` INDETERMINATE. Every subcommand uses
``2`` for *could not tell*, so no caller can read an unreadable subject as a
pass.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from tools.estate_census.classify import EXIT_CODES, INDETERMINATE, classify, render
from tools.estate_census.evidence import (
    BUNDLE_KIND,
    BUNDLE_VERSION,
    credential_in_file,
    read_json,
    read_json_with_reason,
    redact_structure,
)
from tools.estate_census.redaction import redact_text
from tools.estate_census.reporter import (
    ESTATE_BEFORE_ENV,
    LABEL_ENV,
    OUT_JSON_ENV,
    OUT_XML_ENV,
)
from tools.estate_census.watermarks import load_roster, measure

#: The repository root, resolved from THIS FILE rather than the working
#: directory, so the instrument behaves the same run from anywhere. A census
#: invoked from a chunk script in another directory is the ordinary case.
REPO_ROOT = Path(__file__).resolve().parents[2]

#: The declared store roster shipped beside the instrument. Names environment
#: variables, never values, which is what lets it be reviewed in the repository
#: while the credential stays out of it.
DEFAULT_ROSTER = REPO_ROOT / "tools" / "estate_census" / "curated_stores.json"


def _watermarks(args: argparse.Namespace) -> int:
    roster = load_roster(Path(args.roster))
    if roster is None:
        print(f"INDETERMINATE — store roster unreadable at {args.roster}", file=sys.stderr)
        return EXIT_CODES[INDETERMINATE]
    measured = measure(roster)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(measured, indent=2, sort_keys=True) + "\n")
    unmeasured = sorted(key for key, record in measured.items() if record.get("error"))
    print(f"measured {len(measured)} store(s) -> {args.out}")
    for key in unmeasured:
        # `_safe_error` already redacted this at the source. Redacted AGAIN here
        # deliberately, because Dave's requirement covers the case this file cannot
        # see: *"even if a future measurement provider returns one."* A console line
        # is unrecoverable once printed.
        print(f"  UNMEASURED {key}: {redact_text(measured[key]['error'])}")
    # An unmeasured store is reported but does not fail here: the operator may be
    # measuring a subset deliberately. The CLASSIFIER refuses it, which is the
    # right place — a missing position invalidates the comparison, not the read.
    return 0


def _capture(args: argparse.Namespace) -> int:
    """Run pytest under the census reporter, and redact the log we keep.

    The log matters as much as the bundle. pytest's own console output carries a
    credential verbatim — measured — and nothing can change that, so the census
    captures that output and redacts it before writing. Dave's list of artifacts
    that may never carry a credential names *"generated logs"* beside the XML for
    this reason.
    """
    env = dict(os.environ)
    env[OUT_JSON_ENV] = str(Path(args.out_json).resolve())
    if args.out_xml:
        env[OUT_XML_ENV] = str(Path(args.out_xml).resolve())
    if args.estate_before:
        env[ESTATE_BEFORE_ENV] = str(Path(args.estate_before).resolve())
    env[LABEL_ENV] = args.label
    env["PYTHONPATH"] = os.pathsep.join(
        [str(REPO_ROOT), str(REPO_ROOT / "src"), str(REPO_ROOT / "runtime")]
        + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else [])
    )
    # A same-length source mutation inside one mtime second loads STALE bytecode,
    # because CPython validates a .pyc on (mtime-seconds, size) alone. A census
    # that follows a severing must not read the pre-severing bytes.
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    command = [
        sys.executable,
        "-B",
        "-m",
        "pytest",
        "-p",
        "no:cacheprovider",
        "-p",
        "tools.estate_census.reporter",
        "--continue-on-collection-errors",
        *args.pytest_args,
    ]
    done = subprocess.run(
        command, cwd=REPO_ROOT, env=env, capture_output=True, text=True, check=False,
        timeout=args.timeout,
    )
    if args.log:
        Path(args.log).parent.mkdir(parents=True, exist_ok=True)
        Path(args.log).write_text(
            (redact_text(done.stdout) or "") + "\n" + (redact_text(done.stderr) or "") + "\n"
        )
    print(f"pytest exit={done.returncode}  bundle={args.out_json}  log={args.log or '(none)'}")
    if not Path(args.out_json).is_file():
        print("INDETERMINATE — the reporter wrote no bundle", file=sys.stderr)
        return EXIT_CODES[INDETERMINATE]
    return 0


def _attach_estate(args: argparse.Namespace) -> int:
    bundle = read_json(Path(args.bundle))
    if bundle is None:
        print(f"INDETERMINATE — bundle unreadable at {args.bundle}", file=sys.stderr)
        return EXIT_CODES[INDETERMINATE]
    try:
        after = json.loads(Path(args.after).read_text())
    except (OSError, ValueError):
        print(f"INDETERMINATE — after-measurement unreadable at {args.after}", file=sys.stderr)
        return EXIT_CODES[INDETERMINATE]
    # REPAIR 3. This is the one door into the primary bundle that does not pass
    # through `build`, so it carries its own generation boundary. Both sides are
    # walked, not only the one being attached: an `estate.before` that arrived from
    # an older bundle or an externally produced watermark file would otherwise
    # bypass the boundary entirely, which is the same omission this repair closes
    # on the attach side.
    estate = bundle.setdefault("estate", {})
    estate["after"] = redact_structure(after)
    if "before" in estate:
        estate["before"] = redact_structure(estate["before"])
    bundle["kind"], bundle["version"] = BUNDLE_KIND, BUNDLE_VERSION
    Path(args.bundle).write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n")
    print(f"attached after-measurement of {len(after)} store(s) to {args.bundle}")
    return 0


def _classify(args: argparse.Namespace) -> int:
    base, base_why = read_json_with_reason(Path(args.base))
    candidate, candidate_why = read_json_with_reason(Path(args.candidate))
    verdict = classify(
        base,
        candidate,
        base_credential=credential_in_file(Path(args.base)),
        candidate_credential=credential_in_file(Path(args.candidate)),
        declared_chunks=tuple(args.declared_chunk),
        reported_chunks=tuple(args.reported_chunk),
        base_unreadable_reason=base_why,
        candidate_unreadable_reason=candidate_why,
    )
    report = render(verdict)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(report)
    if args.out_json:
        # The MACHINE-READABLE verdict. Dave's instruction: expose reason codes,
        # not merely human text, so a caller cannot be broken by a rewording and
        # a report can be audited for WHICH cause fired.
        Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out_json).write_text(json.dumps(verdict.as_dict(), indent=2, sort_keys=True) + "\n")
    print(report)
    return verdict.exit_code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m tools.estate_census")
    subparsers = parser.add_subparsers(dest="command", required=True)

    water = subparsers.add_parser("watermarks", help="measure declared store positions, read-only")
    water.add_argument("--roster", default=str(DEFAULT_ROSTER))
    water.add_argument("--out", required=True)
    water.set_defaults(handler=_watermarks)

    capture = subparsers.add_parser("capture", help="run pytest under the census reporter")
    capture.add_argument("--out-json", required=True)
    capture.add_argument("--out-xml", default="")
    capture.add_argument("--estate-before", default="")
    capture.add_argument("--log", default="")
    capture.add_argument("--label", default="")
    capture.add_argument("--timeout", type=float, default=3600.0)
    capture.add_argument("pytest_args", nargs=argparse.REMAINDER)
    capture.set_defaults(handler=_capture)

    attach = subparsers.add_parser("attach-estate", help="attach an after-measurement to a bundle")
    attach.add_argument("--bundle", required=True)
    attach.add_argument("--after", required=True)
    attach.set_defaults(handler=_attach_estate)

    verdict = subparsers.add_parser("classify", help="classify a candidate against a base")
    verdict.add_argument("--base", required=True)
    verdict.add_argument("--candidate", required=True)
    verdict.add_argument("--declared-chunk", action="append", default=[])
    verdict.add_argument("--reported-chunk", action="append", default=[])
    verdict.add_argument("--out", default="")
    verdict.add_argument("--out-json", default="", help="machine-readable verdict with reason codes")
    verdict.set_defaults(handler=_classify)

    args = parser.parse_args(argv)
    handler = args.handler
    return int(handler(args))


if __name__ == "__main__":
    sys.exit(main())
