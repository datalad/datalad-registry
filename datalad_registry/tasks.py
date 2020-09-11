from datalad_registry import celery
from datalad_registry import db


@celery.task()
def verify_url(url, token):
    import time
    time.sleep(30)
    db.write("UPDATE tokens SET status = 2 WHERE token = ?",
             token)
