from django.urls import path, include, register_converter, URLPattern, URLResolver
from fortepan_us.kronofoto import views
import fortepan_us.kronofoto.views.places
from fortepan_us.kronofoto.views import collection, webcomponent, downloadpage
from django.views.generic.base import TemplateView
from fortepan_us.kronofoto.views.photosphere import MainStreetList, MainStreetDetail, MainStreetGeojson
from fortepan_us.kronofoto.views import photosphere
from fortepan_us.kronofoto.views.frontpage import RandomRedirect, YearRedirect
from fortepan_us.kronofoto.views.photo import CarouselListView
from fortepan_us.kronofoto.views.agreement import AgreementView
from fortepan_us.kronofoto.views.submission import submission, KronofotoTemplateView
from fortepan_us.kronofoto.views.tagsearch import ContributorSearchView
from fortepan_us.kronofoto.views.donor import ContributorCreateView
from fortepan_us.kronofoto.views import activitypub
from fortepan_us.kronofoto.views import tags_view
from fortepan_us.kronofoto.views import photosphere
from fortepan_us.kronofoto.views import exhibit
from fortepan_us.kronofoto.views import map
from fortepan_us.kronofoto.views import vector_tiles
from django.conf import settings
from django.http.response import HttpResponseBase
from typing import Sequence, Union, List, Callable, Dict, Any, Optional, Tuple


class NegativeIntConverter:
    regex = r'-?\d+'

    def to_python(self, value: str) -> int:
        return int(value)

    def to_url(self, value: int) -> str:
        return "{}".format(value)

class AccessionNumberConverter:
    regex = r'FI\d+'

    def to_python(self, value: str) -> int:
        return int(value[2:])

    def to_url(self, value: int) -> str:
        return "FI" + str(value).zfill(7)

register_converter(NegativeIntConverter, 'negint')
register_converter(AccessionNumberConverter, 'accession')

def directory(
        route: str,
        view: Callable[..., HttpResponseBase],
        kwargs: Optional[Dict[str, Any]] = None,
        name: Optional[str] = None,
        children: Optional[Tuple[Sequence[Union[URLResolver, URLPattern]], Optional[str], Optional[str]]]=None,
    ) -> List[Union[URLPattern, URLResolver]]:
    full_kwargs : Dict[str, Any] = {}
    partial_kwargs : Dict[str, Any] = {}
    if kwargs:
        full_kwargs['kwargs'] = kwargs
        partial_kwargs['kwargs'] = kwargs
    if name:
        full_kwargs['name'] = name
    paths : List[Union[URLPattern, URLResolver]] = [
        path(route, view, **full_kwargs),
        path(route+"/", view, **partial_kwargs),
    ]
    if children:
        paths.append(path(route+"/", children))
    return paths

def build_content_urls(route: str, with_names: bool=False, kwargs: Optional[Dict[str, Any]] = None) -> List[Union[URLPattern, URLResolver]]:
    kwargs = kwargs or {}
    if with_names:
        get_kwargs : Callable[[str], Dict[str, Any]] = lambda x: {"kwargs": kwargs, "name": x}
    else:
        get_kwargs = lambda x: {"kwargs": kwargs}
    return directory(route, views.GridView.as_view(), **get_kwargs("gridview"), children=include([
        *directory('<accession:photo>', views.PhotoView.as_view(), **get_kwargs("photoview"), children=include([
            path('original', views.DownloadPageView.as_view(pk_url_kwarg='photo'), **get_kwargs('download')),
            path('web-component', webcomponent.WebComponentPopupView.as_view(), **get_kwargs('popup-web-component')),
            path('download', downloadpage.DownloadPopupView.as_view(), **get_kwargs('popup-download')),
        ])),
        path('random', views.RandomRedirect.as_view(), **get_kwargs('random-image')),
        path('carousel', CarouselListView.as_view(item_count=40), **get_kwargs('carousel')),
        path('year', YearRedirect.as_view(), **get_kwargs("year-redirect")),
        *directory('map', views.map_list, **get_kwargs('map'), children=include([
            path('photosphere', photosphere.map_photosphere_data, **get_kwargs('map-detail-photosphere.json')),
            path("tiles/<int:zoom>/<int:x>/<int:y>.mvt", vector_tiles.photo_tile, **get_kwargs("photo-tile")),
            path("detail/<int:zoom>/<int:x>/<int:y>/<int:subx>/<int:suby>", map.subtile_detail, **get_kwargs("map-subtile-detail")),
            path('<accession:photo>', views.map_detail, **get_kwargs('map-detail')),
            path('<int:photosphere>', map.detail_photosphere, **get_kwargs('map-detail-photosphere')),
        ])),
    ]))

app_name = 'kronofoto'
urlpatterns : List[Union[URLPattern, URLResolver]] = [
    path('', views.RandomRedirect.as_view(category="photos"), name='random-image'),
    *build_content_urls("photos", with_names=False, kwargs={"category": "photos"}),
    *directory('categories', views.category_list, name="materials-list", children=include([
        *build_content_urls("all", with_names=True, kwargs={}),
        *build_content_urls("<slug:category>", with_names=True, kwargs={}),
    ])),
    path('<str:theme>/logo.svg', views.photo.logo_view, name='logosvg'),
    path('<str:theme>/logo-small.svg', views.photo.logo_small_view, name='logosvgsmall'),
    path('<str:theme>/logo-icon.svg', views.photo.logo_icon_view, name='logo-icon.svg'),
    *directory('collections', views.collections_view, name='collection-create', children=include([
        *directory('<int:pk>', views.collection_view, name='collection-edit', children=include([
            path("embed", views.collection.embed, name="collection-embed"),
            path("remove/<int:photo>", views.collection.remove, name="collection-remove"),
            path("change-visibility", views.collection.change_visibility, name="collection-visibility"),
            path("change-name", views.collection.change_name, name="collection-name"),
            path('delete', views.CollectionDelete.as_view(), name='collection-delete'),
        ])),
    ])),
    *directory('mainstreets', MainStreetList.as_view(), name='mainstreet-list', children=include([
        path('<int:pk>', photosphere.mainstreet_detail, name='mainstreet-detail'),
        path('<int:pk>.geojson', MainStreetGeojson.as_view(), name='mainstreet-data'),
    ])),
    path('mainstreet360', views.photosphere_view, name="mainstreetview"),
    path('mainstreet360/json', views.photosphere_data, name="mainstreetview.json"),
    path('mainstreet360/carousel', views.photosphere_carousel, name='mainstreetview-carousel'),
    path('mainstreet360/infobox', photosphere.info_text, name="mainstreet-info"),
    path('tags', views.TagSearchView.as_view(), name='tag-search'),
    path('autocomplete/contributors/select2', views.contributor_search, name='contributor-search2'),
    path('autocomplete/contributors', ContributorSearchView.as_view(), name='contributor-search'),
    path('autocomplete/places', views.place_search, name='place-search'),
    path('autocomplete/places/all', views.place_search, {"require_photo": False}, name='all-place-search'),
]

urlpatterns = urlpatterns + [
    path('auth/forms', include("fortepan_us.kronofoto.views.forms")),
    path('tag-members/<int:photo>', tags_view, name='tags-view'),
    *directory('list-members/<int:photo>', collection.ListMembers.as_view(), name='popup-add-to-list', children=include([
        path('new-list', collection.NewList.as_view(), name='popup-new-list'),
        path('edit', views.AddToList.as_view(), name='add-to-list'),
    ])),
    path('activitypub/service', views.activitypub.service, name="activitypub-main-service"),
    path('activitypub/service/show', views.activitypub.service_view, name="activitypub-main-service-view"),
    path('activitypub/service/inbox', views.activitypub.service_inbox, name="activitypub-main-service-inbox"),
    path('activitypub/service/outbox', views.activitypub.service_outbox, name="activitypub-main-service-outbox"),
    path('activitypub/service/places', views.activitypub.places_page, name="activitypub-main-service-places"),
    path('activitypub/service/places/<int:pk>', views.activitypub.service_place, name="activitypub-main-service-places"),
    path("activitypub/", include(views.activitypub.data_urls)),
    path('users/<str:username>', views.profile_view, name='user-page'),
    path('attribution', views.attribution, name="attribution"),
    path("exhibits", views.exhibit_list, name="exhibit-list"),
    path("exhibits/info-button", views.exhibit.exhibit_info_button, name="info-button"),
    path("exhibits/<int:pk>-<slug:title>", views.exhibit.view, name='exhibit-view'),
    path("exhibits/<int:pk>/embed", views.exhibit.embed, name='exhibit-embed'),
    path("exhibits/<int:pk>/edit", views.exhibit_edit, name='exhibit-edit'),
    path("exhibits/<int:pk>/delete", views.exhibit.delete, name='exhibit-delete'),
    path("exhibits/<int:pk>/images", views.exhibit_images, name='exhibit-images'),
    path("exhibits/<int:pk>/figure-form-<str:parent>", views.exhibit_figure_form, name='exhibit-figure-form'),
    path("exhibits/<int:pk>/figure-image", views.exhibit_figure_image, name='exhibit-figure-image'),
    path("exhibits/<int:pk>/two-column-image", views.exhibit_two_column_image, name='exhibit-two-column-image'),
    path("exhibits/full-image", views.exhibit_full_image, name='exhibit-full-image'),
    path("exhibits/recard/<int:pk>", exhibit.exhibit_recard, name='exhibit-recard'),
    path("exhibits/<int:pk>/<str:card_type>-form", views.exhibit_card_form, name='exhibit-card-form'),
    path("exhibits/add", views.exhibit_create, name='exhibit-create'),
    path('<slug:short_name>/contributors/add', ContributorCreateView.as_view(), name='contributor-create'),
    path('<slug:short_name>/contributors/added', KronofotoTemplateView.as_view(template_name="kronofoto/pages/contributor-created.html"), name='contributor-created'),
    path("<slug:short_name>/agreement", AgreementView.as_view(), name="agreement"),
    path("<slug:short_name>/materials/contribute", views.submission),
    path("<slug:short_name>/materials/contribute/thanks", KronofotoTemplateView.as_view(template_name="kronofoto/pages/submission_received.html")),
    path("<slug:short_name>/contribute", views.submission, name="submission-create"),
    path("<slug:short_name>/contribute/terms", views.list_terms, name="term-list"),
    path("<slug:short_name>/contribute/terms/define", views.define_terms, name="define-terms"),
    path("<slug:short_name>/contribute/thanks", KronofotoTemplateView.as_view(template_name="kronofoto/pages/submission_received.html"), name="submission-done"),
    path('<slug:short_name>/data.json', views.datadump, name="data-dump"),
    path("<slug:short_name>@<str:domain>/", include(urlpatterns)),
    path("<slug:short_name>/", include(urlpatterns)),
    path("placetypes", views.places.place_types),
    path("placetypes/<int:pk>", views.places.placelist, name="placelist"),
    path(settings.IMAGE_CACHE_URL_PREFIX + "images/<int:block1>/<int:block2>/<str:profile1>.jpg", views.resize_image, name="resize-image"),
    path("", include("fortepan_us.kronofoto.views.vector_tiles")),
]
