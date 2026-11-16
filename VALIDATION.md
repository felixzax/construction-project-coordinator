# Verification record — 1.4.0

Final local Linux run: Python 3.12.14, PySide6 6.8.3, pytest 8.3.5; **127 tests passed in 8.72 seconds**. The expanded `main.py --smoke-test` also exited successfully, checking receipt prices, approval, re-review on price change and Word export. Windows release evidence will be recorded after its build finishes. Automated checks use fictional suppliers, receipts and prices.

Receipt coverage includes supplier/company/contact handling, estimated and actual amounts, unknown versus zero prices, over/under/on-estimate differences, approval/rejection/review dates, resetting obsolete approvals, preserving approval on note-only edits, amount/date/status validation, retained attachments, search, filtered exports, department/project reports, backup/restore, project/contact deletion, v4-to-v5 upgrades, receipt form saving and unfinished draft recovery. All previous project, document, permit, bidding, clipboard, deletion and crash-recovery tests remain included.

Limits: this is local cost/receipt coordination, not accounting, OCR or payment processing. No supplier or bank service is contacted. PDF/image attachments need the appropriate Windows viewer and separate document-file backup. Manual physical Windows/printer acceptance and real supplier/tax validation are not claimed.
