[![codecov](https://codecov.io/gh/datalad/datalad-registry/branch/master/graph/badge.svg?token=CY783CBF77)](https://codecov.io/gh/datalad/datalad-registry)

DataLad registry -- work in progress

  * https://github.com/datalad/datalad/issues/947

---

### NEW Development setup

#### Prerequisites

  * [git](https://git-scm.com/downloads)
  * [git-annex](https://git-annex.branchable.com/install/)
  * [Podman](https://podman.io/docs/installation)

Though we only test Datalad-Registry fully with Podman, you should be able to use Docker
to launch a Datalad-Registry instance with little to no deviation from this guide.

#### To run tests

1. Setup

    1. On Debian systems, install the necessary dependencies for Python PostgreSQL libs:

       `sudo apt-get install libpq-dev python3-dev`

    2. Create a virtual env, activate it, and install Datalad-Registry for testing in
       it:

       `py=3; d=venvs/dev$py; python$py -m venv $d && source $d/bin/activate && python3 -m pip install -e .[tests]`

    3. Install podman-compose for launching the needed components of DataLad-Registry
       for testing:

       `pip install podman-compose`

    4. Launch the needed components of DataLad-Registry for testing:

       `podman-compose -f docker-compose.testing.yml --env-file env.testing up -d`

2. Test execution

    1. Load environment variables from the `env.testing` in a subshell and
       launch the tests within this subshell (Note: using a subshell avoids polluting
       the current shell with the environment variables from the `env.testing`
       file)

       `(set -a && . ./env.testing && set +a && python -m pytest -s -v)`

3. Teardown

   When the testing is done, you can bring down the components of Datalad-Registry
   launched and deactivate the virtual environment activated:

    1. Bring down the components of Datalad-Registry launched:

       `podman-compose -f docker-compose.testing.yml --env-file env.testing down`

    2. Deactivate the virtual environment activated:

       `deactivate`


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

### Read-Only Mode

Datalad-Registry can operate in a read-only mode. In this mode, Datalad-Registry
consists of two services, a web service that accepts only read-only requests and
a read-only database service, as define in `docker-compose.read-only.yml`.
The read-only database service is a replica of the database service in an instance of
Datalad-Registry that allows both reads and writes,
operating in `PRODUCTION` or `DEVELOPMENT` mode.

To set up Datalad-Registry to run in read-only mode involves the following steps:

1. Configure the database service of an existing instance of Datalad-Registry that
   allows both reads and writes, operating in `PRODUCTION` or `DEVELOPMENT` mode, to
   be the primary database service that the database service in the read-only instance
   of Datalad-Registry will replicate from.
   1. Create a role in the primary database service for replication by executing
      the following SQL command via `psql` or any other PostgreSQL client.
      ```SQL
      CREATE ROLE <replica_user> WITH REPLICATION LOGIN ENCRYPTED PASSWORD '<password>';
      ```
      where `<replica_user>` is the name of the role and `<password>` is the password
      for the role to access the primary database service.
   2. Modify the [`postgresql.conf`](https://www.postgresql.org/docs/16/config-setting.html#CONFIG-SETTING-CONFIGURATION-FILE) configuration file of the primary database service.
      1. Enable the [`wal_level`](https://www.postgresql.org/docs/16/runtime-config-wal.html#GUC-WAL-LEVEL) configuration parameter and set its value to `replica`.
      2. Enable the [`wal_log_hints`](https://www.postgresql.org/docs/16/runtime-config-wal.html#GUC-WAL-LOG-HINTS) configuration parameter and set its value to `on`.
      3. Enable the [`wal_keep_size`](https://www.postgresql.org/docs/16/runtime-config-replication.html#GUC-WAL-KEEP-SIZE) configuration parameter and set its value to `1024`.
   3. Modify the [`pg_hba.conf`](https://www.postgresql.org/docs/16/auth-pg-hba-conf.html#AUTH-PG-HBA-CONF) configuration file of the primary database service.
      1. Add the following line to the end of the file.
         ```
         host replication   <replica_user>  <replica_source_ip>/32   md5
         ```
         where `<replica_user>` is the name of the role created two steps before, and
         `<replica_source_ip>` is the IP address of the replica database service in
         the read-only instance of Datalad-Registry. (Note: `<replica_source_ip>/32` as
         a whole specifies a range of IP addresses that a replica database service can
         connect from.)

   ##### Note:
   The location of the `postgresql.conf` and `pg_hba.conf` configuration files
   depends on the individual setup of PostgreSQL. All PostgreSQL setups defined in all
   the Docker Compose files in this project store the `postgresql.conf` and
   `pg_hba.conf` configuration files in `/var/lib/postgresql/data`.
   The application of any changes in the `postgresql.conf` file requires a restart
   of the PostgreSQL service. The application of any changes in the `pg_hba.conf` file
   can be accomplished by either restarting the PostgreSQL service or executing
   the following SQL command via `psql` or any other PostgreSQL client.
   ```SQL
   SELECT pg_reload_conf();
   ```
2. Set up the database service of the read-only instance of Datalad-Registry to be
   a read-only replica of the primary database service.
   1. Take a base backup of the primary database service at a node that is to be served
      as the read-only replica.
      1. Start this node with an empty data directory.
         1. Uncomment the line `command: ["tail", "-f", "/dev/null"]` in
            `docker-compose.read-only.yml`. (This allows starting of the node without
            starting the PostgreSQL service and populating the data directory.)
         2. Start the node by executing the following command.
            ```bash
            (set -a && . ./.env.read-only && set +a && podman-compose -f docker-compose.read-only.yml up read-only-db -d)
            ```
            where `.env.read-only` is a file containing the needed environment variables.
            You can use the `template.env.read-only` file as a template to construct
            this file.
      2. Run the base backup command inside the node.
         1. Get into the BASH shell of the node by running the following command.
            ```bash
            podman exec -it <name_of_the_node> /bin/bash
            ```
            where `<name_of_the_node>` is the name of the container that is the node.
         2. Run the following command [`pg_basebackup`](https://www.postgresql.org/docs/16/app-pgbasebackup.html).
            ```bash
            pg_basebackup -h <primary_ip> -p <port_number> -U <replica_user> -X stream -C -S replica_1 -v -R -W -D /var/lib/postgresql/data
            ```
            where `<primary_ip>` is the IP address of the primary database service,
            `<port_number>` is the port number of the primary database service, and
            `<replica_user>` is the name of the role created in the primary database
            in step 1.
         3. Once the backup is complete, exit the bash shell of the node by running
            the following command.
            ```bash
            exit
            ```
      3. Stop the node by running the following command.
         ```bash
         (set -a && . ./.env.read-only && set +a && podman-compose -f docker-compose.read-only.yml up down)
         ```
      4. Restore the `docker-compose.read-only.yml` file to its original state by
         commenting out the line `command: ["tail", "-f", "/dev/null"]`.

After going through the above steps, the initial setup for running Datalad-Registry
in read-only mode is complete. To start the read-only instance of Datalad-Registry,
just run the following command.
```bash
(set -a && . ./.env.read-only && set +a && podman-compose -f docker-compose.read-only.yml up -d --build)
```


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
