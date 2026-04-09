from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('branches', '0001_initial'),
        ('members', '0010_enrollmentlink_short_url_and_provider'),
        ('payments', '0003_importlog_payment_created_by_payment_ip_address_and_more'),
        ('schemes', '0002_plan_is_diy_visible_plan_terms_pdf_plan_terms_text'),
        ('settings_app', '0005_userprofile_latest_enrollment_link'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PaymentAllocation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('coverage_month', models.DateField(help_text='First day of the month this payment covers.')),
                ('allocated_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('allocation_status', models.CharField(choices=[('PENDING', 'Pending'), ('ALLOCATED', 'Allocated'), ('REVERSED', 'Reversed')], default='ALLOCATED', max_length=20)),
                ('product_name', models.CharField(blank=True, max_length=100)),
                ('policy_type', models.CharField(blank=True, max_length=20)),
                ('agent_name', models.CharField(blank=True, max_length=200)),
                ('agent_code', models.CharField(blank=True, max_length=20)),
                ('retail_premium', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('retail_cover', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('underwriter_premium', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('underwriter_cover', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('admin_fee', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('scheme_fee', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('branch_fee', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('manager_fee', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('agent_commission', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('cash_payout', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('loyalty_programme', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('other_fees', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('agent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='payment_allocations', to='settings_app.agent')),
                ('branch', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='payment_allocations', to='branches.branch')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_payment_allocations', to=settings.AUTH_USER_MODEL)),
                ('member', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payment_allocations', to='members.member')),
                ('payment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='allocations', to='payments.payment')),
                ('plan', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='payment_allocations', to='schemes.plan')),
                ('policy', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payment_allocations', to='members.policy')),
                ('scheme', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='payment_allocations', to='schemes.scheme')),
            ],
            options={
                'ordering': ['-coverage_month', '-payment__date', '-id'],
            },
        ),
        migrations.AddIndex(
            model_name='paymentallocation',
            index=models.Index(fields=['coverage_month'], name='payments_pa_coverag_d588bd_idx'),
        ),
        migrations.AddIndex(
            model_name='paymentallocation',
            index=models.Index(fields=['scheme', 'coverage_month'], name='payments_pa_scheme__d10aa7_idx'),
        ),
        migrations.AddIndex(
            model_name='paymentallocation',
            index=models.Index(fields=['agent', 'coverage_month'], name='payments_pa_agent_i_b7ef25_idx'),
        ),
        migrations.AddConstraint(
            model_name='paymentallocation',
            constraint=models.UniqueConstraint(fields=('payment', 'coverage_month'), name='unique_payment_allocation_month'),
        ),
    ]