from django.core.cache import cache
from django.http import QueryDict, Http404
from django.conf import settings
from django.core.exceptions import BadRequest
from django.templatetags.static import static
from django.template.loader import select_template
from django.shortcuts import get_object_or_404
import random
import json
from ..reverse import set_request, reverse
from ..forms import SearchForm
from ..search.parser import Parser, NoExpression
from ..models import Photo
from ..models.archive import Archive
from ..models import Category
from functools import reduce
import operator
from dataclasses import dataclass, replace
from .base import ArchiveRequest, require_valid_archive
from django.utils.decorators import method_decorator

class ThemeDict(dict):
    def __missing__(self, key):
        return self['us']

@dataclass
class Theme:
    color: str
    colorDarker: str
    colorLighter: str
    menuSvg: str
    infoSvg: str
    downloadSvg: str
    searchSvg: str
    carrotSvg: str
    timelineSvg: str

    name: str
    archive: str

    def logo(self):
        kwargs = {'theme': self.name}
        if self.archive:
            kwargs['short_name'] = self.archive
        return reverse('kronofoto:logosvg', kwargs=kwargs)

    def logosmall(self):
        kwargs = {'theme': self.name}
        if self.archive:
            kwargs['short_name'] = self.archive
        return reverse('kronofoto:logosvgsmall', kwargs=kwargs)

    @classmethod
    def generate_themes(cls):
        # This is a very annoying feature, and this is unpleasantly non-general.
        colors = (
            ('skyblue', ("#6E86BC", "#A8B6D7", "#53658D")),
            ('golden', ("#C2891C", "#D6BC89", "#987024")),
            ('haybail', ("#C2A562", "#CEB57C", "#A28B54")),
        )
        colors = {
            name: Theme(
                color=color[0],
                colorLighter=color[1],
                colorDarker=color[2],
                menuSvg='assets/images/{}/menu.svg'.format(name),
                infoSvg='assets/images/{}/info.svg'.format(name),
                downloadSvg='assets/images/{}/download.svg'.format(name),
                searchSvg='assets/images/{}/search.svg'.format(name),
                carrotSvg='assets/images/{}/carrot.svg'.format(name),
                timelineSvg='assets/images/{}/toggle.svg'.format(name),
                name=name,
                archive=None,
            )
            for name, color in colors
        }
        themes = {
            archive: {
                name: replace(theme, archive=archive)
                for name, theme in colors.items()
            }
            for archive in ('ia', 'ct')
        }
        themes['us'] = colors
        return ThemeDict(themes)

THEME = Theme.generate_themes()

class BaseTemplateMixin:
    category = None
    archive_request_class = ArchiveRequest

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        if self.category:
            kwargs['category'] = self.category
        self.archive_request = self.archive_request_class(request=request, category=kwargs.get("category"), short_name=kwargs.get('short_name'))

    @property
    def params(self):
        return self.archive_request.params
    @property
    def final_expr(self):
        return self.archive_request.final_expr
    @property
    def expr(self):
        return self.archive_request.expr
    @property
    def constraint(self):
        return self.archive_request.constraint
    @property
    def form(self):
        return self.archive_request.form
    @property
    def get_params(self):
        return self.archive_request.get_params
    @property
    def url_kwargs(self):
        return self.archive_request.url_kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.archive_request.common_context)
        return context

    @method_decorator(require_valid_archive)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

class BasePhotoTemplateMixin(BaseTemplateMixin):
    def get_queryset(self):
        return self.archive_request.get_photo_queryset()
