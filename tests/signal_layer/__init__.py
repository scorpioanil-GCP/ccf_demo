# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""Unit suites for the L1 Signal Layer contracts and ingress adapters.

Named ``signal_layer`` rather than ``signal`` deliberately: ``tests/`` is on
``sys.path``, so a package called ``signal`` here would shadow the standard
library module of that name for the whole session — and ``asyncio`` and
``subprocess`` both import it, which would break the cross-process suite in a
way whose cause is nowhere near its symptom.
"""
