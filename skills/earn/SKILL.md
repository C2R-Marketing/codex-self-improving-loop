---
name: earn
description: Run company work under receipt-backed economic pressure using the self-improving Codex survival loop.
---

# /earn

Use this for C2R work that must justify its own token/tool burn.

Default rule: use real economic mode for company work. Real mode starts with a finite balance, requires a provider/router cost receipt hook, refuses unmetered execution, and never converts model grades or predicted value into real income.

```bash
ECON_MODE=real \
START_BALANCE_USD=10 \
COST_HOOK=/absolute/path/to/provider-cost-hook \
python loop/economic_loop.py
```

Optional `EARN_HOOK` may credit only receipt-backed realized/auditable value. If no authoritative receipt exists, earnings stay zero/unknown.

Before growth execution, diagnose the lowest broken GTM layer and repair it before optimizing above it:
1. FOUNDATION — real buyer language, offer strength, alternative/enemy, intent signals, inbox/account technical readiness.
2. STRATEGY — trigger-to-message, niche, channel roles, defensible thesis.
3. EXECUTION — warm audiences first, small signal-specific campaigns, pages/checkout/distribution.
4. COMPOUNDING — follow-up, upsell/repeat/referral, asset reuse, revenue reporting.
5. LEARNING — signal -> message -> channel -> outcome -> attributed revenue -> retained lesson.

Rules:
- Evidence over activity.
- Revenue over meetings/clicks/content volume.
- Existing owned/current systems before new SaaS.
- No unapproved spend, public send/publish, live price/checkout/DNS/credential change, destructive action, or weakening of identity/RBAC/secrets/audit/rollback.
- Preserve every cost/value receipt and final economic state for Production Readiness Audit.
