# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-07-26 20:41
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scheduler', '0005_auto_20170726_2039'),
    ]

    operations = [
        migrations.AddField(
            model_name='resident',
            name='noCallDays',
            field=models.IntegerField(default=0, verbose_name='Number of Call Days'),
        ),
        migrations.AddField(
            model_name='resident',
            name='noWkndCallDays',
            field=models.IntegerField(default=0, verbose_name='Number of Weekend Call Days'),
        ),
    ]
