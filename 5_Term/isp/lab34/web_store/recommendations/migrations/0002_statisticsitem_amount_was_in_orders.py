# Generated by Django 3.1.7 on 2021-04-29 20:54

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recommendations', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='statisticsitem',
            name='amount_was_in_orders',
            field=models.IntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)]),
        ),
    ]
