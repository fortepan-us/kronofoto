# Generated by Django 4.2.9 on 2024-08-23 22:59

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        (
            "kronofoto",
            "0120_rename_archive_car_exhibit_75935e_idx_kronofoto_c_exhibit_992bd5_idx_and_more",
        ),
    ]

    operations = [
        migrations.RemoveField(
            model_name="card",
            name="card_style",
        ),
        migrations.AddField(
            model_name="photocard",
            name="fill_style",
            field=models.IntegerField(
                choices=[(1, "Contain"), (2, "Cover")], default=1
            ),
        ),
        migrations.AlterField(
            model_name="card",
            name="description",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AlterField(
            model_name="photocard",
            name="alignment",
            field=models.IntegerField(
                choices=[(1, "Full"), (2, "Left"), (3, "Right")], default=1
            ),
        ),
    ]
