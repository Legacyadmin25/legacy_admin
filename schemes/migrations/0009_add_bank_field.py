from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('branches', '0001_initial'),
        ('schemes', '0003_plantier'),
    ]

    operations = [
        migrations.AddField(
            model_name='scheme',
            name='bank',
            field=models.ForeignKey(
                blank=True,
                help_text='Bank for this scheme',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='schemes',
                to='branches.bank'
            ),
        ),
        migrations.AlterField(
            model_name='scheme',
            name='branch_code',
            field=models.CharField(blank=True, help_text='Auto-filled when bank is selected', max_length=20, null=True),
        ),
    ]
