# Generated by Django 5.2 on 2025-04-23 16:07

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('schemes', '0002_plan'),
    ]

    operations = [
        migrations.AddField(
            model_name='plan',
            name='max_age',
            field=models.PositiveIntegerField(default=100),
        ),
        migrations.AddField(
            model_name='plan',
            name='min_age',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='plan',
            name='scheme',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='plans', to='schemes.scheme'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='plan',
            name='name',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='plan',
            name='premium',
            field=models.DecimalField(decimal_places=2, max_digits=10),
        ),
    ]
