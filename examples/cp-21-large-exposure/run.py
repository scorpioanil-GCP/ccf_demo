"""Run the example and show a reader what came back.

[ADAPT] freely — presentation only.

Usage::

    export CCF_CP_21_POSTGRES_DSN=...  CCF_CP_21_POSTGRES_SCHEMA=ccf_v2
    export CCF_CP_21_FLUREE_URL=...    CCF_CP_21_FLUREE_LEDGER=fibo-v2
    export CCF_CP_21_MONGO_URI=...     CCF_CP_21_MONGO_DB=fibo_v2
    export CCF_CP_21_TOKEN_CREDITOFFICER=... CCF_CP_21_TOKEN_COMMITTEE=...
    export CCF_CP_21_TOKEN_EXAMINER=...      CCF_CP_21_TOKEN_UNGRANTED=...
    make -s example-cp-21
"""

from __future__ import annotations

import argparse
import json as _json
import sys
import tempfile
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import deployment  # noqa: E402
import produce  # noqa: E402
from ccf.contracts.canonical import content_hash  # noqa: E402
from ccf.products.refusal import RefusalEnvelope  # noqa: E402
from ccf.projection.plan import Perspective  # noqa: E402

QUESTION = HERE / "artifacts" / "question.yaml"
PERSPECTIVES = HERE / "artifacts" / "perspectives.yaml"


def declaration() -> dict[str, Any]:
    return yaml.safe_load(QUESTION.read_text(encoding="utf-8"))["declaration"]


def _bn(value: Any) -> str:
    """Render a magnitude at a scale a reader can hold.

    Regulation O's limit is $500,000 — five orders of magnitude below the
    percentage limits it sits beside — so a fixed `bn` scale would print it as
    `$0.000bn` and hide the very thing `LEX-G09` exists to show.
    """
    try:
        amount = Decimal(str(value))
    except Exception:  # noqa: BLE001 - presentation only
        return str(value)
    if abs(amount) >= Decimal(1_000_000_000):
        return f"${amount / Decimal(1_000_000_000):,.3f}bn"
    if abs(amount) >= Decimal(1_000_000):
        return f"${amount / Decimal(1_000_000):,.3f}m"
    return f"${amount:,.2f}"


def main(argv: list[str]) -> int:
    declared = declaration()
    asked_defaults = dict(declared["question"])
    roles = yaml.safe_load(PERSPECTIVES.read_text(encoding="utf-8"))["declaration"]["perspectives"]
    principal_role = {spec["principal_id"]: name for name, spec in roles.items()}

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--anchor", default=asked_defaults["subject"])
    parser.add_argument("--asked-at", default=asked_defaults["asked_at"])
    parser.add_argument("--intent", default=asked_defaults["intent"],
                        help="one of " + ", ".join(declared["priced_intents"]))
    parser.add_argument("--principal", default=asked_defaults["principal"])
    parser.add_argument("--as-of", default=None)
    parser.add_argument("--regime", default=None,
                        help="one of " + ", ".join(declared["regimes"]))
    parser.add_argument("--connection-basis", default=None,
                        help="one of " + ", ".join(declared["connection_bases"]))
    parser.add_argument("--proposal", default=None,
                        help='JSON object, e.g. \'{"commitment_usd":75000000000}\'')
    parser.add_argument("--no-mitigation", action="store_true",
                        help="ask WITHOUT eligible mitigation recognized")
    parser.add_argument("--debt-tolerance", default=None)
    parser.add_argument("--door", action="store_true")
    parser.add_argument("--case", choices=("breaching", "fits", "basis"), default=None,
                        help="run one of the three measured demonstration cases")
    arguments = parser.parse_args(argv)

    if arguments.door:
        from server import serve as door  # noqa: PLC0415

        return door.main([])

    case: dict[str, Any] = {}
    if arguments.case == "breaching":
        case = declared["breaching_case"]
    elif arguments.case == "fits":
        case = declared["fits_after_mitigation_case"]
    elif arguments.case == "basis":
        case = declared["basis_contrast"]
    anchor = case.get("anchor", arguments.anchor)

    params: dict[str, Any] = {deployment.AS_OF: arguments.as_of or arguments.asked_at}
    if arguments.regime:
        params[deployment.REGIME] = arguments.regime
    if arguments.connection_basis:
        params[deployment.CONNECTION_BASIS] = arguments.connection_basis
    if arguments.proposal:
        params[deployment.PROPOSAL] = _json.loads(arguments.proposal)
    elif case.get("proposal"):
        params[deployment.PROPOSAL] = dict(case["proposal"])
    if arguments.no_mitigation:
        params[deployment.APPLY_MITIGATION] = False
    if arguments.debt_tolerance:
        params["debt_tolerance"] = float(arguments.debt_tolerance)

    role = principal_role.get(arguments.principal)
    if role is None:
        print(f"principal {arguments.principal!r} is not declared in artifacts/perspectives.yaml")
        return 2

    with tempfile.TemporaryDirectory(prefix="cp21-") as scratch:
        with produce.product(Path(scratch)) as opened:
            asked = produce.large_exposure_question(
                opened, anchor=anchor, asked_at=datetime.fromisoformat(arguments.asked_at),
                intent=arguments.intent, freshness=asked_defaults["freshness"], **params)
            outcome = opened.answer(
                asked, perspective=Perspective(principal_id=arguments.principal, role=role))

            print(f"asked        anchor {asked.subject} · {asked.intent} · as of "
                  f"{params[deployment.AS_OF]}")
            print(f"             as {arguments.principal} ({role})")
            if isinstance(outcome, RefusalEnvelope) or not hasattr(outcome, "product"):
                detail = getattr(outcome, "detail", outcome)
                print(f"REFUSED      {detail}")
                return 0

            product = outcome.product
            payload = product.payload
            print(f"served       {content_hash(product)}")
            print(f"             {payload['entities_in_view']} entities · edges "
                  f"{', '.join(payload['edge_types_served'])}")

            group = payload.get("group")
            if group is None:
                print("  group      (no connected group — served computed-empty)")
                return 0

            print(f"\n  group      anchor {group['anchor_lei']} · basis "
                  f"{group['connection_basis']} · DERIVED at ledger t={group['ledger_t']}")
            print(f"             {group['member_count']} member(s), "
                  f"{group['members_lei_registered']} LEI-registered")

            capital = payload["capital_base"]
            print(f"\n  capital    raw {capital['raw_value']} {capital['source_unit']}"
                  f"  ->  {_bn(capital['normalized_value'])} {capital['normalized_unit']}")
            print(f"             authority: {capital['unit_authority']}")
            print(f"             reported {capital['report_date']} · "
                  f"{capital['age_days']} days old at the determination instant")

            regime = payload["regime_in_force"]
            print(f"\n  regime     {regime['regime_id']} · effective {regime['effective_from']}"
                  f" · {regime['rule_form']}")
            print(f"             limit {_bn(regime['limit_value'])} ({regime['effective_basis']})")
            for provision in regime["provisions"]:
                print(f"             cites {provision['passage_id']} "
                      f"[resolved={provision['resolved']}, hash_available="
                      f"{provision['hash_available']}]")
                print(f"               “{provision['quoted_text'][:110]}…”")

            conflict = payload.get("limit_authority_conflict")
            if conflict:
                print(f"\n  CONFLICT   limit `{conflict['limit_id']}` is priced differently by two"
                      f" internal authorities:")
                for row in conflict["authorities"]:
                    print(f"               {row['authority']}: {row['limit_pct_of_capital']}%"
                          f" = {_bn(row['limit_value'])}")
                print(f"             selected `{conflict['selected_authority']}` by rule"
                      f" `{conflict['selected_by_rule']}` — neither is called wrong")

            exposure = payload["aggregate_exposure"]
            print(f"\n  exposure   commitment {_bn(exposure['total_commitment'])} · drawn "
                  f"{_bn(exposure['total_drawn'])} · undrawn {_bn(exposure['total_undrawn'])}")
            print(f"             over {exposure['members_with_exposure']} member(s) with exposure")

            evaluation = payload["evaluation"]
            print(f"\n  evaluation mitigation applied: {evaluation['mitigation_applied']}")
            for row in evaluation["without_proposal"]:
                print(f"               {row['limit_id']:<28} {row['authority']:<28}"
                      f" limit {_bn(row['limit_value'])} counted {_bn(row['exposure_counted'])}"
                      f" util {row['utilisation_pct']}% breached={row['breached']}")
                if row["counting_rules_applied"]:
                    print(f"                 rules: {', '.join(row['counting_rules_applied'])}")
            print(f"             BINDS FIRST: `{evaluation['binding_limit_id']}`"
                  f" ({evaluation['binding_limit_authority']}), headroom "
                  f"{_bn(evaluation['binding_limit_headroom'])}")

            if evaluation.get("with_proposal"):
                print(f"\n  proposal   {_bn(evaluation['proposal_commitment'])} · basis"
                      f" {evaluation['proposal_basis']} (a hypothetical, not evidence)")
                for row in evaluation["with_proposal"]:
                    print(f"               {row['limit_id']:<28} counted "
                          f"{_bn(row['exposure_counted'])} vs {_bn(row['limit_value'])}"
                          f" breached={row['breached']}")
                print(f"             regulatory outcome: {evaluation['regulatory_outcome'].upper()}")

            asymmetry = payload["freshness_asymmetry"]
            print(f"\n  asymmetry  exposure {asymmetry['exposure_instant']} ("
                  f"{asymmetry['exposure_cadence']}) vs capital "
                  f"{asymmetry['capital_report_date']} ({asymmetry['capital_cadence']})")
            print(f"             gap {asymmetry['capital_age_days']} days · resolved="
                  f"{asymmetry['resolved']} — disclosed, never fused")

            debt = payload["population_debt"]
            print(f"\n  debt       {debt['debt']} over {debt['members']} member(s) by"
                  f" `{debt['rule']}` ({debt['rule_authority']})")
            print("             observed evidence only; a proposal cannot move it")

            for finding in payload["findings"]:
                print(f"\n  FINDING    {finding['finding']}")
                print(f"             {finding['detail']}")

            for member in payload:
                if member in ("proposal_effect", "concentration_view", "methodology",
                              "replay_attribution"):
                    print(f"\n  [{role}] serves `{member}`")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
