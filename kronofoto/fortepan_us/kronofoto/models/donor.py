from django.db import models
from django.db.models import Count, QuerySet
from django.contrib.auth import get_user_model
from django.db.models import Count, Q, Exists, OuterRef, F, Subquery, Func
from django.conf import settings
from .collectible import Collectible
from .archive import Archive
from typing_extensions import Self
from typing import final, Any, Type, List, TYPE_CHECKING


class DonorQuerySet(models.QuerySet):
    def annotate_photographedcount(self) -> Self:
        Photo: Any = self.model._meta.get_field("kronofoto_photo_photographed").related_model  # type: ignore
        q = (
            Photo.objects.filter(photographer=OuterRef("id"))
            .annotate(count=Func(F("id"), function="COUNT"))
            .values("count")[:1]
        )
        return self.annotate(photographed_count=Subquery(q))

    def annotate_scannedcount(self) -> Self:
        Photo: Any = self.model._meta.get_field("kronofoto_photo_scanned").related_model  # type: ignore
        q = (
            Photo.objects.filter(scanner=OuterRef("id"))
            .annotate(scanned_count=Func(F("id"), function="COUNT"))
            .values("scanned_count")[:1]
        )
        return self.annotate(scanned_count=Subquery(q))

    def annotate_donatedcount(self) -> Self:
        Photo: Any = self.model._meta.get_field("photo").related_model  # type: ignore
        q = (
            Photo.objects.filter(donor=OuterRef("id"))
            .annotate(donated_count=Func(F("id"), function="COUNT"))
            .values("donated_count")[:1]
        )
        return self.annotate(donated_count=Subquery(q))

    def filter_donated(self) -> Self:
        Photo: Any = self.model._meta.get_field("photo").related_model  # type: ignore
        q = Photo.objects.filter(
            donor__id=OuterRef("pk"), is_published=True, year__isnull=False
        )
        return self.filter(Exists(q))


class Donor(Collectible, models.Model):
    archive = models.ForeignKey(Archive, models.PROTECT, null=False)
    last_name = models.CharField(max_length=257, blank=True)
    first_name = models.CharField(max_length=256, blank=True)
    email = models.EmailField(blank=True)
    home_phone = models.CharField(max_length=256, blank=True)
    street1 = models.CharField(max_length=256, blank=True)
    street2 = models.CharField(max_length=256, blank=True)
    city = models.CharField(max_length=256, blank=True)
    state = models.CharField(max_length=256, blank=True)
    zip = models.CharField(max_length=256, blank=True)
    country = models.CharField(max_length=256, blank=True)

    objects = DonorQuerySet.as_manager()

    class Meta:
        ordering = ("last_name", "first_name")
        indexes = (models.Index(fields=["last_name", "first_name"]),)

    def display_format(self) -> str:
        return (
            "{first} {last}".format(first=self.first_name, last=self.last_name)
            if self.first_name
            else self.last_name
        )

    def __str__(self) -> str:
        if self.first_name or self.last_name:
            return (
                "{last}, {first}".format(first=self.first_name, last=self.last_name)
                if self.first_name
                else self.last_name
            )
        return "Unnamed contributor"

    def encode_params(self, params: Any) -> Any:
        params["donor"] = self.id
        return params.urlencode()

    @staticmethod
    def index() -> Any:
        return [
            {
                "name": "{last}, {first}".format(
                    last=donor.last_name, first=donor.first_name
                ),
                "count": donor.count,
                "href": donor.get_absolute_url(),
            }
            for donor in Donor.objects.annotate(count=Count("photo__id"))
            .order_by("last_name", "first_name")
            .filter(count__gt=0)
        ]
