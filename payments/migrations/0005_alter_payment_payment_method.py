from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0004_paymentallocation'),
    ]

    operations = [
        migrations.AlterField(
            model_name='payment',
            name='payment_method',
            field=models.CharField(
                choices=[
                    ('CASH', 'Cash'),
                    ('CHECK', 'Check'),
                    ('CREDIT', 'Credit Card'),
                    ('BANK_TRANSFER', 'EFT / Bank Transfer'),
                    ('DEBIT_ORDER', 'Debit Order'),
                    ('EASYPAY', 'EasyPay'),
                    ('OTHER', 'Other'),
                ],
                help_text='Method used for payment',
                max_length=20,
            ),
        ),
    ]