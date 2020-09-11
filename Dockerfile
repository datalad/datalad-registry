FROM python:3.7-alpine
WORKDIR /app

RUN apk add --no-cache gcc musl-dev linux-headers

COPY datalad_registry datalad_registry/
COPY pyproject.toml pyproject.toml
COPY setup.cfg setup.cfg
COPY setup.py setup.py

RUN pip install . && mkdir -p instance
