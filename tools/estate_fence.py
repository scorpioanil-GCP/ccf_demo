"""`python -m tools.estate_fence` — refuse a curated write destination BEFORE a run.

`D-IMPL-358` step 15 ruling (Dave, 2026-10-01): *"the curated-estate fence is NOT
deliberately pytest-scoped. 'Nothing seeds .76, ever' governs. `make example-s1-00`
and `make example-s1-01` must refuse a parsed curated host before they transact."*

**The close panel's finding this closes.** The write fence existed only inside
pytest: the symbols ``refuse_to_write_the_curated_estate`` and
``CCF_CURATED_ESTATE_HOSTS`` appeared in ZERO files under ``src/``, ``runtime/``,
``examples/``, ``tools/`` or the ``Makefile``, while two documented operator
targets took their write destination from an operator-exported ``CCF_TEST_*``
value that ``?=`` lets win and called no fence on the path. That is the exact
shape of the accident that left 27 permanent ``ccf:cp04-*`` ledgers and 134
permanent transactions on the curated server. Fluree is append-only, so each is
forever.

**THE SAME PARSER, BY IMPORT RATHER THAN BY COPY.** Every classification decision
here is made by :mod:`tests.examples.estate_guard` — host-level, both PostgreSQL
serializations through ``psycopg.conninfo.conninfo_to_dict``, the Mongo multi-host
authority form, fail-closed on anything it cannot parse, and no port rule. This
module adds a command line and NOT ONE LINE of parsing. A second parser is a
second set of edge cases: the panel measured four alternate spellings the existing
one already accepts, and a copy would have to be fixed twice to fix that once.

Importing the test helper from a build gate is deliberate and is the lesser of two
evils. The alternative is a duplicate parser whose drift nobody would notice until
it mattered. If the helper ever moves to ``src/``, this import follows it and
nothing else here changes.

**What it refuses.** Any of the named variables whose PARSED destination reaches a
host declared in ``CCF_CURATED_ESTATE_HOSTS`` (default ``192.168.4.76``). An unset
variable is NOT a refusal: unset means the deployment's own default applies, which
for the disposable set is localhost or a throwaway container. An UNPARSEABLE value
IS a refusal, because a destination nobody has established must never read as safe.

Exit codes: ``0`` nothing named a curated host; ``1`` something did, and the run
must not proceed; ``2`` the fence itself could not run.
"""

from __future__ import annotations

import argparse
import os
import sys

#: The parser, imported rather than restated. See the module docstring.
from tests.examples.estate_guard import (  # noqa: E402
    CURATED_HOSTS_ENV,
    DEFAULT_CURATED_HOSTS,
    refuse_to_write_the_curated_estate,
)

#: The write-target variables a `make example-*` target can carry. Named, never
#: globbed: a glob over the environment would fence a READ variable too, and the
#: curated estate is meant to be read — `CCF_CP_*` targets point at it by design.
WRITE_TARGET_VARS: tuple[str, ...] = (
    # The disposable set the fence's own message names.
    "CCF_TEST_FLUREE_URL",
    "CCF_TEST_POSTGRES_DSN",
    "CCF_TEST_MONGO_URI",
    # s1-00's write profile reads this one; `provision.py` derives it from
    # `CCF_TEST_POSTGRES_DSN` or from a container it starts, so BOTH are checked —
    # fencing only the operator's input would miss a derived destination.
    "CCF_S1_00_POSTGRES_DSN",
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m tools.estate_fence",
        description=(
            "Refuse a curated write destination before a run transacts."
            " Reads the named environment variables and classifies each with the"
            " pytest fence's own parser."
        ),
    )
    parser.add_argument(
        "--var",
        action="append",
        default=[],
        metavar="NAME",
        help=(
            "an environment variable holding a write destination; repeatable."
            f" Defaults to the {len(WRITE_TARGET_VARS)} write-target variables."
        ),
    )
    parser.add_argument("--label", default="", help="what is about to run, for the message")
    arguments = parser.parse_args(argv)

    names = tuple(arguments.var) or WRITE_TARGET_VARS
    present = {name: os.environ[name] for name in names if os.environ.get(name)}
    try:
        refuse_to_write_the_curated_estate(*present.values())
    except RuntimeError as refused:
        where = f" before {arguments.label}" if arguments.label else ""
        print(
            f"ESTATE FENCE REFUSED{where}.\n\n{refused}\n\n"
            "Checked: " + ", ".join(sorted(present)) + ".\n"
            "Nothing has been transacted. The run stopped before it opened a"
            " writer.",
            file=sys.stderr,
        )
        return 1
    # Say what was checked even when clear: a gate that prints nothing is
    # indistinguishable from a gate that did not run.
    checked = ", ".join(sorted(present)) if present else "(none set — defaults apply)"
    print(f"estate fence: clear. Checked {checked}. Curated hosts from {CURATED_HOSTS_ENV}"
          f" (default {DEFAULT_CURATED_HOSTS}).")
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised through the Makefile
    raise SystemExit(main())
