# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-07-21 15:44
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('scheduler', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='resident',
            name='fname',
            field=models.CharField(blank=True, max_length=50, verbose_name='First Name'),
        ),
        migrations.AddField(
            model_name='resident',
            name='lname',
            field=models.CharField(blank=True, max_length=50, verbose_name='Last Name'),
        ),
        migrations.AddField(
            model_name='service',
            name='year',
            field=models.IntegerField(choices=[(2017, 2017), (2018, 2018), (2019, 2019)], default=2017, verbose_name='Year'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='day',
            name='date',
            field=models.DateField(verbose_name='On Call Day'),
        ),
        migrations.AlterField(
            model_name='day',
            name='residents',
            field=models.ManyToManyField(to='scheduler.Resident', verbose_name='Residents on Call'),
        ),
        migrations.AlterField(
            model_name='dayoff',
            name='date',
            field=models.DateField(verbose_name='PTO Date'),
        ),
        migrations.AlterField(
            model_name='resident',
            name='PTO',
            field=models.ManyToManyField(blank=True, to='scheduler.DayOff', verbose_name='PTO Requested Days'),
        ),
        migrations.AlterField(
            model_name='resident',
            name='name',
            field=models.CharField(blank=True, max_length=50, verbose_name='Resident Name'),
        ),
        migrations.AlterField(
            model_name='resident',
            name='noCallDays',
            field=models.IntegerField(default=0, verbose_name='Number of Call Days'),
        ),
        migrations.AlterField(
            model_name='resident',
            name='noWkndCallDays',
            field=models.IntegerField(default=0, verbose_name='Number of Weekend Call Days'),
        ),
        migrations.AlterField(
            model_name='resident',
            name='year',
            field=models.IntegerField(choices=[(1, 'PGY1'), (2, 'PGY2'), (3, 'PGY3'), (4, 'PGY4'), (5, 'PGY5')], verbose_name='Year of Service'),
        ),
        migrations.AlterField(
            model_name='service',
            name='month',
            field=models.IntegerField(choices=[(1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'), (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'), (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')], verbose_name='Month of Year'),
        ),
        migrations.AlterField(
            model_name='service',
            name='onservice',
            field=models.IntegerField(choices=[(1, 'Trauma'), (2, 'Hepatobiliary / Transplant'), (3, 'Vascular'), (4, 'Colorectal'), (5, 'Breast'), (6, 'Gen Surg - Gold'), (7, 'Gen Surg - Blue'), (8, 'Gen Surg - Orange'), (9, 'Plastics'), (10, 'PCH'), (11, 'Thoracic'), (12, 'Anesthesia / IR'), (13, 'Other')], verbose_name='Service'),
        ),
        migrations.AlterField(
            model_name='service',
            name='res',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='scheduler.Resident', verbose_name='Resident on Service'),
        ),
    ]
