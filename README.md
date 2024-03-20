[![codecov](https://codecov.io/gh/datalad/datalad-registry/branch/master/graph/badge.svg?token=CY783CBF77)](https://codecov.io/gh/datalad/datalad-registry)

Datalad-Registry is now live at [registry.datalad.org](http://registry.datalad.org/).

---
### Preface

We fully test Datalad-Registry with Podman. Nevertheless, you should be able to launch
a Datalad-Registry instance using Docker with little to no deviation from this guide.

### Testing and Development Setup

#### Prerequisites

* The following dependencies are needed in a system in order to test and develop
  Datalad-Registry:

    * [git](https://git-scm.com/downloads)
    * [git-annex](https://git-annex.branchable.com/install/)
    * [Podman](https://podman.io/docs/installation)
    * [podman-compose](https://github.com/containers/podman-compose)

      We strongly recommend installing `podman-compose` and other Python dependencies in
      a [Python virtual environment](https://docs.python.org/3/library/venv.html) for
      this project.

* We use [versioningit](https://github.com/jwodder/versioningit) to determine the
  version of the built package of Datalad-Registry based on the tags in the Git
  repository from which the package is built. To ensure the Datalad-Registry package can
  be built successfully and has the correct version, please make sure your clone
  of [the Datalad-Registry repository](https://github.com/datalad/datalad-registry) have
  all [the tags from the originating repository](https://github.com/datalad/datalad-registry/tags).
  (If you are building the package from an immediate clone
  of [the Datalad-Registry repository](https://github.com/datalad/datalad-registry),
  most likely the clone already have all the tags needed. If you are building the
  package from a clone of a fork
  of [the Datalad-Registry repository](https://github.com/datalad/datalad-registry), you
  may need to
  add [the Datalad-Registry repository](https://github.com/datalad/datalad-registry) as
  a remote to your clone and fetch all the tags from it.)

#### To run tests

1. Setup

    1. On Debian systems, install the necessary dependencies for Python PostgreSQL libs:

       `sudo apt-get install libpq-dev python3-dev`

    2. Install Datalad-Registry for testing in
       the [Python virtual environment](https://docs.python.org/3/library/venv.html) for
       this project (as mentioned in the Prerequisites section):

       `pip install -e .[test]`

    3. Launch the needed components of DataLad-Registry for testing from a subshell with
       needed environment variables loaded from `env.test`.
       (Note: using a subshell avoids polluting the current shell with the environment
       variables from `env.test`):

       `(set -a && . ./env.test && set +a && podman-compose -f docker-compose.test.yml up -d)`

2. Test execution
    1. Launch the tests from a subshell with the needed environment variables loaded
       from `env.test`:

       `(set -a && . ./env.test && set +a && python -m pytest -s -v)`

3. Teardown

   When the testing is done, you can bring down the components of Datalad-Registry
   launched.

    1. Bring down the components of Datalad-Registry launched from a subshell with
       the needed environment variables loaded from `env.test`:

       `(set -a && . ./env.test && set +a && podman-compose -f docker-compose.test.yml down)`

#### To develop

1. Setup

    1. On Debian systems, install the necessary dependencies for Python PostgreSQL libs:

       `sudo apt-get install libpq-dev python3-dev`

    2. Install Datalad-Registry for development in
       the [Python virtual environment](https://docs.python.org/3/library/venv.html) for
       this project (as mentioned in the Prerequisites section):

       `pip install -e .[dev]`

    3. Set values for needed environment variables by creating a `.env.dev` file

       `template.env` is a template for creating the `.env.dev` file. It lists
       all the needed environment variables with defaults. We will use it to create
       the `.env.dev` file.

        1. Create the `.env.dev` file by copying the `template.env` file to `.env.dev`:

           `cp template.env .env.dev`

        2. Modify the `.env.dev` file according to your needs by adjusting the values
           for usernames, passwords, etc.

       *note*: we git ignore all `.env` files.

    4. Launch the needed components of DataLad-Registry for development from a subshell
       with needed environment variables loaded from `.env.dev`.
       (Note: using a subshell avoids polluting the current shell with the environment
       variables from `.env.dev`):

       `(set -a && . ./.env.dev && set +a && podman-compose -f docker-compose.yml -f docker-compose.dev.override.yml up -d --build)`

2. Development

   At this point, the proper development environment is set up. However, please
   note the following characteristics of this development environment:

    1. The current directory at the host is bind-mounted to the `/app` directory within
       the web service container.
    2. The subdirectory `./instance` at the host is bind-mounted to the `/app/instance`
       directory within the web service container to serve as the instance folder for
       the Flask application run by the web service container.
    3. The web service container runs the Flask application in debug mode and reacts to
       changes in the current directory, the codebase, at the host machine.
    4. All other component services of Datalad-Registry, as defined in
       `docker-compose.yml`, do not react to changes in the codebase at
       the host machine. (Note: This behavior is the result of a design choice.
       The worker service, a Celery worker, for example, should not react to changes
       in the codebase at the host machine for the tasks it executes may not always
       be idempotent.)
        1. To realize the changes in the codebase at the host machine in other component
           services, you needed to bring down all the components of Datalad-Registry as
           specified in the following Teardown section and relaunch them according to
           the above Setup section.

3. Teardown

   When done with developing, you can bring down the components of Datalad-Registry
   launched.

    1. Bring down the components of Datalad-Registry launched from a subshell with
       the needed environment variables loaded from `.env.dev`:

       `(set -a && . ./.env.dev && set +a && podman-compose -f docker-compose.yml -f docker-compose.dev.override.yml down)`

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
         (set -a && . ./.env.read-only && set +a && podman-compose -f docker-compose.read-only.yml down)
         ```
      4. Restore the `docker-compose.read-only.yml` file to its original state by
         commenting out the line `command: ["tail", "-f", "/dev/null"]`.

After going through the above steps, the initial setup for running Datalad-Registry
in read-only mode is complete. To start the read-only instance of Datalad-Registry,
just run the following command.
```bash
(set -a && . ./.env.read-only && set +a && podman-compose -f docker-compose.read-only.yml up -d --build)
```
