# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2018-04-30 14:47
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('parliament', '0029_auto_20180323_1039'),
    ]

    operations = [
        migrations.AlterField(
            model_name='interjection',
            name='type',
            field=models.IntegerField(choices=[(1, 'Applause'), (2, 'Speech'), (3, 'Objection'), (4, 'Amusement'), (5, 'Laughter'), (6, 'Outcry')]),
        ),
    ]
