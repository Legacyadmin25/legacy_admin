from django.core.management.base import BaseCommand
from settings_app.models import UserGroup, PagePermission

class Command(BaseCommand):
    help = "Seed default user groups and page permissions"

    def handle(self, *args, **kwargs):
        group_names = [
            "Admin", "Administartion", "Agent", "Claims", "Data Capturer", "Finance",
            "Finance Team", "Manager", "Payments", "Reversal Payments", "Sales",
            "Super Users", "Team Leader"
        ]

        page_names = [
            "Agent Setup", "Branch Setup", "Claims", "Claims Logging", "Claims Process", "Claims Search",
            "Custom Details", "Data Import", "Debit Order", "Dashboard", "Download Schedule", "Find Member",
            "Group Payments", "Import Process", "Imported History", "Manage Member", "Manage Members Payment",
            "Manage Rights", "Member", "New Member", "Payment", "Payments", "Plan Setup", "Policy Payments",
            "Print Payment Receipt", "Reports", "Schedule Email Report", "Scheme Billing", "Scheme Setup",
            "Settings", "SMS Sending", "SMS Template Setup", "Supplementary Benefits", "Underwriter Billing",
            "Underwriter Setup", "User Setup"
        ]

        # Step 1: Create Groups
        self.stdout.write(self.style.NOTICE("Seeding user groups..."))
        for name in group_names:
            group, created = UserGroup.objects.get_or_create(name=name)
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created group: {name}"))

        # Step 2: Create PagePermissions
        self.stdout.write(self.style.NOTICE("Seeding page permissions with default rights..."))

        for group in UserGroup.objects.all():
            for page in page_names:
                permission, created = PagePermission.objects.get_or_create(group=group, page_name=page)

                # Assign default rights
                if group.name == "Admin":
                    permission.has_rights = True
                    permission.is_read = True
                    permission.is_write = True
                    permission.is_delete = True
                    permission.is_update = True
                    permission.is_payment_reversal = True
                elif group.name == "Manager":
                    permission.has_rights = True
                    permission.is_read = True
                    permission.is_write = True
                    permission.is_update = True
                    permission.is_delete = False
                    permission.is_payment_reversal = False
                elif group.name == "Team Leader":
                    permission.has_rights = True
                    permission.is_read = True
                    permission.is_write = True
                    permission.is_update = True
                    permission.is_delete = False
                    permission.is_payment_reversal = False
                else:
                    # All other groups default to no access
                    permission.has_rights = False
                    permission.is_read = False
                    permission.is_write = False
                    permission.is_delete = False
                    permission.is_update = False
                    permission.is_payment_reversal = False

                permission.save()

        self.stdout.write(self.style.SUCCESS("Seeding completed successfully with default rights."))
