DataLad registry -- work in progress

  * [docs/api.md](docs/api.md)
  * https://github.com/datalad/datalad/issues/947

---

### Development setup

Here are steps for setting up a development environment either 1)
using a virtual environment for everything but the celery broker or 2)
using containers for both the Flask and Celery components.

#### Virtual environment with container for Celery broker

After setting of the virtual environment for the project, execute the
following from the top-level of repository.

```console
$ docker-compose -f docker-compose.broker.yml up -d
$ python -m celery worker -A datalad_registry.runcelery.celery &
$ ./flask init-db
$ ./flask run
```

#### Containers for Flask app, Celery broker, and Celery worker

Alternatively, do the following from the top-level of repository.

```console
$ mkdir -p instance
$ sqlite3 <datalad_registry/schema.sql instance/registry.sqlite
$ docker-compose up
```

With a virtual environment set up and activated, the first and second
steps above can be replaced by `./flask init-db`.

### Sample request

The request below should work after completing either of the setups
above.

```console
$ curl http://127.0.1:5000/v1/datasets/6eeadb86-84be-11e6-b24c-002590f97d84/urls
{
  "dsid": "6eeadb86-84be-11e6-b24c-002590f97d84",
  "urls": []
}
```
