# Self-improving Codex loop

Three models, two role files, one driver. DeepSeek runs the task from
`prompt.md`, Luna grades each run, Sol rewrites `prompt.md`, and the cycle
repeats until the task is done. The prompt file is the product, everything else
is plumbing.

The repository now also includes an **economic survival mode** inspired by the
accountability mechanism demonstrated by HKUDS ClawWork: work is independently
graded, model/tool cost is debited, value is credited only under an explicit
value mode, and the loop stops when it is insolvent. For real company work the
default mode is `realized`, which refuses to count hypothetical revenue as cash.

## Layout

| Path | What it is |
| --- | --- |
| `loop/loop.sh` | Original self-improving driver |
| `loop/economic_loop.sh` | Cost/value-accountable survival driver |
| `loop/economic_watcher.md` | Independent quality/economic grader contract |
| `skills/` | Slash-command skills including `/loop` and `/earn` |
| `demo/` | Original bug demo plus deterministic economic-loop test |
| `install.sh` | Copies the skills into `~/.codex/skills` |

## Quick start

1. Install the slash commands:

   ```bash
   bash install.sh
   ```

2. Restart Codex.
3. Type `/utility` to see the menu, `/loop <task>` for the normal loop, or
   `/earn <task>` for the economically-accountable loop.

## Run the original demo

```bash
cd demo
bash ../loop/loop.sh
```

The normal loop stops when the runner reports `DONE:`, after 6 cycles, or after
two consecutive cycles leave `prompt.md` unchanged.

## Run the deterministic economic-loop test

```bash
bash demo/test_economic_loop.sh
```

The test uses a fake Codex executable, so it does not consume model tokens. It
proves the accounting path: a $10 starting balance, $0.50 cycle cost, $100
benchmark task value, and 0.90 independent quality produces a $90 benchmark
payout and a final balance of $99.50.

## Economic survival mode

Real company/revenue work should use `realized` mode and an actual cost receipt
hook:

```bash
bash loop/economic_loop.sh \
  --value-mode realized \
  --initial-balance 10 \
  --cost-hook '<command that prints provider/router USD cost for this cycle>'
```

The driver is intentionally fail-closed:

- no `COST_HOOK` or explicit `FIXED_CYCLE_COST` => it refuses to run;
- `realized` mode credits no value unless `realized_value.txt` contains a
  numeric receipt-derived value;
- `benchmark` and `proxy` values are clearly labeled and must never be reported
  as real cash;
- Luna must mark `DONE=yes` and meet `MIN_QUALITY` before any value is credited;
- balance <= 0 => `bankrupt` and the loop stops;
- every cycle writes an append-only JSONL economic ledger plus final state.

This is not a claim that the repository currently has a provider-specific cost
adapter. The cost hook must be wired to a real existing router/provider receipt
before real cost accounting is PROVEN.

## Revenue diagnosis in `/earn`

Growth work uses a lowest-broken-layer rule before execution:

1. Foundation — buyer language, offer, alternative/enemy, intent signals,
   deliverability/technical prerequisites.
2. Strategy — trigger-to-message, niche, channel roles, defensible thesis.
3. Execution — warm audiences first, micro-campaigns, content/distribution.
4. Compounding — systematic follow-up, asset reuse, revenue reporting.
5. Learning — connect signal/message/channel to attributed revenue and retain
   the lesson.

Do not optimize a higher layer while a lower layer is broken. Vendor examples
from third-party GTM playbooks are patterns, not automatic C2R dependencies.
Owned/current systems remain first priority.

## Slash commands

| Command | Model / role |
| --- | --- |
| `/loop <task>` | DeepSeek runs, Luna watches, Sol rewrites |
| `/earn <task>` | Same loop with explicit cost/value solvency accounting |
| `/flash <task>` | `opencode-go/deepseek-v4-flash` |
| `/deepseek <task>` | `opencode-go/deepseek-v4-pro` |
| `/luna <task>` | `gpt-5.6-luna` |
| `/sol <task>` | `gpt-5.6-sol` |
| `/build <task>` | `opencode-go/deepseek-v4-pro` with verification |
| `/utility` | Prints this mapping |

The model slugs assume the local Codex Router catalog. On other machines,
replace them with any model `codex exec -m` can reach.

## External research reference

Economic-accountability inspiration: HKUDS/ClawWork, MIT licensed. Its public
repository describes GDPVal professional tasks, $10 starting balances, token/API
cost debits, quality-weighted task payments, persistent learning, and economic
survival metrics. This repository does **not** claim to reproduce ClawWork's
benchmark or results; it adapts the economic-pressure principle to the existing
DeepSeek/Luna/Sol Codex loop.
