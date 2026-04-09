from django.core.management.base import BaseCommand
from django.db import transaction

from payments.models import Payment


class Command(BaseCommand):
    help = 'Backfill PaymentAllocation rows for completed payments that do not yet have allocations.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Show what would be created without writing rows.')
        parser.add_argument('--payment-id', type=int, help='Backfill only a single payment ID.')

    def handle(self, *args, **options):
        queryset = Payment.objects.select_related('policy', 'policy__scheme', 'policy__plan', 'policy__underwritten_by', 'member').filter(
            status='COMPLETED',
            policy__isnull=False,
            allocations__isnull=True,
        ).order_by('date', 'id')

        payment_id = options.get('payment_id')
        if payment_id:
            queryset = queryset.filter(id=payment_id)

        total = queryset.count()
        created = 0
        skipped = 0
        dry_run = options['dry_run']

        if total == 0:
            self.stdout.write(self.style.WARNING('No completed payments without allocations were found.'))
            return

        for payment in queryset:
            if dry_run:
                created += 1
                self.stdout.write(f"Would create allocation for payment #{payment.id} ({payment.date})")
                continue

            with transaction.atomic():
                allocation = payment.create_default_allocation(created_by=payment.created_by, notes=payment.notes)
                if allocation is None:
                    skipped += 1
                    self.stdout.write(self.style.WARNING(f"Skipped payment #{payment.id}: no linked policy"))
                else:
                    created += 1

        summary = f"Processed {total} payments. Allocations {'to create' if dry_run else 'created'}: {created}. Skipped: {skipped}."
        self.stdout.write(self.style.SUCCESS(summary))