# Generated by Django 2.0.5 on 2018-07-04 18:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scoping', '0208_auto_20180704_1746'),
    ]

    operations = [
        migrations.AlterField(
            model_name='wosarticle',
            name='so',
            field=models.TextField(help_text='Enter the name of the journal or the title of the book', null=True, verbose_name='Publication Name'),
        ),
    ]
