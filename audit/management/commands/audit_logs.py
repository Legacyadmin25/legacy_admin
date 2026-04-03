"""
Management command to query and display audit logs from the command line.
Useful for security investigations and compliance audits.
"""
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import timedelta
from audit.models import AuditLog, DataAccess
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Query and display audit logs for security investigations'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            help='Filter by username'
        )
        parser.add_argument(
            '--action',
            type=str,
            choices=['create', 'update', 'delete', 'login', 'logout', 'export', 'import', 'view'],
            help='Filter by action type'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Look back this many days (default: 7)'
        )
        parser.add_argument(
            '--ip',
            type=str,
            help='Filter by IP address'
        )
        parser.add_argument(
            '--object',
            type=str,
            help='Filter by object representation (name or ID)'
        )
        parser.add_argument(
            '--data-access',
            action='store_true',
            help='Show data access logs instead of audit logs'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='Limit number of results (default: 50)'
        )
        parser.add_argument(
            '--csv',
            action='store_true',
            help='Output as CSV'
        )
    
    def handle(self, *args, **options):
        # Determine lookback date
        days = options.get('days', 7)
        lookback = timezone.now() - timedelta(days=days)
        
        if options.get('data_access'):
            self.show_data_access_logs(lookback, options)
        else:
            self.show_audit_logs(lookback, options)
    
    def show_audit_logs(self, lookback, options):
        """Display audit logs with applied filters"""
        query = AuditLog.objects.filter(timestamp__gte=lookback)
        
        # Apply filters
        if options.get('user'):
            query = query.filter(username__icontains=options.get('user'))
        
        if options.get('action'):
            query = query.filter(action=options.get('action'))
        
        if options.get('ip'):
            query = query.filter(ip_address=options.get('ip'))
        
        if options.get('object'):
            query = query.filter(object_repr__icontains=options.get('object'))
        
        # Limit results
        limit = options.get('limit', 50)
        logs = query.order_by('-timestamp')[:limit]
        
        if options.get('csv'):
            self.write_csv(logs)
        else:
            self.write_table(logs)
    
    def show_data_access_logs(self, lookback, options):
        """Display data access logs with applied filters"""
        query = DataAccess.objects.filter(timestamp__gte=lookback)
        
        # Apply filters
        if options.get('user'):
            query = query.filter(username__icontains=options.get('user'))
        
        if options.get('ip'):
            query = query.filter(ip_address=options.get('ip'))
        
        # Limit results
        limit = options.get('limit', 50)
        logs = query.order_by('-timestamp')[:limit]
        
        if options.get('csv'):
            self.write_data_access_csv(logs)
        else:
            self.write_data_access_table(logs)
    
    def write_table(self, logs):
        """Display logs in table format"""
        if not logs:
            self.stdout.write(self.style.WARNING('No audit logs found matching criteria'))
            return
        
        self.stdout.write('\n' + '=' * 120)
        self.stdout.write(f"{'Timestamp':<20} {'User':<15} {'Action':<10} {'IP':<15} {'Object':<40}")
        self.stdout.write('-' * 120)
        
        for log in logs:
            timestamp = log.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            user = log.username[:14]
            action = log.get_action_display()[:9]
            ip = log.ip_address or 'N/A'
            obj = (log.object_repr[:39] + '..') if len(log.object_repr) > 40 else log.object_repr
            
            self.stdout.write(f"{timestamp:<20} {user:<15} {action:<10} {ip:<15} {obj:<40}")
            
            # Show data changes if available
            if log.data:
                self.stdout.write(f"  └─ Changes: {log.data}")
        
        self.stdout.write('=' * 120 + '\n')
    
    def write_data_access_table(self, logs):
        """Display data access logs in table format"""
        if not logs:
            self.stdout.write(self.style.WARNING('No data access logs found matching criteria'))
            return
        
        self.stdout.write('\n' + '=' * 120)
        self.stdout.write(f"{'Timestamp':<20} {'User':<15} {'Content Type':<25} {'Fields':<40} {'Reason':<20}")
        self.stdout.write('-' * 120)
        
        for log in logs:
            timestamp = log.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            user = log.username[:14]
            content_type = str(log.content_type)[:24]
            fields = ', '.join(log.fields_accessed) if log.fields_accessed else 'All'
            fields = (fields[:39] + '..') if len(fields) > 40 else fields
            reason = (log.access_reason[:19] + '..') if len(log.access_reason) > 20 else log.access_reason
            
            self.stdout.write(f"{timestamp:<20} {user:<15} {content_type:<25} {fields:<40} {reason:<20}")
        
        self.stdout.write('=' * 120 + '\n')
    
    def write_csv(self, logs):
        """Output audit logs as CSV"""
        self.stdout.write('Timestamp,User,Action,IP Address,Object,Data Changes')
        
        for log in logs:
            timestamp = log.timestamp.isoformat()
            user = log.username
            action = log.get_action_display()
            ip = log.ip_address or ''
            obj = log.object_repr.replace(',', ';')  # Escape commas in object repr
            data = str(log.data).replace(',', ';') if log.data else ''
            
            self.stdout.write(f'"{timestamp}","{user}","{action}","{ip}","{obj}","{data}"')
    
    def write_data_access_csv(self, logs):
        """Output data access logs as CSV"""
        self.stdout.write('Timestamp,User,Content Type,Fields Accessed,Access Reason,IP Address')
        
        for log in logs:
            timestamp = log.timestamp.isoformat()
            user = log.username
            content_type = str(log.content_type)
            fields = '|'.join(log.fields_accessed) if log.fields_accessed else ''
            reason = log.access_reason.replace(',', ';')
            ip = log.ip_address or ''
            
            self.stdout.write(f'"{timestamp}","{user}","{content_type}","{fields}","{reason}","{ip}"')
