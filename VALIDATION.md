# Verification record — 1.11.0

Local Linux: 297 tests passed in 39.71 seconds; expanded source smoke check exited successfully. Work-order list and adjacent valuation/fee form fields were visually inspected locally. Windows verification is pending; no successful Windows 1.11.0 delivery is claimed yet.

Schema 11 adds work orders without automatically posting valuation or fees to budgets. Earlier databases get a .before-v1.11.0.sqlite3 safety copy. Actual expenses remain in the existing receipt/contract workflow.
