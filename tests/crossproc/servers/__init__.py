"""Child server entry points for the cross-process fixture (D-17).

One module per server a cross-process proof needs. Each is runnable as
``python -m`` / ``python <path>`` and, on start, prints ``READY {port}`` to
stdout — the handshake ``crossproc.conftest`` blocks on. Nothing here starts a
server at import time, because the parent imports these modules to reuse their
builders.
"""
