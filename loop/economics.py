#!/usr/bin/env python3
"""Deterministic economic ledger for self-improving agent loops.

This module deliberately does not guess provider token prices or business value.
Costs and credits must be supplied by a verified external source (router/provider
receipt, measured infrastructure cost, or an explicit evaluator/payment rule).

Examples:
  python loop/economics.py init --ledger cycles/economics.json --starting-balance 10
  python loop/economics.py charge --ledger cycles/economics.json --amount 0.12 --source router-receipt --ref run-01
  python loop/economics.py credit --ledger cycles/economics.json --amount 35 --quality 0.8 --source revenue-rubric --ref task-17
  python loop/economics.py status --ledger cycles/economics.json
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "c2r.economic-ledger.v1"


def now_utc() -> str:
    return datetime.now(UTC).isoformat()


def money(value: str | int | float | Decimal) -> Decimal:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"invalid money amount: {value}") from exc
    if amount < 0:
        raise ValueError("amount must be non-negative")
    return amount.quantize(Decimal("0.000001"))


def load(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"ledger does not exist: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported ledger schema")
    return data


def save(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def recompute(data: dict[str, Any]) -> None:
    starting = money(data["starting_balance"])
    cost = sum((money(e["amount"]) for e in data["entries"] if e["kind"] == "charge"), Decimal("0"))
    gross = sum((money(e["amount"]) for e in data["entries"] if e["kind"] == "credit"), Decimal("0"))
    balance = starting + gross - cost
    data["total_cost"] = str(cost)
    data["gross_value"] = str(gross)
    data["net_value"] = str(gross - cost)
    data["balance"] = str(balance)
    data["solvent"] = balance > 0
    data["updated_at"] = now_utc()


def cmd_init(args: argparse.Namespace) -> None:
    path = Path(args.ledger)
    if path.exists() and not args.force:
        raise FileExistsError(f"ledger already exists: {path}; use --force to replace")
    starting = money(args.starting_balance)
    data = {
        "schema_version": SCHEMA_VERSION,
        "created_at": now_utc(),
        "updated_at": now_utc(),
        "starting_balance": str(starting),
        "balance": str(starting),
        "gross_value": "0",
        "total_cost": "0",
        "net_value": "0",
        "solvent": starting > 0,
        "entries": [],
    }
    save(path, data)
    print(json.dumps({"balance": data["balance"], "solvent": data["solvent"]}))


def append_entry(args: argparse.Namespace, kind: str) -> None:
    path = Path(args.ledger)
    data = load(path)
    amount = money(args.amount)
    entry: dict[str, Any] = {
        "timestamp": now_utc(),
        "kind": kind,
        "amount": str(amount),
        "source": args.source,
        "ref": args.ref,
        "note": args.note or "",
    }
    if kind == "credit":
        quality = Decimal(str(args.quality))
        if quality < 0 or quality > 1:
            raise ValueError("quality must be between 0 and 1")
        entry["quality"] = str(quality)
    data["entries"].append(entry)
    recompute(data)
    save(path, data)
    print(json.dumps({"balance": data["balance"], "net_value": data["net_value"], "solvent": data["solvent"]}))


def cmd_status(args: argparse.Namespace) -> None:
    data = load(Path(args.ledger))
    recompute(data)
    print(json.dumps({
        "starting_balance": data["starting_balance"],
        "balance": data["balance"],
        "gross_value": data["gross_value"],
        "total_cost": data["total_cost"],
        "net_value": data["net_value"],
        "solvent": data["solvent"],
        "entry_count": len(data["entries"]),
    }, sort_keys=True))


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="C2R economic ledger")
    sub = p.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init")
    init.add_argument("--ledger", required=True)
    init.add_argument("--starting-balance", required=True)
    init.add_argument("--force", action="store_true")
    init.set_defaults(func=cmd_init)

    for name, kind in (("charge", "charge"), ("credit", "credit")):
        sp = sub.add_parser(name)
        sp.add_argument("--ledger", required=True)
        sp.add_argument("--amount", required=True)
        sp.add_argument("--source", required=True, help="verified source of cost/value")
        sp.add_argument("--ref", required=True, help="receipt/task/run identifier")
        sp.add_argument("--note")
        if kind == "credit":
            sp.add_argument("--quality", required=True, help="0..1 evaluator score")
            sp.set_defaults(func=lambda a, k=kind: append_entry(a, k))
        else:
            sp.set_defaults(func=lambda a, k=kind: append_entry(a, k))

    status = sub.add_parser("status")
    status.add_argument("--ledger", required=True)
    status.set_defaults(func=cmd_status)
    return p


def main() -> int:
    args = parser().parse_args()
    try:
        args.func(args)
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
