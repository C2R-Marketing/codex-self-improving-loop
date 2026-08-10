#!/usr/bin/env python3
"""Solvency-gated wrapper around loop.sh.

The wrapper runs exactly one self-improvement cycle at a time, debits verified
costs after each cycle, optionally credits verified earnings, and refuses to
start another cycle once the real balance is exhausted.

In real mode, COST_HOOK is mandatory. A hook receives the cycle number and must
print JSON: {"amount_usd": 0.01, "receipt": "provider-receipt-id", "note": "..."}.
EARN_HOOK uses the same contract. Earnings are never inferred from model grades.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
ECON = HERE / "economics.py"
LOOP = HERE / "loop.sh"


def run(cmd: list[str], *, env: dict[str, str] | None = None, capture: bool = False) -> str:
    proc = subprocess.run(
        cmd,
        check=True,
        text=True,
        env=env,
        stdout=subprocess.PIPE if capture else None,
        stderr=None,
    )
    return proc.stdout.strip() if capture and proc.stdout else ""


def ledger_status(ledger: Path, start: str) -> dict:
    out = run([sys.executable, str(ECON), "--ledger", str(ledger), "--start-balance", start, "status"], capture=True)
    return json.loads(out)


def record(ledger: Path, start: str, kind: str, cycle: int, payload: dict, mode: str) -> None:
    amount = str(payload.get("amount_usd", ""))
    receipt = str(payload.get("receipt", "")).strip()
    note = str(payload.get("note", "")).strip()
    if not amount:
        raise SystemExit(f"{kind} hook omitted amount_usd")
    cmd = [
        sys.executable, str(ECON), "--ledger", str(ledger), "--start-balance", start,
        kind, "--amount", amount, "--mode", mode, "--cycle", str(cycle),
    ]
    if receipt:
        cmd += ["--receipt", receipt]
    if note:
        cmd += ["--note", note]
    run(cmd, capture=True)


def hook_payload(hook: str, cycle: int) -> dict:
    out = run([hook, str(cycle)], capture=True)
    try:
        payload = json.loads(out)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"hook returned invalid JSON: {out!r}") from exc
    if not isinstance(payload, dict):
        raise SystemExit("hook output must be a JSON object")
    return payload


def main() -> None:
    workdir = Path(os.environ.get("WORKDIR", os.getcwd())).resolve()
    cycles_root = Path(os.environ.get("CYCLES_DIR", workdir / "cycles"))
    ledger = Path(os.environ.get("ECON_LEDGER", cycles_root / "economics.json"))
    start = os.environ.get("START_BALANCE_USD", "10")
    max_cycles = int(os.environ.get("MAX_CYCLES", "6"))
    mode = os.environ.get("ECON_MODE", "real").strip().lower()
    cost_hook = os.environ.get("COST_HOOK", "").strip()
    earn_hook = os.environ.get("EARN_HOOK", "").strip()
    simulated_cycle_cost = os.environ.get("SIMULATED_CYCLE_COST_USD", "0")

    if mode not in {"real", "simulated"}:
        raise SystemExit("ECON_MODE must be real or simulated")
    if mode == "real" and not cost_hook:
        raise SystemExit("ECON_MODE=real requires COST_HOOK; refusing unmetered execution")
    if not (workdir / "prompt.md").exists():
        raise SystemExit(f"missing {workdir / 'prompt.md'}")

    cycles_root.mkdir(parents=True, exist_ok=True)
    state = ledger_status(ledger, start)
    print(f"economic loop: balance=${state['real_balance']} mode={mode} max_cycles={max_cycles}")

    for cycle in range(1, max_cycles + 1):
        state = ledger_status(ledger, start)
        if mode == "real" and Decimal(state["real_balance"]) <= 0:
            print("BANKRUPT: balance exhausted; no further model calls allowed")
            return

        env = os.environ.copy()
        env["WORKDIR"] = str(workdir)
        env["MAX_CYCLES"] = "1"
        env["CYCLES_DIR"] = str(cycles_root / f"economic-cycle-{cycle:02d}")
        print(f"\n=== economic cycle {cycle}/{max_cycles} ===")
        proc = subprocess.run(["bash", str(LOOP), "--workdir", str(workdir), "--max-cycles", "1"], env=env, text=True)
        if proc.returncode != 0:
            raise SystemExit(proc.returncode)

        if mode == "real":
            record(ledger, start, "cost", cycle, hook_payload(cost_hook, cycle), "real")
        else:
            record(
                ledger, start, "cost", cycle,
                {"amount_usd": simulated_cycle_cost, "receipt": f"simulation:{cycle}", "note": "simulated cycle cost"},
                "simulated",
            )

        if earn_hook:
            record(ledger, start, "earn", cycle, hook_payload(earn_hook, cycle), mode)

        state = ledger_status(ledger, start)
        print(
            "ECON: "
            f"balance=${state['real_balance']} income=${state['real_income']} "
            f"cost=${state['real_cost']} net=${state['net_real_value']}"
        )

        run_state = cycles_root / f"economic-cycle-{cycle:02d}" / "state.json"
        if run_state.exists():
            status = json.loads(run_state.read_text(encoding="utf-8")).get("status")
            if status == "done":
                print("DONE: task completed before next economic cycle")
                return

    print("STOP: economic max-cycle budget reached")


if __name__ == "__main__":
    main()
