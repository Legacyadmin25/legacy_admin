import csv
import os
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q, Count
from members.models import Policy
from payments.models import Payment


class Command(BaseCommand):
    help = 'Generate a monthly report of lapsed policies that have been reactivated'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days to look back for reactivated policies (default: 30)'
        )
        parser.add_argument(
            '--output',
            type=str,
            default='',
            help='Output directory for the CSV file (default: current directory)'
        )

    def handle(self, *args, **options):
        days = options['days']
        output_dir = options['output']
        
        # Calculate the date range
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        self.stdout.write(self.style.SUCCESS(f"Generating lapsed policy recovery report from {start_date} to {end_date}"))
        
        # Find policies that were lapsed but have been reactivated
        reactivated_policies = self._find_reactivated_policies(start_date, end_date)
        
        # Generate the report
        filename = self._generate_csv_report(reactivated_policies, output_dir)
        
        self.stdout.write(self.style.SUCCESS(f"Report generated successfully: {filename}"))
        self.stdout.write(self.style.SUCCESS(f"Found {len(reactivated_policies)} reactivated policies"))

    def _find_reactivated_policies(self, start_date, end_date):
        """
        Find policies that were lapsed but have been reactivated within the date range.
        A policy is considered reactivated if:
        1. It had no payments for at least 60 days before the recent payment
        2. It received a payment within the specified date range
        """
        reactivated_policies = []
        
        # Get all policies with payments in the date range
        policies_with_recent_payments = Policy.objects.filter(
            payments__date__gte=start_date,
            payments__date__lte=end_date,
            payments__status='successful'
        ).distinct()
        
        self.stdout.write(f"Found {policies_with_recent_payments.count()} policies with payments in the date range")
        
        # Check each policy to see if it was lapsed before the recent payment
        for policy in policies_with_recent_payments:
            # Get the most recent payment in the date range
            recent_payment = Payment.objects.filter(
                policy=policy,
                date__gte=start_date,
                date__lte=end_date,
                status='successful'
            ).order_by('-date').first()
            
            if not recent_payment:
                continue
            
            # Check if there was a payment gap of at least 60 days before this payment
            previous_payment_cutoff = recent_payment.date - timedelta(days=60)
            previous_payment = Payment.objects.filter(
                policy=policy,
                date__lt=recent_payment.date,
                status='successful'
            ).order_by('-date').first()
            
            # If no previous payment or the previous payment was more than 60 days ago
            if not previous_payment or previous_payment.date < previous_payment_cutoff:
                # This policy was lapsed and has been reactivated
                reactivated_policies.append({
                    'policy': policy,
                    'reactivation_date': recent_payment.date,
                    'reactivation_amount': recent_payment.amount,
                    'days_lapsed': (recent_payment.date - previous_payment.date).days if previous_payment else 'N/A',
                    'payment_method': recent_payment.payment_method
                })
        
        return reactivated_policies

    def _generate_csv_report(self, reactivated_policies, output_dir):
        """Generate a CSV report of reactivated policies"""
        # Create the output directory if it doesn't exist
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Generate the filename with the current date
        date_str = datetime.now().strftime('%Y%m%d')
        filename = os.path.join(output_dir, f'lapsed_policy_recovery_report_{date_str}.csv')
        
        # Write the CSV file
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = [
                'Policy Number', 'Member Name', 'Scheme', 'Plan',
                'Reactivation Date', 'Reactivation Amount', 'Days Lapsed',
                'Payment Method', 'Contact Number', 'Email'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for entry in reactivated_policies:
                policy = entry['policy']
                writer.writerow({
                    'Policy Number': policy.policy_number,
                    'Member Name': f"{policy.member.first_name} {policy.member.last_name}",
                    'Scheme': policy.scheme.name if policy.scheme else 'N/A',
                    'Plan': policy.plan.name if policy.plan else 'N/A',
                    'Reactivation Date': entry['reactivation_date'].strftime('%Y-%m-%d'),
                    'Reactivation Amount': entry['reactivation_amount'],
                    'Days Lapsed': entry['days_lapsed'],
                    'Payment Method': entry['payment_method'],
                    'Contact Number': policy.member.phone_number,
                    'Email': policy.member.email
                })
        
        return filename
