# Generated by Django 5.1.7 on 2025-03-08 11:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='company_email',
            field=models.EmailField(blank=True, max_length=254),
        ),
    ]
