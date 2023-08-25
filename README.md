[![codecov](https://codecov.io/gh/datalad/datalad-registry/branch/master/graph/badge.svg?token=CY783CBF77)](https://codecov.io/gh/datalad/datalad-registry)

DataLad registry -- work in progress

  * https://github.com/datalad/datalad/issues/947

---

### NEW Development setup

#### To run tests

On Debian systems install necessary for Python PostgreSQL libs dependencies:

    apt-get install postgresql-common libpq-dev

Create virtual env with e.g.,

    py=3; d=venvs/dev$py; python$py -m venv $d && source $d/bin/activate && python3 -m pip install -e .[tests]

Start the docker instances of postgres, rabbitmq, and redis:

    docker-compose -f docker-compose.testing.yml --env-file template.env.testing up -d

Now can run the tests after loading environment variables from the temaplte.env.testing.
Using the next shell within to avoid polluting current environment:

    ( set -a && source template.env.testing && set +a && python -m pytest -s -v  )

In the future - above logic would migrate into the session-scoped pytest fixture, [issue #224](https://github.com/datalad/datalad-registry/issues/224).

#### To develop

The template file `template.env.dev` provides all environment variables with some default values.
Copy it to some file and modify secrets (passwords) from the default values, e.g.

    cp template.env.dev .env.dev
    sed -e 's,pass$,secret123t,g' -i .env.dev

*note*: we git ignore all `.env` files.

Now we have two ways to start the services in a development mode, server based and locally based.
Both ways use the `docker-compose.dev.yml` file, and the local development mode also uses
the `docker-compose.dev.local.override.yml` file to achieve a bind mount to the current
directory at the host machine as `/app` within web service container.

##### Server development mode

where the web service will use the copy of the codebase shipped in the docker image of Datalad-registry and not react to the changes in the codebase at the host machine:

    docker compose -f docker-compose.dev.yml --env-file .env.dev up -d --build

The `instance` directory for the web service is in the directory allocated for the web service at the host machine as specified in the `.env.dev` file.

##### Local development mode

where the web service will use the codebase at the host machine, react to the changes in this codebase, and operate in debug mode:

    docker compose -f docker-compose.dev.yml -f docker-compose.dev.local.override.yml --env-file .env.dev up -d --build

The `instance` directory for the web service is in the current directory at the host machine, which is also the codebase in the host machine.

*Note*: Other services will not react to the changes in the codebase at the host machine.

### OLD Development setup

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
