# C2R first revenue-proof run

## Objective
Produce the shortest verified production proof that moves the current TovRose/NMV revenue system from promotion activity toward attributable cash, without new spend or unsafe public mutation.

## Source of truth
Read current `C2R-Marketing/company-os` issues/PRs relevant to website/funnel/attribution/Zeffy before acting, especially the currently open revenue modernization and attribution work. Do not rely on stale summaries when live GitHub state is available.

## Lowest-layer decision
Inspect evidence and choose exactly ONE lane for this run:

A. `FOUNDATION` — if live buyer/offer/account/deliverability evidence required for the next action is missing.
B. `EXECUTION` — if a safe revenue promotion/checkout action is ready but not implemented/tested.
C. `COMPOUNDING` — if purchase/follow-up/upsell/reactivation is the verified bottleneck.
D. `LEARNING` — if events exist but attribution/revenue reconciliation is broken or absent.

Do not work a higher layer while a lower required layer is broken.

## Priority order
1. If an authenticated, least-privilege Zeffy browser profile is available: perform the harmless UNSENT draft/save/reopen canary required by Company OS. Do not customer-send.
2. Else if a safe Woo test environment/order path is available: prove canonical `campaign_id` persistence from landing CTA through a test order and reconciliation receipt.
3. Else: produce the smallest runnable artifact that removes the exact blocker preventing (1) or (2), with proof that the artifact works locally/test-wise.

Do not substitute a new marketing plan, architecture comparison, or tool search for these proofs.

## Economic variable
Primary: attributable verified revenue path readiness.
Secondary: owner minutes eliminated from campaign/attribution operation.

Do not fabricate a dollar value if no real transaction occurs.

## Required evidence
For the chosen lane, capture exact sanitized receipts:
- actor/tool and timestamp;
- before state;
- action taken;
- after state;
- test/result;
- rollback/cancel path where applicable;
- no duplicate-send/order side effect;
- actual model/tool cost if available, otherwise UNKNOWN.

## Hard stops
STOP rather than act if the next step requires:
- new spend/subscription;
- customer/public send outside explicit approval;
- live price/checkout/DNS/credential/permission mutation;
- destructive action;
- exposing PII/secrets;
- weakening RBAC/audit/rollback/owner gates.

## Acceptance criteria
DONE requires exactly one of these PROVEN outcomes:

### Zeffy canary
- authenticated Zeffy UI opened;
- one harmless UNSENT draft created and saved;
- navigation away + reopen proves persistence/idempotent editing;
- no customer send occurred;
- sanitized receipt and cancel/delete-safe path recorded.

### Woo attribution canary
- canonical campaign identifier originates at test landing/CTA;
- persists through test checkout/order metadata;
- can be reconciled back to the source event;
- no live customer charge or production-price change occurred;
- exact test receipt recorded.

### Blocker-removal fallback
- one concrete blocker named;
- code/config/artifact implemented to remove it;
- deterministic test/build passes;
- next canary command/action is executable without another planning step.

## End report
- STATUS: BUILT|TESTED|PROVEN|BROKEN|NOT_VERIFIED
- LAYER: FOUNDATION|STRATEGY|EXECUTION|COMPOUNDING|LEARNING
- ECONOMIC_DELTA: verified facts only
- EVIDENCE: exact files/URLs/tests/receipts
- BLOCKER: if unresolved
- NEXT: one instruction

Only output `DONE:` when one acceptance path above is fully proven.