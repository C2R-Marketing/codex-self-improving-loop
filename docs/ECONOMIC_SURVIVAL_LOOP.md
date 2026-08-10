# Economic survival loop v1

This repo now has an optional economic-accountability driver inspired by the
public design of HKUDS/ClawWork:

- https://github.com/HKUDS/ClawWork

ClawWork's published benchmark starts agents with a small balance, charges work
for model/tool use, evaluates professional-task quality, and rewards accepted
work according to economic task value. The C2R implementation borrows the
**accountability mechanism**, not the benchmark's dataset or claims.

## Why this exists

The normal self-improving loop can optimize completion while still wasting
expensive calls. `loop/economic_loop.py` adds a second invariant:

> the agent must produce verified value before it exhausts its budget.

That is useful for coding, research, marketing, operations, and company-agent
work because it makes cost and quality first-class state instead of invisible
side effects.

## Truth boundary

`economic_loop.py` does **not** claim that its default call charges equal real
provider invoices. The current Codex CLI driver used here does not expose a
stable provider-neutral per-call dollar-cost contract that this repo can rely
on. Therefore:

- every ledger records `cost_basis`;
- defaults are `configured-call-charge`;
- production cost accounting is **NOT PROVEN** until provider/router receipts
  are reconciled into the ledger;
- synthetic `task_value` is benchmark/accountability value, not booked revenue.

Never report simulated earnings as company revenue.

## Run

From a project that already has `prompt.md`:

```bash
python /path/to/codex-self-improving-loop/loop/economic_loop.py \
  --workdir . \
  --start-balance 10 \
  --task-value 250 \
  --runner-call-cost 0.05 \
  --watcher-call-cost 0.03 \
  --rewriter-call-cost 0.08
```

The runner receives the live balance before each cycle. Luna grades the latest
work with `SCORE` and `ACCEPT`; accepted work earns:

```text
payment = task_value * (score / 100)
```

Payment is issued only when:

1. `ACCEPT: yes`, and
2. score meets `--payment-threshold` (default 0.60).

Every model call is charged before execution. If the remaining balance cannot
afford the next configured charge, the driver stops with `status=bankrupt`.

## Artifacts

Default output directory: `economic-cycles/`

- `ledger.jsonl` — append-only event ledger for costs, grades, payments, and bankruptcy;
- `state.json` — final balance/status/total income/total cost;
- `cycle-NN-run.md` — runner output;
- `cycle-NN-watch.md` — quality/economic grade;
- `cycle-NN-rewrite.md` — Sol prompt rewrite when another cycle is needed.

The existing `log.md` also receives the cycle transcript.

## Company mode

For C2R production work, economic accountability should use two ledgers:

### 1. Work-efficiency ledger

Always available. Tracks model/tool spend, retries, quality, cycle count,
verification, and owner-hours avoided. This can use configured estimates while
real cost receipts are unavailable, but must say `ESTIMATED`.

### 2. Revenue ledger

Strict. A task may be credited as actual revenue only when there is an external
transaction receipt (Woo/Amazon/Teachable/etc.) that can be reconciled to the
campaign/task. Drafts, clicks, emails sent, pages built, tests passed, and
synthetic task values are **not revenue**.

For promotion/sales agents, the desired production chain is:

```text
campaign/task -> spend -> artifact/action -> customer event -> order -> cash -> attribution -> retained lesson
```

This is how the self-improving loop becomes a profit loop instead of an
activity loop.

## Quality rule

The economic watcher explicitly penalizes:

- unnecessary model/tool calls;
- repeated work;
- speculative detours;
- unverifiable completion claims;
- missing tests/receipts;
- unsafe or unauthorized actions.

A runner claiming `DONE:` does not finish the economic loop unless the watcher
also emits `ACCEPT: yes`.

## Safety / owner authority

Economic pressure must never cause the agent to weaken safety or acceptance
criteria. The runner and watcher are explicitly told not to trade away:

- authorization;
- secrets boundaries;
- security controls;
- owner approval gates;
- required tests;
- truth/evidence requirements.

The agent is allowed to go bankrupt. It is not allowed to cheat the gate.

## Production readiness

Current status after this change:

- economic driver: **BUILT**;
- deterministic fake-Codex unit tests: **BUILT**;
- GitHub Actions compile/unit-test gate: **BUILT**;
- CI runtime receipt: **PENDING until PR workflow completes**;
- real router/provider cost reconciliation: **NOT BUILT**;
- live C2R revenue receipt reconciliation: **NOT BUILT**;
- autonomous customer-facing execution: **NOT AUTHORIZED by this feature**.

Next production proof is to run one bounded internal coding/research task with
real router/model calls, preserve the ledger, compare configured charges to any
available provider/router usage receipts, and verify the result was worth more
than the measured cost.
