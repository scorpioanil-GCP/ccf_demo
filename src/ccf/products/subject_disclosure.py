"""Which subjects a principal is not told about, decided before anything is fetched (SEC-020 Q8).

SDK-defined (CLAUDE.md §11); the ruling of record is ``D-IMPL-378``, Dave,
2026-10-07 19:31 MST, Q8 (a): *"Require early withholding for affected
composites. Make it an enforced policy decision before subject-dependent
fetches, child resolution or scoring. It cannot depend on learning whether the
subject exists."* SEC-020 stays OPEN.

A projection that withholds a subject from a principal says so with the typed
signal on :class:`~ccf.projection.plan.ProjectionOutput` — but only after its
plan has run, by which time the question has been asked of the deployment's
sources and of a composite's children about that subject. What they wrote and
answered, a rendering after the plan cannot undo
(``src/ccf/products/resolver.py::GovernedResolver``). The early decision moves
the "not told" determination ahead of all of it, and makes it a DECLARATION the
SDK interprets rather than code it runs: :class:`SubjectDisclosurePolicy` is
data, and :meth:`SubjectDisclosurePolicy.discloses` reads the asked identifier,
the already-resolved perspective and the declared sets, and nothing else — no
fabric, no source, no store. So the decision is the same for a subject the
source holds and for one it does not, by construction.

When the policy does not disclose the asked subject,
:meth:`~ccf.products.resolver.GovernedResolver.__call__` asks every
subject-dependent step about :attr:`SubjectDisclosurePolicy.undisclosed_subject`
IN PLACE OF the subject — an identifier the deployment declares names nothing
in any of its sources, children or fabrics — so each step does what it does for
any identifier that names nothing, and the product is computed once along that
path. The deployment's own projection must withhold the same subjects
(:class:`~ccf.products.resolver.UndisclosedSubjectAnswered` otherwise).

Values stay out of code (CINV-01, CLAUDE.md §11): this module declares shape
only — no principal, no role, no subject and no stand-in is named here.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import model_validator

from ccf.contracts.base import CCFContract
from ccf.products.request import SUBJECT_FLOOR_V1
from ccf.projection.plan import Perspective

__ccf_mode__ = "algorithmic"

__all__ = ["SubjectDisclosurePolicy"]


class SubjectDisclosurePolicy(CCFContract):
    """The subjects a principal is not told about, and the identifier asked in their place.

    Attributes:
        undisclosed_subject: The identifier every subject-dependent step is
            asked about in place of a subject this policy does not disclose.
            The deployment's statement that it names nothing in any of its
            sources, its children's sources or its fabrics — and, because it
            reaches the same acquisition seam any asked subject does, it lies
            inside :data:`~ccf.products.request.SUBJECT_FLOOR_V1` and is none
            of the subjects it stands in for. A source that treats it
            differently from any identifier it does not hold — an error for an
            unfamiliar shape, say — is a deployment that has declared the
            wrong stand-in.
        by_principal: Principal identifier to the subjects not disclosed to
            it, read off the resolved :class:`~ccf.projection.plan.Perspective`.
            Stated, never defaulted: an empty mapping is the positive "no
            principal is denied by name".
        by_role: Role to the subjects not disclosed to it, stated likewise. A
            subject is not disclosed when either set for the perspective names
            it.
    """

    undisclosed_subject: str
    by_principal: Mapping[str, frozenset[str]]
    by_role: Mapping[str, frozenset[str]]

    @model_validator(mode="after")
    def _the_stand_in_is_admissible(self) -> SubjectDisclosurePolicy:
        if not SUBJECT_FLOOR_V1.fullmatch(self.undisclosed_subject):
            raise ValueError(
                "undisclosed_subject lies outside the subject floor every asked"
                " subject is held to, and it reaches the same acquisition seam"
                " (SEC-020, Q8)"
            )
        for subjects in (*self.by_principal.values(), *self.by_role.values()):
            if self.undisclosed_subject in subjects:
                raise ValueError(
                    "undisclosed_subject is itself named as a subject this policy"
                    " does not disclose; the stand-in must name nothing"
                    " (SEC-020, Q8)"
                )
        return self

    def discloses(self, *, subject: str, perspective: Perspective) -> bool:
        """Whether ``subject`` may be told to the principal ``perspective`` resolved.

        Pure over the asked identifier, the perspective and this declaration:
        no clock, no registry, no fabric, no source.
        """
        withheld = self.by_principal.get(perspective.principal_id, frozenset()) | self.by_role.get(
            perspective.role, frozenset()
        )
        return subject not in withheld
