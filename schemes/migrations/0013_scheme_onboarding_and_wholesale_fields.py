from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('branches', '0001_initial'),
        ('schemes', '0012_alter_scheme_account_type_alter_scheme_province'),
    ]

    operations = [
        migrations.AddField(
            model_name='plan',
            name='is_wholesale',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='plan',
            name='template_code',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.CreateModel(
            name='BranchSchemeOnboarding',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('onboarding_token', models.CharField(db_index=True, max_length=48, unique=True)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('submitted', 'Submitted'), ('reopened_for_corrections', 'Reopened for Corrections'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='draft', max_length=30)),
                ('is_active', models.BooleanField(default=True)),
                ('expires_at', models.DateTimeField(blank=True, null=True)),
                ('times_used', models.PositiveIntegerField(default=0)),
                ('company_name', models.CharField(blank=True, max_length=200)),
                ('registration_no', models.CharField(blank=True, max_length=100)),
                ('fsp_number', models.CharField(blank=True, max_length=50)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('phone', models.CharField(blank=True, max_length=20)),
                ('bank_account_no', models.CharField(blank=True, max_length=50)),
                ('debit_order_no', models.CharField(blank=True, max_length=50)),
                ('account_type', models.CharField(choices=[('Savings', 'Savings'), ('Current', 'Current')], default='Savings', max_length=20)),
                ('submitted_at', models.DateTimeField(blank=True, null=True)),
                ('submitted_by', models.CharField(blank=True, max_length=200)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('reopened_notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('branch', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='scheme_onboardings', to='branches.branch')),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_scheme_onboardings', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
