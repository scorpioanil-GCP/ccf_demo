# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""Re-export of :mod:`ccf.skills.wire_arguments` under its first, private name.

``TP-04`` / ``SEC353-J-01`` (``D-IMPL-361``). The undeclared-argument rule was
introduced here, privately, for its two first consumers (the ADK adapter and
the MCP tenant guard). The Task 5 follow-on promoted it to the public module
:mod:`ccf.skills.wire_arguments` and widened it to the whole argument rule;
this name stays so those imports hold. New code imports the public module.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from ccf.skills.wire_arguments import (
    ArgumentRefused,
    UndeclaredArgumentRefused,
    refuse_undeclared_arguments,
    undeclared_arguments,
)

__ccf_mode__ = "algorithmic"

__all__ = [
    "ArgumentRefused",
    "UndeclaredArgumentRefused",
    "refuse_undeclared_arguments",
    "undeclared_arguments",
]
