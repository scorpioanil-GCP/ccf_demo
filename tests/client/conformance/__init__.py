# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""The adapter conformance suite — one parity gate, parameterized over transports.

``D-15``. An adapter is **official when it passes this suite**, not when it
demos. The four properties live in :mod:`tests.client.conformance.suite`, which
names no transport; a binding module supplies one
:class:`~tests.client.conformance.suite.AdapterSubject` and calls the same
assertion functions every other transport is held to.

The controls in ``test_the_suite_fires.py`` are this package's substance rather
than its epilogue: with one real transport bound, every cross-adapter comparison
would otherwise degenerate into comparing something to itself, and *a suite that
cannot fail is worse than no suite* because the next adapter will trust it.
"""
