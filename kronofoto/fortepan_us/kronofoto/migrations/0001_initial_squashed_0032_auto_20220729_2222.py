# Generated by Django 3.2.17 on 2023-02-16 20:15

import fortepan_us.kronofoto.models.photo
import fortepan_us.kronofoto.models.photosphere
import fortepan_us.kronofoto.models.tag
import fortepan_us.kronofoto.storage
from django.conf import settings
import django.contrib.gis.db.models.fields
import django.core.validators
from django.db import migrations, models
import django.db.migrations.operations.special
import django.db.models.deletion
import uuid


# Functions from the following migrations need manual copying.
# Move them and any dependencies into this file, then update the
# RunPython operations to refer to the local versions:
# archive.migrations.0016_auto_20210115_2030
def copy_circa(apps, schema_editor):
    CSVRecord = apps.get_model('kronofoto', 'CSVRecord')
    Photo = apps.get_model('kronofoto', 'Photo')
    for record in CSVRecord.objects.filter(photo__isnull=False, circa=True):
        record.photo.circa = record.circa
        record.photo.save()
# archive.migrations.0022_auto_20210407_2155
def gen_uuid(apps, schema_editor):
    MyModel = apps.get_model('kronofoto', 'Collection')
    for row in MyModel.objects.all():
        row.uuid = uuid.uuid4()
        row.save(update_fields=['uuid'])
# archive.migrations.0027_auto_20220621_0259
def copy_address(apps, schema_editor):
    CSVRecord = apps.get_model('kronofoto', 'CSVRecord')
    Photo = apps.get_model('kronofoto', 'Photo')
    for photo in Photo.objects.filter(csvrecord__isnull=False).exclude(csvrecord__address=''):
        photo.address = photo.csvrecord.address
        photo.save()

class Migration(migrations.Migration):

    replaces = [('kronofoto', '0001_initial'), ('kronofoto', '0002_wordcount'), ('kronofoto', '0003_auto_20200610_2212'), ('kronofoto', '0004_phototag_creator'), ('kronofoto', '0005_auto_20200825_0033'), ('kronofoto', '0006_auto_20200827_0209'), ('kronofoto', '0007_auto_20200904_2320'), ('kronofoto', '0008_auto_20200922_2139'), ('kronofoto', '0009_auto_20201001_2126'), ('kronofoto', '0010_auto_20201029_2210'), ('kronofoto', '0011_auto_20201029_2216'), ('kronofoto', '0012_newcutoff'), ('kronofoto', '0013_auto_20210111_2053'), ('kronofoto', '0014_auto_20210111_2258'), ('kronofoto', '0015_photo_circa'), ('kronofoto', '0016_auto_20210115_2030'), ('kronofoto', '0017_auto_20210326_2103'), ('kronofoto', '0018_auto_20210326_2116'), ('kronofoto', '0019_auto_20210331_2231'), ('kronofoto', '0020_auto_20210331_2238'), ('kronofoto', '0021_collection_uuid'), ('kronofoto', '0022_auto_20210407_2155'), ('kronofoto', '0023_auto_20210407_2155'), ('kronofoto', '0024_auto_20210923_2008'), ('kronofoto', '0025_auto_20211006_2126'), ('kronofoto', '0026_auto_20220621_0257'), ('kronofoto', '0027_auto_20220621_0259'), ('kronofoto', '0028_geocodecache_squashed_0030_rename_geocodecache_location'), ('kronofoto', '0029_photo_location_from_google'), ('kronofoto', '0030_auto_20220627_2037'), ('kronofoto', '0031_auto_20220630_2230'), ('kronofoto', '0032_auto_20220729_2222')]

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Donor',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('last_name', models.CharField(blank=True, max_length=256)),
                ('first_name', models.CharField(blank=True, max_length=256)),
                ('home_phone', models.CharField(blank=True, max_length=256)),
                ('street1', models.CharField(blank=True, max_length=256)),
                ('street2', models.CharField(blank=True, max_length=256)),
                ('city', models.CharField(blank=True, max_length=256)),
                ('state', models.CharField(blank=True, max_length=256)),
                ('zip', models.CharField(blank=True, max_length=256)),
                ('country', models.CharField(blank=True, max_length=256)),
            ],
            options={
                'ordering': ('last_name', 'first_name'),
                'index_together': {('last_name', 'first_name')},
            },
        ),
        migrations.CreateModel(
            name='Photo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False)),
                ('original', models.ImageField(editable=False, null=True, upload_to='')),
                ('h700', models.ImageField(editable=False, null=True, upload_to='')),
                ('thumbnail', models.ImageField(editable=False, null=True, upload_to='')),
                ('photographer', models.TextField(blank=True)),
                ('city', models.CharField(blank=True, max_length=128)),
                ('county', models.CharField(blank=True, max_length=128)),
                ('state', models.CharField(blank=True, max_length=64)),
                ('country', models.CharField(blank=True, max_length=64, null=True)),
                ('year', models.SmallIntegerField(blank=True, null=True)),
                ('caption', models.TextField(blank=True)),
                ('is_featured', models.BooleanField(default=False)),
                ('is_published', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('donor', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='kronofoto.donor')),
                ('scanner', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='photos_scanned', to='kronofoto.donor')),
            ],
        ),
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tag', fortepan_us.kronofoto.models.tag.LowerCaseCharField(max_length=64, unique=True)),
                ('slug', models.SlugField(blank=True, editable=False, unique=True)),
            ],
            options={
                'ordering': ('tag',),
            },
        ),
        migrations.CreateModel(
            name='Term',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('term', models.CharField(max_length=64, unique=True)),
                ('slug', models.SlugField(blank=True, editable=False, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='ScannedPhoto',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to='uploads/%Y/%m/%d/')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('accepted', models.BooleanField(null=True)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='scanned_photos', to='kronofoto.donor')),
                ('donor', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='kronofoto.donor')),
            ],
        ),
        migrations.CreateModel(
            name='PrePublishPhoto',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('photo', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='kronofoto.photo')),
            ],
        ),
        migrations.CreateModel(
            name='PhotoVote',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('infavor', models.BooleanField()),
                ('photo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='votes', related_query_name='vote', to='kronofoto.scannedphoto')),
                ('voter', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='PhotoTag',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('accepted', models.BooleanField()),
                ('photo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='kronofoto.photo')),
                ('tag', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='kronofoto.tag')),
                ('creator', models.ManyToManyField(editable=False, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='photo',
            name='tags',
            field=models.ManyToManyField(blank=True, through='kronofoto.PhotoTag', to='kronofoto.Tag'),
        ),
        migrations.AddField(
            model_name='photo',
            name='terms',
            field=models.ManyToManyField(blank=True, to='kronofoto.Term'),
        ),
        migrations.CreateModel(
            name='Collection',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=512)),
                ('visibility', models.CharField(choices=[('PR', 'Private'), ('UL', 'Unlisted'), ('PU', 'Public')], max_length=2)),
                ('owner', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('photos', models.ManyToManyField(blank=True, to='kronofoto.Photo')),
            ],
        ),
        migrations.CreateModel(
            name='WordCount',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('word', models.CharField(blank=True, max_length=64)),
                ('field', models.CharField(choices=[('CA', 'Caption'), ('TA', 'Tag'), ('TE', 'Term')], max_length=2)),
                ('count', models.FloatField()),
                ('photo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='kronofoto.photo')),
            ],
        ),
        migrations.AlterField(
            model_name='photo',
            name='year',
            field=models.SmallIntegerField(blank=True, db_index=True, null=True),
        ),
        migrations.CreateModel(
            name='NewCutoff',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
            ],
        ),
        migrations.CreateModel(
            name='CSVRecord',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('filename', models.TextField(unique=True)),
                ('donorFirstName', models.TextField()),
                ('donorLastName', models.TextField()),
                ('year', models.IntegerField(null=True)),
                ('circa', models.BooleanField(null=True)),
                ('scanner', models.TextField()),
                ('photographer', models.TextField()),
                ('address', models.TextField()),
                ('city', models.TextField()),
                ('county', models.TextField()),
                ('state', models.TextField()),
                ('country', models.TextField()),
                ('comments', models.TextField()),
                ('added_to_archive', models.DateField()),
                ('photo', models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, to='kronofoto.photo')),
            ],
        ),
        migrations.AddField(
            model_name='photo',
            name='circa',
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(
            code=copy_circa,
        ),
        migrations.AlterField(
            model_name='photo',
            name='donor',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='kronofoto.donor'),
        ),
        migrations.AddConstraint(
            model_name='photo',
            constraint=models.CheckConstraint(check=models.Q(('is_published', False), ('donor__isnull', False), _connector='OR'), name='never_published_without_donor'),
        ),
        migrations.AlterField(
            model_name='wordcount',
            name='field',
            field=models.CharField(choices=[('CA', 'Caption'), ('TA', 'Tag'), ('TE', 'Term')], db_index=True, max_length=2),
        ),
        migrations.AlterField(
            model_name='wordcount',
            name='word',
            field=models.CharField(blank=True, db_index=True, max_length=64),
        ),
        migrations.AlterIndexTogether(
            name='wordcount',
            index_together={('word', 'field')},
        ),
        migrations.AlterField(
            model_name='photo',
            name='city',
            field=models.CharField(blank=True, db_index=True, max_length=128),
        ),
        migrations.AlterField(
            model_name='photo',
            name='country',
            field=models.CharField(blank=True, db_index=True, max_length=64, null=True),
        ),
        migrations.AlterField(
            model_name='photo',
            name='county',
            field=models.CharField(blank=True, db_index=True, max_length=128),
        ),
        migrations.AlterField(
            model_name='photo',
            name='state',
            field=models.CharField(blank=True, db_index=True, max_length=64),
        ),
        migrations.AddField(
            model_name='collection',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, editable=False, null=True),
        ),
        migrations.RunPython(
            code=gen_uuid,
            reverse_code=django.db.migrations.operations.special.RunPython.noop,
        ),
        migrations.AlterField(
            model_name='collection',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.AddField(
            model_name='photo',
            name='location_bounds',
            field=django.contrib.gis.db.models.fields.MultiPolygonField(blank=True, null=True, srid=4326),
        ),
        migrations.AddField(
            model_name='photo',
            name='location_point',
            field=django.contrib.gis.db.models.fields.PointField(blank=True, null=True, srid=4326),
        ),
        migrations.AlterField(
            model_name='photo',
            name='original',
            field=models.ImageField(null=True, storage=fortepan_us.kronofoto.storage.OverwriteStorage(), upload_to=fortepan_us.kronofoto.models.photo.get_original_path),
        ),
        migrations.AlterField(
            model_name='photo',
            name='year',
            field=models.SmallIntegerField(blank=True, db_index=True, null=True, validators=[django.core.validators.MinValueValidator(limit_value=1800), django.core.validators.MaxValueValidator(limit_value=2021)]),
        ),
        migrations.AddField(
            model_name='photo',
            name='address',
            field=models.CharField(blank=True, db_index=True, max_length=128),
        ),
        migrations.AlterField(
            model_name='photo',
            name='year',
            field=models.SmallIntegerField(blank=True, db_index=True, null=True, validators=[django.core.validators.MinValueValidator(limit_value=1800), django.core.validators.MaxValueValidator(limit_value=2022)]),
        ),
        migrations.AlterField(
            model_name='tag',
            name='tag',
            field=fortepan_us.kronofoto.models.tag.LowerCaseCharField(editable=False, max_length=64, unique=True),
        ),
        migrations.RunPython(
            code=copy_address,
        ),
        migrations.CreateModel(
            name='Location',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('description', models.TextField(unique=True)),
                ('location_point', django.contrib.gis.db.models.fields.PointField(blank=True, null=True, srid=4326)),
                ('location_bounds', django.contrib.gis.db.models.fields.MultiPolygonField(blank=True, null=True, srid=4326)),
            ],
        ),
        migrations.AddField(
            model_name='photo',
            name='location_from_google',
            field=models.BooleanField(default=False, editable=False),
        ),
        migrations.CreateModel(
            name='PhotoSphere',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False)),
                ('name', models.CharField(max_length=512)),
                ('image', models.ImageField(null=True, storage=fortepan_us.kronofoto.storage.OverwriteStorage(), upload_to=fortepan_us.kronofoto.models.photosphere.get_photosphere_path)),
                ('heading', models.FloatField(default=0, validators=[django.core.validators.MinValueValidator(limit_value=-180), django.core.validators.MaxValueValidator(limit_value=180)])),
                ('location', django.contrib.gis.db.models.fields.PointField(blank=True, null=True, srid=4326)),
            ],
        ),
        migrations.CreateModel(
            name='PhotoSpherePair',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('azimuth', models.FloatField(default=0, validators=[django.core.validators.MinValueValidator(limit_value=-180), django.core.validators.MaxValueValidator(limit_value=180)])),
                ('inclination', models.FloatField(default=0, validators=[django.core.validators.MinValueValidator(limit_value=-90), django.core.validators.MaxValueValidator(limit_value=90)])),
                ('distance', models.FloatField(default=500, validators=[django.core.validators.MinValueValidator(limit_value=1), django.core.validators.MaxValueValidator(limit_value=2000)])),
                ('photo', models.ForeignKey(help_text='Select a photo then click Save and Continue Editing to use the interactive tool', on_delete=django.db.models.deletion.CASCADE, to='kronofoto.photo')),
                ('photosphere', models.ForeignKey(help_text='Select a photo and photo sphere then click Save and Continue Editing to use the interactive tool', on_delete=django.db.models.deletion.CASCADE, to='kronofoto.photosphere')),
            ],
            options={
                'verbose_name': 'Photo position',
            },
        ),
        migrations.AddField(
            model_name='photosphere',
            name='photos',
            field=models.ManyToManyField(through='kronofoto.PhotoSpherePair', to='kronofoto.Photo'),
        ),
        migrations.AlterModelOptions(
            name='term',
            options={'ordering': ['term']},
        ),
        migrations.AddField(
            model_name='photosphere',
            name='description',
            field=models.TextField(default=''),
            preserve_default=False,
        ),
    ]
