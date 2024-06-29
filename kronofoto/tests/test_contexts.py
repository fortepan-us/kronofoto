from django.test.utils import override_settings
from django.test import Client, RequestFactory
from django.http import Http404
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import AnonymousUser, User, Permission
from django.urls import reverse
from hypothesis.extra.django import from_model, register_field_strategy, TestCase
from unittest.mock import Mock
from hypothesis import strategies as st, given, note, settings
import pytest
from pytest_django.asserts import assertTemplateUsed, assertRedirects
from archive.models.photo import Photo
from archive.models.photosphere import PhotoSphere
from archive.models.archive import Archive
from archive.models.donor import Donor
from archive.models import Category
from archive.views.photo import PhotoView
from django.core.files.uploadedfile import SimpleUploadedFile
from .util import photos, donors, archives, small_gif

class Tests(TestCase):

    def test_photo_permissions(self):
        from archive.templatetags.permissions import PhotoPermissions
        archive = Archive.objects.create(slug="slug")
        donor = Donor.objects.create(archive=archive)
        category = Category.objects.create()
        photo = Photo.objects.create(archive=archive, donor=donor, category=category, is_published=True, year=1900, original=SimpleUploadedFile('small.gif', small_gif, content_type='image/gif'))
        permission_list = PhotoPermissions(photo).permissions
        assert 'archive.change_photo' in permission_list
        assert 'archive.view_photo' in permission_list
        assert 'archive.archive.slug.change_photo' in permission_list
        assert 'archive.archive.slug.view_photo' in permission_list

    def test_permission_list_factory_only_handles_photos(self):
        from archive.templatetags.permissions import PermissionListFactory
        with pytest.raises(NotImplementedError):
            PermissionListFactory().permission_list([1,2,3])

    def test_permission_list_factory_handles_photos(self):
        from archive.templatetags.permissions import PermissionListFactory, PhotoPermissions
        archive = Archive.objects.create(slug="slug")
        donor = Donor.objects.create(archive=archive)
        category = Category.objects.create()
        photo = Photo.objects.create(archive=archive, donor=donor, category=category, is_published=True, year=1900, original=SimpleUploadedFile('small.gif', small_gif, content_type='image/gif'))
        assert isinstance(PermissionListFactory().permission_list(photo), PhotoPermissions)


    def test_permissioned_staff_must_have_privs(self):
        from archive.templatetags.permissions import has_view_or_change_permission
        archive = Archive.objects.create(slug="slug")
        donor = Donor.objects.create(archive=archive)
        category = Category.objects.create()
        photo = Photo.objects.create(archive=archive, donor=donor, category=category, is_published=True, year=1900, original=SimpleUploadedFile('small.gif', small_gif, content_type='image/gif'))
        user = User.objects.create_user(username="test_user", is_staff=True)
        assert not has_view_or_change_permission(user, photo)

    def test_permissioned_permissions_must_be_staff(self):
        from archive.templatetags.permissions import has_view_or_change_permission
        archive = Archive.objects.create(slug="slug")
        donor = Donor.objects.create(archive=archive)
        category = Category.objects.create()
        photo = Photo.objects.create(archive=archive, donor=donor, category=category, is_published=True, year=1900, original=SimpleUploadedFile('small.gif', small_gif, content_type='image/gif'))
        user = User.objects.create_user(username="test_user", is_staff=True)
        assert not has_view_or_change_permission(user, photo)

    def test_permissioned_staff_have_privs(self):
        from archive.templatetags.permissions import has_view_or_change_permission
        archive = Archive.objects.create(slug="slug")
        donor = Donor.objects.create(archive=archive)
        category = Category.objects.create()
        photo = Photo.objects.create(archive=archive, donor=donor, category=category, is_published=True, year=1900, original=SimpleUploadedFile('small.gif', small_gif, content_type='image/gif'))
        from django.contrib.contenttypes.models import ContentType
        ct = ContentType.objects.get_for_model(Photo)
        permission = Permission.objects.get(content_type=ct, codename="change_photo")
        user = User.objects.create_user(username="test_user", is_staff=False)
        user.user_permissions.add(permission)
        assert not has_view_or_change_permission(user, photo)

    @settings(max_examples=5)
    @given(archive=archives(), id=st.integers(min_value=1, max_value=100000))
    def test_photo_get_object(self, archive, id):
        photoview = PhotoView()
        photoview.kwargs = {'photo': id}
        if Archive.objects.filter(id=id).exists():
            assert id == photoview.get_object(Archive.objects.all()).id
        else:
            with pytest.raises(Http404):
                photoview.get_object(Archive.objects.all())



    @settings(max_examples=1)
    @given(from_model(PhotoSphere.photos.through, photo=photos(), photosphere=from_model(PhotoSphere, id=st.none(), image=st.builds(lambda: SimpleUploadedFile('small.gif', small_gif, content_type='image/gif')))))
    def test_photosphere_context(self, pair):
        resp = Client().get(f"{reverse('kronofoto:mainstreetview')}?id={pair.id}")

        assertTemplateUsed(resp, 'archive/photosphere_detail.html')
        assert resp.status_code == 200
        assert 'object' in resp.context and resp.context['object'].id == pair.photosphere.id
