"""No transport mints, discloses or catches — the delivery-boundary replay invariant, whole-surface.

``24.6-11`` Task 3; criterion 36; ``D-IMPL-256`` and ``24.6-CONTEXT.md`` D-37.
The ruling of record is Dave's, and the invariant half of it is the sentence
this module turns into a property the tree checks on every run
(``24.6-RULINGS.md`` §7):

    *"Every governed determination that crosses a CCF delivery boundary —
    fulfilled or refused, tool or resource, authorized or denied — must reach
    the replay writer before the response is released. A delivery boundary
    unable to satisfy that invariant is unavailable, not partially governed."*

And the sequence principle, which is the half this module measures:

    *"I like the recorder seam on the governed resolver, but make sure the
    architecture does not accidentally make the transport responsible for
    minting replay. The sequence should conceptually remain:*

    *request → identity/policy → determination → replay → disclosure shaping →
    transport encoding*

    *not:*

    *request → determination → HTTP/MCP → transport notices refusal → writes
    replay.*

    *Replay belongs to the governed determination, not to HTTP or MCP. That
    matters because otherwise the standing-resource/tool asymmetry simply
    reappears somewhere else."*

Why the whole surface, and why here
-----------------------------------

Plans ``24.6-09``, ``24.6-10`` and ``24.6-16`` each proved this for the door
they moved, with their own copied walker and their own planted controls. Each
of those is a statement about one module. **The defect the ruling names is a
second door growing its own mint**, and a test scoped to one door cannot see
that — which is exactly the shape of the asymmetry Dave's last sentence
predicts. So the walk here is over *every* module under
``runtime/ccf_runtime/http_api/`` and ``runtime/ccf_runtime/mcp/``, and it
lands in wave 9 rather than beside any of the three door plans because it can
only be green once all three have landed: ``routes/product.py`` still caught
the entitlement refusal until ``24.6-09``, and ``egress.py`` had no governed
step to encode until ``24.6-10``.

What the walk is a guard ON, stated so a later reader does not widen it
------------------------------------------------------------------------

It is a guard on each walked module's **direct** calls, imports and exception
handlers. It says nothing about what a module's imports go on to do, and it
must not: ``ccf_runtime.authz.product_entitlement`` legitimately imports
``ccf_runtime.http_api.errors``, ``ccf_runtime.mcp.auth`` and ``mcp.server.auth``,
and a transitive reading would turn those into violations of a rule about
transports. The determination layer is allowed to know a door's error
vocabulary; a door is not allowed to make the determination.

The one place the entitlement refusal is caught
------------------------------------------------

``ProductEntitlementRefused`` is a typed decision that must become a governed,
recorded, disclosed shell exactly once. The same AST, run over the whole
``runtime/ccf_runtime/`` package, finds its ``except`` in exactly one module:
:data:`PERMITTED_CATCH_SITE`, the governed delivery-boundary step. A second
catch site anywhere would be a second translation of one decision, and the two
would drift.

Vacuity
-------

An emptiness assertion over a tree walk passes when the walk finds no modules
at all, which is the failure mode ``tools/publish_scan.py::require_populated``
names — *"refusing to report clean over an empty tree"*. So
:func:`transport_mint_violations` **raises** on an empty roster rather than
returning nothing, the roster it returns is asserted to name the three door
modules by name, and each of the three forbidden shapes is watched being
reported on a scratch copy of the real door it corrupts.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

# --- the subject --------------------------------------------------------------

#: The repository root, resolved from this file rather than from a working
#: directory, so the walk reads the same tree however pytest was invoked.
ROOT = pathlib.Path(__file__).resolve().parents[2]

#: The two transport trees. Every module under either is walked; the roster is
#: derived from the filesystem rather than listed, so a module added to either
#: tree is covered with no edit here.
TRANSPORT_TREES: tuple[str, ...] = (
    "runtime/ccf_runtime/http_api",
    "runtime/ccf_runtime/mcp",
)

#: The whole runtime package, for the single-catch-site measurement.
RUNTIME_TREE = "runtime/ccf_runtime"

#: What a transport must never CALL. ``record`` is the one minting seam
#: (``RefusalRecorderProtocol.record``); ``disclose`` and ``disclose_only`` are
#: the Disclosure layer, which a transport must not re-enter — a second reading
#: of one policy is how two doors come to disclose one determination two ways;
#: ``write_replay_record`` and ``record_refusal`` are the replay writer itself.
FORBIDDEN_CALLS = frozenset(
    {"record", "disclose_only", "disclose", "write_replay_record", "record_refusal"}
)

#: What a transport must never IMPORT. A module that imported the writer or the
#: disclosure function has acquired the capability even if today it does not
#: use it, and the call check alone would miss a bare ``disclose(envelope)`` —
#: a ``Name`` call rather than an ``Attribute`` one.
FORBIDDEN_IMPORTS = frozenset(
    {
        "ReplayWriter",
        "record_refusal",
        "build_replay_record",
        "disclose",
        # Phase 24.6 close panel: the second spelling of the Disclosure layer
        # was importable bare while its attribute form was banned.
        "disclose_only",
    }
)

#: What a transport must never call as a bare NAME. The attribute walk sees
#: `recorder.record(` and `disclosure.disclose(`; a module that imported the
#: function and called it bare — `disclose(shell)` — is an `ast.Name` call,
#: which the Phase 24.6 close panel found the attribute walk could not see.
#: `record` is not here: a bare `record(` is any local function of that name,
#: and the minting seam is only ever reached as a method.
FORBIDDEN_NAME_CALLS = frozenset(
    {"disclose", "disclose_only", "record_refusal", "write_replay_record", "build_replay_record"}
)

#: What a transport must never import AS A MODULE. `import ccf.replay.record`
#: hands the module every name in it, so `ccf.replay.record.build_replay_record(`
#: would pass an import ban keyed on names and an attribute ban that did not
#: list the builder (Phase 24.6 close panel). `from ccf.replay.record import
#: DecisionReplayRecord` — a read-side type — is not this: it is a `from`
#: import of a name the roster above does not forbid.
FORBIDDEN_MODULES = frozenset(
    {"ccf.replay.record", "ccf.replay.serve", "ccf.products.disclosure"}
)

#: What a transport must never CATCH. The typed entitlement decision is
#: translated once, by the governed step, and encoded everywhere else.
FORBIDDEN_HANDLER = "ProductEntitlementRefused"

#: The ONE module under ``runtime/ccf_runtime/`` permitted to catch it.
PERMITTED_CATCH_SITE = "runtime/ccf_runtime/authz/delivery_boundary.py"

#: The three doors the roster must name. Asserted by name because a walk that
#: silently stopped reaching one of them would report clean over the door most
#: likely to regress — and because *which* doors this covers is the claim the
#: criterion makes.
REQUIRED_IN_ROSTER: tuple[str, ...] = (
    "runtime/ccf_runtime/http_api/routes/product.py",
    "runtime/ccf_runtime/mcp/egress.py",
    "runtime/ccf_runtime/mcp/experience.py",
)


# --- the walk -----------------------------------------------------------------


def _modules_under(root: pathlib.Path) -> list[pathlib.Path]:
    return sorted(root.rglob("*.py"))


def _violations_in(source: str, *, where: str) -> list[str]:
    """Every forbidden call, import and handler one module's AST holds."""
    tree = ast.parse(source)
    found: list[str] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in FORBIDDEN_CALLS | {"build_replay_record"}
        ):
            found.append(f"{where}:{node.lineno} calls .{node.func.attr}(")
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in FORBIDDEN_NAME_CALLS
        ):
            found.append(f"{where}:{node.lineno} calls {node.func.id}( bare")
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name in FORBIDDEN_IMPORTS:
                    found.append(f"{where}:{node.lineno} imports {alias.name}")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.rsplit(".", 1)[-1] in FORBIDDEN_IMPORTS:
                    found.append(f"{where}:{node.lineno} imports {alias.name}")
                elif alias.name in FORBIDDEN_MODULES:
                    found.append(
                        f"{where}:{node.lineno} imports the module {alias.name}"
                    )
        elif isinstance(node, ast.ExceptHandler) and node.type is not None:
            for name in ast.walk(node.type):
                if isinstance(name, ast.Name) and name.id == FORBIDDEN_HANDLER:
                    found.append(
                        f"{where}:{node.lineno} catches {FORBIDDEN_HANDLER}"
                    )
    return sorted(found)


def transport_mint_violations(root: pathlib.Path) -> tuple[list[str], list[str]]:
    """``(violations, the roster of modules walked)`` for one tree.

    A function over its subject (``D-22``), so the controls below can hand it a
    scratch tree holding a corrupted copy of a real door and watch it report —
    rather than asserting an emptiness that has only ever been empty.

    The handler form covers both spellings, bare and tuple: ``ast.walk`` over
    the handler's type expression reaches the ``Name`` inside a ``Tuple``, so
    ``except (LookupError, ProductEntitlementRefused):`` is reported exactly as
    the bare form is.

    Raises:
        AssertionError: the tree holds no Python module. An emptiness
            assertion over an empty walk is the *"reporting clean over an empty
            tree"* posture, and this refuses it at the source rather than
            leaving every caller to remember.
    """
    modules = _modules_under(root)
    assert modules, (
        f"{root} holds no Python module: a walk that read nothing would report"
        " no violation, which is not the same claim as 'there are none'"
    )
    roster = [str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
              for path in modules]
    violations: list[str] = []
    for path, where in zip(modules, roster, strict=True):
        violations.extend(
            _violations_in(path.read_text(encoding="utf-8"), where=where)
        )
    return sorted(violations), roster


def catch_sites(root: pathlib.Path) -> list[str]:
    """Every module under ``root`` whose AST catches the entitlement refusal."""
    modules = _modules_under(root)
    assert modules, f"{root} holds no Python module"
    caught: list[str] = []
    for path in modules:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler) or node.type is None:
                continue
            if any(
                isinstance(name, ast.Name) and name.id == FORBIDDEN_HANDLER
                for name in ast.walk(node.type)
            ):
                caught.append(str(path.relative_to(ROOT)))
                break
    return sorted(caught)


def _scratch_tree(
    tmp_path: pathlib.Path, *, name: str, source: str, filename: str
) -> pathlib.Path:
    """A directory holding one mutated module, for the walker to read.

    A tree rather than a string, because what the sabotages must corrupt is the
    walk's subject: a control that fed the predicate a hand-written snippet
    would prove the predicate reads snippets, not that it reads the tree.
    """
    root = tmp_path / name
    root.mkdir(parents=True)
    (root / filename).write_text(source, encoding="utf-8")
    return root


def _door_source(relative: str) -> str:
    path = ROOT / relative
    assert path.is_file(), relative
    return path.read_text(encoding="utf-8")


def _plant(source: str, *, needle: str, replacement: str) -> str:
    """One fragment rewritten, with the anchor asserted unique FIRST.

    The count is asserted before the mutation, so an anchor that has drifted
    fails loudly here rather than producing a copy identical to the original —
    which would make the control green for the wrong reason, and a green
    control is worse than none.
    """
    assert source.count(needle) == 1, (
        f"the plant anchor must appear exactly once: {needle!r}"
    )
    mutated = source.replace(needle, replacement, 1)
    assert mutated != source
    return mutated


# --- (a) the whole surface ------------------------------------------------------


def test_no_transport_module_mints_discloses_or_catches_the_entitlement_refusal() -> None:
    """Criterion 36's sequence principle, over both transport trees at once.

    What would fail here: a door that noticed a refusal and wrote its own
    record; a door that re-entered the Disclosure layer and shaped a shell a
    second way; a door that imported the replay writer; a door that caught the
    typed entitlement decision instead of encoding the governed step's return.
    Any of those is *"request → determination → HTTP/MCP → transport notices
    refusal → writes replay"*, which is the sequence Dave's ruling inverts.
    """
    roster: list[str] = []
    violations: list[str] = []
    for tree in TRANSPORT_TREES:
        found, walked = transport_mint_violations(ROOT / tree)
        violations.extend(found)
        roster.extend(walked)

    print(f"walked {len(roster)} transport modules:")
    for module in roster:
        print(f"  {module}")

    assert violations == [], violations

    # The roster is not empty (the helper refuses that) AND it names the three
    # doors: a walk that reached only `__init__.py` files would satisfy the
    # emptiness above while covering nothing.
    for door in REQUIRED_IN_ROSTER:
        assert door in roster, (
            f"{door} is not among the modules walked; the emptiness above is"
            " not a statement about that door"
        )


def test_the_entitlement_refusal_is_caught_in_exactly_one_runtime_module() -> None:
    """One decision, one translation — asserted as a roster, not a count.

    A count of one with the wrong member would audit clean forever
    (``verify-rosters-not-counts``), so the set of catching modules is compared
    for equality against the single permitted site.
    """
    assert catch_sites(ROOT / RUNTIME_TREE) == [PERMITTED_CATCH_SITE]


# --- (b) the three sabotages ----------------------------------------------------


def test_moving_the_mint_into_a_transport_is_red_sabotage(
    tmp_path: pathlib.Path,
) -> None:
    """The defect the criterion exists to prevent, planted and reported.

    A ``recorder.record(`` call inserted into ``egress.py::_answer_question``
    immediately after the governed step returns — the *"transport notices
    refusal → writes replay"* shape, in the exact place a well-meaning edit
    would put it. The scratch tree is reported, and the predicate of (a) is
    therefore RED against it.
    """
    source = _door_source("runtime/ccf_runtime/mcp/egress.py")
    anchor = (
        "            refusal_recorder=recorder,\n"
        "        )\n"
    )
    planted = _plant(
        source,
        needle=anchor,
        replacement=(
            anchor
            + "        recorder.record(  # SABOTAGE\n"
            "            decided, perspective=None, recorded_at=asked_at\n"
            "        )\n"
        ),
    )

    root = _scratch_tree(
        tmp_path, name="egress-mint", source=planted, filename="egress.py"
    )
    violations, roster = transport_mint_violations(root)

    assert roster == ["egress.py"] or roster[0].endswith("egress.py"), roster
    assert any("calls .record(" in entry for entry in violations), violations

    # And the shipped module, through the same predicate, is clean — so the
    # green in (a) is this predicate's and not an empty read's.
    assert _violations_in(source, where="egress.py") == []


def test_a_planted_entitlement_handler_in_a_transport_is_reported(
    tmp_path: pathlib.Path,
) -> None:
    """The second planted form: the door catching the typed decision again.

    ``routes/product.py`` held exactly this handler until ``24.6-09`` moved it
    behind the governed step, so the sabotage restores a state the tree really
    was in — which is the most useful kind, because it is the regression rather
    than an invented one.
    """
    source = _door_source("runtime/ccf_runtime/http_api/routes/product.py")
    anchor = (
        "        if isinstance(decided, RefusalEnvelope):\n"
        "            return _refusal_response(decided)\n"
        "        return decided\n"
    )
    planted = _plant(
        source,
        needle=anchor,
        replacement=(
            "        try:  # SABOTAGE\n"
            "            if isinstance(decided, RefusalEnvelope):\n"
            "                return _refusal_response(decided)\n"
            "        except ProductEntitlementRefused:  # SABOTAGE\n"
            "            raise\n"
            "        return decided\n"
        ),
    )

    root = _scratch_tree(
        tmp_path, name="product-catch", source=planted, filename="product.py"
    )
    violations, _roster = transport_mint_violations(root)

    assert any(
        f"catches {FORBIDDEN_HANDLER}" in entry for entry in violations
    ), violations
    assert _violations_in(source, where="product.py") == []


def test_a_disclosure_call_in_a_transport_is_reported(
    tmp_path: pathlib.Path,
) -> None:
    """The third planted form, in both spellings the Disclosure layer has.

    A transport that re-shaped a shell would be reading the disclosure policy a
    second time, and two readings of one policy are how two doors come to
    answer one determination two ways. Both an attribute call and an import of
    the bare function are planted, because the call check alone cannot see
    ``disclose(envelope, level=..., policy=...)`` — that is a ``Name`` call.
    """
    source = _door_source("runtime/ccf_runtime/mcp/experience.py")
    anchor = (
        "        if isinstance(decided, RefusalEnvelope):\n"
        '            return canonical_bytes(decided).decode("utf-8")\n'
    )
    planted = _plant(
        source,
        needle=anchor,
        replacement=(
            "        if isinstance(decided, RefusalEnvelope):\n"
            "            shell, _decision = disclosure.disclose(  # SABOTAGE\n"
            '                decided, level="minimal", policy=None\n'
            "            )\n"
            '            return canonical_bytes(shell).decode("utf-8")\n'
        ),
    )
    planted_import = planted.replace(
        "from __future__ import annotations",
        "from __future__ import annotations\n\n"
        "from ccf.products.disclosure import disclose  # SABOTAGE",
        1,
    )
    assert planted_import != planted

    root = _scratch_tree(
        tmp_path, name="experience-disclose", source=planted, filename="experience.py"
    )
    violations, _roster = transport_mint_violations(root)
    assert any("calls .disclose(" in entry for entry in violations), violations

    import_root = _scratch_tree(
        tmp_path,
        name="experience-disclose-import",
        source=planted_import,
        filename="experience.py",
    )
    import_violations, _also = transport_mint_violations(import_root)
    assert any(
        "imports disclose" in entry for entry in import_violations
    ), import_violations

    assert _violations_in(source, where="experience.py") == []


def test_a_bare_name_call_and_a_module_import_in_a_transport_are_reported(
    tmp_path: pathlib.Path,
) -> None:
    """The two spellings the Phase 24.6 close panel found the walk could not see.

    (1) `from ccf.products.disclosure import disclose_only` then a BARE
    `disclose_only(shell, …)` — an `ast.Name` call, invisible to an attribute
    walk, and `disclose_only` was not on the import roster either.
    (2) `import ccf.replay.record` then `ccf.replay.record.build_replay_record(`
    — a module import that passes a name-keyed import ban, and a builder the
    attribute ban did not list. Both are planted in a scratch copy of a real
    door and both must be reported; the real door reports nothing.
    """
    source = _door_source("runtime/ccf_runtime/mcp/experience.py")
    anchor = (
        "        if isinstance(decided, RefusalEnvelope):\n"
        '            return canonical_bytes(decided).decode("utf-8")\n'
    )
    planted = _plant(
        source,
        needle=anchor,
        replacement=(
            "        if isinstance(decided, RefusalEnvelope):\n"
            "            shell = disclose_only(decided, level=\"minimal\")  # SABOTAGE\n"
            "            ccf.replay.record.build_replay_record(shell)  # SABOTAGE\n"
            '            return canonical_bytes(shell).decode("utf-8")\n'
        ),
    ).replace(
        "from __future__ import annotations",
        "from __future__ import annotations\n\n"
        "import ccf.replay.record  # SABOTAGE\n"
        "from ccf.products.disclosure import disclose_only  # SABOTAGE",
        1,
    )
    root = _scratch_tree(
        tmp_path, name="experience-name-form", source=planted, filename="experience.py"
    )
    violations, _roster = transport_mint_violations(root)
    assert any("calls disclose_only( bare" in entry for entry in violations), violations
    assert any("imports disclose_only" in entry for entry in violations), violations
    assert any("imports the module ccf.replay.record" in entry for entry in violations), (
        violations
    )
    assert any("calls .build_replay_record(" in entry for entry in violations), violations
    assert _violations_in(source, where="experience.py") == []


def test_a_tuple_form_handler_is_reported(tmp_path: pathlib.Path) -> None:
    """The handler check reads the tuple spelling too.

    ``except (LookupError, ProductEntitlementRefused):`` is the same defect
    wearing a shape a bare-name check would miss, and a check that missed it
    would leave the easiest way to reintroduce the catch unguarded.
    """
    planted = (
        "def handler():\n"
        "    try:\n"
        "        pass\n"
        "    except (LookupError, ProductEntitlementRefused):\n"
        "        pass\n"
    )
    root = _scratch_tree(
        tmp_path, name="tuple-handler", source=planted, filename="door.py"
    )
    violations, _roster = transport_mint_violations(root)
    assert any(f"catches {FORBIDDEN_HANDLER}" in v for v in violations), violations

    # And a handler naming something else is not reported, so the check is
    # about this exception rather than about `except` clauses.
    innocent = planted.replace("ProductEntitlementRefused", "TimeoutError")
    innocent_root = _scratch_tree(
        tmp_path, name="tuple-handler-innocent", source=innocent, filename="door.py"
    )
    assert transport_mint_violations(innocent_root)[0] == []


# --- (c) the vacuity control and the no-edit guard -------------------------------


def test_the_walker_refuses_an_empty_tree(tmp_path: pathlib.Path) -> None:
    """A walk that reads nothing must not be able to report clean.

    Two legs, because "raises on empty" and "does not raise on non-empty" are
    two claims and the first alone would be satisfied by a helper that always
    raised.
    """
    empty = tmp_path / "empty-tree"
    empty.mkdir()
    with pytest.raises(AssertionError, match="holds no Python module"):
        transport_mint_violations(empty)
    with pytest.raises(AssertionError, match="holds no Python module"):
        catch_sites(empty)

    populated = _scratch_tree(
        tmp_path, name="one-module", source="x = 1\n", filename="module.py"
    )
    violations, roster = transport_mint_violations(populated)
    assert violations == []
    assert roster


def test_no_sabotage_edits_the_real_source_tree() -> None:
    """Every plant above is a copy under ``tmp_path``; the two trees are read only.

    Asserted from the trees themselves rather than from ``git``: the claim is
    that the shipped doors hold none of the forbidden shapes right now, which
    is the same predicate (a) runs and is the one a stray write would break.
    """
    for door in REQUIRED_IN_ROSTER:
        assert _violations_in(_door_source(door), where=door) == []
    assert catch_sites(ROOT / RUNTIME_TREE) == [PERMITTED_CATCH_SITE]
