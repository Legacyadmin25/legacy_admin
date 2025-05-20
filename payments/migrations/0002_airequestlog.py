from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('settings_app', '0001_initial'),
        ('schemes', '0001_initial'),
        ('members', '0002_policy_lapse_warning'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('payments', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AIRequestLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('request_type', models.CharField(choices=[('payment_summary', 'Payment Summary'), ('policy_summary', 'Policy Summary'), ('scheme_summary', 'Scheme Summary'), ('agent_summary', 'Agent Summary')], max_length=30)),
                ('prompt_data', models.TextField(help_text='Anonymized data sent to AI service')),
                ('response_data', models.TextField(help_text='Response received from AI service')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('agent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ai_requests', to='settings_app.agent')),
                ('policy', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ai_requests', to='members.policy')),
                ('scheme', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ai_requests', to='schemes.scheme')),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ai_requests', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'AI Request Log',
                'verbose_name_plural': 'AI Request Logs',
                'ordering': ['-created_at'],
            },
        ),
    ]
