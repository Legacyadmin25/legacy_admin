from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('schemes', '0010_migrate_bank_fields'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='scheme',
            name='bank_name',
        ),
    ]
