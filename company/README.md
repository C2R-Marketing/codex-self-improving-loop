# C2R Company Survival / Profit Loop

This lane adapts the existing runner -> watcher -> Sol rewriter loop from coding tasks to company/revenue execution.

It is intentionally stricter than a generic autonomous-business agent. The loop may only count **verified economic receipts** as revenue. It may not invent sales, pipeline, customer intent, costs, conversion rates, or task completion.

## Objective

Maximize verified contribution cash, cash speed, attributable lifetime value, qualified premium demand, owner-hours eliminated, and reusable owned IP while minimizing cash spend, model/tool cost, retries, rework, security risk, and irreversible change.

The company loop is a survival system:

`observe -> find lowest broken layer -> choose highest-value bounded task -> execute -> verify -> score economics -> critique -> rewrite next instruction -> repeat`

A cycle that produces activity but no verified movement toward a revenue/cost/owner-time objective is a failed cycle.

## Five-layer pipeline diagnostic

This is an owner-supplied operating model to test against C2R evidence. It is not treated as independently verified doctrine.

1. **Foundation** — buyer evidence, offer strength, category/enemy, intent signals, deliverability/account readiness.
2. **Strategy** — niche, trigger/message fit, channel portfolio, repeatable thesis.
3. **Execution** — warm audience first, small signal-specific campaigns, landing pages, checkout, outbound/content execution.
4. **Compounding** — follow-up, repurposing, upsell/repeat/referral, revenue reporting.
5. **Learning** — signal -> decision -> action -> outcome -> attribution -> retained lesson.

Always repair the lowest broken layer before optimizing layers above it.

## Economic-accountability rule

Borrow the useful mechanism from economic-survival agent benchmarks: work must pay for itself.

For C2R this is not a fake game balance. Use actual receipts when available:

- `verified_revenue_usd`
- `verified_cash_received_usd`
- `verified_variable_cost_usd`
- `verified_model_tool_cost_usd`
- `verified_owner_minutes_saved`
- `verified_pipeline_value_usd` only when tied to a real qualified opportunity and clearly labeled PIPELINE, never revenue

Unknown values remain `UNKNOWN`; never coerce them to zero or estimates without an explicit estimation field.

Every cycle records:

`economic_delta = verified_cash_received - verified_variable_cost - verified_model_tool_cost`

Revenue that has not been paid yet is tracked separately from cash received.

## Hard controls

The loop may autonomously read, research, draft, analyze, test locally, create isolated branches/artifacts, and prepare approval-ready actions.

It may not autonomously:

- spend money or create paid subscriptions;
- send/publish to customers or the public unless a bounded standing approval explicitly covers the exact action;
- change live price/checkout/DNS/production credentials;
- modify identity/RBAC, owner approval policy, secrets rules, protected evaluators, immutable receipts, or rollback controls;
- delete/remove shipped features or data;
- claim revenue or completion without evidence.

## Run

From this repository:

```bash
bash company/run-company-loop.sh /path/to/company-workdir
```

The workdir must contain `prompt.md`. The wrapper uses the company watcher and rewriter roles while reusing `loop/loop.sh`.

Recommended first prompt: `company/prompt.template.md`.

## Completion contract

The runner may output `DONE:` only when the prompt's acceptance criteria are met with receipts. A plan, issue, draft, commit, PR, or generated artifact is not proof of runtime/commercial success unless the acceptance criteria explicitly define it as the deliverable.

The watcher must label cycle status as one of:

- `PROFIT_PROGRESS` — verified movement in revenue/cash/AOV/repeat/premium/owner-time/cost objective;
- `PROOF_PROGRESS` — necessary verified production capability moved materially closer to monetization;
- `ACTIVITY_ONLY` — work occurred but no meaningful economic/proof movement;
- `REGRESSION` — cost/rework/risk rose or working capability was broken/removed.

`ACTIVITY_ONLY` must not be rewarded as success.