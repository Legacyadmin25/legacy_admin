# Generated by Django 4.2.21 on 2025-05-17 05:05

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('branches', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Scheme',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, unique=True)),
                ('prefix', models.CharField(blank=True, help_text='Short code like CHB-001', max_length=20, null=True)),
                ('registration_no', models.CharField(max_length=100)),
                ('fsp_number', models.CharField(max_length=50)),
                ('email', models.EmailField(max_length=254)),
                ('extra_email', models.EmailField(blank=True, help_text='Additional email address', max_length=254, null=True)),
                ('phone', models.CharField(max_length=20)),
                ('logo', models.ImageField(blank=True, null=True, upload_to='logos/')),
                ('terms', models.TextField(blank=True)),
                ('debit_order_no', models.CharField(max_length=50)),
                ('bank_name', models.CharField(max_length=100)),
                ('branch_code', models.CharField(max_length=20)),
                ('account_no', models.CharField(max_length=50)),
                ('account_type', models.CharField(choices=[('Savings', 'Savings'), ('Current', 'Current')], max_length=50)),
                ('address', models.CharField(blank=True, max_length=255, null=True)),
                ('city', models.CharField(blank=True, max_length=100, null=True)),
                ('province', models.CharField(blank=True, max_length=100, null=True)),
                ('village', models.CharField(blank=True, max_length=100, null=True)),
                ('country', models.CharField(blank=True, max_length=100, null=True)),
                ('postal_code', models.CharField(blank=True, max_length=20, null=True)),
                ('allow_auto_policy_number', models.BooleanField(default=False)),
                ('active', models.BooleanField(default=True)),
                ('branch', models.ForeignKey(help_text='Which branch this scheme belongs to', on_delete=django.db.models.deletion.CASCADE, related_name='schemes', to='branches.branch')),
            ],
        ),
        migrations.CreateModel(
            name='Plan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True)),
                ('policy_type', models.CharField(choices=[('service', 'Service Based'), ('cash', 'Cash Based')], default='service', max_length=20)),
                ('premium', models.DecimalField(decimal_places=2, max_digits=10)),
                ('underwriter', models.CharField(blank=True, default='', max_length=100)),
                ('min_age', models.PositiveIntegerField(default=0)),
                ('max_age', models.PositiveIntegerField(default=100)),
                ('main_cover', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('main_premium', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('main_uw_cover', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('main_uw_premium', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('main_age_from', models.PositiveIntegerField(default=0)),
                ('main_age_to', models.PositiveIntegerField(default=100)),
                ('waiting_period', models.PositiveIntegerField(default=6)),
                ('lapse_period', models.PositiveIntegerField(default=2)),
                ('spouses_allowed', models.PositiveIntegerField(default=0)),
                ('children_allowed', models.PositiveIntegerField(default=0)),
                ('extended_allowed', models.PositiveIntegerField(default=0)),
                ('admin_fee', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('cash_payout', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('agent_commission', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('office_fee', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('scheme_fee', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('manager_fee', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('loyalty_programme', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('other_fees', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('is_active', models.BooleanField(default=True)),
                ('modified', models.DateField(auto_now=True)),
                ('scheme', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='plans', to='schemes.scheme')),
            ],
        ),
    ]
