# Generated by Django 3.2.19 on 2023-09-05 03:56

import archive.models.photo
from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('archive', '0059_alter_photo_caption'),
    ]

    operations = [
        migrations.CreateModel(
            name='ArchiveAgreement',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.TextField()),
                ('version', models.DateTimeField(auto_now=True)),
                ('archive', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='archive.archive')),
            ],
            options={
                'verbose_name': 'agreement',
            },
        ),
        migrations.AlterField(
            model_name='photo',
            name='scanner',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='archive_photo_scanned', to='archive.donor'),
        ),
        migrations.CreateModel(
            name='UserAgreement',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('agreement', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='archive.archiveagreement')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Submission',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False)),
                ('photographer', models.CharField(blank=True, max_length=128)),
                ('address', models.CharField(blank=True, db_index=True, max_length=128)),
                ('city', models.CharField(blank=True, db_index=True, max_length=128)),
                ('county', models.CharField(blank=True, db_index=True, max_length=128)),
                ('state', models.CharField(blank=True, db_index=True, max_length=64)),
                ('country', models.CharField(blank=True, db_index=True, max_length=64, null=True)),
                ('year', models.SmallIntegerField(blank=True, db_index=True, null=True, validators=[django.core.validators.MinValueValidator(limit_value=1800), django.core.validators.MaxValueValidator(limit_value=2023)])),
                ('circa', models.BooleanField(default=False)),
                ('caption', models.TextField(blank=True, verbose_name='comment')),
                ('image', models.ImageField(editable=False, upload_to=archive.models.photo.get_submission_path)),
                ('archive', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='archive.archive')),
                ('donor', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='archive.donor')),
                ('scanner', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='archive_submission_scanned', to='archive.donor')),
                ('uploader', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddIndex(
            model_name='useragreement',
            index=models.Index(fields=['agreement', 'user'], name='archive_use_agreeme_984b80_idx'),
        ),
        migrations.AddConstraint(
            model_name='useragreement',
            constraint=models.UniqueConstraint(fields=('agreement', 'user'), name='unique_agreement_user'),
        ),
    ]
