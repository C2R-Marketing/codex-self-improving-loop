# Economic survival mode

This mode adds economic pressure to the existing DeepSeek -> Luna -> Sol loop without pretending model grades are revenue.

## Design rules

- Real execution begins with a finite balance (`START_BALANCE_USD`, default `$10`).
- Real model/API costs must come from a receipt-producing `COST_HOOK`.
- Real earnings must come from a receipt-producing `EARN_HOOK` (order, invoice, verified payout, or another externally auditable value event).
- A model score never creates real income.
- Simulated benchmark income/cost is stored separately and cannot inflate the real balance.
- Once the real balance is `<= 0`, another real economic cycle is refused.
- Each economic cycle gets its own artifact directory, while the normal `prompt.md`/`log.md` improvement loop continues.

This is intentionally stricter than a benchmark: a beautiful deliverable with no real commercial receipt is quality evidence, not revenue.

## Run a simulation

```bash
cd your-project
export ECON_MODE=simulated
export START_BALANCE_USD=10
export SIMULATED_CYCLE_COST_USD=0.05
export MAX_CYCLES=6
python /path/to/codex-self-improving-loop/loop/economic_loop.py
```

Simulation entries appear only under `simulated_income` / `simulated_cost`.

## Run with real cost accounting

Create an executable hook that reads the provider/router's actual usage receipt for the just-completed cycle and prints one JSON object:

```json
{"amount_usd": 0.0134, "receipt": "router-run-20260809-001", "note": "runner+watcher+rewriter"}
```

Then:

```bash
export ECON_MODE=real
export START_BALANCE_USD=10
export COST_HOOK=/absolute/path/to/provider-cost-hook
python /path/to/codex-self-improving-loop/loop/economic_loop.py
```

`ECON_MODE=real` fails closed if `COST_HOOK` is missing. Do not substitute guessed token prices when the provider/router can return actual cost.

## Credit real earnings

An optional earnings hook uses the same JSON contract:

```json
{"amount_usd": 17.99, "receipt": "woo-order-12345", "note": "attributed NMV sale"}
```

```bash
export EARN_HOOK=/absolute/path/to/revenue-receipt-hook
```

The hook must return only value that the company accepts as realized/auditable income. If the task merely produced a draft, test, benchmark score, predicted value, or hypothetical savings, keep it outside `real_income`.

## Direct ledger commands

```bash
python loop/economics.py --ledger cycles/economics.json status
python loop/economics.py --ledger cycles/economics.json cost \
  --amount 0.02 --receipt provider:abc --note "verified API usage"
python loop/economics.py --ledger cycles/economics.json earn \
  --amount 17.99 --receipt order:123 --note "verified attributed sale"
```

Real cost/earn commands without `--receipt` are rejected.

## Tests

```bash
python -m unittest demo/test_economics.py
```

The tests prove: real entries require receipts; simulated income cannot change the real balance; overspending marks the ledger insolvent.

## What remains before production use

1. Build a router/provider-specific cost hook that reads actual cost receipts from the C2R model-routing stack.
2. Build commerce/revenue hooks against authoritative receipts (Woo first; Amazon/Teachable/Zeffy only when attribution is actually available).
3. Add a task-value/evaluator lane for benchmark use, but keep it explicitly simulated unless it corresponds to actual revenue or an owner-approved accounting rule.
4. Add per-agent/model profitability reporting: income, cost, net, income-per-cost-dollar, quality, retries, elapsed time, and owner-review burden.
5. Add hard per-task and daily spend ceilings before unattended operation.

## ClawWork relationship

HKUDS/ClawWork is the reference pattern: finite starting balance, token/API debits, professional-task evaluation, BLS-based benchmark value, and survival metrics. This implementation borrows the economic-accountability idea but does **not** claim benchmark dollars are company revenue. C2R real mode only credits receipt-backed real value.
