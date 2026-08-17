"""The four parity properties, asserted over a collection of adapters.

``D-15``, from ``docs/superpowers/specs/2026-08-15-ccf-client-design.md`` §6:
*one shared adapter conformance suite, written once and parameterized over
adapters.* This module is that suite. It is the CI enforcement of the "value
evaporates" concern and is the same class of gate as the
composition-preservation tests.

**This module names no transport.** It imports nothing from
``ccf.client.adapters``, holds no scheme string, and reaches every transport
through :class:`AdapterSubject` — a name, a way to connect, and a way to break
the connection. Adding a transport is adding one subject; it is never adding an
assertion, because an assertion added beside a transport is an assertion that
transport was shaped by.

Why the comparison is over a *collection* from the first line
--------------------------------------------------------------
With a single subject bound, a cross-adapter comparison has nothing to compare
against and would pass while checking nothing — the exact defect class this
phase has shipped four times, where *a check stops checking without going red*.
Two things are done about it here, and both are structural:

* every leg does per-subject work that is non-vacuous with one subject — a
  served result must be served and every declared field must be *readable*, a
  refused result must actually refuse, and a broken transport must actually
  raise;
* ``test_the_suite_fires.py`` runs these same functions over a deliberately
  divergent second subject and asserts each one **fails**. The controls call
  the functions below, never a copy of them: a control that tested a copy would
  prove the copy fires.

The fields compared are derived, never hand-picked
---------------------------------------------------
:func:`result_fields` reads :class:`~ccf.client.result.Result`'s own declared
properties and cross-checks them against the two tuples ``result.py`` publishes.
A hand-written list is how *"a parity test that compares only ``payload`` will
stay green"* happens; a derived list means a field added next year joins the
comparison without an edit here, and a derivation that silently returned nothing
is refused rather than passed.

What "break the transport" means, and why the hook may not raise
----------------------------------------------------------------
:attr:`AdapterSubject.break_transport` is handed a deployment root **it owns**
and must return an *adapter of the same type as the healthy one*, pointed at a
substrate that has been damaged. It must not raise
:class:`~ccf.client.errors.TransportError` itself: a hook that raised the very
exception the leg expects would prove only that the hook raises. For an
in-process transport, damaging the substrate means removing what the address
needs in order to name a deployment at all; for a socket transport it means
closing the pipe. Whatever the adapter *does* with the damage is what
:func:`assert_wire_failure_parity` measures, and the same-type check is asserted
rather than trusted.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Final

from ccf.client.client import ProductClient
from ccf.client.errors import RefusedResultError, TransportError
from ccf.client.result import GUARDED_FIELDS, PRE_ASSEMBLY_FIELDS, Result
from ccf.client.wire import TransportAdapter

__all__ = [
    "REFUSAL_VIEW_KEYS",
    "AdapterSubject",
    "Question",
    "assert_decision_instant_is_auditable",
    "assert_guard_holds",
    "assert_guard_parity",
    "assert_one_instant_is_one_decision",
    "assert_one_question_is_one_address",
    "assert_refusal_parity",
    "assert_served_parity",
    "assert_two_parameters_are_two_addresses",
    "assert_wire_failure_parity",
    "result_fields",
]


#: How a subject is handed a deployment to speak to. The suite provisions the
#: root; the transport decides what to do with it.
AdapterFactory = Callable[[Path], TransportAdapter]

#: How the suite obtains a fresh, already-populated deployment root. Named per
#: call so a subject and its broken twin never share a substrate — and so the
#: legs stay honest about which root produced which answer.
Provision = Callable[[str], Path]

#: The field on a served :class:`~ccf.client.result.Result` whose omission from
#: a parity comparison is the single most likely way this gate goes quiet.
#: Named so :func:`result_fields` can refuse a derivation that lost it.
CONTENT_ADDRESS: Final[str] = "content_address"

#: The members of a refusal that must be identical across adapters (``D-15``
#: row 2): the reason, what it names, its unflattened kind, and the request
#: identity it refused. Spelled as the paths a reader would type.
REFUSAL_VIEW_KEYS: Final[tuple[str, ...]] = (
    "refused",
    "refusal.reason",
    "refusal.key",
    "refusal.kind",
    "refusal.request",
)


@dataclass(frozen=True, kw_only=True)
class AdapterSubject:
    """One transport under test — a name, a connection, and a way to break it.

    Attributes:
        name: How this transport is reported in a failure. Also the name the
            suite provisions its deployment root under, so a message names a
            directory a reader can go and look at.
        connect: Build a healthy adapter against a provisioned deployment root.
        break_transport: Build an adapter of the **same type** against a root
            whose substrate has been damaged. The root handed to this callable
            is the subject's to destroy; the healthy leg is given its own. See
            the module docstring for why this callable may not raise.
    """

    name: str
    connect: AdapterFactory
    break_transport: AdapterFactory


@dataclass(frozen=True, kw_only=True)
class Question:
    """One question, asked identically of every subject.

    Attributes:
        product_id: The product class every subject is asked for.
        parameters: The class-declared remainder of the question.
        as_of: The instant to ask against, or ``None`` for the producing
            deployment's own decision instant (``D-04``).
    """

    product_id: str
    parameters: Mapping[str, Any]
    as_of: datetime | None = None


def result_fields() -> tuple[str, ...]:
    """Every field a :class:`~ccf.client.result.Result` declares, derived.

    Read off the class rather than written down, so a seventh field next year
    joins the parity comparison without an edit in this module. The derivation
    is then cross-checked three ways, because a *derivation* that silently
    produced a short list is the same defect as a hand-written list that was
    never updated:

    * it is non-empty — an empty list would make every comparison below pass
      while comparing nothing;
    * it equals ``PRE_ASSEMBLY_FIELDS | GUARDED_FIELDS`` exactly, the partition
      ``result.py`` publishes and ``tests/client/test_result_guard.py`` holds
      the class to;
    * it contains :data:`CONTENT_ADDRESS`, whose absence is the specific way
      this gate would go quiet while still looking like a parity test.

    Raises:
        AssertionError: any of the three cross-checks failed.
    """
    declared = tuple(
        name
        for name, member in vars(Result).items()
        if isinstance(member, property) and not name.startswith("_")
    )
    if not declared:
        raise AssertionError(
            "no declared field was derived from `ccf.client.result.Result`, so"
            " every parity comparison below would compare nothing and pass —"
            " the derivation in `result_fields()` no longer matches how"
            " `Result` declares its members"
        )
    partition = set(PRE_ASSEMBLY_FIELDS) | set(GUARDED_FIELDS)
    if set(declared) != partition:
        raise AssertionError(
            "the fields derived from `ccf.client.result.Result` are not the"
            " partition `result.py` publishes — derived"
            f" {sorted(declared)}, published {sorted(partition)}. A field on"
            " neither side of the assembly boundary is a field no gate covers"
        )
    if CONTENT_ADDRESS not in declared:
        raise AssertionError(
            "the derived field list carries no `content_address`, so a"
            " transport agreeing on `payload` and disagreeing on the address"
            " would pass this suite — that is the one omission `D-15` row 1"
            " exists to forbid"
        )
    return declared


# ---------------------------------------------------------------------------
# The shared machinery — one comparison, one ask, used by every leg.
# ---------------------------------------------------------------------------


def _require_subjects(subjects: Sequence[AdapterSubject], *, leg: str) -> None:
    """Refuse a leg handed no adapters, rather than iterating over nothing.

    An empty collection is the cheapest way for a parity gate to go green
    without checking anything, and Python's own defaults will not report it:
    ``for subject in ():`` is a silent success. So it is refused by name.
    """
    if not subjects:
        raise AssertionError(
            f"the `{leg}` leg was handed no adapters — an empty collection"
            " iterates to a silent success, which is a parity gate reporting"
            " green while comparing nothing"
        )


def _ask(subject: AdapterSubject, root: Path, question: Question) -> Result:
    """Ask ``question`` through ``subject``'s transport, at the client seam.

    Through :class:`~ccf.client.client.ProductClient` and never through the
    adapter directly, because ``D-12`` puts ``Result`` construction and the
    codec's three checks inside the client — a leg that called ``adapter.ask``
    would be asserting parity of the *wire*, one layer below where a caller
    lives.
    """
    return ProductClient(
        product_id=question.product_id, adapter=subject.connect(root)
    ).ask(parameters=question.parameters, as_of=question.as_of)


def _ask_each(
    subjects: Sequence[AdapterSubject], *, provision: Provision, question: Question
) -> dict[str, Result]:
    """Ask every subject the same question, each against its own deployment.

    Each subject gets a **separate** provisioned root. Sharing one would make
    parity a claim about one graph read twice rather than about two transports
    answering independently, and it is not open to the suite anyway: a second
    boot against one graph is a second writer.
    """
    answers: dict[str, Result] = {}
    for subject in subjects:
        if subject.name in answers:
            raise AssertionError(
                f"two subjects answer to the name `{subject.name}` — a parity"
                " report that cannot tell them apart names the wrong transport"
                " when it fails"
            )
        answers[subject.name] = _ask(subject, provision(subject.name), question)
    return answers


def _assert_views_agree(
    views: Mapping[str, Mapping[str, Any]], *, leg: str
) -> None:
    """Hold every subject's view of an answer to the first subject's, key by key.

    The one comparison in this module. Every leg builds a view and calls this,
    so a property proven of this function holds for every leg — and the
    controls exercise it through the legs rather than around them.

    Differences are collected rather than raised on the first, because a report
    naming one field of five that moved sends a reader looking for one cause.
    """
    if not views:
        raise AssertionError(
            f"the `{leg}` leg built no views to compare, so there was nothing"
            " for this comparison to hold to anything"
        )
    names = list(views)
    reference = names[0]
    keys = tuple(views[reference])
    if not keys:
        raise AssertionError(
            f"the `{leg}` leg built an empty view of `{reference}` — comparing"
            " zero keys across any number of adapters is a comparison that"
            " cannot fail"
        )
    differences: list[str] = []
    for other in names[1:]:
        if set(views[other]) != set(keys):
            raise AssertionError(
                f"the `{leg}` leg built different views of `{reference}` and"
                f" `{other}` — compared keys {sorted(keys)} against"
                f" {sorted(views[other])}, so the two were never held to the"
                " same standard"
            )
        for key in keys:
            baseline = views[reference][key]
            value = views[other][key]
            if value != baseline:
                differences.append(
                    f"`{key}`: {reference} answered {baseline!r} and {other}"
                    f" answered {value!r}"
                )
    if differences:
        joined = "; ".join(differences)
        raise AssertionError(
            f"the `{leg}` leg found the transports disagreeing — {joined}."
            " `D-15` requires the same question to produce the same answer"
            " whichever transport carried it"
        )


def _view_of(result: Result, fields: Sequence[str]) -> dict[str, Any]:
    """Read ``fields`` off a result, in order, as the value the leg compares."""
    return {field: getattr(result, field) for field in fields}


def _refusal_view(result: Result) -> dict[str, Any]:
    """The members of a refusal `D-15` row 2 holds identical across adapters."""
    refusal = result.refusal
    if refusal is None:  # pragma: no cover - callers check `refused` first
        raise AssertionError("a refused result carried no refusal")
    return {
        "refused": result.refused,
        "refusal.reason": refusal.reason,
        "refusal.key": refusal.key,
        "refusal.kind": refusal.kind,
        "refusal.request": refusal.request,
    }


# ---------------------------------------------------------------------------
# D-15 row 1 — same question, same instant, same answer and same address.
# ---------------------------------------------------------------------------


def assert_served_parity(
    subjects: Sequence[AdapterSubject],
    *,
    provision: Provision,
    question: Question,
) -> None:
    """The same question at the same instant answers identically everywhere.

    Every **declared** field of :class:`~ccf.client.result.Result` is compared,
    the content address among them. Comparing ``payload`` alone is the named
    trap: a transport that agreed on the payload and disagreed on the address
    would pass a narrower test while being useless for the audit story the
    client exists to serve.

    Non-vacuous with one subject: each answer must actually be served, and
    every declared field must be *readable* on it — which is the guard's
    converse and is not asserted anywhere else.

    Raises:
        AssertionError: a subject refused, a declared field was unreadable on a
            served result, or two transports disagreed about any field.
    """
    _require_subjects(subjects, leg="served parity")
    fields = result_fields()
    answers = _ask_each(subjects, provision=provision, question=question)
    views: dict[str, Mapping[str, Any]] = {}
    for name, result in answers.items():
        if result.refused:
            reason = result.refusal.reason if result.refusal is not None else "?"
            raise AssertionError(
                f"`{name}` refused the served-parity question with"
                f" `{reason}` — this leg compares two served answers, so a"
                " refusal here means the question or the deployment is wrong"
                " and the comparison never happened"
            )
        views[name] = _view_of(result, fields)
    _assert_views_agree(views, leg="served parity")


def assert_one_question_is_one_address(
    subjects: Sequence[AdapterSubject],
    *,
    provision: Provision,
    question: Question,
) -> None:
    """One question, one content address, whichever transport carried it.

    ``D-23``'s cross-adapter half, and the property
    ``tests/examples/test_s1_00_output.py::test_the_same_question_is_stable``
    asserts producer-side. Stated as its own leg because it is the half a
    reader checks when two transports disagree, and it delegates to the same
    comparison every other leg uses rather than restating it.
    """
    _require_subjects(subjects, leg="one address")
    answers = _ask_each(subjects, provision=provision, question=question)
    views: dict[str, Mapping[str, Any]] = {}
    for name, result in answers.items():
        if result.refused:
            raise AssertionError(
                f"`{name}` refused, so it produced no content address for this"
                " leg to hold to anything"
            )
        views[name] = _view_of(result, (CONTENT_ADDRESS,))
    _assert_views_agree(views, leg="one address")


# ---------------------------------------------------------------------------
# D-23 — the existing property, on its new path.
# ---------------------------------------------------------------------------


def assert_two_parameters_are_two_addresses(
    subjects: Sequence[AdapterSubject],
    *,
    provision: Provision,
    question: Question,
    other_parameters: Mapping[str, Any],
) -> None:
    """Two parameter values are two products, through every transport.

    **The existing property, new path.** Producer-side it is
    ``tests/examples/test_s1_00_output.py::test_two_thresholds_are_two_products``
    — *a Context Product is not a precalculated static object; the caller's
    number is part of the question, so it is part of the product's content
    address.* Plan ``17-08`` removes that module with its tree, so the property
    lands here first and is never unasserted in between.

    The address is checked **first** and the payloads second, and the ordering
    is load-bearing rather than stylistic. Two different payloads cannot share
    an address — the codec recomputes the address from the vessel's own bytes
    and refuses a wire that disagrees — so a payload check placed first would
    make the address check unreachable, which is a check that cannot fail
    dressed as a check. Second, the payload comparison is a live check of the
    remaining case: addresses that differ while the payloads are identical,
    which is what a deployment folding the caller's number into the vessel but
    not into the answer would produce.

    Both questions are asked through the **same** subject against the **same**
    deployment, so the only thing that moved is the caller's number.
    """
    _require_subjects(subjects, leg="two parameters")
    if question.parameters == other_parameters:
        raise AssertionError(
            "this leg was handed one parameter mapping twice, so it would"
            " compare a question against itself and report two addresses equal"
            " as a failure of a property nobody tested"
        )
    for subject in subjects:
        root = provision(subject.name)
        first = _ask(subject, root, question)
        second = _ask(
            subject,
            root,
            Question(
                product_id=question.product_id,
                parameters=other_parameters,
                as_of=question.as_of,
            ),
        )
        if first.refused or second.refused:
            raise AssertionError(
                f"`{subject.name}` refused one of the two questions, so this"
                " leg has fewer than two products to compare"
            )
        if first.content_address == second.content_address:
            raise AssertionError(
                f"`{subject.name}` gave two different parameter values one"
                f" content address, `{first.content_address}` — the caller's"
                " number is part of the question and therefore part of the"
                " product's address, and a transport where it is not is"
                " serving a precalculated object"
            )
        if first.payload == second.payload:
            raise AssertionError(
                f"`{subject.name}` gave two different parameter values two"
                " addresses and one payload — the caller's number reached the"
                " vessel without reaching the answer, so the address moved for"
                " a reason the caller cannot see in what it was handed"
            )


# ---------------------------------------------------------------------------
# D-15 row 2 — the same refusal, identically, everywhere.
# ---------------------------------------------------------------------------


def assert_refusal_parity(
    subjects: Sequence[AdapterSubject],
    *,
    provision: Provision,
    refusing_question: Question,
) -> None:
    """A question the class does not answer refuses identically everywhere.

    The reason, what it names, its unflattened kind and the request identity it
    refused are all compared. Dropping ``refusal.key`` from one transport's
    decode leaves ``reason`` intact and the governed "no" unattributable — so
    it is a difference this leg reports rather than a detail it tolerates.

    Raises:
        AssertionError: a subject answered rather than refused, or two
            transports refused differently.
    """
    _require_subjects(subjects, leg="refusal parity")
    answers = _ask_each(subjects, provision=provision, question=refusing_question)
    views: dict[str, Mapping[str, Any]] = {}
    for name, result in answers.items():
        if not result.refused:
            raise AssertionError(
                f"`{name}` answered the refusing question instead of refusing"
                " it — this leg compares two governed refusals, so a served"
                " answer here means the question is answerable and the"
                " comparison never happened"
            )
        views[name] = _refusal_view(result)
    _assert_views_agree(views, leg="refusal parity")


# ---------------------------------------------------------------------------
# D-15 row 3 — the fail-closed guard, on every adapter, per field.
# ---------------------------------------------------------------------------


def assert_guard_holds(result: object, *, subject: str) -> None:
    """Every post-assembly field raises on a refused result. Six, not one.

    ``D-08``. The names come from :data:`~ccf.client.result.GUARDED_FIELDS`, so
    a seventh guarded field is exercised here the day it is declared. Reading
    them by :func:`getattr` in a loop is what lets a control observe *which*
    names this function actually touched — one ``pytest.raises`` on ``payload``
    would license five unguarded fields, and no grep over this file could tell
    the difference between a name it exercises and a name it mentions.

    Takes an ``object`` rather than a ``Result`` deliberately: the recording
    stand-in in ``test_the_suite_fires.py`` is not a ``Result``, and it is how
    the claim *"every guarded name was accessed"* is measured rather than
    assumed.

    Raises:
        AssertionError: :data:`~ccf.client.result.GUARDED_FIELDS` is empty, or
            any guarded name handed back a value instead of raising.
    """
    if not GUARDED_FIELDS:
        raise AssertionError(
            "`ccf.client.result.GUARDED_FIELDS` is empty, so this leg would"
            " iterate over nothing and report a guard that does not exist as"
            " holding"
        )
    unguarded: list[str] = []
    for field in GUARDED_FIELDS:
        try:
            getattr(result, field)
        except RefusedResultError:
            continue
        unguarded.append(field)
    if unguarded:
        raise AssertionError(
            f"`{subject}` handed back {sorted(unguarded)} on a refused result"
            " instead of raising `RefusedResultError` — a post-assembly field"
            " read off a refusal is how a governed no becomes an empty answer"
            " three layers downstream"
        )


def assert_guard_parity(
    subjects: Sequence[AdapterSubject],
    *,
    provision: Provision,
    refusing_question: Question,
) -> None:
    """The fail-closed guard holds on every adapter, for every guarded name."""
    _require_subjects(subjects, leg="guard parity")
    answers = _ask_each(subjects, provision=provision, question=refusing_question)
    for name, result in answers.items():
        if not result.refused:
            raise AssertionError(
                f"`{name}` answered the refusing question, so this leg had no"
                " refused result to read a guarded field off"
            )
        assert_guard_holds(result, subject=name)


# ---------------------------------------------------------------------------
# D-15 row 4 — a broken wire is never a refusal.
# ---------------------------------------------------------------------------


def assert_wire_failure_parity(
    subjects: Sequence[AdapterSubject],
    *,
    provision: Provision,
    question: Question,
    refusing_question: Question,
) -> None:
    """Kill the transport and get a ``TransportError`` — never a refusal.

    ``D-10``/``D-15(d)``. The three cases stay three: a refusal is a value the
    fabric returned, a caller's negligence raises at the caller, and a wire
    that never spoke is a :class:`~ccf.client.errors.TransportError`. An
    adapter that catches its own connection error and synthesizes a refusal has
    reported *"the fabric said no"* when nothing was ever asked, and the caller,
    having branched correctly, records an audited refusal that never happened.

    Three things are asserted per subject, and the second and third are what
    stop this leg proving itself:

    * the broken transport raises ``TransportError`` and produces **no**
      ``Result``, refused or otherwise;
    * the break hook returned an adapter of the *same type* as the healthy one,
      so the leg is measuring a damaged substrate rather than a substituted
      object that raises on principle;
    * a genuine refusal through the **healthy** transport does *not* raise —
      without which "everything raises" would pass this leg.

    Raises:
        AssertionError: any of the three failed for any subject.
    """
    _require_subjects(subjects, leg="wire failure")
    for subject in subjects:
        healthy = subject.connect(provision(subject.name))
        broken = subject.break_transport(provision(f"{subject.name}-broken"))
        if type(broken) is not type(healthy):
            raise AssertionError(
                f"`{subject.name}` broke its transport by substituting a"
                f" `{type(broken).__name__}` for a"
                f" `{type(healthy).__name__}` — the hook must damage the"
                " substrate and leave the adapter alone, or this leg proves"
                " only that the substitute raises"
            )
        client = ProductClient(product_id=question.product_id, adapter=broken)
        try:
            produced = client.ask(
                parameters=question.parameters, as_of=question.as_of
            )
        except TransportError:
            pass
        else:
            state = "a refusal" if produced.refused else "a served product"
            raise AssertionError(
                f"`{subject.name}` answered a broken transport with {state}"
                " instead of raising `TransportError` — a wire that never spoke"
                " reported as a governed answer is the one inversion `D-10`"
                " exists to prevent"
            )
        refused = ProductClient(
            product_id=refusing_question.product_id, adapter=healthy
        ).ask(
            parameters=refusing_question.parameters, as_of=refusing_question.as_of
        )
        if not refused.refused:
            raise AssertionError(
                f"`{subject.name}` answered the refusing question through a"
                " healthy transport, so this leg never showed that a refusal"
                " and a broken wire are different — and a transport that raised"
                " on everything would have passed the check above"
            )


# ---------------------------------------------------------------------------
# DEF-17-07 — the decision instant a caller can audit and verify.
# ---------------------------------------------------------------------------


def assert_decision_instant_is_auditable(
    subjects: Sequence[AdapterSubject],
    *,
    provision: Provision,
    question: Question,
    refusing_question: Question,
) -> None:
    """A caller can recover *which instant answered*, and prove they recovered it.

    ``DEF-17-07``, mechanized here because Dave ruled that *"the conformance
    suite is exactly where what every adapter must expose identically gets
    mechanized"*. The question this leg answers with a measurement: **can a
    caller audit which instant the server resolved, using only what a**
    ``Result`` **already exposes?**

    :attr:`~ccf.client.result.Result.temporal_boundary` is the echo of the
    *question* and is ``None`` when the caller deferred to the server, which is
    correct and is exactly why the audit path is one level in:

    * on a **served** result, ``result.lineage.graph_snapshot_at`` is the
      temporal anchor of the graph state read — the instant that answered;
    * on a **refused** result, ``result.refusal.request.temporal_boundary`` is
      the resolved instant the refusal was reached at, which survives the
      assembly boundary because it is pre-assembly (``D-09``).

    Recovering a value proves nothing on its own, so the leg **verifies** it:
    asking the same question again pinned to the recovered instant must
    reproduce the identical content address. A transport reporting an instant
    it did not answer at fails that, and no amount of a well-formed datetime
    saves it.

    **This leg is per-subject, and a cross-subject comparison was removed from
    it** (``D-IMPL-149``, Dave, 2026-08-17). It used to end at
    ``_assert_views_agree(recovered, leg="decision instant")``, holding every
    subject's *recovered* instant to the first subject's. That demand and the
    refusal above contradict each other: asking with ``as_of=None`` is what
    makes the recovery non-trivial, and it is also what makes each subject read
    **its own clock**. Two in-process deployments — no MCP, no process boundary
    — were measured recovering instants **116 ms apart**, so the demand was not
    hard to satisfy under load; it was unsatisfiable in principle for any two
    subjects whatsoever. It was green only while a single subject was bound,
    which made it a comparison of one thing with itself. The cross-adapter half
    of ``DEF-17-07`` now lives in
    :func:`assert_one_instant_is_one_decision`, where the instant is an
    **input** and a comparison across subjects therefore means something.

    Raises:
        AssertionError: the question already pinned an instant (which would make
            the recovery trivial), a recovered instant was absent or naive, the
            pinned re-ask produced a different address, or a refusal named no
            instant it was reached at.
    """
    _require_subjects(subjects, leg="decision instant")
    if question.as_of is not None:
        raise AssertionError(
            "this leg asks with `as_of=None` on purpose — handed a question"
            " that already names its instant, it would recover the value it"
            " was given and prove nothing about what the server resolved"
        )
    for subject in subjects:
        root = provision(subject.name)
        served = _ask(subject, root, question)
        if served.refused:
            raise AssertionError(
                f"`{subject.name}` refused the served question, so this leg had"
                " no lineage to read an instant off"
            )
        if served.temporal_boundary is not None:
            raise AssertionError(
                f"`{subject.name}` echoed a temporal boundary for a question"
                " that named none — `Result.temporal_boundary` is the echo of"
                " the question, and a transport filling it in has answered a"
                " question the caller did not ask"
            )
        instant = served.lineage.graph_snapshot_at
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise AssertionError(
                f"`{subject.name}` reported a naive `graph_snapshot_at`, which"
                " names no instant a second party can pin to"
            )
        pinned = _ask(
            subject,
            root,
            Question(
                product_id=question.product_id,
                parameters=question.parameters,
                as_of=instant,
            ),
        )
        if pinned.refused:
            raise AssertionError(
                f"`{subject.name}` refused the same question pinned to the"
                " instant it had just reported answering at"
            )
        if pinned.content_address != served.content_address:
            raise AssertionError(
                f"`{subject.name}` reported answering at {instant!r}, but"
                " asking the same question pinned to that instant produced"
                f" `{pinned.content_address}` rather than"
                f" `{served.content_address}` — the reported instant is not the"
                " instant that answered, so a caller cannot audit the decision"
                " from the result"
            )
        refused = _ask(subject, root, refusing_question)
        if not refused.refused or refused.refusal is None:
            raise AssertionError(
                f"`{subject.name}` answered the refusing question, so this leg"
                " never checked that a refusal names its own instant"
            )
        if refused.refusal.request.temporal_boundary is None:
            raise AssertionError(
                f"`{subject.name}` refused without naming the instant it"
                " refused at — the request identity is pre-assembly and"
                " survives a refusal by `D-09`, so a caller auditing a governed"
                " no has nothing to place it in time with"
            )


# ---------------------------------------------------------------------------
# DEF-17-07, cross-adapter — one pinned instant, one decision, every transport.
# ---------------------------------------------------------------------------


def assert_one_instant_is_one_decision(
    subjects: Sequence[AdapterSubject],
    *,
    provision: Provision,
    question: Question,
) -> None:
    """One instant the **test** pins is one decision, whichever transport asked.

    ``DEF-17-07``'s cross-adapter half, split out of
    :func:`assert_decision_instant_is_auditable` by ``D-IMPL-149`` (Dave,
    2026-08-17). That leg asks with ``as_of=None`` on purpose, so each subject
    resolves an instant from its own clock; holding those recovered instants to
    each other was unsatisfiable for any two subjects and is gone. Here the
    instant is an **input**, identical for every subject by construction, and a
    comparison across subjects is therefore a claim about the transports rather
    than about when they were scheduled.

    **The precondition is the mechanism, so it is enforced rather than
    documented.** Handed a question that names no instant, this leg *refuses* —
    the mirror image of the refusal in
    :func:`assert_decision_instant_is_auditable`, and for the same reason: a
    comparison whose premise does not hold reports a difference that belongs to
    the clock. The two refusals together are what keep the split from collapsing
    back into the defect it repairs.

    Two things are asserted, and the first is what makes the leg non-vacuous
    with a single subject:

    * **per subject, against the input** — the answer echoes the pinned instant
      in ``temporal_boundary`` and is anchored to it in
      ``lineage.graph_snapshot_at``. This is *correctness*, not agreement: a
      transport that quietly answered as of some other moment fails here even if
      every other subject did the same thing. No other leg checks it, because
      every other leg compares subjects to each other rather than to what was
      asked.
    * **across subjects** — the audit view (the echoed instant, the graph
      anchor, and the address answered at that instant) is identical. Two
      transports can pass the per-subject half and still disagree here, by
      answering the pinned instant with different products; that case is
      controlled for in ``test_the_suite_fires.py`` and, through a real second
      door, in ``test_the_mcp_binding_fires.py``.

    The address is in the compared view deliberately, and it overlaps with
    :func:`assert_served_parity`, which compares every declared field including
    this one. The overlap is stated rather than avoided: without the address
    this leg would compare two values that both had to equal ``question.as_of``
    to get here, which is a cross-subject comparison that cannot fail — the
    exact shape of defect ``D-IMPL-149`` was raised about.

    Raises:
        AssertionError: the question named no instant, a subject refused, a
            subject echoed or anchored to an instant other than the one pinned,
            or two transports disagreed about the decision they reached at it.
    """
    _require_subjects(subjects, leg="one instant")
    if question.as_of is None:
        raise AssertionError(
            "this leg requires a question whose `as_of` the test pinned —"
            " handed one that names no instant, every subject would resolve"
            " its own from its own clock and the comparison below would report"
            " two transports disagreeing about when they were scheduled"
            " (`D-IMPL-149`)"
        )
    answers = _ask_each(subjects, provision=provision, question=question)
    views: dict[str, Mapping[str, Any]] = {}
    for name, result in answers.items():
        if result.refused:
            reason = result.refusal.reason if result.refusal is not None else "?"
            raise AssertionError(
                f"`{name}` refused the pinned question with `{reason}`, so this"
                " leg has no decision to place at the instant it named"
            )
        if result.temporal_boundary != question.as_of:
            raise AssertionError(
                f"`{name}` was asked at {question.as_of!r} and echoed"
                f" {result.temporal_boundary!r} — the caller named the instant,"
                " so a result reporting a different one has answered a question"
                " nobody asked and says so in the field an auditor reads first"
            )
        anchor = result.lineage.graph_snapshot_at
        if anchor != question.as_of:
            raise AssertionError(
                f"`{name}` was asked at {question.as_of!r} and read graph state"
                f" anchored at {anchor!r} — the echo can be honest while the"
                " answer is not, so the anchor is checked against the input"
                " rather than against the echo"
            )
        views[name] = {
            "temporal_boundary": result.temporal_boundary,
            "lineage.graph_snapshot_at": anchor,
            CONTENT_ADDRESS: result.content_address,
        }
    _assert_views_agree(views, leg="one instant")
