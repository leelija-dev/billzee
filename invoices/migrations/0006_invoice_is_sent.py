# Generated by Django 5.1.7 on 2025-03-08 19:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0005_invoice_profile'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='is_sent',
            field=models.BooleanField(default=False, help_text='Indicates if the invoice has been sent to the customer'),
        ),
    ]
