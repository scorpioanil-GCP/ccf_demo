"""Cross-process proofs: real subprocesses, real loopback HTTP (D-15/D-16).

A package rather than a bare directory because the child server entry points
under :mod:`crossproc.servers` are imported by the parent tests — the same
builder that the child serves is the one the parent recomputes its expected
value from, so there is no second copy to drift.
"""
