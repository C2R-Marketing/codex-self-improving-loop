---
name: earn
description: Run a self-improving Codex task under explicit economic pressure. Use when the user asks the agent to earn its keep, prove ROI, survive on a budget, or run ClawWork-style cost/value accounting.
---

# /earn skill

Run the economic self-improving loop. DeepSeek executes, Luna independently grades quality, and Sol rewrites the task prompt. Every cycle is charged. Value is credited only according to the selected value mode.

## Default company mode

Use `realized` for real C2R revenue/company work. This is fail-closed: no revenue is credited unless `realized_value.txt` contains a numeric receipt-derived value.

```bash
bash loop/economic_loop.sh \
  --value-mode realized \
  --initial-balance 10 \
  --cost-hook '<provider/router command that prints the actual USD cost for the cycle>'
```

Do not invent or estimate the cost hook. Use an existing provider/router receipt source. If no reliable cost source exists, report the gate as blocked rather than pretending calls are free.

## Benchmark/proxy modes

For a controlled benchmark only:

```bash
bash loop/economic_loop.sh \
  --value-mode benchmark \
  --task-value 250 \
  --initial-balance 10 \
  --fixed-cycle-cost 0.05
```

`benchmark` is simulated economic value. `proxy` is an internal value proxy. Neither is cash revenue and the ledger labels the source.

## Required behavior

- Start with the lowest-cost model likely to pass acceptance criteria.
- Luna must grade evidence, not effort.
- Sol may improve the prompt but may not weaken acceptance criteria.
- Stop immediately on bankruptcy.
- Do not credit value before the task is independently graded DONE and meets `MIN_QUALITY`.
- For real company work, do not credit a sale, lead value, cost saving, or revenue without a receipt.
- Preserve the economic ledger and state file as production-readiness evidence.

## Revenue tasks

Before executing a growth task, diagnose the lowest broken GTM layer and do not optimize above a broken lower layer:

1. Foundation — ICP language, offer, enemy/alternative, intent signals, deliverability/technical prerequisites.
2. Strategy — trigger-to-message, niche, channel roles, defensible thesis.
3. Execution — warm audiences first, micro-campaigns, content/distribution mechanics.
4. Compounding — follow-up ownership, repurposing, revenue reporting instead of activity metrics.
5. Learning — close the loop from signal/message/channel to attributed revenue and retained lesson.

For C2R, replace vendor-specific examples with owned/current systems first. No new paid SaaS or spend is authorized by this skill.
