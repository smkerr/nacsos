# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2017-03-22 13:57
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scoping', '0065_auto_20170322_1328'),
    ]

    operations = [
        migrations.AddField(
            model_name='query',
            name='dlstat',
            field=models.CharField(max_length=6, null=True, verbose_name='Query download status'),
        ),
    ]
