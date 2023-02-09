# Generated by Django 3.2.17 on 2023-02-09 06:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('archive', '0037_auto_20230209_0445'),
    ]

    operations = [
        migrations.AlterField(
            model_name='photo',
            name='tags',
            field=models.ManyToManyField(blank=True, db_index=True, through='archive.PhotoTag', to='archive.Tag'),
        ),
    ]
