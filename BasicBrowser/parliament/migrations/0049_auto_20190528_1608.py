# Generated by Django 2.2 on 2019-05-28 16:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('parliament', '0048_person_creation_date'),
    ]

    operations = [
        migrations.AlterField(
            model_name='person',
            name='creation_date',
            field=models.DateTimeField(auto_now_add=True, null=True, verbose_name='Date of entry creation'),
        ),
    ]
