from django.core.management.base import BaseCommand
from branches.models import Bank

class Command(BaseCommand):
    help = 'Adds initial bank data to the database'

    def handle(self, *args, **options):
        banks = [
            ("ABSA", "632005"),
            ("FNB", "250655"),
            ("Nedbank", "198765"),
            ("Standard Bank", "051001"),
            ("Capitec Bank", "470010"),
            ("Investec Bank", "580105"),
            ("Tyme Bank", "678910"),
            ("SA Post Bank", "460005"),
            ("Rand Merchant Bank (RMB)", "261251"),
            ("RMB Private Bank", "222026"),
            ("African Bank", "430000"),
            ("Discovery Bank", "679000"),
            ("Sasfin Bank", "683000"),
            ("Bank of Athens", "410506"),
            ("Bidvest Bank", "462005"),
            ("Standard Chartered Bank", "730020"),
            ("HBZ Bank Limited", "570126"),
            ("HSBC Bank", "587000"),
        ]
        
        created_count = 0
        for name, branch_code in banks:
            _, created = Bank.objects.get_or_create(
                name=name,
                defaults={'branch_code': branch_code}
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'Added bank: {name} ({branch_code})'))
        
        self.stdout.write(self.style.SUCCESS(f'Successfully added {created_count} banks to the database.'))
