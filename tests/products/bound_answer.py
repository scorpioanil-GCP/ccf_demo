"""An honest answer to the question asked, for a hand-built ``ChildCandidate`` (`SEC-025`).

`SEC-025` (Q16) made the composite admission gate hold every ``local-dispatch``
and ``mcp`` child's answered subject to the question its composite asked
(``ccf.products.composite::CompositeAdmissionGate.hold_answer_to_question``).
A test that builds a candidate by hand, to exercise some OTHER check, states
that the child answered the question asked — or the gate rightly refuses it
``question-mismatch`` before the check under test is reached.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ccf.products.child_resolver import ChildQuestion
from ccf.products.door import AnsweredQuestion, WireRequest

#: The one subject a hand-built candidate is asked about and answers.
SUBJECT = "fixture-subject"
INTENT = "fixture-intent"
FRESHNESS = "fixture-freshness"


def answered_as_asked(product_class: str, asked_at: datetime) -> dict[str, Any]:
    """``ChildCandidate`` keywords: the question asked, and the door's echo of it."""
    return {
        "asked_question": ChildQuestion(
            subject=SUBJECT, intent=INTENT, freshness=FRESHNESS, parameters={}
        ),
        "question_echo": WireRequest(
            product_id=product_class, parameters={}, temporal_boundary=asked_at
        ),
        "answered_question": AnsweredQuestion(
            subject=SUBJECT, intent=INTENT, freshness=FRESHNESS, asked_at=asked_at
        ),
    }
