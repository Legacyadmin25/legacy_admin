from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('members', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='policy',
            name='lapse_warning',
            field=models.CharField(
                choices=[('none', 'No Warning'), ('warning', 'At Risk'), ('lapsed', 'Lapsed')],
                default='none',
                max_length=10
            ),
        ),
    ]
