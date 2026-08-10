# C2R first revenue-proof run

## Objective
Produce the shortest verified production proof that moves the current TovRose/NMV revenue system toward attributable cash without new spend or unsafe public mutation.

## Source of truth
Read current `C2R-Marketing/company-os` issues/PRs for website/funnel/attribution/Zeffy first. Do not rely on stale summaries when live GitHub state is available.

## Choose exactly one lowest-layer lane
A. FOUNDATION — missing live buyer/offer/account/deliverability evidence blocks the next action.
B. EXECUTION — a safe promotion/checkout action is ready but not implemented/tested.
C. COMPOUNDING — purchase/follow-up/upsell/reactivation is the verified bottleneck.
D. LEARNING — events exist but attribution/revenue reconciliation is broken or absent.

## Priority
1. If authenticated least-privilege Zeffy browser access exists: prove harmless UNSENT draft -> save -> navigate away -> reopen -> edit persistence. No customer send.
2. Else if a safe Woo test order path exists: prove canonical `campaign_id` from landing CTA through test order metadata and reconciliation. No live customer charge.
3. Else: implement and deterministically test the smallest artifact that removes the exact blocker preventing 1 or 2.

Do not substitute another marketing plan, architecture comparison, or tool search.

## Economic variable
Primary: attributable verified revenue-path readiness.
Secondary: owner minutes eliminated from campaign/attribution operation.
Do not fabricate dollar value if no transaction occurs.

## Hard stops
STOP rather than act if the next step requires unapproved spend/subscription, customer/public send, live price/checkout/DNS/credential/permission mutation, destructive action, PII/secret exposure, or weakening RBAC/audit/rollback/owner gates.

## DONE acceptance
DONE requires one fully evidenced outcome:
- Zeffy canary persisted safely with no customer send; or
- Woo campaign attribution round-trip proven through a safe test order; or
- one concrete blocker removed by working code/config with deterministic test and an immediately executable next canary.

End report:
STATUS: BUILT|TESTED|PROVEN|BROKEN|NOT_VERIFIED
LAYER: FOUNDATION|STRATEGY|EXECUTION|COMPOUNDING|LEARNING
ECONOMIC_DELTA: receipt-backed facts only
EVIDENCE: exact files/URLs/tests/receipts
BLOCKER: if unresolved
NEXT: one instruction
