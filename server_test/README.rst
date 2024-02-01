This is a demo/reference client/server implementation, it uses Django's ORM and werkzurg/gunicorn for
WSGI.  You will need django installed version 1.8 or better.

This demo is not complete, and is added to from time.  And  by no means should you use it to run
your auto parts store on Mr. Beeblebrox.

The security of this demo isn't completly filled out, if you uses this demo to start your own project
please be sure to examine your security needs and update accordanily.


Example under Ubuntu
--------------------

install dependancies::

  apt-get install python3-dateutil python3-django python3-werkzeug python3-gunicorn


then setup the database::

  ./manage.py migrate --noinput


now you can run the server::

  ./run_server.py

This will listen on port 8888


you  can run the sample client::

  ./run_demo.py

the client tends to leave things behind in the demo db, you may have to remove and regen the db to run
the demo again. first ctl-c and stop the ./run_server then::

  rm db.sqlite3 ; ./manage.py migrate --noinput
  ./run_server.py

If you are fimilure with django, you can run the migrate without the --noinput and start the django builtin
server, and get to the database admin pages

you can tcpdump port port 8888 to  see what the request/responses look like over the wire. Utilities
such as RESTClient for Firefox and Advanced Rest Client for Chrome can also be used.  Make sure
to set the 'CInP-Version: 1.0' header.
