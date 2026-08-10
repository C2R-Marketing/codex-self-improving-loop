#!/usr/bin/env python3
"""Economic accountability gate for agent work.

This module deliberately separates *real* economic value from benchmark/proxy
scores. It never labels benchmark earnings as business revenue.

Input is a JSON object on stdin or via --input. Output is a normalized JSON
receipt suitable for append-only ledgers and CI gates.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

REAL_VALUE_BASES = {"revenue", "cost_avoided", "owner_hours"}
ALL_VALUE_BASES = REAL_VALUE_BASES | {"benchmark", "proxy"}


class EconomicGateError(ValueError):
    pass


def _finite_nonnegative(name: str, value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise EconomicGateError(f"{name} must be a number") from exc
    if not math.isfinite(number) or number < 0:
        raise EconomicGateError(f"{name} must be finite and >= 0")
    return number


def _quality(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError) as exc:
        raise EconomicGateError("quality must be a number") from exc
    if not math.isfinite(score) or score < 0 or score > 1:
        raise EconomicGateError("quality must be between 0 and 1")
    return score


@dataclass(frozen=True)
class Receipt:
    task_id: str
    value_basis: str
    starting_balance_usd: float
    observed_cost_usd: float
    gross_value_usd: float
    quality: float
    quality_floor: float
    credited_value_usd: float
    ending_balance_usd: float
    net_value_usd: float
    solvent: bool
    economically_positive: bool
    real_value: bool
    evidence_uri: str | None
    status: str


def evaluate(payload: dict[str, Any], *, require_real_value: bool = False) -> Receipt:
    task_id = str(payload.get("task_id") or "").strip()
    if not task_id:
        raise EconomicGateError("task_id is required")

    value_basis = str(payload.get("value_basis") or "").strip().lower()
    if value_basis not in ALL_VALUE_BASES:
        raise EconomicGateError(
            f"value_basis must be one of: {', '.join(sorted(ALL_VALUE_BASES))}"
        )

    real_value = value_basis in REAL_VALUE_BASES
    if require_real_value and not real_value:
        raise EconomicGateError(
            "real-value gate rejected benchmark/proxy value; provide revenue, "
            "cost_avoided, or owner_hours evidence"
        )

    starting_balance = _finite_nonnegative(
        "starting_balance_usd", payload.get("starting_balance_usd", 0)
    )
    observed_cost = _finite_nonnegative(
        "observed_cost_usd", payload.get("observed_cost_usd", 0)
    )
    gross_value = _finite_nonnegative(
        "gross_value_usd", payload.get("gross_value_usd", 0)
    )
    quality = _quality(payload.get("quality", 0))
    quality_floor = _quality(payload.get("quality_floor", 0))
    min_balance = _finite_nonnegative(
        "minimum_balance_usd", payload.get("minimum_balance_usd", 0)
    )

    evidence_uri_raw = payload.get("evidence_uri")
    evidence_uri = str(evidence_uri_raw).strip() if evidence_uri_raw else None
    if real_value and not evidence_uri:
        raise EconomicGateError(
            "real economic value requires evidence_uri; do not book unverified revenue/savings"
        )

    credited = gross_value * quality if quality >= quality_floor else 0.0
    ending_balance = starting_balance - observed_cost + credited
    net_value = credited - observed_cost
    solvent = ending_balance >= min_balance
    economically_positive = net_value > 0

    if not solvent:
        status = "BANKRUPT"
    elif real_value and economically_positive:
        status = "REAL_VALUE_POSITIVE"
    elif real_value:
        status = "REAL_VALUE_NONPOSITIVE"
    elif economically_positive:
        status = "PROXY_POSITIVE_NOT_REVENUE"
    else:
        status = "PROXY_NONPOSITIVE_NOT_REVENUE"

    return Receipt(
        task_id=task_id,
        value_basis=value_basis,
        starting_balance_usd=round(starting_balance, 6),
        observed_cost_usd=round(observed_cost, 6),
        gross_value_usd=round(gross_value, 6),
        quality=round(quality, 6),
        quality_floor=round(quality_floor, 6),
        credited_value_usd=round(credited, 6),
        ending_balance_usd=round(ending_balance, 6),
        net_value_usd=round(net_value, 6),
        solvent=solvent,
        economically_positive=economically_positive,
        real_value=real_value,
        evidence_uri=evidence_uri,
        status=status,
    )


def _load_payload(path: str | None) -> dict[str, Any]:
    raw = Path(path).read_text(encoding="utf-8") if path else sys.stdin.read()
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise EconomicGateError("input must be a JSON object")
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", help="JSON input file; defaults to stdin")
    parser.add_argument(
        "--require-real-value",
        action="store_true",
        help="fail if value_basis is benchmark/proxy",
    )
    args = parser.parse_args()

    try:
        receipt = evaluate(_load_payload(args.input), require_real_value=args.require_real_value)
    except (EconomicGateError, json.JSONDecodeError, OSError) as exc:
        print(json.dumps({"status": "INVALID", "error": str(exc)}), file=sys.stderr)
        return 2

    print(json.dumps(asdict(receipt), sort_keys=True))
    return 0 if receipt.solvent else 3


if __name__ == "__main__":
    raise SystemExit(main())
