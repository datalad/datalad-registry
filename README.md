DataLad registry -- work in progress

  * [docs/openapi.yml](docs/openapi.yml)
  * https://github.com/datalad/datalad/issues/947

---

### Development setup

Here are steps for setting up a development environment either 1)
using a virtual environment for everything but the celery broker or 2)
using containers for both the Flask and Celery components.  Note that
these steps are not required to execute the pytest-based test suite.

#### Virtual environment with container for Celery broker

After setting up the virtual environment for the project, execute the
following from the top-level of repository.

```console
$ ./up
```

#### Containers for Flask app, Celery broker, and Celery worker

Alternatively, do the following from the top-level of repository.

```console
$ docker-compose up
```

With a virtual environment activated, the database at
instance/registry.sqlite can optionally be initiated before executing
the above command by running `./flask init-db`.  This makes inspecting
the database from the local machine easier because the permissions
will match the local user's.

#### Sample request

The request below should work after completing either of the setups
above.

```console
$ curl http://127.0.1:5000/v1/datasets/6eeadb86-84be-11e6-b24c-002590f97d84/urls
{
  "ds_id": "6eeadb86-84be-11e6-b24c-002590f97d84",
  "urls": []
}
```
