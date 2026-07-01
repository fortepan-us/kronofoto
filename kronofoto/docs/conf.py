# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
import os, sys, django
sys.path.insert(0, os.path.abspath('..'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tests.settings')
django.setup()

project = 'kronofoto'
copyright = '2025, fortepan_us'
author = 'fortepan_us'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinxcontrib_django",
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

napoleon_google_docstring = True
napoleon_use_param = True
napoleon_use_rtype = True
django_show_db_tables = True

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']


def setup(app):
    # sphinxcontrib_django's docstring processor assumes every documented
    # class is a concrete Django model with a populated `_meta`. The bare
    # `django.db.models.Model` class itself has none (it's abstract), but
    # still gets swept up by autodoc when a module imports it directly for
    # type hints (e.g. admin.py's `Type[Model]` annotations), crashing the
    # build. Skip it before sphinxcontrib_django ever sees it.
    from django.db.models import Model as DjangoModel

    def skip_bare_django_model(app, what, name, obj, skip, options):
        if what == "class" and obj is DjangoModel:
            return True
        return skip

    app.connect("autodoc-skip-member", skip_bare_django_model)
