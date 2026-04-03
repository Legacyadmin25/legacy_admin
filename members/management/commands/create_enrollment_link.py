"""
Management command to generate enrollment links
Agents/branch managers can generate shareable links for clients

Usage:
python manage.py create_enrollment_link --scheme=1 --branch=1 --agent=5 --expires=7
or
python manage.py create_enrollment_link --scheme=1 --branch=1  # No expiry
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import timedelta
from members.models_public_enrollment import EnrollmentLink
from schemes.models import Scheme
from branches.models import Branch
from settings_app.models import Agent
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Generate enrollment links for public policy applications'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--scheme',
            type=int,
            required=True,
            help='Scheme ID'
        )
        
        parser.add_argument(
            '--branch',
            type=int,
            required=True,
            help='Branch ID'
        )
        
        parser.add_argument(
            '--agent',
            type=int,
            help='Agent ID (optional)',
            default=None
        )
        
        parser.add_argument(
            '--expires',
            type=int,
            help='Expires in N days (optional, default: never expires)',
            default=None
        )
        
        parser.add_argument(
            '--count',
            type=int,
            help='Generate N links (default: 1)',
            default=1
        )
        
        parser.add_argument(
            '--user',
            type=int,
            help='User ID who is creating the link',
            default=None
        )
    
    def handle(self, *args, **options):
        # Get scheme
        try:
            scheme = Scheme.objects.get(id=options['scheme'])
        except Scheme.DoesNotExist:
            raise CommandError(f"Scheme with ID {options['scheme']} does not exist")
        
        # Get branch
        try:
            branch = Branch.objects.get(id=options['branch'])
        except Branch.DoesNotExist:
            raise CommandError(f"Branch with ID {options['branch']} does not exist")
        
        # Get agent (if provided)
        agent = None
        if options['agent']:
            try:
                agent = Agent.objects.get(id=options['agent'])
            except Agent.DoesNotExist:
                raise CommandError(f"Agent with ID {options['agent']} does not exist")
        
        # Get user who created the link
        created_by = None
        if options['user']:
            try:
                created_by = User.objects.get(id=options['user'])
            except User.DoesNotExist:
                raise CommandError(f"User with ID {options['user']} does not exist")
        
        # Calculate expiry
        expires_at = None
        if options['expires']:
            expires_at = timezone.now() + timedelta(days=options['expires'])
        
        # Create links
        links = []
        for i in range(options['count']):
            link = EnrollmentLink.objects.create(
                scheme=scheme,
                branch=branch,
                agent=agent,
                expires_at=expires_at,
                created_by=created_by
            )
            links.append(link)
            
            self.stdout.write(
                self.style.SUCCESS(f'✓ Link {i+1}: {link.token}')
            )
        
        # Summary
        self.stdout.write(self.style.SUCCESS(f'\n✅ Created {len(links)} enrollment link(s)'))
        self.stdout.write(f'Scheme: {scheme.name}')
        self.stdout.write(f'Branch: {branch.name}')
        if agent:
            self.stdout.write(f'Agent: {agent.first_name} {agent.last_name}')
        self.stdout.write(f'Expires: {"Never" if not expires_at else expires_at.strftime("%Y-%m-%d %H:%M")}')
        
        # Print links with URLs
        self.stdout.write('\n📱 Share these links with clients:\n')
        for link in links:
            base_url = 'https://yoursite.com'  # Change to your domain
            full_url = f'{base_url}/apply/{link.token}/'
            self.stdout.write(self.style.HTTP_INFO(full_url))
