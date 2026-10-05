"""`D-IMPL-364` `SEC-008` B1 and B4 — the L2 writer's coverage, and the carve-out's words.

**The clauses, quoted.** `D-IMPL-364` (Dave, 2026-10-04), `SEC-008`:

    *B1 (writer coverage).* Every write-capable entry point of the L2 writer —
    ``AssemblyWorker.ingest``, ``.ingest_admitted``, ``.admit_entity_claim``,
    ``.admit_relationship_claim`` — either refuses, before any write, an envelope or
    claim whose instant lies outside the tenant's pinned window around the injected
    fabric clock, or is proved structurally unreachable from every supported governed
    ingress; a test enumerates the four entry points and, for each, names the guard
    site or the unreachability proof, and disabling the guard at that site reddens a
    named control.

    *B4 (the carve-out, per choice 2).* ``observed_at`` continues to be the
    envelope's ``ingestion_timestamp``, which on the paved road is the question's
    bounded ``asked_at``; the SDK documents it as the bounded as-of boundary, not as
    "the clock" (``src/ccf/products/product.py::AcquisitionContext``); and the
    bitemporal as-of read (valid-time ``asked_at``, transaction-time ``served_at``)
    is an identified OPEN row in this log or the gap ledger.

**Why B1 is discharged by two different kinds of proof, and why that is the ruling
rather than a shortcut.** Dave's standing placement ruling — quoted in
``tests/signal_layer/test_step8_temporal_write_guard.py``'s module docstring — is that
the temporal write guard is *a shared admission function beside*
``refuse_foreign_envelope``, **not** inside ``AssemblyWorker``: the worker stays
tenant-free and clock-free. A guard inside the worker would contradict that ruling.
So B1's first limb (``ingest``) is satisfied by its **sole governed caller's** guard,
and its other three limbs by **structural unreachability** from every supported
governed ingress, plus a disclosure in each method's own docstring naming the audit
mechanism that does apply to it.

**What this module measures, and what it deliberately does not.** It reads the
shipped tree by AST and pins three facts a later edit could silently take away: the
roster of write-capable entry points, who calls each one, and — inside the one
governed caller — that the guard's call precedes the writer's. It does not execute
the route; that is `SEC-008` B3's job, at
``tests/signal_layer/test_step8_temporal_write_guard.py::test_on_the_paved_road_a_TICKING_clock_reaches_the_write_guard_and_it_is_governed``
and
``tests/products/test_d_impl_347_seam_refusals.py::test_the_sdks_own_temporal_write_refusal_is_a_governed_refusal_without_a_declaration``.

**A tripwire over the real tree cannot prove itself.** A counting function that
silently matched nothing would report "exactly one call site" for a method with
twenty, and a reader would never know. So every counting and ordering function here
is the test module's own, and
``test_the_call_site_counter_and_the_ordering_reader_both_BITE`` applies those same
functions to a SCRATCH tree carrying planted call sites and a swapped guard — never
to the real tree, which is read-only here.
"""

from __future__ import annotations

import ast
import pathlib
import re
import textwrap

# The repository root: this file is `tests/signal_layer/<name>.py`.
_ROOT = pathlib.Path(__file__).resolve().parents[2]

_WORKER_REL = "src/ccf/assembly/worker.py"
_PRODUCT_REL = "src/ccf/products/product.py"

#: The one governed caller of the writer outside the writer itself.
_SEAM_SITE = f"{_PRODUCT_REL}::OpenedProduct._acquisition_seam"

#: The four write-capable entry points, as `D-IMPL-364` B1 enumerates them.
_ENTRY_POINTS = frozenset(
    {"ingest", "ingest_admitted", "admit_entity_claim", "admit_relationship_claim"}
)

#: Each B1 tripwire, and the EDIT that reddens it. Named per the clause's
#: *"disabling the guard at that site reddens a named control"*, and measured
#: rather than asserted by ``test_the_call_site_counter_and_the_ordering_reader_both_BITE``.
B1_TRIPWIRE_SEVERINGS: dict[str, str] = {
    "the-ingest-caller-roster": (
        "add any `worker.ingest(` call site in `src/` or `runtime/` outside"
        f" `{_SEAM_SITE}` — measured on a scratch tree, where one planted"
        " module-level caller takes the roster from one site to two"
    ),
    "the-guard-precedes-the-writer": (
        "in `src/ccf/products/product.py::OpenedProduct._acquisition_seam`, move"
        " `worker.ingest(envelope)` above"
        " `temporal_bound.refuse_outside_window(envelope, now=ingress_at)` —"
        " measured on a scratch tree with exactly that swap"
    ),
    "the-unreachable-entry-points-stay-uncalled": (
        "add a `worker.ingest_admitted(`, `worker.admit_entity_claim(` or"
        " `worker.admit_relationship_claim(` call site anywhere in `src/` or"
        " `runtime/` outside `AssemblyWorker`'s own methods — measured on the same"
        " scratch tree, where each goes from zero sites to one"
    ),
    "the-unreachable-entry-points-disclose-their-audit-mechanism": (
        "delete the phrase 'outside the supported ingress surface' from, or remove"
        " the word 'audit' from, any of the three methods' docstrings in"
        " `src/ccf/assembly/worker.py` — this pin IS the content, so the severing"
        " is the removal"
    ),
    "the-entry-point-roster-stays-exactly-four": (
        "add or remove a public non-property method on"
        " `src/ccf/assembly/worker.py::AssemblyWorker` — a fifth write-capable door"
        " is a design change and must not arrive unenumerated"
    ),
}


# --- the test module's own readers, applied to a root it is handed ----------------


def _python_files(root: pathlib.Path) -> tuple[pathlib.Path, ...]:
    """Every `.py` file under ``root/src`` and ``root/runtime``."""
    found: list[pathlib.Path] = []
    for tree in ("src", "runtime"):
        found.extend(sorted((root / tree).rglob("*.py")))
    return tuple(found)


def _site_ids(root: pathlib.Path, method: str) -> tuple[str, ...]:
    """Every ``relpath::Class.outermost_function`` that calls ``.<method>(``.

    A TUPLE, with duplicates kept: a set would hide a second call planted inside the
    same function, which is exactly one of the edits this must catch.
    """
    sites: list[str] = []
    for path in _python_files(root):
        source = path.read_text(encoding="utf-8")
        if f".{method}(" not in source:
            continue
        module = ast.parse(source)
        relative = path.relative_to(root).as_posix()
        owners: dict[int, tuple[str, ...]] = {}

        def _walk(node: ast.AST, path_so_far: tuple[str, ...], in_function: bool) -> None:
            for child in ast.iter_child_nodes(node):
                if isinstance(child, ast.ClassDef):
                    _walk(child, (*path_so_far, child.name), in_function)
                elif isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
                    # The chain stops at the OUTERMOST function.
                    next_path = path_so_far if in_function else (*path_so_far, child.name)
                    _walk(child, next_path, True)
                else:
                    if isinstance(child, ast.Call):
                        func = child.func
                        if isinstance(func, ast.Attribute) and func.attr == method:
                            owners.setdefault(id(child), path_so_far)
                            sites.append(f"{relative}::{'.'.join(path_so_far)}")
                    _walk(child, path_so_far, in_function)

        _walk(module, (), False)
    return tuple(sites)


def _outside_the_writer(sites: tuple[str, ...]) -> tuple[str, ...]:
    """The sites that are NOT inside ``AssemblyWorker``'s own methods."""
    inside = f"{_WORKER_REL}::AssemblyWorker."
    return tuple(site for site in sites if not site.startswith(inside))


def _seam_order(root: pathlib.Path) -> tuple[int, int]:
    """``(guard offset, writer offset)`` inside ``_acquisition_seam``'s own source."""
    path = root / _PRODUCT_REL
    source = path.read_text(encoding="utf-8")
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.FunctionDef) and node.name == "_acquisition_seam":
            segment = ast.get_source_segment(source, node)
            assert segment is not None, "the seam's source segment did not resolve"
            guard = "temporal_bound.refuse_outside_window("
            writer = "worker.ingest("
            assert segment.count(guard) == 1, (
                f"the guard call occurs {segment.count(guard)} time(s) in the seam;"
                " this reader assumes exactly one and would otherwise compare the"
                " wrong pair of offsets"
            )
            assert segment.count(writer) == 1, (
                f"the writer call occurs {segment.count(writer)} time(s) in the seam"
            )
            return segment.index(guard), segment.index(writer)
    raise AssertionError(f"no `_acquisition_seam` in {path}")


def _entry_points(root: pathlib.Path) -> frozenset[str]:
    """``AssemblyWorker``'s public, non-property methods, read by AST.

    Properties are excluded because they return pinned strings and hold no writer
    handle; the private helpers (``_stitch``, ``_relationship_rules``) are excluded
    because they are not doors. What is left is the WRITE-CAPABLE surface, measured
    from the module rather than copied from the clause.
    """
    source = (root / _WORKER_REL).read_text(encoding="utf-8")
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ClassDef) and node.name == "AssemblyWorker":
            return frozenset(
                member.name
                for member in node.body
                if isinstance(member, ast.FunctionDef | ast.AsyncFunctionDef)
                and not member.name.startswith("_")
                and not any(
                    isinstance(decorator, ast.Name) and decorator.id == "property"
                    for decorator in member.decorator_list
                )
            )
    raise AssertionError("no `AssemblyWorker` in the worker module")


def _attribute_block(docstring: str, name: str) -> str:
    """The ``Attributes:`` entry for ``name``, and nothing else in the docstring.

    Sliced rather than searched whole-docstring, because a phrase this clause bans
    for ``instant`` may be perfectly correct about a different member.
    """
    lines = textwrap.dedent(docstring).splitlines()
    collected: list[str] = []
    indent: int | None = None
    for line in lines:
        head = re.match(r"^(\s*)(\w+):", line)
        if indent is None:
            if head is not None and head.group(2) == name:
                indent = len(head.group(1))
                collected.append(line)
            continue
        if line.strip() and head is not None and len(head.group(1)) <= indent:
            break
        collected.append(line)
    assert collected, f"no {name!r} entry in the Attributes block"
    return "\n".join(collected)


# --- B1(a): the roster -------------------------------------------------------------


def test_the_write_capable_entry_points_of_the_l2_writer_are_EXACTLY_four() -> None:
    """B1: *"a test enumerates the four entry points"*.

    An EXACT SET measured from ``src/ccf/assembly/worker.py`` by AST, never a count
    and never a copy of the clause's list: a right count with a wrong member audits
    clean forever. A fifth public non-property method on ``AssemblyWorker`` is a
    fifth write-capable door, and it reddens here before it can arrive with no
    disposition — which is precisely the state B1 was written to end for the two
    ``admit_*`` methods.
    """
    assert _entry_points(_ROOT) == _ENTRY_POINTS


# --- B1(b): `ingest` — the guard site, named -------------------------------------


def test_the_only_governed_caller_of_ingest_outside_the_writer_is_the_acquisition_seam() -> None:
    """B1 for ``ingest``: the guard site is its SOLE governed caller's guard.

    `D-IMPL-364` lets an entry point be covered by a guard rather than by
    unreachability, and Dave's placement ruling puts the guard outside the worker.
    That only discharges the clause if the set of callers is CLOSED, so the set is
    pinned here as an exact set: one site,
    ``src/ccf/products/product.py::OpenedProduct._acquisition_seam``, which calls
    ``temporal_bound.refuse_outside_window`` immediately before ``worker.ingest``.

    The severing that reddens this is ``the-ingest-caller-roster`` in
    :data:`B1_TRIPWIRE_SEVERINGS`, and it is measured on a scratch tree by
    ``test_the_call_site_counter_and_the_ordering_reader_both_BITE``.
    """
    outside = _outside_the_writer(_site_ids(_ROOT, "ingest"))
    assert set(outside) == {_SEAM_SITE}, outside
    assert len(outside) == 1, (
        f"`ingest` is called {len(outside)} time(s) outside the writer; the guard"
        " covers one call, and a second call in the same function would be"
        " unguarded while the distinct-site set still read clean"
    )


def test_in_the_acquisition_seam_the_write_guard_PRECEDES_the_writer() -> None:
    """B1: *"either refuses, BEFORE ANY WRITE"*.

    A guard that runs after the write refuses nothing — the claim has landed, and the
    exception then makes the fabric's state and its answer disagree. The ordering is
    read off the seam's own source segment rather than described in prose, so the
    swap is visible the moment it happens.

    The severing that reddens this is ``the-guard-precedes-the-writer``, measured on
    a scratch tree below.
    """
    guard, writer = _seam_order(_ROOT)
    assert guard < writer, (
        "`worker.ingest(` now precedes `temporal_bound.refuse_outside_window(` in"
        " `OpenedProduct._acquisition_seam`: the write happens and the guard then"
        " refuses something already written"
    )


# --- B1(c): the other three — unreachability, and the disclosure ------------------


def test_the_three_other_entry_points_have_NO_caller_outside_the_writer() -> None:
    """B1 for the other three: *"proved structurally unreachable"*.

    ``ingest_admitted`` has no ``src/`` or ``runtime/`` caller at all — it relays
    into ``self.ingest`` with ``ingestion_timestamp=ingested_at`` and is reached only
    by a deployment that holds an ``AdmittedProduct``. ``admit_entity_claim`` and
    ``admit_relationship_claim`` are called ONLY from inside
    ``AssemblyWorker.ingest``, so on every supported governed ingress they sit behind
    the seam's guard rather than beside it.

    An exact EMPTY set per method, never "no unexpected callers": the severing
    ``the-unreachable-entry-points-stay-uncalled`` takes each from zero sites to one,
    and is measured on a scratch tree below.
    """
    for method in ("ingest_admitted", "admit_entity_claim", "admit_relationship_claim"):
        outside = _outside_the_writer(_site_ids(_ROOT, method))
        assert outside == (), (
            f"`{method}` is now called from {outside} — outside"
            f" `{_WORKER_REL}::AssemblyWorker`. B1 covered it by unreachability from"
            " every supported governed ingress, and that proof no longer holds:"
            " either guard the new call site or re-rule the clause"
        )


def test_each_unreachable_entry_point_DISCLOSES_that_it_is_outside_the_supported_ingress_surface() -> None:
    """B1: *"names the guard site or the unreachability proof"* — in the code.

    A proof that lives only in a test is a proof the next implementor will not read.
    Each of the three entry points B1 covers by unreachability must say so in its own
    docstring — that it is outside the supported governed ingress surface, and what
    its actual audit mechanism is (B2: *"every other write path names its actual
    audit mechanism"*).

    **RED today, and this is the clause's substance rather than a formality.**
    Measured on the shipped tree: none of the three docstrings carries either phrase,
    which is the exact state `D-IMPL-364` records as *"the two ``admit_*`` methods
    have no disposition"*.

    The pin IS the content, so the severing is the removal:
    ``the-unreachable-entry-points-disclose-their-audit-mechanism``.
    """
    source = (_ROOT / _WORKER_REL).read_text(encoding="utf-8")
    docstrings: dict[str, str] = {}
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ClassDef) and node.name == "AssemblyWorker":
            for member in node.body:
                if isinstance(member, ast.FunctionDef):
                    docstrings[member.name] = ast.get_docstring(member) or ""

    missing: dict[str, list[str]] = {}
    for method in ("ingest_admitted", "admit_entity_claim", "admit_relationship_claim"):
        document = docstrings.get(method, "")
        absent = [
            phrase
            for phrase in ("outside the supported ingress surface", "audit")
            if phrase not in document
        ]
        if absent:
            missing[method] = absent
    assert missing == {}, (
        f"these entry points do not disclose their disposition: {missing}."
        " B1 covers them by structural unreachability from every supported governed"
        " ingress; the method itself must say so, and must name the audit mechanism"
        " that does apply to it"
    )


# --- B1(d): the non-vacuity control, on a SCRATCH tree ---------------------------


_PLANTED_CALLER = '''

def _planted_second_caller(worker: object, envelope: object) -> None:  # planted
    """A planted module-level caller. Never in the real tree."""
    worker.ingest(envelope)  # type: ignore[attr-defined]
    worker.ingest_admitted(envelope)  # type: ignore[attr-defined]
    worker.admit_entity_claim(tenant_id="t", claim=envelope)  # type: ignore[attr-defined]
    worker.admit_relationship_claim(tenant_id="t", claim=envelope)  # type: ignore[attr-defined]
'''

_SWAP_ANCHOR = (
    "                temporal_bound.refuse_outside_window(envelope, now=ingress_at)\n"
    "                worker.ingest(envelope)"
)
_SWAP_REPLACEMENT = (
    "                worker.ingest(envelope)\n"
    "                temporal_bound.refuse_outside_window(envelope, now=ingress_at)"
)


def _scratch_tree(destination: pathlib.Path, *, planted: bool, swapped: bool) -> pathlib.Path:
    """A two-file copy of the real tree's writer and its one governed caller."""
    for relative in (_WORKER_REL, _PRODUCT_REL):
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text((_ROOT / relative).read_text(encoding="utf-8"), encoding="utf-8")
    product = destination / _PRODUCT_REL
    source = product.read_text(encoding="utf-8")
    if swapped:
        occurrences = source.count(_SWAP_ANCHOR)
        assert occurrences == 1, (
            f"the swap anchor occurs {occurrences} time(s); fix the anchor rather"
            " than widening the match, or this control measures nothing"
        )
        source = source.replace(_SWAP_ANCHOR, _SWAP_REPLACEMENT)
    if planted:
        source = source + _PLANTED_CALLER
    product.write_text(source, encoding="utf-8")
    return destination


def test_the_call_site_counter_and_the_ordering_reader_both_BITE(
    tmp_path: pathlib.Path,
) -> None:
    """THE NON-VACUITY CONTROL for every tripwire above.

    A reader that silently matched nothing would report "exactly one call site" for a
    method with twenty, and "the guard precedes the writer" for a seam with neither
    call in it. So the same two functions the tripwires use are applied here to a
    SCRATCH tree — two files, copied — carrying the planted call sites and the
    swapped guard that each named severing describes. The real tree is never written
    to by this module.

    Three measurements, one per severing shape:

    1. ``the-ingest-caller-roster`` — a planted module-level caller takes ``ingest``
       from one site outside the writer to two, and the distinct set from one name to
       two.
    2. ``the-unreachable-entry-points-stay-uncalled`` — the same planted caller takes
       each of the other three from ZERO sites outside the writer to one.
    3. ``the-guard-precedes-the-writer`` — swapping the two lines inverts the offsets
       the ordering reader compares.

    Plus the baseline: on an UNPLANTED, UNSWAPPED copy the readers agree with what
    they report about the real tree, so the scratch tree is a faithful stand-in and
    not a different measurement.
    """
    # (0) BASELINE: a faithful copy reproduces the real tree's readings.
    clean = _scratch_tree(tmp_path / "clean", planted=False, swapped=False)
    assert set(_outside_the_writer(_site_ids(clean, "ingest"))) == {_SEAM_SITE}
    clean_guard, clean_writer = _seam_order(clean)
    assert clean_guard < clean_writer

    # (1) + (2) PLANTED: one new module-level caller, four entry points.
    planted = _scratch_tree(tmp_path / "planted", planted=True, swapped=False)
    ingest_sites = _outside_the_writer(_site_ids(planted, "ingest"))
    assert len(ingest_sites) == 2, ingest_sites
    assert set(ingest_sites) == {
        _SEAM_SITE,
        f"{_PRODUCT_REL}::_planted_second_caller",
    }, ingest_sites
    for method in ("ingest_admitted", "admit_entity_claim", "admit_relationship_claim"):
        sites = _outside_the_writer(_site_ids(planted, method))
        assert sites == (f"{_PRODUCT_REL}::_planted_second_caller",), (method, sites)

    # (3) SWAPPED: the ordering reader inverts.
    swapped = _scratch_tree(tmp_path / "swapped", planted=False, swapped=True)
    guard, writer = _seam_order(swapped)
    assert writer < guard, (
        "the swap did not take: the ordering reader still reports the guard first,"
        " so `test_in_the_acquisition_seam_the_write_guard_PRECEDES_the_writer`"
        " could not tell the two arrangements apart"
    )


def test_every_B1_tripwire_names_its_severing() -> None:
    """The ledger is complete, and each entry names an EDIT rather than a wish.

    B1 requires that *"disabling the guard at that site reddens a named control"*.
    The names live in :data:`B1_TRIPWIRE_SEVERINGS`; three of the five are measured
    directly above, and the other two are content pins whose severing is the removal
    of the content. This test exists so a tripwire cannot be added without its
    severing being written down — the failure mode a label-presence guard in
    ``test_step8_temporal_write_guard.py`` was measured to have.
    """
    assert set(B1_TRIPWIRE_SEVERINGS) == {
        "the-ingest-caller-roster",
        "the-guard-precedes-the-writer",
        "the-unreachable-entry-points-stay-uncalled",
        "the-unreachable-entry-points-disclose-their-audit-mechanism",
        "the-entry-point-roster-stays-exactly-four",
    }
    for name, severing in B1_TRIPWIRE_SEVERINGS.items():
        assert severing.strip(), f"{name!r} names no severing"


# --- B4: the carve-out's words, and the row that stays open ----------------------


def test_the_acquisition_context_instant_is_documented_as_the_bounded_boundary_not_the_clock() -> None:
    """B4: *"the SDK documents it as the bounded as-of boundary, not as 'the clock'"*.

    `D-IMPL-364` choice 2, Dave's words: *"Accept the stamp carve-out. Correct
    ``AcquisitionContext.instant`` documentation and create an identified OPEN row
    for the bitemporal as-of read."*

    **Why a docstring is the clause rather than a nicety.** ``instant`` is the value
    every envelope's ``ingestion_timestamp`` must carry, and ``ingestion_timestamp``
    becomes ``observed_at`` in ``AssemblyWorker._stitch`` — *when the fabric learned
    the claim*. On the paved road that value is the question's bounded ``asked_at``,
    which is NOT a clock reading: it is a caller-supplied instant admitted only
    inside the tenant's pinned window (`SEC-008` A1). Calling it "the clock" in the
    one place an implementor reads before writing an ``acquire`` invites exactly the
    substitution the carve-out was accepted in order to avoid.

    Measured on the shipped tree: the ``instant`` entry says *"and the clock an SDK L1
    adapter used inside ``acquire`` is constructed with"* and says nothing about a
    bounded as-of boundary. **RED today.**

    Sliced to the ``instant`` entry alone — the banned phrase may be perfectly
    correct about a different member, and a whole-docstring search would make this
    test about the wrong text.
    """
    from ccf.products.product import AcquisitionContext

    document = AcquisitionContext.__doc__ or ""
    block = _attribute_block(document, "instant")
    assert "bounded as-of boundary" in block, (
        "`AcquisitionContext.instant` does not document itself as the bounded as-of"
        f" boundary. What it says: {block!r}"
    )
    assert "the clock" not in block, (
        "`AcquisitionContext.instant` still calls itself a clock, which is the"
        f" sentence choice 2 ruled must be corrected. What it says: {block!r}"
    )


def test_the_bitemporal_as_of_read_is_an_identified_open_row() -> None:
    """B4: *"the bitemporal as-of read ... is an identified OPEN row in this log"*.

    `D-IMPL-364` records the gap: the row *"exists only in the design's §7.4
    table"*, and a table row inside a design document is not an identified open
    obligation — nothing enumerates it, nothing reports on it, and it closes by
    being forgotten. The clause requires an entry in the decision log (or the gap
    ledger) with an id, so it can be cited and so its closure is an act rather than
    an omission.

    `D-IMPL-364` itself allocates the id: *"this entry takes ``D-IMPL-364``; next
    free ``D-IMPL-365``."*

    **RED today** — no line in ``docs/DECISIONS.md`` begins ``**D-IMPL-365``. This
    file is READ here and never written; the entry is the GREEN phase's work.
    """
    decisions = (_ROOT / "docs" / "DECISIONS.md").read_text(encoding="utf-8")
    rows = [
        line for line in decisions.splitlines() if line.startswith("**D-IMPL-365")
    ]
    assert rows, (
        "no `**D-IMPL-365` entry in docs/DECISIONS.md: the bitemporal as-of read"
        " (valid-time `asked_at`, transaction-time `served_at`) is still carried"
        " only by the design's §7.4 table, which is not an identified open row"
    )
    assert len(rows) == 1, f"{len(rows)} entries claim the id D-IMPL-365"
    entry = rows[0]
    for phrase in ("bitemporal", "OPEN"):
        assert phrase in entry, (
            f"the D-IMPL-365 entry does not contain {phrase!r}; B4 requires an"
            " identified OPEN row for the bitemporal as-of read"
        )
