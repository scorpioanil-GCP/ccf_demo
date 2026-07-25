"""The property harness: composition preservation and staged-vs-direct (D-14).

Two suites live here, and between them they cover both test classes
FEASIBILITY.md §11 names for D-08:

``test_composition.py``
    ``(A∘B)(G) = A(B(G))`` for **every ordered pair** of shipped operators
    (whitepaper §7.4), asserted on canonical bytes.
``test_staged_vs_direct.py``
    the projection engine's two-stage execution against direct composition
    followed by ``Π.invoke`` (whitepaper §7.5).

Both legs run over two classes of input, per D-14: Hypothesis-generated
banking-shaped graph states, and curated fixture graphs holding the edge cases
generation is unlikely to find on its own (empty results, fully policy-filtered
graphs, claims straddling the temporal boundary).

Neither suite touches Postgres. Operators are pure reads over an immutable
:class:`~ccf.graph.protocols.GraphView`, so the property needs a *value*, not a
substrate — and a property suite that needed a database would be run rarely
enough to stop being a property suite (04-RESEARCH.md Pitfall 6).
"""
