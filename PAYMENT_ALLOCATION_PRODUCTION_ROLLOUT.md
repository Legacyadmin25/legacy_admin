# Payment Allocation Production Rollout

Use this checklist when deploying the allocation-backed reporting changes to production.

## 1. Pre-deployment checks

- Confirm the production environment already has the Python packages required by reports and PDF generation.
- Take a database backup before applying migrations or backfilling historical allocations.
- Confirm no finance team member is actively capturing payments during the backfill window.
- Confirm environment variables for database, encryption key, staticfiles, email, and any short-link integrations are set correctly.

## 2. Deploy code and migrate

- Deploy the updated codebase to the production app directory.
- Activate the production virtual environment.
- Run `python manage.py check`.
- Run `python manage.py migrate`.
- Run `python manage.py collectstatic --noinput` if your deployment requires static collection.
- Restart the Passenger app or touch the restart file used by your host.

## 3. Backfill safely

- First preview the scope with `python manage.py backfill_payment_allocations --dry-run`.
- Review how many completed payments will receive allocations.
- If the number looks wrong, stop and inspect production payment statuses before continuing.
- Run `python manage.py backfill_payment_allocations`.
- If needed for a single case, use `python manage.py backfill_payment_allocations --payment-id <id>`.

## 4. Validate totals

- Open Payment Allocation Report for the current month and compare totals against the known finance cash-up.
- Open Payment Allocation Report for at least one historical month that should now be populated by the backfill.
- Open All Members Report for one scheme and confirm expected policy counts.
- Open Amendments Report and confirm import-based changes and audited updates appear for a known test case.
- Open one agent dashboard and confirm the commission widget matches the allocation report for the same month.

## 5. Spot-check data integrity

- Pick 3 to 5 completed payments from before the feature release.
- Confirm each now has a PaymentAllocation row.
- Confirm the allocation coverage month is correct for first-cover cases and regular renewals.
- Confirm commission, admin fee, scheme fee, branch fee, and wholesale totals match the linked plan and agent settings.

## 6. Rollback strategy

- If migrations fail, restore from backup and redeploy the previous release.
- If only the backfill output is wrong, stop using the new reports until the allocation rows are corrected.
- Do not delete historical allocations blindly in production without first isolating the affected payment IDs and confirming the month-inference issue.

## 7. Post-deployment signoff

- Finance confirms month cash-up totals are correct.
- Operations confirms historical payment months are populated.
- Admin team confirms amendments report is readable and exportable.
- Agent users confirm dashboard commission values are no longer placeholders.