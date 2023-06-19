[![codecov](https://codecov.io/gh/datalad/datalad-registry/branch/master/graph/badge.svg?token=CY783CBF77)](https://codecov.io/gh/datalad/datalad-registry)

DataLad registry -- work in progress

  * https://github.com/datalad/datalad/issues/947

---

### Development setup

Here are steps for setting up a development environment either 1)
using a virtual environment for everything but the Celery broker, or 2)
using containers for both the Flask and Celery components.  Note that
these steps are not required to execute the pytest-based test suite.

#### Virtual environment with container for Celery broker ("develop mode")

After setting up the virtual environment for the project, run `./up develop`
from the top level of the repository in order to run the Flask process in the
foreground.  To run it in the background instead, run `./up --bg develop`.

Alternatively, one can run `./up-tests develop`, which runs `./up --bg develop`
with a temporary directory as the instance path and also waits for the Flask
process to start receiving connections before finishing.

To bring down the Docker containers started by `up`, run `./down`.  If
`up-tests` was run, the background Flask and Celery processes can be brought
down as well by instead running `./down develop`.

#### Containers for Flask app, Celery broker, and Celery worker

To run all of the Flask, Celery, etc. processes inside Docker containers, run
just `./up` from the top level of the repository.  To bring down the Docker
containers, run `./down`.

#### Sample request

The request below should work after completing either of the setups above.

```console
$ curl http://127.0.1:5000/v1/datasets/6eeadb86-84be-11e6-b24c-002590f97d84/urls
{
  "ds_id": "6eeadb86-84be-11e6-b24c-002590f97d84",
  "urls": []
}
```

#### Environment Variables

The server instance can be configured via the following environment variables
when running the `up` or `up-tests` scripts:

- `DATALAD_REGISTRY_PASSWORD` — *(required)* the password to use for the
  PostgreSQL database and RabbitMQ instance.

- `DATALAD_REGISTRY_INSTANCE_PATH` — The directory in which to store the
  server's data; defaults to `$PWD/instance`.  When running Flask inside a
  Docker container, this is the path on the host where the data will be
  mounted.

- `DATALAD_REGISTRY_DB_INSTANCE_PATH` — The directory at which to mount the
  contents of the PostgreSQL database; defaults to
  `$DATALAD_REGISTRY_INSTANCE_PATH/db`.

- `DATALAD_REGISTRY_DATASET_CACHE` — The directory in which to cache DataLad
  repositories; defaults to `$DATALAD_REGISTRY_INSTANCE_PATH/cache`.  This only
  has an effect in develop mode.

- `DATALAD_REGISTRY_LOG_LEVEL` — Logging level for the Flask and Celery
  processes; defaults to `DEBUG`.  This only has an effect in develop mode.


### Running tests

Tests are run with pytest, which can be invoked by running `tox`.  By default,
the tests will create & use a Dockerized PostgreSQL instance with a random
password which is destroyed when the tests finish.  To keep the PostgreSQL
container around after the tests finish, set the
`DATALAD_REGISTRY_PERSIST_DOCKER_COMPOSE` environment variable to a value other
than `0`.

To use the PostgreSQL container brought up by `./up` instead, pass the
`--devserver` option to pytest (When using tox, this can be done by running
`tox -- --devserver`) and ensure that the `DATALAD_REGISTRY_PASSWORD`
environment variable is set to the proper value.
