FROM neurodebian:latest
WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get install -y --no-install-recommends eatmydata && \
    eatmydata apt-get install -y --no-install-recommends gnupg locales && \
    echo "en_US.UTF-8 UTF-8" >>/etc/locale.gen && locale-gen && \
    eatmydata apt-get install -y --no-install-recommends \
      git python3-pip git-annex-standalone datalad && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN git config --system user.name "dl-registry" && \
    git config --system user.email "dl-registry@example.com"

COPY datalad_registry datalad_registry/
COPY pyproject.toml pyproject.toml
COPY setup.cfg setup.cfg
COPY setup.py setup.py

RUN pip3 install wheel && pip3 install . && mkdir -p instance
