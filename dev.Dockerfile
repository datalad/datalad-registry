FROM docker.io/debian:11
WORKDIR /app

# Install dependencies
# TODO: Consider removing the eatmydata dependency. It may not be needed.
RUN DEBIAN_FRONTEND=noninteractive apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends eatmydata && \
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
      && \
    DEBIAN_FRONTEND=noninteractive apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Set user info for git (needed for datalad operations)
RUN git config --system user.name "dl-registry" && \
    git config --system user.email "dl-registry@example.com"

RUN ["pip3", "install", "--no-cache-dir", "-U","pip", "setuptools"]

RUN ["pip3", "install", "--no-cache-dir", "wheel"]

COPY requirements.txt requirements.txt

RUN ["pip3", "install", "--no-cache-dir", "-r", "requirements.txt"]

COPY setup.cfg setup.cfg
COPY setup.py setup.py
COPY pyproject.toml pyproject.toml

COPY datalad_registry_client datalad_registry_client
COPY .git .git
COPY datalad_registry datalad_registry

RUN ["pip3", "install", "--no-cache-dir", "."]
