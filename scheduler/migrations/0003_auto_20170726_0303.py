# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-07-26 03:03
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scheduler', '0002_auto_20170721_1544'),
    ]

    operations = [
        migrations.AddField(
            model_name='service',
            name='callDays',
            field=models.IntegerField(default=0, verbose_name='Call Days This Month'),
        ),
        migrations.AddField(
            model_name='service',
            name='callDaysYTD',
            field=models.IntegerField(default=0, verbose_name='Call Days YTD'),
        ),
        migrations.AddField(
            model_name='service',
            name='wkndcallDays',
            field=models.IntegerField(default=0, verbose_name='Weekend Call Days This Month'),
        ),
        migrations.AddField(
            model_name='service',
            name='wkndcallDaysTYD',
            field=models.IntegerField(default=0, verbose_name='Weekend Call Days YTD'),
        ),
        migrations.AlterField(
            model_name='service',
            name='onservice',
            field=models.IntegerField(choices=[(1, 'Trauma'), (2, 'Hepatobiliary / Transplant'), (3, 'Vascular'), (4, 'Colorectal'), (5, 'Breast'), (6, 'Gen Surg - Gold'), (7, 'Gen Surg - Blue'), (8, 'Gen Surg - Orange'), (9, 'Plastics'), (10, 'PCH'), (11, 'Thoracic'), (12, 'Anesthesia / IR'), (13, 'Critical Care'), (14, 'Harding'), (15, 'Other')], verbose_name='Service'),
        ),
    ]
