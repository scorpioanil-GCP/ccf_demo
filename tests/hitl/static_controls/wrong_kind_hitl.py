"""STATIC NEGATIVE CONTROL — D-IMPL-353 §9, the HITL transport handle.

Meant to FAIL mypy. Checked on its own by ``tests/hitl/test_capability_static.py``,
which asserts the exact diagnostics below. No suppression comment and no cast:
a handler holding a queue-read capability cannot hand it to ``submit``, and a
handler holding a submit capability cannot hand it to ``view``, without
silencing the type checker — which §4's lint refuses.

If this file ever type-checks clean, the static tooth is gone at this handle.
"""

from __future__ import annotations

from ccf.hitl.transport import HitlActionSubmission, InMemoryHitlTransport
from ccf.authz.capability import Authorized, HitlQueueRead, HitlSubmit


def a_reader_tries_to_submit(
    transport: InMemoryHitlTransport,
    read: Authorized[HitlQueueRead],
    submission: HitlActionSubmission,
) -> None:
    transport.submit(read, submission=submission)  # WRONG-KIND-1


def a_submitter_tries_to_read(
    transport: InMemoryHitlTransport, submit: Authorized[HitlSubmit]
) -> None:
    transport.view(submit)  # WRONG-KIND-2
