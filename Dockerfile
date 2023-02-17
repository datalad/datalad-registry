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

#  === Move the app code into the container ===
# todo: This is needed possibly because the current installation of the app requires
#       git repo references. If Poetry is used for this project, this may not be needed.
COPY .git .git/

COPY datalad_registry datalad_registry/
COPY pyproject.toml pyproject.toml
COPY setup.cfg setup.cfg
COPY setup.py setup.py
#  === Move the app code into the container ends ===

# Install the app in the container
RUN pip3 install wheel && pip3 install . && mkdir -p instance
