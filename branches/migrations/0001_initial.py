# Generated by Django 4.2.21 on 2025-05-17 05:05

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Bank',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('branch_code', models.CharField(max_length=10)),
            ],
        ),
        migrations.CreateModel(
            name='Branch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('location', models.CharField(blank=True, max_length=255, null=True)),
                ('code', models.CharField(blank=True, max_length=100, null=True)),
                ('phone', models.CharField(blank=True, max_length=20, null=True)),
                ('cell', models.CharField(blank=True, max_length=20, null=True)),
                ('physical_address', models.CharField(blank=True, max_length=255, null=True)),
                ('street', models.CharField(blank=True, max_length=255, null=True)),
                ('town', models.CharField(blank=True, max_length=100, null=True)),
                ('province', models.CharField(blank=True, choices=[('EC', 'Eastern Cape'), ('FS', 'Free State'), ('GP', 'Gauteng'), ('KZN', 'KwaZulu-Natal'), ('LP', 'Limpopo'), ('MP', 'Mpumalanga'), ('NC', 'Northern Cape'), ('NW', 'North West'), ('WC', 'Western Cape')], max_length=100, null=True)),
                ('account_no', models.CharField(blank=True, max_length=50, null=True)),
                ('region', models.CharField(blank=True, max_length=100, null=True)),
                ('postal_code', models.CharField(blank=True, max_length=10, null=True)),
                ('modified_user', models.CharField(blank=True, max_length=255, null=True)),
                ('modified_date', models.DateTimeField(auto_now=True)),
                ('bank', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='branches', to='branches.bank')),
            ],
        ),
    ]
