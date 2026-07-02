**Kronofoto** is an extremely user-friendly upload and display tool, which arranges images along a simple but engaging timeline. Using Kronofoto, users can fast forward toward the present or backward deeper into the past. The code for Kronofoto can be used for all sorts of different collection types beyond photographs.

Unlike archive-style digital repositories, which often mirror the priorities of physical archives and divide collections by provenance, Kronofoto prioritizes the experience of browsing to explore images of the past by time, supported by robust metadata, tagging, and search features. This creates a fundamentally different viewing experience than clicking around in segmented collections–more delightful, more diverse, more holistic, more grounded in the social history of a collection.


Kronofoto features a suite of tools to engage the public in visual history and customize user experience. 
MyList allows researchers and creators to create customized lists of photos according to their own interests and needs. Lists are viewable in grid or timeline view, and can be saved for future reference, shared with others, and even embedded into a website. 

* **Embed** allows community institutions to embed any version of a collection into their own website (for example, all the photos from their particular town; all the musical programs from a particular year) making images most relevant to their publics immediately available. 

* **Exhibit** (in development) empowers users to curate a digital exhibit or story. Users will be able to draw upon any image from the Kronofoto portal and insert it into a variety of text + image template options, which  create a dynamic vertical exhibit with parallax scrolling. Users will also be able to embed their final exhibits into another website.

* **Krono360** (in development) is an immersive visual geolocation tool that exactly and beautifully situates historic photographs in the modern landscape with an immersive degree of visual precision.

# Install the dependencies:

You must use Python 3. Dependencies and virtual environments are managed with
[Hatch](https://hatch.pypa.io/) (see `kronofoto/pyproject.toml`), not a plain
`requirements.txt` venv.

Install Hatch:

    pip install hatch

You'll also need the system GIS libraries used by the spatialite database backend:

    sudo apt-get install gdal-bin spatialite-bin libsqlite3-mod-spatialite

# Configure kronofoto:

Settings live in `kronofoto/fortepan_us/settings/` (`dev.py`, `prod.py`, etc.) —
there is no `examplesettings.py` to copy. For local development, set:

    export SECRET_KEY=some-dev-secret
    export DJANGO_SETTINGS_MODULE=fortepan_us.settings.dev

Hatch will create its virtual environment and install dependencies automatically
the first time you run a command. All commands below are run from the
`kronofoto/kronofoto` directory (the inner one, next to `pyproject.toml`):

    cd kronofoto

Run the migrations:

    hatch run manage migrate

Create the cache table:

    hatch run manage createcachetable

Create a superuser account:

    hatch run manage createsuperuser

The test server can then be started up:

    hatch run manage runserver 0.0.0.0:8000

Note: `APPEND_SLASH` is disabled in the dev settings, so URLs like `/admin`
will 404 — always include the trailing slash (`/admin/`).

You will also need to log into the admin and [change the site domain](http://127.0.0.1:8000/admin/sites/site/) from example.com to 127.0.0.1:8000.

    http://127.0.0.1:8000/admin/sites/site/
