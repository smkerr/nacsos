# Generated by Django 2.2.2 on 2021-09-14 11:34

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('scoping', '0341_docusercat_texts'),
    ]

    operations = [
        migrations.RenameField(
            model_name='query',
            old_name='collections',
            new_name='editions',
        ),
        migrations.RenameField(
            model_name='query',
            old_name='wos_db',
            new_name='wos_collections',
        ),
    ]
