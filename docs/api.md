
### Registering new dataset URL

Registering a new URL for a dataset consists of the following steps:

  * retrieving a challenge token

  * adding the challenge token to the specified git reference and
    making that change available via the URL

  * issuing a request to add the URL


#### Getting challenge token

    GET /v1/datasets/{dsid}/urls/{url_encoded}/token

Get a challenge token for dataset `dsid` and base64-encoded
`url_encoded` (using Python's URL-safe character set).

Sample request:

    curl \
      $E/v1/datasets/6eeadb86-84be-11e6-b24c-002590f97d84/urls/aHR0cHM6Ly9kYXRhc2V0cy5kYXRhbGFkLm9yZy9sYWJzL2hheGJ5L3JhaWRlcnMvLmdpdA==/token

Sample response:

    Status: 200
    Cache-Control: max-age=600

    {
        "dsid": "6eeadb86-84be-11e6-b24c-002590f97d84",
        "url": "https://datasets.datalad.org/labs/haxby/raiders/.git",
        "ref": "refs/datalad-registry/0612a88655746eb05d73732e9cc5ea289253a53b",
        "token": "0612a88655746eb05d73732e9cc5ea289253a53b"
    }


#### Add new URL

    POST /v1/datasets/{dsid}/urls

    {
        "url": "URL",
        "token": "TOKEN",
        "ref": "REF"
    }

Sample request:

    curl -X POST -H "Content-Type: application/json" \
      -d '{"url": "https://datasets.datalad.org/labs/haxby/raiders/.git",
           "token": "0612a88655746eb05d73732e9cc5ea289253a53b",
           "ref": "refs/datalad-registry/0612a88655746eb05d73732e9cc5ea289253a53b"}' \
      $E/v1/datasets/6eeadb86-84be-11e6-b24c-002590f97d84/urls

Sample response:

    Status: 202
    Location: /v1/datasets/6eeadb86-84be-11e6-b24c-002590f97d84/urls/aHR0cHM6Ly9kYXRhc2V0cy5kYXRhbGFkLm9yZy9sYWJzL2hheGJ5L3JhaWRlcnMvLmdpdA==

    {
        "dsid": "6eeadb86-84be-11e6-b24c-002590f97d84",
        "url": "aHR0cHM6Ly9kYXRhc2V0cy5kYXRhbGFkLm9yZy9sYWJzL2hheGJ5L3JhaWRlcnMvLmdpdA=="
    }


#### Query status of added URL

    GET /v1/datasets/{dsid}/urls/{url_encoded}

Sample request:

    curl \
      $E/v1/datasets/6eeadb86-84be-11e6-b24c-002590f97d84/urls/aHR0cHM6Ly9kYXRhc2V0cy5kYXRhbGFkLm9yZy9sYWJzL2hheGJ5L3JhaWRlcnMvLmdpdA==

Sample Response:

    Status: 200

    {
        "dsid": "6eeadb86-84be-11e6-b24c-002590f97d84",
        "url": "https://datasets.datalad.org/labs/haxby/raiders/.git",
        "status": "known"
    }

where `status` is "unknown", "known", "URL pending verification", and
"verification failed".


### Getting URLs for a dataset

    GET /v1/datasets/{dsid}/urls

Sample request:

    curl $E/v1/datasets/6eeadb86-84be-11e6-b24c-002590f97d84/urls

Sample response:

    Status: 200

    {
        "dsid": "6eeadb86-84be-11e6-b24c-002590f97d84",
        "urls": ["https://datasets.datalad.org/labs/haxby/raiders/.git"]
    }
