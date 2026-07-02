from __future__ import annotations
from django.contrib.gis.db import models
import icontract
from django_stubs_ext import WithAnnotations
import base64
import json
from django.core.files.storage import default_storage
from django.http import QueryDict
from django.core.signing import Signer
from django.db import transaction
from django.db.models import (
    Q,
    Window,
    F,
    Min,
    Subquery,
    Count,
    OuterRef,
    Sum,
    Max,
    QuerySet,
)
from django.db.models.functions import Lower
from django.db.models.signals import post_delete, pre_delete
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.core.files.uploadedfile import InMemoryUploadedFile
from fortepan_us.kronofoto.reverse import reverse
from django.utils.http import urlencode
from datetime import datetime
import uuid
from PIL import Image, ExifTags, ImageOps, UnidentifiedImageError
from io import BytesIO
import os
from os import path
import operator
from bisect import bisect_left
from functools import reduce
from fortepan_us.kronofoto.storage import OverwriteStorage
from .donor import Donor, DonorQuerySet
from .tag import Tag, TagQuerySet
from .archive import Archive, RemoteActor
from .category import Category
from .place import Place
import requests
from dataclasses import dataclass
from django.core.cache import cache
from typing import (
    Dict,
    Any,
    List,
    Sequence,
    Optional,
    Set,
    Tuple,
    Protocol,
    TypedDict,
    Callable,
    Iterable,
    overload,
    Union,
)
from typing_extensions import Self
from fortepan_us.kronofoto.imageutil import ImageSigner
from itertools import chain, cycle, islice
from typing import Dict, Any, List, Optional, Set, Tuple, Protocol, TypeVar, Generic
from typing_extensions import Self
#from .activity_dicts import ActivitypubImage, PhotoValue

EMPTY_PNG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
bisect = lambda xs, x: min(bisect_left(xs, x), len(xs) - 1)

DonorQuerySetT = TypeVar("DonorQuerySetT", bound=models.QuerySet[Donor])

class Thumbnail(TypedDict):
    url: str
    height: int
    width: int


EMPTY_THUMBNAIL = Thumbnail(url=EMPTY_PNG, height=75, width=75)
@dataclass
class License:
    name: str
    url: str
    staticfile: str

LICENSES = {
    "CC-BY-SA-4.0": License(
        name="Attribution-ShareAlike 4.0 International",
        url="https://creativecommons.org/licenses/by-sa/4.0/",
        staticfile="kronofoto/images/Creative-Commons-Icons.svg",
    ),
    "CC-BY-NC-SA-4.0": License(
        name="Attribution-NonCommercial-ShareAlike 4.0 International",
        url="https://creativecommons.org/licenses/by-nc-sa/4.0/",
        staticfile="kronofoto/images/cc-by-nc-sa.svg",
    ),
}


class PhotoQuerySet(models.QuerySet["Photo"]):
    def filter_donated(self, donors: DonorQuerySetT) -> DonorQuerySetT:
        """Filter a Donor queryset to only those that have donated images, as
        opposed to scanning or photographing images.

        Args:
            donors (DonorQuerySetT): A donor query set

        Returns:
            DonorQuerySetT: Donors that have not donated a photo are excluded from the donors.
        """
        q = self.filter(donor__id=OuterRef("pk"), is_published=True, year__isnull=False)
        return donors.filter(models.Exists(q))

    def with_scanned_annotation(self, donors: DonorQuerySetT) -> DonorQuerySetT:
        """Annotate a donor query set with counts of photos scanned by the donor.

        Args:
            donors (DonorQuerySetT): The donors to annotate.

        Returns:
            DonorQuerySetT: The donors query set with a `scanned_count` which is a count of the images scanned by the donor.
        """
        q = (
            self.filter(scanner=OuterRef("id"))
            .annotate(scanned_count=models.Func(F("id"), function="COUNT"))
            .values("scanned_count")[:1]
        )
        return donors.annotate(scanned_count=Subquery(q))

    def with_donated_annotation(self, donors: DonorQuerySetT) -> DonorQuerySetT:
        """Annotate a donor query set with counts of photos donated by the donor.

        Args:
            donors (DonorQuerySetT): The donors to annotate.

        Returns:
            DonorQuerySetT: The donors query set with a `donated_count` which is a count of the images donated by the donor.
        """
        q = (
            self.filter(donor=OuterRef("id"))
            .annotate(donated_count=models.Func(F("id"), function="COUNT"))
            .values("donated_count")[:1]
        )
        return donors.annotate(donated_count=Subquery(q))

    def with_photographed_annotation(self, donors: DonorQuerySetT) -> DonorQuerySetT:
        """Annotate a donor query set with counts of photos photographed by the donor.

        Args:
            donors (DonorQuerySetT): The donors to annotate.

        Returns:
            DonorQuerySetT: The donors query set with a `photographed_count` which is a count of the images photographed by the donor.
        """
        q = (
            self.filter(photographer=OuterRef("id"))
            .annotate(count=models.Func(F("id"), function="COUNT"))
            .values("count")[:1]
        )
        return donors.annotate(photographed_count=Subquery(q))

    def year_range(self) -> Dict[str, Any]:
        """Determine the first year and last year for photos in this query set.

        Returns:
            dict[str, Any]: The dict has `start` and `end` keys first first and last year.
        """
        return self.aggregate(end=Max("year"), start=Min("year"))

    def photos_before(self, *, year: int, id: int) -> Self:
        """Given a year and an id number, filter this query set to those appearing before that point in the query set, in reverse order.

        Args:
            year (int): A year.
            id (int): A photo ID

        Returns:
            PhotoQuerySet: This queryset in reverse archive order starting at the position given by `year` and `id`.
        """
        photos = self.filter(Q(year__lt=year) | Q(year=year, id__lt=id)).order_by(
            "-year", "-id"
        )
        return photos

    def photos_after(self, *, year: int, id: int) -> Self:
        """Given a year and an id number, filter this query set to those appearing after that point in the query set, in order.

        Args:
            year (int): A year.
            id (int): A photo ID

        Returns:
            PhotoQuerySet: This queryset in archive order starting at the position given by `year` and `id`.
        """
        photos = self.filter(Q(year__gt=year) | Q(year=year, id__gt=id)).order_by(
            "year", "id"
        )
        return photos

def format_location(force_country: bool = False, **kwargs: str) -> str:
    """Deprecated"""
    parts = []
    if kwargs.get("address", None):
        parts.append(kwargs["address"])
    if kwargs.get("city", None):
        parts.append(kwargs["city"])
    if kwargs.get("county", None):
        parts.append("{} County".format(kwargs["county"]))
    if kwargs.get("state", None):
        parts.append(kwargs["state"])
    if (force_country or not parts) and "country" in kwargs:
        parts.append(kwargs["country"])
    s = ", ".join(parts)
    return s or "Location: n/a"


def get_original_path(instance: "Photo", filename: str) -> str:
    """Generate a storage path for a Photo.

    Args:
        instance (Photo): The Photo being stored.
        filename (str): Ignored

    Returns:
        str: A storage path, which is incidentally based on the Photo's UUID and its creation time.
    """
    created = datetime.now() if instance.created is None else instance.created
    return path.join(
        "original",
        str(created.year),
        str(created.month),
        str(created.day),
        "{}.jpg".format(instance.uuid),
    )


def get_submission_path(instance: "Submission", filename: str) -> str:
    """Generate a storage path for a Submission.

    Args:
        instance (Submission): The Submission being stored.
        filename (str): Ignored

    Returns:
        str: A storage path, which is incidentally based on the Submission's UUID.
    """
    return path.join("submissions", "{}.jpg".format(instance.uuid))


@dataclass
class PlaceData:
    "Deprecated."
    address: str
    city: str
    county: str
    state: str
    country: str

    def get_query(self) -> str:
        parts = []
        if self.city:
            parts.append('city:"{}"'.format(self.city))
        if not self.city and self.county:
            parts.append('county:"{}"'.format(self.county))
        if self.state:
            parts.append('state:"{}"'.format(self.state))
        if self.country:
            parts.append('country:"{}"'.format(self.country))

        return " AND ".join(parts)


class PhotoBase(models.Model):
    """Abstract Base for Photo and Submission. It is the core model of this
    application.

    Photos belong to Archives.

    They have a Category, specifying whether this is a photo or map or something else.

    Photos are donated by Donors, scanned by Donors, and photographed by Donors.

    Photos have Terms, which are curated labels given by the archivists.

    They have a Place and a time (year), which is sometimes vague (circa).

    They also have a location_point is the exact location is known.

    And of course, they also have a description.
    """
    archive = models.ForeignKey(Archive, on_delete=models.PROTECT, null=False)
    category = models.ForeignKey(Category, models.PROTECT, null=False)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    donor = models.ForeignKey(Donor, models.PROTECT, null=True)
    terms = models.ManyToManyField("kronofoto.Term", blank=True)
    photographer = models.ForeignKey(
        Donor,
        models.PROTECT,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_photographed",
    )
    address = models.CharField(max_length=128, blank=True)
    city = models.CharField(max_length=128, blank=True)
    county = models.CharField(max_length=128, blank=True)
    state = models.CharField(max_length=64, blank=True)
    country = models.CharField(max_length=64, null=True, blank=True)
    place = models.ForeignKey(
        Place,
        models.PROTECT,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_place",
    )
    location_point = models.PointField(null=True, srid=4326, blank=True)
    year = models.SmallIntegerField(
        null=True,
        blank=True,
        db_index=True,
        validators=[
            MinValueValidator(limit_value=1800),
            MaxValueValidator(limit_value=datetime.now().year),
        ],
    )
    circa = models.BooleanField(default=False)
    caption = models.TextField(blank=True, verbose_name="comment")
    license = models.CharField(max_length=64, blank=False, default="CC-BY-SA-4.0", null=False, choices=[(code, license.name) for code, license in LICENSES.items()])

    scanner = models.ForeignKey(
        Donor,
        null=True,
        on_delete=models.SET_NULL,
        blank=True,
        related_name="%(app_label)s_%(class)s_scanned",
    )

    def get_place(self, with_address: bool = False) -> PlaceData:
        "Deprecated."
        return PlaceData(
            address=self.address,
            city=self.city,
            county=self.county,
            state=self.state,
            country=self.country or "",
        )

    @property
    def place_query(self) -> str:
        "Deprecated."
        return self.get_place().get_query()

    def location(self, with_address: bool = False, force_country: bool = False) -> str:
        "Deprecated."
        kwargs: Dict[str, str] = dict(
            city=self.city,
            state=self.state,
            county=self.county,
        )
        if self.country:
            kwargs["country"] = self.country
        if with_address:
            kwargs["address"] = self.address
        if self.city:
            del kwargs["county"]
        return format_location(force_country=force_country, **kwargs)

    @property
    def licensedef(self) -> License:
        return LICENSES[self.license]

    class Meta:
        abstract = True


class Submission(PhotoBase):
    """A model for user submitted Photos. They submitted to Archives and
    expected to be curated or rejected.
    """
    image = models.ImageField(upload_to=get_submission_path, null=False)
    uploader = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True
    )

    def __str__(self) -> str:
        """Get a short description of this Submission for the admin.

        Returns:
            str: A description including the year and place.
        """
        location = self.place
        stuff = [str(self.donor)]
        if self.year:
            stuff.append(str(self.year))
        if location:
            stuff.append(location.fullname)
        return " - ".join(stuff)


class ResizerBase(Protocol):
    """Base for resize images functions."""
    @property
    def output_height(self) -> int:
        "Desired height"
        ...
    @property
    def output_width(self) -> int:
        "Desired width"
        ...
    def crop_image(self, *, image: Image.Image) -> Image.Image:
        """Abstract method that allows a subclass to crop the image and change its aspect ratio.

        Returns:
            Image.Image: An image with the desired aspect ratio.
        """
        ...

    def resize(self, *, image: Image.Image) -> Image.Image:
        """Resize an image to the target size.

        Returns:
            Image.Image: The resized Image.
        """
        image = self.crop_image(image=image)
        return image.resize(
            (self.output_width, self.output_height),
            Image.Resampling.LANCZOS,
        )


@dataclass
class FixedHeightResizer(ResizerBase):
    """A class that resizes Images to a specific height without changing the
    aspect ratio.
    """
    height: int
    original_width: int
    original_height: int

    def crop_image(self, *, image: Image.Image) -> Image.Image:
        return image

    @property
    def output_height(self) -> int:
        return self.height

    @property
    def output_width(self) -> int:
        return round(self.original_width * self.height / self.original_height)


@dataclass
class FixedWidthResizer(ResizerBase):
    """A class that resizes Images to a specific width without changing the
    aspect ratio.
    """
    width: int
    original_width: int
    original_height: int

    def crop_image(self, *, image: Image.Image) -> Image.Image:
        return image

    @property
    def output_height(self) -> int:
        return round(self.original_height * self.width / self.original_width)

    @property
    def output_width(self) -> int:
        return self.width


@dataclass
class FixedResizer(ResizerBase):
    """A class that resizes Images to a height and width and will crop the image if necessary.
    """
    width: int
    height: int
    original_width: int
    original_height: int

    @property
    def crop_coords(self) -> Tuple[int, int, int, int]:
        """Calculate the range of pixels to crop the new image out of.

        The new image should touch either both sides or the top and bottom. If
        reducing the height is necessary, the selected pixels are biased a bit
        towards the top of the image, because more interesting stuff tends to be
        in the upper half of the image.

        Returns:
            tuple[int, int, int, int]: left, top, right, bottom
        """
        original_origin_x = self.original_width / 2
        original_origin_y = self.original_height / 4
        output_ratio = self.width / self.height
        adjusted_output_width = min(
            self.original_width, self.original_height * output_ratio
        )
        adjusted_output_height = min(
            self.original_height, self.original_width / output_ratio
        )
        adjusted_origin_x = adjusted_output_width / 2
        adjusted_origin_y = adjusted_output_height / 4
        xoff = round(original_origin_x - adjusted_origin_x)
        yoff = round(original_origin_y - adjusted_origin_y)
        return (
            xoff,
            yoff,
            round(xoff + adjusted_output_width),
            round(yoff + adjusted_output_height),
        )

    def crop_image(self, *, image: Image.Image) -> Image.Image:
        return image.crop(self.crop_coords)

    @property
    def output_height(self) -> int:
        return self.height

    @property
    def output_width(self) -> int:
        return self.width


@dataclass
class ImageData:
    height: int
    width: int
    url: str
    name: str


class LabelProtocol(Protocol):
    def label_lower(self) -> str:
        pass

    def label(self) -> str:
        pass


class Photo(PhotoBase):
    """Extends PhotoBase by adding federation attributes, Place search
    optimizations and more.
    """
    original = models.ImageField(
        upload_to=get_original_path,
        storage=OverwriteStorage(),
        null=True,
        editable=True,
    )
    remote_image = models.URLField(null=True, editable=False)
    remote_page = models.URLField(null=True, editable=False)
    places = models.ManyToManyField("kronofoto.Place", editable=False)
    original_height = models.IntegerField(default=0, editable=False)
    original_width = models.IntegerField(default=0, editable=False)

    @property
    def fullsizeurl(self) -> str:
        """Get the URL for the original image. The original image can be on
        other servers in the federation.

        Returns:
            str: The image URL.
        """
        if self.remote_image:
            return self.remote_image
        elif self.original:
            return self.original.url
        raise ValueError

    @overload
    def image_url(self, *, height: int) -> str: ...
    @overload
    def image_url(self, *, height: Optional[int] = None, width: int) -> str: ...
    def image_url(
        self, *, height: Optional[int] = None, width: Optional[int] = None
    ) -> str:
        """Get the URL for the image with a certain height and/or width.

        The `height` and `width` arguments are both optional, but at least one
        must be supplied.

        Args:
            height (int, optional): Desired height.
            width (int, optional): Desired width.

        Returns:
            str: The URL with that image resolution.
        """
        assert height is not None or width is not None

        if self.original.name != '':
            path = self.original.name
        elif self.remote_image:
            path = (0, self.remote_image)
        else:
            return ""
        return ImageSigner(id=self.id, path=path, width=width, height=height).url

    def ldid(self) -> str:
        """Get the LD-ID for this Photo, which may or may not be on another server.

        Returns:
            str: A URL that will contain this Photo definition in the response.
        """
        from .ldid import LdId
        try:
            return LdId.objects.get(content_type__app_label="kronofoto", content_type__model="photo", object_id=self.id).ld_id
        except LdId.DoesNotExist:
            return reverse(
                "kronofoto:activitypub_data:archives:photos:detail",
                kwargs={"short_name": self.archive.slug, "pk": self.id},
            )

    def get_image_dimensions(self) -> Tuple[int, int]:
        """Gets the image dimensions, and saves the result in the table if doing so required loading the image file.

        Returns:
            tuple[int, int]: width, height
        """
        if self.original_height == 0 or self.original_width == 0:
            Image.MAX_IMAGE_PIXELS = 195670000
            self.original_height = self.original.height
            self.original_width = self.original.width
            Photo.objects.filter(id=self.id).update(
                original_height=self.original_height, original_width=self.original_width
            )
        return (self.original_width, self.original_height)

    @property
    def h700(self) -> Optional[ImageData]:
        """Get ImageData for a 700 pixel tall version of this Photo.

        Returns:
            ImageData | None: ImageData containing height and width of the new image and the URL. It will return None when the Photo is not saved (no ID) or there is no original or remote_image set.
        """
        from fortepan_us.kronofoto.imageutil import ImageSigner

        if not (self.original or self.remote_image) or not self.id:
            return None
        if self.remote_image:
            path = (0, self.remote_image)
            width, height = 0, 700
        elif self.original:
            path = self.original.name
            width, height = self.get_image_dimensions()
        else:
            raise ValueError
        signer = ImageSigner(id=self.id, path=path, width=0, height=700)
        return ImageData(
            height=700,
            width=round(width*700/height),
            url=signer.url,
            name="h700",
        )

    @property
    def thumbnail(self) -> Optional[ImageData]:
        """Get ImageData for a 75 by 75 pixel version of this image.

        Returns:
            ImageData | None: ImageData containing height and width of the new image and the URL. It will return None when the Photo is not saved (no ID) or there is no original or remote_image set.
        """
        if not (self.original or self.remote_image) or not self.id:
            return None
        from fortepan_us.kronofoto.imageutil import ImageSigner
        if self.remote_image:
            path = (0, self.remote_image)
        elif self.original:
            path = self.original.name
        signer = ImageSigner(id=self.id, path=path, width=75, height=75)
        return ImageData(
            height=75,
            width=75,
            url=signer.url,
            name="thumbnail",
        )

    tags = models.ManyToManyField(
        Tag, db_index=True, blank=True, through="kronofoto.PhotoTag"
    )
    is_featured = models.BooleanField(default=False)
    is_published = models.BooleanField(default=False, db_index=True)
    local_context_id = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        validators=[
            RegexValidator(
                regex="[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}",
                message="This should be blank or 36 alphanumerics with hyphens grouped like this: 8-4-4-4-12",
            )
        ],
    )
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    objects = PhotoQuerySet.as_manager()

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=Q(is_published=False) | Q(donor__isnull=False),
                name="never_published_without_donor",
            ),
        ]
        indexes = (
            models.Index(fields=["archive", "id"]),
            models.Index(
                fields=["year", "id"],
                condition=Q(is_published=True, year__isnull=False),
                name="year_id_sort",
            ),
            models.Index(
                fields=["donor_id", "year", "id"],
                condition=Q(is_published=True, year__isnull=False),
                name="donor_year_id_sort",
            ),
            models.Index(
                fields=["donor_id", "category", "year", "id"],
                condition=Q(is_published=True, year__isnull=False),
                name="d_category_year_id_sort",
            ),
            models.Index(
                fields=["donor_id", "archive", "year", "id"],
                condition=Q(is_published=True, year__isnull=False),
                name="d_archive_year_id_sort",
            ),
            models.Index(
                fields=["donor_id", "category", "archive", "year", "id"],
                condition=Q(is_published=True, year__isnull=False),
                name="d_category_archive_year_id_s",
            ),
            models.Index(
                fields=["category", "year", "id"],
                condition=Q(is_published=True, year__isnull=False),
                name="category_year_id_sort",
            ),
            models.Index(
                fields=["archive", "year", "id"],
                condition=Q(is_published=True, year__isnull=False),
                name="archive_year_id_sort",
            ),
            models.Index(
                fields=["category", "archive", "year", "id"],
                condition=Q(is_published=True, year__isnull=False),
                name="category_archive_year_id_sort",
            ),
            models.Index(
                fields=["place_id", "year", "id"],
                condition=Q(is_published=True, year__isnull=False),
                name="pyear_id_sort",
            ),
            models.Index(
                fields=["donor_id", "place_id", "year", "id"],
                condition=Q(is_published=True, year__isnull=False),
                name="donor_pyear_id_sort",
            ),
            models.Index(
                fields=["donor_id", "category", "place_id", "year", "id"],
                condition=Q(is_published=True, year__isnull=False),
                name="d_category_pyear_id_sort",
            ),
            models.Index(
                fields=["donor_id", "archive", "place_id", "year", "id"],
                condition=Q(is_published=True, year__isnull=False),
                name="d_archive_pyear_id_sort",
            ),
            models.Index(
                fields=["donor_id", "category", "archive", "place_id", "year", "id"],
                condition=Q(is_published=True, year__isnull=False),
                name="d_category_archive_pyear_id_s",
            ),
            models.Index(
                fields=["category", "place_id", "year", "id"],
                condition=Q(is_published=True, year__isnull=False),
                name="category_pyear_id_sort",
            ),
            models.Index(
                fields=["archive", "place_id", "year", "id"],
                condition=Q(is_published=True, year__isnull=False),
                name="archive_pyear_id_sort",
            ),
            models.Index(
                fields=["category", "archive", "place_id", "year", "id"],
                condition=Q(is_published=True, year__isnull=False),
                name="category_archive_pyear_id_sort",
            ),
        )

    #def reconcile(self, object: ActivitypubImage | PhotoValue, donor: Donor, place: Place | None = None) -> None:
    #    if isinstance(object, PhotoValue):
    #        self.caption = object.content
    #        remote_image = object.url
    #        self.category, _ = Category.objects.get_or_create(
    #            slug=object.category.slug,
    #            defaults={"name": object.category.name},
    #        )
    #        self.year = object.year
    #        self.circa = object.circa
    #        self.is_published = object.is_published
    #        self.donor = donor
    #        self.place = place
    #    else:
    #        self.caption = object["content"]
    #        self.donor = donor
    #        self.year = object["year"]
    #        self.circa = object["circa"]
    #        self.is_published = object["is_published"]
    #        self.donor = donor
    #        self.remote_image = object["url"]
    #        self.category, _ = Category.objects.get_or_create(
    #            slug=object["category"]["slug"],
    #            defaults={"name": object["category"]["name"]},
    #        )
    #    self.save()

    @property
    def activity_dict(self) -> Dict[str, Any]:
        "Deprecated."
        return {
            "id": reverse(
                "kronofoto:activitypub-photo",
                kwargs={"short_name": self.archive.slug, "pk": self.id},
            ),
            "type": "Image",
            "attributedTo": [
                reverse(
                    "kronofoto:activitypub-archive",
                    kwargs={"short_name": self.archive.slug},
                )
            ],
            "content": self.caption,
            "url": self.original.url,
        }

    def is_owned_by(self, actor: RemoteActor) -> bool:
        """Determine if this Photo is owned by the RemoteActor.

        Args:
            actor (RemoteActor): An actor

        Returns:
            bool: True if this Photo is owned by actor.
        """
        return self.archive.actor is not None and self.archive.actor.id == actor.id

    def page_number(self) -> Dict[str, Optional[int]]:
        "Get the page number of this photo for the Paginator."
        return {"year:gte": self.year, "id:gt": self.id - 1}

    def get_all_tags(self, user: Optional[User] = None) -> List[LabelProtocol]:
        """Return a list of tag and term objects, annotated with label and label_lower for label and sorting.

        Args:
            user (User, optional): Defaults to None. The User will be taken into account when determining the tags.

        Returns:
            list[LabelProtocol]: A list of tags and terms associated with this Photo. If the user has submitted tags that have not been accepted, they will be included in the list.
        """
        tags = self.get_accepted_tags(user=user).annotate(
            label_lower=Lower("tag"), label=models.F("tag")
        )
        terms = self.terms.annotate(label_lower=Lower("term"), label=models.F("term"))
        return list(tags) + list(terms)  # type: ignore

    def get_accepted_tags(self, user: Optional[User] = None) -> models.QuerySet[Tag]:
        """Return a queryset of tags associated with this Photo.

        Args:
            user (User, optional): Defaults to None. The User will be taken into account when determining the tags.

        Returns:
            models.QuerySet[Tag]: The tags associated with this Photo. If the user has submitted tags that have not been accepted, they will be included in the list.
        """
        query = Q(phototag__accepted=True)
        if user:
            query |= Q(phototag__creator__pk=user.pk)
        return self.tags.filter(query)

    def get_proposed_tags(self) -> models.QuerySet[Tag]:
        """Get Tags that have been submitted but not accepted.

        Returns:
            models.QuerySet[Tag]: The unaccepted Tags associated with this Photo.
        """
        return self.tags.filter(phototag__accepted=False)

    def add_params(self, url: str, params: Optional[QueryDict]) -> str:
        """Add url encoded params if required to a url, else return the
        unmodified url.

        This conveniently avoids adding a ? to the URL if there are no params.
        However, this could probably be added to the custom `reverse` function.

        Args:
            url (str): A URL.
            params (QueryDict, optional): Query parameters.

        Returns:
            str: A URL including the query parameters.
        """
        if params:
            url = "{}?{}".format(url, params.urlencode())
        return url

    def create_url(
        self,
        viewname: str,
        queryset: Optional[int] = None,
        params: Optional[QueryDict] = None,
    ) -> str:
        "Deprecated"
        kwargs = {"photo": self.id}
        url = reverse(
            viewname,
            kwargs=kwargs,
        )
        return self.add_params(url=url, params=params)

    def get_download_page_url(
        self,
        kwargs: Optional[Dict[str, Any]] = None,
        params: Optional[QueryDict] = None,
    ) -> str:
        """A get_absolute_url alternative for the download page.

        Args:
            kwargs (dict[str, Any], optional): Defaults to None. Allows preserving archive and category in the download page url.
            params (QueryDict, optional): Defaults to None. Allows preserving query constraints for web components.

        Returns:
            str: A URL for the download page for this Photo.
        """
        kwargs = kwargs or {}
        url = reverse("kronofoto:download", kwargs=dict(**kwargs, **{"pk": self.id}))
        if params:
            params = params.copy()
        else:
            params = QueryDict(mutable=True)
        return self.add_params(url=url, params=params)

    def get_urls(self, embed: bool = False) -> Dict[str, str]:
        "Deprecated."
        return {
            "url": self.get_absolute_url(),
        }

    def get_grid_url(
        self,
        kwargs: Optional[Dict[str, Any]] = None,
        params: Optional[QueryDict] = None,
    ) -> str:
        """A get_absolute_url alternative to the grid page that starts with this
        image.

        Args:
            kwargs (dict[str, Any], optional): Defaults to None. Allows preserving archive and category in the grid page url.
            params (QueryDict, optional): Defaults to None. Allows preserving query constraints for web components.

        Returns:
            str: A URL for the grid page for this Photo.

        Raises:
            ValueError: If the year is not set, the grid page cannot exist.
        """
        if self.year:
            kwargs = kwargs or {}
            url = reverse("kronofoto:gridview", kwargs=kwargs)
            if params:
                params = params.copy()
            else:
                params = QueryDict(mutable=True)
            params["year:gte"] = str(self.year)
            params["id:gt"] = str(self.id - 1)
            return self.add_params(url=url, params=params)
        raise ValueError("Photo.year must be set")

    def get_archive_url(
        self,
    ) -> str:
        """Get the timeline url for this photo within its archive.

        Returns:
            str: The URL for this photo within its archive.
        """
        kwargs = {
            "short_name": self.archive.slug,
            "photo": self.id,
        }
        if self.archive.server_domain:
            kwargs['domain'] = self.archive.server_domain
        url = reverse("kronofoto:photoview", kwargs=kwargs)
        return url

    def get_absolute_url(
        self,
        kwargs: Optional[Dict[str, Any]] = None,
        params: Optional[QueryDict] = None,
    ) -> str:
        """Get the timeline view version of this image.

        Args:
            kwargs (dict[str, Any], optional): Defaults to None. Allows preserving archive and category in the timeline page url.
            params (QueryDict, optional): Defaults to None. Allows preserving query constraints for web components.

        Returns:
            str: A URL for the timeline page for this Photo.
        """
        kwargs = kwargs or {}
        kwargs = dict(**kwargs)
        kwargs["photo"] = self.id
        url = reverse("kronofoto:photoview", kwargs=kwargs)
        if params:
            return "{}?{}".format(url, params.urlencode())
        return url

    def get_edit_url(self) -> str:
        """Get the admin change url for this photo.

        Returns:
            str: A URL for the admin change page.
        """
        return reverse("admin:kronofoto_photo_change", args=(self.id,))

    @staticmethod
    def format_url(**kwargs: Any) -> str:
        "deprecated"
        return "{}?{}".format(reverse("kronofoto:gridview"), urlencode(kwargs))

    def get_county_url(self) -> str:
        "deprecated"
        return Photo.format_url(county=self.county, state=self.state)

    def get_city_url(self) -> str:
        "deprecated"
        return Photo.format_url(city=self.city, state=self.state)

    class CityIndexer:
        "deprecated"
        def index(self) -> List[Dict[str, Any]]:
            return Photo.city_index()

    class CountyIndexer:
        "deprecated"
        def index(self) -> List[Dict[str, Any]]:
            return Photo.county_index()

    @staticmethod
    def index_by_fields(*fields: str) -> List[Dict[str, Any]]:
        "deprecated"
        return [
            {
                "name": ", ".join(p[field] for field in fields),
                "count": p["count"],
                "href": Photo.format_url(**{field: p[field] for field in fields}),
            }
            for p in Photo.objects.filter(is_published=True)
            .exclude(reduce(operator.or_, (Q(**{field: ""}) for field in fields)))
            .values(*fields)
            .annotate(count=Count("id"))
            .order_by(*fields)
        ]

    @staticmethod
    def county_index() -> List[Dict[str, Any]]:
        "deprecated"
        return Photo.index_by_fields("county", "state")

    @staticmethod
    def city_index() -> List[Dict[str, Any]]:
        "deprecated"
        return Photo.index_by_fields("city", "state")

    def __str__(self) -> str:
        return self.accession_number

    @staticmethod
    def accession2id(accession: str) -> int:
        """Accession Numbers in the fortepan system start with FI and are
        followed with a 7 digit number. This retrieves the number part.

        Args:
            accession (str): a FI number, like FI0056752. It does not need to be 7 digits. It can be more or less.

        Returns:
            int: The number from the string, like 56752.

        Raises:
            ValueError: The string must start with FI and then be a number.
        """
        if not accession.startswith("FI"):
            raise ValueError("{} doesn't start with FI", accession)
        return int(accession[2:])

    @property
    def accession_number(self) -> str:
        """Return this Photo's accession number, like `FI0056752`.

        Returns:
            str: The accession number.
        """
        return "FI" + str(self.id).zfill(7)

    def resizer(
        self, *, size: int, original_width: int, original_height: int
    ) -> ResizerBase:
        "Deprecated"
        if size == "thumbnail":
            return FixedResizer(
                width=75,
                height=75,
                original_width=original_width,
                original_height=original_height,
            )
        elif size == "h700":
            return FixedHeightResizer(
                height=700,
                original_width=original_width,
                original_height=original_height,
            )
        raise NotImplementedError

    @dataclass
    class Saver:
        "Deprecated"
        uuid: uuid.UUID
        path: str

        def save(self, *, image: Image.Image) -> str:
            fname = self.format_path()
            image.save(os.path.join(settings.MEDIA_ROOT, fname), "JPEG")
            return fname

        def format_path(self) -> str:
            return self.path.format(self.uuid)

    def saver_(self, *, size: int, uuid: uuid.UUID) -> Saver:
        "Deprecated"
        if size == "thumbnail":
            return Photo.Saver(uuid=uuid, path="thumb/{}.jpg")
        elif size == "h700":
            return Photo.Saver(uuid=uuid, path="h700/{}.jpg")
        raise NotImplementedError


    def describe(self, user: Optional[User] = None) -> Set[str]:
        """Get a set of strings describing a photo. Useful for alt text.

        Args:
            user (User, optional): Defaults to None. If a user is given, the set will include tags the user has suggested even if they are not accepted.

        Returns:
            set[str]: a set of strings describing the Photo.
        """
        terms = {str(t) for t in self.terms.all()}
        tags = {str(t) for t in self.get_accepted_tags(user)}
        location = self.location()
        locations = {place.name for place in self.places.all()}
        return (
            terms
            | tags
            | locations
            | {str(self.donor)}
            | {self.archive.name, self.archive.slug}
            | {self.category.name}
            | {"history", "historic"}
        )

    def notices(self) -> List["LocalContextNotice"]:
        """Get the list of Local Context Notices.

        Returns:
            list[LocalContextNotice]: The `LocalContextNotice` objects for this Photo.
        """
        if not self.local_context_id:
            return []

        def _() -> List[LocalContextNotice]:
            url = "{base}projects/{id}/".format(
                base=settings.LOCAL_CONTEXTS, id=self.local_context_id
            )
            resp = requests.get(url)
            if resp.status_code == 200:
                return [
                    LocalContextNotice(
                        name=notice["name"],
                        img_url=notice["img_url"],
                        svg_url=notice["svg_url"],
                        default_text=notice["default_text"],
                    )
                    for notice in resp.json()["notice"]
                ]
            else:
                return []

        val = cache.get_or_set(self.local_context_id, _, timeout=24 * 60 * 60)
        if val and isinstance(val, list):
            return val
        else:
            return []


def get_resized_path(instance: Any, filename: str) -> str:
    "Deprecated"
    return path.join(
        "resized",
        "{}_{}_{}.jpg".format(instance.width, instance.height, instance.photo.uuid),
    )


@dataclass
class LocalContextNotice:
    name: str
    img_url: str
    svg_url: str
    default_text: str


class PhotoTag(models.Model):
    """M2M through class for Photo-Tag relations.

    Since Tag objects have no attributes or interesting behavior, it would
    probably be okay to put the Tag TextField in this model as a unique field.
    That would eliminate the need to find dead tags and delete them.
    """
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)
    photo = models.ForeignKey(Photo, on_delete=models.CASCADE)
    accepted = models.BooleanField()
    creator = models.ManyToManyField(User, editable=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tag", "photo"], name="unique_tag_photo"),
        ]
        indexes = [
            models.Index(fields=["tag", "photo"]),
        ]

    def __str__(self) -> str:
        return str(self.tag)


def remove_deadtags(sender: Any, instance: Tag, **kwargs: Any) -> None:
    """Locate Tags which have no Photos attached and delete them."""
    if instance.tag.phototag_set.count() == 0:
        instance.tag.delete()


def disconnect_deadtags(*args: Any, **kwargs: Any) -> None:
    """Remote signal for removing dead tags"""
    post_delete.disconnect(remove_deadtags, sender=Photo.tags.through)


def connect_deadtags(*args: Any, **kwargs: Any) -> None:
    """Install signal for removing dead tags"""
    post_delete.connect(remove_deadtags, sender=Photo.tags.through)


post_delete.connect(remove_deadtags, sender=Photo.tags.through)
pre_delete.connect(disconnect_deadtags, sender=Tag)
post_delete.connect(connect_deadtags, sender=Tag)


@dataclass
class PhotoPlaceholder:
    """Wraps a Photo and provide a hook to provide an alternate thumbnail. Used
    to make an empty/invisible thumbnail.
    """
    thumbnail: Thumbnail
    is_spacer: bool
    photo: Photo

    def get_absolute_url(self, *args: Any, **kwargs: Any) -> str:
        """Get the Photo's absolute url.

        Args:
            *args (Any): Arg list that will be passed through to the photo's get_absolute_url unmodified.
            *kwargs (Any): Arg keywords that will be passed through to the photo's get_absolute_url unmodified.

        Returns:
            str: The canonical URL for the photo."
        """
        return self.photo.get_absolute_url(*args, **kwargs)

    @property
    def id(self) -> int:
        """Get the photo instance ID.

        Returns:
            int: The photo's ID.
        """
        return self.photo.id

    @property
    def year(self) -> Optional[int]:
        """Get the photo instance year.

        Returns:
            Optional[int]: The photo's year. It can return None if the photo
            does not have a year.
        """
        return self.photo.year


@dataclass
class CarouselList:
    "Used to get a set of Photos that are near each other in keyset order."
    queryset: QuerySet

    @property
    def keyset(self) -> QuerySet:
        """Subclasses must implement. Allows jumping into the middle of the queryset (eg keyset pagination)"""
        raise NotImplementedError

    @property
    def wrapped_queryset(self) -> QuerySet:
        """Subclasses must implement. Allows reversing the queryset order."""
        raise NotImplementedError

    def carousel_list(
        self, *, item_count: int, func: Optional[Callable] = None
    ) -> List[Photo]:
        """Get a list of photos in queryset order, and can loop back around to
        the beginning of the queryset, and invisible thumbnails are used after
        the loop.

        Args:
            item_count (int): How many photos to put in the list.
            func (callable): Allow caller to wrap Photo instances so alternate absolute urls and image sizes can be used in templates.

        Returns:
            list[Photo]: A list of item_count Photos.
        """
        keyset: Iterable = self.keyset[:item_count]
        if func:
            keyset = [func(item) for item in keyset]
        wrapped_qs = self.wrapped_queryset
        cycling = cycle(
            PhotoPlaceholder(
                thumbnail=EMPTY_THUMBNAIL,
                is_spacer=True,
                photo=func(photo) if func else photo,
            )
            for photo in wrapped_qs[:item_count]
        )
        looping = chain(keyset, cycling)
        return list(islice(looping, item_count))


@dataclass
class BackwardList(CarouselList):
    "Fetch N photos in reverse archive order starting with `year`, `id`."
    queryset: PhotoQuerySet
    year: int
    id: int

    @property
    def keyset(self) -> PhotoQuerySet:
        """Get a queryset that starts with the current photo.

        Returns:
            PhotoQuerySet: The set of photos before this point in archive order.
        """
        return self.queryset.photos_before(year=self.year, id=self.id)

    @property
    def wrapped_queryset(self) -> PhotoQuerySet:
        """Order the archive in reverse archive order

        Returns:
            PhotoQuerySet: A Photo QuerySet that is orderd in reverse archive order.
        """
        return self.queryset.order_by("-year", "-id")


@dataclass
class ForwardList(CarouselList):
    "Fetch N photos in reverse archive order starting with `year`, `id`."
    queryset: PhotoQuerySet
    year: int
    id: int

    @property
    def keyset(self) -> PhotoQuerySet:
        """Get a queryset that starts with the current photo.

        Returns:
            PhotoQuerySet: The set of photos after this point in archive order.
        """
        return self.queryset.photos_after(year=self.year, id=self.id)

    @property
    def wrapped_queryset(self) -> PhotoQuerySet:
        """Order the archive in archive order

        Returns:
            PhotoQuerySet: A Photo QuerySet that is orderd in archive order.
        """
        return self.queryset
