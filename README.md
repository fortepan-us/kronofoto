# kronofoto

# Install the dependencies:

You must use Python 3. Optionally, you probably should use a virtual environment:

    python -m venv kfenv
    source kfenv/bin/activate
    
Install dependencies:

    python -m pip install -r requirements.txt

# Configure kronofoto:

Copy the examplesettings.py file in the kronofoto directory to settings.py. Fill in the missing values.

Run the migrations:

    ./manage.py migrate

Create the cache table:

    ./manage.py createcachetable
    
Create a superuser account:

    ./manage.py createsuperuser

The test server can then be started up:

    ./manage.py runserver 0.0.0.0:8000

You will also need to log into the admin and [change the site domain](http://127.0.0.1:8000/admin/sites/site/) from example.com to 127.0.0.1:8000.

    http://127.0.0.1:8000/admin/sites/site/
