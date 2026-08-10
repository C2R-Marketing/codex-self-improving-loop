#!/usr/bin/env python3
"""Receipt-backed economic ledger for the self-improving Codex loop.

Real mode is deliberately fail-closed: costs and earnings must be recorded with
an external receipt id. Simulated benchmark entries are stored separately and
never counted as real revenue.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

ZERO = Decimal("0")


def money(raw: str) -> Decimal:
    try:
        value = Decimal(str(raw)).quantize(Decimal("0.000001"))
    except InvalidOperation as exc:
        raise SystemExit(f"invalid amount: {raw}") from exc
    if value < ZERO:
        raise SystemExit("amount must be non-negative")
    return value


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load(path: Path, start_balance: Decimal) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "schema": 1,
        "start_balance": str(start_balance),
        "real_balance": str(start_balance),
        "real_cost": "0",
        "real_income": "0",
        "simulated_cost": "0",
        "simulated_income": "0",
        "entries": [],
        "created_at": now(),
    }


def save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def require_receipt(mode: str, receipt: str | None) -> None:
    if mode == "real" and not (receipt or "").strip():
        raise SystemExit("real entries require --receipt; synthetic income/cost is forbidden")


def add_entry(data: dict, *, kind: str, amount: Decimal, mode: str, receipt: str | None,
              note: str | None, cycle: int | None) -> None:
    require_receipt(mode, receipt)
    entry = {
        "ts": now(),
        "mode": mode,
        "kind": kind,
        "amount_usd": str(amount),
        "receipt": receipt,
        "note": note,
        "cycle": cycle,
    }
    data["entries"].append(entry)

    if mode == "real":
        balance = Decimal(data["real_balance"])
        if kind == "cost":
            data["real_cost"] = str(Decimal(data["real_cost"]) + amount)
            balance -= amount
        else:
            data["real_income"] = str(Decimal(data["real_income"]) + amount)
            balance += amount
        data["real_balance"] = str(balance)
    else:
        key = "simulated_cost" if kind == "cost" else "simulated_income"
        data[key] = str(Decimal(data[key]) + amount)


def status(data: dict) -> dict:
    cost = Decimal(data["real_cost"])
    income = Decimal(data["real_income"])
    balance = Decimal(data["real_balance"])
    return {
        "start_balance": data["start_balance"],
        "real_balance": str(balance),
        "real_income": str(income),
        "real_cost": str(cost),
        "net_real_value": str(income - cost),
        "income_per_cost_dollar": str((income / cost).quantize(Decimal("0.0001"))) if cost else None,
        "simulated_income": data["simulated_income"],
        "simulated_cost": data["simulated_cost"],
        "solvent": balance > ZERO,
        "entries": len(data["entries"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", default="cycles/economics.json")
    parser.add_argument("--start-balance", default="10")
    sub = parser.add_subparsers(dest="cmd", required=True)

    for cmd in ("cost", "earn"):
        p = sub.add_parser(cmd)
        p.add_argument("--amount", required=True)
        p.add_argument("--mode", choices=("real", "simulated"), default="real")
        p.add_argument("--receipt")
        p.add_argument("--note")
        p.add_argument("--cycle", type=int)
    sub.add_parser("status")

    args = parser.parse_args()
    path = Path(args.ledger)
    data = load(path, money(args.start_balance))

    if args.cmd in {"cost", "earn"}:
        add_entry(
            data,
            kind="cost" if args.cmd == "cost" else "income",
            amount=money(args.amount),
            mode=args.mode,
            receipt=args.receipt,
            note=args.note,
            cycle=args.cycle,
        )
        save(path, data)
    print(json.dumps(status(data), sort_keys=True))


if __name__ == "__main__":
    main()
