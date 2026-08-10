#!/usr/bin/env python3
"""Solvency-constrained self-improving Codex loop.

This is inspired by economic-agent benchmarks such as ClawWork, but it does NOT
claim that configured call charges equal the provider's real invoice. Codex CLI
currently does not expose a stable provider-neutral per-call dollar-cost contract
that this small driver can rely on. Therefore every ledger record states its cost
basis explicitly.

The loop:
1. runner executes prompt.md;
2. watcher scores the work against acceptance criteria;
3. accepted work earns score * task value;
4. every model call drains the balance;
5. Sol rewrites the prompt after failed/partial work;
6. the loop stops on accepted completion, bankruptcy, max cycles, or no progress.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def parse_grade(text: str) -> tuple[int, bool, str]:
    score_match = re.search(r"(?mi)^SCORE:\s*(\d{1,3})\s*$", text)
    accept_match = re.search(r"(?mi)^ACCEPT:\s*(yes|no)\s*$", text)
    next_match = re.search(r"(?mi)^NEXT:\s*(.+?)\s*$", text)
    if not score_match or not accept_match:
        return 0, False, "Malformed watcher output; emit required SCORE/ACCEPT fields."
    score = max(0, min(100, int(score_match.group(1))))
    accepted = accept_match.group(1).lower() == "yes"
    next_step = next_match.group(1).strip() if next_match else "Fix the highest-impact verified gap."
    return score, accepted, next_step


def run_codex(*, codex: str, model: str, sandbox: str, workdir: Path, input_text: str, output: Path) -> str:
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        codex,
        "exec",
        "-m",
        model,
        "-s",
        sandbox,
        "-C",
        str(workdir),
        "--skip-git-repo-check",
        "--ephemeral",
        "-o",
        str(output),
        "-",
    ]
    completed = subprocess.run(
        command,
        input=input_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"codex exec failed for {model} (exit={completed.returncode}): "
            f"{completed.stderr[-2000:]}"
        )
    if not output.exists():
        raise RuntimeError(f"codex exec returned success but did not create {output}")
    return output.read_text(encoding="utf-8", errors="replace")


def main() -> int:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Run a self-improving loop under an explicit economic budget.")
    parser.add_argument("--workdir", default=os.environ.get("WORKDIR", os.getcwd()))
    parser.add_argument("--codex", default=os.environ.get("CODEX_BIN", "codex"))
    parser.add_argument("--runner-model", default=os.environ.get("RUNNER_MODEL", "opencode-go/deepseek-v4-flash"))
    parser.add_argument("--watcher-model", default=os.environ.get("WATCHER_MODEL", "gpt-5.6-luna"))
    parser.add_argument("--rewriter-model", default=os.environ.get("REWRITER_MODEL", "gpt-5.6-sol"))
    parser.add_argument("--watcher-file", default=os.environ.get("WATCHER_FILE", str(here / "economic-watcher.md")))
    parser.add_argument("--rewriter-file", default=os.environ.get("REWRITER_FILE", str(here / "rewriter.md")))
    parser.add_argument("--start-balance", type=float, default=float(os.environ.get("START_BALANCE", "10")))
    parser.add_argument("--task-value", type=float, default=float(os.environ.get("TASK_VALUE", "100")))
    parser.add_argument("--payment-threshold", type=float, default=float(os.environ.get("PAYMENT_THRESHOLD", "0.60")))
    parser.add_argument("--runner-call-cost", type=float, default=float(os.environ.get("RUNNER_CALL_COST", "0.05")))
    parser.add_argument("--watcher-call-cost", type=float, default=float(os.environ.get("WATCHER_CALL_COST", "0.03")))
    parser.add_argument("--rewriter-call-cost", type=float, default=float(os.environ.get("REWRITER_CALL_COST", "0.08")))
    parser.add_argument("--cost-basis", default=os.environ.get("COST_BASIS", "configured-call-charge"))
    parser.add_argument("--max-cycles", type=int, default=int(os.environ.get("MAX_CYCLES", "6")))
    parser.add_argument("--no-progress-stop", type=int, default=int(os.environ.get("NO_PROGRESS_LIMIT", "2")))
    parser.add_argument("--artifacts-dir", default=os.environ.get("ECONOMIC_CYCLES_DIR", "economic-cycles"))
    args = parser.parse_args()

    workdir = Path(args.workdir).resolve()
    prompt = workdir / "prompt.md"
    log = workdir / "log.md"
    watcher_file = Path(args.watcher_file).resolve()
    rewriter_file = Path(args.rewriter_file).resolve()
    artifacts = workdir / args.artifacts_dir
    ledger = artifacts / "ledger.jsonl"
    state_path = artifacts / "state.json"

    for required in (prompt, watcher_file, rewriter_file):
        if not required.exists():
            print(f"missing required file: {required}", file=sys.stderr)
            return 2
    log.touch(exist_ok=True)
    artifacts.mkdir(parents=True, exist_ok=True)

    if args.start_balance <= 0 or args.task_value < 0:
        print("start balance must be > 0 and task value must be >= 0", file=sys.stderr)
        return 2
    if not 0 <= args.payment_threshold <= 1:
        print("payment threshold must be between 0 and 1", file=sys.stderr)
        return 2
    for name, value in (
        ("runner-call-cost", args.runner_call_cost),
        ("watcher-call-cost", args.watcher_call_cost),
        ("rewriter-call-cost", args.rewriter_call_cost),
    ):
        if value < 0:
            print(f"{name} must be >= 0", file=sys.stderr)
            return 2

    balance = round(args.start_balance, 8)
    total_cost = 0.0
    total_income = 0.0
    no_progress = 0
    status = "max-cycles"
    cycles_run = 0

    def charge(role: str, amount: float, cycle: int) -> bool:
        nonlocal balance, total_cost, status
        if balance + 1e-12 < amount:
            append_jsonl(
                ledger,
                {
                    "ts": utc_now(),
                    "cycle": cycle,
                    "event": "bankrupt_before_call",
                    "role": role,
                    "required": amount,
                    "balance": balance,
                    "cost_basis": args.cost_basis,
                },
            )
            status = "bankrupt"
            return False
        before = balance
        balance = round(balance - amount, 8)
        total_cost = round(total_cost + amount, 8)
        append_jsonl(
            ledger,
            {
                "ts": utc_now(),
                "cycle": cycle,
                "event": "cost",
                "role": role,
                "amount": amount,
                "balance_before": before,
                "balance_after": balance,
                "cost_basis": args.cost_basis,
            },
        )
        return True

    append_jsonl(
        ledger,
        {
            "ts": utc_now(),
            "event": "start",
            "start_balance": balance,
            "task_value": args.task_value,
            "payment_threshold": args.payment_threshold,
            "cost_basis": args.cost_basis,
            "warning": "Configured charges are not claimed to equal provider invoice costs unless COST_BASIS explicitly says so and an external reconciliation proves it.",
        },
    )

    for cycle in range(1, args.max_cycles + 1):
        cycles_run = cycle
        tag = f"{cycle:02d}"
        run_out = artifacts / f"cycle-{tag}-run.md"
        watch_out = artifacts / f"cycle-{tag}-watch.md"
        rewrite_out = artifacts / f"cycle-{tag}-rewrite.md"
        before_prompt = sha256(prompt)

        if not charge("runner", args.runner_call_cost, cycle):
            break
        runner_input = (
            "# Economic state\n"
            f"Current balance: {balance:.8f}\n"
            f"This runner call charge: {args.runner_call_cost:.8f} ({args.cost_basis})\n"
            f"Maximum task value if accepted: {args.task_value:.8f}\n"
            "Spend tokens and tool calls only when they increase verified completion probability.\n"
            "Do not weaken acceptance criteria to save budget.\n\n"
            "# Task\n" + prompt.read_text(encoding="utf-8")
        )
        try:
            run_text = run_codex(
                codex=args.codex,
                model=args.runner_model,
                sandbox="workspace-write",
                workdir=workdir,
                input_text=runner_input,
                output=run_out,
            )
        except Exception as exc:
            append_jsonl(ledger, {"ts": utc_now(), "cycle": cycle, "event": "runner_error", "error": str(exc)})
            status = "runner-error"
            break

        with log.open("a", encoding="utf-8") as handle:
            handle.write(f"\n## Economic cycle {tag}\n### run ({utc_now()})\n{run_text}\n")

        if not charge("watcher", args.watcher_call_cost, cycle):
            break
        watcher_input = (
            watcher_file.read_text(encoding="utf-8")
            + "\n\n--- current prompt.md ---\n"
            + prompt.read_text(encoding="utf-8")
            + "\n\n--- latest runner output ---\n"
            + run_text
            + "\n\n--- recent log.md ---\n"
            + "\n".join(log.read_text(encoding="utf-8", errors="replace").splitlines()[-160:])
        )
        try:
            watch_text = run_codex(
                codex=args.codex,
                model=args.watcher_model,
                sandbox="read-only",
                workdir=workdir,
                input_text=watcher_input,
                output=watch_out,
            )
        except Exception as exc:
            append_jsonl(ledger, {"ts": utc_now(), "cycle": cycle, "event": "watcher_error", "error": str(exc)})
            status = "watcher-error"
            break

        score, accepted, next_step = parse_grade(watch_text)
        with log.open("a", encoding="utf-8") as handle:
            handle.write(f"\n### economic watch ({utc_now()})\n{watch_text}\n")

        payment = 0.0
        if accepted and score / 100.0 >= args.payment_threshold:
            payment = round(args.task_value * (score / 100.0), 8)
            before_payment = balance
            balance = round(balance + payment, 8)
            total_income = round(total_income + payment, 8)
            append_jsonl(
                ledger,
                {
                    "ts": utc_now(),
                    "cycle": cycle,
                    "event": "payment",
                    "score": score,
                    "amount": payment,
                    "task_value": args.task_value,
                    "balance_before": before_payment,
                    "balance_after": balance,
                },
            )

        append_jsonl(
            ledger,
            {
                "ts": utc_now(),
                "cycle": cycle,
                "event": "grade",
                "score": score,
                "accepted": accepted,
                "next": next_step,
                "payment": payment,
                "balance": balance,
            },
        )

        runner_claimed_done = bool(re.search(r"(?mi)^DONE:", run_text))
        if accepted and runner_claimed_done:
            status = "done"
            break

        if not charge("rewriter", args.rewriter_call_cost, cycle):
            break
        rewriter_input = (
            rewriter_file.read_text(encoding="utf-8")
            + "\n\n--- economic constraint ---\n"
            + f"Balance after runner/watcher: {balance:.8f}. Avoid token-expanding rewrites.\n"
            + "The latest watcher NEXT is authoritative only if it preserves the original acceptance criteria.\n"
            + "\n--- current prompt.md ---\n"
            + prompt.read_text(encoding="utf-8")
            + "\n--- latest watcher grade ---\n"
            + watch_text
            + "\n--- recent log.md ---\n"
            + "\n".join(log.read_text(encoding="utf-8", errors="replace").splitlines()[-180:])
        )
        try:
            rewrite_text = run_codex(
                codex=args.codex,
                model=args.rewriter_model,
                sandbox="workspace-write",
                workdir=workdir,
                input_text=rewriter_input,
                output=rewrite_out,
            )
        except Exception as exc:
            append_jsonl(ledger, {"ts": utc_now(), "cycle": cycle, "event": "rewriter_error", "error": str(exc)})
            status = "rewriter-error"
            break

        with log.open("a", encoding="utf-8") as handle:
            handle.write(f"\n### economic rewrite ({utc_now()})\n{rewrite_text}\n")

        after_prompt = sha256(prompt)
        if before_prompt == after_prompt:
            no_progress += 1
        else:
            no_progress = 0
        append_jsonl(
            ledger,
            {
                "ts": utc_now(),
                "cycle": cycle,
                "event": "cycle_end",
                "prompt_changed": before_prompt != after_prompt,
                "no_progress_streak": no_progress,
                "balance": balance,
            },
        )
        if no_progress >= args.no_progress_stop:
            status = "no-progress"
            break

    state = {
        "status": status,
        "cycles_run": cycles_run,
        "balance": balance,
        "start_balance": args.start_balance,
        "total_income": total_income,
        "total_cost": total_cost,
        "net_change": round(balance - args.start_balance, 8),
        "task_value": args.task_value,
        "cost_basis": args.cost_basis,
        "runner_model": args.runner_model,
        "watcher_model": args.watcher_model,
        "rewriter_model": args.rewriter_model,
        "ledger": str(ledger),
        "finished_at": utc_now(),
    }
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(state, indent=2, sort_keys=True))
    return 0 if status == "done" else 1


if __name__ == "__main__":
    raise SystemExit(main())
