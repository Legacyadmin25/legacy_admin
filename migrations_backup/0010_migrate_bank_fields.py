from django.db import migrations

def migrate_bank_data(apps, schema_editor):
    Scheme = apps.get_model('schemes', 'Scheme')
    Bank = apps.get_model('branches', 'Bank')
    
    # For each scheme, try to find or create a matching bank
    for scheme in Scheme.objects.all():
        if not scheme.bank and hasattr(scheme, 'bank_name') and scheme.bank_name:
            # Try to find an existing bank with the same name
            bank = Bank.objects.filter(name__iexact=scheme.bank_name).first()
            
            # If no bank found, create a new one
            if not bank and hasattr(scheme, 'branch_code') and scheme.branch_code:
                bank = Bank.objects.create(
                    name=scheme.bank_name,
                    branch_code=scheme.branch_code
                )
            
            if bank:
                scheme.bank = bank
                scheme.save(update_fields=['bank'])

class Migration(migrations.Migration):

    dependencies = [
        ('schemes', '0009_alter_scheme_branch_code_and_more'),
    ]

    operations = [
        migrations.RunPython(migrate_bank_data, migrations.RunPython.noop),
    ]
