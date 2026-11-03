#!/usr/bin/env python3
"""Pure tests for the two bank-side conditions that counting cannot fake.

A flat 2,000 interactions satisfies §F's number and DEFEATS ITS PURPOSE:
relationship-strength scoring needs a real gradient to measure. And an even
spread across 50 anchors puts every client near 40 nodes, making §F's
`limit=200` truncation case unreachable.

    uv run validators/test_coverage_shape.py
"""

from __future__ import annotations

import sys

from generators.generate_coverage import (allocate_interactions,
                                          recency_weights)


def main() -> int:
    weights = recency_weights(quarters=8)
    alloc = allocate_interactions(total=2000, anchors=[f"LEI{i:02d}" for i in range(50)],
                                  dense_anchor="LEI00", dense_share=0.12)
    dense = alloc["LEI00"]
    others = [v for k, v in alloc.items() if k != "LEI00"]

    cases = [
        ("weights cover every quarter", len(weights) == 8),
        ("weights are normalised", abs(sum(weights) - 1.0) < 1e-9),
        ("the most recent quarter is heaviest", weights[0] == max(weights)),
        ("the oldest quarter is lightest", weights[-1] == min(weights)),
        ("recency is a real gradient, not a tilt",
         weights[0] >= 2.0 * weights[-1]),
        ("the allocation totals the target", sum(alloc.values()) == 2000),
        ("every anchor gets some interactions", all(v > 0 for v in alloc.values())),
        ("the dense anchor is deliberately concentrated",
         dense >= 3 * (sum(others) / len(others))),
        ("the dense anchor can exceed a 200-node depth-2 traversal",
         dense >= 200),
    ]
    failures = sum(not ok for _, ok in cases)
    for label, ok in cases:
        print(f"  [{'ok  ' if ok else 'FAIL'}] {label}")
    print(f"\n  {len(cases) - failures}/{len(cases)} cases behave as specified\n")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
