# Generated by Django 2.2.15 on 2020-08-27 02:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('archive', '0005_auto_20200825_0033'),
    ]

    operations = [
        migrations.AlterField(
            model_name='photo',
            name='year',
            field=models.SmallIntegerField(blank=True, db_index=True, null=True),
        ),
    ]