# Generated by Django 3.2.21 on 2023-09-14 06:21

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('archive', '0065_alter_donor_users_starred_by'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='photo',
            name='photographer',
        ),
        migrations.RemoveField(
            model_name='submission',
            name='photographer',
        ),
    ]
