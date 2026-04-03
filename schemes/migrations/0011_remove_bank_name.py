from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('schemes', '0009_add_bank_field'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='scheme',
            name='bank_name',
        ),
    ]
