from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from django.utils.safestring import mark_safe
from .models import Photo, Tag, Term, PhotoTag
from django.conf import settings
from django.urls import reverse

@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    pass


class TagInline(admin.TabularInline):
    model = PhotoTag
    extra = 1


@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    readonly_fields = ["h700_image"]
    inlines = (TagInline,)
    list_filter = ('phototag__accepted',)
    list_display = ('thumb_image', 'accession_number', 'year', 'caption')

    def thumb_image(self, obj):
        return mark_safe('<img src="{}" width="{}" height="{}" />'.format(obj.thumbnail.url, obj.thumbnail.width, obj.thumbnail.height))

    def h700_image(self, obj):
        return mark_safe('<img src="{}" width="{}" height="{}" />'.format(obj.h700.url, obj.h700.width, obj.h700.height))

class UserTagInline(admin.TabularInline):
    model = PhotoTag.creator.through
    extra = 0
    fields = ['thumb_image', 'tag', 'accepted']
    readonly_fields = ['thumb_image', 'tag', 'accepted']
    verbose_name_plural = "??????"

    def thumb_image(self, instance):
        return mark_safe(
            '<a href="{edit_url}"><img src="{thumb}" width="{width}" height="{height}" /></a>'.format(
                edit_url=reverse('admin:archive_photo_change', args=(instance.phototag.photo.id,)),
                thumb=instance.phototag.photo.thumbnail.url,
                width=instance.phototag.photo.thumbnail.width,
                height=instance.phototag.photo.thumbnail.height,
            )
        )

    def tag(self, instance):
        return instance.phototag.tag.tag

    def accepted(self, instance):
        return 'yes' if instance.phototag.accepted else 'no'

class KronofotoUserAdmin(UserAdmin):
    inlines = (UserTagInline,)

admin.site.unregister(User)
admin.site.register(User, KronofotoUserAdmin)
