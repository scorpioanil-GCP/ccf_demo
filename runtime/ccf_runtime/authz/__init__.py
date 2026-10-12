# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""Tenant authorization for the Experience-Layer doors (HARD-04).

SDK-defined (CLAUDE.md §8.2/§8.3 — an extension beyond the whitepaper, and
it says so); D-IMPL-68. The scope mapping is a versioned Control Plane
policy artifact (:mod:`ccf_runtime.authz.artifact`); the authorizer seam
and its reference interpreter (:mod:`ccf_runtime.authz.protocol`) are
imported by both doors; the shared action-ID vocabulary lives in
:mod:`ccf_runtime.authz.refusals`. Authorization is enforced at the doors
and never sinks below the door trust boundary (D-IMPL-68 ruling text).

The SDK ships grammar and matching mechanism only: no scope string, tenant
name, or mapping value appears in this package (CINV-01; CLAUDE.md §11).

Algorithmic module (CINV-03).
"""

__ccf_mode__ = "algorithmic"
