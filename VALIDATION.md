# Verification record — 1.10.0

Local Linux: 279 tests passed in 35.58 seconds and the expanded source smoke check exited successfully. Windows verification is pending; no successful 1.10.0 Windows delivery is claimed yet.

Schema 10 adds approvals/history and parts/reimbursement fields. Earlier databases receive a .before-v1.10.0.sqlite3 safety copy. Reimbursement is not added as a second budget cost; approval prices are separate manual tracking records.
