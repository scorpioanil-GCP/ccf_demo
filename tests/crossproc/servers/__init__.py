# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""Child server entry points for the cross-process fixture (D-17).

One module per server a cross-process proof needs. Each is runnable as
``python -m`` / ``python <path>`` and, on start, prints ``READY {port}`` to
stdout — the handshake ``crossproc.conftest`` blocks on. Nothing here starts a
server at import time, because the parent imports these modules to reuse their
builders.
"""
