#
# Docker file for the container of the web, worker, scheduler, and monitor services
#

FROM docker.io/phusion/baseimage:jammy-1.0.1
WORKDIR /app

# A workaround for setting the HOME environment variable
# when /sbin/my_init is used as the init process.
# See https://github.com/phusion/baseimage-docker?tab=readme-ov-file#environment-variables
# for more information.
RUN echo /root > /etc/container_environment/HOME

# Install dependencies
# TODO: Consider removing the eatmydata dependency. It may not be needed.
RUN DEBIAN_FRONTEND=noninteractive apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends eatmydata && \
    DEBIAN_FRONTEND=noninteractive apt-get upgrade -y -o Dpkg::Options::="--force-confold" && \
    DEBIAN_FRONTEND=noninteractive eatmydata apt-get install -y --no-install-recommends gnupg locales && \
    echo "en_US.UTF-8 UTF-8" >>/etc/locale.gen && locale-gen && \
    DEBIAN_FRONTEND=noninteractive eatmydata apt-get install -y --no-install-recommends \
      build-essential \
      datalad \
      git \
      git-annex \
      libpq-dev \
      python3-dev \
      python3-pip \
      python3-venv \
      python3-gdbm \
      && \
    DEBIAN_FRONTEND=noninteractive apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Create a Python virtual environment
RUN python3 -m venv /venv

# Activate the virtual environment
ENV PATH="/venv/bin:$PATH"

# Set user info for git (needed for datalad operations)
RUN git config --system user.name "dl-registry" && \
    git config --system user.email "dl-registry@example.com"

RUN ["pip3", "install", "--no-cache-dir", "-U","pip", "setuptools"]

COPY requirements.txt requirements.txt

RUN ["pip3", "install", "--no-cache-dir", "-r", "requirements.txt"]

COPY setup.cfg setup.cfg
COPY setup.py setup.py
COPY pyproject.toml pyproject.toml

COPY datalad_registry_client datalad_registry_client
COPY .git .git
COPY datalad_registry datalad_registry

RUN ["pip3", "install", "--no-cache-dir", "."]
