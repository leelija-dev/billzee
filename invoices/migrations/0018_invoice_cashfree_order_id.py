# Generated by Django 5.0.4 on 2025-04-09 07:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0017_invoice_paypal_payment_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='cashfree_order_id',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
