# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2016-12-12 12:29
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scoping', '0015_auto_20161212_1220'),
    ]

    operations = [
        migrations.AlterField(
            model_name='wosarticle',
            name='em',
            field=models.TextField(null=True),
        ),
    ]
