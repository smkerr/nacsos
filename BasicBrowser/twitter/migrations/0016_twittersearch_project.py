# Generated by Django 2.1.2 on 2019-02-05 10:42

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('scoping', '0257_wosarticle_ems'),
        ('twitter', '0015_auto_20190109_1616'),
    ]

    operations = [
        migrations.AddField(
            model_name='twittersearch',
            name='project',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='scoping.Project'),
        ),
    ]
