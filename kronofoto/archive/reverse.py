from django.urls import reverse as django_reverse, resolve as django_resolve, ResolverMatch
from django.contrib.sites.shortcuts import get_current_site
from threading import local
from dataclasses import dataclass
from django.contrib.sites.models import Site
from urllib.parse import urlparse

requests = local()

@dataclass
class ResolveResults:
    domain: str
    match: ResolverMatch

def get_request():
    return getattr(requests, 'current_request', None)

def set_request(req):
    requests.current_request = req

def as_absolute(uri):
    req = get_request()
    return req.build_absolute_uri(uri) if req else uri

def reverse(viewname, urlconf=None, args=None, kwargs=None, current_app=None, domain=None):
    domain = domain or Site.objects.get_current().domain
    uri = django_reverse(viewname, urlconf=urlconf, args=args, kwargs=kwargs, current_app=current_app)
    return "//{domain}{uri}".format(domain=domain, uri=uri)

def resolve(path, urlconf=None):
    parseResults = urlparse(path)
    match = django_resolve(parseResults.path)
    return ResolveResults(parseResults.netloc, match)
