from branches.models import Bank

def add_initial_banks():
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
    
    for name, branch_code in banks:
        Bank.objects.get_or_create(
            name=name,
            defaults={'branch_code': branch_code}
        )
    print("Successfully added initial banks.")

if __name__ == "__main__":
    import os
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Legacyadmin.settings')
    django.setup()
    add_initial_banks()
